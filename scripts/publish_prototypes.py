"""Write prototypes/prototypes.js so the lyric lab can offer each prototype vocal stem."""
import json, glob, os
LABELS = {
 "A_elevenlabs_oneshot": "A · Hook: ElevenLabs Music one-shot (its own phrasing)",
 "B_elevenlabs_comped": "B · Hook: ElevenLabs lines snapped to original slots (EL refrain)",
 "C_elevenlabs_comped_exact_refrain": "C · Hook: ElevenLabs lines + EXACT original refrain & stacks (Seed-VC)",
 "D_minimax_comped": "D · Hook: MiniMax Music lines snapped to slots",
 "E_acestep_inpaint": "E · Hook: ACE-Step inpaint over the original",
 "L1_ly_t1_oneshot": "L1 · Hook: Lyria 3.5 one-shot (its own melody & timing)",
 "L2_ly_t1_layered": "L2 · Hook: Lyria lead lines + ORIGINAL refrain & backing re-voiced into the Lyria singer (Seed-VC)",
 "RA_rap_elevenlabs_oneshot": "RA · Rap: ElevenLabs Music one-shot",
 "RB_rap_elevenlabs_comped": "RB · Rap: ElevenLabs Music snapped to original line grid",
 "RC_rap_tts_v3": "RC · Rap: designed voice, ElevenLabs TTS v3, snapped to grid",
 "RC_rap_tts_multilingual_v2": "RC2 · Rap: designed voice, TTS multilingual v2, snapped to grid",
 "RD_rap_minimax": "RD · Rap: MiniMax Music",
}
items = []
for f in sorted(glob.glob("prototypes/out/*__vocals_full.mp3")):
    name = os.path.basename(f).replace("__vocals_full.mp3", "")
    items.append({"id": name, "label": LABELS.get(name, name), "src": f, "mix": f"prototypes/out/{name}.mp3",
                  "start": 170.8 if name.startswith("R") else 31.0})
open("prototypes/prototypes.js", "w").write("window.PROTOTYPES = " + json.dumps(items, indent=1) + ";\n")
print(len(items), "prototypes published:", [i["id"] for i in items])
