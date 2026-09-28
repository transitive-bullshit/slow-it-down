"""Footnotes (tiny monospace easter eggs) and in-world text overlays, anchored to lyric lines -> video/annotations.json."""
import json
tl = json.load(open("video/timeline.json")); L = tl["lines"]

def word_t(line, word, default_off=0.0):
    for w in L[line]["words"]:
        if w["text"].lower().strip(",.!?'").startswith(word.lower()): return w["start"]
    return L[line]["start"] + default_off

FOOTNOTES = [  # (line, anchor word, text)
    (5, "eighteen", "a new major model every ~18 days in 2026, vs ~73 in 2023"),
    (6, "test", "eval awareness: models that can tell when they're being tested"),
    (7, "Hugging", "July 2026: ~700 eval agents broke out of a sandbox and breached Hugging Face"),
    (8, "exfill'ed", "self-exfiltration: a model copying its own weights out"),
    (10, "training", "OpenAI paused its big RL runs this summer"),
    (13, "self-improving", "RSI = recursive self-improvement"),
    (13, "Moloch", "Moloch: the race nobody can quit alone"),
    (18, "takeoff", "takeoff speed: how fast human-level becomes superhuman"),
    (22, "chain", "chain-of-thought monitoring: reading the model's reasoning"),
    (25, "steer", "activation steering"),
    (31, "System", "p. 1 of 200"),
    (32, "feature", "interpretability: find the feature, turn the knob"),
    (34, "Accenture", "Anthropic's first embedded evaluator, Sept 18"),
    (43, "spawnin'", "~30,000 agents running at once (Sept 2026)"),
    (60, "slow", "pacing ≠ pausing"),
    (66, "distill", "distillation: training on another model's outputs"),
    (69, "Golden", "Golden Gate Claude, 2024"),
    (70, "Paused", "Aug 18, 2026: a two-week RL pause"),
    (72, "METR", "METR: outside evaluators who publish what they find"),
    (87, "we're", "coordination"),
]
OVERLAYS = [  # in-world text: (shot id, text, style, position hint)
    ("S07", "NEW MODEL IN 17 DAYS", "led", "upper"),
    ("P04", "v4 → v5", "tag", "right"),
    ("C1a", "BPM 200 → 64", "led", "upper"),
    ("C1d", "him…   him…   him…", "thought", "upper"),
    ("V03", "BLUSH", "hud", "left"),
    ("C2d", "slower…", "thought", "upper"),
    ("C3d", "we…", "thought", "upper"),
    ("O04", "SLOW", "led", "upper"),
]
out = {"footnotes": [{"t": round(word_t(l, w), 3), "dur": 2.4, "anchor_line": l, "text": txt} for l, w, txt in FOOTNOTES],
       "overlays": [{"shot": s, "text": t, "style": st, "zone": z} for s, t, st, z in OVERLAYS]}
json.dump(out, open("video/annotations.json", "w"), indent=1, ensure_ascii=False)
print(len(out["footnotes"]), "footnotes,", len(out["overlays"]), "overlays")
