#!/usr/bin/env python3
"""Download the caption/card fonts (Google Fonts, SIL OFL) and resolve their names for libass.

    python video/tools/fetch_fonts.py            # download missing fonts, write fonts.json + fonts.conf, verify
    python video/tools/fetch_fonts.py --force    # re-download everything

Output (video/tools/fonts/):
  *.ttf           static TrueType instances served by the Google Fonts CSS API
  OFL-<family>.txt  licence for each family (from github.com/google/fonts)
  fonts.json      role -> {file, family (name ID 1, what libass matches), bold, italic, metrics}
  fonts.conf      a fontconfig config (our dir + system dirs) for the static ffmpeg build's libass

The verify step renders one ASS line per role through ffmpeg/libass and checks the
`fontselect:` log line resolves to our file (not a system fallback).
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONTS = HERE / "fonts"
sys.path.insert(0, str(HERE))

# role -> (Google Fonts family, weight, italic, local file name, OFL dir in google/fonts)
FAMILIES = {
    "neon":        ("Tilt Neon", 400, False, "TiltNeon-Regular.ttf", "tiltneon"),
    "neon_sign":   ("Monoton", 400, False, "Monoton-Regular.ttf", "monoton"),
    "neon_script": ("Neonderthaw", 400, False, "Neonderthaw-Regular.ttf", "neonderthaw"),
    "serif_italic": ("Playfair Display", 400, True, "PlayfairDisplay-Italic.ttf", "playfairdisplay"),
    "serif_italic_semibold": ("Playfair Display", 600, True, "PlayfairDisplay-SemiBoldItalic.ttf", "playfairdisplay"),
    "chrome":      ("Abril Fatface", 400, False, "AbrilFatface-Regular.ttf", "abrilfatface"),
    "mono":        ("IBM Plex Mono", 400, False, "IBMPlexMono-Regular.ttf", "ibmplexmono"),
    "mono_light":  ("IBM Plex Mono", 300, False, "IBMPlexMono-Light.ttf", "ibmplexmono"),
    "mono_medium": ("IBM Plex Mono", 500, False, "IBMPlexMono-Medium.ttf", "ibmplexmono"),
    "card_title":  ("Bodoni Moda", 500, False, "BodoniModa-Medium.ttf", "bodonimoda"),
    "card_title_bold": ("Bodoni Moda", 800, False, "BodoniModa-ExtraBold.ttf", "bodonimoda"),
    "card_italic": ("Bodoni Moda", 400, True, "BodoniModa-Italic.ttf", "bodonimoda"),
    "typewriter":  ("Courier Prime", 400, False, "CourierPrime-Regular.ttf", "courierprime"),
    "hand":        ("Caveat", 500, False, "Caveat-Medium.ttf", "caveat"),
}

CSS_API = "https://fonts.googleapis.com/css2?family={fam}:ital,wght@{ital},{wght}"
OFL_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/{dir}/OFL.txt"


def fetch(url: str) -> bytes:
    # An empty User-Agent makes the CSS API serve plain TrueType (instead of woff/woff2).
    req = urllib.request.Request(url, headers={"User-Agent": ""})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def download(force=False):
    FONTS.mkdir(parents=True, exist_ok=True)
    for role, (fam, wght, ital, fname, ofl_dir) in FAMILIES.items():
        out = FONTS / fname
        if out.exists() and not force:
            continue
        css = fetch(CSS_API.format(fam=fam.replace(" ", "+"), ital=int(ital), wght=wght)).decode()
        m = re.search(r"url\((https://[^)]+\.ttf)\)", css)
        if not m:
            raise SystemExit(f"no TTF url for {fam} {wght} {'italic' if ital else ''}:\n{css[:400]}")
        out.write_bytes(fetch(m.group(1)))
        print(f"  downloaded {fname:40s} ({out.stat().st_size // 1024} KB)")
        lic = FONTS / f"OFL-{ofl_dir}.txt"
        if not lic.exists():
            try:
                lic.write_bytes(fetch(OFL_URL.format(dir=ofl_dir)))
            except Exception as e:  # licence text is nice-to-have; the font is still OFL
                print(f"  (could not fetch OFL.txt for {fam}: {e})")


def name_record(tt, nid):
    rec = tt["name"].getName(nid, 3, 1, 0x409) or tt["name"].getName(nid, 1, 0, 0)
    return str(rec) if rec else None


def resolve():
    from fontTools.ttLib import TTFont
    roles, files = {}, {}
    for role, (fam, wght, ital, fname, _) in FAMILIES.items():
        path = FONTS / fname
        tt = TTFont(path, lazy=True)
        os2, head, hhea = tt["OS/2"], tt["head"], tt["hhea"]
        family1 = name_record(tt, 1)
        sub2 = name_record(tt, 2) or "Regular"
        info = {
            "file": fname,
            "family": family1,                       # what goes in the ASS Fontname field
            "style": sub2,
            "full_name": name_record(tt, 4),
            "ps_name": name_record(tt, 6),
            "typo_family": name_record(tt, 16),
            "weight_class": os2.usWeightClass,
            "bold": "Bold" in sub2,                  # ASS Bold flag needed to pick this face
            "italic": bool(os2.fsSelection & 1),     # ASS Italic flag needed to pick this face
            "units_per_em": head.unitsPerEm,
            "win_ascent": os2.usWinAscent,
            "win_descent": os2.usWinDescent,
            "cap_height": getattr(os2, "sCapHeight", 0) or int(0.7 * head.unitsPerEm),
            "x_height": getattr(os2, "sxHeight", 0) or int(0.5 * head.unitsPerEm),
            "hhea_ascent": hhea.ascent,
            "hhea_descent": hhea.descent,
        }
        roles[role] = info
        files[fname] = info
    manifest = {
        "note": "family = OpenType name ID 1, which libass matches against the ASS Fontname; "
                "set Bold/Italic flags as listed to select the face. All fonts: SIL Open Font License.",
        "roles": roles,
    }
    (FONTS / "fonts.json").write_text(json.dumps(manifest, indent=1))
    return manifest


def write_fontconfig():
    cache = FONTS / ".fccache"
    cache.mkdir(exist_ok=True)
    conf = f"""<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <!-- paths relative to this file, so the config works from any checkout -->
  <dir prefix="relative">.</dir>
  <dir>/System/Library/Fonts</dir>
  <dir>/Library/Fonts</dir>
  <dir>~/Library/Fonts</dir>
  <dir>/usr/share/fonts</dir>
  <cachedir prefix="relative">.fccache</cachedir>
