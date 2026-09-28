# Caption and compositing pipeline

The tools that turn `timeline.json` + `edl.json` into the finished music video: in-world neon lyrics, footnotes and overlays (ASS/libass), noir cards, graded shots, film grain, and the delayed song.

**Look (current art direction):** a restrained Blade Runner (1982) / Blade Runner 2049 frame. Mostly shadow and smoky haze, sodium amber against steel teal, and neon only as small, soft accents. Captions are small and warm, as if lit in a Deakins frame.

```bash
source .venv/bin/activate                                   # Python 3.12
python video/tools/fetch_fonts.py                           # once: fonts -> video/tools/fonts/ (+ libass check)
python video/tools/make_placeholder_edl.py                  # video/edl.json from video/shotlist.json
python video/tools/render.py video/edl.json video/out.mp4   # captions + cards + shots -> final video
```

Test renders, both using the real keyframes as stills:
- `video/tests/caption_test_55-100.mp4`: song 55–100 s, from pre-chorus 1 into chorus 1. Stills are in `video/tests/stills_55-100/`.
- `video/tests/caption_test.mp4`: the cold open plus the first 75 s. Stills are in `video/tests/stills/`.

## ffmpeg and libass

The Homebrew ffmpeg (9.0.1, `/opt/homebrew/bin/ffmpeg`) is built **without libass, freetype and fontconfig**, so it has no `subtitles`, `ass` or `drawtext` filters. The tools therefore use the static ffmpeg 7.1 bundled with the `imageio-ffmpeg` wheel. It has libass, fontconfig, freetype, harfbuzz, fribidi and libx264.

- `common.ffmpeg_bin()` picks, in order: `$FFMPEG`, the Homebrew binary (only if it gains libass), the imageio binary, then `ffmpeg` on PATH.
- fontconfig gets its config from `video/tools/fonts/fonts.conf` (via `FONTCONFIG_FILE`). Without it, the static build's fontconfig can't initialise and libass falls back to CoreText.
- Captions are burned with the **`ass`** filter, `shaping=complex`, not with `subtitles`. The `subtitles` filter goes through lavf's ASS demuxer, which drops the `Kerning: yes` header, so glyphs would render unkerned and drift from the layout.

Packages added to `.venv`: `imageio-ffmpeg` (the ffmpeg), `fonttools` (name tables), and `uharfbuzz` (HarfBuzz text measurement that matches libass; PIL here has no raqm).

## The tools

| Tool | What it does |
|---|---|
| `fetch_fonts.py [--force]` | Downloads static TTF instances from the Google Fonts CSS API plus each family's OFL.txt. Writes `fonts/fonts.json` (role -> file, OpenType family name ID 1, bold/italic flags, metrics) and `fonts/fonts.conf`, then renders one line per role through libass to check that each resolves to our file. |
| `captions.py [timeline] [edl] [out.ass] [--no-ghost] [--all-overlays]` | Timeline + EDL -> `video/build/captions.ass`. Every event is offset by `pre_roll`. It takes footnotes and overlays from the EDL, or from `video/annotations.json` when the EDL has none. `render.py` runs it automatically. |
| `cards.py [edl] [--only C1,C2] [--force] [--stills DIR]` | Renders each EDL card to `video/build/cards/<id>_<hash>.mp4`: PIL frames piped to x264, B&W, grain. `render.py` calls it for any card that is missing or out of date. |
| `render.py [edl] [out.mp4] [--range V0 V1 \| --song-end S] [--stills 12,s61.9] [--preset slow] [--crf 16] [--captions f.ass \| --no-captions] [--all-overlays] [-j N]` | Plans segments, renders them in parallel (cached by content hash in `video/build/segments/`), then runs one final pass: concat, vignette, captions, grain, H.264 CRF 16 yuv420p 24 fps, and AAC 320k audio delayed by `pre_roll`. `--stills` grabs PNGs afterwards; a bare number is video time, and an `s` prefix means song time. |
| `render.py … --share-copy video/build/slow_it_down_share.mp4` | after the master, also writes a smaller share copy: CRF 22 with a 7 Mbps cap, AAC 256k taken straight from the WAV, `+faststart`. The full video comes out around 209 MB. |
| `make_placeholder_edl.py [--from shotlist\|timeline] [-o path]` | Builds a test EDL. The default source is the 70 shots in `video/shotlist.json`, with `src` = `video/gen/{clips,lipsync}/<id>.mp4` and `still` = `video/gen/keyframes/<id>.png`. `--from timeline` makes one shot per lyric line, graded by section: Intro bw, Verse 1 neon, Pre-Chorus strobe, Chorus amber (gold for chorus 3), Verse 2 silver, Rap fisheye, Outro dawn. Cards C1/C2/C3, 20 footnotes and 8 overlays come from `video/annotations.json`. |

