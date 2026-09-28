"""Cold-open demo: the DJ turns the slow jam into a race track, then a tape-stop drops into the real song."""
import json
import numpy as np, soundfile as sf, librosa

SR = 44100
g = json.load(open("analysis/grid.json")); P, T0 = g["beat_period_s"], g["t0_s"]; BAR = 8 * P
inst, _ = librosa.load("audio/stems/instrumental_bsroformer.wav", sr=SR, mono=False)
orig, _ = librosa.load("audio/original/slow-it-down.wav", sr=SR, mono=False)

SPEED = 1.25                                    # 123 -> ~154 BPM, pitch up ~3.9 st ("nightcore" race feel)
a, b = T0 + 16 * BAR, T0 + 20 * BAR              # 4 bars of the hook groove
seg = inst[:, int(a * SR):int(b * SR)]
fast = np.stack([librosa.resample(ch, orig_sr=SR, target_sr=int(SR / SPEED)) for ch in seg])
n = fast.shape[1]; beat = P / SPEED              # four-on-the-floor at the sped-up double-time beat

def kick(sr=SR, dur=0.28):
    t = np.arange(int(sr * dur)) / sr
    f = 45 + 110 * np.exp(-t * 28); ph = 2 * np.pi * np.cumsum(f) / sr
    return np.sin(ph) * np.exp(-t * 9) * 0.9
def clap(sr=SR, dur=0.18):
    rng = np.random.default_rng(0); x = rng.standard_normal(int(sr * dur))
    x = librosa.effects.preemphasis(x, coef=0.97); t = np.arange(len(x)) / sr
    return x * np.exp(-t * 22) * 0.25
drums = np.zeros(n); K, C = kick(), clap()
for i in range(int(n / SR / beat) + 1):
    s = int(i * beat * SR)
    if s >= n: break
    k = K[: n - s]; drums[s:s + len(k)] += k
    if i % 2 == 1:
        c = C[: n - s]; drums[s:s + len(c)] += c
# riser over the last 2 bars: noise through a rising band
rise_len = int(2 * BAR / SPEED * SR); rng = np.random.default_rng(1)
noise = rng.standard_normal(rise_len); env = np.linspace(0, 1, rise_len) ** 2
S = librosa.stft(noise, n_fft=1024, hop_length=256); freqs = librosa.fft_frequencies(sr=SR, n_fft=1024)
centers = np.geomspace(300, 9000, S.shape[1])
mask = np.exp(-((np.log(freqs[:, None]) - np.log(centers[None, :])) ** 2) / 0.08)
riser = librosa.istft(S * mask, hop_length=256, length=rise_len) * env
riser = riser / (np.abs(riser).max() + 1e-9) * 0.25
race = fast * 0.8 + drums[None, :] * 0.9
race[:, -rise_len:] += riser[None, :]

# DJ Moloch hype, pitched down 3 semitones, over the first bars
hype, _ = librosa.load("audio/tests/_moloch_hype.mp3", sr=SR, mono=True)
hype = librosa.effects.pitch_shift(hype, sr=SR, n_steps=-3)
hype = hype / (np.abs(hype).max() + 1e-9) * 0.9
start = int(0.4 * SR); end = min(n, start + len(hype))
race[:, start:end] += hype[: end - start][None, :] * 1.1

# tape-stop over the last 1.6 s of the race: playback rate ramps 1 -> 0
ts = int(1.6 * SR); tail = race[:, -ts:]
rate = np.linspace(1.0, 0.0, ts) ** 1.3
pos = np.cumsum(rate); pos = pos / pos[-1] * (ts - 1) * 0.55
stopped = np.stack([np.interp(pos, np.arange(ts), ch) for ch in tail]) * np.linspace(1, 0.2, ts)[None, :]
race = np.concatenate([race[:, :-ts], stopped], axis=1)

gap = np.zeros((2, int(0.45 * SR)))
song = orig[:, : int((T0 + 5 * BAR + 1.0) * SR)]      # into the first sung line
out = np.concatenate([race, gap, song], axis=1)
out = out / (np.abs(out).max() + 1e-9) * 0.97
sf.write("audio/tests/cold_open_demo.wav", out.T, SR)
print(f"race {race.shape[1]/SR:.1f}s + gap + song intro {song.shape[1]/SR:.1f}s = {out.shape[1]/SR:.1f}s")
