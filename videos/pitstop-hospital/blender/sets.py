"""Sets, each built around its own origin: pit lane, operating theatre, corridor, ICU bay, hospital exterior,
viewing room, Ferrari engineering room, chart stage. A shot builds exactly one set (plus its cast)."""
import math
import bpy
from mathutils import Vector
from lib import (V, box, cyl, sphere, torus, tube, mesh_obj, palette, area, world, cyclorama, mat, group, link, sun)
from people import person
from props import (f1car, wheel, wheel_gun, lollipop, jack, cot, monitor, iv_pole, vent, op_table,
                   surgical_lamp, drapes, clipboard, jack_between)

# reusable poses ------------------------------------------------------------------
POSE = dict(
    stand=dict(),
    gun=dict(crouch=0.5, lean=35, legL=(85, 12, 125), legR=(45, 12, 115), armL=(80, 8, 25), armR=(70, 5, 35), head=(0, 10)),
    tyre_hold=dict(crouch=0.12, lean=18, legL=(25, 8, 30), legR=(10, 8, 20), armL=(55, 20, 70), armR=(55, 20, 70)),
    tyre_off=dict(crouch=0.25, lean=30, legL=(50, 10, 60), legR=(20, 10, 50), armL=(70, 10, 30), armR=(70, 10, 30)),
    jack=dict(crouch=0.15, lean=25, legL=(35, 6, 30), legR=(-10, 6, 15), armL=(55, 6, 20), armR=(55, 6, 20)),
    brace=dict(crouch=0.2, lean=35, legL=(40, 10, 50), legR=(10, 10, 40), armL=(80, 5, 10), armR=(80, 5, 10)),
    lolli=dict(armR=(65, 10, 50), armL=(10, 10, 20), head=(0, -5)),
    work=dict(lean=22, head=(0, 30), armL=(55, 6, 60), armR=(55, 6, 60)),
    reach=dict(lean=28, head=(0, 25), armL=(75, 4, 20), armR=(40, 10, 70)),
    reach2=dict(lean=18, head=(15, 15), armL=(30, 15, 40), armR=(85, 0, 10)),
    push=dict(lean=12, armL=(60, 4, 30), armR=(60, 4, 30), legL=(20, 4, 15), legR=(-15, 4, 10)),
    walk=dict(armL=(-20, 6, 15), armR=(25, 6, 25), legL=(-18, 4, 8), legR=(22, 4, 20)),
    lead=dict(armR=(140, 15, 25), armL=(30, 8, 50), head=(-10, 5)),
    watch=dict(head=(0, 5), armL=(10, 10, 80), armR=(5, 10, 20)),
    talk=dict(armR=(45, 15, 70), armL=(15, 10, 40), head=(20, 0)),
    sit=dict(crouch=0.45, lean=5, legL=(90, 6, 90), legR=(90, 6, 90), armL=(55, 6, 55), armR=(55, 6, 55)),
    hold_bag=dict(lean=10, armL=(50, 10, 60), armR=(70, 10, 40), head=(0, 25)),
    # pit-stop action
    carry_out=dict(crouch=0.12, lean=-8, legL=(-15, 6, 10), legR=(28, 6, 22), armL=(50, 25, 60), armR=(50, 25, 60), head=(0, 12)),
    tyre_push=dict(crouch=0.18, lean=28, legL=(42, 8, 40), legR=(-12, 8, 15), armL=(72, 18, 22), armR=(72, 18, 22)),
    jack_lift=dict(crouch=0.12, lean=-14, legL=(-25, 8, 15), legR=(32, 8, 25), armL=(38, 6, 8), armR=(38, 6, 8)),
    ready=dict(crouch=0.28, lean=22, legL=(32, 12, 42), legR=(32, 12, 42), armL=(42, 10, 40), armR=(42, 10, 40)),
    go_signal=dict(armR=(165, 8, 5), armL=(15, 10, 20), head=(0, -12)),
    step_back=dict(lean=-6, legL=(-22, 6, 10), legR=(22, 6, 15), armL=(25, 15, 30), armR=(25, 15, 30), head=(0, -5)),
)


def hand_world(root, k="R"):
    """World position of a block person's hand (set by voxel.block_person), or None."""
    if ("hand" + k) not in root:
        return None
    bpy.context.view_layer.update()
    return root.matrix_world @ Vector(root["hand" + k])


def hands_mid(root):
    """Midpoint between a block person's hands, in world space (None for the smooth mannequins)."""
    l, r = hand_world(root, "L"), hand_world(root, "R")
    return None if l is None else (l + r) / 2


