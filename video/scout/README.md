# fal.ai model scouting for Club Frontier (2026-09-28)

**Status: stopped early.** The fal account balance ran out at 11:21, about $3.25 into the tests. Since then every call has failed with `User is locked. Reason: Exhausted balance`, and uploads fail with a 403. So the balance was well under the $15 budget. The keyframe tests are complete. Three image-to-video tests finished. The lip-sync, upscaling, and slow-dance video tests never ran; their scripts are ready to re-run after a top-up. No request was blocked by moderation.

Everything below comes from the live catalog (`fal.ai/api/models`, 1,502 models), the OpenAPI schemas, the pricing API (`api.fal.ai/v1/models/pricing`), and the real test outputs. Measured latency is total wall time, and the queue was about 1–2 s every time.

## Recommended stack

| Category | Primary | Fallback | Tested? |
|---|---|---|---|
| Keyframes (multi-reference) | `fal-ai/nano-banana-pro/edit` | `fal-ai/kling-image/o3/image-to-image` | Yes, both |
| Image-to-video | `fal-ai/veo3.1/fast/image-to-video` (plus `fal-ai/veo3.1/fast/first-last-frame-to-video`) | `alibaba/wan-3.0/image-to-video`; hero shots: `bytedance/seedance-2.5/image-to-video` | Yes (Kling v3 Pro, the likely co-primary, was blocked by the balance) |
| Singing lip-sync | `fal-ai/bytedance/omnihuman/v1.5` | `fal-ai/creatify/aurora`, or i2v followed by `fal-ai/sync-lipsync/v3` | **No** (balance) |
| Upscale / interpolation | `topaz/upscale/video/precision`, `topaz/interpolate/video` | `fal-ai/seedvr/upscale/video`, `fal-ai/film/video` | **No** (balance) |

### 1. Keyframes (tested: 7 models, 10 images, all in `img/`)

Setup: `refs/singer_nbpro.png` and `refs/muse_nbpro.png` were made with `fal-ai/nano-banana-pro` (text-to-image, 16:9, 2K, $0.15 each). They were downscaled to 1920 px wide (`refs/*_ref_1920.png`) and passed as references. Scene A is the tasteful slow-dance with both characters. Scene B is the singer alone from a new angle. Prompts are in `prompts.py`, and face crops are compared in `frames/sheet_faces.jpg`.

| Endpoint | Working params | Price | Latency | Output | Notes |
|---|---|---|---|---|---|
| **`fal-ai/nano-banana-pro/edit`** | `{"prompt", "image_urls":[singer, muse], "aspect_ratio":"16:9", "resolution":"2K", "output_format":"png"}`; refer to the references as "image 1 / image 2" | $0.15 per image (1K/2K); $0.30 at 4K | 25–26 s | 2752x1536 | Best overall: faces, glasses, curls, cardigan, her bob and forearm/neck mesh all carried over. Strong prompt adherence and a clean painterly-3D look. It ignored "low-angle" in Scene B. |
| **`fal-ai/kling-image/o3/image-to-image`** | `{"prompt":"...@Image1...@Image2...", "image_urls":[...], "aspect_ratio":"16:9", "resolution":"2K", "output_format":"png"}`; also accepts `elements` (a frontal image plus up to 3 angle references per character, cited as `@Element1`) | $0.028 per image (1K/2K); double at 4K | 63–65 s | 2720x1536 | Identity as good as Nano Banana Pro and the closest to the reference's lighting and set. By far the best value. |
| `fal-ai/nano-banana-2/edit` | Same as Nano Banana Pro (also has `thinking_level`, and 0.5K–4K) | $0.08 at 1K; $0.12 at 2K | 21.5 s | 2752x1536 | Nearly identical to Nano Banana Pro here, with a little less detail. |
| `bytedance/seedream/v5/pro/edit` | `{"prompt":"...Figure 1...Figure 2...", "image_urls":[...], "image_size":{"width":2048,"height":1152}, "output_format":"png"}` | $0.0675, plus $0.0045 per extra reference (output ≤1536²); $0.135 above that | 98–122 s | 2048x1152 | Most dynamic crowd and lighting (best Scene B). Slight identity drift: thinner glasses, narrower face. |
| `openai/gpt-image-2.5/flare/edit` | `{"prompt", "image_urls":[...], "image_size":{"width":1536,"height":864}, "quality":"medium"}` | Token-based (est. ~$0.05–0.10 at medium) | 20.5 s | 1536x864 | Good composition, but the man came out older with a heavier beard. |
| `alibaba/qwen-image-3/edit` | `{"prompt", "image_urls":[...≤3, each ≤2048 px], "image_size":{"width":2048,"height":1152}}` | $0.04 at 1K; $0.075 at 2K | 101 s | 2048x1152 | Decent identity. Maximum of 3 references. |
| `meta/muse-image/edit` | `{"prompt", "image_urls":[...≤10], "aspect_ratio":"16:9"}` | Not published (pricing API reports $0.01 per image) | 23.6 s | 2048x1152 | Decent. The man looks younger and more cartoonish. |