### Missing footage

For each shot the renderer tries `src` (a video or an image), then `still` (a keyframe, with a slow push-in), then a dark placeholder slate. The slate shows a bokeh "club" backdrop with a silhouette opposite the caption zone, and the shot id, section, timing, grade, zone and prompt summary. Files that are unreadable or still being written (modified under 3 s ago) are skipped.

### Timing

Say a shot's slot is `D = end - start` and the source has `A = duration - src_in`.
- If `A >= D * speed`, the source is trimmed.
- If not, it's slowed to `A / D`, down to a minimum of 0.5x, using frame-blended `framerate`.
- Below 0.5x, it plays at 0.5x and freezes on its last frame.
- `make_placeholder_edl.py` also carries per-clip fixes found in review (C2c gets `caption_inset` 0.17 as well): P01 gets `src_in` 0.45 (its first 0.42 s is a static hold) and R09 gets `src_crop` [0, 0.14, 1, 1] (a black band is baked into its top 13%). A shotlist `src_in` / `src_crop` overrides these.
- Lip-sync shots (`"retime": "freeze"`) are never slowed. They play in real time from `src_in` and hold the last frame. `make_placeholder_edl.py` sets `src_in` to 0.1 s for them, because `generate.py` cuts their vocal 0.1 s before the shot starts.

Frame boundaries are `round(t * fps)`, so every segment has an exact frame count and audio sync holds (measured at 6.000 s).

## EDL schema (`video/edl.json`)

Shot and footnote times are in **song seconds**. Card times are in **video seconds**, where 0 is the first frame of the cold open. Video time = song time + `pre_roll`. The video's length is `pre_roll + song duration + tail`, or the end of the last card if that's later. Paths are relative to the project root.

```jsonc
{
  "fps": 24, "size": [1920, 1080],
  "pre_roll": 6.0,            // seconds of cold-open cards (silence) before the song
  "tail": 3.0,                // seconds of silence after the song (end card lives here)
  "audio": "video/audio/suno_B.wav",
  "timeline": "video/timeline.json",
  "look": {"grain": 0.2, "vignette": 0.3},   // global finishing, 0..1 (0 = off); keep grain subtle
  "shots": [{
    "id": "C1a",
    "src": "video/gen/clips/C1a.mp4",        // video or image; missing -> still -> slate
    "still": "video/gen/keyframes/C1a.png",  // optional fallback image (slow push-in)
    "start": 59.54, "end": 63.92,            // SONG seconds
    "src_in": 0.0,                           // seconds into the source
    "speed": 1.0,                            // playback speed (auto slow-down / freeze if short)
    "retime": "slow",                        // slow = slow down to 0.5x then freeze; freeze = real time + hold (lip-sync)
    "src_crop": [0, 0.14, 1, 1],             // optional [x0, y0, x1, y1] fractions: trim baked-in bars before the fit
    "grade": "amber",                        // none|bw|bw_to_color|neon|strobe|amber|silver|fisheye|dawn|gold
    "letterbox": true,                       // 2.39:1 bars (captions stay inside the picture)
    "lb_shift": 0.09,                        // letterbox headroom: move the picture down this fraction of
                                             // frame height under the bars (0..0.128 visible; 0 = centred)
    "caption_inset": 0.17,                   // optional: left/right-zone text this fraction of frame width in
                                             // from the edge (default 0.0625), for frame-edge foreground
    "fx": ["flash_in"],                      // see below
    "caption_zone": "upper",                 // lower|upper|left|right|center
    "fit": "cover",                          // optional: cover (crop) | contain (pad)
    "section": "Chorus", "prompt": "…", "motion": "…"   // optional, shown on placeholder slates
  }],
  "cards": [
    {"id": "C1", "start": 0.0, "end": 3.2, "kind": "quote",
     "text": "Biggest AI Rivals Agree They Need to Slow It Down",
     "sub": "— The Wall Street Journal, Sept. 13, 2026"},
    {"id": "C2", "start": 3.2, "end": 6.0, "kind": "title", "text": "AI SAFETY HAS A BRANDING PROBLEM."},
    {"id": "C3", "start": 253.32, "end": 263.4, "kind": "end",
     "text": "Don't pace the frontier.\nJust slow it down, baby.",
     "credit": ["THE-DARIO feat. DADDY SAMA — Slow It Down (Pace the Frontier Remix)",
                "Parody. Not affiliated with any lab, artist, or head of state."]}
    // kind "credit": text + sub (or credit[]) in the credit style
  ],
  "footnotes": [
    {"t": 38.31, "dur": 2.4, "anchor_line": 8,       // t = SONG time of the anchor word
     "text": "self-exfiltration: a model copying its own weights out",
     "anchor_word": 3}                               // optional index or word prefix; default = word nearest t
  ],
  "overlays": [
    {"shot": "C1a", "text": "BPM 200 → 64", "style": "led", "zone": "upper",
     "enabled": true,              // false = skip unless --all-overlays (text painted into the keyframe)
     "start": 59.6, "end": 63.9,   // optional SONG-time override (default: the shot's span)
     "pos": [960, 700],            // optional pixel centre (pin to a wall/prop), overrides the zone
     "size": 36, "color": "#FF9A2E", "pitch": 10}   // optional per style
  ]
}
```

