"""Sets, each built around its own origin: pit lane, operating theatre, corridor, ICU bay, hospital exterior,
viewing room, Ferrari engineering room, chart stage. A shot builds exactly one set (plus its cast)."""
import math
import bpy
from mathutils import Vector
from lib import (V, box, cyl, sphere, torus, tube, mesh_obj, palette, area, world, cyclorama, mat, group, link, sun)
from people import person
from props import (f1car, wheel, wheel_gun, lollipop, jack, cot, monitor, iv_pole, vent, op_table,
                   surgical_lamp, drapes, clipboard)

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
)


def P(name, x, y, rot, pose, outfit, **kw):
    pose_ = POSE[pose] if isinstance(pose, str) else pose
    return person(name, (x, y, 0), rot, pose_, outfit, **kw)


# ---------------------------------------------------------------- pit lane
def pit_set(car_y=0.0, crew=True, wheels_off=False, lit=True, car=True, crew_skip=()):
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
    if crew:
        pit_crew(crew_skip)
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


def pit_crew(skip=()):
    """About twenty: three per wheel, two jacks, two stabilisers, two wing men, the lollipop man."""
    cast = []
    for (y, side, tag) in [(1.8, 1, "FL"), (1.8, -1, "FR"), (-1.78, 1, "RL"), (-1.78, -1, "RR")]:
        if tag in skip:
            continue
        rot = -90 if side == 1 else 90
        cast.append(P(f"gun{tag}", side * 1.45, y, rot, "gun", "crew"))
        g = wheel_gun(f"wg{tag}")
        g.location = (side * 1.15, y, 0.38)
        g.rotation_euler = (0, 0, math.radians(rot))
        cast.append(P(f"off{tag}", side * 1.75, y + 0.75, rot + side * 25, "tyre_off", "crew"))
        cast.append(P(f"on{tag}", side * 1.8, y - 0.75, rot - side * 25, "tyre_hold", "crew"))
        t = wheel(f"newtyre{tag}", 0.36, 0.34, 1)
        t.location = (side * 1.45, y - 0.85, 0.62)
        t.rotation_euler = (0, 0, 0)
    if "jacks" not in skip:
        cast.append(P("fjack", 0, 4.0, 180, "jack", "crew"))
        j = jack("fjack_eq")
        j.location = (0, 2.95, 0)
        j.rotation_euler = (0, 0, math.pi)
        cast.append(P("rjack", 0, -3.9, 0, "jack", "crew"))
        j2 = jack("rjack_eq")
        j2.location = (0, -2.85, 0)
    for s in (1, -1):
        if "stab" not in skip:
            cast.append(P(f"stab{s}", s * 1.3, 0.1, -90 * s, "brace", "crew"))
        if "wing" not in skip:
            cast.append(P(f"wing{s}", s * 1.2, 2.95, 180 + s * 30, "brace", "crew"))
    if "lolli" not in skip:
        cast.append(P("lolliman", -0.9, 4.6, 180, "lolli", "crew"))
        l = lollipop("lolli_eq")
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
    area("th_key", (0, 0, 3.1), (0, 0, 0), 900, 2.5)
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
        P("leader", 0.0, -0.75, 0, "lead", "surgeon")
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


# ---------------------------------------------------------------- hospital exterior (London)
def exterior_set():
    M = palette()
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
    box("tower", (4, 4, 40), (-45, 90, 20), tw)
    box("clockblk", (5, 5, 6), (-45, 90, 42), tw)
    cyl("spire", 3.2, 10, (-45, 90, 50), tw, seg=4, r2=0.2, rot=(0, 0, math.pi / 4))
    for s in (1, -1):
        cyl("clockface", 1.6, 0.1, (-45, 90 - 2.55, 42), M["clay"], rot=(math.pi / 2, 0, 0))
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.0
    sun.angle = math.radians(8)
    so = link(bpy.data.objects.new("sun", sun))
    so.rotation_euler = (math.radians(55), 0, math.radians(-35))
    sc = bpy.context.scene
    # haze so the tower fades into the sky
    w = sc.world
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
    """Dim staff room: two doctors watching a pit stop on a wall screen."""
    M = palette()
    world(0.05, (0.8, 0.85, 0.9))
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
    box("bar_before", (0.9, 0.9, before * k), (-0.7, 0, before * k / 2), M["clay2"], bev=0.04)
    box("bar_after", (0.9, 0.9, after * k), (0.7, 0, after * k / 2), M["red"], bev=0.04)
    area("ch_key", (3, -5, 6), (0, 0, 0.8), 1500, 6)
    area("ch_fill", (-4, -3, 2), (0, 0, 0.8), 300, 5)
