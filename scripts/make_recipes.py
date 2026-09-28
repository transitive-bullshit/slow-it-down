"""Write assembly recipes for each prototype variant."""
import json, os, sys
sys.path.insert(0, "scripts")
from match_lines import load_words, best_span

spec = json.load(open("prototypes/spec.json"))
grids = json.load(open("prototypes/work/take_grids.json"))
os.makedirs("prototypes/recipes", exist_ok=True)
W_E1, W_E2 = [30.6, 95.2], [170.6, 204.6]
rap_lines = spec["excerpts"]["E2_rap_verse"]["sections"][0]["lines"]
LP = spec["excerpts"]["E2_rap_verse"]["line_period_s"]

def save(r):
    json.dump(r, open(f"prototypes/recipes/{r['name']}.json", "w"), indent=1); print("recipe", r["name"], len(r.get("clips", [])), "clips")

def comp(lines, takes, bus, fit_default=None, report=True):
    """lines: [(dst, text, fit)], takes: [(tag, vocals_path)] in priority order -> clips"""
    words = {t: load_words(t) for t, _ in takes}
    clips = []
    for dst, text, fit in lines:
        best = None
        for t, path in takes:
            sc, span = best_span(text, words[t])
            if span and (best is None or sc > best[0] + 0.08): best = (sc, t, path, span)
        if not best:
            print(f"  MISSING: {text}"); continue
        sc, t, path, (a, b, heard) = best
        if report: print(f"  {dst:7.2f}  {sc:.2f} {t:10s} {heard}")
        clips.append({"src": path, "src_start": a, "src_end": b, "dst": dst, "bus": bus, "fit": fit or fit_default})
    return clips

which = sys.argv[1:] or ["A", "RA", "RB", "RC"]
if "A" in which:
    save({"name": "A_elevenlabs_oneshot", "window": W_E1,
          "takes": [{"src": "prototypes/work/el_E1_s11/vocals.wav", "grid": grids["el_E1_s11"], "bar_time": 31.446, "bus": "lead"}]})
if "RA" in which:
    save({"name": "RA_rap_elevenlabs_oneshot", "window": W_E2, "vocal_over_inst_lu": 4.0,
          "takes": [{"src": "prototypes/work/el_E2_s21/vocals.wav", "grid": grids["el_E2_s21"], "bar_time": 171.933, "bus": "rap"}]})
if "RB" in which:
    lines = [(l[0], l[1], LP * 1.02) for l in rap_lines]
    save({"name": "RB_rap_elevenlabs_comped", "window": W_E2, "vocal_over_inst_lu": 4.0,
          "clips": comp(lines, [("el_E2_s21", "prototypes/work/el_E2_s21/vocals.wav"), ("el_E2_s7", "prototypes/work/el_E2_s7/vocals.wav")], "rap")})
if "RC" in which:
    for model in ["eleven_v3", "eleven_multilingual_v2"]:
        al = json.load(open(f"prototypes/raw/elevenlabs/tts_rap_{model}.json"))
        a = al["alignment"]; chars = "".join(a["characters"]); st, en = a["character_start_times_seconds"], a["character_end_times_seconds"]
        clips, pos = [], 0
        for l in rap_lines:
            txt = l[1].replace("METR", "Meter").replace("e/accs", "e-accs")
            i = chars.find(txt, pos)
            if i < 0: print("  TTS line not found:", txt); continue
            j = i + len(txt) - 1; pos = j
            clips.append({"src": f"prototypes/raw/elevenlabs/tts_rap_{model}.mp3", "src_start": st[i], "src_end": en[j], "dst": l[0], "bus": "rap", "fit": LP * 1.02})
        save({"name": f"RC_rap_tts_{model.replace('eleven_', '')}", "window": W_E2, "vocal_over_inst_lu": 4.0, "clips": clips})
