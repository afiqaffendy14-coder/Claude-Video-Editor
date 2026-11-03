"""Animation (blocking pass) for the halo short: every shot becomes a baked, keyframed .blend.

Principles (owner's direction): every move has an intention; characters look at things before they touch them;
anticipation before big actions, ease-in/out, follow-through and overlapping action; different speeds for
different people; background characters react; weight and momentum (lean into acceleration, settle when stopping,
recoil on impact); planted feet; nothing teleports; no clipping (validate.py checks every frame).
Lighting/grade/effects are not the focus yet.

Monza runs on ONE crash clock, tau (s), so the shots that show it agree with each other:
    tau = 0 when Verstappen's right wheels hit the sausage kerb; ~0.9 landing on Hamilton's halo;
    ~2.4 both cars at rest in the gravel (shots.TAB).
    shot 25 = tau -2.21..0 (real time), shot 1 = tau 0..0.86 in slow motion (so 25 -> 1 loops seamlessly),
    shot 3 = tau -5.0..-2.9, shot 4 = the whole move in real time with the camera riding with Hamilton's car.

Run: blender -b --factory-startup --python blender/halo_anim.py -- <out_dir> [shot ids...]   -> <out_dir>/sNN.blend
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector, Matrix, Quaternion, Euler
import lib
from lib import reset, setup_render, box, mat, palette, look_at, camera, link
import shots as SH
import halo_sets as H
import voxel, rig, choreo
from choreo import Performer, ease, sstep, overshoot, wob, FPS
from bake import rig_cast, key_obj, fcurves, free, regrip
from props import f1car_block, digits

V = Vector
D2R = math.radians


# ---------------------------------------------------------------- small helpers
def frames(f0, f1, pad=3):
    for f in range(f0 - pad, f1 + pad):
        yield f, (f - f0) / FPS


def set_M(ob, M):
    ob.matrix_world = M
    bpy.context.view_layer.update()


def key_M(ob, f, M, prev=None):
    loc, q, sc = M.decompose()
    ob.location = loc
    ob.rotation_euler = q.to_euler("XYZ", prev) if prev is not None else q.to_euler("XYZ")
    ob.scale = sc
    ob.keyframe_insert("location", frame=f)
    ob.keyframe_insert("rotation_euler", frame=f)
    ob.keyframe_insert("scale", frame=f)
    return ob.rotation_euler.copy()


def M_of(loc, yaw=0.0, pitch=0.0, roll=0.0):
    return Matrix.Translation(V(loc)) @ Euler((D2R(pitch), D2R(roll), D2R(yaw)), "XYZ").to_matrix().to_4x4()


def lerp_M(A, B, x):
    x = min(1.0, max(0.0, x))  # padding frames before/after a shot can push the factor out of range
    la, qa, sa = A.decompose()
    lb, qb, sb = B.decompose()
    return Matrix.LocRotScale(la.lerp(lb, x), qa.slerp(qb, x), sa.lerp(sb, x))


class Cam:
    """Keys the scene camera every frame from a function t -> (loc, target, roll)."""

    def __init__(self, lens=30, dof=None, fstop=2.8):
        camera(V((0, -5, 2)), V((0, 0, 1)), lens, dof, fstop)
        self.cam = bpy.context.scene.camera

    def key(self, f, loc, target, roll=0.0, lens=None):
        c = self.cam
        c.location = V(loc)
        look_at(c, V(target), roll)
        c.keyframe_insert("location", frame=f)
        c.keyframe_insert("rotation_euler", frame=f)
        if lens:
            c.data.lens = lens
            c.data.keyframe_insert("lens", frame=f)
        if c.data.dof.use_dof:
            c.data.dof.focus_distance = (V(loc) - V(target)).length
            c.data.dof.keyframe_insert("focus_distance", frame=f)


def lerp3(a, b, x):
    return V(a).lerp(V(b), x)


def path_bezier(p0, p1, p2, p3, u):
    p0, p1, p2, p3 = map(V, (p0, p1, p2, p3))
    a = p0.lerp(p1, u); b = p1.lerp(p2, u); c = p2.lerp(p3, u)
    d = a.lerp(b, u); e = b.lerp(c, u)
    return d.lerp(e, u), (e - d)


def hermite(p0, m0, p1, m1, s):
    """Cubic Hermite between p0 and p1 with end velocities m0, m1 (already scaled by the segment's duration)."""
    s2, s3 = s * s, s * s * s
    return p0 * (2 * s3 - 3 * s2 + 1) + m0 * (s3 - 2 * s2 + s) + p1 * (-2 * s3 + 3 * s2) + m1 * (s3 - s2)


def smoother(x):
    x = min(1.0, max(0.0, x))
    return x * x * x * (x * (6 * x - 15) + 10)


def spline(keys):
    """A smooth curve through timed keys [(t, value)], values floats or Vectors: velocity is continuous through every
    key (Catmull-Rom tangents, scaled by the key times) and zero at the first and last key, so a movement eases in,
    flows through its middle keys without stopping, and eases out. Holds before the first and after the last key."""
    ks = [(t, V(v) if not isinstance(v, (int, float)) else float(v)) for t, v in keys]

    def tangent(i):
        if i == 0 or i == len(ks) - 1:
            return ks[i][1] * 0
        (ta, a), (tb, b) = ks[i - 1], ks[i + 1]
        return (b - a) / (tb - ta)

    def f(t):
        if t <= ks[0][0]:
            return ks[0][1] * 1
        if t >= ks[-1][0]:
            return ks[-1][1] * 1
        for i in range(len(ks) - 1):
            (t0, a), (t1, b) = ks[i], ks[i + 1]
            if t <= t1:
                d = t1 - t0
                return hermite(a, tangent(i) * d, b, tangent(i + 1) * d, (t - t0) / d)
    return f


def qcurve(qs, w):
    """Bezier through quaternion control points (de Casteljau with slerp): a smooth change of attitude."""
    qs = list(qs)
    while len(qs) > 1:
        qs = [a.slerp(b, w) for a, b in zip(qs, qs[1:])]
    return qs[0]


# ---------------------------------------------------------------- the Monza crash clock
class Crash:
    """Both cars on the crash clock tau. Built once per shot: Hamilton's car 'ham', Verstappen's 'ver' with their
    resting relation (REL, real contact) solved by the contact settle.

    One continuous movement, no pauses: both cars keep their speed through the kerb strike; Verstappen's car rides
    up the kerb, flies a real ballistic arc (gravity 9.81) while rolling over, and lands on the halo with the impact
    (a damped rebound, both cars jolted); then they slide together into the gravel and slow to rest with no jerk."""
    V0 = 14.8          # Hamilton's speed (m/s) at tau = 0, decelerating to rest at T_REST
    T_LAND, T_REST = 0.9, 4.5  # a long slide: still ~7 m/s when shot 4 cuts, crawling to rest only after shot 6
    G = 9.81

    def __init__(self, ham_driver=True):
        self.ham, self.ver = H.monza_cars(ham_driver=ham_driver)
        bpy.context.view_layer.update()
        self.REL = self.ham.matrix_world.inverted() @ self.ver.matrix_world
        self.P0 = V((SH.HAM_X, -9.6, 0))
        self.P3 = V((SH.TAB[0], SH.TAB[1], 0))
        self.kerb = M_of((H.SAUSAGE[0] - 0.75, H.SAUSAGE[1] + 0.4, 0.22), yaw=4, pitch=6, roll=-9)
        self.air = M_of((0, 0, 0), yaw=40, pitch=4, roll=-34)  # attitude mid-flight (rolling over toward Hamilton)
        # Hamilton's path into the gravel, parameterised by distance (arc-length table)
        self.ctrl = (self.P0, self.P0 + V((0, 8, 0)), self.P3 + V((-3.5, -6, 0)), self.P3)
        pts = [path_bezier(*self.ctrl, i / 400)[0] for i in range(401)]
        self.arc = [0.0]
        for a, b in zip(pts, pts[1:]):
            self.arc.append(self.arc[-1] + (b - a).length)
        Lp, T, v0 = self.arc[-1], self.T_REST, self.V0
        # distance d(t) = v0 t + a t^2 + b t^3 + c t^4 with d(T) = Lp and zero speed AND zero deceleration at rest
        A = Matrix(((T ** 2, T ** 3, T ** 4), (2 * T, 3 * T ** 2, 4 * T ** 3), (2, 6 * T, 12 * T ** 2)))
        self.coef = A.inverted() @ V((Lp - v0 * T, -v0, 0.0))
        # each car's lowest points (tyre bottoms, plank, wing, nose) in its own frame: whatever the car does, it is
        # lifted just enough that none of them goes below the ground (rigid body on the ground, never through it)
        self.low = {}
        for car in (self.ham, self.ver):
            inv = car.matrix_world.inverted()
            pts = [inv @ p for p in H._points(car)]
            self.low[car.name] = [p for p in pts if p.z < 0.2] or pts
        self.land_M = None
        self.land_M = self.ham_M(self.T_LAND, jolt=False) @ self.REL

    def on_ground(self, car, M):
        lowest = min((M @ p).z for p in self.low[car.name])
        return Matrix.Translation(V((0, 0, max(0.0, -lowest)))) @ M

    # -- Hamilton ------------------------------------------------------------------------------------------------
    def ham_y_before(self, tau):
        """Before the kerb: braking from 30 m/s down to 14.8 m/s over the last 2.6 s (tau <= 0), down his lane."""
        a = (30.0 - self.V0) / 2.6
        if tau >= -2.6:
            return self.P0.y + self.V0 * tau - 0.5 * a * tau * tau  # speed V0 - a*tau: 30 m/s at -2.6, V0 at 0
        y26 = self.P0.y + self.V0 * -2.6 - 0.5 * a * 6.76
        return y26 + 30.0 * (tau + 2.6)

    def dist(self, tau):
        if tau >= self.T_REST:
            return self.arc[-1]
        a, b, c = self.coef
        return self.V0 * tau + a * tau ** 2 + b * tau ** 3 + c * tau ** 4

    def u_at(self, d):
        arc = self.arc
        if d >= arc[-1]:
            return 1.0
        lo, hi = 0, len(arc) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if arc[mid] <= d:
                lo = mid
            else:
                hi = mid
        return (lo + (d - arc[lo]) / max(1e-9, arc[hi] - arc[lo])) / (len(arc) - 1)

    def jolt(self, tau):
        """Hamilton's car taking the hit: pushed down on its suspension and kicked sideways, settling (0 at rest)."""
        dt = tau - self.T_LAND
        if dt <= 0:
            return 0.0, 0.0, 0.0
        e = math.exp(-dt * 6.0)
        dz = -0.05 * e * math.sin(dt * 16) - 0.02 * (1 - sstep(dt / 1.2)) * sstep(dt / 0.08)
        roll = -3.5 * e * math.cos(dt * 13) * sstep(dt / 0.05)
        yaw = 7.0 * sstep(dt / 0.35) * (1 - sstep((dt - 0.35) / 1.1))
        return dz, roll, yaw

    def ham_M(self, tau, jolt=True):
        if tau <= 0:
            return M_of((SH.HAM_X, self.ham_y_before(tau), 0))
        u = self.u_at(self.dist(tau))
        p, d = path_bezier(*self.ctrl, u)
        yaw = math.degrees(math.atan2(-d.x, d.y)) if d.length > 1e-6 else SH.TAB[2]
        w = sstep(min(1, max(0, (u - 0.8) / 0.2)))
        yaw = yaw * (1 - w) + SH.TAB[2] * w
        dz = roll = dyaw = 0.0
        if jolt:
            dz, roll, dyaw = self.jolt(tau)
            # the gravel: small bumps while still moving, fading as the car slows
            if p.x > 7.0 and tau < self.T_REST:
                sp = 1 - sstep(tau / self.T_REST)
                dz += 0.012 * sp * math.sin(tau * 41) * math.sin(tau * 17 + 1)
                roll += 1.2 * sp * math.sin(tau * 29 + 2)
            return self.on_ground(self.ham, M_of(p + V((0, 0, dz)), yaw + dyaw, 0.0, roll))
        return M_of(p, yaw)

    # -- Verstappen ----------------------------------------------------------------------------------------------
    def ver_xy(self, tau):
        if tau <= 0:  # alongside on the right, edging over onto the kerb, keeping pace (no slowing for it)
            x = SH.VER_X + (self.kerb.translation.x - SH.VER_X) * sstep((tau + 0.7) / 0.7)
            y = self.ham_y_before(tau) + 1.2 + 0.8 * sstep((tau + 2.2) / 2.2)
            return V((x, y, 0))
        if tau < self.T_LAND:  # flight: from the kerb at its speed to the landing point at Hamilton's speed there
            k, L = self.kerb.translation, self.land_M.translation
            h1 = self.ham_M(self.T_LAND + 0.01, jolt=False).translation - self.ham_M(self.T_LAND - 0.01, jolt=False).translation
            v1 = h1 / 0.02
            T = self.T_LAND
            p = hermite(V((k.x, k.y, 0)), V((0, self.V0, 0)) * T, V((L.x, L.y, 0)), V((v1.x, v1.y, 0)) * T, tau / T)
            return p
        return None

    def ver_z(self, tau):
        """Height of the car's origin: the kerb lifts it 0.22 m and launches it; then gravity until the landing."""
        k0, zl, T = 0.22, self.land_M.translation.z, self.T_LAND
        vz0 = (zl - k0 + 0.5 * self.G * T * T) / T  # the launch speed that brings it down exactly onto the halo
        if tau <= -0.15:
            return 0.0
        if tau <= 0:
            return hermite(0.0, 0.0, k0, vz0 * 0.15, (tau + 0.15) / 0.15)
        return k0 + vz0 * tau - 0.5 * self.G * tau * tau

    def ver_M(self, tau):
        if tau >= self.T_LAND:  # landed: carried with Hamilton's car; the impact rebound, a damped wobble
            M = self.ham_M(tau) @ self.REL
            dt = tau - self.T_LAND
            e = math.exp(-dt * 7.0)
            rb = Matrix.Translation(V((0, 0, 0.055 * e * abs(math.sin(dt * 17)))))
            wob_ = Euler((D2R(2.5 * e * math.sin(dt * 15)), D2R(-3.0 * e * math.sin(dt * 12 + 0.6)), 0)).to_matrix().to_4x4()
            loc = M.translation.copy()
            return self.on_ground(self.ver, rb @ Matrix.Translation(loc) @ wob_ @ Matrix.Translation(-loc) @ M)
        xy = self.ver_xy(tau)
        q_base = Euler((0, 0, 0)).to_quaternion()
        q_kerb = self.kerb.to_quaternion()
        q_land = self.land_M.to_quaternion()
        q_air = self.air.to_quaternion()
        if tau <= 0:
            q = q_base.slerp(q_kerb, sstep((tau + 0.15) / 0.15) * 0.5)  # the kerb tips it (half way to the kerb attitude)
        else:  # one smooth roll-over from the kerb attitude through the air to the landing attitude
            q0 = q_base.slerp(q_kerb, 0.5)
            q = qcurve([q0, q_kerb, q_air, q_land], smoother(tau / self.T_LAND) * 0.7 + (tau / self.T_LAND) * 0.3)
        return self.on_ground(self.ver, Matrix.LocRotScale(V((xy.x, xy.y, self.ver_z(tau))), q, V((1, 1, 1))))

    def key(self, f, tau):
        self._pe = getattr(self, "_pe", {})
        self._pe["ham"] = key_M(self.ham, f, self.ham_M(tau), self._pe.get("ham"))
        self._pe["ver"] = key_M(self.ver, f, self.ver_M(tau), self._pe.get("ver"))


class CrashDebris:
    """The violence of it, on the crash clock (so it is slow in the slow motion): bits of the sausage kerb kicked
    up at the strike, carbon fragments thrown off both cars at the landing, and gravel sprayed from the wheels all
    the way through the slide. Each piece flies a ballistic arc (g = 9.81), tumbling, and stays where it lands."""

    def __init__(self, cr, seed=11):
        import random
        rnd = random.Random(seed)
        M = palette()
        self.cr = cr
        self.parts = []  # (object, spawn tau, p0, v0, spin)

        def add(name, size, m, tau0, p0, v0):
            o = box(name, size, (0, 0, -50), m)
            spin = V((rnd.uniform(-12, 12), rnd.uniform(-12, 12), rnd.uniform(-12, 12)))
            self.parts.append((o, tau0, V(p0), V(v0), spin))

        k = V((H.SAUSAGE[0] - 0.1, H.SAUSAGE[1] + 0.4, 0.15))
        for i in range(12):  # the kerb strike
            add(f"deb_kerb{i}", (0.06, 0.08, 0.05), M["yellow"] if i % 2 else M["dark"], rnd.uniform(-0.04, 0.04),
                k + V((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.6, 0.6), 0)),
                V((rnd.uniform(0.5, 3.0), rnd.uniform(4, 12), rnd.uniform(1.5, 4.5))))
        Lm = cr.land_M
        hv = (cr.ham_M(cr.T_LAND + 0.02, jolt=False).translation - cr.ham_M(cr.T_LAND - 0.02, jolt=False).translation) / 0.04
        cols = [M["dark"], M["navy"], M["teal"], M["blackcar"], M["silver"], M["rbred"]]
        for i in range(30):  # the landing: carbon fibre everywhere
            s = rnd.choice([0.04, 0.06, 0.09])
            add(f"deb_land{i}", (s, s * rnd.uniform(1, 2.5), s * 0.5), rnd.choice(cols), cr.T_LAND + rnd.uniform(0, 0.05),
                Lm @ V((rnd.uniform(-0.6, 0.6), rnd.uniform(-1.8, 1.0), rnd.uniform(-0.1, 0.3))),
                hv * rnd.uniform(0.6, 1.1) + V((rnd.uniform(-4, 4), rnd.uniform(-3, 3), rnd.uniform(2, 6))))
        grav = mat("gravelbit", (0.74, 0.67, 0.54), 0.95)
        n = 0
        tau = cr.T_LAND
        while tau < cr.T_REST * 0.75 and n < 70:  # gravel sprayed from the wheels while they are in the trap
            Mh = cr.ham_M(tau, jolt=False)
            if Mh.translation.x > 7.3:
                v = (cr.ham_M(tau + 0.02, jolt=False).translation - cr.ham_M(tau - 0.02, jolt=False).translation) / 0.04
                for side in (1, -1):
                    p = Mh @ V((side * 0.8, rnd.choice([1.8, -1.78]), 0.05))
                    add(f"deb_grav{n}", (0.05, 0.05, 0.04), grav, tau, p,
                        v * rnd.uniform(0.2, 0.5) + V((side * rnd.uniform(0.5, 2.5), rnd.uniform(-1, 1), rnd.uniform(1.0, 3.0))))
                    n += 1
            tau += 0.06

    def key(self, f, tau):
        for o, t0, p0, v0, spin in self.parts:
            dt = tau - t0
            if dt < 0:
                o.location, o.scale = p0, (0.001, 0.001, 0.001)
            else:
                t_land = (v0.z + math.sqrt(v0.z ** 2 + 2 * 9.81 * max(0.0, p0.z))) / 9.81  # when it reaches the ground
                d = min(dt, t_land)
                p = p0 + v0 * d + V((0, 0, -4.905 * d * d))
                p.z = max(0.02, p.z)
                o.location, o.scale = p, (1, 1, 1)
                o.rotation_euler = tuple(s * d for s in spin)
            o.keyframe_insert("location", frame=f)
            o.keyframe_insert("scale", frame=f)
            o.keyframe_insert("rotation_euler", frame=f)


