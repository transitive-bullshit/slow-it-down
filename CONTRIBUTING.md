# Contributing

This repo is the full working directory behind [Slow It Down – AI Music Video](https://www.transitivebullsh.it/projects/slow-it-down-ai-music-video): the pipeline code, every prompt, the shot list and timeline, the review tool, and a receipt for every paid generation. This doc covers how to run it, where things live, and what’s deliberately left out.

## Setup

You’ll need [uv](https://docs.astral.sh/uv/), `ffmpeg` (`brew install ffmpeg`), and a [fal](https://fal.ai) API key. It was built on an Apple Silicon Mac with Python 3.12.

```bash
uv sync                              # the video pipeline
uv sync --group timing               # + word timings, the beat grid, vocal separation (beat_this, mlx-whisper, audio-separator)
uv sync --group audio-experiments    # + everything the rejected audio rounds in scripts/ used
cp .env.example .env                 # then fill in FAL_KEY (the other keys are only for the experiments and the Notion publisher)
```

Run scripts with `uv run --env-file .env python <script>`. uv manages `.venv` and makes it match `uv.lock` exactly, so `uv sync` removes anything else you installed there by hand.

A few extras, only if you need them:

- **The audio experiments** also need the `rubberband` CLI (`brew install rubberband`).
- **Seed-VC** (singing voice conversion, rejected) lives in its own environment. Clone [Seed-VC](https://github.com/Plachta/Seed-VC) into `tools/seed-vc/`, then create `.venv-seedvc` from [`tools/seedvc-requirements-macos.txt`](tools/seedvc-requirements-macos.txt). See [`scripts/seedvc_convert.sh`](scripts/seedvc_convert.sh).
- **pip instead of uv:** `uv export --no-hashes --no-emit-project > requirements.txt` generates a pip file from the lock.

## The pipeline

The one input that isn’t in the repo is the song itself: put the Suno track at `video/audio/suno_B.wav`. Everything else is in git.

```bash
uv run --group timing python scripts/align_lyrics.py video/audio/suno_B_whisper_mix.json video/audio/suno_B.wav   # word timings -> video/timeline.json
uv run python video/shots.py                                              # storyboard -> video/shotlist.json
uv run --env-file .env python video/generate.py keyframes                 # one still per shot
uv run --env-file .env python video/generate.py clips                     # image-to-video
uv run --env-file .env python video/generate.py lipsync                   # the two rap close-ups
uv run python video/tools/make_placeholder_edl.py                         # shot list -> video/edl.json
uv run python video/tools/render.py video/edl.json video/build/full.mp4 --share-copy video/build/share.mp4
uv run python video/review/build_review.py --cut video/build/full.mp4 --share video/build/share.mp4
uv run python video/review/server.py                                      # the review tool at http://localhost:8765
```

`generate.py` skips anything that already exists, so every step is safe to re-run. Each paid call writes its prompt, parameters, and result to [`video/gen/receipts/`](video/gen/receipts/). A full pass costs roughly $55 on fal: about $11 in keyframes, $43 in clips, and $1 in lip-sync.

### Where each step lives

| Step | Code | Output |
|---|---|---|
| Lyrics | [`docs/lyrics-current.txt`](docs/lyrics-current.txt), [`docs/03-lyrics-v1.md`](docs/03-lyrics-v1.md) | |
| Song (Suno V6) | [`docs/lyrics-suno.txt`](docs/lyrics-suno.txt), [`docs/06-suno-package.md`](docs/06-suno-package.md) | `video/audio/suno_B.wav` (not in git) |
| Timing | [`scripts/align_lyrics.py`](scripts/align_lyrics.py) | [`video/timeline.json`](video/timeline.json) |
| Storyboard | [`video/shots.py`](video/shots.py) | [`video/shotlist.json`](video/shotlist.json) |
| Characters | [`video/restyle_refs_br.py`](video/restyle_refs_br.py) | `video/gen/refs/` |
| Keyframes, clips, lip-sync | [`video/generate.py`](video/generate.py), [`video/models.json`](video/models.json) | `video/gen/{keyframes,clips,lipsync}/` |
| Captions, footnotes, grades, render | [`video/tools/`](video/tools/README.md), [`video/annotations.py`](video/annotations.py) | `video/build/` |
| Review | [`video/review/`](video/review/) | `video/review/feedback.md` |
| Poster | [`video/poster/make_posters.py`](video/poster/make_posters.py) | `video/poster/options/` |
| Write-up | [`video/notion/`](video/notion/) | the Notion page |

The compositor has its own docs in [`video/tools/README.md`](video/tools/README.md). The model scout’s notes are in [`video/scout/README.md`](video/scout/README.md).

### Redoing a single shot

This is how every review round worked:

1. Edit the shot’s prompt in [`video/shots.py`](video/shots.py) and run it.
2. Move the old files aside: `video/gen/keyframes/<ID>.png` and `video/gen/clips/<ID>.mp4`.
3. Run `generate.py keyframes <ID>`, then `generate.py clips <ID>`. If the shot has an end frame (`end=`), the clip automatically uses Veo’s first + last frame mode.
4. Rebuild the EDL and re-render. Only the changed shot’s segment re-renders, which takes a few minutes.

If Veo refuses a shot, run `FALLBACK=wan uv run --env-file .env python video/generate.py clips <ID>` to use Wan 2.2 instead.

## Tests

```bash
uv run pytest
```

The smoke tests in [`tests/`](tests/) run offline in about a second. They check that the committed shot list matches `video/shots.py`, that the EDL builds, and that the captions build from the committed timeline and fonts. [CI](.github/workflows/test.yml) runs them on every push and pull request, along with a compile check of every Python file. It installs only the core dependencies, has no secrets, and never calls fal or any other API.

## What’s in the repo

```text
docs/                  creative direction, lyrics (plain + Suno-tagged), audio plan, video treatment, Suno package
scripts/               audio analysis and the audio experiments (alignment, ACE-Step, Lyria, Seed-VC, stems)
analysis/              beat grid, song map, and vocal line timings for the original (timings only, no lyrics)
prototypes/            specs and the listening page for the rejected audio rounds
video/shots.py         the storyboard: 70 shots with image and motion prompts -> video/shotlist.json
video/generate.py      keyframes, clips, and lip-sync on fal (models in video/models.json)
video/gen/receipts/    the prompt, parameters, and result of every paid generation
video/tools/           the compositor: captions (ASS/libass), grades, cards, and the final render
video/review/          the scene-by-scene review tool and my feedback history (feedback_v3.md, feedback_v4.md)
video/poster/          the first-frame poster options
release/               the DistroKid kit: square cover, store lyrics, form answers (the WAV and covers are git-ignored)
video/notion/          the script that published the write-up to Notion
```

`lyric-lab.html` and `prototypes/listen.html` are in git, but they play audio that isn’t, so they only work locally.

## What’s not in the repo, on purpose

- **The original song, its stems, and every audio prototype built on them.** They’re copyrighted, and not mine to redistribute. Please don’t commit them, or anything derived from the original recording.
- **Generated media** (about 6 GB of keyframes, clips, renders, and caches). It’s all reproducible from `video/shotlist.json` and the receipts, and the showcase copies are hosted on [my site](https://www.transitivebullsh.it/projects/slow-it-down-ai-music-video).
- **Third-party code and model weights:** the Seed-VC checkout and the virtualenvs.

`.gitignore` blocks media files everywhere. For a deliberate exception, use `git add -f`.
