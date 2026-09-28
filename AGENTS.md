# AGENTS.md

An AI-made R&B parody music video, published at https://www.transitivebullsh.it/projects/slow-it-down-ai-music-video. This repo is a working directory of scripts, prompts, and data, not a package. For setup, commands, and a step-by-step map, see `CONTRIBUTING.md`. The compositor is documented in `video/tools/README.md`.

## Mental model

```text
docs/ lyrics → song (Suno, external) → video/timeline.json (timed words)
→ video/shots.py → video/shotlist.json (shots + prompts)
→ video/generate.py → video/gen/ (keyframes, clips, lip-sync on fal)
→ video/tools/make_placeholder_edl.py → video/edl.json → video/tools/render.py → video/build/
→ video/review/ (the user's scene-by-scene notes land in video/review/feedback.md) → repeat
```

## Edit sources, not outputs

- **Shots and prompts:** edit `video/shots.py`, then rerun it. Don't hand-edit `shotlist.json` or `edl.json`; they get regenerated, and a test fails if the shot list drifts from `shots.py`.
- **Per-shot render tweaks:** `video/tools/make_placeholder_edl.py`.
- **Models:** `video/models.json`.
- **Lyrics:** `docs/lyrics-suno.txt`.
- **The plan vs. what shipped:** `docs/05-video-treatment.md` is the original plan. `video/shots.py` is what actually shipped.

## Costs and side effects

- **Paid APIs:** `video/generate.py`, `video/poster/`, and `video/scout/` call fal. Ask before batch runs, and regenerate only the shots in question.
- **Regenerating:** generation skips existing outputs. To redo something, move the file aside rather than deleting it. Every paid call leaves a receipt in `video/gen/receipts/`.
- **The public site:** `video/notion/` writes to the user's website CMS. Only run it when asked.
- **Keys:** they come from `.env` (see `.env.example`). Never print them.

## Media is not in git

- **A fresh clone has no media:** no audio, keyframes, clips, or renders. `.gitignore` blocks media everywhere.
- **Copyright:** never commit the original song or anything derived from it. Showcase media lives on the user's site (R2); link to it rather than adding files.
- **Where docs go:** `README.md` is a marketing page that mirrors the published write-up. Technical docs go in `CONTRIBUTING.md`.

## Creative rules that held up

- **Real people:** they're recognizable caricatures, never photoreal. The likeness comes from reference images; shot prompts describe them without naming them.
- **Look:** one outfit per character, and restrained noir lighting rather than heavy neon.
- **Prompting:** ask for what you want, not what you don't ("no smoke" still gets you smoke).
- **Refusals:** when a model refuses a shot, retry with `FALLBACK=wan`. Composite anything that must stay static.

## Checks

`uv run pytest` runs offline in about a second, and CI runs the same thing. `uv run` is safe. `uv sync` removes anything that isn't in `uv.lock` from `.venv`.