def pov(crash, tau, look_up=0.0, look_right=0.0):
    """Hamilton's eyes inside the helmet; look_up/right turn his head (degrees) toward the danger."""
    M = crash.ham_M(tau)
    eye = M @ V((0, 0.26, 0.86))
    d = V((math.sin(D2R(look_right)) * math.cos(D2R(look_up)), math.cos(D2R(look_right)) * math.cos(D2R(look_up)), math.sin(D2R(look_up))))
    tgt = M @ (V((0, 0.26, 0.86)) + d * 6.0)
    return eye, tgt


def hide_head(car_name):
    for o in [bpy.data.objects[car_name + "_head"]] + list(bpy.data.objects[car_name + "_head"].children_recursive):
        o.hide_render = True


# ---------------------------------------------------------------- shot motion
SLOW, RAMP = 0.23, 0.5  # shot 1: real time ramping down to 0.23x over its first 0.5 s


def tau_shot1(t):
    """Shot 1's crash clock: starts at real speed (continuing shot 25, the loop) and ramps smoothly into slow motion
    (the integral of a speed that eases from 1 down to SLOW)."""
    if t <= 0:
        return t
    x = min(t, RAMP) / RAMP
    tau = SLOW * min(t, RAMP) + (1 - SLOW) * RAMP * (x - (x ** 3 - x ** 4 / 2))
    return tau + SLOW * max(0.0, t - RAMP)


def onboard_shake(tau):
    """The car's vibration felt through the camera, on the crash clock (so it slows down in the slow motion and runs
    straight through the 25 -> 1 loop): a buzz from the engine and the kerbs, a slow roll from the bumps."""
    up = 0.006 * math.sin(2 * math.pi * 11 * tau) + 0.004 * math.sin(2 * math.pi * 17.3 * tau + 1.1) + 0.003 * math.sin(2 * math.pi * 3.1 * tau + 0.4)
    side = 0.004 * math.sin(2 * math.pi * 7.3 * tau + 2.0) + 0.002 * math.sin(2 * math.pi * 13.1 * tau)
    roll = 0.6 * math.sin(2 * math.pi * 4.0 * tau) + 0.35 * math.sin(2 * math.pi * 9.2 * tau + 0.7)
    return up, side, roll


def anim_monza_pov(n, f0, f1, dur):
    """Shots 25 and 1: one continuous onboard view, Hamilton's head turning toward Verstappen's car. Shot 25 runs
    tau -2.21 -> 0 in real time and the film loops from its last frame straight into shot 1's first: same clock, same
    head direction, same vibration."""
    H.monza_set()
    cr = Crash()
    deb = CrashDebris(cr)
    hide_head("ham")
    cam = Cam(14)
    for f, t in frames(f0, f1):
        deb.key(f, -2.21 + t if n == 25 else tau_shot1(t))
        if n == 25:
            tau = -2.21 + t
            lr = 4 + 22 * sstep((t - 1.2) / 1.0)  # glances right as the car alongside goes for the kerb
            up = 2 + 6 * sstep((t - 1.6) / 0.6)
        else:
            tau = tau_shot1(t)
            lr = 26 - 14 * sstep(t / dur)
            up = 8 + 52 * sstep((t - 0.2) / (dur - 0.2))  # eyes up to the car coming over the halo
        cr.key(f, tau)
        e, g = pov(cr, tau, up, lr)
        su, ss, sr = onboard_shake(tau)
        R = cr.ham_M(tau).to_3x3()
        jig = R @ V((ss, 0, su))
        cam.key(f, e + jig, g + jig, sr)
    return []


SLOW5 = 0.35  # shots 5 and 6: the slide continues in slow motion


def shot_dur(n):
    s = {x[0]: x for x in SH.SHOTS}[n]
    return s[2] - s[1]


def tau_of(n, t):
    """The crash clock for every Monza shot that shows the crash: the cars never stop between cuts.
    1 -> 2 one slow motion (the landing early in 2); 3 -> 4 real time (4 ends with the cars still sliding fast);
    5 -> 6 carry 4 on in slow motion; 20 -> 21 the landing again, very slow, then the push-off."""
    if n == 1:
        return tau_shot1(t)
    if n == 2:
        return tau_shot1(shot_dur(1) + t)
    if n == 5:
        return SHOT3_TAU[1] + shot_dur(4) + SLOW5 * t
    if n == 6:
        return SHOT3_TAU[1] + shot_dur(4) + SLOW5 * (shot_dur(5) + t)
    if n == 20:
        return 0.70 + 0.13 * t
    if n == 21:
        return 0.70 + 0.13 * shot_dur(20) + 0.3 * t
    raise KeyError(n)


