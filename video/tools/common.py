"""Shared helpers for the caption / card / render tools.

Paths in timeline.json / edl.json / shotlist.json are relative to the project root.
All lyric/shot/footnote times are SONG seconds; the final video is `pre_roll` + song (+ `tail`).
"""
from __future__ import annotations

import functools
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "video"
TOOLS = VIDEO / "tools"
FONTS = TOOLS / "fonts"
BUILD = VIDEO / "build"


def rel(p) -> Path:
    """Resolve a project-relative (or absolute) path."""
    p = Path(p)
    return p if p.is_absolute() else ROOT / p


def load_json(p):
    with open(rel(p)) as f:
        return json.load(f)


def load_timeline(path=None):
    """Final video/timeline.json, falling back to the provisional one."""
    if path:
        return load_json(path)
    for cand in ("video/timeline.json", "video/timeline_provisional.json"):
        if rel(cand).exists():
            return load_json(cand)
    raise FileNotFoundError("no video/timeline.json")


def song_duration(tl) -> float:
    return float(tl.get("duration") or max(l["end"] for l in tl["lines"]))


# --------------------------------------------------------------------------- ffmpeg

def _filters(exe) -> str:
    try:
        return subprocess.run([exe, "-hide_banner", "-filters"], capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return ""


def has_filter(exe, name) -> bool:
    return any(len(l.split()) > 1 and l.split()[1] == name for l in _filters(exe).splitlines())


@functools.lru_cache(maxsize=None)
def ffmpeg_bin(require_libass=True) -> str:
    """An ffmpeg with libass (`subtitles`/`ass` filters).

    Order: $FFMPEG, /opt/homebrew/bin/ffmpeg, the static build bundled by the
    `imageio-ffmpeg` wheel (ships libass + fontconfig + freetype + harfbuzz + x264),
    then whatever `ffmpeg` is on PATH. The Homebrew 9.x bottle is built without libass.
    """
    cands = []
    if os.environ.get("FFMPEG"):
        cands.append(os.environ["FFMPEG"])
    cands.append("/opt/homebrew/bin/ffmpeg")
    try:
        import imageio_ffmpeg
        cands.append(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        pass
    if shutil.which("ffmpeg"):
        cands.append(shutil.which("ffmpeg"))
    seen = []
    for c in cands:
        if c in seen or not Path(c).exists():
            continue
        seen.append(c)
        if not require_libass or has_filter(c, "subtitles"):
            return c
    if require_libass:
        raise RuntimeError("no ffmpeg with libass found (tried %s). `uv pip install imageio-ffmpeg` "
                           "provides one." % ", ".join(seen))
    return seen[0]


@functools.lru_cache(maxsize=None)
def ffprobe_bin():
    for c in (os.environ.get("FFPROBE"), "/opt/homebrew/bin/ffprobe", shutil.which("ffprobe")):
        if c and Path(c).exists():
            return c
    return None


def ffmpeg_env():
    """Environment for ffmpeg runs: point the static build's fontconfig at our config."""
    env = dict(os.environ)
    conf = FONTS / "fonts.conf"
    if conf.exists():
        env["FONTCONFIG_FILE"] = str(conf)
    return env


def probe(path) -> dict:
    """{duration, width, height, fps, has_video} for a media file (ffprobe, else ffmpeg -i)."""
    path = str(rel(path))
    fp = ffprobe_bin()
    if fp:
        r = subprocess.run([fp, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
                           capture_output=True, text=True)
        if r.returncode == 0:
            d = json.loads(r.stdout)
            vs = [s for s in d.get("streams", []) if s.get("codec_type") == "video"]
            info = {"duration": float(d.get("format", {}).get("duration") or 0), "has_video": bool(vs)}
            if vs:
                v = vs[0]
                num, den = (v.get("avg_frame_rate") or v.get("r_frame_rate") or "0/1").split("/")
                info.update(width=int(v.get("width", 0)), height=int(v.get("height", 0)),
                            fps=float(num) / float(den) if float(den) else 0.0)
                if v.get("duration"):
                    info["duration"] = float(v["duration"])
            return info
    r = subprocess.run([ffmpeg_bin(False), "-hide_banner", "-i", path], capture_output=True, text=True)
    info = {"duration": 0.0, "has_video": False}
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    if m:
        info["duration"] = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    m = re.search(r"Video: .*?(\d{2,5})x(\d{2,5}).*?([\d.]+) fps", r.stderr)
    if m:
        info.update(has_video=True, width=int(m.group(1)), height=int(m.group(2)), fps=float(m.group(3)))
    return info


def run(cmd, quiet=True, **kw):
    """Run an ffmpeg command; raise with the tail of stderr on failure."""
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, env=ffmpeg_env(), **kw)
    if r.returncode != 0:
        tail = "\n".join(r.stderr.strip().splitlines()[-25:])
        raise RuntimeError(f"command failed ({r.returncode}): {' '.join(map(str, cmd))[:600]}\n{tail}")
    return r


# --------------------------------------------------------------------------- ASS helpers

def ass_time(t: float) -> str:
    t = max(0.0, t)
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def hex_rgb(h: str):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def c(h: str) -> str:
    """'#RRGGBB' -> ASS override colour '&HBBGGRR&'."""
    r, g, b = hex_rgb(h)
    return f"&H{b:02X}{g:02X}{r:02X}&"


def a(v: float | int) -> str:
    """alpha as ASS '&HAA&'; float 0..1 is OPACITY (1 = opaque), int is raw ASS alpha (0 = opaque)."""
    if isinstance(v, float):
        v = int(round((1.0 - max(0.0, min(1.0, v))) * 255))
    return f"&H{max(0, min(255, v)):02X}&"


def style_colour(h: str, alpha: int = 0) -> str:
    r, g, b = hex_rgb(h)
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"


def ass_escape(text: str) -> str:
    return text.replace("\\", "⧵").replace("{", "(").replace("}", ")").replace("\n", " ")


def ass_header(w, h, styles, title="captions"):
    return (f"[Script Info]\n; generated by video/tools/captions.py\nTitle: {title}\nScriptType: v4.00+\n"
            f"PlayResX: {w}\nPlayResY: {h}\nWrapStyle: 2\nScaledBorderAndShadow: yes\nKerning: yes\n"
            f"YCbCr Matrix: TV.709\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
            "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
            "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            + "\n".join(styles) + "\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, "
            "MarginV, Effect, Text\n")


# --------------------------------------------------------------------------- fonts / measurement

@functools.lru_cache(maxsize=None)
def font_manifest():
    p = FONTS / "fonts.json"
    if not p.exists():
        raise FileNotFoundError("run `python video/tools/fetch_fonts.py` first")
    return json.loads(p.read_text())


class Font:
    """Text metrics that match libass: an ASS \\fs N makes (winAscent + winDescent) == N px."""

    _cache: dict = {}

    def __new__(cls, role):
        if role not in cls._cache:
            cls._cache[role] = super().__new__(cls)
            cls._cache[role]._init(role)
        return cls._cache[role]

    def _init(self, role):
        import uharfbuzz as hb
        info = font_manifest()["roles"][role]
        self.role, self.info = role, info
        self.path = FONTS / info["file"]
        self.family = info["family"]
        self.bold, self.italic = info["bold"], info["italic"]
        self.upem = info["units_per_em"]
        self.asc_u, self.desc_u = info["win_ascent"], info["win_descent"]
        self.cap_u, self.x_u = info["cap_height"], info["x_height"]
        blob = hb.Blob.from_file_path(str(self.path))
        self._hb_face = hb.Face(blob)
        self._hb_font = hb.Font(self._hb_face)
        self._hb = hb

    def em(self, fs):             # pixels per em at ASS font size fs
        return fs * self.upem / (self.asc_u + self.desc_u)

    def ascent(self, fs):         # baseline offset from the top of the line box
        return fs * self.asc_u / (self.asc_u + self.desc_u)

    def descent(self, fs):
        return fs * self.desc_u / (self.asc_u + self.desc_u)

    def cap(self, fs):
        return self.cap_u * self.em(fs) / self.upem

    def xh(self, fs):
        return self.x_u * self.em(fs) / self.upem

    def _shape(self, text):
        hb = self._hb
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self._hb_font, buf, {"kern": True, "liga": True})
        return buf

    def width(self, text, fs, fsp=0.0, scale_x=100.0):
        buf = self._shape(text)
        adv = sum(p.x_advance for p in buf.glyph_positions)
        return (adv * self.em(fs) / self.upem + fsp * len(text)) * scale_x / 100.0

    def ink(self, text, fs):
        """(top, bottom) of the inked glyphs relative to the baseline, in px (y down, top < 0)."""
        buf = self._shape(text)
        top, bot = 0.0, 0.0
        for info in buf.glyph_infos:
            ext = self._hb_font.get_glyph_extents(info.codepoint)
            if ext is None:
                continue
            top = max(top, ext.y_bearing)
            bot = min(bot, ext.y_bearing + ext.height)
        k = self.em(fs) / self.upem
        return -top * k, -bot * k

    def style_line(self, name, fs, primary="#FFFFFF", outline="#000000", back="#000000", bord=0, shad=0,
                   an=7, spacing=0, p_alpha=0, o_alpha=0, b_alpha=0):
        return (f"Style: {name},{self.family},{fs},{style_colour(primary, p_alpha)},&H000000FF,"
                f"{style_colour(outline, o_alpha)},{style_colour(back, b_alpha)},{-1 if self.bold else 0},"
                f"{-1 if self.italic else 0},0,0,100,100,{spacing},0,1,{bord},{shad},{an},0,0,0,1")


# --------------------------------------------------------------------------- EDL

GRADES = ("none", "bw", "bw_to_color", "neon", "strobe", "amber", "silver", "fisheye", "dawn", "gold")

# In-world text that the regenerated keyframes now paint in themselves; these overlays default to off
# (EDL "enabled": false) and only render with --all-overlays or an explicit "enabled": true.
PAINTED_IN_OVERLAYS = {"S07", "C1d", "C2d", "C3d", "V03", "O04"}


def overlay_enabled(ov, force_all=False):
    if force_all:
        return True
    if "enabled" in ov:
        return bool(ov["enabled"])
    if ov.get("optional"):
        return False
    return ov.get("shot") not in PAINTED_IN_OVERLAYS
ZONES = ("lower", "upper", "left", "right", "center")
CARD_KINDS = ("quote", "title", "end", "credit", "image")   # image: a still held for the card's frames (the poster)


def load_edl(path):
    """Load edl.json and fill defaults (see video/tools/README.md for the schema)."""
    e = load_json(path)
    e.setdefault("fps", 24)
    e.setdefault("size", [1920, 1080])
    e.setdefault("pre_roll", 6.0)
    e.setdefault("tail", 0.0)
    e.setdefault("audio", "video/audio/suno_B.wav")
    e.setdefault("timeline", "video/timeline.json")
    e.setdefault("look", {})
    e["look"].setdefault("grain", 0.2)
    e["look"].setdefault("vignette", 0.3)
    for s in e.setdefault("shots", []):
        s.setdefault("src", None)
        s.setdefault("src_in", 0.0)
        s.setdefault("speed", 1.0)
        s.setdefault("grade", "none")
        s.setdefault("letterbox", False)
        s.setdefault("fx", [])
        s.setdefault("caption_zone", "lower")
        s.setdefault("retime", "slow")
        s.setdefault("lb_shift", 0.0)
        if not 0.0 <= float(s.get("caption_inset") or 0.0) <= 0.4:
            raise ValueError(f"shot {s['id']}: caption_inset must be between 0 and 0.4 (fraction of frame width)")
        sc = s.get("src_crop")
        if sc is not None and not (len(sc) == 4 and 0 <= sc[0] < sc[2] <= 1 and 0 <= sc[1] < sc[3] <= 1):
            raise ValueError(f"shot {s['id']}: src_crop must be [x0, y0, x1, y1] fractions with x0<x1, y0<y1")
        if not 0.0 <= float(s["lb_shift"]) <= 0.2:
            raise ValueError(f"shot {s['id']}: lb_shift must be between 0 and 0.2 (fraction of frame height)")
        if s["retime"] not in ("slow", "freeze"):
            raise ValueError(f"shot {s['id']}: retime must be 'slow' or 'freeze'")
        if s["grade"] not in GRADES:
            raise ValueError(f"shot {s['id']}: unknown grade {s['grade']!r} (one of {GRADES})")
        if s["caption_zone"] not in ZONES:
            raise ValueError(f"shot {s['id']}: unknown caption_zone {s['caption_zone']!r} (one of {ZONES})")
        if s["end"] <= s["start"]:
            raise ValueError(f"shot {s['id']}: end <= start")
    for cd in e.setdefault("cards", []):
        if cd.get("kind") not in CARD_KINDS:
            raise ValueError(f"card {cd.get('id')}: unknown kind {cd.get('kind')!r} (one of {CARD_KINDS})")
        if cd["kind"] == "image" and not (cd.get("src") and rel(cd["src"]).exists()):
            raise ValueError(f"card {cd.get('id')}: image card needs an existing 'src' file")
    e.setdefault("footnotes", [])
    e.setdefault("overlays", [])
    e["shots"].sort(key=lambda s: s["start"])
    return e


def edl_duration(e, tl=None) -> float:
    """Total video length in seconds: pre_roll + song + tail (and never shorter than the last card)."""
    tl = tl or load_timeline(e.get("timeline"))
    d = e["pre_roll"] + song_duration(tl) + e["tail"]
    return max([d] + [cd["end"] for cd in e["cards"]])
