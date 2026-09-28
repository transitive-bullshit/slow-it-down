#!/usr/bin/env bash
# Seed-VC zero-shot singing voice conversion: keeps the source melody, swaps in the reference voice's timbre.
# Model: seed-uvit-whisper-base (f0-conditioned, 44.1 kHz, BigVGAN); f0 conditioning on, auto-f0-adjust off.
# usage: scripts/seedvc_convert.sh <src.wav> <ref.wav> <out.wav> [semitone_shift=0] [diffusion_steps=40]
#   src   dry sung vocal (a clean lead stem works best); long files are chunked internally
#   ref   5-25 s of the target voice, clean and dry; only the first 25 s are used
#   out   44.1 kHz mono 24-bit WAV, same length as src, so it drops back in at the same offset
# env overrides: SEEDVC_DEVICE=auto|mps|cpu  SEEDVC_CFG=0.7  SEEDVC_SEED=1234 (new take)  SEEDVC_FP16=true
set -euo pipefail
if [ $# -lt 3 ]; then sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit 1; fi
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/.venv-seedvc/bin/activate"
exec python "$ROOT/scripts/seedvc_infer.py" "$1" "$2" "$3" \
  --semitones "${4:-0}" --steps "${5:-40}" \
  --cfg "${SEEDVC_CFG:-0.7}" --device "${SEEDVC_DEVICE:-auto}" \
  --seed "${SEEDVC_SEED:-1234}" --fp16 "${SEEDVC_FP16:-true}"