def anim_wreck_close(n, f0, f1, dur):
    """Shots 2 and 5, close on the cockpit: the camera rides with Hamilton's car (the gravel and the stands stream
    past behind), slow motion. 2: Verstappen's tyre comes down onto the halo and bounces; 5: the two cars still
    sliding together, the tyre on the hoop. Hamilton's helmet flinches at the hit, then turns a little."""
    H.monza_set()
    cr = Crash()
    deb = CrashDebris(cr)
    head = bpy.data.objects["ham_head"]
    h0 = head.rotation_euler.copy()
    cam = Cam(24 if n == 2 else 38, 1.6, 4.0)
    if n == 2:
        c0, c1, g = V((0.95, 1.7, 0.74)), V((0.8, 1.45, 0.8)), V((0.0, 0.2, 1.0))
    else:
        c0, c1, g = (V(p) for p in SHOT5_CAM)
    t_hit = (cr.T_LAND - tau_of(n, 0.0)) / (tau_of(n, 1.0) - tau_of(n, 0.0))  # when the tyre lands (shot time)
    for f, t in frames(f0, f1):
        tau = tau_of(n, t)
        cr.key(f, tau)
        deb.key(f, tau)
        Mc = cr.ham_M(tau, jolt=False)
        if n == 2:
            fl = sstep((t - t_hit) / 0.1) * (1 - sstep((t - t_hit - 0.3) / 0.4))
            head.rotation_euler = (h0.x + D2R(-7 * fl), h0.y, h0.z + D2R(6 * sstep((t - t_hit - 0.4) / 0.6)))
        else:
            head.rotation_euler = (h0.x + D2R(-4 * sstep((t - 0.25) / 0.12) * (1 - sstep((t - 0.5) / 0.3))), h0.y,
                                   h0.z + D2R(10 * sstep((t - 0.6) / 0.5)))
        head.keyframe_insert("rotation_euler", frame=f)
        dt = tau - cr.T_LAND  # the hit shakes the camera too (in slow motion)
        k = 0.02 * math.exp(-max(0, dt) * 5) * (dt > 0)
        jig = V((wob(tau, 13, k), wob(tau, 11, k, 1), wob(tau, 15, k, 2)))
        cam.key(f, Mc @ c0.lerp(c1, t / dur) + jig, Mc @ g, 4 if n == 2 else 0)
    return []


def anim_landing_close(n, f0, f1, dur):
    """Shots 20 and 21, back at Monza, very slow motion with both cars travelling: 20, low beside the helmet,
    tilted: the rear tyre comes down onto the halo; 21, from above: the tyre on the hoop is pushed off onto the
    engine cover, away from his head, as the cars keep sliding."""
    H.monza_set()
    cr = Crash()
    deb = CrashDebris(cr)
    head = bpy.data.objects["ham_head"]
    h0 = head.rotation_euler.copy()
    if n == 21:  # where the halo pushes the tyre: slewed round, the wheel off the hoop onto the engine cover
        Vm = cr.ver.matrix_world.copy()
        cr.ver.rotation_euler.z += D2R(14)
        H.place_point(cr.ver, H.REAR_WHEEL, (0.42, -0.65, 0.66 + 0.37 + 0.6))
        H.settle(cr.ver, cr.ham, drop=1.4)
        REL_defl = cr.ham.matrix_world.inverted() @ cr.ver.matrix_world
        set_M(cr.ver, Vm)
        cam = Cam(28)
        c0, c1, g = V((2.9, 2.9, 3.2)), V((2.5, 2.4, 2.9)), V((0.1, 0.0, 0.95))
    else:
        cam = Cam(18)
        c0, c1, g = V((-0.62, 1.05, 0.66)), V((-0.58, 1.0, 0.68)), V((0.05, 0.1, 1.55))
    pe = {}
    for f, t in frames(f0, f1):
        tau = tau_of(n, t)
        deb.key(f, tau)
        Mh = cr.ham_M(tau)
        pe["h"] = key_M(cr.ham, f, Mh, pe.get("h"))
        if n == 21:
            x = smoother((t - 0.1) / 1.0)
            Mv = Mh @ lerp_M(cr.REL, REL_defl, x)
            Mv = Matrix.Translation(V((0, 0, 0.08 * math.sin(math.pi * x)))) @ Mv  # rides up over the hoop
            Mv = cr.on_ground(cr.ver, Mv)
        else:
            Mv = cr.ver_M(tau)
        pe["v"] = key_M(cr.ver, f, Mv, pe.get("v"))
        dt = tau - cr.T_LAND
        if n == 20:
            fl = sstep(dt / 0.02) * (1 - sstep((dt - 0.05) / 0.08))
            head.rotation_euler = (h0.x + D2R(8 * fl), h0.y, h0.z)
            head.keyframe_insert("rotation_euler", frame=f)
        Mc = cr.ham_M(tau, jolt=False)
        k = (0.025 if n == 20 else 0.012) * math.exp(-max(0, dt) * 6) * (dt > 0)
        jig = V((wob(tau, 9, k), wob(tau, 7, k, 1), wob(tau, 8, k, 2)))
        cam.key(f, Mc @ c0.lerp(c1, smoother(t / dur)) + jig, Mc @ g, 14 if n == 20 else 0)
    return []


SHOT3_TAU = (-2.23, -0.15)  # shot 3 ends exactly where shot 4 starts on the crash clock


def anim_monza_wide(n, f0, f1, dur):
    """Shot 3: a TV camera up in the tifosi grandstand (outside of the straight, the same side as shot 4: no
    crossing the line), on a long lens, whip-panning with the two cars as they brake side by side toward the
    chicane; looking down across the track, the packed stand opposite fills everything behind them (no sky, no
    empty ground). Ends on the instant shot 4 starts."""
    H.monza_set()
    cr = Crash()
    cam = Cam(55)
    a, b = SHOT3_TAU
    prev = None
    for f, t in frames(f0, f1):
        tau = a + (b - a) * t / dur
        cr.key(f, tau)
        hp = cr.ham_M(tau).translation
        vp = cr.ver_M(tau).translation
        mid = (hp + vp) / 2
        tgt = V((mid.x, mid.y + 1.2, 0.5))  # leading the cars a little, both in frame
        prev = tgt if prev is None else prev.lerp(tgt, 0.55)  # an operator following, a touch behind
        cam.key(f, (27.0, -44.0 + 6.0 * t / dur, 7.6), prev)
    return []


def anim_launch(n, f0, f1, dur):
    """Shot 4: one continuous move, the camera riding beside Hamilton's car (we start on it): Verstappen's car
    comes up on the right, hits the kerb, is launched over and lands across Hamilton's, both slide into the gravel."""
    H.monza_set()
    cr = Crash()
    deb = CrashDebris(cr)
    cam = Cam(32)
    prev = ptgt = None
    for f, t in frames(f0, f1):
        tau = SHOT3_TAU[1] + t  # real time, picking up the instant shot 3 cut away; the cars are still sliding at the cut
        cr.key(f, tau)
        deb.key(f, tau)
        hp = cr.ham_M(tau, jolt=False).translation
        vp = cr.ver_M(tau).translation
        mid = (hp + vp) / 2  # both cars in the centre of the frame
        # camera: low, front-right of the pair, travelling with them, tight enough that the cars and the stands fill
        # the frame; a handheld operator struggling to keep up (constant shake, a hard jolt at the landing)
        w = sstep((tau - 0.6) / 1.6)
        off = V((4.6 + 1.0 * w, 6.0 + 0.8 * w, 1.5 + 0.9 * w))
        loc = V((mid.x, mid.y, 0)) + off
        loc.x = min(loc.x, 15.4)  # stay inside the tyre wall and hoardings (x 16.2)
        tgt = V((mid.x, mid.y, 0.35 + 0.5 * min(vp.z, 1.4)))
        prev = loc if prev is None else prev.lerp(loc, 0.4)  # a camera operator's lag, not a locked rig
        ptgt = tgt if ptgt is None else ptgt.lerp(tgt, 0.5)
        dt = tau - cr.T_LAND
        k = 0.015 + 0.07 * math.exp(-max(0, dt) * 4) * (dt > 0) + 0.03 * math.exp(-((tau - 0.0) / 0.12) ** 2)
        jig = V((wob(t, 13, k), wob(t, 11, k * 0.6, 1), wob(t, 17, k, 2)))
        cam.key(f, prev + jig, ptgt + jig * 0.4, wob(t, 7, 22 * k, 0.5) + 3 * math.sin(t * 1.7))
    return []


SHOT5_CAM = ((1.05, 1.4, 1.14), (0.9, 1.25, 1.1), (0.03, 0.3, 1.02))  # wreck frame: start, end, target (lens 38)
HALO_C = V((0, 0.12, 0.86))  # the halo's centre in the car's frame


def anim_halo_reveal(n, f0, f1, dur):
    """Shot 6 picks up exactly where shot 5 ends (same place, same framing, the cars at rest in the gravel): the
    halo begins to glow; Verstappen's car falls away block by block, then Hamilton's car and helmet do too, outside
    in, leaving just the halo where it was, which turns slowly as the camera pulls back round it. A shallow focus
    keeps Monza soft behind it."""
    H.monza_set()
    cr = Crash()
    glow = mat("halo_hero", (0.75, 0.06, 0.05), 0.35, emit=(1.0, 0.3, 0.22), emit_strength=0.0)
    for o in cr.ham.children_recursive:
        if o.type in ("MESH", "CURVE") and o.get("halo"):
            for sl in o.material_slots:
                sl.material = glow
    cam = Cam(38, 1.6, 2.8)
    return dict(kind="reveal", cr=cr, cam=cam, glow=glow)


def reveal_keys(st, f0, f1, dur):
    """The slide carries on in slow motion (from shot 5) while the cars fall away around the halo."""
    cr, cam = st["cr"], st["cam"]
    bpy.context.view_layer.update()
    hc = cr.ham.matrix_world @ HALO_C  # the cars are still at the origin here: distances for the order blocks go in
    groups = [(cr.ver, 0.08, 0.55), (cr.ham, 0.38, 0.75)]  # (car, start, spread): Verstappen's goes first
    keyed = []
    for car, a, spread in groups:  # all of Verstappen's car goes (its halo too); Hamilton's halo stays
        parts = [o for o in car.children_recursive if o.type == "MESH" and (car is cr.ver or not o.get("halo"))]
        d = {o.name: (o.matrix_world.translation - hc).length for o in parts}
        far = max(d.values())
        for o in parts:
            keyed.append((o, o.location.copy(), o.scale.copy(), a + spread * (1 - d[o.name] / far)))
    node = st["glow"].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    ham_root = cr.ham
    s5a, s5b, s5t = (V(p) for p in SHOT5_CAM)  # in Hamilton's (moving) car frame
    drift = (s5b - s5a) / shot_dur(5)  # shot 5's steady camera drift (m/s), carried on
    head = bpy.data.objects["ham_head"]
    head.rotation_euler.z += D2R(10)  # where shot 5 left his helmet (turned 10 degrees)
    end_cam, end_tgt = V((1.55, -1.25, 1.55)), HALO_C + V((0, 0, 0.05))
    pe = pv = None
    for f, t in frames(f0, f1):
        tau = tau_of(6, t)
        Mh, Mc = cr.ham_M(tau), cr.ham_M(tau, jolt=False)
        pv = key_M(cr.ver, f, cr.ver_M(tau), pv)
        hcw = Mh @ HALO_C
        for o, l, s, t0 in keyed:  # each block falls a little and shrinks to nothing
            x = sstep((t - t0) / 0.32)
            o.location = l + V((0, 0, -0.2 * x * x))
            o.scale = s * max(0.0, 1 - x)
            o.keyframe_insert("location", frame=f)
            o.keyframe_insert("scale", frame=f)
        node.default_value = 3.5 * sstep((t - 0.1) / 0.9)
        node.keyframe_insert("default_value", frame=f)
        # the halo (all that is left of Hamilton's car) turns slowly about its own centre once the car has gone
        a = D2R(32 * ease(t, 1.05, dur + 0.6) + 6 * max(0.0, t - 1.05))
        Mrot = Matrix.Translation(hcw) @ Matrix.Rotation(a, 4, "Z") @ Matrix.Translation(-hcw)
        pe = key_M(ham_root, f, Mrot @ Mh, pe)
        # camera, riding with the slide: shot 5's slow drift continues, then pulls back and round to the halo
        # alone, a 3/4 view
        z = smoother((t - 0.25) / (dur - 0.25))
        c0 = s5b + drift * max(-0.1, t)
        loc = c0.lerp(end_cam, z) + V((0, 0, 0.35 * math.sin(math.pi * z)))
        cam.key(f, Mc @ loc, Mc @ s5t.lerp(end_tgt, smoother((t - 0.15) / 1.2)), 0, 38 - 6 * z)


def fan_heads(perfs, car, f0, f1):
    """Fans follow the passing car with their heads (eye direction), each a little late; booing arm pumps and
    board waving at their own speed, getting bigger as it passes."""
    pass


def anim_fans(n, f0, f1, dur):
    """Shot 7: the 2018 car with its new halo passes below; the tifosi turn to watch it, then boo and wave their
    red-X boards harder as it goes by."""
    SH.s07()
    car = bpy.data.objects["car2018"]
    car.location.x = 4.5
    return dict(kind="fans", car=car, y0=-27.4, y1=4.7)  # passes the camera at ~1 s, never stopping


