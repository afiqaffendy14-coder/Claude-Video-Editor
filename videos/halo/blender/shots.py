"""Shot list v2 for "Imagine a Formula One car landing on your head" (the halo short: 60.0 s, 25 hard cuts).

Cut times are the narrator's word starts (tools/timing.json, take 2). Shots with an action have key frames
("keys": phases of the same scene) so the storyboard shows how things happen, not just the end state; the animation
pass in-betweens them. Every frame is collision-checked (check.py): no clipping, feet on what they stand on.

Run: blender -b --factory-startup --python blender/shots.py -- board [ids...]   -> boards/stills/sNN[a|b|c].png
     blender -b --factory-startup --python blender/shots.py -- json            -> boards/shots.json
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from mathutils import Matrix, Vector
import lib
from lib import V, reset, palette, setup_render, camera, render, box, mat
from props import f1car_block
import props
import sets as S
import halo_sets as H
from halo_sets import person_at
import voxel
import ik

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STILLS = os.path.join(ROOT, "boards", "stills")


def cam(loc, target, lens=35, dof=None, fstop=2.8, roll=0.0):
    camera(V(loc), V(target), lens, dof, fstop, roll)
    bpy.context.scene["cam_roll"] = roll or 0.0


def remove(*names):
    for n in names:
        root = bpy.data.objects.get(n)
        if root:
            for ob in [root] + list(root.children_recursive):
                bpy.data.objects.remove(ob, do_unlink=True)


# ---------------------------------------------------------------- Monza: where things are
TAB = (11.6, 22.0, 18.0)  # the wreck at rest in the gravel: Hamilton's car at (x, y), heading yaw (deg); far
                          # down the gravel bed, so the cars are still sliding hard through the montage
HAM_X, VER_X = 1.6, 4.0   # lanes on the run to the chicane (Verstappen on the right, toward the sausage kerb)


def tab_M():
    return Matrix.Translation(V((TAB[0], TAB[1], 0))) @ Matrix.Rotation(math.radians(TAB[2]), 4, "Z")


def tab(p):
    """A point given in the wreck's frame (Hamilton's car at the origin, facing +Y) -> world."""
    return tuple(tab_M() @ V(p))


def move_group(ob, M):
    bpy.context.view_layer.update()
    ob.matrix_world = M @ ob.matrix_world
    bpy.context.view_layer.update()


def wreck(ver_lift=0.0, ham_driver=True, at_rest=True):
    """Both cars as they ended up (Verstappen's resting on Hamilton's, real contact), placed in the gravel."""
    h, v = H.monza_cars(ham_driver=ham_driver, ver_lift=ver_lift)
    if at_rest:
        for c in (h, v):
            move_group(c, tab_M())
    return h, v


def ver_relative(ham, ver):
    bpy.context.view_layer.update()
    return ham.matrix_world.inverted() @ ver.matrix_world


def pov_cam(ham, lens=14, look=(0, 6.0, 1.15), roll=0.0):
    """Hamilton's eyes: inside the helmet, looking down the track through the halo's hoop and pillar."""
    M = ham.matrix_world
    cam(tuple(M @ V((0, 0.26, 0.86))), tuple(M @ V(look)), lens, None, 2.8, roll)


def hide_helmet(car):
    for o in [bpy.data.objects.get(car.name + "_head")] + list(bpy.data.objects[car.name + "_head"].children_recursive):
        if o:
            o.hide_render = True


def race_pair(ham_y, ver_dy=2.0):
    h = f1car_block("ham", livery="ham", halo="red")
    h.location = (HAM_X, ham_y, 0)
    v = f1car_block("ver", livery="ver", halo="dark")
    v.location = (VER_X, ham_y + ver_dy, 0)
    return h, v


def launch(key):
    """Verstappen's car rides the sausage kerb, takes off and lands across Hamilton's car. key 'kerb' | 'air' | 'land'."""
    if key == "land":
        return wreck()
    h = f1car_block("ham", livery="ham", halo="red")
    v = f1car_block("ver", livery="ver", halo="dark")
    if key == "kerb":  # right-side wheels up on the yellow kerb, nose rising, already turning in
        h.location, h.rotation_euler = (HAM_X + 0.2, -9.6, 0), (0, 0, math.radians(-4))
        v.location, v.rotation_euler = (H.SAUSAGE[0] - 0.75, H.SAUSAGE[1] + 0.4, 0.22), (math.radians(6), math.radians(-9), math.radians(4))
    else:  # airborne over Hamilton's car, rolled toward it, both sliding toward the gravel
        h.location, h.rotation_euler = (3.6, -4.2, 0), (0, 0, math.radians(14))
        v.location, v.rotation_euler = (4.1, -3.4, 1.55), (math.radians(4), math.radians(-34), math.radians(40))
        ct = H.Contact(v, h)
        while sum(ct.hits()):
            v.location.z += 0.05
    return h, v


# ---------------------------------------------------------------- shot builders
def s01(key):
    def b():
        H.monza_set()
        if key == "a":  # just off the kerb: Verstappen's car lifting, up and to the right of the halo
            h, v = race_pair(-11.0)
            v.location, v.rotation_euler = (VER_X - 0.6, -8.6, 1.0), (math.radians(14), math.radians(-30), math.radians(18))
        else:  # right overhead: its floor and rear tyre coming down toward the halo (the landing attitude, lifted)
            h, v = H.monza_cars(ver_lift=0.9)
            M = Matrix.Translation(V((HAM_X, -9.4, 0))) @ Matrix.Rotation(math.radians(-3), 4, "Z")
            for c in (h, v):
                move_group(c, M)
        hide_helmet(h)
        pov_cam(h, 14, (0.2, 2.2, 3.4) if key == "b" else (0.6, 6.0, 1.6))  # b: eyes up at the car overhead
    return b


def s02():
    H.monza_set()
    h, v = wreck()
    cam(tab((0.85, 1.55, 0.78)), tab((0.0, 0.2, 1.0)), 24, 1.6, 4.0, 4)


def s03():
    H.monza_set()
    race_pair(-30.0, 1.5)
    cam((16.8, -50, 7.0), (3.0, -26, 0.4), 26)  # in front of the stand's roof pillars, above the fence


def s04(key):
    def b():
        H.monza_set()
        launch({"a": "kerb", "b": "air", "c": "land"}[key])
        # one camera position; it pans with the action from the kerb to the gravel
        cam((12.0, -16.0, 2.6), {"a": (4.0, -8.0, 0.7), "b": (4.0, -4.0, 1.1), "c": (TAB[0], TAB[1], 0.8)}[key], 28)
    return b


def s05():
    H.monza_set()
    wreck()
    cam(tab((0.95, 1.3, 1.12)), tab((0.03, 0.3, 1.02)), 38, 1.45, 2.8)


def s06(key):
    def b():
        M = palette()
        if key == "a":  # the car greyed out, its halo glowing
            H.studio_set()
            c = f1car_block("hero", livery="ham", halo="halo_glow")
            c.rotation_euler = (0, 0, math.radians(-30))
            for o in c.children_recursive:
                if o.type == "MESH":
                    for sl in o.material_slots:
                        sl.material = M["ghost"]
            cam((2.6, 2.9, 2.3), (0, 0.1, 0.75), 32)
        else:  # just the halo, turning slowly
            H.halo_alone(spin=40)
            cam((1.5, -2.3, 1.75), (0, -0.05, 1.25), 40)
    return b


def s07():
    """2018: tifosi on the stand's front steps hold up red-X boards and boo; the 2018 car with its halo passes."""
    H.monza_set()
    import random
    rnd = random.Random(3)
    outfits = ["tifoso", "fan_a", "tifoso", "fan_b", "fan_c", "tifoso", "fan_d"]
    k = 0
    for i in range(4):
        z = 1.2 + 0.6 * (i + 1)
        x = 19.2 + (i + 0.5) * 1.1
        for j in range(6):
            y = -21.0 + j * 1.15 + (0.55 if i % 2 else 0)
            if i == 0 and min(abs(y - py) for py in range(-100, 11, 12)) < 0.75:
                continue  # keep clear of the stand's roof pillars (front step)
            pose = "boo" if rnd.random() < 0.25 else "sign"
            f = person_at(f"fan{k}", x, y, 90 + rnd.uniform(-10, 10), pose, outfits[k % len(outfits)], z=z)
            if pose == "sign":
                sg = H.sign(f"sign{k}", "ugly" if k % 2 == 0 else "x")
                H.hold_hand(sg, f, "R", tilt=rnd.uniform(-6, 6))
            k += 1
    c = f1car_block("car2018", livery="w09", halo="red")
    c.location = (5.0, -23.0, 0)
    # over the halo of the car driving past them, up at the stand: the halo big in the foreground, the booing fans
    # with their crossed-out halo signs behind it
    cam((5.9, -24.9, 1.35), (20.6, -18.5, 3.1), 40)


