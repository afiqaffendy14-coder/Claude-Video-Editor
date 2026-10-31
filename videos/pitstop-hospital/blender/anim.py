"""Animated render: each shot's storyboard framing becomes one continuous camera move at constant speed
(no easing, so the camera never settles or stops), passing through the storyboard framing at mid-shot.

Run: .venv-blender/bin/python anim.py <out_dir> <w> <h> <samples> <fps> <shot ids...>
     -> <out_dir>/f00000.png ... numbered by the film's own frame index (t * fps)
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from mathutils import Vector, Matrix
import lib
from lib import reset, setup_render, render, look_at
import shots

# per-shot moves, applied around a pivot `d` metres in front of the camera; u runs -0.5 .. +0.5 over the shot
#   push: metres along the view   truck: metres sideways   crane: metres up (keeps aim)
#   orbit: degrees around the pivot's vertical axis   spin: degrees of roll drift   d: pivot distance
MOVES = {
    1: dict(push=0.28, orbit=7, spin=-3, d=1.55),
    2: dict(push=1.2, spin=12, d=8.0),
    3: dict(crane=1.6, push=3.0, d=25.0),
    4: dict(orbit=-20, push=0.25, d=2.25),
    5: dict(push=0.32, truck=0.12, spin=2, d=1.1),
    6: dict(push=1.4, d=10.0, travel=(0, 0.7, 0)),
    7: dict(push=0.3, d=2.0, travel=(0, 0.7, 0), follow=True),
    8: dict(push=0.12, orbit=8, d=0.5),
    9: dict(spin=8, push=0.2, d=1.2),
    10: dict(truck=0.2, d=2.5, travel=(0, 0.7, 0), follow=True),
    11: dict(spin=-10, push=0.6, d=4.6),
    12: dict(orbit=10, push=0.2, d=1.5),
    13: dict(orbit=-6, push=0.3, d=1.35),
    14: dict(push=0.5, d=4.0),
    15: dict(push=0.5, d=6.0),
    16: dict(orbit=10, d=7.0),
    17: dict(push=0.3, orbit=6, d=2.0),
    18: dict(push=0.3, orbit=-6, d=2.0),
    19: dict(push=0.6, d=5.0),
    20: dict(push=0.12, d=0.5),
    21: dict(push=0.4, d=5.0),
    22: dict(push=0.25, d=1.4),
    23: dict(push=0.15, d=3.3),
    24: dict(orbit=8, push=0.2, d=2.0),
    25: dict(push=0.3, d=2.2),
    26: dict(spin=10, push=0.5, d=4.6),
    27: dict(spin=-6, push=0.15, d=1.1),
    28: dict(truck=0.08, push=0.08, d=0.5),
    29: dict(orbit=-8, push=0.2, d=2.0),
    30: dict(push=0.6, d=4.7),
    31: dict(push=0.5, d=3.3),
    32: dict(push=0.4, d=7.0),
    33: dict(push=0.8, d=7.0),
    34: dict(push=0.1, orbit=6, d=0.5),
    35: dict(push=0.3, orbit=-6, spin=2, d=1.95),
}

TRAVELLERS = ("cot", "cor_vent", "cor_iv")  # corridor props that roll along with the team


def shot_props(n, t, dur, start):
    """Things that move in a shot besides people and camera: the car arriving/leaving, the falling syringe."""
    if n == 15 and "car" in bpy.data.objects:  # rolls into the box, slowing down
        k = min(1.0, t / dur)
        bpy.data.objects["car"].location.y = start["car"][1] - 1.6 + 1.6 * (1 - (1 - k) ** 2)
    if n == 32 and "car" in bpy.data.objects:  # pulls away, speeding up
        c = bpy.data.objects["car"]
        h = Vector((-math.sin(c.rotation_euler.z), math.cos(c.rotation_euler.z), 0))
        c.location = Vector(start["car"]) + h * (1.2 * t + 1.6 * t * t)
    if n == 13:  # the syringe tumbles to the floor (slowed down)
        for nm in ("syr_barrel", "syr_plunger", "syr_tip"):
            ob = bpy.data.objects.get(nm)
            if ob:
                z0 = start[nm][2]
                ob.location.z = max(0.03, z0 - 0.55 * t * t)
                ob.rotation_euler.x = start[nm + "_rx"] + 2.2 * t


def camera_path(cam, mv):
    """Return f(u) -> (location, pivot, roll) for this shot's move."""
    m0 = cam.matrix_world.copy()
    loc0 = m0.translation.copy()
    fwd = -(m0.to_3x3() @ Vector((0, 0, 1))).normalized()
    right = (m0.to_3x3() @ Vector((1, 0, 0))).normalized()
    up_cam = (m0.to_3x3() @ Vector((0, 1, 0))).normalized()
    d = mv.get("d", cam.data.dof.focus_distance if cam.data.dof.use_dof else 3.0)
    pivot0 = loc0 + fwd * d
    roll0 = bpy.context.scene.get("cam_roll", 0.0)  # the storyboard's tilt, as given to camera()
    straight_down = abs(fwd.z) > 0.97

    def at(u):
        loc, pivot = loc0.copy(), pivot0.copy()
        if mv.get("orbit") and not straight_down:
            a = math.radians(mv["orbit"] * u)
            rel = loc - pivot
            rel = Matrix.Rotation(a, 3, "Z") @ rel
            loc = pivot + rel
        f = (pivot - loc).normalized()
        r = Vector((f.y, -f.x, 0)).normalized() if not straight_down else right
        loc += f * mv.get("push", 0) * u
        pivot += f * mv.get("push", 0) * u * 0.0  # aim point stays put: the push closes in on it
        loc += r * mv.get("truck", 0) * u
        pivot += r * mv.get("truck", 0) * u
        loc.z += mv.get("crane", 0) * u
        return loc, pivot, roll0 + mv.get("spin", 0) * u

    return at, straight_down, m0