def anim_static_set(builder):
    def a(n, f0, f1, dur):
        builder()
        return dict(kind="people")
    return a


# ---------------------------------------------------------------- people behaviours
def look_at_head(pf, target, t0=0.0, t1=0.3, until=99.0, back=0.3):
    """Turn the head toward a world point (acknowledge it) between t0 and t1, hold, turn back after `until`."""
    def fx(t, p):
        hd = p["rot"]
        loc = p["loc"]
        d = V(target) - (V(loc) + V((0, 0, 1.6)))
        yaw = math.degrees(math.atan2(-d.x, d.y)) - hd
        yaw = (yaw + 180) % 360 - 180
        pitch = -math.degrees(math.atan2(d.z, V((d.x, d.y)).length))
        x = ease(t, t0, t1) * (1 - ease(t, until, until + back))
        p["head"][0] = p["head"][0] * (1 - x) + max(-60, min(60, yaw)) * x
        p["head"][1] = p["head"][1] * (1 - x) + max(-30, min(35, pitch)) * x
    pf.extra.append(fx)


def gesture(pf, k, keys):
    """A hand moving smoothly through offsets from its rest place, in the body's frame: keys [(t, (out, fwd, up))]
    where 'out' is away from the body's midline on that hand's side. The path is a spline (eases in, flows through
    the middle keys, eases out); it rides on the chest (or the head, for a hand at the face) and keeps the idle
    life underneath."""
    rest = pf.hand_local[k]
    side = 1.0 if rest.x >= 0 else -1.0
    ks = [(tt, V((side * o[0], o[1], o[2]))) for tt, o in keys]
    if ks[0][1].length > 1e-6:
        ks.insert(0, (ks[0][0] - 0.35, V((0, 0, 0))))
    if ks[-1][1].length > 1e-6:
        ks.append((ks[-1][0] + 0.4, V((0, 0, 0))))
    sp = spline(ks)

    def fx(t, p):
        h = p["hands"][k]
        if h and h[0] in ("local", "head"):
            p["hands"][k] = (h[0], h[1] + sp(t))
    pf.extra.append(fx)


def head_keys(pf, keys, add=True):
    """Head (yaw, pitch) along a spline of timed keys: looks, tilts, nods, all eased and flowing."""
    sp = spline([(t, V((y, pch, 0))) for t, (y, pch) in keys])

    def fx(t, p):
        v = sp(t)
        if add:
            p["head"][0] += v.x
            p["head"][1] += v.y
        else:
            p["head"][0], p["head"][1] = v.x, v.y
    pf.extra.append(fx)


def body_keys(pf, keys):
    """Offsets to crouch / lean / side along a spline: keys [(t, (crouch, lean, side))]."""
    sp = spline([(t, V(v)) for t, v in keys])

    def fx(t, p):
        v = sp(t)
        p["crouch"] += v.x
        p["lean"] += v.y
        p["side"] += v.z
    pf.extra.append(fx)


def head_shake(pf, t0, cycles=1.5, amp=12, freq=1.6):
    """A shake of the head: the amplitude swells and fades (no sudden start or stop)."""
    T = cycles / freq

    def fx(t, p):
        x = min(1.0, max(0.0, (t - t0) / T))
        env = math.sin(math.pi * x) ** 1.5 if 0 < x < 1 else 0.0
        p["head"][0] += amp * env * math.sin(2 * math.pi * freq * (t - t0))
    pf.extra.append(fx)


def nod(pf, t0, n=2, amp=9, freq=1.4):
    T = n / freq

    def fx(t, p):
        x = min(1.0, max(0.0, (t - t0) / T))
        env = math.sin(math.pi * x) if 0 < x < 1 else 0.0
        p["head"][1] += amp * env * 0.5 * (1 - math.cos(2 * math.pi * freq * (t - t0)))
    pf.extra.append(fx)


def breathe_big(pf, t0, t1, lean=-6, crouch=-0.02):
    """A relieved exhale: chest lifts then sinks, shoulders drop."""
    def fx(t, p):
        x = math.sin(math.pi * min(1, max(0, (t - t0) / (t1 - t0))))
        p["lean"] += lean * x
        p["crouch"] += crouch * x
    pf.extra.append(fx)


def busy_hands(pf, seed, dur):
    """Background crew at work at their own calm pace: one hand at a time reaches to a spot a little in front
    (a keyboard, a screen, a tablet), works there, comes back; the head looks down at the work. Smooth splines,
    small moves, no twitching."""
    import random
    rnd = random.Random(seed)
    head_keys(pf, [(0.0, (0, 10)), (dur + 1.0, (0, 10))])
    for k in "LR":
        t = rnd.uniform(0.0, 0.6) + (0.5 if k == "R" else 0.0)
        keys = [(t - 0.1, (0, 0, 0))]
        while t < dur + 1.0:
            spot = (rnd.uniform(-0.04, 0.02), rnd.uniform(0.1, 0.16), rnd.uniform(0.06, 0.14))
            keys += [(t + 0.45, spot), (t + 0.9, tuple(v + rnd.uniform(-0.015, 0.015) for v in spot)), (t + 1.35, (0, 0.02, 0.02))]
            t += rnd.uniform(1.5, 2.2)
        gesture(pf, k, keys)


def walk_path(pf, pts, t0, t1, cadence=1.9, lift=0.09):
    """Walk along a polyline between t0 and t1 with planted footsteps; heading follows the path; eases in/out."""
    pts = [V((p[0], p[1], 0)) for p in pts]
    L = [0.0]
    for a, b in zip(pts, pts[1:]):
        L.append(L[-1] + (b - a).length)

    def at(s):
        s = max(0, min(L[-1], s))
        for i in range(len(pts) - 1):
            if s <= L[i + 1] or i == len(pts) - 2:
                u = (s - L[i]) / max(1e-6, L[i + 1] - L[i])
                d = pts[i + 1] - pts[i]
                return pts[i].lerp(pts[i + 1], u), math.degrees(math.atan2(-d.x, d.y))
        return pts[-1], 0

    def path(t):
        s = L[-1] * ease(t, t0, t1)
        loc, hd = at(s)
        return loc, hd
    pf.walk(path, t0 - 0.2, t1 + 0.1, cadence=cadence, duty=0.62, lift=lift)
    for k, s in (("L", 1), ("R", -1)):
        loc, hd = path(t0 - 0.3)
        r = D2R(hd)
        pf.foot_world[k] = V((loc.x + s * 0.1 * math.cos(r), loc.y + s * 0.1 * math.sin(r), pf.foot_world[k].z))

    def fx(t, p):  # lean into the start, settle at the stop; knees bend to walk; arms swing opposite the legs
        sp = (ease(t + 0.05, t0, t1) - ease(t - 0.05, t0, t1)) / 0.1 * L[-1] / max(0.1, t1 - t0)
        p["lean"] += 4 * min(1.5, sp)
        p["crouch"] += 0.07 * min(1.0, sp / 0.8)  # a straight leg can't take a step: the hips drop a little
        for k, s in (("L", 1), ("R", -1)):
            if p["hands"][k] and p["hands"][k][0] == "local":
                p["hands"][k] = ("local", p["hands"][k][1] + V((0, 0.1 * s * math.sin(math.pi * cadence * t) * min(1, sp), 0)))
    pf.extra.append(fx)
    return path


