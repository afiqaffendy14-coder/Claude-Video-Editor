"""Bake every shot into a ready-to-render .blend: rigged characters, keyframed choreography, camera moves with
handheld shake where it fits, props that move (car, tyres, wheel guns, syringe, chart blocks), motion blur, 30 fps.

Run (Blender's Python or the bpy module):  bake.py <out_dir> [shot ids...]   -> <out_dir>/sNN.blend
Nothing is rendered here; render.py renders the .blend files on a GPU.
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector, Matrix, Euler
import lib
from lib import reset, setup_render, box, mat, palette, look_at
import shots, voxel, rig, choreo, pitstop
from choreo import Performer, ease, sstep, overshoot, wob, FPS
from anim import MOVES, camera_path

V = Vector


# ---------------------------------------------------------------- cast -> rigs
def rig_cast():
    """Replace every static block person with a rig in the same pose; re-attach what they were holding."""
    perf = {}
    statics = [o for o in bpy.data.objects if o.get("person") and o.get("args") and not o.get("rig")]
    for i, root in enumerate(statics):
        a = json.loads(root["args"])
        J = {k: V(v) for k, v in json.loads(root["joints"]).items()}
        bpy.context.view_layer.update()
        M = root.matrix_world.copy()
        wr = {k: M @ J["wr" + k] for k in "LR"}
        an = {k: M @ J["an" + k] for k in "LR"}
        name, pose = root.name, a["pose"]
        pose_name = root.get("pose_name", "custom")
        for ob in [root] + list(root.children_recursive):
            bpy.data.objects.remove(ob, do_unlink=True)
        arm = rig.build(name, a["outfit"], a["scale"])
        act = rig.Actor(arm).place(V(a["loc"]), a["rot"], crouch=pose["crouch"])
        for k in "LR":
            act.hand[k].location = wr[k]
            act.foot[k].location = an[k]
        arm["pose_name"] = pose_name
        bpy.context.view_layer.update()
        base = dict(loc=list(a["loc"]), rot=a["rot"], crouch=pose["crouch"], lean=pose["lean"], twist=pose["twist"],
                    head=list(pose["head"]))
        perf[name] = Performer(act, base, seed=i + 1)
    holds = json.loads(bpy.context.scene.get("holds", "[]"))
    for h in holds:
        pf, ob = perf.get(h["person"]), bpy.data.objects.get(h["obj"])
        if not pf or not ob:
            continue
        ks = ("R",) if h["mode"] == "hand" else ("L", "R")
        for k in ks:
            if h["mode"] == "hand":  # the prop follows the hand (lollipop)
                mw = ob.matrix_world.copy()
                ob.parent = pf.a.hand[k]
                ob.matrix_parent_inverse = pf.a.hand[k].matrix_world.inverted()
            else:  # the hand follows the prop (tyres, wheel guns, jack levers)
                pf.a.grip(k, ob)
                pf.gripped[k] = True
    for pf in perf.values():  # refresh what each performer considers its rest pose
        pf.__init__(pf.a, pf.base, seed=pf.rnd.random() * 1e6)
    return perf


def remove_perf(perf, nm):
    """Take a character out of a shot (it would block the camera)."""
    root = bpy.data.objects.get(nm)
    if root is None:
        return
    for ob in [root] + list(root.children_recursive) + [o for o in bpy.data.objects if o.name.startswith(nm + "_ik_")]:
        bpy.data.objects.remove(ob, do_unlink=True)
    perf.pop(nm, None)


def regrip(pf, k, ob):
    pf.a.grip(k, ob)
    pf.gripped[k] = True


def free(pf, k):
    t = pf.a.hand[k]
    bpy.context.view_layer.update()
    mw = t.matrix_world.copy()
    t.parent = None
    t.matrix_world = mw
    pf.gripped[k] = False
    pf.hand_local[k] = pf.a.arm.matrix_world.inverted() @ mw.translation


def key_obj(ob, f, loc=None, rot=None, scale=None):
    if loc is not None:
        ob.location = loc
        ob.keyframe_insert("location", frame=f)
    if rot is not None:
        ob.rotation_euler = rot
        ob.keyframe_insert("rotation_euler", frame=f)
    if scale is not None:
        ob.scale = scale
        ob.keyframe_insert("scale", frame=f)


def frames(f0, f1, pad=3):
    for f in range(f0 - pad, f1 + pad):
        yield f, (f - f0) / FPS


def empty_at(name, loc, parent=None):
    e = lib.link(bpy.data.objects.new(name, None))
    e.empty_display_size = 0.03
    e.location = loc
    if parent:
        bpy.context.view_layer.update()
        e.parent = parent
        e.matrix_parent_inverse = parent.matrix_world.inverted()
    return e


# ---------------------------------------------------------------- behaviours
def operate(pf, work, t_offset=0.0, spread=0.07, lift=0.0, instrument=True, look=18):
    """Surgeon at work: both hands over the work point, small precise movements, eyes on the hands."""
    for k in "LR":
        free(pf, k)
    a = pf.a
    r = a.right

    def fx(t, p, work=V(work)):
        tg = t + t_offset  # film clock: keeps shots 35 -> 1 continuous across the loop
        for k, s in (("L", 1), ("R", -1)):  # L hand on the body's L (+right axis) side
            base = work + r * (s * spread) + V((0, 0, 0.04 + lift))
            d = V((wob(tg, 0.55 if k == "R" else 0.4, 0.018, pf.ph + s), wob(tg, 0.7 if k == "R" else 0.45, 0.014, pf.ph + 2 * s),
                   wob(tg, 0.9 if k == "R" else 0.6, 0.012, pf.ph + 3 * s) - 0.01 * (k == "R") * (1 + math.sin(2 * math.pi * 1.1 * tg))))
            p["hands"][k] = ("world", base + d)
        p["head"][1] += look + wob(tg, 0.3, 1.0)
        p["head"][0] = p["head"][0] * 0.3
        p["side"] *= 0.5
    pf.extra.append(fx)
    if instrument:  # forceps in the right hand
        M = palette()
        h = a.hand["R"]
        for i, dx in enumerate((-0.006, 0.006)):
            box(f"{pf.a.name}_forceps{i}", (0.006, 0.13, 0.006), tuple(h.location + a.heading * 0.08 + r * dx + V((0, 0, -0.03))),
                M["steel"], rot=(math.radians(-25), 0, a.arm.rotation_euler.z)).parent = h


def run_with(pf, base_xy, v, cadence=3.4, lean=14, lift=0.14, bob=0.04):
    """Sprint alongside the cot (root moves with v, planted running steps, bobbing, leaning in)."""
    hd = pf.base["rot"]
    b = V((base_xy[0], base_xy[1], 0))
    path = lambda t: (b + v * t, hd)
    pf.base["loc"] = list(b)
    pf.walk(path, -0.4, 3.0, cadence=cadence, duty=0.36, lift=lift, width=0.11)
    for k in "LR":
        pf.foot_world[k] = V((b.x + (0.11 if k == "L" else -0.11) * math.cos(math.radians(hd)),
                              b.y + (0.11 if k == "L" else -0.11) * math.sin(math.radians(hd)), pf.foot_world[k].z))

    def fx(t, p):
        p["lean"] = pf.base["lean"] * 0.3 + lean + wob(t, cadence / 2, 2.0, pf.ph)
        p["crouch"] = pf.base["crouch"] * 0.3 + 0.06 - bob * abs(math.sin(math.pi * cadence * t + pf.ph))
        p["head"][0] = wob(t, 0.9, 12, pf.ph + 1)  # glancing about: it's an emergency
        for k, s in (("L", 1), ("R", -1)):
            if p["hands"][k] is not None and p["hands"][k][0] == "local":  # free arm pumps
                hl = pf.hand_local[k]
                p["hands"][k] = ("local", hl + V((0, 0.13 * s * math.sin(math.pi * cadence * t + pf.ph), 0.1 + 0.05 * s * math.sin(math.pi * cadence * t + pf.ph))))
    pf.extra.append(fx)


def scramble(pf, seed, t1, reach_pts=(), radius=0.12, turn=20):
    """Emergency at the bedside: quick repositioning steps, turning, reaching in, heads snapping round."""
    import random
    rnd = random.Random(seed)
    b0 = V(pf.base["loc"])
    hd0 = pf.base["rot"]
    moves = []
    t = rnd.uniform(0.05, 0.35)
    loc, hd = b0.copy(), hd0
    while t < t1 + 0.6:
        nl = b0 + V((rnd.uniform(-radius, radius), rnd.uniform(-radius, radius), 0))
        nh = hd0 + rnd.uniform(-turn, turn)
        moves.append((t, t + 0.35, loc, nl, hd, nh))
        loc, hd = nl, nh
        t += rnd.uniform(0.7, 1.1)

    def path(t):
        cur, h = b0, hd0
        for (ta, tb, la, lb, ha, hb) in moves:
            if t < ta:
                break
            x = ease(t, ta, tb)
            cur, h = la.lerp(lb, x), ha + (hb - ha) * x
        return cur, h
    pf.path = path
    for (ta, tb, la, lb, ha, hb) in moves:  # two quick steps per move, feet land where the body goes
        r = math.radians(hb)
        right = V((math.cos(r), math.sin(r), 0))
        pf.step_to("L", ta - 0.02, ta + 0.18, V((lb.x, lb.y, 0.09)) + right * 0.1)
        pf.step_to("R", ta + 0.14, tb, V((lb.x, lb.y, 0.09)) - right * 0.1)
    pf.lift = 0.07
    reaches = []
    if reach_pts:
        t = rnd.uniform(0.0, 0.3)
        i = 0
        while t < t1 + 0.6:
            reaches.append((t, t + 0.3, t + rnd.uniform(0.55, 0.85), "R" if i % 2 == 0 else "L", V(reach_pts[i % len(reach_pts)])))
            i += 1
            t += rnd.uniform(0.5, 0.8)

    def fx(t, p):
        p["head"][0] += wob(t, 0.8, 14, pf.ph) + 10 * math.sin(3.1 * t + pf.ph)
        p["lean"] = pf.base["lean"] + wob(t, 0.6, 5, pf.ph + 1)
        for (ta, tb, te, k, pt) in reaches:
            if ta <= t <= te + 0.3 and not pf.gripped[k]:
                x = ease(t, ta, tb) * (1 - ease(t, te, te + 0.3))
                cur = p["hands"][k]
                M = Matrix.Translation(p["loc"]) @ Matrix.Rotation(math.radians(p["rot"]), 4, "Z")
                rest = M @ cur[1] if cur and cur[0] == "local" else pt
                p["hands"][k] = ("world", rest.lerp(pt + V((wob(t, 2.0, 0.02), 0, wob(t, 1.7, 0.015))), x))
    pf.extra.append(fx)


def busy(pf, seed, t1, outer=False):
    """Emergency work at a station: hands dart between spots within reach on the cot edge (or the machine in front),
    hold, move on; the head snaps between the job and the monitor; weight shifts, the odd quick re-set of a foot.
    Everything is in the person's own frame, so no one ever reaches into a neighbour."""
    import random
    rnd = random.Random(seed)
    spots = [V((0.14, 0.46, 1.1)), V((0.02, 0.5, 1.08)), V((-0.12, 0.47, 1.1)), V((0.1, 0.42, 1.14)), V((-0.08, 0.43, 1.13))]
    if outer:
        spots = [V((0.12, 0.34, 1.05)), V((-0.1, 0.34, 1.12)), V((0.0, 0.3, 1.2))]
    tasks = {k: [] for k in "LR"}
    for k in "LR":
        t = rnd.uniform(-0.2, 0.25)
        while t < t1 + 0.5:
            sp = rnd.choice([v for v in spots if (v.x >= -0.02) == (k == "L")] or spots)
            reach = rnd.uniform(0.18, 0.26)
            hold = rnd.uniform(0.25, 0.5)
            tasks[k].append((t, t + reach, t + reach + hold, sp + V((rnd.uniform(-0.03, 0.03), rnd.uniform(-0.03, 0.03), 0))))
            t += reach + hold + rnd.uniform(0.05, 0.15)
    looks = []
    t = rnd.uniform(0.0, 0.4)
    while t < t1 + 0.5:
        looks.append((t, rnd.choice([-35, -20, 25, 40]) if rnd.random() < 0.45 else 0))
        t += rnd.uniform(0.35, 0.7)
    hd = pf.base["rot"]
    rt = V((math.cos(math.radians(hd)), math.sin(math.radians(hd)), 0))
    for i in range(2):  # a couple of quick foot re-sets (planted otherwise)
        k = "LR"[i]
        tu = rnd.uniform(0.2, max(0.3, t1 - 0.3))
        pf.step_to(k, tu, tu + 0.2, pf.foot_world[k] + rt * rnd.uniform(-0.05, 0.05) + V((0, 0, 0)))
    pf.lift = 0.05

    def fx(t, p):
        for k in "LR":
            cur, prev_sp = pf.hand_local[k], pf.hand_local[k]
            for (ta, tb, te, sp) in tasks[k]:
                if t < ta:
                    break
                x = ease(t, ta, tb)
                cur = prev_sp.lerp(sp, x) + (V((wob(t, 3.1, 0.012), 0, wob(t, 2.7, 0.01))) if t > tb else V())
                prev_sp = sp
            p["hands"][k] = ("local", cur)
        yaw = 0.0
        prev = 0.0
        for (tl, y) in looks:
            if t < tl:
                break
            yaw = prev + (y - prev) * ease(t, tl, tl + 0.12)
            prev = y
        p["head"][0] = p["head"][0] * 0.3 + yaw
        p["head"][1] += -12 * (abs(yaw) > 15)
        p["side"] += wob(t, 0.9, 2.5, pf.ph)
        p["lean"] += wob(t, 0.7, 3.0, pf.ph + 1)
    pf.extra.append(fx)


