#!/usr/bin/env python3
"""Assemble the music video from an EDL: cards + graded shots + burned-in captions + delayed audio.

    python video/tools/render.py video/edl.json video/out.mp4
    python video/tools/render.py video/edl.json video/tests/caption_test.mp4 --song-end 75
    python video/tools/render.py video/edl.json out.mp4 --range 60 90 --preset veryfast   # video seconds
    python video/tools/render.py video/edl.json out.mp4 --stills 12,30.5,s61.9            # also grab PNGs
                                                        (plain = video seconds, s-prefix = song seconds)
How it works
  1. Plan: paint every video frame with its owner (shots at pre_roll + song time, cards on top,
     black in gaps) and cut the result into segments with exact frame counts.
  2. Render each segment to a high-quality intermediate (cached by content hash in video/build/segments):
       source -> fit 1920x1080 (cover) -> timing -> grade preset -> fx -> letterbox -> exactly N frames.
     Letterboxed shots can carry "lb_shift" (fraction of frame height): the picture moves down under the
     2.39:1 bars so close-ups keep their headroom.
     Timing: a source longer than its slot is trimmed; a shorter one is slowed down (down to 0.5x),
     and if that's still not enough it plays at 0.5x and freezes on its last frame. Shots with
     "retime": "freeze" (lip-sync) are never slowed: they play in real time and hold the last frame.
     Missing source -> the shot's keyframe still (slow push-in) -> a dark placeholder slate
     showing the shot id and prompt summary.
  3. Final pass: concat -> subtle vignette -> captions.ass (libass) -> soft film grain -> H.264
     (CRF 16, yuv420p, 24 fps) + the song delayed by pre_roll (AAC 320k).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (BUILD, FONTS, edl_duration, ffmpeg_bin, load_edl, load_timeline, probe, rel,  # noqa: E402
                    run)

RENDER_VERSION = "r11"   # bump to invalidate cached segments when filters change
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}


# --------------------------------------------------------------------------- grades & fx

def bloom(strength=0.3, sigma=22, thresh=0.55, uid="g"):
    """Highlight bloom, blended in RGB (screen). `uid` keeps pad labels unique within one chain."""
    return (f"format=gbrp,split=2[bl{uid}0][bl{uid}1];[bl{uid}1]gblur=sigma={sigma},"
            f"curves=all='0/0 {thresh}/0 1/1'[bl{uid}2];[bl{uid}0][bl{uid}2]blend=all_mode=screen:all_opacity={strength}")


def strobe_expr(seg, bpm_div=2, amount=0.16, width=2):
    """eq brightness expression that flashes for `width` frames on each beat subdivision (song-synced)."""
    P = seg["beat_period"] / bpm_div
    ph = (seg["song_t0"] - seg["beat_t0"]) % P
    return f"{amount}*lt(mod(t+{ph:.4f},{P:.5f}),{width / seg['fps']:.4f})"


def shake(amount=18):
    return (f"crop=w=iw-{2 * amount}:h=ih-{2 * amount}:x='{amount}+{amount * 0.9:.1f}*sin(n*1.93+3*sin(n*0.41))':"
            f"y='{amount}+{amount * 0.9:.1f}*cos(n*2.71+2*sin(n*0.29))',scale=1920:1080")


def haze(strength=0.2, sigma=48, uid="g"):
    """Atmospheric haze: screen a very soft copy over the frame (lifts shadows, blooms practicals)."""
    return (f"format=gbrp,split=2[hz{uid}0][hz{uid}1];[hz{uid}1]gblur=sigma={sigma}[hz{uid}2];"
            f"[hz{uid}0][hz{uid}2]blend=all_mode=screen:all_opacity={strength}")


BW_TO_COLOR = dict(ramp=1.2, hue=80, sat=0.6, glow=0.4)   # hue: degrees to rotate the source colour


def bw_to_color(seg, ramp=None, hue=None, sat=None, glow=None):
    """The Wizard-of-Oz cut: the `bw` look until `ramp` s before the shot ends, then colour fades in
    (alpha ramp over the B&W branch) by the cut, with a transient bloom that peaks as it arrives and is
    gone by the last frame. The arriving colour is the source's, hue-rotated (S02's magenta neon wash
    lands on warm sodium amber) with its saturation scaled to `sat`, so it reads as warm light, not a tint."""
    cfg = dict(BW_TO_COLOR)
    cfg.update({k: v for k, v in dict(ramp=ramp, hue=hue, sat=sat, glow=glow).items() if v is not None})
    ramp = cfg["ramp"]
    t_end = (seg["shot_frames"] - seg["f_off"]) / seg["fps"]      # shot end, in segment-local seconds
    t0 = max(0.0, t_end - ramp)
    half = ramp / 2
    bw = ",".join(grade_filters("bw", seg))
    return (f"split=2[bwc0][bwc1];"
            f"[bwc0]{bw}[bwcA];"
            f"[bwc1]hue=h={cfg['hue']}:s={cfg['sat']},"
            f"colorbalance=rm=0.04:gm=0.01:bm=-0.05:rh=0.04:gh=0.01:bh=-0.05,split=2[bwcK][bwc2];"
            f"[bwcK]format=yuva420p,fade=t=in:st={t0:.3f}:d={ramp:.3f}:alpha=1[bwcB];"
            f"[bwc2]format=gbrp,gblur=sigma=24,curves=all='0/0 0.5/0 1/1',"
            f"fade=t=in:st={t0:.3f}:d={half:.3f},fade=t=out:st={t0 + half:.3f}:d={half:.3f}[bwcG];"
            f"[bwcA][bwcB]overlay=format=auto,format=gbrp[bwcC];"
            f"[bwcC][bwcG]blend=all_mode=screen:all_opacity={cfg['glow']}")


GRADE_DOC = {  # restrained Blade Runner (1982) / 2049 look: shadow, haze, sodium amber vs steel teal
    "none": "untouched",
    "bw": "16 mm noir: desaturate, S-curve, crushed blacks (+ heavier grain via fx)",
    "bw_to_color": "bw until 1.2 s before the cut, then colour floods in (source hue-rotated to sodium amber, sat 0.6) with a brief bloom",
    "neon": "desaturated teal-and-amber split: teal shadows, sodium-amber highlights",
    "strobe": "hard red with crushed blacks (no magenta), a soft beat-synced flash (2.1 Hz), slight handheld jitter",
    "amber": "warm hazy sodium orange (2049 Las Vegas): low contrast, lifted blacks, haze bloom",
    "silver": "cool steel-blue: low saturation, blue-teal balance, clean highlights",
    "fisheye": "mild barrel distortion (lenscorrection) plus a gold-highlight / teal-shadow grade",
    "dawn": "pale grey-blue with a peach lift in the highlights, lifted blacks",
    "gold": "amber's warmer, slightly richer sibling with a stronger haze",
}


def grade_filters(g, seg):
    if g == "bw_to_color":
        return [bw_to_color(seg)]
    if g == "bw":
        return ["hue=s=0", "curves=master='0/0 0.16/0.07 0.5/0.49 0.84/0.93 1/1'", "eq=contrast=1.08"]
    if g == "neon":
        return ["eq=saturation=0.78:contrast=1.05",
                "colorbalance=rs=-0.07:gs=0.01:bs=0.06:rm=0.02:gm=0.0:bm=-0.02:rh=0.09:gh=0.03:bh=-0.08",
                "curves=master='0/0.02 0.5/0.49 1/0.97'"]
    if g == "strobe":
        return ["eq=saturation=1.08:contrast=1.16",
                "colorbalance=rs=0.14:gs=-0.07:bs=-0.11:rm=0.12:gm=-0.07:bm=-0.13:rh=0.03:gh=-0.02:bh=-0.09",
                "curves=master='0/0 0.14/0.02 0.5/0.45 1/0.98'",
                f"eq=eval=frame:brightness='{strobe_expr(seg, 2, 0.10)}'", shake(6)]
    if g == "amber":
        return ["eq=saturation=1.0:contrast=0.98",
                "colorbalance=rs=0.04:gs=-0.01:bs=-0.05:rm=0.07:gm=-0.015:bm=-0.08:rh=0.04:gh=0.0:bh=-0.05",
                "curves=master='0/0.02 0.5/0.51 1/0.97'", haze(0.10)]
    if g == "gold":
        return ["eq=saturation=1.06:contrast=0.98",
                "colorbalance=rs=0.05:gs=-0.005:bs=-0.06:rm=0.10:gm=-0.01:bm=-0.10:rh=0.07:gh=0.01:bh=-0.07",
                "curves=master='0/0.02 0.5/0.52 1/0.97'", haze(0.14)]
    if g == "silver":
        return ["eq=saturation=0.55:contrast=1.06:brightness=0.01",
                "colorbalance=rs=-0.08:gs=-0.01:bs=0.08:rm=-0.06:gm=0.0:bm=0.06:rh=-0.02:gh=0.02:bh=0.05",
                "curves=master='0/0.02 0.6/0.63 1/0.98'"]
    if g == "fisheye":
        return ["lenscorrection=k1=0.12:k2=0.02:i=bilinear", "scale=2208:1242:flags=bicubic", "crop=1920:1080",
                "eq=saturation=0.95:contrast=1.06",
                "colorbalance=rs=-0.04:gs=0.0:bs=0.05:rh=0.10:gh=0.05:bh=-0.08", bloom(0.14, 16, 0.65)]
    if g == "dawn":
        return ["eq=saturation=0.62:contrast=0.9:brightness=0.03",
                "colorbalance=rs=-0.04:gs=0.0:bs=0.06:rm=0.04:gm=0.01:bm=-0.01:rh=0.09:gh=0.04:bh=-0.02",
                "curves=master='0/0.07 0.5/0.55 1/0.98'"]
    return []


FX_DOC = {
    "grain": "extra (heavier) luma grain on this shot",
    "vignette": "extra vignette on this shot",
    "flash_in": "2-frame white flash on the shot's first frames",
    "flash_out": "2-frame white flash on the shot's last frames",
    "fade_in": "0.5 s fade up from black", "fade_out": "0.5 s fade to black",
    "bloom": "highlight bloom", "shake": "handheld jitter", "chroma": "RGB split",
    "strobe": "beat-synced white strobe", "push_in": "slow 6% push-in (videos; stills always drift in)",
}


def fx_filters(fx, seg):
    out = []
    n, first, last = seg["n"], seg["f_off"] == 0, seg["f_off"] + seg["n"] >= seg["shot_frames"]
    for f in fx:
        if f == "grain":
            out.append("noise=c0s=14:c0f=t+u")
        elif f == "vignette":
            out.append("vignette=angle=PI/4.4")
        elif f == "bloom":
            out.append(bloom(0.3, uid="f"))
        elif f == "shake":
            out.append(shake(14))
        elif f == "chroma":
            out.append("rgbashift=rh=-4:bh=4")
        elif f == "strobe":
            out.append(f"eq=eval=frame:brightness='{strobe_expr(seg, 2, 0.18)}'")
        elif f == "push_in" and seg["mode"] == "video":
            N = seg["shot_frames"]
            out.append(f"scale=3840:2160,zoompan=z='1+0.06*(on+{seg['f_off']})/{N}':d=1:"
                       f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps={seg['fps']}")
        elif f == "fade_in" and first:
            out.append("fade=t=in:st=0:d=0.5")
        elif f == "fade_out" and last:
            out.append(f"fade=t=out:st={max(0, n / seg['fps'] - 0.5):.3f}:d=0.5")
    return out


def post_fx(fx, seg):
    """Flashes go after the grade so they stay white."""
    out = []
    n, first = seg["n"], seg["f_off"] == 0
    last = seg["f_off"] + seg["n"] >= seg["shot_frames"]
    if "flash_in" in fx and first:
        out += ["drawbox=x=0:y=0:w=iw:h=ih:color=white@1.0:t=fill:enable='eq(n,0)'",
                "drawbox=x=0:y=0:w=iw:h=ih:color=white@0.55:t=fill:enable='eq(n,1)'"]
    if "flash_out" in fx and last:
        out += [f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.55:t=fill:enable='eq(n,{n - 2})'",
                f"drawbox=x=0:y=0:w=iw:h=ih:color=white@1.0:t=fill:enable='eq(n,{n - 1})'"]
    return out


def lb_shift_filters(w, h, shift):
    """Letterbox headroom: move the picture down by `shift` x frame height (clamped to the bar) so a
    close-up keeps the top of the head; the rows pushed off the bottom go under the bottom bar."""
    bar = round((h - w / 2.39) / 2)
    d = int(round(min(max(shift, 0.0) * h, bar) / 2)) * 2       # even, for yuv420 chroma
    return [f"crop={w}:{h - d}:0:0", f"pad={w}:{h}:0:{d}:black"] if d else []


def letterbox_filters(w, h):
    bar = round((h - w / 2.39) / 2)
    return [f"drawbox=x=0:y=0:w=iw:h={bar}:color=black@1:t=fill",
            f"drawbox=x=0:y=ih-{bar}:w=iw:h={bar}:color=black@1:t=fill"]


# --------------------------------------------------------------------------- placeholder slate

PALETTE = ["#FF2E88", "#20C4C8", "#FFB347", "#E8A598", "#8A5CFF", "#FFFFFF", "#FF5A36", "#3A7BFF"]


def make_slate(shot, out, w=1920, h=1080):
    """Dark 'club at night' backdrop (bokeh, beams, a subject silhouette opposite the caption zone)
    plus the shot id and prompt summary. Seeded by the shot id, so it's stable."""
    import numpy as np
    from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont
    rs = np.random.default_rng(int(hashlib.md5(shot["id"].encode()).hexdigest()[:8], 16))
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    xx = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    top, bot = np.array([10, 9, 20], np.float32), np.array([30, 17, 32], np.float32)
    img = np.broadcast_to(top * (1 - yy) + bot * yy, (h, w, 3)).copy()
    floor = np.array([[255, 60, 140], [40, 200, 210], [255, 170, 60]][rs.integers(3)], np.float32)
    img += floor * (np.exp(-(((xx - 0.5) / 0.55) ** 2 + ((yy - 1.05) / 0.35) ** 2) * 2.2) * 0.35)

    def add_layer(layer, blur):
        nonlocal img
        img += np.asarray(layer.filter(ImageFilter.GaussianBlur(blur)), np.float32)

    beams = Image.new("RGB", (w, h))
    bd = ImageDraw.Draw(beams)
    for _ in range(3):
        x0, spread = rs.uniform(0.1, 0.9) * w, rs.uniform(120, 260)
        col = tuple(int(v * 0.2) for v in ImageColor.getrgb(PALETTE[rs.integers(len(PALETTE))]))
        drift = rs.uniform(-400, 400)
        bd.polygon([(x0 - 18, -10), (x0 + 18, -10), (x0 + drift + spread, h), (x0 + drift - spread, h)], fill=col)
    add_layer(beams, 40)
    bok = Image.new("RGB", (w, h))
    bk = ImageDraw.Draw(bok)
    for _ in range(int(rs.integers(16, 28))):
        cx, cy, r = rs.uniform(0, w), rs.uniform(0, h * 0.75), rs.uniform(18, 120)
        k = rs.uniform(0.18, 0.6)
        col = tuple(int(v * k) for v in ImageColor.getrgb(PALETTE[rs.integers(len(PALETTE))]))
        bk.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    add_layer(bok, 9)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")
    # a subject silhouette opposite the caption zone, so the placeholder reads like a composed frame
    zone = shot.get("caption_zone", "lower")
    sx = {"left": 0.66, "right": 0.34}.get(zone, 0.5 + rs.uniform(-0.12, 0.12))
    sy = {"upper": 0.64, "lower": 0.42}.get(zone, 0.52)
    sil = Image.new("L", (w, h), 0)
    sd = ImageDraw.Draw(sil)
    hx, hy, hr = sx * w, sy * h - 120, 78
    sd.ellipse([hx - hr * 0.8, hy - hr, hx + hr * 0.8, hy + hr], fill=255)
    sd.polygon([(hx - 70, hy + 70), (hx + 70, hy + 70), (hx + 260, h + 50), (hx - 260, h + 50)], fill=255)
    sil = sil.filter(ImageFilter.GaussianBlur(6))
    rim = sil.filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * 0.6))
    im = Image.composite(Image.blend(im, Image.new("RGB", (w, h), PALETTE[rs.integers(4)]), 0.35), im, rim)
    im = Image.composite(Image.new("RGB", (w, h), (6, 5, 9)), im, sil)
    # the label, in a corner away from the caption zone
    draw = ImageDraw.Draw(im)
    fm = ImageFont.truetype(str(FONTS / "IBMPlexMono-Medium.ttf"), 34)
    fl = ImageFont.truetype(str(FONTS / "IBMPlexMono-Light.ttf"), 21)
    meta = f"{shot.get('section') or ''} · {shot['start']:.2f}–{shot['end']:.2f}s · {shot.get('grade')} · zone {zone}"
    rows, cur = [], ""
    for wd in (shot.get("prompt") or "").split():
        if len(cur) + len(wd) + 1 > 64:
            rows.append(cur)
            cur = wd
        else:
            cur = f"{cur} {wd}".strip()
    if cur:
        rows.append(cur)
    if len(rows) > 4:
        rows = rows[:4]
        rows[-1] = rows[-1][:60] + "…"
    block_h = 78 + 28 * len(rows)
    bx = 64 if zone != "left" else w - 64 - 900
    by = 64 if zone == "lower" else h - 64 - block_h
    draw.text((bx, by), f"{shot['id']}  PLACEHOLDER", font=fm, fill=(236, 226, 232))
    draw.text((bx, by + 46), meta, font=fl, fill=(170, 160, 170))
    for i, r in enumerate(rows):
        draw.text((bx, by + 78 + 28 * i), r, font=fl, fill=(140, 130, 142))
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    return out