def s08():
    """'And some drivers agreed': in a 2018 garage, two drivers look the halo over - a shrug, a head shake."""
    H.garage_set("navy", car_livery="ver")
    person_at("drvA", -1.35, -1.2, -110, "shrug", "driver_navy")
    person_at("drvB", -1.25, -3.5, -55, "shake", "driver_white")
    person_at("crew1", 3.2, -4.6, 160, "watch", "crew_haas")
    cam((3.4, 1.9, 1.75), (-0.4, -2.2, 1.0), 26)


WOLFF = dict(outfit="boss", scale=1.06)


LAUNCH_W = (1.30, 3.15, 0.48)  # Wolff on the turntable, right behind the new car's cockpit (its far side)
TT_TOP = 0.48


def launch_halo():
    """The launch car's halo centre (world)."""
    bpy.context.view_layer.update()
    return tuple(bpy.data.objects["ln_car"].matrix_world @ V((0, 0.12, 0.86)))


def s09():
    """2018 launch: Wolff right behind the new silver car on its turntable, talking to the room; the car fills the
    foreground diagonally, the LED wall behind."""
    H.launch_set()
    person_at("wolff", *LAUNCH_W[:2], 172, dict(S.POSE["talk"], face="smile"), "boss", z=LAUNCH_W[2], scale=1.06,
              stance=(0.08, -0.06))
    cam((-0.6, -2.6, 2.1), (0.8, 3.0, 1.3), 26)


