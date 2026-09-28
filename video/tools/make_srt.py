#!/usr/bin/env python3
"""Timeline + EDL -> an SRT of the sung lyrics, for YouTube closed captions.

    python video/tools/make_srt.py                                  # -> video/build/slow_it_down.en.srt
    python video/tools/make_srt.py video/edl.json video/build/x.srt

One cue per timed lyric line (lead, rap, chant and backing), offset by the EDL's pre_roll so the times
match the final video. A cue starts just before its first word and holds briefly after its last, but
never overlaps the next cue. Stylized spellings ("sloow") are normalized, lines wider than a caption
row are wrapped onto two rows, and each cue is marked with ♪. The "ahoo" ad-libs are left out, as in
the burned-in captions.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BUILD, load_edl, load_timeline  # noqa: E402

LEAD_IN, HOLD, ROW = 0.15, 0.35, 42   # s before the first word, s after the last, max chars per row


def clean(text):
    return re.sub(r"\b([Ss])lo+w", r"\1low", text)


def wrap(text):
    """One row, or two rows split at the comma / ellipsis (else the space) that balances them best."""
    if len(text) <= ROW:
        return [text]

    def rows(i):
        return [text[:i].rstrip(), text[i:].lstrip()]

    spaces = [m.start() for m in re.finditer(" ", text)]
    punct = [m.end() for m in re.finditer(r"(?:,|\.\.\.) ", text)]
    for cands in (punct, spaces):
        if cands:
            best = rows(min(cands, key=lambda i: max(map(len, rows(i)))))
            if max(map(len, best)) <= ROW:
                return best
    return rows(min(spaces, key=lambda i: max(map(len, rows(i)))))


def cues(tl, pre):
    out = []
    for ln in tl["lines"]:
        if not ln["words"]:
            continue
        w0, w1 = ln["words"][0]["start"], max(w["end"] for w in ln["words"])
        out.append(dict(w0=w0, w1=w1, start=w0 - LEAD_IN, end=w1 + HOLD, text=clean(ln["text"])))
    out.sort(key=lambda c: c["w0"])
    for a, b in zip(out, out[1:]):
        # hand over at the next line's lead-in, but never cut the current line's last word short
        # unless the next line's first word genuinely starts before it ends
        cut = min(max(b["start"], a["w1"]), b["w0"])
        a["end"], b["start"] = min(a["end"], cut), max(b["start"], cut)
    for c in out:
        c["start"], c["end"] = max(0.0, c["start"] + pre), c["end"] + pre
    return out


def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_srt(cs):
    blocks = []
    for n, c in enumerate(cs, 1):
        rows = wrap(c["text"])
        rows[0] = "♪ " + rows[0]
        rows[-1] += " ♪"
        blocks.append(f"{n}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n" + "\n".join(rows) + "\n")
    return "\n".join(blocks)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("edl", nargs="?", default="video/edl.json")
    ap.add_argument("out", nargs="?", default=str(BUILD / "slow_it_down.en.srt"))
    a = ap.parse_args()
    edl = load_edl(a.edl)
    cs = cues(load_timeline(edl.get("timeline")), float(edl["pre_roll"]))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(to_srt(cs), encoding="utf-8")
    print(f"{a.out}: {len(cs)} cues, {cs[0]['start']:.2f}s to {cs[-1]['end']:.2f}s (pre_roll {edl['pre_roll']}s)")


if __name__ == "__main__":
    main()
