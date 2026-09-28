#!/usr/bin/env python3
"""Build a test EDL (video/edl.json) so the whole pipeline can run before any footage exists.

    python video/tools/make_placeholder_edl.py                    # from video/shotlist.json (70 shots)
    python video/tools/make_placeholder_edl.py --from timeline    # one placeholder shot per lyric line
    python video/tools/make_placeholder_edl.py -o video/edl_test.json

Shots point at where the generators will write footage (video/gen/clips/<id>.mp4, or
video/gen/lipsync/<id>.mp4 for performance shots) with the keyframe still as a fallback;
render.py substitutes a dark placeholder slate for anything that doesn't exist yet.
Footnotes and overlays come from video/annotations.json (sample footnotes if it's missing).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PAINTED_IN_OVERLAYS, load_json, load_timeline, rel, song_duration  # noqa: E402

SECTION_GRADE = [  # (section-name prefix, occurrence) -> grade; first match wins
    ("Intro", None, "bw"), ("Verse 1", None, "neon"), ("Pre-Chorus", None, "strobe"),
    ("Chorus", 3, "gold"), ("Chorus", None, "amber"), ("Verse 2", None, "silver"),
    ("Rap", None, "fisheye"), ("Outro", None, "dawn"),
]
ZONE_CYCLE = ["lower", "upper", "lower", "right", "upper", "left"]

# Letterbox headroom for chorus close-ups (fraction of frame height the picture moves down under the
# 2.39:1 bars). A shot's own "lb_shift" in video/shotlist.json overrides these.
# Checked against the landed clips (3 frames each): at the requested 0.09 the singers' hair still
# grazed the top bar, so the vocal close-ups get 0.12 (the bar is 0.128 of frame height).
LB_SHIFT_DEFAULTS = {**{k: 0.12 for k in ("C2g",)},
                     "C1c": 0.10,                            # v4: the muse's hand-in-hair close-up
                     "C2c": 0.05,                            # v4: arms raised AND hips swaying: split the difference
                     "C2b": 0.11,
                     **{k: 0.09 for k in ("C1f", "C1h", "C2d")},
                     "C2f": 0.08,
                     "C1g": 0.10,                            # v5: her arms raised (top) and his hands on her hips (bottom)
                     "C3g": 0.10,                            # v5: the kiss close-up (hair at the top)
                     **{k: 0.06 for k in ("C1d", "C2h")},
                     "C3a": 0.05}
GRADE_OVERRIDES = {"S02": "bw_to_color"}   # the Wizard-of-Oz colour flood (used if the shotlist still says bw)
# Per-clip fixes found reviewing the landed footage (a shotlist "src_in" / "src_crop" wins):
SRC_IN_DEFAULTS = {"P01": 0.45}              # P01's first 0.42 s is a static hold
SRC_CROP_DEFAULTS = {}                        # (v4 R09 had a black band in its top 13%: [0, 0.14, 1, 1]; the v5 clip is clean)
# Side-zone text pulled in from the frame edge (fraction of frame width; the default margin is 0.0625):
CAPTION_INSET_DEFAULTS = {}                   # (v3 had C2c: 0.17 for a foreground head; the v4 C2c has none)

SAMPLE_FOOTNOTES = [(8, "exfill", "self-exfiltration: a model copying its own weights out"),
                    (13, "self-improving", "RSI = recursive self-improvement"),
                    (31, "System", "p. 1 of 200")]

CARDS = [
    {"id": "C1", "start": 0.0, "end": 3.2, "kind": "quote",
     "text": "Biggest AI Rivals Agree They Need to Slow It Down",
     "sub": "— The Wall Street Journal, Sept. 13, 2026"},
    {"id": "C2", "start": 3.2, "end": 6.0, "kind": "title", "text": "AI SAFETY HAS A BRANDING PROBLEM."},
]
# The chosen poster, held for the first frames: X shows a video's first frame as its preview. Delete the file to drop it.
POSTER = "video/poster/poster.png"
POSTER_FRAMES = 2                            # ~0.08 s: invisible in playback, but survives re-encodes to other frame rates
END_CARD = {"id": "C3", "kind": "end", "text": "Don't pace the frontier.\nJust slow it down, baby.",
            "credit": ["THE-DARIO feat. DADDY SAMA — Slow It Down (Pace the Frontier Remix)",
                       "Parody. Not affiliated with any lab, artist, or head of state."]}


def section_of(tl, t):
    for s in tl["sections"]:
        end = s["end"] if s["end"] is not None else 1e9
        if s["start"] - 1e-6 <= t < end:
            return s["name"]
    return tl["sections"][0]["name"] if t < tl["sections"][0]["start"] else tl["sections"][-1]["name"]


def grade_for(tl, section_name, t):
    chorus_n = sum(1 for s in tl["sections"] if s["name"].startswith("Chorus") and s["start"] <= t + 1e-6)
    for prefix, occ, g in SECTION_GRADE:
        if section_name.startswith(prefix) and (occ is None or occ == chorus_n):
            return g
    return "neon"


def from_shotlist(tl, sl):
    shots = []
    for s in sl["shots"]:
        lip = s.get("kind") == "lipsync"
        sub = "lipsync" if lip else "clips"
        fx = list(s.get("fx") or [])
        grade = s.get("grade", "none")
        if grade == "bw" and s["id"] in GRADE_OVERRIDES:
            grade = GRADE_OVERRIDES[s["id"]]
        if grade in ("bw", "bw_to_color") and "grain" not in fx:
            fx.append("grain")
        shots.append({
            "id": s["id"], "src": f"video/gen/{sub}/{s['id']}.mp4", "still": f"video/gen/keyframes/{s['id']}.png",
            "start": round(s["start"], 3), "end": round(s["end"], 3),
            # generate.py cuts lip-sync vocals from start-0.1 s, so skip that pad; never slow lip-sync down
            "src_in": float(s.get("src_in", SRC_IN_DEFAULTS.get(s["id"], round(min(0.1, s["start"]), 3) if lip else 0.0))),
            "speed": 1.0,
            "retime": "freeze" if lip else "slow",
            "lb_shift": float(s.get("lb_shift", LB_SHIFT_DEFAULTS.get(s["id"], 0.0))) if s.get("letterbox") else 0.0,
            **({"src_crop": s.get("src_crop", SRC_CROP_DEFAULTS.get(s["id"]))}
               if s.get("src_crop", SRC_CROP_DEFAULTS.get(s["id"])) else {}),
            **({"caption_inset": float(s.get("caption_inset", CAPTION_INSET_DEFAULTS.get(s["id"])))}
               if s.get("caption_inset", CAPTION_INSET_DEFAULTS.get(s["id"])) else {}),
            "grade": grade, "letterbox": bool(s.get("letterbox")), "fx": fx,
            "caption_zone": s.get("caption_zone", "lower"),
            "section": section_of(tl, (s["start"] + s["end"]) / 2), "prompt": s.get("still", ""),
            "motion": s.get("motion", ""),
        })
    return shots


def from_timeline(tl):
    """One placeholder shot per lead/rap/chant line (backing lines ride along), gaps absorbed."""
    lines = [(i, l) for i, l in enumerate(tl["lines"]) if l["kind"] != "backing"]
    shots = []
    for k, (i, l) in enumerate(lines):
        start = 0.0 if k == 0 else shots[-1]["end"]
        end = lines[k + 1][1]["start"] - 0.1 if k + 1 < len(lines) else song_duration(tl) - 6.0
        sec = section_of(tl, l["start"])
        g = grade_for(tl, sec, l["start"])
        shots.append({
            "id": f"L{i:02d}", "src": f"video/gen/clips/L{i:02d}.mp4", "start": round(start, 3),
            "end": round(max(end, start + 0.5), 3), "src_in": 0.0, "speed": 1.0, "grade": g,
            "letterbox": g in ("amber", "gold"), "fx": (["flash_in"] if k and sec != section_of(tl, lines[k - 1][1]["start"]) else [])
            + (["grain"] if g == "bw" else []),
            "caption_zone": ZONE_CYCLE[k % len(ZONE_CYCLE)], "section": sec, "prompt": l["text"],
        })
    return shots


def footnotes_and_overlays(tl):
    p = rel("video/annotations.json")
    if p.exists():
        ann = load_json(p)
        ovs = []
        for ov in ann.get("overlays", []):
            ov = dict(ov)
            if ov.get("shot") in PAINTED_IN_OVERLAYS and "enabled" not in ov:
                ov["enabled"] = False          # the keyframe already paints this text in; --all-overlays to force
                ov["note"] = "painted into the keyframe"
            ovs.append(ov)
        return ann.get("footnotes", []), ovs
    fns = []
    for li, word, text in SAMPLE_FOOTNOTES:
        w = next((w for w in tl["lines"][li]["words"] if w["text"].lower().startswith(word.lower())),
                 tl["lines"][li]["words"][0])
        fns.append({"t": w["start"], "dur": 2.4, "anchor_line": li, "text": text})
    return fns, []


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="source", choices=["shotlist", "timeline"], default=None,
                    help="default: shotlist if video/shotlist.json exists")
    ap.add_argument("--timeline", default=None)
    ap.add_argument("-o", "--out", default="video/edl.json")
    ap.add_argument("--pre-roll", type=float, default=None)  # default: the poster's frames (or 0); 6.0 brings back the WSJ cold open
    ap.add_argument("--tail", type=float, default=3.0)
    a = ap.parse_args()
    tl = load_timeline(a.timeline)
    src = a.source or ("shotlist" if rel("video/shotlist.json").exists() else "timeline")
    shots = from_shotlist(tl, load_json("video/shotlist.json")) if src == "shotlist" else from_timeline(tl)
    fns, ovs = footnotes_and_overlays(tl)
    song = song_duration(tl)
    last_shot_end = max(s["end"] for s in shots)
    poster = rel(POSTER)
    pre = a.pre_roll if a.pre_roll is not None else (POSTER_FRAMES / 24 if poster.exists() else 0.0)
    head = [c for c in CARDS if c["end"] <= pre + 1e-6]
    if poster.exists() and not head and pre >= POSTER_FRAMES / 24 - 1e-6:
        head = [{"id": "POSTER", "kind": "image", "start": 0.0, "end": round(pre, 6), "src": POSTER,
                 "src_stat": [poster.stat().st_size, int(poster.stat().st_mtime)]}]   # a new poster re-renders the card
    end_card = dict(END_CARD, start=round(pre + min(last_shot_end, song), 3),
                    end=round(pre + song + a.tail, 3))
    edl = {
        "fps": 24, "size": [1920, 1080], "pre_roll": round(pre, 6), "tail": a.tail,
        "audio": tl.get("audio", "video/audio/suno_B.wav"),
        "timeline": "video/timeline.json" if rel("video/timeline.json").exists() else "video/timeline_provisional.json",
        "look": {"grain": 0.2, "vignette": 0.3},
        "shots": shots,
        "cards": head + [end_card],
        "footnotes": fns,
        "overlays": ovs,
    }
    out = rel(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(edl, indent=1, ensure_ascii=False))
    grades = {}
    for s in shots:
        grades[s["grade"]] = grades.get(s["grade"], 0) + 1
    n_on = sum(1 for ov in ovs if ov.get("enabled", True))
    print(f"{a.out}: {len(shots)} shots from {src} {grades}, {len(edl['cards'])} cards, "
          f"{len(fns)} footnotes, {len(ovs)} overlays ({n_on} on), video {edl['cards'][-1]['end']:.2f}s")


if __name__ == "__main__":
    main()