# --------------------------------------------------------------------------- planning

def plan(edl, tl, v0=None, v1=None):
    fps = edl["fps"]
    pre = edl["pre_roll"]
    total = edl_duration(edl, tl)
    F = int(round(total * fps))
    owner = [None] * F
    for i, s in enumerate(edl["shots"]):
        f0, f1 = int(round((pre + s["start"]) * fps)), int(round((pre + s["end"]) * fps))
        for f in range(max(0, f0), min(F, f1)):
            owner[f] = ("shot", i)
    for j, cd in enumerate(edl["cards"]):
        f0, f1 = int(round(cd["start"] * fps)), int(round(cd["end"] * fps))
        for f in range(max(0, f0), min(F, f1)):
            owner[f] = ("card", j)
    a_ = 0 if v0 is None else max(0, int(round(v0 * fps)))
    b_ = F if v1 is None else min(F, int(round(v1 * fps)))
    segs = []
    f = a_
    while f < b_:
        o = owner[f]
        g = f
        while g < b_ and owner[g] == o:
            g += 1
        segs.append({"owner": o, "f0": f, "f1": g})
        f = g
    return segs, F


def _usable(path, is_image):
    """Skip files that are still being written or are broken (fall through to the next option)."""
    try:
        if path.stat().st_size < 1024 or time.time() - path.stat().st_mtime < 3:
            return False
        if is_image:
            from PIL import Image
            with Image.open(path) as im:
                im.load()
            return True
        info = probe(path)
        return bool(info.get("has_video")) and info.get("duration", 0) > 0.05
    except Exception:
        return False


