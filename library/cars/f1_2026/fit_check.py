"""Check that the master block character (library/characters/block_character, helmet on) fits the cockpit:
seat it with character_blender.seat_in_car (driver pose, IK hands on the steering-wheel grips), then report any
part that pokes out through the bodywork or whose helmet touches the halo/headrest.

blender -b --factory-startup --python fit_check.py -- [--skin driver_silver_arrow] [--livery silver_arrow] [--render]
-> prints a report; with --render also writes sheet/fit/*.png
"""
import os
import sys
import numpy as np
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "characters", "block_character"))
import blueprint as bp  # noqa: E402
import car_blender  # noqa: E402
import character_blender as ch  # noqa: E402


def arg(name, default):
    a = sys.argv
    return a[a.index(name) + 1] if name in a else default


def surface_points(ob, step=0.008):
    """Points spread over the deformed (posed) surface of a mesh, world space, with each point's polygon index."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    M = np.array(ev.matrix_world)
    co = np.array([v.co for v in me.vertices])
    co = (np.c_[co, np.ones(len(co))] @ M.T)[:, :3]
    pts, pid = [], []
    for p in me.polygons:
        q = co[list(p.vertices)]
        a, b, d = q[0], q[1], q[3]
        nu = max(2, int(np.linalg.norm(b - a) / step) + 1)
        nv = max(2, int(np.linalg.norm(d - a) / step) + 1)
        u, v = np.meshgrid(np.linspace(0.02, 0.98, nu), np.linspace(0.02, 0.98, nv))
        u, v = u.ravel()[:, None], v.ravel()[:, None]
        c = q[2]
        pts.append((1 - u) * (1 - v) * a + u * (1 - v) * b + u * v * c + (1 - u) * v * d)
        pid.append(np.full(len(u), p.index))
    ev.to_mesh_clear()
    return np.concatenate(pts), np.concatenate(pid)


def dominant_bone(ob):
    """Polygon index -> name of the bone that moves it most (layer 1/2 meshes; helmet = head)."""
    names = {g.index: g.name for g in ob.vertex_groups}
    vb = {}
    for v in ob.data.vertices:
        if v.groups:
            g = max(v.groups, key=lambda g: g.weight)
            vb[v.index] = names[g.group]
    return {p.index: vb.get(p.vertices[0], "head") for p in ob.data.polygons}


def main():
    render = "--render" in sys.argv
    skin = arg("--skin", "driver_silver_arrow")
    livery = arg("--livery", "silver_arrow")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    car = car_blender.load_car("car", livery)
    drv = ch.make_character("driver", skin, helmet=True)
    ch.seat_in_car(drv, car)
    bpy.context.view_layer.update()
    d = bp.build(livery)
    filled = d["m"] > 0
    opening = lambda x, y, z: ((np.abs(x) / 0.27) ** 6 + ((y - 0.26) / 0.52) ** 6 <= 1) & (z > 0.48)
    grips = np.array(bp.SEAT["grips"])
    report = {}
    for ob in ch.objects(drv):
        if ob.name.endswith("layer2"):
            continue   # the see-through shell follows layer 1 within 0.25 px
        p, pid = surface_points(ob)
        bone = dominant_bone(ob)
        i = np.floor((p[:, 0] - bp.X0) / bp.VOX).astype(int)
        j = np.floor((p[:, 1] - bp.Y0) / bp.VOX).astype(int)
        k = np.floor((p[:, 2] - bp.Z0) / bp.VOX).astype(int)
        inside = (i >= 0) & (i < bp.NX) & (j >= 0) & (j < bp.NY) & (k >= 0) & (k < bp.NZ)
        solid = np.zeros(len(p), bool)
        solid[inside] = filled[i[inside], j[inside], k[inside]]
        cock = opening(p[:, 0], p[:, 1], p[:, 2])
        near_grip = np.min(np.linalg.norm(p[:, None, :] - grips[None], axis=2), axis=1) < 0.075
        for b in sorted(set(bone.values())):
            sel = np.array([bone[x] == b for x in pid])
            if ob.name.endswith("helmet") or b == "head":
                bad = sel & solid & (p[:, 2] > 0.5)
                what = "touches the halo / headrest / bodywork"
            elif b.startswith("forearm"):
                bad = sel & ~solid & ~cock & ~near_grip       # hands may touch the grips
                what = "pokes out of the bodywork"
            else:
                bad = sel & ~solid & ~cock
                what = "pokes out of the bodywork"
            if bad.any():
                q = p[bad]
                report[f"{ob.name}:{b}"] = (int(bad.sum()), int(sel.sum()), what, q.min(0), q.max(0))
    print("FIT REPORT", skin, "in", livery)
    if not report:
        print("  clean: nothing pokes out, the helmet clears the halo and headrest, hands on the grips")
    for k_, (n, tot, what, lo, hi) in sorted(report.items()):
        print(f"  {k_}: {n}/{tot} surface points {what}  (x {lo[0]:.2f}..{hi[0]:.2f} y {lo[1]:.2f}..{hi[1]:.2f}"
              f" z {lo[2]:.2f}..{hi[2]:.2f})")
    for side in ("L", "R"):
        pb = drv.pose.bones[f"forearm.{side}"]
        hand = drv.matrix_world @ pb.tail
        g = Vector(bp.SEAT["grips"][0 if side == "L" else 1])
        print(f"  hand {side}: {(hand - g).length * 100:.1f} cm from its grip")
    if render:
        import render_sheet as rs
        sc = bpy.context.scene
        sc.render.engine = "CYCLES"
        rs.gpu(sc)
        sc.cycles.samples, sc.cycles.use_denoising = 64, True
        sc.render.film_transparent = True
        sc.view_settings.view_transform, sc.view_settings.look = "AgX", "AgX - Medium High Contrast"
        rs.world()
        L = {"key": rs.area("key", 4.0, 1500), "fill": rs.area("fill", 5.0, 300), "top": rs.area("top", 7.0, 1100),
             "rim": rs.area("rim", 3.0, 900)}
        floor = bpy.data.objects.new("floor", bpy.data.meshes.new("floor"))
        floor.data.from_pydata([(-30, -30, 0), (30, -30, 0), (30, 30, 0), (-30, 30, 0)], [], [(0, 1, 2, 3)])
        sc.collection.objects.link(floor)
        floor.is_shadow_catcher = True
        cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
        sc.collection.objects.link(cam)
        sc.camera = cam
        out = os.path.join(HERE, "sheet", "fit")
        os.makedirs(out, exist_ok=True)
        sc.render.resolution_x, sc.render.resolution_y = 1400, 1000
        hide = [o for o in car.children_recursive if o.type == "MESH" and o.name.startswith("car_body")]
        for name, (cp, tg, lens, cut) in {"fit_front_left": ((-2.2, 2.0, 1.9), (0, 0.15, 0.75), 45, False),
                                          "fit_side": ((-4.0, 0.15, 0.95), (0, 0.15, 0.75), 50, False),
                                          "fit_xray_side": ((-4.0, 0.15, 0.95), (0, 0.15, 0.6), 50, True),
                                          "fit_rear_above": ((-1.2, -2.6, 2.4), (0, 0.15, 0.7), 45, False)}.items():
            for o in hide:
                o.hide_render = cut
            cam.location = cp
            f, r, u = rs.look(cam, tg)
            cam.data.lens = lens
            rs.rig_lights(L, f, r, tg)
            sc.render.filepath = os.path.join(out, name + ".png")
            bpy.ops.render.render(write_still=True)


main()
