# -*- coding: utf-8 -*-
"""题目数据服务：加载 server/problems/ 下的 JSON 题库。"""
import json
import threading
from pathlib import Path

PROBLEM_DIR = Path(__file__).resolve().parent / "problems"
_CACHE = {}
_LOCK = threading.Lock()


def load_all():
    with _LOCK:
        if not _CACHE:
            for p in sorted(PROBLEM_DIR.glob("P*.json")):
                try:
                    _CACHE[p.stem] = json.loads(p.read_text(encoding="utf-8"))
                except Exception as e:  # pragma: no cover
                    raise RuntimeError("加载题库失败 %s: %s" % (p, e))
        return _CACHE


def get_problem(pid):
    return load_all().get(pid)


def list_problems():
    """题目列表概要（不含测试数据与题面全文）。"""
    items = []
    for pid, p in sorted(load_all().items()):
        items.append({
            "id": pid,
            "title": p["title"],
            "difficulty": p["difficulty"],
            "tags": p["tags"],
            "time_limit_ms": p["time_limit_ms"],
            "memory_limit_mb": p["memory_limit_mb"],
            "variant_labels": [v["label"] for v in p["variants"]],
            "test_count": len(p["variants"][0]["tests"]),
        })
    return items