Not found or deprecated: FLUX Kontext is superseded by `fal-ai/flux-2-max/edit` and `-pro/edit` (untested). No Nano Banana 3, Gemini 3.5 image, or Imagen 5 endpoint exists. `fal-ai/ideogram/character` still exists (untested).

### 2. Image-to-video (tested on the singer frame; grabs in `frames/sheet_i2v_singer.jpg`)

Prompt: a slow-motion mic lift, a turn to camera, and a slow dolly-in (see `SINGER_MOTION` in `run_i2v.py`). First frame: `refs/singer_ref_1920.png`.

| Endpoint | Working params | Price | Latency | Output | Notes |
|---|---|---|---|---|---|
| **`fal-ai/veo3.1/fast/image-to-video`** | `{"image_url", "prompt", "duration":"6s", "resolution":"1080p", "aspect_ratio":"16:9", "generate_audio":false}` | $0.10/s (720p/1080p, no audio); $0.15/s with audio; $0.30/s at 4K | 102 s | 1920x1080, 24 fps, 6 s | Did every beat of the prompt: lift, turn, and push-in to a close-up. Style held. The face got slightly smoother and more generic by the end. Lengths are only 4, 6, or 8 s. Start plus end frames via `fal-ai/veo3.1/fast/first-last-frame-to-video`; up to 3 references via `.../reference-to-video` (8 s only). `safety_tolerance` goes from 1 to 6 (default 4). |
| `bytedance/seedance-2.5/image-to-video` | `{"image_url", "prompt", "duration":"5", "draft":true, "generate_audio":false}` | Draft 480p $0.2205/s; 720p $0.473/s; 1080p $1.164/s | 96 s | 856x478 draft, 24 fps | Most faithful of the three: the face matches the reference closely and the motion is natural. Returned a `draft_id` (see `ledger.jsonl`), which can be finished at 1080p within 7 days via `bytedance/seedance-2.5/draft/complete` (untested). Also supports `end_image_url`, 4–30 s clips, and `reference-to-video` with up to 30 image refs plus video and audio refs. Price is the drawback. |
| `alibaba/wan-3.0/image-to-video` | `{"start_image_url", "prompt", "duration":5, "resolution":"720p", "aspect_ratio":"16:9", "audio":false}` | $0.05/s at 480p, $0.10/s at 720p, $0.20/s at 1080p | 130 s | 1280x720, 30 fps | Good identity and motion; the mic comes off its clip correctly. Supports `end_image_url`. A reference-to-video variant exists. |
| `fal-ai/kling-video/v3/pro/image-to-video` | `{"start_image_url", "prompt", "duration":"5", "generate_audio":false}`, plus `end_image_url` and `elements` for character refs, and `multi_prompt` for multi-shot | $0.112/s (audio off) | — | 3–15 s | **Untested (balance).** Has the best feature set for a 40–60 shot video: start and end frames, character elements, and multi-shot. Test it first after a top-up; it could replace Veo as primary. |
| `minimax/h3-max/image-to-video` (Hailuo) | `{"image_url", "prompt", "duration":5, "resolution":"1080P"}` | $0.08/s at 1080P until Sep 30, then $0.16/s | — | 5–15 s | **Untested (balance).** Supports `end_image_url`. |
| `google/gemini-omni-flash/v1.1/image-to-video` | `{"image_url", "prompt", "duration":5, "resolution":"720p"}` | $0.10/s at 720p; $0.15/s at 1080p | — | 3–10 s | **Untested (balance).** |
| `fal-ai/sora-2/image-to-video` | — | $0.10/s | — | — | **Failed:** `Downstream service unavailable`. It is also hidden from the catalog. Drop it. |

