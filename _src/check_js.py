# -*- coding: utf-8 -*-
"""用 esprima 校验最终 HTML 中所有 <script> 的 JS 语法"""
import os, re, esprima

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "价格打码水印工具.html")
html = open(path, encoding="utf-8").read()

scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
print("script 块数量:", len(scripts))
for i, s in enumerate(scripts):
    s = s.strip()
    if not s:
        print(f"[{i}] 空")
        continue
    try:
        esprima.parseScript(s)
        print(f"[{i}] 语法 OK（{len(s)} 字符）")
    except Exception as e:
        print(f"[{i}] 语法错误: {e}")
