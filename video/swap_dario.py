"""Swap the updated THE-DARIO likeness (refs/dario.png) into existing keyframes without changing their composition.
usage: python video/swap_dario.py [ids...]   (default: every shot with dario whose face is visible). Old frames go to keyframes/_v2."""
import json, sys, pathlib, shutil, time, concurrent.futures as cf, requests, fal_client
KF = pathlib.Path("video/gen/keyframes"); OLD = KF / "_v2"; OLD.mkdir(exist_ok=True)
SHOTS = {s["id"]: s for s in json.load(open("video/shotlist.json"))["shots"]}
SKIP = {"S03", "C1a"}   # seen from behind / hand only
PROMPT = ("In image 1, redraw only the man with dark curly hair and round dark-rimmed glasses so that his face and build match the man in image 2: "
          "a lean face with defined cheekbones and jaw, short neatly cropped dark curly hair, the same round dark-rimmed glasses, and a slim athletic build. "
          "Keep his pose, expression, gesture and charcoal cardigan, and keep everything else in image 1 exactly the same: composition, framing, camera angle, "
          "the other people, background, lighting, colors (if image 1 is black-and-white it stays black-and-white), any text, and the painterly neo-noir graphic-novel style. The output is image 1 with only his face and build changed; image 2 is just a face reference and none of its pose, gesture or background should appear. Full-bleed 16:9, no borders.")
ARGS = {"aspect_ratio": "16:9", "resolution": "2K", "output_format": "png", "safety_tolerance": "5"}
ref = fal_client.upload_file("video/gen/refs/dario.png")
def one(sid):
    p = KF / f"{sid}.png"; bak = OLD / f"{sid}.png"
    if bak.exists(): return f"done already {sid}"
    for k in range(6):
        try:
            res = fal_client.subscribe("fal-ai/nano-banana-pro/edit", arguments={"prompt": PROMPT, "image_urls": [fal_client.upload_file(str(p)), ref], **ARGS})
            data = requests.get(res["images"][0]["url"], timeout=300).content
            shutil.copy(p, bak); p.write_bytes(data); return f"ok {sid}"
        except Exception as e:
            if ("locked" in str(e) or "TOP_UP" in str(e) or "429" in str(e)) and k < 5: time.sleep(25); continue
            return f"FAIL {sid}: {str(e)[:200]}"
ids = sys.argv[1:] or [k for k, s in SHOTS.items() if "dario" in s["chars"] and k not in SKIP]
print(len(ids), "shots:", " ".join(ids), flush=True)
with cf.ThreadPoolExecutor(6) as ex:
    for r in ex.map(one, ids): print(time.strftime("%H:%M:%S"), r, flush=True)
