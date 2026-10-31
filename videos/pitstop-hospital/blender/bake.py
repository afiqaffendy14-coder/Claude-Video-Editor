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
import shots, voxel, rig, choreo
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


def regrip(pf, k, ob):
    pf.a.grip(k, ob)
    pf.gripped[k] = True


def free(pf, k):
    t = pf.a.hand[k]
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
def operate(pf, work, t_offset=0.0, spread=0.07, lift=0.0, instrument=True):
    """Surgeon at work: both hands over the work point, small precise movements, eyes on the hands."""
    for k in "LR":
        free(pf, k)
    a = pf.a
    r = a.right

    def fx(t, p, work=V(work)):
        tg = t + t_offset  # film clock: keeps shots 35 -> 1 continuous across the loop
        for k, s in (("L", -1), ("R", 1)):
            base = work + r * (s * spread) + V((0, 0, 0.04 + lift))
            d = V((wob(tg, 0.55 if k == "R" else 0.4, 0.018, pf.ph + s), wob(tg, 0.7 if k == "R" else 0.45, 0.014, pf.ph + 2 * s),
                   wob(tg, 0.9 if k == "R" else 0.6, 0.012, pf.ph + 3 * s) - 0.01 * (k == "R") * (1 + math.sin(2 * math.pi * 1.1 * tg))))
            p["hands"][k] = ("world", base + d)
        p["head"][1] += 18 + wob(tg, 0.3, 1.0)
        p["head"][0] = p["head"][0] * 0.3
        p["side"] *= 0.5
    pf.extra.append(fx)
    if instrument:  # forceps in the right hand
        M = palette()
        h = a.hand["R"]
        for i, dx in enumerate((-0.006, 0.006)):
            box(f"{pf.a.name}_forceps{i}", (0.006, 0.13, 0.006), tuple(h.location + a.heading * 0.08 + r * dx + V((0, 0, -0.03))),
                M["steel"], rot=(math.radians(-25), 0, a.arm.rotation_euler.z)).parent = h


def run_with(pf, base_xy, v, cadence=2.6, lean=14, lift=0.16, bob=0.045):
    """Sprint alongside the cot (root moves with v, planted running steps, bobbing, leaning in)."""
    hd = pf.base["rot"]
    b = V((base_xy[0], base_xy[1], 0))
    path = lambda t: (b + v * t, hd)
    pf.base["loc"] = list(b)
    pf.walk(path, -0.2, 3.0, cadence=cadence, duty=0.42, lift=lift, width=0.11)
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
                p["hands"][k] = ("local", hl + V((0, 0.2 * s * math.sin(math.pi * cadence * t + pf.ph), 0.12 + 0.06 * s * math.sin(math.pi * cadence * t + pf.ph))))
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


