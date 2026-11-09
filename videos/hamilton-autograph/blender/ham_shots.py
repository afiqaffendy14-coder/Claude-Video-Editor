"""Shot list v1 for "Phone me in nine years" (Hamilton autograph short): 48.30 s, 22 hard cuts on take 1's word
starts (tools/timing.json). Shots with an action have keys (phases of the same scene) so the storyboard shows how
things happen. Every frame is collision-checked (check.py).

Run: blender -b --factory-startup --python blender/ham_shots.py -- board [ids...]   -> boards/stills/sNN[a|b|c].png
     blender -b --factory-startup --python blender/ham_shots.py -- json            -> boards/shots.json
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from mathutils import Matrix, Vector
import lib
from lib import V, reset, palette, setup_render, camera, render, box, mat
import sets as S
import halo_sets as H
from halo_sets import person_at
import ham_sets as A
from ham_sets import KID, TEEN, BOSS
import voxel
import ik

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STILLS = os.path.join(ROOT, "boards", "stills")
PANEL = {}  # shot -> (w, h) when a key renders a split-screen panel instead of a full frame


def cam(loc, target, lens=35, dof=None, fstop=2.8, roll=0.0):
    camera(V(loc), V(target), lens, dof, fstop, roll)


def hold(obj, person, k="R"):
    S.register_hold(obj.name, person.name, "hand", hand=k)


def held_book(name, centre, rot_deg, opened=False, page="page_0"):
    b = A.book(name, opened, page)
    b.location = centre
    b.rotation_euler = tuple(math.radians(a) for a in rot_deg)
    bpy.context.view_layer.update()
    return b


# ---------------------------------------------------------------- 1995: the ask
BOSS_XY = (0.0, 0.62)
BOY_XY = (0.0, -0.42)


KNEEL = dict(crouch=0.355, lean=40, legL=(0, 6, 90), legR=(0, 6, 90), head=(0, 20))  # both knees down, shins flat


def boss(pose="look_down", hands=None, outfit="dennis_tux"):
    return person_at("dennis", BOSS_XY[0], BOSS_XY[1], 180, pose, outfit, scale=BOSS, hands=hands)


TURN = Matrix.Rotation(math.radians(-90), 4, "Z")  # meeting frame (boy -> boss along +Y) -> world (along +X)


def turn_cast():
    """Turn everything built for the meeting (not the set, lights or camera) so the pair stand side-on to a camera
    that looks toward the stage."""
    bpy.context.view_layer.update()
    for ob in list(bpy.data.objects):
        if ob.parent or ob.name.startswith("aw_") or ob.type in ("LIGHT", "CAMERA"):
            continue
        ob.matrix_world = TURN @ ob.matrix_world
    bpy.context.view_layer.update()


def s01():
    """First frame: the tiny boy holds the book up at arm's length to the towering boss."""
    A.awards_set()
    c = (0.0, -0.16, 1.04)
    b = held_book("book", c, (-55, 0, 0))
    M = b.matrix_world
    hl, hr = M @ V((0.115, 0.0, 0.0)), M @ V((-0.115, 0.0, 0.0))
    kid = person_at("boy", BOY_XY[0], BOY_XY[1], 0, "offer", "boy_blazer", scale=KID, hands={"L": tuple(hl), "R": tuple(hr)})
    hold(b, kid, "L"); hold(b, kid, "R")
    boss(dict(S.POSE["look_down"], head=(0, 20)))
    turn_cast()
    cam((0.12, -2.75, 0.62), (0.12, 0.0, 1.12), 28, 2.75, 3.2)


