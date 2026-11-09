"""All four liveries side by side, each with its team driver, appended from the saved .blend files
(so this also checks load_kart + seat_in_car end to end).

blender -b --factory-startup --python render_lineup.py -- [--samples 96] [--steer 0]
-> sheet/lineup.png
"""
import importlib.util
import os
import sys
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "characters", "block_character"))
import kart_blueprint as bp  # noqa: E402
import kart_blender  # noqa: E402
import character_blender as ch  # noqa: E402

_sp = importlib.util.spec_from_file_location("f1_render_sheet", os.path.join(HERE, "..", "f1_2026", "render_sheet.py"))
rs = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(rs)


def main():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    samples = int(a[a.index("--samples") + 1]) if "--samples" in a else 96
    steer = float(a[a.index("--steer") + 1]) if "--steer" in a else 0.0
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    rs.gpu(sc)
    sc.cycles.samples, sc.cycles.use_denoising = samples, True
    sc.render.film_transparent = True
    sc.view_settings.view_transform, sc.view_settings.look = "AgX", "AgX - Medium High Contrast"
    rs.world()
    for i, liv in enumerate(bp.LIVERIES):
        k = kart_blender.load_kart(f"k{i}", liv)
        n = len(bp.LIVERIES)
        k.location = ((i - (n - 1) / 2) * 1.65, -abs(i - (n - 1) / 2) * 0.35, 0)
        k["steer"] = steer
        d = ch.make_character(f"d{i}", bp.driver_skin(liv), helmet=True)
        ch.seat_in_car(d, k)
    floor = bpy.data.objects.new("floor", bpy.data.meshes.new("floor"))
    floor.data.from_pydata([(-30, -30, 0), (30, -30, 0), (30, 30, 0), (-30, 30, 0)], [], [(0, 1, 2, 3)])
    sc.collection.objects.link(floor)
    floor.is_shadow_catcher = True
    L = {"key": rs.area("key", 4.0, 1500), "fill": rs.area("fill", 5.0, 300), "top": rs.area("top", 7.0, 1100),
         "rim": rs.area("rim", 3.0, 900)}
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    tgt = (0.0, -0.20, 0.36)
    cam.location = (-1.6, 9.6, 3.3)
    f, r, u = rs.look(cam, tgt)
    cam.data.lens = 45
    rs.rig_lights(L, f, r, tgt)
    sc.render.resolution_x, sc.render.resolution_y = 2400, 1100
    sc.render.filepath = os.path.join(HERE, "sheet", "lineup.png")
    bpy.ops.render.render(write_still=True)
    print("rendered lineup")


main()
