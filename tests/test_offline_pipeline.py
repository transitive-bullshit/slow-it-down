"""Offline smoke tests: the storyboard, EDL, and caption builders run on the committed data.

No media, no API keys, no network. Paid generation (video/generate.py) and rendering are deliberately not exercised.
"""
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def run(args, cwd=ROOT):
    r = subprocess.run([sys.executable, *map(str, args)], cwd=cwd, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, f"{args} failed:\n{r.stdout[-1500:]}\n{r.stderr[-3000:]}"
    return r


def test_shotlist_is_up_to_date(tmp_path):
    """video/shotlist.json is exactly what video/shots.py generates from the committed timeline."""
    (tmp_path / "video").mkdir()
    shutil.copy(ROOT / "video/timeline.json", tmp_path / "video/timeline.json")
    run([ROOT / "video/shots.py"], cwd=tmp_path)
    fresh = json.loads((tmp_path / "video/shotlist.json").read_text())
    committed = json.loads((ROOT / "video/shotlist.json").read_text())
    assert fresh == committed, "video/shotlist.json is stale: run `uv run python video/shots.py` and commit it"
    assert len(committed["shots"]) == 70


def test_edl_builds(tmp_path):
    out = tmp_path / "edl.json"
    run(["video/tools/make_placeholder_edl.py", "-o", out])
    edl = json.loads(out.read_text())
    assert len(edl["shots"]) == 70
    assert edl["cards"][-1]["kind"] == "end"
    starts = [s["start"] for s in edl["shots"]]
    assert starts == sorted(starts), "shots should be in timeline order"


def test_captions_build(tmp_path):
    edl, ass = tmp_path / "edl.json", tmp_path / "captions.ass"
    run(["video/tools/make_placeholder_edl.py", "-o", edl])
    run(["video/tools/captions.py", "video/timeline.json", edl, ass])
    text = ass.read_text()
    assert "[Events]" in text
    assert text.count("Dialogue:") > 1000, "expected per-word neon layers for the whole song"
    assert "METR" in text, "display spellings from the timeline should reach the captions"
