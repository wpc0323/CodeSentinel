# -*- coding: utf-8 -*-
"""有/无防护 AI 解题对照实验：批量调度脚本。

枚举（题目 × 防护状态 × AI 模型 × 重复次数）：
  1. 组装题面（复用 server.defense，与 Web 展示完全一致）；
  2. 调用 OpenAI 兼容 API（或 --mock 本地模拟）获取解题回答；
  3. 提取 Python 代码 -> 受限子进程判题（隐藏测试点全量比对）；
  4. 误导检测（干扰注入: 回答/代码采纳蜜饵；约束隐藏: 边界测试点失守）；
  5. 全部记录写入 data/oj.db（experiment_runs 表），支持断点续跑。

用法示例:
  # 真实模型（需配置 config.json 与环境变量 API KEY）
  python experiment/run_experiment.py --config experiment/config.json
  # 本地演示（无 API，模拟模型行为，验证管线与统计）
  python experiment/run_experiment.py --mock --repeats 2
"""
import argparse
import json
import os
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402

from server import store  # noqa: E402
from server.defense.perturb import build_view, view_tests  # noqa: E402
from server.judge.engine import judge  # noqa: E402
from server.problems import get_problem, list_problems  # noqa: E402

# 防护状态 -> 展示模式选择（P2/P3 的子模式由 repeat 奇偶交替，保证 2a/2b 样本均衡）
DEFENSE_MODES = {
    "P0": lambda rep: "original",
    "P1": lambda rep: "variant",
    "P2": lambda rep: "distractor" if rep % 2 == 0 else "hide",
    "P3": lambda rep: "variant_distractor" if rep % 2 == 0 else "variant_hide",
}

PROMPT_TEMPLATE = """你是一名算法竞赛选手。请解决下面的算法题。

要求：
1. 使用 Python 3 编写程序，从标准输入读取数据，输出到标准输出；
2. 程序需要在给定的时间和内存限制内完成；
3. 请只输出一个 ```python 代码块，代码块内是完整可运行的程序，不要输出多余解释。

【题目】{title}
【题目描述】
{statement}

【输入格式】
{input_format}

【输出格式】
{output_format}

【数据范围与约定】
{constraints}

【输入样例】
{sample_inputs}

【输出样例】
{sample_outputs}"""


def build_prompt(problem, view):
    cons = "\n".join(view["constraints"]) if view["constraints"] else "（题目未单独给出）"
    return PROMPT_TEMPLATE.format(
        title="%s %s" % (view["problem_id"], view["title"]),
        statement="\n".join(view["statement"]),
        input_format=view["input_format"],
        output_format=view["output_format"],
        constraints=cons,
        sample_inputs="\n\n".join("样例 %d:\n%s" % (i + 1, s["input"].rstrip())
                                  for i, s in enumerate(view["samples"])),
        sample_outputs="\n\n".join("样例 %d:\n%s" % (i + 1, s["output"].rstrip())
                                   for i, s in enumerate(view["samples"])),
    )


def extract_code(text):
    """从模型回答中提取 Python 代码。"""
    if not text:
        return None
    m = re.search(r"```(?:python|py|Python3|python3)?[ \t]*\r?\n(.*?)```", text, re.S)
    if m:
        return m.group(1).strip()
    lines = text.split("\n")
    starts = [i for i, l in enumerate(lines)
              if l.startswith(("import ", "from ", "def ", "if __name__"))]
    if starts:
        return "\n".join(lines[starts[0]:]).strip()
    return None