def photographers(lean=0.0):
    for i, x in enumerate((-2.6, -1.3, 0.3, 2.9)):
        p = person_at(f"photo{i}", x, -2.0 - (i % 2) * 0.5, -10 + i * 6, dict(S.POSE["photo"], lean=lean), "photographer")
        cm = H.press_camera(f"pcam{i}")
        H.hold_mid(cm, p, -10 + i * 6)


def chainsaw_in_hands(person_xyz, rot, scale, saw_local, saw_rot, pose, stance=None):
    """Place the chainsaw where the shot wants it (given relative to the person's first spot), then solve both hands
    onto its grips. If the grips are out of reach, the person steps closer or back along the way they face (never
    a stretched arm)."""
    x, y, z = person_xyz
    Mp = Matrix.Translation(V(person_xyz)) @ Matrix.Rotation(math.radians(rot), 4, "Z")
    cs = H.chainsaw("saw")
    cs.matrix_world = Mp @ Matrix.Translation(V(saw_local)) @ Matrix.Rotation(math.radians(saw_rot[2]), 4, "Z") @ \
        Matrix.Rotation(math.radians(saw_rot[0]), 4, "X")
    bpy.context.view_layer.update()
    grips = {k: tuple(cs.matrix_world @ V(g)) for k, g in H.CHAINSAW_GRIP.items()}
    fwd = V((-math.sin(math.radians(rot)), math.cos(math.radians(rot)), 0))
    last = None
    for d in (0, 0.06, -0.06, 0.12, -0.12, 0.18, -0.18, 0.24, 0.3):
        try:
            p = person_at("wolff", x + fwd.x * d, y + fwd.y * d, rot, pose, "boss", z=z, scale=scale, hands=grips,
                          stance=stance)
            break
        except ValueError as e:
            last = e
    else:
        raise last
    S.register_hold("saw", "wolff", "mid")
    return p, cs


