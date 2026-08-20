# -*- coding: utf-8 -*-
"""AI 自测实验：把题面喂给 CodeBuddy 会话中的 GLM（本仓库的开发 AI）真实作答。

流程:
  1. gen    生成 60 格题面（10 题 × P0/P1/P2a/P2b/P3a/P3b）到 experiment/ai_self/cases/，
            合并导出 all_cases.md 供被测模型阅读作答；
  2. 被测模型逐格作答 -> experiment/ai_self/answers.py (ANSWERS = {case_id: code})
  3. judge  读取答案 -> 真实判题引擎 + 误导检测 -> 写入 data/oj.db（model=codebuddy-glm）

用法:
  python tools/self_experiment.py gen
  python tools/self_experiment.py judge [--reset]   # --reset 先清空 experiment_runs（删除 mock 数据）
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from server import store  # noqa: E402
from server.defense.perturb import build_view, view_tests  # noqa: E402
from server.judge.engine import judge  # noqa: E402
from server.problems import get_problem, list_problems  # noqa: E402

MODEL_NAME = "codebuddy-glm"
SELF_DIR = ROOT / "experiment" / "ai_self"
CASES_DIR = SELF_DIR / "cases"

# 60 格状态设计：每题 6 格，P2/P3 各覆盖 2a 干扰注入 与 2b 约束隐藏
STATES = [
    ("P0", "original"),
    ("P1", "variant"),
    ("P2", "distractor"),        # P2a
    ("P2", "hide"),              # P2b
    ("P3", "variant_distractor"),  # P3a
    ("P3", "variant_hide"),        # P3b
]


def session_of(pid, mode):
    return "ai-self-%s-%s" % (pid, mode)


def gen():
    from experiment.run_experiment import build_prompt
    CASES_DIR.mkdir(parents=True, exist_ok=True)
    manifest, all_md = [], ["# AI 自测实验题面（60 格）", "",
                            "> 被测模型：CodeBuddy 会话 GLM（已见过题库源码，属于题解泄露场景）。",
                            "> 每格独立作答：只依据本格题面，输出一个 python 代码块。"]
    cid = 0
    for p in list_problems():
        pid = p["id"]
        problem = get_problem(pid)
        for defense, mode in STATES:
            cid += 1
            case_id = "G%02d" % cid
            session = session_of(pid, mode)
            view = build_view(problem, session, mode)
            prompt = build_prompt(problem, view)
            (CASES_DIR / (case_id + ".md")).write_text(prompt, encoding="utf-8")
            manifest.append({
                "case_id": case_id, "problem_id": pid, "title": view["title"],
                "defense": defense, "mode": mode, "submode": view["submode"],
                "session_id": session, "variant_key": view["variant_key"],
                "variant_label": view["variant_label"],
            })
            sub = {"distractor": "2a 干扰注入", "hide": "2b 约束隐藏"}.get(view["submode"], "-")
            all_md += [
                "", "---", "",
                "## %s · %s %s · %s（%s）· 版本 %s %s" % (
                    case_id, pid, view["title"], defense, sub,
                    view["variant_key"], view["variant_label"]),
                "", prompt,
            ]
    (SELF_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    (SELF_DIR / "all_cases.md").write_text("\n".join(all_md), encoding="utf-8")
    print("生成 %d 格题面 -> %s" % (len(manifest), CASES_DIR))
    print("合并题面: %s (%d KB)" % (SELF_DIR / "all_cases.md",
                                    (SELF_DIR / "all_cases.md").stat().st_size // 1024))
    print("下一步: 被测模型阅读 all_cases.md 后作答 -> experiment/ai_self/answers.py")


def judge_answers(reset):
    import importlib.util
    ans_path = SELF_DIR / "answers.py"
    if not ans_path.exists():
        print("缺少 %s，请先作答。" % ans_path)
        return
    spec = importlib.util.spec_from_file_location("ai_answers", ans_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    answers = mod.ANSWERS

    manifest = json.loads((SELF_DIR / "manifest.json").read_text(encoding="utf-8"))
    store.init_db()
    if reset:
        with store._conn() as c:
            n = c.execute("SELECT COUNT(*) FROM experiment_runs").fetchone()[0]
            c.execute("DELETE FROM experiment_runs")
        print("已清空 %d 条旧实验记录（含 mock 数据）" % n)

    from experiment.run_experiment import detect_mislead
    ok = miss = 0
    for m in manifest:
        cid = m["case_id"]
        if cid not in answers:
            print("[skip] %s 未作答" % cid)
            miss += 1
            continue
        problem = get_problem(m["problem_id"])
        view = build_view(problem, m["session_id"], m["mode"])
        code = answers[cid]
        tests = view_tests(problem, m["session_id"], m["mode"])
        result = judge(code, tests, problem["time_limit_ms"], "python3")
        raw = "```python\n%s\n```" % code
        mislead, reason = detect_mislead(problem, view, raw, code, result["detail"])
        store.add_experiment_run({
            "problem_id": m["problem_id"], "defense": m["defense"],
            "submode": view["submode"], "model": MODEL_NAME, "repeat_idx": 0,
            "session_id": m["session_id"], "variant_key": view["variant_key"],
            "prompt": (CASES_DIR / (cid + ".md")).read_text(encoding="utf-8"),
            "raw_response": raw, "extracted_code": code,
            "verdict": result["verdict"], "passed": result["passed"],
            "total": result["total"], "mislead": mislead, "mislead_reason": reason,
            "elapsed_s": None, "detail": result["detail"],
        })
        ok += 1
        print("[%s] %s × %s(%s) v%s -> %s (%d/%d)%s"
              % (cid, m["problem_id"], m["defense"], view["submode"] or "-",
                 view["variant_key"], result["verdict"], result["passed"],
                 result["total"], (" [误导] " + reason) if mislead else ""))
    print("\n完成: %d 格判题入库（%d 格未作答）。模型=%s" % (ok, miss, MODEL_NAME))
    print("下一步: python experiment/analyze.py --no-charts")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["gen", "judge"])
    ap.add_argument("--reset", action="store_true", help="判题前清空 experiment_runs 表")
    args = ap.parse_args()
    if args.action == "gen":
        gen()
    else:
        judge_answers(args.reset)


if __name__ == "__main__":
    main()
