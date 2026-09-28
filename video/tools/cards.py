#!/usr/bin/env python3
"""Render the cold-open and end cards as short MP4s (film-noir black and white, 16 mm grain).

    python video/tools/cards.py                       # every card in video/edl.json -> video/build/cards/<id>.mp4
    python video/tools/cards.py video/edl.json --only C1 --stills video/tests/stills

Kinds (EDL `cards[]`, times in VIDEO seconds):
  quote   typewriter reveal of `text` (Courier Prime) under a faint Bodoni quote mark, `sub` (attribution)
          fades in underneath in Playfair italic. Venetian-blind light across the back wall.
  title   slow fade-up of `text` set like a luxury house mark (Bodoni Moda: small tracked caps line +
          a big ExtraBold line), with a gentle settle and halation.
  end     `text` line 1 in Bodoni italic, line 2 flickers on as white neon (Tilt Neon, the lyric face),
          then the `credit` lines in tracked IBM Plex Mono. Fades to black at the very end.
  credit  `text` + `sub` (or `credit` lines) in the end-card credit style.
render.py calls card_clip() and caches by content hash, so editing a card re-renders just that card.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BUILD, FONTS, ffmpeg_bin, load_edl, rel  # noqa: E402

CARDS_VERSION = "k5"
PAPER = (236, 233, 226)   # warm off-white for type on black


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def tracked_width(fnt, text, track):
    return sum(fnt.getlength(ch) for ch in text) + track * (len(text) - 1)


def draw_tracked(draw, xy, text, fnt, fill, track):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += fnt.getlength(ch) + track


class Film:
    """Background, grain, flicker and gate weave shared by all cards."""

    def __init__(self, w, h, seed, blinds=True):
        self.w, self.h = w, h
        self.rs = np.random.default_rng(seed)
        yy = np.linspace(-1, 1, h, dtype=np.float32)[:, None]
        xx = np.linspace(-1, 1, w, dtype=np.float32)[None, :] * (w / h)
        spot = np.exp(-((xx + 0.15) ** 2 * 0.55 + (yy + 0.25) ** 2 * 1.1)) * 34.0
        bg = 5.0 + spot
        if blinds:  # venetian-blind light falling diagonally across the back wall
            u = (xx * 0.55 + yy * 0.9) * 7.5
            slats = (np.sin(u * math.pi) > 0.15).astype(np.float32)
            slats = np.asarray(Image.fromarray((slats * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(7)),
                               np.float32) / 255
            window = np.exp(-((xx - 0.9) ** 2 * 0.35 + (yy + 0.1) ** 2 * 0.9))
            bg += slats * window * 22.0
        vig = 1 - 0.55 * np.clip((xx / (w / h)) ** 2 * 0.7 + yy ** 2 * 0.6, 0, 1)
        self.bg = (bg * vig).astype(np.float32)
        self.vig = vig.astype(np.float32)

    def finish(self, lum, t_idx):
        """lum: HxW float (0..255). Adds flicker, grain, dust, weave; returns uint8 RGB with a warm-neutral tone."""
        rs = self.rs
        flicker = 1.0 + rs.normal(0, 0.018)
        lum = lum * flicker
        g = rs.normal(0, 1, (self.h // 2, self.w // 2)).astype(np.float32)
        g = np.asarray(Image.fromarray(g).resize((self.w, self.h), Image.BICUBIC), np.float32)
        mid = 0.35 + 0.65 * np.clip(1 - np.abs(lum - 110) / 150, 0, 1)
        lum = lum + g * 7.5 * mid
        if rs.random() < 0.35:   # dust specks
            for _ in range(rs.integers(1, 4)):
                x, y = rs.integers(0, self.w), rs.integers(0, self.h)
                r = rs.integers(1, 3)
                lum[max(0, y - r):y + r, max(0, x - r):x + r] += rs.choice([-60, 90])
        if rs.random() < 0.08:   # a faint vertical scratch
            x = rs.integers(0, self.w)
            lum[:, x:x + 1] += 26
        lum = np.clip(lum, 0, 255)
        dy, dx = (rs.integers(-1, 2), rs.integers(-1, 2)) if rs.random() < 0.3 else (0, 0)
        if dx or dy:
            lum = np.roll(np.roll(lum, dy, 0), dx, 1)
        rgb = np.stack([lum * 1.0, lum * 0.985, lum * 0.955], -1)
        return np.clip(rgb, 0, 255).astype(np.uint8)


def text_layer(w, h, items):
    """items: list of (xy, text, font, track). Returns an L-mode mask as float 0..1."""
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    for xy, text, fnt, track in items:
        draw_tracked(d, xy, text, fnt, 255, track)
    return np.asarray(im, np.float32) / 255


def glow(mask, radius, strength):
    im = Image.fromarray((mask * 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(radius)), np.float32) / 255 * strength


# --------------------------------------------------------------------------- card kinds

def frames_quote(card, w, h, n, fps):
    film = Film(w, h, 13)
    fnt = font("CourierPrime-Regular.ttf", 66)
    sub_f = font("PlayfairDisplay-Italic.ttf", 36)
    qm_f = font("BodoniModa-Italic.ttf", 300)
    words = card["text"].split()
    if fnt.getlength(card["text"]) <= w * 0.66:
        lines = [card["text"]]
    else:   # two lines, the most even break
        k = min(range(1, len(words)), key=lambda i: max(fnt.getlength(" ".join(words[:i])),
                                                        fnt.getlength(" ".join(words[i:]))))
        lines = [" ".join(words[:k]), " ".join(words[k:])]
    lh = 88
    block_w = max(fnt.getlength(l_) for l_ in lines)
    x0 = (w - block_w) / 2
    y0 = h / 2 - lh * len(lines) / 2 - 30
    chars = [(li, ci) for li, l_ in enumerate(lines) for ci in range(len(l_))]
    # typewriter timing: irregular keystrokes, a beat at word gaps
    rs = np.random.default_rng(7)
    t, times = 0.30, []
    for li, ci in chars:
        ch = lines[li][ci]
        times.append(t)
        t += (0.020 if ch == " " else 0.034) + rs.uniform(0, 0.022) + (0.06 if ch in ",." else 0)
    t_done = t
    qm = text_layer(w, h, [((x0 - 190, y0 - 150), "“", qm_f, 0)])
    sub = card.get("sub", "")
    sub_w = sub_f.getlength(sub)
    sub_mask = text_layer(w, h, [((x0 + block_w - sub_w, y0 + lh * len(lines) + 34), sub, sub_f, 0)])
    for i in range(n):
        tt = i / fps
        k = sum(1 for tm in times if tm <= tt)
        items = []
        for li, l_ in enumerate(lines):
            shown = "".join(lines[li2][ci] for li2, ci in chars[:k] if li2 == li)
            if shown:
                items.append(((x0, y0 + li * lh), shown, fnt, 0))
        m = text_layer(w, h, items)
        if 0 < k < len(chars):   # the newest key strike lands a touch brighter
            li, ci = chars[k - 1]
            prefix = lines[li][:ci]
            px = x0 + fnt.getlength(prefix)
            hit = text_layer(w, h, [((px, y0 + li * lh), lines[li][ci], fnt, 0)])
            m = np.maximum(m, hit * 1.0)
        # cursor: a block that blinks after typing is done
        cur_on = (tt < t_done) or (int(tt * 2.2) % 2 == 0)
        lum = film.bg.copy() + qm * 28 * smooth((tt - 0.1) / 0.8)
        lum = lum * (1 - m) + m * 232
        if cur_on and tt < t_done + 1.4:
            li, ci = chars[min(k, len(chars) - 1)]
            prefix = lines[li][:ci + (1 if k >= len(chars) else 0)]
            cx = x0 + fnt.getlength(prefix) + 4
            cy = y0 + li * lh + 12
            lum[int(cy):int(cy + 58), int(cx):int(cx + 30)] = 200
        a_sub = smooth((tt - t_done - 0.15) / 0.6)
        lum = lum * (1 - sub_mask * a_sub) + sub_mask * a_sub * 205
        lum *= 1 - smooth((tt - (n / fps - 0.18)) / 0.18)   # dip to black into the next card
        yield film.finish(lum, i)


def frames_title(card, w, h, n, fps):
    film = Film(w, h, 29, blinds=False)
    text = card["text"].strip()
    # split "AI SAFETY HAS A BRANDING PROBLEM." -> small line + big line (last two words big)
    parts = text.split()
    big_n = 2 if len(parts) > 3 else len(parts)
    small, big = " ".join(parts[:-big_n]), " ".join(parts[-big_n:])
    f_small = font("BodoniModa-Medium.ttf", 44)
    f_big = font("BodoniModa-ExtraBold.ttf", 104)
    tr_s, tr_b = 16, 7
    ws, wb = tracked_width(f_small, small, tr_s), tracked_width(f_big, big, tr_b)
    ys, yb = h / 2 - 96, h / 2 - 30
    m_small = text_layer(w, h, [(((w - ws) / 2, ys), small, f_small, tr_s)]) if small else 0
    m_big = text_layer(w, h, [(((w - wb) / 2, yb), big, f_big, tr_b)])
    rule = np.zeros((h, w), np.float32)
    rule[int(yb + 178):int(yb + 180), int(w / 2 - 56):int(w / 2 + 56)] = 1.0
    halo = glow(np.maximum(m_small if isinstance(m_small, np.ndarray) else 0, m_big), 18, 0.55)
    for i in range(n):
        tt = i / fps
        a_s = smooth((tt - 0.0) / 0.8)
        a_b = smooth((tt - 0.22) / 0.95)
        a_r = smooth((tt - 0.95) / 0.5)
        out = smooth((tt - (n / fps - 0.30)) / 0.30)
        lum = film.bg.copy() * 0.8
        lum += halo * 60 * a_b
        if isinstance(m_small, np.ndarray):
            lum = lum * (1 - m_small * a_s) + m_small * a_s * 225
        # slow settle of the big line: slight vertical drift up, done by blending two offsets
        lum = lum * (1 - m_big * a_b) + m_big * a_b * 240
        lum = lum * (1 - rule * a_r * 0.7) + rule * a_r * 0.7 * 180
        lum *= 1 - out
        yield film.finish(lum, i)


def frames_end(card, w, h, n, fps):
    film = Film(w, h, 41)
    lines = card["text"].split("\n")
    l1, l2 = lines[0], (lines[1] if len(lines) > 1 else "")
    f1 = font("BodoniModa-Italic.ttf", 64)
    f2 = font("TiltNeon-Regular.ttf", 112)
    fc = font("IBMPlexMono-Regular.ttf", 23)
    fc2 = font("IBMPlexMono-Light.ttf", 20)
    w1, w2 = f1.getlength(l1), f2.getlength(l2)
    y1, y2 = h / 2 - 150, h / 2 - 62
    m1 = text_layer(w, h, [(((w - w1) / 2, y1), l1, f1, 0)])
    m2 = text_layer(w, h, [(((w - w2) / 2, y2), l2, f2, 0)]) if l2 else np.zeros((h, w), np.float32)
    g2a, g2b = glow(m2, 10, 1.0), glow(m2, 34, 0.8)
    credits = card.get("credit") or []
    cm = []
    for k, cl in enumerate(credits):
        fnt = fc if k == 0 else fc2
        tr = 3 if k == 0 else 1
        cw = tracked_width(fnt, cl, tr)
        cm.append(text_layer(w, h, [(((w - cw) / 2, h / 2 + 150 + k * 44), cl, fnt, tr)]))
    flick = [1, 0, 1, 0.3, 0, 1, 0.6, 1]   # neon ignition, one value per frame
    t_neon = 1.5
    dur = n / fps
    for i in range(n):
        tt = i / fps
        lum = film.bg.copy() * 0.85
        a1 = smooth((tt - 0.2) / 1.2)
        lum = lum * (1 - m1 * a1) + m1 * a1 * 228
        fi = int((tt - t_neon) * fps)
        a2 = 0.0 if fi < 0 else (flick[fi] if fi < len(flick) else 1.0)
        if a2 > 0:
            hum = 1 + 0.03 * math.sin(tt * 37)
            lum += (g2b * 70 + g2a * 120) * a2 * hum
            lum = lum * (1 - m2 * a2) + m2 * a2 * 252
        for k, m in enumerate(cm):
            ac = smooth((tt - 3.3 - k * 0.5) / 0.9) * (0.85 if k == 0 else 0.62)
            lum = lum * (1 - m * ac) + m * ac * 210
        lum *= 1 - smooth((tt - (dur - 1.1)) / 1.1)
        yield film.finish(lum, i)


def frames_credit(card, w, h, n, fps):
    lines = card.get("credit") or [l_ for l_ in (card.get("text"), card.get("sub")) if l_]
    return frames_end({"text": "", "credit": lines}, w, h, n, fps)


def frames_image(card, w, h, n, fps):
    """A still image held for the card's frames: the poster, shown as the video's first frame (X's preview)."""
    from PIL import Image
    src = Path(card["src"])
    if not src.is_absolute():
        src = Path(__file__).resolve().parents[2] / src
    frame = np.asarray(Image.open(src).convert("RGB").resize((w, h), Image.LANCZOS), dtype=np.uint8)
    for _ in range(n):
        yield frame


KINDS = {"quote": frames_quote, "title": frames_title, "end": frames_end, "credit": frames_credit, "image": frames_image}


# --------------------------------------------------------------------------- output

def card_clip(card, fps=24, size=(1920, 1080), force=False):
    """Path to the rendered card (rendering it if missing or out of date)."""
    key = hashlib.sha1(json.dumps([card, fps, list(size), CARDS_VERSION], sort_keys=True).encode()).hexdigest()[:10]
    out = BUILD / "cards" / f"{card['id']}_{key}.mp4"
    if out.exists() and not force:
        return out
    render_card(card, fps, size, out)
    return out


def render_card(card, fps, size, out):
    w, h = size
    n = int(round(card["end"] * fps)) - int(round(card["start"] * fps))
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(f"{out.stem}.{os.getpid()}.tmp.mp4")   # unique per process: safe to run concurrently
    cmd = [ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", "-frames:v", str(n), "-c:v", "libx264", "-preset", "medium",
           "-crf", "12", "-pix_fmt", "yuv420p", "-r", str(fps), str(tmp)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for frame in KINDS[card["kind"]](card, w, h, n, fps):
        p.stdin.write(frame.tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError(f"ffmpeg failed rendering card {card['id']}")
    os.replace(tmp, out)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edl", nargs="?", default="video/edl.json")
    ap.add_argument("--only", default=None, help="comma list of card ids")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--stills", default=None, help="dir: also save a few PNG frames per card")
    a = ap.parse_args()
    edl = load_edl(a.edl)
    only = set(a.only.split(",")) if a.only else None
    for cd in edl["cards"]:
        if only and cd["id"] not in only:
            continue
        p = card_clip(cd, edl["fps"], tuple(edl["size"]), force=a.force)
        print(f"{cd['id']} ({cd['kind']}, {cd['end'] - cd['start']:.2f}s): {p}")
        if a.stills:
            d = rel(a.stills)
            d.mkdir(parents=True, exist_ok=True)
            dur = cd["end"] - cd["start"]
            for frac in (0.35, 0.95) if cd["kind"] != "end" else (0.25, 0.55, 0.8):
                t = dur * frac
                png = d / f"card_{cd['id']}_{t:05.2f}s.png"
                subprocess.run([ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t:.3f}", "-i", str(p),
                                "-frames:v", "1", "-update", "1", str(png)], check=True)
                print(f"   still {png}")


if __name__ == "__main__":
    main()
