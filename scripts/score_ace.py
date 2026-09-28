"""Score whole-mix edit takes: parody-word match per changed line, similarity to the original mix, worst 2 s window."""
import json, glob, re, sys, numpy as np, librosa, mlx_whisper
from difflib import SequenceMatcher
A, B = 46.3, 94.2
pattern = sys.argv[1]
spec = json.load(open("prototypes/spec.json"))
slots = sorted([l for sec in spec["excerpts"]["E1_verse_prehook_hook"]["sections"] for l in sec["lines"]], key=lambda l: l[0])
par = [l for l in slots if A <= l[0] < B and l[2] == "lead" and "REFRAIN" not in l[3]]
norm = lambda s: re.sub(r"[^a-z' ]+", " ", s.lower().replace("—", " ")).split()
src, sr = librosa.load("prototypes/raw/ace_edit/chorus_src.wav", sr=22050, mono=True)
M = lambda y: librosa.power_to_db(librosa.feature.melspectrogram(y=y, sr=sr, n_mels=64, hop_length=512)); Ms = M(src); fps = sr / 512
rows = []
for f in sorted(glob.glob(pattern)):
    y, _ = librosa.load(f, sr=sr, mono=True); Mo = M(y); n = min(Ms.shape[1], Mo.shape[1])
    sec = np.array([np.corrcoef(Ms[:, int(i*fps):int((i+1)*fps)].ravel(), Mo[:, int(i*fps):int((i+1)*fps)].ravel())[0, 1] for i in range(int(n/fps))])
    worst2 = min(np.mean(sec[i:i+2]) for i in range(len(sec) - 1))
    res = mlx_whisper.transcribe(f, path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language="en", word_timestamps=True, condition_on_previous_text=False)
    words = [(A + w["start"], norm(w["word"])) for s in res["segments"] for w in s.get("words", [])]; words = [(t, w[0]) for t, w in words if w]
    sc = []
    for l in par:
        nxt = min([s[0] for s in slots if s[0] > l[0] + 0.1] + [B]); heard = [w for t, w in words if l[0] - 0.6 <= t < nxt]
        sc.append(SequenceMatcher(None, norm(l[1]), heard).ratio())
    rows.append({"take": f.split("/")[-1], "new_words": float(np.mean(sc)), "similarity": float(sec.mean()), "worst2s": float(worst2),
                 "downs": sum(1 for t, w in words if w == "down"), "per_line": [round(x, 2) for x in sc]})
rows.sort(key=lambda r: -(r["new_words"] + 0.5 * r["worst2s"]))
print(f"{'take':26s} {'new-words':>9s} {'similar':>7s} {'worst2s':>7s} {'downs':>5s}  per-line (P1..P6 | A1..A4)")
for r in rows:
    pl = r["per_line"]; print(f"{r['take']:26s} {r['new_words']:9.2f} {r['similarity']:7.2f} {r['worst2s']:7.2f} {r['downs']:5d}  {pl[:6]} | {pl[6:]}")
json.dump(rows, open(f"prototypes/raw/ace_edit/scores_{pattern.split('/')[-1].replace('*','X')}.json", "w"), indent=1)
