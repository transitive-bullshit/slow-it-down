"""Category 3 tests: singing lip-sync from a still (refs/singer_ref_1920.png) + 6 s of sung vocals
(audio/stems/vocals_reference_bsroformer.wav 61.0-67.0 s -> refs/vocal_61-67.wav)."""
import sys, concurrent.futures as cf
from scout import run

IMG = "@file:video/scout/refs/singer_ref_1920.png"
AUD = "@file:video/scout/refs/vocal_61-67.wav"
SING_PROMPT = (
    "The man in glasses sings a soulful, sensual R&B slow jam into the microphone: expressive mouth movements matching "
    "the vocals, gentle head sway, eyebrows lifting on the high notes, eyes half-closed, subtle breathing and shoulder "
    "movement, one hand on his chest. Neon lights flicker softly in the hazy club. Keep the stylized painterly 3D "
    "animation look of the image.")

JOBS = {
    "lipsync/L_omnihuman15_720": ("fal-ai/bytedance/omnihuman/v1.5", 0.96, {
        "image_url": IMG, "audio_url": AUD, "resolution": "720p", "prompt": SING_PROMPT}),
    "lipsync/L_aurora_720": ("fal-ai/creatify/aurora", 0.84, {
        "image_url": IMG, "audio_url": AUD, "resolution": "720p", "prompt": SING_PROMPT}),
    "lipsync/L_sync3_i2v": ("fal-ai/sync-lipsync/v3/image-to-video", 0.80, {
        "image_url": IMG, "audio_url": AUD}),
    "lipsync/L_kling_avatar2pro": ("fal-ai/kling-video/ai-avatar/v2/pro", 0.69, {
        "image_url": IMG, "audio_url": AUD, "prompt": SING_PROMPT}),
    "lipsync/L_h3max_lipsync_768": ("minimax/h3-max/lip-sync/image-to-video", 0.48, {
        "image_url": IMG, "audio_url": AUD, "resolution": "768P"}),
    "lipsync/L_ltx25_a2v_fast": ("lightricks/ltx-2.5/audio-to-video/fast", 0.78, {
        "image_url": IMG, "audio_url": AUD, "prompt": SING_PROMPT, "aspect_ratio": "16:9"}),
}

if __name__ == "__main__":
    names = sys.argv[1:] or list(JOBS)
    with cf.ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda n: run(n, JOBS[n][0], JOBS[n][2], JOBS[n][1]), names))
