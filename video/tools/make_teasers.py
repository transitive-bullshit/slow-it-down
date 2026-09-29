"""X teasers: short chorus cuts of the finished video, each opening on its own poster frame.

usage: uv run python video/tools/make_teasers.py [posters] [cuts] [ids...]    (default: both steps, every teaser)
  posters -> video/build/teasers/<id>_poster.png   (1920x1080; X shows a video's first frame as its preview)
  cuts    -> video/build/teasers/<id>.mp4          (2 poster frames, the cut, a short ring-out, a fade to black)
             video/build/teasers/_posters.jpg      (the posters side by side)

The picture comes from the share render, so the captions, footnotes and grades match the full video. The sound
comes from the song WAV: the full mix for the cut, then a crossfade into the instrumental stem (video/audio/sep_B)
for the tail, so a cut can end between two sung lines without running into the next one. Nothing here calls an API.
"""
import json, pathlib, subprocess, sys, tempfile
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "video" / "poster"))
from make_posters import neon, LEAD_PAL, BACK_PAL  # noqa: E402  (the main poster's neon title)

SRC = ROOT / "video/build/slow_it_down_share_v5.mp4"
MIX, INST = ROOT / "video/audio/suno_B.wav", ROOT / "video/audio/sep_B/instrumental.wav"
OUT = ROOT / "video/build/teasers"
FONTS = ROOT / "video/tools/fonts"
EDL = json.load(open(ROOT / "video/edl.json"))
FPS, PRE = EDL["fps"], EDL["pre_roll"]
SHOTS = {s["id"]: s for s in EDL["shots"]}
POSTER_FRAMES = 2      # same as the full video: long enough to be the preview, short enough to vanish on autoplay
HOLD, XF = 1.2, 0.08   # picture held after the last line (fading to black), and the mix -> instrumental crossfade (s)

# Song seconds. t0/t1 sit where the lead's pitch track (sep_B vocals) changes words, at a breath where there is one;
# the choruses are sung straight through, so most joins have no silence. `ring` is how long the instrumental carries
# on after t1: each one takes the next drum hit as a button and fades before the next bar's groove comes in.
# head/tail name the first and last shot: when the audio starts before `head` (or runs past `tail`), that shot's
# edge frame is held instead of flashing the neighbouring shot.
TEASERS = {
    "A_dance": dict(  # chorus 2, second half: her solo dance -> "slower..." -> the grind -> "now she's aligned"
        t0=144.77, t1=168.44, ring=0.6, head="C2c", tail="C2h",
        poster=dict(key="C2c", side="right", scale=0.8, y=610)),
    "B_arms_race": dict(  # "Enough with the motherfuckin' ARMS RACE" -> all of chorus 1 -> "now she's aligned"
        t0=57.30, t1=91.66, ring=0.6, head="P06", tail="C1h",
        poster=dict(option="E_fader")),
    "C_clone_army": dict(  # "She's spawnin' agents on me... DJ Moloch" -> ARMS RACE -> "slow takeoff with me, mane"
        t0=128.41, t1=144.72, ring=0.55, head="P14", tail="C2b",
        poster=dict(key="P14", side="left", scale=0.9, y=630, shade=True)),
}


def draw_title(img, x, y, f_lead, f_down, s=1.0):
    """The main poster's title at scale s: amber "slow it / down" plus the backing vocal's teal "down" staircase."""
    w1, w2 = f_lead.getlength("slow it"), f_lead.getlength("down")
    neon(img, "slow it", f_lead, (x, y), LEAD_PAL)
    neon(img, "down", f_lead, (x + 0.42 * w1, y + 150 * s), LEAD_PAL)
    for k, (dx, dy) in enumerate(((0.42 * w1 + w2 + 34 * s, 205 * s), (0.42 * w1 + w2 + 120 * s, 285 * s))):
        neon(img, "down", f_down, (x + dx, y + dy), BACK_PAL, glow=0.75 - 0.2 * k, bed=0.3)


def poster(tid):
    p = TEASERS[tid]["poster"]
    if "option" in p:  # an already-composed option from video/poster/ (same title, same layout)
        im = Image.open(ROOT / "video/poster/options" / f"{p['option']}.png").convert("RGB")
    else:
        W, H = 1920, 1080
        im = ImageOps.fit(Image.open(ROOT / "video/gen/keyframes" / f"{p['key']}.png").convert("RGB"), (W, H), Image.LANCZOS)
        img = np.asarray(im, float) / 255
        if p.get("shade"):  # a soft dark pool under the title for busy frames
            yy, xx = np.mgrid[0:H, 0:W]
            cx = 0.22 * W if p["side"] == "left" else 0.78 * W
            d = np.sqrt(((xx - cx) / (0.42 * W)) ** 2 + ((yy - 0.78 * H) / (0.42 * H)) ** 2)
            img *= (1 - 0.55 * np.clip(1 - d, 0, 1) ** 1.5)[..., None]
        sc = p.get("scale", 1.0)
        f_lead = ImageFont.truetype(str(FONTS / "TiltNeon-Regular.ttf"), round(150 * sc))
        f_down = ImageFont.truetype(str(FONTS / "Neonderthaw-Regular.ttf"), round(92 * sc))
        w1, w2, wd = f_lead.getlength("slow it"), f_lead.getlength("down"), f_down.getlength("down")
        block = max(w1, 0.42 * w1 + w2 + 120 * sc + wd)
        x = 150 * sc if p["side"] == "left" else W - 110 * sc - block
        draw_title(img, x, p.get("y", 560), f_lead, f_down, sc)
        im = Image.fromarray((np.clip(img, 0, 1) * 255).astype("uint8"))
    out = OUT / f"{tid}_poster.png"
    im.save(out)
    print("poster", out.relative_to(ROOT), flush=True)
    return im


