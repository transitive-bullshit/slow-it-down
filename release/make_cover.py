"""Album cover (3000x3000) for the DistroKid release: the square outpaint of poster base B_shh + the poster's neon title.

usage: python release/make_cover.py
  in:  release/cover-work/sid_full.png   (nano-banana-pro edit of video/poster/base/B_shh.png to 1:1 4K; receipt next to it)
  out: release/cover.jpg        "slow it down" + the teal "down down" staircase, as on the poster
       release/cover-title-only.jpg   "slow it down" alone, so the cover text matches the release title exactly
"""
import pathlib, sys
import numpy as np
from PIL import Image, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "video/poster"))
from make_posters import neon, LEAD_PAL, BACK_PAL, FONTS  # noqa: E402

N = 3000
SRC = ROOT / "release/cover-work/sid_full.png"


def cover(staircase):
    img = np.asarray(Image.open(SRC).convert("RGB").resize((N, N), Image.LANCZOS), float) / 255
    s = N / 1080 * 0.62                                     # the poster's type scale, fitted to the haze left of her
    f_lead = ImageFont.truetype(str(FONTS / "TiltNeon-Regular.ttf"), round(150 * s))
    f_down = ImageFont.truetype(str(FONTS / "Neonderthaw-Regular.ttf"), round(92 * s))
    l1, l2 = "slow it", "down"
    w1, w2 = f_lead.getlength(l1), f_lead.getlength(l2)
    x, y = round(0.055 * N), round(0.60 * N)
    neon(img, l1, f_lead, (x, y), LEAD_PAL)
    neon(img, l2, f_lead, (x + 0.42 * w1, y + 150 * s), LEAD_PAL)
    if staircase:
        for k, (dx, dy) in enumerate(((0.42 * w1 + w2 + 34 * s, 205 * s), (0.42 * w1 + w2 + 120 * s, 285 * s))):
            neon(img, "down", f_down, (x + dx, y + dy), BACK_PAL, glow=0.75 - 0.2 * k, bed=0.3)
    return Image.fromarray((np.clip(img, 0, 1) * 255).astype("uint8"))


if __name__ == "__main__":
    for name, stair in (("cover.jpg", True), ("cover-title-only.jpg", False)):
        cover(stair).save(ROOT / "release" / name, quality=95, subsampling=0)
        print("wrote", name)
