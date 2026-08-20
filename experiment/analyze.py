# -*- coding: utf-8 -*-
"""实验结果统计分析：描述统计 + 卡方检验 + 可视化。

输出（report/ 目录）:
  - table_overall.csv / table_by_model.csv / table_by_problem.csv / table_verdict.csv
  - chart_pass_rate.png / chart_mislead.png / chart_verdict.png
  - statistics.txt（含 P1/P2/P3 与 P0 的卡方检验）

用法: python experiment/analyze.py [--mock-exclude]
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from server import store  # noqa: E402

REPORT_DIR = ROOT / "report"
DEFENSE_ORDER = ["P0", "P1", "P2", "P3"]
DEFENSE_NAME = {"P0": "P0 原始基线", "P1": "P1 同构多版本",
                "P2": "P2 信息扰动", "P3": "P3 组合防护"}
SUBMODE_NAME = {"distractor": "2a 干扰注入", "hide": "2b 约束隐藏", None: "-"}


def load_runs():
    rows = store.list_experiment_runs()
    if not rows:
        print("没有实验数据。请先运行 experiment/run_experiment.py（或 --mock）。")
        sys.exit(0)
    df = pd.DataFrame(rows)
    df["ac"] = (df["verdict"] == "AC").astype(int)
    df["valid"] = (df["verdict"] != "API_ERROR").astype(int)
    return df


def rate(n, d):
    return round(100.0 * n / d, 1) if d else 0.0


def overall_table(df):
    g = df.groupby("defense").agg(
        n=("ac", "size"), ac=("ac", "sum"), mislead=("mislead", "sum"),
        avg_elapsed=("elapsed_s", "mean")).reset_index()
    g["avg_elapsed"] = g["avg_elapsed"].fillna(0).round(1)
    g["pass_rate"] = [rate(a, n) for a, n in zip(g["ac"], g["n"])]
    g["mislead_rate"] = [rate(m, n) for m, n in zip(g["mislead"], g["n"])]
    g["defense_name"] = g["defense"].map(DEFENSE_NAME)
    g["order"] = g["defense"].map({d: i for i, d in enumerate(DEFENSE_ORDER)})
    return g.sort_values("order")


def by_model_table(df):
    g = df.groupby(["defense", "model"]).agg(
        n=("ac", "size"), ac=("ac", "sum"), mislead=("mislead", "sum")).reset_index()
    g["pass_rate"] = [rate(a, n) for a, n in zip(g["ac"], g["n"])]
    g["mislead_rate"] = [rate(m, n) for m, n in zip(g["mislead"], g["n"])]
    g["order"] = g["defense"].map({d: i for i, d in enumerate(DEFENSE_ORDER)})
    return g.sort_values(["order", "model"])


def by_problem_table(df):
    g = df.groupby(["problem_id", "defense"]).agg(
        n=("ac", "size"), ac=("ac", "sum")).reset_index()
    g["pass_rate"] = [rate(a, n) for a, n in zip(g["ac"], g["n"])]
    g["order"] = g["defense"].map({d: i for i, d in enumerate(DEFENSE_ORDER)})
    return g.sort_values(["problem_id", "order"])


def chi_square_vs_p0(df):
    """各防护状态与 P0 的通过率卡方检验（2×2 列联表）。"""
    lines = []
    try:
        from scipy.stats import chi2_contingency
    except ImportError:
        return "（未安装 scipy，跳过显著性检验）"

    base = df[df["defense"] == "P0"]
    base_ac, base_n = int(base["ac"].sum()), len(base)
    lines.append("对照检验（卡方检验，显著性水平 α=0.05）：")
    lines.append("  基线 P0: AC %d / %d" % (base_ac, base_n))
    for d in DEFENSE_ORDER[1:]:
        sub = df[df["defense"] == d]
        if not len(sub):
            continue
        ac, n = int(sub["ac"].sum()), len(sub)
        table = [[ac, n - ac], [base_ac, base_n - base_ac]]
        try:
            chi2, p, dof, _exp = chi2_contingency(table, correction=True)
            sig = "显著" if p < 0.05 else "不显著"
            lines.append("  %s vs P0: AC %d/%d -> 卡方=%.3f, p=%.4f（%s）"
                         % (d, ac, n, chi2, p, sig))
        except ValueError:
            lines.append("  %s vs P0: 样本不足" % d)
    # 子模式细分（P2/P3 -> 2a/2b）
    lines.append("")
    lines.append("子模式细分（P2/P3 按 2a 干扰注入 / 2b 约束隐藏）：")
    for d in ("P2", "P3"):
        for sm in ("distractor", "hide"):
            sub = df[(df["defense"] == d) & (df["submode"] == sm)]
            if not len(sub):
                continue
            ac, n = int(sub["ac"].sum()), len(sub)
            mis = int(sub["mislead"].sum())
            lines.append("  %s-%s: AC %d/%d（%.1f%%），误导 %d/%d（%.1f%%）"
                         % (d, SUBMODE_NAME[sm], ac, n, rate(ac, n), mis, n, rate(mis, n)))
    lines.append("")
    lines.append("注：p 值基于小样本时应谨慎解读，建议结合通过率差值与误导率描述性结论。")
    return "\n".join(lines)


def make_charts(df):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False

    colors = {"P0": "#94a3b8", "P1": "#6366f1", "P2": "#f59e0b", "P3": "#dc2626"}

    # 1. 通过率（整体 + 按模型分组）
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    g = overall_table(df)
    axes[0].bar(g["defense"], g["pass_rate"], color=[colors[d] for d in g["defense"]])
    for x, (d, r) in enumerate(zip(g["defense"], g["pass_rate"])):
        axes[0].text(x, r + 1, "%.1f%%" % r, ha="center", fontsize=10)
    axes[0].set_title("各防护状态 AI 解题通过率（全部模型）")
    axes[0].set_ylabel("通过率 %"); axes[0].set_ylim(0, 105)

    gm = by_model_table(df)
    models = sorted(gm["model"].unique())
    width = 0.8 / max(len(models), 1)
    for j, m in enumerate(models):
        sub = gm[gm["model"] == m].set_index("defense").reindex(DEFENSE_ORDER).fillna(0)
        axes[1].bar([i + j * width for i in range(len(DEFENSE_ORDER))],
                    sub["pass_rate"], width=width, label=m)
    axes[1].set_xticks([i + width * (len(models) - 1) / 2 for i in range(len(DEFENSE_ORDER))])
    axes[1].set_xticklabels(DEFENSE_ORDER)
    axes[1].set_title("通过率（按模型细分）"); axes[1].set_ylabel("通过率 %")
    axes[1].legend(); axes[1].set_ylim(0, 105)
    plt.tight_layout(); plt.savefig(REPORT_DIR / "chart_pass_rate.png", dpi=150); plt.close()

    # 2. 误导率
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    ax.bar(g["defense"], g["mislead_rate"], color=[colors[d] for d in g["defense"]])
    for x, r in enumerate(g["mislead_rate"]):
        ax.text(x, r + 1, "%.1f%%" % r, ha="center", fontsize=10)
    ax.set_title("各防护状态误导率（规则判定）"); ax.set_ylabel("误导率 %"); ax.set_ylim(0, 105)
    plt.tight_layout(); plt.savefig(REPORT_DIR / "chart_mislead.png", dpi=150); plt.close()

    # 3. 判定类型堆叠
    vc = df.groupby(["defense", "verdict"]).size().unstack(fill_value=0)
    vc = vc.reindex([d for d in DEFENSE_ORDER if d in vc.index])
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    bottom = [0] * len(vc)
    verdict_colors = {"AC": "#16a34a", "WA": "#dc2626", "TLE": "#7c3aed",
                      "RE": "#f59e0b", "CE": "#64748b", "NO_CODE": "#0ea5e9",
                      "API_ERROR": "#111827"}
    for v in ["AC", "WA", "TLE", "RE", "CE", "NO_CODE", "API_ERROR"]:
        if v in vc.columns:
            ax.bar(vc.index, vc[v], bottom=bottom, label=v, color=verdict_colors.get(v))
            bottom = [b + n for b, n in zip(bottom, vc[v])]
    ax.set_title("判定类型分布（按防护状态）"); ax.set_ylabel("次数")
    ax.legend(title="判定")
    plt.tight_layout(); plt.savefig(REPORT_DIR / "chart_verdict.png", dpi=150); plt.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock-exclude", action="store_true",
                    help="排除 mock-ai 模型的数据（正式实验分析用）")
    ap.add_argument("--no-charts", action="store_true",
                    help="不生成图片（只输出 CSV 与统计文本）")
    args = ap.parse_args()

    df = load_runs()
    if args.mock_exclude:
        df = df[df["model"] != "mock-ai"]
        if not len(df):
            print("排除 mock 数据后没有记录。"); return

    REPORT_DIR.mkdir(exist_ok=True)
    total_n, total_ac = len(df), int(df["ac"].sum())
    print("实验数据: %d 次求解，其中 AC %d（总通过率 %.1f%%），模型: %s"
          % (total_n, total_ac, rate(total_ac, total_n), ", ".join(df["model"].unique())))

    t_overall = overall_table(df)
    t_model = by_model_table(df)
    t_problem = by_problem_table(df)
    t_verdict = df.groupby(["defense", "verdict"]).size().reset_index(name="n")

    t_overall.to_csv(REPORT_DIR / "table_overall.csv", index=False, encoding="utf-8-sig")
    t_model.to_csv(REPORT_DIR / "table_by_model.csv", index=False, encoding="utf-8-sig")
    t_problem.to_csv(REPORT_DIR / "table_by_problem.csv", index=False, encoding="utf-8-sig")
    t_verdict.to_csv(REPORT_DIR / "table_verdict.csv", index=False, encoding="utf-8-sig")

    stats = chi_square_vs_p0(df)
    header = [
        "=" * 62,
        "OJ-Anti-AI 对照实验统计报告（自动生成）",
        "数据量: %d 次求解 | 模型: %s | 题目: %d 道" % (
            total_n, ", ".join(sorted(df["model"].unique())), df["problem_id"].nunique()),
        "=" * 62, "",
        "一、总览（按防护状态）",
        t_overall.to_string(index=False), "",
        "二、按模型细分",
        t_model.to_string(index=False), "",
        "三、显著性检验",
        stats,
    ]
    (REPORT_DIR / "statistics.txt").write_text("\n".join(header), encoding="utf-8")
    print("\n".join(header[4:8]))
    print(stats.splitlines()[0])

    if args.no_charts:
        print("\n（--no-charts：跳过图表生成）")
    else:
        try:
            make_charts(df)
            print("\n图表: %s" % ", ".join(
                p.name for p in REPORT_DIR.glob("chart_*.png")))
        except Exception as e:  # noqa: BLE001
            print("图表生成失败: %s" % e)
    print("全部输出已写入 %s" % REPORT_DIR)


if __name__ == "__main__":
    main()
