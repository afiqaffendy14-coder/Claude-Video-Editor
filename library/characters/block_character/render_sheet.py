"""Render the views for the master character model sheet (Cycles, GPU) -> sheet/renders/*.png + anchors.json.

blender -b --factory-startup --python render_sheet.py -- [--samples 64] [view ...]
"""
import json
import math
import os
import sys
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
CARS = os.path.join(HERE, "..", "..", "cars", "f1_2026")
sys.path.insert(0, HERE)
sys.path.insert(0, CARS)
import character_blender as ch  # noqa: E402
import template as T  # noqa: E402
import skins as SK  # noqa: E402
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("car_render_sheet", os.path.join(CARS, "render_sheet.py"))
_car_rs = importlib.util.module_from_spec(_spec)   # the car sheet's light/camera helpers
_spec.loader.exec_module(_car_rs)

gpu, world, area, look, rig_lights = _car_rs.gpu, _car_rs.world, _car_rs.area, _car_rs.look, _car_rs.rig_lights
OUT = os.path.join(HERE, "sheet", "renders")
PPM = 900                      # ortho pixels per metre
CZ = 0.79
ORTHO = {"front": (0, 1), "right": (1, 0), "back": (0, -1), "left": (-1, 0)}   # camera direction from the character
POSE_SHOTS = ["idle", "walk", "run", "sit", "wave", "point", "cheer", "think", "shrug", "fist_pump"]
RIG_POSE = dict(arm_L=(0, 38, 0), arm_R=(0, 38, 0), leg_L=(0, 8), leg_R=(0, 8))


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = dict(samples=64, views=[])
    i = 0
    while i < len(a):
        if a[i] == "--samples":
            o["samples"] = int(a[i + 1])
            i += 2
            continue
        o["views"].append(a[i])
        i += 1
    return o


def clear_chars():
    for ob in list(bpy.data.objects):
        if ob.name not in ("floor", "cam", "key", "fill", "top", "rim"):
            bpy.data.objects.remove(ob, do_unlink=True)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)


def setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    print("device", gpu(sc))
    sc.cycles.use_denoising = True
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    world()
    floor = bpy.data.objects.new("floor", bpy.data.meshes.new("floor"))
    floor.data.from_pydata([(-40, -40, 0), (40, -40, 0), (40, 40, 0), (-40, 40, 0)], [], [(0, 1, 2, 3)])
    sc.collection.objects.link(floor)
    floor.is_shadow_catcher = True
    L = {"key": area("key", 3.0, 900), "fill": area("fill", 4.0, 220, (0.92, 0.96, 1.0)),
         "top": area("top", 5.0, 600), "rim": area("rim", 2.5, 650, (1.0, 0.97, 0.92))}
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    return sc, cam, L


def shoot(sc, name, w, h):
    sc.render.resolution_x, sc.render.resolution_y = int(w), int(h)
    sc.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("rendered", name, flush=True)


def ortho(cam, L, d, target, scale, light_scale=1.0):
    target = Vector(target)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = scale
    cam.data.clip_end = 60
    cam.location = target + Vector((d[0], d[1], 0)).normalized() * 12
    f, r, u = look(cam, target)
    rig_lights(L, f, r, target)
    for ob in L.values():
        ob.location = target + (ob.location - target) * light_scale
    return f, r, u


def persp(cam, L, pos, target, lens, light_scale=1.0):
    cam.data.type = "PERSP"
    cam.data.lens = lens
    cam.data.sensor_width = 36
    cam.data.clip_end = 100
    cam.location = pos
    f, r, u = look(cam, target)
    rig_lights(L, f, r, Vector(target))
    for ob in L.values():
        ob.location = Vector(target) + (ob.location - Vector(target)) * light_scale
    return f, r, u


def project_ortho(p, d, target, w, h, scale):
    """World point -> pixel in an ortho view looking along -d."""
    dv = Vector((d[0], d[1], 0)).normalized()
    right = (-dv).cross(Vector((0, 0, 1))).normalized()
    ppm = max(w, h) / scale
    q = Vector(p) - Vector(target)
    return (w / 2 + q.dot(right) * ppm, h / 2 - q.z * ppm)


def joints(root):
    bpy.context.view_layer.update()
    out = {}
    for pb in root.pose.bones:
        out[pb.name] = (list(root.matrix_world @ pb.head), list(root.matrix_world @ pb.tail))
    return out