def ecg_scroll(t):
    """Scroll the monitor trace so the heart line runs across the screen."""
    for m in bpy.data.materials:
        if m.name.startswith("px_custom_ecg"):
            mp = next(n for n in m.node_tree.nodes if n.type == "MAPPING")
            mp.inputs["Location"].default_value[0] = 0.5 + (t * 0.45) % 1.0


def main():
    out, w, h, spp, fps = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    ids = [int(a) for a in sys.argv[6:]]
    os.makedirs(out, exist_ok=True)
    table = {n: (t0, t1, b) for n, t0, t1, b, _ in shots.SHOTS}
    for n in ids:
        t0, t1, b = table[n]
        reset()
        setup_render(w, h, spp, "/tmp/unused.png")
        sc = bpy.context.scene
        sc.cycles.use_adaptive_sampling = True
        sc.render.use_persistent_data = True  # keep the scene's BVH between frames: only the camera moves
        sc.cycles.max_bounces, sc.cycles.diffuse_bounces, sc.cycles.glossy_bounces = 4, 2, 1
        shots.build(b)
        cam = sc.camera
        at, straight_down, m0 = camera_path(cam, MOVES.get(n, dict(push=0.3)))
        import anim_people
        people = anim_people.People()
        mv = MOVES.get(n, dict(push=0.3))
        travel = Vector(mv.get("travel", (0, 0, 0)))
        start = {}
        for nm in ("car", "syr_barrel", "syr_plunger", "syr_tip") + TRAVELLERS:
            ob = bpy.data.objects.get(nm)
            if ob:
                start[nm] = tuple(ob.location)
                start[nm + "_rx"] = ob.rotation_euler.x
        f0, f1 = math.ceil(t0 * fps - 1e-6), math.ceil(t1 * fps - 1e-6)
        for f in range(f0, f1):
            path = os.path.join(out, f"f{f:05d}.png")
            if os.path.exists(path):
                continue
            t = f / fps
            u = (t - t0) / (t1 - t0) - 0.5
            loc, pivot, roll = at(u)
            if mv.get("follow"):  # tracking shot: the camera travels with the team
                loc = loc + travel * (t - t0)
                pivot = pivot + travel * (t - t0)
            if straight_down:  # top-down: drop straight in, spin around the view axis
                cam.matrix_world = Matrix.Translation(loc) @ (Matrix.Rotation(math.radians(roll), 4, "Z") @ m0.to_3x3().to_4x4())
                cam.location = loc
            else:
                cam.location = loc
                look_at(cam, pivot, roll)
            ecg_scroll(t)
            people.frame(t - t0, travel if travel.length else None)
            for nm in TRAVELLERS:
                ob = bpy.data.objects.get(nm)
                if ob and travel.length:
                    ob.location = Vector(start[nm]) + travel * (t - t0)
            shot_props(n, t - t0, t1 - t0, start)
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True)
        print(f"ANIM shot {n} frames {f0}-{f1 - 1}", flush=True)


if __name__ == "__main__":
    main()
