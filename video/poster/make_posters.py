"""Poster / first-frame options: the muse in Club Frontier + "slow it down" in the video's own neon caption style.

usage: python video/poster/make_posters.py [gen] [compose]    (default: both; gen skips images that already exist)
  gen      -> video/poster/base/<id>.png        (nano-banana-pro edit, conditioned on the muse's character ref)
  compose  -> video/poster/options/<id>.png     (1920x1080, the title set off-centre in amber neon + teal "down"s)
              video/poster/options/_sheet.jpg   (all options side by side)
The chosen one becomes the video's first frame (X shows the first frame as the preview) and the YouTube thumbnail.
"""
import json, pathlib, sys, time, concurrent.futures as cf
import numpy as np, requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[2]
P = ROOT / "video" / "poster"; (P / "base").mkdir(parents=True, exist_ok=True); (P / "options").mkdir(exist_ok=True)
SL = json.load(open(ROOT / "video/shotlist.json"))
MUSE = SL["characters"]["muse"] + ", in a deep red satin slip dress"
STYLE = SL["style"] + ", no text, letters or readable signage anywhere in the image"
FONTS = ROOT / "video/tools/fonts"

# id -> (prompt, side the title goes on)
CONCEPTS = {
    "A_glance": (f"A cinematic poster frame: {MUSE}, seen from behind at waist height as she walks away into the smoky amber haze of a dark nightclub dance floor, "
                 "glancing back over her bare shoulder straight at the camera with a slow, knowing half-smile; half of her face in shadow, one glowing violet eye catching "
                 "the light; she is placed on the right third of the frame and the left third is empty dark haze", "left"),
    "B_shh": (f"An intimate close-up poster frame: {MUSE}, face turned three-quarters toward the camera, lit by a single thin slash of warm amber light across her glowing "
              "violet eyes while the rest of her face falls into deep shadow, one finger pressed to her dark red lips as if to say shh, the silver mesh choker glinting; "
              "her face fills the right half of the frame and the left half is dark smoky nightclub haze with soft out-of-focus amber bokeh", "left"),
    "C_doorway": (f"A mysterious poster frame: the curvy silhouette of {MUSE} standing in the tall doorway of a smoky nightclub, backlit by warm amber haze so only a thin rim "
                  "of light traces her figure and the red satin, her face in shadow except for two softly glowing violet eyes looking at the camera, one hand resting on "
                  "the door frame; she stands on the left third and the right two thirds are dark haze with a faint red glow", "right"),
    "D_booth": (f"A poster frame: {MUSE}, reclining in a deep dark leather booth in a smoky nightclub, one arm draped along the back of the booth, legs crossed, looking "
                "straight at the camera through a thin veil of smoke with a slow inviting half-smile, a single shaft of warm amber light falling across her from above "
                "while the rest of the club stays dark; she is on the right half and the left third is empty dark haze", "left"),
    "E_fader": (f"A poster frame: in the foreground the elegant hand of {MUSE}, silver mesh on her forearm, fingertip slowly pulling a glowing amber tempo fader down on a "
                "DJ mixer; just behind it in soft focus her face, glowing violet eyes looking up at the camera, red lips parted, a red satin strap on her shoulder; "
                "the composition sits on the left two thirds and the right third is dark smoky negative space", "right"),
    "F_spotlight": (f"A low-angle poster frame: {MUSE}, alone on a black mirrored dance floor under a single warm amber spotlight, head tilted back and eyes closed, one arm "
                    "raised with her fingers in her black bob, the rest of the club lost in dark smoke, her reflection in the floor; she stands on the right third and "
                    "the left side is empty dark haze", "left"),
}

def gen(ids):
    import fal_client
    ref = fal_client.upload_file(str(ROOT / "video/gen/refs/muse.png"))
    def one(cid):
        out = P / "base" / f"{cid}.png"
        if out.exists(): return f"exists {cid}"
        prompt, _ = CONCEPTS[cid]
        for k in range(6):
            try:
                res = fal_client.subscribe("fal-ai/nano-banana-pro/edit", arguments={
                    "prompt": f"{prompt}. Use the reference image only for her face, hair, eyes and dress. {STYLE}",
                    "image_urls": [ref], "aspect_ratio": "16:9", "resolution": "2K", "output_format": "png", "safety_tolerance": "5"})
                out.write_bytes(requests.get(res["images"][0]["url"], timeout=300).content); return f"ok {cid}"
            except Exception as e:
                if ("locked" in str(e) or "TOP_UP" in str(e)) and k < 5: time.sleep(25); continue
                return f"FAIL {cid}: {str(e)[:200]}"
    with cf.ThreadPoolExecutor(6) as ex:
        for r in ex.map(one, ids): print(r, flush=True)

