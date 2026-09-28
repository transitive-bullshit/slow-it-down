"""Beat/downbeat tracking + tempo + key estimate for the original mix."""
import json, sys
import numpy as np
import librosa
from beat_this.inference import File2Beats

src = sys.argv[1] if len(sys.argv) > 1 else "audio/original/slow-it-down.wav"
out = sys.argv[2] if len(sys.argv) > 2 else "analysis/beats.json"

f2b = File2Beats(checkpoint_path="final0", device="mps", dbn=False)
beats, downbeats = f2b(src)
beats, downbeats = np.asarray(beats), np.asarray(downbeats)

ibi = np.diff(beats)
bpm_median = 60.0 / np.median(ibi)
# beats per bar from downbeat spacing
bar_lengths = [int(((beats >= a) & (beats < b)).sum()) for a, b in zip(downbeats[:-1], downbeats[1:])]
vals, counts = np.unique(bar_lengths, return_counts=True)

# key estimate (Krumhansl-Schmuckler on CQT chroma)
y, sr = librosa.load(src, sr=22050, mono=True)
y_h = librosa.effects.harmonic(y)
chroma = librosa.feature.chroma_cqt(y=y_h, sr=sr).mean(axis=1)
maj = np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88])
mnr = np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17])
names = ['C','C#','D','Eb','E','F','F#','G','Ab','A','Bb','B']
scores = []
for i in range(12):
    scores.append((np.corrcoef(np.roll(maj, i), chroma)[0,1], f"{names[i]} major"))
    scores.append((np.corrcoef(np.roll(mnr, i), chroma)[0,1], f"{names[i]} minor"))
scores.sort(reverse=True)

res = {
    "duration_s": float(librosa.get_duration(y=y, sr=sr)),
    "bpm_median": round(float(bpm_median), 2),
    "bpm_mean_local": round(float(60.0 / ibi.mean()), 2),
    "tempo_stability_cv": round(float(ibi.std() / ibi.mean()), 4),
    "n_beats": int(len(beats)), "n_downbeats": int(len(downbeats)),
    "beats_per_bar_histogram": {int(v): int(c) for v, c in zip(vals, counts)},
    "first_beat_s": round(float(beats[0]), 3), "first_downbeat_s": round(float(downbeats[0]), 3),
    "key_candidates": [{"key": k, "r": round(float(r), 3)} for r, k in scores[:4]],
    "beats_s": [round(float(b), 3) for b in beats],
    "downbeats_s": [round(float(d), 3) for d in downbeats],
}
json.dump(res, open(out, "w"), indent=1)
print({k: v for k, v in res.items() if k not in ("beats_s", "downbeats_s")})
print("first 12 downbeats:", res["downbeats_s"][:12])