# ---------------------------------------------------------------- shot table
def shot_people(n, perf, f0, f1, dur, st):
    """Per-shot character performances (intentions, reactions, timing)."""
    P = perf
    if n == 7:
        # 'When it arrived in 2018, fans called it ugly': the tifosi pick the car up coming down the straight, follow
        # it past (each a little late), then boo and wave their red-X boards at it, each at their own calm tempo
        car = st["car"]
        for i, (nm, pf) in enumerate(sorted(P.items())):
            delay = 0.12 * (i % 5)
            tempo = 1.0 + 0.18 * (i % 4)
            st.setdefault("wave", {})[pf.a.name] = (delay, tempo, i)  # their boards wave at the same tempo
            def fx(t, p, pf=pf, delay=delay, i=i, tempo=tempo):
                cy = st["y0"] + (st["y1"] - st["y0"]) * min(1, max(0, t) / dur)
                d = V((car.location.x, cy, 0.8)) - (V(p["loc"]) + V((0, 0, 1.6)))
                yaw = (math.degrees(math.atan2(-d.x, d.y)) - p["rot"] + 180) % 360 - 180
                x = smoother((t - 0.1 - delay) / 0.6)
                p["head"][0] = p["head"][0] * (1 - x) + max(-55, min(55, yaw)) * x
                p["head"][1] += 6 * x
                pump = smoother((t - 0.9 - delay) / 0.6)  # booing once it's level with them
                ph = 2 * math.pi * tempo * t + i
                p["lean"] += 3 * pump * math.sin(ph)
                for k in "LR":
                    h = p["hands"][k]
                    if h and h[0] in ("local", "head"):
                        p["hands"][k] = (h[0], h[1] + V((0, 0.02 * pump * math.sin(ph), 0.03 * pump * (0.5 + 0.5 * math.sin(ph + 0.6)))))
            pf.extra.append(fx)
            if i % 2:  # half of them shake their heads at it: no
                head_shake(pf, 0.8 + delay, 2.5, 14, 1.4 + 0.15 * (i % 3))
        return list(P.values())
    if n == 8:
        # 'And some drivers agreed': both size up the halo; one shrugs (hands open, shoulders up, eases down),
        # the other shakes his head slowly, then they look at each other
        a, b, c = P["drvA"], P["drvB"], P["crew1"]
        look_at_head(a, (0, -2.0, 1.0), 0.0, 0.3)
        look_at_head(b, (0, -2.0, 1.0), 0.0, 0.35)
        for k in "LR":
            gesture(a, k, [(0.55, (0.1, 0.07, 0.11)), (0.85, (0.11, 0.075, 0.115))])
        body_keys(a, [(0.25, (0, 0, 0)), (0.6, (-0.025, -3, 0)), (0.9, (-0.022, -3, 0)), (1.3, (0, 0, 0))])
        head_keys(a, [(0.3, (0, 0)), (0.6, (0, -6)), (0.95, (0, -5)), (1.35, (0, 0))])
        head_shake(b, 0.3, 1.5, 12, 1.6)
        look_at_head(b, (-1.35, -1.2, 1.6), 1.0, 1.3)
        busy_hands(c, 3, dur)
        return [a, b, c]
    if n == 9:
        # 'Mercedes boss Toto Wolff said, "If"': talking to the room, a hand opening as he makes his point, a glance
        # down at the halo in front of him and back up
        w = P["wolff"]
        hp = V(SH.launch_halo())
        look_at_head(w, hp, 0.55, 0.85, 1.25, 0.3)
        gesture(w, "R", [(0.25, (0.03, 0.08, 0.08)), (0.65, (0.07, 0.1, 0.12)), (1.05, (0.03, 0.09, 0.09)), (1.45, (0.06, 0.1, 0.11))])
        body_keys(w, [(0.0, (0, 0, 0)), (0.6, (0, 4, 1.5)), (1.2, (0, 2, -1)), (1.8, (0, 0, 0))])
        return [w]
    if n == 10:
        # '"If you give me a chainsaw, I would take it off."': crouched at the case behind the car he lifts the saw
        # with its weight, rises, turns to the halo with two steps and holds it up at it, leaning back with a grin
        w = P["wolff"]
        rot0, rot1 = w.base["rot"], SH.s10_aim_rot()
        T_UP, T_TURN = (0.2, 1.05), (0.85, 1.55)
        def fx(t, p):
            up = smoother((t - T_UP[0]) / (T_UP[1] - T_UP[0]))
            p["crouch"] = w.base["crouch"] * (1 - up) + 0.015 * math.sin(math.pi * up)
            p["lean"] = w.base["lean"] * (1 - up) - 8 * smoother((t - 1.25) / 0.5)
            p["twist"] = w.base["twist"] * (1 - up)  # the crouch's twist unwinds as he stands square to the halo
            p["rot"] = rot0 + ((rot1 - rot0 + 180) % 360 - 180) * smoother((t - T_TURN[0]) / (T_TURN[1] - T_TURN[0]))
            p["head"][1] = 25 * (1 - smoother((t - 0.45) / 0.6)) + 4 * smoother((t - 1.2) / 0.4)
            p["head"][0] = 0
        w.extra.append(fx)
        r_end = D2R(rot1)
        right_end = V((math.cos(r_end), math.sin(r_end), 0))
        fwd_end = V((-math.sin(r_end), math.cos(r_end), 0))
        base = V(w.base["loc"])
        fz = w.foot_world["L"].z
        w.step_to("L", 0.95, 1.3, V((base.x, base.y, fz)) + right_end * 0.1 + fwd_end * 0.12)
        w.step_to("R", 1.2, 1.55, V((base.x, base.y, fz)) - right_end * 0.1 - fwd_end * 0.1)
        st["wolff_pf"] = w
        st["saw0"] = bpy.data.objects["saw"].matrix_world.copy()
        st["aim_rot"] = rot1
        return [w]
    if n == 17:
        return climb_people(P, f0, f1, dur, st)
    if n == 18:
        # 'Grosjean had doubted it': sizing up the halo, hand at his chin, a slow sceptical shake, the thumb working
        # along his jaw
        g, c = P["gro"], P["crew1"]
        look_at_head(g, (0.0, -1.9, 1.0), 0.0, 0.25)
        head_keys(g, [(0.0, (0, 0)), (0.5, (-4, 3)), (1.0, (3, 4)), (1.5, (0, 2))])
        head_shake(g, 0.55, 1.0, 7, 1.3)
        gesture(g, "L", [(0.25, (0.0, 0.0, -0.015)), (0.65, (0.005, 0.0, 0.01)), (1.05, (0.0, 0.0, -0.012))])
        body_keys(g, [(0.0, (0, 0, 0)), (0.7, (0, 3, -2)), (1.4, (0, 2, -1))])
        busy_hands(c, 5, dur)
        return [g, c]
    if n == 22:
        # 'Hamilton said it saved his neck': rubbing the back of his neck, a slow roll of the head one way and the
        # other, then a look back at the car that landed on him and a breath out
        l = P["lewis"]
        elbow_pole(l, "R", (-0.62, 0.05, 1.5))  # the elbow flared out to the side and up, clear of his body
        def roll(t, p):
            env = smoother(t / 0.4) * (1 - smoother((t - 1.25) / 0.4))
            p["head"][1] += 7 * env * math.sin(2 * math.pi * 0.5 * t)
            p["side"] += 5 * env * math.sin(2 * math.pi * 0.5 * t + 1.2)
        l.extra.append(roll)
        def rub(t, p):  # small circles of the fingers on the neck
            h = p["hands"]["R"]
            env = smoother(t / 0.3) * (1 - smoother((t - 1.3) / 0.4))
            if h and h[0] in ("local", "head"):
                a = 2 * math.pi * 0.9 * t
                p["hands"]["R"] = (h[0], h[1] + V((0.015 * env * math.cos(a), 0, 0.015 * env * math.sin(a))))
        l.extra.append(rub)
        look_at_head(l, SH.tab((0.0, 0.3, 1.2)), 1.25, 1.65)
        breathe_big(l, 1.5, 2.3, lean=-4, crouch=-0.015)
        ms = [P[k] for k in P if k.startswith("marshal")]
        for i, m in enumerate(ms):
            look_at_head(m, SH.tab((0.0, 0.3, 1.0)), 0.2 + 0.35 * i, 0.6 + 0.35 * i)
        return [l] + ms
    if n == 23:
        # 'His team boss said it had definitely saved his life': on the radio, listening; a long breath out of
        # relief, the free hand to his chest, two slow nods; the crew turn to him
        w, c1, c2 = P["wolff"], P["crew1"], P["crew2"]
        radio = "R" if w.hand_kind["R"] == "head" else "L"
        elbow_pole(w, radio, (-0.5 if radio == "R" else 0.5, 0.2, 1.15))  # hand to the headset, elbow out and down
        head_keys(w, [(0.0, (0, 0)), (0.5, (-6, 4)), (1.0, (-4, 6))])
        breathe_big(w, 0.6, 1.9, lean=-6)
        free = "L" if w.hand_kind["R"] == "head" else "R"
        gesture(w, free, [(0.9, (-0.04, 0.12, 0.22)), (1.7, (-0.045, 0.125, 0.23))])
        nod(w, 1.8, 2, 8, 1.3)
        look_at_head(c1, (1.7, -0.6, 1.7), 0.9, 1.25)
        busy_hands(c2, 7, dur)
        look_at_head(c2, (1.7, -0.6, 1.7), 1.4, 1.8)
        return [w, c1, c2]
    if n == 24:
        # 'That boss was Toto Wolff': he looks down at the saw in his hands, lifts it a touch, then up at us with
        # a grin and a small shrug
        w = P["wolff"]
        elbow_pole(w, "R", (-0.5, 0.3, 0.95))  # elbows out to the sides and a little forward, not behind him
        elbow_pole(w, "L", (0.5, 0.3, 0.95))
        head_keys(w, [(0.0, (0, 24)), (0.35, (0, 26)), (0.95, (3, -2)), (1.4, (-4, -4)), (2.0, (-3, -3))], add=False)
        body_keys(w, [(0.0, (0, 0, 0)), (0.9, (0, 0, 0)), (1.25, (-0.018, -3, 2)), (1.7, (-0.005, -1, 1))])
        st.setdefault("lift", {})["saw"] = spline([(0.15, 0.0), (0.6, 0.05), (1.1, 0.04), (1.6, 0.055)])  # hefts it
        return [w]
    return list(P.values())


def climb_people(P, f0, f1, dur, st):
    """Shot 17: Grosjean climbs over the barrier (hands over the top rail, knee up, over, drops to the track side
    with a landing crouch), the medic RUNS in from off frame, reaches him, and they walk out together; the marshal
    keeps the extinguisher on the fire."""
    BX, RT, Y = H.BARRIER_X, 1.24, SH.CLIMB_Y
    g, med = P["gro"], P["medic"]
    # Grosjean vaults the barrier, facing the track the whole time:
    #   0.00-0.35 anticipation: hands on the top rail, knees bend, lean in
    #   0.35-0.95 the vault: hips up and over (a ballistic arc), knees tucked so the feet stay ABOVE the rail
    #             (ankles >= 1.36 m while within 0.35 m of it); hands let go once the hips pass over them
    #   0.95-1.35 landing on the track side: knees absorb it (crouch), then he straightens
    LEGZ = 0.855
    land = V((BX - 0.55, Y, 0))
    start = V((BX + 0.42, Y, 0))
    T0, T1 = 0.35, 0.95
    def vault(t):
        u = min(1.0, max(0.0, (t - T0) / (T1 - T0)))
        x = start.x + (land.x - start.x) * sstep(u)
        dz = 1.0 * 4 * u * (1 - u)  # hips up to ~1.85 m at the top of the arc
        return u, x, dz
    def crouch_at(t):
        u = vault(t)[0]
        pre = ease(t, 0.0, T0)
        return 0.07 * pre * (1 - ease(t, T0, T0 + 0.12)) + 0.2 * ease(t, T1, T1 + 0.1) * (1 - ease(t, T1 + 0.12, 1.4))

    def raw_foot(k, s, t):
        """Push off, tuck the feet up under the hips (above the rail while they are over it), come down."""
        u, x, dz = vault(t)
        hip = V((x, Y, LEGZ + dz - crouch_at(t)))
        ground0 = V((start.x - (0.05 if k == "L" else -0.05), Y + s * 0.1, 0.09))
        ground1 = V((land.x + (0.08 if k == "L" else -0.08), Y + s * 0.1, 0.09))
        if t < T0:
            return ground0
        if t > T1:
            return ground1
        tuck = V((hip.x + 0.12, Y + s * 0.1, max(0.09, hip.z - 0.42)))
        ft = ground0.lerp(tuck, smoother(u / 0.4)).lerp(ground1, smoother((u - 0.55) / 0.45))
        if abs(ft.x - BX) < 0.3:
            ft.z = max(ft.z, RT + 0.29)
        ft.z = max(ft.z, hip.z - 0.74)  # a leg can't stretch further than it is long
        return ft

    # feet move at most 0.2 m a frame (6 m/s): sampled densely, they may fall only that fast (no snapping down)
    tab = {}
    for k, s in (("L", 1), ("R", -1)):
        pts, prev = [], None
        for i in range(int(2.0 * FPS * 4) + 1):
            t = -0.2 + i / (FPS * 4)
            ft = raw_foot(k, s, t)
            if prev is not None:  # up or down, at most 0.05 m per quarter frame
                ft = V((ft.x, ft.y, min(prev.z + 0.05, max(prev.z - 0.05, ft.z))))
            pts.append(ft)
            prev = ft
        tab[k] = pts

    def foot_path(k, t):
        f = (t + 0.2) * FPS * 4
        i = max(0, min(len(tab[k]) - 2, int(f)))
        return tab[k][i].lerp(tab[k][i + 1], min(1.0, max(0.0, f - i)))

    def g_fx(t, p):
        u, x, dz = vault(t)
        p["loc"] = V((x, Y, dz))
        p["rot"] = 90
        pre = ease(t, 0.0, T0)
        p["crouch"] = 0.07 * pre * (1 - ease(t, T0, T0 + 0.12)) + 0.2 * ease(t, T1, T1 + 0.1) * (1 - ease(t, T1 + 0.12, 1.4))
        p["lean"] = 10 * pre * (1 - u) + 10 * ease(t, T1, T1 + 0.1) * (1 - ease(t, 1.1, 1.4))
        hip = V((x, Y, LEGZ + dz - p["crouch"]))
        grip = 1 - smoother((t - T0 + 0.02) / 0.3)  # lets go as the hips rise past his hands' reach
        arms_dn = 1 - smoother((t - T1 - 0.05) / 0.45)  # after the landing the arms come down to his sides
        Mb = g.body_M(p)
        for k, s in (("L", 1), ("R", -1)):
            # on the rail -> up and out for balance (within reach of the shoulders) -> hanging at his sides: one
            # continuous path, never a jump
            rail = V((BX - 0.02, Y + s * 0.26, RT + 0.2))
            bal = hip + V((-0.15, s * 0.42, 0.62))
            side_ = Mb @ V((s * 0.27, 0.03, 0.9))
            w_ = rail.lerp(bal, 1 - grip).lerp(side_, 1 - arms_dn)
            p["hands"][k] = ("world", w_) if t < T1 + 0.55 else ("local", V((s * 0.27, 0.03, 0.9)))
            ground0 = V((start.x - (0.05 if k == "L" else -0.05), Y + s * 0.1, 0.09))
            ground1 = V((land.x + (0.08 if k == "L" else -0.08), Y + s * 0.1, 0.09))
            if t < T0:  # standing at the barrier, knees bending
                p["feet"][k] = ground0
            elif t < 1.5:  # the vault's feet, from the speed-limited table (see foot_path below)
                p["feet"][k] = foot_path(k, t)
        p["head"][1] = -12 * (1 - u) + 20 * ease(t, T1, T1 + 0.2) * (1 - ease(t, 1.3, 1.6))
    g.extra.append(g_fx)
    g.base["loc"] = list(start)
    # then he walks out with the medic (planted steps, natural stride), toward the left of frame
    out_path = [(land.x, land.y), (land.x - 0.6, land.y + 0.45), (land.x - 1.3, land.y + 0.95)]
    gp = walk_path(g, out_path, 1.55, dur + 0.6, cadence=3.4)
    def g_after(t, p):
        if t >= 1.75:
            loc, hd = gp(t)
            p["loc"], p["rot"] = loc, hd
    g.extra.append(g_after)
    # medic: one continuous path - runs in from off frame (left of camera), slows and stops beside him, then walks
    # out with him, a hand on his shoulder; planted steps all the way (fast while running, slower walking out)
    m_start = V((BX - 4.4, Y - 1.8, 0))  # enters from frame right, along the track side, clear of the marshal

    def beside(t):
        """Walking at his right side (away from the barrier), half a pace back (not in front of him)."""
        gl, hd = gp(t)
        r = D2R(hd)
        left = V((math.cos(r), math.sin(r), 0))
        fwd = V((-math.sin(r), math.cos(r), 0))
        return gl - left * 0.62 - fwd * 0.45, hd  # behind his right shoulder, an arm's length away
    meet, hd_meet = beside(1.55)
    run_hd = math.degrees(math.atan2(-(meet - m_start).x, (meet - m_start).y))
    def turn(a, b, x):
        return a + ((b - a + 180) % 360 - 180) * x
    RUN0 = -0.7  # he is already running when the shot opens (no start from a standstill at full speed)

    def m_path(t):
        if t < 1.45:
            u = 1 - (1 - min(1, max(0.0, t - RUN0) / (1.45 - RUN0))) ** 2  # running in, slowing to a stop beside him
            return m_start.lerp(meet, u), turn(run_hd, hd_meet, sstep((t - 1.15) / 0.3))
        if t < 1.55:
            return meet, hd_meet
        return beside(t)
    med.walk(m_path, RUN0 - 0.2, dur + 0.4, cadence=3.0, duty=0.5, lift=0.12)
    loc0, hd0 = m_path(RUN0 - 0.3)
    for k, s in (("L", 1), ("R", -1)):
        r = D2R(hd0)
        med.foot_world[k] = V((loc0.x + s * 0.1 * math.cos(r), loc0.y + s * 0.1 * math.sin(r), med.foot_world[k].z))
    def m_fx(t, p):
        p["lean"] += 14 * (1 - ease(t, 1.1, 1.55))  # leaning into the run, upright as he stops
        p["crouch"] += 0.1 * (1 - ease(t, 1.0, 1.5)) + 0.06 * ease(t, 1.5, 1.7)  # knees bent: running, then walking
        look_at_head_now(p, V((BX - 0.2, Y, 1.4)) if t < 1.75 else V((land[0] - 3.4, land[1] + 2.4, 1.5)))
        if t >= 1.5:
            gl, hd = gp(t)
            x = ease(t, 1.5, 1.7)
            r = D2R(hd)
            left = V((math.cos(r), math.sin(r), 0))
            fwd = V((-math.sin(r), math.cos(r), 0))
            back = gl - fwd * (0.1125 + 0.1) - left * 0.12 + V((0, 0, 1.2))  # on his upper back, right of the spine
            rest = med.body_M(p) @ med.hand_local["L"]
            p["hands"]["L"] = ("world", rest.lerp(back, smoother((t - 1.5) / 0.3)))  # his hand on the back, guiding
    med.extra.append(m_fx)
    return [g, med] + [P[k] for k in P if k.startswith("marshal")]


