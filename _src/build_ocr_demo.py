# -*- coding: utf-8 -*-
"""构建 PaddleOCR 对比测试页（单文件、100% 离线）
读取 _deps/ocr/ 下的依赖，gzip+base64 内嵌进 _src/ocr_demo.html.template 生成 ocr_demo.html
"""
import base64
import gzip
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPS = os.path.join(ROOT, "_deps", "ocr")
TMPL = os.path.join(ROOT, "_src", "ocr_demo.html.template")
OUT = os.path.join(ROOT, "ocr_demo.html")


def gz_b64(name):
    with open(os.path.join(DEPS, name), "rb") as f:
        raw = f.read()
    comp = gzip.compress(raw, compresslevel=9)
    b64 = base64.b64encode(comp).decode("ascii")
    print("%s: raw=%d gz=%d b64=%d" % (name, len(raw), len(comp), len(b64)))
    return b64


def main():
    ort_js_path = os.path.join(DEPS, "ort.min.js")
    with open(ort_js_path, "r", encoding="utf-8", errors="replace") as f:
        ort_js = f.read()
    # JSON 转义为 JS 字符串字面量，并防止 </script> 提前闭合
    ort_js_json = ort_js.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n")
    ort_js_json = ort_js_json.replace("</script", "<\\/script").replace("</SCRIPT", "<\\/SCRIPT")

    dict_path = os.path.join(DEPS, "ppocr_keys_v1.txt")
    with open(dict_path, "r", encoding="utf-8") as f:
        dict_lines = [ln.rstrip("\n").rstrip("\r") for ln in f.readlines()]
    dict_array_json = json.dumps(dict_lines, ensure_ascii=False)

    with open(TMPL, "r", encoding="utf-8") as f:
        html = f.read()

    repl = {
        "__ORT_JS_JSON__": ort_js_json,
        "__ORT_WASM_GZ_B64__": gz_b64("ort-wasm-simd.wasm"),
        "__DET_ONNX_GZ_B64__": gz_b64("ch_PP-OCRv4_det_mobile.onnx"),
        "__REC_ONNX_GZ_B64__": gz_b64("ch_PP-OCRv4_rec_mobile.onnx"),
        "__DICT_ARRAY_JSON__": dict_array_json,
    }
    for k, v in repl.items():
        if k not in html:
            print("WARN: placeholder %s not found in template" % k)
        html = html.replace(k, v)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("OK -> %s (%.2f MB)" % (OUT, os.path.getsize(OUT) / 1048576))


if __name__ == "__main__":
    sys.exit(main())
