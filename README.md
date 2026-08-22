# OJ-Anti-AI 在线评测场景下 AI 解题防护机制的设计与对照实验研究

简易评测 Web 系统 + 两种 AI 防护机制 + 有/无防护对照实验框架。

参考立项书：`立项书.md`（必做项 M1-M7 / 验收标准 A1-A6）。

## 1. 环境要求

- **操作系统**：Windows / Linux / macOS
- **Python**：3.8+（推荐 3.11+）
- **依赖**：自动通过 `requirements.txt` 安装（FastAPI / uvicorn / httpx / pandas / scipy / matplotlib）
- **浏览器**：现代浏览器（Chrome / Edge / Firefox，支持 HTML5 Canvas）
- **可选环境变量**（仅真实 AI 实验需要）：
  - `DEEPSEEK_API_KEY=sk-xxx`（DeepSeek 模型）
  - `DASHSCOPE_API_KEY=sk-xxx`（通义千问 Qwen-plus，对应 `config.example.json`）

> 密钥不写入文件，通过 `experiment/config.json` 的 `api_key_env` 字段引用环境变量名。

## 2. 安装

```bash
# 克隆仓库后进入项目根目录
cd oj-anti-ai

# 一键创建虚拟环境并安装所有依赖
python start.py
```

首次运行 `start.py` 会自动：
1. 创建 `.venv` 虚拟环境
2. 安装 `requirements.txt` 中全部依赖
3. 生成题库 JSON 文件到 `server/problems/`（8 道自拟题）
4. 初始化 SQLite 数据库 `data/oj.db`
5. 启动服务并打开浏览器

手动等效步骤：

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python tools\build_problems.py          # 生成题库（已提交生成结果可跳过）
```

## 3. 如何启动

### 一键启动（推荐）

```bash
# 默认端口 8000，启动后自动打开浏览器
python start.py

# 指定端口
python start.py --port 9000

# 重新生成题库后启动
python start.py --rebuild-problems
```

### 手动启动

```bash
.venv\Scripts\python -m uvicorn server.app:app --port 8000
```

启动后打开 <http://127.0.0.1:8000> 即可访问。

### 启动实验

```bash
# Mock 实验（无需 API Key，用固定返回值模拟 AI 行为）
python start.py --mock-experiment
# 或手动：
.venv\Scripts\python experiment\run_experiment.py --mock --repeats 2

# 真实模型实验（需先复制 config.example.json 为 config.json 并设置环境变量）
.venv\Scripts\python experiment\run_experiment.py --problems P001,P004 --defenses P0,P2 --repeats 5

