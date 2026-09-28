"""Fit a constant-tempo grid to beat_this output (song is programmed at a fixed tempo)."""
import json, numpy as np

d = json.load(open("analysis/beats.json"))
b = np.array(d["beats_s"])
P = 60 / 123.0  # initial double-time beat period guess
t0 = b[0]
for _ in range(5):
    k = np.round((b - t0) / P)
    # robust: drop outliers > 60ms from grid
    resid = b - (t0 + k * P)
    m = np.abs(resid) < 0.06
    A = np.vstack([np.ones(m.sum()), k[m]]).T
    (t0, P), *_ = np.linalg.lstsq(A, b[m], rcond=None)
resid = b - (t0 + np.round((b - t0) / P) * P)
print(f"double-time BPM {60/P:.3f}  half-time BPM {30/P:.3f}  t0 {t0:.3f}s  inliers {np.mean(np.abs(resid)<0.03):.2%}  resid_sd {resid[np.abs(resid)<0.06].std()*1000:.1f}ms")
json.dump({"beat_period_s": P, "bpm_double": 60/P, "bpm_half": 30/P, "t0_s": t0}, open("analysis/grid.json", "w"), indent=1)
