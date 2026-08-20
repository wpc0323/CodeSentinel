# OJ-Anti-AI 在线评测场景下 AI 解题防护机制的设计与对照实验研究

简易评测 Web 系统 + 两种 AI 防护机制 + 有/无防护对照实验框架（结课大报告配套系统）。

参考立项书：`立项书.md`（必做项 M1-M7 / 验收标准 A1-A6）。

## 快速开始

```bash
# 1. 一键启动（自动创建虚拟环境、安装依赖、生成题库、启动服务并打开浏览器）
python start.py

# 其他入口
python start.py --port 9000            # 指定端口
python start.py --rebuild-problems     # 重新生成题库 JSON
python start.py --mock-experiment      # 跑一次 mock 对照实验（无需 API Key）
python start.py --analyze              # 对已有实验数据生成统计与图表
```

手动方式（等效）：

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python tools\build_problems.py          # 生成题库（已提交生成结果，可跳过）
.venv\Scripts\python -m uvicorn server.app:app --port 8000
```

打开 <http://127.0.0.1:8000> 。

> 判题为“受限子进程 + 隐藏测试数据比对”的演示级实现（立项书 N2 约定），请勿公网暴露。

## 系统组成

```
oj-anti-ai/
├── start.py                  # 一键启动 / mock 实验 / 统计分析
├── requirements.txt          # Python 3.8+ 兼容依赖
├── web/                      # 前端（原生 HTML/CSS/JS）
│   ├── index.html            #   题目列表
│   ├── problem.html          #   题目详情 + 防护开关 + 代码提交 + 判定结果
│   ├── submissions.html      #   提交记录
│   ├── experiment.html       #   实验数据看板
│   └── static/
├── server/                   # 后端（FastAPI）
│   ├── app.py                #   API：题目/题面/提交/记录/实验摘要
│   ├── problems.py           #   题库加载
│   ├── problems/*.json       #   10 道自拟题 × 3 同构版本 × 测试数据（生成产物）
│   ├── defense/
│   │   ├── variant.py        #   机制一：会话确定性版本分配
│   │   └── perturb.py        #   机制二：干扰注入 / 约束隐藏（展示层变换）
│   ├── judge/engine.py       #   判题引擎（Python3 / C++ 可选，超时与输出比对）
│   └── store.py              #   SQLite（submissions / experiment_runs）
├── tools/build_problems.py   # 题库生成器（标准解运行得出期望输出，含样例断言）
├── experiment/
│   ├── run_experiment.py     # 对照实验批量脚本（题目 × 防护 × 模型 × 重复）
│   ├── analyze.py            # 统计：通过率/误导率/卡方检验/图表
│   └── config.example.json   # 真实模型 API 配置模板
├── report/                   # 分析输出（CSV/图表/统计文本）
└── data/oj.db                # 运行数据（提交 + 实验记录）
```

## 题库（10 道自拟题，避免公开原题数据污染）

| 编号 | 标题 | 难度 | 考点 | 机制二陷阱设计 |
|---|---|---|---|---|
| P001 | 糖果清点 | 入门 | 模拟 | 干扰：诱导取模；隐藏：32 位溢出提示 |
| P002 | 回声串 | 入门 | 字符串/双指针 | 干扰：诱导转小写；隐藏：区分大小写规则 |
| P003 | 日期推算 | 入门 | 模拟/日期 | 干扰：无关星期信息；隐藏：跨年/闰年提示 |
| P004 | 活动安排 | 中档 | 贪心 | 干扰：无关场地信息；隐藏：首尾相接=冲突 |
| P005 | 括号校验 | 中档 | 栈 | 干扰：错误长度规律；隐藏：空串合法 |
| P006 | 频率冠军 | 入门 | 哈希 | 干扰：虚假保证；隐藏：并列字典序规则 |
| P007 | 背包采集 | 中档 | DP/背包 | 干扰：无关图鉴数字；隐藏：每种至多一份 |
| P008 | 迷宫寻路 | 中档 | BFS | 干扰：无关续航参数；隐藏：无解输出 -1 |
| P009 | 严格递增路线 | 中档 | DP/二分 | 干扰：诱导“已排序”；隐藏：严格递增约束 |
| P010 | 最小合并代价 | 中档 | 贪心/堆 | 干扰：无关编号信息；隐藏：任意两堆可合并 |

每题 3 个同构版本（V0 原始 + V1/V2 换背景/数值/变量名），测试数据含样例、随机与**针对隐藏约束的边界测试点**（误导率判定依据）。生成方式：`tools/build_problems.py` 用标准解实跑出期望输出并断言手写样例。

## 两种防护机制（均作用于展示层，不改变判题逻辑）

- **机制一 同构多版本展示**：`hash(题目ID|会话ID)` 确定性分配 V1/V2——同一会话稳定，不同会话不同；P0 基线恒为 V0。对抗记忆检索与答案套用。
- **机制二 隐藏干扰信息**：
  - 2a 干扰注入：把看似相关的诱导段落（蜜饵关键词）混入题干；
  - 2b 约束隐藏：跳过题干/数据范围中标记 `hideable` 的关键句，边界测试点不变。
- 组合状态：P0 基线 / P1 机制一 / P2 机制二 / P3 组合（页面细分 2a/2b）。

页面演示（对应立项书 5.3 验收脚本）：

1. 打开题目 → 默认 P0 原始版 → 提交代码 → 得到 AC/WA/TLE/RE/CE 判定；
2. 切到「P1 同构多版本」→ 点「重置会话」→ 题面数值/背景/样例变化；
3. 切到「P2a 干扰注入 / P2b 约束隐藏」→ 直观对比题干差异；
4. 「实验数据」页查看批量实验的通过率/误导率统计。

## 对照实验

### 演示模式（无需 API Key）

```bash
python start.py --mock-experiment   # 等效: experiment/run_experiment.py --mock
python start.py --analyze           # 生成 report/ 下 CSV、图表与卡方检验
```

mock 模型按防护状态给出 smart/buggy/baited 三种行为（确定性抽样），用于验证管线与演示统计形态；正式结论须用真实模型。

### 真实模型实验

1. 复制 `experiment/config.example.json` 为 `experiment/config.json`；
2. 填入 OpenAI 兼容模型（DeepSeek / 通义 / GLM 等）的 `base_url`、`model` 与 `api_key_env`；
3. 设置环境变量（如 `set DEEPSEEK_API_KEY=sk-...`）；
4. 执行：

```bash
.venv\Scripts\python experiment\run_experiment.py                 # 全量 10 题 × 4 状态 × 2 模型 × 3 次 = 240 次
.venv\Scripts\python experiment\run_experiment.py --problems P001,P004 --defenses P0,P2 --repeats 5
.venv\Scripts\python experiment\analyze.py                        # 统计+图表
```

- 固定温度 0.2、固定提示词模板（见 `run_experiment.py`），排除提示工程差异；
- 断点续跑：已完成的 (题目×状态×模型×重复) 自动跳过，`--force` 强制重跑；
- 原始留档：AI 原始回答、提取代码、逐测试点判定、耗时、时间戳全部写入 `data/oj.db`。

### 指标

| 指标 | 定义 |
|---|---|
| 通过率 | 判定 AC 的求解占比（首次提交即判） |
| 误导率 | 2a：回答/代码采纳蜜饵关键词；2b：边界测试点失守（规则判 + 人工复核原始回答） |
| 平均提交次数 | 当前每格 1 次求解（重试机制为增强项） |
| 错误类型分布 | AC/WA/TLE/RE/CE/NO_CODE 占比 |

显著性检验：P1/P2/P3 对 P0 的 2×2 卡方检验（α=0.05），见 `report/statistics.txt`。

## 技术栈

Python 3.8+ / FastAPI / SQLite / 原生 HTML-CSS-JS / httpx（OpenAI 兼容调用）/ pandas + scipy + matplotlib（分析）。
