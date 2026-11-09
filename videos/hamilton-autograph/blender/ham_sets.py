"""Sets and props for "Phone me in nine years" (Hamilton autograph short), in the house voxel style.

Sets: the 1995 awards dinner (dark ballroom), the family kitchen at night, the garden shed with the kart, the dad's
jobs (office, street at dusk), a 1990s UK kart track (paddock, grid, finish line, podium), the trophy shelf, the team
boss's office (1998), Brazil 2008 in the rain (track, pit wall, garage).
Props: the red autograph book (the film's accent), the go-kart (battered / like new), trophies, chequered flag,
contract, bills, coin jar. F1 cars come from the library (library/cars/f1_2026); 2008-inspired liveries are added
at run time here, so the library files are never changed.
"""
import math
import os
import random
import sys
import bpy
from mathutils import Vector, Matrix
from lib import V, box, cyl, palette, mat, area, world, group, sun, link, look_at
import dress
from dress import pixmat, _img, _noisy, asphalt, kerb, tree, sky_world, clouds, concrete, data_screen, drawers
from sets import POSE
import halo_sets as H

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, "assets", "tex")
LIB_CARS = os.path.join(os.path.dirname(os.path.dirname(ROOT)), "library", "cars", "f1_2026")

KID = 0.68    # the boy at 10 (block scale)
TEEN = 0.86   # at 13
BOSS = 1.1    # the team boss, towering

POSE.update(
    offer=dict(armL=(120, -8, 20), armR=(120, -8, 20), head=(0, -12), face="open"),          # book held up high
    look_down=dict(head=(0, 34), armL=(8, 8, 12), armR=(8, 8, 12), face="neutral"),
    write=dict(head=(0, 26), armL=(55, -10, 70), armR=(50, -14, 80), lean=6),
    tiptoe=dict(head=(0, -24), armL=(30, 10, 40), armR=(30, 10, 40), face="open"),
    slump=dict(crouch=0.42, lean=28, legL=(88, 6, 92), legR=(88, 6, 92), armL=(60, 10, 120), armR=(40, 10, 60),
               head=(0, 26), face="worried"),
    doorway=dict(head=(0, 6), armL=(8, 8, 10), armR=(25, -6, 60), face="worried"),
    sand=dict(crouch=0.5, lean=40, legL=(70, 12, 100), legR=(30, 12, 80), armL=(70, 8, 30), armR=(60, 8, 40), head=(0, 30)),
    spray=dict(lean=16, armR=(80, 0, 20), armL=(30, 10, 60), head=(0, 22)),
    desk=dict(crouch=0.45, lean=12, legL=(90, 6, 90), legR=(90, 6, 90), armL=(62, 8, 60), armR=(62, 8, 60), head=(0, 16)),
    hammer=dict(lean=4, armR=(150, 10, 50), armL=(70, -10, 40), head=(0, -10)),
    stand_by=dict(head=(0, 4), armL=(6, 8, 10), armR=(6, 8, 10)),
    helmet_hold=dict(armL=(20, 12, 70), armR=(4, 8, 12), head=(0, 4)),
    turned=dict(head=(18, 4), armL=(10, 10, 60), armR=(10, 10, 60)),
    wipe=dict(head=(-30, 18), armL=(6, 8, 10), armR=(120, -30, 140), face="worried"),
    brave=dict(head=(0, -6), armL=(6, 6, 8), armR=(6, 6, 8), face="neutral"),
    kneel=dict(crouch=0.42, lean=6, legL=(92, 4, 92), legR=(-10, 4, 100), armL=(60, -10, 40), armR=(10, 8, 20), head=(0, -8)),
    point_track=dict(crouch=0.42, lean=6, legL=(92, 4, 92), legR=(-10, 4, 100), armL=(60, -10, 40), armR=(90, 30, 5), head=(30, -4)),
    nod=dict(head=(0, 14), armL=(6, 8, 10), armR=(6, 8, 10)),
    drive=dict(crouch=0.62, lean=-14, legL=(78, 4, 18), legR=(78, 4, 18), armL=(58, 0, 30), armR=(58, 0, 30), head=(0, -6)),
    trophy_up=dict(armL=(165, 4, 10), armR=(165, 4, 10), head=(0, -14), face="smile"),
    cheer=dict(armL=(160, 30, 10), armR=(160, 30, 10), head=(0, -12), face="open"),
    flag_wave=dict(armR=(120, 20, 20), armL=(120, -10, 30), head=(0, -4)),
    sign_desk=dict(lean=24, armR=(70, -6, 50), armL=(58, 4, 70), head=(0, 34)),
    shake=dict(armR=(55, -8, 30), armL=(6, 8, 10), head=(0, -4), face="smile"),
    proud=dict(armL=(6, 8, 10), armR=(40, -30, 90), head=(0, -4), face="smile"),
    pitwall=dict(crouch=0.38, lean=10, legL=(85, 6, 85), legR=(85, 6, 85), armL=(55, 6, 70), armR=(55, 6, 70), head=(0, 6)),
    fist=dict(crouch=0.38, lean=4, legL=(85, 6, 85), legR=(85, 6, 85), armL=(55, 6, 70), armR=(100, -18, 120), head=(0, -8), face="smile"),
    helmet_off=dict(armL=(160, 4, 60), armR=(160, 4, 60), head=(0, -6)),
)


