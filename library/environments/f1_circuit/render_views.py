"""Render camera presets from blend/circuit.blend (EEVEE) for checks and the model sheet.

blender -b blend/circuit.blend --python render_views.py -- [--out DIR] [--time day|night|...] [--cams a,b] [--scale 0.5] [--samples 32]
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import lighting, cameras

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
opt = lambda k, d: argv[argv.index(k) + 1] if k in argv else d
out = opt("--out", os.path.join(os.path.dirname(os.path.abspath(__file__)), "sheet", "views"))
mode = opt("--time", "day")
scale = float(opt("--scale", "0.5"))
samples = int(opt("--samples", "24"))
cams = opt("--cams", "")
os.makedirs(out, exist_ok=True)
sc = bpy.context.scene
lighting.eevee(sc, samples)
lighting.set_time(sc, mode)
sc.render.resolution_percentage = int(scale * 100)
sc.render.image_settings.file_format = "PNG"
names = cams.split(",") if cams else sorted(o.name for o in bpy.data.objects if o.type == "CAMERA")
for n in names:
    cameras.use(n)
    sc.render.filepath = os.path.join(out, f"{n}_{mode}.png")
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"RENDER {n} {mode} {time.time() - t0:.1f}s", flush=True)
