"""Animation test: frames -> (shot 7's three panels stacked) -> the storyboard grade -> 1080x1920 -> title box and
captions -> voiceover -> MP4 (and a phone copy under 30 MiB). No sound effects yet (that is stage 5).

Run: .venv-tools/Scripts/python tools/compose_test.py <frames_dir> <captions_dir> <out.mp4>
"""
import glob, json, os, re, subprocess, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
frames, caps, out = (os.path.abspath(a) for a in sys.argv[1:4])
FPS, ANIM = 30, 48.30 + 5 / 30          # the animation ends at the hard cut after "Hamilton."
FADE, END = 47.56 + 5 / 30, 49.50 + 5 / 30       # from "Hamilton" the real 2008 photo fades in over 0.5 s and holds to END
N = int(round(ANIM * FPS))

# shot 7: three 540x320 panels -> one 540x960 frame
p0 = os.path.join(frames, "panel0")
if os.path.isdir(p0):
    for f in sorted(glob.glob(os.path.join(p0, "f*.png"))):
        name = os.path.basename(f)
        dst = os.path.join(frames, name)
        if os.path.exists(dst):
            continue
        parts = [os.path.join(frames, f"panel{i}", name) for i in range(3)]
        if all(os.path.exists(p) for p in parts):
            pw, ph = Image.open(parts[0]).size           # 540x320 for tests, 1080x640 for the final
            im = Image.new("RGB", (pw, 3 * ph))
            sw = max(2, pw // 270)
            for i, p in enumerate(parts):
                im.paste(Image.open(p).convert("RGB"), (0, i * ph))
                if i:  # a thin dark seam between panels
                    im.paste((8, 8, 8), (0, i * ph - sw, pw, i * ph + sw))
            im.save(dst)
missing = [f for f in range(N) if not os.path.exists(os.path.join(frames, f"f{f:05d}.png"))]
if missing:
    print(f"{len(missing)} frames missing, first {missing[:5]}")
    sys.exit(1)

grade = "null" if os.environ.get("GRADED") else re.search(r'GRADE="(.+)"', open(os.path.join(ROOT, "boards", "grade.sh")).read()).group(1)
meta = json.load(open(os.path.join(caps, "captions.json")))
vo = os.path.join(ROOT, "assets", "audio", "narrator", "vo.wav")
# the photo (CC BY 2.0, Alistair Rickman, assets/photo/CREDIT.txt): a 9:16 crop around his face, 12 % oversize for
# a slow push in
src = Image.open(os.path.join(ROOT, "assets", "photo", "hamilton_2008_rickman.jpg")).convert("RGB")
cw = int(src.height * 9 / 16)
cx = int(src.width * 0.52)
photo_png = os.path.join(frames, "photo_end.png")
src.crop((cx - cw // 2, 0, cx + cw // 2, src.height)).resize((1210, 2150), Image.LANCZOS).save(photo_png)
args = ["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(frames, "f%05d.png")]
for c in meta:
    args += ["-loop", "1", "-framerate", str(FPS), "-t", f"{END}", "-i", os.path.join(caps, os.path.basename(c["file"].replace("\\", "/")))]
args += ["-loop", "1", "-framerate", str(FPS), "-t", f"{END - FADE:.3f}", "-i", photo_png, "-i", vo]
SFX = os.environ.get("SFX")  # the sound-effects mix (tools/sfx_mix_ham.py), +3 dB here, still well under the voice
if SFX:
    args += ["-i", os.path.abspath(SFX)]
pi = len(meta) + 1
chain = [f"[0:v]{grade},scale=1080:1920:flags=lanczos,tpad=stop_mode=clone:stop_duration={END - ANIM + 0.1:.2f},format=yuv420p[g0]",
         f"[{pi}:v]scale=w='trunc(1210*(1+0.05*t/{END - FADE:.2f})/2)*2':h=-2:eval=frame,"
         f"crop=1080:1920:(iw-1080)/2:(ih-1920)*0.25,eq=saturation=1.04:contrast=1.03,format=yuva420p,"
         f"fade=in:st=0:d=0.5:alpha=1,setpts=PTS+{FADE}/TB[ph]",
         f"[g0][ph]overlay=0:0:eof_action=pass:format=auto,format=yuv420p[v0]"]
last = "v0"
for i, c in enumerate(meta):
    chain.append(f"[{last}][{i + 1}:v]overlay=0:0:enable='between(t,{c['start']:.3f},{c['end'] - 0.001:.3f})'[v{i + 1}]")
    last = f"v{i + 1}"
if SFX:
    # The voice is the film: clear in a car or on a phone speaker. A gentle compressor evens it out, the effects sit
    # lower, and the mix is levelled to YouTube's -14 LUFS (louder than the -16 voice-only master before).
    chain.append(f"[{len(meta) + 2}:a]highpass=f=70,acompressor=threshold=-24dB:ratio=3:attack=5:release=90:makeup=3dB,"
                 f"apad,atrim=0:{END}[vo];[{len(meta) + 3}:a]volume=-1dB,apad,atrim=0:{END}[fx];"
                 f"[vo][fx]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=9,"
                 f"aresample=48000,alimiter=limit=0.84:level=false[a]")
else:
    chain.append(f"[{len(meta) + 2}:a]apad,atrim=0:{END}[a]")
enc = ["-filter_complex", ";".join(chain), "-map", f"[{last}]", "-map", "[a]", "-t", f"{END}", "-r", str(FPS),
       "-c:v", "libx264", "-profile:v", "high", "-level", "4.0", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
       "-movflags", "+faststart"]
subprocess.run(args + enc + ["-crf", "18", "-preset", "medium", out], check=True)
phone = out.replace(".mp4", "-phone.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out, "-c:v", "libx264", "-profile:v", "high", "-level", "4.0",
                "-pix_fmt", "yuv420p", "-b:v", "3500k", "-maxrate", "4500k", "-bufsize", "9000k", "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart", phone], check=True)
for f in (out, phone):
    print(f, f"{os.path.getsize(f) / 2**20:.1f} MiB")
