"""Render every view of the kart model sheet from the blueprint (same kart, same scale in every orthographic view).

blender -b --factory-startup --python render_sheet.py -- [--livery silver_arrow] [--scale 0.5] [--samples 96] [view ...]
-> sheet/<livery>/renders/<view>.png (transparent, shadow on the floor) and anchors.json
"""
import importlib.util
import json
import os
import sys
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "characters", "block_character"))
import kart_blueprint as bp  # noqa: E402
import kart_blender  # noqa: E402

_sp = importlib.util.spec_from_file_location("f1_render_sheet", os.path.join(HERE, "..", "f1_2026", "render_sheet.py"))
rs = importlib.util.module_from_spec(_sp)   # the F1 sheet's studio: world, lights, GPU, camera aim
_sp.loader.exec_module(rs)

PPM = 950  # pixels per metre in every orthographic view
CY, CZ = 0.03, 0.33
ORTHO = {  # name: (camera direction, up, width m, height m)
    "side_left": ((1, 0, 0), (0, 0, 1), 1.96, 0.70),
    "side_right": ((-1, 0, 0), (0, 0, 1), 1.96, 0.70),
    "front": ((0, -1, 0), (0, 0, 1), 1.50, 0.70),
    "rear": ((0, 1, 0), (0, 0, 1), 1.50, 0.70),
    "top": ((0, 0, -1), (1, 0, 0), 1.96, 1.50),
    "bottom": ((0, 0, 1), (-1, 0, 0), 1.96, 1.50),
}
PERSP = {  # name: (camera, target, lens, w, h, hidden objects, driver?)
    "q_front_left": ((-1.95, 2.45, 1.10), (0.0, 0.06, 0.20), 70, 1800, 1050, (), False),
    "q_rear_left": ((-2.05, -2.30, 1.05), (0.0, -0.06, 0.22), 70, 1800, 1050, (), False),
    "c_cockpit": ((-0.62, 0.78, 0.98), (0.0, 0.08, 0.26), 45, 1600, 1200, (), False),
    "c_engine": ((0.80, -0.62, 0.98), (0.31, -0.27, 0.17), 40, 1600, 1200, (), False),
    "c_rear_axle": ((0.62, -1.20, 0.34), (0.12, -0.52, 0.15), 40, 1600, 1200, ("rear_bumper",), False),
    "c_front_end": ((-0.98, 1.20, 0.50), (-0.24, 0.48, 0.13), 45, 1600, 1200, (), False),
    "c_wheel": ((-1.00, 0.95, 0.24), (-0.60, 0.5175, 0.124), 55, 1600, 1200, (), False),
    "c_seat": ((-1.05, -0.80, 0.78), (-0.24, -0.26, 0.24), 45, 1600, 1200, (), False),
    "d_front_left": ((-2.2, 2.65, 1.45), (0.0, 0.0, 0.42), 55, 1800, 1300, (), True),
    "d_rear_right": ((2.0, -2.5, 1.55), (0.0, -0.02, 0.42), 55, 1800, 1300, (), True),
}


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = dict(scale=1.0, samples=96, views=[], livery="silver_arrow")
    i = 0
    while i < len(a):
        if a[i] in ("--scale", "--livery", "--samples"):
            o[a[i][2:]] = type(o[a[i][2:]])(a[i + 1]); i += 2
        else:
            o["views"].append(a[i]); i += 1
    return o


def main():
    o = args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    print("device", rs.gpu(sc))
    sc.cycles.samples = o["samples"]
    sc.cycles.use_denoising = True
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    rs.world()
    root, objs = kart_blender.make_kart("kart", livery=o["livery"])
    driver = None
    floor = bpy.data.objects.new("floor", bpy.data.meshes.new("floor"))
    floor.data.from_pydata([(-30, -30, 0), (30, -30, 0), (30, 30, 0), (-30, 30, 0)], [], [(0, 1, 2, 3)])
    sc.collection.objects.link(floor)
    floor.is_shadow_catcher = True
    L = {"key": rs.area("key", 4.0, 1500), "fill": rs.area("fill", 5.0, 300, (0.92, 0.96, 1.0)),
         "top": rs.area("top", 7.0, 1100), "rim": rs.area("rim", 3.0, 900, (0.85, 1.0, 0.97))}
    base_energy = {k: ob.data.energy for k, ob in L.items()}
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    out = os.path.join(HERE, "sheet", o["livery"], "renders")
    os.makedirs(out, exist_ok=True)
    apath = os.path.join(out, "anchors.json")
    anchors = json.load(open(apath)) if os.path.exists(apath) else {}
    views = o["views"] or list(ORTHO) + list(PERSP)
    for v in views:
        for k, ob in L.items():
            ob.data.energy = base_energy[k]
        for ob in objs.values():
            ob.hide_render = False
        floor.hide_render = v == "bottom"
        want_driver = v in PERSP and PERSP[v][6]
        if want_driver and driver is None:
            import character_blender as ch
            skin = bp.driver_skin(o["livery"])
            driver = ch.make_character("driver", skin, helmet=True)
            ch.seat_in_car(driver, root)
        if driver is not None:
            for ob in [driver] + list(driver.children_recursive):
                ob.hide_render = not want_driver
        if v in ORTHO:
            d, up, wm, hm = ORTHO[v]
            target = Vector((0, CY, CZ))
            cam.location = target - Vector(d) * 6
            f, r, u = rs.look(cam, target, up)
            cam.data.type = "ORTHO"
            cam.data.ortho_scale = max(wm, hm)
            cam.data.clip_end = 30
            w, h = round(wm * PPM * o["scale"]), round(hm * PPM * o["scale"])
            if v == "bottom":
                for k, ob in L.items():
                    ob.location = target + Vector((0, 0, -5)) + {"key": Vector((-2, 2, 0)), "fill": Vector((2, -2, 1)),
                                                                  "top": Vector((0, 0, -1)), "rim": Vector((0, 4, 3))}[k]
                    ob.data.energy *= 0.45
                    rs.look(ob, target)
            else:
                rs.rig_lights(L, f, r, target)
        else:
            cpos, tgt, lens, w, h, hide, _ = PERSP[v]
            cam.location = cpos
            f, r, u = rs.look(cam, tgt)
            cam.data.type = "PERSP"
            cam.data.lens = lens
            cam.data.sensor_width = 36
            cam.data.clip_start = 0.02
            cam.data.clip_end = 60
            w, h = round(w * o["scale"]), round(h * o["scale"])
            rs.rig_lights(L, f, r, tgt)
            for k in hide:
                objs[k].hide_render = True
        sc.render.resolution_x, sc.render.resolution_y = w, h
        sc.render.resolution_percentage = 100
        sc.render.filepath = os.path.join(out, v + ".png")
        bpy.context.view_layer.update()
        bpy.ops.render.render(write_still=True)
        anchors[v] = dict(w=w, h=h, ppm=PPM * o["scale"] if v in ORTHO else None, points={})
        for name, p in bp.ANCHORS.items():
            c = world_to_camera_view(sc, cam, Vector(p))
            anchors[v]["points"][name] = (round(c.x * w, 1), round((1 - c.y) * h, 1), round(c.z, 3))
        print("rendered", v, w, h, flush=True)
    json.dump(anchors, open(apath, "w"), indent=1)


if __name__ == "__main__":
    main()