def hold(obj, root, fallback):
    """Put a wheel between a person's hands, its axle along the line from hand to hand."""
    register_hold(obj.name, root.name, "wheel")
    l, r = hand_world(root, "L"), hand_world(root, "R")
    if l is None:
        obj.location = fallback
        return
    d = r - l
    obj.location = (l + r) / 2
    obj.rotation_euler = (0, 0, math.atan2(d.y, d.x))


def P(name, x, y, rot, pose, outfit, **kw):
    pose_ = POSE[pose] if isinstance(pose, str) else pose
    r = person(name, (x, y, 0), rot, pose_, outfit, **kw)
    r["pose_name"] = pose if isinstance(pose, str) else "custom"
    return r


def register_hold(obj_name, person_name, mode, **extra):
    """Record that a prop follows a person's hands (anim_people.py re-places it every frame)."""
    import json
    sc = bpy.context.scene
    holds = json.loads(sc.get("holds", "[]"))
    holds.append(dict(obj=obj_name, person=person_name, mode=mode, **extra))
    sc["holds"] = json.dumps(holds)


# ---------------------------------------------------------------- pit lane
def pit_set(car_y=0.0, crew=True, wheels_off=False, lit=True, car=True, crew_skip=(), phase="ready"):
    """Car faces +Y in its box at the origin; garage on -X; pit wall on +X."""
    M = palette()
    world(0.55, (0.93, 0.94, 0.96))
    box("pit_floor", (40, 80, 0.1), (0, 0, -0.05), M["clay"])
    # painted box: grey outline + darker working lane
    for x, y, sx, sy in [(-1.6, 0, 0.08, 7.6), (1.6, 0, 0.08, 7.6), (0, 3.8, 3.28, 0.08), (0, -3.8, 3.28, 0.08)]:
        box("pit_line", (sx, sy, 0.005), (x, y, 0.003), M["clay2"])
    box("fast_lane_line", (0.12, 80, 0.005), (3.5, 0, 0.003), M["clay2"])
    # garage
    box("gar_back", (0.3, 12, 5), (-10.5, 0, 2.5), M["clay"])
    for s in (1, -1):
        box("gar_side", (6, 0.3, 5), (-7.5, s * 6, 2.5), M["clay"])
    box("gar_roof", (6.6, 12.6, 0.4), (-7.3, 0, 5.1), M["clay"])
    box("gar_header", (0.5, 12.6, 1.0), (-4.4, 0, 4.4), M["clay"])
    box("gar_floor", (6, 12, 0.02), (-7.5, 0, 0.01), M["clay2"])
    for i in range(3):  # tyre stacks inside
        for j in range(4):
            w = wheel(f"stack{i}{j}", 0.33, 0.33, 1)
            w.location = (-9.7, -3.5 + i * 0.8, 0.17 + j * 0.34)
            w.rotation_euler = (0, math.pi / 2, 0)
    for i in range(3):
        m = monitor(f"gar_mon{i}", 0.9, 0.55, wave=False)
        m.location = (-10.3, 1.5 + i * 1.1, 2.4)
        m.rotation_euler = (0, 0, -math.pi / 2)
    # overhead gantry with rig lights, neighbouring garages' walls
    box("gantry", (0.3, 8, 0.3), (-3.6, 0, 3.9), M["grey"], bev=0.04)
    for y in (-2.5, 0, 2.5):
        box("rig", (0.4, 0.4, 0.15), (-3.6, y, 3.7), M["dark"], bev=0.04)
    for s in (1, -1):
        box("neighbour", (6, 0.3, 5), (-7.5, s * 13, 2.5), M["clay"])
    # pit wall + catch fence posts
    box("pit_wall", (0.6, 80, 1.1), (7.5, 0, 0.55), M["clay"], bev=0.05)
    for y in range(-30, 31, 4):
        cyl("fence", 0.05, 4, (7.7, y, 3.0), M["grey"], seg=8)
    if car:
        c = f1car("car")
        c.location = (0, car_y, 0.0)
        if wheels_off:
            for nm in ("car_wf1", "car_wf-1"):
                bpy.data.objects[nm].location.x *= 1.6
    if car and phase in ("swap",):
        bpy.data.objects["car"].location.z = 0.07  # up on the jacks
    if crew:
        pit_crew(crew_skip, phase, car)
    import lib
    if lib.STYLE.get("voxel"):
        import dress
        dress.pit_dress()
        return M
    if lit:
        bg = bpy.context.scene.world.node_tree.nodes["Background"]
        bg.inputs[0].default_value = (0.45, 0.65, 1.0, 1)
        bg.inputs[1].default_value = 0.7
        sun("pit_sun", (42, 0, -50), 4.5, 2.0, (1.0, 0.93, 0.82))
    return M