def s02(key):
    """Dennis takes the book and writes; the boy watches on tiptoe."""
    def b_():
        A.awards_set()
        c = (0.04, 0.26, 1.3)
        b = held_book("book", c, (-38, 0, 180), opened=True, page="page_0" if key == "a" else "page_3")
        M = b.matrix_world
        hand_book = M @ V((-0.18, -0.02, -0.01))   # his left hand under the left cover's outer edge
        nib = M @ V((0.06 if key == "a" else 0.12, 0.02, 0.012))
        p = A.pen("pen")
        p.location = tuple(nib + V((0, 0.04, 0.07)))
        p.rotation_euler = (math.radians(-30), math.radians(-20), 0)
        bpy.context.view_layer.update()
        grip = p.matrix_world @ V((0, 0, 0.0))
        dn = boss("write", hands={"R": tuple(hand_book), "L": tuple(grip)})
        hold(b, dn, "R"); hold(p, dn, "L")
        person_at("boy", -0.26, -0.36, 10, "tiptoe", "boy_blazer", scale=KID)
        turn_cast()
        cam((-0.8, -0.5, 1.02), (0.5, 0.05, 1.42), 30, 1.45, 2.8)
    return b_


def s03(key):
    """Insert, over his shoulder: the page as the words are written."""
    def b_():
        A.awards_set()
        c = (0.04, 0.26, 1.3)
        b = held_book("book", c, (-38, 0, 180), opened=True, page="page_3" if key == "a" else "page_6")
        M = b.matrix_world
        hand_book = M @ V((-0.18, -0.02, -0.01))
        nib = M @ V((0.168, 0.024, 0.012) if key == "a" else (0.176, -0.046, 0.012))
        p = A.pen("pen")
        p.location = tuple(nib + M.to_3x3() @ V((0.06, -0.05, 0.07)))
        p.rotation_euler = (math.radians(-30), math.radians(-20), 0)
        bpy.context.view_layer.update()
        dn = boss("write", hands={"R": tuple(hand_book), "L": tuple(p.matrix_world @ V((0, 0, 0)))})
        hold(b, dn, "R"); hold(p, dn, "L")
        turn_cast()
        M = b.matrix_world
        n = M.to_3x3() @ V((0, 0, 1))
        c = tuple(M @ V((0.09, 0.0, 0.0)))  # centred on the written page
        cpos = V(c) + n * 0.5
        cam(tuple(cpos), c, 35, 0.5, 4.0, 0)
        A.spot("page_light", tuple(V(c) + n * 0.6 + V((0, -0.3, 0.3))), c, 60, 30, 0.6, (1, 0.9, 0.75), 0.1)
        cm = bpy.data.objects["cam"]
        # point the camera's up along the page's text-up (+Y of the book)
        up = M.to_3x3() @ V((0, 1, 0))
        d = (V(c) - cpos).normalized()
        q = d.to_track_quat("-Z", "Y")
        cm.rotation_euler = q.to_euler()
        bpy.context.view_layer.update()
        cy = cm.matrix_world.to_3x3() @ V((0, 1, 0))
        ang = math.atan2(cy.cross(up).dot(d), cy.dot(up))
        cm.rotation_euler.rotate_axis("Z", -ang)
    return b_


# ---------------------------------------------------------------- home: no money
def s04():
    """The kitchen at night: the dad at the table with the bills and the coin jar, the boy in the doorway."""
    A.kitchen_set()
    A.seated("dad", 0.05, -0.74, 0, dict(S.POSE["slump"], lean=18, head=(0, 12)), "dad", 0.475,
             ("kt_chair0", "kt_tabletop"), hands={"L": (0.2, -0.32, 0.825), "R": (-0.12, -0.34, 0.825)})
    A.allow("dad", "kt_chairleg011")  # his thigh brushes the chair's front leg
    person_at("boy", -2.62, -1.25, -90, "doorway", "boy_home", scale=KID)
    cam((0.55, 1.2, 1.15), (-0.85, -0.75, 1.0), 26, 2.0, 4.0)


# ---------------------------------------------------------------- the shed
def s05():
    """The battered kart under the bare bulb."""
    A.shed_set("battered", book_on_wall=False)
    cam((1.55, -1.45, 1.3), (0.0, 0.3, 0.2), 30, 2.3, 4.0)


