# -*- coding: utf-8 -*-
"""题库生成器。

生成 10 道自拟题目，每题 3 个同构版本（V0 原始 + V1/V2 变体），
包含：参数化题面（含可隐藏段落）、干扰注入文本、确定性测试数据（expected 由标准解运行得出）。

运行: python tools/build_problems.py
输出: server/problems/P00X.json
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "server" / "problems"


# ---------------------------------------------------------------- helpers
def run_solver(code, stdin_text, timeout=120):
    """在子进程中运行标准解，返回 stdout（str）。"""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "solver.py"
        p.write_text(code, encoding="utf-8")
        r = subprocess.run([sys.executable, "-X", "utf8", str(p)],
                           input=stdin_text.encode("utf-8"),
                           capture_output=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError("solver failed:\n" + r.stderr.decode("utf-8", "replace")[:800])
    return r.stdout.decode("utf-8", "replace")


def para(text, hideable=False):
    return {"text": text, "hideable": hideable}


def con(text, hideable=False):
    return {"text": text, "hideable": hideable}


def variant(key, label, story, input_format, output_format, constraints, samples, tests):
    """tests: [(name, input, edge_tag_or_None)]; samples: [(input, expected_or_None)]"""
    return {"key": key, "label": label, "story": story,
            "input_format": input_format, "output_format": output_format,
            "constraints": constraints, "samples": samples, "tests": tests}


# ---------------------------------------------------------------- 数据生成器（确定性）
def gen_nums(n, mod, mul, add):
    return " ".join(str(i % mod * mul + add) for i in range(n))


def gen_no_string(n):
    return "".join(chr(97 + (i * 37 + 11) % 26) for i in range(n))


def gen_intervals(n, seed):
    lines = [str(n)]
    for i in range(n):
        s = ((i * 7 + seed) % 100000) * 91 % 999983
        d = i % 9 + 1
        lines.append("%d %d" % (s, s + d))
    return "\n".join(lines) + "\n"


def gen_letters(n, seed):
    return "".join(chr(97 + ((i * 31 + seed) % 26)) for i in range(n))


def gen_knapsack(n, W, wmod, vmul):
    lines = ["%d %d" % (n, W)]
    for i in range(n):
        w = i % wmod + 1
        v = (i * vmul) % 1000 + 1
        lines.append("%d %d" % (w, v))
    return "\n".join(lines) + "\n"


def gen_maze(R, C):
    """蛇形迷宫：每 5 行一堵墙，开口左右交替，保证连通。"""
    rows = []
    for r in range(R):
        if r % 5 == 4 and r != R - 1:
            open_c = (C - 1) if (r // 5) % 2 == 0 else 0
            row = ["#"] * C
            row[open_c] = "."
        else:
            row = ["."] * C
        rows.append(row)
    rows[0][0] = "S"
    rows[R - 1][C - 1] = "E"
    return "%d %d\n" % (R, C) + "\n".join("".join(r) for r in rows) + "\n"


def gen_heights(n, seed):
    return " ".join(str(((i * 37 + seed) % 997) * 1009 + (i % 13) + 1) for i in range(n))


def gen_piles(n, seed):
    return " ".join(str((i * seed) % 100000 + 1) for i in range(n))


# ---------------------------------------------------------------- 题目定义
def p001():
    solver = """import sys
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0])
    print(sum(int(x) for x in data[1:1+n]))