def pit_crew(skip=(), phase="ready", car=True):
    """About twenty: three per wheel, two jacks, two stabilisers, two wing men, the lollipop man.
    phase: 'ready' (poised, car in the box), 'arrive' (poised, car rolling in), 'swap' (car on jacks, old tyres
    coming off, new ones going on), 'go' (crew stepping back, board up, car leaving or gone)."""
    cast = []
    swap, go = phase == "swap", phase == "go"
    for (y, side, tag, wn) in [(1.8, 1, "FL", "car_wf1"), (1.8, -1, "FR", "car_wf-1"), (-1.78, 1, "RL", "car_wr1"), (-1.78, -1, "RR", "car_wr-1")]:
        if tag in skip:
            continue
        rot = 90 if side == 1 else -90  # face the car (people face +Y at rot 0)
        out = side * (0.5 if go else 0.0)  # step back from the car when it goes
        gun = P(f"gun{tag}", side * 1.45 + out, y, rot, "step_back" if go else "gun", "crew")
        cast.append(gun)
        g = wheel_gun(f"wg{tag}")
        g.rotation_euler = (0, 0, math.radians(rot))
        hm = hands_mid(gun)
        g.location = hm if hm is not None else (side * (1.15 if not go else 1.75), y, 0.38 if not go else 0.9)
        register_hold(g.name, gun.name, "mid")
        off = P(f"off{tag}", side * 1.75 + out, y + 0.75, rot + side * 25,
                "carry_out" if swap else ("step_back" if go else "tyre_off"), "crew")
        on = P(f"on{tag}", side * 1.8 + out, y - 0.75, rot - side * 25,
               "tyre_push" if swap else ("step_back" if go else "tyre_hold"), "crew")
        cast += [off, on]
        t = wheel(f"newtyre{tag}", 0.36, 0.34, 1)
        if go:  # the old tyre is left lying beside the box
            t.location = (side * 2.6, y + 0.4, 0.17)
            t.rotation_euler = (0, math.radians(90), 0)
        else:  # the new tyre is held between the tyre-on man's hands (sidewalls in his palms)
            hold(t, on, fallback=(side * 1.45, y - 0.85, 0.62))
        if swap and car and wn in bpy.data.objects:  # the old tyre comes away in the tyre-off man's hands
            w = bpy.data.objects[wn]
            mw = w.matrix_world.copy()
            w.parent = None
            w.matrix_world = mw
            hold(w, off, fallback=(side * 1.55, y + 0.55, 0.52))
    if "jacks" not in skip:
        jp = "jack_lift" if swap else ("step_back" if go else "jack")
        fj = P("fjack", -1.25 if go else 0, 4.0 if not go else 3.9, 180, jp, "crew")  # steps aside to let the car out
        rj = P("rjack", 0, -3.9, 0, jp, "crew")
        cast += [fj, rj]
        lift = 0.07 if swap else 0.0
        if go:  # the front jack is pulled clear of the exit, lying beside the box
            jack_between("fjack_eq", (-1.75, 3.0, 0.11), (-1.75, 4.3, 0.14))
        else:
            fm = hands_mid(fj)
            jack_between("fjack_eq", (0, 2.95, 0.12 + lift), fm if fm is not None else (0, 4.3, 0.9))
            register_hold("fjack_eq", fj.name, "jack", head=[0, 2.95, 0.12 + lift])
        rm = hands_mid(rj)
        jack_between("rjack_eq", (0, -2.85, 0.12 + lift), rm if rm is not None else (0, -4.2, 0.9))
        register_hold("rjack_eq", rj.name, "jack", head=[0, -2.85, 0.12 + lift])
    for s in (1, -1):
        if "stab" not in skip:
            cast.append(P(f"stab{s}", s * (1.3 + (0.5 if go else 0)), 0.1, 90 * s, "step_back" if go else "brace", "crew"))
        if "wing" not in skip:
            cast.append(P(f"wing{s}", s * (1.2 + (0.5 if go else 0)), 2.95, 180 - s * 30, "step_back" if go else "brace", "crew"))
    if "lolli" not in skip:
        lm = P("lolliman", -0.9, 4.6, 180, "go_signal" if go else "lolli", "crew")
        cast.append(lm)
        l = lollipop("lolli_eq")
        h = hand_world(lm, "R")
        if h is not None:  # the pole sits in his right hand; board leans toward the driver (or straight up for go)
            l.location = h
            register_hold(l.name, lm.name, "hand", hand="R")
            l.rotation_euler = (0 if go else math.radians(18), 0, 0)
        elif go:  # board lifted high: go
            l.location = (-0.72, 4.62, 1.15)
            l.rotation_euler = (0, 0, 0)
        else:
            l.location = (-0.75, 4.25, 0.65)
            l.rotation_euler = (math.radians(28), 0, 0)
    return cast


