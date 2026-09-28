"""Screenshot of the scene review tool for the Notion page, via headless Chrome + CDP (no autosave is triggered:
the note and the Redo state are set for display only, without the input/click events that save feedback)."""
import asyncio, base64, json, pathlib, subprocess, time, urllib.request
import websockets
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "video/notion/assets/review-tool.png"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROFILE = pathlib.Path("/private/tmp/claude-501/-Users-tfischer-dev-videos-slow-it-down-claude/3b20e6c0-83f3-4de9-9cc2-6c49b2e19c64/scratchpad/chrome-shot")
NOTE = ("Winnie the Pooh should not be lip syncing but instead he should be taking honey from the weights jar. "
        "The movement should be him taking honey at the beginning frame and end frame. Make sure the WEIGHTS jar is readable in both.")
JS = """(() => {
  const el = document.getElementById('scene-R05'); if (!el) return 'no card';
  el.querySelector('textarea').value = %s;
  el.dataset.status = 'redo';
  el.querySelectorAll('.status button').forEach(b => b.setAttribute('aria-pressed', b.dataset.s === 'redo'));
  el.querySelector('.tags button[data-t="image"]').setAttribute('aria-pressed', 'true');
  el.scrollIntoView({block: 'start'}); window.scrollBy(0, -96);
  document.querySelectorAll('.scene.cur').forEach(e => e.classList.remove('cur')); el.classList.add('cur');
  return 'ok';
})()""" % json.dumps(NOTE)

async def main():
    proc = subprocess.Popen([CHROME, "--headless=new", "--remote-debugging-port=9333", f"--user-data-dir={PROFILE}", "--hide-scrollbars",
                             "--window-size=1600,1100", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try: targets = json.load(urllib.request.urlopen("http://127.0.0.1:9333/json/list")); break
            except Exception: time.sleep(0.2)
        ws_url = next(t["webSocketDebuggerUrl"] for t in targets if t["type"] == "page")
        async with websockets.connect(ws_url, max_size=64 * 1024 * 1024) as ws:
            n = 0
            async def cmd(method, **params):
                nonlocal n; n += 1; my = n
                await ws.send(json.dumps({"id": my, "method": method, "params": params}))
                while True:
                    m = json.loads(await ws.recv())
                    if m.get("id") == my: return m.get("result", {})
            await cmd("Emulation.setDeviceMetricsOverride", width=1600, height=1100, deviceScaleFactor=1.5, mobile=False)
            await cmd("Page.navigate", url="http://localhost:8765/video/review/")
            await asyncio.sleep(4)
            r = await cmd("Runtime.evaluate", expression=JS, returnByValue=True); print("inject:", r.get("result", {}).get("value"))
            await asyncio.sleep(3)
            shot = await cmd("Page.captureScreenshot", format="png")
            OUT.write_bytes(base64.b64decode(shot["data"])); print("saved", OUT, OUT.stat().st_size // 1024, "KB")
    finally:
        proc.terminate()
asyncio.run(main())
