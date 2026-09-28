"""Detect and crop comic-panel borders / letterbox bars that the image model sometimes paints, then rescale back to 16:9.
usage: python video/fix_borders.py [--dry] [files...]   (default: all video/gen/keyframes/*.png; originals kept as *_raw.png)"""
import sys, pathlib, numpy as np
from PIL import Image
def edge(a, axis_len, rows=True):
    """Pixels in from an edge covered by a painted bar/border: a near-flat black (or light) band that ends in a sharp
    jump to picture. Dark vignettes that fade gradually into the painting are left alone."""
    line = lambda i: a[i] if rows else a[:, i]
    flat = lambda l: (l.std(axis=0).mean() <= 2.5 and l.mean() <= 8) or (l.std(axis=0).mean() <= 7 and l.mean() >= 210)
    n = 0
    while n < int(axis_len * 0.14) and flat(line(n)): n += 1
    if n < 4: return 0
    return n if any(line(min(n + k, axis_len - 1)).std(axis=0).mean() >= 25 for k in range(0, 18)) else 0
def crop_box(im):
    a = np.asarray(im.convert("RGB")).astype(np.float32); h, w = a.shape[:2]
    t, b = edge(a, h), edge(a[::-1], h); l, r = edge(a, w, False), edge(a[:, ::-1], w, False)
    if max(t, b, l, r) < 4: return None
    m = 6                                          # a few extra pixels past the painted edge line
    x0, y0, x1, y1 = l + (m if l else 0), t + (m if t else 0), w - r - (m if r else 0), h - b - (m if b else 0)
    cw, ch = x1 - x0, y1 - y0                        # trim the long side back to 16:9, centered
    if cw / ch > 16 / 9: nw = int(ch * 16 / 9); x0 += (cw - nw) // 2; x1 = x0 + nw
    else: nh = int(cw * 9 / 16); y0 += (ch - nh) // 2; y1 = y0 + nh
    return (x0, y0, x1, y1), (t, b, l, r)
if __name__ == "__main__":
    dry = "--dry" in sys.argv; files = [pathlib.Path(f) for f in sys.argv[1:] if f != "--dry"] or sorted(pathlib.Path("video/gen/keyframes").glob("*.png"))
    for p in files:
        if p.stem.endswith("_raw"): continue
        im = Image.open(p); res = crop_box(im)
        if not res: continue
        box, tblr = res; print(f"{p.stem}: border t/b/l/r={tblr} -> crop {box}")
        if not dry:
            raw = p.with_name(p.stem + "_raw.png")
            if not raw.exists(): im.save(raw)
            im.crop(box).resize(im.size, Image.LANCZOS).save(p)
