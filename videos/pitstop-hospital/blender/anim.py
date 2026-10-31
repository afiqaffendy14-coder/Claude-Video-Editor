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
    2: dict(push=2.2, spin=24, d=8.0),
    3: dict(crane=1.6, push=3.0, d=25.0),
    4: dict(orbit=-20, push=0.25, d=2.25),
    5: dict(push=0.32, truck=0.12, spin=2, d=1.1),
}


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
        f0, f1 = math.ceil(t0 * fps - 1e-6), math.ceil(t1 * fps - 1e-6)
        for f in range(f0, f1):
            path = os.path.join(out, f"f{f:05d}.png")
            if os.path.exists(path):
                continue
            t = f / fps
            u = (t - t0) / (t1 - t0) - 0.5
            loc, pivot, roll = at(u)
            if straight_down:  # top-down: drop straight in, spin around the view axis
                cam.matrix_world = Matrix.Translation(loc) @ (Matrix.Rotation(math.radians(roll), 4, "Z") @ m0.to_3x3().to_4x4())
                cam.location = loc
            else:
                cam.location = loc
                look_at(cam, pivot, roll)
            ecg_scroll(t)
            people.frame(t - t0)
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True)
        print(f"ANIM shot {n} frames {f0}-{f1 - 1}", flush=True)


if __name__ == "__main__":
    main()
