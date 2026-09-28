"""Generation pipeline for the video: character refs -> keyframes -> image-to-video -> lip-sync. Idempotent (skips existing files).

usage:
  python video/generate.py refs                 # character reference images (one per character + wardrobe look)
  python video/generate.py keyframes [ids...]   # one still per shot, conditioned on character refs
  python video/generate.py clips [ids...]       # image-to-video per shot
  python video/generate.py lipsync [ids...]     # singing/rapping shots: still + vocal segment -> performance
Endpoints and parameters are set in video/models.json (filled in from the model scout).
"""
import json, os, sys, time, pathlib, subprocess, concurrent.futures as cf
import requests, fal_client

ROOT = pathlib.Path(__file__).resolve().parent
SL = json.load(open(ROOT / "shotlist.json"))
CFG = json.load(open(ROOT / "models.json"))
OUT = ROOT / "gen"; (OUT / "refs").mkdir(parents=True, exist_ok=True)
for sub in ("keyframes", "clips", "lipsync", "receipts"): (OUT / sub).mkdir(exist_ok=True)
SHOTS = {s["id"]: s for s in SL["shots"]}
CH, WD = SL["characters"], SL["wardrobe"]

def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)
def fetch(url, path): pathlib.Path(path).write_bytes(requests.get(url, timeout=600).content); return path
def upload(path, cache={}):
    if path not in cache:
        for k in range(8):
            try: cache[path] = fal_client.upload_file(str(path)); break
            except Exception:
                if k == 7: raise
                time.sleep(15 + 10 * k)
    return cache[path]
def run(endpoint, args, receipt, tries=10):
    t = time.time()
    for k in range(tries):                     # fal sometimes answers "User is locked (TOP_UP)" while a top-up settles
        try:
            res = fal_client.subscribe(endpoint, arguments=args, with_logs=False); break
        except Exception as e:
            msg = str(e)
            if ("locked" in msg or "TOP_UP" in msg or "429" in msg or "timed out" in msg.lower()) and k < tries - 1:
                time.sleep(20 + 15 * k); continue
            raise
    json.dump({"endpoint": endpoint, "args": {k: v for k, v in args.items() if not str(v).startswith("data:")},
               "seconds": round(time.time() - t, 1), "result": res}, open(OUT / "receipts" / f"{receipt}.json", "w"), indent=1)
    return res
def first_url(res, key):
    v = res.get(key)
    if isinstance(v, list): v = v[0]
    return v["url"] if isinstance(v, dict) else v

# ---------------- character references
REFS = {  # id -> prompt (style appended)
    "dario_v1": f"character reference portrait, waist-up, three-quarter view, {CH['dario']}, {WD['dario']['v1']}, standing in a moody neon nightclub",
    "dario_c1": f"character reference portrait, waist-up, three-quarter view, {CH['dario']}, {WD['dario']['c1']}, warm amber nightclub light",
    "dario_c3": f"character reference portrait, waist-up, three-quarter view, {CH['dario']}, {WD['dario']['c3']}, warm gold nightclub light",
    "muse_v1": f"character reference portrait, waist-up, three-quarter view, {CH['muse']}, {WD['muse']['v1']}, moody neon nightclub",
    "muse_v2": f"character reference portrait, waist-up, three-quarter view, {CH['muse']}, {WD['muse']['v2']}, cool silver-blue light",
    "muse_c3": f"character reference portrait, waist-up, three-quarter view, {CH['muse']}, {WD['muse']['c3']}, warm gold light",
    "moloch": f"character reference portrait, {CH['moloch']}",
    "sama": f"character reference portrait, waist-up, {CH['sama']}, nightclub with glossy highlights",
    "don": f"character reference portrait, waist-up, {CH['don']}, gilded dining room",
    "bear": f"character reference, full body, {CH['bear']}, nightclub bar",
    "consultant": f"character reference portrait, {CH['consultant']}, nightclub corner booth",
}
def ref_path(rid): return OUT / "refs" / f"{rid}.png"

def refs(ids=None):
    ep, extra = CFG["t2i"]["endpoint"], CFG["t2i"].get("args", {})
    def one(rid):
        p = ref_path(rid)
        if p.exists(): return f"exists {rid}"
        res = run(ep, {"prompt": f"{REFS[rid]}. {SL['style']}", **extra}, f"ref_{rid}")
        fetch(first_url(res, "images"), p); return f"ok {rid}"
    with cf.ThreadPoolExecutor(6) as ex:
        for r in ex.map(one, ids or list(REFS)): log(r)

def refs_for(shot):
    """Character references for this shot's cast (one look per character, all video long); <id>_b.png is an optional second angle."""
    return [p for c in shot["chars"] for p in (ref_path(c), ref_path(c + "_b")) if p.exists()]