def elbow_pole(pf, k, local_pt):
    """Point an arm's elbow at a place relative to the body (an IK pole that rides with the person), so the elbow
    flares out naturally instead of folding in or twisting backwards. The pole angle is the one that really
    puts the elbow on that side (tested on the rig)."""
    arm = pf.a.arm
    e = bpy.data.objects.new(f"{arm.name}_pole.{k}", None)
    bpy.context.scene.collection.objects.link(e)
    e.parent = arm
    e.location = V(local_pt)
    c = next(c for c in arm.pose.bones["forearm." + k].constraints if c.type == "IK")
    c.pole_target = e
    best = None
    for deg in range(-180, 180, 15):
        c.pole_angle = D2R(deg)
        bpy.context.view_layer.update()
        elbow = arm.matrix_world @ arm.pose.bones["forearm." + k].head
        d = (elbow - e.matrix_world.translation).length
        if best is None or d < best[0]:
            best = (d, deg)
    c.pole_angle = D2R(best[1])
    bpy.context.view_layer.update()
    return e


def look_at_head_now(p, target):
    d = V(target) - (V(p["loc"]) + V((0, 0, 1.6)))
    yaw = (math.degrees(math.atan2(-d.x, d.y)) - p["rot"] + 180) % 360 - 180
    p["head"][0] = max(-60, min(60, yaw))
    p["head"][1] = max(-30, min(35, -math.degrees(math.atan2(d.z, V((d.x, d.y)).length))))


def build_climb():
    """Shot 17's start: Grosjean at the barrier ready to climb, the medic off frame, the marshal on the fire."""
    BX, Y = H.BARRIER_X, SH.CLIMB_Y
    SH.climb_scene()
    SH.s17_a_person()
    H.person_at("medic", BX - 3.4, Y - 2.0, -20, "walk", "medic", stance=(0.2, -0.2))
    m = H.person_at("marshal", BX - 1.6, -0.2, 160, "hose", "marshal", stance=(0.22, -0.18))
    ex = H.extinguisher("ext")
    H.hold_mid(ex, m, 160)
    bpy.context.view_layer.update()
    H.foam("foam", ex.matrix_world @ V((0, 0.4, 0.15)), V((0.25, -0.9, -0.35)), 2.2)
    SH.cam((3.8, 7.2, 1.7), (BX - 0.6, Y - 0.2, 1.05), 26)


ANIM = {
    1: anim_monza_pov, 25: anim_monza_pov,
    2: anim_wreck_close, 5: anim_wreck_close,
    3: anim_monza_wide,
    4: anim_launch,
    6: anim_halo_reveal,
    7: anim_fans,
    20: anim_landing_close, 21: anim_landing_close,
}


def build_people_shot(n):
    """Shots whose set and cast come from the storyboard builder (first key), animated from there."""
    table = {s[0]: s for s in SH.SHOTS}
    keys = table[n][3]
    if n == 17:
        return build_climb
    return keys.get("a") or keys.get("") or list(keys.values())[0]