def unplug_fx(f0, f1, dur):
    import shots as SH
    J = V(SH.UNPLUG_J)
    sc = bpy.context.scene

    def group(name, members, at):
        g = empty_at(name, at)
        bpy.context.view_layer.update()
        for nm in members:
            ob = bpy.data.objects.get(nm)
            if ob:
                ob.parent = g
                ob.matrix_parent_inverse = g.matrix_world.inverted()
        return g
    gl = group("uL", ["uhandL", "uthumbL", "usleeveL"], J + V((0, 0, 0.04)))
    gb = group("uB", ["connB"] + [f"connB_ridge{i}" for i in range(3)], J + V((0, 0, -0.04)))
    gr = group("uR", ["uhandR", "uthumbR", "usleeveR"], J + V((0, 0, -0.04)))
    lag = empty_at("uB_lag", J + V((0, 0, -0.16)))
    down = bpy.data.objects.get("unplug_down")
    bpy.context.view_layer.update()
    for idx, e in ((0, gb), (1, lag)):  # the loose tube end rides on the yellow half (and lags behind it)
        m = down.modifiers.new(f"hook{idx}", "HOOK")
        m.object = e
        m.vertex_indices_set([idx])
        m.matrix_inverse = e.matrix_world.inverted()
    b0, r0, l0, lag0 = gb.location.copy(), gr.location.copy(), gl.location.copy(), lag.location.copy()
    t_rel = 1.05

    def b_pos(t):
        tw = overshoot(t, 0.28, 0.62, 0.1)                       # quarter-turn to unlock
        pull = overshoot(t, 0.68, 1.0, 0.06)                     # then pulled apart
        p = b0 + V((0, -0.05, -0.1)) * pull + V((wob(t, 7, 0.002), 0, 0)) * (1 - pull)
        if t > t_rel:                                            # let go: it drops and swings on its tube
            u = t - t_rel
            p = p + V((0.02 * math.sin(3.1 * u) * math.exp(-1.5 * u), -0.07 * math.sin(5.5 * u) * math.exp(-1.6 * u),
                       -0.11 * (1 - math.exp(-5 * u) * math.cos(6 * u))))
        return p, math.radians(95 * tw - 5 * tw * (t > 0.62))
    for f, t in frames(f0, f1, pad=6):
        p, rz = b_pos(t)
        key_obj(gb, f, loc=p, rot=(0, 0, rz))
        pl, _ = b_pos(max(0.0, t - 0.09))
        key_obj(lag, f, loc=lag0 + (pl - b0) * 0.75)
        if t <= t_rel:
            key_obj(gr, f, loc=r0 + (p - b0), rot=(0, 0, rz))
        else:  # the hand comes away, up and out of shot
            u = ease(t, t_rel, t_rel + 0.55)
            pr, _ = b_pos(t_rel)
            key_obj(gr, f, loc=r0 + (pr - b0) + V((-0.12, -0.16, 0.1)) * u, rot=(0, 0, rz))
        key_obj(gl, f, loc=l0 + V((wob(t, 3.3, 0.0025), wob(t, 2.9, 0.002), wob(t, 4.1, 0.0015))))
    for i, td in enumerate((1.02, 1.3, 1.55, 1.8)):  # drips keep coming from the open end
        d = bpy.data.objects.get(f"drip{i}")
        if not d:
            continue
        top = J + V((0.004 * i, 0, -0.012))
        for f, t in frames(f0, f1, pad=6):
            u = t - td
            z = top.z - 4.9 * u * u if u > 0 else top.z
            on = 1.0 if (u > 0 and z > 0.86) else 0.001
            key_obj(d, f, loc=(top.x, top.y, max(z, 0.86)), scale=(on, on, on * (1 + min(2.0, 6 * max(u, 0)))))


