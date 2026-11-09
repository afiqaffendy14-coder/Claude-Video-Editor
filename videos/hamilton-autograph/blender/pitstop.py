"""The pit stop, staged for the rigged crew. One stop clock q drives everything, so every pit shot shows a
consistent moment of the same stop:

  q < 0      car rolling into the box (shot 15), crew poised, guns raised, new tyres held ready
  0 .. .02   car lifts on the jacks, guns onto the nuts
  .02 - .12  guns rattle the nuts off
  .12 - .18  guns lift clear (up, out of the wheel's way)
  .14 - .32  tyre-off men pull the old wheels straight out
  .32 - .55  ...and carry them aside, stepping back with them
  .45 - .70  tyre-on men push the new tyres onto the hubs, stepping in with them
  .72 - .79  guns back on the nuts, .79 - .90 rattle them tight
  .93 - 1.0  guns lift away;  .97 - 1.03 car drops;  > 1.0 jack pulled clear

Stations are solved from the hand-hold points (arms are short: wrist within ~0.42 m of the shoulder), and
everybody has a clear patch of floor: gun man kneels square to the wheel, tyre-off man forward-outboard of him,
tyre-on man aft-outboard, wing men kneel in front of the wing, jack men on the levers, lollipop man ahead.
"""
import math
import bpy
from mathutils import Vector, Matrix
from choreo import ease, sstep, wob, FPS

V = Vector
PELVIS, SPINE, SH_W = 0.855, 0.45, 0.292
CORNERS = [("FL", 1, 1, "car_wf1"), ("FR", -1, 1, "car_wf-1"), ("RL", 1, -1, "car_wr1"), ("RR", -1, -1, "car_wr-1")]
SPANS = {2: (0.05, 0.55), 16: (0.4, 0.75), 17: (0.2, 0.62), 18: (0.5, 0.92), 19: (0.78, 1.08), 23: (0.8, 0.88),
         24: (0.84, 0.95), 15: (-1.0, 0.0)}


# ---------------------------------------------------------------- geometry helpers
def heading_of(rot):
    r = math.radians(rot)
    return V((-math.sin(r), math.cos(r), 0))


def right_of(rot):
    r = math.radians(rot)
    return V((math.cos(r), math.sin(r), 0))


def rot_toward(frm, to):
    d = V(to) - V(frm)
    return math.degrees(math.atan2(-d.x, d.y))


def shoulders(root, rot, crouch, lean):
    hd, rt = heading_of(rot), right_of(rot)
    base = V((root[0], root[1], PELVIS - crouch + SPINE * math.cos(math.radians(lean)))) + hd * SPINE * math.sin(math.radians(lean))
    return {"L": base + rt * SH_W, "R": base - rt * SH_W}


def solve_root(grips, rot, crouch, lean, near, reach=0.37, keep_out=None):
    """Root position (on the floor) from which both wrists sit ~reach from their shoulders."""
    best, bp = 1e9, V(near)
    for i in range(-24, 25):
        for j in range(-24, 25):
            p = V((near[0] + i * 0.025, near[1] + j * 0.025, 0))
            if keep_out and not keep_out(p):
                continue
            S = shoulders(p, rot, crouch, lean)
            e = sum(((S[k] - V(grips[k])).length - reach) ** 2 for k in grips) + 0.02 * (p - V(near)).length ** 2
            if max((S[k] - V(grips[k])).length for k in grips) > 0.43:
                e += 10
            if e < best:
                best, bp = e, p
    return bp


def match_lr(local, world, rot):
    """Give each hand the hold on its own side of the body (no crossed arms)."""
    rt = right_of(rot)
    if (world["L"] - world["R"]).dot(rt) < 0:
        return {"L": local["R"], "R": local["L"]}, {"L": world["R"], "R": world["L"]}
    return local, world


def hub(s, f, lift=0.0, car_y=0.0):
    return V((s * (0.8 if f > 0 else 0.78), (1.8 if f > 0 else -1.78) + car_y, 0.43 + lift))


# ---------------------------------------------------------------- the stop clock
def lift(q):
    return 0.07 * ease(q, -0.03, 0.02) * (1 - ease(q, 0.97, 1.03))


def car_y(q):
    return -2.6 * (min(0.0, q) ** 2) if q < 0 else 0.0  # rolls in, decelerating to a stop at q = 0


GUN_X, GUN_DY = 1.56, -0.32  # gun man kneels outboard and aft of the hub...
GUN_YAW = 25.0               # ...with the gun angled onto the nut, leaving the wheel's front half to the tyre-off man


