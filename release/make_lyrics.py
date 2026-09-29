"""Store lyrics for DistroKid: the written lyrics (docs/lyrics-current.txt), not the Suno-coaxing spellings.

usage: python release/make_lyrics.py   ->   release/lyrics.txt
The final take sings these lines in this order (checked against video/timeline.json), plus the wordless intro chant.
Undoes the pronunciation hacks: "Meter" -> METR, "exfill'ed" -> exfilled; drops trailing commas and curly apostrophes.
"""
import pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHANT = "Oh-oh-oh-oh-oh-oh, yo-oh, yo-oh, yo-oh"
FIXES = {"Meter in the room": "METR in the room", "exfill'ed": "exfilled", "’": "'"}

text = (ROOT / "docs/lyrics-current.txt").read_text()
for a, b in FIXES.items(): text = text.replace(a, b)
lines = [re.sub(r",\s*$", "", l.rstrip()) for l in text.strip().splitlines()]
(ROOT / "release/lyrics.txt").write_text(f"{CHANT}\n{CHANT}\n\n" + "\n".join(lines) + "\n")
print("wrote release/lyrics.txt")