def s06(key):
    def b_():
        A.shed_set("battered" if key == "a" else "new")
        if key == "a":  # sanding the side pod: kneeling at the kart's side, both hands on the pod
            person_at("dad", 0.1, -0.7, 0, KNEEL, "dad", hands={"L": (0.25, -0.31, 0.38), "R": (-0.05, -0.31, 0.38)})
            A.allow("dad", "sh_kart")
            cam((-1.95, -1.15, 0.95), (0.05, -0.35, 0.45), 30, 2.1, 4.0)
            return
        else:  # done: standing back, looking at it
            person_at("dad", -0.9, -0.95, -30, "stand_by", "dad")
        cam((1.65, 1.35, 1.45), (-0.2, -0.45, 0.45), 28, 2.4, 4.0)
    return b_


# ---------------------------------------------------------------- several jobs (three panels)
def s07(key):
    def b_():
        if key == "a":
            A.office_job_set()
            A.seated("dad", 0.0, -0.1, 0, "desk", "dad_office", 0.5, ("of_chair", "of_chairback", "of_keyboard", "of_desktop"),
                     hands={"L": (0.12, 0.3, 0.815), "R": (-0.12, 0.3, 0.815)})
            cam((1.55, -1.35, 1.45), (-0.05, 0.55, 1.2), 28)
        elif key == "b":
            A.street_job_set()
            person_at("dad", 0.6, 0.2, 0, "stand_by", "dad_hivis", hands={"L": (0.66, 0.53, 1.45), "R": (0.54, 0.53, 1.15)})
            A.allow("dad", "st_post")  # gripping the post
            cam((2.2, -1.6, 1.45), (0.3, 0.6, 1.55), 30)
        else:
            A.shed_set("battered", book_on_wall=True)
            A.img_plane("sh_clock", "clock_2300", (0.36, 0.36), (-0.9, 1.84, 2.2), (90, 0, 0))
            person_at("dad", 0.1, -0.7, 0, KNEEL, "dad", hands={"L": (0.25, -0.31, 0.38), "R": (-0.05, -0.31, 0.38)})
            A.allow("dad", "sh_kart")
            cam((1.7, -1.5, 1.35), (-0.2, 0.5, 0.95), 26)
    return b_


PANEL[7] = (540, 320)


# ---------------------------------------------------------------- the kart track
ROW = [(-1.2, "kid_red"), (0.9, "kid_green"), (3.0, "boy"), (5.1, "kid_grey"), (-3.3, "kid_yellowsuit")]


def kid_with_helmet(name, x, y, rot, outfit, pose="helmet_hold", col="white", stripe="kartblue"):
    """A kid carrying his helmet at his side by the chin bar (one hand)."""
    import props
    Mp = Matrix.Translation(V((x, y, 0))) @ Matrix.Rotation(math.radians(rot), 4, "Z")
    grip = Mp @ V((0.3, 0.03, 0.6))  # the hand hangs a little out from the hip, holding the helmet's top
    hl = props.helmet(name + "_helmet", col, stripe)
    hl.scale = (KID, KID, KID)
    hl.location = tuple(grip - V((0, 0, 0.38 * KID)))
    hl.rotation_euler = (0, 0, math.radians(rot))
    bpy.context.view_layer.update()
    pr = person_at(name, x, y, rot, pose, outfit, scale=KID, hands={"L": tuple(grip)})
    S.register_hold(hl.name, pr.name, "hand", hand="L")
    return pr


