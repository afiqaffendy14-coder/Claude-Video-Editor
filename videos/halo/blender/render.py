"""Render the baked shots (out/blend/sNN.blend) to numbered frames on the GPU. Frames already on disk are skipped,
so an interrupted render picks up where it stopped.

Run:  blender -b --python blender/render.py -- <blend_dir> <frames_dir> [eevee|cycles] [quality%] [shot ids...]
      eevee (default): fast, ~10-20 min for the minute on an RTX laptop.  cycles: path traced, slower, a bit nicer.
"""
import os, sys
import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
src, out = os.path.abspath(argv[0]), os.path.abspath(argv[1])
engine = argv[2] if len(argv) > 2 else "eevee"
pct = int(argv[3]) if len(argv) > 3 else 100
ids = [int(a) for a in argv[4:]] or sorted(int(f[1:3]) for f in os.listdir(src) if f.startswith("s") and f.endswith(".blend"))
os.makedirs(out, exist_ok=True)


def gpu_cycles(sc):
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
        try:
            prefs.compute_device_type = kind
            prefs.get_devices()
            devs = [d for d in prefs.devices if d.type == kind]
            if devs:
                for d in prefs.devices:
                    d.use = d.type == kind
                sc.cycles.device = "GPU"
                print(f"Cycles on {kind}: {', '.join(d.name for d in devs)}", flush=True)
                return kind
        except (TypeError, ValueError):
            continue
    sc.cycles.device = "CPU"
    print("No GPU found for Cycles: rendering on the CPU (slow).", flush=True)
    return "CPU"


def setup(sc):
    r = sc.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = 1080, 1920, pct
    r.fps = 30
    preview = os.environ.get("PREVIEW")  # quick movement review: fewer samples, no motion blur
    r.use_motion_blur = not preview
    r.motion_blur_shutter = 0.3  # a touch of blur on fast motion, never smeared
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    r.use_overwrite = False   # resume: frames already rendered are skipped
    r.use_placeholder = True  # lets two Blender windows share the job without clashing
    r.filepath = os.path.join(out, "f#####")
    if engine == "cycles":
        r.engine = "CYCLES"
        kind = gpu_cycles(sc)
        sc.cycles.samples = 48 if kind != "CPU" else 16
        sc.cycles.use_adaptive_sampling = True
        sc.cycles.use_denoising = True
        sc.cycles.denoiser = "OPTIX" if kind == "OPTIX" else "OPENIMAGEDENOISE"
        sc.render.use_persistent_data = True
    else:
        r.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
        e = sc.eevee
        for attr, val in (("taa_render_samples", 12 if preview else int(os.environ.get("SAMPLES", 48))), ("use_shadows", True), ("shadow_ray_count", 1 if preview else 2),
                          ("shadow_step_count", 4 if preview else 8),
                          ("use_raytracing", not preview), ("ray_tracing_method", "SCREEN"), ("use_gtao", True),
                          ("fast_gi_method", "GLOBAL_ILLUMINATION"), ("use_volumetric_shadows", False),
                          ("motion_blur_steps", 2), ("use_motion_blur", not preview)):
            if hasattr(e, attr):
                try:
                    setattr(e, attr, val)
                except (TypeError, ValueError):
                    pass
        # see-through materials (screens, glass) blend instead of being dithered noise
        for m in bpy.data.materials:
            if hasattr(m, "surface_render_method"):
                m.surface_render_method = "BLENDED" if m.blend_method == "BLEND" else "DITHERED"


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
for n in ids:
    path = os.path.join(src, f"s{n:02d}.blend")
    bpy.ops.wm.open_mainfile(filepath=path)
    sc = bpy.context.scene
    setup(sc)
    if not os.environ.get("PREVIEW"):  # the final look: lighting, atmosphere, tone mapping per environment
        import look
        print(f"shot {n:02d}: look '{look.apply(sc, n)}'", flush=True)
        if n in (3, 4, 13, 14, 15):  # the fast racing and crash shots: more motion blur sells the speed
            sc.render.motion_blur_shutter = 0.55
    todo = [f for f in range(sc.frame_start, sc.frame_end + 1) if not os.path.exists(os.path.join(out, f"f{f:05d}.png"))]
    print(f"shot {n:02d}: frames {sc.frame_start}-{sc.frame_end}, {len(todo)} to render", flush=True)
    if os.environ.get("ONE"):  # look test: one frame of the shot at the given fraction (e.g. ONE=0.6), timed
        import time
        f = sc.frame_start + int((sc.frame_end - sc.frame_start) * float(os.environ["ONE"]))
        sc.frame_set(f)
        sc.render.filepath = os.path.join(out, f"look_s{n:02d}.png")
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"LOOK s{n:02d} f{f} {time.time() - t0:.1f}s", flush=True)
        continue
    if os.environ.get("RENDER_DRYRUN"):
        print("dry run:", sc.render.engine, getattr(sc.eevee, "taa_render_samples", None), flush=True)
    elif todo:
        bpy.ops.render.render(animation=True)
print("RENDER DONE", flush=True)
