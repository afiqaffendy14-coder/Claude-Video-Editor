"""Assemble the movement-review test video: preview frames + take-2 voiceover + burnt-in captions (lower third,
up to 3 words, break at punctuation, same chunking as the storyboard pages). 60.0 s, 30 fps, 1080x1920.

Run: python tools/preview.py out/pframes out/halo-preview.mp4
Missing frames are filled with the previous frame (and listed), so the video always runs the full minute.
"""
import json, os, re, shutil, subprocess, sys

frames_dir, out = sys.argv[1], sys.argv[2]
FPS, N = 30, 1800
here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

missing, last = [], None
for f in range(N):
    p = os.path.join(frames_dir, f"f{f:05d}.png")
    if os.path.exists(p) and os.path.getsize(p) > 0:
        last = p
    else:
        missing.append(f)
        if last:
            shutil.copyfile(last, p)
if missing:
    print(f"filled {len(missing)} missing frames: {missing[:10]}{'...' if len(missing) > 10 else ''}")

words = [w for l in json.load(open(os.path.join(here, "tools", "timing.json")))["lines"] for w in l["words"]]
chunks, cur = [], []
for w in words:
    cur.append(w)
    if len(cur) == 3 or re.search(r'[,.?!:…"]$', w["w"]):
        chunks.append(cur)
        cur = []
if cur:
    chunks.append(cur)

font = "C\\:/Windows/Fonts/ariblk.ttf"
filters = ["scale=1080:1920:flags=lanczos"]
for i, c in enumerate(chunks):
    a = c[0]["start"]
    b = chunks[i + 1][0]["start"] if i + 1 < len(chunks) else 60.0
    text = " ".join(w["w"] for w in c).rstrip(",.:").replace("\\", "").replace("'", "’").replace(":", "\\:").replace('"', "")
    filters.append(f"drawtext=fontfile='{font}':text='{text}':fontsize=62:fontcolor=white:borderw=7:bordercolor=black:"
                   f"x=(w-text_w)/2:y=h*0.74-text_h/2:enable='between(t,{a:.3f},{b:.3f})'")
script = os.path.join(os.path.dirname(out), "preview_filter.txt")
filters.append("format=yuv420p")  # phones only decode 4:2:0 H.264 (the PNGs would otherwise give 4:4:4)
open(script, "w", encoding="utf-8").write(",\n".join(filters))
vo = os.path.join(here, "assets", "audio", "narrator", "vo_60.wav")
cmd = ["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(frames_dir, "f%05d.png"), "-i", vo,
       "-/filter:v", script,  # ffmpeg 7+: read the filter graph from a file
       "-frames:v", str(N), "-c:v", "libx264", "-profile:v", "high", "-level:v", "4.0", "-pix_fmt", "yuv420p",
       "-crf", "21", "-preset", "medium", "-r", str(FPS),
       "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
       "-movflags", "+faststart", "-shortest", out]  # plays on phones: 4:2:0, High@4.0, index at the front
subprocess.run(cmd, check=True)
print("wrote", out)
