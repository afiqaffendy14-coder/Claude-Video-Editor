"""Stage 3, lighting and grade: every shot gets the storyboard grade the owner liked (boards/grade.sh), its scene's
colour, and its brightness set into a band for its kind of place (night interiors dark and moody but readable,
the grey paddock and the garage brighter, the rain in between), so no shot is too dark or too bright and the cuts
between shots of one place match. Then a soft bloom on the brightest parts and a fine grain.

Run: .venv-tools/Scripts/python tools/grade_frames.py out/frames_test out/frames_graded
(shot 7's three panels must already be stacked into f*.png: compose_test.py does that.)
"""
import json, math, os, re, subprocess, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
src, dst = (os.path.abspath(a) for a in sys.argv[1:3])
os.makedirs(dst, exist_ok=True)
FPS = 30
BASE = re.search(r'GRADE="(.+)"', open(os.path.join(ROOT, "boards", "grade.sh")).read()).group(1)

# shot -> (scene colour, target mean luma 0-255 after the grade)
SCENE = {
    "ball":    ("colorbalance=rs=0.01:bs=0.02:rh=0.04:gh=0.015:bh=-0.03", 50),     # dark ballroom, warm light
    "night":   ("colorbalance=rs=0.02:bs=-0.01:rh=0.04:gh=0.01:bh=-0.04", 58),     # tungsten at night
    "jobs":    ("colorbalance=rh=0.015:bh=-0.01", 100),
    "paddock": ("colorbalance=rs=-0.01:bs=0.02:rh=0.01:bh=-0.01", 104),           # grey British day
    "podium":  ("colorbalance=rh=0.02:bh=-0.015", 112),
    "shelf":   ("colorbalance=rs=0.02:rh=0.04:bh=-0.04", 58),
    "office":  ("colorbalance=rs=0.01:bs=0.01:rh=0.02:bh=-0.02", 72),
    "rain":    ("colorbalance=rs=-0.03:gs=-0.005:bs=0.04:rh=0.02:bh=-0.01", 84),  # cool, wet Interlagos dusk
    "garage":  ("colorbalance=bs=0.02:rh=0.01", 118),
}
ENV = {1: "ball", 2: "ball", 3: "ball", 4: "night", 5: "night", 6: "night", 7: "jobs", 8: "paddock", 9: "paddock",
       10: "paddock", 11: "paddock", 12: "paddock", 13: "paddock", 14: "podium", 15: "shelf", 16: "office",
       17: "rain", 18: "rain", 19: "rain", 20: "rain", 21: "night", 22: "rain"}
SPLIT = {19: ("garage", 0.45)}
# shots whose brightness the owner has already set in the render: keep it (1a was made darker on purpose, 10 was
# asked for "between too dark and too bright")
GAMMA = {1: 1.0, 10: 1.08}
ONLY = set(int(a) for a in sys.argv[3:])   # shot 19's second half is the garage
POLISH = ("format=gbrp,split=2[a][b];[b]lutrgb=r='if(gt(val,215),val,0)':g='if(gt(val,215),val,0)':b='if(gt(val,215),val,0)',"
          "gblur=sigma=14[g];[a][g]blend=all_mode=screen:all_opacity=0.22,noise=alls=2:allf=t,format=rgb24")

ns = {}
s = open(os.path.join(ROOT, "blender", "ham_anim.py"), encoding="utf-8").read()
exec(s[s.index("FS = 5"):s.index("}", s.index("SHOT_T = {")) + 1], {"END": 48.30 + 5 / 30}, ns)
SHOT_T = ns["SHOT_T"]
N = int(round((48.30 + 5 / 30) * FPS))


def ffgrade(frames, vf, out_dir):
    """Grade a list of frame numbers with one filter chain (frames are copied to a temp sequence)."""
    tmp = os.path.join(dst, "_seq")
    os.makedirs(tmp, exist_ok=True)
    for i, f in enumerate(frames):
        p = os.path.join(tmp, f"s{i:05d}.png")
        if os.path.exists(p):
            os.remove(p)
        os.link(os.path.join(src, f"f{f:05d}.png"), p)
    outp = os.path.join(tmp, "o%05d.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(tmp, "s%05d.png"),
                    "-filter_complex", vf, "-start_number", "0", outp], check=True)
    for i, f in enumerate(frames):
        os.replace(os.path.join(tmp, f"o{i:05d}.png"), os.path.join(out_dir, f"f{f:05d}.png"))
        os.remove(os.path.join(tmp, f"s{i:05d}.png"))


def mean_luma(frames, vf):
    """Mean luma of a few frames after a filter chain."""
    vals = []
    for f in frames:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(src, f"f{f:05d}.png"), "-vf", vf + ",format=gray",
                              "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
        vals.append(np.frombuffer(raw, np.uint8).mean())
    return float(np.mean(vals))


report = []
for n, (a, b) in SHOT_T.items():
    if ONLY and n not in ONLY:
        continue
    f0, f1 = int(round(a * FPS)), min(N, int(round(b * FPS)))
    parts = [(ENV[n], list(range(f0, f1)))]
    if n in SPLIT:
        env2, w = SPLIT[n]
        fm = int(round((a + (b - a) * w) * FPS))
        parts = [(ENV[n], list(range(f0, fm))), (env2, list(range(fm, f1)))]
    for env, frames in parts:
        col, target = SCENE[env]
        pre = f"{BASE},{col}"
        probe = frames[:: max(1, len(frames) // 4)][:4]
        m = mean_luma(probe, pre)
        g = math.log(max(m, 1) / 255) / math.log(target / 255)          # eq gamma that moves the mean to the target
        g = GAMMA.get(n, max(0.78, min(1.32, g)))
        vf = f"{pre},eq=gamma={g:.3f},{POLISH}"
        ffgrade(frames, vf, dst)
        after = mean_luma(probe[:2], f"{pre},eq=gamma={g:.3f}")
        report.append((n, env, round(m), round(after), round(g, 2)))
        print(f"shot {n:2d} {env:8s} luma {m:5.1f} -> {after:5.1f} (gamma {g:.2f})", flush=True)
if not ONLY:
    json.dump(report, open(os.path.join(dst, "grade_report.json"), "w"), indent=1)
os.rmdir(os.path.join(dst, "_seq"))
