"""Align our script (docs/lyrics-suno.txt) to a Whisper word transcript of the Suno track -> video/timeline.json.

Global (Needleman-Wunsch) alignment on normalized words, so repeated choruses stay in order. Each script word gets the
time of the transcript word it aligned to; unmatched words are interpolated between matched neighbours. Lines, sections,
and a beat grid (beat_this) are written out for the storyboard, the captions and the edit.

usage: python scripts/align_lyrics.py <whisper.json> <audio.wav> [out=video/timeline.json]
"""
import json, re, sys
import numpy as np
from difflib import SequenceMatcher

wjson, audio = sys.argv[1], sys.argv[2]
out = sys.argv[3] if len(sys.argv) > 3 else "video/timeline.json"

def norm(w):
    w = w.lower().replace("sloow", "slow").replace("slooow", "slow").replace("ohhh", "oh")
    return re.sub(r"[^a-z0-9']", "", w)

# ---- script: sections -> lines -> words (ad-libs in parentheses are kept as their own lines, flagged)
sections, lines = [], []
cur = None
for raw in open("docs/lyrics-suno.txt"):
    raw = raw.rstrip("\n")
    if raw.startswith("["):
        name = raw.strip("[]")
        if name == "End": continue
        sections.append({"name": name, "lines": []}); cur = sections[-1]; continue
    if not raw.strip() or cur is None: continue
    main = re.sub(r"\([^)]*\)", "", raw).strip()
    adlibs = re.findall(r"\(([^)]*)\)", raw)
    if main:
        kind = "rap" if cur["name"].startswith("Rap") else "lead"
        lines.append({"section": len(sections) - 1, "text": main, "kind": kind, "adlib": adlibs[0] if adlibs else None})
        cur["lines"].append(len(lines) - 1)
    elif adlibs:
        kind = "chant" if cur["name"] == "Intro" else "backing"
        lines.append({"section": len(sections) - 1, "text": adlibs[0], "kind": kind, "adlib": None})
        cur["lines"].append(len(lines) - 1)

toks = []   # (line index, word as written)
for i, l in enumerate(lines):
    for w in l["text"].replace("—", " ").split():
        if norm(w): toks.append((i, w))

# ---- transcript words
W = json.load(open(wjson))
segs = W["segments"] if isinstance(W, dict) else W
heard = [(norm(x["word"]), x["start"], x["end"]) for s in segs for x in s.get("words", []) if norm(x["word"])]

# ---- words the singer pronounces one way but the captions spell another
DISPLAY = {"Meter": "METR"}

# ---- global alignment
A = [norm(w) for _, w in toks]; B = [h[0] for h in heard]
n, m = len(A), len(B)
sim = lambda a, b: 1.0 if a == b else (0.6 if SequenceMatcher(None, a, b).ratio() >= 0.75 else -0.6)
GAP = -0.4
S = np.zeros((n + 1, m + 1)); T = np.zeros((n + 1, m + 1), dtype=np.int8)   # 0 diag, 1 up (skip script), 2 left (skip heard)
S[1:, 0] = GAP * np.arange(1, n + 1); T[1:, 0] = 1
S[0, 1:] = GAP * np.arange(1, m + 1); T[0, 1:] = 2
for i in range(1, n + 1):
    ai = A[i - 1]
    for j in range(1, m + 1):
        d = S[i - 1, j - 1] + sim(ai, B[j - 1]); u = S[i - 1, j] + GAP; l = S[i, j - 1] + GAP
        if d >= u and d >= l: S[i, j], T[i, j] = d, 0
        elif u >= l: S[i, j], T[i, j] = u, 1
        else: S[i, j], T[i, j] = l, 2
match = [None] * n
i, j = n, m
while i > 0 and j > 0:
    t = T[i, j]
    if t == 0:
        if sim(A[i - 1], B[j - 1]) > 0: match[i - 1] = j - 1
        i, j = i - 1, j - 1
    elif t == 1: i -= 1
    else: j -= 1

