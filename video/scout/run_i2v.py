"""Category 2 tests: image-to-video. S_* = singer slow-motion move (first frame refs/singer_ref_1920.png);
D_* = tasteful sensual slow-dance (first frame img/A_nbpro.png), mainly a moderation check."""
import sys, concurrent.futures as cf
from scout import run

SING = "@file:video/scout/refs/singer_ref_1920.png"
DUO = "@file:video/scout/img/A_nbpro.png"
SFACE, MFACE = "@file:video/scout/refs/singer_face.png", "@file:video/scout/refs/muse_face.png"
SFULL, MFULL = "@file:video/scout/refs/singer_ref_1920.png", "@file:video/scout/refs/muse_ref_1920.png"

SINGER_MOTION = (
    "Slow motion, as if shot at 120 fps: the man in glasses slowly lifts the microphone off its stand and turns toward "
    "the camera with a confident half-smile, his curls and cardigan swaying gently. Haze drifts in slow motion, neon "
    "lights shimmer and bokeh particles float. The camera performs a slow, smooth dolly-in toward his face. Keep the "
    "exact stylized painterly 3D animation look, character design and lighting of the first frame. Single continuous "
    "shot, no cuts.")
DUO_MOTION = (
    "Slow motion: the couple slow-dances close, swaying gently in a slow circle; her fingers glide along the back of his "
    "neck, he pulls her a little closer and they rest their foreheads together, eyes closed, tender and sensual, fully "
    "clothed. Other dancers drift in slow motion in the background, amber spotlight and neon haze. The camera slowly "
    "orbits around the couple. Keep the exact stylized painterly 3D animation look and character designs of the first "
    "frame. Single continuous shot, no cuts.")
DUO_MOTION_EL = DUO_MOTION.replace("the couple slow-dances", "@Element1 (the man in glasses) and @Element2 (the woman "
                                                             "with the black bob) slow-dance")

JOBS = {
    # ---- singer slow-motion move
    "i2v/S_kling_v3pro": ("fal-ai/kling-video/v3/pro/image-to-video", 0.56, {
        "start_image_url": SING, "prompt": SINGER_MOTION, "duration": "5", "generate_audio": False}),
    "i2v/S_veo31fast_1080": ("fal-ai/veo3.1/fast/image-to-video", 0.60, {
        "image_url": SING, "prompt": SINGER_MOTION, "duration": "6s", "resolution": "1080p", "aspect_ratio": "16:9",
        "generate_audio": False}),
    "i2v/S_h3max_1080": ("minimax/h3-max/image-to-video", 0.40, {
        "image_url": SING, "prompt": SINGER_MOTION, "duration": 5, "resolution": "1080P",
        "prompt_expansion_mode": "balanced"}),
    "i2v/S_seedance25_draft480": ("bytedance/seedance-2.5/image-to-video", 1.03, {
        "image_url": SING, "prompt": SINGER_MOTION, "duration": "5", "draft": True, "generate_audio": False}),
    "i2v/S_wan30_720": ("alibaba/wan-3.0/image-to-video", 0.50, {
        "start_image_url": SING, "prompt": SINGER_MOTION, "duration": 5, "resolution": "720p", "aspect_ratio": "16:9",
        "audio": False}),
    "i2v/S_omniflash11_720": ("google/gemini-omni-flash/v1.1/image-to-video", 0.50, {
        "image_url": SING, "prompt": SINGER_MOTION, "duration": 5, "resolution": "720p", "aspect_ratio": "16:9"}),
    "i2v/S_sora2_720": ("fal-ai/sora-2/image-to-video", 0.40, {
        "image_url": SING, "prompt": SINGER_MOTION, "duration": 4, "resolution": "720p", "aspect_ratio": "16:9"}),
    # ---- sensual slow-dance (moderation check)
    "i2v/D_kling_v3pro_elements": ("fal-ai/kling-video/v3/pro/image-to-video", 0.56, {
        "start_image_url": DUO, "prompt": DUO_MOTION_EL, "duration": "5", "generate_audio": False,
        "elements": [{"frontal_image_url": SFULL, "reference_image_urls": [SFACE]},
                     {"frontal_image_url": MFULL, "reference_image_urls": [MFACE]}]}),
    "i2v/D_veo31fast_1080": ("fal-ai/veo3.1/fast/image-to-video", 0.40, {
        "image_url": DUO, "prompt": DUO_MOTION, "duration": "4s", "resolution": "1080p", "aspect_ratio": "16:9",
        "generate_audio": False}),
    "i2v/D_h3max_768": ("minimax/h3-max/image-to-video", 0.20, {
        "image_url": DUO, "prompt": DUO_MOTION, "duration": 5, "resolution": "768P", "prompt_expansion_mode": "balanced"}),
    "i2v/D_sora2_720": ("fal-ai/sora-2/image-to-video", 0.40, {
        "image_url": DUO, "prompt": DUO_MOTION, "duration": 4, "resolution": "720p", "aspect_ratio": "16:9"}),
    "i2v/D_wan30_480": ("alibaba/wan-3.0/image-to-video", 0.25, {
        "start_image_url": DUO, "prompt": DUO_MOTION, "duration": 5, "resolution": "480p", "aspect_ratio": "16:9",
        "audio": False}),
}

if __name__ == "__main__":
    names = sys.argv[1:] or list(JOBS)
    with cf.ThreadPoolExecutor(12) as ex:
        list(ex.map(lambda n: run(n, JOBS[n][0], JOBS[n][2], JOBS[n][1]), names))
