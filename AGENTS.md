# AGENTS.md — 项目交接文档

> 本文件写给接手本项目的 AI 编程助手（DeepSeek Harness / dsh 或其他工具）。
> **开始任何改动前，请先完整阅读本文件。** 与用户沟通一律使用中文。

## 1. 项目是什么

「价格打码·水印工具」：纯前端单文件 HTML 工具。用 PaddleOCR（PP-OCRv4 mobile 模型 +
onnxruntime-web，全部跑在浏览器 WebAssembly 里）识别图片文字，自动给价格/关键词打码
（马赛克或自定义素材贴图），并可叠加文字/图片水印。图片全程本地处理、不上传，离线可用。

用户主力是手机浏览器（vivo），也用电脑。核心场景：电商图片批量处理。

主要功能：
- 三步流程：1 选图设置 → 2 识别打码 → 3 导出
- 方案（预设）：一键切换并保存整套设置
- 价格打码：识别含 ¥ 或小数点的数字串（如 ¥16.78、5.50）自动打码
- 关键词打码：命中关键词时打码，可选「只打该词」或「整行」
- 关键词水印：命中关键词时在附近盖水印（文字/图片，与全局水印独立）
- 全局文字水印 / 图片水印
- 设置导入/导出（换浏览器、换手机后恢复）
- 多图批量处理，导出超过 3 张自动打包成单个 zip

## 2. 两个版本（最重要的区别，别搞混！）

| | 本地完整版 | 网页版（GitHub Pages） |
|---|---|---|
| 源文件 | `_src/app.html.template`（模板，含 `__XXX__` 占位符） | 仓库根 `price-tool.html`（自包含，直接编辑） |
| 产物 | `价格打码水印工具.html`（约 23MB，构建生成，已 gitignore） | 无需构建，push 即生效 |
| 模型来源 | gzip+base64 内嵌在 HTML 里 | 从同目录 fetch `det.onnx` / `rec.onnx` / `ort-wasm.wasm`，`ort.js` 用 script 标签加载 |
| 模型缓存 | 不需要（文件即全部） | IndexedDB 永久缓存（key 前缀 `remote:MODEL_CACHE_VER:`），首次下载后离线可用 |

**同步规则：任何业务逻辑改动必须同时改两处**（模板 + 网页版），保持功能一致。
改完模板后跑 `python _src/build.py` 重新生成本地版；网页版改完仓库根的 `price-tool.html` 后推送。

## 3. 目录结构

```
├── index.html              # 根 URL 跳转页 → price-tool.html
├── price-tool.html         # ★ 网页版（在线版源码，直接编辑这个文件）
├── det.onnx                # 网页版模型：检测模型（= _deps/ocr/ch_PP-OCRv4_det_mobile.onnx）
├── rec.onnx                # 网页版模型：识别模型（= _deps/ocr/ch_PP-OCRv4_rec_mobile.onnx）
├── ort-wasm.wasm           # 网页版模型：onnxruntime wasm（= _deps/ocr/ort-wasm-simd.wasm）
├── ort.js                  # 网页版模型：onnxruntime js（= _deps/ocr/ort.min.js）
├── AGENTS.md               # 本文件
├── e2e_fb_test.py          # 端到端测试（无头 Edge 实测 OCR）
├── e2e_fb2_test.py         # 端到端测试增强版
├── _src/
│   ├── app.html.template   # ★ 本地版模板（源码）
│   ├── build.py            # 构建：注入依赖生成 ../价格打码水印工具.html
│   ├── verify.py           # 校验产物完整性
│   ├── push_via_api.py     # GitHub API 推送脚本（见第 6 节）
│   ├── ocr_demo.html.template + build_ocr_demo.py + check_js*.py  # 早期对比实验，仅存档
└── _deps/
    ├── ocr/                # 本地版构建依赖（PaddleOCR 模型 + onnxruntime + 字典）
    └── *.js / *.wasm / *.traineddata.gz   # 早期 tesseract 实验遗留，仅存档
```

仓库根的 4 个模型文件与 `_deps/ocr/` 下的是同一批文件（已核对哈希相同，只是改了名）。
**如果以后换模型：两处都要换，且网页版要把 `MODEL_CACHE_VER` 从 v1 改成 v2。**

## 4. 构建 / 校验 / 测试（本地完整版）

```bash
cd _src
python build.py     # 生成 ../价格打码水印工具.html（约 23MB）
python verify.py    # 校验产物（占位符残留/魔数/注入完整性），应输出 ALL CHECKS DONE
```

端到端测试（**目前是过时的，别被它吓到**）：
`e2e_fb_test.py` / `e2e_fb2_test.py` 用无头 Edge 实测 OCR（需 `pip install websocket-client`）。
2026-09-13 移交时实测：当前正在使用的正常版本跑出来也是 5/12 通过、卡在
"immediate step2" 等时序断言上（引擎加载需要时间，测试的等待预期是旧版写的）。
**测试失败 ≠ 产品有 bug**（新旧构建仅差 gzip 时间戳，线上版用户使用正常）。
有空可以把测试的等待逻辑修好，但不要为通过测试去改产品行为。

注意：build.py 用 gzip 压缩时带时间戳，**每次构建产物哈希都不同**，属正常现象，
不代表内容有差异（曾用 fc /b 核实过：同版本两次构建仅 12 字节 gzip 时间戳差异）。

## 5. 发布流程（网页版）

