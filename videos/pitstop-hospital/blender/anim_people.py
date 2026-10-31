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
    """-> (pose, (forward, sideways) offset in metres in the person's own frame)."""
    p = {k: (list(v) if isinstance(v, (list, tuple)) else v) for k, v in base.items()}
    s = lambda f, a=1.0, o=0.0: a * math.sin(2 * math.pi * f * t + ph + o)
    off = (0.0, 0.0)

    def add(k, i, d):
        v = list(p.get(k, (0, 0, 0)))
        v[i] += d
        p[k] = tuple(v)

    if name in ("work", "reach", "reach2", "hold_bag"):
        add("armL", 2, s(1.1, 16)); add("armR", 2, s(0.9, 18, 1.3)); add("armR", 0, s(0.7, 9, 0.4))
        p["head"] = (p.get("head", (0, 0))[0] + s(0.35, 8), p.get("head", (0, 0))[1] + s(0.6, 5, 0.8))
        p["lean"] = p.get("lean", 0) + s(0.5, 3)
    elif name in ("talk", "watch"):
        add("armR", 2, s(0.8, 20)); add("armR", 0, s(0.5, 10, 0.6))
        p["head"] = (p.get("head", (0, 0))[0] + s(0.3, 12), p.get("head", (0, 0))[1] + s(0.5, 4))
    elif name == "gun":
        add("armL", 0, s(13, 2.5)); add("armR", 0, s(13, 2.5, 0.5)); p["lean"] = p.get("lean", 0) + s(7, 1.5)
    elif name == "carry_out":
        off = (-0.9 * t, 0.0)
        p = _walk(p, t, 1.6, 20)
        p["armL"], p["armR"] = base["armL"], base["armR"]
    elif name == "tyre_push":
        off = (0.45 * t, 0.0)
        p = _walk(p, t, 1.4, 16)
        p["armL"], p["armR"] = base["armL"], base["armR"]
    elif name == "jack_lift":
        p["lean"] = -4 - 12 * min(1.0, t / 1.2) + s(1.5, 1.5)
    elif name == "ready":
        p["crouch"] = p.get("crouch", 0) + 0.03 * math.sin(2 * math.pi * 2.2 * t + ph)
    elif name == "step_back":
        off = (-0.6 * t, 0.0)
        p = _walk(p, t, 1.4, 18)
    elif name == "go_signal":
        add("armR", 0, -95 + min(95, 140 * t))
    elif name == "lead":
        add("armR", 0, -80 + min(80, 110 * t)); p["head"] = (s(0.4, 10), 5)
    elif name in ("walk", "push"):
        off = ((1.15 if name == "walk" else 0.8) * t, 0.0)
        p = _walk(p, t, 1.7 if name == "walk" else 1.3, 26 if name == "walk" else 18)
        if name == "push":
            p["armL"], p["armR"] = base["armL"], base["armR"]
    else:  # breathing, small head turns
        p["head"] = (p.get("head", (0, 0))[0] + s(0.25, 6), p.get("head", (0, 0))[1] + s(0.4, 2))
    return p, off


class People:
    """Snapshot of the people in a built shot, re-posed per frame."""

    def __init__(self):
        self.people = []
        for ob in list(bpy.data.objects):
            if ob.get("person") and ob.get("args"):
                a = json.loads(ob["args"])
                self.people.append(dict(name=ob.name, pose_name=ob.get("pose_name", "custom"), **a))
        self.holds = json.loads(bpy.context.scene.get("holds", "[]"))

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
            root = block_person(q["name"], tuple(loc), q["rot"], pose, q["outfit"], q["scale"])
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