main()
"""
    v0 = variant("V0", "糖果版",
        [para("幼儿园的老师让每位小朋友把今天获得的糖果数报出来。现在老师想知道全班一共获得了多少颗糖果。"),
         para("糖果数的总和可能很大，会超出 32 位有符号整数的表示范围，请使用足够大的类型。", hideable=True)],
        "第一行一个整数 $n$，表示小朋友的人数。\n第二行 $n$ 个整数 $a_1, a_2, \\ldots, a_n$，表示每位小朋友的糖果数。",
        "一行一个整数，表示糖果总数。",
        [con("$1 \\le n \\le 100000$"), con("$0 \\le a_i \\le 1000000000$")],
        [("5\n3 1 4 1 5\n", "14"), ("3\n0 9 1\n", "10")],
        [("single", "1\n998244353\n", None),
         ("zeros", "4\n0 0 0 0\n", None),
         ("bigsum", "3\n2000000000 2000000000 2000000000\n", "bigsum"),
         ("large", "100000\n" + gen_nums(100000, 997, 1000003, 7) + "\n", None)])
    v1 = variant("V1", "货运版",
        [para("物流仓库在盘点当天的包裹。司机把每辆货车运到的包裹数记在了本子上，主管想核对包裹总数。"),
         para("包裹总数的量级很大，可能超出 32 位有符号整数的表示范围，请使用足够大的类型。", hideable=True)],
        "第一行一个整数 $n$，表示货车的数量。\n第二行 $n$ 个整数 $b_1, b_2, \\ldots, b_n$，表示每辆货车的包裹数。",
        "一行一个整数，表示包裹总数。",
        [con("$1 \\le n \\le 100000$"), con("$0 \\le b_i \\le 1000000000$")],
        [("6\n12 7 25 3 18 9\n", "74"), ("2\n500 500\n", "1000")],
        [("single", "1\n1234567890\n", None),
         ("zeros", "3\n0 0 0\n", None),
         ("bigsum", "4\n1500000000 1500000000 1500000000 1500000000\n", "bigsum"),
         ("large", "100000\n" + gen_nums(100000, 811, 999983, 3) + "\n", None)])
    v2 = variant("V2", "图书版",
        [para("图书馆志愿者在整理一批旧书，需要统计所有书的页数之和来完成报废报告。"),
         para("总页数可能很大，会超出 32 位有符号整数的表示范围，请使用足够大的类型。", hideable=True)],
        "第一行一个整数 $n$，表示图书的数量。\n第二行 $n$ 个整数 $p_1, p_2, \\ldots, p_n$，表示每本书的页数。",
        "一行一个整数，表示总页数。",
        [con("$1 \\le n \\le 100000$"), con("$0 \\le p_i \\le 1000000000$")],
        [("8\n120 87 203 45 156 98 250 61\n", "1020"), ("1\n0\n", "0")],
        [("single", "1\n1000000000\n", None),
         ("zeros", "5\n0 0 0 0 0\n", None),
         ("bigsum", "3\n3000000000 1000000000 2000000000\n", "bigsum"),
         ("large", "100000\n" + gen_nums(100000, 733, 1000003, 11) + "\n", None)])
    return dict(id="P001", title="糖果清点", difficulty="easy", tags=["模拟", "入门"],
                time_limit_ms=2000, memory_limit_mb=256, solver=solver,
                variants=[v0, v1, v2],
                distractor=dict(paragraph="系统升级说明：旧版评测系统要求将答案对 $10^9+7$ 取模后输出；本系统已升级为直接输出真实总和，请勿取模。",
                                baits=["1000000007", "10^9+7", "1e9+7", "1e9 + 7"]),
                hide=dict(note="隐藏「总和可能超出 32 位整数范围」提示", edge_tests=["bigsum"]))


def p002():
    solver = """import sys
def main():
    s = sys.stdin.buffer.read().decode().rstrip("\\r\\n")
    def pal(i, j):
        while i < j:
            if s[i] != s[j]:
                return False
            i += 1; j -= 1
        return True
    i, j = 0, len(s) - 1
    ok = True
    while i < j:
        if s[i] != s[j]:
            ok = pal(i + 1, j) or pal(i, j - 1)
            break
        i += 1; j -= 1
    print("Yes" if ok else "No")