def gun_dir(s, f):
    """Unit vector from the nut out along the gun (towards the gun man)."""
    a = math.radians(GUN_YAW)
    return V((s * math.cos(a), -f * math.sin(a), 0))


def gun_yaw(s, f):
    d = -gun_dir(s, f)  # the nose points back at the nut
    return math.atan2(-d.x, d.y)


def gun_pos(s, f, q, t):
    """Wheel gun centre and pitch: upright in front of the chest (ready, and while the wheels change), level on the
    nut while it spins the nut off/on. Returns (location, pitch, rattling)."""
    h = hub(s, f, lift(q), car_y(q))
    on = h + V((s * 0.095, 0, 0)) + gun_dir(s, f) * 0.27
    hs = V((s * GUN_X, hub(s, f).y + f * GUN_DY, 0))
    up = hs + (hub(s, f) - hs).normalized() * 0.3 + V((0, 0, 1.2))  # held up in front of his face, above the wheel's path
    a = ease(q, -0.06, 0.0) * (1 - ease(q, 0.12, 0.18)) + ease(q, 0.74, 0.8) * (1 - ease(q, 0.93, 1.0))
    p = up.lerp(on, a)
    rattle = (0.0 < q < 0.12) or (0.8 < q < 0.9)
    if rattle:
        p = p + V((0, 0, 0.004 * math.sin(2 * math.pi * 14 * t)))
    return p, math.radians(90) * (1 - a), rattle


def old_wheel_pos(s, f, q):
    h = hub(s, f, lift(q) * (1 - ease(q, 0.16, 0.3)) + 0.07 * ease(q, 0.16, 0.3), car_y(q))  # off the car: no longer rides the jacks
    out = ease(q, 0.16, 0.3)     # straight off the hub (inner edge clears the front wing's endplate)
    along = ease(q, 0.24, 0.5)   # then along the car, away from the gun man...
    away = ease(q, 0.42, 0.58)   # ...and out to the side
    lift_up = ease(q, 0.36, 0.55)  # lifted to carry, once clear of the gun man's arms
    return h + V((s * 0.34 * out, 0, 0)) + V((0, f * 1.0, 0)) * along + V((s * 0.26, 0, 0)) * away + V((0, 0, 0.17 * lift_up))


def new_tyre_pos(s, f, q):
    h = hub(s, f, lift(q), car_y(q))
    wait = V((s * (1.25 + 0.3 * (1 - ease(q, -0.25, 0.0))), hub(s, f).y - f * 1.05, 0.45))  # waits at its station (further out while the car rolls in)
    x = ease(q, 0.45, 0.7)
    p = wait.lerp(h, x)
    return p + V((0, 0, 0.05 * math.sin(math.pi * x)))  # a little lift as it swings on


# ---------------------------------------------------------------- staging
def remove_tree(name):
    ob = bpy.data.objects.get(name)
    if ob:
        for o in [ob] + list(ob.children_recursive):
            bpy.data.objects.remove(o, do_unlink=True)


def key(ob, f, loc=None, rot=None):
    if loc is not None:
        ob.location = loc
        ob.keyframe_insert("location", frame=f)
    if rot is not None:
        ob.rotation_euler = rot
        ob.keyframe_insert("rotation_euler", frame=f)


def detach(ob):
    bpy.context.view_layer.update()
    mw = ob.matrix_world.copy()
    ob.parent = None
    ob.matrix_world = mw


def grip_point(ob, local):
    """An empty fixed to a prop at a local offset: hands parent to these, so they hold the prop at that spot."""
    e = bpy.data.objects.new(ob.name + "_hold", None)
    bpy.context.scene.collection.objects.link(e)
    e.empty_display_size = 0.02
    e.parent = ob
    e.location = local
    return e