# ---------------------------------------------------------------- object motion for prop shots
def prop_motion(n, f0, f1, dur, st):
    if n == 6:
        reveal_keys(st, f0, f1, dur)
        return
    if n == 7:
        # low on the inside of the track, looking across at the stand: the 2018 car with its halo sweeps through the
        # frame; then the camera pushes in and zooms to the tifosi booing and holding up UGLY and X signs
        car = st["car"]
        cam = Cam(30)
        for f, t in frames(f0, f1):
            y = st["y0"] + (st["y1"] - st["y0"]) * t / dur  # constant speed: it keeps moving through the cut
            car.location.y = y
            car.keyframe_insert("location", frame=f)
            z = smoother((t - 1.05) / (dur - 1.05))
            loc = lerp3((1.0, -17.5, 1.05), (11.5, -17.6, 2.75), z)
            tgt = lerp3((20.5, -17.3, 2.4), (20.7, -17.8, 3.25), z)
            pan = 0.9 * math.exp(-((t - 1.0) / 0.35) ** 2)  # a little whip with the car as it passes
            cam.key(f, loc + V((0, 0, 0.01 * math.sin(t * 7))), tgt + V((0, 1.5 * pan, 0)), 0, 30 + 32 * z)
        return
    sc = bpy.context.scene
    cam = sc.camera
    if n == 10:
        # the saw rides in his hands' frame (his body's), so the grip never stretches: from the case, lifted with
        # its weight in an arc, brought in to the chest as he rises and turns, then pushed out and up at the halo,
        # a small bob of follow-through as he stops
        saw = bpy.data.objects["saw"]
        w = st["wolff_pf"]
        L0 = w.body_M(w.pose(0.0)).inverted() @ st["saw0"]
        x0, y0, z0 = SH.LAUNCH_W
        # the aim pose: the saw placement nearest the intended one (out in front, pitched up at the halo) at which
        # both wrists - where they hold the saw, as cast - are within the rig's arm length of the shoulders
        bpy.context.view_layer.update()
        S0inv = st["saw0"].inverted()
        wl = {k: S0inv @ w.a.hand[k].matrix_world.translation for k in "LR"}
        pe_ = w.pose(dur)
        S1, _ = w._bend(pe_["lean"], pe_["twist"], pe_["side"], pe_["head"])
        bones = w.a.arm.data.bones
        sh = {k: S1 @ bones["upperarm." + k].head_local for k in "LR"}
        reach_ = {k: bones["upperarm." + k].length + bones["forearm." + k].length - 0.03 for k in "LR"}
        Binv = w.body_M(pe_).inverted()
        bl = V(w.base["loc"])  # where he really stands (the cast may have stepped him a few cm to reach the case)
        Mp = Matrix.Translation(V((bl.x, bl.y, z0))) @ Matrix.Rotation(D2R(st["aim_rot"]), 4, "Z")
        best = None
        for yv in (0.06, 0.1, 0.14, 0.18, 0.22, 0.26, 0.3, 0.34):
            for zv in (0.95, 1.0, 1.05, 1.1, 1.15):
                for pitch in (0, 6, 12, 18):
                    for yaw in range(-75, 76, 15):  # held across the body, bar out to one side, like a real saw
                        cand = Mp @ Matrix.Translation(V((0.0, yv, zv))) @ Matrix.Rotation(D2R(yaw), 4, "Z") @ Matrix.Rotation(D2R(pitch), 4, "X")
                        if all((Binv @ (cand @ wl[k]) - sh[k]).length <= reach_[k] for k in "LR"):
                            margin = min(reach_[k] - (Binv @ (cand @ wl[k]) - sh[k]).length for k in "LR")
                            cost = abs(yv - 0.42) + abs(zv - 1.12) + abs(pitch - 12) / 60 + abs(yaw) / 150 - min(margin, 0.05)
                            if best is None or cost < best[0]:
                                best = (cost, cand)
        c0 = Mp @ Matrix.Translation(V((0.0, 0.42, 1.12)))
        print("s10 aim saw", "found" if best else "NOT FOUND", "reach", {k: round(reach_[k], 3) for k in "LR"},
              "sh", {k: tuple(round(v, 2) for v in sh[k]) for k in "LR"},
              "wrist@default", {k: tuple(round(v, 2) for v in Binv @ (c0 @ wl[k])) for k in "LR"},
              "wl", {k: tuple(round(v, 2) for v in wl[k]) for k in "LR"}, flush=True)
        Mend = best[1] if best else Mp @ Matrix.Translation(V((0.0, 0.3, 1.0)))
        # the saw rides on his chest (it straightens up with him, so the arms never stretch), moving within that
        # frame from where it lay on the case to the aim
        X0, X2 = st["saw0"], w.carry_M(dur).inverted() @ Mend
        pe = None
        for f, t in frames(f0, f1):
            x = smoother((t - 0.25) / 1.35)
            dt = max(0.0, t - 1.6)
            bob = Matrix.Translation(V((0, 0, 0.018 * math.exp(-dt * 5) * math.sin(dt * 16))))
            pe = key_M(saw, f, bob @ w.carry_M(t) @ lerp_M(X0, X2, x), pe)
        _static_cam(cam, f0, f1, (-0.9, -2.9, 2.15), (0.75, 2.9, 1.25), (-0.75, -2.6, 2.1), (0.7, 2.9, 1.25))
        return
    if n == 11:
        pad, rod = bpy.data.objects["pr_pad"], bpy.data.objects["pr_rod"]
        z_up, z_dn = pad.location.z, st["press_contact"]
        rod_top = 2.9
        reads = st["reads"]
        for f, t in frames(f0, f1):
            x = ease(t, 0.2, 1.3)
            z = z_up + (z_dn - z_up) * x - 0.006 * ease(t, 1.3, 1.5) * (1 + 0.3 * math.sin(t * 40))
            pad.location.z = z
            pad.keyframe_insert("location", frame=f)
            zb = z + 0.05
            rod.scale.z = (rod_top - zb) / st["rod_len"]
            rod.location.z = (zb + rod_top) / 2
            rod.keyframe_insert("location", frame=f)
            rod.keyframe_insert("scale", frame=f)
            load = ease(t, 1.3, 2.0)
            idx = min(len(reads) - 1, int(load * (len(reads) - 1) + 1e-6))
            for i, grp in enumerate(reads):
                for o in grp:
                    o.hide_render = i != idx
                    o.keyframe_insert("hide_render", frame=f)
        _static_cam(cam, f0, f1, *SHOT11_CAM)
        return
    if n == 12:
        bus = bpy.data.objects["hg_bus"]
        moving = [bus] + [bpy.data.objects[o] for o in ("hg_spreader", "hg_cable-2.8", "hg_cable2.8")]
        main = bpy.data.objects["hg_cablemain"]
        z_rest = st["bus_rest"]
        top0 = {o.name: o.location.z for o in moving}
        drop = bus.location.z - z_rest
        bz0 = bus.location.z
        for f, t in frames(f0, f1):
            # lowered on the crane, slowing as it nears the halo; the touch-down: a small rebound up (never
            # through the halo) that dies away - it holds
            x = smoother(t / 1.0)
            settle = 0.03 * math.exp(-max(0, t - 1.0) * 7) * abs(math.sin(max(0, t - 1.0) * 14))
            dz = -drop * x + settle * (t > 1.0)
            for o in moving:
                o.location.z = top0[o.name] + dz
                o.keyframe_insert("location", frame=f)
            zs = top0["hg_spreader"] + dz + 0.15
            main.scale.z = (10.9 - zs) / st["main_len"]
            main.location.z = (10.9 + zs) / 2
            main.keyframe_insert("location", frame=f)
            main.keyframe_insert("scale", frame=f)
            # low by the stand, looking up at the bus coming down; tilts down with it to frame bus and halo together
            u = smoother(t / dur)
            tz = 0.6 * (bz0 + dz + 2.1) + 0.4 * 1.6
            cam.location = lerp3((-6.4, -10.8, 0.9), (-5.9, -10.2, 1.0), u)
            look_at(cam, V((0.0, 0.2, tz)))
            cam.keyframe_insert("location", frame=f)
            cam.keyframe_insert("rotation_euler", frame=f)
        return
    if n == 13:
        cars = [o for o in bpy.data.objects if o.parent is None and (o.name == "gro" or o.name.startswith("pk"))]
        y0 = {c.name: c.location.y for c in cars}
        for f, t in frames(f0, f1):
            for i, c in enumerate(cars):
                c.location.y = y0[c.name] + (24 + 0.8 * i) * t
                c.location.x += 0
                c.keyframe_insert("location", frame=f)
            g = bpy.data.objects["gro"].location
            cam.location = V((-8.4, -40 + 6 * t, 6.5))
            look_at(cam, V((0.5, g.y + 6, 0.5)))
            cam.keyframe_insert("location", frame=f)
            cam.keyframe_insert("rotation_euler", frame=f)
        return
    if n == 14:
        # flat out down the straight (~45 m/s), a sudden turn to the right across the track and into the steel:
        # the car follows one path (straight, then a curve that ends pointing at the barrier), its heading always
        # along the way it is moving; the chase camera keeps him in frame and brakes after the hit
        g = bpy.data.objects["gro"]
        others = [o for o in bpy.data.objects if o.parent is None and o.name.startswith("pk")]
        o0 = {o.name: o.location.copy() for o in others}
        BX = H.BARRIER_X
        hit = V((BX - 2.95, -2.0, 0))
        dirh = V((math.sin(D2R(62)), math.cos(D2R(62)), 0))  # heading at impact (yaw -62)
        c0, c1, c2 = V((0.6, -24.0, 0)), V((0.6, -14.0, 0)), hit - dirh * 4.0
        bez = [path_bezier(c0, c1, c2, hit, i / 200)[0] for i in range(201)]
        arc = [0.0]
        for a_, b_ in zip(bez, bez[1:]):
            arc.append(arc[-1] + (b_ - a_).length)
        T, vel = T14_HIT, 45.0
        fr_, re_ = st["front"], st["rear"]
        f_hit = f0 + round(T * FPS)
        for o in st["intact"] + st["torn"]:  # the barrier: intact until the hit, torn open and bent from then on
            for ff in (f_hit - 1, f_hit):
                o.hide_render = (ff >= f_hit) == (o in st["intact"])
                o.keyframe_insert("hide_render", frame=ff)
        pf_ = pr_ = None
        def car_at(t):
            s = vel * min(t, T) - vel * T + arc[-1]  # distance along the curve (negative: still on the straight)
            if s <= 0:
                return V((c0.x, c0.y + s, 0)), 0.0
            i = min(199, max(0, next((j for j in range(200) if arc[j + 1] >= s), 199)))
            u = (i + (s - arc[i]) / max(1e-9, arc[i + 1] - arc[i])) / 200
            p, d = path_bezier(c0, c1, c2, hit, u)
            return p, math.degrees(math.atan2(-d.x, d.y))
        pe = None
        cy = None
        for f, t in frames(f0, f1):
            if f < f_hit:
                p, yaw = car_at(t)
                M = M_of(p, yaw, 0, -4 * sstep((t - (T - 0.6)) / 0.4))  # rolls onto its outside wheels in the turn
                g.scale = (1, 1, 1)
                F, R = split_state(0.0)
                fr_.scale = re_.scale = (0.001, 0.001, 0.001)
            else:  # the hit: the car tears in two, the front half through the steel, the back half spinning away
                M = hit_M()
                g.scale = (0.001, 0.001, 0.001)
                F, R = split_state(t - T)
                fr_.scale = re_.scale = (1, 1, 1)
            pe = key_M(g, f, M, pe)
            g.scale = (0.001, 0.001, 0.001) if f >= f_hit else (1, 1, 1)
            g.keyframe_insert("scale", frame=f)
            pf_ = key_M(fr_, f, F, pf_)
            pr_ = key_M(re_, f, R, pr_)
            for o in (fr_, re_):
                o.scale = (0.001, 0.001, 0.001) if f < f_hit else (1, 1, 1)
                o.keyframe_insert("scale", frame=f)
            st["xp"].key(f, t - T)
            st.setdefault("dbr", ImpactDebris()).key(f, t - T)
            for i, o in enumerate(others):  # the cars around him (placed relative to him as on the board), racing on
                y_start = car_at(0.0)[0].y + (o0[o.name].y + 14.0)
                o.location = V((o0[o.name].x, y_start + (42.5 + 1.5 * i) * t, 0))
                o.keyframe_insert("location", frame=f)
            gp = M.translation
            # chase camera on its own smooth speed: matching him, then braking to a stop after the hit
            ct = min(t, 2.7)
            xb = min(1.0, max(0.0, (t - 2.7) / 0.9))
            cyy = c0.y + vel * ct - vel * T + arc[-1] - 9.0 + vel * 0.45 * (1 - (1 - xb) ** 2)
            dt = t - T  # the blast shakes the camera
            k = 0.12 * math.exp(-max(0.0, dt) * 3.5) * (dt > 0)
            jig = V((wob(t, 13, k), wob(t, 11, k * 0.7, 1), wob(t, 16, k, 2)))
            cam.location = V((-4.6, cyy, 2.2)) + jig  # along the left edge of the track, clear of the other cars
            look_at(cam, gp + V((0.4 + 1.2 * smoother(dt / 0.6), 2.0, 0.5 + 0.6 * smoother(dt / 0.6))), wob(t, 9, 30 * k))
            cam.keyframe_insert("location", frame=f)
            cam.keyframe_insert("rotation_euler", frame=f)
        return
    if n == 15:  # continues shot 14 from the frame it cut on: the halves still moving, the fireball dying into the fire
        fr, rr = bpy.data.objects["gro_front"], bpy.data.objects["gro_rear"]
        ts0 = shot_dur(14) - T14_HIT
        fires = [o for o in bpy.data.objects if "_f" in o.name and o.name.startswith("bh_fire")]
        fs0 = {o.name: (o.scale.copy(), o.location.copy()) for o in fires}
        dbr = ImpactDebris()
        pf_, pr_ = None, None
        for f, t in frames(f0, f1):
            ts = ts0 + t
            dbr.key(f, ts)
            F, R = split_state(ts)
            pf_ = key_M(fr, f, F, pf_)
            pr_ = key_M(rr, f, R, pr_)
            st["xp"].key(f, ts)
            for o in fires:
                s0, l0 = fs0[o.name]
                g_ = ease(t, 0.25 + 0.3 * ((hash(o.name) % 7) / 7), 0.8 + 0.3 * ((hash(o.name) % 5) / 5))
                o.scale = s0 * max(0.001, g_) * (1 + 0.15 * math.sin(t * 9 + hash(o.name) % 11) * g_)
                o.keyframe_insert("scale", frame=f)
        _static_cam(cam, f0, f1, (2.2, -12.0, 5.2), (7.0, -1.6, 0.6), (2.6, -11.0, 4.6), (7.2, -1.4, 0.7))
        return
    if n == 16:  # slow motion: the front half pushing through; the top rail rides up over the halo
        fr = bpy.data.objects["gro_front"]
        F1 = fr.matrix_world.copy()
        F0 = Matrix.Translation(V((-0.7, 0, 0))) @ F1
        rails = [bpy.data.objects[f"bent_rail{s}"] for s in (1, -1)]
        r1 = {o.name: (o.location.copy(), o.rotation_euler.copy()) for o in rails}
        pe = None
        for f, t in frames(f0, f1):
            x = ease(t, 0.0, 2.2)
            pe = key_M(fr, f, lerp_M(F0, F1, x), pe)
            for o, s in zip(rails, (1, -1)):
                l1, e1 = r1[o.name]
                l0 = V((H.BARRIER_X, s * 0.65, 1.09))
                o.location = l0.lerp(l1, x)
                o.rotation_euler = (e1.x * x, 0, 0)
                o.keyframe_insert("location", frame=f)
                o.keyframe_insert("rotation_euler", frame=f)
        _static_cam(cam, f0, f1, (6.25, -1.55, 1.5), (H.BARRIER_X + 0.12, 0.0, 0.98), (6.5, -1.3, 1.4), (H.BARRIER_X + 0.12, 0.0, 0.98))
        return
    if n == 19:
        h = bpy.data.objects["trophy_halo"]
        r0 = h.rotation_euler.z
        for f, t in frames(f0, f1):
            h.rotation_euler.z = r0 + D2R(28 * t / dur)
            h.keyframe_insert("rotation_euler", frame=f)
        _static_cam(cam, f0, f1, (1.5, -2.7, 2.35), (0, 0, 1.3), (1.0, -2.3, 2.1), (0, 0, 1.3))
        return
    if n in (20, 21):
        h, v = bpy.data.objects["ham"], bpy.data.objects["ver"]
        V1 = v.matrix_world.copy()
        if n == 20:  # the last half-metre in slow motion: accelerating down, the hit, a short recoil
            V0 = Matrix.Translation(V((0, 0, 0.45))) @ V1
            head = bpy.data.objects["ham_head"]
            h0 = head.rotation_euler.copy()
            pe = None
            for f, t in frames(f0, f1):
                x = min(1, (t / 2.2) ** 2)
                M = lerp_M(V0, V1, x)
                dt = t - 2.2
                if dt > 0:
                    M = Matrix.Translation(V((0, 0, 0.03 * math.exp(-dt * 7) * abs(math.sin(dt * 16))))) @ V1
                pe = key_M(v, f, M, pe)
                head.rotation_euler = (h0.x + D2R(8 * sstep((t - 2.1) / 0.1) * (1 - sstep((t - 2.6) / 0.6))), h0.y, h0.z)
                head.keyframe_insert("rotation_euler", frame=f)
                sh_ = 0.02 * math.exp(-max(0, dt) * 5) * (dt > 0)
                cam.location = st["cam0"] + V((wob(t, 9, sh_), wob(t, 7, sh_), wob(t, 8, sh_)))
                look_at(cam, st["camT"], 14)
                cam.keyframe_insert("location", frame=f)
                cam.keyframe_insert("rotation_euler", frame=f)
        else:
            V2 = st["ver_deflected"]
            pe = None
            for f, t in frames(f0, f1):
                x = ease(t, 0.15, 1.1)
                M = lerp_M(V1, V2, x)
                M = Matrix.Translation(V((0, 0, 0.08 * math.sin(math.pi * x)))) @ M  # rides up over the hoop
                pe = key_M(v, f, M, pe)
            _static_cam(cam, f0, f1, SH.tab((2.9, 2.9, 3.2)), SH.tab((0.1, 0.0, 0.95)), SH.tab((2.5, 2.4, 2.9)), SH.tab((0.1, 0.0, 0.95)))
        return
    # people shots: a slow, purposeful camera drift (no flashy moves)
    c0 = cam.matrix_world.translation.copy()
    fwd = -(cam.matrix_world.to_3x3() @ V((0, 0, 1)))
    tgt = c0 + fwd * (cam.data.dof.focus_distance if cam.data.dof.use_dof else 3.0)
    roll = sc.get("cam_roll", 0.0)
    _static_cam(cam, f0, f1, c0, tgt, c0 + fwd * 0.25, tgt, roll)


# shot 11: low and front-left, looking up into the press: the halo on its buck at the bottom, the ram above it and
# the load display on the beam at the top, all in one frame (slow push-in)
SHOT11_CAM = ((-1.1, -5.3, 1.35), (0.0, 0.0, 2.55), (-0.85, -4.75, 1.4), (0.0, 0.0, 2.5))


