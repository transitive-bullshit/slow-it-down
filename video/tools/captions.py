#!/usr/bin/env python3
"""Lyrics, footnotes and in-world overlays as an ASS script (libass), in the look of docs/05-video-treatment.md.

    python video/tools/captions.py video/timeline.json video/edl.json video/build/captions.ass
    python video/tools/captions.py                      # same defaults (timeline from the EDL)

What it draws (every event is offset by the EDL's pre_roll, so times match the final video).
Look: restrained Blade Runner / 2049 -- small warm captions, sodium amber against steel teal, soft glow.
  lead     warm sodium-amber / tungsten-gold neon (Tilt Neon), one ASS event per word per layer: light
           contrast bed, soft spill, halo, and the tube (cream core, amber edge). Words sit as faint unlit
           glass from the line's start and flicker on gently at each word's start.
           CAPS runs (LOSS DROP, ARMS RACE) become tracked caps, a little bigger, on their own row.
  backing  "Down, down, down": steel-teal / pale-cyan neon script, dimmer than the lead; each "down" lands
           one step lower and further right (a staircase that continues across back-to-back backing
           lines) and fades as it falls.
  rap      gold-chrome Didone caps (Abril Fatface): ~2 px clipped bands interpolate a warm mirror gradient,
           a bevel rim, a soft blurred shadow; each word slams in (138% -> 97% -> 100% over 5 frames).
  chant    small, widely tracked Playfair italic on a soft dark bed, fading in word by word.
  footnote thin, low-contrast IBM Plex Mono Light in pale warm off-white with a 1 px elbow leader drawn
           on from the anchor word; in letterboxed shots it sits in the matte.
  overlay  in-world text tied to a shot: led (amber split-flap board; "A → B" counts or flips),
           tag (steel-teal version pill), thought (warm handwritten words), hud (steel-teal reticle/label).
           Overlays with "enabled": false (text now painted into the keyframes) need --all-overlays.

Placement follows the covering shot's caption_zone; a line that crosses a cut into a shot with a
different zone is split at the cut. Letterboxed shots keep text inside the 2.39:1 picture. A line
shows from 0.15 s before its first word to 0.35 s after its last, clipped so it never overlaps the
next line in the same zone. Overlays avoid the zones the lyrics use during the shot
(hint -> opposite -> any free zone).

Layout is done here, word by word, with HarfBuzz metrics that match libass (\\fs N makes
winAscent + winDescent = N px); burn it with ffmpeg's `ass` filter (shaping=complex) so kerning
matches -- the `subtitles` filter drops the script's "Kerning: yes" header.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import re
import sys
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (BUILD, Font, ass_escape, ass_header, c, load_edl, load_json, load_timeline,  # noqa: E402
                    overlay_enabled, rel, song_duration)

# --------------------------------------------------------------------------- look

# Restrained Blade Runner look: sodium amber / tungsten gold against steel teal; neon only as soft accents.
LEAD_PAL = dict(core="#FFF1D6", edge="#FFB54E", halo="#FF9E36", spill="#E57A22",
                ghost_fill="#D8C6AC", ghost_edge="#B89C78")
EMPH_PAL = dict(core="#FFF8EA", edge="#FFC266", halo="#FFA945", spill="#F08C2E")
BACK_PAL = dict(core="#DCF5F2", edge="#8ACFCB", halo="#5AAFB1", spill="#2F8A93")
CHROME_STOPS = [  # warm gold-chrome, top -> bottom of the capitals: sky, brass, dark horizon, warm bounce
    (0.00, "#FFFBF2"), (0.18, "#F5E8CD"), (0.36, "#D9C199"), (0.47, "#A3875D"), (0.505, "#3A2E21"),
    (0.545, "#52432F"), (0.575, "#FFF2DA"), (0.66, "#FFF8EC"), (0.82, "#D0B78C"), (0.94, "#A68B62"),
    (1.00, "#CBB389")]
CHROME_BAND_PX = 2.0


def chrome_at(k):
    k = max(0.0, min(1.0, k))
    for (k0, c0), (k1, c1) in zip(CHROME_STOPS, CHROME_STOPS[1:]):
        if k <= k1:
            t = (k - k0) / max(1e-6, k1 - k0)
            a0 = [int(c0[i:i + 2], 16) for i in (1, 3, 5)]
            a1 = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
            return "#%02X%02X%02X" % tuple(round(x + (y - x) * t) for x, y in zip(a0, a1))
    return CHROME_STOPS[-1][1]


CHANT = dict(fill="#EFE7DA", shadow="#000000")
FOOT = dict(text="#EADFC8", leader="#EADFC8", halo="#000000")

LEAD = dict(role="neon", fs_wide=78, fs_side=70, emph_role="neon", emph_cap=1.18, emph_fsp=5.0,
            max_wide=1000, max_side=620, fade_out=0.24, pre=0.15, post=0.35)
RAP = dict(role="chrome", fs_wide=74, fs_side=62, max_wide=1150, max_side=660, fade_out=0.18,
           edge=0.08)   # rap stays >= 8% inside the frame edges (the fisheye grade bends the edges)
CHANT_CFG = dict(role="serif_italic", fs=46, fsp=7)
BACKING = dict(role="neon_script", fs=116, shrink=0.95, dx=108, dy=52, life=1.5,
               slots=3,           # staircase positions; back-to-back lines reuse them
               fs_band=92,        # upper/lower-zone staircases live in the lead band: smaller type...
               dy_min=15,         # ...shrunk until each step drops at least this much
               dx_band=104,
               band_default=110,  # band height when no lead block is showing in the zone
               dx_side=72)        # side zones: a compact staircase centred under the lead block
FOOT_CFG = dict(role="mono_light", fs=25, wrap=64)

BED_ALPHA = 0xB8            # contrast bed under lit neon (0x00 opaque .. 0xFF invisible)
EMPHASIS_MIN_LEN = 4        # an all-caps word this long (or a run containing one) is emphasis, not an acronym
FRAME = 1 / 24              # set from the EDL's fps in Captions.__init__


def fl(t):          # the start time as libass sees it (ASS stores centiseconds; we floor)
    return math.floor(t * 100 + 1e-4) / 100


def fmt_t(t):
    cs = math.floor(t * 100 + 1e-4)
    h, cs = divmod(max(cs, 0), 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def rng(*key) -> float:
    """Deterministic 0..1 'random' from a key (stable across runs)."""
    h = hashlib.md5(repr(key).encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def lerp(x, y, k):
    return x + (y - x) * k


def alpha_hex(v):   # int 0..255 -> '&HAA&'
    return f"&H{int(max(0, min(255, round(v)))):02X}&"


# --------------------------------------------------------------------------- data

@dataclass
class WordBox:
    text: str
    x: float
    base: float
    w: float
    fs: float
    role: str
    emph: bool
    t_on: float
    t_end: float
    row: int = 0
    fsp: float = 0.0

    @property
    def font(self):
        return Font(self.role)

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):     # vertical centre of the line box (what \an5 anchors to)
        f = self.font
        return self.base + (f.descent(self.fs) - f.ascent(self.fs)) / 2

    @property
    def cap_top(self):
        return self.base - self.font.cap(self.fs)


@dataclass
class Placed:
    idx: int
    kind: str
    zone: str
    letterbox: bool
    on: float
    off: float
    words: list = field(default_factory=list)
    bbox: tuple = (0, 0, 0, 0)
    nrows: int = 1


class Frame:
    """Safe areas for a 1920x1080 frame, with or without the 2.39:1 letterbox."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.bar = round((h - w / 2.39) / 2)          # 138 px at 1920x1080
        self.x0, self.x1 = round(w * 0.0625), round(w * 0.9375)

    def top(self, lb):
        return (self.bar + 44) if lb else 92

    def bottom(self, lb):
        return (self.h - self.bar - 40) if lb else self.h - 96

    def mid(self, lb):
        return self.h / 2


# --------------------------------------------------------------------------- text utils

def clean_word(t):
    return ass_escape(t.strip())


def is_caps(t):
    core = re.sub(r"[^A-Za-z]", "", t)
    return len(core) >= 2 and core.isupper()


def emphasis_flags(words):
    """CAPS runs that contain a word of >= EMPHASIS_MIN_LEN letters (LOSS DROP, ARMS RACE; not AGI/DJ/RL)."""
    caps = [is_caps(w) for w in words]
    flags = [False] * len(words)
    i = 0
    while i < len(words):
        if caps[i]:
            j = i
            while j + 1 < len(words) and caps[j + 1]:
                j += 1
            if any(len(re.sub(r"[^A-Za-z]", "", words[k])) >= EMPHASIS_MIN_LEN for k in range(i, j + 1)):
                for k in range(i, j + 1):
                    flags[k] = True
            i = j + 1
        else:
            i += 1
    return flags


PHRASE_START = {"on", "in", "at", "with", "and", "but", "or", "while", "like", "when", "where", "to", "for",
                "of", "from", "if", "than", "then", "she's", "she", "i", "i'm", "i'd", "you", "girl", "baby",
                "ooh", "now", "just", "except", "cause", "'cause"}
WEAK_END = {"the", "a", "an", "to", "of", "my", "your", "her", "his", "their", "gon'", "i", "i'm", "you",
            "and", "this", "some", "on", "in", "with"}