class Station:
    """Moves a performer between stances (root, heading, crouch, lean) with planted steps in between."""

    def __init__(self, pf, stances, step_len=0.36):
        """stances: [(t_start_of_move, t_end_of_move, root, rot, crouch, lean)], first one is where they begin."""
        self.pf, self.st = pf, stances
        r0, rot0 = stances[0][2], stances[0][3]
        pf.base.update(loc=list(r0), rot=rot0, crouch=stances[0][4], lean=stances[0][5], twist=0)
        pf.a.place(V((r0[0], r0[1], 0)), rot0, stances[0][4])
        rt = right_of(rot0)
        pf.foot_world = {k: V((r0[0], r0[1], 0.09)) + rt * (0.1 if k == "L" else -0.1) for k in "LR"}
        pf.steps = []
        pf.lift = 0.09
        prev = stances[0]
        for st in stances[1:]:
            ta, tb, root, rot = st[0], st[1], V(st[2]), st[3]
            d = (root - V(prev[2])).length
            if d < 0.05:
                prev = st
                continue
            n = max(1, math.ceil(d / step_len))
            rt = right_of(rot)
            for i in range(n + 1):  # alternate feet, the last step brings the feet together under the new stance
                u = (i + 1) / (n + 1)
                k = "LR"[i % 2]
                pos = V(prev[2]).lerp(root, min(1.0, u * 1.15))
                t_up = ta + (tb - ta) * i / (n + 1)
                t_land = t_up + (tb - ta) / (n + 1) * 1.1
                tgt = V((pos.x, pos.y, 0.09)) + rt * (0.1 if k == "L" else -0.1)
                if i == n:
                    tgt = V((root.x, root.y, 0.09)) + rt * (0.1 if k == "L" else -0.1)
                pf.step_to(k, t_up, min(t_land, tb + 0.05), tgt)
            prev = st
        pf.path = self.path
        c0, l0 = stances[0][4], stances[0][5]

        def fx(t, p):
            _, _, c, l = self.stance(t)
            p["crouch"] += c - c0
            p["lean"] += l - l0
        pf.extra.insert(0, fx)

    def stance(self, t):
        cur = list(self.st[0][2:])
        for st in self.st[1:]:
            x = ease(t, st[0], st[1])
            if x <= 0:
                break
            cur = [V(cur[0]).lerp(V(st[2]), x), cur[1] + (st[3] - cur[1]) * x, cur[2] + (st[4] - cur[2]) * x,
                   cur[3] + (st[5] - cur[3]) * x]
        return V(cur[0]), cur[1], cur[2], cur[3]

    def path(self, t):
        r, rot, _, _ = self.stance(t)
        return V((r.x, r.y, 0)), rot


