#!/usr/bin/env bash
# ElevenLabs speech-to-speech on a vocal slice, then lay it back over the instrumental.
# usage: scripts/el_sts.sh <vocal.wav> <start_s> <dur_s> <voice_id> <label>
set -euo pipefail
set -a; . ~/.env; set +a
VOC="$1"; SS="$2"; DUR="$3"; VID="$4"; LABEL="$5"
INST=audio/stems/instrumental_bsroformer.wav
OUT=audio/tests; mkdir -p "$OUT"
ffmpeg -hide_banner -loglevel error -y -ss "$SS" -t "$DUR" -i "$VOC" -ac 1 -ar 44100 "$OUT/_src_$LABEL.wav"
curl -sS -f -X POST "https://api.elevenlabs.io/v1/speech-to-speech/$VID?output_format=mp3_44100_192" \
  -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -F "audio=@$OUT/_src_$LABEL.wav" \
  -F "model_id=eleven_multilingual_sts_v2" \
  -F 'voice_settings={"stability":0.35,"similarity_boost":0.85,"style":0.3,"use_speaker_boost":true}' \
  -o "$OUT/sts_$LABEL.mp3"
ffmpeg -hide_banner -loglevel error -y -ss "$SS" -t "$DUR" -i "$INST" -i "$OUT/sts_$LABEL.mp3" \
  -filter_complex "[1:a]volume=1.6,aresample=44100[v];[0:a][v]amix=inputs=2:normalize=0,alimiter=limit=0.95[m]" -map "[m]" \
  -c:a libmp3lame -q:a 2 "$OUT/sts_${LABEL}_over_instrumental.mp3"
rm -f "$OUT/_src_$LABEL.wav"
echo "ok: $OUT/sts_$LABEL.mp3"