# ---------------------------------------------------------------- per-shot choreography
def shot_fx(n, perf, f0, f1, dur):
    P = perf.get
    M = palette()
    tg0 = {1: 0.0, 35: -1.9}.get(n, 0.0)

    if n in (1, 35):  # the surgeon operating; 35 is the 1.9 s just before 1 (seamless loop)
        s = P("surg")
        s.base.update(loc=[0.0, -0.45, 0.0], lean=38, crouch=0.03)
        s.a.place(V((0, -0.45, 0)), 0, 0.03)
        s.foot_world = {k: s.a.foot[k].matrix_world.translation.copy() for k in "LR"}
        operate(s, (0.0, 0.05, 0.9), t_offset=tg0, spread=0.06, look=-10)
        s.t_off = tg0  # idle breathing etc. on the film clock too, so 35's last frame flows into 1's first

    if n in (4, 5):  # surgery on the table: two surgeons across the table, staggered so their heads never meet
        if n == 5:
            for nm in ("surg3", "nurse1"):
                if nm in perf:
                    for ob in [bpy.data.objects[nm]] + list(bpy.data.objects[nm].children_recursive) + \
                              [o for o in bpy.data.objects if o.name.startswith(nm + "_ik_")]:
                        bpy.data.objects.remove(ob, do_unlink=True)
                    perf.pop(nm)
        drop = 0.15  # a lower table, so the surgeons work over it instead of leaning into the drapes
        for ob in bpy.data.objects:
            if ob.parent is None and (ob.name.startswith(("table", "drape", "op_")) and ob.type in ("MESH", "EMPTY")):
                ob.location.z -= drop
        for nm, x, y, wy in (("surg1", 0.66, 0.14, 0.3), ("surg2", -0.66, 0.58, 0.4)):
            pf = P(nm)
            if pf:
                rot = 90 if x > 0 else -90
                pf.base.update(loc=[x, y, 0], rot=rot, lean=18, crouch=0.08)
                pf.a.place(V((x, y, 0)), rot, 0.08)
                pf.foot_world = {k: pf.a.foot[k].matrix_world.translation.copy() for k in "LR"}
                operate(pf, (math.copysign(0.16, x), wy, 1.2), spread=0.07, instrument=(x > 0), look=12)
        an = P("anaesthetist")
        if an:  # stands clear of the anaesthesia machine, watching the baby's face
            an.base.update(loc=[0.3, 1.16, 0], rot=200)
            an.a.place(V((0.3, 1.16, 0)), 200, an.base["crouch"])
            an.foot_world = {k: an.a.foot[k].matrix_world.translation.copy() for k in "LR"}
            an.hand_local = {"L": V((0.2, 0.2, 1.1)), "R": V((-0.24, 0.12, 0.92))}  # one hand on the bag, one by the side
            an.extra.append(lambda t, p: p["head"].__setitem__(1, p["head"][1] + 12))

    if n in (6, 7, 10):  # sprinting the cot to intensive care
        cot = bpy.data.objects.get("cot")
        cy = cot.location.y
        v = V((0, 2.3, 0))
        vent, iv = bpy.data.objects.get("cor_vent"), bpy.data.objects.get("cor_iv")
        ivx = -0.98 if n == 10 else 0.98  # shot 10 is filmed from the right: the drip stand trails on the far side
        if vent:
            vent.location = (-0.98, cy + 1.12, 0)
        if iv:
            iv.location = (ivx, cy - 0.6, 0)
        bag = box("ambu_bag", (0.09, 0.16, 0.08), (0.2, cy + 0.2, 0.95), mat("ambu", (0.2, 0.45, 0.85), 0.5))
        grips = {}
        # the cot spans y = cy-0.75 .. cy+0.29 (foot rail at cy-0.74), its side rails sit at x = +-0.35, 0.86 high;
        # everyone holds on with the hand on the cot's side (arms are short: wrist within 0.45 m of the shoulder)
        team = dict(porter=(0.0, cy - 0.98, 0), nurse_c1=(-0.66, cy - (0.35 if n == 10 else 0.2), 0),
                    nurse_c2=(0.66, cy - 0.55, 0), anaes_c=(0.62, cy + 0.3, 0), doc_c=(-0.62, cy + 0.78, 0))
        for nm, xy in team.items():
            pf = P(nm)
            if not pf:
                continue
            pf.base.update(rot=0, lean=8, crouch=0.04, twist=0, head=[0, 0])
            pf.a.place(V(xy), 0, 0.04)
            pf.foot_world = {k: pf.a.foot[k].matrix_world.translation.copy() for k in "LR"}
            pf.hand_local = {k: pf.a.arm.matrix_world.inverted() @ pf.a.hand[k].matrix_world.translation for k in "LR"}
            for k in "LR":
                if pf.gripped[k]:
                    free(pf, k)
        hands = {"porter": {"L": (cot, (0.2, cy - 0.76, 0.9)), "R": (cot, (-0.2, cy - 0.76, 0.9))},
                 "nurse_c1": {"L": (cot, (-0.37, cy - (0.3 if n == 10 else 0.15), 0.9))},
                 "nurse_c2": {"R": (cot, (0.37, cy - 0.4, 0.9))},
                 "anaes_c": {"R": (bag, (0.22, cy + 0.2, 0.97))},
                 "doc_c": {"R": (vent, (-0.86, cy + 0.98, 1.06))}}
        if n == 10:
            hands["nurse_c1"]["R"] = (iv, (ivx, cy - 0.58, 1.05))
        else:
            hands["nurse_c2"]["L"] = (iv, (ivx, cy - 0.58, 1.05))
        for nm, hs in hands.items():
            pf = P(nm)
            if not pf:
                continue
            for k, (par, loc) in hs.items():
                if par is None:
                    continue
                pf.a.hand[k].location = loc
                regrip(pf, k, par)
            run_with(pf, team[nm][:2], v)
        for ob in (cot, vent, iv, bag):
            if ob:
                start = ob.location.copy()
                for f, t in frames(f0, f1):
                    key_obj(ob, f, loc=start + v * t + V((0, 0, 0.004 * math.sin(2 * math.pi * 5.2 * t)) if ob is cot else V()))
        for f, t in frames(f0, f1):  # the bag being squeezed
            sq = 0.5 + 0.5 * math.sin(2 * math.pi * 1.0 * t)
            key_obj(bag, f, scale=(1 - 0.28 * sq, 1, 1 - 0.18 * sq))

    if n in (9, 11, 12, 13):  # intensive care: everyone scrambling, each at their own station round the cot
        # cot: x +-0.38, y -0.25..0.85, mattress top 0.71; stations 0.75 m apart so nobody shares space
        if n == 9:  # the close-up's hands are c2's; c1 and c8 would stand in front of the lens
            for nm in ("c8", "c1", "c2", "c4"):
                remove_perf(perf, nm)
        ST = dict(c2=(-0.72, 0.8, -90), c4=(-0.72, -0.1, -90), c1=(0.72, 0.8, 90), c3=(0.72, -0.1, 90),
                  c8=(0.0, 1.56, 180), c5=(0.0, -0.92, 0), c6=(1.5, 1.0, 12), c7=(-1.4, 0.3, -95))
        for i, (nm, (x, y, rot)) in enumerate(ST.items()):
            pf = P(nm)
            if not pf:
                continue
            for k in "LR":
                if pf.gripped[k]:
                    free(pf, k)
            outer = nm in ("c6", "c7")
            end = nm in ("c5", "c8")
            pf.base.update(loc=[x, y, 0], rot=rot, lean=18 if outer else (16 if end else 32), crouch=0.06 if outer else 0.1, twist=0, head=[0, 14])
            pf.a.place(V((x, y, 0)), rot, pf.base["crouch"])
            pf.foot_world = {k: pf.a.foot[k].matrix_world.translation.copy() for k in "LR"}
            pf.hand_local = {"L": V((0.22, 0.12, 0.86)), "R": V((-0.22, 0.12, 0.86))}
            busy(pf, seed=n * 10 + i, t1=dur, outer=outer)
        if n == 9:  # close-up insert: gloved hands twist the connector, pull it apart, the loose end drops away
            unplug_fx(f0, f1, dur)
        if n == 13:  # a syringe slips off the edge and clatters down
            parts = [bpy.data.objects.get(nm) for nm in ("syr_barrel", "syr_plunger", "syr_tip")]
            g = empty_at("syringe", (0.42, -0.24, 0.7))
            for ob in parts:
                if ob:
                    ob.parent = g
                    ob.matrix_parent_inverse = g.matrix_world.inverted()
                    ob.location = ob.location - V((0.48, -0.42, 0.62)) + V((0.42, -0.24, 0.7)) - V((0.42, -0.24, 0.7))
            g0 = V((0.4, -0.28, 0.72))
            for f, t in frames(f0, f1):
                fall = max(0.0, t - 0.15)
                z = 0.72 - 4.9 * 0.55 * fall * fall
                rx = 2.5 * fall
                if z < 0.03:  # bounce once, then settle and skid a little
                    tb = math.sqrt((0.72 - 0.03) / (4.9 * 0.55)) + 0.15
                    u = t - tb
                    z = 0.03 + max(0.0, 0.6 * u - 4.9 * 0.55 * u * u) * 0.25
                    rx = 2.5 * (tb - 0.15) + 1.2 * min(u, 0.4)
                key_obj(g, f, loc=g0 + V((0.12 * fall, -0.1 * fall, 0)) + V((0, 0, z - g0.z)), rot=(rx, 0.4 * rx, 0.3))

    if n in pitstop.SPANS:
        pitstop.stage(n, perf, f0, f1, dur, frames, regrip)
    if n in (23, 24, 32, 33):
        pit_fx(n, perf, f0, f1, dur)

    if n == 14:  # one doctor points at the screen
        b = P("docB")
        if b:
            free(b, "R")
            b.extra.append(lambda t, p: p["hands"].__setitem__("R", ("local", b.hand_local["R"] + V((0, 0.12, 0.26)) * ease(t, 0.3, 0.9))))

    if n in (21, 22):  # an engineer points at the hospital footage, another leans in
        e = P("eng3")
        if e:
            free(e, "R")
            e.extra.append(lambda t, p: p["hands"].__setitem__("R", ("local", e.hand_local["R"].lerp(V((-0.18, 0.38, 1.33)), overshoot(t, 0.2, 0.9)))))
        e2 = P("eng2")
        if e2:
            e2.extra.append(lambda t, p: p.__setitem__("lean", p["lean"] + 8 * ease(t, 0.3, 1.2)))

    if n == 20:  # the doctor leans over the table, picks up the phone and lifts it to look at the screen
        c = P("caller")
        phone = bpy.data.objects.get("phone")
        if c and phone:
            for k in "LR":
                if c.gripped[k]:
                    free(c, k)
            c.base.update(loc=[0.85, -1.8, 0], rot=0, lean=52, crouch=0.08, head=[0, 18])
            c.a.place(V((0.85, -1.8, 0)), 0, 0.08)
            c.foot_world = {k: c.a.foot[k].matrix_world.translation.copy() for k in "LR"}
            c.hand_local = {"L": V((0.24, 0.1, 0.8)), "R": V((-0.2, 0.3, 0.95))}
            ph_start = phone.location.copy()
            scr = bpy.data.objects.get("phone_screen")
            if scr:
                bpy.context.view_layer.update()
                scr.parent = phone
                scr.matrix_parent_inverse = phone.matrix_world.inverted()
            lift_to = V((-0.06, -0.2, 0.3))
            for f, t in frames(f0, f1):
                x = ease(t, 0.6, 1.45)
                key_obj(phone, f, loc=ph_start + lift_to * x, rot=(math.radians(55 * x), 0, math.radians(15 - 10 * x)))

            def pick(t, p):
                reach = ease(t, 0.05, 0.55)
                x = ease(t, 0.6, 1.45)
                pt = ph_start + lift_to * x + V((0.0, -0.03, 0.06))
                M_ = Matrix.Translation(p["loc"]) @ Matrix.Rotation(math.radians(p["rot"]), 4, "Z")
                p["hands"]["R"] = ("world", (M_ @ c.hand_local["R"]).lerp(pt, reach))
                p["lean"] -= 14 * x  # straightens a little as the phone comes up
                p["crouch"] -= 0.03 * x
            c.extra.append(pick)
            c.a.arm["holds"] = ["phone"]
    if n in (14, 20):  # the doctors stand in front of the sofa, not in it
        for nm in ("docA", "docB"):
            pf = P(nm)
            if pf:
                nb = V(pf.base["loc"]) + V((0, 0.62, 0))
                pf.base["loc"] = list(nb)
                pf.a.place(nb, pf.base["rot"], pf.base["crouch"])
                pf.foot_world = {k: pf.a.foot[k].matrix_world.translation.copy() for k in "LR"}
                pf.hand_local = {k: pf.a.arm.matrix_world.inverted() @ pf.a.hand[k].matrix_world.translation for k in "LR"}

    if n == 25:  # the lead anaesthetist raises his hand: everyone turns to him
        l = P("leader")
        if l:
            free(l, "R")
            l.extra.append(lambda t, p: p["hands"].__setitem__("R", ("local", l.hand_local["R"] + V((0, 0.08, -0.25)) * (1 - overshoot(t, 0.0, 0.7)))))
        for nm in ("o2", "o3", "o4"):
            pf = P(nm)
            if pf:
                pf.extra.append(lambda t, p: p["head"].__setitem__(0, p["head"][0] * 0.3 + 25 * ease(t, 0.15, 0.6)))

    if n in (26, 27, 29):  # the ordered handover: one task each, in turn, each within their own reach
        ld = P("leader")
        if ld and not ld.gripped["L"]:
            ld.hand_local["L"] = V((0.24, 0.14, 0.92))
        for i, nm in enumerate(("o1", "o2", "o3", "o4")):
            pf = P(nm)
            if not pf or pf.gripped["R"]:
                continue
            ta = 0.15 + 0.35 * i
            rest = pf.hand_local["R"]
            goal = V((-0.1, 0.4, 1.1))

            def task(t, p, pf=pf, ta=ta, rest=rest, goal=goal):
                x = ease(t, ta, ta + 0.35) * (1 - ease(t, ta + 0.9, ta + 1.3))
                p["hands"]["R"] = ("local", rest.lerp(goal, x) + V((0, 0, 0.01 * math.sin(6 * t))) * x)
                p["head"][1] += 15 * x
            pf.extra.append(task)

    if n == 28:  # the checklist: the leader holds it and ticks, one by one
        l = P("leader")
        cb = bpy.data.objects.get("cb")
        if cb and l:
            ticks = sorted([o for o in bpy.data.objects if o.name.startswith("cb_tick")], key=lambda o: o.name)
            for i, tk in enumerate(ticks):
                for f, t in frames(f0, f1):
                    on = ease(t, 0.25 + 0.3 * i, 0.32 + 0.3 * i)
                    key_obj(tk, f, scale=(max(0.001, on), max(0.001, on), max(0.001, on)))

    if n in (30, 31):  # the blocks drop into the stacks, one after another, with a little settle
        blocks = sorted([o for o in bpy.data.objects if o.name.startswith("blk")], key=lambda o: (o.location.x, o.location.z))
        for i, b in enumerate(blocks):
            rest = b.location.copy()
            for f, t in frames(f0, f1):
                ta = 0.05 + 0.09 * i
                x = overshoot(t, ta, ta + 0.32, 0.06)
                key_obj(b, f, loc=rest + V((0, 0, 1.2 * (1 - x))))

    if n == 34:  # a tiny hand closes around a gloved finger
        bh = bpy.data.objects.get("bhand")
        if bh:
            for f, t in frames(f0, f1):
                g = ease(t, 0.4, 1.2)
                key_obj(bh, f, scale=(1 + 0.15 * g, 1 - 0.25 * g, 1 + 0.1 * g))

    if n == 3:  # passers-by walk along the (raised) pavement, each in a lane, at a natural stride
        top = 0.16
        lanes = {0: 4.75, 1: 3.95, 2: 5.5, 3: 2.45}  # the trees stand at y 3.0-3.4
        for i in range(4):
            pf = P(f"walker{i}")
            if not pf:
                continue
            hd = pf.base["rot"]
            b0 = V((pf.base["loc"][0], lanes[i], top))
            pf.base["loc"] = list(b0)
            pf.a.place(b0, hd, 0.0)
            d = V((-math.sin(math.radians(hd)), math.cos(math.radians(hd)), 0))
            rt = V((math.cos(math.radians(hd)), math.sin(math.radians(hd)), 0))
            pf.foot_world = {k: V((b0.x, b0.y, top + 0.09)) + rt * (0.1 if k == "L" else -0.1) for k in "LR"}
            pf.hand_local = {"L": V((0.3, 0.02, 0.86)), "R": V((-0.3, 0.02, 0.86))}
            for k in "LR":
                if pf.gripped[k]:
                    free(pf, k)
            pf.walk(lambda t, b=b0, d=d, hd=hd: (b + d * 0.95 * t, hd), -0.6, dur + 0.4, cadence=2.3, duty=0.62, lift=0.08)
            pf.extra.append(lambda t, p, pf=pf: [p["hands"].__setitem__(k, ("local", pf.hand_local[k] + V((0, 0.13 * s * math.sin(math.pi * 2.3 * t), 0.02)))) for k, s in (("L", 1), ("R", -1))])

    return list(perf.values())


