"""Assets for the Notion project page (all uploaded to and hosted by Notion): python video/notion/prepare_assets.py
Writes video/notion/assets/: cover, composites of each look/likeness round, the storyboard, audio excerpts from the
rejected rounds, and a few outtake clips. The review-tool screenshot is made separately (screenshot_review.py).
"""
import json, pathlib, subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "video/notion/assets"; OUT.mkdir(parents=True, exist_ok=True)
G = ROOT / "video/gen"
FONT = "/System/Library/Fonts/Supplemental/Futura.ttc"
BG, AMBER, MUTED = (12, 11, 10), (232, 176, 96), (170, 160, 146)

def ff(*args): subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str, args)], check=True)
def font(size): return ImageFont.truetype(FONT, size)
def trim_bars(im, thresh=10):
    """Drop uniform near-black bars (baked-in letterboxing) from the top and bottom."""
    import numpy as np
    rows = np.asarray(im.convert("L")).mean(axis=1); keep = np.where(rows > thresh)[0]
    return im.crop((0, int(keep[0]), im.width, int(keep[-1]) + 1)) if len(keep) and (keep[0] > 4 or keep[-1] < im.height - 5) else im
def fit(im, w, h):
    """Scale to cover w x h, centre-crop."""
    im = trim_bars(im)
    s = max(w / im.width, h / im.height); im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2; return im.crop((x, y, x + w, y + h))

def labelled_grid(panels, cols, w, h, out, label_h=64, pad=12):
    """panels: [(image path, label, sublabel)] -> one sheet with a caption bar under each panel."""
    rows = (len(panels) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (w + pad) + pad, rows * (h + label_h + pad) + pad), BG); d = ImageDraw.Draw(sheet)
    for i, (p, lab, sub) in enumerate(panels):
        x, y = pad + (i % cols) * (w + pad), pad + (i // cols) * (h + label_h + pad)
        sheet.paste(fit(Image.open(p).convert("RGB"), w, h), (x, y))
        d.text((x + 4, y + h + 8), lab, fill=AMBER, font=font(30))
        if sub: d.text((x + 4 + d.textlength(lab, font=font(30)) + 14, y + h + 13), sub, fill=MUTED, font=font(24))
    sheet.save(out, quality=86); return out

def stacked(rows_, out, w=1800, label_h=58):
    """rows_: [(sheet path, label, sublabel)] stacked vertically with a caption bar above each."""
    ims = [Image.open(p).convert("RGB") for p, _, _ in rows_]
    ims = [im.resize((w, round(im.height * w / im.width)), Image.LANCZOS) for im in ims]
    H = sum(im.height + label_h for im in ims)
    sheet = Image.new("RGB", (w, H), BG); d = ImageDraw.Draw(sheet); y = 0
    for im, (_, lab, sub) in zip(ims, rows_):
        d.text((10, y + 12), lab, fill=AMBER, font=font(32))
        if sub: d.text((10 + d.textlength(lab, font=font(32)) + 16, y + 18), sub, fill=MUTED, font=font(26))
        sheet.paste(im, (0, y + label_h)); y += im.height + label_h
    sheet.save(out, quality=86); return out

# ---- cover: the poster (B)
Image.open(ROOT / "video/poster/poster.png").convert("RGB").resize((1920, 1080), Image.LANCZOS).save(OUT / "cover.jpg", quality=92)

# ---- the three looks
stacked([(G / "refs/_contact_all.jpg", "Look v1 · stylized 3D", "rejected: too Pixar, and the wardrobe kept changing"),
         (G / "refs/_contact_cast_v2.jpg", "Look v2 · painterly cyberpunk", "rejected: way too much purple neon"),
         (G / "refs/_contact_cast_v3.jpg", "Look v3 · Blade Runner restraint", "final: smoke, sodium amber, steel teal, recognizable caricatures")],
        OUT / "looks.jpg")

# ---- Dario likeness passes
labelled_grid([(G / "refs/_v0/dario_v1.png", "v1", "generic, Pixar-ish"),
               (G / "refs/_v1/dario.png", "v2", "handsome, but not him"),
               (G / "refs/dario_br.png", "v3", "recognizable caricature"),
               (G / "refs/dario_head.png", "final", "leaner, fitter, still him")], 2, 1280, 720, OUT / "dario.jpg")

# ---- the honey bear
labelled_grid([(G / "refs/_v1_bear.png", "try 1", "a random teddy bear"),
               (G / "refs/bear_d.png", "try 3", "reads as Pooh"),
               (G / "keyframes/R05.png", "final shot", "his shadow isn't bear-shaped")], 3, 960, 540, OUT / "pooh.jpg")

# ---- storyboard: all 70 shots, current keyframes
shots = json.load(open(ROOT / "video/shotlist.json"))["shots"]
cols, W, H, pad, lab = 7, 540, 304, 8, 30
rows = (len(shots) + cols - 1) // cols
sb = Image.new("RGB", (cols * (W + pad) + pad, rows * (H + lab + pad) + pad), BG); d = ImageDraw.Draw(sb)
for i, s in enumerate(shots):
    x, y = pad + (i % cols) * (W + pad), pad + (i // cols) * (H + lab + pad)
    sb.paste(fit(Image.open(G / f"keyframes/{s['id']}.png").convert("RGB"), W, H), (x, y))
    d.text((x + 2, y + H + 4), f"{s['id']}  {s['start']:.1f}s  {s['grade']}", fill=AMBER, font=font(20))
sb.save(OUT / "storyboard.jpg", quality=84)

# ---- audio excerpts from the rejected rounds (18 s, faded)
P = ROOT / "prototypes/out"
for src, ss, out in ((P / "A_elevenlabs_oneshot.mp3", 30, "round1-elevenlabs-music.mp3"),
                     (P / "L2_ly_t1_layered.mp3", 30, "round2-lyria-plus-seedvc.mp3"),
                     (P / "ace/p1arms_s7.mp3", 3, "round3-ace-step-lyric-edit.mp3")):
    ff("-ss", ss, "-t", 18, "-i", src, "-af", "afade=t=in:d=0.3,afade=t=out:st=16.8:d=1.2", "-c:a", "libmp3lame", "-b:a", "160k", OUT / out)

# ---- outtakes (720p)
for src, out, audio in ((G / "clips/_R05_wan.mp4", "outtake-shadow-grows-ears.mp4", False),
                        (G / "clips/_v3/V04_v4vapor.mp4", "outtake-wand-blows-smoke.mp4", False),
                        (G / "lipsync/C1c.mp4", "outtake-lipsync-cut.mp4", True)):
    ff("-i", src, "-vf", "scale=1280:-2:flags=lanczos,fps=24,format=yuv420p", "-c:v", "libx264", "-crf", "22", "-preset", "slow",
       *(["-c:a", "aac", "-b:a", "128k"] if audio else ["-an"]), "-movflags", "+faststart", OUT / out)

for p in sorted(OUT.iterdir()): print(f"{p.name:40s} {p.stat().st_size / 1e6:6.2f} MB")