# ---- times per script word (interpolate gaps)
starts = np.array([heard[k][1] if k is not None else np.nan for k in match], float)
ends = np.array([heard[k][2] if k is not None else np.nan for k in match], float)
idx = np.arange(n); ok = ~np.isnan(starts)
starts[~ok] = np.interp(idx[~ok], idx[ok], starts[ok]); ends[~ok] = np.interp(idx[~ok], idx[ok], ends[ok])
ends = np.maximum(ends, starts + 0.08)

for li, l in enumerate(lines):
    for say, show in DISPLAY.items(): l["text"] = re.sub(rf"\b{say}\b", show, l["text"])
    ks = [k for k, (ln, _) in enumerate(toks) if ln == li]
    if ks:
        l["start"], l["end"] = round(float(starts[ks[0]]), 3), round(float(ends[ks[-1]]), 3)
        l["words"] = [{"text": toks[k][1], "start": round(float(starts[k]), 3), "end": round(float(ends[k]), 3), "matched": match[k] is not None} for k in ks]
        for w in l["words"]:
            core = w["text"].strip(",.!?")
            if core in DISPLAY: w["text"] = w["text"].replace(core, DISPLAY[core])
        l["matched_frac"] = round(sum(match[k] is not None for k in ks) / len(ks), 2)
# backing "down, down, down" lines that the transcript couldn't pin: spread them evenly across their gap
i = 0
while i < len(lines):
    if lines[i]["kind"] == "backing":
        j = i
        while j < len(lines) and lines[j]["kind"] == "backing": j += 1
        group = lines[i:j]
        weak = any(g.get("matched_frac", 0) < 0.5 or g["end"] - g["start"] < 0.7 for g in group)
        if weak and i > 0 and j < len(lines):
            a = lines[i - 1]["end"]; b = lines[j]["start"]
            if b - a > 0.8:
                step = (b - a) / len(group)
                for k, g in enumerate(group):
                    g0, g1 = a + k * step, a + (k + 1) * step - 0.05
                    n_w = len(g["words"]); ws = (g1 - g0) / max(1, n_w)
                    g["start"], g["end"] = round(g0, 3), round(g1, 3)
                    for q, w in enumerate(g["words"]): w["start"], w["end"] = round(g0 + q * ws, 3), round(g0 + (q + 1) * ws - 0.03, 3)
                    g["respread"] = True
        i = j
    else:
        i += 1
for si, s in enumerate(sections):
    ls = [lines[i] for i in s["lines"] if "start" in lines[i]]
    s["start"] = min(l["start"] for l in ls) if ls else None
for si, s in enumerate(sections):
    nxt = [t["start"] for t in sections[si + 1:] if t["start"] is not None]
    s["end"] = nxt[0] if nxt else None

# ---- beat grid
from beat_this.inference import File2Beats
beats, downs = File2Beats(checkpoint_path="final0", device="mps", dbn=False)(audio)
beats = np.asarray(beats); P, t0 = float(np.median(np.diff(beats))), float(beats[0])
for _ in range(6):
    k = np.round((beats - t0) / P); mk = np.abs(beats - (t0 + k * P)) < 0.06
    (t0, P), *_ = np.linalg.lstsq(np.vstack([np.ones(mk.sum()), k[mk]]).T, beats[mk], rcond=None)
import soundfile as sf
dur = sf.info(audio).duration
tl = {"audio": audio, "duration": round(dur, 3), "beat_period": round(float(P), 5), "bpm": round(60 / float(P), 2),
      "beat_t0": round(float(t0), 4), "beats": [round(float(b), 3) for b in beats], "downbeats": [round(float(d), 3) for d in downs],
      "sections": [{"name": s["name"], "start": s["start"], "end": s["end"], "lines": s["lines"]} for s in sections], "lines": lines}
json.dump(tl, open(out, "w"), indent=1)
print(f"{len(lines)} lines, {sum(x is not None for x in match)}/{n} script words matched; {tl['bpm']} BPM grid (t0 {t0:.3f}s), {dur:.1f}s")
for s in sections:
    print(f"  {s['name']:34s} {s['start']:7.2f} -> {s['end'] if s['end'] else dur:7.2f}")
