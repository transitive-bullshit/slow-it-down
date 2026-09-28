"""Pitch-fidelity check: does a converted vocal keep the source melody?

usage (project .venv): python scripts/pitch_compare.py SRC.wav OUT.wav [OUT2 ...] [--expect-shift -12]

pyin (C2..C6) on both files, frame by frame at zero lag (drop-in alignment). A frame counts as voiced only if
pyin says so AND it is within 40 dB of that file's loudest frame, so separation bleed and reverb tails are ignored.
Reports:
  voiced overlap : frames voiced in both / frames voiced in the source (and the Jaccard index)
  corr           : Pearson correlation of MIDI pitch over the frames voiced in both
  median shift   : median(out - src) in semitones
  <=1st folded   : % of shared voiced frames within 1 semitone once octave errors are folded away
  <=1st exact    : same, without folding (octave jumps count as misses)
  lag            : best alignment offset of the pitch tracks, in ms (positive = output late)
"""
import argparse

import librosa
import numpy as np

SR, HOP, FRAME = 22050, 256, 2048
FMIN, FMAX = librosa.note_to_hz("C2"), librosa.note_to_hz("C6")
GATE_DB = 40.0


def track(path):
    y, _ = librosa.load(path, sr=SR, mono=True)
    f0, voiced, _ = librosa.pyin(y, fmin=FMIN, fmax=FMAX, sr=SR, frame_length=FRAME, hop_length=HOP)
    db = librosa.amplitude_to_db(librosa.feature.rms(y=y, frame_length=FRAME, hop_length=HOP)[0], ref=np.max)
    n = min(len(f0), len(db))
    return f0[:n], voiced[:n] & np.isfinite(f0[:n]) & (db[:n] > -GATE_DB)


def fold(d):
    return (d + 6.0) % 12.0 - 6.0


def compare(f_src, v_src, f_out, v_out, expect=0.0):
    n = min(len(f_src), len(f_out))
    f_src, v_src, f_out, v_out = f_src[:n], v_src[:n], f_out[:n], v_out[:n]
    both = v_src & v_out
    r = {"src_voiced": int(v_src.sum()), "out_voiced": int(v_out.sum()), "both": int(both.sum()),
         "overlap": both.sum() / max(v_src.sum(), 1), "jaccard": both.sum() / max((v_src | v_out).sum(), 1)}
    if both.sum() < 10:
        return r | {"corr": np.nan, "median_shift": np.nan, "within1_fold": np.nan, "within1_exact": np.nan,
                    "within_half_fold": np.nan}
    m_src, m_out = librosa.hz_to_midi(f_src[both]), librosa.hz_to_midi(f_out[both])
    d = m_out - m_src - expect
    return r | {"corr": float(np.corrcoef(m_src, m_out)[0, 1]), "median_shift": float(np.median(m_out - m_src)),
                "within1_fold": float(np.mean(np.abs(fold(d)) <= 1.0)),
                "within_half_fold": float(np.mean(np.abs(fold(d)) <= 0.5)),
                "within1_exact": float(np.mean(np.abs(d) <= 1.0))}


def best_lag(f_src, v_src, f_out, v_out, max_ms=150):
    best, best_score = 0, -1.0
    k = int(max_ms / 1000 * SR / HOP)
    for lag in range(-k, k + 1):
        if lag >= 0:
            a = compare(f_src[: len(f_src) - lag] if lag else f_src, v_src[: len(v_src) - lag] if lag else v_src,
                        f_out[lag:], v_out[lag:])
        else:
            a = compare(f_src[-lag:], v_src[-lag:], f_out, v_out)
        score = a["within1_fold"] if np.isfinite(a.get("within1_fold", np.nan)) else -1
        score = score * a["overlap"]
        if score > best_score:
            best, best_score = lag, score
    return best * HOP / SR * 1000


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("outputs", nargs="+")
    ap.add_argument("--expect-shift", type=float, default=0.0, help="intended transposition in semitones")
    a = ap.parse_args()
    f_src, v_src = track(a.source)
    print(f"source {a.source}: {v_src.sum()} voiced frames of {len(v_src)} ({HOP / SR * 1000:.1f} ms hop)")
    hdr = f"{'file':44s} {'overlap':>7s} {'jacc':>5s} {'corr':>6s} {'med.st':>7s} {'<=1st fold':>10s} {'<=.5st':>7s} {'<=1st exact':>11s} {'lag ms':>7s}"
    print(hdr)
    for p in a.outputs:
        f_out, v_out = track(p)
        r = compare(f_src, v_src, f_out, v_out, a.expect_shift)
        lag = best_lag(f_src, v_src, f_out, v_out)
        print(f"{p.split('/')[-1][:44]:44s} {r['overlap']:7.1%} {r['jaccard']:5.2f} {r['corr']:6.3f} {r['median_shift']:+7.2f} "
              f"{r['within1_fold']:10.1%} {r['within_half_fold']:7.1%} {r['within1_exact']:11.1%} {lag:+7.1f}")


if __name__ == "__main__":
    main()