def pit_fx(n, perf, f0, f1, dur):
    """The pit stop as a real stop: car arrives, jacks up, guns off, tyres off/on, guns on, drop, go.
    Each shot plays its part of that sequence; the crew stay at their stations until the car has left."""
    P = perf.get
    car = bpy.data.objects.get("car")
    if n == 32 and car:  # board up, the car accelerates away; the crew rise as it clears them
        start = car.location.copy()
        h = V((-math.sin(car.rotation_euler.z), math.cos(car.rotation_euler.z), 0))
        for f, t in frames(f0, f1):
            key_obj(car, f, loc=start + h * (1.0 * t + 1.8 * t * t))
    if n in (32, 33):  # after the stop: guns carried, old tyres laid down clear of everyone, jack pulled aside
        for tag, sd, f in (("FL", 1, 1), ("FR", -1, 1), ("RL", 1, -1), ("RR", -1, -1)):
            t_ = bpy.data.objects.get(f"newtyre{tag}")
            if t_:  # (in this phase the 'new tyre' objects are the old tyres) stacked two high by the garage
                i_ = ("FL", "FR", "RL", "RR").index(tag)
                t_.location = (-3.45, 0.85 if i_ < 2 else -0.85, 0.17 + 0.34 * (i_ % 2))
            g = P(f"gun{tag}")
            gun = bpy.data.objects.get(f"wg{tag}")
            if g and gun:
                for k in "LR":
                    if g.gripped[k]:
                        free(g, k)
                bpy.context.view_layer.update()
                gun.parent = g.a.hand["R"]
                gun.location = (0, 0, 0)
                gun.rotation_euler = (math.radians(90), 0, 0)  # hanging from the hand, nose down
                gun.matrix_parent_inverse = Matrix.Identity(4)
                g.a.arm["holds"] = [gun.name]
                g.hand_local = {"L": V((0.3, 0.05, 0.86)), "R": V((-0.3, 0.08, 0.88))}
        jk = bpy.data.objects.get("fjack_eq")
        if jk:
            jk.location.x -= 1.3
        for nm in ("wing1", "wing-1"):
            pf = P(nm)
            if pf:
                sd = 1 if nm == "wing1" else -1
                nb = V((sd * 1.9, 3.4, 0))
                pf.base["loc"] = list(nb)
                pf.a.place(nb, pf.base["rot"], pf.base["crouch"])
                pf.foot_world = {k: pf.a.foot[k].matrix_world.translation.copy() for k in "LR"}
                pf.hand_local = {k: pf.a.arm.matrix_world.inverted() @ pf.a.hand[k].matrix_world.translation for k in "LR"}
    if n == 33:  # the box empties: everyone takes a step back and relaxes - shoulders drop, a look round
        for nm in ("fjack", "rjack"):
            pf = P(nm)
            if pf:
                for k in "LR":
                    if pf.gripped[k]:
                        free(pf, k)
                pf.hand_local = {"L": V((0.3, 0.05, 0.86)), "R": V((-0.3, 0.05, 0.86))}
        for i, pf in enumerate(perf.values()):
            if pf.a.name == "lolliman":
                continue
            if not pf.gripped["L"] and not pf.gripped["R"] and not pf.a.arm.get("holds"):
                pf.hand_local = {"L": V((0.3, 0.05, 0.86)), "R": V((-0.3, 0.05, 0.86))}
            b = V(pf.base["loc"])
            out = V((b.x, b.y * 0.15, 0)).normalized() if abs(b.x) > 0.3 else V((0, 1 if b.y > 0 else -1, 0))
            ta = 0.3 + 0.12 * (i % 5)
            pf.step_to("L", ta, ta + 0.32, pf.foot_world["L"] + out * 0.26)
            pf.step_to("R", ta + 0.3, ta + 0.62, pf.foot_world["R"] + out * 0.26)
            pf.path = (lambda t, b=b, out=out, ta=ta, hd=pf.base["rot"]: (b + out * 0.26 * ease(t, ta, ta + 0.62), hd))
            pf.extra.append(lambda t, p, ta=ta: (p.__setitem__("lean", p["lean"] * (1 - 0.7 * ease(t, ta, ta + 0.8))),
                                               p.__setitem__("crouch", p["crouch"] * (1 - 0.8 * ease(t, ta, ta + 0.8)))))
    if n == 24 or n == 23:  # the lollipop man: steady, then the board starts to lift
        l = P("lolliman")
        if l:
            l.extra.append(lambda t, p: p["hands"].__setitem__("R", ("local", l.hand_local["R"] + V((0, 0, 0.12)) * ease(t, dur * 0.55, dur * 1.1))) if not l.gripped["R"] else None)