# ---------------------------------------------------------------- operating theatre
def theatre_set(team=True, lamps_aside=False):
    M = palette()
    world(0.25, (0.85, 0.9, 0.95))
    wall = mat("theatre_wall", (0.62, 0.72, 0.74), 0.7)
    box("th_floor", (9, 9, 0.1), (0, 0, -0.05), M["clay2"])
    for x, y, sx, sy in [(-4.5, 0, 0.2, 9), (4.5, 0, 0.2, 9), (0, 4.5, 9, 0.2), (0, -4.5, 9, 0.2)]:
        box("th_wall", (sx, sy, 3.4), (x, y, 1.7), wall)
    box("th_ceiling", (9, 9, 0.2), (0, 0, 3.4), M["clay"])
    for x in (-2.5, 2.5):
        box("th_panel", (1.6, 1.6, 0.04), (x, 0, 3.29), M["panel"])
    op_table("table")
    # the tiny patient under drapes, only the drape shape shows
    d = drapes("drape", 1.0, 0.75)
    d.location = (0, 0.15, 1.08)
    import lib
    if lib.STYLE.get("voxel"):  # the baby on the table: face up, cap, closed eyes; dark surgical drape so it reads
        px = 0.045
        drape_dark = mat("drape_dark", (0.05, 0.3, 0.34), 0.85)
        bpy.data.objects["drape"].data.materials[0] = drape_dark
        top = 1.15 + 1.75 * px
        box("op_baby_head", (5 * px, 5 * px, 3.5 * px), (0, 0.62, 1.15), M["babyskin"])
        box("op_baby_cap", (5 * px + 0.01, 1.6 * px, 3.5 * px + 0.012), (0, 0.69, 1.152), mat("babyhat", (0.98, 0.9, 0.75), 0.9))
        for sx in (1, -1):
            box(f"op_baby_eye{sx}", (1.1 * px, 0.35 * px, 0.008), (sx * 1.1 * px, 0.62, top), M["dark"])
            box(f"op_baby_cheek{sx}", (px, px, 0.006), (sx * 1.5 * px, 0.57, top), mat("cheek", (0.95, 0.5, 0.45), 0.6))
        box("op_baby_body", (6 * px, 9 * px, 2 * px), (0, 0.28, 1.13), drape_dark)
        box("op_site", (2.4 * px, 2.4 * px, 0.012), (0, 0.36, 1.18), mat("site", (0.85, 0.45, 0.4), 0.5))
    else:
        sphere("pt_bump", 1, (0, 0.2, 1.1), M["gown"], scale=(0.16, 0.3, 0.06))
    for i, (x, y) in enumerate([(-1.1, 0.9), (1.2, -0.9)] if lamps_aside else [(-0.45, 0.4), (0.5, -0.2)]):
        l = surgical_lamp(f"lamp{i}", 1.0)
        l.location = (x, y, 2.15)
        l.rotation_euler = (math.radians(12 if i else -10), math.radians(10 if i else -15), 0)
    vent("anaes").location = (0, 1.5, 0)
    mn = monitor("th_mon", 0.6, 0.4)
    mn.location = (0.95, 1.25, 1.75)
    mn.rotation_euler = (0, 0, math.radians(200))
    cyl("th_boom", 0.03, 1.4, (0.95, 1.3, 2.6), M["white"])
    iv_pole("th_iv").location = (-0.9, 1.0, 0)
    box("th_trolley", (0.5, 0.9, 0.05), (1.4, -1.0, 0.9), M["steel"], bev=0.01)
    for sx in (1, -1):
        for sy in (1, -1):
            cyl("tl", 0.015, 0.9, (1.4 + sx * 0.2, -1.0 + sy * 0.4, 0.45), M["steel"])
    if team:
        P("surg1", 0.75, 0.05, 90, "work", "surgeon")
        P("surg2", -0.75, 0.15, -90, "work", "surgeon")
        P("surg3", 0.7, -0.7, 60, "reach", "surgeon")
        P("nurse1", -0.8, -0.8, -60, "work", "surgeon")
        P("anaesthetist", 0.35, 1.35, 160, "watch", "surgeon")
    import lib
    if lib.STYLE.get("voxel"):  # blocky look reads brighter: calm the lamps and the key
        bpy.data.materials["lamp"].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 1.5
    area("th_key", (0, 0, 3.1), (0, 0, 0), 900 if not lib.STYLE.get("voxel") else 320, 2.5)
    area("th_fill", (3, -3, 2.8), (0, 0, 1), 250, 3)
    area("th_fill2", (-3, 3, 2.8), (0, 0, 1), 150, 3)


