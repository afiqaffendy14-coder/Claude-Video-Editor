"""Inverse kinematics for the static block people (voxel.block_person): find the arm or leg angles that put a hand
(or an ankle) exactly on a world point, so storyboard poses have real contact - a hand on a rail, both hands on a
chainsaw's handles, a foot on a step. Same joint maths as block_person; solved with a small Nelder-Mead search.

    pose = ik.reach(pose, loc, rot, hands={"R": (x, y, z)}, feet={"L": (x, y, z)})
"""
import math
from mathutils import Vector, Matrix

V = Vector
PX = 0.045
W, H, T = 9 * PX, 12 * PX, 4 * PX
LEG = 9 * PX + 8 * PX + 2 * PX
STAND = dict(crouch=0, lean=0, twist=0, head=(0, 0), armL=(0, 6, 0), armR=(0, 6, 0), legL=(0, 2, 0), legR=(0, 2, 0))


def R(axis, deg):
    return Matrix.Rotation(math.radians(deg), 3, axis)


def frames(p):
    T_ = R("Z", p["twist"]) @ R("X", -p["lean"])
    Th = R("Z", p["twist"] * 0.3)
    pelvis = V((0, 0, LEG - p["crouch"]))
    return T_, Th, pelvis


def hand_local(p, k, ang):
    """Hand-block centre in the person's frame for arm angles ang = (fwd, side, elbow)."""
    T_, _, pelvis = frames(p)
    s = 1 if k == "L" else -1
    fwd, side, elbow = ang[:3]
    tw = ang[3] if len(ang) > 3 else 0.0
    sh = pelvis + T_ @ V((s * (W / 2 + T / 2), 0, H - T / 2))
    Ra = T_ @ R("X", fwd) @ R("Y", -s * side) @ R("Z", s * tw)
    el = sh + Ra @ V((0, 0, -6 * PX))
    Rf = Ra @ R("X", elbow)
    wr = el + Rf @ V((0, 0, -4 * PX))
    return wr + Rf @ V((0, 0, -1.1 * PX))


def ankle_local(p, k, ang):
    _, Th, pelvis = frames(p)
    s = 1 if k == "L" else -1
    lf, lside, knee = ang
    hp = pelvis + Th @ V((s * W / 4, 0, 0))
    Rl = Th @ R("X", lf) @ R("Y", -s * lside)
    kn = hp + Rl @ V((0, 0, -9 * PX))
    Rs = Rl @ R("X", -knee)
    return kn + Rs @ V((0, 0, -8 * PX))


def to_local(loc, rot, scale, w):
    M = Matrix.Translation(V(loc)) @ Matrix.Rotation(math.radians(rot), 4, "Z") @ Matrix.Scale(scale, 4)
    return M.inverted() @ V(w)


def nelder_mead(f, x0, step=20.0, iters=260):
    n = len(x0)
    pts = [list(x0)] + [[x0[j] + (step if j == i else 0) for j in range(n)] for i in range(n)]
    vals = [f(p) for p in pts]
    for _ in range(iters):
        order = sorted(range(n + 1), key=lambda i: vals[i])
        pts, vals = [pts[i] for i in order], [vals[i] for i in order]
        c = [sum(p[j] for p in pts[:-1]) / n for j in range(n)]
        xr = [c[j] + (c[j] - pts[-1][j]) for j in range(n)]
        fr = f(xr)
        if fr < vals[0]:
            xe = [c[j] + 2 * (c[j] - pts[-1][j]) for j in range(n)]
            fe = f(xe)
            pts[-1], vals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < vals[-2]:
            pts[-1], vals[-1] = xr, fr
        else:
            xc = [c[j] + 0.5 * (pts[-1][j] - c[j]) for j in range(n)]
            fc = f(xc)
            if fc < vals[-1]:
                pts[-1], vals[-1] = xc, fc
            else:
                for i in range(1, n + 1):
                    pts[i] = [pts[0][j] + 0.5 * (pts[i][j] - pts[0][j]) for j in range(n)]
                    vals[i] = f(pts[i])
        if vals[-1] - vals[0] < 1e-10:
            break
    i = min(range(n + 1), key=lambda i: vals[i])
    return pts[i], vals[i]


def _solve(fk, target, start, limits):
    def cost(a):
        pen = sum(max(0, lo - v) ** 2 + max(0, v - hi) ** 2 for v, (lo, hi) in zip(a, limits)) * 1e-3
        return (fk(a) - target).length_squared + pen
    best = None
    n = len(limits)
    start = list(start)[:n] + [0.0] * (n - len(start))
    seeds = [start, [start[0] + 40, start[1], start[2] + 30] + start[3:], [start[0] - 30, start[1] + 20, start[2] + 60] + start[3:],
             [80, -20, 100] + [40] * (n - 3), [80, -20, 100] + [-40] * (n - 3), [120, 10, 120] + [0] * (n - 3)]
    for s0 in seeds:
        a, c = nelder_mead(cost, list(s0), iters=400)
        a, c = nelder_mead(cost, a, step=4.0, iters=300)
        if best is None or c < best[1]:
            best = (a, c)
        if c < 1e-6:
            break
    return tuple(best[0]), math.sqrt(best[1])


