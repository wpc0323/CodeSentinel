# -*- coding: utf-8 -*-
"""OJ-Anti-AI 简易评测系统后端（FastAPI）。

API:
  GET  /api/problems                     题目列表
  GET  /api/problem/{pid}?session&mode   题面视图（应用防护机制）
  POST /api/submit                       提交代码并判题
  GET  /api/submissions?problem_id&session_id&limit
  GET  /api/submission/{sid}             单条提交详情（含代码/测试点明细）
  GET  /api/experiment/summary           实验结果聚合
  GET  /api/health                       健康检查
静态页面挂载在 web/ 目录（根路径）。
"""
import asyncio
import functools
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from server import store
from server.defense.perturb import MODES, build_view, view_tests
from server.judge.engine import judge
from server.problems import get_problem, list_problems

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="OJ-Anti-AI 简易评测系统", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])

_JUDGE_SEM = asyncio.Semaphore(2)  # 判题并发上限（受限子进程）


@app.on_event("startup")
def _startup():
    store.init_db()


@app.get("/api/health")
def health():
    return {"ok": True, "problems": len(list_problems())}


@app.get("/api/problems")
def api_problems():
    return {"problems": list_problems()}


@app.get("/api/problem/{pid}")
def api_problem(pid: str, session: str = Query(default=""),
                mode: str = Query(default="original"),
                view_token: str = Query(default=""),
                avoid: str = Query(default="")):
    p = get_problem(pid)
    if not p:
        raise HTTPException(404, "题目不存在: %s" % pid)
    if mode not in MODES:
        raise HTTPException(400, "无效模式: %s（可选 %s）" % (mode, ", ".join(MODES)))
    if not session:
        session = str(uuid.uuid4())
    # view_token 非空时按它分配版本（每次刷新换 token 即换版本）；为空时回退到 session 稳定分配
    token = view_token if view_token else None
    avoid_key = avoid if avoid else None
    view = build_view(p, session, mode, view_token=token, avoid_key=avoid_key)
    view["view_token"] = view_token
    return view


class SubmitReq(BaseModel):
    problem_id: str
    session_id: str = Field(default="")
    mode: str = Field(default="original")
    language: str = Field(default="python3")
    view_token: str = Field(default="")
    avoid: str = Field(default="")
    code: str


@app.post("/api/submit")
async def api_submit(req: SubmitReq):
    p = get_problem(req.problem_id)
    if not p:
        raise HTTPException(404, "题目不存在: %s" % req.problem_id)
    if req.mode not in MODES:
        raise HTTPException(400, "无效模式: %s" % req.mode)
    session = req.session_id or str(uuid.uuid4())
    token = req.view_token if req.view_token else None
    avoid_key = req.avoid if req.avoid else None

    # 判题测试集与展示版本保持一致（用同一 view_token + avoid 选版本）
    tests = view_tests(p, session, req.mode, view_token=token, avoid_key=avoid_key)
    variant = build_view(p, session, req.mode, view_token=token, avoid_key=avoid_key)

    async with _JUDGE_SEM:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, functools.partial(judge, req.code, tests, p["time_limit_ms"], req.language))

    sid = store.add_submission(
        session, req.problem_id, variant["variant_key"], req.mode, req.language,
        result["verdict"], result["passed"], result["total"], req.code, result["detail"])
    return {
        "submission_id": sid,
        "problem_id": req.problem_id,
        "title": p["title"],
        "variant_key": variant["variant_key"],
        "variant_label": variant["variant_label"],
        "defense_label": variant["defense_label"],
        "language": req.language,
        **result,
    }


@app.get("/api/submissions")
def api_submissions(problem_id: str = Query(default=None),
                    session_id: str = Query(default=None),
                    limit: int = Query(default=50, ge=1, le=500)):
    return {"submissions": store.list_submissions(problem_id, session_id, limit)}


@app.get("/api/submission/{sid}")
def api_submission(sid: int):
    s = store.get_submission(sid)
    if not s:
        raise HTTPException(404, "提交不存在")
    return s


@app.get("/api/experiment/summary")
def api_experiment_summary():
    return store.experiment_summary()


# 静态页面（最后挂载，API 路由优先）
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