# ---------------------------------------------------------------- corridor
def corridor_set(cot_y=0.0, team=True, dim=False):
    M = palette()
    world(0.12 if dim else 0.25, (0.85, 0.9, 0.95))
    wall = mat("cor_wall", (0.75, 0.78, 0.78), 0.7)
    box("cor_floor", (3.2, 40, 0.1), (0, 0, -0.05), M["clay2"])
    for s in (1, -1):
        box("cor_wall", (0.2, 40, 3.2), (s * 1.6, 0, 1.6), wall)
        box("cor_rail", (0.06, 40, 0.12), (s * 1.5, 0, 0.95), M["clay"], bev=0.02)
        for y in range(-16, 17, 6):
            box("cor_door", (0.08, 1.4, 2.2), (s * 1.52, y + (1.5 if s > 0 else 0), 1.1), M["clay2"], bev=0.02)
            box("cor_win", (0.09, 0.3, 0.5), (s * 1.52, y + (1.5 if s > 0 else 0) + 0.3, 1.6), M["glass"])
    box("cor_ceiling", (3.2, 40, 0.1), (0, 0, 3.2), M["clay"])
    for y in range(-18, 19, 3):
        box("cor_light", (0.8, 1.4, 0.04), (0, y, 3.14), M["panel"])
    # double doors to intensive care at the far end
    box("icu_frame", (3.2, 0.2, 3.2), (0, 18, 1.6), M["clay"])
    for s in (1, -1):
        box("icu_door", (0.95, 0.08, 2.3), (s * 0.5, 17.85, 1.15), M["white"], bev=0.02)
        box("icu_doorwin", (0.4, 0.09, 0.5), (s * 0.5, 17.83, 1.6), M["glass"])
    if team:
        c = cot("cot")
        c.location = (0, cot_y, 0)
        v = vent("cor_vent")
        v.location = (0.55, cot_y + 0.9, 0)
        iv = iv_pole("cor_iv")
        iv.location = (-0.5, cot_y + 0.75, 0.0)
        P("porter", 0, cot_y - 1.0, 0, "push", "scrubs")
        P("anaes_c", 0.1, cot_y + 1.0, 180, "hold_bag", "surgeon")
        P("nurse_c1", -0.75, cot_y + 0.2, -80, "walk", "scrubs")
        P("nurse_c2", 0.75, cot_y - 0.3, 80, "walk", "scrubs")
        P("doc_c", 0.65, cot_y + 0.6, 100, "reach2", "surgeon")
    area("cor_fill", (0, cot_y - 4, 2.9), (0, cot_y + 3, 0.5), 300 if dim else 700, 3)