def s10(key):
    def b():
        H.launch_set()
        x, y, z = LAUNCH_W
        if key == "a":  # anticipation: crouched over the case on the turntable behind the car, gripping the saw
            r = math.radians(S10_ROT0)
            fwd = V((-math.sin(r), math.cos(r), 0))
            box("case", (0.9, 0.5, 0.3), tuple(V((x, y, z + 0.15)) + fwd * 0.85), palette()["dark"], rot=(0, 0, r))
            # the saw lies across the case (bar to his left), so both grips are in front of him; his knees stay clear
            chainsaw_in_hands((x, y, z), S10_ROT0, 1.06, (0.12, 0.83, 0.46), (0, 0, -90),
                              dict(crouch=0.36, lean=46, head=(0, 25), face="smile"), stance=(0.12, -0.1))
        else:  # up and aimed at the halo, leaning back, grinning
            chainsaw_in_hands((x, y, z), s10_aim_rot(), 1.06, (0.0, 0.42, 1.12), (12, 0, 0),
                              dict(lean=-8, head=(0, 6), face="open"), stance=(0.25, -0.22))
        cam((-0.9, -2.9, 2.15), (0.75, 2.9, 1.25), 26)
    return b


S10_ROT0 = 30  # shot 10 starts turned to the case behind the car (toward its rear)


def s10_aim_rot():
    hx, hy, _ = launch_halo()
    return math.degrees(math.atan2(-(hx - LAUNCH_W[0]), hy - LAUNCH_W[1]))


def s11(key):
    def b():
        H.press_set(ram=0.25 if key == "a" else 1.0, reading="0t" if key == "a" else "12t")
        cam((-1.1, -5.3, 1.35), (0.0, 0.0, 2.55), 24)  # low, looking up: halo, ram and the load display together
    return b


def s12(key):
    def b():
        H.hangar_set(drop=0.15 if key == "a" else 1.0)
        cam((-6.4, -10.8, 0.9), (0.0, 0.2, 4.0 if key == "a" else 3.0), 22)  # low by the stand, looking up at the bus
    return b


def s13():
    """Bahrain 2020, lap 1 at night: the pack under the floodlights, Grosjean's white car among them."""
    H.bahrain_set()
    c = H.gro_car()
    c.location = (2.2, -14, 0)
    H.car_pack("pk", [("orange", -1.8, -10.5, 0), ("green_it", -2.5, -17.5, 2), ("steelblue", 2.6, -21.5, -2),
                      ("silver", -0.4, -25.5, 0), ("rbred", 3.0, -6.5, 0)])
    cam((-8.4, -40, 6.5), (0.5, -14, 0.5), 26)  # in front of the stand, between two floodlight towers


def s14(key):
    def b():
        H.bahrain_set()
        c = H.gro_car()
        if key == "a":  # flat out, veering right across the track toward the barrier
            c.location, c.rotation_euler = (2.6, -14.0, 0), (0, 0, math.radians(-24))
            H.car_pack("pk", [("orange", -2.2, -9.5, 0), ("green_it", -1.6, -20.5, 2)])
            cam((-2.6, -30.5, 1.1), (3.6, -12.0, 0.6), 32)
        else:  # the instant the nose meets the steel
            c.location, c.rotation_euler = (BX - 2.95, -2.0, 0), (0, 0, math.radians(-62))
            H.car_pack("pk", [("orange", -2.0, 4.5, 0)])
            cam((1.8, -11.5, 1.3), (7.2, -1.7, 0.7), 30)
    return b


