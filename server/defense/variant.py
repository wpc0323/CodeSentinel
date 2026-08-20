# -*- coding: utf-8 -*-
"""防护机制一：题目同构多版本展示（Isomorphic Variant Display）。

按 (题目ID, 分配键) 确定性分配版本：同一分配键稳定，不同分配键不同。
- 分配键通常是会话 ID（稳定版本，用于实验复现）；
- 也可传入一次性 view_token（每次刷新换版本，用于演示）。
原始模式（P0/基线）强制使用 V0。
"""
import hashlib


def choose_variant(problem, session_id, force_original=False, avoid_key=None):
    """选择同构版本。

    avoid_key: 若指定，则从候选版本中排除该 key（用于"换版本"时保证一定切换）。
               当排除后只剩一个候选时直接返回它；候选为空时回退到不排除。
    """
    variants = problem["variants"]
    if not variants:
        return None
    if force_original or len(variants) < 2:
        return variants[0]
    # 候选 = 非原始版本（V1, V2, ...）
    candidates = variants[1:]
    if avoid_key:
        filtered = [v for v in candidates if v["key"] != avoid_key]
        if filtered:  # 排除后仍有候选，用之；否则回退到全候选（避免空集）
            candidates = filtered
    key = "%s|%s" % (problem["id"], str(session_id))
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return candidates[int(h[:8], 16) % len(candidates)]