# ---------------------------------------------------------------- ICU bay
def icu_set(mode="chaos", baby=True, skip=()):
    """mode: 'chaos' (crowded, everyone at once) | 'order' (roles, one leader) | 'empty'."""
    M = palette()
    world(0.05, (0.6, 0.8, 0.9))
    wall = mat("icu_wall", (0.38, 0.55, 0.56), 0.75)
    box("icu_floor", (8, 8, 0.1), (0, 0, -0.05), mat("icu_floor", (0.42, 0.47, 0.5), 0.6))
    box("icu_back", (8, 0.2, 3.2), (0, 2.2, 1.6), wall)
    for s in (1, -1):
        box("icu_side", (0.2, 6, 3.2), (s * 3.2, -0.8, 1.6), wall)
    box("icu_ceiling", (8, 8, 0.1), (0, 0, 3.2), M["clay"])
    box("icu_front", (8, 0.2, 3.2), (0, -3.8, 1.6), wall)
    box("icu_window", (2.4, 0.1, 1.2), (-1.2, -3.68, 1.6), mat("icu_win", (0.8, 0.9, 1.0), 0.2, emit=(0.75, 0.88, 1.0), emit_strength=1.5))
    box("icu_door", (1.2, 0.1, 2.2), (1.6, -3.68, 1.1), M["white"], bev=0.02)
    box("icu_light", (0.9, 0.5, 0.04), (0, 0.2, 3.14), mat("icu_glow", (1, 1, 1), 0.3, emit=(1.0, 0.85, 0.65), emit_strength=3))
    box("gas_rail", (3.0, 0.1, 0.25), (0, 2.08, 1.45), M["white"], bev=0.03)
    for i in range(6):
        cyl("outlet", 0.035, 0.05, (-1.2 + i * 0.48, 2.02, 1.45), M["grey"] if i % 2 else M["yellow"], rot=(math.pi / 2, 0, 0))
    c = cot("icu_cot", baby=baby, tubes=True)
    c.location = (0, 0.3, 0)
    m = monitor("icu_mon", 0.55, 0.38)
    m.location = (0.95, 1.95, 1.9)
    box("mon_arm", (0.6, 0.06, 0.06), (0.7, 2.0, 1.9), M["white"], bev=0.02)
    v = vent("icu_vent")
    v.location = (-1.0, 1.55, 0)
    iv_pole("icu_iv1").location = (1.2, 1.65, 0)
    iv_pole("icu_iv2").location = (-1.55, 1.4, 0)
    # cables from the cot to the wall
    tube("cab1", [V((0.25, 0.7, 0.8)), V((0.6, 1.3, 0.7)), V((0.9, 1.9, 1.7))], 0.006, M["dark"])
    tube("cab2", [V((-0.2, 0.75, 0.8)), V((-0.6, 1.2, 1.0)), V((-0.95, 1.6, 1.1))], 0.012, M["tube"])
    if mode == "chaos":
        cast = [("c1", 0.75, 0.4, 100, "reach"), ("c2", -0.75, 0.5, -95, "reach2"), ("c3", 0.6, -0.55, 50, "talk"),
                ("c4", -0.6, -0.65, -40, "reach"), ("c5", 0.05, -0.95, 10, "talk"), ("c6", 1.2, 0.9, 140, "work"),
                ("c7", -1.25, -0.1, -110, "talk"), ("c8", 0.35, 1.2, 200, "reach2")]
        outfits = ["surgeon", "scrubs", "scrubs", "surgeon", "doctor", "scrubs", "surgeon", "scrubs"]
        for (n, x, y, r, p), o in zip(cast, outfits):
            P(n, x, y, r, p, o)
    elif mode == "order":
        P("leader", 0.0, -0.75, 0, "lead", "leader")
        if "o1" not in skip: P("o1", 0.75, 0.45, 90, "work", "scrubs")
        if "o2" not in skip: P("o2", -0.75, 0.45, -90, "work", "scrubs")
        if "o3" not in skip: P("o3", 0.85, -0.3, 75, "watch", "scrubs")
        if "o4" not in skip: P("o4", -0.85, -0.3, -75, "watch", "surgeon")
    area("icu_key", (0.3, 0.1, 2.6), (0, 0.3, 0.7), 110, 0.9, color=(1.0, 0.86, 0.68))
    area("icu_rim", (-2.6, 1.8, 2.4), (0, 0.2, 1.0), 220, 1.5, color=(0.55, 0.8, 1.0))
    area("icu_fill", (2.5, -3, 2.0), (0, 0.3, 1.0), 60, 3, color=(0.7, 0.85, 1.0))
    import lib
    if lib.STYLE.get("voxel"):
        import dress
        dress.icu_dress()
        if baby:
            hose = mat("hose", (0.85, 0.92, 0.96), 0.3)
            ivl = mat("ivline_soft", (0.45, 0.75, 1.0), 0.25)
            et = tube("et_hose", [V((0.0, 0.54, 0.86)), V((0.0, 0.5, 1.02)), V((-0.32, 0.86, 1.12)),
                                  V((-0.78, 1.28, 1.05)), V((-0.95, 1.37, 0.95))], 0.014, hose)
            iv = tube("iv_line", [V((-0.1, 0.48, 0.8)), V((-0.3, 0.62, 0.93)), V((-0.42, 0.78, 0.95)),
                                  V((-0.95, 1.12, 1.08)), V((-1.45, 1.4, 1.68))], 0.006, ivl)
            et["smooth"] = True
            iv["smooth"] = True
            box("iv_tape", (0.05, 0.04, 0.02), (-0.1, 0.48, 0.79), M["white"])