</fontconfig>
"""
    (FONTS / "fonts.conf").write_text(conf)


def verify(manifest):
    from common import ffmpeg_bin, ffmpeg_env, ass_header
    exe = ffmpeg_bin(require_libass=True)
    styles = []
    events = []
    for i, (role, info) in enumerate(manifest["roles"].items()):
        styles.append(f"Style: R{i},{info['family']},48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,"
                      f"{-1 if info['bold'] else 0},{-1 if info['italic'] else 0},0,0,100,100,0,0,1,1,0,7,10,10,10,1")
        events.append(f"Dialogue: 0,0:00:00.00,0:00:01.00,R{i},,0,0,0,,{{\\pos(20,{10 + i * 52})}}{role}: Slow it down 0123")
    ass = ass_header(1920, 1080, styles) + "\n".join(events) + "\n"
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "v.ass"
        p.write_text(ass)
        png = Path(td) / "v.png"
        r = subprocess.run([exe, "-hide_banner", "-loglevel", "verbose", "-y", "-f", "lavfi", "-i",
                            "color=c=black:s=1920x1080:d=1", "-vf",
                            f"ass=filename={p}:fontsdir={FONTS}:shaping=complex", "-frames:v", "1", "-update", "1", str(png)],
                           capture_output=True, text=True, env=ffmpeg_env())
        log = r.stderr
        ok = True
        for role, info in manifest["roles"].items():
            pat = re.compile(r"fontselect: \(" + re.escape(info["family"]) + r", (\d+), (\d+)\) -> ([^,]+)")
            hits = [m.group(3) for m in pat.finditer(log)]
            good = any(Path(h).name == info["file"] or info["file"] in h or h.endswith(info["ps_name"] or "?")
                       for h in hits)
            print(f"  {role:22s} '{info['family']}' b={int(info['bold'])} i={int(info['italic'])} -> "
                  f"{hits[0] if hits else 'NOT SELECTED'} {'OK' if good else '<-- check'}")
            ok &= good
        if "impossible to init fontconfig" in log:
            print("  fontconfig: NOT initialised (libass falls back to CoreText)")
        else:
            print("  fontconfig: initialised via FONTCONFIG_FILE=" + str(FONTS / "fonts.conf"))
        return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-verify", action="store_true")
    a = ap.parse_args()
    download(a.force)
    write_fontconfig()
    m = resolve()
    for role, info in m["roles"].items():
        print(f"  {role:22s} {info['file']:36s} family='{info['family']}' style='{info['style']}'")
    if not a.no_verify:
        sys.exit(0 if verify(m) else 1)
