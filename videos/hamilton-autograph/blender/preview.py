"""Quick look at baked shots: a handful of small, noisy frames per shot (CPU-friendly), for checking motion.
Run:  preview.py <blend_dir> <out_dir> <frames per shot> [shot ids...]   -> <out_dir>/pNN_FFFF.png
"""
import os, sys
import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [a for a in sys.argv[1:] if not a.endswith(".py")]
src, out, k = argv[0], argv[1], int(argv[2])
ids = [int(a) for a in argv[3:]] or sorted(int(f[1:3]) for f in os.listdir(src) if f.endswith(".blend"))
os.makedirs(out, exist_ok=True)
for n in ids:
    bpy.ops.wm.open_mainfile(filepath=os.path.join(src, f"s{n:02d}.blend"))
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 3
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
    sc.render.resolution_percentage = 22
    sc.render.use_motion_blur = False
    sc.render.image_settings.file_format = "PNG"
    f0, f1 = sc.frame_start, sc.frame_end
    for i in range(k):
        f = round(f0 + (f1 - f0) * i / max(1, k - 1))
        sc.frame_set(f)
        sc.render.filepath = os.path.join(out, f"p{n:02d}_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
    print("previewed", n, flush=True)