# 统计分析（生成 report/ 下的 CSV、图表与卡方检验）
python start.py --analyze
# 或手动：
.venv\Scripts\python experiment\analyze.py
# 排除 mock 数据的纯真实实验分析：
.venv\Scripts\python experiment\analyze.py --mock-exclude
# 仅输出 CSV/统计文本，不生成图表：
.venv\Scripts\python experiment\analyze.py --no-charts
```

### 停止服务

在终端中按 `Ctrl+C` 停止 uvicorn 服务。

### 常见问题

| 问题 | 解决 |
|------|------|
| 端口 8000 已占用 | `--port 9000` 换端口，或 `Get-NetTCPConnection -LocalPort 8000` 查找并结束旧进程 |
| 题目页面 JS 报错 | 硬刷新 Ctrl+F5 清除缓存（`common.js?v=N` 缓存破坏机制） |
| Mock 实验报错 | 确保 `data/oj.db` 存在（启动一次服务即自动创建） |
| 真实 API 调用失败 | 检查 `config.json` 的 `base_url` 和对应环境变量（如 `DASHSCOPE_API_KEY`）是否正确设置 |

> ⚠️ 判题为"受限子进程 + 隐藏测试数据比对"的演示级实现，**请勿公网暴露**。

## 4. 目录或工程结构

```
oj-anti-ai/
├── start.py                  # 一键启动入口（建环境/装依赖/生成题库/启服务/跑实验/分析）
├── requirements.txt          # Python 依赖清单
│
├── web/                      # 前端（原生 HTML5 + Canvas + Vanilla JS）
│   ├── index.html            #   题目列表页
│   ├── problem.html          #   答题页（Canvas 抗抓取 + 防护开关 + 提交判题 + 反作弊弹窗）
│   ├── submissions.html      #   提交记录列表
│   ├── experiment.html       #   实验数据看板（聚合统计图表）
│   └── static/
│       ├── common.js         #   核心 JS：App 对象、Canvas 渲染、水印、AI 干扰行注入
│       └── style.css         #   全局样式
│
├── server/                   # 后端（FastAPI + SQLite）
│   ├── app.py                #   HTTP API（7 个端点：health/problems/problem/submit/submissions/experiment）
│   ├── problems.py           #   题库加载器
│   ├── store.py              #   SQLite 存储层（submissions / experiment_runs 两张表）
│   ├── problems/*.json       #   8 道自拟题 × 3 同构版本 × 测试数据（生成产物）
│   ├── defense/
│   │   ├── variant.py        #   机制一：会话确定性同构版本分配
│   │   └── perturb.py        #   机制二：干扰注入 / 约束隐藏；数据模型核心（表/树/图结构）
│   └── judge/
│       └── engine.py         #   判题引擎（Python3 子进程执行 + C++ 可选降级）
│
├── tools/
│   └── build_problems.py     # 题库生成器（标准解实跑期望输出 + 样例断言）
│
├── experiment/               # 对照实验框架
│   ├── run_experiment.py     # 批量实验脚本（题目 × 防护 × 模型 × 重复）
│   ├── analyze.py            # 统计分析（通过率/误导率/卡方检验/图表输出）
│   ├── config.example.json   # 真实 AI 模型 API 配置模板 → 复制为 config.json 使用
│   └── ai_self/              # mock 模式本地样例库（cases/ + answers.py + manifest.json）
│
├── data/oj.db                # SQLite 数据库（提交记录 + 实验结果，自动创建，不入库）
├── report/                   # 分析输出产物（CSV / 图表 / 统计文本，不入库）
│
├── README.md                 # 本文件（项目启动说明）
└── .gitignore                # 排除 config.json/.env/data/report/日志等
```

### 各模块职责一览

| 目录/文件 | 职责 | 关键接口/函数 |
|----------|------|-------------|
| `web/static/common.js` | Canvas 抗抓取渲染、水印、AI 干扰行 | `App.renderAntiAICanvas()`, `App.initWatermark()` |
| `server/defense/perturb.py` | 题面视图组装（树）、测试集组装（图）、模式配置（表） | `build_view()`, `view_tests()`, `MODES_TABLE` |
| `server/judge/engine.py` | 受限子进程判题 | `judge(code, tests, time_limit_ms)` |
| `experiment/run_experiment.py` | 批量 AI 对抗实验 | `run_experiment.py --mock/--repeats` |
| `experiment/analyze.py` | 统计与图表 | `analyze.py [--mock-exclude] [--no-charts]` |
| `start.py` | 一键入口 | `--port/--mock-experiment/--analyze` |

## 5. 两种防护机制

均作用于展示层，不改变判题逻辑：

- **机制一 同构多版本展示**（P1）：`hash(题目ID\|会话ID)` 确定性分配 V1/V2——同一会话稳定，不同会话不同；P0 基线恒为 V0。
- **机制二 信息扰动**：
  - P2a 干扰注入：把诱导段落（蜜饵关键词）混入题干；
  - P2b 约束隐藏：跳过标记 `hideable` 的关键句，边界测试点不变。
- **组合状态**：
  - P3a 多版本 + 干扰注入（机制一 + P2a）
  - P3b 多版本 + 约束隐藏（机制一 + P2b）

> 展示模式共 6 种：`original(P0)` / `variant(P1)` / `distractor(P2a)` / `hide(P2b)` / `variant_distractor(P3a)` / `variant_hide(P3b)`，见 `server/defense/perturb.py` 的 `MODES_TABLE`。
> 实验脚本 `run_experiment.py` 用 P0–P3 粗分组，P2/P3 通过 repeat 奇偶交替映射到具体子模式。

前端防护功能（答题页 toolbar）：
- 🔄 换同构版本 / 👁️ 防窥模式 / 💧 水印开关 / 🤖 AI 干扰行开关 / 📋 重置会话
- 进入答题页弹出反作弊提示弹窗

## 6. 题库（8 道自拟题）

| 编号 | 标题 | 难度 | 考点 | 陷阱设计 |
|---|---|---|---|---|
| P001 | 糖果清点 | 入门 | 模拟 | 干扰：诱导取模；隐藏：32 位溢出提示 |
| P002 | 回声串 | 入门 | 字符串/双指针 | 干扰：诱导转小写；隐藏：区分大小写规则 |
| P003 | 日期推算 | 入门 | 模拟/日期 | 干扰：无关星期信息；隐藏：跨年/闰年提示 |
| P004 | 活动安排 | 中档 | 贪心 | 干扰：无关场地信息；隐藏：首尾相接=冲突 |
| P005 | 括号校验 | 中档 | 栈 | 干扰：错误长度规律；隐藏：空串合法 |
| P006 | 频率冠军 | 入门 | 哈希 | 干扰：虚假保证；隐藏：并列字典序规则 |
| P007 | 迷宫寻路 | 中档 | BFS | 干扰：无关续航参数；隐藏：无解输出 -1 |
| P008 | 背包采集 | 中档 | DP/背包 | 干扰：无关图鉴数字；隐藏：每种至多一份 |

每题 3 个同构版本（V0 原始 + V1/V2 换背景/数值/变量名），测试数据含样例、随机与边界误导判定点。

## 7. 对照实验指标

| 指标 | 定义 |
|---|---|
| 通过率 | 判定 AC 的求解占比 |
| 误导率 | P2a：采纳蜜饵关键词；P2b：边界测试点失守 |
| 错误类型分布 | AC/WA/TLE/RE/CE 占比 |