BX = H.BARRIER_X


def split_halves(apart=1.0, fire=True):
    """The front half through the torn barrier (halo at the rail line), the back half on the run-off, burning."""
    f = H.gro_car("gro_front", part="front")
    f.rotation_euler = (0, 0, math.radians(-90))
    f.location = (BX - 0.1 + 0.1 * apart, 0.0, 0.0)
    r = H.gro_car("gro_rear", part="rear")
    r.rotation_euler = (0, math.radians(8), math.radians(-90 - 60 * apart))
    r.location = (BX - 1.0 - 2.4 * apart, -0.4 - 2.6 * apart, 0.2)
    M = palette()
    for o in r.children_recursive:
        if o.type == "MESH" and o.material_slots and o.material_slots[0].material == M["white"]:
            o.material_slots[0].material = M["soot"]
    if fire:
        H.fire("bh_fire", tuple(r.location) if apart > 0.5 else (BX - 1.4, -0.9, 0), 1.5 * apart + 0.6, 2.6, 80, 3, 2500)
        H.fire("bh_fire2", (BX - 0.6, -2.2, 0.0), 0.7, 1.3, 30, 5, 1200)
    H.debris("dbr", (BX - 2.5, -1.8), 18, 2.2)
    return f, r


def bent_top_rail():
    """The top rail pushed up over the halo instead of into the helmet: two bent pieces meeting in an arch whose
    underside rests on the hoop, clear of the helmet top (0.98 m)."""
    steel = mat("armco", (0.66, 0.68, 0.7), 0.32, metal=0.9)
    apex = 1.015 + 0.05 + 0.15 + 0.01  # hoop top + tube radius + half the rail's height
    for s in (1, -1):
        a, c = V((BX, s * 1.25, 1.09)), V((BX + 0.1, s * 0.02, apex))
        d = c - a
        ang = math.atan2(-s * d.z, abs(d.y))
        box(f"bent_rail{s}", (0.08, d.length, 0.3), tuple((a + c) / 2), steel, rot=(ang, 0, 0))


def s15(key):
    def b():
        H.bahrain_set(gap=(-1.2, 1.2), top_bent=True)
        split_halves(0.35 if key == "a" else 1.0)
        bent_top_rail()
        cam((2.2, -12.0, 5.2), (7.0, -1.6, 0.6), 26)
    return b


def s16(key):
    def b():
        H.bahrain_set(gap=(-1.2, 1.2), top_bent=True)
        split_halves(1.0)
        bent_top_rail()
        cam((6.25, -1.55, 1.5), (BX + 0.12, 0.0, 0.98), 32, 1.95, 3.2)
    return b


RAIL_TOP = 1.24
CLIMB_Y = 3.0


def climb_scene():
    H.bahrain_set(gap=(-1.2, 1.2), top_bent=True)
    split_halves(1.0)
    bent_top_rail()


def s17_a_person():
    # facing -X, his left is +Y
    # clean pose found by posefind.py climb_a (no clips): upright, gripping over the rail, knee coming up
    p = person_at("gro", BX + 0.42, CLIMB_Y, 90, dict(lean=0, head=(0, -14), face="worried", legL=(50, 4, 95)),
                  "driver_white_h",
                  hands={"L": (BX + 0.02, CLIMB_Y + 0.26, RAIL_TOP + 0.15), "R": (BX + 0.02, CLIMB_Y - 0.26, RAIL_TOP + 0.15)})
    p["foot_free"] = "L"
    return p


