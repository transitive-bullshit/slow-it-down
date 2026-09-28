"""Contact sheet of keyframes (or any stills) with shot IDs: python video/contact_sheet.py out.jpg ID [ID ...] (IDs map to video/gen/keyframes/ID.png)."""
import sys, pathlib
from PIL import Image, ImageDraw, ImageFont
out, ids = sys.argv[1], sys.argv[2:]
cols = 4 if len(ids) > 6 else min(3, len(ids)); W, H, pad = 800, 450, 10
rows = (len(ids) + cols - 1) // cols
sheet = Image.new("RGB", (cols * (W + pad) + pad, rows * (H + pad) + pad), (10, 10, 14)); d = ImageDraw.Draw(sheet)
f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Futura.ttc", 34)
for i, sid in enumerate(ids):
    p = pathlib.Path(sid) if sid.endswith(".png") else pathlib.Path(f"video/gen/keyframes/{sid}.png")
    x, y = pad + (i % cols) * (W + pad), pad + (i // cols) * (H + pad)
    if p.exists(): sheet.paste(Image.open(p).convert("RGB").resize((W, H)), (x, y))
    d.rectangle((x, y, x + 110, y + 46), fill=(0, 0, 0)); d.text((x + 8, y + 4), p.stem, fill=(255, 90, 200), font=f)
sheet.save(out, quality=85); print(out, sheet.size)
