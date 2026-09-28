"""Local server for the scene review tool: serves the project (with HTTP Range, so video seeks work) and saves feedback.

usage: python3 video/review/server.py [--port 8765]    then open http://localhost:8765/
GET  /api/feedback  -> the saved feedback state (video/review/feedback.json)
POST /api/feedback  -> {"state": {...}, "markdown": "..."}; writes feedback.json and feedback.md next to this file
Binds to 127.0.0.1 only. Standard library only.
"""
import argparse, json, os, pathlib, re, tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def atomic_write(path, text):
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=path.suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as f: f.write(text)
    os.replace(tmp, path)

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw): super().__init__(*a, directory=str(ROOT), **kw)
    def log_message(self, fmt, *a):
        if "/api/" in (self.path or ""): super().log_message(fmt, *a)

    def end_headers(self):
        if self.path.endswith((".html", ".js", ".json", "/")): self.send_header("Cache-Control", "no-cache")
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(302); self.send_header("Location", "/video/review/"); self.end_headers(); return
        if self.path.startswith("/api/feedback"):
            p = HERE / "feedback.json"
            body = p.read_bytes() if p.exists() else b"{}"
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body); return
        rng = self.headers.get("Range")
        if not rng: return super().do_GET()
        path = self.translate_path(self.path)
        if not os.path.isfile(path): return super().do_GET()
        m = re.match(r"bytes=(\d*)-(\d*)$", rng.strip())
        size = os.path.getsize(path)
        if not m: self.send_error(416); return
        start = int(m.group(1)) if m.group(1) else max(0, size - int(m.group(2) or 0))
        end = int(m.group(2)) if m.group(1) and m.group(2) else size - 1
        end = min(end, size - 1)
        if start > end: self.send_response(416); self.send_header("Content-Range", f"bytes */{size}"); self.end_headers(); return
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start); left = end - start + 1
            try:
                while left > 0:
                    chunk = f.read(min(1 << 20, left))
                    if not chunk: break
                    self.wfile.write(chunk); left -= len(chunk)
            except (BrokenPipeError, ConnectionResetError): pass

    def do_POST(self):
        if not self.path.startswith("/api/feedback"): self.send_error(404); return
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            atomic_write(HERE / "feedback.json", json.dumps(data.get("state", {}), indent=1, ensure_ascii=False))
            if isinstance(data.get("markdown"), str): atomic_write(HERE / "feedback.md", data["markdown"])
            body = b'{"ok": true}'; self.send_response(200)
        except Exception as e:
            body = json.dumps({"ok": False, "error": str(e)}).encode(); self.send_response(500)
        self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8765); a = ap.parse_args()
    print(f"scene review: http://localhost:{a.port}/  (serving {ROOT})", flush=True)
    ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()
