"""
绘制 OJ Anti-AI 项目的模块图（Day 1 主路径）。
运行：python docs/draw_architecture.py
输出：docs/module_diagram.png
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.font_manager as fm

# 使用 Windows 常见中文字体，确保中文正常显示
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun']
plt.rcParams['axes.unicode_minus'] = False

fig, ax = plt.subplots(figsize=(14, 10))
ax.set_xlim(0, 14)
ax.set_ylim(0, 10)
ax.axis('off')

# 颜色
colors = {
    'actor': '#E3F2FD',      # 外部参与者
    'web': '#FFF3E0',        # 前端
    'api': '#E8F5E9',        # API 网关
    'service': '#F3E5F5',    # 服务层
    'judge': '#FFEBEE',      # 判题
    'store': '#E0F7FA',      # 存储
    'tool': '#FFFDE7',       # 工具
    'experiment': '#FBE9E7', # 实验
}

def box(ax, x, y, w, h, text, color, fontsize=10):
    """画圆角矩形并居中写字。"""
    rect = FancyBboxPatch((x - w/2, y - h/2), w, h,
                          boxstyle="round,pad=0.05,rounding_size=0.2",
                          facecolor=color, edgecolor='#333333', linewidth=1.2)
    ax.add_patch(rect)
    ax.text(x, y, text, ha='center', va='center', fontsize=fontsize,
            wrap=True, color='#212121', weight='bold')
    return rect

def arrow(ax, x1, y1, x2, y2, label='', color='#555555'):
    """带标签的箭头。"""
    style = "Simple, tail_width=0.5, head_width=4, head_length=6"
    kw = dict(arrowstyle=style, color=color, lw=1.2)
    a = FancyArrowPatch((x1, y1), (x2, y2), connectionstyle="arc3,rad=0",
                        **kw)
    ax.add_patch(a)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx, my + 0.18, label, fontsize=8, ha='center', va='bottom',
                color=color, bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                                        edgecolor='none', alpha=0.8))

# ========== 外部参与者 ==========
box(ax, 1.5, 8.5, 2.0, 0.9, 'OJ 用户\n（学生）', colors['actor'])
box(ax, 1.5, 5.0, 2.0, 0.9, '研究者/管理员', colors['actor'])
box(ax, 1.5, 1.5, 2.0, 0.9, 'AI 模型\n（实验对象）', colors['actor'])

# ========== 前端 / Web ==========
box(ax, 4.5, 8.5, 2.2, 0.9, 'web/\n前端页面', colors['web'])

# ========== API 网关 ==========
box(ax, 7.5, 6.7, 2.4, 1.0, 'server/app.py\nAPI 网关 / 路由', colors['api'], fontsize=11)

# ========== 服务层 ==========
box(ax, 7.5, 8.5, 2.4, 0.9, 'server/problems.py\n题目数据服务', colors['service'])
box(ax, 7.5, 4.8, 2.4, 0.9, 'server/defense/\n防御变换模块', colors['service'])
box(ax, 11.0, 6.7, 2.2, 1.0, 'server/judge/\nengine.py\n判题引擎', colors['judge'], fontsize=10)

# ========== 存储 ==========
box(ax, 11.0, 4.8, 2.2, 0.9, 'server/store.py\nSQLite 存储', colors['store'])

# ========== 工具与实验 ==========
box(ax, 4.5, 5.0, 2.2, 0.9, 'tools/\nbuild_problems.py\n题目构造工具', colors['tool'], fontsize=9)
box(ax, 4.5, 1.5, 2.2, 0.9, 'experiment/\nrun_experiment.py\n实验运行器', colors['experiment'], fontsize=9)
box(ax, 7.5, 1.5, 2.4, 0.9, 'experiment/\nanalyze.py\n实验分析器', colors['experiment'], fontsize=9)
box(ax, 11.0, 1.5, 2.2, 0.9, 'start.py\n启动器', colors['api'])

# ========== 主路径箭头（Day 1 核心流程） ==========
# 学生 -> web
arrow(ax, 2.5, 8.5, 3.4, 8.5, '浏览/提交')
# web -> API
arrow(ax, 5.6, 8.5, 6.3, 7.3, 'HTTP')
# API -> problems
arrow(ax, 7.5, 7.7, 7.5, 8.0, '取题')
# problems -> API
arrow(ax, 7.5, 8.0, 7.5, 7.7)
# API -> defense
arrow(ax, 7.5, 6.2, 7.5, 5.3, '变换题面')
# defense -> API
arrow(ax, 7.5, 5.3, 7.5, 6.2)
# API -> judge
arrow(ax, 8.7, 6.7, 9.9, 6.7, '提交代码')
# judge -> store
arrow(ax, 11.0, 6.2, 11.0, 5.3, '存结果')
# judge -> API (返回结果)
arrow(ax, 9.9, 6.5, 8.7, 6.5, '判题结果')
# API -> web (返回)
arrow(ax, 6.3, 6.9, 5.6, 8.2, '返回结果')

# ========== 实验路径 ==========
# 研究者 -> build_problems
arrow(ax, 2.5, 5.0, 3.4, 5.0, '构造/维护')
# build_problems -> problems 数据（虚线概念）
arrow(ax, 5.6, 5.3, 6.3, 8.2, '题目文件', color='#888888')
# 研究者 -> run_experiment
arrow(ax, 2.5, 4.6, 3.4, 2.0, '发起实验', color='#888888')
# AI 模型 -> run_experiment
arrow(ax, 2.5, 2.0, 3.4, 1.7, '生成答案', color='#888888')
# run_experiment -> API
arrow(ax, 5.6, 1.8, 6.3, 6.2, '批量提交', color='#888888')
# run_experiment -> analyze
arrow(ax, 5.6, 1.5, 6.3, 1.5, '原始数据', color='#888888')
# analyze -> store
arrow(ax, 8.7, 1.5, 9.9, 4.4, '读取结果', color='#888888')

# ========== 启动器 ==========
arrow(ax, 11.0, 2.0, 11.0, 4.3, '启动服务', color='#888888')

# ========== 标题与图例 ==========
ax.text(7, 9.6, 'OJ Anti-AI 项目模块图（Day 1 主路径）',
        fontsize=16, ha='center', va='center', weight='bold', color='#1A237E')

legend_items = [
    (colors['actor'], '外部参与者'),
    (colors['web'], '前端'),
    (colors['api'], 'API / 启动'),
    (colors['service'], '业务服务'),
    (colors['judge'], '判题'),
    (colors['store'], '存储'),
    (colors['tool'], '工具'),
    (colors['experiment'], '实验'),
]
for i, (c, label) in enumerate(legend_items):
    lx = 0.8 + i * 1.6
    ly = 0.4
    ax.add_patch(FancyBboxPatch((lx, ly - 0.15), 0.4, 0.3,
                                boxstyle="round,pad=0.02,rounding_size=0.05",
                                facecolor=c, edgecolor='#333333', linewidth=0.8))
    ax.text(lx + 0.5, ly, label, fontsize=8, va='center')

# 主路径高亮说明
ax.text(7, 9.2, 'Day 1 主路径：用户/模型 → web → API → 题目服务/防御模块 → 判题引擎 → SQLite 存储 → 结果展示',
        fontsize=10, ha='center', va='center', color='#BF360C',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFF8E1', edgecolor='#FFB300'))

plt.tight_layout()
plt.savefig('c:/Users/sztu/Desktop/work/oj-anti-ai/docs/module_diagram.png', dpi=200, bbox_inches='tight',
            facecolor='white', edgecolor='none')
print('已保存：docs/module_diagram.png')
