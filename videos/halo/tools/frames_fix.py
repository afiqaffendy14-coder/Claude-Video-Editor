"""Prepare out/frames before a render pass (run with Blender's Python):
  * deletes broken frames (empty or truncated PNGs left by an interrupted render) so they get rendered again
  * with shot numbers, deletes those shots' frames so just those shots are re-rendered
Run: blender -b --factory-startup --python tools/frames_fix.py -- <frames_dir> [shot ids...]
"""
import os, sys
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
d = argv[0]
ids = [int(a) for a in argv[1:]]
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "blender"))
removed = 0
if os.path.isdir(d):
    sizes = {f: os.path.getsize(os.path.join(d, f)) for f in os.listdir(d) if f.endswith(".png")}
    typical = sorted(sizes.values())[len(sizes) // 2] if sizes else 0
    for f, sz in sizes.items():
        ok = sz > max(20000, typical * 0.15)
        if ok:
            with open(os.path.join(d, f), "rb") as fh:  # a complete PNG ends with the IEND chunk
                fh.seek(-12, 2)
                ok = b"IEND" in fh.read()
        if not ok:
            os.remove(os.path.join(d, f))
            removed += 1
            print("broken frame removed:", f)
    if ids:
        import shots
        table = {s[0]: s for s in shots.SHOTS}
        for n in ids:
            _, t0, t1 = table[n][:3]
            for fr in range(round(t0 * 30), round(t1 * 30)):
                p = os.path.join(d, f"f{fr:05d}.png")
                if os.path.exists(p):
                    os.remove(p)
                    removed += 1
            print(f"shot {n}: frames {round(t0 * 30)}-{round(t1 * 30) - 1} cleared for re-render")
print(f"frames_fix: {removed} frame(s) to re-render")
