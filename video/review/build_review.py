"""Build the scene review tool's assets from the latest cut: per-scene final-cut clips, posters and data.js.

usage: python video/review/build_review.py [--cut video/build/full_v3.mp4] [--only S01,C1f] [--force]
Re-run after regenerating shots and re-rendering; only scenes whose sources changed are rebuilt (unless --force).
Outputs (all under video/review/): posters/<id>.jpg (keyframe), frames/<id>.jpg (a frame of the final cut),
cut/<id>.mp4 (the scene as it plays in the video, with audio), data.js.
"""
import argparse, ast, concurrent.futures as cf, json, os, pathlib, subprocess, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
REV = ROOT / "video" / "review"
ap = argparse.ArgumentParser()
ap.add_argument("--cut", default="video/build/full_v5.mp4")
ap.add_argument("--share", default="video/build/slow_it_down_share_v5.mp4")
ap.add_argument("--only", default="")
ap.add_argument("--force", action="store_true")
args = ap.parse_args()
CUT, SHARE = ROOT / args.cut, ROOT / args.share
ONLY = {s for s in args.only.split(",") if s}

SL = json.load(open(ROOT / "video/shotlist.json"))
TL = json.load(open(ROOT / "video/timeline.json"))
EDL = json.load(open(ROOT / "video/edl.json"))
PRE = EDL["pre_roll"]
for sub in ("posters", "frames", "cut"): (REV / sub).mkdir(parents=True, exist_ok=True)

# ---- readable prompts: swap the long character descriptions for names (constants parsed from shots.py, not executed)
consts = {}
for node in ast.parse((ROOT / "video/shots.py").read_text()).body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Constant):
        consts[node.targets[0].id] = node.value.value
NAMES = [(f"{consts['DARIO']}, {consts['ONE_OUTFIT']}", "THE-DARIO"), (f"{consts['MUSE']}, in a deep red satin slip dress", "the muse"),
         (consts["DARIO"], "THE-DARIO"), (consts["MUSE"], "the muse"), (consts["MOLOCH"], "DJ Moloch"), (consts["SAMA"], "DADDY SAMA"),
         (consts["DON"], "the Don"), (consts["BEAR"], "the honey bear"), (consts["CONSULTANT"], "the consultant"),
         (consts["EACC"], "the e/acc hype man"), (consts["CLUB"], "Club Frontier")]
def readable(text):
    for long, short in NAMES: text = text.replace(long, short)
    return text

# ---- sections, numbered in order ("Chorus 1", "Chorus 2", ...)
bases = [s["name"].split(" - ")[0] for s in TL["sections"]]
secs, seen = [], {}
for s, base in zip(TL["sections"], bases):
    seen[base] = seen.get(base, 0) + 1
    name = f"{base} {seen[base]}" if bases.count(base) > 1 else base
    secs.append({"name": name, "start": s["start"], "end": s["end"] or TL["duration"]})
def section_of(t):   # shots start on the beat up to ~0.4 s before their lyric line
    for s in secs:
        if s["start"] <= t + 0.45 < s["end"]: return s["name"]
    return secs[0]["name"] if t < secs[0]["start"] else secs[-1]["name"]

def lyrics_in(a, b):
    out = []
    for l in TL["lines"]:
        if "start" not in l: continue
        ov = min(b, l["end"]) - max(a, l["start"])
        if ov > 0.25 or (l["start"] >= a and l["start"] < b):
            out.append({"kind": l["kind"], "text": l["text"], "start": round(l["start"], 2), "end": round(l["end"], 2)})
    return out

GEN = {"S06": "Wan 2.2 (Veo and Kling refused the Trump frame)", "R05": "Wan 2.2 first + last frame, static-silhouette composite (Veo refused)",
       **{k: "Veo 3.1 Fast, first + last frame" for k in ("S02", "S04", "C3g")}}
items = []
# ---- poster / first-frame options (video/poster/options/<id>.png): chosen with Keep, then spliced in as the first frame
POSTER_TITLES = {"A": "The glance back", "B": "Shh", "C": "The doorway", "D": "The booth", "E": "Hand on the fader", "F": "The spotlight"}
for png in sorted((ROOT / "video/poster/options").glob("[A-Z]_*.png")):
    letter = png.stem.split("_")[0]
    items.append({"id": f"POSTER-{letter}", "type": "poster", "section": "Poster · first frame", "vstart": 0.0, "vend": 0.0, "start": 0.0, "end": 0.0,
                  "title": POSTER_TITLES.get(letter, png.stem), "src": str(png.relative_to(ROOT)),
                  "desc": "Candidate first frame (the preview X shows) and YouTube thumbnail. Mark your pick with Keep; notes welcome."})
if any(c["start"] < PRE and c.get("kind") in ("quote", "title") for c in EDL["cards"]): items.append({"id": "OPEN", "type": "card", "section": "Cold open", "vstart": 0.0, "vend": PRE, "start": -PRE, "end": 0.0,
              "title": "Cold open cards", "desc": " / ".join(c["text"] for c in EDL["cards"] if c["start"] < PRE and c.get("text")),
              "detail": "; ".join(f"{c['kind']}: {c['text']}" + (f" ({c['sub']})" if c.get("sub") else "") for c in EDL["cards"] if c["start"] < PRE and c.get("text"))})