def resolve_source(shot):
    """src (video or image) -> still (keyframe) -> placeholder slate."""
    for key in ("src", "still"):
        p = shot.get(key)
        if p and rel(p).exists():
            is_img = rel(p).suffix.lower() in IMAGE_EXT
            if _usable(rel(p), is_img):
                return ("still" if is_img else "video"), rel(p)
            print(f"  warning: {shot['id']}: {p} is unreadable or still being written; skipping it", file=sys.stderr)
    return "slate", None


def segment_spec(edl, tl, seg):
    fps, (w, h) = edl["fps"], edl["size"]
    pre = edl["pre_roll"]
    kind, idx = seg["owner"] if seg["owner"] else ("gap", None)
    n = seg["f1"] - seg["f0"]
    spec = {"kind": kind, "n": n, "fps": fps, "size": [w, h], "v": RENDER_VERSION,
            "beat_period": tl.get("beat_period", 0.94), "beat_t0": tl.get("beat_t0", 0.0)}
    if kind == "shot":
        s = edl["shots"][idx]
        sf0 = int(round((pre + s["start"]) * fps))
        sf1 = int(round((pre + s["end"]) * fps))
        mode, src = resolve_source(s)
        spec.update(id=s["id"], mode=mode, src=str(src) if src else None,
                    src_stat=[src.stat().st_size, int(src.stat().st_mtime)] if src else None,
                    f_off=seg["f0"] - sf0, shot_frames=sf1 - sf0, song_t0=(seg["f0"] - int(round(pre * fps))) / fps,
                    grade=s["grade"], fx=list(s["fx"]), letterbox=bool(s["letterbox"]),
                    src_in=float(s["src_in"]), speed=float(s["speed"]), fit=s.get("fit", "cover"),
                    retime=s.get("retime", "slow"), lb_shift=float(s.get("lb_shift") or 0.0),
                    src_crop=s.get("src_crop"),
                    # only placeholder slates draw these, so zone/prompt edits don't re-render real footage
                    slate={k: s.get(k) for k in ("id", "start", "end", "grade", "caption_zone", "section", "prompt")}
                    if mode == "slate" else None)
        if mode == "video":
            info = probe(src)
            spec["src_dur"] = info.get("duration", 0.0)
            spec["src_has_video"] = info.get("has_video", True)
    elif kind == "card":
        cd = edl["cards"][idx]
        cf0 = int(round(cd["start"] * fps))
        spec.update(id=cd["id"], card=cd, f_off=seg["f0"] - cf0, card_frames=int(round(cd["end"] * fps)) - cf0)
    else:
        spec.update(id="gap")
    if kind == "shot":   # hash the resolved filter chains too, so tweaking a preset re-renders its shots
        spec["chain"] = grade_filters(spec["grade"], spec) + fx_filters(spec["fx"], spec) + post_fx(spec["fx"], spec)
    spec["hash"] = hashlib.sha1(json.dumps(spec, sort_keys=True, default=str).encode()).hexdigest()[:12]
    return spec