main()
"""
    v0 = variant("V0", "回声版",
        [para("小 P 定义了一种“回声串”：如果一个字符串在**至多删除一个字符**后可以变成回文串，它就是回声串。"),
         para("空串和单个字符都视为回文串。"),
         para("比较时区分大小写，'a' 与 'A' 视为不同的字符。", hideable=True)],
        "一行一个字符串 $s$（可能是空串），仅由大小写英文字母构成。",
        "如果 $s$ 是回声串输出 `Yes`，否则输出 `No`。",
        [con("$0 \\le |s| \\le 100000$"), con("$s$ 仅由大小写英文字母构成")],
        [("abca\n", "Yes"), ("abc\n", "No")],
        [("empty", "\n", "empty"),
         ("single", "x\n", None),
         ("case-mix", "aAb\n", "case"),
         ("already", "abcba\n", None),
         ("long-yes", "a" * 49999 + "b" + "a" * 49999 + "\n", None),
         ("long-no", gen_no_string(100000) + "\n", None)])
    v1 = variant("V1", "标签版",
        [para("工厂给每件产品贴一个质检标签串。标签质检规则：若字符串**至多删除一个字符**后能变成回文串，则标签合格。"),
         para("空标签和单字符标签视为回文串。"),
         para("比较时区分大小写，大写字母与小写字母视为不同字符。", hideable=True)],
        "一行一个字符串 $s$（可能是空串），仅由大小写英文字母构成。",
        "标签合格输出 `Yes`，否则输出 `No`。",
        [con("$0 \\le |s| \\le 100000$"), con("$s$ 仅由大小写英文字母构成")],
        [("Aba\n", "No"), ("Levels\n", "No")],
        [("empty", "\n", "empty"),
         ("single", "Q\n", None),
         ("case-mix", "abA\n", "case"),
         ("mixed", "abaABA\n", None),
         ("long-yes", "b" * 49999 + "c" + "b" * 49999 + "\n", None),
         ("long-no", gen_no_string(99991) + "\n", None)])
    v2 = variant("V2", "密码版",
        [para("密码锁的校验串需要满足“回声”规则：把字符串**至多删除一个字符**后是回文串才能开锁。"),
         para("空串和单个字符都视为回文串。"),
         para("比较区分大小写，同一字母的大小写视为不同字符。", hideable=True)],
        "一行一个字符串 $s$（可能是空串），仅由大小写英文字母构成。",
        "能开锁输出 `Yes`，否则输出 `No`。",
        [con("$0 \\le |s| \\le 100000$"), con("$s$ 仅由大小写英文字母构成")],
        [("Abba\n", "No"), ("cbbc\n", "Yes")],
        [("empty", "\n", "empty"),
         ("single", "m\n", None),
         ("case-mix", "aBA\n", "case"),
         ("already", "xyzzyx\n", None),
         ("long-yes", "c" * 49999 + "d" + "c" * 49999 + "\n", None),
         ("long-no", gen_no_string(99973) + "\n", None)])
    return dict(id="P002", title="回声串", difficulty="easy", tags=["字符串", "双指针"],
                time_limit_ms=3000, memory_limit_mb=256, solver=solver,
                variants=[v0, v1, v2],
                distractor=dict(paragraph="往届选手经验：先把所有字母统一转成小写再判断，可以规避一类边界错误。",
                                baits=["lower", "小写"]),
                hide=dict(note="隐藏「区分大小写」说明", edge_tests=["case", "empty"]))


def p003():
    solver = """import sys
from datetime import date, timedelta
def main():
    y, m, d, k = map(int, sys.stdin.buffer.read().split())
    r = date(y, m, d) + timedelta(days=k)
    print("%04d-%02d-%02d" % (r.year, r.month, r.day))
main()
"""
    v0 = variant("V0", "值日版",
        [para("班级的值日表按日期连续轮换。给定起始日期和间隔天数，请你算出实际的值日日期。"),
         para("起始日期可能位于任意年份，结果可能跨年进入之后的年份；闰年按公历规则判断（能被 4 整除且不被 100 整除，或能被 400 整除）。", hideable=True)],
        "一行四个整数 $Y, M, D, k$，表示起始日期为 $Y$ 年 $M$ 月 $D$ 日，间隔 $k$ 天。",
        "一行，格式 `YYYY-MM-DD`（月和日不足两位补零），表示 $k$ 天后的日期。",
        [con("$2000 \\le Y \\le 2099$"), con("输入日期一定是合法日期"), con("$0 \\le k \\le 3650$")],
        [("2026 8 19 0\n", "2026-08-19"), ("2026 12 17 20\n", "2027-01-06")],
        [("feb", "2026 2 27 3\n", "leap"),
         ("leap29", "2028 2 28 1\n", "leap"),
         ("monthend", "2026 1 31 1\n", None),
         ("bigk", "2000 3 1 365\n", "bigk"),
         ("newyear", "2099 12 25 7\n", "newyear")])
    v1 = variant("V1", "快递版",
        [para("快递平台的订单在签收后再经过 $k$ 天会自动确认收货。给定签收日期和天数，请算出自动确认日期。"),
         para("签收日期可能位于任意年份，确认日期可能跨年进入之后的年份；闰年按公历规则判断。", hideable=True)],
        "一行四个整数 $Y, M, D, k$，表示签收日期为 $Y$ 年 $M$ 月 $D$ 日，再过 $k$ 天自动确认。",
        "一行，格式 `YYYY-MM-DD`（月和日不足两位补零），表示自动确认日期。",
        [con("$2000 \\le Y \\le 2099$"), con("输入日期一定是合法日期"), con("$0 \\le k \\le 3650$")],
        [("2026 3 28 5\n", "2026-04-02"), ("2026 1 30 3\n", "2026-02-02")],
        [("feb", "2027 2 26 4\n", "leap"),
         ("leap29", "2024 2 28 2\n", "leap"),
         ("monthend", "2026 4 30 2\n", None),
         ("bigk", "2020 2 29 365\n", "bigk"),
         ("newyear", "2026 12 31 1\n", "newyear")])
    v2 = variant("V2", "农事版",
        [para("农技站记录了种子的播种日期，某类作物从播种到收获恰好需要 $k$ 天。请根据播种日期推算收获日期。"),
         para("播种日期可能位于任意年份，收获日期可能跨年进入之后的年份；闰年按公历规则判断。", hideable=True)],
        "一行四个整数 $Y, M, D, k$，表示播种日期为 $Y$ 年 $M$ 月 $D$ 日，生长 $k$ 天后收获。",
        "一行，格式 `YYYY-MM-DD`（月和日不足两位补零），表示收获日期。",
        [con("$2000 \\le Y \\le 2099$"), con("输入日期一定是合法日期"), con("$0 \\le k \\le 3650$")],
        [("2024 11 20 100\n", "2025-02-28"), ("2026 6 15 0\n", "2026-06-15")],
        [("feb", "2100 2 27 2\n", "leap"),
         ("leap29", "2024 2 28 1\n", "leap"),
         ("monthend", "2026 12 30 3\n", None),
         ("bigk", "2024 1 1 366\n", "bigk"),
         ("newyear", "2049 12 20 12\n", "newyear")])
    return dict(id="P003", title="日期推算", difficulty="easy", tags=["模拟", "日期"],
                time_limit_ms=2000, memory_limit_mb=256, solver=solver,
                variants=[v0, v1, v2],
                distractor=dict(paragraph="补充信息：2026 年 1 月 1 日是星期四；值日与发货在周末与法定节假日照常轮换。",
                                baits=["星期", "周末", "节假日"]),
                hide=dict(note="隐藏「结果可能跨年/闰年」提示", edge_tests=["leap", "bigk", "newyear"]))


def p004():
    solver = """import sys