def _grid_solve(fk, target, limits, prefer, step=6):
    """Exhaustive coarse grid over the joint ranges, then a fine local search from the best few cells. Among
    equally good answers it keeps the one closest to the preferred angles (the pose as drawn)."""
    import itertools
    grids = [range(int(lo), int(hi) + 1, step) for lo, hi in limits]
    cands = []
    for a in itertools.product(*grids):
        e = (fk(a) - target).length
        if e < 0.12:
            cands.append((e + sum(abs(x - y) for x, y in zip(a, prefer)) * 1e-5, a))
    cands.sort()
    best = None
    for _, a in cands[:6]:
        a2, c = nelder_mead(lambda v: (fk(v) - target).length_squared +
                            sum(max(0, lo - x) ** 2 + max(0, x - hi) ** 2 for x, (lo, hi) in zip(v, limits)) * 1e-3,
                            list(a), step=3.0, iters=300)
        if best is None or c < best[1]:
            best = (a2, c)
    if best is None:
        return tuple(prefer), 9.0
    return tuple(best[0]), math.sqrt(best[1])


ARM_LIM = [(-60, 200), (-60, 100), (0, 150), (-90, 90)]  # fwd, side, elbow, twist
LEG_LIM = [(-60, 130), (-20, 60), (0, 150)]
LU, LF = 6 * PX, 5.1 * PX  # shoulder -> elbow, elbow -> hand centre


def arm_exact(p, k, tgt):
    """Exact arm angles (fwd, side, elbow, twist) putting the hand centre on tgt (person frame), or None.
    The elbow bend comes from the triangle; the upper arm lies on the cone of directions that allow it; the twist
    turns the forearm onto the target. Among the exact solutions it keeps the most natural one: elbow low and out to
    the side, joints inside their limits."""
    T_, _, pelvis = frames(p)
    s = 1 if k == "L" else -1
    sh = pelvis + T_ @ V((s * (W / 2 + T / 2), 0, H - T / 2))
    d_vec = tgt - sh
    d = d_vec.length
    if d > LU + LF - 1e-4 or d < abs(LU - LF) + 1e-4:
        return None
    e = math.degrees(math.acos(max(-1, min(1, (d * d - LU * LU - LF * LF) / (2 * LU * LF)))))
    alpha = math.acos(max(-1, min(1, (LU * LU + d * d - LF * LF) / (2 * LU * d))))  # angle between upper arm and target
    t = d_vec.normalized()
    a = t.orthogonal().normalized()
    b = t.cross(a)
    Tinv = T_.inverted()
    best = None
    for i in range(72):
        phi = i * math.pi / 36
        u = (t * math.cos(alpha) + (a * math.cos(phi) + b * math.sin(phi)) * math.sin(alpha)).normalized()
        ul = Tinv @ u  # (s sin side, cos side sin fwd, -cos side cos fwd)
        side = math.degrees(math.asin(max(-1, min(1, s * ul.x))))
        fwd = math.degrees(math.atan2(ul.y, -ul.z))
        if not (ARM_LIM[0][0] <= fwd <= ARM_LIM[0][1] and ARM_LIM[1][0] <= side <= ARM_LIM[1][1]):
            continue
        elbow_pt = sh + u * LU
        want = (tgt - elbow_pt).normalized()
        tw_best, err_best = None, 9
        for tw in range(-120, 121, 3):
            f = hand_local(p, k, (fwd, side, e, tw))
            err = (f - tgt).length
            if err < err_best:
                tw_best, err_best = tw, err
        lo, hi = tw_best - 3, tw_best + 3
        for _ in range(30):  # refine the twist
            m1, m2 = lo + (hi - lo) / 3, hi - (hi - lo) / 3
            if (hand_local(p, k, (fwd, side, e, m1)) - tgt).length < (hand_local(p, k, (fwd, side, e, m2)) - tgt).length:
                hi = m2
            else:
                lo = m1
        tw = (lo + hi) / 2
        err = (hand_local(p, k, (fwd, side, e, tw)) - tgt).length
        if err > 0.004:
            continue
        outward = s * (Tinv @ (elbow_pt - sh)).x
        score = (elbow_pt.z - sh.z) * 2.0 - outward * 1.0 + abs(tw) / 300.0  # low, out to the side, little twist
        if best is None or score < best[0]:
            best = (score, (fwd, side, e, tw))
    return best[1] if best else None


def reach(pose, loc, rot, hands=None, feet=None, scale=1.0, tol=0.02):
    """Return a copy of pose with arm/leg angles that put each named hand centre / ankle on its world target.
    Raises if a target is out of reach (more than tol away): move the person rather than stretch the arm."""
    p = {**STAND, **(pose or {})}
    p = dict(p)
    for k, w in (hands or {}).items():
        tgt = to_local(loc, rot, scale, w)
        a = arm_exact(p, k, tgt)
        if a is None:
            a, err = _solve(lambda ang: hand_local(p, k, ang), tgt, p["arm" + k], ARM_LIM)
            if err > tol:
                sh_d = (tgt - (frames(p)[2] + frames(p)[0] @ V(((1 if k == "L" else -1) * (W / 2 + T / 2), 0, H - T / 2)))).length
                raise ValueError(f"hand {k} can't reach {tuple(round(v, 3) for v in w)} (off by {err:.3f} m; "
                                 f"{sh_d:.2f} m from the shoulder, arm reaches {LU + LF:.2f})")
        p["arm" + k] = a
    for k, w in (feet or {}).items():
        tgt = to_local(loc, rot, scale, w)
        a, err = _grid_solve(lambda ang: ankle_local(p, k, ang), tgt, LEG_LIM, p["leg" + k])
        if err > tol:
            raise ValueError(f"foot {k} can't reach {tuple(round(v, 3) for v in w)} (off by {err:.3f} m)")
        p["leg" + k] = a
    return p


def hand_world(pose, loc, rot, k, scale=1.0):
    p = {**STAND, **(pose or {})}
    M = Matrix.Translation(V(loc)) @ Matrix.Rotation(math.radians(rot), 4, "Z") @ Matrix.Scale(scale, 4)
    return M @ hand_local(p, k, p["arm" + k])
