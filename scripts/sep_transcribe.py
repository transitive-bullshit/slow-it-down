"""Separate vocals from a generated take, then Whisper-transcribe with word timings (absolute song time)."""
import json, os, subprocess, sys, glob
import mlx_whisper
src, tag, t0 = sys.argv[1], sys.argv[2], float(sys.argv[3])
work = f"prototypes/work/{tag}"; os.makedirs(work, exist_ok=True)
wav = f"{work}/mix.wav"
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-ar", "44100", "-ac", "2", wav], check=True)
if not glob.glob(f"{work}/*(Vocals)*.wav"):
    subprocess.run(["audio-separator", wav, "-m", "model_bs_roformer_ep_317_sdr_12.9755.ckpt", "--model_file_dir",
                    os.path.expanduser("~/.cache/audio-separator"), "--output_dir", work, "--output_format", "WAV"],
                   check=True, capture_output=True)
voc = glob.glob(f"{work}/*(Vocals)*.wav")[0]
os.replace(voc, f"{work}/vocals.wav")
for f in glob.glob(f"{work}/*(Instrumental)*.wav"): os.replace(f, f"{work}/instrumental.wav")
res = mlx_whisper.transcribe(f"{work}/vocals.wav", path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language="en",
                             word_timestamps=True, condition_on_previous_text=False)
json.dump({"t0": t0, "segments": res["segments"]}, open(f"{work}/whisper.json", "w"))
print(f"== {tag}")
for seg in res["segments"]:
    print(f"{seg['start']+t0:7.2f}-{seg['end']+t0:7.2f}  {seg['text'].strip()}")
