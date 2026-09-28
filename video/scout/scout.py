"""fal.ai scouting harness: run one endpoint call, save its outputs, and log cost + latency to ledger.jsonl.

usage (from the project root, with FAL_KEY exported via `set -a; . ~/.env; set +a`):
  .venv/bin/python video/scout/scout.py <name> <endpoint_id> <est_cost_usd> '<json args>'

In the JSON args, any string of the form "@file:<path>" is uploaded to fal storage (cached in uploads.json) and replaced
by its URL. Outputs land in video/scout/<subdir of name>, e.g. name "i2v/kling_v3_singer" -> video/scout/i2v/kling_v3_singer.mp4.
A hard budget cap (CAP) is enforced on the sum of est_cost over successful calls in the ledger.
"""
import json, sys, time, pathlib, threading, mimetypes
import requests, fal_client

ROOT = pathlib.Path(__file__).resolve().parent
LEDGER = ROOT / "ledger.jsonl"
UPLOADS = ROOT / "uploads.json"
CAP = 14.0
_lock = threading.Lock()


def spent():
    tot = 0.0
    if LEDGER.exists():
        for line in LEDGER.open():
            r = json.loads(line)
            if r.get("ok"):
                tot += r.get("est_cost", 0)
    return tot


def upload(path):
    path = str(pathlib.Path(path).resolve())
    with _lock:
        cache = json.loads(UPLOADS.read_text()) if UPLOADS.exists() else {}
    if path in cache:
        return cache[path]
    url = fal_client.upload_file(path)
    with _lock:
        cache = json.loads(UPLOADS.read_text()) if UPLOADS.exists() else {}
        cache[path] = url
        UPLOADS.write_text(json.dumps(cache, indent=1))
    return url


def resolve(obj):
    if isinstance(obj, str) and obj.startswith("@file:"):
        return upload(obj[6:])
    if isinstance(obj, list):
        return [resolve(x) for x in obj]
    if isinstance(obj, dict):
        return {k: resolve(v) for k, v in obj.items()}
    return obj


def media_urls(res):
    """Yield (key_path, url, content_type) for every file-like object in a result."""
    if isinstance(res, dict):
        if isinstance(res.get("url"), str) and res["url"].startswith("http"):
            yield "", res["url"], res.get("content_type") or ""
            return
        for k, v in res.items():
            for kp, u, ct in media_urls(v):
                yield (k + ("." + kp if kp else "")), u, ct
    elif isinstance(res, list):
        for i, v in enumerate(res):
            for kp, u, ct in media_urls(v):
                yield (f"{i}" + ("." + kp if kp else "")), u, ct


def ext_for(url, ct):
    tail = url.split("?")[0].rsplit(".", 1)
    if len(tail) == 2 and len(tail[1]) <= 4:
        return tail[1]
    return (mimetypes.guess_extension(ct or "") or ".bin").lstrip(".")


def run(name, endpoint, args, est_cost):
    if spent() + est_cost > CAP:
        raise SystemExit(f"budget cap: spent {spent():.2f} + {est_cost:.2f} > {CAP}")
    args = resolve(args)
    t0 = time.time()
    marks = {}

    def on_enqueue(rid):
        marks["request_id"] = rid

    def on_update(st):
        if isinstance(st, fal_client.InProgress) and "start" not in marks:
            marks["start"] = time.time()

    ok, err, res = True, None, None
    try:
        res = fal_client.subscribe(endpoint, arguments=args, on_enqueue=on_enqueue, on_queue_update=on_update,
                                   client_timeout=2400)
    except Exception as e:  # moderation / validation / provider errors
        ok, err = False, f"{type(e).__name__}: {e}"[:3000]
    t1 = time.time()
    files = []
    if res:
        outs = list(media_urls(res))
        for i, (kp, url, ct) in enumerate(outs):
            if not any(s in kp for s in ("image", "video", "audio", "images", "file")) and len(outs) > 1:
                pass
            suffix = "" if len(outs) == 1 else f"_{kp.replace('.', '_') or i}"
            p = ROOT / f"{name}{suffix}.{ext_for(url, ct)}"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(requests.get(url, timeout=600).content)
            files.append(str(p.relative_to(ROOT)))
    rec = {
        "name": name, "endpoint": endpoint, "args": args, "est_cost": est_cost if ok else 0.0, "ok": ok, "error": err,
        "latency_s": round(t1 - t0, 1),
        "queue_s": round(marks["start"] - t0, 1) if "start" in marks else None,
        "request_id": marks.get("request_id"), "files": files,
        "result": {k: v for k, v in (res or {}).items() if k not in ("video", "image", "images", "audio")},
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with _lock, LEDGER.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    status = "OK " if ok else "ERR"
    print(f"{status} {name} [{endpoint}] {rec['latency_s']}s est ${est_cost:.3f} files={files} {err or ''}"[:1500],
          flush=True)
    return rec


if __name__ == "__main__":
    name, endpoint, cost, args = sys.argv[1], sys.argv[2], float(sys.argv[3]), json.loads(sys.argv[4])
    run(name, endpoint, args, cost)
