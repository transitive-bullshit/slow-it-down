"""Whole-mix lyric edit with ACE-Step (fal-ai/ace-step/audio-to-audio, edit_mode="lyrics").

A full mix goes in (no stem separation) and only the words change, so the voice, delivery and beat stay the original's.
ACE-Step needs the words currently sung in the input as conditioning. They come from a private Whisper transcript,
are passed straight to the API, and are never printed or saved in the project; receipts record only the parody lines.

Pass 1 edits a slice of the original song. Pass 2 (--src) re-edits an earlier output on the same timeline, so lines that
already came out right are left alone and the edit concentrates on the lines that still differ.

usage: SCRATCH=... python scripts/ace_lyric_edit.py <name> <start_s> <end_s> [--src take.mp3] [--seeds 7 42 ...]
                                                   [--extra '{"lyric_guidance_scale": 2.5}'] [--workers 4]
"""
import argparse, json, os, subprocess, pathlib, concurrent.futures as cf
import requests, fal_client, mlx_whisper

ap = argparse.ArgumentParser()
ap.add_argument("name"); ap.add_argument("start", type=float); ap.add_argument("end", type=float)
ap.add_argument("--src"); ap.add_argument("--seeds", type=int, nargs="*", default=[7, 42, 123, 1991, 2026, 31337])
ap.add_argument("--extra", default="{}"); ap.add_argument("--workers", type=int, default=4)
ap.add_argument("--assume-prev", action="store_true", help="pass 2: input's words = parody lines for pass-1-edited slots, original transcript elsewhere")
ap.add_argument("--swap", default="{}", help='per-slot one-word swaps on the CURRENT line, e.g. {"67.05": {"work": "train"}}')
a = ap.parse_args()
A, B, name, EXTRA, SWAP = a.start, a.end, a.name, json.loads(a.extra), {float(k): v for k, v in json.loads(a.swap).items()}
OUT = pathlib.Path("prototypes/raw/ace_edit"); OUT.mkdir(parents=True, exist_ok=True)
PRIV = pathlib.Path(os.environ["SCRATCH"]) / "ace_private"; PRIV.mkdir(parents=True, exist_ok=True)
spec = json.load(open("prototypes/spec.json"))
slots = sorted([l for sec in spec["excerpts"]["E1_verse_prehook_hook"]["sections"] for l in sec["lines"]], key=lambda l: l[0])
TAGS = ("r&b, slow jam, 2013 contemporary r&b, male vocal, smooth tenor, falsetto, sultry, intimate, stacked backing vocals, "
        "call and response, 808, finger snaps, lush pads, 61.5 bpm, a major")

def ff(*args): subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)

# 1) input audio: a slice of the original mix, or an earlier edit on the same timeline
clip = OUT / f"{name}_src.wav"
if a.src: ff("-i", a.src, "-ar", "44100", str(clip))
else: ff("-ss", str(A), "-to", str(B), "-i", "audio/original/slow-it-down.wav", str(clip))

# 2) private transcript of what the input currently sings (lead stem for the original, full mix for an edit)
priv = PRIV / ("p1arms.json" if a.assume_prev else f"{name}.json")
if not priv.exists():
    if a.src and not a.assume_prev: tr = str(clip)
    else:
        tr = str(PRIV / f"{name}_lead.wav"); ff("-ss", str(A), "-to", str(B), "-i", "audio/stems/lead_vocal_original.wav", tr)
    res = mlx_whisper.transcribe(tr, path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language="en",
                                 word_timestamps=True, condition_on_previous_text=False)
    json.dump(res["segments"], open(priv, "w"))
segs = json.load(open(priv))

# word-level assignment: every transcribed word goes to the line slot it falls in
words = [(A + w["start"], w["word"].strip()) for sg in segs for w in sg.get("words", []) if w["word"].strip()]
from difflib import SequenceMatcher
orig_pairs = list(words)                      # words as sung, before any swap
for k, sw in SWAP.items():
    for key, rep in sw.items():
        cand = [(SequenceMatcher(None, key, "".join(ch for ch in w.lower() if ch.isalpha())).ratio(), j)
                for j, (t, w) in enumerate(words) if k - 0.5 <= t <= k + 3.5]
        r, j = max(cand) if cand else (0, None)
        if j is not None and r >= 0.6: words[j] = (words[j][0], rep); print(f"  swap @{k}: {key}->{rep} (match {r:.2f}, t={words[j][0]:.2f})")
        else: print(f"  swap @{k}: {key} not found (best {r:.2f})")
in_clip = [l for l in slots if A - 0.5 <= l[0] < B]
bounds = [l[0] - 0.35 for l in in_clip] + [B + 1]
cur_lines, new_lines, changed = [], [], 0
inslot = lambda pairs, i: [w for t, w in pairs if (t < bounds[1] if i == 0 else bounds[i] <= t < bounds[i + 1])]
for i, l in enumerate(in_clip):
    ws_orig, ws_new = inslot(orig_pairs, i), inslot(words, i)     # as sung / with one-word swaps applied
    if not ws_orig: continue
    is_parody = l[2] == "lead" and "REFRAIN" not in l[3]
    is_swap = any(abs(k - l[0]) < 0.2 for k in SWAP)
    parody = l[1].replace("—", ",")
    cur = parody if (a.assume_prev and is_parody and not is_swap) else " ".join(ws_orig)
    target = parody if (is_parody and not is_swap) else " ".join(ws_new)
    cur_lines.append(cur); new_lines.append(target); changed += target != cur
print(f"{name}: {len(cur_lines)} line slots, {changed} to change")

# 3) upload once, run seeds in parallel
url = fal_client.upload_file(str(clip))
def run(seed):
    out = OUT / f"{name}_s{seed}.mp3"
    if out.exists(): return f"exists {out}"
    args = {"audio_url": url, "edit_mode": "lyrics", "original_tags": TAGS, "tags": TAGS,
            "original_lyrics": "\n".join(cur_lines), "lyrics": "\n".join(new_lines), "seed": seed, **EXTRA}
    try: res = fal_client.subscribe("fal-ai/ace-step/audio-to-audio", arguments=args)
    except Exception as e: return f"error {seed}: {str(e)[:200]}"
    out.write_bytes(requests.get(res["audio"]["url"], timeout=300).content)
    parody = [l for l, sl in zip(new_lines, in_clip) if l not in cur_lines and not any(abs(k - sl[0]) < 0.2 for k in SWAP)] + [f"slot {k}: swaps {v}" for k, v in SWAP.items()]
    json.dump({"take": out.stem, "endpoint": "fal-ai/ace-step/audio-to-audio", "clip": [A, B], "src": a.src or "original",
               "seed": seed, "tags": TAGS, "extra": EXTRA, "parody_lines_requested": parody,
               "note": "input's current words supplied from a private transcript; not stored"}, open(out.with_suffix(".json"), "w"), indent=1)
    return f"ok {out}"
with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
    for r in ex.map(run, a.seeds): print(r, flush=True)