# ---------------------------------------------------------------- hospital exterior (London)
def exterior_set():
    M = palette()
    import lib
    if lib.STYLE.get("voxel"):  # passers-by on the pavement
        for i, (x, y, r, o) in enumerate([(9.5, 4.6, 90, "suit"), (13.5, 3.4, -90, "doctor"), (16.5, 4.9, 90, "engineer"), (11.8, 5.2, -90, "scrubs")]):
            P(f"walker{i}", x, y, r, "walk", o)
    world(0.8, (0.9, 0.93, 0.98))
    brick = mat("facade", (0.78, 0.74, 0.7), 0.8)
    box("street", (120, 120, 0.1), (0, 0, -0.05), M["clay2"])
    box("pavement", (60, 4, 0.16), (0, 4, 0.08), M["clay"])
    box("facade", (40, 12, 18), (0, 16, 9), brick)
    for i in range(-9, 10):
        for j in range(5):
            box("win", (1.1, 0.1, 1.6), (i * 2.0, 9.95, 2.6 + j * 3.2), M["grey"], bev=0.02)
            box("sill", (1.3, 0.25, 0.12), (i * 2.0, 9.9, 1.75 + j * 3.2), M["clay"])
    box("canopy", (8, 2.5, 0.25), (0, 8.8, 3.6), M["clay"], bev=0.05)
    for s in (1, -1):
        cyl("canopy_post", 0.1, 3.5, (s * 3.6, 7.8, 1.8), M["clay"])
    box("door", (3, 0.12, 2.8), (0, 9.95, 1.4), M["dark"])
    for x in (-14, -8, 8, 14):  # street trees
        cyl("trunk", 0.15, 3, (x, 3.2, 1.5), M["grey"])
        sphere("crown", 1.6, (x, 3.2, 4.2), mat("leaf", (0.42, 0.52, 0.42), 0.9), scale=(1, 1, 0.9))
    # distant clock tower in haze
    tw = mat("tower", (0.82, 0.83, 0.86), 0.9)
    import lib
    tx = 45 if lib.STYLE.get("voxel") else -45  # blocky shot looks right of the facade
    box("tower", (4, 4, 40), (tx, 90, 20), tw)
    box("clockblk", (5, 5, 6), (tx, 90, 42), tw)
    cyl("spire", 3.2, 10, (tx, 90, 50), tw, seg=4, r2=0.2, rot=(0, 0, math.pi / 4))
    for s in (1, -1):
        cyl("clockface", 1.6, 0.1, (tx, 90 - 2.55, 42), M["clay"], rot=(math.pi / 2, 0, 0))
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.0
    sun.angle = math.radians(8)
    so = link(bpy.data.objects.new("sun", sun))
    so.rotation_euler = (math.radians(55), 0, math.radians(-35))
    sc = bpy.context.scene
    # haze so the tower fades into the sky
    w = sc.world
    import lib
    if lib.STYLE.get("voxel"):  # blocky: gradient sky and block clouds instead of haze
        import dress
        dress.sky_world()
        dress.clouds((0, 30), n=10, z=40, spread=60)
        return
    vol = w.node_tree.nodes.new("ShaderNodeVolumeScatter")
    vol.inputs["Density"].default_value = 0.004
    w.node_tree.links.new(vol.outputs[0], w.node_tree.nodes["World Output"].inputs["Volume"])


# ---------------------------------------------------------------- rooms with a screen
def screen_image(name, img_path, size=(1.6, 0.9), loc=(0, 0, 1.5), rot=0.0, strength=1.4):
    """A wall screen showing a rendered image (used to show one shot inside another)."""
    m = bpy.data.materials.new(name + "_mat")
    m.use_nodes = True
    nt = m.node_tree
    em = nt.nodes.new("ShaderNodeEmission")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(img_path)
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    w, h = size
    ob = mesh_obj(name, [V((-w / 2, 0, -h / 2)), V((w / 2, 0, -h / 2)), V((w / 2, 0, h / 2)), V((-w / 2, 0, h / 2))],
                  [(0, 1, 2, 3)], m)
    uv = ob.data.uv_layers.new()
    for i, c in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[i].uv = c
    ob.location = loc
    ob.rotation_euler = (0, 0, rot)
    return ob


