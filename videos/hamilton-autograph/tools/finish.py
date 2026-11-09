"""The finish: the final frames -> per-scene colour grade + bloom + vignette + grain -> captions -> voiceover and
sound design -> the final MP4 (H.264 High, yuv420p, AAC, faststart: plays on phones).

Run: python tools/finish.py <frames_dir> <captions_dir> <sfx.wav> <out.mp4>
Each shot is graded on its own (its environment's grade, from blender/look.py's table) into a lossless segment;
the segments are joined, then captions and audio go on in one last encode.
"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "blender"))
frames, caps, sfx, out = sys.argv[1:5]
FPS = 30

# the same environment table the renders used (look.py imports bpy, so read the sets from the source instead)
MONZA = {1, 2, 3, 4, 5, 6, 7, 20, 21, 22, 25}
BAHRAIN = {13, 14, 15, 16, 17}
GARAGE = {8, 18, 23}
LAUNCH = {9, 10, 24}
ENV = {**{n: "monza" for n in MONZA}, **{n: "bahrain" for n in BAHRAIN}, **{n: "garage" for n in GARAGE},
       **{n: "launch" for n in LAUNCH}, 11: "lab", 12: "hangar", 19: "pedestal"}

# warm for the sunny day, cool shadows / warm highlights for the night, clean and slightly cool indoors,
# teal-orange on the launch stage, contrasty for the trophy shot
GRADE = {
    "monza":    "colorbalance=rs=0.02:bs=-0.03:rm=0.02:bm=-0.02:rh=0.03:gh=0.01:bh=-0.03,eq=contrast=1.1:saturation=1.22",
    "bahrain":  "colorbalance=rs=-0.04:gs=-0.01:bs=0.06:rm=-0.01:bm=0.02:rh=0.05:gh=0.02:bh=-0.03,eq=contrast=1.12:saturation=1.18:brightness=-0.015",
    "garage":   "colorbalance=rs=-0.01:bs=0.03:rh=0.02,eq=contrast=1.12:saturation=1.2:brightness=-0.02",
    "launch":   "colorbalance=rs=-0.03:gs=0.01:bs=0.03:rh=0.04:gh=0.01:bh=-0.03,eq=contrast=1.12:saturation=1.2:brightness=-0.02",
    "lab":      "colorbalance=bs=0.03:rh=-0.01,eq=contrast=1.1:saturation=1.12",
    "hangar":   "colorbalance=rs=0.01:bs=0.01:rh=0.02,eq=contrast=1.12:saturation=1.25",
    "pedestal": "colorbalance=bs=0.02:rh=0.03:bh=-0.02,eq=contrast=1.14:saturation=1.18",
}
# soft bloom (only the brightest parts glow), a gentle vignette, fine film grain
# (in RGB: eq hands over YUV, and a screen blend on the chroma planes would tint everything purple)
POLISH = ("format=gbrp,vibrance=intensity=0.18,split=2[a][b];[b]lutrgb=r='if(gt(val,205),val,0)':g='if(gt(val,205),val,0)':b='if(gt(val,205),val,0)',"
          "gblur=sigma=22[g];[a][g]blend=all_mode=screen:all_opacity=0.3,vignette=a=0.42,noise=alls=3:allf=t")

shots = json.load(open(os.path.join(ROOT, "boards", "shots.json")))
tmp = tempfile.mkdtemp(prefix="halo_finish_")
graded = os.path.join(ROOT, "out", "graded.mkv")  # REUSE_GRADE=1: keep the graded picture, only re-mix the sound
segs = [] if not (os.environ.get("REUSE_GRADE") and os.path.exists(graded)) else None
for s in (shots if segs is not None else []):
    n = s["n"]
    f0, f1 = round(s["start"] * FPS), round(s["end"] * FPS)
    seg = os.path.join(tmp, f"seg{n:02d}.mkv")
    vf = f"{GRADE[ENV[n]]},{POLISH}"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-start_number", str(f0),
                    "-i", os.path.join(frames, "f%05d.png"), "-frames:v", str(f1 - f0),
                    "-filter_complex", vf, "-c:v", "ffv1", "-pix_fmt", "gbrp", seg], check=True)
    segs.append(seg)
    print("graded", n, ENV[n], flush=True)
if segs is not None:
    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in segs))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", graded], check=True)

meta = json.load(open(os.path.join(caps, "captions.json")))
vo = os.path.join(ROOT, "assets", "audio", "narrator", "vo_60.wav")
args = ["ffmpeg", "-v", "error", "-y", "-i", graded]
for c in meta:
    args += ["-i", os.path.join(caps, os.path.basename(c["file"]))]
args += ["-i", vo, "-i", sfx]
chain = ["[0:v]scale=1080:1920:flags=lanczos[v0]"]
last = "v0"
for i, c in enumerate(meta):
    chain.append(f"[{last}][{i + 1}:v]overlay=0:0:enable='between(t,{c['start']:.3f},{c['end']:.3f})'[v{i + 1}]")
    last = f"v{i + 1}"
vi, si = len(meta) + 1, len(meta) + 2
chain.append(f"[{last}]format=yuv420p[vout]")
# the voice on top; the sound design under it, ducked a little whenever the narrator speaks
chain.append(f"[{vi}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=1.0,asplit=2[vo][key]")
chain.append(f"[{si}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=0.6[fx0]")
chain.append("[fx0][key]sidechaincompress=threshold=0.025:ratio=6:attack=15:release=400[fx]")  # out of the voice's way
chain.append("[vo][fx]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.89[aout]")
args += ["-filter_complex", ";".join(chain), "-map", "[vout]", "-map", "[aout]", "-t", "60",
         "-c:v", "libx264", "-profile:v", "high", "-level:v", "4.0", "-pix_fmt", "yuv420p", "-crf", "17",
         "-preset", "slow", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
         "-movflags", "+faststart", out]
subprocess.run(args, check=True)
print("wrote", out)
