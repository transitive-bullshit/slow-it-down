"""Re-style the cast into the painterly cyberpunk-noir look. Approved designs (refs/_v0) are used as identity references.
One look per character for the whole video: THE-DARIO in the charcoal shawl cardigan, the muse in the red satin dress."""
import json, pathlib, concurrent.futures as cf, requests, fal_client
R = pathlib.Path("video/gen/refs"); V0 = R / "_v0"
SL = json.load(open("video/shotlist.json")); STYLE = SL["style"]; CH = SL["characters"]
ARGS = {"aspect_ratio": "16:9", "resolution": "2K", "output_format": "png", "safety_tolerance": "5"}
KEEP = "Keep the exact same character design, face and outfit; change only the rendering style."
JOBS = {
  "dario": (["dario_v1"], f"Repaint this exact man: identical face, curly dark hair, dark-rimmed glasses and stubble, same charcoal cashmere shawl-collar cardigan over a black t-shirt. Waist-up, three-quarter view, in a neon cyberpunk nightclub. {KEEP} {STYLE}"),
  "muse": (["muse_v2"], f"Repaint this exact woman: identical face, glossy black bob, iridescent blue-violet eyes, silver mesh choker and forearm mesh, same deep red satin slip dress. Waist-up, three-quarter view, in a neon cyberpunk nightclub. {KEEP} {STYLE}"),
  "moloch": (["moloch"], f"Repaint this exact character: the chrome bull mask with curved horns and glowing red eyes, black leather coat, heavy rings, hands on DJ turntables, red lasers and haze. {KEEP} {STYLE}"),
  "don": (["don"], f"Repaint this exact caricature: same face and swept golden hair, navy suit and very long red tie, in a gilded candlelit dining room. {KEEP} {STYLE}"),
  "sama": (["sama"], f"Repaint this exact man: same face and tousled light-brown hair, grey crewneck under a glossy black puffer jacket, one-strap backpack, thin gold chain, in a glossy nightclub. {KEEP} {STYLE}"),
  "consultant": (["consultant"], f"Repaint this exact man in a navy suit with an ID lanyard and a tablet, in a dark nightclub corner booth. {KEEP} {STYLE}"),
  "eacc": (["eacc"], f"Repaint this exact young man in an ACCELERATE bomber jacket shouting into a megaphone in a nightclub. {KEEP} {STYLE}"),
  "bear": ([], f"{CH['bear']}, standing behind a neon-lit bar counter and hugging a round clay honey pot labeled WEIGHTS with honey dripping from his paw, sly but innocent expression, comedic. {STYLE.replace('sensual late-night mood, ', 'playful late-night mood, ')}"),
}
up = {}
def upl(p):
    if p not in up: up[p] = fal_client.upload_file(str(p))
    return up[p]
def one(item):
    rid, (refs, prompt) = item
    out = R / f"{rid}.png"
    if out.exists(): return f"exists {rid}"
    try:
        if refs: res = fal_client.subscribe("fal-ai/nano-banana-pro/edit", arguments={"prompt": prompt, "image_urls": [upl(V0 / f"{r}.png") for r in refs], **ARGS})
        else: res = fal_client.subscribe("fal-ai/nano-banana-pro", arguments={"prompt": prompt, **ARGS})
        out.write_bytes(requests.get(res["images"][0]["url"], timeout=300).content); return f"ok {rid}"
    except Exception as e:
        return f"FAIL {rid}: {str(e)[:160]}"
with cf.ThreadPoolExecutor(1) as ex:
    for r in ex.map(one, JOBS.items()): print(r, flush=True)