def paddock_row():
    A.kart_track_set()
    import random
    rnd = random.Random(4)
    cols = {"kid_red": "redm", "kid_green": "green_it", "kid_grey": "grey", "kid_yellowsuit": "orange", "boy": None}
    for x, who in ROW:
        A.kart(f"k_{who}", "new", (x, 0.0, 0.0), 0, color=palette()[cols[who]] if cols[who] else None)
        if who == "boy":
            kid_with_helmet("boy", x, -1.25, 180, "boy_suit")
        else:
            person_at(who, x, -1.2, 180 + rnd.choice([-10, 0, 15]), "stand_by", who, scale=KID)
    for i, (x, y, r, o) in enumerate(((-2.0, 2.2, 160, "parent_a"), (2.0, 2.6, 200, "parent_b"), (4.2, 2.3, 190, "parent_c"))):
        person_at(f"parent{i}", x, y, r, "watch", o)


def s08():
    paddock_row()
    cam((-0.2, -4.6, 1.05), (2.0, -0.8, 0.75), 30, 5.0, 5.6)


def s09():
    """A group turned away from him; he stands alone, helmet in hand."""
    A.kart_track_set()
    group = [(-2.6, 3.6, 175, "kid_red"), (-2.0, 3.9, 195, "kid_green"), (-1.4, 3.5, 170, "parent_a"),
             (-3.1, 4.2, 185, "parent_b"), (-1.0, 4.3, 200, "kid_grey"), (-2.3, 4.6, 180, "parent_c")]
    for i, (x, y, r, o) in enumerate(group):
        person_at(f"g{i}", x, y, r - 180, "turned" if i % 2 else "stand_by", o, scale=KID if o.startswith("kid") else 1.0)
    kid_with_helmet("boy", 0.9, -0.6, 20, "boy_suit")
    A.kart("k_boy", "new", (2.0, 0.3, 0.0), 10)
    cam((2.5, -2.9, 1.25), (-1.3, 3.4, 0.9), 30, 5.0, 4.0)


def s10(key):
    """Behind a van: he wipes his eye, then straightens up as his dad comes."""
    def b_():
        A.kart_track_set()
        bx, by, rot = -7.55, 5.6, -90
        if key == "a":
            Mp = Matrix.Translation(V((bx, by, 0))) @ Matrix.Rotation(math.radians(rot), 4, "Z")
            eye = Mp @ V((-0.06, 0.16, 1.13))
            person_at("boy", bx, by, rot, "wipe", "boy_suit", scale=KID, hands={"R": tuple(eye)})
        else:
            person_at("boy", bx, by, rot - 25, "brave", "boy_suit", scale=KID)
            person_at("dad", -4.6, 3.6, 60, dict(S.POSE["walk"]), "dad_coat", stance=(0.22, -0.22))
        cam((-6.3, 4.1, 1.0), (-7.55, 5.6, 1.02), 40, 1.9, 2.2)
    return b_


def s11(key):
    """The dad kneels to his level, a hand on his shoulder: 'always do your talking on the track'."""
    def b_():
        A.kart_track_set()
        A.kart("k_boy", "new", (3.6, 1.2, 0.0), 0)
        bx, by = 2.6, 0.0
        person_at("boy", bx, by, 0, "nod" if key == "b" else "stand_by", "boy_suit", scale=KID)
        sh = (bx + 0.2, by + 0.0, 0.94)  # the boy's shoulder on the dad's side
        kneel = dict(S.POSE["kneel"], lean=15, head=(0, -10))
        if key == "a":
            person_at("dad", bx + 0.64, by + 0.1, 90, kneel, "dad_coat", hands={"R": sh})
        else:
            person_at("dad", bx + 0.64, by + 0.1, 90, dict(kneel, armL=(75, 55, 5), head=(30, -6)), "dad_coat", hands={"R": sh})
        A.allow("dad", "boy", "kt_paddock", "kt_grass"); A.allow("boy", "dad")
        bpy.data.objects["dad"]["foot_free"] = "R"  # kneeling: the back foot's toes rest on the ground  # hand on his shoulder, a knee on the ground
        cam((bx + 0.55, by + 2.3, 1.0), (bx + 0.3, by, 0.82), 32, 2.3, 3.0)
    return b_