def best_wrap(widths, space, max_w, ends_punct, emph, max_rows=4, texts=None):
    """Line breaking for lyrics: the fewest rows that fit (or one more if it reads better), keeping
    phrases together (breaks after punctuation / before a new clause, never inside a proper noun,
    never after a weak word like 'the'), then the most even rows."""
    n = len(widths)
    texts = texts or [""] * n
    low = [re.sub(r"[^a-z'’]", "", t.lower()) for t in texts]
    starts_phrase = [w in PHRASE_START for w in low]
    ends_weak = [w in WEAK_END for w in low]
    capital = [bool(re.match(r"^[\"'(]*[A-Z]", t)) and w not in ("i", "i'm", "i'd") for t, w in zip(texts, low)]

    comfy = 0.62 * max_w     # rows up to this wide cost nothing; beyond it, width is penalised

    def cost_of(rows, r_min):
        ws = [sum(widths[a_:b_]) + space * (b_ - a_ - 1) for a_, b_ in rows]
        cost = 0.8 * max(0.0, max(ws) - comfy) + 420 * (len(rows) - r_min)
        if len(rows) > 1:
            cost += 0.25 * (max(ws) - min(ws))
        for a_, b_ in rows[:-1]:
            if ends_punct[b_ - 1]:
                cost -= 220
            if emph[b_] and not emph[b_ - 1]:
                cost -= 650          # a CAPS run gets its own row, like a sign
            if emph[b_ - 1] and not emph[b_]:
                cost -= 120
            if starts_phrase[b_]:
                cost -= 110
            if ends_weak[b_ - 1]:
                cost += 280
            if capital[b_ - 1] and capital[b_] and not ends_punct[b_ - 1]:
                cost += 400          # "Hugging / Face", "DJ / Moloch"
        for a_, b_ in rows:
            if b_ - a_ == 1 and not emph[a_]:
                cost += 260
        return cost, max(ws)

    def fits(rows):
        return max(sum(widths[a_:b_]) + space * (b_ - a_ - 1) for a_, b_ in rows) <= max_w

    def partitions(R):
        for br in combinations(range(1, n), R - 1):
            cuts = (0,) + br + (n,)
            yield [(cuts[k], cuts[k + 1]) for k in range(R)]

    r_min = next((R for R in range(1, min(max_rows, n) + 1) if any(fits(r) for r in partitions(R))), None)
    if r_min is None:
        return [(0, n)]
    best = None
    for R in range(r_min, min(r_min + 1, n) + 1):     # the fewest rows, or one more if it reads better
        for rows in partitions(R):
            if not fits(rows):
                continue
            cost, _ = cost_of(rows, r_min)
            if best is None or cost < best[0]:
                best = (cost, rows)
    return best[1]


# --------------------------------------------------------------------------- the builder