# ---------------------------------------------------------------- per-shot choreography
def shot_fx(n, perf, f0, f1, dur):
    P = perf.get
    M = palette()
    tg0 = {1: 0.0, 35: -1.9}.get(n, 0.0)

    if n in (1, 35):  # the surgeon operating; 35 is the 1.9 s just before 1 (seamless loop)
        s = P("surg")
        s.base.update(loc=[0.0, -0.33, 0.0], lean=31, crouch=0.04)
        s.a.place(V((0, -0.33, 0)), 0, 0.04)
        s.foot_world = {k: s.a.foot[k].matrix_world.translation.copy() for k in "LR"}
        operate(s, (0.0, 0.2, 0.86), t_offset=tg0)

    if n == 4:  # surgery on the table
        for nm, x in (("surg1", 0.6), ("surg2", -0.6)):
            pf = P(nm)
            if pf:
                pf.base.update(loc=[x, 0.32, 0], lean=32, crouch=0.05)
                pf.a.place(V((x, 0.32, 0)), pf.base["rot"], 0.05)
                pf.foot_world = {k: pf.a.foot[k].matrix_world.translation.copy() for k in "LR"}
                operate(pf, (math.copysign(0.09, x), 0.34, 1.2), spread=0.06, instrument=(x > 0))
        an = P("anaesthetist")
        if an:
            an.extra.append(lambda t, p: p["head"].__setitem__(1, p["head"][1] + 12))

    if n in (6, 7, 10):  # sprinting the cot to intensive care
        cot = bpy.data.objects.get("cot")
        cy = cot.location.y
        v = V((0, 2.3, 0))
        vent, iv = bpy.data.objects.get("cor_vent"), bpy.data.objects.get("cor_iv")
        if vent:
            vent.location = (-0.98, cy + 1.05, 0)
        if iv:
            iv.location = (0.98, cy - 0.32, 0)
        bag = box("ambu_bag", (0.09, 0.16, 0.08), (0.18, cy + 0.42, 0.98), mat("ambu", (0.2, 0.45, 0.85), 0.5))
        grips = {}

        def grip_on(parent, name, loc):
            grips[name] = empty_at(name, loc, parent)
            return grips[name]
        team = dict(porter=(0.0, cy - 0.98, 0), nurse_c1=(-0.66, cy + 0.0, 0), nurse_c2=(0.66, cy - 0.3, 0),
                    anaes_c=(0.62, cy + 0.6, 0), doc_c=(-0.62, cy + 0.72, 0))
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
        hands = {"porter": {"L": (cot, (-0.2, cy - 0.55, 0.9)), "R": (cot, (0.2, cy - 0.55, 0.9))},
                 "nurse_c1": {"R": (cot, (-0.37, cy + 0.02, 0.9))},
                 "nurse_c2": {"L": (cot, (0.37, cy - 0.3, 0.9)), "R": (iv, (0.98, cy - 0.32, 1.05))},
                 "anaes_c": {"L": (cot, (0.37, cy + 0.62, 0.9)), "R": (bag, (0.22, cy + 0.42, 0.98))},
                 "doc_c": {"L": (vent, (-0.8, cy + 1.02, 1.0))}}
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

    if n in (9, 11, 12, 13):  # intensive care: everyone scrambling
        cot = bpy.data.objects.get("icu_cot")
        cy = cot.location.y if cot else 0.3
        pts_in = [(0.12, cy + 0.15, 0.95), (-0.12, cy + 0.05, 0.95), (0.05, cy + 0.3, 0.97), (-0.05, cy - 0.15, 0.95)]
        for i, nm in enumerate(("c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8")):
            pf = P(nm)
            if not pf:
                continue
            near = (V(pf.base["loc"]) - V((0, cy, 0))).length < 1.05
            scramble(pf, seed=n * 10 + i, t1=dur, reach_pts=pts_in if near else (), radius=0.1 if near else 0.16)
        if n == 9:  # c2 pulls a line's connector apart, on camera
            line = bpy.data.objects.get("iv_line")
            pf = P("c2")
            if line and pf:
                junction = V((-0.42, 0.78, 0.95))
                conn = box("iv_conn", (0.035, 0.06, 0.035), tuple(junction), M["white"])
                cap = box("iv_conn_cap", (0.03, 0.02, 0.03), tuple(junction + V((0, 0.035, 0))), M["yellow"])
                cap.parent = conn
                cap.matrix_parent_inverse = conn.matrix_world.inverted()
                hook = line.modifiers.new("unplug", "HOOK")
                hook.object = conn
                # the baby-side half of the line follows the connector: hook the first two control points' handles
                hook.vertex_indices_set([6, 7, 8])
                start = junction.copy()
                pull = start + V((-0.12, -0.16, 0.16))
                for f, t in frames(f0, f1):
                    x = overshoot(t, 0.55, 1.15, 0.05)
                    key_obj(conn, f, loc=start.lerp(pull, x) + V((0, 0, 0.01 * math.sin(6 * t)) if x > 0 else V()),
                            rot=(math.radians(25 * x), 0, math.radians(-30 * x)))
                free(pf, "R")

                def unplug(t, p, conn_start=start, pull=pull):
                    reach = ease(t, 0.1, 0.5)
                    x = overshoot(t, 0.55, 1.15, 0.05)
                    hand = conn_start.lerp(pull, x) + V((0.03, -0.02, 0.01))
                    M_ = Matrix.Translation(p["loc"]) @ Matrix.Rotation(math.radians(p["rot"]), 4, "Z")
                    rest = M_ @ pf.hand_local["R"]
                    p["hands"]["R"] = ("world", rest.lerp(hand, reach))
                    p["head"][0] = 0.4 * p["head"][0]
                    p["head"][1] += 20 * reach
                pf.extra.append(unplug)
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

    if n in (2, 15, 16, 17, 18, 19, 23, 24, 32, 33):
        pit_fx(n, perf, f0, f1, dur)

    if n == 14:  # one doctor points at the screen
        b = P("docB")
        if b:
            free(b, "R")
            b.extra.append(lambda t, p: p["hands"].__setitem__("R", ("local", b.hand_local["R"] + V((0, 0.15, 0.32)) * ease(t, 0.3, 0.9))))

    if n in (21, 22):  # an engineer points at the hospital footage, another leans in
        e = P("eng3")
        if e:
            free(e, "R")
            e.extra.append(lambda t, p: p["hands"].__setitem__("R", ("local", e.hand_local["R"] + V((0.05, 0.2, 0.35)) * overshoot(t, 0.2, 0.9))))
        e2 = P("eng2")
        if e2:
            e2.extra.append(lambda t, p: p.__setitem__("lean", p["lean"] + 8 * ease(t, 0.3, 1.2)))

    if n == 20:  # the doctor picks up the phone
        c = P("caller")
        phone = bpy.data.objects.get("phone")
        if c and phone:
            free(c, "R")
            ph_start = phone.location.copy()
            scr = bpy.data.objects.get("phone_screen")
            if scr:
                scr.parent = phone
                scr.matrix_parent_inverse = phone.matrix_world.inverted()
            for f, t in frames(f0, f1):
                x = ease(t, 0.55, 1.4)
                key_obj(phone, f, loc=ph_start + V((0.05, -0.12, 0.28)) * x, rot=(math.radians(60 * x), 0, math.radians(15)))

            def pick(t, p):
                reach = ease(t, 0.0, 0.55)
                x = ease(t, 0.55, 1.4)
                pt = ph_start + V((0.05, -0.12, 0.28)) * x + V((0.03, -0.02, 0.02))
                M_ = Matrix.Translation(p["loc"]) @ Matrix.Rotation(math.radians(p["rot"]), 4, "Z")
                p["hands"]["R"] = ("world", (M_ @ c.hand_local["R"]).lerp(pt, reach))
            c.extra.append(pick)

    if n == 25:  # the lead anaesthetist raises his hand: everyone turns to him
        l = P("leader")
        if l:
            free(l, "R")
            l.extra.append(lambda t, p: p["hands"].__setitem__("R", ("local", l.hand_local["R"] + V((0, 0.08, -0.25)) * (1 - overshoot(t, 0.0, 0.7)))))
        for nm in ("o2", "o3", "o4"):
            pf = P(nm)
            if pf:
                pf.extra.append(lambda t, p: p["head"].__setitem__(0, p["head"][0] * 0.3 + 25 * ease(t, 0.15, 0.6)))

    if n in (26, 27, 29):  # the ordered handover: one task each, in turn
        cot = bpy.data.objects.get("icu_cot")
        cy = cot.location.y if cot else 0.3
        for i, nm in enumerate(("o1", "o2", "o3", "o4")):
            pf = P(nm)
            if not pf or pf.gripped["R"]:
                continue
            pt = V((0.1 * (1 if i % 2 else -1), cy + 0.1 - 0.12 * i, 0.94))
            ta = 0.15 + 0.35 * i

            def task(t, p, pf=pf, pt=pt, ta=ta):
                x = ease(t, ta, ta + 0.35) * (1 - ease(t, ta + 0.9, ta + 1.3))
                M_ = Matrix.Translation(p["loc"]) @ Matrix.Rotation(math.radians(p["rot"]), 4, "Z")
                p["hands"]["R"] = ("world", (M_ @ pf.hand_local["R"]).lerp(pt, x))
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

    if n == 3:  # passers-by walk along the pavement
        for i in range(4):
            pf = P(f"walker{i}")
            if not pf:
                continue
            b = V(pf.base["loc"])
            hd = pf.base["rot"]
            d = V((-math.sin(math.radians(hd)), math.cos(math.radians(hd)), 0))
            pf.walk(lambda t, b=b, d=d, hd=hd: (b + d * 1.25 * t, hd), -0.3, dur + 0.3, cadence=1.9, duty=0.62, lift=0.09)
            pf.extra.append(lambda t, p, pf=pf: [p["hands"].__setitem__(k, ("local", pf.hand_local[k] + V((0, 0.16 * s * math.sin(math.pi * 1.9 * t), 0.03)))) for k, s in (("L", 1), ("R", -1))])

    return list(perf.values())


