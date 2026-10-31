"""Character animation for the blocky film: every frame, each person is rebuilt in a pose that moves with time,
and whatever they hold (tyres, wheel guns, jack levers, the lollipop) is re-placed in their hands.

Motion is continuous (sines and steady drifts, no holds), driven by the pose each person was given in sets.py:
work/reach/talk  hands busy, head nods        gun        wheel-gun rattle in the arms
carry_out        walks the old tyre away       tyre_push  walks the new tyre in
jack_lift        heaves back on the lever      ready      bouncing on their toes
step_back        backs away from the car       go_signal  board arm rising
lead             hand rising to take charge    walk/push  walking forward
anything else    breathing and small head turns
"""
import json, math
import bpy
from mathutils import Vector, Matrix
import voxel
from props import jack_between


def _walk(p, t, speed=1.0, stride=26):
    """Leg and arm swing for walking (speed in steps per second)."""
    a = math.sin(2 * math.pi * speed * t)
    p["legL"] = (stride * a, 4, 12 + 10 * max(0, -a))
    p["legR"] = (-stride * a, 4, 12 + 10 * max(0, a))
    if "armL" not in p or p.get("_free_arms"):
        p["armL"] = (-20 * a, 6, 15)
        p["armR"] = (20 * a, 6, 15)
    return p


def animate(name, base, t, ph):
    """-> (pose, (forward, sideways) offset in metres in the person's own frame).
    Small, slow, continuous movements: just enough to feel alive. Pit crew stay at their stations."""
    p = {k: (list(v) if isinstance(v, (list, tuple)) else v) for k, v in base.items()}
    s = lambda f, a=1.0, o=0.0: a * math.sin(2 * math.pi * f * t + ph + o)
    off = (0.0, 0.0)

    def add(k, i, d):
        v = list(p.get(k, (0, 0, 0)))
        v[i] += d
        p[k] = tuple(v)

    def head(yaw, pitch):
        h = p.get("head", (0, 0))
        p["head"] = (h[0] + yaw, h[1] + pitch)

    if name in ("work", "reach", "reach2", "hold_bag"):  # hands busy, head almost still
        add("armL", 2, s(0.45, 7)); add("armR", 2, s(0.38, 8, 1.3)); add("armR", 0, s(0.3, 4, 0.4))
        head(s(0.2, 2), s(0.25, 1.5, 0.8))
    elif name in ("talk", "watch"):
        add("armR", 2, s(0.35, 8)); head(s(0.18, 3), 0)
    elif name == "gun":  # the wheel gun buzzes in his hands; he stays put
        add("armL", 0, s(9, 1.2)); add("armR", 0, s(9, 1.2, 0.5))
    elif name == "carry_out":  # old tyre eased off the hub: a short, slow step back, still at his station
        off = (-min(0.35, 0.18 * t), 0.0)
    elif name == "tyre_push":  # new tyre offered up to the hub: a short, slow step in
        off = (min(0.25, 0.12 * t), 0.0)
    elif name == "jack_lift":  # leans back on the lever as the nose comes up
        p["lean"] = p.get("lean", -12) - 4 * min(1.0, t / 1.5)
    elif name in ("ready", "brace"):
        p["crouch"] = p.get("crouch", 0) + 0.012 * math.sin(2 * math.pi * 0.8 * t + ph)
    elif name == "step_back":  # only once the car has gone: a slow step away
        off = (-0.25 * t, 0.0)
    elif name == "go_signal":
        add("armR", 0, -30 + min(30, 25 * t))
    elif name == "lead":
        add("armR", 0, -40 + min(40, 35 * t)); head(s(0.2, 2), 0)
    elif name in ("walk", "push"):
        off = ((1.0 if name == "walk" else 0.7) * t, 0.0)
        p = _walk(p, t, 1.5 if name == "walk" else 1.2, 22 if name == "walk" else 16)
        if name == "push":
            p["armL"], p["armR"] = base["armL"], base["armR"]
    else:  # breathing, a little look around
        head(s(0.15, 3), s(0.2, 1))
    return p, off