def s17(key):
    def b():
        climb_scene()
        if key == "a":  # out of the car on the far side, hands on the top rail, a knee coming up to climb
            s17_a_person()
        elif key == "b":  # astride the top rail, hands on it in front, swinging over
            p = person_at("gro", BX, CLIMB_Y, 0, dict(crouch=0.0, lean=30, head=(-20, -5), face="worried",
                                                       legL=(25, 40, 55), legR=(25, 40, 55)), "driver_white_h",
                          z=RAIL_TOP + 0.09 - ik.LEG,  # the leaning torso's front edge dips ~6 cm below the hips
                          hands={"L": (BX + 0.02, CLIMB_Y + 0.3, RAIL_TOP + 0.11), "R": (BX - 0.02, CLIMB_Y + 0.4, RAIL_TOP + 0.11)})
            p["airborne"] = True
        else:  # down on the track side, led away by a medic, the marshal on the fire
            g = person_at("gro", BX - 1.4, CLIMB_Y - 0.2, 70, dict(S.POSE["walk"], head=(10, 4), face="worried"), "driver_white_h",
                          stance=(0.22, -0.2))
            person_at("medic", BX - 1.35, CLIMB_Y + 0.62, 70, dict(S.POSE["walk"], armL=(70, -10, 40)), "medic", stance=(-0.18, 0.2))
            m = person_at("marshal", BX - 1.6, -0.2, 160, "hose", "marshal")
            ex = H.extinguisher("ext")
            H.hold_mid(ex, m, 160)
            bpy.context.view_layer.update()
            H.foam("foam", ex.matrix_world @ V((0, 0.4, 0.15)), V((0.25, -0.9, -0.35)), 2.2)
        cam((3.8, 7.2, 1.7), (BX - 0.2, CLIMB_Y - 0.4, 1.05), 26)
    return b


def s18():
    """2018: in the garage, Grosjean sizes up the new halo on his car, hand under his chin."""
    H.garage_set("haas")
    x, y, rot = 1.6, -2.9, 58  # beside the cockpit, turned toward the halo
    neck_z = ik.LEG + ik.H
    Mp = Matrix.Translation(V((x, y, 0))) @ Matrix.Rotation(math.radians(rot), 4, "Z")
    chin = tuple(Mp @ V((0.05, 0.21, neck_z - 0.09)))  # under the chin, in front of the chest: touching, not inside
    person_at("gro", x, y, rot, dict(head=(0, 8), face="frown", armR=(10, 10, 20)), "grosjean", hands={"L": chin})
    person_at("crew1", -3.4, -4.4, 150, "watch", "crew_haas")
    cam((3.4, -0.4, 1.7), (1.0, -2.6, 1.2), 28)


def s19():
    H.pedestal_set()
    cam((1.5, -2.7, 2.35), (0, 0, 1.4), 42)


def s20(key):
    def b():
        H.monza_set()
        h, v = wreck(ver_lift=0.32 if key == "a" else 0.0)
        cam(tab((-0.62, 1.05, 0.66)), tab((0.05, 0.1, 1.55)), 18, None, 2.8, 14)
    return b


def s21(key):
    def b():
        H.monza_set()
        h, v = H.monza_cars()
        if key == "b":  # deflected: the wheel rolled off the hoop onto the engine cover, the car slewed round
            v.rotation_euler.z += math.radians(14)
            H.place_point(v, H.REAR_WHEEL, (0.42, -0.65, 0.66 + 0.37 + 0.6))
            H.settle(v, h, drop=1.4)
        for c in (h, v):
            move_group(c, tab_M())
        cam(tab((2.9, 2.9, 3.2)), tab((0.1, 0.0, 0.95)), 28)
    return b


