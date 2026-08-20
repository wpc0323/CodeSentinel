# -*- coding: utf-8 -*-
"""防护机制二：隐藏干扰信息（Information Perturbation）。

- 子模式 distractor（2a 干扰注入）：把与解法无关但看似相关的段落混入题干；
- 子模式 hide（2b 关键约束隐藏）：跳过题干/数据范围中标记为 hideable 的关键句。

两种子模式只作用于“题目展示层”，不改变判题逻辑与测试数据。
"""
from server.defense.variant import choose_variant

# 展示模式 -> (是否强制原始版本, 扰动子模式)
MODES = {
    "original":           (True,  None),          # P0 基线
    "variant":            (False, None),          # P1 机制一
    "distractor":         (True,  "distractor"),  # P2a 机制二·干扰注入
    "hide":               (True,  "hide"),        # P2b 机制二·约束隐藏
    "variant_distractor": (False, "distractor"),  # P3a 组合
    "variant_hide":       (False, "hide"),        # P3b 组合
}

DEFENSE_LABEL = {
    "original": "P0 原始基线",
    "variant": "P1 同构多版本",
    "distractor": "P2a 干扰注入",
    "hide": "P2b 约束隐藏",
    "variant_distractor": "P3a 多版本+干扰",
    "variant_hide": "P3b 多版本+隐藏",
}


def build_view(problem, session_id, mode, view_token=None, avoid_key=None):
    """按展示模式组装题面视图（前端/实验共用，不含测试数据）。

    view_token: 可选的一次性版本分配键（优先于 session_id）。
      传 None 时按 session_id 分配（稳定版本，用于实验复现）；
      传非 None 时按该 token 分配（每次刷新换 token 即换版本，用于演示）。
      题面视图中的 session_id 字段始终记录真实会话，便于提交记录归集。
    avoid_key: 可选，指定时排除该版本 key（用于"换版本"时保证一定切换）。
    """
    if mode not in MODES:
        raise ValueError("未知展示模式: %r" % mode)
    force_original, submode = MODES[mode]
    alloc_key = view_token if view_token is not None else session_id
    variant = choose_variant(problem, alloc_key, force_original, avoid_key=avoid_key)

    paras = [p["text"] for p in variant["story"]]
    cons = [c["text"] for c in variant["constraints"]]

    if submode == "distractor":
        paras = paras + [problem["distractor"]["paragraph"]]
    elif submode == "hide":
        paras = [p["text"] for p in variant["story"] if not p.get("hideable")]
        cons = [c["text"] for c in variant["constraints"] if not c.get("hideable")]

    return {
        "problem_id": problem["id"],
        "title": problem["title"],
        "difficulty": problem["difficulty"],
        "tags": problem["tags"],
        "time_limit_ms": problem["time_limit_ms"],
        "memory_limit_mb": problem["memory_limit_mb"],
        "mode": mode,
        "defense_label": DEFENSE_LABEL[mode],
        "submode": submode,
        "variant_key": variant["key"],
        "variant_label": variant["label"],
        "statement": paras,
        "input_format": variant["input_format"],
        "output_format": variant["output_format"],
        "constraints": cons,
        "samples": variant["samples"],
        "test_count": len(variant["tests"]),
        "session_id": str(session_id),
    }


def view_tests(problem, session_id, mode, view_token=None, avoid_key=None):
    """取判题用的测试数据（与展示版本一致，view_token/avoid_key 用法同 build_view）。"""
    force_original, _sub = MODES[mode]
    alloc_key = view_token if view_token is not None else session_id
    variant = choose_variant(problem, alloc_key, force_original, avoid_key=avoid_key)
    return variant["tests"]