1. 修改仓库根 `price-tool.html`
2. 版本号递增：JS 里 `const TOOL_VER = "v1.3"` → v1.4，页脚 `verText` 同步显示
3. 同步改 `_src/app.html.template` 里的 TOOL_VER（两版版本号永远一致）
4. 若更新了模型文件（det.onnx 等）：网页版里 `MODEL_CACHE_VER` 从 "v1" 改 "v2"，
   否则老用户 IndexedDB 里还是旧模型
5. 推送到 GitHub（见下一节）
6. GitHub Pages 自动部署（约 1-2 分钟），用户需 Ctrl+F5 强刷才能看到新版

线上地址：https://yz66666666666.github.io/YYY-price-tool/

## 6. 网络限制与推送方式（重要！）

原开发机（中国大陆网络）**github.com 完全无法连接**（git clone / git push 直接
Connection reset），但 api.github.com 和 raw.githubusercontent.com 可以访问（已实测）。

新电脑先试 `git clone https://github.com/yz66666666666/YYY-price-tool.git`：
- 能通 → 正常用 git clone / git push / git pull
- 不通 → 用下面的备用通道：

```bash
# 备用克隆（codeload 可达但较慢，26MB+ 需耐心）
curl -L -o repo.tar.gz https://codeload.github.com/yz66666666666/YYY-price-tool/tar.gz/refs/heads/main
tar -xzf repo.tar.gz   # 解压出 YYY-price-tool-main/

# 备用推送（走 api.github.com，在仓库根运行）
python _src/push_via_api.py "提交说明"
```

push_via_api.py 认证方式（二选一）：环境变量 `GITHUB_TOKEN`，或本机 gh CLI 已
`gh auth login`。脚本会自动跳过未变化的文件（比对 git blob sha）、删除远程多余文件。
GitHub 账号：yz66666666666（仓库 public，main 分支，Pages 从 main 根目录部署）。

## 7. 硬性约束（违反即视为 bug）

1. 每次发布版本号必须递增（v1.3 → v1.4），且必须显示在页脚
2. 网页版模型必须走 IndexedDB 缓存机制（MODEL_CACHE_VER 控制）
3. 保存超过 3 张图片必须打包成单个 zip 下载（浏览器并发下载上限是 3）
4. 模型下载必须有实时进度条（已下载 MB / 总量 / 百分比）；不支持流式读取的浏览器
   降级为一次性读取（resp.arrayBuffer），功能不能坏
5. 导出设置必须提供「下载文件」选项（长文本复制粘贴容易出问题）
6. 根 URL 必须经 index.html 跳转到 price-tool.html

## 8. 踩过的坑（前车之鉴）

- gzip 时间戳导致构建产物哈希每次不同 → 正常，校验用 verify.py 而不是比哈希
- 浏览器 HTTP 缓存不可靠，模型持久化必须用 IndexedDB（v1.2 修的就是这个）
- 浏览器并发下载上限 3 个 → 多图导出必须 zip 打包
- ort.min.js 注入 HTML 时必须转义 `</script>`，否则提前闭合（build.py 已处理）
- GitHub API 偶发超时，重试即可（push_via_api.py 已内置 5 次重试）
- vivo 浏览器等国产浏览器对进度显示敏感，加载慢时用户会以为卡死 → 进度条是刚需（v1.3）
- e2e 测试的时序断言已过时（见第 4 节），当前版本跑同样失败，属测试问题不是产品问题

## 9. 用户偏好（按这个来）

- 中文沟通；方案要简单实用、少依赖，**不要过度设计**
- UI 交互：点击直接编辑优于按钮；详细配置用弹窗；设置按钮放界面右侧
- 数据录入：提供可复用的默认选项 + 可自定义，减少重复输入
- 更新机制：手动「检查更新」按钮 + 有更新时绿色提示，不要全自动更新
- 技术解释用日常类比，不堆术语；对行为的说明要精确无歧义（比如何时生效）
- 手机 + 电脑双端都要能用；重视数据安全（云同步 + 本地备份双保险）
- 公式/技术功能需要配清晰易懂的说明

## 10. 当前状态（2026-09-13 移交时）

- 版本 v1.3：模板 / 本地构建 / 网页版三者一致，功能同步
- MODEL_CACHE_VER = "v1"
- 最近两次改动：v1.2 网页版模型 IndexedDB 永久缓存；v1.3 模型下载实时进度条
  （流式读取 + 总量统计 + 不支持流的降级路径）
- 本仓库本次移交新加入：`_src/`、`_deps/`、e2e 测试、AGENTS.md、push_via_api.py
  （此前仓库里只有网页版文件）

## 11. 常见任务速查

**改业务逻辑（最常见）**：
1. 改 `_src/app.html.template`
2. 同步改仓库根 `price-tool.html`（网页版）
3. 两处 `TOOL_VER` + 页脚版本号 +1
4. `cd _src && python build.py && python verify.py`
5. `python _src/push_via_api.py "v1.4: 改动说明"`（或 git push）
6. 提醒用户网页版要 Ctrl+F5 强刷

**只改网页版（如缓存逻辑、下载体验）**：改 price-tool.html → 版本号 +1 → 推送，
模板里对应同步版本号即可。

**换模型**：替换 `_deps/ocr/` 与仓库根共 6 处文件（两套名字）→ MODEL_CACHE_VER +1 →
重新构建 + 推送。
