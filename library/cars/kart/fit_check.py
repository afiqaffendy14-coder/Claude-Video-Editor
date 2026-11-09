"""Check that the master block character (helmet on) fits the kart: seat it with character_blender.seat_in_car
(kart pose, IK hands on the steering-wheel grips), then report every part of the driver that sits inside the
kart's voxels (seat, wheel, column, tank, engine, radiator, bodywork) and how far the hands are from the grips.

blender -b --factory-startup --python fit_check.py -- [--skin driver_silver_arrow] [--livery silver_arrow]
        [--steer 0] [--render]
-> prints a report; with --render also writes sheet/fit/*.png
"""
import importlib.util
import os
import sys
import numpy as np
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "characters", "block_character"))
import kart_blueprint as bp  # noqa: E402
import kart_blender  # noqa: E402
import character_blender as ch  # noqa: E402

_sp = importlib.util.spec_from_file_location("f1_render_sheet", os.path.join(HERE, "..", "f1_2026", "render_sheet.py"))
rs = importlib.util.module_from_spec(_sp)   # studio helpers (lights, world, GPU) shared with the F1 sheet
_sp.loader.exec_module(rs)


def arg(name, default):
    a = sys.argv
    return a[a.index(name) + 1] if name in a else default


def surface_points(ob, step=0.006, inset=0.003):
    """Points over the deformed surface of a mesh (world space), pulled `inset` inside, with polygon indices."""
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
        n = np.cross(b - a, d - a)
        n = n / (np.linalg.norm(n) + 1e-12)
        nu = max(2, int(np.linalg.norm(b - a) / step) + 1)
        nv = max(2, int(np.linalg.norm(d - a) / step) + 1)
        u, v = np.meshgrid(np.linspace(0.02, 0.98, nu), np.linspace(0.02, 0.98, nv))
        u, v = u.ravel()[:, None], v.ravel()[:, None]
        c = q[2]
        pts.append((1 - u) * (1 - v) * a + u * (1 - v) * b + u * v * c + (1 - u) * v * d - n * inset)
        pid.append(np.full(len(u), p.index))
    ev.to_mesh_clear()
    return np.concatenate(pts), np.concatenate(pid)


def dominant_bone(ob):
    names = {g.index: g.name for g in ob.vertex_groups}
    vb = {}
    for v in ob.data.vertices:
        if v.groups:
            g = max(v.groups, key=lambda g: g.weight)
            vb[v.index] = names[g.group]
    return {p.index: vb.get(p.vertices[0], "head") for p in ob.data.polygons}


def check(kart, drv, livery):
    """{part:bone: (points inside, total, kart materials hit, bbox)} for the current steer angle."""
    bpy.context.view_layer.update()
    d = bp.build(livery)
    m = d["m"].copy()
    steer = kart["steer"]
    # the voxel grid is the kart at steer 0: test the steering wheel by un-turning the points instead
    grips = np.array([np.array(ob.matrix_world.translation) for ob in bpy.data.objects
                      if ob.name.startswith(drv.name + "_grip.")])
    report = {}
    for ob in ch.objects(drv):
        if ob.name.endswith("layer2"):
            continue
        p, pid = surface_points(ob)
        bone = dominant_bone(ob)
        i = np.floor((p[:, 0] - bp.X0) / bp.VOX).astype(int)
        j = np.floor((p[:, 1] - bp.Y0) / bp.VOX).astype(int)
        k = np.floor((p[:, 2] - bp.Z0) / bp.VOX).astype(int)
        inside = (i >= 0) & (i < bp.NX) & (j >= 0) & (j < bp.NY) & (k >= 0) & (k < bp.NZ)
        hit = np.zeros(len(p), np.uint8)
        hit[inside] = m[i[inside], j[inside], k[inside]]
        if steer:
            hit[d["part"][np.clip(i, 0, bp.NX - 1), np.clip(j, 0, bp.NY - 1), np.clip(k, 0, bp.NZ - 1)]
                == bp.STEER] = 0
        prt = np.zeros(len(p), np.uint8)
        prt[inside] = d["part"][i[inside], j[inside], k[inside]]
        on_rim = (prt == bp.STEER) & np.isin(hit, [bp.GRIP, bp.PIN, bp.ALU, bp.TAPE])  # hands wrap rim, spokes, tape
        near_grip = (np.min(np.linalg.norm(p[:, None, :] - grips[None], axis=2), axis=1) < 0.14) & on_rim
        for b in sorted(set(bone.values())):
            sel = np.array([bone[x] == b for x in pid])
            bad = sel & (hit > 0)
            if b.startswith("forearm"):
                bad &= ~near_grip
            if bad.any():
                mats = sorted({bp.MATS[x]["name"] for x in hit[bad].tolist()})
                q = p[bad]
                report[f"{ob.name.split('_')[-1]}:{b}"] = (int(bad.sum()), int(sel.sum()), mats, q.min(0), q.max(0))
    return report


