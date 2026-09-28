"""Find where each parody line was sung inside generated takes (Whisper word timings), for comping."""
import json, re
from difflib import SequenceMatcher

def norm_words(s):
    s = s.lower().replace("phaseone[big]", "phase one big").replace("e/accs", "e accs").replace("metr", "meter")
    s = s.replace("datacenter", "data center").replace("dim-lit", "dim lit")
    return re.sub(r"[^a-z' ]+", " ", s).split()

def load_words(tag):
    w = json.load(open(f"prototypes/work/{tag}/whisper.json"))
    out = []
    for seg in w["segments"]:
        for x in seg.get("words", []):
            for k, part in enumerate(norm_words(x["word"])):
                out.append({"w": part, "start": x["start"], "end": x["end"]})
    return out

def _score(tstr, words, i, j):
    return SequenceMatcher(None, tstr, "".join(x["w"] for x in words[i:j])).ratio()

def best_span(target, words, min_score=0.6):
    """Character-level fuzzy match, so 'outta' ~ 'out of', 'paused' ~ 'pause', 'meter' ~ 'met her'."""
    tw = norm_words(target); tstr = "".join(tw); n = len(tw); best = (0, None, None)
    for i in range(len(words)):
        for L in range(max(1, n - 3), n + 5):
            j = i + L
            if j > len(words): break
            sc = _score(tstr, words, i, j)
            if sc > best[0]: best = (sc, i, j)
    sc, i, j = best
    if i is None or sc < min_score: return sc, None
    changed = True
    while changed:                       # trim or grow edges while the match improves
        changed = False
        for ni, nj in ((i + 1, j), (i, j - 1), (i - 1, j), (i, j + 1)):
            if 0 <= ni < nj <= len(words):
                s2 = _score(tstr, words, ni, nj)
                if s2 > sc + 1e-6: sc, i, j, changed = s2, ni, nj, True
    return sc, (words[i]["start"], words[j-1]["end"], " ".join(x["w"] for x in words[i:j]))