Other current endpoints, all untested: `lightricks/ltx-2.5/image-to-video/fast` (1080p at $0.13/s; `fps` 48 or 50 gives 2x slow motion when conformed to 24 fps, which no other endpoint offers natively), `blackforestlabs/flux-3/image-to-video` / `first-last-frame-to-video` / `keyframes-to-video` (1080p at $0.29/s; draft at $0.06/s), `alibaba/happy-horse/v1.1/image-to-video` (1080p at $0.18/s), `xai/grok-imagine-video/v1.5/image-to-video`, `luma/agent/ray/v3.2/image-to-video`, and `fal-ai/vidu/q3/image-to-video`. No endpoint has a "slow motion" switch. Write slow motion into the prompt, or retime afterwards with `topaz/interpolate/video` (`slowdown_factor`).

### 3. Singing lip-sync (all untested: the balance ran out before the run)

Test input: `refs/singer_ref_1920.png` plus `refs/vocal_61-67.wav` (6.0 s, cut from `audio/stems/vocals_reference_bsroformer.wav` at 61–67 s). Command: `python video/scout/run_lipsync.py`, about $4.55 for all six.

| Endpoint | Params | Price | Limits |
|---|---|---|---|
| **`fal-ai/bytedance/omnihuman/v1.5`** | `{"image_url", "audio_url", "resolution":"720p", "prompt"}` | $0.16/s | Audio up to 30 s at 1080p or 60 s at 720p. Optional `mask_url` picks which person sings. Animates the full body and emotion, not just the mouth. |
| `fal-ai/creatify/aurora` | `{"image_url", "audio_url", "resolution":"720p", "prompt"}` | $0.14/s at 720p; $0.07/s at 480p (rounded up to whole seconds) | Advertised for "speaking or singing". |
| `fal-ai/sync-lipsync/v3/image-to-video` | `{"image_url", "audio_url"}` | $0.1333/s | Advertised for "any illustration or animated frame". |
| `fal-ai/sync-lipsync/v3` (video in) | `{"video_url", "audio_url", "sync_mode":"cut_off"}` | $8/min | Lip-syncs an existing i2v performance clip, keeping the camera move. |
| `minimax/h3-max/lip-sync/image-to-video` | `{"image_url", "audio_url", "resolution":"768P"}` | $0.08/s at 768P; $0.16/s at 1080P; $0.32/s at 2K | Audio 5–14.8 s. New on Sep 17. |
| `fal-ai/kling-video/ai-avatar/v2/pro` | `{"image_url", "audio_url", "prompt"}` | $0.115/s | Supports stylized characters. |
| `lightricks/ltx-2.5/audio-to-video/fast` | `{"image_url", "audio_url", "prompt", "aspect_ratio":"16:9"}` | $0.13/s at 1080p | Audio 2–20 s (the pro version caps at 10 s). |