Cards win over shots where they overlap, and gaps render black. A card is re-rendered whenever its JSON changes.

**Grades** (all ffmpeg filters, applied per shot). They're deliberately subtle, because the keyframes already carry the look:

| Grade | Look |
|---|---|
| `neon` | desaturated teal-and-amber split: teal shadows, sodium-amber highlights |
| `strobe` | hard red with crushed blacks (no magenta), a soft white flash on every beat (2.1 Hz, under the 3 Hz photosensitivity line), slight handheld jitter |
| `amber` | warm, hazy sodium orange (2049 Las Vegas): orange mids, a light haze screen pass, near-neutral blacks |
| `gold` | amber's warmer, slightly richer sibling with a little more haze |
| `silver` | cool steel-blue |
| `dawn` | pale grey-blue with a peach lift and lifted blacks |
| `fisheye` | mild barrel distortion (`lenscorrection` k1 0.12, k2 0.02, zoomed 1.15x; measured: no black corner pixels at 1.14x and above) plus gold highlights and teal shadows. The keyframes no longer paint the fisheye in. |
| `bw` | desaturate, S-curve, crushed blacks (unchanged) |
| `bw_to_color` | the Wizard-of-Oz cut (S02): the `bw` look until 1.2 s before the shot ends, then colour fades in by the cut, with a brief bloom that peaks as it arrives. The arriving colour is the source's, hue-rotated +80° (S02's magenta neon wash lands on sodium amber, median about 35°) at 0.6 saturation, so it reads as warm light rather than a tint. Tunable via `BW_TO_COLOR` in `render.py`. |

**fx:**

| fx | Effect |
|---|---|
| `flash_in` / `flash_out` | 2-frame white flash (100% then 55%) |
| `grain` | heavier grain on this shot |
| `vignette` | extra vignette on this shot |
| `bloom` | highlight bloom |
| `shake` | handheld jitter |
| `chroma` | RGB split |
| `strobe` | beat flash on any grade |
| `push_in` | 6% slow push-in on videos (stills always drift in) |
| `fade_in` / `fade_out` | 0.5 s fade from/to black |

**Overlay styles.** An overlay avoids the zones the lyrics occupy during its shot. It tries its zone hint, then the opposite zone, then any free zone.

Six overlays are off by default because their text is now painted into the keyframes: S07 (NEXT MODEL IN 18 DAYS), C1d, C2d and C3d (thoughts), V03 (BLUSH) and O04 (SLOW). `make_placeholder_edl.py` writes `"enabled": false` for them, and `--all-overlays` forces them on. Two stay on: C1a's BPM board and P04's version tag.

| Style | Look |
|---|---|
| `led` | an amber split-flap board with warm, Nixie-like glyphs on dark flaps. Tiles cascade in left to right, flipping through a few characters. `"A → B"` counts down if both are numbers (`BPM 200 → 64`), with each changed digit flipping; otherwise it flips at mid-shot. |
| `tag` | a thin steel-teal version pill; `v4 → v5` ticks over with a glitch |
| `thought` | handwritten words in warm pale gold, split on runs of 2+ spaces, fading in one by one and drifting |
| `hud` | steel-teal reticle, draw-on leader, typed label and a small readout |

## Caption design (captions.py)

- **Lead lines.** Warm sodium-amber / tungsten-gold neon in Tilt Neon, about 34 px cap height (78 px size), one ASS event per word per layer.
  - The layers are a light contrast bed, a soft spill, a halo, then the tube (warm cream core with an amber edge). Glow and bloom are gentle.
  - Words sit as faint unlit glass from the line's start and flicker on gently at their word times.
  - Lines wrap by phrase: after commas, before clauses, never inside a proper noun.