def pit_fx(n, perf, f0, f1, dur):
    """The pit stop as a real stop: car arrives, jacks up, guns off, tyres off/on, guns on, drop, go.
    Each shot plays its part of that sequence; the crew stay at their stations until the car has left."""
    P = perf.get
    car = bpy.data.objects.get("car")
    span = {2: (0.05, 0.55), 16: (0.4, 0.75), 17: (0.2, 0.62), 18: (0.5, 0.92), 19: (0.78, 1.05)}.get(n)
    if span and car:
        p0, p1 = span
        prog = lambda t: p0 + (p1 - p0) * (t / dur)
        for tag, side, front in (("FL", 1, 1), ("FR", -1, 1), ("RL", 1, -1), ("RR", -1, -1)):
            wy = 1.8 if front > 0 else -1.78
            hub = V((side * (0.8 if front > 0 else 0.78), wy, 0.43))
            old = bpy.data.objects.get(f"car_w{'f' if front > 0 else 'r'}{side}")
            new = bpy.data.objects.get(f"newtyre{tag}")
            gun = bpy.data.objects.get(f"wg{tag}")
            out = V((side, 0, 0))
            aside = V((0, front, 0))
            for f, t in frames(f0, f1):
                q = prog(t)
                if old:  # off the hub, out past the gun, then swung aside to the tyre-off man's side
                    a = sstep((q - 0.15) / 0.25)
                    b = sstep((q - 0.4) / 0.3)
                    key_obj(old, f, loc=hub + out * (0.42 * a) + aside * (0.55 * b) + out * (0.18 * b) + V((0, 0, -0.05 * b)))
                if new:  # waiting outboard, then onto the hub
                    a = sstep((q - 0.45) / 0.3)
                    key_obj(new, f, loc=hub + out * (0.5 * (1 - a)) - aside * (0.45 * (1 - a)))
                if gun:  # on the nut (rattling), back out for the swap, back in to tighten
                    away = sstep((q - 0.12) / 0.08) * (1 - sstep((q - 0.75) / 0.08))
                    rattle = (q < 0.14 or q > 0.82) and q < 0.95
                    jit = V((0, 0, 0.004 * math.sin(2 * math.pi * 14 * t))) if rattle else V()
                    key_obj(gun, f, loc=hub + out * (0.155 + 0.21 + 0.22 * away) + jit,
                            rot=(0, 0, math.radians(90 if side > 0 else -90) + (math.radians(1.5) * math.sin(2 * math.pi * 11 * t) if rattle else 0)))
        if n == 19:  # job done: the car drops off the jacks
            for f, t in frames(f0, f1):
                key_obj(car, f, loc=(car.location.x, car.location.y, 0.07 * (1 - ease(prog(t), 0.97, 1.03))))
    if n == 15 and car:  # the car arrives and stops on its marks; the crew crouch, ready
        start = car.location.copy()
        for f, t in frames(f0, f1):
            k = min(1.0, t / dur)
            key_obj(car, f, loc=start + V((0, 2.6 * (1 - (1 - k) ** 2.2), 0)))
        for pf in perf.values():
            pf.extra.append(lambda t, p, pf=pf: p["head"].__setitem__(0, p["head"][0] * 0.4 - 18 * (1 - ease(t, 0.0, dur))))
    if n == 32 and car:  # board up, the car accelerates away; the crew rise as it clears them
        start = car.location.copy()
        h = V((-math.sin(car.rotation_euler.z), math.cos(car.rotation_euler.z), 0))
        for f, t in frames(f0, f1):
            key_obj(car, f, loc=start + h * (1.0 * t + 1.8 * t * t))
    if n == 33:  # the box empties: the crew walk back to the garage, a few calm steps
        for pf in perf.values():
            b = V(pf.base["loc"])
            hd = pf.base["rot"]
            to_g = V((-1, 0.15, 0)).normalized()
            pf.walk(lambda t, b=b, hd=hd, d=to_g: (b + d * 0.7 * max(0.0, t - 0.25), hd), -0.2, dur + 0.3, cadence=1.6, duty=0.65, lift=0.07)
    if n == 24 or n == 23:  # the lollipop man: steady, then the board starts to lift
        l = P("lolliman")
        if l:
            l.extra.append(lambda t, p: p["hands"].__setitem__("R", ("local", l.hand_local["R"] + V((0, 0, 0.12)) * ease(t, dur * 0.55, dur * 1.1))) if not l.gripped["R"] else None)
    for nm in ("fjack", "rjack"):  # jack men hold the lever down, leaning back on it
        pf = P(nm)
        if pf:
            pf.extra.append(lambda t, p: p.__setitem__("lean", p["lean"] - 3 + wob(t, 0.5, 1.5)))


# ---------------------------------------------------------------- camera
SHAKE = {6: (0.018, 0.7), 7: (0.022, 0.9), 10: (0.02, 0.8), 9: (0.008, 0.35), 11: (0.01, 0.4), 12: (0.012, 0.5),
         13: (0.012, 0.5), 2: (0.004, 0.15), 16: (0.006, 0.2), 17: (0.008, 0.3), 18: (0.008, 0.3), 32: (0.01, 0.4)}


def bake_camera(n, f0, f1, t0, t1):
    sc = bpy.context.scene
    cam = sc.camera
    mv = MOVES.get(1 if n == 35 else n, dict(push=0.3))
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
        ad = cam.animation_data
        for fc in ad.action.fcurves if hasattr(ad.action, "fcurves") else []:
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