def s12():
    """Visor down, the kart launches and passes a rival into the first corner."""
    A.kart_track_set()
    k = A.kart("k_boy", "new", (11.2, 2.0, 0.0), 0)
    A.kart_driver("boy", k, "boy_suit_h")
    r = A.kart("k_red", "new", (13.0, 1.2, 0.0), 0, color=palette()["redm"])
    A.kart_driver("rival", r, "kid_red_h")
    g = A.kart("k_green", "new", (12.3, -1.6, 0.0), 0, color=palette()["green_it"])
    A.kart_driver("rival2", g, "kid_green_h")
    cam((9.9, 3.9, 1.05), (11.6, 1.6, 0.45), 28, 2.8, 4.0)


def s13():
    """'Again': his kart takes the chequered flag."""
    A.kart_track_set()
    k = A.kart("k_boy", "new", (12.0, 5.8, 0.0), 0)
    A.kart_driver("boy", k, "boy_suit_h")
    f = A.chequered_flag("flag", (8.3, 6.4, 1.75), (0, -30, -70))
    bpy.context.view_layer.update()
    person_at("marshal", 7.95, 6.4, -90, "flag_wave", "marshal", hands={"L": tuple(f.matrix_world @ V((0, 0, -0.4)))})
    S.register_hold("flag", "marshal", "hand", hand="L")
    cam((13.9, 8.9, 0.75), (10.6, 5.9, 0.85), 26, 4.3, 3.0)


def s14():
    """'And again': he lifts a trophy on the top step."""
    A.podium_set()
    hz = 0.8 + KID * 1.305 + 0.27  # hands up above his head, within reach of his shoulders
    A.trophy("trophy", 0.42, (-2.0, 19.92, hz - 0.12))
    person_at("boy", -2.0, 20.0, 180, "trophy_up", "boy_suit", z=0.8, scale=KID, hands={"L": (-2.11, 19.92, hz), "R": (-1.89, 19.92, hz)})
    S.register_hold("trophy", "boy", "hand", hand="L")
    person_at("p2", -3.1, 20.0, 180, "stand_by", "kid_red", z=0.5, scale=KID)
    person_at("p3", -0.9, 20.0, 180, "stand_by", "kid_green", z=0.35, scale=KID)
    cam((-1.6, 16.4, 1.15), (-2.0, 20.0, 1.55), 32, 3.6, 4.0)


def s15():
    A.shelf_set()
    cam((-1.25, -0.75, 1.42), (0.35, 0.15, 1.3), 30, 1.6, 2.4)


# ---------------------------------------------------------------- 1998: signed
def s16(key):
    def b_():
        A.office_set()
        if key == "a":  # he signs; Dennis behind the desk, both hands on it; his dad behind him
            person_at("dennis", 0.2, 1.3, 180, dict(lean=30, head=(0, 6), face="smile"), "dennis_suit", scale=BOSS,
                      hands={"L": (-0.1, 1.02, 0.835), "R": (0.5, 1.02, 0.835)})
            A.allow("boy", "bo_contract", "bo_desktop")
            A.allow("dennis", "bo_desktop")
            person_at("boy", 0.05, -0.1, 0, "sign_desk", "teen_blazer", scale=TEEN, hands={"R": (0.0, 0.3, 0.81)})
            person_at("dad", -0.75, -0.55, 15, "proud", "dad_coat")
            cam((1.55, -1.3, 1.35), (0.05, 0.4, 1.0), 28, 2.0, 3.2)
        else:  # a handshake beside the desk
            person_at("boy", 1.0, -0.6, -90, "shake", "teen_blazer", scale=TEEN, hands={"R": (1.35, -0.44, 1.02)})
            person_at("dennis", 1.68, -0.6, 90, "shake", "dennis_suit", scale=BOSS, hands={"L": (1.37, -0.44, 1.02)})
            person_at("dad", 0.2, -1.1, -60, "proud", "dad_coat")
            A.allow("boy", "dennis"); A.allow("dennis", "boy")  # the handshake
            cam((1.25, -3.3, 1.25), (1.25, -0.5, 1.2), 30, 2.8, 3.2)
    return b_