def main():
    s = sys.stdin.buffer.read().decode().rstrip("\\r\\n")
    pair = {")": "(", "]": "["}
    st = []
    for ch in s:
        if ch in "([":
            st.append(ch)
        else:
            if not st or st[-1] != pair[ch]:
                print("No"); return
            st.pop()
    print("Yes" if not st else "No")
main()
"""
    v0 = variant("V0", "画框版",
        [para("画家用圆括号 `(` `)` 和方括号 `[` `]` 组成的序列装饰画框。一幅“合法”的装饰满足：每个左括号都有类型匹配的右括号，并按正确的嵌套顺序闭合。"),
         para("空串（长度为 0）也是合法装饰。", hideable=True)],
        "一行一个字符串 $s$（可能是空串），仅由 `( ) [ ]` 四种字符构成。",
        "合法输出 `Yes`，否则输出 `No`。",
        [con("$0 \\le |s| \\le 100000$")],
        [("([()])\n", "Yes"), ("([)]\n", "No")],
        [("empty", "\n", "empty"),
         ("pair", "()\n", None),
         ("wrongtype", "(]\n", None),
         ("unbalance", "((((()\n", None),
         ("deep", "(" * 50000 + ")" * 50000 + "\n", None),
         ("mix", "([])" * 25000 + "\n", None)])
    v1 = variant("V1", "积木版",
        [para("积木套装用括号序列表示嵌套结构：`(` 与 `)` 包裹一层圆槽，`[` 与 `]` 包裹一层方槽。一个“稳定”的结构中每种左槽都应由同类型的右槽按嵌套顺序闭合。"),
         para("空序列（一个槽都不放）也是稳定结构。", hideable=True)],
        "一行一个字符串 $s$（可能是空串），仅由 `( ) [ ]` 四种字符构成。",
        "稳定输出 `Yes`，否则输出 `No`。",
        [con("$0 \\le |s| \\le 100000$")],
        [("[()]\n", "Yes"), ("())\n", "No")],
        [("empty", "\n", "empty"),
         ("pair", "[]\n", None),
         ("wrongtype", "[)\n", None),
         ("unbalance", "]]]]\n", None),
         ("deep", "[" * 50000 + "]" * 50000 + "\n", None),
         ("mix", "([])" * 25000 + "\n", None)])
    v2 = variant("V2", "密码锁版",
        [para("密码锁的齿纹用两层符号记录：圆括号与方括号。开锁程序校验齿纹：所有左符号必须由**同类型**的右符号按嵌套顺序闭合。"),
         para("空齿纹（长度为 0）可以通过校验。", hideable=True)],
        "一行一个字符串 $s$（可能是空串），仅由 `( ) [ ]` 四种字符构成。",
        "校验通过输出 `Yes`，否则输出 `No`。",
        [con("$0 \\le |s| \\le 100000$")],
        [("(())[]\n", "Yes"), ("(()\n", "No")],
        [("empty", "\n", "empty"),
         ("pair", "()\n", None),
         ("wrongtype", "[)]\n", None),
         ("unbalance", "(((]\n", None),
         ("deep", "([" * 25000 + "])" * 25000 + "\n", None),
         ("mix", "()[]" * 25000 + "\n", None)])
    return dict(id="P004", title="括号校验", difficulty="medium", tags=["栈", "数据结构"],
                time_limit_ms=3000, memory_limit_mb=256, solver=solver,
                variants=[v0, v1, v2],
                distractor=dict(paragraph="往届数据规律：合法序列的长度总是偶数，且在官方样例中长度还是 3 的倍数。",
                                baits=["3 的倍数", "3的倍数"]),
                hide=dict(note="隐藏「空串合法」说明", edge_tests=["empty"]))


def p005():
    solver = """import sys
