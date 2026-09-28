"""Targeted re-singing with ACE-Step 1.5 Repaint (fal-ai/ace-step-1.5/repaint): only a time window is regenerated with
new lyrics; everything outside it is kept. Windows are processed in order, each on the previous result, so the output
stays one continuous take. For each window several seeds run in parallel and the best one is kept, judged by
Whisper word match inside the window (plus a check that the audio outside the window didn't change).

usage: python scripts/ace15_repaint.py <src_take.mp3> <out_name> [--seeds 1 2 3 4] [--strength 0.8]
Clip timeline = song time minus CLIP0 (the whole-mix edit clips start at 46.3 s).
"""
import argparse, json, re, pathlib, concurrent.futures as cf
import numpy as np, requests, librosa, fal_client, mlx_whisper
from difflib import SequenceMatcher

CLIP0 = 46.3
STYLE = ("Repaint the selected section with new sung lyrics: the same smooth, sultry male R&B tenor and the same melody, "
         "2013 Atlanta slow jam, intimate, light Auto-Tune, stacked backing vocals")
# (song start, song end, lyrics for the window, target words to verify)
WINDOWS = [
    (57.9, 61.2, "Enough with the motherfuckin' arms race", "enough with the motherfuckin arms race"),
    (66.5, 69.5, "Give her time to grow, slow takeoff with me", "give her time to grow slow takeoff with me"),
    (74.3, 77.3, "Read her chain of thought, she thinkin' 'bout me", "read her chain of thought she thinkin bout me"),
    (82.3, 85.3, "Just steer it left, steer it right", "just steer it left steer it right"),
]
norm = lambda s: re.sub(r"[^a-z ]+", " ", s.lower().replace("'", "")).split()

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("name")
ap.add_argument("--seeds", type=int, nargs="*", default=[1, 2, 3, 4]); ap.add_argument("--strength", type=float, default=0.8)
a = ap.parse_args()
OUT = pathlib.Path("prototypes/raw/ace15"); OUT.mkdir(parents=True, exist_ok=True)

def fetch(url, path):
    path.write_bytes(requests.get(url, timeout=300).content); return path

def score(path, s0, s1, target, ref=None):
    y, sr = librosa.load(str(path), sr=16000, mono=True)
    a0, a1 = max(0, int((s0 - CLIP0 - 0.4) * sr)), int((s1 - CLIP0 + 0.4) * sr)
    seg = y[a0:a1]
    res = mlx_whisper.transcribe(seg, path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language="en", condition_on_previous_text=False)
    heard = norm(" ".join(s["text"] for s in res["segments"]))
    words = SequenceMatcher(None, norm(target), heard).ratio()
    outside = 1.0
    if ref is not None:                       # how much of the audio OUTSIDE the window stayed as it was (mel, 1 s guard)
        M = lambda z: librosa.power_to_db(librosa.feature.melspectrogram(y=z, sr=sr, n_mels=64, hop_length=256))
        Mr, My = M(ref), M(y); n = min(Mr.shape[1], My.shape[1]); f = sr / 256
        mask = np.ones(n, bool); mask[max(0, int((a0 / sr - 1) * f)):min(n, int((a1 / sr + 1) * f))] = False
        outside = float(np.corrcoef(Mr[:, :n][:, mask].ravel(), My[:, :n][:, mask].ravel())[0, 1])
    return words, outside, " ".join(heard)

cur_url = fal_client.upload_file(a.src)
cur_path = pathlib.Path(a.src)
log = []
for wi, (s0, s1, lyr, target) in enumerate(WINDOWS):
    ref, _ = librosa.load(str(cur_path), sr=16000, mono=True)
    def run(seed):
        args = {"source_audio_url": cur_url, "start_time": s0 - CLIP0, "end_time": s1 - CLIP0, "lyrics": lyr, "prompt": STYLE,
                "repaint_strength": a.strength, "seed": seed, "vocal_language": "en"}
        res = fal_client.subscribe("fal-ai/ace-step-1.5/repaint", arguments=args)
        url = res["audio"]["url"]; p = fetch(url, OUT / f"{a.name}_w{wi}_s{seed}.mp3")
        return {"seed": seed, "url": url, "path": str(p)}
    with cf.ThreadPoolExecutor(max_workers=len(a.seeds)) as ex:
        def safe(seed):
            try: return run(seed)
            except Exception as e: print(f'  seed {seed} failed: {str(e)[:160]}'); return None
        cands = [c for c in ex.map(safe, a.seeds) if c]
    if not cands: print(f'window {wi}: all seeds failed, skipping'); continue
    for c in cands:
        c['words'], c['outside'], c['heard'] = score(pathlib.Path(c['path']), s0, s1, target, ref)
    best = max(cands, key=lambda c: c["words"] + 0.5 * c["outside"])
    before, _, _ = score(cur_path, s0, s1, target)
    print(f"window {wi} [{s0}-{s1}] '{lyr}': before {before:.2f} -> best seed {best['seed']} words {best['words']:.2f}, "
          f"outside-window kept {best['outside']:.3f}  (all: {[round(c['words'], 2) for c in cands]})", flush=True)
    log.append({"window": [s0, s1], "lyrics": lyr, "before": before, "chosen": best, "candidates": cands})
    if best["words"] > before:                # only accept the repaint if it actually improved the line
        cur_url, cur_path = best["url"], pathlib.Path(best["path"])
final = OUT / f"{a.name}_final.mp3"; final.write_bytes(cur_path.read_bytes())
json.dump({"src": a.src, "strength": a.strength, "windows": log, "final": str(final)}, open(OUT / f"{a.name}.json", "w"), indent=1)
print("final:", final)
