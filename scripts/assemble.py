"""Assemble prototype vocals on the song timeline and mix them over the instrumental.

usage: python scripts/assemble.py <recipe.json>

A recipe places audio on the original song's timeline (seconds):
  "takes": whole generated takes, time-stretched onto our 123 BPM grid
           {"src", "grid": {"beat_period", "t0"}, "bar_time", "bus", "gain_db"}
  "clips": single lines or refrain pieces
           {"src", "src_start", "src_end", "dst", "bus", "gain_db", "fit"}
           src_start lands exactly on dst; "fit" squeezes the clip to at most that many seconds.
  "window": [start, end] of the excerpt mix to export.
"""
import json, os, subprocess, sys
import numpy as np, soundfile as sf, librosa, pyrubberband as pyrb, pyloudnorm as pyln
from pedalboard import Pedalboard, HighpassFilter, Compressor, Reverb, Delay, Gain, Limiter

SR = 44100
SONG_LEN = 256.1
BEAT = 60 / 123.0
INSTRUMENTAL = "audio/stems/instrumental_bsroformer.wav"
PRE, POST = 0.06, 0.30          # breath before a line, tail after it


def load(path):
    y, _ = librosa.load(path, sr=SR, mono=False)
    return np.vstack([y, y]) if y.ndim == 1 else y[:2]


def fade(x, fin=0.01, fout=0.08):
    n_in, n_out = int(fin * SR), int(fout * SR)
    x = x.copy()
    if n_in: x[:, :n_in] *= np.linspace(0, 1, n_in)
    if n_out: x[:, -n_out:] *= np.linspace(1, 0, n_out)
    return x


def stretch(x, rate):
    return np.vstack([pyrb.time_stretch(ch, SR, rate) for ch in x]) if abs(rate - 1) > 1e-4 else x


def add(canvas, x, t):
    i = int(round(t * SR))
    if i < 0: x, i = x[:, -i:], 0
    j = min(canvas.shape[1], i + x.shape[1])
    if j > i: canvas[:, i:j] += x[:, : j - i]


CHAINS = {
    "lead": Pedalboard([HighpassFilter(90), Compressor(threshold_db=-20, ratio=3, attack_ms=5, release_ms=90),
                        Delay(delay_seconds=0.366, feedback=0.15, mix=0.06),
                        Reverb(room_size=0.28, damping=0.6, wet_level=0.10, dry_level=0.92, width=0.7)]),
    "backing": Pedalboard([HighpassFilter(160), Compressor(threshold_db=-22, ratio=3, attack_ms=8, release_ms=120),
                           Reverb(room_size=0.45, damping=0.5, wet_level=0.18, dry_level=0.85, width=1.0)]),
    "rap": Pedalboard([HighpassFilter(80), Compressor(threshold_db=-18, ratio=3.5, attack_ms=4, release_ms=70),
                       Reverb(room_size=0.18, damping=0.7, wet_level=0.06, dry_level=0.95, width=0.5)]),
}


def main(recipe_path):
    R = json.load(open(recipe_path))
    name = R["name"]
    buses = {}
    cache = {}
    src = lambda p: cache.setdefault(p, load(p))

    for tk in R.get("takes", []):
        y = src(tk["src"])
        rate = tk["grid"]["beat_period"] / BEAT                     # >1 speeds up
        y = stretch(y, rate)
        t0 = tk["grid"]["t0"] / rate
        bus = buses.setdefault(tk.get("bus", "lead"), np.zeros((2, int(SONG_LEN * SR))))
        add(bus, fade(y * 10 ** (tk.get("gain_db", 0) / 20), 0.02, 0.5), tk["bar_time"] - t0)

    for c in R.get("clips", []):
        y = src(c["src"])
        a, b = max(0.0, c["src_start"] - PRE), c["src_end"] + POST
        x = y[:, int(a * SR): int(b * SR)]
        lead_in = c["src_start"] - a
        if c.get("fit") and (c["src_end"] - c["src_start"]) > c["fit"]:
            rate = (c["src_end"] - c["src_start"]) / c["fit"]
            x = stretch(x, rate); lead_in /= rate
        if R.get("normalize_clips", True):             # sources come from different engines at different levels
            env = np.abs(x).max(axis=0); act = env > env.max() * 10 ** (-40 / 20)
            if act.any():
                rms_db = 20 * np.log10(np.sqrt(np.mean(x[:, act] ** 2)) + 1e-9)
                target = -20.0 if c.get("bus", "lead") != "backing" else -23.0
                x = x * 10 ** (np.clip(target - rms_db, -18, 18) / 20)
        bus = buses.setdefault(c.get("bus", "lead"), np.zeros((2, int(SONG_LEN * SR))))
        add(bus, fade(x * 10 ** (c.get("gain_db", 0) / 20)), c["dst"] - lead_in)

    # per-bus processing, then level the vocals against the instrumental
    meter = pyln.Meter(SR)
    w0, w1 = R["window"]
    inst = load(INSTRUMENTAL)[:, : int(SONG_LEN * SR)]
    inst = np.pad(inst, ((0, 0), (0, int(SONG_LEN * SR) - inst.shape[1])))
    seg = lambda x: x[:, int(w0 * SR): int(w1 * SR)]
    vocals = np.zeros_like(inst)
    for bname, x in buses.items():
        vocals[:, : x.shape[1]] += CHAINS.get(bname, CHAINS["lead"])(x, SR)
    inst_lufs = meter.integrated_loudness(seg(inst).T)
    voc_lufs = meter.integrated_loudness(seg(vocals).T)
    target = inst_lufs + R.get("vocal_over_inst_lu", 3.0)
    vocals *= 10 ** ((target - voc_lufs) / 20)

    mix = seg(inst) + seg(vocals)
    mix = Pedalboard([Limiter(threshold_db=-1.5, release_ms=120)])(mix, SR)
    mix *= 10 ** ((-14.0 - meter.integrated_loudness(mix.T)) / 20)
    mix = np.clip(fade(mix, 0.3, 0.8), -0.99, 0.99)

    os.makedirs("prototypes/out", exist_ok=True)
    tmp = f"prototypes/out/_{name}.wav"
    sf.write(tmp, mix.T, SR)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", tmp, "-c:a", "libmp3lame", "-q:a", "2",
                    f"prototypes/out/{name}.mp3"], check=True)
    os.remove(tmp)
    vpath = f"prototypes/out/{name}__vocals_full.wav"
    sf.write(vpath, vocals.T.clip(-1, 1), SR)   # same balance vs the raw instrumental as in the mix
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", vpath, "-c:a", "libmp3lame", "-q:a", "3",
                    vpath.replace(".wav", ".mp3")], check=True)
    os.remove(vpath)
    print(f"{name}: inst {inst_lufs:.1f} LUFS, vocals leveled to {target:.1f}; wrote prototypes/out/{name}.mp3 (+ full-length vocal stem)")


if __name__ == "__main__":
    main(sys.argv[1])