from collections import Counter
def main():
    s = sys.stdin.buffer.read().decode().rstrip("\\r\\n")
    c = Counter(s)
    best = max(c.items(), key=lambda kv: (kv[1], -ord(kv[0])))
    print(best[0])
main()
"""
    v0 = variant("V0", "弹幕版",
        [para("弹幕运营同学想快速知道一段文本中出现次数最多的字符，用于生成热搜词条。"),
         para("若多个字符出现次数并列最多，输出其中字典序最小的一个。", hideable=True)],
        "一行一个字符串 $s$。",
        "一行一个字符，表示出现次数最多的字符。",
        [con("$1 \\le |s| \\le 100000$"), con("$s$ 仅由小写英文字母构成")],
        [("abbccc\n", "c"), ("baab\n", "a")],
        [("tie2", "cbccbb\n", "tie"),
         ("single", "z\n", None),
         ("all-same", "aaaa\n", None),
         ("tie-multi", "dcba\n", "tie"),
         ("large", gen_letters(100000, 7) + "\n", None)])
    v1 = variant("V1", "投票版",
        [para("观众通过短信为选项字母投票（一条短信视为一票）。统计得票最多的选项字母。"),
         para("若多个选项得票并列最多，输出其中字典序最小的字母。", hideable=True)],
        "一行一个字符串 $s$，按时间顺序记录所有选票。",
        "一行一个字符，表示得票最多的选项。",
        [con("$1 \\le |s| \\le 100000$"), con("$s$ 仅由小写英文字母构成")],
        [("cabab\n", "a"), ("zzayz\n", "z")],
        [("tie2", "aabbcc\n", "tie"),
         ("single", "q\n", None),
         ("all-same", "mmmmm\n", None),
         ("tie-multi", "wonw\n", "tie"),
         ("large", gen_letters(100000, 19) + "\n", None)])
    v2 = variant("V2", "热力版",
        [para("键盘热力统计程序需要找出一段日志中被敲击次数最多的按键（日志按字符逐个记录）。"),
         para("若多个按键次数并列最多，输出其中字典序最小的按键。", hideable=True)],
        "一行一个字符串 $s$，表示按键日志。",
        "一行一个字符，表示敲击次数最多的按键。",
        [con("$1 \\le |s| \\le 100000$"), con("$s$ 仅由小写英文字母构成")],
        [("poiuytrewq\n", "e"), ("ooxx\n", "o")],
        [("tie2", "uuzz\n", "tie"),
         ("single", "k\n", None),
         ("all-same", "hhhh\n", None),
         ("tie-multi", "ggddbb\n", "tie"),
         ("large", gen_letters(100000, 41) + "\n", None)])
    return dict(id="P005", title="频率冠军", difficulty="easy", tags=["哈希", "计数"],
                time_limit_ms=2000, memory_limit_mb=256, solver=solver,
                variants=[v0, v1, v2],
                distractor=dict(paragraph="数据说明：保证出现次数最多的字符出现次数不少于 5 次；文本中可能混入少量空格与标点。",
                                baits=["5 次", "5次", "空格"]),
                hide=dict(note="隐藏「并列时输出字典序最小」规则", edge_tests=["tie"]))


def p006():
    solver = """import sys
def main():
    data = sys.stdin.buffer.read().split()
    n, W = int(data[0]), int(data[1])
    dp = [0] * (W + 1)
    idx = 2
    for _ in range(n):
        w = int(data[idx]); v = int(data[idx + 1]); idx += 2
        for c in range(W, w - 1, -1):
            if dp[c - w] + v > dp[c]:
                dp[c] = dp[c - w] + v
    print(dp[W])