def stage(n, perf, f0, f1, dur, frames, hold_fn):
    """Re-stage the crew of a pit shot. hold_fn(pf, k, ob) grips a hand to an object."""
    P = perf.get
    span = SPANS.get(n)
    if span is None:
        return
    p0, p1 = span
    q_of = lambda t: p0 + (p1 - p0) * t / dur
    t_of = lambda q: (q - p0) / (p1 - p0) * dur
    car = bpy.data.objects.get("car")
    for nm in ("stab1", "stab-1"):  # no stabilisers: it gives every corner crew room to work
        if nm in perf:
            remove_tree(nm)
            for k in ("hand", "foot"):
                for side in "LR":
                    remove_tree(f"{nm}_ik_{k}.{side}")
            perf.pop(nm)
    arriving = p0 < 0
    if n == 15:  # the rear jack man would be in the car's way as it arrives: he steps in after it has stopped
        for nm in ("rjack", "rjack_eq"):
            remove_tree(nm)
            for k in ("hand", "foot"):
                for side in "LR":
                    remove_tree(f"rjack_ik_{k}.{side}")
            perf.pop(nm, None)
    for (tag, s, f, wn) in CORNERS:
        old, new, gun = bpy.data.objects.get(wn), bpy.data.objects.get(f"newtyre{tag}"), bpy.data.objects.get(f"wg{tag}")
        # ---- props, every frame from the stop clock
        for ob in (old, new, gun):
            if ob:
                if ob.parent and ob.parent.name != "car":
                    pass
                detach(ob)
        if new:
            new.rotation_euler = (0, 0, 0 if s > 0 else math.pi)
        if old:
            old.rotation_euler = (0, 0, 0)
        if gun:
            gun.rotation_euler = (0, 0, gun_yaw(s, f))
        for fr, t in frames(f0, f1):
            q = q_of(t)
            if old:
                key(old, fr, loc=old_wheel_pos(s, f, q))
            if new:
                key(new, fr, loc=new_tyre_pos(s, f, q))
            if gun:
                p, pitch, rattle = gun_pos(s, f, q, t)
                key(gun, fr, loc=p, rot=(pitch, 0, gun_yaw(s, f) + (math.radians(1.5) * math.sin(2 * math.pi * 11 * t) if rattle else 0)))
        crew_corner(P, s, f, tag, old, new, gun, q_of, t_of, arriving)
    # ---- the car: lifts, drops; rolls in for shot 15
    if car:
        y0 = car.location.y
        for fr, t in frames(f0, f1):
            q = q_of(t)
            key(car, fr, loc=(car.location.x, car_y(q) if arriving else y0, lift(q)))
    # ---- wing men kneel in front of the wing with an adjuster on the flap
    for s in (1, -1):
        w = P(f"wing{s}")
        if not w:
            continue
        for k in "LR":
            if w.gripped[k]:
                w.a.hand[k].parent = None
                w.gripped[k] = False
        from lib import box
        from lib import palette
        M = palette()
        x = s * 0.5
        tool = box(f"wingtool{s}", (0.03, 0.03, 0.34), (x, 2.93, 0.4), M["dark"])
        handle = box(f"wingtool{s}_t", (0.16, 0.03, 0.03), (x, 2.93, 0.57), M["dark"])
        bpy.context.view_layer.update()
        handle.parent = tool
        handle.matrix_parent_inverse = tool.matrix_world.inverted()
        Station(w, [(0, 0, V((x, 3.38, 0)), 180, 0.36, 40)])
        kneel(w, 180)
        for k, dx in (("L", 0.06), ("R", -0.06)):
            hp = grip_point(tool, (dx * s, 0, 0.17))
            bpy.context.view_layer.update()
            w.a.hand[k].location = hp.matrix_world.translation
            hold_fn(w, k, hp)
        for fr, t in frames(f0, f1):  # a quarter turn on the adjuster, then back
            q = q_of(t)
            key(tool, fr, rot=(0, 0, math.radians(90) * ease(q, 0.2, 0.45) * (1 - ease(q, 0.6, 0.8))))
    # ---- jack men: front pulls the jack out after the drop, both lean on their levers
    for nm, eq in (("fjack", "fjack_eq"), ("rjack", "rjack_eq")):
        j = P(nm)
        jack = bpy.data.objects.get(eq)
        if not j or not jack:
            continue
        sgn = 1 if nm == "fjack" else -1
        grip = next((o for o in jack.children if o.name.endswith("_grip")), None)
        for k in "LR":
            if j.gripped[k]:
                j.a.hand[k].parent = None
                j.gripped[k] = False
        bpy.context.view_layer.update()
        gw = grip.matrix_world.translation.copy() if grip else V((0, sgn * 3.7, 0.9))
        rot = 180 if sgn > 0 else 0
        gk = {"L": gw + V((0.13 * (-1 if sgn > 0 else 1), 0, 0.02)), "R": gw + V((-0.13 * (-1 if sgn > 0 else 1), 0, 0.02))}
        r0 = solve_root(gk, rot, 0.14, 18, V((0, gw.y + sgn * 0.35, 0)))
        out = 0.75
        Station(j, [(0, 0, r0, rot, 0.14, 18), (t_of(1.0), t_of(1.08), r0 + V((0, sgn * out, 0)), rot, 0.1, 8)])
        for k in "LR":
            hp = grip_point(jack, jack.matrix_world.inverted() @ gk[k])
            bpy.context.view_layer.update()
            j.a.hand[k].location = hp.matrix_world.translation
            hold_fn(j, k, hp)
        start = jack.location.copy()
        for fr, t in frames(f0, f1):
            q = q_of(t)
            key(jack, fr, loc=start + V((0, sgn * out * ease(q, 1.0, 1.08), lift(q) * 0.0)))


def kneel(pf, rot):
    """Feet tucked behind, shins on the floor."""
    hd, rt = heading_of(rot), right_of(rot)
    r = V(pf.base["loc"])
    pf.foot_world = {k: V((r.x, r.y, 0.09)) - hd * 0.3 + rt * (0.11 if k == "L" else -0.11) for k in "LR"}
    pf.steps = []


def ready_hands(pf):
    """Hands up and forward, ready to grab."""
    for k in "LR":
        pf.a.hand[k].parent = None
        pf.gripped[k] = False
    pf.hand_local = {k: V(((0.18 if k == "L" else -0.18), 0.32, 0.95)) for k in "LR"}


def unhold(pf):
    for k in "LR":
        pf.a.hand[k].parent = None
        pf.gripped[k] = False


def frame_of(p):
    return Matrix.Translation(p["loc"]) @ Matrix.Rotation(math.radians(p["rot"]), 4, "Z")