# ---------------------------------------------------------------- camera
def fcurves(ob):
    """F-curves of an object's action (Blender 5 keeps them in the slot's channelbag of a layered action)."""
    ad = ob.animation_data
    if not ad or not ad.action:
        return []
    act = ad.action
    if hasattr(act, "fcurves"):
        return list(act.fcurves)
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            cb = strip.channelbag(ad.action_slot)
            if cb:
                out += list(cb.fcurves)
    return out


RUN_CAM = {6: (0, 2.0, 0), 7: (0, 2.25, 0), 10: (0, 2.3, 0)}  # (shot 9 is a close-up with a light handheld feel)
SHAKE = {6: (0.018, 0.7), 7: (0.022, 0.9), 10: (0.02, 0.8), 9: (0.0025, 0.3), 11: (0.01, 0.4), 12: (0.012, 0.5),
         13: (0.012, 0.5), 2: (0.004, 0.15), 16: (0.006, 0.2), 17: (0.008, 0.3), 18: (0.008, 0.3), 32: (0.01, 0.4)}


def bake_camera(n, f0, f1, t0, t1):
    sc = bpy.context.scene
    cam = sc.camera
    mv = dict(MOVES.get(1 if n == 35 else n, dict(push=0.3)))
    if n in RUN_CAM:  # the camera runs with the team
        mv.update(travel=RUN_CAM[n], follow=True)
    at, straight_down, m0 = camera_path(cam, mv)
    s1 = next(s for s in shots.SHOTS if s[0] == 1)
    travel = V(mv.get("travel", (0, 0, 0)))
    for f, t in frames(f0, f1):
        if n == 35:  # the shot-1 camera path, run backwards in time: lands exactly on shot 1's first frame
            u = (t - 1.9) / (s1[2] - s1[1]) - 0.5
        else:
            u = t / (t1 - t0) - 0.5
        loc, pivot, roll = at(u)
        if mv.get("follow"):
            loc, pivot = loc + travel * t, pivot + travel * t
        if straight_down:
            cam.matrix_world = Matrix.Translation(loc) @ (Matrix.Rotation(math.radians(roll), 4, "Z") @ m0.to_3x3().to_4x4())
        else:
            cam.location = loc
            look_at(cam, pivot, roll)
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
    if n in SHAKE:  # handheld feel: smooth noise, not jitter
        amp, ang = SHAKE[n]
        for fc in fcurves(cam):
            m = fc.modifiers.new("NOISE")
            m.scale = 9.0
            m.strength = amp * 2 if fc.data_path == "location" else math.radians(ang) * 2
            m.phase = fc.array_index * 7.3 + n
            m.blend_type = "ADD"


