# -*- coding: utf-8 -*-
"""防护机制二：隐藏干扰信息（Information Perturbation）。

- 子模式 distractor（2a 干扰注入）：把与解法无关但看似相关的段落混入题干；
- 子模式 hide（2b 关键约束隐藏）：跳过题干/数据范围中标记为 hideable 的关键句。

两种子模式只作用于“题目展示层”，不改变判题逻辑与测试数据。
"""
from server.defense.variant import choose_variant


# ---------------------------------------------------------------------------
# 展示模式查找表（Table）
#   - 表头（columns）：mode / force_original / submode / defense / label
#   - 每行是一组互斥的展示模式配置；MODES_TABLE 即"模式 -> 属性"的关系表。
#   原散装 dict 已改为带列名的有序表，便于扩展新列（如 future 的 noise 等级）。
# ---------------------------------------------------------------------------
# 表头定义（列顺序即下方各行取值顺序）
MODE_COLUMNS = ["mode", "force_original", "submode", "defense", "label"]

# 表体：每行对应一种展示模式（行 = 模式，列 = 属性）
MODES_TABLE = [
    # mode             force_original  submode     defense  label
    ("original",           True,        None,       "P0",  "P0 原始基线"),
    ("variant",            False,       None,       "P1",  "P1 同构多版本"),
    ("distractor",         True,        "distractor", "P2a", "P2a 干扰注入"),
    ("hide",               True,        "hide",     "P2b", "P2b 约束隐藏"),
    ("variant_distractor", False,       "distractor", "P3a", "P3a 多版本+干扰"),
    ("variant_hide",       False,       "hide",     "P3b", "P3b 多版本+隐藏"),
]

# 兼容旧接口：由表派生的快速索引（dict），保证外部 MODES[mode] 仍可用
MODES = {row[0]: (row[1], row[2]) for row in MODES_TABLE}
DEFENSE_LABEL = {row[0]: row[4] for row in MODES_TABLE}

# 表的行索引（按 mode 取整行），供需要"整行属性"的调用方使用
MODE_ROWS = {row[0]: dict(zip(MODE_COLUMNS, row)) for row in MODES_TABLE}


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

    # 题面段落（故事）树：段落节点 -> 句子叶子
    story_nodes = []
    for p in variant["story"]:
        if submode == "hide" and p.get("hideable"):
            continue  # 约束隐藏模式跳过可隐藏段落
        story_nodes.append({
            "kind": "paragraph",
            "hideable": bool(p.get("hideable", False)),
            "text": p["text"],
            "sentences": _split_sentences(p["text"]),
        })
    if submode == "distractor":
        para = problem["distractor"]["paragraph"]
        story_nodes.append({
            "kind": "paragraph",
            "hideable": False,
            "is_distractor": True,                  # 标记蜜饵段落（树中的特殊节点）
            "text": para,
            "sentences": _split_sentences(para),
        })

    # 数据范围（约束）树
    cons_nodes = []
    for c in variant["constraints"]:
        if submode == "hide" and c.get("hideable"):
            continue
        cons_nodes.append({
            "kind": "constraint",
            "hideable": bool(c.get("hideable", False)),
            "text": c["text"],
            "sentences": _split_sentences(c["text"]),
        })

    # 向下兼容字段（纯文本数组形态，旧消费方无需改动）
    statement_text = [n["text"] for n in story_nodes]
    constraints_text = [n["text"] for n in cons_nodes]

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
        # 树结构（新增）：段落节点 -> 句子叶子
        "statement_tree": story_nodes,
        "constraints_tree": cons_nodes,
        # 向下兼容（旧版 string[] 形态）
        "statement": statement_text,
        "constraints": constraints_text,
        "input_format": variant["input_format"],
        "output_format": variant["output_format"],
        "samples": variant["samples"],
        "test_count": len(variant["tests"]),
        "session_id": str(session_id),
    }


def view_tests(problem, session_id, mode, view_token=None, avoid_key=None):
    """取判题用的测试数据（与展示版本一致，view_token/avoid_key 用法同 build_view）。

    返回**图(Graph)**增强的测试集：
      - "tests"：测试点列表（节点），每项含原 {name, input, output, edge}；
      - "graph"：图关系元数据（边界点误导判定边，见 build_test_graph），
        供误导率判定使用，对判题引擎透明（仍可直接迭代 tests）。
    """
    force_original, _sub = MODES[mode]
    alloc_key = view_token if view_token is not None else session_id
    variant = choose_variant(problem, alloc_key, force_original, avoid_key=avoid_key)
    return build_test_graph(variant["tests"])


def _split_sentences(text):
    """把一段题面文本拆成句子（按中英文句末标点），作为树的叶子节点。

    返回句子字符串列表（保留原顺序）。空段返回空列表。
    """
    if not text:
        return []
    parts, buf = [], ""
    for ch in text:
        buf += ch
        if ch in "。.!?！？\n":
            if buf.strip():
                parts.append(buf.strip())
            buf = ""
    if buf.strip():
        parts.append(buf.strip())
    return parts


def build_test_graph(tests):
    """把扁平测试点列表构造成图(Graph)结构。

    节点(node)：每个测试点 {name, input, output, edge}。
    边(edge)：有向边 edge_node -> [受其影响的测试点名]，表示"若该边界点被 WA，
    则这些测试点视为受误导（误导传播）"。
    adjacency：边界点名 -> 受其影响的测试点名列表（图邻接表）。

    保持对判题引擎透明：返回的仍是可迭代的测试点列表（原字段齐全），
    仅额外附带 graph 关系元数据。
    """
    edge_names = [t["name"] for t in tests if t.get("edge")]
    adjacency = {name: [t["name"] for t in tests] for name in edge_names}
    return {
        "tests": tests,                       # 节点列表（判题引擎直接消费）
        "graph": {                            # 图关系元数据
            "nodes": [t["name"] for t in tests],
            "edge_nodes": edge_names,         # 边界/误导节点
            "adjacency": adjacency,           # 邻接表：边界点 -> 受影响点
        },
    }