Not available on fal: Hedra Character-3 and OmniHuman v2 (no schema). Also present but older: `fal-ai/infinitalk` ($0.20/s), `fal-ai/wan/v2.2-14b/speech-to-video` ($0.20/s at 720p), and `fal-ai/heygen/avatar4/image-to-video` ($0.10/s).

### 4. Upscaling and interpolation (untested)

- `topaz/upscale/video/precision`: `{"video_url", "model":"Proteus", "upscale_factor":2}`, $0.10 per 10 s of output at 720p or $0.20 at 1080p. The "Gaia 2" animation model costs $0.10 per 10 s at up to 1080p.
- `topaz/interpolate/video`: `{"video_url", "model":"Apollo" or "Chronos", "slowdown_factor":2, "target_fps":24}`. Converting 10 s from 30 to 60 fps costs about $0.30 at 1080p; slow motion bills on the full output duration.
- Cheap alternatives: `fal-ai/seedvr/upscale/video` ($0.001 per megapixel of video, about $0.25 for 5 s at 1080p), `fal-ai/flashvsr/upscale/video` ($0.0005 per MP), `fal-ai/bytedance-upscaler/upscale/video` ($0.0072/s at 1080p), and `fal-ai/film/video` or `fal-ai/rife/video` ($0.0013 per compute second).

## Moderation
- The slow-dance keyframe passed on all 7 image models: Nano Banana Pro (safety_tolerance at its default of 4), Nano Banana 2, Seedream 5 Pro, GPT-image-2.5, Kling O3, Qwen-image-3, and Muse. Nothing was blocked.
- The slow-dance video test never ran. The upload of `img/A_nbpro.png` failed with a 403 once the account was locked. Jobs `D_*` in `run_i2v.py` are ready.

## What failed
- The balance lock hit `S_kling_v3pro`, `S_h3max_1080`, `S_omniflash11_720`, all 5 `D_*` jobs, and all 6 lip-sync jobs. Failed calls were rejected before running, so they cost nothing.
- Sora 2 returned `downstream_service_unavailable`.

## Cost to finish the video (unit prices above; no rerolls)
- **70 keyframes:** Nano Banana Pro at 2K = $10.50 (Kling O3 = $1.96).
- **64 i2v clips of 5 s:**
  - Veo 3.1 Fast at 1080p, no audio, generated at 6 s = $38.40.
  - Kling v3 Pro at 5 s = $35.84.
  - Wan 3.0 at 1080p = $64.
  - H3-max at 1080P after Sep 30 = $51.20.
  - Seedance 2.5 at 720p = $151; at 1080p = $372.
- **6 lip-sync shots of 5 s:** OmniHuman v1.5 = $4.80 (Aurora $4.20, sync-3 $4.00).
- **Optional Topaz upscale** of 64 clips = about $6.40.
- **Remaining scout tests:** about $8 (Kling, H3-max, Omni Flash, 5 slow-dance videos, 6 lip-sync, upscale).
- **Total:** about $60 with no rerolls, or **about $100–125 with 1.5–2x rerolls**.

## Files
- `scout.py`: the harness. Usage: `python video/scout/scout.py <name> <endpoint> <est_cost> '<json>'`, where `@file:` paths are auto-uploaded. It logs every call to `ledger.jsonl` with args, latency, request_id and result metadata.
- `run_keyframes.py`, `run_i2v.py`, `run_lipsync.py`: the test batches. Pass job names to re-run a subset, for example `python video/scout/run_i2v.py i2v/S_kling_v3pro i2v/S_h3max_1080 i2v/D_kling_v3pro_elements i2v/D_veo31fast_1080 i2v/D_h3max_768 i2v/D_wan30_480`.
- `prompts.py`: character and style blocks. The characters are original and no real people are named.
- `refs/`, `img/`, `i2v/`, `frames/` (contact sheets and grabs), `uploads.json` (cache of fal storage URLs).
- Known harness gap: an upload error raises inside the thread pool and aborts the rest of the batch.
