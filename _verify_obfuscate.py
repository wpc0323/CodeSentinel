# -*- coding: utf-8 -*-
"""验证题面反抓取：dump DOM 后统计零宽字符/白色span/样例纯净度。"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_dom_dump.html"

edge = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not Path(edge).exists():
    edge = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

subprocess.run([
    edge, "--headless", "--disable-gpu", "--dump-dom",
    "--virtual-time-budget=6000",
    "http://127.0.0.1:8000/problem.html?id=P001&mode=variant",
], stdout=open(OUT, "w", encoding="utf-8"), stderr=subprocess.DEVNULL, timeout=60)

dom = OUT.read_text(encoding="utf-8")
zw = re.compile("[\u200b\u200c\u200d\u2060]")
# 浏览器序列化时会把 #ffffff 规范化为 rgb(255, 255, 255)，两种都匹配
spans = re.compile(r"color:\s*(?:#ffffff|rgb\(255,\s*255,\s*255\))", re.I)
pres = re.compile(r"<pre>[\s\S]*?</pre>")

zw_total = len(zw.findall(dom))
white_total = len(spans.findall(dom))
pre_list = pres.findall(dom)
pre_zw = sum(len(zw.findall(p)) for p in pre_list)
pre_white = sum(len(spans.findall(p)) for p in pre_list)

print("ZW chars total: %d" % zw_total)
print("white spans total: %d" % white_total)
print("pre blocks: %d | ZW in pre: %d | white in pre: %d" % (len(pre_list), pre_zw, pre_white))

# 抽样打印一段题面文本，展示零宽字符的实际分布
m = re.search(r"<p>[\s\S]{20,400}?</p>", dom)
if m:
    seg = re.sub(r"<[^>]+>", "", m.group(0))
    print("\nsample paragraph (raw repr, ZW visible as escapes):")
    print(repr(seg[:200]))

OUT.unlink()