def crew_corner(P, s, f, tag, old, new, gun, q_of, t_of, arriving):
    """Gun man, tyre-off man, tyre-on man at one corner. Hands are computed every frame from where the gun and
    wheels are (so they can reach in, hold, let go and wave without ever snapping)."""
    h0 = hub(s, f)
    gun_spot = V((s * GUN_X, h0.y + f * GUN_DY, 0))
    # ---- gun man: kneels square to the wheel; sits back with the gun raised while the wheels change; hand up when done
    g = P(f"gun{tag}")
    if g and gun:
        unhold(g)
        rot = rot_toward(gun_spot, h0)
        if arriving:
            Station(g, [(0, 0, gun_spot, rot, 0.36, 8), (t_of(-0.07), t_of(0.0), gun_spot, rot, 0.36, 20)])
        else:
            Station(g, [(0, 0, gun_spot, rot, 0.36, 20), (t_of(0.11), t_of(0.18), gun_spot, rot, 0.36, 6),
                        (t_of(0.74), t_of(0.8), gun_spot, rot, 0.36, 20), (t_of(0.92), t_of(1.0), gun_spot, rot, 0.36, 6)])
        kneel(g, rot)
        Rg = Matrix.Rotation(gun_yaw(s, f), 3, "Z")
        add_t_handle(gun)
        hold = {"L": V((0.075, -0.06, 0.29)), "R": V((-0.075, -0.06, 0.29))}  # gun-local: both hands on the T-handle
        wg = {k: Rg @ v for k, v in hold.items()}
        hold, _ = match_lr(hold, wg, rot)

        def gfx(t, p, hold=hold):
            q = q_of(t)
            gp, pitch, _ = gun_pos(s, f, q, t)
            Rf = Matrix.Rotation(gun_yaw(s, f), 3, "Z") @ Matrix.Rotation(pitch, 3, "X")
            M = frame_of(p)
            wave = ease(q, 0.9, 0.97)
            for k in "LR":
                on_gun = gp + Rf @ hold[k]
                if k == "L" and wave > 0:
                    up = M @ V((0.2, 0.08, 1.25 - p["crouch"] + 0.3 + 0.05 * math.sin(9 * t)))
                    on_gun = on_gun.lerp(up, wave)
                p["hands"][k] = ("world", on_gun)
            p["head"][1] += -4 * (1 - ease(q, 0.12, 0.18)) - 4 * ease(q, 0.74, 0.8) * (1 - ease(q, 0.9, 0.97))
        g.extra.append(gfx)
        g.a.arm["holds"] = [gun.name]
    # ---- tyre-off man: forward-outboard of the gun man; ready, reaches in as the gun lifts, pulls the wheel off,
    #      carries it along the car and out to the side, stepping with it
    o = P(f"off{tag}")
    if o and old:
        unhold(o)
        gl = {"L": V((s * 0.2, f * 0.04, 0.17)), "R": V((s * 0.2, f * 0.31, 0.04))}  # outer face, front half
        near = V((s * 1.3, h0.y + f * 0.3, 0))
        rot = 90 if s > 0 else -90
        gl, _ = match_lr(gl, {k: h0 + v for k, v in gl.items()}, rot)
        away_gun = lambda p: (p - gun_spot).length > 0.8 and abs(p.x) > 1.2 and f * (p.y - h0.y) > 0.36
        r0 = solve_root({k: h0 + gl[k] for k in "LR"}, rot, 0.35, 34, near, keep_out=away_gun)
        W1, W2 = old_wheel_pos(s, f, 0.32), old_wheel_pos(s, f, 0.6)
        rot2 = rot + s * f * 15
        clear = lambda W: (lambda p: (p - gun_spot).length > 0.8 and abs(p.x) > (1.2 if f < 0 else 1.25)
                           and (V((p.x, p.y, 0)) - V((W.x, W.y, 0))).length > 0.42)
        r1 = solve_root({k: W1 + gl[k] for k in "LR"}, rot, 0.3, 30, r0 + V((W1.x - h0.x, W1.y - h0.y, 0)), keep_out=clear(W1))
        r2 = solve_root({k: W2 + gl[k] for k in "LR"}, rot2, 0.2, 22, r0 + V((W2.x - h0.x, W2.y - h0.y, 0)), keep_out=clear(W2))
        if arriving:
            st = [(0, 0, r0 + heading_of(rot) * -0.12, rot, 0.3, 18)]
        else:
            st = [(0, 0, r0, rot, 0.3, 16), (t_of(0.1), t_of(0.16), r0, rot, 0.35, 34),
                  (t_of(0.16), t_of(0.32), r1, rot, 0.3, 30), (t_of(0.33), t_of(0.56), r2, rot2, 0.2, 22)]
        Station(o, st)
        if not arriving:  # between stances the body rides with the wheel (same easing), so the grip never stretches
            offs = [(r0 - h0), (r1 - W1), (r2 - W2)]
            stance = o.path

            def opath(t, offs=offs, stance=stance):
                q = q_of(t)
                W = old_wheel_pos(s, f, q)
                a, b = ease(q, 0.16, 0.32), ease(q, 0.33, 0.56)
                off = offs[0].lerp(offs[1], a).lerp(offs[2], b)
                return V((W.x + off.x, W.y + off.y, 0)), stance(t)[1]
            o.path = opath
        o.a.arm["holds"] = [old.name]

        def ofx(t, p, gl=gl):
            q = q_of(t)
            M = frame_of(p)
            grab = 0.0 if arriving else ease(q, 0.1, 0.16)
            W = old_wheel_pos(s, f, q)
            for k, x in (("L", 0.2), ("R", -0.2)):
                ready = M @ V((x, 0.3, 0.98 - p["crouch"] + wob(t, 1.3, 0.01)))
                p["hands"][k] = ("world", ready.lerp(W + gl[k], grab))
            p["head"][1] += 10 * grab
        o.extra.append(ofx)
    # ---- tyre-on man: aft-outboard holding the new tyre; steps in and pushes it onto the hub, lets go, steps back
    m = P(f"on{tag}")
    if m and new:
        unhold(m)
        rot = 0 if f > 0 else 180
        hd = heading_of(rot)
        R = Matrix.Rotation(0 if s > 0 else math.pi, 3, "Z")
        gw = {"L": V((0.15, -f * 0.22, 0.27)), "R": V((-0.15, -f * 0.22, 0.27))}  # world offsets from the tyre centre
        gw, _ = match_lr(gw, gw, rot)
        w0 = new_tyre_pos(s, f, -0.5)
        r0 = solve_root({k: w0 + gw[k] for k in "LR"}, rot, 0.26, 20, w0 - hd * 0.75, keep_out=lambda p: abs(p.x) > 1.2 and (p - gun_spot).length > 0.8)
        r1 = solve_root({k: h0 + gw[k] for k in "LR"}, rot, 0.28, 18, h0 - hd * 0.8 + V((s * 0.2, 0, 0)),
                        keep_out=lambda p: abs(p.x) > 0.95 and abs(p.y - h0.y) > 0.72 and (p - gun_spot).length > 0.9)
        r_back = r1 - hd * 0.32 + V((s * 0.1, 0, 0))
        if arriving:  # waits further out while the car rolls in, steps in with the tyre as it stops
            Station(m, [(0, 0, r0 + V((s * 0.3, 0, 0)), rot, 0.26, 20), (t_of(-0.25), t_of(0.0), r0, rot, 0.26, 20)])
        else:
            Station(m, [(0, 0, r0, rot, 0.26, 20), (t_of(0.45), t_of(0.7), r1, rot, 0.28, 18),
                        (t_of(0.71), t_of(0.84), r_back, rot, 0.06, 2)])
        m.a.arm["holds"] = [new.name]

        def mfx(t, p, gw=gw):
            q = q_of(t)
            M = frame_of(p)
            let_go = ease(q, 0.7, 0.76)
            T = new_tyre_pos(s, f, q)
            for k, x in (("L", 0.2), ("R", -0.2)):
                hold_p = T + gw[k]
                if k == "R":  # hand up: tyre on
                    free = M @ V((-0.24, 0.12, 1.25 - p["crouch"] + 0.32 + 0.03 * math.sin(7 * t)))
                else:
                    free = M @ V((0.3, 0.0, 0.85))
                p["hands"][k] = ("world", hold_p.lerp(free, let_go))
            p["head"][1] += 14 * (1 - let_go)
        m.extra.append(mfx)


def add_t_handle(gun):
    """A D/T handle on top of the wheel gun (real ones have one): a short post and a crossbar the hands hold."""
    if bpy.data.objects.get(gun.name + "_tpost"):
        return
    from lib import box, palette
    M = palette()
    bpy.context.view_layer.update()
    post = box(gun.name + "_tpost", (0.035, 0.035, 0.22), (0, 0, 0), M["dark"])
    bar = box(gun.name + "_tbar", (0.2, 0.04, 0.04), (0, 0, 0), M["dark"])
    for ob, loc in ((post, (0, -0.06, 0.17)), (bar, (0, -0.06, 0.29))):
        ob.parent = gun
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.location = loc
        ob.rotation_euler = (0, 0, 0)