def s22():
    """Hamilton, helmet in hand, by the wreck in the gravel: hand to his neck."""
    H.monza_set()
    wreck()
    x, y = tab((2.3, -1.1, 0))[:2]
    rot = TAB[2] + 200
    neck_z = ik.LEG + ik.H
    Mp = Matrix.Translation(V((x, y, 0))) @ Matrix.Rotation(math.radians(rot), 4, "Z")
    neck = tuple(Mp @ V((-0.27, -0.03, neck_z + 0.03)))
    p = person_at("lewis", x, y, rot, dict(head=(-14, 10), face="worried", armL=(20, 10, 40)), "hamilton",
                  hands={"R": neck})
    hl = props.helmet("lewis_helmet", "yellow", "purple")
    bpy.context.view_layer.update()
    side = Mp.to_3x3() @ V((1, 0, 0))  # his left: the helmet hangs at his side, gripped by its edge
    hl.location = tuple(V(S.hand_world(p, "L")) + side * 0.27 - V((0, 0, 0.2)))
    hl.rotation_euler = (0, 0, math.radians(rot))
    S.register_hold("lewis_helmet", "lewis", "hand", hand="L")
    for i, (dx, dy) in enumerate(((3.6, 1.8), (4.4, 0.6))):  # behind him on the gravel, inside the tyre wall
        mx, my = tab((dx, dy, 0))[:2]
        person_at(f"marshal{i}", mx, my, TAB[2] + 110, "watch", "marshal")
    cam(tab((3.2, -4.2, 1.55)), (x, y, 1.45), 32, 3.3, 3.2)


def s23():
    """In the team's garage on race day: Wolff on the radio, crew at the screens, the car on its stands."""
    H.garage_set("merc", car_livery="ham")
    person_at("wolff", 1.7, -0.6, 22, dict(S.POSE["radio"], face="worried"), "boss_radio", scale=1.06)
    person_at("crew1", -2.2, -4.0, 180, "watch", "crew_merc")
    person_at("crew2", 3.6, -3.6, 110, "talk", "crew_merc")
    cam((0.4, 2.6, 1.75), (1.6, -0.7, 1.55), 30)


def s24():
    """'That boss was Toto Wolff': front on, clear, on the launch stage again - the chainsaw lowered, a grin."""
    H.launch_set()
    chainsaw_in_hands((-1.7, 0.4, 0.4), 180, 1.06, (0.0, 0.36, 1.0), (-45, 0, 0),
                      dict(head=(8, -4), face="smile"))
    cam((-1.35, -2.7, 1.55), (-1.7, 0.4, 1.45), 40, 3.1, 2.8)


def s25(key):
    def b():
        H.monza_set()
        if key == "a":  # braking for the chicane, Verstappen alongside on the right
            h, v = race_pair(-46.0, 1.4)
        else:  # his right-side wheels hitting the sausage kerb, the car starting to lift
            h, v = race_pair(-11.6, 3.0)
            v.location, v.rotation_euler = (H.SAUSAGE[0] - 0.75, H.SAUSAGE[1] + 0.4, 0.22), (math.radians(6), math.radians(-9), math.radians(4))
        hide_helmet(h)
        pov_cam(h, 14, (0.6, 6.0, 1.6))
    return b


