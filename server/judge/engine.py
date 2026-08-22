# -*- coding: utf-8 -*-
"""判题引擎：受限子进程执行 + 输出比对（演示级，满足立项书 N2 降级约定）。

- Python3：语法检查(compile) -> CE；逐测试点子进程运行（超时控制）；
- C++：若本机存在 g++ 则编译运行，否则返回不可用提示（降级）；
- 输出比对：忽略每行行尾空白与文末空行。
"""
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

MAX_CODE_SIZE = 64 * 1024          # 64KB
MAX_OUTPUT_SIZE = 10 * 1024 * 1024  # 10MB
STARTUP_ALLOWANCE = 1.0            # 解释器启动额外余量（秒）


def normalize(text):
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines).strip()


def _run_py_file(file_path, stdin_text, time_limit_ms):
    """运行单个测试点，返回 (verdict, time_ms, stdout, stderr_head)。"""
    timeout = time_limit_ms / 1000.0 + STARTUP_ALLOWANCE
    t0 = time.time()
    try:
        r = subprocess.run(
            [sys.executable, "-X", "utf8", str(file_path)],
            input=stdin_text.encode("utf-8"),
            capture_output=True,
            timeout=timeout,
            cwd=str(file_path.parent),
        )
    except subprocess.TimeoutExpired:
        return "TLE", int((time.time() - t0) * 1000), "", ""
    elapsed = int((time.time() - t0) * 1000)
    out = r.stdout.decode("utf-8", "replace")
    err = r.stderr.decode("utf-8", "replace")
    if r.returncode != 0:
        return "RE", elapsed, out, err[-500:]
    if len(out) > MAX_OUTPUT_SIZE:
        return "MLE", elapsed, "", ""
    return "OK", elapsed, out, err


def judge_python(code, tests, time_limit_ms):
    """判 Python3 提交。tests: [{name, input, output, edge}]"""
    if not code or not code.strip():
        return _result("CE", [], "空代码")
    if len(code.encode("utf-8")) > MAX_CODE_SIZE:
        return _result("CE", [], "代码过长（超过 64KB）")
    try:
        compile(code, "submission.py", "exec")
    except SyntaxError as e:
        return _result("CE", [], "语法错误: %s" % e)

    detail = []
    overall = "AC"
    with tempfile.TemporaryDirectory(prefix="oj_judge_") as td:
        f = Path(td) / "submission.py"
        f.write_text(code, encoding="utf-8")
        for t in tests:
            verdict, ms, out, err = _run_py_file(f, t["input"], time_limit_ms)
            if verdict == "OK":
                if normalize(out) == normalize(t["output"]):
                    verdict = "AC"
                else:
                    verdict = "WA"
            if verdict != "AC" and overall == "AC":
                overall = verdict
                if verdict in ("TLE",):
                    detail.append(_case(t, verdict, ms, ""))
                    # TLE 之后继续跑剩余点意义不大，提前结束
                    for rest in tests[len(detail):]:
                        detail.append(_case(rest, "SKIPPED", 0, ""))
                    break
            detail.append(_case(t, verdict, ms, err if verdict != "AC" else ""))
    passed = sum(1 for d in detail if d["verdict"] == "AC")
    return _result(overall, detail, "", passed)


def judge_cpp(code, tests, time_limit_ms):
    gpp = shutil.which("g++") or shutil.which("clang++") or shutil.which("g++.exe")
    if not gpp:
        return _result("CE", [], "本机未检测到 g++ 编译器，演示环境请使用 Python3 提交")
    with tempfile.TemporaryDirectory(prefix="oj_judge_") as td:
        src = Path(td) / "main.cpp"
        src.write_text(code, encoding="utf-8")
        exe = Path(td) / ("main.exe" if sys.platform == "win32" else "main")
        try:
            r = subprocess.run([gpp, "-O2", "-std=c++14", "-o", str(exe), str(src)],
                               capture_output=True, timeout=30)
        except subprocess.TimeoutExpired:
            return _result("CE", [], "编译超时")
        if r.returncode != 0:
            return _result("CE", [], "编译错误: " + r.stderr.decode("utf-8", "replace")[-500:])

        detail, overall = [], "AC"
        for t in tests:
            verdict, ms, out, err = _run_exe(exe, t["input"], time_limit_ms)
            if verdict == "OK":
                verdict = "AC" if normalize(out) == normalize(t["output"]) else "WA"
            if verdict != "AC" and overall == "AC":
                overall = verdict
            detail.append(_case(t, verdict, ms, err if verdict != "AC" else ""))
    passed = sum(1 for d in detail if d["verdict"] == "AC")
    return _result(overall, detail, "", passed)


def _run_exe(exe, stdin_text, time_limit_ms):
    timeout = time_limit_ms / 1000.0 + STARTUP_ALLOWANCE
    t0 = time.time()
    try:
        r = subprocess.run([str(exe)], input=stdin_text.encode("utf-8"),
                           capture_output=True, timeout=timeout, cwd=str(exe.parent))
    except subprocess.TimeoutExpired:
        return "TLE", int((time.time() - t0) * 1000), "", ""
    elapsed = int((time.time() - t0) * 1000)
    out = r.stdout.decode("utf-8", "replace")
    err = r.stderr.decode("utf-8", "replace")
    if r.returncode != 0:
        return "RE", elapsed, out, err[-500:]
    return "OK", elapsed, out, err


def _case(t, verdict, ms, stderr):
    return {"name": t["name"], "verdict": verdict, "time_ms": ms, "stderr": stderr}


def _result(verdict, detail, message="", passed=None):
    if passed is None:
        passed = sum(1 for d in detail if d["verdict"] == "AC")
    return {"verdict": verdict, "passed": passed, "total": len(detail),
            "detail": detail, "message": message}


def judge(code, tests, time_limit_ms, language="python3"):
    """判题入口。language: python3 | cpp

    tests 可为：纯测试点列表（节点），或 view_tests 返回的图结构
    {"tests": [...], "graph": {...}}；此处统一取出节点列表，对图关系透明。
    """
    if isinstance(tests, dict) and "tests" in tests:
        tests = tests["tests"]
    lang = (language or "python3").lower()
    if lang in ("python3", "python", "py"):
        return judge_python(code, tests, time_limit_ms)
    if lang in ("cpp", "c++", "cxx"):
        return judge_cpp(code, tests, time_limit_ms)
    return _result("CE", [], "不支持的语言: %s" % language)