def obstacles():
    """World boxes hands must stay out of: the car body, cot walls, the baby, the operating table."""
    keys = ("car_mono", "car_pod", "car_fw", "car_rw", "car_floor", "car_airbox", "car_nose", "car_halo",
            "_side", "_end", "_head", "_hat", "_body", "_blanket", "_fold", "table_top", "table_pad", "op_baby")
    out = []
    for ob in bpy.data.objects:
        if ob.type != "MESH" or ob.get("person") or any(p.get("person") for p in ob.parent_recursive):
            continue
        if not any(k in ob.name for k in keys) or ob.name.startswith(("wg", "newtyre", "fjack", "rjack", "lolli")):
            continue
        if "_w" in ob.name and ("car_wf" in ob.name or "car_wr" in ob.name):
            continue
        pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        if (hi - lo).length < 12:
            out.append((lo - Vector((0.03, 0.03, 0.03)), hi + Vector((0.03, 0.03, 0.03))))
    return out


def _inside(p, box):
    lo, hi = box
    return lo.x <= p.x <= hi.x and lo.y <= p.y <= hi.y and lo.z <= p.z <= hi.z


class People:
    """Snapshot of the people in a built shot, re-posed per frame."""

    def __init__(self):
        self.people = []
        for ob in list(bpy.data.objects):
            if ob.get("person") and ob.get("args"):
                a = json.loads(ob["args"])
                self.people.append(dict(name=ob.name, pose_name=ob.get("pose_name", "custom"), **a))
        self.holds = json.loads(bpy.context.scene.get("holds", "[]"))
        bpy.context.view_layer.update()
        self.blocks = obstacles()

    def frame(self, t):
        from voxel import block_person
        from sets import hand_world
        for i, q in enumerate(self.people):
            old = bpy.data.objects.get(q["name"])
            if old:
                for ob in [old] + list(old.children_recursive):
                    bpy.data.objects.remove(ob, do_unlink=True)
            pose, (fwd, side) = animate(q["pose_name"], q["pose"], t, ph=1.7 * i)
            r = math.radians(q["rot"])
            heading = Vector((-math.sin(r), math.cos(r), 0))
            right = Vector((math.cos(r), math.sin(r), 0))
            loc = Vector(q["loc"]) + heading * fwd + right * side
            for attempt in range(16):  # no clipping: step back until both hands are clear of the car, cot, baby, table
                root = block_person(q["name"], tuple(loc), q["rot"], pose, q["outfit"], q["scale"])
                hands = [hand_world(root, k) for k in "LR"]
                if hands[0] is None or not any(_inside(h, b) for h in hands for b in self.blocks):
                    break
                for ob in [root] + list(root.children_recursive):
                    bpy.data.objects.remove(ob, do_unlink=True)
                loc = loc - heading * 0.03
            root["pose_name"] = q["pose_name"]
            voxel.texture_person(root)
        bpy.context.view_layer.update()
        for h in self.holds:
            ob = bpy.data.objects.get(h["obj"])
            root = bpy.data.objects.get(h["person"])
            if root is None:
                continue
            l, r_ = hand_world(root, "L"), hand_world(root, "R")
            if l is None:
                continue
            if h["mode"] == "wheel" and ob:
                d = r_ - l
                ob.location = (l + r_) / 2
                ob.rotation_euler = (0, 0, math.atan2(d.y, d.x))
            elif h["mode"] == "mid" and ob:
                ob.location = (l + r_) / 2
            elif h["mode"] == "hand" and ob:
                ob.location = hand_world(root, h.get("hand", "R"))
            elif h["mode"] == "jack":
                old = bpy.data.objects.get(h["obj"])
                if old:
                    for o in [old] + list(old.children_recursive):
                        bpy.data.objects.remove(o, do_unlink=True)
                g = jack_between(h["obj"], tuple(h["head"]), tuple((l + r_) / 2))
                voxel.texture_boxes([g] + list(g.children_recursive))
