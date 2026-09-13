# -*- coding: utf-8 -*-
"""通过 GitHub API 把仓库根目录同步到远程 main 分支。

背景：开发机所在网络 github.com 无法直连（git push 会 Connection reset），
但 api.github.com 可达。本脚本用 Git Data API（blobs -> tree -> commit -> update ref）
完成一次完整提交，效果等同 git push。

用法（在仓库根目录运行）：
    python _src/push_via_api.py "提交说明"

认证（二选一）：
    1. 环境变量 GITHUB_TOKEN
    2. 本机 gh CLI 已 gh auth login（脚本自动执行 gh auth token 取凭证）

行为：
    - 与远程 main 最新树比对（git hash-object 计算 blob sha），未变化的文件自动跳过
    - 远程存在、本地不存在的文件会被删除（保持与本地目录完全一致）
    - 排除 .gitignore 中的构建产物（见下方 EXCLUDES，两处需同步维护）
"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

REPO = "yz66666666666/YYY-price-tool"
API = "https://api.github.com"
BRANCH = "main"

# 与 .gitignore 保持一致：构建产物不推送
EXCLUDES = {"价格打码水印工具.html", "ocr_demo.html"}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 仓库根


def get_token():
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        return tok.strip()
    try:
        return subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    except Exception:
        sys.exit("未找到凭证：请设置 GITHUB_TOKEN 环境变量，或先运行 gh auth login")


TOKEN = get_token()


def api(method, path, payload=None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    last = None
    for i in range(5):
        req = urllib.request.Request(API + path, data=body, method=method, headers={
            "Authorization": "Bearer " + TOKEN,
            "Accept": "application/vnd.github+json",
            "User-Agent": "price-tool-push",
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                data = r.read()
                return json.loads(data) if data else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")
            sys.exit("HTTP %s %s\n%s" % (e.code, path, detail[:800]))
        except Exception as e:
            last = e
            print("  网络错误，重试 %d/5: %s" % (i + 1, e))
            time.sleep(3 * (i + 1))
    sys.exit("API 多次失败: %s (%s)" % (path, last))


def collect_files():
    out = {}
    for dirpath, _dirs, names in os.walk(ROOT):
        if os.sep + ".git" in dirpath:
            continue
        for n in names:
            p = os.path.join(dirpath, n)
            rel = os.path.relpath(p, ROOT).replace("\\", "/")
            if rel in EXCLUDES or rel.startswith("_tmp_"):
                continue
            out[rel] = p
    return out


def _blob_sha_py(path):
    """不依赖 git 的实现：git 的 blob sha = sha1("blob <字节数>\\0" + 文件内容)。
    本机没装 git 时用这个，结果与 git hash-object --no-filters 一致。"""
    import hashlib
    size = os.path.getsize(path)
    h = hashlib.sha1()
    h.update(("blob %d\0" % size).encode("ascii"))
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def blob_sha(path):
    """git hash-object --no-filters 的结果就是 GitHub 的 blob sha（跳过换行转换）。
    本机没有 git 时自动退回纯 Python 实现（见上）。"""
    try:
        return subprocess.check_output(
            ["git", "hash-object", "--no-filters", path], text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return _blob_sha_py(path)


def main():
    msg = sys.argv[1] if len(sys.argv) > 1 else "sync via API " + time.strftime("%Y-%m-%d %H:%M")

    ref = api("GET", "/repos/%s/git/ref/heads/%s" % (REPO, BRANCH))
    parent = ref["object"]["sha"]
    base = api("GET", "/repos/%s/git/commits/%s" % (REPO, parent))["tree"]["sha"]
    remote_tree = api("GET", "/repos/%s/git/trees/%s?recursive=1" % (REPO, base))
    if remote_tree.get("truncated"):
        sys.exit("远程树过大被截断，请改用 git 操作")
    remote = {t["path"]: t for t in remote_tree.get("tree", []) if t["type"] == "blob"}

    local = collect_files()
    tree_items = []

    # 上传新增/变更文件
    for rel in sorted(local):
        p = local[rel]
        if rel in remote and remote[rel]["sha"] == blob_sha(p):
            continue
        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        r = api("POST", "/repos/%s/git/blobs" % REPO, {"content": b64, "encoding": "base64"})
        tree_items.append({"path": rel, "mode": "100644", "type": "blob", "sha": r["sha"]})
        print("上传: %s (%.1f MB)" % (rel, os.path.getsize(p) / 1048576))

    # 删除远程多余文件
    for rel in sorted(set(remote) - set(local)):
        tree_items.append({"path": rel, "mode": "100644", "type": "blob", "sha": None})
        print("删除: %s" % rel)

    if not tree_items:
        print("没有变化，无需提交")
        return

    tree = api("POST", "/repos/%s/git/trees" % REPO,
               {"base_tree": base, "tree": tree_items})
    commit = api("POST", "/repos/%s/git/commits" % REPO,
                 {"message": msg, "tree": tree["sha"], "parents": [parent]})
    api("PATCH", "/repos/%s/git/refs/heads/%s" % (REPO, BRANCH), {"sha": commit["sha"]})
    print("完成: %s - %s" % (commit["sha"][:7], msg))


if __name__ == "__main__":
    main()
