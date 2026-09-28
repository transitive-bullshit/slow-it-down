"""Cast refs, v2 look: restrained Blade Runner / 2049 neo-noir. THE-DARIO and DADDY SAMA become recognizable caricatures;
everyone else keeps their approved design (refs/_v1) and is only relit. Writes refs/<id>_br[_n].png candidates."""
import json, sys, pathlib, concurrent.futures as cf, requests, fal_client, time
R = pathlib.Path("video/gen/refs"); V1 = R / "_v1"
STYLE = ("painterly neo-noir graphic-novel frame in the spirit of Blade Runner (1982) and Blade Runner 2049: semi-realistic digital painting "
         "with visible brushstrokes and fine ink linework, adult realistic proportions, restrained desaturated palette, deep shadows, smoky haze "
         "and soft volumetric light shafts from one or two motivated sources, warm sodium-amber and cool steel-teal tones, neon used sparingly as "
         "small soft practical accents in the background only, rain-wet reflective surfaces, soft film grain, cinematic widescreen composition with "
         "generous negative space, not Pixar, not cartoonish, no glossy plastic 3D look, no oversaturated magenta or purple, full-bleed 16:9 image "
         "that fills the entire frame edge to edge, with no black bars, no letterbox, no panel borders and no captions")
DARIO = ("a recognizable, flattering graphic-novel caricature of Anthropic CEO Dario Amodei: early 40s, short dense dark-brown curly hair, "
         "round dark-rimmed glasses, a round friendly clean-shaven face with full cheeks, a big warm toothy smile, one hand raised mid-gesture "
         "as if explaining something, drawn with a fit, lean build")
SAMA = ("a recognizable graphic-novel caricature of OpenAI CEO Sam Altman: about 40, slim, short medium-brown hair swept up at the front, "
        "big wide-set green eyes with an intense earnest stare, straight brows, a lean face with high cheekbones and a narrow chin, clean-shaven, "
        "a tight-lipped little smirk")
OUT_D = "wearing a tailored charcoal cashmere shawl-collar cardigan over a black t-shirt"
OUT_S = "wearing a grey crewneck sweater under a glossy black puffer jacket, a one-strap backpack and a thin gold chain"
RELIGHT = ("Repaint this exact image in a restrained Blade Runner 2049 neo-noir palette: keep the identical character, face, pose, outfit and composition, "
           "but replace the saturated magenta and purple neon with smoky haze, deep shadow, warm sodium-amber key light and a cool steel-teal rim, "
           "neon only as small soft accents far in the background. ")
JOBS = {
  "dario_br": ([], f"character reference portrait, waist-up, three-quarter view: {DARIO}, {OUT_D}, standing in a dim smoky nightclub. {STYLE}"),
  "dario_br2": ([], f"character reference portrait, waist-up, facing camera: {DARIO}, {OUT_D}, leaning on a bar in a dim smoky nightclub. {STYLE}"),
  "sama_br": ([], f"character reference portrait, waist-up, three-quarter view: {SAMA}, {OUT_S}, standing in a dim smoky nightclub. {STYLE}"),
  "sama_br2": ([], f"character reference portrait, waist-up, facing camera: {SAMA}, {OUT_S}, in a dim smoky nightclub with a gold-lit bar behind him. {STYLE}"),
  "muse_br": (["muse"], RELIGHT + STYLE),
  "moloch_br": (["moloch"], RELIGHT.replace("replace the saturated magenta and purple neon with", "keep his red LED eyes and some red laser light, but otherwise use") + STYLE),
  "don_br": (["don"], RELIGHT + STYLE),
  "consultant_br": (["consultant"], RELIGHT + STYLE),
  "eacc_br": (["eacc"], RELIGHT + STYLE),
  "bear_br": (["bear"], RELIGHT + "Keep him a round golden-yellow cartoon honey bear with small black dot eyes in a grey Mao-style tunic, playful and comedic. " + STYLE.replace("adult realistic proportions, ", "")),
}
ARGS = {"aspect_ratio": "16:9", "resolution": "2K", "output_format": "png", "safety_tolerance": "5"}
def one(item):
    rid, (refs, prompt) = item
    out = R / f"{rid}.png"
    if out.exists(): return f"exists {rid}"
    for k in range(6):
        try:
            if refs: res = fal_client.subscribe("fal-ai/nano-banana-pro/edit", arguments={"prompt": prompt, "image_urls": [fal_client.upload_file(str(V1 / f"{r}.png")) for r in refs], **ARGS})
            else: res = fal_client.subscribe("fal-ai/nano-banana-pro", arguments={"prompt": prompt, **ARGS})
            out.write_bytes(requests.get(res["images"][0]["url"], timeout=300).content); return f"ok {rid}"
        except Exception as e:
            if ("locked" in str(e) or "TOP_UP" in str(e)) and k < 5: time.sleep(25); continue
            return f"FAIL {rid}: {str(e)[:200]}"
ids = sys.argv[1:] or list(JOBS)
with cf.ThreadPoolExecutor(5) as ex:
    for r in ex.map(one, [(i, JOBS[i]) for i in ids]): print(r, flush=True)
