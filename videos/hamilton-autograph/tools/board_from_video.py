"""Frames for a preview storyboard, taken out of the finished MP4 (so they show the grade and the captions as seen).
Run: python tools/board_from_video.py <video.mp4> <boards/shots_VER.json> <out_dir>
Each shot's keys are taken at the same moments build.mjs uses: the middle, or (i + 0.5) / n through the shot."""
import json, os, subprocess, sys
video, shots, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
for s in json.load(open(shots, encoding="utf-8")):
    n = len(s["keys"])
    for i, k in enumerate(s["keys"]):
        t = s["start"] + (s["end"] - s["start"]) * (0.5 if n == 1 else (i + 0.5) / n)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1",
                        "-vf", "scale=540:960:flags=lanczos", os.path.join(out, f"s{s['n']:02d}{k}.png")], check=True)
print("ok", len(os.listdir(out)))