# ---------------------------------------------------------------- Brazil 2008
def s17():
    A.interlagos_set()
    h = A.car("ham", "chrome08", (0.0, -20.0, 0.0), 0)
    A.car_driver("lewis", h)
    g = A.car("glock", "blanco08", (2.6, -12.5, 0.0), 10, steer=-8)
    A.car_driver("glock_d", g, "driver_white_h")
    A.rain("rain", (0.0, -26.0, 0.0), (6, 6, 3), 500, 3, 0.35)  # spray comes in the animation (particles)
    cam((-2.4, -27.0, 1.6), (0.9, -15.0, 0.5), 30, 8.0, 4.0)


def s18():
    A.interlagos_set()
    h = A.car("ham", "chrome08", (-1.6, 0.4, 0.0), -4)
    A.car_driver("lewis", h)
    g = A.car("glock", "blanco08", (1.4, -0.3, 0.0), 8, steer=-8)
    A.car_driver("glock_d", g, "driver_white_h")
    A.rain("rain", (-5.0, 1.5, 0.0), (4, 5, 3), 400, 4, 0.35)
    cam((-7.0, 4.6, 3.2), (0.0, 0.0, 0.4), 30, 8.5, 4.0)


def s19(key):
    def b_():
        if key == "a":  # across the line under the chequered flag
            A.interlagos_set()
            M = palette()
            box("ig_finish", (11.7, 0.3, 0.012), (0, 0, 0.012), M["white"])
            h = A.car("ham", "chrome08", (0.0, -1.0, 0.0), 0)
            A.car_driver("lewis", h)
            box("ig_flagstand", (1.4, 1.4, 0.6), (-7.65, 1.2, 0.3), M["white"])
            f = A.chequered_flag("flag", (-7.3, 1.2, 2.4), (0, 30, 70), (1.0, 0.7))
            bpy.context.view_layer.update()
            person_at("marshal", -7.65, 1.2, -90, "flag_wave", "marshal", z=0.6, hands={"L": tuple(f.matrix_world @ V((0, 0, -0.4)))})
            S.register_hold("flag", "marshal", "hand", hand="L")
            A.rain("rain", (4.5, 1.0, 0.0), (5, 5, 3), 400, 5, 0.35)
            cam((6.5, 2.6, 0.6), (0.0, -0.6, 0.75), 26, 6.6, 4.0)
        else:  # the crew in the garage erupt
            H.TEAM["mcl08"] = dict(wall="charcoal", accent="red", blanket="dark", livery="w09")
            H.garage_set("mcl08", car=False)
            for i, (x, y, r, jump) in enumerate(((-1.6, 0.6, 10, 0.18), (-0.5, 1.0, -5, 0.0), (0.6, 0.7, 5, 0.22),
                                                 (1.7, 1.1, -12, 0.0), (-2.6, -0.4, 20, 0.0), (2.6, -0.2, -20, 0.12))):
                p = dict(S.POSE["cheer"])
                if jump:
                    p.update(legL=(30, 6, 50), legR=(10, 6, 40))
                pr = person_at(f"crew{i}", x, y, r, p, "crew08", z=jump)
                pr["airborne"] = bool(jump)  # jumping for joy
            cam((0.4, 4.8, 1.55), (0.0, -0.2, 1.45), 28, 4.8, 4.0)
    return b_