def main():
    o = args()
    sc, cam, L = setup()
    sc.cycles.samples = o["samples"]
    os.makedirs(OUT, exist_ok=True)
    apath = os.path.join(OUT, "anchors.json")
    A = json.load(open(apath)) if os.path.exists(apath) else {}
    want = lambda v: not o["views"] or v in o["views"] or any(v.startswith(x) for x in o["views"])
    tz = (0, 0, CZ)
    W, H = round(1.0 * PPM), round(1.62 * PPM)

    if any(want(v) for v in ORTHO) or want("three_quarter") or want("back_three_quarter"):
        clear_chars()
        root = ch.make_character("base", "base", pose="stand")
        for v, d in ORTHO.items():
            if want(v):
                ortho(cam, L, d, tz, 1.62)
                shoot(sc, v, W, H)
        if want("three_quarter"):
            persp(cam, L, (1.75, 2.2, 1.15), (0, 0, 0.74), 52)
            shoot(sc, "three_quarter", 1100, 1500)
        if want("back_three_quarter"):
            persp(cam, L, (-1.75, -2.2, 1.35), (0, 0, 0.74), 52)
            shoot(sc, "back_three_quarter", 1100, 1500)

    if want("rig"):
        clear_chars()
        root = ch.make_character("rig", "base", pose=RIG_POSE)
        J = joints(root)
        A["rig"] = {}
        for v, d in (("front", (0, 1)), ("right", (1, 0))):
            ortho(cam, L, d, tz, 1.62)
            shoot(sc, "rig_" + v, W, H)
            A["rig"][v] = {b: [project_ortho(hd, d, tz, W, H, 1.62), project_ortho(tl, d, tz, W, H, 1.62)]
                           for b, (hd, tl) in J.items()}
        # bend bands (px heights) for the overlay
        A["bands"] = {k: p["bend"][0] for k, p in T.parts().items() if "bend" in p}

    if want("layers"):
        for i, (name, kw) in enumerate((("layer1", dict(layer2=False)), ("layer2", dict()),
                                        ("helmet", dict(helmet=True)))):
            clear_chars()
            ch.make_character("drv", "driver_silver_arrow", pose="idle", face="smile" if i < 2 else "neutral", **kw)
            persp(cam, L, (1.95, 2.55, 1.6), (0, 0, 0.9), 60)
            shoot(sc, "layers_" + name, 900, 1000)

    if want("faces"):
        clear_chars()
        n = len(T.EXPRESSIONS)
        sp = 0.5
        for i, e in enumerate(T.EXPRESSIONS):
            ch.make_character(f"f{i}", "base", face=e, location=((i - (n - 1) / 2) * -sp, 0, 0))
        tgt = (0, 0, 1.26)
        ortho(cam, L, (0, 1), tgt, n * sp, light_scale=1.5)
        shoot(sc, "faces", round(n * sp * 800), round(0.6 * 800))
        A["faces"] = dict(n=n, spacing_px=sp * 800, width=round(n * sp * 800), height=round(0.6 * 800))

    if want("poses"):
        for pz in POSE_SHOTS:
            if not want("poses") and not want("pose_" + pz):
                continue
            clear_chars()
            root = ch.make_character("p", "base", pose=pz, face={"cheer": "grin", "fist_pump": "shout",
                                                                  "think": "look_right", "shrug": "worried",
                                                                  "wave": "smile", "run": "angry"}.get(pz, "neutral"))
            if pz == "sit":
                crate = bpy.data.objects.new("crate", bpy.data.meshes.new("crate"))
                x0, x1, y0, y1, z1 = -0.25, 0.25, -0.24, 0.12, 0.18
                crate.data.from_pydata([(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0), (x0, y0, z1), (x1, y0, z1),
                                        (x1, y1, z1), (x0, y1, z1)], [],
                                       [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
                m = bpy.data.materials.new("crate")
                m.use_nodes = True
                m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.16, 0.17, 0.19, 1)
                crate.data.materials.append(m)
                sc.collection.objects.link(crate)
            persp(cam, L, (1.55, 2.45, 1.25), (0, 0.05, 0.84), 40)
            shoot(sc, "pose_" + pz, 760, 1000)

    if want("lineup"):
        clear_chars()
        names = list(SK.SKINS)
        n = len(names)
        sp = 0.9
        faces = ["neutral", "smile", "neutral", "grin", "smile", "smile", "neutral"]
        A["lineup"] = []
        for i, s in enumerate(names):
            x = (i - (n - 1) / 2) * -sp
            ch.make_character(f"s{i}", s, pose="idle", face=faces[i % len(faces)], location=(x, 0, 0))
        persp(cam, L, (0.0, 9.0, 1.55), (0, 0, 0.78), 50, light_scale=1.6)
        cam.data.lens = 50
        w, h = 3600, 1250
        shoot(sc, "lineup", w, h)
        bpy.context.view_layer.update()
        from bpy_extras.object_utils import world_to_camera_view
        for i, s in enumerate(names):
            x = (i - (n - 1) / 2) * -sp
            p = world_to_camera_view(sc, cam, Vector((x, 0, 0)))
            A["lineup"].append(dict(skin=s, title=SK.SKINS[s]["title"], px=p.x * w, py=(1 - p.y) * h))

    if want("in_car"):
        clear_chars()
        import car_blender
        car = car_blender.load_car("car", "silver_arrow")
        drv = ch.make_character("drv", "driver_silver_arrow", helmet=True)
        ch.seat_in_car(drv, car)
        car["steer"] = 0.0
        persp(cam, L, (-2.7, 2.6, 2.3), (0, 0.15, 0.6), 50, light_scale=1.4)
        shoot(sc, "in_car", 1500, 1000)
        persp(cam, L, (-0.95, 1.75, 1.45), (0, 0.15, 0.68), 45, light_scale=1.0)
        shoot(sc, "in_car_close", 1000, 1000)

    json.dump(A, open(apath, "w"), indent=1)


if __name__ == "__main__":
    main()
