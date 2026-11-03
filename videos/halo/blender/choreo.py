"""Choreography: turns each shot's static storyboard cast into rigged characters and keyframes them.

Every character is driven by a per-frame function (sampled on every frame, so motion is exact and continuous):
  root position/heading, crouch (hips drop with feet planted), spine lean/twist, head, both wrists, both ankles.
Feet only move during planned steps (planted otherwise: no sliding). Hands either follow a gripped prop or move
relative to the body. Motions use smooth curves with anticipation/follow-through; nothing ever snaps to a stop at
a cut. Loop: shot 35 is the 1.9 s that come right before shot 1 (same set, same camera path, same clock), so the
end of the film runs straight back into the start.
"""
import math, random
import bpy
from mathutils import Vector, Matrix, Euler
import rig

V = Vector
FPS = 30


# ---------------------------------------------------------------- curves
def sstep(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def ease(t, a, b):
    """0 -> 1 between times a and b, smooth (zero speed at the ends of the action, not at the cut)."""
    return sstep((t - a) / (b - a)) if b > a else float(t >= b)


def overshoot(t, a, b, amount=0.08):
    """0 -> 1 with a small overshoot and settle (follow-through)."""
    x = min(1.0, max(0.0, (t - a) / (b - a)))
    return 1 - (1 - x) ** 3 * math.cos(x * math.pi * 1.0) + amount * math.sin(x * math.pi) * (1 - x) * 4 * x


def wob(t, f, a, ph=0.0):
    return a * math.sin(2 * math.pi * f * t + ph)


# ---------------------------------------------------------------- performer
class Performer:
    """One rigged character and the function that poses it at time t (seconds, shot-local)."""

    def __init__(self, actor, base, seed):
        self.a = actor
        self.base = base  # dict(loc, rot, crouch, lean, twist, head)
        self.rnd = random.Random(seed)
        self.ph = self.rnd.uniform(0, 6.28)
        arm = actor.arm
        bpy.context.view_layer.update()
        inv = arm.matrix_world.inverted()
        self.hand_local = {k: inv @ actor.hand[k].matrix_world.translation for k in "LR"}
        # hands given relative to the body ride on the chest (or the head): they follow crouch, lean, twist and the
        # idle sway instead of staying fixed over the feet while the body moves under them
        self.scale = arm.scale.x
        bones = arm.data.bones
        self.spine_rest = bones["spine"].matrix_local.copy()
        self.head_rest = bones["head"].matrix_local.copy()
        head_c = self.head_rest.translation + V((0, 0, 0.18))
        self.hand_kind = {k: "head" if (self.hand_local[k] - head_c).length < 0.3 else "local" for k in "LR"}
        self.foot_world = {k: actor.foot[k].matrix_world.translation.copy() for k in "LR"}
        self.gripped = {k: actor.hand[k].parent is not None for k in "LR"}
        self.path = None  # optional: t -> (loc Vector on the ground, heading deg)
        self.steps = []  # [(k, t_lift, t_land, from Vector, to Vector)]
        self.extra = []  # functions (t, pose) -> None, layered on top
        self.t_off = 0.0  # shifts the idle motion's clock (used for the loop: shot 35 runs into shot 1)

    # ---- planning helpers ------------------------------------------------------------------------------------
    def walk(self, path, t0, t1, cadence=1.8, duty=0.62, lift=0.1, width=0.1):
        """Plan planted footsteps along path(t) -> (ground loc, heading deg) between t0 and t1.
        cadence = steps per second (both feet together); duty = share of each foot's cycle spent on the ground.
        A foot lands ahead of the hips and stays put until it lifts again: no sliding."""
        self.path = path
        Tc = 2.0 / cadence
        swing = (1 - duty) * Tc
        for k, off in (("L", 0.0), ("R", Tc / 2)):
            tl = t0 - Tc + off
            while tl < t1 + Tc:
                loc, hd = path(tl + duty * Tc / 2)
                r = math.radians(hd)
                right = V((math.cos(r), math.sin(r), 0))
                to = V((loc.x, loc.y, self.foot_world[k].z)) + right * (width if k == "L" else -width)
                self.steps.append((k, tl - swing, tl, to))
                tl += Tc
        self.steps.sort(key=lambda s: s[2])
        self.lift = lift

    def step_to(self, k, t_up, t_land, to):
        """One deliberate step (repositioning at a station, stepping back with a tyre...)."""
        self.steps.append((k, t_up, t_land, V(to)))
        self.steps.sort(key=lambda s: s[2])
        self.lift = getattr(self, "lift", 0.08)

    def foot_at(self, k, t):
        """Ankle position: planted between steps, a smooth arc while stepping."""
        prev = self.foot_world[k]
        for (kk, t_up, t_land, to) in self.steps:
            if kk != k:
                continue
            if t < t_up:
                return prev
            if t <= t_land:
                x = (t - t_up) / max(1e-6, t_land - t_up)
                p = prev.lerp(to, sstep(x))
                p.z = prev.z + (to.z - prev.z) * x + math.sin(math.pi * x) * getattr(self, "lift", 0.1)
                return p
            prev = to
        return prev

    # ---- pose -------------------------------------------------------------------------------------------------
    def pose(self, t):
        b = self.base
        ti = t + self.t_off
        loc, rot = (self.path(t) if self.path else (V(b["loc"]), b["rot"]))
        p = dict(loc=V(loc), rot=rot, crouch=b["crouch"], lean=b["lean"], twist=b["twist"], side=0.0,
                 head=list(b["head"]), hands={}, feet={})
        # idle life: breathing, weight shift, a little look around (all slow, all continuous)
        p["crouch"] += wob(ti, 0.25, 0.004, self.ph)
        p["side"] += wob(ti, 0.2, 1.2, self.ph + 1)
        p["head"][0] += wob(ti, 0.15, 2.5, self.ph + 2)
        p["head"][1] += wob(ti, 0.22, 1.0, self.ph + 3)
        for k in "LR":
            p["hands"][k] = None if self.gripped[k] else (self.hand_kind[k], self.hand_local[k] + V((wob(ti, 0.3, 0.006, self.ph + (0 if k == "L" else 1.7)), 0,
                                                                                                     wob(ti, 0.27, 0.006, self.ph + 2.4))))
            p["feet"][k] = self.foot_at(k, t) if self.steps else self.foot_world[k]
        for fn in self.extra:
            fn(t, p)
        return p

    def _bend(self, lean, twist, side, head):
        """Armature-space transforms of the chest and of the head for a spine/head pose (same axes as rig.key_*)."""
        ls = rig.LEAN_SIGN
        Es = Euler((math.radians(-lean * ls), math.radians(twist), math.radians(side)), "XYZ").to_matrix().to_4x4()
        Eh = Euler((math.radians(-head[1] * ls), math.radians(head[0]), 0), "XYZ").to_matrix().to_4x4()
        S = self.spine_rest @ Es @ self.spine_rest.inverted()
        Hd = self.head_rest @ Eh @ self.head_rest.inverted()
        return S, S @ Hd

    def carry_M(self, t):
        """World transform that takes anything attached to the chest at the cast pose to where it is at time t
        (props held in the hands: they ride with the body, so the grip never stretches)."""
        p = self.pose(t)
        b = self.base
        p0 = dict(loc=V(b["loc"]), rot=b["rot"], crouch=b["crouch"])
        S0, _ = self._bend(b["lean"], b["twist"], 0.0, b["head"])
        S1, _ = self._bend(p["lean"], p["twist"], p["side"], p["head"])
        return self.body_M(p) @ S1 @ S0.inverted() @ self.body_M(p0).inverted()

    def body_M(self, p):
        """World matrix of the armature for pose p (root dropped by the crouch, scaled like the rig)."""
        return Matrix.Translation(V((p["loc"].x, p["loc"].y, p["loc"].z - p["crouch"]))) @ \
            Matrix.Rotation(math.radians(p["rot"]), 4, "Z") @ Matrix.Scale(self.scale, 4)

    def key(self, f, t):
        p = self.pose(t)
        a = self.a
        a.key_root(f, loc=V((p["loc"].x, p["loc"].y, p["loc"].z - p["crouch"])), rot_deg=p["rot"])
        a.key_spine(f, lean=p["lean"], twist=p["twist"], side=p["side"])
        a.key_head(f, yaw=p["head"][0], pitch=p["head"][1])
        b = self.base
        S0, H0 = self._bend(b["lean"], b["twist"], 0.0, b["head"])
        S1, H1 = self._bend(p["lean"], p["twist"], p["side"], p["head"])
        M = self.body_M(p)
        chest, head = M @ S1 @ S0.inverted(), M @ H1 @ H0.inverted()
        for k in "LR":
            h = p["hands"][k]
            if h is None:
                continue
            kind, v = h
            w = {"local": chest, "head": head, "root": M}.get(kind)
            a.key_target(a.hand[k], f, (w @ v) if w is not None else v)
        for k in "LR":
            a.key_target(a.foot[k], f, p["feet"][k])


def bake(performers, f0, f1, extra_frames=3):
    """Key every performer on every frame of the shot (plus a few either side for motion blur and the cut)."""
    for f in range(f0 - extra_frames, f1 + extra_frames):
        t = (f - f0) / FPS
        for pf in performers:
            pf.key(f, t)