- **CAPS runs** (LOSS DROP, ARMS RACE; acronyms like AGI or DJ are excluded) are set as tracked Tilt Neon caps at 1.18x, on their own row, with a small pop and a soft glow lift.
- **Backing "Down, down, down".** Cool steel-teal / pale-cyan neon script (Neonderthaw), dimmer than the lead. Each backing line fills a 3-step staircase, each "down" one step lower and one step right, and each fades as it falls.
  - Back-to-back lines reuse the three slots. Every word fades before the next word that needs its slot arrives.
  - **Placement follows the shot on screen, not the previous line.** The staircase is laid out per zone segment and re-seeds wherever the backing crosses a cut into a shot with a different `caption_zone`. No word outlives its zone's shot run: it's cut off at the cut.
  - **Lower zone:** the staircase lives in the lower band, between the lead block's top edge and the letterbox bar (or the frame's safe bottom), beside the lead text: to its right if there's room, else to its left. The type shrinks until each step drops at least 15 px and no two words touch.
  - **Upper zone:** the mirror image. It starts at the top band, between the top bar and the lead block's bottom edge.
  - **Left and right zones:** a compact staircase just below the lead block, centred under it and inside its column. This keeps it off both the subject toward frame centre and any frame-edge foreground.
  - A backing word is never placed above the lead block's zone band, never overlaps visible lead text or an overlay, and never enters the bars. `captions.py` records every word's box in `Captions.staircases`, so these rules can be checked.
- **Rap.** Kept at least 8% inside the frame edges. Abril Fatface caps in warm gold-chrome: about 2 px clipped bands give a gradient of pale sky, brass, a dark horizon and a warm bounce. Each word has a bevel rim and a soft blurred drop shadow, and slams in at 138%, overshoots to 97%, then settles at 100% over 5 frames with a soft warm hit-flash.
- **Chant (intro, B&W).** Small Playfair Display italic, tracked +7, fading in word by word on a common drifting baseline, with a soft dark bed.
- **Placement.** Each line follows the caption zone of the shot covering it. A line that crosses a cut into a different zone is split at the cut. Letterboxed shots keep text inside the picture.
  - A lead line never hangs over a cut into a shot with a different zone: it clears at the cut, unless one of its words is still being sung. Its footnote clears too.
  - A shot's `caption_inset` pulls side-zone text in from the frame edge. C2c uses it because an out-of-focus foreground head fills its right edge.
  - A line shows from 0.15 s before its first word to 0.35 s after its last, clipped so it never overlaps the next line in the same zone.
- **Footnotes.** IBM Plex Mono Light, 25 px, pale warm off-white and low contrast, with a thin 1 px leader: a dot on the anchor word, a 45° rise and a short run, drawn on over 0.16 s.
  - They sit on the side of the block next to the anchor's row, dodge each other, sit in the matte in letterboxed shots, and never outlive their lyric by more than about 0.2 s.
  - Like the stairs, they stay in the caption block's column. Long notes wrap to the column's width. If a note doesn't fit beside the leader, it sits directly over the word on a short vertical tick.

## Fonts (all SIL OFL, in `fonts/`)

Family names are the ones libass matches (name ID 1).

| Role | Family (file) | Used for |
|---|---|---|
| neon | Tilt Neon (TiltNeon-Regular.ttf) | lead lyrics; end-card neon line |
| neon_sign | Monoton (Monoton-Regular.ttf) | unused since the Blade Runner retune (CAPS now use tracked Tilt Neon) |
| neon_script | Neonderthaw (Neonderthaw-Regular.ttf) | backing "down"s |
| serif_italic | Playfair Display, italic (PlayfairDisplay-Italic.ttf) | chant; quote attribution |
| chrome | Abril Fatface (AbrilFatface-Regular.ttf) | rap |
| mono / mono_light / mono_medium | IBM Plex Mono / IBM Plex Mono Light / IBM Plex Mono Medium | footnotes (Light), credits, split-flap and HUD (Medium), slates |
| card_title / card_title_bold / card_italic | Bodoni Moda Medium / Bodoni Moda ExtraBold / Bodoni Moda italic | title and end cards |
| typewriter | Courier Prime (CourierPrime-Regular.ttf) | quote-card typewriter |
| hand | Caveat Medium (Caveat-Medium.ttf) | "thought" overlays |
| serif_italic_semibold | Playfair Display SemiBold, italic | spare |

## Known limitations

- **Caption zones.** Zones come from the shot list, not from the pixels. When final clips land, check framing and edit `caption_zone` per shot. Overlays can be pinned with `pos`, but nothing is motion-tracked.
- **Word timing.** Timings are used as given, including `matched: false` words. The ad-libs ("ahoo") aren't captioned because the timeline has no timing for them.
- **Tuning.** Grades were tuned on keyframe stills and slates, not on moving footage. Slow motion uses frame blending, not optical flow.
- **Chant splitting.** Chant lines split at cuts like lead lines, so the intro chant line 1 appears in two places.
- **File size.** At CRF 16 with grain, the video runs about 22 Mbps, around 700 MB for the full video. The segment cache in `video/build/` grows as you iterate; delete it freely.
