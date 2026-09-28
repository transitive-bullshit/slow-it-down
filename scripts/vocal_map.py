"""Vocal activity + Whisper word timing -> line/bar map.

Writes only structural data (timings, bar positions, syllable counts) to analysis/.
The raw transcript stays in the session scratchpad (it is the original lyric text),
and is never written into the project.
"""
import json, os, sys, re
import numpy as np
import librosa, soundfile as sf
import pronouncing, pyphen

VOC = sys.argv[1]
SCRATCH = os.environ["SCRATCH"]
grid = json.load(open("analysis/grid.json"))
P, T0 = grid["beat_period_s"], grid["t0_s"]          # 123 BPM beat
QN = 2 * P                                            # quarter note at 61.5 BPM
BAR = 4 * QN                                          # one 4/4 bar at 61.5 BPM (~3.90 s)

def barpos(t):
    """Position as bar.beat.16th in the 61.5-BPM frame, bars counted from t0 (bar 1)."""
    x = (t - T0) / BAR
    bar = int(np.floor(x)); frac = x - bar
    beat = int(np.floor(frac * 4)); six = int(round((frac * 4 - beat) * 4))
    if six == 4: beat, six = beat + 1, 0
    if beat == 4: bar, beat = bar + 1, 0
    return f"{bar+1}.{beat+1}.{six+1}", round(float(x) + 1, 3)

# --- vocal activity (RMS) ---
y, sr = librosa.load(VOC, sr=22050, mono=True)
hop = 512
rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0]
db = 20 * np.log10(rms + 1e-9); db -= db.max()
act = db > -32
t = librosa.frames_to_time(np.arange(len(act)), sr=sr, hop_length=hop)
segs, on = [], None
for i, a in enumerate(act):
    if a and on is None: on = t[i]
    if not a and on is not None: segs.append([on, t[i]]); on = None
if on is not None: segs.append([on, t[-1]])
merged = []
for s in segs:
    if merged and s[0] - merged[-1][1] < 0.35: merged[-1][1] = s[1]
    else: merged.append(s)
merged = [s for s in merged if s[1] - s[0] > 0.25]

# --- whisper ---
raw_path = os.path.join(SCRATCH, "whisper_raw.json")
if not os.path.exists(raw_path):
    import mlx_whisper
    res = mlx_whisper.transcribe(VOC, path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
                                 language="en", word_timestamps=True,
                                 condition_on_previous_text=False,
                                 no_speech_threshold=0.4, compression_ratio_threshold=2.6)
    json.dump(res, open(raw_path, "w"))
res = json.load(open(raw_path))

dic = pyphen.Pyphen(lang="en_US")
def syl(word):
    w = re.sub(r"[^a-z']", "", word.lower())
    if not w: return 0
    ph = pronouncing.phones_for_word(w)
    if ph: return pronouncing.syllable_count(ph[0])
    return max(1, len(dic.inserted(w).split("-")))

lines = []
for seg in res["segments"]:
    words = seg.get("words", [])
    if not words: continue
    s, e = words[0]["start"], words[-1]["end"]
    n_syl = sum(syl(w["word"]) for w in words)
    bp, bx = barpos(s)
    tag = " ".join(w["word"].strip() for w in words[:2])  # identifier only, not stored
    lines.append({"start_s": round(s, 2), "end_s": round(e, 2), "bar_pos": bp, "bar_float": bx,
                  "dur_s": round(e - s, 2), "syllables": n_syl, "n_words": len(words), "_tag": tag,
                  "word_onsets_s": [round(w["start"], 2) for w in words]})

print(f"BAR={BAR:.3f}s  vocal-activity segments={len(merged)}  whisper segments={len(lines)}")
for i, L in enumerate(lines):
    print(f"{i:3d} {L['start_s']:7.2f}-{L['end_s']:7.2f}  bar {L['bar_pos']:>8}  syl {L['syllables']:2d}  [{L['_tag']}…]")
json.dump({"bar_s": BAR, "activity": [[round(a,2), round(b,2)] for a, b in merged],
           "lines": [{k: v for k, v in L.items() if k != "_tag"} for L in lines]},
          open("analysis/vocal_lines_raw.json", "w"), indent=1)
