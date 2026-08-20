# -*- coding: utf-8 -*-
"""SQLite 存储：提交记录与实验运行记录。"""
import json
import sqlite3
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "oj.db"

_LOCK = threading.Lock()


def _conn():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _LOCK, _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL NOT NULL,
            session_id TEXT NOT NULL,
            problem_id TEXT NOT NULL,
            variant_key TEXT NOT NULL,
            mode TEXT NOT NULL,
            language TEXT NOT NULL,
            verdict TEXT NOT NULL,
            passed INTEGER NOT NULL,
            total INTEGER NOT NULL,
            code TEXT NOT NULL,
            detail_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS experiment_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL NOT NULL,
            problem_id TEXT NOT NULL,
            defense TEXT NOT NULL,
            submode TEXT,
            model TEXT NOT NULL,
            repeat_idx INTEGER NOT NULL,
            session_id TEXT NOT NULL,
            variant_key TEXT NOT NULL,
            prompt TEXT NOT NULL,
            raw_response TEXT,
            extracted_code TEXT,
            verdict TEXT NOT NULL,
            passed INTEGER,
            total INTEGER,
            mislead INTEGER NOT NULL DEFAULT 0,
            mislead_reason TEXT,
            elapsed_s REAL,
            detail_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_exp_key ON experiment_runs(problem_id, defense, model, repeat_idx);
        """)


# ---------------------------------------------------------------- 提交记录
def add_submission(session_id, problem_id, variant_key, mode, language, verdict,
                   passed, total, code, detail):
    init_db()
    with _LOCK, _conn() as c:
        cur = c.execute(
            "INSERT INTO submissions(ts, session_id, problem_id, variant_key, mode, language,"
            " verdict, passed, total, code, detail_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (time.time(), session_id, problem_id, variant_key, mode, language,
             verdict, passed, total, code, json.dumps(detail, ensure_ascii=False)))
        return cur.lastrowid


def list_submissions(problem_id=None, session_id=None, limit=50):
    init_db()
    q = "SELECT id, ts, session_id, problem_id, variant_key, mode, language, verdict, passed, total FROM submissions"
    cond, args = [], []
    if problem_id:
        cond.append("problem_id=?"); args.append(problem_id)
    if session_id:
        cond.append("session_id=?"); args.append(session_id)
    if cond:
        q += " WHERE " + " AND ".join(cond)
    q += " ORDER BY id DESC LIMIT ?"
    args.append(int(limit))
    with _LOCK, _conn() as c:
        return [dict(r) for r in c.execute(q, args).fetchall()]


def get_submission(sid):
    init_db()
    with _LOCK, _conn() as c:
        r = c.execute("SELECT * FROM submissions WHERE id=?", (sid,)).fetchone()
        return dict(r) if r else None


# ---------------------------------------------------------------- 实验记录
def has_experiment_run(problem_id, defense, model, repeat_idx):
    init_db()
    with _LOCK, _conn() as c:
        r = c.execute("SELECT id FROM experiment_runs WHERE problem_id=? AND defense=? AND"
                      " model=? AND repeat_idx=?", (problem_id, defense, model, repeat_idx)).fetchone()
        return r is not None


def add_experiment_run(record):
    init_db()
    with _LOCK, _conn() as c:
        cur = c.execute(
            "INSERT INTO experiment_runs(ts, problem_id, defense, submode, model, repeat_idx,"
            " session_id, variant_key, prompt, raw_response, extracted_code, verdict, passed,"
            " total, mislead, mislead_reason, elapsed_s, detail_json)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (record.get("ts", time.time()), record["problem_id"], record["defense"],
             record.get("submode"), record["model"], record["repeat_idx"],
             record["session_id"], record["variant_key"], record["prompt"],
             record.get("raw_response"), record.get("extracted_code"), record["verdict"],
             record.get("passed"), record.get("total"), record.get("mislead", 0),
             record.get("mislead_reason"), record.get("elapsed_s"),
             json.dumps(record.get("detail"), ensure_ascii=False)))
        return cur.lastrowid


def list_experiment_runs(problem_id=None):
    init_db()
    q = "SELECT * FROM experiment_runs"
    args = []
    if problem_id:
        q += " WHERE problem_id=?"; args.append(problem_id)
    q += " ORDER BY id"
    with _LOCK, _conn() as c:
        return [dict(r) for r in c.execute(q, args).fetchall()]


def experiment_summary():
    """按防护状态聚合：运行数、AC 数、误导数、平均耗时。"""
    init_db()
    with _LOCK, _conn() as c:
        rows = c.execute(
            "SELECT defense, COUNT(*) n, SUM(CASE WHEN verdict='AC' THEN 1 ELSE 0 END) ac,"
            " SUM(mislead) mislead, AVG(elapsed_s) avg_elapsed FROM experiment_runs"
            " GROUP BY defense ORDER BY defense").fetchall()
        by_model = c.execute(
            "SELECT defense, model, COUNT(*) n, SUM(CASE WHEN verdict='AC' THEN 1 ELSE 0 END) ac,"
            " SUM(mislead) mislead FROM experiment_runs GROUP BY defense, model"
            " ORDER BY defense, model").fetchall()
        by_problem = c.execute(
            "SELECT problem_id, defense, COUNT(*) n, SUM(CASE WHEN verdict='AC' THEN 1 ELSE 0 END) ac"
            " FROM experiment_runs GROUP BY problem_id, defense ORDER BY problem_id, defense").fetchall()
        verdicts = c.execute(
            "SELECT defense, verdict, COUNT(*) n FROM experiment_runs"
            " GROUP BY defense, verdict ORDER BY defense, verdict").fetchall()
    return {
        "overall": [dict(r) for r in rows],
        "by_model": [dict(r) for r in by_model],
        "by_problem": [dict(r) for r in by_problem],
        "by_verdict": [dict(r) for r in verdicts],
        "total_runs": sum(r["n"] for r in rows),
    }