def frame(t):  # song seconds -> frame index in the rendered video
    return round((t + PRE) * FPS)


def audio(a0, n, ring, path):
    """The mix from song time a0 for n seconds, crossfading into `ring` seconds of the instrumental stem, then
    silence to the end of the HOLD."""
    mix, sr = sf.read(MIX, dtype="float32")
    inst = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", str(INST), "-f", "f32le", "-ac", "2", "-ar", str(sr), "-"],
                                        capture_output=True, check=True).stdout, "float32").reshape(-1, 2)  # 44.1k stem -> 48k
    i0, i1, it = round(a0 * sr), round((a0 + n) * sr), round(ring * sr)
    xf = round(XF * sr)
    body = mix[i0:i1 + xf].copy()
    body[:round(0.015 * sr)] *= np.linspace(0, 1, round(0.015 * sr))[:, None]    # no click on the way in
    ramp = np.linspace(0, 1, xf)[:, None]
    body[-xf:] *= ramp[::-1]                    # equal-gain crossfade: the instrumental is part of the mix (correlated)
    tail = inst[i1:i1 + xf + it].copy()
    tail[:xf] *= ramp
    k = np.arange(len(tail) - xf) / sr
    tail[xf:] *= np.cos(np.clip((k - 0.1) / (ring - 0.1), 0, 1) * np.pi / 2)[:, None]   # hold briefly, then fade
    body[-xf:] += tail[:xf]
    silence = lambda s: np.zeros((round(s * sr), 2), "float32")
    y = np.concatenate([silence(POSTER_FRAMES / FPS), body, tail[xf:], silence(max(0.0, HOLD - ring))])
    sf.write(path, y, sr, subtype="FLOAT")


def cut(tid):
    c = TEASERS[tid]
    f0, f1 = frame(c["t0"]), frame(c["t1"])
    h0, h1 = frame(SHOTS[c["head"]]["start"]), frame(SHOTS[c["tail"]]["end"])
    v0, v1 = max(f0, h0), min(f1, h1)                   # frames actually taken from the render
    n_tail = round(HOLD * FPS)
    total = (f1 - f0) + n_tail                          # cut + ring-out, in frames
    pad_in, pad_out = v0 - f0, total - (v0 - f0) - (v1 - v0)
    fade = round(0.9 * FPS)
    poster_png = OUT / f"{tid}_poster.png"
    out = OUT / f"{tid}.mp4"
    with tempfile.TemporaryDirectory() as tmp:
        wav = pathlib.Path(tmp) / "a.wav"
        audio(f0 / FPS - PRE, (f1 - f0) / FPS, c["ring"], wav)
        fc = (f"[0:v]trim=end_frame={POSTER_FRAMES},setpts=PTS-STARTPTS,scale=1920:1080,setsar=1,format=yuv420p[p];"
              f"[1:v]trim=end_frame={v1 - v0},setpts=PTS-STARTPTS,"
              f"tpad=start={pad_in}:start_mode=clone:stop={pad_out}:stop_mode=clone,"
              f"fade=t=out:start_frame={total - fade}:nb_frames={fade},setsar=1,format=yuv420p[v];"
              f"[p][v]concat=n=2:v=1:a=0[out]")
        cmd = ["ffmpeg", "-v", "error", "-y",
               "-loop", "1", "-framerate", str(FPS), "-t", f"{(POSTER_FRAMES + 1) / FPS:.4f}", "-i", str(poster_png),
               "-ss", f"{(v0 - 0.5) / FPS:.4f}", "-i", str(SRC),
               "-i", str(wav),
               "-filter_complex", fc, "-map", "[out]", "-map", "2:a",
               "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(FPS),
               "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-shortest", "-movflags", "+faststart", str(out)]
        subprocess.run(cmd, check=True)
    dur = (POSTER_FRAMES + total) / FPS
    print(f"cut    {out.relative_to(ROOT)}  {dur:.1f}s  (song {c['t0']:.2f}-{c['t1']:.2f}, "
          f"held {pad_in}+{pad_out - n_tail} frames)", flush=True)


def sheet(ims):
    tw, th, pad = 960, 540, 14
    s = Image.new("RGB", (len(ims) * (tw + pad) + pad, th + 2 * pad + 40), (12, 11, 10))
    d = ImageDraw.Draw(s)
    lab = ImageFont.truetype("/System/Library/Fonts/Supplemental/Futura.ttc", 30)
    for i, (tid, im) in enumerate(ims):
        x = pad + i * (tw + pad)
        s.paste(im.resize((tw, th), Image.LANCZOS), (x, pad))
        d.text((x + 4, pad + th + 6), tid.replace("_", " · ", 1).replace("_", " "), fill=(232, 176, 96), font=lab)
    s.save(OUT / "_posters.jpg", quality=88)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    steps = [a for a in sys.argv[1:] if a in ("posters", "cuts")] or ["posters", "cuts"]
    ids = [a for a in sys.argv[1:] if a in TEASERS] or list(TEASERS)
    if "posters" in steps:
        sheet([(t, poster(t)) for t in ids])
    if "cuts" in steps:
        for t in ids:
            cut(t)
