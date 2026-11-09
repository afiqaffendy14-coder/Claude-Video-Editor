"""EEVEE review clips of the saved assets (the same engine the shorts render with).

blender -b --factory-startup --python showcase.py -- turntable|rig|lineup [--preview]
-> sheet/showcase/<mode>/####.png
  turntable: the silver car turning 360 degrees on a studio floor
  rig:       close on the front-left wheel: steering sweeps left and right while the car rolls (bake_roll)
  lineup:    all four liveries side by side, slow dolly
"""
import math
import os
import sys
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import car_blender as car  # noqa: E402
import render_sheet as rs  # noqa: E402

FPS = 30


def eevee(sc, preview):
    ids = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in ids else "BLENDER_EEVEE"
    e = sc.eevee
    for attr, val in (("taa_render_samples", 16 if preview else 48), ("use_shadows", True), ("shadow_ray_count", 2),
                      ("shadow_step_count", 8), ("use_raytracing", True), ("ray_tracing_method", "SCREEN"),
                      ("use_gtao", True), ("fast_gi_method", "GLOBAL_ILLUMINATION")):
        if hasattr(e, attr):
            try:
                setattr(e, attr, val)
            except (TypeError, ValueError):
                pass
    sc.view_settings.view_transform, sc.view_settings.look = "AgX", "AgX - Medium High Contrast"
    sc.render.fps = FPS


def studio(sc):
    rs.world()
    fl = bpy.data.objects.new("floor", bpy.data.meshes.new("floor"))
    fl.data.from_pydata([(-300, -300, 0), (300, -300, 0), (300, 300, 0), (-300, 300, 0)], [], [(0, 1, 2, 3)])
    m = bpy.data.materials.new("studio_floor")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.32, 0.33, 0.35, 1)
    b.inputs["Roughness"].default_value = 0.45
    fl.data.materials.append(m)
    sc.collection.objects.link(fl)
    L = {"key": rs.area("key", 4.0, 1500), "fill": rs.area("fill", 5.0, 350), "top": rs.area("top", 7.0, 1100),
         "rim": rs.area("rim", 3.0, 1000)}
    return L


def camera(sc, loc, target, lens):
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.location = loc
    cam.data.lens = lens
    rs.look(cam, target)
    return cam


def main():
    a = sys.argv[sys.argv.index("--") + 1:]
    mode, preview = a[0], "--preview" in a
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    eevee(sc, preview)
    L = studio(sc)
    out = os.path.join(HERE, "sheet", "showcase", mode)
    os.makedirs(out, exist_ok=True)
    sc.render.filepath = os.path.join(out, "")
    sc.render.image_settings.file_format = "PNG"
    sc.render.resolution_x = sc.render.resolution_y = 1080
    if mode == "turntable":
        root = car.load_car("hero", "silver_arrow")
        n = 6 * FPS
        sc.frame_start, sc.frame_end = 1, n
        root.rotation_euler.z = 0
        root.keyframe_insert("rotation_euler", index=2, frame=1)
        root.rotation_euler.z = 2 * math.pi
        root.keyframe_insert("rotation_euler", index=2, frame=n + 1)
        for fc in root.animation_data.action.fcurves if hasattr(root.animation_data.action, "fcurves") else []:
            for k in fc.keyframe_points:
                k.interpolation = "LINEAR"
        cam = camera(sc, (-6.2, 6.2, 2.6), (0, 0, 0.42), 55)
        f, r, u = rs.look(cam, (0, 0, 0.42))
        rs.rig_lights(L, f, r, Vector((0, 0, 0.42)))
    elif mode == "rig":
        root = car.load_car("hero", "silver_arrow")
        n = 4 * FPS
        sc.frame_start, sc.frame_end = 1, n
        for fr in range(1, n + 1):
            t = (fr - 1) / FPS
            root["steer"] = 22 * math.sin(2 * math.pi * t / 2.0)
            root.keyframe_insert('["steer"]', frame=fr)
            root.location.y = 1.2 * t                       # creeping forward 1.2 m/s
            root.keyframe_insert("location", index=1, frame=fr)
        car.bake_roll(root, 1, n)
        cam = camera(sc, (-2.9, 4.9, 1.9), (-0.35, 1.7, 0.42), 35)
        cam.parent = root                      # camera rides with the car (root-local position)
        cam.matrix_parent_inverse.identity()
        f, r, u = rs.look(cam, (-0.35, 1.7, 0.42))
        rs.rig_lights(L, f, r, Vector((-0.35, 1.7, 0.42)))
        for ob in L.values():
            ob.parent = root
            ob.matrix_parent_inverse.identity()
    elif mode == "lineup":
        liveries = ["silver_arrow", "rosso", "papaya", "midnight"]
        for i, lv in enumerate(liveries):
            r_ = car.load_car(lv, lv)
            r_.location = ((i - 1.5) * 3.3, -i * 1.6, 0)
            r_.rotation_euler.z = math.radians(-28)
        n = 5 * FPS
        sc.frame_start, sc.frame_end = 1, n
        cam = camera(sc, (-8.5, 8.5, 3.6), (0, -2.4, 0.4), 38)
        cam.keyframe_insert("location", frame=1)
        cam.location = (-5.5, 10.4, 2.8)
        cam.keyframe_insert("location", frame=n)
        tgt = bpy.data.objects.new("tgt", None)
        sc.collection.objects.link(tgt)
        tgt.location = (0, -2.4, 0.4)
        c = cam.constraints.new("TRACK_TO")
        c.target, c.track_axis, c.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
        f = (Vector((0, -1.2, 0.4)) - Vector((-6, 8.5, 3))).normalized()
        rs.rig_lights(L, f, f.cross(Vector((0, 0, 1))).normalized(), Vector((0, -1.2, 0.4)))
        for ob in L.values():
            ob.data.energy *= 1.6
            ob.data.size *= 2.0
    if preview:
        sc.frame_step = 3
    bpy.ops.render.render(animation=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, f"{mode}.blend"))


main()
