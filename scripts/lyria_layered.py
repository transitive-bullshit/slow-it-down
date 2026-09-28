"""Round 2: Lyria 3.5 lead + the ORIGINAL refrain and backing stack re-voiced into the Lyria singer (Seed-VC), layered.

usage: python scripts/lyria_layered.py <take_tag>      e.g. ly_t1   (expects prototypes/work/<tag>/vocals.wav + whisper.json)
Writes recipes L1_<tag>_oneshot and L2_<tag>_layered, then renders both with assemble.py.
"""
import glob, json, os, subprocess, sys
import numpy as np, soundfile as sf, librosa
sys.path.insert(0, "scripts")
from match_lines import load_words, best_span

tag = sys.argv[1]
W = f"prototypes/work/{tag}"
SR = 44100
T0, BAR = 0.227, 3.9024
Q = BAR / 4                                         # quarter note at 61.5 BPM
bar = lambda b, beat=1.0: T0 + (b - 1) * BAR + (beat - 1) * Q
spec = json.load(open("prototypes/spec.json"))
E1 = spec["excerpts"]["E1_verse_prehook_hook"]
SEG = (29.5, 95.5)                                   # song-time slice we re-voice from the original stems


def run(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


# 1) lead / backing split of the Lyria vocal (karaoke model)
if not glob.glob(f"{W}/kara/*(Vocals)*.wav"):
    run(["audio-separator", f"{W}/vocals.wav", "-m", "bs_roformer_karaoke_frazer_becruily.ckpt", "--model_file_dir",
         os.path.expanduser("~/.cache/audio-separator"), "--output_dir", f"{W}/kara", "--output_format", "WAV"])
lyria_lead = glob.glob(f"{W}/kara/*(Vocals)*.wav")[0]

# 2) Lyria's beat grid (for the one-shot overlay) and a clean reference clip of its lead voice
from beat_this.inference import File2Beats
b, _ = File2Beats(checkpoint_path="final0", device="mps", dbn=False)(f"{W}/mix.wav")
b = np.asarray(b); P, t0 = 60 / 123.0, b[0]
for _ in range(6):
    k = np.round((b - t0) / P); m = np.abs(b - (t0 + k * P)) < 0.06
    (t0, P), *_ = np.linalg.lstsq(np.vstack([np.ones(m.sum()), k[m]]).T, b[m], rcond=None)
grid = {"beat_period": float(P), "t0": float(t0)}
y, _ = librosa.load(lyria_lead, sr=SR, mono=True)
ref = f"audio/voices/lead_ref_{tag}.wav"
os.makedirs("audio/voices", exist_ok=True)
sf.write(ref, y[int(0.0 * SR): int(15.5 * SR)], SR)            # the verse: four sung lines, backing removed

# 3) Seed-VC: original lead + backing, same melody and timing, in the Lyria singer's voice
conv = {}
for name, stem in [("lead", "audio/stems/lead_vocal_original.wav"), ("backing", "audio/stems/backing_vocals_original.wav")]:
    src = f"{W}/orig_{name}_seg.wav"; out = f"{W}/orig_{name}_as_{tag}.wav"
    if not os.path.exists(out):
        s, _ = librosa.load(stem, sr=SR, mono=True)
        sf.write(src, s[int(SEG[0] * SR): int(SEG[1] * SR)], SR)
        run(["scripts/seedvc_convert.sh", src, ref, out, "0", "40"])
    conv[name] = out

# 4) recipes
def clip(src, a, b, dst, bus, fit=None, gain=0):
    return {"src": src, "src_start": a, "src_end": b, "dst": dst, "bus": bus, "fit": fit, "gain_db": gain}

rec1 = {"name": f"L1_{tag}_oneshot", "window": [30.6, 95.2],
        "takes": [{"src": f"{W}/vocals.wav", "grid": grid, "bar_time": bar(9), "bus": "lead"}]}

clips = []
# exact refrain pieces from the re-voiced original (source times are relative to SEG[0])
S = lambda t: t - SEG[0]
for u in range(4):                                   # pickup + 6 downs of each hook unit (lead and backing)
    a, e = bar(16 + 2 * u, 3.55), bar(18 + 2 * u, 1.45)
    clips.append(clip(conv["lead"], S(a), S(e), a, "lead"))
    clips.append(clip(conv["backing"], S(bar(17 + 2 * u, 1.0) - 0.1), S(e), bar(17 + 2 * u, 1.0) - 0.1, "backing"))
tag_a, tag_e = bar(24, 3.05), bar(25, 2.3)            # "DJ, you got to slow it (ahoo)"
clips.append(clip(conv["lead"], S(tag_a), S(tag_e), tag_a, "lead"))
clips.append(clip(conv["backing"], S(tag_a), S(tag_e), tag_a, "backing"))
for bb in range(9, 13):                              # the stacked "ahoo" answering each verse line
    a, e = bar(bb, 1.15), bar(bb, 3.0)
    clips.append(clip(conv["backing"], S(a), S(e), a, "backing"))

# new lyric lines: Lyria's lead, snapped to where the original singer sings each line
words = load_words(tag)
lead_lines = [(l[0], l[1]) for sec in E1["sections"] for l in sec["lines"] if l[2] == "lead" and "REFRAIN" not in l[3]]
slot_end = {}
all_times = sorted([l[0] for sec in E1["sections"] for l in sec["lines"]])
report = []
for dst, text in lead_lines:
    nxt = min([t for t in all_times if t > dst + 0.1] + [dst + 4.0])
    sc, span = best_span(text, words)
    if not span:
        report.append(f"MISSING {text}"); continue
    a, e, heard = span
    clips.append(clip(lyria_lead, a, e, dst, "lead", fit=max(1.0, nxt - dst + 0.25)))
    report.append(f"{dst:6.2f} {sc:.2f} {heard}")
rec2 = {"name": f"L2_{tag}_layered", "window": [30.6, 95.2], "clips": clips}
for r in (rec1, rec2):
    json.dump(r, open(f"prototypes/recipes/{r['name']}.json", "w"), indent=1)
print("\n".join(report))
for r in (rec1, rec2):
    subprocess.run([sys.executable, "scripts/assemble.py", f"prototypes/recipes/{r['name']}.json"], check=True)