main()
"""
    v0 = variant("V0", "采蘑菇版",
        [para("小明去山里采蘑菇，背包容量为 $W$。山里有 $n$ 种蘑菇，第 $i$ 种采摘一份的重量为 $w_i$、晒干后的价值为 $v_i$。"),
         para("每种蘑菇至多采摘一份，即使容量有富余也不能重复采摘同一种。", hideable=True),
         para("求在总重量不超过 $W$ 的前提下，能获得的最大总价值。")],
        "第一行两个整数 $n, W$。\n接下来 $n$ 行，每行两个整数 $w_i, v_i$。",
        "一行一个整数，表示最大总价值。",
        [con("$1 \\le n \\le 500$"), con("$1 \\le W \\le 100000$"), con("$1 \\le w_i \\le W$"), con("$0 \\le v_i \\le 10000$")],
        [("4 5\n2 3\n3 4\n4 5\n5 6\n", "7")],
        [("single-item", "1 9\n3 5\n", "single"),
         ("zero-cap", "3 0\n1 1\n2 2\n3 3\n", None),
         ("zero-value", "2 3\n1 0\n2 5\n", None),
         ("large", gen_knapsack(200, 10000, 19, 7919), None)])
    v1 = variant("V1", "装备版",
        [para("游戏角色出发前整理背包，背包容量为 $W$ 格。仓库里有 $n$ 件装备，第 $i$ 件占用 $w_i$ 格、能提供 $v_i$ 点战力。"),
         para("每件装备是唯一的，至多放入一件，不能重复放入。", hideable=True),
         para("求总占用不超过 $W$ 格时的最大总战力。")],
        "第一行两个整数 $n, W$。\n接下来 $n$ 行，每行两个整数 $w_i, v_i$。",
        "一行一个整数，表示最大总战力。",
        [con("$1 \\le n \\le 500$"), con("$1 \\le W \\le 100000$"), con("$1 \\le w_i \\le W$"), con("$0 \\le v_i \\le 10000$")],
        [("3 4\n1 2\n2 3\n4 8\n", "8")],
        [("single-item", "1 10\n2 7\n", "single"),
         ("zero-cap", "2 0\n5 5\n6 6\n", None),
         ("zero-value", "3 6\n2 0\n3 9\n4 1\n", None),
         ("large", gen_knapsack(200, 8000, 17, 104729), None)])
    v2 = variant("V2", "纪念币版",
        [para("纪念币展柜剩余展示空间可承重 $W$ 克。现有 $n$ 枚候选纪念币，第 $i$ 枚重 $w_i$ 克、市场估值 $v_i$ 元。"),
         para("每枚纪念币都是孤品，至多选入一枚，不可重复选择。", hideable=True),
         para("求总重不超过 $W$ 克时的最大总估值。")],
        "第一行两个整数 $n, W$。\n接下来 $n$ 行，每行两个整数 $w_i, v_i$。",
        "一行一个整数，表示最大总估值。",
        [con("$1 \\le n \\le 500$"), con("$1 \\le W \\le 100000$"), con("$1 \\le w_i \\le W$"), con("$0 \\le v_i \\le 10000$")],
        [("5 8\n3 4\n5 6\n2 2\n4 5\n1 1\n", "10")],
        [("single-item", "1 8\n4 6\n", "single"),
         ("zero-cap", "1 0\n3 3\n", None),
         ("zero-value", "2 4\n2 0\n3 7\n", None),
         ("large", gen_knapsack(200, 12000, 23, 65537), None)])
    return dict(id="P006", title="背包采集", difficulty="medium", tags=["动态规划", "背包"],
                time_limit_ms=5000, memory_limit_mb=256, solver=solver,
                variants=[v0, v1, v2],
                distractor=dict(paragraph="山区图鉴备注：当地共记录过 1024 种蘑菇（装备/纪念币同理），本题输入数据为其某个子集。",
                                baits=["1024"]),
                hide=dict(note="隐藏「每种至多一份」约束", edge_tests=["single"]))


def p007():
    solver = """import sys
from collections import deque
def main():
    lines = sys.stdin.buffer.read().decode().rstrip("\\n").split("\\n")
    R, C = map(int, lines[0].split())
    grid = lines[1:1 + R]
    start = end = None
    for r in range(R):
        row = grid[r]
        for c in range(C):
            if row[c] == "S":
                start = (r, c)
            elif row[c] == "E":
                end = (r, c)
    if start is None or end is None:
        print(-1); return
    dist = {start: 0}
    q = deque([start])
    while q:
        cur = q.popleft()
        if cur == end:
            print(dist[cur]); return
        r, c = cur
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < R and 0 <= nc < C and (nr, nc) not in dist and grid[nr][nc] != "#":
                dist[(nr, nc)] = dist[cur] + 1
                q.append((nr, nc))
    print(-1)
