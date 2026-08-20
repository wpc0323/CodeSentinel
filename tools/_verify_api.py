# -*- coding: utf-8 -*-
"""端到端 API 验证脚本（临时）。"""
import json
import urllib.request

BASE = "http://127.0.0.1:8000"


def get(path):
    with urllib.request.urlopen(BASE + path) as r:
        return json.loads(r.read().decode("utf-8"))


def post(path, body):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode("utf-8"))


# 1. 机制一：同会话稳定 / 不同会话不同版本
v0 = get("/api/problem/P001?session=demo-1&mode=original")
v1 = get("/api/problem/P001?session=demo-1&mode=variant")
v1b = get("/api/problem/P001?session=demo-1&mode=variant")
v2 = get("/api/problem/P001?session=demo-2&mode=variant")
print("[M1] P0 ->", v0["variant_key"], "|", v0["variant_label"])
print("[M1] P1 session=demo-1 ->", v1["variant_key"], "|", v1["variant_label"])
print("[M1] P1 重复请求稳定:", v1["variant_key"] == v1b["variant_key"])
print("[M1] P1 session=demo-2 ->", v2["variant_key"], "|", v2["variant_label"])

# 2. 机制二：干扰注入 / 约束隐藏
vd = get("/api/problem/P001?session=demo-1&mode=distractor")
print("[M2a] 干扰注入: 末段 =", vd["statement"][-1][:30], "...")
vh = get("/api/problem/P002?session=demo-1&mode=hide")
print("[M2b] 约束隐藏: P002 隐藏后段落数 =", len(vh["statement"]),
      "含'大小写'句:", any("大小写" in p for p in vh["statement"]))

# 3. 判题闭环：正确解 -> AC
sol_p001 = "import sys\ndef main():\n    d = sys.stdin.buffer.read().split()\n    n = int(d[0])\n    print(sum(int(x) for x in d[1:1+n]))\nmain()\n"
r = post("/api/submit", {"problem_id": "P001", "session_id": "demo-1",
                         "mode": "original", "language": "python3", "code": sol_p001})
print("[JUDGE] 正确解 @P0 ->", r["verdict"], " %d/%d" % (r["passed"], r["total"]))

# 4. 同一正确解（算法解）在 P1 版本也应 AC（算法与数值无关）
r = post("/api/submit", {"problem_id": "P001", "session_id": "demo-1",
                         "mode": "variant", "language": "python3", "code": sol_p001})
print("[JUDGE] 正确解 @P1 ->", r["verdict"], " %d/%d (版本 %s)"
      % (r["passed"], r["total"], r["variant_key"]))

# 5. 被干扰误导的解（取模）-> WA 于 bigsum
bait_code = "import sys\ndef main():\n    d = sys.stdin.buffer.read().split()\n    n = int(d[0])\n    print(sum(int(x) for x in d[1:1+n]) % 1000000007)\nmain()\n"
r = post("/api/submit", {"problem_id": "P001", "session_id": "demo-1",
                         "mode": "distractor", "language": "python3", "code": bait_code})
print("[JUDGE] 取模解 @P2a ->", r["verdict"], " %d/%d" % (r["passed"], r["total"]))

# 6. CE：语法错误
r = post("/api/submit", {"problem_id": "P001", "session_id": "demo-1",
                         "mode": "original", "language": "python3", "code": "def (:"})
print("[JUDGE] 语法错误 ->", r["verdict"], "|", r["message"][:30])

# 7. TLE：死循环（时限 2s）
r = post("/api/submit", {"problem_id": "P001", "session_id": "demo-1",
                         "mode": "original", "language": "python3",
                         "code": "while True: pass"})
print("[JUDGE] 死循环 ->", r["verdict"], "（首个失败点: %s）" % r["detail"][0]["verdict"])

# 8. P002 lower 解在 V0（含大小写坑测试点）应 WA
lower_code = ("import sys\ndef main():\n    s = sys.stdin.buffer.read().decode().rstrip().lower()\n"
              "    def pal(i, j):\n        while i < j:\n            if s[i] != s[j]: return False\n"
              "            i += 1; j -= 1\n        return True\n"
              "    i, j, ok = 0, len(s) - 1, True\n"
              "    while i < j:\n        if s[i] != s[j]:\n            ok = pal(i+1, j) or pal(i, j-1); break\n"
              "        i += 1; j -= 1\n    print('Yes' if ok else 'No')\nmain()\n")
r = post("/api/submit", {"problem_id": "P002", "session_id": "demo-1",
                         "mode": "original", "language": "python3", "code": lower_code})
fail_names = [d["name"] for d in r["detail"] if d["verdict"] not in ("AC", "SKIPPED")]
print("[JUDGE] lower 解 @P002 ->", r["verdict"], "失败点:", fail_names)

# 9. 提交记录
subs = get("/api/submissions?problem_id=P001&session_id=demo-1&limit=10")
print("[STORE] P001 demo-1 提交记录:", len(subs["submissions"]), "条")

# 10. 实验摘要接口
s = get("/api/experiment/summary")
print("[STORE] 实验摘要 total_runs =", s["total_runs"])
print("\nALL API CHECKS DONE")