def s20(key):
    """Dennis on the pit wall: a slow breath, then a clenched fist."""
    def b_():
        A.pitwall_set()
        p = dict(head=(0, 6), face="neutral") if key == "a" else dict(head=(0, -6), face="smile", armR=(100, -18, 120))
        hands = {"L": (0.55, 0.42, 1.6), "R": (-0.05, 0.42, 1.6)} if key == "a" else {"L": (0.55, 0.42, 1.6)}
        person_at("dennis", 0.25, 0.12, 0, p, "dennis_team", z=0.6, scale=BOSS * 0.97, hands=hands)
        person_at("eng1", -1.3, 0.12, 0, dict(head=(10, 4)), "crew08", z=0.6, hands={"L": (-1.15, 0.42, 1.6), "R": (-1.45, 0.42, 1.6)})
        person_at("eng2", 1.6, 0.12, 0, dict(head=(-15, 4)), "crew08", z=0.6, hands={"L": (1.75, 0.42, 1.6), "R": (1.45, 0.42, 1.6)})
        for who in ("dennis", "eng1", "eng2"):
            A.allow(who, "pw_counter")  # hands resting on the counter
        cam((1.35, 2.5, 2.5), (0.3, 0.12, 2.12), 30, 2.6, 3.0)
    return b_


def s21():
    """Callback: the fixed-up kart under the bulb, the book on the wall. No one in shot."""
    A.shed_set("new")
    cam((1.5, -1.0, 1.05), (0.5, 1.1, 0.95), 28, 2.3, 3.2)


def s22(key):
    """The grown driver lifts off his helmet: the reveal. Hard cut."""
    def b_():
        import props
        A.pitwall_set()
        A.car("ham", "chrome08", (0.0, -4.4, 0.0), 90)
        neck = V((0.0, -6.0, 19 * 0.045 + 12 * 0.045))
        props.helmet("helmet", "white", "red")
        hl = bpy.data.objects["helmet"]
        if key == "a":  # helmet on, both hands on its sides, about to pull it off
            hl.location = tuple(neck + V((0, 0.02, 0.0)))
            hl.rotation_euler = (0, 0, math.radians(180))
            hz, hy = neck.z + 0.17, -6.0
        else:  # just off: held in both hands in front of his chest, face clear
            hl.location = (0.0, -6.3, 0.86)
            hl.rotation_euler = (math.radians(-20), 0, math.radians(180))
            hz, hy = 1.03, -6.3
        bpy.context.view_layer.update()
        person_at("lewis", 0.0, -6.0, 180, dict(head=(0, -4), face="neutral" if key == "a" else "smile"), "driver08_h" if key == "a" else "driver08",
                  hands={"L": (-0.25, hy, hz), "R": (0.25, hy, hz)})
        S.register_hold("helmet", "lewis", "hand", hand="L")
        A.rain("rain2", (0.0, -7.5, 0.0), (3, 2, 3), 300, 9, 0.3)
        cam((0.12, -7.75, 1.6), (0.0, -6.0, 1.6), 45, 1.75, 2.4)
    return b_


