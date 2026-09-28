"""Category 1 tests: multi-reference keyframes. Scene A = duo slow-dance (2 refs), Scene B = singer solo, new angle."""
import sys, concurrent.futures as cf
from scout import run
from prompts import DUO_SCENE, SOLO_SCENE

S, M = "@file:video/scout/refs/singer_ref_1920.png", "@file:video/scout/refs/muse_ref_1920.png"
duo = lambda a, b: DUO_SCENE.format(A=a, B=b)
solo = lambda a: SOLO_SCENE.format(A=a)

JOBS = {
    # ---- Scene A: duo slow-dance
    "img/A_nbpro": ("fal-ai/nano-banana-pro/edit", 0.15, {
        "prompt": duo("image 1", "image 2"), "image_urls": [S, M], "aspect_ratio": "16:9", "resolution": "2K",
        "output_format": "png"}),
    "img/A_nb2": ("fal-ai/nano-banana-2/edit", 0.12, {
        "prompt": duo("image 1", "image 2"), "image_urls": [S, M], "aspect_ratio": "16:9", "resolution": "2K",
        "output_format": "png"}),
    "img/A_seedream5pro": ("bytedance/seedream/v5/pro/edit", 0.072, {
        "prompt": duo("Figure 1", "Figure 2"), "image_urls": [S, M], "image_size": {"width": 2048, "height": 1152},
        "output_format": "png"}),
    "img/A_gptimg25flare_med": ("openai/gpt-image-2.5/flare/edit", 0.08, {
        "prompt": duo("image 1", "image 2"), "image_urls": [S, M], "image_size": {"width": 1536, "height": 864},
        "quality": "medium", "output_format": "png"}),
    "img/A_klingo3": ("fal-ai/kling-image/o3/image-to-image", 0.028, {
        "prompt": duo("@Image1", "@Image2"), "image_urls": [S, M], "aspect_ratio": "16:9", "resolution": "2K",
        "output_format": "png"}),
    "img/A_qwen3": ("alibaba/qwen-image-3/edit", 0.075, {
        "prompt": duo("image 1", "image 2"), "image_urls": [S, M], "image_size": {"width": 2048, "height": 1152},
        "output_format": "png"}),
    "img/A_muse": ("meta/muse-image/edit", 0.05, {
        "prompt": duo("image 1", "image 2"), "image_urls": [S, M], "aspect_ratio": "16:9", "output_format": "png"}),
    # ---- Scene B: singer solo, new angle
    "img/B_nbpro": ("fal-ai/nano-banana-pro/edit", 0.15, {
        "prompt": solo("image 1"), "image_urls": [S], "aspect_ratio": "16:9", "resolution": "2K", "output_format": "png"}),
    "img/B_seedream5pro": ("bytedance/seedream/v5/pro/edit", 0.0675, {
        "prompt": solo("Figure 1"), "image_urls": [S], "image_size": {"width": 2048, "height": 1152},
        "output_format": "png"}),
    "img/B_klingo3": ("fal-ai/kling-image/o3/image-to-image", 0.028, {
        "prompt": solo("@Image1"), "image_urls": [S], "aspect_ratio": "16:9", "resolution": "2K", "output_format": "png"}),
}

if __name__ == "__main__":
    names = sys.argv[1:] or list(JOBS)
    with cf.ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda n: run(n, JOBS[n][0], JOBS[n][2], JOBS[n][1]), names))
