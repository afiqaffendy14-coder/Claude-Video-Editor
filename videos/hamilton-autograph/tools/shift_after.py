"""Give a word more air: insert a short silence into the voiceover at a point inside a pause, and shift everything
after it (word timings, shot times, rendered frames, film length) by the same whole number of frames.

Used once (round 5): "At the track" came 0.18 s after "racing." and 70 ms before the cut, so the short "At" got
swallowed. 5 frames (0.167 s) of silence go in at 16.95 s.

Run: ../../.venv-audio/Scripts/python tools/shift_after.py 16.95 5
"""
import json, os, re, shutil, sys
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AT, NF = float(sys.argv[1]), int(sys.argv[2])
FPS = 30
DT = NF / FPS
bk = os.path.join(ROOT, "out", "before_shift")
os.makedirs(bk, exist_ok=True)


def backup(p):
    shutil.copy2(p, os.path.join(bk, os.path.basename(p)))


def sh(t):
    return t + DT if t >= AT else t


# voiceover: silence in the pause
vo = os.path.join(ROOT, "assets", "audio", "narrator", "vo.wav")
backup(vo)
y, sr = sf.read(vo, dtype="float32")
i = int(AT * sr)
pad = np.zeros((int(round(DT * sr)),) + y.shape[1:], np.float32)
sf.write(vo, np.concatenate([y[:i], pad, y[i:]]), sr, subtype="FLOAT")

# word timings
tp = os.path.join(HERE, "timing.json")
backup(tp)
d = json.load(open(tp, encoding="utf-8"))
for l in d["lines"]:
    for k in ("start", "end"):
        if k in l:
            l[k] = round(sh(l[k]), 3)
    for w in l["words"]:
        w["start"], w["end"] = round(sh(w["start"]), 3), round(sh(w["end"]), 3)
d["duration"] = round(d["duration"] + DT, 3)
json.dump(d, open(tp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def shift_numbers(path, pattern):
    """Shift every time literal matched by pattern (group 1) that is >= AT."""
    backup(path)
    s = open(path, encoding="utf-8").read()
    s = re.sub(pattern, lambda m: m.group(0).replace(m.group(1), f"{sh(float(m.group(1))):.2f}" if float(m.group(1)) >= AT else m.group(1)), s)
    open(path, "w", encoding="utf-8").write(s)


# shot times and film length in the animation
ap = os.path.join(ROOT, "blender", "ham_anim.py")
backup(ap)
s = open(ap, encoding="utf-8").read()
a, b = s.index("SHOT_T = {"), s.index("}", s.index("SHOT_T = {"))
st = re.sub(r"(\d+\.\d+)", lambda m: f"{sh(float(m.group(1))):.2f}" if float(m.group(1)) >= AT else m.group(1), s[a:b])
s = s[:a] + st + s[b:]
s = re.sub(r"^END = 48\.30", f"END = {48.30 + DT:.4f}", s, flags=re.M)
open(ap, "w", encoding="utf-8").write(s)

# the storyboard shot tables
for v in ("shots_v5.json",):
    p = os.path.join(ROOT, "boards", v)
    dd = json.load(open(p, encoding="utf-8"))
    for x in dd:
        x["start"], x["end"] = round(sh(x["start"]), 3), round(sh(x["end"]), 3)
    json.dump(dd, open(os.path.join(ROOT, "boards", "shots_v6.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# rendered frames: everything from the first shifted frame moves up NF numbers (highest first)
fr = os.path.join(ROOT, "out", "frames_test")
f0 = int(round(sh(17.07) * FPS)) - NF   # the first frame of shot 8 before the shift
names = sorted((int(n[1:6]) for n in os.listdir(fr) if re.match(r"f\d{5}\.png$", n) and int(n[1:6]) >= f0), reverse=True)
for n in names:
    os.rename(os.path.join(fr, f"f{n:05d}.png"), os.path.join(fr, f"f{n + NF:05d}.png"))
print(f"inserted {DT:.3f}s at {AT}s; {len(names)} frames moved up {NF}; first moved {f0}")