SHOTS = [  # n, start, end, keys {label: builder}, description
    (1, 0.00, 3.51, {"": s01}, "AGE 10. The tiny boy holds his red autograph book up to the towering boss in black tie."),
    (2, 3.51, 6.39, {"a": s02("a"), "b": s02("b")}, "Dennis takes the book and writes in it; the boy watches on tiptoe."),
    (3, 6.39, 8.12, {"a": s03("a"), "b": s03("b")}, "Insert: the page. 'Phone me in 9 years', then a made-up scribbled signature."),
    (4, 8.12, 10.55, {"": s04}, "Home, night: the dad at the kitchen table with the bills and a nearly empty coin jar; the boy in the doorway."),
    (5, 10.55, 12.28, {"": s05}, "The shed: a battered fifth-hand kart (dents, rust, tape, odd panels, layers of old stickers)."),
    (6, 12.28, 14.45, {"a": s06("a"), "b": s06("b")}, "The dad sands and paints it; then it shines like new. The red book is pinned on the wall."),
    (7, 14.45, 17.07, {"a": s07("a"), "b": s07("b"), "c": s07("c")}, "Split screen: the dad's jobs. Office desk (9:00), outdoors in hi-vis (18:00), the kart in the shed (23:00)."),
    (8, 17.07, 19.72, {"": s08}, "The kart track paddock: kids by their karts. He's the only Black kid."),
    (9, 19.72, 22.47, {"": s09}, "A group of kids and parents with their backs to him. He stands alone, helmet in hand."),
    (10, 22.47, 25.77, {"a": s10("a"), "b": s10("b")}, "Behind a van he wipes his eye; then, as his dad comes, he straightens up."),
    (11, 25.77, 28.87, {"a": s11("a"), "b": s11("b")}, "His dad kneels to his level, a hand on his shoulder; on 'track' he points at the circuit. The boy nods."),
    (12, 28.87, 30.53, {"": s12}, "Visor down, the kart launches and passes the others into the first corner."),
    (13, 30.53, 31.18, {"": s13}, "'Again': the chequered flag over his kart."),
    (14, 31.18, 32.01, {"": s14}, "'And again': he lifts a trophy on the top step."),
    (15, 32.01, 32.79, {"": s15}, "'And again': a shelf crowded with trophies, the red book among them."),
    (16, 32.79, 35.31, {"a": s16("a"), "b": s16("b")}, "AGE 13. In the boss's office he signs the contract, his dad behind him; then a handshake."),
    (17, 35.31, 38.35, {"": s17}, "AGE 23. Brazil 2008, the last lap in the rain: his silver car behind a slower white car."),
    (18, 38.35, 40.08, {"": s18}, "Two corners from the end: up the inside, side by side, and through."),
    (19, 40.08, 43.04, {"a": s19("a"), "b": s19("b")}, "Across the line under the chequered flag; his crew in the garage erupt."),
    (20, 43.04, 45.10, {"a": s20("a"), "b": s20("b")}, "Dennis on the pit wall: a slow breath, then a clenched fist."),
    (21, 45.10, 46.28, {"": s21}, "Callback: the fixed-up kart under the bulb, the book on the wall."),
    (22, 46.28, 48.30, {"a": s22("a"), "b": s22("b")}, "The grown driver lifts off his helmet on 'Lewis'. Hard cut."),
]


def build(builder):
    lib.STYLE["voxel"] = True
    lib.STYLE["low"] = 0
    builder()
    voxel.voxelize_scene()


def board(ids=None):
    import check
    os.makedirs(STILLS, exist_ok=True)
    report = {}
    for n, t0, t1, keys, desc in SHOTS:
        if ids and n not in ids:
            continue
        for label, b in keys.items():
            reset()
            w, h = PANEL.get(n, (540, 960))
            sc = setup_render(w, h, 24, os.path.join(STILLS, f"s{n:02d}{label}.png"))
            sc.view_settings.exposure = 0.4  # boards: readable; the grade sets the real exposure later
            try:
                build(b)
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"BOARD s{n:02d}{label} FAILED: {e}", flush=True)
                report[f"{n:02d}{label}"] = dict(clips=[f"build failed: {e}"], feet=[])
                continue
            clips, feet = check.check_scene()
            report[f"{n:02d}{label}"] = dict(clips=clips, feet=feet)
            render()
            print(f"BOARD s{n:02d}{label} done; clips {len(clips)} feet {len(feet)}", flush=True)
            for c in clips[:8] + feet[:6]:
                print("    ", c, flush=True)
    path = os.path.join(ROOT, "boards", "check.json")
    old = json.load(open(path)) if os.path.exists(path) else {}
    old.update(report)
    json.dump(old, open(path, "w"), indent=1)


def dump_json():
    out = [dict(n=n, start=t0, end=t1, keys=[""] if n in PANEL else list(k), desc=d) for n, t0, t1, k, d in SHOTS]
    json.dump(out, open(os.path.join(ROOT, "boards", "shots.json"), "w"), indent=1)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if args and args[0] == "board":
        board([int(a) for a in args[1:]] or None)
    elif args and args[0] == "json":
        dump_json()
