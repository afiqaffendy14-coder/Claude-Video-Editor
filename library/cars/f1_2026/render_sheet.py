"""Render every view of the model sheet from the blueprint (same car, same scale in every orthographic view).

blender -b --factory-startup --python render_sheet.py -- [--scale 0.5] [--samples 96] [view ...]
-> sheet/renders/<view>.png (transparent, shadow on the floor) and sheet/renders/anchors.json
"""
import json
import math
import os
import sys
import bpy
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blueprint as bp  # noqa: E402
import car_blender  # noqa: E402

PPM = 480  # pixels per metre in every orthographic view
CY, CZ = 0.09, 0.515  # centre of the car's bounding box (y, z)
ORTHO = {  # name: (camera direction, up, width m, height m)
    "side_left": ((1, 0, 0), (0, 0, 1), 5.72, 1.13),
    "side_right": ((-1, 0, 0), (0, 0, 1), 5.72, 1.13),
    "front": ((0, -1, 0), (0, 0, 1), 2.19, 1.13),
    "rear": ((0, 1, 0), (0, 0, 1), 2.19, 1.13),
    "top": ((0, 0, -1), (1, 0, 0), 5.72, 2.19),
    "bottom": ((0, 0, 1), (-1, 0, 0), 5.72, 2.19),
}
PERSP = {  # name: (camera, target, lens, w, h, hidden parts)
    "q_front_left": ((-5.3, 6.6, 2.9), (0.0, 0.35, 0.35), 70, 1800, 1050, ()),
    "q_rear_left": ((-5.6, -6.4, 2.7), (0.0, -0.3, 0.38), 70, 1800, 1050, ()),
    "c_cockpit": ((-2.0, 1.45, 1.95), (0.0, 0.22, 0.76), 50, 1600, 1200, ()),
    "c_front_wing": ((-1.75, 4.15, 0.80), (-0.30, 2.45, 0.19), 50, 1600, 1200, ()),
    "c_sidepod": ((-2.7, 1.25, 1.35), (-0.42, -0.35, 0.45), 50, 1600, 1200, ()),
    "c_rear_wing": ((-1.9, -4.55, 0.85), (0.0, -2.28, 0.55), 50, 1600, 1200, ()),
    "c_wheel": ((-2.25, 2.55, 0.62), (-0.81, 1.69, 0.36), 60, 1600, 1200, ()),
    "c_brake": ((-2.0, 2.45, 0.85), (-0.74, 1.69, 0.36), 60, 1600, 1200, ("tyre_FL", "rim_FL")),
}


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    o = dict(scale=1.0, samples=96, views=[], livery="silver_arrow")
    i = 0
    while i < len(a):
        if a[i] == "--scale":
            o["scale"] = float(a[i + 1]); i += 2
        elif a[i] == "--livery":
            o["livery"] = a[i + 1]; i += 2
        elif a[i] == "--samples":
            o["samples"] = int(a[i + 1]); i += 2
        else:
            o["views"].append(a[i]); i += 1
    return o


def look(ob, target, up=(0, 0, 1)):
    f = (Vector(target) - ob.location).normalized()
    r = f.cross(Vector(up)).normalized()
    u = r.cross(f)
    ob.rotation_euler = Matrix((r, u, -f)).transposed().to_euler()
    return f, r, u


def gpu(sc):
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = kind
            prefs.get_devices()
        except (TypeError, ValueError):
            continue
        if [d for d in prefs.devices if d.type == kind]:
            for d in prefs.devices:
                d.use = d.type == kind
            sc.cycles.device = "GPU"
            return kind
    return "CPU"


def world():
    w = bpy.data.worlds.new("studio")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = -0.3, 0.9
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (0.05, 0.055, 0.06, 1)
    mix.inputs["B"].default_value = (0.75, 0.77, 0.8, 1)
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.35
    return mix


def area(name, size, power, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.size, ld.energy, ld.color = size, power, color
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def rig_lights(L, f, r, target):
    t = Vector(target)
    f, r = Vector(f), Vector(r)
    up = Vector((0, 0, 1)) if abs(f.z) < 0.9 else Vector((1, 0, 0))
    place = {
        "key": t - f * 5 - r * 3.5 + up * 4.5,
        "fill": t - f * 5 + r * 4.5 + up * 1.2,
        "top": t + Vector((0, 0, 6)) if abs(f.z) < 0.9 else t - f * 6,
        "rim": t + f * 5 + up * 3.5 - r * 1.5,
    }
    for k, ob in L.items():
        ob.location = place[k]
        look(ob, t, (0, 1, 0) if k == "top" else (0, 0, 1))


def main():
    o = args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    print("device", gpu(sc))
    sc.cycles.samples = o["samples"]
    sc.cycles.use_denoising = True
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    world()
    root, objs = car_blender.make_car("w17", livery=o["livery"], compound="medium")
    floor = bpy.data.objects.new("floor", bpy.data.meshes.new("floor"))
    floor.data.from_pydata([(-30, -30, 0), (30, -30, 0), (30, 30, 0), (-30, 30, 0)], [], [(0, 1, 2, 3)])
    sc.collection.objects.link(floor)
    floor.is_shadow_catcher = True
    L = {"key": area("key", 4.0, 1500), "fill": area("fill", 5.0, 300, (0.92, 0.96, 1.0)),
         "top": area("top", 7.0, 1100), "rim": area("rim", 3.0, 900, (0.85, 1.0, 0.97))}
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    out = os.path.join(HERE, "sheet", o["livery"], "renders")
    os.makedirs(out, exist_ok=True)
    apath = os.path.join(out, "anchors.json")
    anchors = json.load(open(apath)) if os.path.exists(apath) else {}
    views = o["views"] or list(ORTHO) + list(PERSP)
    for v in views:
        for ob in objs.values():
            ob.hide_render = False
        floor.hide_render = v == "bottom"
        if v in ORTHO:
            d, up, wm, hm = ORTHO[v]
            target = Vector((0, CY, CZ))
            cam.location = target - Vector(d) * 12
            f, r, u = look(cam, target, up)
            cam.data.type = "ORTHO"
            cam.data.ortho_scale = max(wm, hm)
            cam.data.clip_end = 50
            w, h = round(wm * PPM * o["scale"]), round(hm * PPM * o["scale"])
            if v == "bottom":
                for k, ob in L.items():
                    ob.location = target + Vector((0, 0, -5)) + {"key": Vector((-2, 2, 0)), "fill": Vector((2, -2, 1)),
                                                                  "top": Vector((0, 0, -1)), "rim": Vector((0, 4, 3))}[k]
                    ob.data.energy *= 0.45
                    look(ob, target)
            else:
                rig_lights(L, f, r, target)
        else:
            cpos, tgt, lens, w, h, hide = PERSP[v]
            cam.location = cpos
            f, r, u = look(cam, tgt)
            cam.data.type = "PERSP"
            cam.data.lens = lens
            cam.data.sensor_width = 36
            cam.data.clip_end = 100
            w, h = round(w * o["scale"]), round(h * o["scale"])
            rig_lights(L, f, r, tgt)
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
