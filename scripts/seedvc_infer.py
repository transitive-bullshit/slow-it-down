"""Seed-VC singing voice conversion: the f0-conditioned 44.1 kHz model (seed-uvit-whisper-base).

Thin driver around tools/seed-vc/inference.py. It runs upstream main() unchanged (f0 conditioning on), and adds:
  * RMVPE returns float64 f0, which MPS cannot hold, so f0 is cast to float32 (upstream crashes on MPS otherwise).
  * --device overrides upstream's auto pick (cuda > mps > cpu); --seed makes takes reproducible.
  * Exactly one output file at the path you give: 44.1 kHz mono 24-bit WAV, padded/trimmed to the
    source length so it drops back into the mix at the same offset.
  * Offline Hugging Face mode once the weights are cached in tools/seed-vc/checkpoints.

Run it with .venv-seedvc (scripts/seedvc_convert.sh does this for you):
  python scripts/seedvc_infer.py SRC REF OUT [--semitones 0] [--steps 40] [--cfg 0.7] [--device auto|mps|cpu] [--seed N]
"""
import argparse
import glob
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEEDVC = ROOT / "tools" / "seed-vc"
SR = 44100


def str2bool(v):
    return str(v).lower() in ("1", "true", "yes", "y", "on")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="sung vocal to convert (dry, ideally a clean stem)")
    ap.add_argument("reference", help="target voice, 5-25 s (only the first 25 s are used)")
    ap.add_argument("output", help="output .wav (44.1 kHz mono, 24-bit)")
    ap.add_argument("--semitones", type=int, default=0, help="transpose the melody (0 keeps the key)")
    ap.add_argument("--steps", type=int, default=40, help="diffusion steps (30-50 for singing)")
    ap.add_argument("--cfg", type=float, default=0.7, help="inference cfg rate")
    ap.add_argument("--device", choices=["auto", "mps", "cpu"], default="auto")
    ap.add_argument("--fp16", type=str2bool, default=True, help="fp16 autocast for the DiT (default true)")
    ap.add_argument("--auto-f0-adjust", type=str2bool, default=False,
                    help="shift source pitch to the reference's median pitch (off for singing)")
    ap.add_argument("--seed", type=int, default=1234, help="diffusion noise seed (change it for another take)")
    ap.add_argument("--no-length-match", action="store_true", help="keep the model's raw output length")
    a = ap.parse_args()

    src, ref, out = (os.path.abspath(p) for p in (a.source, a.reference, a.output))
    for p in (src, ref):
        if not os.path.isfile(p):
            sys.exit(f"seedvc: no such file: {p}")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

    # upstream uses cwd-relative paths (./checkpoints, configs/, modules/)
    os.chdir(SEEDVC)
    sys.path.insert(0, str(SEEDVC))
    os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
    if (SEEDVC / "checkpoints" / "models--Plachta--Seed-VC").is_dir():
        os.environ.setdefault("HF_HUB_OFFLINE", "1")  # weights already cached: skip the Hub round-trips

    import numpy as np
    import soundfile as sf
    import torch
    import inference as sv  # sets HF_HUB_CACHE=./checkpoints/hf_cache and picks a device

    if a.device != "auto":
        sv.device = torch.device(a.device)

    load_s = {}
    upstream_load = sv.load_models

    def load_models(args):
        t = time.time()
        model, semantic_fn, f0_fn, vocoder_fn, campplus, to_mel, mel_args = upstream_load(args)
        load_s["t"] = time.time() - t

        def f0_fn32(audio, thred=0.03):
            return f0_fn(audio, thred=thred).astype(np.float32)

        return model, semantic_fn, f0_fn32, vocoder_fn, campplus, to_mel, mel_args

    sv.load_models = load_models
    torch.manual_seed(a.seed)
    if torch.backends.mps.is_available():
        torch.mps.manual_seed(a.seed)

    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        sv.main(argparse.Namespace(
            source=src, target=ref, output=tmp,
            diffusion_steps=a.steps, length_adjust=1.0, inference_cfg_rate=a.cfg,
            f0_condition=True, auto_f0_adjust=a.auto_f0_adjust, semi_tone_shift=a.semitones,
            checkpoint=None, config=None, fp16=a.fp16,
        ))
        wavs = glob.glob(os.path.join(tmp, "*.wav"))
        if len(wavs) != 1:
            sys.exit(f"seedvc: expected one output wav, found {wavs}")
        y, sr = sf.read(wavs[0], dtype="float32")
    total = time.time() - t0
    if y.ndim > 1:
        y = y.mean(axis=1)
    assert sr == SR, sr

    raw_len = len(y)
    if not a.no_length_match:
        try:
            info = sf.info(src)
            n = int(round(info.frames * SR / info.samplerate))
        except Exception:  # formats libsndfile can't open (m4a etc.)
            import librosa
            n = int(round(librosa.get_duration(path=src) * SR))
        y = np.pad(y, (0, max(0, n - len(y))))[:n]
    sf.write(out, np.clip(y, -1.0, 1.0), SR, subtype="PCM_24")

    dur = len(y) / SR
    conv = total - load_s.get("t", 0.0)
    print(f"seedvc: wrote {out} ({dur:.2f} s @ {SR} Hz, model output {raw_len} samples)")
    print(f"seedvc: device={sv.device} steps={a.steps} cfg={a.cfg} semitones={a.semitones} fp16={a.fp16} seed={a.seed} | "
          f"load {load_s.get('t', 0):.1f}s, convert {conv:.1f}s ({conv / max(dur, 1e-6) * 10:.1f}s per 10s of audio)")
    if sv.device.type == "mps":
        print(f"seedvc: MPS driver memory now {torch.mps.driver_allocated_memory() / 2**30:.2f} GiB")


if __name__ == "__main__":
    main()