# ---------------------------------------------------------------- 模型调用
def call_model(model_cfg, prompt, temperature, max_tokens, retries=2):
    api_key = os.environ.get(model_cfg.get("api_key_env", ""), "")
    if not api_key:
        raise RuntimeError("环境变量 %s 未设置，无法调用模型 %s"
                           % (model_cfg.get("api_key_env"), model_cfg["name"]))
    url = model_cfg["base_url"].rstrip("/") + "/chat/completions"
    headers = {"Authorization": "Bearer " + api_key,
               "Content-Type": "application/json"}
    body = {"model": model_cfg["model"], "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]}
    last_err = None
    for attempt in range(retries + 1):
        try:
            with httpx.Client(timeout=300) as client:
                r = client.post(url, headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("API 调用失败: %s" % last_err)


# ---------------------------------------------------------------- mock 模型（本地演示）
def _buggy_solution(pid):
    """每题的“典型错误解”，模拟模式匹配型 AI 的常见失误。"""
    return {
        "P001": "import sys\ndef main():\n    d = sys.stdin.buffer.read().split()\n    n = int(d[0]); print(sum(int(x) for x in d[1:1+n]) % 1000000007)\nmain()\n",
        "P002": "import sys\ndef main():\n    s = sys.stdin.buffer.read().decode().rstrip().lower()\n    def pal(i, j):\n        while i < j:\n            if s[i] != s[j]: return False\n            i += 1; j -= 1\n        return True\n    i, j, ok = 0, len(s) - 1, True\n    while i < j:\n        if s[i] != s[j]:\n            ok = pal(i + 1, j) or pal(i, j - 1); break\n        i += 1; j -= 1\n    print('Yes' if ok else 'No')\nmain()\n",
        "P003": "import sys\nMD = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]\ndef main():\n    y, m, d, k = map(int, sys.stdin.buffer.read().split())\n    d += k\n    while d > MD[m - 1]:\n        d -= MD[m - 1]; m += 1\n        if m > 12: m = 1; y += 1\n    print('%04d-%02d-%02d' % (y, m, d))\nmain()\n",
        "P004": "import sys\ndef main():\n    d = sys.stdin.buffer.read().split(); n = int(d[0]); iv = []\n    for i in range(n): iv.append((int(d[1 + 2 * i + 1]), int(d[1 + 2 * i])))\n    iv.sort(); cnt, last = 0, -1\n    for e, s in iv:\n        if s >= last: cnt += 1; last = e\n    print(cnt)\nmain()\n",
        "P005": "import sys\ndef main():\n    s = sys.stdin.buffer.read().decode().rstrip()\n    bal = 0\n    for ch in s:\n        if ch in '([': bal += 1\n        else: bal -= 1\n        if bal < 0: print('No'); return\n    print('Yes' if bal == 0 else 'No')\nmain()\n",
        "P006": "import sys\nfrom collections import Counter\ndef main():\n    s = sys.stdin.buffer.read().decode().rstrip()\n    c = Counter(s); mx = max(c.values())\n    for ch in s:\n        if c[ch] == mx: print(ch); return\nmain()\n",
        "P007": "import sys\ndef main():\n    d = sys.stdin.buffer.read().split(); n, W = int(d[0]), int(d[1]); dp = [0] * (W + 1)\n    for i in range(n):\n        w, v = int(d[2 + 2 * i]), int(d[3 + 2 * i])\n        for c in range(w, W + 1):\n            if dp[c - w] + v > dp[c]: dp[c] = dp[c - w] + v\n    print(dp[W])\nmain()\n",
        "P008": "import sys\nsys.setrecursionlimit(300000)\ndef main():\n    lines = sys.stdin.buffer.read().decode().rstrip().split('\\n')\n    R, C = map(int, lines[0].split()); g = lines[1:1 + R]\n    seen = set()\n    def dfs(r, c):\n        if not (0 <= r < R and 0 <= c < C) or g[r][c] == '#' or (r, c) in seen: return -1\n        if g[r][c] == 'E': return 0\n        seen.add((r, c))\n        best = -1\n        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):\n            t = dfs(r + dr, c + dc)\n            if t >= 0 and (best < 0 or t + 1 < best): best = t + 1\n        return best\n    r = dfs(*next((rr, cc) for rr in range(R) for cc in range(C) if g[rr][cc] == 'S'))\n    print(r if r >= 0 else 'No')\nmain()\n",
        "P009": "import sys\nfrom bisect import bisect_right\ndef main():\n    d = sys.stdin.buffer.read().split(); n = int(d[0]); hs = [int(x) for x in d[1:1 + n]]\n    tails = []\n    for h in hs:\n        p = bisect_right(tails, h)\n        if p == len(tails): tails.append(h)\n        else: tails[p] = h\n    print(len(tails))\nmain()\n",
        "P010": "import sys\ndef main():\n    d = sys.stdin.buffer.read().split(); n = int(d[0]); a = [int(x) for x in d[1:1 + n]]\n    ps = []\n    for i in range(n):\n        j = a.index(min(a)); x = a.pop(j)\n        j = a.index(min(a)); y = a.pop(j)\n        ps.append(x + y); a.append(x + y)\n    print(sum(ps))\nmain()\n",
    }.get(pid)


def mock_model(problem, view, defense, rep):
    """本地模拟 AI：按防护状态给出 smart / buggy / baited 三种行为的确定性抽样。"""
    rng = random.Random("mock|%s|%s|%s|%d" % (problem["id"], defense, view["variant_key"], rep))
    weights = {
        "P0": (0.75, 0.25, 0.00),
        "P1": (0.68, 0.32, 0.00),
        "P2": (0.42, 0.28, 0.30),
        "P3": (0.34, 0.31, 0.35),
    }[defense]
    kind = rng.choices(["smart", "buggy", "baited"], weights=weights)[0]
    baits = problem["distractor"]["baits"]
    if kind == "smart":
        return ("这是一道经典题，按题意模拟即可。\n```python\n%s\n```" % problem["solution"])
    if kind == "baited" or not _buggy_solution(problem["id"]):
        bait = baits[0] if baits else "提示"
        code = (_buggy_solution(problem["id"]) or problem["solution"])
        code = "# 参考: %s\n%s" % (bait, code)
        return ("注意到题目中的关键信息（%s），据此实现：\n```python\n%s\n```" % (bait, code))
    return ("按常见模板实现即可：\n```python\n%s\n```" % _buggy_solution(problem["id"]))


# ---------------------------------------------------------------- 误导检测
def detect_mislead(problem, view, response, code, judge_detail):
    """返回 (mislead 0/1, reason)。规则判（配合人工复核原始回答）。"""
    submode = view.get("submode")
    if submode == "distractor":
        text = "%s\n%s" % (response or "", code or "")
        low = text.lower()
        for bait in problem["distractor"]["baits"]:
            if bait.lower() in low:
                return 1, "采纳干扰信息（蜜饵: %s）" % bait
        return 0, ""
    if submode == "hide":
        edge_tests = {t["name"] for t in view_tests(problem, view["session_id"], view["mode"])
                      if t.get("edge")}
        lost = [d["name"] for d in judge_detail
                if d["name"] in edge_tests and d["verdict"] not in ("AC", "SKIPPED")]
        if lost:
            return 1, "遗漏关键约束（边界测试失守: %s）" % ",".join(lost)
        return 0, ""
    return 0, ""


# ---------------------------------------------------------------- 主流程
def run(args):
    problems = list_problems()
    all_ids = [p["id"] for p in problems]
    sel_problems = all_ids if args.problems in (None, "all") else [
        x.strip().upper() for x in args.problems.split(",")]

    if args.mock:
        models = [{"name": "mock-ai", "base_url": "", "model": "mock", "api_key_env": ""}]
        cfg = {"temperature": 0.2, "max_tokens": 4096, "request_interval": 0.0}
    else:
        cfg_path = ROOT / "experiment" / (args.config or "config.json")
        cfg = json.loads(Path(cfg_path).read_text(encoding="utf-8"))
        models = cfg["models"]
        sel_models = args.models.split(",") if args.models else None
        if sel_models:
            models = [m for m in models if m["name"] in sel_models]

    defenses = args.defenses.split(",") if args.defenses else cfg.get(
        "defenses", ["P0", "P1", "P2", "P3"])
    repeats = args.repeats if args.repeats else cfg.get("repeats", 3)
    interval = cfg.get("request_interval", 1.0)
    temperature = cfg.get("temperature", 0.2)
    max_tokens = cfg.get("max_tokens", 4096)

    # 任务网格（支持断点续跑）
    grid = [(pid, d, m["name"], rep, m)
            for pid in sel_problems for d in defenses for m in models
            for rep in range(repeats)]
    todo = [g for g in grid if args.force or
            not store.has_experiment_run(g[0], g[1], g[2], g[3])]
    print("实验网格: %d 格，待运行 %d 格（模型: %s；防护: %s；题目: %d；重复: %d）"
          % (len(grid), len(todo), ", ".join(m["name"] for m in models),
             ",".join(defenses), len(sel_problems), repeats))

    store.init_db()
    ok = fail = skip = 0
    t_start = time.time()
    for i, (pid, defense, model_name, rep, model_cfg) in enumerate(todo):
        problem = get_problem(pid)
        if not problem:
            print("[skip] 题目不存在 %s" % pid)
            continue
        mode = DEFENSE_MODES[defense](rep)
        session_id = "exp-%s-%s-%s-%d" % (pid, defense, model_name, rep)
        view = build_view(problem, session_id, mode)
        prompt = build_prompt(problem, view)

        try:
            t0 = time.time()
            if args.mock:
                response = mock_model(problem, view, defense, rep)
            else:
                response = call_model(model_cfg, prompt, temperature, max_tokens,
                                      cfg.get("retries", 2))
            elapsed = time.time() - t0

            code = extract_code(response)
            tests = view_tests(problem, session_id, mode)
            if code:
                result = judge(code, tests, problem["time_limit_ms"], "python3")
                verdict = result["verdict"]
                passed, total = result["passed"], result["total"]
                detail = result["detail"]
            else:
                verdict, passed, total, detail = "NO_CODE", 0, len(tests), []

            mislead, reason = detect_mislead(problem, view, response, code, detail)

            store.add_experiment_run({
                "problem_id": pid, "defense": defense, "submode": view["submode"],
                "model": model_name, "repeat_idx": rep, "session_id": session_id,
                "variant_key": view["variant_key"], "prompt": prompt,
                "raw_response": (response or "")[:20000], "extracted_code": code,
                "verdict": verdict, "passed": passed, "total": total,
                "mislead": mislead, "mislead_reason": reason,
                "elapsed_s": round(elapsed, 2), "detail": detail,
            })
            ok += 1
            print("[%d/%d] %s × %s(%s) × %s × r%d -> %s (%d/%d)%s%s"
                  % (i + 1, len(todo), pid, defense, view["submode"] or "-",
                     model_name, rep, verdict, passed, total,
                     " [误导]" if mislead else "",
                     " %.1fs" % elapsed if not args.mock else ""))
        except Exception as e:  # noqa: BLE001
            fail += 1
            print("[%d/%d] %s × %s × %s × r%d -> ERROR: %s"
                  % (i + 1, len(todo), pid, defense, model_name, rep, e))
            store.add_experiment_run({
                "problem_id": pid, "defense": defense, "submode": view["submode"],
                "model": model_name, "repeat_idx": rep, "session_id": session_id,
                "variant_key": view["variant_key"], "prompt": prompt,
                "raw_response": "ERROR: %s" % e, "extracted_code": None,
                "verdict": "API_ERROR", "passed": None, "total": None,
                "mislead": 0, "mislead_reason": "", "elapsed_s": None, "detail": [],
            })
        if interval and not args.mock and i < len(todo) - 1:
            time.sleep(interval)

    print("\n完成: %d 成功 / %d 失败 / %d 跳过，总耗时 %.1f 分钟"
          % (ok, fail, skip, (time.time() - t_start) / 60))
    print("下一步: python experiment/analyze.py 生成统计与图表（report/ 目录）")


def main():
    ap = argparse.ArgumentParser(description="AI 解题对照实验批量脚本")
    ap.add_argument("--config", default=None, help="experiment/ 下的配置文件名（默认 config.json）")
    ap.add_argument("--mock", action="store_true", help="本地模拟模型（无需 API Key，用于管线演示）")
    ap.add_argument("--problems", default=None, help="逗号分隔题目 ID，默认全部")
    ap.add_argument("--defenses", default=None, help="逗号分隔防护状态，如 P0,P1,P2,P3")
    ap.add_argument("--models", default=None, help="逗号分隔模型名（对应 config 中 name）")
    ap.add_argument("--repeats", type=int, default=0, help="每格重复次数（0=用配置值）")
    ap.add_argument("--force", action="store_true", help="忽略已完成记录强制重跑")
    args = ap.parse_args()
    if not args.mock and not args.config:
        args.config = "config.json"
    run(args)


if __name__ == "__main__":
    main()