def viewing_room(img, outfit="doctor"):
    """Staff room: two doctors watching a pit stop on a wall screen (screen-lit, but not murky)."""
    M = palette()
    world(0.18, (0.8, 0.85, 0.9))
    area("vr_ceiling", (0, 0, 3.0), (0, 0.3, 0.8), 140, 2.5, color=(1.0, 0.95, 0.88))
    box("vr_floor", (8, 8, 0.1), (0, 0, -0.05), M["clay2"])
    box("vr_wall", (8, 0.2, 3.2), (0, 2.6, 1.6), mat("vr_wall", (0.6, 0.66, 0.68), 0.7))
    box("vr_tv", (2.15, 0.08, 1.25), (0, 2.46, 1.6), M["dark"], bev=0.02)
    screen_image("vr_screen", img, (2.0, 1.125), (0, 2.41, 1.6))
    box("vr_sofa", (2.4, 0.9, 0.45), (0, -0.4, 0.23), M["grey"], bev=0.08)
    box("vr_back", (2.4, 0.25, 0.6), (0, -0.8, 0.6), M["grey"], bev=0.08)
    P("docA", -0.45, -0.25, 0, "watch", outfit)
    P("docB", 0.5, -0.1, -8, "talk", "surgeon")
    area("vr_screenlight", (0, 2.3, 1.6), (0, -1, 1.2), 120, 2.0, color=(0.95, 0.9, 0.9), shape="RECTANGLE", size_y=1.1)
    area("vr_rim", (-3, -3, 3), (0, 0, 1), 60, 3)


def ferrari_room(img):
    """Engineering room in red: engineers at a desk studying hospital footage; a red car on display behind."""
    M = palette()
    world(0.35, (0.92, 0.92, 0.94))
    box("fr_floor", (14, 14, 0.1), (0, 0, -0.05), M["clay"])
    box("fr_wall", (14, 0.2, 4), (0, 3.2, 2), M["clay"])
    box("fr_tv", (2.6, 0.08, 1.5), (0, 3.05, 1.9), M["dark"], bev=0.02)
    screen_image("fr_screen", img, (2.45, 1.38), (0, 3.0, 1.9))
    box("fr_desk", (3.2, 0.9, 0.06), (0, 1.3, 0.75), M["white"], bev=0.02)
    for sx in (1, -1):
        box("fr_desk_leg", (0.06, 0.8, 0.72), (sx * 1.5, 1.3, 0.37), M["grey"])
    for i, x in enumerate((-0.9, 0, 0.9)):
        m = monitor(f"fr_mon{i}", 0.5, 0.32, wave=False)
        m.location = (x, 1.55, 1.0)
    P("eng1", -0.8, 0.5, 0, "watch", "engineer")
    P("eng2", 0.6, 0.45, 10, "talk", "engineer")
    P("eng3", 0.05, 0.1, -5, dict(armR=(80, 5, 30), head=(0, 5)), "engineer")
    c = f1car("show_car")
    c.location = (-4.6, -1.5, 0)
    c.rotation_euler = (0, 0, math.radians(-35))
    area("fr_key", (3, -4, 5), (0, 1, 1), 1500, 6)
    area("fr_fill", (-4, -3, 3), (0, 1, 1), 300, 5)


def chart_set(before=5.42, after=3.15, labels=("BEFORE", "AFTER")):
    """Two clay bars on a white stage: before (grey) and after (red)."""
    M = palette()
    world(0.6, (0.94, 0.94, 0.95))
    cyclorama(loc=(0, -22, 0), rot=0.0)
    k = 0.32
    import lib
    if lib.STYLE.get("voxel"):  # one block per error: 5.42 -> five blocks and a 0.42 sliver
        for x, val, m in ((-0.7, before, M["grey"]), (0.7, after, M["red"])):
            n, frac = int(val), val - int(val)
            for i in range(n):
                box(f"blk{x}_{i}", (0.9, 0.9, k * 0.96), (x, 0, k * (i + 0.5)), m)
            if frac > 0.02:
                box(f"blk{x}_f", (0.9, 0.9, k * frac * 0.96), (x, 0, k * (n + frac / 2)), m)
    else:
        box("bar_before", (0.9, 0.9, before * k), (-0.7, 0, before * k / 2), M["clay2"], bev=0.04)
        box("bar_after", (0.9, 0.9, after * k), (0.7, 0, after * k / 2), M["red"], bev=0.04)
    area("ch_key", (3, -5, 6), (0, 0, 0.8), 1500, 6)
    area("ch_fill", (-4, -3, 2), (0, 0, 0.8), 300, 5)