def timing(spec):
    """(source start seconds, effective speed) for a video shot segment."""
    fps = spec["fps"]
    slot = spec["shot_frames"] / fps
    avail = max(0.0, spec["src_dur"] - spec["src_in"])
    speed = spec["speed"]
    if avail + 1e-3 >= slot * speed or spec.get("retime") == "freeze":
        eff = speed                    # trim, or (lip-sync) play in real time and hold the last frame
    else:
        eff = max(avail / slot, 0.5)   # slow down as far as 0.5x, then freeze the last frame
    return spec["src_in"] + spec["f_off"] / fps * eff, eff


def render_segment(spec, out):
    fps, (w, h), n = spec["fps"], spec["size"], spec["n"]
    exe = ffmpeg_bin()
    inputs, chain = [], []
    fit = [f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos", f"crop={w}:{h}"]
    sc = spec.get("src_crop")
    pre_crop = []
    if sc and list(sc) != [0, 0, 1, 1]:     # [x0, y0, x1, y1] as fractions of the source frame
        x0, y0, x1, y1 = sc
        pre_crop = [f"crop=trunc(iw*{x1 - x0:.4f}/2)*2:trunc(ih*{y1 - y0:.4f}/2)*2:trunc(iw*{x0:.4f}):trunc(ih*{y0:.4f})"]
    if spec["kind"] == "gap":
        inputs = ["-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:r={fps}"]
    elif spec["kind"] == "card":
        from cards import card_clip
        clip = card_clip(spec["card"], fps, (w, h))
        inputs = ["-ss", f"{spec['f_off'] / fps:.4f}", "-i", str(clip)]
        chain += fit + ["tpad=stop_mode=clone:stop_duration=2"]
    else:
        mode = spec["mode"]
        if mode == "video":
            ss, eff = timing(spec)
            inputs = ["-ss", f"{ss:.4f}", "-i", spec["src"]]
            if spec.get("fit") == "contain":
                fit = [f"scale={w}:{h}:force_original_aspect_ratio=decrease:flags=lanczos",
                       f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black"]
            chain += pre_crop + fit + [f"setpts=(PTS-STARTPTS)/{eff:.5f}"]
            chain += [f"framerate=fps={fps}" if eff < 0.97 else f"fps={fps}",
                      f"tpad=stop_mode=clone:stop_duration={n / fps + 1:.2f}"]
        else:
            if mode == "slate":
                src = BUILD / "slates" / f"{spec['id']}_{hashlib.sha1(json.dumps(spec['slate'], sort_keys=True).encode()).hexdigest()[:8]}.png"
                if not src.exists():
                    make_slate(spec["slate"], src, w, h)
            else:
                src = Path(spec["src"])
            N = max(1, spec["shot_frames"])
            inputs = ["-loop", "1", "-framerate", str(fps), "-i", str(src)]
            chain += (pre_crop if mode == "still" else []) + [
                      f"scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase:flags=bicubic", f"crop={w * 2}:{h * 2}",
                      f"zoompan=z='1.025+0.055*(on+{spec['f_off']})/{N}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                      f":s={w}x{h}:fps={fps}"]
        if spec["letterbox"] and spec.get("lb_shift"):
            chain += lb_shift_filters(w, h, spec["lb_shift"])
        chain += grade_filters(spec["grade"], spec) + fx_filters(spec["fx"], spec)
        chain += ["format=yuv420p"] + post_fx(spec["fx"], spec)
        if spec["letterbox"]:
            chain += letterbox_filters(w, h)
    chain += ["setsar=1", "format=yuv420p"]
    graph = "[0:v]" + ",".join(chain) + "[v]"
    tmp = out.with_name(f"{out.stem}.{os.getpid()}.tmp.mp4")   # unique per process: safe to run concurrently
    run([exe, "-hide_banner", "-y", *inputs, "-filter_complex", graph, "-map", "[v]", "-frames:v", str(n),
         "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast", "-crf", "10", "-pix_fmt", "yuv420p",
         "-an", "-threads", "4", str(tmp)])
    os.replace(tmp, out)
    return out


# --------------------------------------------------------------------------- final pass

def final_pass(edl, tl, seg_files, v0, v1, out, captions, preset="slow", crf=16):
    fps, (w, h) = edl["fps"], edl["size"]
    exe = ffmpeg_bin()
    work = BUILD / "work"
    work.mkdir(parents=True, exist_ok=True)
    lst = work / f"concat_{os.getpid()}.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in seg_files))
    look = edl.get("look", {})
    g, vg = float(look.get("grain", 0.3)), float(look.get("vignette", 0.3))
    dur = v1 - v0
    vf = []
    if vg > 0:
        vf.append(f"vignette=angle={0.2 + vg * 0.9:.3f}:mode=forward:eval=init")
    if captions:
        esc = str(captions).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
        fdir = str(FONTS).replace(":", "\\:")
        # the `ass` filter reads the script directly (the `subtitles` filter goes through lavf's ASS
        # demuxer, which drops "Kerning: yes"); complex shaping = HarfBuzz, matching our layout metrics
        vf += [f"setpts=PTS+{v0:.4f}/TB", f"ass=filename='{esc}':fontsdir='{fdir}':shaping=complex",
               "setpts=PTS-STARTPTS"]
    vf.append("format=yuv420p")
    graph = "[0:v]" + ",".join(vf) + "[vs]"
    if g > 0:
        graph += (f";color=c=0x808080:s={w // 2}x{h // 2}:r={fps},format=yuv420p,noise=c0s={int(10 + g * 60)}:c0f=t+u,"
                  f"gblur=sigma=0.7,scale={w}:{h}:flags=bicubic[gr];"
                  f"[vs][gr]blend=all_mode=overlay:c0_opacity={0.25 + g * 0.5:.3f}:c1_opacity=0:c2_opacity=0:shortest=1,"
                  f"format=yuv420p[v]")
    else:
        graph += ";[vs]null[v]"
    pre_ms = int(round(edl["pre_roll"] * 1000))
    graph += (f";[1:a]aresample=48000,adelay={pre_ms}:all=1,apad,atrim=start={v0:.4f}:end={v1:.4f},"
              f"asetpts=PTS-STARTPTS[a]")
    out = rel(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    run([exe, "-hide_banner", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(rel(edl["audio"])),
         "-filter_complex", graph, "-map", "[v]", "-map", "[a]", "-t", f"{dur:.4f}",
         "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p", "-profile:v", "high",
         "-r", str(fps), "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-movflags", "+faststart", str(out)])
    lst.unlink(missing_ok=True)
    return out


def share_copy(edl, master, out, v0, v1, crf=22, maxrate="7000k"):
    """Smaller H.264 copy for sharing (about 200 MB for the full video): re-encodes the master's picture at
    CRF ~22 with a bitrate cap, and takes the audio from the original WAV (delayed by pre_roll), so the
    audio is encoded to AAC 256k once rather than transcoded from the master's AAC. +faststart for streaming."""
    exe = ffmpeg_bin()
    dur = v1 - v0
    pre_ms = int(round(edl["pre_roll"] * 1000))
    graph = (f"[1:a]aresample=48000,adelay={pre_ms}:all=1,apad,atrim=start={v0:.4f}:end={v1:.4f},"
             f"asetpts=PTS-STARTPTS[a]")
    out = rel(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    run([exe, "-hide_banner", "-y", "-i", str(master), "-i", str(rel(edl["audio"])), "-filter_complex", graph,
         "-map", "0:v", "-map", "[a]", "-t", f"{dur:.4f}", "-c:v", "libx264", "-preset", "slow", "-crf", str(crf),
         "-maxrate", maxrate, "-bufsize", "14000k", "-pix_fmt", "yuv420p", "-profile:v", "high", "-r", str(edl["fps"]),
         "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", str(out)])
    return out


def grab_stills(video, times_v, v0, out_dir, stem):
    exe = ffmpeg_bin()
    out_dir = rel(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    outs = []
    for t in times_v:
        p = out_dir / f"{stem}_{t:07.2f}s.png"
        run([exe, "-hide_banner", "-y", "-ss", f"{t - v0:.4f}", "-i", str(video), "-frames:v", "1", "-update", "1", str(p)])
        outs.append(p)
    return outs


# --------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edl", nargs="?", default="video/edl.json")
    ap.add_argument("out", nargs="?", default="video/out.mp4")
    ap.add_argument("--range", nargs=2, type=float, metavar=("V0", "V1"), help="render only this span (video seconds)")
    ap.add_argument("--song-end", type=float, help="render from the start to this SONG time (e.g. 75)")
    ap.add_argument("--captions", default=None, help="ASS to burn (default: regenerate video/build/captions.ass)")
    ap.add_argument("--no-captions", action="store_true")
    ap.add_argument("--all-overlays", action="store_true",
                    help="also draw overlays marked enabled:false (in-world text painted into keyframes)")
    ap.add_argument("--stills", default=None, help="comma list of times to grab after rendering (sNN = song time)")
    ap.add_argument("--stills-dir", default=None)
    ap.add_argument("--preset", default="slow", help="x264 preset for the final encode")
    ap.add_argument("--crf", type=int, default=16)
    ap.add_argument("--share-copy", default=None, metavar="PATH",
                    help="also write a smaller share copy (CRF 22, 7 Mbps cap, AAC 256k, +faststart)")
    ap.add_argument("-j", "--jobs", type=int, default=max(2, (os.cpu_count() or 4) // 2))
    a = ap.parse_args()

    t_start = time.time()
    edl = load_edl(a.edl)
    tl = load_timeline(edl.get("timeline"))
    total = edl_duration(edl, tl)
    v0, v1 = 0.0, total
    if a.range:
        v0, v1 = max(0.0, a.range[0]), min(total, a.range[1])
    if a.song_end is not None:
        v1 = min(total, edl["pre_roll"] + a.song_end)
    v0 = round(v0 * edl["fps"]) / edl["fps"]
    v1 = round(v1 * edl["fps"]) / edl["fps"]

    captions = None
    if not a.no_captions:
        if a.captions:
            captions = rel(a.captions)
        else:
            from captions import build as build_captions
            captions = BUILD / "captions.ass"
            _, _, n_ev = build_captions(edl.get("timeline"), a.edl, captions, all_overlays=a.all_overlays)
            print(f"captions: {captions} ({n_ev} events)")

    segs, F = plan(edl, tl, v0, v1)
    seg_dir = BUILD / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)
    specs = [segment_spec(edl, tl, s) for s in segs]
    files = [seg_dir / f"{sp['id']}_{sp['hash']}.mp4" for sp in specs]
    todo = [(sp, f) for sp, f in zip(specs, files) if not f.exists()]
    missing = sorted({sp["id"] for sp in specs if sp["kind"] == "shot" and sp["mode"] != "video"})
    print(f"plan: {len(specs)} segments for {v0:.2f}-{v1:.2f}s ({len(todo)} to render, "
          f"{len(specs) - len(todo)} cached); {len(missing)} shots without footage -> still/slate")
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        for i, _ in enumerate(ex.map(lambda sf: render_segment(*sf), todo)):
            pass
    print(f"segments done in {time.time() - t_start:.1f}s")
    out = final_pass(edl, tl, files, v0, v1, a.out, captions, preset=a.preset, crf=a.crf)
    print(f"wrote {out} ({v1 - v0:.2f}s) in {time.time() - t_start:.1f}s")
    if a.share_copy:
        sc = share_copy(edl, out, a.share_copy, v0, v1)
        print(f"wrote share copy {sc} ({sc.stat().st_size / 1e6:.0f} MB)")
    if a.stills:
        times = []
        for tok in a.stills.split(","):
            tok = tok.strip()
            times.append(edl["pre_roll"] + float(tok[1:]) if tok.startswith("s") else float(tok))
        times = [t for t in times if v0 <= t < v1]
        stills = grab_stills(out, times, v0, a.stills_dir or (Path(a.out).parent / "stills"), Path(a.out).stem)
        for p in stills:
            print(f"  still {p}")


if __name__ == "__main__":
    main()
