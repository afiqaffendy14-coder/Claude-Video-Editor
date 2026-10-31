"""Assemble a clip: rendered frames -> colour grade -> scale -> caption overlays -> voiceover + sound effects.

Run: python3 tools/compose.py <frames_dir> <fps> <captions_dir> <sfx.wav> <t_from> <t_to> <out.mp4> [width height]
The grade is the one in boards/grade.sh, so stills and video match.
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
frames, fps, caps, sfx, t0, t1, out = sys.argv[1:8]
fps, t0, t1 = int(fps), float(t0), float(t1)
W, H = (int(sys.argv[8]), int(sys.argv[9])) if len(sys.argv) > 9 else (720, 1280)
grade = re.search(r'GRADE="(.+)"', open(os.path.join(HERE, "..", "boards", "grade.sh")).read()).group(1)
vo = os.path.join(HERE, "..", "assets", "audio", "narrator", "v6_take1_60.wav")
first = int(round(t0 * fps))
meta = json.load(open(os.path.join(caps, "captions.json")))

args = ["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-start_number", str(first), "-i", os.path.join(frames, "f%05d.png")]
for c in meta:
    args += ["-i", c["file"]]
args += ["-ss", str(t0), "-t", str(t1 - t0), "-i", vo, "-i", sfx]
n = len(meta)
chain = [f"[0:v]{grade},scale={W}:{H}:flags=lanczos,format=yuv420p[v0]"]
last = "v0"
for i, c in enumerate(meta):
    a = max(c["start"], t0) - t0 if i else 0.0
    b = min(c["end"], t1) - t0
    chain.append(f"[{last}][{i + 1}:v]overlay=0:0:enable='between(t,{a:.3f},{b:.3f})'[v{i + 1}]")
    last = f"v{i + 1}"
vi, si = n + 1, n + 2
fade = max(0.0, (t1 - t0) - 0.15)
chain.append(f"[{vi}:a]volume=1.0,afade=t=out:st={fade:.3f}:d=0.15[vo]")
chain.append(f"[{si}:a]volume=0.32[fx]")
chain.append("[vo][fx]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.89[aout]")
args += ["-filter_complex", ";".join(chain), "-map", f"[{last}]", "-map", "[aout]", "-t", str(t1 - t0),
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out]
subprocess.run(args, check=True)
print("wrote", out)