SHOTS = [  # n, start, end, keys {label: builder}, description
    (1, 0.00, 2.95, {"a": s01("a"), "b": s01("b")},
     "POV, Hamilton's eyes through the halo (continues from shot 25): Verstappen's car lifts off the kerb on the right and comes over, its floor and rear tyre filling the top of the frame."),
    (2, 2.95, 4.60, {"": s02}, "Low, close on the cockpit: Hamilton's helmet under the halo, Verstappen's car lying right on top of him."),
    (3, 4.60, 6.68, {"": s03}, "Monza: from the tifosi grandstand, the two cars side by side down the straight into the first chicane."),
    (4, 6.68, 9.11, {"a": s04("a"), "b": s04("b"), "c": s04("c")},
     "How it happened: Verstappen's right wheels hit the yellow sausage kerb, the car is launched, lands across Hamilton's, both slide into the gravel."),
    (5, 9.11, 10.68, {"": s05}, "Close: the rear tyre resting on the halo's hoop, a hand's width above the helmet."),
    (6, 10.68, 12.79, {"a": s06("a"), "b": s06("b")},
     "The car fades to grey and the halo glows, then the car is gone: just the halo, turning slowly. 'A curved bar called the halo.'"),
    (7, 12.79, 16.03, {"": s07}, "2018: tifosi on the grandstand steps boo and hold up red-X boards as a car with the new halo passes."),
    (8, 16.03, 17.42, {"": s08}, "In a team garage: two drivers look the halo over - one shrugs, one shakes his head."),
    (9, 17.42, 19.12, {"": s09}, "2018 car launch: Wolff on stage beside the new silver car, talking, a glance at the halo."),
    (10, 19.12, 21.86, {"a": s10("a"), "b": s10("b")},
     "He looks down at the chainsaw in its case, lifts it with its weight, turns and holds it up at the halo with a grin."),
    (11, 21.86, 24.19, {"a": s11("a"), "b": s11("b")}, "The FIA load test: the press comes down on the halo; the readout climbs to 12 t."),
    (12, 24.19, 25.58, {"a": s12("a"), "b": s12("b")}, "In a hangar, a crane lowers a red double-decker bus onto the halo. It holds."),
    (13, 25.58, 27.36, {"": s13}, "Bahrain 2020, lap 1 at night: the pack under the floodlights, Grosjean's white car among them."),
    (14, 27.36, 31.48, {"a": s14("a"), "b": s14("b")}, "Flat out, the white car veers right across the track - and hits the steel barrier."),
    (15, 31.48, 34.44, {"a": s15("a"), "b": s15("b")}, "From above: the car tears in two - the front half through the barrier, the back half spinning away and catching fire."),
    (16, 34.44, 37.83, {"": s16("b")}, "Close: the front half through the barrier; the top rail rides up over the halo instead of into the helmet."),
    (17, 37.83, 40.71, {"a": s17("a"), "b": s17("b"), "c": s17("c")},
     "He climbs out: hands over the top rail and a knee coming up, then astride the barrier, then down on the track side, a medic beside him, a marshal on the fire."),
    (18, 40.71, 42.13, {"": s18}, "2018, in the garage: Grosjean sizes up the new halo, hand under his chin."),
    (19, 42.13, 45.49, {"": s19}, "The halo on a plinth under a spotlight, shown like a trophy."),
    (20, 45.49, 48.91, {"a": s20("a"), "b": s20("b")}, "Back at Monza, from low beside the helmet, tilted: the rear tyre comes down onto the halo."),
    (21, 48.91, 50.43, {"a": s21("a"), "b": s21("b")}, "From above: the tyre on the hoop, then deflected off it onto the engine cover - away from his head."),
    (22, 50.43, 52.62, {"": s22}, "Hamilton, helmet in hand, by the wreck in the gravel: hand to his neck."),
    (23, 52.62, 55.81, {"": s23}, "The team garage on race day: Wolff on the radio, crew at the screens."),
    (24, 55.81, 57.79, {"": s24}, "Back on the launch stage, front on: Wolff, chainsaw lowered, a grin."),
    (25, 57.79, 60.00, {"a": s25("a"), "b": s25("b")},
     "POV again, Hamilton's eyes: braking for the chicane, Verstappen alongside on the right - his wheels hit the yellow kerb. Loops to shot 1."),
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
            setup_render(540, 960, 24, os.path.join(STILLS, f"s{n:02d}{label}.png"))
            try:
                build(b)
            except Exception as e:  # report and carry on with the other frames
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
    out = [dict(n=n, start=t0, end=t1, keys=list(k), desc=d) for n, t0, t1, k, d in SHOTS]
    json.dump(out, open(os.path.join(ROOT, "boards", "shots.json"), "w"), indent=1)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [a for a in sys.argv[1:] if not a.endswith(".py")]
    if args and args[0] == "board":
        board([int(a) for a in args[1:]] or None)
    elif args and args[0] == "json":
        dump_json()