# ---------- neon type, matching captions.py (LEAD_PAL amber lead, BACK_PAL teal backing "down"s)
LEAD_PAL = dict(core="#FFF1D6", edge="#FFB54E", halo="#FF9E36", spill="#E57A22")
BACK_PAL = dict(core="#DCF5F2", edge="#8ACFCB", halo="#5AAFB1", spill="#2F8A93")
def rgb(h): return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], float) / 255
def neon(img, text, font, xy, pal, glow=1.0, bed=0.55):
    """Draw neon text onto an RGB float array (H, W, 3) in place: contrast bed, spill, halo, edge, crisp core."""
    H, W, _ = img.shape
    m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).text(xy, text, font=font, fill=255)
    fs = font.size
    a = np.asarray(m.filter(ImageFilter.GaussianBlur(0.30 * fs)), float) / 255
    img *= (1 - bed * np.clip(a * 1.6, 0, 1))[..., None]                          # dark bed for legibility
    for rad, col, k in ((0.55 * fs, "spill", 0.55), (0.22 * fs, "halo", 0.8), (0.07 * fs, "edge", 0.95)):
        g = np.asarray(m.filter(ImageFilter.GaussianBlur(rad)), float)[..., None] / 255
        img[:] = 1 - (1 - img) * (1 - np.clip(g * k * glow * 1.5, 0, 1) * rgb(pal[col]))   # screen blend
    tube = Image.new("L", (W, H), 0); ImageDraw.Draw(tube).text(xy, text, font=font, fill=255, stroke_width=max(2, round(0.035 * fs)), stroke_fill=255)
    t = np.asarray(tube.filter(ImageFilter.GaussianBlur(0.012 * fs)), float)[..., None] / 255
    img[:] = img * (1 - t) + rgb(pal["edge"]) * t
    core = np.asarray(m.filter(ImageFilter.GaussianBlur(0.006 * fs)), float)[..., None] / 255
    img[:] = img * (1 - core) + rgb(pal["core"]) * core

def compose(ids):
    W, H = 1920, 1080
    f_lead = ImageFont.truetype(str(FONTS / "TiltNeon-Regular.ttf"), 150)
    f_down = ImageFont.truetype(str(FONTS / "Neonderthaw-Regular.ttf"), 92)
    outs = []
    for cid in ids:
        src = P / "base" / f"{cid}.png"
        if not src.exists(): continue
        im = Image.open(src).convert("RGB").resize((W, H), Image.LANCZOS)
        img = np.asarray(im, float) / 255
        side = CONCEPTS[cid][1]
        l1, l2 = "slow it", "down"
        w1, w2, wd = f_lead.getlength(l1), f_lead.getlength(l2), f_down.getlength("down")
        block = max(w1, 0.42 * w1 + w2 + 120 + wd)          # title plus the teal staircase
        x = 150 if side == "left" else W - 110 - block
        y = 560
        neon(img, l1, f_lead, (x, y), LEAD_PAL)
        neon(img, l2, f_lead, (x + 0.42 * w1, y + 150), LEAD_PAL)
        # the backing vocal's staircase: two dimmer teal "down"s stepping down and right
        for k, (dx, dy) in enumerate(((0.42 * w1 + f_lead.getlength(l2) + 34, 205), (0.42 * w1 + f_lead.getlength(l2) + 120, 285))):
            neon(img, "down", f_down, (x + dx, y + dy), BACK_PAL, glow=0.75 - 0.2 * k, bed=0.3)
        out = Image.fromarray((np.clip(img, 0, 1) * 255).astype("uint8"))
        out.save(P / "options" / f"{cid}.png"); out.resize((1280, 720), Image.LANCZOS).save(P / "options" / f"{cid}_thumb.jpg", quality=90)
        outs.append((cid, out))
        print("composed", cid, flush=True)
    if outs:
        cols, tw, th, pad = 3, 960, 540, 14
        rows = (len(outs) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + pad + 40) + pad), (12, 11, 10)); d = ImageDraw.Draw(sheet)
        lab = ImageFont.truetype("/System/Library/Fonts/Supplemental/Futura.ttc", 30)
        for i, (cid, im) in enumerate(outs):
            x0, y0 = pad + (i % cols) * (tw + pad), pad + (i // cols) * (th + pad + 40)
            sheet.paste(im.resize((tw, th), Image.LANCZOS), (x0, y0)); d.text((x0 + 4, y0 + th + 4), cid.replace("_", " · "), fill=(232, 176, 96), font=lab)
        sheet.save(P / "options" / "_sheet.jpg", quality=88); print("sheet", sheet.size)

if __name__ == "__main__":
    steps = [a for a in sys.argv[1:] if a in ("gen", "compose")] or ["gen", "compose"]
    ids = [a for a in sys.argv[1:] if a in CONCEPTS] or list(CONCEPTS)
    if "gen" in steps: gen(ids)
    if "compose" in steps: compose(ids)
