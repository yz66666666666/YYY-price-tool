# -*- coding: utf-8 -*-
"""校验最终 HTML 产物（PaddleOCR 版）"""
import base64, gzip, io, re, os

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "价格打码水印工具.html")
html = open(path, encoding="utf-8").read()

# 1. 构建占位符残留（仅检查本脚本的 5 个占位符；ort.min.js 内部自带的 __FUNC__ 之类不算）
leftover = re.findall(r"__ORT_JS_JSON__|__ORT_WASM_GZ_B64__|__DET_ONNX_GZ_B64__|__REC_ONNX_GZ_B64__|__DICT_JSON__", html)
print("构建占位符残留:", leftover if leftover else "无")

# 2. 结构完整性
print("html闭合:", html.rstrip().endswith("</html>"))
print("script标签数:", html.count("<script"))
print("总长度: %.2f MB" % (len(html) / 1048576))

# 3. gzip 资源校验（解压后检查魔数）
def check_gz(var):
    m = re.search(r'const %s = "([^"]+)";' % var, html)
    assert m, "%s 缺失" % var
    raw = base64.b64decode(m.group(1))
    gz = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    print("%s: gz=%d 解压=%d 头部=%s" % (var, len(raw), len(gz), gz[:4].hex()))
    return gz

wasm = check_gz("ORT_WASM_GZ")
assert wasm[:4] == b"\x00asm", "wasm 魔数错误"
det = check_gz("DET_ONNX_GZ")
rec = check_gz("REC_ONNX_GZ")
# onnx 是 protobuf 二进制，无文本魔数；det/rec 结构相似即可（首个字段 varint=ir_version）
assert det[:2] == rec[:2], "det/rec 头部不一致"

# 4. ORT_JS 注入（含转义引号，用非贪婪跨转义匹配）
m = re.search(r'const ORT_JS = "((?:[^"\\]|\\.)*)";', html)
assert m, "ORT_JS 缺失"
print("ORT_JS 注入:", len(m.group(1)) > 1000)

# 5. 字典数组校验
m = re.search(r'const DICT = (\[.*?\]);', html, re.S)
assert m, "DICT 缺失"
dict_list = re.findall(r'"(?:[^"\\]|\\.)*"', m.group(1))
print("DICT 条目数:", len(dict_list))

# 6. 内联 script 安全（只有主 script 的闭合 </script>，ORT_JS 内若有未转义的会多出来）
print("</script> 出现次数:", html.count("</script>"))

print("ALL CHECKS DONE")