# ---------------- keyframes
def keyframes(ids=None):
    edit, t2i = CFG["edit"], CFG["t2i"]
    def one(sid):
        s = SHOTS[sid]; p = OUT / "keyframes" / f"{sid}.png"
        if p.exists():
            try: return f"exists {sid}" + end_frame(s, refs_for(s))
            except Exception as e: return f"FAIL {sid} end frame: {str(e)[:200]}"
        rs = refs_for(s)
        try:
            if rs:
                args = {"prompt": s["still_prompt"] + " Use the reference images only for the characters' faces, hair and outfits, keeping them consistent and recognizable; compose a new scene exactly as described, with its own background and lighting.",
                        edit["image_key"]: [upload(r) for r in rs], **edit.get("args", {})}
                res = run(edit["endpoint"], args, f"kf_{sid}")
            else:
                res = run(t2i["endpoint"], {"prompt": s["still_prompt"], **t2i.get("args", {})}, f"kf_{sid}")
            fetch(first_url(res, "images"), p); return f"ok {sid} ({len(rs)} refs)" + end_frame(s, rs)
        except Exception as e:
            return f"FAIL {sid}: {str(e)[:200]}"
    def end_frame(s, rs):   # optional last frame for first+last-frame video: same shot, the start frame as scene reference
        pe = OUT / "keyframes" / f"{s['id']}_end.png"
        if not s.get("end_still_prompt") or pe.exists(): return ""
        args = {"prompt": s["end_still_prompt"] + " This is the last frame of the same shot as the final reference image: same location, lighting, camera, "
                          "outfit and painterly style; use the other reference images only for the character's face and hair.",
                edit["image_key"]: [upload(r) for r in rs] + [upload(OUT / "keyframes" / f"{s['id']}.png")], **edit.get("args", {})}
        fetch(first_url(run(edit["endpoint"], args, f"kf_{s['id']}_end"), "images"), pe); return " + end frame"
    with cf.ThreadPoolExecutor(6) as ex:
        for r in ex.map(one, ids or list(SHOTS)): log(r)

# ---------------- image-to-video
def clips(ids=None):
    fb = os.environ.get("FALLBACK")                    # FALLBACK=1 (Kling) or FALLBACK=wan for shots Veo refuses
    i2v = CFG["i2v_wan"] if fb == "wan" else CFG["i2v_fallback"] if fb else CFG["i2v"]
    def one(sid):
        s = SHOTS[sid]; kf = OUT / "keyframes" / f"{sid}.png"; p = OUT / "clips" / f"{sid}.mp4"
        if p.exists(): return f"exists {sid}"
        if not kf.exists(): return f"no keyframe {sid}"
        end = OUT / "keyframes" / f"{sid}_end.png"
        cfg = CFG["i2v_first_last"] if end.exists() and not fb else i2v   # a last frame pins where the shot lands
        slow = " Graceful slow motion." if s["grade"] in ("amber", "gold") else ""
        args = {"prompt": s["motion"] + slow + " Painterly neo-noir graphic-novel animation: keep the hand-painted brushwork, ink lines and lighting of the first frame, same characters, faces and outfits throughout, smooth cinematic camera, no on-screen text changes.",
                cfg["image_key"]: upload(kf), **cfg.get("args", {})}
        if end.exists() and cfg.get("end_key"): args[cfg["end_key"]] = upload(end)
        if "durations" in cfg:               # shortest allowed clip that covers the slot (slow-mo shots may stretch to ~1.4x)
            need = s["dur"] / (1.4 if s["grade"] in ("amber", "gold") else 1.05)
            pick = next((dd for dd in cfg["durations"] if dd >= need), cfg["durations"][-1])
            args["duration"] = cfg["duration_fmt"].format(pick)
        try:
            res = run(cfg["endpoint"], args, f"i2v_{sid}")
            fetch(first_url(res, "video"), p); return f"ok {sid}"
        except Exception as e:
            return f"FAIL {sid}: {str(e)[:200]}"
    with cf.ThreadPoolExecutor(CFG.get("i2v_workers", 6)) as ex:
        for r in ex.map(one, ids or [k for k, v in SHOTS.items() if v["kind"] == "gen"]): log(r)

# ---------------- lip-sync
def lipsync(ids=None):
    ls = CFG["lipsync"]
    voc = ROOT / "audio" / "sep_B" / "vocals.wav"
    def one(sid):
        s = SHOTS[sid]; kf = OUT / "keyframes" / f"{sid}.png"; p = OUT / "lipsync" / f"{sid}.mp4"
        if p.exists(): return f"exists {sid}"
        seg = OUT / "lipsync" / f"{sid}_vocal.wav"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(max(0, s["start"] - 0.1)), "-to", str(s["end"] + 0.1),
                        "-i", str(voc), "-ac", "1", "-ar", "44100", str(seg)], check=True)
        from PIL import Image                               # OmniHuman rejects the 8 MB 2K PNGs: send a 1080p JPEG (and a matching mask)
        small = OUT / "lipsync" / f"{sid}_in.jpg"
        Image.open(kf).convert("RGB").resize((1920, 1080), Image.LANCZOS).save(small, quality=92)
        args = {ls["image_key"]: upload(small), ls["audio_key"]: upload(seg), **ls.get("args", {})}
        mask = OUT / "lipsync" / f"{sid}_mask.png"          # optional: only the person in the white area sings
        if mask.exists():
            msmall = OUT / "lipsync" / f"{sid}_mask_in.png"
            Image.open(mask).convert("L").resize((1920, 1080)).save(msmall); args["mask_url"] = upload(msmall)
        if ls.get("prompt_key"): args[ls["prompt_key"]] = s["motion"] + ", singing expressively with natural mouth shapes, painterly cyberpunk-noir graphic-novel look, same character and outfit"
        try:
            res = run(ls["endpoint"], args, f"ls_{sid}")
            fetch(first_url(res, "video"), p); return f"ok {sid}"
        except Exception as e:
            return f"FAIL {sid}: {str(e)[:200]}"
    with cf.ThreadPoolExecutor(3) as ex:
        for r in ex.map(one, ids or [k for k, v in SHOTS.items() if v["kind"] == "lipsync"]): log(r)

if __name__ == "__main__":
    cmd, ids = sys.argv[1], sys.argv[2:] or None
    {"refs": refs, "keyframes": keyframes, "clips": clips, "lipsync": lipsync}[cmd](ids)
