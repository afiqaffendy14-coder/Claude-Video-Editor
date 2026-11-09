"""Before boards/build.mjs: stack the split-screen panels (shot 7: a, b, c) into one 540x960 still, then grade
every still into boards/graded (boards/grade.sh look). Run: .venv-tools/Scripts/python tools/board_prep.py"""
import glob, os, subprocess
from PIL import Image
B = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "boards")
st = os.path.join(B, "stills")
parts = [os.path.join(st, f"s07{k}.png") for k in "abc"]
if all(os.path.exists(p) for p in parts):
    out = Image.new("RGB", (540, 960), (0, 0, 0))
    for i, p in enumerate(parts):
        out.paste(Image.open(p).convert("RGB"), (0, i * 320))
    out.save(os.path.join(st, "s07.png"))
os.makedirs(os.path.join(B, "graded"), exist_ok=True)
for f in sorted(glob.glob(os.path.join(st, "s*.png"))):
    subprocess.run(["bash", os.path.join(B, "grade.sh"), f, os.path.join(B, "graded", os.path.basename(f))], check=True)
print("graded", len(glob.glob(os.path.join(B, "graded", "*.png"))))
