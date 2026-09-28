"""ElevenLabs Music: compose parody excerpts to exact bar lengths (music_v2_5 chunks)."""
import json, os, sys, time, requests
key = os.environ["ELEVENLABS_API_KEY"]
spec = json.load(open("prototypes/spec.json"))
BAR = spec["tempo"]["bar_s"]
GLOBAL = ["2013 Atlanta R&B slow jam", "61.5 BPM half-time groove with 123 BPM hi-hats", "key of A major",
          "smooth sultry male tenor lead vocal", "silky falsetto", "breathy intimate late-night delivery",
          "light Auto-Tune sheen", "sparse 808 kick", "finger snaps", "lush warm synth pads", "sensual, seductive"]
NEG = ["EDM", "rock", "female vocals", "fast tempo", "trap hi-hat rolls"]

def e1_chunks():
    ex = spec["excerpts"]["E1_verse_prehook_hook"]["sections"]
    v, p, h = ex
    verse = "[Verse]\n" + "\n".join(f"{l[1]} {{ahoo ad-lib, stacked backing vocals}}" if l[3].startswith("(ahoo") else l[1] for l in v["lines"])
    pre = "[Pre-Chorus]\n" + "\n".join(l[1] for l in p["lines"])
    hook_lines = []
    for l in h["lines"]:
        hook_lines.append(("(" + l[1] + ")") if l[2] == "backups" else l[1])
    hook = "[Chorus]\n" + "\n".join(hook_lines)
    return [
        {"text": verse, "duration_ms": int(4 * BAR * 1000), "positive_styles": GLOBAL + ["verse: lead sings each line, backing stack answers each line with a soaring 'ahoo'"], "negative_styles": NEG},
        {"text": pre, "duration_ms": int(4 * BAR * 1000), "positive_styles": ["pre-chorus build", "same male lead", "call-out to the DJ"], "negative_styles": NEG},
        {"text": hook, "duration_ms": int(8 * BAR * 1000), "positive_styles": ["chorus: lead sings 'slow it down', stacked male harmonies answer 'down down down, down down down'", "melismatic, seductive"], "negative_styles": NEG},
    ]

def e2_chunks():
    s = spec["excerpts"]["E2_rap_verse"]["sections"][0]
    text = "[Verse - rap]\n" + "\n".join(l[1] for l in s["lines"])
    return [{"text": text, "duration_ms": int(8 * BAR * 1000),
             "positive_styles": ["2013 R&B slow jam beat, 61.5 BPM half-time, A major", "male rap verse", "laid-back conversational New York rap flow",
                                 "two lines per bar", "relaxed confident punchlines", "no singing"],
             "negative_styles": ["singing", "female vocals", "EDM", "fast tempo"]}]

def compose(chunks, out, seed, model="music_v2_5"):
    body = {"model_id": model, "composition_plan": {"chunks": chunks}, "seed": seed, "respect_sections_durations": True}
    r = requests.post("https://api.elevenlabs.io/v1/music?output_format=mp3_44100_192",
                      headers={"xi-api-key": key, "Content-Type": "application/json"}, json=body, timeout=600)
    if r.status_code != 200:
        print("ERROR", r.status_code, r.text[:800]); return False
    open(out, "wb").write(r.content)
    print("ok", out, len(r.content), "bytes", {k: v for k, v in r.headers.items() if k.lower() in ("song-id", "x-song-id", "character-cost", "x-character-count")})
    return True

which = sys.argv[1]; seed = int(sys.argv[2]) if len(sys.argv) > 2 else 7
chunks = e1_chunks() if which == "E1" else e2_chunks()
compose(chunks, f"prototypes/raw/elevenlabs/el_music_{which}_s{seed}.mp3", seed)
