# -*- coding: utf-8 -*-
"""构建脚本：把 PaddleOCR（onnxruntime-web + PP-OCRv4 mobile）引擎文件注入模板，生成最终单文件 HTML。
用法：python build.py
输出：价格打码水印工具.html
"""
import base64
import gzip
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
DEPS = os.path.join(BASE, "..", "_deps")

TPL = os.path.join(BASE, "app.html.template")
OUT = os.path.join(ROOT, "价格打码水印工具.html")
OCR = os.path.join(DEPS, "ocr")


def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def gz_b64(name):
    raw = read_bytes(os.path.join(OCR, name))
    comp = gzip.compress(raw, compresslevel=9)
    return base64.b64encode(comp).decode("ascii")


def main():
    tpl = read_text(TPL)

    # onnxruntime.js 作为 JS 字符串注入（含 </script> 转义）
    ort_js = read_text(os.path.join(OCR, "ort.min.js"))
    ort_js_json = ort_js.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n")
    ort_js_json = ort_js_json.replace("</script", "<\\/script").replace("</SCRIPT", "<\\/SCRIPT")

    # 字典转数组（与 RapidOCR character_list 对齐）
    dict_lines = [ln.rstrip("\n").rstrip("\r") for ln in read_text(os.path.join(OCR, "ppocr_keys_v1.txt")).split("\n")]
    dict_json = json.dumps(dict_lines, ensure_ascii=False)

    repl = {
        "/*__ORT_JS_JSON__*/": ort_js_json,
        "/*__ORT_WASM_GZ_B64__*/": gz_b64("ort-wasm-simd.wasm"),
        "/*__DET_ONNX_GZ_B64__*/": gz_b64("ch_PP-OCRv4_det_mobile.onnx"),
        "/*__REC_ONNX_GZ_B64__*/": gz_b64("ch_PP-OCRv4_rec_mobile.onnx"),
        "/*__DICT_JSON__*/": dict_json,
    }
    for k, v in repl.items():
        if k not in tpl:
            print("WARN: placeholder %s not found" % k)
        tpl = tpl.replace(k, v)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(tpl)

    print("OK ->", OUT)
    print("size: %.2f MB" % (os.path.getsize(OUT) / 1024 / 1024))


if __name__ == "__main__":
    main()
