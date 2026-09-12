# 价格打码·水印工具

纯前端单文件工具：PaddleOCR（PP-OCRv4 mobile + onnxruntime-web）在浏览器本地识别图片文字，
自动给价格/关键词打码（马赛克/素材贴图），可叠加文字/图片水印。图片不上传，完全离线可用。

- **在线使用**：https://yz66666666666.github.io/YYY-price-tool/
- **本地完整版**：`cd _src && python build.py` 生成 `价格打码水印工具.html`（约 23MB，模型内嵌）

## 结构

| 文件 | 说明 |
|---|---|
| `price-tool.html` | 网页版（在线版源码，直接编辑） |
| `_src/app.html.template` | 本地版模板（构建源码） |
| `_src/build.py` / `verify.py` | 构建 / 校验本地版 |
| `_src/push_via_api.py` | GitHub API 推送（github.com 直连不通时用） |
| `det.onnx` `rec.onnx` `ort.js` `ort-wasm.wasm` | 网页版加载的模型文件 |
| `_deps/ocr/` | 本地版构建依赖（与上面是同一批模型，原名） |

**AI 编程助手请先阅读 [AGENTS.md](AGENTS.md)** —— 包含双版本同步规则、发布流程、
版本号/缓存约束和用户偏好。

## 发布网页版

改 `price-tool.html` → 版本号 +1（`TOOL_VER`）→ `git push`（或 `python _src/push_via_api.py "说明"`）
→ Pages 自动部署 → 用户 Ctrl+F5 强刷。
