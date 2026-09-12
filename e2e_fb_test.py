import json, os, shutil, subprocess, tempfile, time
import urllib.request
from urllib.parse import quote
import websocket

ROOT = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(ROOT, "价格打码水印工具.html")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PORT = 9247
URL = "file:///" + quote(HTML.replace("\\", "/"), safe="/:@")

results = []
def check(name, cond):
    results.append((name, bool(cond)))
    print(("PASS" if cond else "FAIL"), "-", name)

prof = tempfile.mkdtemp(prefix="edge-fb-")
proc = subprocess.Popen([EDGE, "--headless=new", f"--remote-debugging-port={PORT}",
                         "--remote-allow-origins=*", f"--user-data-dir={prof}",
                         "--disable-gpu", URL],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
ws = None
try:
    ws_url = None
    for _ in range(80):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json") as r:
                targets = json.load(r)
            page = [t for t in targets if t.get("type") == "page" and "file:" in (t.get("url") or "")]
            if page:
                ws_url = page[0]["webSocketDebuggerUrl"]
                break
        except Exception:
            time.sleep(0.3)
    assert ws_url
    ws = websocket.create_connection(ws_url, max_size=None)
    ws.settimeout(300)
    _id = 0
    def send(method, params=None):
        global _id
        _id += 1
        ws.send(json.dumps({"id": _id, "method": method, "params": params or {}}))
        while True:
            m = json.loads(ws.recv())
            if m.get("id") == _id:
                return m
    send("Page.enable"); send("Runtime.enable")
    def ev(expr, await_promise=False):
        try:
            m = send("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": await_promise})
            res = m.get("result", {}).get("result", {})
            return res.get("value")
        except Exception:
            return None
    def wait_for(expr, timeout=300, interval=1.0):
        t0 = time.time()
        while time.time() - t0 < timeout:
            v = ev(expr)
            if v:
                return v
            time.sleep(interval)
        return None

    check("app loaded", wait_for("typeof bindUI === 'function'", 120))
    ev("localStorage.clear(); indexedDB.deleteDatabase('price-tool-model-cache')")
    ev("location.reload()")
    check("reload ok", wait_for("typeof bindUI === 'function'", 120))

    inject = """
(async () => {
  const c = document.createElement('canvas');
  c.width = 900; c.height = 700;
  const g = c.getContext('2d');
  g.fillStyle = '#ffffff'; g.fillRect(0, 0, 900, 700);
  g.fillStyle = '#000000'; g.font = '48px sans-serif';
  g.fillText('商品金额  ¥16.78', 60, 120);
  g.fillText('自动扣款￥23.00元', 60, 240);
  g.fillText('实付款', 60, 360);
  const blob = await new Promise(r => c.toBlob(r, 'image/png'));
  addPhotos([new File([blob], 'test.png', { type: 'image/png' })]);
  return 'ok';
})()
"""
    ev(inject, await_promise=True)
    check("photo added", wait_for("S.photos.length === 1", 30))

    # 点击识别，立即（<600ms）检查是否切到步骤2 且显示加载提示
    ev("document.getElementById('btnRun').click()")
    time.sleep(0.5)
    fb_step = ev("S.step")
    fb_txt = ev("document.getElementById('progressText').textContent") or ""
    print("   at 0.5s: step=%s text=%s" % (fb_step, fb_txt))
    check("immediate step2", fb_step == 2)
    check("loading hint shown", "正在加载识别引擎" in fb_txt)

    check("run completes step3", wait_for("S.step === 3", 300, 1.0))
    check("recognized", ev("S.photos[0].recognized === true"))
    labels = ev("S.photos[0].boxes.map(b => b.label).join('|')") or ""
    check("price box", "¥16.78" in labels)

    # 第二次（引擎已就绪）：点击后应立即显示"识别中"反馈
    ev("document.getElementById('back2').click()")
    check("back to step1", wait_for("S.step === 1", 10))
    ev("document.getElementById('btnRun').click()")
    time.sleep(0.3)
    fb2 = ev("S.step")
    print("   at 0.3s after 2nd click: step=%s" % fb2)
    check("2nd click immediate step2", fb2 == 2)
    check("2nd run completes", wait_for("S.step === 3", 300, 1.0))
    check("2nd recognized", ev("S.photos[0].recognized === true && S.photos[0].boxes.length > 0"))
finally:
    if ws:
        try: ws.close()
        except Exception: pass
    proc.terminate()
    try: shutil.rmtree(prof, ignore_errors=True)
    except Exception: pass

failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} passed")
if failed:
    print("FAILED:", failed)
    raise SystemExit(1)
print("ALL OK")