def main():
    render = "--render" in sys.argv
    skin = arg("--skin", "driver_silver_arrow")
    livery = arg("--livery", "silver_arrow")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    kart = kart_blender.make_kart("kart", livery)[0]
    drv = ch.make_character("driver", skin, helmet=True)
    ch.seat_in_car(drv, kart)
    kart["steer"] = float(arg("--steer", 0))
    report = check(kart, drv, livery)
    print("FIT REPORT", skin, "in kart", livery, "steer", kart["steer"])
    if not report:
        print("  clean: no part of the driver is inside the kart")
    for k_, (n, tot, mats, lo, hi) in sorted(report.items()):
        print(f"  {k_}: {n}/{tot} points inside {mats}  (x {lo[0]:.3f}..{hi[0]:.3f} y {lo[1]:.3f}..{hi[1]:.3f}"
              f" z {lo[2]:.3f}..{hi[2]:.3f})")
    for side in ("L", "R"):
        pb = drv.pose.bones[f"forearm.{side}"]
        hand = drv.matrix_world @ pb.tail
        g = bpy.data.objects[f"driver_grip.{side}"].matrix_world.translation
        print(f"  hand {side}: {(hand - g).length * 100:.1f} cm from its grip")
    for nm in ("shin.L", "shin.R", "thigh.L", "head"):
        pb = drv.pose.bones[nm]
        print(f"  {nm}: head {tuple(round(x, 3) for x in drv.matrix_world @ pb.head)}"
              f" tail {tuple(round(x, 3) for x in drv.matrix_world @ pb.tail)}")
    if render:
        sc = bpy.context.scene
        sc.render.engine = "CYCLES"
        rs.gpu(sc)
        sc.cycles.samples, sc.cycles.use_denoising = 48, True
        sc.render.film_transparent = True
        sc.view_settings.view_transform, sc.view_settings.look = "AgX", "AgX - Medium High Contrast"
        rs.world()
        L = {"key": rs.area("key", 3.0, 700), "fill": rs.area("fill", 4.0, 150), "top": rs.area("top", 5.0, 500),
             "rim": rs.area("rim", 2.5, 400)}
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
        views = {"fit_front_left": ((-1.6, 1.9, 1.3), (0, 0.0, 0.40), 40),
                 "fit_side": ((-3.2, 0.0, 0.55), (0, 0.0, 0.42), 50),
                 "fit_front": ((0.0, 3.2, 0.70), (0, 0.0, 0.40), 50),
                 "fit_top": ((0.0, 0.0, 3.4), (0, 0.0, 0.3), 50),
                 "fit_rear_above": ((1.3, -1.9, 1.5), (0, 0.0, 0.40), 40)}
        for name, (cp, tg, lens) in views.items():
            if views and len(sys.argv) and "--only" in sys.argv and name not in arg("--only", ""):
                continue
            cam.location = cp
            f, r, u = rs.look(cam, tg, (0, 1, 0) if name == "fit_top" else (0, 0, 1))
            cam.data.lens = lens
            rs.rig_lights(L, f, r, tg)
            sc.render.filepath = os.path.join(out, name + ".png")
            bpy.ops.render.render(write_still=True)


main()