def carry_props(pfs, f0, f1, st, skip=()):
    """Props held in the hands (a helmet, a sign, the saw) ride with the chest of the person holding them, so the
    hands, which are attached to the prop, move with the body instead of being held still while it sways.
    Signs also wave: a rock about the hand, at the fan's own tempo once the car is level with them."""
    done = set()
    for pf in pfs:
        for k in "LR":
            prop = pf.a.hand[k].parent
            if prop is None or prop.name in done or prop.name in skip:
                continue
            done.add(prop.name)
            bpy.context.view_layer.update()
            M0 = prop.matrix_world.copy()
            grip0 = pf.a.hand[k].matrix_world.translation.copy()
            wave = st.get("wave", {}).get(pf.a.name) if prop.name.startswith("sign") else None
            lift = st.get("lift", {}).get(prop.name)
            r = D2R(pf.base["rot"])
            fwd = V((-math.sin(r), math.cos(r), 0))
            pe = None
            for f, t in frames(f0, f1):
                M = pf.carry_M(t) @ M0
                if wave:
                    delay, tempo, i = wave
                    pump = smoother((t - 0.9 - delay) / 0.6)
                    a = D2R(9 * pump * math.sin(2 * math.pi * tempo * t + i + 0.4))
                    g = pf.carry_M(t) @ grip0
                    M = Matrix.Translation(g) @ Matrix.Rotation(a, 4, fwd) @ Matrix.Translation(-g) @ M
                if lift:
                    M = Matrix.Translation(V((0, 0, lift(t)))) @ M
                pe = key_M(prop, f, M, pe)


# ---------------------------------------------------------------- Bahrain: the impact (shots 14 and 15 share it)
T14_HIT = 3.0  # shot 14: the instant the nose meets the steel (shot time)
HIT_M = None


def hit_M():
    BX = H.BARRIER_X
    return M_of((BX - 2.95, -2.0, 0), -62)


def split_state(ts):
    """The two halves ts seconds after the impact: the front half carries on through the torn barrier, braking
    hard in the steel; the back half is thrown back and spins away, bouncing, to where it burns (shot 15)."""
    BX = H.BARRIER_X
    F_end = M_of((BX, 0.0, 0.0), -90)
    R_end = M_of((BX - 3.4, -3.0, 0.2), -150, 0.0, 8)
    Mi = hit_M()
    xf = 1 - (1 - min(1.0, max(0.0, ts) / 0.35)) ** 3
    F = lerp_M(Mi, F_end, xf)
    F = F @ Euler((D2R(-5 * math.sin(math.pi * xf)), 0, 0)).to_matrix().to_4x4()  # the nose digs in, rocks back
    xr = 1 - (1 - min(1.0, max(0.0, ts) / 1.6)) ** 2
    R = lerp_M(Mi, R_end, xr)
    R = Matrix.Translation(V((0, 0, 0.6 * abs(math.sin(math.pi * min(1.0, xr * 1.6))) * (1 - xr)))) @ R
    return F, R


class Explosion:
    """A fireball at the impact: glowing blocks bursting out (hot cores, orange body, embers), lifting and slowly
    dying down into the fire; dark smoke blocks rising after; a flash of light. Keyed on the time since impact."""

    def __init__(self, name, center, seed=3):
        import random
        rnd = random.Random(seed)
        M = palette()
        self.c = V(center)
        self.parts = []
        for i in range(80):
            d = V((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.2, 1))).normalized()
            r = rnd.uniform(0.3, 2.3)
            s = rnd.choice([0.18, 0.27, 0.36, 0.45])
            m = M["fire2"] if r < 0.9 else (M["fire"] if rnd.random() < 0.75 else M["ember"])
            self.parts.append((box(f"{name}{i}", (s, s, s), (0, 0, -50), m), d, r, rnd.uniform(0, 6.28), "fire"))
        for i in range(24):
            d = V((rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), 1)).normalized()
            self.parts.append((box(f"{name}_smoke{i}", (0.5, 0.5, 0.5), (0, 0, -50), M["soot"]), d, rnd.uniform(1.0, 3.5),
                               rnd.uniform(0, 6.28), "smoke"))
        lt = bpy.data.lights.new(name + "_flash", "POINT")
        lt.color, lt.shadow_soft_size = (1.0, 0.55, 0.2), 1.5
        self.light = link(bpy.data.objects.new(name + "_flash", lt))
        self.light.location = self.c + V((0, 0, 1.0))

    def key(self, f, ts):
        for o, d, r, ph, kind in self.parts:
            if ts < 0:
                o.location, o.scale = self.c, (0.001, 0.001, 0.001)
            elif kind == "fire":
                grow = 1 - math.exp(-ts * 9)
                o.location = self.c + d * r * grow + V((0, 0, 0.7 * ts))
                k = smoother(ts / 0.05) * (1 - 0.65 * smoother((ts - 0.35) / 1.4)) * (1 + 0.15 * math.sin(ts * 23 + ph))
                o.scale = (max(0.001, k),) * 3
            else:
                x = smoother((ts - 0.2) / 0.6)
                o.location = self.c + d * r * x + V((0, 0, 1.2 * ts))
                o.scale = (max(0.001, x * (0.8 + 0.4 * math.sin(ph))),) * 3
            o.keyframe_insert("location", frame=f)
            o.keyframe_insert("scale", frame=f)
        e = 0.0 if ts < 0 else 80000 * math.exp(-ts * 6) + 6000 * smoother(ts / 0.1)
        self.light.data.energy = e
        self.light.data.keyframe_insert("energy", frame=f)


class ImpactDebris:
    """Bodywork thrown out of the impact (the 'dbr' blocks lying on the run-off in shot 15): from the hit they
    fly out and land where they lie. Same pieces and clock in shots 14 and 15."""

    def __init__(self):
        import random
        self.deb = [o for o in bpy.data.objects if o.name.startswith("dbr")]
        self.end = {o.name: o.location.copy() for o in self.deb}
        rnd = random.Random(3)
        self.v = {o.name: V((rnd.uniform(-3, 1), rnd.uniform(-3, 2), rnd.uniform(1.5, 3.5))) for o in self.deb}

    def key(self, f, ts):
        p0 = V((H.BARRIER_X - 0.5, -0.2, 0.5))
        for o in self.deb:
            tt = min(max(ts, 0.0), 0.75)
            v = self.v[o.name]
            pos = p0 + V((v.x * tt, v.y * tt, v.z * tt - 4.9 * tt * tt))
            pos.z = max(self.end[o.name].z, pos.z)
            o.location = pos.lerp(self.end[o.name], ease(ts, 0.6, 0.9))
            o.scale = (1, 1, 1) if ts >= 0 else (0.001, 0.001, 0.001)
            o.keyframe_insert("location", frame=f)
            o.keyframe_insert("scale", frame=f)


def build_impact(st, shot):
    """Shot 14: the halves, the torn barrier and the fireball, waiting for the impact. Shot 15: the fireball only
    (the halves and the torn barrier are its set)."""
    BX = H.BARRIER_X
    if shot == 14:
        M = palette()
        st["front"] = H.gro_car("gro_front", part="front")
        st["rear"] = H.gro_car("gro_rear", part="rear")
        for o in st["rear"].children_recursive:
            if o.type == "MESH" and o.material_slots and o.material_slots[0].material == M["white"]:
                o.material_slots[0].material = M["soot"]
        before = {o.name for o in bpy.data.objects}
        H.armco("bh_armcoT", -60, 60, BX, gap=(-1.2, 1.2), top_bent=True)
        SH.bent_top_rail()
        st["torn"] = [o for o in bpy.data.objects if o.name not in before]
        st["intact"] = [o for o in bpy.data.objects if o.name.startswith("bh_armco_")]
        H.debris("dbr", (BX - 2.5, -1.8), 18, 2.2)  # the same pieces shot 15 has lying on the run-off
    st["xp"] = Explosion("bh_xp", (BX - 0.4, -0.7, 0.4))


def animate_bobs(f0, f1):
    """The cut-out crowds jump up and down, each card at its own tempo, on the film's clock (frame / FPS) so they
    carry straight across cuts; tempos are whole cycles per minute so they also run through the 60 s loop."""
    obs = [o for o in bpy.data.objects if o.get("bob")]
    for o in obs:
        ph, amp, fr = o["bob"]
        fr = max(1, round(fr * 60)) / 60.0
        z0 = o.location.z
        for f, _ in frames(f0, f1):
            T = f / FPS
            o.location.z = z0 + amp * (0.5 - 0.5 * math.cos(2 * math.pi * fr * T + ph))
            o.keyframe_insert("location", index=2, frame=f)
        o.location.z = z0


def _static_cam(cam, f0, f1, l0, t0_, l1, t1_, roll=0.0):
    for f, t in frames(f0, f1):
        x = sstep((f - f0) / max(1, f1 - f0))
        cam.location = V(l0).lerp(V(l1), x)
        look_at(cam, V(t0_).lerp(V(t1_), x), roll)
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)


# ---------------------------------------------------------------- per-shot extra setup for prop shots
def prop_setup(n, st):
    if n == 11:
        bpy.data.objects["pr_pad"].location.z  # built at ram=0 below
    return st


def build_prop_shot(n):
    st = {}
    if n == 11:
        top = H.press_set(ram=0.0, reading="")
        st["press_contact"] = top + 0.05 + 0.05
        rod = bpy.data.objects["pr_rod"]
        st["rod_len"] = rod.dimensions.z
        st["reads"] = []
        mat_ = mat("readout", (0.2, 1, 0.4), 0.3, emit=(0.2, 1, 0.4), emit_strength=4)
        for i, txt in enumerate(("0t", "3t", "6t", "9t", "12t")):
            st["reads"].append(digits(f"pr_read{i}", txt, H.READOUT, "x", "z", 0.1, mat_, 0.012))
        SH.cam(SHOT11_CAM[0], SHOT11_CAM[1], 24)
    elif n == 12:
        top = H.hangar_set(drop=0.0)
        st["bus_rest"] = top - 0.2
        st["main_len"] = bpy.data.objects["hg_cablemain"].dimensions.z
        SH.cam((-6.4, -10.8, 0.9), (0.0, 0.2, 6.0), 22)
    elif n in (20, 21):
        H.monza_set()
        h, v = H.monza_cars()
        if n == 21:
            V1 = v.matrix_world.copy()
            v.rotation_euler.z += D2R(14)
            H.place_point(v, H.REAR_WHEEL, (0.42, -0.65, 0.66 + 0.37 + 0.6))
            H.settle(v, h, drop=1.4)
            st["ver_deflected"] = SH.tab_M() @ v.matrix_world
            set_M(v, V1)
        for c in (h, v):
            SH.move_group(c, SH.tab_M())
        if n == 20:
            st["cam0"], st["camT"] = V(SH.tab((-0.62, 1.05, 0.66))), V(SH.tab((0.05, 0.1, 1.55)))
            SH.cam(st["cam0"], st["camT"], 18, None, 2.8, 14)
        else:
            SH.cam(SH.tab((2.9, 2.9, 3.2)), SH.tab((0.1, 0.0, 0.95)), 28)
    return st


PROP_SHOTS = {11, 12}
SET_SHOTS = {13: "", 14: "a", 15: "b", 16: "", 19: ""}


# ---------------------------------------------------------------- one shot
def bake_shot(n, out_dir):
    table = {s[0]: s for s in SH.SHOTS}
    _, t0, t1, keys, desc = table[n]
    reset()
    lib.STYLE["voxel"], lib.STYLE["low"] = True, 0
    setup_render(1080, 1920, 16, "//frames/f")
    rig.calibrate()
    f0, f1 = round(t0 * FPS), round(t1 * FPS)
    dur = t1 - t0
    st = {}
    if n in ANIM and n not in (6, 7):
        ANIM[n](n, f0, f1, dur)
        voxel.voxelize_scene()
        perf, pfs = {}, []
    else:
        if n in (6, 7):
            st = ANIM[n](n, f0, f1, dur)
        elif n in PROP_SHOTS:
            st = build_prop_shot(n)
        elif n in SET_SHOTS:
            k = SET_SHOTS[n]
            keys[k]()
            if n in (14, 15):
                build_impact(st, n)
        else:
            build_people_shot(n)()
        voxel.voxelize_scene()
        perf = rig_cast()
        pfs = shot_people(n, perf, f0, f1, dur, st) if perf else []
        if pfs:
            carry_props(pfs, f0, f1, st, skip=("saw",) if n == 10 else ())
        prop_motion(n, f0, f1, dur, st)
        if pfs:
            choreo.bake(pfs, f0, f1)
    animate_bobs(f0, f1)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = f0, f1 - 1
    sc["shot"] = n
    sc["desc"] = desc
    for img in bpy.data.images:
        if img.source == "FILE" and not img.packed_file:
            try:
                img.pack()
            except RuntimeError:
                pass
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"s{n:02d}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    print(f"BAKED s{n:02d} frames {f0}-{f1 - 1} -> {path}", flush=True)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:]
    out = argv[0]
    ids = [int(a) for a in argv[1:]] or [s[0] for s in SH.SHOTS]
    for n in ids:
        try:
            bake_shot(n, out)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"BAKE s{n:02d} FAILED: {e}", flush=True)