for s in SL["shots"]:
    kind = s["kind"]
    raw = f"video/gen/{'lipsync' if kind == 'lipsync' else 'clips'}/{s['id']}.mp4"
    items.append({
        "id": s["id"], "type": "shot", "section": section_of(s["start"]),
        "start": s["start"], "end": s["end"], "dur": round(s["end"] - s["start"], 2), "vstart": round(s["start"] + PRE, 3), "vend": round(s["end"] + PRE, 3),
        "grade": s["grade"], "zone": s["caption_zone"], "letterbox": s.get("letterbox", False), "chars": s["chars"],
        "gen": GEN.get(s["id"], "OmniHuman 1.5 lip-sync" + (f" ({s['lipsync_voice']})" if s.get("lipsync_voice") else "") if kind == "lipsync" else "Veo 3.1 Fast"),
        "still": readable(s["still"]), "motion": s["motion"], "notes": s.get("notes", ""),
        "lyrics": lyrics_in(s["start"], s["end"]),
        "keyframe": f"video/gen/keyframes/{s['id']}.png", "raw": raw if (ROOT / raw).exists() else None,
        "keyframe_end": f"video/gen/keyframes/{s['id']}_end.png" if (ROOT / f"video/gen/keyframes/{s['id']}_end.png").exists() else None,
    })
endc = [c for c in EDL["cards"] if c["start"] >= PRE]
if endc:
    c = endc[0]
    items.append({"id": "END", "type": "card", "section": "End card", "vstart": c["start"], "vend": c["end"], "start": c["start"] - PRE, "end": c["end"] - PRE,
                  "title": "End card", "desc": c["text"].replace("\n", " "), "detail": " / ".join([c["text"].replace("\n", " ")] + c.get("credit", []))})

# ---- media: scene cut from the master (720p, with audio), a frame of it, and the keyframe poster
def run(cmd): subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
def fresh(out, *srcs): return out.exists() and not args.force and all(out.stat().st_mtime >= pathlib.Path(p).stat().st_mtime for p in srcs if pathlib.Path(p).exists())
def build(it):
    i = it["id"]
    if ONLY and i not in ONLY: return f"skip {i}"
    cut, frame, poster = REV / "cut" / f"{i}.mp4", REV / "frames" / f"{i}.jpg", REV / "posters" / f"{i}.jpg"
    if it["type"] == "poster":            # full image + a true feed-size copy (roughly how big X shows it in the timeline)
        src = ROOT / it["src"]
        if not fresh(poster, src): run(["ffmpeg", "-y", "-i", str(src), "-vf", "scale=960:-2:flags=lanczos", "-q:v", "3", str(poster)])
        if not fresh(frame, src): run(["ffmpeg", "-y", "-i", str(src), "-vf", "scale=400:-2:flags=lanczos", "-q:v", "3", str(frame)])
        return f"ok {i}"
    a, d = it["vstart"], it["vend"] - it["vstart"]
    if not fresh(cut, CUT):
        run(["ffmpeg", "-y", "-ss", f"{a:.3f}", "-i", str(CUT), "-t", f"{d:.3f}", "-vf", "scale=1280:720:flags=lanczos", "-c:v", "libx264",
             "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(cut)])
    if not fresh(frame, cut):   # a frame where the caption is lit: 65% through the scene
        run(["ffmpeg", "-y", "-ss", f"{d * 0.65:.3f}", "-i", str(cut), "-frames:v", "1", "-vf", "scale=960:-2", "-q:v", "3", str(frame)])
    if it.get("keyframe_end"):
        pe = REV / "posters" / f"{i}_end.jpg"; kfe = ROOT / it["keyframe_end"]
        if not fresh(pe, kfe): run(["ffmpeg", "-y", "-i", str(kfe), "-vf", "scale=960:-2:flags=lanczos", "-q:v", "3", str(pe)])
    kf = ROOT / it.get("keyframe", "")
    if it["type"] == "shot" and kf.exists():
        if not fresh(poster, kf): run(["ffmpeg", "-y", "-i", str(kf), "-vf", "scale=960:-2:flags=lanczos", "-q:v", "3", str(poster)])
    elif not fresh(poster, frame): run(["cp", str(frame), str(poster)])
    return f"ok {i}"
t0 = time.time()
with cf.ThreadPoolExecutor(4) as ex:
    res = list(ex.map(build, items))
print(sum(r.startswith("ok") for r in res), "scenes built in", round(time.time() - t0), "s")

for it in items:
    it["poster"] = f"posters/{it['id']}.jpg"; it["frame"] = f"frames/{it['id']}.jpg"; it["cut"] = f"cut/{it['id']}.mp4"
    if it.get("keyframe_end"): it["poster_end"] = f"posters/{it['id']}_end.jpg"
sections = []
for it in items:
    if not sections or sections[-1]["name"] != it["section"]:
        sections.append({"name": it["section"], "vstart": it["vstart"], "items": []})
    sections[-1]["items"].append(it["id"]); sections[-1]["vend"] = it["vend"]
CHG = json.load(open(REV / "changes.json")) if (REV / "changes.json").exists() else {}
for it in items:
    if it["id"] in CHG.get("items", {}) and CHG.get("version") == pathlib.Path(args.cut).stem: it["changed"] = CHG["items"][it["id"]]
meta = {"cut": args.cut, "share": args.share, "built": time.strftime("%Y-%m-%d %H:%M"), "duration": round(EDL["pre_roll"] + TL["duration"] + EDL.get("tail", 0), 2),
        "pre_roll": PRE, "version": pathlib.Path(args.cut).stem,
        "changes_note": CHG.get("note", "") if CHG.get("version") == pathlib.Path(args.cut).stem else ""}
(REV / "data.js").write_text("window.REVIEW = " + json.dumps({"meta": meta, "sections": sections, "items": items}, ensure_ascii=False, indent=1) + ";\n")
print("data.js:", len(items), "items in", len(sections), "sections")
