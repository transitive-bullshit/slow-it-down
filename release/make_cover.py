"""Covers for the release and for social posts, all from outpaints of poster base B_shh plus the poster's neon title.

usage: python release/make_cover.py [square] [vertical]    (default: both)
  square:   release/cover-work/sid_full.png  (B_shh outpainted to 1:1, 4K)
            -> release/cover.jpg              3000x3000, "slow it down" + the teal "down down" staircase, as on the poster
            -> release/cover-title-only.jpg   "slow it down" alone, so the cover text matches the release title exactly
  vertical: release/cover-work/sid_vert.png  (sid_full outpainted to 9:16)
            -> release/cover-vertical.jpg     1440x2560 TikTok / Reels cover. Her face and the title stay inside the middle
               3:4 band the profile grid shows, and clear of the feed's caption (bottom) and buttons (right edge).
Each cover-work image has its fal receipt (prompt + parameters) next to it.
"""
import pathlib, sys
import numpy as np
from PIL import Image, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "video/poster"))
from make_posters import neon, LEAD_PAL, BACK_PAL, FONTS  # noqa: E402

WORK = ROOT / "release/cover-work"


def title(img, x, y, s, staircase=True):
    """The poster's title block at scale s (1 = the 1920x1080 poster's 150 px type), top-left at (x, y)."""
    f_lead = ImageFont.truetype(str(FONTS / "TiltNeon-Regular.ttf"), round(150 * s))
    f_down = ImageFont.truetype(str(FONTS / "Neonderthaw-Regular.ttf"), round(92 * s))
    w1, w2 = f_lead.getlength("slow it"), f_lead.getlength("down")
    neon(img, "slow it", f_lead, (x, y), LEAD_PAL)
    neon(img, "down", f_lead, (x + 0.42 * w1, y + 150 * s), LEAD_PAL)
    if staircase:
        for k, (dx, dy) in enumerate(((0.42 * w1 + w2 + 34 * s, 205 * s), (0.42 * w1 + w2 + 120 * s, 285 * s))):
            neon(img, "down", f_down, (x + dx, y + dy), BACK_PAL, glow=0.75 - 0.2 * k, bed=0.3)


def load(name, size):
    return np.asarray(Image.open(WORK / name).convert("RGB").resize(size, Image.LANCZOS), float) / 255


def save(img, name):
    Image.fromarray((np.clip(img, 0, 1) * 255).astype("uint8")).save(ROOT / "release" / name, quality=95, subsampling=0)
    print("wrote", name)


def square():
    N = 3000
    for name, stair in (("cover.jpg", True), ("cover-title-only.jpg", False)):
        img = load("sid_full.png", (N, N))
        title(img, round(0.055 * N), round(0.60 * N), N / 1080 * 0.62, stair)   # in the haze left of her, as on the poster
        save(img, name)


def vertical():
    """The title stacked down the dark left column ("slow" / "it" / "down"), with the teal "down"s cascading below it:
    the poster's staircase turned on its side. Everything sits inside the 3:4 band the profile grid shows (y 12.5-87.5%)."""
    W, H = 1440, 2560
    img = load("sid_vert.png", (W, H))
    size = 1
    while True:                                       # the largest type whose widest word fits the left column
        f_lead = ImageFont.truetype(str(FONTS / "TiltNeon-Regular.ttf"), size + 4)
        if max(f_lead.getlength(w) for w in ("slow", "it", "down")) > 0.46 * W: break
        size += 4
    f_lead = ImageFont.truetype(str(FONTS / "TiltNeon-Regular.ttf"), size)
    f_down = ImageFont.truetype(str(FONTS / "Neonderthaw-Regular.ttf"), round(size * 0.62))
    x, y, lh = round(0.06 * W), round(0.405 * H), round(size * 0.98)
    for k, word in enumerate(("slow", "it", "down")):
        neon(img, word, f_lead, (x, y + k * lh), LEAD_PAL)
    wd = f_lead.getlength("down")
    for k, (dx, dy) in enumerate(((0.30 * wd, 3.05 * lh), (0.62 * wd, 3.62 * lh))):
        neon(img, "down", f_down, (x + dx, y + dy), BACK_PAL, glow=0.75 - 0.2 * k, bed=0.3)
    save(img, "cover-vertical.jpg")


if __name__ == "__main__":
    steps = [a for a in sys.argv[1:] if a in ("square", "vertical")] or ["square", "vertical"]
    for step in steps: globals()[step]()