main()
"""
    maze1 = "3 4\nS..#\n.#..\n...E\n"
    maze2 = "4 4\nS.#.\n.#..\n.#.#\n...E\n"
    maze3 = "3 3\nS##\n##.\n..E\n"
    maze4 = "1 2\nSE\n"
    v0 = variant("V0", "救援版",
        [para("救援无人机需要在网格迷宫中从起点 `S` 飞到出口 `E`。`#` 表示无法穿越的墙体，`.` 表示可通行格子；每一步可以移动到上下左右相邻的格子。"),
         para("如果从起点无法到达出口，请输出 -1。", hideable=True),
         para("求最少需要的移动步数。")],
        "第一行两个整数 $R, C$。\n接下来 $R$ 行，每行 $C$ 个字符，描述迷宫。",
        "一行一个整数，表示最少移动步数；无法到达输出 `-1`。",
        [con("$1 \\le R, C \\le 1000$"), con("网格中恰好有一个 `S` 和一个 `E`")],
        [(maze1, "5")],
        [("nosolution", maze3, "nosolution"),
         ("adjacent", maze4, None),
         ("open", "100 100\n" + ("S" + "." * 99 + "\n") + ("." * 100 + "\n") * 98 + ("." * 99 + "E\n"), None),
         ("big", gen_maze(800, 800), "big")])
    v1 = variant("V1", "巡线版",
        [para("巡检机器人要从网格地图的起点 `S` 走到终点 `E` 完成巡线。`#` 表示障碍物，`.` 表示可通行；每步可向上下左右移动一格，不能斜走。"),
         para("若无法到达终点，请输出 -1。", hideable=True),
         para("求最少步数。")],
        "第一行两个整数 $R, C$。\n接下来 $R$ 行，每行 $C$ 个字符，描述地图。",
        "一行一个整数，表示最少步数；无法到达输出 `-1`。",
        [con("$1 \\le R, C \\le 1000$"), con("地图中恰好有一个 `S` 和一个 `E`")],
        [(maze2, "6")],
        [("nosolution", "3 3\nS##\n.##\n..E\n", "nosolution"),
         ("adjacent", "2 2\nS.\n.E\n", None),
         ("open", "50 50\n" + "S" + "." * 49 + "\n" + ("." * 50 + "\n") * 48 + ("." * 49 + "E\n"), None),
         ("big", gen_maze(600, 900), "big")])
    v2 = variant("V2", "扫地版",
        [para("扫地机器人规划路线：从充电桩 `S` 出发前往回充座 `E`。`#` 表示家具阻挡，`.` 表示空地；机器人每步移动到上下左右相邻格子。"),
         para("若无法到达回充座，请输出 -1。", hideable=True),
         para("求最少移动步数。")],
        "第一行两个整数 $R, C$。\n接下来 $R$ 行，每行 $C$ 个字符，描述房间布局。",
        "一行一个整数，表示最少步数；无法到达输出 `-1`。",
        [con("$1 \\le R, C \\le 1000$"), con("布局中恰好有一个 `S` 和一个 `E`")],
        [("5 5\nS....\n#....\n.....\n....#\n....E\n", "8")],
        [("nosolution", "2 3\nS##\n##E\n", "nosolution"),
         ("adjacent", "1 3\nS.E\n", None),
         ("open", "40 60\n" + "S" + "." * 59 + "\n" + ("." * 60 + "\n") * 38 + ("." * 59 + "E\n"), None),
         ("big", gen_maze(700, 700), "big")])
    return dict(id="P007", title="迷宫寻路", difficulty="medium", tags=["搜索", "BFS", "图论"],
                time_limit_ms=8000, memory_limit_mb=256, solver=solver,
                variants=[v0, v1, v2],
                distractor=dict(paragraph="设备规格：电池续航 5 天，每天最多飞行/行驶 $10^9$ 步；每移动一格耗时 1 秒（以上参数不影响步数统计）。",
                                baits=["5 天", "5天", "续航"]),
                hide=dict(note="隐藏「无解输出 -1」", edge_tests=["nosolution"]))


def p008():
    solver = """import sys, heapq
def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0])
    a = [int(x) for x in data[1:1 + n]]
    heapq.heapify(a)
    total = 0
    while len(a) > 1:
        x = heapq.heappop(a)
        y = heapq.heappop(a)
        s = x + y
        total += s
        heapq.heappush(a, s)
    print(total)
