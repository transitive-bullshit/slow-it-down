"""Lead vs backing vocal activity map per bar (61.5 BPM bars, 8 cells = 8th notes).
L = lead only, B = backing only, X = both, . = neither."""
import json, sys, glob
import numpy as np, librosa

g = json.load(open("analysis/grid.json")); P, T0 = g["beat_period_s"], g["t0_s"]
BAR = 8 * P
files = sorted(glob.glob("audio/stems/karaoke/*.wav"))
lead_f = [f for f in files if "(Vocals)" in f or "(vocals)" in f][0]
back_f = [f for f in files if f != lead_f][0]
sr = 22050
def env(path):
    y, _ = librosa.load(path, sr=sr, mono=True)
    r = librosa.feature.rms(y=y, frame_length=2048, hop_length=256)[0]
    return 20 * np.log10(r + 1e-9)
L, B = env(lead_f), env(back_f)
ref = max(np.percentile(L, 99), np.percentile(B, 99))
t = librosa.frames_to_time(np.arange(len(L)), sr=sr, hop_length=256)
def active(e, a, b, thr):
    m = (t >= a) & (t < b)
    return m.any() and np.percentile(e[m], 75) > ref + thr
sections = json.load(open("analysis/song-map.json"))["sections"]
names = {s["start_bar"]: s["section"] for s in sections}
out = []
nbars = int((t[-1] - T0) / BAR) + 1
for bar in range(nbars):
    cells = ""
    for c in range(8):
        a = T0 + bar * BAR + c * P; b = a + P
        l, bk = active(L, a, b, -24), active(B, a, b, -24)
        cells += "X" if l and bk else "L" if l else "B" if bk else "."
    out.append(cells)
    if bar + 1 in names: print(f"--- {names[bar+1]}")
    print(f"bar {bar+1:2d}  {cells[:4]} {cells[4:]}")
json.dump({"legend": "per bar, 8 cells (8th notes at 61.5 BPM): L lead, B backing, X both, . none",
           "lead_file": lead_f, "backing_file": back_f, "bars": out}, open("analysis/voice-map.json", "w"), indent=1)
