# OJ Anti-AI 模块职责表

> 与 `module_diagram.png` 配套使用。范围聚焦 Day 1 主路径：用户/模型进入前端 → API → 题目/防御 → 判题 → 存储 → 结果展示。

## 外部参与者

| 名称 | 职责 | 输入 | 输出 | 依赖谁 | 谁负责 |
|---|---|---|---|---|---|
| OJ 用户（学生） | 在 Web 端浏览题目、切换防护模式、提交代码并查看结果 | 题面、提交反馈 | 代码提交、模式选择 | web/ 前端页面 | 最终用户 |
| 研究者/管理员 | 构造题目、发起批量实验、查看分析报表 | 原始题面、实验配置 | 实验数据、分析结论 | tools/、experiment/、analyze/ | 待补充 |
| AI 模型（实验对象） | 在实验模式下读取题目并生成候选答案 | 带防御变换的题面 | 候选答案代码 | experiment/run_experiment.py | 待补充 |

## 内部模块

| 名称 | 职责 | 输入 | 输出 | 依赖谁 | 谁负责 |
|---|---|---|---|---|---|
| `web/` 前端页面 | 提供题目列表、题面详情、提交、提交记录、实验聚合等页面（`index/problem/submissions/experiment.html`）；前端管理 session、view_token、防窥模式，经根路径 `/` 静态挂载加载 | 后端 API 返回的 JSON 数据 | 渲染后的 HTML 页面；向 API 发送的 HTTP 请求 | `server/app.py`（静态挂载 `/` 与 `/api/*`） | 待补充 |
| `server/app.py` API 网关 / 路由 | 暴露 `/api/*` 接口，接收前端与实验脚本请求，协调题目服务、防御模块、判题引擎、存储完成主流程；并以 `StaticFiles` 把 `web/` 挂在根路径 `/` | HTTP 请求（problems、problem、submit、submissions、submission、experiment/summary、health） | HTTP 响应（题面、判题结果、提交记录、实验聚合等 JSON） | `server/problems.py`、`server/defense/`、`server/judge/engine.py`、`server/store.py` | 待补充 |
| `server/problems.py` 题目数据服务 | 加载 `server/data/problems.json`，按 problem_id + mode + session + view_token + avoid 选取同构版本，输出题面与测试元数据 | problem_id、mode、session、view_token、avoid | 题面（statement、samples、constraints、variant_key 等） | `server/data/problems.json`（由 tools 生成） | 待补充 |
| `server/defense/` 防御变换模块 | 实现机制一（同构多版本 `variant.py`）与机制二（干扰注入 / 约束隐藏 `perturb.py`），按模式变换题面；`MODES` 定义可选模式、`build_view`/`view_tests` 生成展示与判题测试集 | 原始题面、模式选项、session、view_token、avoid | 变换后的题面及版本 key；与展示一致的判题测试集 | `server/problems.py` 提供的原始题面 | 待补充 |
| `server/judge/engine.py` 判题引擎 | 编译/解释用户代码，在沙箱子进程中运行测试点（由 `defense.view_tests` 提供），比对输出，返回 AC/WA/TLE/MLE/RE 等判定 | 代码、语言、测试数据、时间/内存限制 | 每条测试点判定结果、总体 verdict、运行耗时与错误信息 | `server/defense/`（取测试数据）、`server/store.py`（持久化） | 待补充 |
| `server/store.py` SQLite 存储 | 管理 SQLite 数据库；`submissions` 表持久化提交记录，`experiment_runs` 表持久化实验运行记录；提供 `experiment_summary` 聚合 | 判题结果、提交元数据、实验运行记录 | 可查询的提交记录、实验运行记录、聚合报表 | 无（被依赖） | 待补充 |
| `tools/build_problems.py` 题目构造工具 | 根据模板或手动配置生成多版本题目数据，输出 `server/data/problems.json` | 题目配置 / 模板文件 | `server/data/problems.json` 及隐藏测试数据 | 无（被依赖） | 待补充 |
| `experiment/run_experiment.py` 实验运行器 | 批量调用后端 API，让 AI 模型在原始/防御模式下作答，收集原始实验数据并写入 `experiment_runs` | 模型接口、题目列表、模式配置 | 批量提交结果、原始日志（写入 `store.experiment_runs`） | `server/app.py`、AI 模型接口、`server/store.py` | 待补充 |
| `experiment/analyze.py` 实验分析器 | 读取 `store` 中 `experiment_runs` 的实验结果，统计不同防御模式下 AI 通过率/误导率变化，生成图表与报告 | `experiment_runs` 中的实验记录 | 分析报表、可视化图表、Markdown 报告 | `server/store.py` | 待补充 |
| `start.py` 启动器 | 一键启动 uvicorn 服务，初始化数据库与数据文件 | 命令行参数 / 环境配置 | 运行中的后端服务进程 | `server/app.py`、`server/store.py` | 待补充 |

## 模块协作说明（Day 1 主路径）

1. **浏览题目**：OJ 用户打开 `web/index.html` → 请求 `server/app.py` `/api/problems` → `server/problems.py` 读取 `server/data/problems.json` → 返回题目列表给前端渲染。
2. **查看题面**：用户进入 `web/problem.html` → API 携带 `mode` + `view_token` → `server/problems.py` 调用 `server/defense/` 生成对应版本题面 → 返回前端展示。
3. **提交代码**：用户点击提交 → API 接收代码与模式信息 → `server/judge/engine.py` 运行隐藏测试点 → 将结果写入 `server/store.py` → API 返回判定详情给前端。
4. **实验验证**：研究者用 `tools/build_problems.py` 生成题目 → `experiment/run_experiment.py` 批量调用 API 让 AI 作答 → `experiment/analyze.py` 读取 `server/store.py` 生成分析报告。

## 本期范围说明

- **包含**：前端展示、API 路由、题目服务、防御变换、判题引擎、SQLite 存储、题目构造、实验运行与分析、服务启动器。
- **暂不深入**：完整类图、细粒度权限系统、分布式判题、在线 IDE 高级功能、模型训练代码（仅调用模型接口作答）。