class Captions:
    def __init__(self, tl, edl, annotations=None, shotlist=None, unlit=True, all_overlays=False):
        self.tl, self.edl = tl, edl
        self.W, self.H = edl["size"]
        self.fps = edl["fps"]
        global FRAME
        FRAME = 1 / self.fps
        self.pre = float(edl["pre_roll"])
        self.fr = Frame(self.W, self.H)
        self.unlit = unlit
        self.events = []                         # (layer, start_video, end_video, style, text)
        self.shots = edl["shots"]
        self.shotlist = {s["id"]: s for s in (shotlist or {}).get("shots", [])}
        ann = annotations or {}
        self.footnotes = edl.get("footnotes") or ann.get("footnotes", [])
        self.all_overlays = all_overlays
        self.overlays = edl.get("overlays") or ann.get("overlays", [])
        self.placed: dict[int, Placed] = {}
        self.ov_boxes = []          # (t0, t1, (x0, y0, x1, y1)) of drawn overlays, for the staircases

    # ---- time helpers (song seconds in, video seconds stored)
    def v(self, t_song):
        return t_song + self.pre

    def fq(self, t_song):
        """Snap a song time to the nearest video frame (returns song seconds)."""
        return round(self.v(t_song) * self.fps) / self.fps - self.pre

    def add(self, layer, t0, t1, style, text):
        if t1 - t0 < 0.5 * FRAME:
            return
        self.events.append((layer, self.v(t0), self.v(t1), style, text))

    def ms(self, t_song, ev_start_song):
        return int(round((self.v(t_song) - fl(self.v(ev_start_song))) * 1000))

    def key(self, t_song, ev_start, tags):
        """Tags that take effect exactly at the frame at t_song (1 ms transition, half a frame early)."""
        m = self.ms(t_song, ev_start) - 20
        if m <= 0:
            return tags   # caller prepends to the initial block
        return f"\\t({m},{m + 1},{tags})"

    def ramp(self, t0_song, t1_song, ev_start, tags, accel=None):
        m0 = max(0, self.ms(t0_song, ev_start))
        m1 = max(m0 + 1, self.ms(t1_song, ev_start))
        return f"\\t({m0},{m1},{accel},{tags})" if accel else f"\\t({m0},{m1},{tags})"

    # ---- shots & zones
    def shot_for(self, t0, t1):
        best, ov = None, 0.0
        for s in self.shots:
            o = min(t1, s["end"]) - max(t0, s["start"])
            if o > ov:
                best, ov = s, o
        if best is None:  # nothing overlaps: nearest shot
            mid = (t0 + t1) / 2
            best = min(self.shots, key=lambda s: min(abs(mid - s["start"]), abs(mid - s["end"])), default=None)
        return best

    def zone_for(self, t0, t1):
        s = self.shot_for(t0, t1)
        return (s["caption_zone"], bool(s.get("letterbox"))) if s else ("lower", False)

    # ---- layout
    def layout(self, idx, texts, times, zone, lb, role, fs, emph, max_w, emph_role=None, emph_cap=1.0,
               gap_k=0.46, upper=False, gap_min_k=0.36, side_margin=None):
        fr = self.fr
        x_lo = side_margin if side_margin is not None else fr.x0
        x_hi = self.W - side_margin if side_margin is not None else fr.x1
        items = []
        for tx, e_ in zip(texts, emph):
            r_ = emph_role if (e_ and emph_role) else role
            if e_ and emph_role:
                fs_e = Font(role).cap(fs) * emph_cap / (Font(r_).cap_u / Font(r_).upem) * \
                    (Font(r_).asc_u + Font(r_).desc_u) / Font(r_).upem
            else:
                fs_e = fs
            shown = tx.upper() if upper else tx
            fsp_e = LEAD.get("emph_fsp", 0.0) if (e_ and emph_role) else 0.0
            items.append((shown, r_, fs_e, Font(r_).width(shown, fs_e, fsp=fsp_e)))
        space = max(Font(role).width(" ", fs) * 1.08, gap_min_k * Font(role).cap(fs))
        punct = [bool(re.search(r"[,.;:!?…]$", t)) for t in texts]
        rows = best_wrap([it[3] for it in items], space, max_w, punct, emph, texts=texts)
        # vertical extents per row from the inked glyphs
        row_info = []
        for a_, b_ in rows:
            tops, bots = [], []
            for k in range(a_, b_):
                t_, bt_ = Font(items[k][1]).ink(items[k][0], items[k][2])
                tops.append(t_)
                bots.append(bt_)
            cap = max(Font(items[k][1]).cap(items[k][2]) for k in range(a_, b_))
            row_info.append((min(min(tops), -cap), max(max(bots), 0.18 * cap), cap))
        gap = gap_k * Font(role).cap(fs)
        heights = [bt - tp for tp, bt, _ in row_info]
        block_h = sum(heights) + gap * (len(rows) - 1)
        if zone == "lower":
            y_top = fr.bottom(lb) - block_h
        elif zone == "upper":
            y_top = fr.top(lb)
        else:
            y_top = fr.mid(lb) - block_h / 2

        def gap_after(k):   # next to an emphasis word, size the gap to the bigger face
            if k + 1 < len(items) and (emph[k] or emph[k + 1]) and emph_role:
                big = max((items[j] for j in (k, k + 1) if emph[j]), key=lambda it: it[2])
                return max(space, 0.62 * Font(big[1]).cap(big[2]))
            return space

        widths = [sum(items[k][3] for k in range(a_, b_)) + sum(gap_after(k) for k in range(a_, b_ - 1))
                  for a_, b_ in rows]
        block_w = max(widths)
        cx = {"left": x_lo + block_w / 2, "right": x_hi - block_w / 2}.get(zone, self.W / 2)
        boxes = []
        y = y_top
        for r, ((a_, b_), (tp, bt, _), rw) in enumerate(zip(rows, row_info, widths)):
            base = y - tp
            x = cx - rw / 2
            for k in range(a_, b_):
                shown, r_, fs_k, w_k = items[k]
                fsp_k = LEAD.get("emph_fsp", 0.0) if (emph[k] and emph_role) else 0.0
                boxes.append(WordBox(shown, x, base, w_k, fs_k, r_, emph[k], times[k][0], times[k][1], r, fsp_k))
                x += w_k + gap_after(k)
            y += (bt - tp) + gap
        bbox = (cx - block_w / 2, y_top, cx + block_w / 2, y_top + block_h)
        return boxes, bbox, len(rows)

    # ---- lines
    def zone_at(self, t):
        """(zone, letterbox, shot id) of the shot on screen at song time t."""
        for sh in self.shots:
            if sh["start"] - 1e-6 <= t < sh["end"]:
                return sh["caption_zone"], bool(sh.get("letterbox")), sh["id"]
        z, lb = self.zone_for(t, t + 0.01)
        return z, lb, None

    def split_line(self, ln):
        """Split a line where it crosses a cut into a shot with a different caption zone.
        Returns [(word indices, zone, letterbox)]; tiny fragments stay with their neighbour."""
        ws = ln["words"]
        keys = [self.zone_at(w["start"])[:2] for w in ws]
        parts = []
        for i, k in enumerate(keys):
            if parts and parts[-1][1] == k:
                parts[-1][0].append(i)
            else:
                parts.append(([i], k))

        def weak(pt):
            idx = pt[0]
            return len(idx) == 1 or (ws[idx[-1]]["end"] - ws[idx[0]]["start"]) < 0.55

        changed = True
        while changed and len(parts) > 1:
            changed = False
            for j, pt in enumerate(parts):
                if weak(pt):
                    nb = j - 1 if j > 0 else j + 1
                    lo, hi = sorted((j, nb))
                    keep = parts[nb][1]
                    merged = (parts[lo][0] + parts[hi][0], keep)
                    parts[lo:hi + 1] = [merged]
                    changed = True
                    break
        if len(parts) == 1:   # one block: the zone of the shot that covers most of the line
            z, lb = self.zone_for(ws[0]["start"], max(w["end"] for w in ws))
            return [(list(range(len(ws))), z, lb)]
        return [(idx, z, lb) for idx, (z, lb) in parts]

    def build_lines(self):
        L = self.tl["lines"]
        main = []
        for i, ln in enumerate(L):
            if ln["kind"] == "backing" or not ln["words"]:
                continue
            pre = 0.35 if ln["kind"] == "chant" else LEAD["pre"]
            for widx, zone, lb in self.split_line(ln):
                ws = [ln["words"][k] for k in widx]
                on = ws[0]["start"] - pre
                off = max(w["end"] for w in ws) + LEAD["post"]
                pl = Placed(i, ln["kind"], zone, lb, on, off)
                pl.widx = widx
                main.append(pl)
        main.sort(key=lambda p: p.on)
        # never overlap the next line in the same zone
        for k, p in enumerate(main):
            for q in main[k + 1:]:
                if q.on >= p.off:
                    break
                if q.zone == p.zone:
                    last_start = max(L[p.idx]["words"][wi]["start"] for wi in p.widx)
                    p.off = max(q.on - FRAME, last_start + 0.25)
                    break
        for p in main:              # never hang over a cut into a shot with a different zone
            last_start = max(L[p.idx]["words"][wi]["start"] for wi in p.widx)
            z, lb_, _ = self.zone_at(last_start)
            p.cut = None
            if z == p.zone and bool(lb_) == bool(p.letterbox):
                p.cut = self.zone_run_end(last_start)
                p.off = min(p.off, max(p.cut, last_start + 0.25))
        self.parts = main
        self.word_boxes = {}
        for p in main:
            ln = L[p.idx]
            words = [ln["words"][k] for k in p.widx]
            texts = [clean_word(w["text"]) for w in words]
            times, prev = [], -1e9
            for w in words:
                s_ = max(w["start"], prev)      # reveal order never goes backwards
                times.append((s_, max(w["end"], s_)))
                prev = s_
            side = p.zone in ("left", "right")
            sh = self.shot_for(words[0]["start"], max(w["end"] for w in words))
            inset = float((sh or {}).get("caption_inset") or 0.0)
            inset_px = round(self.W * inset) if inset else None
            if p.kind == "rap":
                boxes, bbox, n = self.layout(p.idx, texts, times, p.zone, p.letterbox, RAP["role"],
                                             RAP["fs_side" if side else "fs_wide"], [False] * len(texts),
                                             RAP["max_side" if side else "max_wide"], upper=True, gap_k=0.36,
                                             gap_min_k=0.58, side_margin=max(round(self.W * RAP["edge"]), inset_px or 0))
            elif p.kind == "chant":
                fs = CHANT_CFG["fs"]
                boxes, bbox, n = self.layout(p.idx, texts, times, p.zone, p.letterbox, CHANT_CFG["role"], fs,
                                             [False] * len(texts), 1400, side_margin=inset_px)
                self._apply_tracking(boxes, CHANT_CFG["fsp"])   # widths += \fsp, re-centre rows
            else:
                emph = emphasis_flags([clean_word(w["text"]) for w in ln["words"]])
                emph = [emph[k] for k in p.widx]
                boxes, bbox, n = self.layout(p.idx, texts, times, p.zone, p.letterbox, LEAD["role"],
                                             LEAD["fs_side" if side else "fs_wide"], emph,
                                             LEAD["max_side" if side else "max_wide"],
                                             emph_role=LEAD["emph_role"], emph_cap=LEAD["emph_cap"],
                                             side_margin=inset_px)
            p.words, p.bbox, p.nrows = boxes, bbox, n
            for wi, b in zip(p.widx, boxes):
                self.word_boxes[(p.idx, wi)] = (p, b)
            self.placed.setdefault(p.idx, p)
            {"rap": self.draw_rap, "chant": self.draw_chant}.get(p.kind, self.draw_lead)(p)
        return main

    def _apply_tracking(self, boxes, fsp):
        rows = {}
        for b in boxes:
            rows.setdefault(b.row, []).append(b)
        for bs in rows.values():
            cx = (bs[0].x + bs[-1].x + bs[-1].w) / 2
            for b in bs:
                b.w += fsp * len(b.text)
            space = Font(bs[0].role).width(" ", bs[0].fs) * 1.08 + fsp
            total = sum(b.w for b in bs) + space * (len(bs) - 1)
            x = cx - total / 2
            for b in bs:
                b.x = x
                x += b.w + space

    # ---- lead neon
    FLICKER = [(.6, .15, 1, .5, 1), (1, .35, 1), (.5, 1, .3, 1), (1, 1, .4, 1), (.8, .2, .9, 1), (1, .55, 1, 1)]

    def draw_lead(self, p):
        for k, wb in zip(p.widx, p.words):
            self.neon_word(wb, p.on, p.off, EMPH_PAL if wb.emph else LEAD_PAL, seed=(p.idx, k), emph=wb.emph)

    def neon_word(self, wb, on, off, pal, seed, emph=False, layer0=0, ghost=None, style="Neon"):
        ghost = self.unlit if ghost is None else ghost
        style = "NeonSign" if wb.role == "neon_sign" else ("NeonScript" if wb.role == "neon_script" else style)
        f = wb.font
        cap = f.cap(wb.fs)
        rev = max(self.fq(wb.t_on), self.fq(on))
        if rev >= off - FRAME:
            return
        pat = self.FLICKER[int(rng("flk", *seed) * len(self.FLICKER))]
        pos = f"\\an5\\pos({wb.cx:.1f},{wb.cy:.1f})\\fs{wb.fs:.1f}" + (f"\\fsp{wb.fsp:.1f}" if wb.fsp else "")
        fade = f"\\fad(0,{int(LEAD['fade_out'] * 1000)})"
        k_spill = 1.15 if emph else 1.0
        spill_b, spill_bl, spill_a = 0.44 * cap * k_spill, 0.52 * cap * k_spill, 0xC4 if not emph else 0xB0
        halo_b, halo_bl, halo_a = 0.15 * cap, 0.18 * cap, 0x78 if not emph else 0x60
        edge_b, edge_bl = max(1.6, 0.06 * cap), max(1.3, 0.06 * cap)
        steps = [rev + i * FRAME for i in range(len(pat))]
        settle = steps[-1] + FRAME
        # stutter: an occasional one-frame dip later on (a tired tube)
        stut = None
        if rng("stut", *seed) < 0.14 and off - rev > 1.2:
            stut = self.fq(lerp(rev + 0.55, off - 0.45, rng("stut_t", *seed)))

        # spill + halo glow (outline only; the fill stays transparent)
        for lay, (col, b, bl, tgt) in enumerate([(pal["spill"], spill_b, spill_bl, spill_a),
                                                 (pal["halo"], halo_b, halo_bl, halo_a)]):
            t0 = rev
            init = f"{pos}\\bord{b:.1f}\\blur{bl:.1f}\\1a&HFF&\\3c{c(col)}\\3a&HFF&\\shad0"
            tr = ""
            for st, pv in zip(steps, pat):
                val = lerp(0xFF, tgt + (0xFF - tgt) * 0.35, pv)     # glow comes up behind the core
                tag = f"\\3a{alpha_hex(val)}"
                kk = self.key(st, t0, tag)
                if kk.startswith("\\t"):
                    tr += kk
                else:
                    init += kk
            if emph:  # ignition flash: brighter and wider, then settle
                tr += self.key(settle, t0, f"\\3a{alpha_hex(max(0, tgt - 0x38))}\\bord{b * 1.25:.1f}")
                tr += self.ramp(settle + FRAME, settle + 0.45, t0, f"\\3a{alpha_hex(tgt)}\\bord{b:.1f}", 0.6)
            else:
                tr += self.ramp(settle, settle + 0.22, t0, f"\\3a{alpha_hex(tgt)}")
            if stut:
                tr += self.key(stut, t0, "\\3a&HF0&") + self.key(stut + FRAME, t0, f"\\3a{alpha_hex(tgt)}")
            self.add(layer0 + 1 + lay, t0, off, style, "{" + init + tr + fade + "}" + wb.text)

        # the tube: crisp hot core with a soft coloured edge
        t0 = self.fq(on) if ghost else rev
        if ghost:
            init = (f"{pos}\\bord1.1\\blur0.9\\shad0\\1c{c(pal.get('ghost_fill', '#C8B0BE'))}"
                    f"\\3c{c(pal.get('ghost_edge', '#8A6A7A'))}\\1a&HFF&\\3a&HDE&")
            fade = f"\\fad(140,{int(LEAD['fade_out'] * 1000)})"
        else:
            init = f"{pos}\\bord{edge_b:.1f}\\blur{edge_bl:.1f}\\shad0\\1c{c(pal['core'])}\\3c{c(pal['edge'])}\\alpha&HFF&"
        tr = ""
        for n_, (st, pv) in enumerate(zip(steps, pat)):
            val = lerp(0xB0, 0x00, pv)
            tag = f"\\alpha{alpha_hex(val)}"
            if n_ == 0:
                tag = f"\\1c{c(pal['core'])}\\3c{c(pal['edge'])}\\bord{edge_b:.1f}" + tag
                if emph:
                    tag += "\\fscx108\\fscy108"
            kk = self.key(st, t0, tag)
            if kk.startswith("\\t"):
                tr += kk
            else:
                init += kk
        if emph:
            tr += self.ramp(rev + FRAME, rev + 0.19, t0, "\\fscx100\\fscy100", 0.7)
        if stut:
            tr += self.key(stut, t0, "\\alpha&H90&") + self.key(stut + FRAME, t0, "\\alpha&H00&")
        self.add(layer0 + 3, t0, off, style, "{" + init + tr + fade + "}" + wb.text)
        # contrast bed: a soft dark cloud under the lit word so neon holds up over bright/red frames
        self.add(layer0, rev, off, style,
                 f"{{{pos}\\bord{0.34 * cap * k_spill:.1f}\\blur{0.62 * cap * k_spill:.1f}\\1a&HFF&\\3c&H0A0508&"
                 f"\\3a&HFF&\\shad0" + self.ramp(rev, rev + 0.14, rev, f"\\3a{alpha_hex(BED_ALPHA)}") + f"{fade}}}{wb.text}")

    # ---- chant (intro): small, spaced, italic, soft
    def draw_chant(self, p):
        fsp = CHANT_CFG["fsp"]
        end = p.off + 0.25
        drift = 12.0   # the whole line floats up this much over its life, words stay on one baseline
        for k, wb in enumerate(p.words):
            t_in = max(self.fq(wb.t_on) - 0.10, p.on)
            x = wb.x
            yb = wb.base + wb.font.descent(wb.fs)
            y1 = yb - drift * (t_in - p.on) / max(0.1, end - p.on)
            txt = (f"{{\\an1\\fs{wb.fs}\\fsp{fsp}\\bord3.4\\3c&H000000&\\3a&H6C&\\shad0\\blur3.0"
                   f"\\1c{c(CHANT['fill'])}\\1a&H18&"
                   f"\\move({x:.1f},{y1:.1f},{x:.1f},{yb - drift:.1f})"
                   f"\\fad(420,520)}}{wb.text}")
            self.add(8, t_in, end, "Chant", txt)

    # ---- rap chrome
    def draw_rap(self, p):
        rows = {}
        for wb in p.words:
            rows.setdefault(wb.row, []).append(wb)
        for r, bs in rows.items():
            tops, bots = zip(*[b.font.ink(b.text, b.fs) for b in bs])
            base = bs[0].base
            top, bot = base + min(tops), base + max(max(bots), 0)
            cap_bot = base
            for k, wb in enumerate(bs):
                self.chrome_word(wb, p, top, cap_bot, bot, seed=(p.idx, r, k))

    def chrome_word(self, wb, p, top, cap_bot, bot, seed):
        t0 = max(self.fq(wb.t_on), self.fq(p.on))
        off = p.off
        if t0 >= off - FRAME:
            return
        s0 = 138
        pos = f"\\an5\\pos({wb.cx:.1f},{wb.cy:.1f})\\fs{wb.fs:.1f}"
        slam = (f"\\fscx{s0}\\fscy{s0}" + self.ramp(t0, t0 + 3 * FRAME, t0, "\\fscx97\\fscy97", 1.6)
                + self.ramp(t0 + 3 * FRAME, t0 + 5 * FRAME, t0, "\\fscx100\\fscy100"))
        fade = f"\\fad(0,{int(RAP['fade_out'] * 1000)})"
        # soft drop shadow (a blurred offset copy), then the dark bronze body + rim
        self.add(9, t0, off, "Chrome",
                 f"{{\\an5\\pos({wb.cx + 0.035 * wb.fs:.1f},{wb.cy + 0.05 * wb.fs:.1f})\\fs{wb.fs:.1f}{slam}"
                 f"\\1c&H000000&\\3c&H000000&\\1a&H70&\\3a&H70&\\bord{0.03 * wb.fs:.1f}\\blur{0.06 * wb.fs:.1f}"
                 f"\\shad0{fade}}}{wb.text}")
        self.add(10, t0, off, "Chrome",
                 f"{{{pos}{slam}\\1c{c('#34281C')}\\3c{c('#150F09')}\\bord{0.03 * wb.fs:.1f}\\blur0.7"
                 f"\\shad0{fade}}}{wb.text}")
        # bevel rim: a bright copy nudged up-left peeks out along the top edges
        self.add(10, t0, off, "Chrome",
                 f"{{\\an5\\pos({wb.cx - 1.2:.1f},{wb.cy - 1.6:.1f})\\fs{wb.fs:.1f}{slam}\\1c&HFFFFFF&\\bord0\\shad0"
                 f"\\blur0.6\\1a&H30&{fade}}}{wb.text}")
        # mirror gradient: thin clipped bands, colours interpolated along the chrome profile
        h = cap_bot - top
        nb = max(8, int(round(h / CHROME_BAND_PX)))
        for i in range(nb):
            k0, k1 = i / nb, (i + 1) / nb
            y0 = top + k0 * h if i > 0 else top - 0.6 * wb.fs
            y1 = top + k1 * h if i < nb - 1 else bot + 0.6 * wb.fs
            col = chrome_at((k0 + k1) / 2)
            self.add(11, t0, off, "Chrome",
                     f"{{{pos}{slam}\\clip(0,{y0:.2f},{self.W},{y1 + 0.35:.2f})\\1c{c(col)}\\bord0\\shad0"
                     f"\\blur0.4{fade}}}{wb.text}")
        # hit flash
        self.add(12, t0, t0 + 0.25, "Chrome",
                 f"{{{pos}{slam}\\1c{c('#FFF4E0')}\\bord{0.02 * wb.fs:.1f}\\3c{c('#FFE2B0')}\\blur2.5\\shad0\\alpha&H60&"
                 + self.ramp(t0 + FRAME, t0 + 0.22, t0, "\\alpha&HFF&") + f"}}{wb.text}")

    # ---- backing staircase
    def zone_run_end(self, t):
        """End (song s) of the run of contiguous shots with the same caption zone + letterbox as the shot
        at time t: the cut after which text laid out for this zone could land on a face."""
        idx = next((i for i, sh in enumerate(self.shots) if sh["start"] - 1e-6 <= t < sh["end"]), None)
        if idx is None:
            return t + 10.0
        key = (self.shots[idx]["caption_zone"], bool(self.shots[idx].get("letterbox")))
        end = self.shots[idx]["end"]
        for sh in self.shots[idx + 1:]:
            if abs(sh["start"] - end) > 0.05 or (sh["caption_zone"], bool(sh.get("letterbox"))) != key:
                break
            end = sh["end"]
        return end

    def build_backing(self):
        """Backing "Down, down, down" lines -> staircases.

        Each backing line's words take the slots of a 3-step staircase (each successive "down" one step
        lower and one step right); back-to-back lines reuse the slots, and every word fades before the
        next word that needs its slot. The staircase is laid out per zone segment: it re-seeds wherever
        the backing crosses a cut into a shot with a different caption zone, and no word outlives the
        shot run it was laid out for.
          upper / lower zone -> band layout: inside the lead block's band (never above a lower-zone lead
                                block's top edge, never below an upper-zone block's bottom edge), beside the
                                lead text, clear of the letterbox bars.
          left / right / center -> column layout: below the lead block, inside its column."""
        L = self.tl["lines"]
        cfg = BACKING
        lines = []
        for i, ln in enumerate(L):
            if ln["kind"] != "backing" or not ln["words"]:
                continue
            if lines and ln["words"][0]["start"] < L[lines[-1]]["words"][-1]["start"] - 0.05:
                continue  # duplicate detection of the same take (overlapping) -> skip
            lines.append(i)
        groups = []
        for i in lines:
            if groups and L[i]["words"][0]["start"] - L[groups[-1][-1]]["words"][-1]["end"] <= 0.6:
                groups[-1].append(i)
            else:
                groups.append([i])
        self.staircases = []
        for g in groups:
            words, prev = [], -1e9
            for li in g:
                for wi, w in enumerate(L[li]["words"]):
                    t = max(w["start"], prev + 0.22)
                    prev = t
                    t_on = self.fq(t)
                    zone, lb, _ = self.zone_at(t_on + 0.01)
                    words.append(dict(line=li, slot=wi % cfg["slots"], text=clean_word(w["text"]).rstrip(",."),
                                      t_on=t_on, zone=zone, lb=bool(lb), run_end=self.zone_run_end(t_on + 0.01)))
            segs = []
            for w in words:        # re-seed at every cut into a different zone
                key = (w["zone"], w["lb"], w["run_end"])
                if segs and segs[-1]["key"] == key:
                    segs[-1]["words"].append(w)
                else:
                    segs.append(dict(key=key, zone=w["zone"], lb=w["lb"], words=[w]))
            for sg in segs:
                ws = sg["words"]
                for k, w in enumerate(ws):
                    t_off = w["t_on"] + cfg["life"] * (0.94 ** w["slot"])
                    nxt = next((v for v in ws[k + 1:] if v["slot"] == w["slot"]), None)
                    if nxt is not None:
                        t_off = min(t_off, nxt["t_on"] - 0.06)
                    t_off = min(t_off, w["run_end"])          # never outlive the zone's shot run
                    w["t_off"] = max(t_off, w["t_on"] + 2 * FRAME)
                self.draw_staircase(sg, g)

    def _visible_blocks(self, t0, t1):
        return [p for p in self.parts if p.on < t1 and p.off > t0]

    def draw_staircase(self, sg, g):
        cfg = BACKING
        ws = sg["words"]
        used = sorted({w["slot"] for w in ws})
        t0, t1 = ws[0]["t_on"], max(w["t_off"] for w in ws)
        visible = self._visible_blocks(t0, t1)
        if sg["zone"] in ("upper", "lower"):
            pos, fs_list, drift = self.band_layout(sg["zone"], sg["lb"], visible, t0, t1, used, ws)
        else:
            pos, fs_list, drift = self.column_layout(sg["zone"], sg["lb"], visible, used, ws)
        f = Font(cfg["role"])
        for w in ws:
            j = used.index(w["slot"])
            cx, base = pos[j]
            fs = fs_list[j]
            wd = f.width(w["text"], fs)
            wb = WordBox(w["text"], cx - wd / 2, base, wd, fs, cfg["role"], False, w["t_on"], w["t_off"])
            dim = 0x38 + min(0x40, 0x0A * j)      # always dimmer than the lead, fading as it descends
            self.backing_word(wb, w["t_on"], w["t_off"], dim, seed=(tuple(g), w["line"], w["slot"]), drift=drift)
            self.staircases.append(dict(zone=sg["zone"], t_on=w["t_on"], t_off=w["t_off"], text=w["text"],
                                        box=(wb.x, base + f.ink(w["text"], fs)[0], wb.x + wd, base + f.ink(w["text"], fs)[1])))

    def band_layout(self, zone, lb, visible, t0, t1, used, ws):
        """Staircase inside an upper/lower lead band, beside the lead text: to its right if there's room,
        else to its left (still stepping down and right). The type shrinks until the steps both drop
        enough to read and fit beside the text without words touching."""
        fr, cfg = self.fr, BACKING
        f = Font(cfg["role"])
        m = len(used)
        same = [p for p in visible if p.zone == zone]
        if zone == "lower":
            b_bot = (self.H - fr.bar - 8) if lb else (self.H - 44)
            b_top = min([p.bbox[1] for p in same] or [fr.bottom(lb) - cfg["band_default"]])
        else:
            b_top = (fr.bar + 8) if lb else 44
            b_bot = max([p.bbox[3] for p in same] or [fr.top(lb) + cfg["band_default"]])
        obs = [(p.bbox[0], p.bbox[2]) for p in visible if p.bbox[1] < b_bot and p.bbox[3] > b_top]
        obs += [(b[0], b[2]) for (a0, a1, b) in getattr(self, "ov_boxes", [])
                if a0 < t1 and a1 > t0 and b[1] < b_bot and b[3] > b_top]
        free = free_intervals(fr.x0, fr.x1, obs, pad=44)
        slot_text = {sl: max((w["text"] for w in ws if w["slot"] == sl), key=len) for sl in used}
        best = None
        for k in range(14):
            fs = cfg["fs_band"] * (0.95 ** k)
            texts = [slot_text[sl] for sl in used]
            inks = [f.ink(t, fs) for t in texts]
            ink_t, ink_b = min(i[0] for i in inks), max(i[1] for i in inks)
            ink_h = ink_b - ink_t
            drift = 0.05 * f.cap(fs)
            band_h = (b_bot - b_top) - drift
            dy = (band_h - ink_h) / max(1, m - 1) if m > 1 else 0.0
            dy = max(0.0, min(dy, cfg["dy"]))
            widths = [f.width(t, fs) for t in texts]
            if dy >= 0.9 * ink_h:          # steps clear each other vertically: a regular stride
                gaps = [cfg["dx_band"]] * (m - 1)
            else:                          # shallow steps: space by the words' widths so they never touch
                gaps = [widths[j] / 2 + widths[j + 1] / 2 + 12 for j in range(m - 1)]
            need = sum(gaps) + widths[0] / 2 + widths[-1] / 2
            if not obs:
                place = ("c", (self.W / 2 - need / 2, self.W / 2 + need / 2))
            else:
                right = [iv for iv in free if iv[0] >= max(o[1] for o in obs) and iv[1] - iv[0] >= need]
                left = [iv for iv in free if iv[1] <= min(o[0] for o in obs) and iv[1] - iv[0] >= need]
                place = ("r", right[-1]) if right else (("l", left[0]) if left else None)
            ok = (m == 1 or dy >= cfg["dy_min"]) and place is not None
            best = (fs, ink_t, ink_b, drift, dy, widths, gaps, need, place)
            if ok:
                break
        fs, ink_t, ink_b, drift, dy, widths, gaps, need, place = best
        if place is None:   # last resort: the widest gap, words may sit closer than ideal
            iv = max(free, key=lambda v: v[1] - v[0]) if free else (fr.x0, fr.x1)
            place = ("r", iv)
        side, iv = place
        x_first = (iv[0] + widths[0] / 2) if side == "r" else (iv[1] - need + widths[0] / 2)
        if side == "c":
            x_first = iv[0] + widths[0] / 2
        xs = [x_first]
        for gp in gaps:
            xs.append(xs[-1] + gp)
        if zone == "lower":                      # descend to the band's bottom edge
            base_last = b_bot - drift - ink_b
            bases = [base_last - dy * (m - 1 - j) for j in range(m)]
        else:                                    # start at the band's top edge
            bases = [b_top - ink_t + dy * j for j in range(m)]
        return list(zip(xs, bases)), [fs] * m, drift

    def column_layout(self, zone, lb, visible, used, ws):
        """Side/center zones: a compact staircase just below the lead block (never above it), centred
        under the block and kept inside its column, stepping down and right. Centring keeps it off both
        the subject (toward frame centre) and frame-edge foreground (e.g. an over-the-shoulder head)."""
        fr, cfg = self.fr, BACKING
        f = Font(cfg["role"])
        m = len(used)
        fs0 = cfg["fs"]
        same = [p for p in visible if p.zone == zone]
        if same:
            bx0 = min(p.bbox[0] for p in same)
            bx1 = max(p.bbox[2] for p in same)
            by1 = max(p.bbox[3] for p in same)
        else:
            col_w = 560
            bx0 = fr.x0 if zone == "left" else (fr.x1 - col_w if zone == "right" else self.W / 2 - col_w / 2)
            bx1 = bx0 + col_w
            by1 = self.H / 2
        slot_text = {sl: max((w["text"] for w in ws if w["slot"] == sl), key=len) for sl in used}
        fss = [fs0 * cfg["shrink"] ** j for j in range(m)]
        texts = [slot_text[sl] for sl in used]
        widths = [f.width(t, fs) for t, fs in zip(texts, fss)]
        inks = [f.ink(t, fs) for t, fs in zip(texts, fss)]
        ink_h = max(b - t for t, b in inks)
        dy = max(cfg["dy"], ink_h + 6)            # steps clear each other vertically
        dx = cfg["dx_side"]
        xs = [dx * j for j in range(m)]
        lo, hi = max(fr.x0, bx0 - 20), min(fr.x1, bx1 + 20)
        ext = lambda: (xs[0] - widths[0] / 2, xs[-1] + widths[-1] / 2)
        e0, e1 = ext()
        if m > 1 and e1 - e0 > hi - lo:           # narrow column: tighten the stride
            dx = max(24.0, (hi - lo - widths[0] / 2 - widths[-1] / 2) / (m - 1))
            xs = [dx * j for j in range(m)]
            e0, e1 = ext()
        shift = (bx0 + bx1) / 2 - (e0 + e1) / 2
        shift = min(max(shift, lo - e0), hi - e1)
        xs = [x + shift for x in xs]
        top = by1 + 0.30 * f.cap(fs0)             # first word's ink top, just under the block
        bot_lim = fr.bottom(lb)
        if m > 1 and top + ink_h + dy * (m - 1) > bot_lim:
            dy = max(0.7 * ink_h, (bot_lim - top - ink_h) / (m - 1))
        bases = [top - inks[0][0] + dy * j for j in range(m)]
        return list(zip(xs, bases)), fss, 0.10 * f.cap(fs0)

    def backing_word(self, wb, t_on, t_off, dim, seed, drift=None):
        f = wb.font
        cap = f.cap(wb.fs)
        pal = BACK_PAL
        pat = self.FLICKER[int(rng("bflk", *seed) * len(self.FLICKER))][:3]
        drift = 0.16 * cap if drift is None else drift
        mv = f"\\move({wb.cx:.1f},{wb.cy:.1f},{wb.cx:.1f},{wb.cy + drift:.1f})"
        life = t_off - t_on
        fade_ms = int(max(0.0, min(life - 0.30, life - 0.08)) * 1000) if life > 0.4 else int(life * 400)
        fade = f"\\fad(0,{fade_ms})"
        layers = [(pal["spill"], 0.46 * cap, 0.50 * cap, 0xB4), (pal["halo"], 0.15 * cap, 0.17 * cap, 0x6C)]
        for lay, (col, b, bl, tgt) in enumerate(layers):
            init = f"{mv}\\fs{wb.fs:.1f}\\bord{b:.1f}\\blur{bl:.1f}\\1a&HFF&\\3c{c(col)}\\shad0"
            tr = ""
            for i, pv in enumerate(pat):
                kk = self.key(t_on + i * FRAME, t_on, f"\\3a{alpha_hex(lerp(0xFF, min(0xFF, tgt + dim), pv))}")
                if kk.startswith("\\t"):
                    tr += kk
                else:
                    init += kk
            self.add(5 + lay, t_on, t_off, "NeonScript", "{" + init + tr + fade + "}" + wb.text)
        init = (f"{mv}\\fs{wb.fs:.1f}\\bord{max(1.8, 0.06 * cap):.1f}\\blur{max(1.2, 0.05 * cap):.1f}\\shad0"
                f"\\1c{c(pal['core'])}\\3c{c(pal['edge'])}")
        tr = ""
        for i, pv in enumerate(pat):
            kk = self.key(t_on + i * FRAME, t_on, f"\\alpha{alpha_hex(lerp(0xC0, dim, pv))}")
            if kk.startswith("\\t"):
                tr += kk
            else:
                init += kk
        self.add(7, t_on, t_off, "NeonScript", "{" + init + tr + fade + "}" + wb.text)
        self.add(4, t_on, t_off, "NeonScript",
                 f"{{{mv}\\fs{wb.fs:.1f}\\bord{0.36 * cap:.1f}\\blur{0.6 * cap:.1f}\\1a&HFF&\\3c&H0A0508&\\3a&HFF&"
                 f"\\shad0" + self.ramp(t_on, t_on + 0.12, t_on, f"\\3a{alpha_hex(min(0xFF, BED_ALPHA + dim))}")
                 + f"{fade}}}{wb.text}")

    # ---- footnotes
    def build_footnotes(self):
        active = []   # (t0, t1, bbox)
        L = self.tl["lines"]
        for fn in sorted(self.footnotes, key=lambda f_: f_["t"]):
            li = fn.get("anchor_line")
            if li is None or li >= len(L) or not L[li]["words"]:
                continue
            ln = L[li]
            if isinstance(fn.get("anchor_word"), int):
                wi = fn["anchor_word"]
            elif isinstance(fn.get("anchor_word"), str):
                wi = next((k for k, w in enumerate(ln["words"])
                           if w["text"].lower().strip(",.!?'").startswith(fn["anchor_word"].lower())), 0)
            else:
                wi = min(range(len(ln["words"])), key=lambda k: abs(ln["words"][k]["start"] - fn["t"]))
            hit = self.word_boxes.get((li, wi))
            if hit is None:
                continue
            p, wb = hit
            t0 = max(self.fq(fn["t"]), self.fq(p.on))
            t1 = min(fn["t"] + fn.get("dur", 2.4), p.off + 0.2)   # never outlive its lyric by much
            t1 = max(t1, min(t0 + 1.5, p.off + 0.6))
            if getattr(p, "cut", None) and p.cut > t0 + 0.4:
                t1 = min(t1, p.cut)                                 # nor hang over a zone-changing cut
            box = self.footnote(fn["text"], wb, p, t0, t1, active)
            active.append((t0, t1, box))

    def footnote(self, text, wb, p, t0, t1, active):
        """Tiny mono note by the anchor word with a thin leader (dot, 45° rise, short run). It stays in
        the caption block's own column (the zone keeps faces clear): the text wraps to the column's
        width, sits above the block (or below, for a bottom-row anchor), beside the leader if it fits,
        else directly over the word on a short vertical tick. In letterboxed shots it can sit in the matte."""
        f = Font(FOOT_CFG["role"])
        fs = FOOT_CFG["fs"]
        lh = fs * 1.02
        bx0, by0, bx1, by1 = p.bbox
        margin = 70 if p.zone in ("left", "right") else 240
        col_lo, col_hi = max(26.0, bx0 - margin), min(self.W - 26.0, bx1 + margin)
        lines, tw = [text], f.width(text, fs)
        for wrap in (FOOT_CFG["wrap"], 52, 44, 38, 32, 28, 24, 20):
            lines = wrap_text(text, wrap)
            tw = max(f.width(l_, fs) for l_ in lines)
            if tw <= col_hi - col_lo:
                break
        th = lh * len(lines)
        last_row = max(w.row for w in p.words)
        top_lim, bot_lim = 26, self.H - 26
        cap = wb.font.cap(wb.fs)
        need = th + 34
        can_above = by0 - need >= top_lim
        can_below = by1 + need <= bot_lim
        if wb.row == 0 and can_above:
            side = "above"
        elif wb.row == last_row and can_below:
            side = "below"
        elif can_above and (wb.row == 0 or not can_below):
            side = "above"
        else:
            side = "below"
        bar = self.fr.bar if p.letterbox else 0
        if side == "above":
            ay = wb.cap_top - 0.22 * cap
            ty = min(ay - 28, by0 - 10 - th / 2)
            if bar and ty - th / 2 < bar + 6:          # would straddle the matte edge -> sit inside the bar
                ty = min(ty, bar - 8 - th / 2)
            ty = max(ty, top_lim + th / 2)
        else:
            ay = wb.base + 0.40 * cap
            ty = max(ay + 28, by1 + 10 + th / 2)
            if bar and ty + th / 2 > self.H - bar - 6:
                ty = max(ty, self.H - bar + 8 + th / 2)
            ty = min(ty, bot_lim - th / 2)
        ax = wb.cx
        run = 24
        vy = -1 if side == "above" else 1

        def place(ty_):
            rise_ = abs(ty_ - ay)
            rx0 = ax + rise_ + run + 10
            lx1 = ax - rise_ - run - 10
            if rx0 + tw <= col_hi:
                return "side", 1, rx0, rise_
            if lx1 - tw >= col_lo:
                return "side", -1, lx1 - tw, rise_
            return "tick", 0, min(max(ax - tw / 2, col_lo), col_hi - tw), rise_

        mode, horiz, box_x0, rise = place(ty)
        for _ in range(4):   # dodge other live notes by stepping further out
            box = (box_x0, ty - th / 2, box_x0 + tw, ty + th / 2)
            if not any(not (t1 <= a0 or t0 >= a1) and _overlap(box, b) for a0, a1, b in active):
                break
            step = th + 12
            if side == "above" and ty - step - th / 2 >= top_lim:
                ty -= step
            elif side == "below" and ty + step + th / 2 <= bot_lim:
                ty += step
            else:
                break
            mode, horiz, box_x0, rise = place(ty)
        box = (box_x0, ty - th / 2, box_x0 + tw, ty + th / 2)
        if mode == "side":
            pts = [(ax, ay), (ax + horiz * rise, ay + vy * rise), (ax + horiz * (rise + run), ay + vy * rise)]
        else:
            edge = ty + th / 2 + 5 if side == "above" else ty - th / 2 - 5
            pts = [(ax, ay), (ax, edge)]
        draw = poly_stroke(pts, 1.1) + " " + circle(ax, ay, 2.4)
        x_lo, x_hi = min(q[0] for q in pts) - 4, max(q[0] for q in pts) + 4
        y_lo, y_hi = min(q[1] for q in pts) - 4, max(q[1] for q in pts) + 4
        clip0 = f"\\clip({ax - 3:.0f},{ay - 3:.0f},{ax + 3:.0f},{ay + 3:.0f})"      # grows out from the dot
        clip1 = f"\\clip({x_lo:.0f},{y_lo:.0f},{x_hi:.0f},{y_hi:.0f})"
        lead_off = min(t1, p.off)
        self.add(20, t0, lead_off, "Draw",
                 f"{{\\an7\\pos(0,0)\\bord0\\shad1\\4c{c(FOOT['halo'])}\\4a&HB0&\\blur0.4\\1c{c(FOOT['leader'])}"
                 f"\\1a&H58&{clip0}" + self.ramp(t0, t0 + 0.18, t0, clip1) + f"\\fad(0,220)\\p1}}{draw}")
        body = "\\N".join(ass_escape(l_) for l_ in lines)
        if mode == "side":
            tx = pts[-1][0] + horiz * 10
            pos = f"\\an{4 if horiz > 0 else 6}\\pos({tx:.1f},{ty:.1f})"
        else:
            pos = f"\\an7\\pos({box_x0:.1f},{ty - th / 2:.1f})"
        self.add(21, t0 + 0.10, t1, "Foot",
                 f"{{{pos}\\fs{fs}\\1c{c(FOOT['text'])}\\1a&H30&\\bord2.0"
                 f"\\3c{c(FOOT['halo'])}\\3a&H98&\\blur2.2\\shad0\\fsp0.6\\fad(260,340)}}{body}")
        return box

    # ---- overlays
    def build_overlays(self):
        for ov in self.overlays:
            if not overlay_enabled(ov, self.all_overlays):
                continue
            shot = next((s for s in self.shots if s["id"] == ov["shot"]), None) or self.shotlist.get(ov["shot"])
            if shot is None:
                print(f"  overlay for unknown shot {ov['shot']} skipped", file=sys.stderr)
                continue
            t0 = ov.get("start", shot["start"])
            t1 = ov.get("end", shot["end"])
            lb = bool(shot.get("letterbox"))
            dur = max(0.01, t1 - t0)
            used = {p.zone for p in self.parts if min(t1, p.off) - max(t0, p.on) >= min(0.6, 0.3 * dur)}
            used.add(shot.get("caption_zone", "lower"))
            zone = pick_zone(ov.get("zone", "upper"), used)
            style = ov.get("style", "led")
            fn = {"led": self.ov_led, "tag": self.ov_tag, "thought": self.ov_thought, "hud": self.ov_hud}.get(style)
            if fn is None:
                print(f"  overlay style {style!r} unknown, skipped", file=sys.stderr)
                continue
            fn(ov, t0, t1, zone, lb)

    def zone_anchor(self, zone, lb, w, h):
        """Top-left for a w x h element in a zone."""
        fr = self.fr
        if zone == "upper":
            return self.W / 2 - w / 2, fr.top(lb) + 6
        if zone == "lower":
            return self.W / 2 - w / 2, fr.bottom(lb) - h
        if zone == "left":
            return fr.x0 + 20, self.H / 2 - h / 2
        if zone == "right":
            return fr.x1 - w - 20, self.H / 2 - h / 2
        return self.W / 2 - w / 2, self.H / 2 - h / 2

    def ov_led(self, ov, t0, t1, zone, lb):
        """Amber split-flap board with warm Nixie-like glyphs. Tiles cascade in left to right, flipping
        through a few characters; "A → B" counts (numbers) or flips (anything else) mid-shot."""
        text = ov["text"]
        a_txt, b_txt, prefix = split_arrow(text)
        t0q, t1q = self.fq(t0), self.fq(t1)
        states = []
        if b_txt is None:
            states = [(t0q, text)]
        elif a_txt.isdigit() and b_txt.isdigit():
            n0, n1 = int(a_txt), int(b_txt)
            width = max(len(a_txt), len(b_txt))
            t_end = t0q + 0.7 * (t1q - t0q)
            steps = max(2, int((t_end - t0q) / (2 * FRAME)))
            last = None
            for i in range(steps + 1):
                val = round(lerp(n0, n1, 1 - (1 - i / steps) ** 2.4))
                st = prefix + str(val).rjust(width)
                if st != last:
                    states.append((t0q + i * 2 * FRAME, st))
                    last = st
        else:
            states = [(t0q, prefix + a_txt), (self.fq(lerp(t0q, t1q, 0.5)), prefix + b_txt)]
        n = max(len(st) for _, st in states)
        states = [(t, st.ljust(n)) for t, st in states]
        f = Font("mono_medium")
        fs = ov.get("size", 44)
        glyph_w = f.width("0", fs)
        tile_w, tile_h, gap = glyph_w + 0.30 * fs, 1.22 * fs, 0.10 * fs
        pad = 0.22 * fs
        board_w, board_h = n * tile_w + (n - 1) * gap + 2 * pad, tile_h + 2 * pad
        x0, y0 = self.zone_anchor(zone, lb, board_w, board_h)
        if "pos" in ov:
            x0, y0 = ov["pos"][0] - board_w / 2, ov["pos"][1] - board_h / 2
        fade = "\\fad(200,260)"
        tiles, splits = [], []
        centers = []
        for i in range(n):
            tx = x0 + pad + i * (tile_w + gap)
            ty = y0 + pad
            tiles.append(rounded_rect(tx, ty, tile_w, tile_h, 0.10 * fs))
            splits.append(f"m {tx:.1f} {ty + tile_h / 2 - 0.9:.1f} l {tx + tile_w:.1f} {ty + tile_h / 2 - 0.9:.1f} "
                          f"{tx + tile_w:.1f} {ty + tile_h / 2 + 0.9:.1f} {tx:.1f} {ty + tile_h / 2 + 0.9:.1f}")
            centers.append((tx + tile_w / 2, ty + tile_h / 2))
        self.ov_boxes.append((t0q, t1q, (x0, y0, x0 + board_w, y0 + board_h)))
        self.add(30, t0q, t1q, "Draw", f"{{\\an7\\pos(0,0)\\bord0\\shad0\\blur3\\1c&H080706&\\1a&H50&{fade}\\p1}}"
                 + rounded_rect(x0, y0, board_w, board_h, 0.16 * fs))
        self.add(31, t0q, t1q, "Draw", f"{{\\an7\\pos(0,0)\\bord0\\shad0\\blur0.6\\1c{c('#1C1814')}\\1a&H18&{fade}\\p1}}"
                 + " ".join(tiles))
        self.add(34, t0q, t1q, "Draw", f"{{\\an7\\pos(0,0)\\bord0\\shad0\\1c&H000000&\\1a&H30&{fade}\\p1}}" + " ".join(splits))
        # per-tile timelines: (start, char, is_flip_frame)
        flap_chars = "0123456789ABCDEFGHJKLMNPRSTUVWXYZ"
        for i in range(n):
            tl_i = []
            prev = None
            for k, (t, st) in enumerate(states):
                ch = st[i]
                if k == 0:
                    ts = t + i * 0.045
                    nflip = 3 + int(rng("flap", text, i) * 3)
                    for j in range(nflip):
                        rc = flap_chars[int(rng("flapc", text, i, j) * len(flap_chars))]
                        tl_i.append((self.fq(ts + j * 2 * FRAME), rc, False))
                        tl_i.append((self.fq(ts + (j * 2 + 1) * FRAME), rc, True))
                    tl_i.append((self.fq(ts + nflip * 2 * FRAME), ch, False))
                elif ch != prev:
                    tl_i.append((t, ch, True))
                    tl_i.append((t + FRAME, ch, False))
                prev = ch
            tl_i.sort(key=lambda e: e[0])
            cx, cy = centers[i]
            for j, (ts, ch, flip) in enumerate(tl_i):
                te = tl_i[j + 1][0] if j + 1 < len(tl_i) else t1q
                if te <= ts or not ch.strip():
                    continue
                sq = "\\fscy52" if flip else ""
                last = j == len(tl_i) - 1
                fd = "\\fad(0,260)" if last else ""
                body = ass_escape(ch)
                self.add(35, ts, te, "Hud", f"{{\\an5\\pos({cx:.1f},{cy:.1f})\\fs{fs}{sq}\\1a&HFF&\\bord3\\blur5"
                         f"\\3c{c('#FF8F2A')}\\3a&H9C&\\shad0{fd}}}{body}")
                self.add(36, ts, te, "Hud", f"{{\\an5\\pos({cx:.1f},{cy:.1f})\\fs{fs}{sq}\\1c{c('#FFDCA8')}"
                         f"\\bord0.8\\3c{c('#FFB060')}\\blur0.8\\shad0{'\\1a&H50&' if flip else ''}{fd}}}{body}")

    def ov_tag(self, ov, t0, t1, zone, lb):
        a_txt, b_txt, prefix = split_arrow(ov["text"])
        f = Font("mono_medium")
        fs = ov.get("size", 32)
        col, core = "#7FC9C3", "#E6FAF7"
        txts = [prefix + a_txt] if b_txt is None else [prefix + a_txt, prefix + b_txt]
        w = max(f.width(t_, fs, fsp=2) for t_ in txts) + 34
        h = f.cap(fs) + 26
        x0, y0 = self.zone_anchor(zone, lb, w, h)
        if zone in ("left", "right"):
            y0 += 90
        if "pos" in ov:
            x0, y0 = ov["pos"][0] - w / 2, ov["pos"][1] - h / 2
        t0q, t1q = self.fq(t0), self.fq(t1)
        self.ov_boxes.append((t0q, t1q, (x0, y0, x0 + w, y0 + h)))
        tm = self.fq(lerp(t0q, t1q, 0.55)) if b_txt else t1q
        fade = "\\fad(180,220)"
        self.add(34, t0q, t1q, "Draw", f"{{\\an7\\pos(0,0)\\bord1.3\\blur1.2\\shad0\\1a&HFF&\\3c{c(col)}\\3a&H30&{fade}\\p1}}"
                 + rounded_rect(x0, y0, w, h, h / 2))
        self.add(34, t0q, t1q, "Draw", f"{{\\an7\\pos(0,0)\\bord5\\blur9\\shad0\\1a&HFF&\\3c{c(col)}\\3a&HB8&{fade}\\p1}}"
                 + rounded_rect(x0, y0, w, h, h / 2))
        cx, cy = x0 + w / 2, y0 + h / 2
        segs = [(t0q, tm, txts[0])]
        if b_txt:   # glitch tick: jitter, scrambled glyph, then the new version
            segs += [(tm, tm + FRAME, "v#"), (tm + FRAME, tm + 2 * FRAME, txts[0]), (tm + 2 * FRAME, tm + 3 * FRAME, "v%"),
                     (tm + 3 * FRAME, t1q, txts[1])]
        for n_, (sa, sb, s_) in enumerate(segs):
            jit = (rng("tag", n_) - 0.5) * 8 if 0 < n_ < len(segs) - 1 else 0
            fd = "\\fad(180,0)" if n_ == 0 else ("\\fad(0,220)" if n_ == len(segs) - 1 else "")
            flash = self.ramp(sa + FRAME, sa + 0.35, sa, "\\3a&H60&\\bord3") if n_ == len(segs) - 1 and b_txt else ""
            self.add(35, sa, sb, "Hud", f"{{\\an5\\pos({cx + jit:.1f},{cy:.1f})\\fs{fs}\\fsp2\\1c{c(core)}\\3c{c(col)}"
                     f"\\bord{2.2 if flash else 3}\\blur2.5\\3a&H{'10' if flash else '60'}&\\shad0{flash}{fd}}}{ass_escape(s_)}")

    def ov_thought(self, ov, t0, t1, zone, lb):
        words = [w_ for w_ in re.split(r"\s{2,}", ov["text"].strip()) if w_]
        fs = ov.get("size", 70)
        t0q, t1q = self.fq(t0), self.fq(t1)
        n = len(words)
        W = min(1100, 360 * n)
        x0, y0 = self.zone_anchor(zone, lb, W, fs * 1.6)
        for k, wd in enumerate(words):
            kx = (k + 0.5) / n
            x = x0 + kx * W + (rng("th_x", wd, k) - 0.5) * 60
            y = y0 + fs * 0.7 + math.sin(kx * math.pi) * -26 + (rng("th_y", wd, k) - 0.5) * 30
            ta = t0q + 0.25 + k * min(0.55, (t1q - t0q) / (n + 1.5))
            dx, dy = (rng("th_dx", k) - 0.5) * 70, -24 - rng("th_dy", k) * 30
            rot0 = (rng("th_r", k) - 0.5) * 10
            mv = f"\\move({x:.0f},{y:.0f},{x + dx:.0f},{y + dy:.0f},0,{int((t1q - ta) * 1000)})"
            body = ass_escape(wd)
            common = f"\\an5{mv}\\fs{fs}\\frz{rot0:.1f}" + self.ramp(ta, t1q, ta, f"\\frz{rot0 * -0.4:.1f}")
            self.add(36, ta, t1q, "Hand", f"{{{common}\\bord8\\blur13\\1a&HFF&\\3c{c('#E8A04A')}\\3a&HB0&\\shad0\\fad(600,450)}}{body}")
            self.add(37, ta, t1q, "Hand", f"{{{common}\\bord1.2\\blur1.2\\1c{c('#FFF4E2')}\\3c{c('#F2C488')}\\1a&H30&\\shad0"
                     f"\\fad(600,450)}}{body}")

    def ov_hud(self, ov, t0, t1, zone, lb):
        label = ov["text"]
        f = Font("mono_medium")
        fs = ov.get("size", 28)
        col, core = "#86CFC9", "#E3F7F4"
        t0q, t1q = self.fq(t0), self.fq(t1)
        tw = f.width(label, fs, fsp=7)
        # reticle towards the frame centre, label out in the zone
        lx, ly = self.zone_anchor(zone, lb, tw + 40, 120)
        if zone == "right":
            rx, ry = lx - 170, ly + 150
            elbow = (lx - 30, ly + 30)
        else:
            rx, ry = lx + tw + 210, ly + 150
            elbow = (lx + tw + 60, ly + 30)
        if "pos" in ov:
            rx, ry = ov["pos"]
        fade = "\\fad(150,250)"
        ret = circle(rx, ry, 17, ring=1.4) + " " + circle(rx, ry, 3) + " " + " ".join(
            poly_stroke([(rx + dx0, ry + dy0), (rx + dx1, ry + dy1)], 1.3)
            for dx0, dy0, dx1, dy1 in [(-30, 0, -21, 0), (21, 0, 30, 0), (0, -30, 0, -21), (0, 21, 0, 30)])
        self.add(38, t0q, t1q, "Draw", f"{{\\an7\\pos(0,0)\\bord0\\shad0\\blur0.5\\1c{c(core)}\\fscx60\\fscy60"
                 f"\\org({rx:.0f},{ry:.0f})" + self.ramp(t0q, t0q + 0.25, t0q, "\\fscx100\\fscy100", 0.5)
                 + f"{fade}\\p1}}{ret}")
        self.add(38, t0q, t1q, "Draw", f"{{\\an7\\pos(0,0)\\bord4\\blur7\\shad0\\1a&HFF&\\3c{c(col)}\\3a&HA0&{fade}\\p1}}{ret}")
        start = (rx + (-19 if zone == 'right' else 19) * 0.8, ry - 12)
        pts = [start, elbow, (lx + (tw + 20 if zone == "right" else -10), ly + 30)]
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        if zone == "right":
            clip0 = f"\\clip({max(xs) - 1:.0f},{min(ys) - 3:.0f},{max(xs) + 3:.0f},{max(ys) + 3:.0f})"
        else:
            clip0 = f"\\clip({min(xs) - 3:.0f},{min(ys) - 3:.0f},{min(xs) + 1:.0f},{max(ys) + 3:.0f})"
        clip1 = f"\\clip({min(xs) - 3:.0f},{min(ys) - 3:.0f},{max(xs) + 3:.0f},{max(ys) + 3:.0f})"
        self.add(38, t0q + 0.12, t1q, "Draw", f"{{\\an7\\pos(0,0)\\bord0\\shad0\\blur0.4\\1c{c(core)}\\1a&H20&{clip0}"
                 + self.ramp(t0q + 0.12, t0q + 0.34, t0q + 0.12, clip1) + f"{fade}\\p1}}" + poly_stroke(pts, 1.3))
        # label types on, with a blinking block cursor
        ta = t0q + 0.34
        chars = ""
        for i, ch in enumerate(label):
            m = self.ms(ta + i * 0.045, ta)
            chars += f"{{\\alpha&HFF&\\t({max(0, m - 1)},{m},\\alpha&H00&)}}{ass_escape(ch)}"
        self.add(39, ta, t1q, "Hud", f"{{\\an4\\pos({lx:.0f},{ly:.0f})\\fs{fs}\\fsp7\\1c{c(core)}\\3c{c(col)}\\bord2.5"
                 f"\\blur3\\3a&H70&\\shad0\\fad(0,250)}}{chars}")
        self.add(39, ta, t1q, "Hud", f"{{\\an4\\pos({lx:.0f},{ly + 34:.0f})\\fs{fs * 0.52:.0f}\\fsp3\\1c{c(col)}\\1a&H50&"
                 f"\\bord0\\shad0\\fad(250,250)}}FEATURE #{int(rng('hud', label) * 9e6) + 1000000:,} · ACT ▲")
        # underline rule
        self.add(38, ta, t1q, "Draw", f"{{\\an7\\pos(0,0)\\bord0\\shad0\\1c{c(col)}\\1a&H60&\\fad(250,250)\\p1}}"
                 + poly_stroke([(lx, ly + 22), (lx + tw, ly + 22)], 1.0))

    # ---- output
    def styles(self):
        def st(name, role, fs=60, primary="#FFFFFF", outline="#000000", back="#000000"):
            return Font(role).style_line(name, fs, primary=primary, outline=outline, back=back, an=5)
        return [st("Neon", "neon"), st("NeonSign", "neon_sign"), st("NeonScript", "neon_script"),
                st("Chrome", "chrome"), st("Chant", "serif_italic"), st("Foot", "mono_light"), st("Hud", "mono_medium"),
                st("Hand", "hand"), st("Draw", "mono")]

    def write(self, out):
        self.events.sort(key=lambda e: (e[1], e[0]))
        lines = [f"Dialogue: {ly},{fmt_t(t0)},{fmt_t(t1)},{st},,0,0,0,,{tx}" for ly, t0, t1, st, tx in self.events]
        out = rel(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(ass_header(self.W, self.H, self.styles(), title="Slow It Down captions") + "\n".join(lines) + "\n")
        return len(lines)


# --------------------------------------------------------------------------- drawing helpers

def _overlap(b1, b2, pad=10):
    return not (b1[2] + pad < b2[0] or b2[2] + pad < b1[0] or b1[3] + pad < b2[1] or b2[3] + pad < b1[1])


def free_intervals(lo, hi, obstacles, pad=40):
    """Gaps in [lo, hi] not covered by any (x0, x1) obstacle expanded by `pad`, left to right."""
    spans = sorted((max(lo, a - pad), min(hi, b + pad)) for a, b in obstacles if b + pad > lo and a - pad < hi)
    out, cur = [], lo
    for a, b in spans:
        if a > cur:
            out.append((cur, a))
        cur = max(cur, b)
    if cur < hi:
        out.append((cur, hi))
    return out


def pick_zone(hint, used):
    opposite = {"upper": "lower", "lower": "upper", "left": "right", "right": "left", "center": "upper"}
    for z in (hint, opposite.get(hint, "upper"), "upper", "lower", "right", "left"):
        if z not in used:
            return z
    return opposite.get(hint, "upper")


def split_arrow(text):
    """'BPM 200 → 64' -> ('200', '64', 'BPM '); 'v4 → v5' -> ('v4', 'v5', ''); 'SLOW' -> ('SLOW', None, '')."""
    m = re.match(r"^(.*?)(\S+)\s*(?:→|->)\s*(\S+)\s*$", text)
    if not m:
        return text, None, ""
    return m.group(2), m.group(3), m.group(1)


def wrap_text(text, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}" if cur else w
    if cur:
        lines.append(cur)
    return lines


def tint(hexcol, k):
    r, g, b = int(hexcol[1:3], 16), int(hexcol[3:5], 16), int(hexcol[5:7], 16)
    return "#%02X%02X%02X" % tuple(int(v + (255 - v) * k) for v in (r, g, b))


def circle(x, y, r, ring=None):
    k = 0.5523 * r

    def arc(rr, kk, rev=False):
        pts = [f"m {x + rr:.1f} {y:.1f}",
               f"b {x + rr:.1f} {y + kk:.1f} {x + kk:.1f} {y + rr:.1f} {x:.1f} {y + rr:.1f}",
               f"b {x - kk:.1f} {y + rr:.1f} {x - rr:.1f} {y + kk:.1f} {x - rr:.1f} {y:.1f}",
               f"b {x - rr:.1f} {y - kk:.1f} {x - kk:.1f} {y - rr:.1f} {x:.1f} {y - rr:.1f}",
               f"b {x + kk:.1f} {y - rr:.1f} {x + rr:.1f} {y - kk:.1f} {x + rr:.1f} {y:.1f}"]
        if rev:  # opposite winding -> a hole (libass uses non-zero winding)
            pts = [f"m {x + rr:.1f} {y:.1f}",
                   f"b {x + rr:.1f} {y - kk:.1f} {x + kk:.1f} {y - rr:.1f} {x:.1f} {y - rr:.1f}",
                   f"b {x - kk:.1f} {y - rr:.1f} {x - rr:.1f} {y - kk:.1f} {x - rr:.1f} {y:.1f}",
                   f"b {x - rr:.1f} {y + kk:.1f} {x - kk:.1f} {y + rr:.1f} {x:.1f} {y + rr:.1f}",
                   f"b {x + kk:.1f} {y + rr:.1f} {x + rr:.1f} {y + kk:.1f} {x + rr:.1f} {y:.1f}"]
        return " ".join(pts)
    if ring:
        ri = r - ring
        return arc(r, k) + " " + arc(ri, 0.5523 * ri, rev=True)
    return arc(r, k)


def square(x, y, r):
    return f"m {x - r:.1f} {y - r:.1f} l {x + r:.1f} {y - r:.1f} {x + r:.1f} {y + r:.1f} {x - r:.1f} {y + r:.1f}"


def rounded_rect(x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    k = 0.5523 * r
    x1, y1 = x + w, y + h
    return (f"m {x + r:.1f} {y:.1f} l {x1 - r:.1f} {y:.1f} b {x1 - r + k:.1f} {y:.1f} {x1:.1f} {y + r - k:.1f} {x1:.1f} {y + r:.1f} "
            f"l {x1:.1f} {y1 - r:.1f} b {x1:.1f} {y1 - r + k:.1f} {x1 - r + k:.1f} {y1:.1f} {x1 - r:.1f} {y1:.1f} "
            f"l {x + r:.1f} {y1:.1f} b {x + r - k:.1f} {y1:.1f} {x:.1f} {y1 - r + k:.1f} {x:.1f} {y1 - r:.1f} "
            f"l {x:.1f} {y + r:.1f} b {x:.1f} {y + r - k:.1f} {x + r - k:.1f} {y:.1f} {x + r:.1f} {y:.1f}")


def poly_stroke(pts, width):
    """A polyline as filled quads (ASS drawings have no strokes)."""
    out = []
    hw = width / 2
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy) or 1
        nx, ny = -dy / ln * hw, dx / ln * hw
        ex, ey = dx / ln * hw, dy / ln * hw     # extend by half-width so joints close
        out.append(f"m {x0 + nx - ex:.2f} {y0 + ny - ey:.2f} l {x1 + nx + ex:.2f} {y1 + ny + ey:.2f} "
                   f"{x1 - nx + ex:.2f} {y1 - ny + ey:.2f} {x0 - nx - ex:.2f} {y0 - ny - ey:.2f}")
    return " ".join(out)


_LED_ROWS = {  # 5x7 dot-matrix glyphs, one string per row
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "D": ["###..", "#..#.", "#...#", "#...#", "#...#", "#..#.", "###.."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".####"],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": [".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "J": ["..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."],
    "X": ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": ["..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."],
    "→": [".....", "..#..", "...#.", "#####", "...#.", "..#..", "....."],
    " ": ["....."] * 7,
    ".": [".....", ".....", ".....", ".....", ".....", ".##..", ".##.."],
    ":": [".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."],
    "-": [".....", ".....", ".....", "#####", ".....", ".....", "....."],
    "!": ["..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."],
    "?": [".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."],
    "#": [".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."],
    "%": ["##...", "##..#", "...#.", "..#..", ".#...", "#..##", "...##"],
    "…": [".....", ".....", ".....", ".....", ".....", ".....", "#.#.#"],
}
assert all(len(v) == 7 and all(len(r) == 5 for r in v) for v in _LED_ROWS.values()), "LED glyphs must be 5x7"
LED_FONT = {k: "".join(v) for k, v in _LED_ROWS.items()}


def led_dots(s):
    dots = []
    for n, ch in enumerate(s.upper()):
        g = LED_FONT.get(ch, LED_FONT["?"])
        g = (g + "." * 35)[:35]
        for j in range(7):
            for i in range(5):
                if g[j * 5 + i] == "#":
                    dots.append((n * 6 + i, j))
    return dots


# --------------------------------------------------------------------------- main

def build(timeline_path, edl_path, out_path, unlit=True, all_overlays=False):
    edl = load_edl(edl_path)
    tl = load_timeline(timeline_path or edl.get("timeline"))
    ann = load_json("video/annotations.json") if rel("video/annotations.json").exists() else None
    shotlist = load_json("video/shotlist.json") if rel("video/shotlist.json").exists() else None
    cap = Captions(tl, edl, annotations=ann, shotlist=shotlist, unlit=unlit, all_overlays=all_overlays)
    main = cap.build_lines()
    cap.build_overlays()          # before the staircases, which dodge overlay boxes
    cap.build_backing()
    cap.build_footnotes()
    n = cap.write(out_path)
    return cap, main, n


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("timeline", nargs="?", default=None, help="timeline.json (default: the EDL's 'timeline')")
    ap.add_argument("edl", nargs="?", default="video/edl.json")
    ap.add_argument("out", nargs="?", default=str(BUILD / "captions.ass"))
    ap.add_argument("--no-ghost", action="store_true", help="hide unlit words until they flicker on")
    ap.add_argument("--all-overlays", action="store_true",
                    help="also draw overlays marked enabled:false (text already painted into the keyframes)")
    a_ = ap.parse_args()
    cap, main, n = build(a_.timeline, a_.edl, a_.out, unlit=not a_.no_ghost, all_overlays=a_.all_overlays)
    zones = {}
    for p in main:
        zones[p.zone] = zones.get(p.zone, 0) + 1
    n_ov = sum(1 for ov in cap.overlays if overlay_enabled(ov, a_.all_overlays))
    print(f"{a_.out}: {n} events, {len(main)} lines {zones}, {len(cap.footnotes)} footnotes, "
          f"{n_ov}/{len(cap.overlays)} overlays on, song {song_duration(cap.tl):.1f}s + pre_roll {cap.pre}s")