def ecg_keys(f0, f1):
    for m in bpy.data.materials:
        if m.name.startswith("px_custom_ecg"):
            mp = next(nd for nd in m.node_tree.nodes if nd.type == "MAPPING")
            for f, t in frames(f0, f1):
                mp.inputs["Location"].default_value[0] = 0.5 + 0.45 * (f / FPS)
                mp.inputs["Location"].keyframe_insert("default_value", index=0, frame=f)


# ---------------------------------------------------------------- one shot
def bake_shot(n, out_dir):
    table = {s[0]: s for s in shots.SHOTS}
    _, t0, t1, builder, desc = table[n]
    reset()
    lib.STYLE["voxel"], lib.STYLE["low"] = True, 0
    setup_render(1080, 1920, 16, "//frames/f")
    rig.calibrate()
    shots.build(table[1][3] if n == 35 else builder)
    perf = rig_cast()
    f0, f1 = round(t0 * FPS), round(t1 * FPS)
    dur = t1 - t0
    pfs = shot_fx(n, perf, f0, f1, dur)
    choreo.bake(pfs, f0, f1)
    bake_camera(n, f0, f1, t0, t1)
    ecg_keys(f0, f1)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = f0, f1 - 1
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = 0.5
    sc["shot"] = n
    sc["desc"] = desc
    for img in bpy.data.images:  # carry the screen images and pixel textures inside the file
        if img.source == "FILE" and not img.packed_file:
            try:
                img.pack()
            except RuntimeError:
                pass
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"s{n:02d}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    print(f"BAKED s{n:02d} frames {f0}-{f1 - 1} -> {path}", flush=True)
    return path


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [a for a in sys.argv[1:] if not a.endswith(".py")]
    out = argv[0]
    ids = [int(a) for a in argv[1:]] or [s[0] for s in shots.SHOTS]
    for n in ids:
        bake_shot(n, out)