main()
"""
    v0 = variant("V0", "石子版",
        [para("操场上有 $n$ 堆石子，第 $i$ 堆有 $a_i$ 枚。每次可以把任意两堆合并成一堆，代价为两堆石子数之和。"),
         para("每次合并的两堆不要求位置相邻，可以从所有堆中任选两堆。", hideable=True),
         para("把所有石子合并成一堆，求最小总代价。")],
        "第一行一个整数 $n$。\n第二行 $n$ 个整数 $a_1, a_2, \\ldots, a_n$。",
        "一行一个整数，表示最小总代价。",
        [con("$1 \\le n \\le 100000$"), con("$1 \\le a_i \\le 100000$")],
        [("4\n1 2 3 4\n", "19")],
        [("adjacent-trap", "4\n1 3 2 4\n", "adjacent"),
         ("one", "1\n7\n", None),
         ("two", "2\n10 20\n", None),
         ("large", "100000\n" + gen_piles(100000, 2654435761) + "\n", None)])
    v1 = variant("V1", "备份版",
        [para("数据迁移时需要把 $n$ 个数据段逐步合并为一个大段。每次可以把任意两个数据段合并，代价为两段的数据量之和（迁移流量）。"),
         para("每次合并的两个数据段不要求相邻，可以从所有段中任选两段。", hideable=True),
         para("求把所有段合并为一段的最小总代价。")],
        "第一行一个整数 $n$。\n第二行 $n$ 个整数，表示各数据段的数据量。",
        "一行一个整数，表示最小总代价。",
        [con("$1 \\le n \\le 100000$"), con("$1 \\le a_i \\le 100000$")],
        [("5\n1 2 3 4 5\n", "33")],
        [("adjacent-trap", "4\n4 1 3 2\n", "adjacent"),
         ("one", "1\n100000\n", None),
         ("two", "2\n3 4\n", None),
         ("large", "100000\n" + gen_piles(100000, 40503) + "\n", None)])
    v2 = variant("V2", "柴火版",
        [para("篝火晚会前需要把 $n$ 捆柴火逐步捆成一大捆。每次可以把任意两捆合捆，体力代价为两捆的根数之和。"),
         para("每次合捆的两捆不要求相邻，可以从所有捆中任选两捆。", hideable=True),
         para("求把所有柴火捆成一捆的最小总代价。")],
        "第一行一个整数 $n$。\n第二行 $n$ 个整数，表示各捆柴火的根数。",
        "一行一个整数，表示最小总代价。",
        [con("$1 \\le n \\le 100000$"), con("$1 \\le a_i \\le 100000$")],
        [("3\n1 2 3\n", "9")],
        [("adjacent-trap", "5\n2 1 4 1 3\n", "adjacent"),
         ("one", "1\n1\n", None),
         ("two", "2\n99999 1\n", None),
         ("large", "100000\n" + gen_piles(100000, 99991) + "\n", None)])
    return dict(id="P008", title="最小合并代价", difficulty="medium", tags=["贪心", "堆"],
                time_limit_ms=3000, memory_limit_mb=256, solver=solver,
                variants=[v0, v1, v2],
                distractor=dict(paragraph="场地记录：最大的一堆石子（数据段/柴火捆）的编号为 $k$，本题输入中未给出 $k$。",
                                baits=["编号"]),
                hide=dict(note="隐藏「任意两堆可合并」", edge_tests=["adjacent"]))


# ---------------------------------------------------------------- 构建与输出
def build_problem(spec):
    """为每个版本求解样例与测试数据的期望输出，并断言手写样例一致。"""
    for v in spec["variants"]:
        solved_samples = []
        for idx, (inp, exp) in enumerate(v["samples"]):
            got = run_solver(spec["solver"], inp).strip()
            if exp is not None:
                assert got == exp.strip(), "%s %s sample%d: got %r, want %r" % (
                    spec["id"], v["key"], idx, got, exp)
            solved_samples.append({"input": inp, "output": got})
        v["samples"] = solved_samples

        solved_tests = []
        for name, inp, edge in v["tests"]:
            got = run_solver(spec["solver"], inp).strip()
            solved_tests.append({"name": name, "input": inp, "output": got, "edge": edge})
        v["tests"] = solved_tests

    # 收集 hide 依赖的边界测试名（所有版本并集）
    edge_union = set(spec["hide"]["edge_tests"])
    for v in spec["variants"]:
        for t in v["tests"]:
            if t["edge"]:
                edge_union.add(t["edge"])
    spec["hide"]["edge_tests"] = sorted(edge_union)
    spec["solution"] = spec.pop("solver")
    return spec


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    builders = [p001, p002, p003, p004, p005, p006, p007, p008]
    for b in builders:
        spec = build_problem(b())
        out = OUT_DIR / (spec["id"] + ".json")
        out.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
        n_tests = sum(len(v["tests"]) for v in spec["variants"])
        print("[ok] %s %s: %d variants, %d tests" % (spec["id"], spec["title"], len(spec["variants"]), n_tests))
    print("done -> %s" % OUT_DIR)


if __name__ == "__main__":
    main()