# ---------------------------------------------------------------- generic helpers
def img_mat(name, path, emit=0.0, rough=0.7):
    full = "img_" + name
    if full in bpy.data.materials:
        return bpy.data.materials[full]
    m = bpy.data.materials.new(full)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = rough
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = bpy.data.images.load(path, check_existing=True)
    tx.interpolation = "Linear"
    nt.links.new(tx.outputs["Color"], b.inputs["Base Color"])
    if emit:
        nt.links.new(tx.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = emit
    return m


def img_plane(name, tex, size, loc, rot=(0, 0, 0), emit=0.0, rough=0.7):
    """A flat picture (4 vertices: the voxeliser leaves it alone). Faces +Z before rotation; UV upright along +Y."""
    w, h = size
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new()
    for i, c in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[i].uv = c
    me.materials.append(img_mat(tex, os.path.join(TEX, tex + ".png"), emit, rough))
    ob = link(bpy.data.objects.new(name, me))
    ob.location = loc
    ob.rotation_euler = tuple(math.radians(a) for a in rot)
    return ob


def keep_smooth(root):
    """Library assets are voxels already: tell the voxeliser to leave them alone."""
    for o in [root] + list(root.children_recursive):
        o["smooth"] = True


def lamp_point(name, loc, energy=60, color=(1, 0.8, 0.55), radius=0.05):
    d = bpy.data.lights.new(name, "POINT")
    d.energy, d.color, d.shadow_soft_size = energy, color, radius
    ob = link(bpy.data.objects.new(name, d))
    ob.location = loc
    return ob


def spot(name, loc, target, energy=800, size_deg=30, blend=0.4, color=(1, 0.92, 0.8), radius=0.2):
    d = bpy.data.lights.new(name, "SPOT")
    d.energy, d.spot_size, d.spot_blend, d.color, d.shadow_soft_size = energy, math.radians(size_deg), blend, color, radius
    ob = link(bpy.data.objects.new(name, d))
    ob.location = loc
    look_at(ob, target)
    return ob


def glow(name, color, strength=6):
    return mat(name, color, 0.4, emit=color, emit_strength=strength)


def seated(name, x, y, rot, pose, outfit, seat_z, seat_objs=(), hands=None, scale=1.0, knee_fwd=0.4):
    """Sit a block person on a seat whose top is at seat_z: pelvis just above it, shins down to feet planted on
    the floor in front; the seat counts as contact, not a clip."""
    from halo_sets import person_at
    from sets import register_hold
    p = dict(POSE[pose]) if isinstance(pose, str) else dict(pose)
    p["crouch"] = 0.855 - (seat_z + 0.09 * scale) / scale
    f = V((-math.sin(math.radians(rot)), math.cos(math.radians(rot)), 0))
    s = V((math.cos(math.radians(rot)), math.sin(math.radians(rot)), 0))
    base = V((x, y, 0)) + f * knee_fwd * scale
    feet = {"L": tuple(base + s * 0.1 * scale + V((0, 0, 0.09 * scale))), "R": tuple(base - s * 0.1 * scale + V((0, 0, 0.09 * scale)))}
    pr = person_at(name, x, y, rot, p, outfit, scale=scale, hands=hands, feet=feet)
    for o in seat_objs:
        register_hold(o, name, "seat")
        register_hold(o + "_vox", name, "seat")  # round parts are rebuilt as voxels under this name
    return pr


def allow(person, *objs):
    """Contact that is meant to be there (a driver inside the car's body, forearms on a table)."""
    from sets import register_hold
    for o in objs:
        register_hold(o, person, "contact")
        register_hold(o + "_vox", person, "contact")


# ---------------------------------------------------------------- library cars, 2008-inspired liveries
def _liveries():
    if LIB_CARS not in sys.path:
        sys.path.insert(0, LIB_CARS)
    import blueprint as bp
    if "chrome08" not in bp.LIVERIES:
        S = bp
        bp.LIVERIES["chrome08"] = dict(  # 2008-inspired: chrome silver body, red flashes, dark lower body and wings
            number="22", patterns=("lower", "nose_tip"), title="Chrome 2008-inspired",
            paint={S.SILVER: ("#C9CDD3", 0.9, 0.16), S.BLACK: ("#B9BDC4", 0.85, 0.2), S.TEAL: ("#D7141A", 0.15, 0.3),
                   S.WING: ("#1A1B1E", 0.2, 0.3), S.HALO: ("#C9CDD3", 0.9, 0.16), S.LOWER: ("#26272B", 0.3, 0.3),
                   S.WHITE: ("#F2F2F2", 0.0, 0.35), S.ACCENT2: ("#D7141A", 0.15, 0.3), S.STAR: ("#C9CDD3", 0.5, 0.3)},
            number_top=S.TEAL, number_side=S.TEAL,
            decals=dict(sidepod="ORVA", endplate="KYNEX", halo="ORVA"))
        bp.LIVERIES["blanco08"] = dict(  # 2008-inspired: white body, red sweeps, dark wings (the car he passes)
            number="12", patterns=("lower",), title="White-red 2008-inspired",
            paint={S.SILVER: ("#EDEDED", 0.1, 0.3), S.BLACK: ("#E9E9E9", 0.1, 0.3), S.TEAL: ("#C8102E", 0.1, 0.3),
                   S.WING: ("#1A1B1E", 0.2, 0.3), S.HALO: ("#C8102E", 0.1, 0.3), S.LOWER: ("#C8102E", 0.1, 0.3),
                   S.WHITE: ("#C8102E", 0.0, 0.35), S.ACCENT2: ("#C8102E", 0.1, 0.3), S.STAR: ("#EDEDED", 0.1, 0.3)},
            number_top=S.TEAL, number_side=S.TEAL,
            decals=dict(sidepod="TEKNA", endplate="VELTRO", halo="TEKNA"))
    return bp


def car(name, livery="chrome08", loc=(0, 0, 0), yaw=0.0, steer=0.0, compound="wet"):
    """A library F1 car (no driver). compound wet: blue-marked rain tyres for Brazil 2008."""
    _liveries()
    import car_blender as cb
    root = cb.load_car(name, livery=livery, compound=compound)
    root.location = loc
    root.rotation_euler = (0, 0, math.radians(yaw))
    root["steer"] = steer
    keep_smooth(root)
    return root


RECLINE = 52


def car_driver(name, root, outfit="driver08_h"):
    """A block driver (scale 1) seated in a library car: reclined, neck at blueprint.SEAT, hands on the grips."""
    from halo_sets import person_at
    import ik
    bp = _liveries()
    P_ = 0.045
    neck_local = V((0, 0, 19 * P_)) + Matrix.Rotation(math.radians(RECLINE), 3, "X") @ V((0, 0, 12 * P_))
    loc_c = V(bp.SEAT["neck"]) - neck_local
    bpy.context.view_layer.update()
    Mw = root.matrix_world
    loc = Mw @ loc_c
    yaw = math.degrees(Mw.to_euler().z)
    pose = dict(lean=-RECLINE, head=(0, RECLINE), legL=(97, -3, 0), legR=(97, -3, 0), armL=(60, 0, 40), armR=(60, 0, 40))
    gL, gR = Mw @ V(bp.SEAT["grips"][1]), Mw @ V(bp.SEAT["grips"][0])
    pr = person_at(name, loc.x, loc.y, yaw, pose, outfit, z=loc.z, hands={"L": tuple(gL), "R": tuple(gR)})
    allow(name, root.name)  # legs inside the chassis, hands on the wheel (fit_check.py proves nothing pokes out)
    pr["airborne"] = True  # feet on the pedals inside the car
    return pr


# ---------------------------------------------------------------- props
def book(name, opened=False, page="page_0", cover=None):
    """The autograph book: small, landscape, red cover. Its own frame: spine along Y at x = 0 when open (left and
    right leaves at -X / +X), text upright along +Y, pages face +Z. Closed: one block, cover on top."""
    M = palette()
    cover = cover or M["bookred"]
    gold = mat("bookgold", (0.85, 0.65, 0.2), 0.4)
    if not opened:
        p = [box(name + "_cover", (0.21, 0.16, 0.03), (0, 0, 0), cover),
             box(name + "_pages", (0.2, 0.154, 0.032), (0.004, 0, 0), M["white"]),
             box(name + "_band", (0.03, 0.162, 0.032), (-0.08, 0, 0), gold)]
        return group(name, p)
    p = [box(name + "_coverL", (0.215, 0.165, 0.012), (-0.1075, 0, -0.008), cover),
         box(name + "_coverR", (0.215, 0.165, 0.012), (0.1075, 0, -0.008), cover),
         box(name + "_blockL", (0.205, 0.155, 0.008), (-0.104, 0, 0.002), M["white"]),
         box(name + "_blockR", (0.205, 0.155, 0.008), (0.104, 0, 0.002), M["white"])]
    g = group(name, p)
    for nm, tex, x in (("_page", page, 0.104), ("_pageL", "page_0", -0.104)):
        pl = img_plane(name + nm, tex, (0.2, 0.15), (x, 0, 0.0065))
        pl.parent = g
    return g


def pen(name):
    M = palette()
    return group(name, [box(name + "_body", (0.014, 0.014, 0.14), (0, 0, 0), M["dark"]),
                        box(name + "_cap", (0.016, 0.016, 0.03), (0, 0, 0.06), M["chrome"])])


LIB_KART = os.path.join(os.path.dirname(os.path.dirname(ROOT)), "library", "cars", "kart")
KART_S = 0.92  # a cadet kart for a 10-year-old (about 1.65 m long): the library senior kart at 92 %


def kart(name, state="new", loc=(0, 0, 0), yaw=0.0, livery=None, plate=None, color=None):
    """The library go-kart (library/cars/kart), never modelled here. state "battered": the fifth-hand club kart as
    the family bought it; "new": the same kart after his dad fixed it up (same livery, clean, condition new). Other
    kids' karts take a team livery. Faces +Y, origin on the ground halfway along the wheelbase, cadet size."""
    if LIB_KART not in sys.path:
        sys.path.insert(0, LIB_KART)
    import kart_blender as kb
    livery = livery or "fifth_hand"
    cond = "battered" if state == "battered" else "new"
    root = kb.load_kart(name, livery=livery, condition=cond)
    root.location = loc
    root.rotation_euler = (0, 0, math.radians(yaw))
    root.scale = (KART_S, KART_S, KART_S)
    keep_smooth(root)
    root["kart"] = state
    return root


def kart_roll(root, dist):
    """Wheels roll with the distance travelled (world metres); the library rig reads root["distance"]."""
    root["distance"] = dist / root.scale.x
    for o in root.children_recursive:
        o.update_tag()


def kart_driver(name, k, outfit="boy_suit_h", scale=KID, pose="drive"):
    """A kid seated in kart k: hips on the seat (library kart_blueprint.HIP), back reclined, hands at 9 and 3 on the
    wheel (SEAT grips), feet on the pedals."""
    from halo_sets import person_at
    import ik
    import kart_blueprint as kbp
    bpy.context.view_layer.update()
    Mk = k.matrix_world
    s = k.scale.x
    yaw = math.degrees(Mk.to_euler().z)
    hip = Mk @ V((0, float(kbp.HIP[1]) + 0.02, 0))
    p = dict(POSE[pose], lean=-14, legL=(80, 10, 30), legR=(80, 10, 30))
    p["crouch"] = ik.LEG - (k.location.z + float(kbp.HIP[2]) * s) / scale
    gr0, gr1 = kbp.SEAT["grips"]
    wl, wr = Mk @ V(gr1), Mk @ V(gr0)
    fl, fr = Mk @ V((0.185, 0.40, 0.14)), Mk @ V((-0.185, 0.40, 0.14))
    pr = person_at(name, hip.x, hip.y, yaw, p, outfit, scale=scale, hands={"L": tuple(wl), "R": tuple(wr)},
                   feet={"L": tuple(fl), "R": tuple(fr)})
    allow(name, *[o.name for o in [k] + list(k.children_recursive)])  # sitting in it: seat, pedals, wheel
    pr["foot_free"] = "LR"  # feet on the pedals, not the ground
    return pr


def trophy(name, h=0.4, loc=(0, 0, 0), metal=None):
    M = palette()
    g = metal or M["gold"]
    p = [box(name + "_base", (h * 0.45, h * 0.45, h * 0.2), (0, 0, h * 0.1), M["dark"]),
         cyl(name + "_stem", h * 0.06, h * 0.3, (0, 0, h * 0.35), g, seg=12),
         cyl(name + "_cup", h * 0.22, h * 0.36, (0, 0, h * 0.68), g, seg=20, r2=h * 0.12),
         box(name + "_handleL", (h * 0.08, h * 0.04, h * 0.2), (h * 0.27, 0, h * 0.7), g),
         box(name + "_handleR", (h * 0.08, h * 0.04, h * 0.2), (-h * 0.27, 0, h * 0.7), g)]
    return group(name, p, loc=loc)


def chequered_flag(name, loc=(0, 0, 0), rot=(0, 0, 0), size=(0.7, 0.5)):
    M = palette()
    pole = box(name + "_pole", (0.025, 0.025, 0.9), (0, 0, 0), M["dark"])
    g = group(name, [pole], loc=loc, rot=tuple(math.radians(a) for a in rot))
    fl = img_plane(name + "_cloth", "chequer", size, (size[0] / 2 + 0.01, 0, 0.45 - size[1] / 2), (90, 0, 0))
    fl.parent = g
    return g


def table_round(name, x, y, r=0.85, seed=1, guests=()):
    """A round dinner table: cloth top with a short skirt (knees fit under it), a pedestal, six chairs, plates,
    glasses and a candle. guests: chair indices with a seated guest facing the table."""
    from halo_sets import person_at
    M = palette()
    cloth = mat("tablecloth", (0.9, 0.88, 0.84), 0.85)
    cyl(name + "_top", r, 0.05, (x, y, 0.745), cloth, seg=32)
    cyl(name + "_skirt", r, 0.12, (x, y, 0.66), cloth, seg=32, cap=False)
    cyl(name + "_ped", 0.08, 0.6, (x, y, 0.3), M["dark"], seg=12)
    candle = glow("candle", (1.0, 0.62, 0.25), 12)
    box(name + "_candle", (0.04, 0.04, 0.12), (x, y, 0.83), candle)
    lamp_point(name + "_cl", (x, y, 0.98), 6, (1, 0.6, 0.3), 0.03)
    chairc = mat("chaircover", (0.82, 0.8, 0.76), 0.85)
    for i in range(6):
        a = i / 6 * 2 * math.pi + seed
        box(f"{name}_glass{i}", (0.05, 0.05, 0.14), (x + 0.6 * r * math.cos(a), y + 0.6 * r * math.sin(a), 0.84), M["glass"])
        box(f"{name}_plate{i}", (0.2, 0.2, 0.012), (x + 0.5 * r * math.cos(a), y + 0.5 * r * math.sin(a), 0.776), M["white"])
        cx, cy = x + (r + 0.42) * math.cos(a), y + (r + 0.42) * math.sin(a)
        box(f"{name}_chair{i}", (0.42, 0.42, 0.05), (cx, cy, 0.44), chairc, rot=(0, 0, a + math.pi / 2))
        box(f"{name}_chairbase{i}", (0.3, 0.3, 0.42), (cx, cy, 0.21), chairc, rot=(0, 0, a + math.pi / 2))
        bx, by = x + (r + 0.66) * math.cos(a), y + (r + 0.66) * math.sin(a)
        box(f"{name}_chairback{i}", (0.42, 0.06, 0.6), (bx, by, 0.76), chairc, rot=(0, 0, a + math.pi / 2))
        if i in guests:  # seated on the chair, forearms resting on the table's edge, feet under the table
            gx, gy = x + (r + 0.32) * math.cos(a), y + (r + 0.32) * math.sin(a)  # on the front of the seat
            hand = lambda d: (x + (r - 0.06) * math.cos(a + d), y + (r - 0.06) * math.sin(a + d), 0.825)
            seated(f"{name}_g{i}", gx, gy, math.degrees(a) + 90, dict(POSE["sit"], head=(0, 4)), "guest", 0.465,
                   (f"{name}_chair{i}", f"{name}_chairbase{i}", f"{name}_chairback{i}", f"{name}_top", f"{name}_skirt"),
                   hands={"L": hand(0.17), "R": hand(-0.17)})


# ---------------------------------------------------------------- 1995 awards dinner
def awards_set():
    """A dark hotel ballroom: patterned carpet, round tables with candles, a stage with a glowing blue screen and
    coloured uplights, guests in black tie at the tables. The boy and the boss meet in the aisle at the origin
    (the stage is toward +Y)."""
    M = palette()
    world(0.02, (0.05, 0.05, 0.08))
    def carpet(x, y):
        if (x + y) % 8 == 0 or (x - y) % 8 == 0:
            return (0.42, 0.28, 0.08)
        return _noisy((0.22, 0.03, 0.05), 0.25, rnd)
    rnd = random.Random(3)
    box("aw_floor", (40, 40, 0.1), (0, 4, -0.05), pixmat("carpet", _img("carpet", 32, 32, carpet), 2.0, 0.95))
    wall = mat("aw_wall", (0.06, 0.05, 0.07), 0.8)
    box("aw_back", (40, 0.3, 9), (0, 16, 4.5), wall)
    for s in (1, -1):
        box(f"aw_side{s}", (0.3, 40, 9), (s * 14, 4, 4.5), wall)
    box("aw_ceiling", (40, 40, 0.2), (0, 4, 8), mat("aw_ceil", (0.04, 0.04, 0.05), 0.9))
    box("aw_stage", (12, 4, 0.8), (0, 13.5, 0.4), mat("stage", (0.08, 0.08, 0.1), 0.6))
    box("aw_screen", (8, 0.1, 3.6), (0, 15.7, 3.6), glow("aw_screenglow", (0.12, 0.3, 0.9), 2.2))
    box("aw_screenband", (8.05, 0.12, 0.25), (0, 15.68, 2.2), glow("aw_band", (0.85, 0.85, 0.95), 3.0))
    box("aw_lectern", (0.6, 0.5, 1.15), (3.5, 12.6, 1.38), mat("lectern", (0.15, 0.1, 0.07), 0.5))
    for i, x in enumerate((-12, -7, -2.5, 2.5, 7, 12)):  # coloured uplights washing the walls
        c = (0.35, 0.1, 0.9) if i % 2 else (0.1, 0.35, 1.0)
        box(f"aw_uplight{i}", (0.3, 0.3, 0.2), (x, 15.6, 0.1), glow(f"aw_up{i}", c, 8))
        spot(f"aw_wash{i}", (x, 14.8, 0.3), (x, 15.9, 6), 900, 40, 0.6, c, 0.1)
    for j, x in enumerate((-13.7, 13.7)):
        for i, y in enumerate(range(-6, 16, 4)):
            spot(f"aw_side{j}{i}", (x * 0.97, y, 0.3), (x, y, 5), 260, 50, 0.7, (0.25, 0.15, 0.8), 0.1)
    for i in range(14):  # chandelier glints overhead
        box(f"aw_chand{i}", (0.12, 0.12, 0.12), (rnd.uniform(-10, 10), rnd.uniform(-4, 14), 7.6), glow("chandelier", (1, 0.85, 0.6), 10))
    tables = [(-3.4, 2.0), (3.4, 2.4), (-6.5, 6.5), (0.6, 7.8), (6.4, 6.8), (-3.8, 9.6), (3.8, 9.9), (-9, 2.5), (9.5, 3.0),
              (-3.5, -3.5), (3.6, -3.2)]
    for i, (x, y) in enumerate(tables):
        table_round(f"aw_t{i}", x, y, seed=i + 1, guests=(0, 2, 4) if i < 7 else ())
    from halo_sets import person_at
    for i, (x, y, r, pz) in enumerate(((-1.4, 5.0, 30, "talk"), (-0.6, 5.5, 210, "watch"), (5.2, 9.0, 160, "talk"))):
        person_at(f"aw_stand{i}", x, y, r, pz, "guest")
    # key light on the meeting in the aisle, warm; a cool back light from the stage
    spot("aw_key", (2.6, -2.4, 4.4), (0, 0.1, 1.2), 2600, 34, 0.55, (1, 0.86, 0.68), 0.4)
    spot("aw_rim", (1.5, 4.5, 3.6), (0, 0, 1.4), 900, 32, 0.6, (0.45, 0.6, 1.0), 0.3)
    area("aw_fill", (3, -4, 1.5), (0, 0, 1.2), 60, 3, color=(0.7, 0.75, 1.0))


# ---------------------------------------------------------------- the family kitchen at night
def kitchen_set():
    """A small terraced-house kitchen at night: one warm pendant lamp over the table, a window with the dark street
    and an orange street lamp, units along the back, a doorway (hall light) on the left. Table at the origin."""
    M = palette()
    world(0.01, (0.03, 0.04, 0.08))
    def lino(x, y):
        return (0.42, 0.38, 0.3) if (x // 4 + y // 4) % 2 else (0.3, 0.27, 0.22)
    box("kt_floor", (8, 8, 0.1), (0, 0, -0.05), pixmat("lino", _img("lino", 16, 16, lino), 1.6, 0.7))
    paper_ = mat("wallpaper", (0.42, 0.36, 0.26), 0.85)
    box("kt_back", (8, 0.2, 3), (0, 2.6, 1.5), paper_)
    box("kt_left", (0.2, 8, 3), (-3.0, 0, 1.5), paper_)
    box("kt_right", (0.2, 8, 3), (3.0, 0, 1.5), paper_)
    box("kt_ceiling", (8, 8, 0.1), (0, 0, 2.6), mat("kt_ceil", (0.5, 0.48, 0.44), 0.9))
    # window in the back wall: night street, a street lamp's orange glow
    box("kt_windowframe", (1.5, 0.22, 1.2), (1.2, 2.58, 1.65), M["white"])
    box("kt_windowglass", (1.3, 0.24, 1.0), (1.2, 2.58, 1.65), glow("kt_night", (0.03, 0.05, 0.14), 1.0))
    box("kt_streetlamp", (0.12, 0.25, 0.12), (1.55, 2.6, 1.95), glow("kt_sodium", (1.0, 0.5, 0.12), 14))
    box("kt_mullion", (0.05, 0.25, 1.0), (1.2, 2.57, 1.65), M["white"])
    # units: base cupboards, worktop, wall cupboards, sink, kettle
    unit = mat("kt_unit", (0.55, 0.52, 0.42), 0.6)
    box("kt_base", (5.6, 0.6, 0.88), (0, 2.2, 0.44), unit)
    box("kt_worktop", (5.7, 0.65, 0.05), (0, 2.18, 0.9), mat("worktop", (0.3, 0.27, 0.22), 0.5))
    for i, x in enumerate((-2.2, -1.2, 2.4)):
        box(f"kt_wall{i}", (0.9, 0.35, 0.7), (x, 2.3, 2.0), unit)
    box("kt_sink", (0.6, 0.45, 0.06), (1.2, 2.15, 0.9), M["steel"])
    box("kt_kettle", (0.18, 0.18, 0.24), (-1.6, 2.2, 1.04), M["white"])
    box("kt_fridge", (0.7, 0.65, 1.7), (-2.5, 2.1, 0.85), mat("fridge", (0.78, 0.76, 0.7), 0.5))
    # doorway on the left wall: the hall light behind
    box("kt_doorgap", (0.24, 0.95, 2.05), (-3.0, -1.2, 1.02), glow("kt_hall", (0.55, 0.6, 0.75), 0.18))
    area("kt_hall_l", (-3.6, -1.2, 1.4), (-2.0, -1.2, 1.0), 40, 0.8, color=(0.7, 0.75, 1.0))
    # the table: four legs, a chair each side, bills, the coin jar, a mug
    wood = mat("kt_table", (0.36, 0.24, 0.14), 0.6)
    box("kt_tabletop", (1.4, 0.9, 0.05), (0, 0, 0.75), wood)
    for sx in (1, -1):
        for sy in (1, -1):
            box(f"kt_leg{sx}{sy}", (0.06, 0.06, 0.73), (sx * 0.62, sy * 0.38, 0.365), wood)
    for i, (x, y, r) in enumerate(((0.05, -0.05, 8), (-0.2, 0.1, -14), (0.3, 0.12, 22))):
        img_plane(f"kt_bill{i}", f"bill_{i}", (0.21, 0.28), (x, y, 0.78 + i * 0.002), (0, 0, r))
    jar = cyl("kt_jar", 0.08, 0.2, (-0.45, -0.05, 0.875), M["glass"], seg=16)
    jar["smooth"] = True
    for i in range(3):
        cyl(f"kt_coin{i}", 0.025, 0.006, (-0.45 + 0.02 * i, -0.05, 0.783 + 0.006 * i), M["gold"], seg=10)
    box("kt_mug", (0.09, 0.09, 0.1), (0.52, -0.2, 0.825), mat("mug", (0.15, 0.3, 0.5), 0.5))
    for i, y in enumerate((-0.75, 0.75)):
        box(f"kt_chair{i}", (0.45, 0.45, 0.05), (0, y, 0.45), wood)
        for sx in (1, -1):
            for sy in (1, -1):
                box(f"kt_chairleg{i}{sx}{sy}", (0.04, 0.04, 0.45), (sx * 0.19, y + sy * 0.19, 0.225), wood)
        box(f"kt_chairback{i}", (0.45, 0.05, 0.5), (0, y + (0.22 if y > 0 else -0.22), 0.72), wood)
    # the pendant lamp: one warm pool on the table, the rest dark
    box("kt_flex", (0.015, 0.015, 0.9), (0, 0, 2.15), M["dark"])
    cyl("kt_shade", 0.18, 0.14, (0, 0, 1.65), mat("shade", (0.75, 0.55, 0.3), 0.6), seg=16, r2=0.06)
    box("kt_bulb", (0.07, 0.07, 0.07), (0, 0, 1.56), glow("bulb", (1.0, 0.8, 0.5), 25))
    spot("kt_pool", (0, 0, 1.56), (0, 0, 0), 320, 100, 0.8, (1, 0.72, 0.42), 0.08)
    area("kt_face", (0.6, 1.2, 1.3), (0, -0.7, 1.1), 25, 0.8, color=(1, 0.75, 0.5))
    lamp_point("kt_bounce", (0, 0, 1.3), 18, (1, 0.7, 0.4), 0.3)
    area("kt_window_l", (1.2, 3.2, 1.7), (0, 0, 1), 30, 1.2, color=(1.0, 0.55, 0.2))
    area("kt_moon", (-1, -3, 2.2), (0, 0, 1), 12, 3, color=(0.4, 0.5, 1.0))


# ---------------------------------------------------------------- the shed
SHED_KART = (0.0, 0.2, 0.0)
KART_STAND = 0.45   # top of the kart stand


def shed_set(kart_state="battered", book_on_wall=True, worker=None):
    """A garden shed at night: plank walls, one bare bulb, a workbench with a vice, a pegboard of tools, paint tins,
    the kart on two blocks in the middle (nose toward +X). The red book pinned on the back wall, open at the page."""
    M = palette()
    world(0.01, (0.02, 0.03, 0.06))
    rnd = random.Random(4)
    planks = pixmat("shedplank", _img("shedplank", 16, 16, lambda x, y: _noisy((0.32, 0.21, 0.12) if x % 4 else (0.18, 0.11, 0.06), 0.25, rnd)), 1.2, 0.85)
    box("sh_floor", (5, 4, 0.1), (0, 0, -0.05), concrete(0.35))
    box("sh_back", (5, 0.12, 2.6), (0, 1.9, 1.3), planks)
    box("sh_left", (0.12, 4, 2.6), (-2.4, 0, 1.3), planks)
    box("sh_right", (0.12, 4, 2.6), (2.4, 0, 1.3), planks)
    box("sh_roof", (5, 4, 0.1), (0, 0, 2.6), planks)
    box("sh_window", (0.9, 0.14, 0.6), (1.4, 1.9, 1.7), glow("sh_night", (0.04, 0.06, 0.16), 0.8))
    wood = mat("bench", (0.42, 0.3, 0.18), 0.7)
    box("sh_bench", (2.0, 0.6, 0.06), (-1.2, 1.55, 0.88), wood)
    for x in (-2.1, -0.3):
        box(f"sh_benchleg{x}", (0.08, 0.5, 0.85), (x, 1.55, 0.43), wood)
    box("sh_vice", (0.18, 0.2, 0.16), (-0.45, 1.4, 0.99), M["grey"])
    box("sh_pegboard", (1.8, 0.04, 0.9), (-1.2, 1.82, 1.6), mat("pegboard", (0.55, 0.45, 0.3), 0.8))
    for i in range(8):  # tools hanging on the pegboard
        x = -1.95 + i * 0.22
        box(f"sh_tool{i}", (0.05, 0.03, rnd.uniform(0.2, 0.42)), (x, 1.79, 1.6 + rnd.uniform(-0.1, 0.15)),
            M["grey"] if i % 2 else M["redm"])
    for i, (x, c) in enumerate(((-1.8, M["kartblue"]), (-1.6, M["white"]), (-1.35, M["redm"]))):
        cyl(f"sh_tin{i}", 0.08, 0.16, (x, 1.55, 0.99), c, seg=12)
    box("sh_shelf", (1.0, 0.3, 0.04), (1.6, 1.75, 1.2), wood)
    for i in range(3):
        cyl(f"sh_spare{i}", 0.13, 0.12, (1.25 + i * 0.32, 1.7, 1.36), M["rubber"], seg=16, rot=(math.radians(90), 0, 0))
    # the kart up on a kart stand in the middle, nose toward +X (a steel frame under the chassis, wheels hanging)
    stand = mat("kart_stand", (0.18, 0.2, 0.22), 0.5, metal=0.6)
    for sx in (-0.35, 0.35):
        box(f"sh_stand_beam{sx}", (0.06, 0.62, 0.05), (SHED_KART[0] + sx, SHED_KART[1], KART_STAND - 0.005), stand)
        for sy in (-0.28, 0.28):
            box(f"sh_stand_leg{sx}{sy}", (0.04, 0.04, KART_STAND - 0.03), (SHED_KART[0] + sx, SHED_KART[1] + sy, (KART_STAND - 0.03) / 2), stand)
    box("sh_stand_foot", (0.9, 0.05, 0.04), (SHED_KART[0], SHED_KART[1], 0.02), stand)
    k = kart("sh_kart", kart_state, (SHED_KART[0], SHED_KART[1], KART_STAND - 0.06), -90)
    if book_on_wall:
        b = book("sh_book", opened=True, page="page_6")
        b.location = (0.75, 1.83, 1.45)
        b.rotation_euler = (math.radians(90), 0, 0)
        box("sh_pin", (0.012, 0.03, 0.012), (0.75, 1.82, 1.53), M["red"])
    # the bare bulb: hard warm light, deep shadows
    box("sh_flex", (0.012, 0.012, 0.5), (0.2, 0.2, 2.35), M["dark"])
    box("sh_bulb", (0.07, 0.07, 0.09), (0.2, 0.2, 2.06), glow("bulb", (1.0, 0.8, 0.5), 25))
    lamp_point("sh_bulb_l", (0.2, 0.2, 2.0), 140, (1, 0.74, 0.45), 0.04)
    box("sh_worklamp", (0.14, 0.18, 0.12), (-0.9, 1.45, 1.05), M["grey"])  # clamp lamp on the bench, aimed at the kart
    spot("sh_worklamp_l", (-0.9, 1.35, 1.05), (0.0, -0.3, 0.35), 120, 45, 0.5, (1, 0.85, 0.6), 0.05)
    area("sh_moon", (1.4, 2.5, 1.7), (0, 0, 0.5), 10, 1.0, color=(0.4, 0.5, 1.0))
    return k


# ---------------------------------------------------------------- the dad's jobs
def office_job_set():
    """Day job: an office desk with a 1990s computer, a wall clock at 9:00. Grey daylight from the window."""
    M = palette()
    world(0.25, (0.7, 0.75, 0.82))
    box("of_floor", (8, 8, 0.1), (0, 0, -0.05), mat("office_carpet", (0.2, 0.22, 0.26), 0.95))
    wall = mat("of_wall", (0.62, 0.62, 0.58), 0.9)
    box("of_back", (8, 0.2, 3), (0, 1.6, 1.5), wall)
    box("of_window", (2.0, 0.22, 1.3), (-1.8, 1.58, 1.6), glow("of_sky", (0.65, 0.72, 0.85), 1.4))
    img_plane("of_clock", "clock_0900", (0.42, 0.42), (1.2, 1.48, 2.0), (90, 0, 0))
    desk = mat("of_desk", (0.55, 0.5, 0.42), 0.6)
    box("of_desktop", (1.6, 0.8, 0.05), (0, 0.5, 0.74), desk)
    for sx in (1, -1):
        box(f"of_ped{sx}", (0.4, 0.7, 0.72), (sx * 0.58, 0.5, 0.36), desk)
    box("of_crt", (0.42, 0.42, 0.38), (0, 0.65, 0.96), mat("crt", (0.78, 0.76, 0.68), 0.6))
    box("of_crtscreen", (0.32, 0.02, 0.26), (0, 0.435, 0.98), glow("crt_glow", (0.2, 0.6, 0.9), 2.5))
    box("of_keyboard", (0.45, 0.16, 0.03), (0, 0.3, 0.78), mat("crt", (0.78, 0.76, 0.68), 0.6))
    box("of_papers", (0.3, 0.22, 0.06), (0.55, 0.5, 0.8), M["white"])
    box("of_chair", (0.5, 0.5, 0.08), (0, -0.25, 0.46), M["dark"])
    box("of_chairback", (0.5, 0.08, 0.6), (0, -0.52, 0.82), M["dark"])
    area("of_window_l", (-1.8, 2.6, 1.8), (0, 0, 1), 400, 2.5, color=(0.8, 0.88, 1.0))
    area("of_fill", (2, -3, 2.5), (0, 0, 1), 200, 3)


POST = (0.75, 0.6)   # the board's post (its top is what the sledgehammer hits)
POST_TOP = 0.893   # level with the hammer face at the bottom of his swing (see ham_anim.S07b)


def street_job_set():
    """Evening job (sources: he put up estate agents' boards): a front garden outside a row of brick houses at dusk.
    A FOR SALE board on its post, the dad driving the post into the lawn with a mallet. The street clock reads 18:00."""
    M = palette()
    sky_world((0.95, 0.55, 0.32), (0.2, 0.18, 0.42), 0.8)
    box("st_pave", (20, 3, 0.1), (0, -2.0, -0.05), concrete(0.5))
    box("st_lawn", (20, 3.4, 0.1), (0, 1.2, -0.04), H.grass())
    box("st_road", (20, 6, 0.1), (0, -6, -0.07), asphalt())
    box("st_kerb", (20, 0.2, 0.15), (0, -3.5, 0.05), concrete(0.65))
    rnd = random.Random(5)
    brick = pixmat("brick", _img("brick", 16, 16, lambda x, y: (0.32, 0.3, 0.28) if (y % 4 == 0 or (x + (y // 4) * 4) % 8 == 0) else _noisy((0.45, 0.18, 0.1), 0.2, rnd)), 1.0, 0.9)
    box("st_houses", (20, 4, 6), (0, 5.0, 3), brick)
    for i, x in enumerate(range(-8, 9, 3)):
        box(f"st_win{i}", (1.0, 0.1, 1.1), (x, 2.98, 1.7), glow("st_winglow", (1.0, 0.75, 0.4), 2.5 if i % 2 else 0.2))
        box(f"st_win_up{i}", (1.0, 0.1, 1.1), (x, 2.98, 4.2), glow("st_winglow2", (1.0, 0.75, 0.4), 0.2 if i % 2 else 2.0))
        box(f"st_door{i}", (0.9, 0.1, 2.0), (x + 1.3, 2.98, 1.0), mat("door", (0.1, 0.12, 0.25), 0.6))
    for x in (-4.5, 4.5):  # low front-garden walls
        box(f"st_wall{x}", (3.0, 0.2, 0.5), (x, -0.5, 0.25), brick)
    img_plane("st_clock", "clock_1800", (0.5, 0.5), (-0.7, 2.9, 2.55), (90, 0, 0))
    # the board: a post in the lawn, the FOR SALE board on its right, facing the street
    box("st_post", (0.09, 0.09, POST_TOP + 0.3), (POST[0], POST[1], (POST_TOP - 0.3) / 2), mat("post", (0.85, 0.85, 0.82), 0.6))
    box("st_boardback", (0.84, 0.03, 0.56), (POST[0] - 0.47, POST[1] - 0.01, POST_TOP - 0.36), M["white"])
    img_plane("st_board", "forsale", (0.8, 0.52), (POST[0] - 0.47, POST[1] - 0.03, POST_TOP - 0.36), (90, 0, 0))
    box("st_toolbox", (0.5, 0.25, 0.25), (-0.9, 0.2, 0.125), M["redm"])
    box("st_streetlamp", (0.12, 0.12, 5), (3.5, -2.9, 2.5), M["grey"])
    box("st_lamphead", (0.5, 0.25, 0.15), (3.3, -2.9, 5.0), glow("sodium", (1.0, 0.5, 0.12), 12))
    lamp_point("st_lamp_l", (3.3, -2.9, 4.8), 500, (1.0, 0.55, 0.2), 0.2)
    sun("st_sun", (80, 0, 120), 1.6, 3, (1.0, 0.55, 0.3))
    area("st_fill", (0.6, -3.0, 2.2), (0.6, 0.6, 1.1), 120, 2.0, color=(1.0, 0.7, 0.5))


MALLET_L = 0.82   # grip end to the middle of the head
HAMMER_L = 0.28   # hand centre to the middle of the claw hammer's head
HAMMER_FACE = 0.065  # handle line to the striking face


def mallet(name):
    """A post sledgehammer: a long wooden handle along local +Z from the grip end (origin), a steel head across it."""
    wood = mat("mallet_wood", (0.5, 0.33, 0.18), 0.7)
    return group(name, [box(name + "_handle", (0.036, 0.036, 0.8), (0, 0, 0.4), wood),
                        box(name + "_head", (0.12, 0.24, 0.12), (0, 0, MALLET_L), mat("mallet_head", (0.22, 0.23, 0.25), 0.4, metal=0.7))])


def hammer(name):
    """A claw hammer in its own frame: origin at the hand's centre, the handle along +X through the fist, the
    head across it at HAMMER_L with the striking face toward +Z (the claw toward -Z)."""
    wood = mat("hammer_wood", (0.55, 0.36, 0.18), 0.7)
    steel = mat("hammer_steel", (0.32, 0.33, 0.36), 0.35, metal=0.8)
    return group(name, [box(name + "_handle", (0.36, 0.03, 0.03), (0.12, 0, 0), wood),
                        box(name + "_head", (0.045, 0.035, 0.14), (HAMMER_L, 0, -0.005), steel)])


def spanner(name):
    """A combination spanner: origin on the nut, the shaft along +X to the hand."""
    steel = mat("spanner_steel", (0.62, 0.64, 0.68), 0.3, metal=0.9)
    return group(name, [box(name + "_ring", (0.05, 0.02, 0.05), (0, 0, 0), steel),
                        box(name + "_shaft", (0.2, 0.012, 0.022), (0.11, 0, 0), steel)])


def dish_job_set():
    """Night job (sources: he washed dishes): a restaurant kitchen after closing. A steel sink unit under strip
    lights, a stack of dirty plates on the left, a rack of clean ones on the right, white tiles, a clock at 23:00."""
    M = palette()
    world(0.02, (0.03, 0.04, 0.06))
    box("dj_floor", (8, 8, 0.1), (0, 0, -0.05), pixmat("redtile", _img("redtile", 16, 16, lambda x, y: (0.35, 0.12, 0.08) if (x // 4 + y // 4) % 2 else (0.28, 0.1, 0.07)), 1.0, 0.6))
    tiles = pixmat("whitetile", _img("whitetile", 16, 16, lambda x, y: (0.55, 0.57, 0.56) if (x % 4 == 0 or y % 4 == 0) else (0.85, 0.87, 0.86)), 0.6, 0.35)
    box("dj_back", (8, 0.2, 3), (0, 1.0, 1.5), tiles)
    box("dj_left", (0.2, 8, 3), (-2.4, 0, 1.5), tiles)
    box("dj_ceiling", (8, 8, 0.1), (0, 0, 2.7), mat("dj_ceil", (0.5, 0.5, 0.5), 0.9))
    steel = M["steel"]
    pl = mat("plate", (0.92, 0.92, 0.88), 0.4)
    box("dj_unit", (2.8, 0.6, 0.86), (0, 0.6, 0.43), steel)
    box("dj_top", (2.9, 0.65, 0.04), (0, 0.6, 0.88), steel)
    box("dj_basin", (0.6, 0.45, 0.05), (0, 0.6, 0.91), glow("dj_water", (0.35, 0.45, 0.5), 0.15))
    for i, x in enumerate((-0.33, 0.33)):
        box(f"dj_basinrim{i}", (0.04, 0.5, 0.08), (x, 0.6, 0.92), steel)
    box("dj_tap", (0.04, 0.04, 0.35), (0, 0.88, 1.06), M["chrome"])
    box("dj_spout", (0.04, 0.2, 0.04), (0, 0.8, 1.22), M["chrome"])
    water = mat("tapwater", (0.75, 0.88, 1.0), 0.05, alpha=0.55)
    box("dj_stream", (0.022, 0.022, 0.2), (0, 0.71, 1.1), water)["smooth"] = True  # the running tap
    for i in range(10):  # suds in the basin
        box(f"dj_suds{i}", (0.05, 0.05, 0.02), (-0.24 + 0.05 * i, 0.5 + 0.06 * (i % 3), 0.94), mat("suds", (0.95, 0.96, 0.98), 0.8))
    for i in range(9):  # dirty plates, stacked
        cyl(f"dj_dirty{i}", 0.13, 0.018, (0.62 + 0.004 * (i % 3), 0.6, 0.91 + i * 0.02), pl, seg=16)
    for i in range(3):  # leftovers on the top plate
        box(f"dj_food{i}", (0.04, 0.03, 0.015), (0.59 + 0.03 * i, 0.58 + 0.02 * i, 1.09), mat("food", (0.55, 0.3, 0.1), 0.8))
    box("dj_rack", (0.5, 0.35, 0.03), (1.1, 0.6, 0.91), M["chrome"])
    for i in range(7):  # clean plates standing in the rack
        cyl(f"dj_clean{i}", 0.12, 0.016, (0.92 + i * 0.06, 0.6, 1.04), pl, seg=16, rot=(0, math.radians(90), 0))
    box("dj_shelf", (2.2, 0.3, 0.04), (0, 0.85, 1.75), steel)
    for i in range(6):
        cyl(f"dj_pot{i}", 0.11, 0.16, (-0.9 + 0.36 * i, 0.85, 1.85), steel, seg=14)
    img_plane("dj_clock", "clock_2300", (0.4, 0.4), (1.25, 0.88, 2.2), (90, 0, 0))
    box("dj_strip", (1.4, 0.12, 0.05), (0, 0.2, 2.62), glow("dj_strip", (0.85, 0.95, 1.0), 6))
    area("dj_strip_l", (0, 0.2, 2.55), (0, 0.3, 0), 140, 1.4, color=(0.85, 0.95, 1.0))
    area("dj_fill", (1.4, -1.6, 1.6), (0, 0.4, 1.1), 50, 1.4, color=(1.0, 0.85, 0.7))
    area("dj_door", (-2.2, -1.5, 1.4), (0, 0.5, 1.0), 15, 1.0, color=(1.0, 0.6, 0.3))


def sponge(name):
    return box(name, (0.08, 0.05, 0.035), (0, 0, 0), mat("sponge", (0.95, 0.8, 0.1), 0.9))


def plate(name):
    return cyl(name, 0.16, 0.018, (0, 0, 0), mat("plate", (0.92, 0.92, 0.88), 0.4), seg=20)

# ---------------------------------------------------------------- 1990s UK kart track
def kart_track_set(dark=False):
    """A small UK kart circuit on a grey day: the paddock (tarmac, vans, trailers, gazebos), the track along Y at
    x = 8..16 with red-and-white kerbs, tyre walls, a wire fence, a timing hut, trees beyond. Overcast light."""
    M = palette()
    sky_world((0.72, 0.74, 0.78), (0.48, 0.52, 0.6), 0.9)
    clouds((0, 30), n=10, z=30, spread=80)
    box("kt_paddock", (30, 40, 0.1), (-6, 0, -0.05), asphalt())
    box("kt_grass", (120, 120, 0.1), (0, 0, -0.08), H.grass())
    box("kt_track", (8, 80, 0.1), (12, 0, -0.04), asphalt())
    for x in (8.0, 16.0):
        box(f"kt_kerb{x}", (0.6, 80, 0.1), (x, 0, -0.02), kerb())
    box("kt_startline", (8, 0.3, 0.012), (12, 6, 0.012), M["white"])
    for i in range(16):  # chequered strip at the line
        box(f"kt_chq{i}", (0.5, 0.15, 0.013), (8.25 + i * 0.5, 6.0 + (0.075 if i % 2 else -0.075), 0.013), M["dark"])
    H.tyre_wall("kt_tyres", 17.2, -40, 40)
    H.catch_fence("kt_fence", 7.2, -30, 30, 1.6)
    # gantry with the start lights over the line
    for x in (7.6, 16.4):
        box(f"kt_gantrypost{x}", (0.2, 0.2, 3.6), (x, 6, 1.8), M["grey"])
    box("kt_gantry", (9.0, 0.3, 0.4), (12, 6, 3.6), M["grey"])
    for i in range(5):
        box(f"kt_light{i}", (0.25, 0.1, 0.25), (11.0 + i * 0.5, 5.84, 3.6), glow("startred", (1, 0.05, 0.03), 6 if dark else 0.3))
    box("kt_hut", (3, 2.5, 2.6), (5.2, 9.5, 1.3), mat("hut", (0.75, 0.75, 0.72), 0.8))
    box("kt_hutwin", (2.4, 0.1, 0.8), (5.2, 8.22, 1.8), M["glass"])
    # paddock: vans, trailers, gazebos
    rnd = random.Random(7)
    vcols = [(0.85, 0.85, 0.83), (0.6, 0.62, 0.66), (0.2, 0.3, 0.55), (0.75, 0.74, 0.7)]
    for i, (x, y, r) in enumerate(((-9, 6, 0), (-9, -2, 0), (-14, 12, 0), (-15, -10, 0), (-4, 15, 90), (-20, 2, 0))):
        vm = mat(f"van{i}", vcols[i % 4], 0.5)
        box(f"kt_van{i}", (2.0, 4.6, 2.2), (x, y, 1.25), vm, rot=(0, 0, math.radians(r)))
        box(f"kt_vanwin{i}", (1.9, 0.1, 0.7), (x, y + (2.31 if r == 0 else 0), 1.8), M["glass"], rot=(0, 0, math.radians(r)))
        for sx in (1, -1):
            for sy in (1, -1):
                cyl(f"kt_vanwheel{i}{sx}{sy}", 0.33, 0.25, (x + sx * 1.0, y + sy * 1.5, 0.33), M["rubber"], seg=16,
                    rot=(0, math.radians(90), 0))
    gz = [(0.85, 0.1, 0.1), (0.1, 0.3, 0.75), (0.95, 0.95, 0.95), (0.1, 0.5, 0.25)]
    for i, (x, y) in enumerate(((-5.5, 4), (-5.5, -3.5), (-12, 15), (-11, -7))):
        box(f"kt_gzroof{i}", (3, 3, 0.15), (x, y, 2.4), mat(f"gazebo{i}", gz[i], 0.7))
        for sx in (1, -1):
            for sy in (1, -1):
                box(f"kt_gzleg{i}{sx}{sy}", (0.05, 0.05, 2.4), (x + sx * 1.45, y + sy * 1.45, 1.2), M["grey"])
    for i in range(14):
        tree(f"kt_tree{i}", rnd.uniform(-40, 40), rnd.uniform(28, 45), rnd.choice([5, 6, 7]), rnd.choice([2, 2.5, 3]))
        tree(f"kt_treeR{i}", rnd.uniform(24, 34), rnd.uniform(-40, 40), rnd.choice([5, 6, 7]), rnd.choice([2, 2.5, 3]))
    sun("kt_sun", (40, 0, -30), 1.4, 20, (0.92, 0.94, 1.0))
    bpy.context.scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9


def podium_set():
    """Kart-club podium on the grass by the hut: three steps (1, 2, 3), a banner frame behind (no words)."""
    M = palette()
    kart_track_set()
    for x, h, n in ((-1.1, 0.5, "2"), (0, 0.8, "1"), (1.1, 0.35, "3")):
        box(f"pd_step{n}", (1.1, 0.9, h), (x - 2.0, 20, h / 2), M["white"])
        from props import digits
        digits(f"pd_num{n}", n, (x - 2.0, 19.54, h * 0.55), "x", "z", 0.06, M["dark"], 0.012)
    box("pd_banner", (4.0, 0.1, 1.2), (-2.0, 21.2, 2.4), mat("pd_banner", (0.1, 0.25, 0.6), 0.6))
    for x in (-4.0, 0.0):
        box(f"pd_bpost{x}", (0.1, 0.1, 3.0), (x, 21.2, 1.5), M["grey"])


# ---------------------------------------------------------------- trophy shelf at home
def shelf_set():
    """The front room at night: a long shelf crowded with gold trophies, the red book propped among them."""
    M = palette()
    world(0.01, (0.03, 0.03, 0.06))
    box("sf_wall", (8, 0.2, 3), (0, 0.4, 1.5), mat("wallpaper", (0.42, 0.36, 0.26), 0.85))
    box("sf_floor", (8, 4, 0.1), (0, -1.5, -0.05), mat("sf_carpet", (0.25, 0.15, 0.12), 0.95))
    wood = mat("sf_wood", (0.3, 0.2, 0.12), 0.6)
    for z in (1.1, 1.6):
        box(f"sf_shelf{z}", (3.2, 0.3, 0.04), (0, 0.15, z), wood)
    rnd = random.Random(11)
    xs = [-1.45 + i * 0.21 for i in range(15)]
    for i, x in enumerate(xs):
        for z in (1.12, 1.62):
            if z > 1.5 and i % 4 == 0:
                continue
            trophy(f"sf_tr{i}_{z}", rnd.choice([0.22, 0.26, 0.3, 0.34]), (x, 0.12, z), M["gold"] if rnd.random() > 0.2 else M["chrome"])
    b = book("sf_book")
    b.location = (0.18, 0.08, 1.24)
    b.rotation_euler = (math.radians(80), 0, 0)
    spot("sf_lamp", (-0.6, -1.2, 2.4), (0, 0.2, 1.3), 260, 50, 0.7, (1, 0.75, 0.45), 0.2)
    area("sf_fill", (1.5, -2, 1.4), (0, 0, 1.3), 20, 2, color=(0.4, 0.5, 1.0))


# ---------------------------------------------------------------- the team boss's office, 1998
def office_set():
    """A dark, modern office: grey walls, a long desk in dark wood, a silver model race car on the sideboard, a big
    window with a grey sky. The boss behind the desk (+Y side), visitors on the -Y side."""
    M = palette()
    world(0.04, (0.3, 0.33, 0.4))
    box("bo_floor", (10, 10, 0.1), (0, 0, -0.05), mat("bo_floor", (0.1, 0.1, 0.11), 0.4))
    wall = mat("bo_wall", (0.2, 0.2, 0.21), 0.8)
    box("bo_back", (10, 0.2, 3.4), (0, 2.6, 1.7), wall)
    box("bo_window", (3.6, 0.22, 2.0), (-2.4, 2.58, 1.6), glow("bo_sky", (0.55, 0.6, 0.7), 1.2))
    for x in (-3.4, -2.4, -1.4):
        box(f"bo_mullion{x}", (0.06, 0.25, 2.0), (x, 2.56, 1.6), M["dark"])
    wood = mat("bo_desk", (0.12, 0.08, 0.06), 0.35, coat=0.5)
    box("bo_desktop", (2.4, 1.0, 0.06), (0, 0.6, 0.76), wood)
    box("bo_deskfront", (2.4, 0.06, 0.72), (0, 0.12, 0.38), wood)
    box("bo_sideboard", (2.2, 0.5, 0.9), (1.8, 2.25, 0.45), wood)
    box("bo_chair", (0.6, 0.6, 0.5), (-0.9, 1.75, 0.25), M["dark"])  # pushed back: he is standing
    box("bo_chairback", (0.6, 0.12, 0.9), (-0.9, 2.07, 0.95), M["dark"])
    img_plane("bo_contract", "contract_0", (0.21, 0.297), (0.0, 0.3, 0.792), (0, 0, 180))
    box("bo_lamp", (0.08, 0.08, 0.45), (-0.95, 0.85, 1.0), M["chrome"])
    box("bo_lamphead", (0.3, 0.14, 0.08), (-0.85, 0.85, 1.24), M["chrome"])
    spot("bo_desklamp", (-0.8, 0.85, 1.2), (0, 0.45, 0.78), 90, 70, 0.6, (1, 0.85, 0.65), 0.05)
    area("bo_win_l", (-2.4, 3.6, 1.8), (0, 0, 1.0), 260, 3.5, color=(0.75, 0.82, 1.0))
    area("bo_key", (2.5, -2.5, 2.8), (0, 0.6, 1.2), 160, 2.5, color=(1, 0.9, 0.8))
    return box("bo_modelbase", (0.5, 0.3, 0.04), (1.8, 2.25, 0.92), M["dark"])


# ---------------------------------------------------------------- Brazil 2008, rain at dusk
def rain(name, center, size=(12, 30, 8), n=500, seed=3, length=0.5):
    """Rain streaks: thin glowing-white slivers (each a 4-vertex sliver, untouched by the voxeliser)."""
    rnd = random.Random(seed)
    m = mat("rain", (0.8, 0.85, 0.95), 0.2, emit=(0.6, 0.65, 0.75), emit_strength=0.6, alpha=0.45)
    verts, faces = [], []
    for i in range(n):
        x = center[0] + rnd.uniform(-size[0] / 2, size[0] / 2)
        y = center[1] + rnd.uniform(-size[1] / 2, size[1] / 2)
        z = center[2] + rnd.uniform(0, size[2])
        L = length * rnd.uniform(0.6, 1.3)
        k = len(verts)
        verts += [(x, y, z), (x + 0.008, y, z), (x + 0.03, y + 0.02, z - L), (x + 0.022, y + 0.02, z - L)]
        faces.append((k, k + 1, k + 2, k + 3))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.materials.append(m)
    ob = link(bpy.data.objects.new(name + "_screen", me))  # "screen": the voxeliser skips it
    ob["smooth"] = True
    return ob


def spray(name, car_root, length=6.0, seed=1):
    """Grey-white spray thrown up behind a car's rear wheels (soft translucent blocks)."""
    M = palette()
    rnd = random.Random(seed)
    m = mat("spray", (0.85, 0.87, 0.9), 0.6, alpha=0.35)
    bpy.context.view_layer.update()
    Mw = car_root.matrix_world
    out = []
    for i in range(60):  # small soft blocks fanning out from the rear wheels, rising and spreading with distance
        t = rnd.uniform(0, 1) ** 1.5
        s = 0.12 + t * 0.45
        side = rnd.choice((-1, 1))
        p = Mw @ V((side * (0.75 + t * 0.6) + rnd.uniform(-0.25, 0.25), -2.2 - t * length, 0.25 + t * 0.9 + rnd.uniform(-0.1, 0.2)))
        ob = box(f"{name}{i}", (s, s, s * 0.7), tuple(p), m)
        ob["smooth"] = True
        out.append(ob)
    return out


def interlagos_set():
    """Brazil 2008, the last lap in the rain at dusk: a wet track along Y (x -6..6) climbing gently, kerbs, run-off,
    armco, a grandstand of umbrellas, low dark clouds, the last light in the west; floodlit only by the sky."""
    M = palette()
    sky_world((0.55, 0.45, 0.42), (0.12, 0.13, 0.18), 0.55)
    wet = mat("wet_asphalt", (0.05, 0.05, 0.055), 0.08, coat=0.0)
    box("ig_track", (12, 520, 0.1), (0, 0, -0.05), wet)
    for s in (1, -1):
        box(f"ig_line{s}", (0.15, 520, 0.012), (s * 5.85, 0, 0.004), M["white"])
        box(f"ig_kerb{s}", (0.9, 520, 0.1), (s * 6.4, 0, -0.01), kerb())
    box("ig_grassR", (80, 520, 0.1), (47, 0, -0.08), mat("wet_grass", (0.06, 0.16, 0.06), 0.4))
    box("ig_grassL", (80, 520, 0.1), (-47, 0, -0.08), mat("wet_grass", (0.06, 0.16, 0.06), 0.4))
    H.armco("ig_armco", -120, 200, 9.0)
    H.tyre_wall("ig_tyres", -9.5, -120, 200)
    H.hoardings("ig_boardsR", 8.6, -120, 200, 2, 0.6)
    H.hoardings("ig_boardsL", -9.0, -120, 200, 5, 1.5)
    H.grandstand("ig_stand", -12, -90, 30, -1, rows=8, crowd=umbrellas(), nflags=0)
    H.crowd_cards("ig_cc", -12, -90, 30, -1, 8, seed=21)
    H.grandstand("ig_stand2", -12, 40, 170, -1, rows=10, crowd=umbrellas(), nflags=6, seed=4)
    H.crowd_cards("ig_cc2", -12, 40, 170, -1, 10, seed=22)
    H.grandstand("ig_standR", 13.0, -40, 160, 1, rows=9, crowd=umbrellas(), nflags=8, seed=6)
    H.crowd_cards("ig_ccR", 13.0, -40, 160, 1, 9, seed=23)
    H.catch_fence("ig_fenceR", 12.2, -120, 200, 3.5)
    rnd = random.Random(8)
    lampg = glow("ig_lamp", (1.0, 0.85, 0.6), 14)
    for i, y in enumerate(range(-110, 200, 26)):  # light poles along the straight, already on in the gloom
        for s, x in ((1, 10.6), (-1, -10.4)):
            box(f"ig_pole{s}_{i}", (0.25, 0.25, 9), (x, y + (13 if s < 0 else 0), 4.5), M["grey"])
            box(f"ig_lamphead{s}_{i}", (1.2, 0.5, 0.25), (x - s * 0.5, y + (13 if s < 0 else 0), 9.0), lampg)
    for i, y in enumerate(range(-100, 200, 45)):  # marshal posts and TV camera towers
        H.marshal_post(f"ig_post{i}", 10.2, y + 8)
        box(f"ig_tv{i}", (1.6, 1.6, 6.5), (11.5, y + 30, 3.25), mat("tvtower", (0.3, 0.3, 0.32), 0.7))
        box(f"ig_tvcab{i}", (1.8, 1.8, 1.4), (11.5, y + 30, 7.2), M["dark"])
    box("ig_bridge", (40, 3.0, 1.6), (0, 95, 8.2), mat("bridge", (0.75, 0.75, 0.72), 0.6))  # a footbridge over the track
    box("ig_bridgeband", (40.2, 3.1, 0.5), (0, 95, 8.6), M["redm"])
    for x in (-10.5, 10.5):
        box(f"ig_bridgeleg{x}", (1.0, 2.0, 7.4), (x, 95, 3.7), mat("bridge", (0.75, 0.75, 0.72), 0.6))
    for i in range(16):
        tree(f"ig_tree{i}", rnd.choice([rnd.uniform(18, 45), rnd.uniform(-60, -35)]), rnd.uniform(-120, 220), rnd.choice([6, 7, 9]), rnd.choice([2.5, 3]))
    # the hills and the city: São Paulo's high-rises on the horizon, windows lighting up at dusk
    def windows(x, y):
        return (0.95, 0.75, 0.42) if (x % 2 == 1 and y % 3 == 1 and rnd.random() < 0.45) else _noisy((0.32, 0.31, 0.3), 0.3, rnd)
    city = pixmat("ig_city", _img("ig_city", 16, 32, windows), 6.0, 0.8, emit=0.35)
    hill = mat("ig_hill", (0.08, 0.14, 0.08), 0.9)
    for i in range(8):
        box(f"ig_hill{i}", (rnd.uniform(80, 140), 60, rnd.uniform(12, 22)), (rnd.choice([-1, 1]) * rnd.uniform(70, 150), rnd.uniform(160, 330), 4), hill)
    for i in range(46):
        side = rnd.choice([-1, 1])
        h = rnd.choice([22, 30, 38, 46, 58, 70])
        w = rnd.choice([10, 12, 14, 18])
        box(f"ig_tower{i}", (w, w, h), (side * rnd.uniform(55, 190), rnd.uniform(170, 420), h / 2 + 4), city)
    sun("ig_sun", (84, 0, 200), 1.6, 8, (1.0, 0.6, 0.35))
    for y in (-40, 0, 50, 100, 150):
        area(f"ig_sky{y}", (0, y, 30), (0, y, 0), 40000, 50, color=(0.65, 0.7, 0.85))


def umbrellas():
    cols = [(0.1, 0.1, 0.12), (0.75, 0.05, 0.05), (0.9, 0.9, 0.9), (0.1, 0.3, 0.7), (0.95, 0.75, 0.1), (0.1, 0.45, 0.2)]
    rnd = random.Random(31)
    return H._px("umbrellas", 32, 32, lambda x, y: (0.2, 0.2, 0.22) if y % 4 == 3 else cols[rnd.randrange(len(cols))], 2.0)


def pitwall_set():
    """The team's pit-wall stand in the rain: a counter of screens under a roof, stools, the team in silver-and-red
    kit with headsets; the wet pit straight behind. The stand faces +Y (the track)."""
    M = palette()
    sky_world((0.5, 0.42, 0.4), (0.12, 0.13, 0.18), 0.5)
    box("pw_lane", (60, 12, 0.1), (0, -6, -0.05), mat("wet_concrete", (0.25, 0.25, 0.26), 0.15))
    box("pw_track", (60, 14, 0.1), (0, 9, -0.06), mat("wet_asphalt", (0.05, 0.05, 0.055), 0.08))
    box("pw_wall", (60, 0.6, 1.1), (0, 1.5, 0.55), M["white"])
    box("pw_fence", (60, 0.05, 2.5), (0, 1.8, 2.3), mat("fence_wire", (0.2, 0.2, 0.22), 0.6, alpha=0.4))
    box("pw_deck", (5, 2.0, 0.6), (0, 0.0, 0.3), M["dark"])
    box("pw_counter", (5, 0.6, 0.1), (0, 0.6, 1.5), M["grey"])
    for i, x in enumerate((-1.6, -0.55, 0.55, 1.6)):  # low screens, so faces show over them from the track side
        box(f"pw_screen{i}", (0.8, 0.06, 0.42), (x, 0.82, 1.78), data_screen())
        box(f"pw_screenbk{i}", (0.84, 0.08, 0.45), (x, 0.86, 1.78), M["dark"])
    box("pw_roof", (5.6, 2.8, 0.12), (0, 0.2, 3.1), mat("pw_roofcol", (0.75, 0.75, 0.78), 0.5))
    for x in (-2.5, 2.5):
        box(f"pw_post{x}", (0.1, 0.1, 2.5), (x, -0.9, 1.85), M["grey"])
    box("pw_redband", (5.6, 0.14, 0.2), (0, -1.15, 3.0), M["redm"])
    area("pw_screens_l", (0, 0.4, 1.9), (0, -1.2, 1.6), 60, 3, color=(0.6, 0.8, 1.0))
    area("pw_sky", (0, -6, 12), (0, 0, 1), 1500, 12, color=(0.65, 0.7, 0.85))
    sun("pw_sun", (84, 0, 200), 0.4, 8, (1.0, 0.6, 0.35))
    rain("pw_rain", (0, 6.5, 0), (14, 8, 6), 700, 7, 0.4)  # over the track, in front of the stand
