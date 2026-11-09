"""Sets and props for "Imagine a Formula One car landing on your head" (the halo short), in the blocky style.

Sets: Monza's first chicane (tifosi grandstand and flags, kerbs and sausage kerbs, gravel, tyre walls, catch fence,
hoardings, distance boards, the park's trees), Bahrain at night (floodlights, grandstand, tower, palms, armco),
a team garage (team colours, gantry screens, tyre blankets, tool chests, pit lane outside), a car launch stage
(LED wall, truss, photographers), the FIA load-test press, a hangar with a crane (the bus test), a plinth.
Props are sized for the block people's short arms: everything hand-held has ONE grip point.
Colour: the halo is the film's one accent (red); liveries are generic team colours, no logos.
"""
import math
import random
import bpy
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from lib import V, box, cyl, palette, mat, area, world, cyclorama, group, sun, link, look_at
from props import f1car_block, halo_part, digits, wheel, HALO_R
import dress
from dress import pixmat, _img, _noisy, asphalt, kerb, tree, sky_world, clouds, concrete, data_screen, drawers
from sets import P, POSE, hand_world, hands_mid, register_hold

POSE.update(
    chainsaw=dict(lean=8, armL=(62, 4, 38), armR=(62, 4, 38), legL=(14, 4, 8), legR=(-10, 4, 4), head=(0, 12)),
    sign=dict(armR=(150, 12, 10), armL=(15, 10, 20), head=(0, -6)),
    boo=dict(armR=(160, 14, 5), armL=(150, 14, 10), head=(0, -8), face="open"),
    shrug=dict(armL=(30, 40, 95), armR=(30, 40, 95), head=(12, 6), face="frown"),
    shake=dict(head=(-22, 6), armL=(10, 10, 80), armR=(8, 10, 70), face="frown"),
    chin=dict(head=(14, 8), armL=(55, -25, 110), armR=(8, 12, 20), face="frown"),
    radio=dict(armR=(150, -40, 150), armL=(20, 8, 70), head=(0, 4)),
    photo=dict(armL=(88, -8, 105), armR=(88, -8, 105), head=(0, 4)),
    point=dict(armR=(85, 10, 10), armL=(10, 8, 30), head=(0, 0), face="open"),
    hose=dict(lean=12, armL=(66, 6, 34), armR=(66, 6, 34), legL=(26, 6, 18), legR=(-14, 6, 8), head=(0, 10)),
)


# ---------------------------------------------------------------- materials
def _px(name, w, h, fn, tile=1.0, rough=0.9, emit=0.0):
    return pixmat(name, _img(name, w, h, fn), tile, rough, emit)


def gravel():
    rnd = random.Random(31)
    return _px("gravel", 16, 16, lambda x, y: _noisy((0.74, 0.67, 0.54), 0.3, rnd), 0.5, 0.95)


def grass():
    rnd = random.Random(18)
    return _px("grass", 16, 16, lambda x, y: _noisy((0.3, 0.58, 0.22), 0.25, rnd))


def sand():
    rnd = random.Random(32)
    return _px("sand", 16, 16, lambda x, y: _noisy((0.62, 0.5, 0.34), 0.2, rnd))


def tifosi():
    """Monza crowd: mostly Ferrari red, some white, yellow and green; a darker step every fourth row."""
    rnd = random.Random(40)
    cols = [(0.75, 0.04, 0.03)] * 6 + [(0.92, 0.92, 0.9), (0.9, 0.75, 0.1), (0.05, 0.45, 0.2), (0.1, 0.1, 0.12), (0.8, 0.55, 0.4)]
    return _px("tifosi", 32, 32, lambda x, y: (0.32, 0.32, 0.33) if y % 4 == 3 else cols[rnd.randrange(len(cols))], 2.0)


def crowd_people(height=0.62):
    """A flat crowd 'cut-out': heads and shoulders side by side (skin, hair, caps; Ferrari red shirts mostly) on the
    stand's grey. Cards of it bob up and down: people jumping and cheering, no 3D needed. The image is fitted to a
    card `height` tall (its centre at the object origin), eight people every 4 m along it."""
    rnd = random.Random(42)
    shirts = [(0.75, 0.04, 0.03)] * 5 + [(0.92, 0.92, 0.9), (0.9, 0.75, 0.1), (0.05, 0.45, 0.2), (0.15, 0.3, 0.7)]
    skins = [(0.85, 0.66, 0.5), (0.7, 0.5, 0.36), (0.45, 0.3, 0.2), (0.9, 0.72, 0.58)]
    hair = [(0.12, 0.08, 0.05), (0.3, 0.2, 0.1), (0.75, 0.04, 0.03), (0.9, 0.85, 0.6)]
    figs = [(rnd.choice(shirts), rnd.choice(skins), rnd.choice(hair), rnd.random() < 0.3) for _ in range(8)]
    key = f"px_custom_crowdcard_{height:.2f}"
    if key in bpy.data.materials:
        return bpy.data.materials[key]

    def f(x, y):  # 32 x 16: eight people 4 px wide; y = 0 at the bottom
        sh, sk, hr, arm = figs[x // 4]
        cx = x % 4
        if y <= 8:
            return sh if cx < 4 else (0.3, 0.3, 0.31)
        if 9 <= y <= 11 and 1 <= cx <= 2:
            return sk
        if y == 12 and 1 <= cx <= 2:
            return hr
        if arm and cx == 3 and 9 <= y <= 14:  # an arm up, waving
            return sh
        return (0.32, 0.32, 0.33)
    m = pixmat(f"crowdcard_{height:.2f}", _img("crowdpeople", 32, 16, f), 1.0, 0.85)
    mp = next(n for n in m.node_tree.nodes if n.type == "MAPPING")
    mp.inputs["Scale"].default_value = (1 / 4.0, 1 / 4.0, 1 / height)  # 4 m of people across, one image tall
    mp.inputs["Location"].default_value = (0.0, 0.0, 0.5)              # the image's bottom at the card's bottom
    return m


def crowd_cards(name, x0, y0, y1, side, rows, skip=(), seg=6.0, seed=7):
    """Bobbing crowd cards in front of each riser of a grandstand (and its first row standing at the front),
    in sections that move at their own tempo. skip: [(row_max, ya, yb)] where real 3D fans stand instead."""
    m = crowd_people()
    rnd = random.Random(seed)
    for i in range(rows):
        x = x0 + side * (i + 0.5) * 1.1 - side * 0.6
        z = 1.2 + 0.6 * (i + 1)
        n = int((y1 - y0) / seg)
        for j in range(n):
            ya, yb = y0 + j * seg, y0 + (j + 1) * seg
            if any(i <= r and ya < sb and yb > sa for r, sa, sb in skip):
                continue
            ob = box(f"{name}{i}_{j}", (0.04, seg - 0.05, 0.62), (x, (ya + yb) / 2, z + 0.29), m)
            ob["bob"] = (rnd.uniform(0, 6.28), rnd.uniform(0.04, 0.08), rnd.uniform(1.3, 2.3))


def crowd_night():
    rnd = random.Random(41)
    cols = [(0.9, 0.9, 0.88), (0.75, 0.05, 0.04), (0.1, 0.1, 0.12), (0.15, 0.3, 0.7), (0.8, 0.6, 0.3), (0.6, 0.6, 0.62)]
    return _px("crowd_night", 32, 32, lambda x, y: (0.25, 0.25, 0.26) if y % 4 == 3 else cols[rnd.randrange(len(cols))], 2.0)


def hoarding(seed, base):
    """A trackside board in plain colours with a white pixel band (no text, no logos)."""
    rnd = random.Random(seed)
    def f(x, y):
        if 5 <= y <= 9 and rnd.random() < 0.7 and 2 <= x <= 29:
            return (0.95, 0.95, 0.95)
        return base
    return _px(f"hoard{seed}", 32, 16, f, 4.0, 0.6)


def led_wall():
    """Launch-stage LED wall: a silver-to-teal pixel gradient with a lighter band, glowing."""
    def f(x, y):
        k = y / 15
        c = (0.55 * (1 - k) + 0.0 * k, 0.6 * (1 - k) + 0.62 * k, 0.65 * (1 - k) + 0.55 * k)
        return tuple(min(1, v * (1.3 if 6 <= y <= 8 else 1.0)) for v in c)
    return _px("ledwall", 32, 16, f, 8.0, 0.4, emit=2.2)


# ---------------------------------------------------------------- props
def place_point(ob, local, target):
    """Move a group so that its local point lands on a world target (rotation already set)."""
    bpy.context.view_layer.update()
    ob.location = V(target) - ob.matrix_world.to_3x3() @ V(local)
    bpy.context.view_layer.update()


def chainsaw(name):
    """Origin = between the two grips: the top handle (left hand, local (0, 0.02, 0.14)) and the rear handle
    (right hand, local (0, -0.27, 0.02)). Guide bar forward (+Y)."""
    M = palette()
    p = [box(name + "_body", (0.18, 0.36, 0.22), (0, -0.02, -0.04), M["orange"]),
         box(name + "_engine", (0.16, 0.2, 0.08), (0, -0.04, 0.08), M["dark"]),
         box(name + "_top", (0.2, 0.05, 0.05), (0, 0.02, 0.17), M["dark"]),
         box(name + "_topL", (0.04, 0.05, 0.12), (0.08, 0.02, 0.11), M["dark"]),
         box(name + "_topR", (0.04, 0.05, 0.12), (-0.08, 0.02, 0.11), M["dark"]),
         box(name + "_rear", (0.05, 0.14, 0.05), (0, -0.27, 0.02), M["dark"]),
         box(name + "_bar", (0.035, 0.62, 0.09), (0, 0.47, -0.05), M["steel"]),
         box(name + "_chainT", (0.04, 0.64, 0.015), (0, 0.47, 0.0), M["dark"]),
         box(name + "_chainB", (0.04, 0.64, 0.015), (0, 0.47, -0.1), M["dark"])]
    return group(name, p)


CHAINSAW_GRIP = {"L": (0.0, 0.02, 0.17), "R": (0.0, -0.27, 0.02)}


def press_camera(name):
    """A photographer's camera: body, lens forward (+Y), flash on top. Origin = between the hands."""
    M = palette()
    p = [box(name + "_body", (0.2, 0.1, 0.13), (0, 0.0, 0), M["dark"]),
         box(name + "_lens", (0.1, 0.16, 0.1), (0, 0.12, 0), M["dark"]),
         box(name + "_glass", (0.07, 0.01, 0.07), (0, 0.205, 0), M["chrome"]),
         box(name + "_flash", (0.07, 0.05, 0.07), (0.05, 0.0, 0.1), M["lamp"])]
    return group(name, p)


def extinguisher(name):
    """Origin = between the two hands; nozzle points forward (+Y)."""
    M = palette()
    p = [box(name + "_can", (0.16, 0.16, 0.5), (0, 0.02, -0.12), M["red"]),
         box(name + "_head", (0.08, 0.1, 0.08), (0, 0.02, 0.17), M["dark"]),
         box(name + "_nozzle", (0.05, 0.3, 0.05), (0, 0.22, 0.15), M["dark"])]
    return group(name, p)


def foam(name, start, direction, length=2.0, seed=4):
    """Extinguisher spray: white blocks thickening along a cone."""
    rnd = random.Random(seed)
    m = mat("foam", (0.95, 0.96, 0.98), 0.9, emit=(1, 1, 1), emit_strength=0.4)
    d = V(direction).normalized()
    for i in range(26):
        t = rnd.random() ** 0.8
        c = V(start) + d * (t * length) + V((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * (0.05 + 0.35 * t)
        s = 0.06 + 0.12 * t
        box(f"{name}{i}", (s, s, s), tuple(c), m)


HALO_ICON = ["...........",
             "..HHHHHHH..",
             ".H.......H.",
             ".H...H...H.",
             ".H...H...H.",
             ".H...H...H.",
             ".H...H...H.",
             ".H.......H.",
             "..........."]  # the halo seen from the front: hoop, centre pillar, side mounts


LETTERS = {"U": ["101", "101", "101", "101", "111"], "G": ["111", "100", "101", "101", "111"],
           "L": ["100", "100", "100", "100", "111"], "Y": ["101", "101", "010", "010", "010"]}


def sign(name, kind="x"):
    """A fan's protest board on a short pole, readable from the track (its +Y face, text laid out for a viewer
    there): 'ugly' = UGLY in red pixel letters; 'x' = a big red X; 'halo' = the halo crossed out.
    Origin = grip (in one hand)."""
    M = palette()
    p = [box(name + "_pole", (0.04, 0.04, 0.5), (0, 0, 0.12), M["clay2"])]
    if kind == "ugly":
        px, zc = 0.05, 0.58
        word = "UGLY"
        W = len(word) * 4 - 1
        p.append(box(name + "_card", ((W + 2) * px, 0.02, 7 * px), (0, 0, zc), M["white"]))
        for i, ch in enumerate(word):
            for r, row in enumerate(LETTERS[ch]):
                for c, bit in enumerate(row):
                    if bit == "1":
                        x = -((i * 4 + c) - (W - 1) / 2) * px  # mirrored: reads left to right from the track
                        p.append(box(f"{name}_l{i}{r}{c}", (px, 0.034, px), (x, 0, zc + (2 - r) * px), M["red"]))
        return group(name, p)
    px = 0.05 if kind == "x" else 0.045
    icon = HALO_ICON if kind == "halo" else ["." * 9] * 9
    W, Hh = len(icon[0]), len(icon)
    zc = 0.6
    p.append(box(name + "_card", ((W + 1) * px, 0.02, (Hh + 1) * px), (0, 0, zc), M["white"]))
    for r, row in enumerate(icon):
        for c in range(W):
            x, z = (c - (W - 1) / 2) * px, zc + ((Hh - 1) / 2 - r) * px
            on_x = abs(c - r * (W - 1) / (Hh - 1)) < 0.75 or abs(c - (W - 1 - r * (W - 1) / (Hh - 1))) < 0.75
            if on_x:
                p.append(box(f"{name}_x{r}_{c}", (px, 0.034, px), (x, 0, z), M["red"]))
            elif row[c] == "H":
                p.append(box(f"{name}_h{r}_{c}", (px, 0.028, px), (x, 0, z), M["dark"]))
    return group(name, p)


def flag(name, loc, height=2.2):
    """Italian tricolour on a short pole (the tifosi's flags)."""
    M = palette()
    p = [box(name + "_pole", (0.04, 0.04, height), (0, 0, height / 2), M["clay2"])]
    for i, m in enumerate((M["green_it"], M["white"], M["red"])):
        p.append(box(f"{name}_s{i}", (0.3, 0.02, 0.6), (0.17 + i * 0.3, 0, height - 0.3), m))
    return group(name, p, loc=loc)


def hold_mid(obj, person, yaw, pitch=0.0):
    hm = hands_mid(person)
    obj.rotation_euler = (math.radians(pitch), 0, math.radians(yaw))
    if hm is not None:
        obj.location = hm
    register_hold(obj.name, person.name, "mid")


def hold_hand(obj, person, k="R", tilt=0.0):
    h = hand_world(person, k)
    if h is not None:
        obj.location = h
    obj.rotation_euler = (math.radians(tilt), 0, person.rotation_euler.z)
    register_hold(obj.name, person.name, "hand", hand=k)


def bus(name):
    """Red double-decker, long axis along X (front at +X), body underside at local z = 0.2."""
    M = palette()
    red = mat("busred", (0.72, 0.02, 0.02), 0.55)                     # deep London red, satin (no big hotspot)
    roofred = mat("busroof", (0.55, 0.02, 0.02), 0.5, coat=0.3)
    cream = mat("buscream", (0.93, 0.86, 0.66), 0.5)
    gold = mat("busgold", (0.95, 0.7, 0.15), 0.3, metal=0.6)
    glass = mat("busglass", (0.04, 0.035, 0.03), 0.4, emit=(1.0, 0.75, 0.45), emit_strength=0.12)  # lit inside, no glare
    seat = mat("busseat", (0.12, 0.05, 0.08), 0.8)
    frame = M["clay"]
    L, Wd = 10.4, 2.5
    p = [box(name + "_lower", (L, Wd, 2.0), (0, 0, 1.2), red),
         box(name + "_upper", (L - 0.3, Wd, 1.9), (-0.1, 0, 3.15), red),
         box(name + "_roof", (L - 0.6, Wd - 0.2, 0.14), (-0.1, 0, 4.16), roofred),
         box(name + "_roofedge", (L - 0.4, Wd - 0.06, 0.08), (-0.1, 0, 4.1), roofred),
         box(name + "_band", (L + 0.01, Wd + 0.01, 0.16), (0, 0, 2.22), cream),
         box(name + "_skirt", (L, Wd + 0.02, 0.22), (0, 0, 0.31), M["dark"])]
    for s in (1, -1):
        p.append(box(f"{name}_coach{s}", (L - 0.4, 0.02, 0.04), (0, s * (Wd / 2 + 0.012), 2.05), gold))  # coachline
    for s in (1, -1):  # windows: individual panes with pillars between, two decks; seat backs inside the lit glass
        for deck, z, h in (("lo", 1.55, 0.85), ("up", 3.3, 0.9)):
            n = 7
            for i in range(n):
                x = -L / 2 + 1.0 + i * (L - 2.6) / (n - 1)
                if deck == "lo" and i == n - 1 and s == -1:
                    continue  # the door is there
                p.append(box(f"{name}_w{deck}{s}{i}", (1.05, 0.04, h), (x, s * (Wd / 2 + 0.01), z), glass))
                for k in (-1, 1):  # two seat backs per pane, low in the window
                    p.append(box(f"{name}_seat{deck}{s}{i}{k}", (0.32, 0.045, h * 0.28), (x + k * 0.25, s * (Wd / 2 + 0.012), z - h * 0.32), seat))
        p.append(box(f"{name}_mirror{s}", (0.08, 0.3, 0.25), (L / 2 + 0.15, s * (Wd / 2 + 0.18), 2.0), M["dark"]))
        p.append(box(f"{name}_mirrorarm{s}", (0.3, 0.05, 0.05), (L / 2 + 0.05, s * (Wd / 2 + 0.05), 2.15), M["dark"]))
    # front door ahead of the front axle (two glass leaves, near side -Y), clear of the wheel arch
    for i, x in enumerate((L / 2 - 1.45, L / 2 - 0.75)):
        p.append(box(f"{name}_door{i}", (0.62, 0.04, 1.7), (x, -(Wd / 2 + 0.015), 1.12), glass))
        p.append(box(f"{name}_doorframe{i}", (0.66, 0.035, 1.76), (x, -(Wd / 2 + 0.005), 1.12), M["dark"]))
    # front: split windscreen (flush with each deck's face), destination blind with the route number, headlights,
    # indicators, grille, bumper, number plate
    p.append(box(name + "_wsl", (0.04, Wd - 0.3, 1.25), (L / 2 + 0.01, 0, 1.45), glass))
    p.append(box(name + "_wsu", (0.04, Wd - 0.3, 0.95), (L / 2 - 0.25 + 0.01, 0, 3.25), glass))
    p.append(box(name + "_blind", (0.05, 1.6, 0.3), (L / 2 + 0.02, 0, 2.45), M["dark"]))
    for i in range(5):
        p.append(box(f"{name}_blindtxt{i}", (0.052, 0.12, 0.08), (L / 2 + 0.02, -0.65 + i * 0.24, 2.45), M["yellow"]))
    p.append(box(name + "_route", (0.052, 0.3, 0.2), (L / 2 + 0.02, 0.6, 2.45), M["white"]))
    for s in (1, -1):
        p.append(box(f"{name}_head{s}", (0.05, 0.3, 0.16), (L / 2 + 0.02, s * 0.9, 0.62), M["lamp"]))
        p.append(box(f"{name}_ind{s}", (0.05, 0.12, 0.1), (L / 2 + 0.02, s * 1.12, 0.62), mat("amber", (1, 0.5, 0.0), 0.3, emit=(1, 0.5, 0), emit_strength=4)))
        p.append(box(f"{name}_tail{s}", (0.05, 0.16, 0.4), (-L / 2 - 0.02, s * 1.0, 0.75), mat("taillight", (0.8, 0.02, 0.02), 0.3, emit=(1, 0, 0), emit_strength=2)))
        p.append(box(f"{name}_advert{s}", (6.2, 0.03, 0.55), (-0.6, s * (Wd / 2 + 0.01), 2.55), M["white"]))
        p.append(box(f"{name}_advtxt{s}", (3.2, 0.035, 0.18), (-1.3, s * (Wd / 2 + 0.012), 2.55), M["dark"]))
        p.append(box(f"{name}_vent{s}", (1.2, 0.5, 0.06), (-2.0 + s * 1.8, 0, 4.26), M["grey"]))
    p.append(box(name + "_grille", (0.05, 0.9, 0.2), (L / 2 + 0.02, 0, 0.55), M["dark"]))
    p.append(box(name + "_bumper", (0.14, Wd + 0.04, 0.16), (L / 2 + 0.05, 0, 0.3), M["dark"]))
    p.append(box(name + "_plate", (0.05, 0.5, 0.12), (L / 2 + 0.13, 0, 0.3), M["yellow"]))
    p.append(box(name + "_rearwin", (0.04, Wd - 0.6, 0.8), (-(L - 0.3) / 2 - 0.1 - 0.015, 0, 3.3), glass))
    p.append(box(name + "_rearplate", (0.05, 0.5, 0.12), (-L / 2 - 0.02, 0, 0.6), M["yellow"]))
    p.append(box(name + "_engine", (0.05, 1.6, 0.5), (-L / 2 - 0.02, 0, 1.25), M["grey"]))
    # wheels in arches: the axle 0.5 up so the tyres touch the ground line (local z 0); hubs flush with the side
    for x in (-L / 2 + 2.2, L / 2 - 2.6):
        for s in (1, -1):
            # dark wheel well on the side, the tyre's outer face just proud of it, the hub on the tyre's face
            p.append(box(f"{name}_arch{x:.0f}{s}", (1.25, 0.05, 1.0), (x, s * (Wd / 2 + 0.005), 0.65), M["dark"]))
            w = cyl(f"{name}_wheel{x:.0f}{s}", 0.5, 0.3, (x, s * (Wd / 2 - 0.11), 0.5), M["rubber"], seg=24, rot=(math.pi / 2, 0, 0))
            p.append(w)
            p.append(cyl(f"{name}_hub{x:.0f}{s}", 0.22, 0.04, (x, s * (Wd / 2 + 0.04), 0.5), M["chrome"], seg=16, rot=(math.pi / 2, 0, 0)))
            p.append(box(f"{name}_archtrim{x:.0f}{s}", (1.3, 0.03, 0.06), (x, s * (Wd / 2 + 0.03), 1.13), M["dark"]))
    return group(name, p)


def armco(name, y0, y1, x, gap=None, top_bent=False):
    """Triple steel rail on posts along Y at x (rail tops at 0.5, 0.87, 1.24). gap=(ya, yb): torn open there, the
    ends folded outward (+X); top_bent: the top rail is pushed up and over the gap instead of torn."""
    M = palette()
    steel = mat("armco", (0.66, 0.68, 0.7), 0.32, metal=0.9)
    for y in range(int(y0), int(y1) + 1, 2):
        if gap and gap[0] - 0.3 < y < gap[1] + 0.3:
            continue
        box(f"{name}_post{y}", (0.14, 0.14, 1.3), (x + 0.12, y, 0.65), M["grey"])
    spans = [(y0, y1)] if not gap else [(y0, gap[0]), (gap[1], y1)]
    for k, z in enumerate((0.35, 0.72, 1.09)):
        for a, b in spans:
            box(f"{name}_rail{k}_{a:.0f}", (0.08, b - a, 0.3), (x, (a + b) / 2, z), steel)
        if gap and not (top_bent and k == 2):
            for side, yy in ((-1, gap[0]), (1, gap[1])):
                box(f"{name}_torn{k}{side}", (0.08, 0.7, 0.3), (x + 0.3, yy - side * 0.25, z), steel,
                    rot=(0, 0, math.radians(side * 55)))
    return steel


def fire(name, center, radius=1.2, height=1.6, n=60, seed=1, light=900):
    """Flames as glowing blocks: hot yellow cores, orange bodies, embers low, plus an orange glow light."""
    M = palette()
    rnd = random.Random(seed)
    c = V(center)
    for i in range(n):
        a, r = rnd.uniform(0, 2 * math.pi), radius * rnd.random() ** 0.6
        h = height * (1 - r / (radius + 1e-6)) * rnd.uniform(0.4, 1.0)
        s = rnd.choice([0.09, 0.135, 0.18])
        m = M["fire2"] if r < radius * 0.35 else (M["fire"] if rnd.random() < 0.8 else M["ember"])
        box(f"{name}_f{i}", (s, s, max(s, h)), (c.x + r * math.cos(a), c.y + r * math.sin(a), c.z + max(s, h) / 2), m)
    lt = bpy.data.lights.new(name + "_glow", "POINT")
    lt.energy, lt.color, lt.shadow_soft_size = light, (1.0, 0.45, 0.12), 0.8
    link(bpy.data.objects.new(name + "_glow", lt)).location = (c.x, c.y, c.z + height * 0.6)


def debris(name, center, n=14, spread=2.5, seed=8, colors=("white", "dark", "red")):
    """Broken bodywork: small blocks lying on the ground (they rest on it, not in it)."""
    M = palette()
    rnd = random.Random(seed)
    for i in range(n):
        s = (rnd.choice([0.1, 0.18, 0.25]), rnd.choice([0.1, 0.2, 0.35]), rnd.choice([0.03, 0.05]))
        box(f"{name}{i}", s, (center[0] + rnd.uniform(-spread, spread), center[1] + rnd.uniform(-spread, spread), s[2] / 2),
            M[rnd.choice(colors)], rot=(0, 0, rnd.uniform(0, 3.14)))


# ---------------------------------------------------------------- physical resting contact
def _boxes(group_ob):
    out = []
    for o in group_ob.children_recursive:
        if o.type == "MESH" and len(o.data.vertices) == 8:
            lo = V([min(v.co[i] for v in o.data.vertices) for i in range(3)])
            hi = V([max(v.co[i] for v in o.data.vertices) for i in range(3)])
            M = o.matrix_world
            wc = [M @ V((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
            wlo = V([min(c[i] for c in wc) for i in range(3)])
            whi = V([max(c[i] for c in wc) for i in range(3)])
            out.append((M.inverted(), lo, hi, wlo, whi))
    return out


def _points(group_ob):
    pts = []
    for o in group_ob.children_recursive:
        if o.type == "MESH":
            M = o.matrix_world
            pts += [M @ v.co for v in o.data.vertices]
    return pts


def _tube_bvhs(group_ob):
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for o in group_ob.children_recursive:
        if o.type == "CURVE" and o.get("halo"):
            me = o.evaluated_get(dg).to_mesh()
            M = o.matrix_world
            out.append(BVHTree.FromPolygons([M @ v.co for v in me.vertices], [tuple(p.vertices) for p in me.polygons]))
            o.evaluated_get(dg).to_mesh_clear()
    return out


class Contact:
    """Pre-computed geometry of `base` (its blocks and halo tubes) and `top`'s points in top-local space, so `top`
    can be tested at many trial placements quickly."""

    def __init__(self, top, base):
        bpy.context.view_layer.update()
        self.top = top
        self.boxes, self.tubes = _boxes(base), _tube_bvhs(base)
        inv = top.matrix_world.inverted()
        self.local = [inv @ p for p in _points(top)]
        self.blo = V([min(b[3][i] for b in self.boxes) for i in range(3)])
        self.bhi = V([max(b[4][i] for b in self.boxes) for i in range(3)])

    def hits(self, pad=0.004):
        """(points below the ground, points inside the base car) at top's current placement."""
        bpy.context.view_layer.update()
        M = self.top.matrix_world
        g = c = 0
        for lp in self.local:
            p = M @ lp
            if p.z < -pad:
                g += 1
                continue
            if not all(self.blo[i] - 0.1 < p[i] < self.bhi[i] + 0.1 for i in range(3)):
                continue
            for inv, lo, hi, wlo, whi in self.boxes:
                if not all(wlo[i] < p[i] < whi[i] for i in range(3)):
                    continue
                q = inv @ p
                if all(lo[i] + pad < q[i] < hi[i] - pad for i in range(3)):
                    c += 1
                    break
            else:
                for t in self.tubes:
                    hit = t.find_nearest(p, 0.3)
                    if hit[0] is not None and (p - hit[0]).dot(hit[1]) < -pad:
                        c += 1
                        break
        return g, c


def penetration(top, base, pad=0.004):
    g, c = Contact(top, base).hits(pad)
    return g + c


def settle(top, base, drop=1.5, contact=None):
    """Lower `top` straight down onto `base` (and the ground) to resting contact: the lowest height at which nothing
    intersects (bisection; `top` must start clear). Returns (z, what it rests on: 'ground', 'car' or 'both')."""
    ct = contact or Contact(top, base)
    hi = top.location.z
    lo = hi - drop
    for _ in range(18):
        top.location.z = (lo + hi) / 2
        g, c = ct.hits()
        if g or c:
            lo = top.location.z
        else:
            hi = top.location.z
    top.location.z = hi
    top.location.z = hi - 0.008
    g, c = ct.hits()
    top.location.z = hi
    bpy.context.view_layer.update()
    return hi, ("both" if g and c else "ground" if g else "car" if c else "none")


def lowest_z(group_ob):
    return min(p.z for p in _points(group_ob))


# ---------------------------------------------------------------- the two Monza cars
VER_REST = dict(roll=-8, yaw=72)           # Verstappen's car lying across Hamilton's, nose in the gravel
REAR_WHEEL = (0.78, -1.78, 0.37)          # Verstappen's left-rear wheel (car-local) that lands on the halo
HALO_HIT = (0.06, 0.42, 1.07)             # where on Hamilton's halo it lands (car-local, top of the tube)


def monza_tableau(ham, ver):
    """Rest Verstappen's car across Hamilton's: the rear wheel on the halo, the nose on the ground. The pitch is
    searched so both contacts are real (no floating, no sinking), then the car is settled down onto the halo."""
    lo, hi = -28.0, 0.0
    ct = None
    for _ in range(12):
        pitch = (lo + hi) / 2
        ver.rotation_euler = (math.radians(pitch), math.radians(VER_REST["roll"]), math.radians(VER_REST["yaw"]))
        place_point(ver, REAR_WHEEL, V(HALO_HIT) + V((0, 0, 0.37 + 0.6)))
        ct = ct or Contact(ver, ham)
        z, on = settle(ver, ham, drop=1.4, contact=ct)
        if on == "both":
            break
        if on == "ground":
            lo = pitch  # nose on the gravel, wheel hovering over the halo: less nose-down
        else:
            hi = pitch  # wheel on the halo, nose in the air: more nose-down
    ver["rest_on"] = on
    return ver


def monza_cars(phase="rest", ham_driver=True, ver_lift=0.0):
    """Hamilton's car at the origin facing +Y. phase 'rest': Verstappen's car resting on it (tableau);
    'above': the same attitude, lifted ver_lift metres, still falling onto the halo."""
    h = f1car_block("ham", livery="ham", halo="red", driver=ham_driver)
    v = f1car_block("ver", livery="ver", halo="dark")
    monza_tableau(h, v)
    if ver_lift:
        v.location.z += ver_lift
    return h, v


# ---------------------------------------------------------------- track furniture
def tyre_wall(name, x, y0, y1, face=1):
    M = palette()
    n = int((y1 - y0) / 1.0)
    for i in range(n):
        y = y0 + 0.5 + i
        box(f"{name}{i}", (0.8, 0.98, 1.0), (x, y, 0.5), M["rubber"])
        box(f"{name}_belt{i}", (0.82, 1.0, 0.22), (x, y, 0.62), M["white" if (i // 2) % 2 else "red"])


def catch_fence(name, x, y0, y1, h=4.0):
    M = palette()
    for y in range(int(y0), int(y1) + 1, 4):
        box(f"{name}_post{y}", (0.1, 0.1, h), (x, y, h / 2), M["grey"])
    wire = mat("fence_wire", (0.2, 0.2, 0.22), 0.6)
    for z in (1.4, 2.2, 3.0, 3.8):
        box(f"{name}_wire{z}", (0.03, y1 - y0, 0.03), (x, (y0 + y1) / 2, z), wire)


def hoardings(name, x, y0, y1, seed=0, z=1.2, face=1):
    cols = [(0.75, 0.05, 0.04), (0.92, 0.92, 0.9), (0.05, 0.45, 0.2), (0.9, 0.72, 0.08), (0.1, 0.12, 0.3)]
    n = int((y1 - y0) / 4)
    for i in range(n):
        box(f"{name}{i}", (0.08, 3.9, 0.9), (x, y0 + 2 + i * 4, z), hoarding(seed + i % 5, cols[(seed + i) % 5]))


def grandstand(name, x0, y0, y1, side=1, rows=8, crowd=None, roof=True, nflags=10, seed=1, lit=False):
    """Stepped stand rising away from the track (side=+1: toward +X), crowd texture on the risers, a roof on
    pillars, flags on the top row."""
    M = palette()
    crowd = crowd or tifosi()
    L = y1 - y0
    for i in range(rows):
        x = x0 + side * (i + 0.5) * 1.1
        h = 1.2 + 0.6 * (i + 1)
        box(f"{name}_step{i}", (1.1, L, h), (x, (y0 + y1) / 2, h / 2), concrete(0.7))
        box(f"{name}_crowd{i}", (0.06, L, 0.55), (x - side * 0.56, (y0 + y1) / 2, h - 0.05 + 0.27), crowd)
    xb = x0 + side * (rows * 1.1 + 0.3)
    hb = 1.2 + 0.6 * rows + 4
    box(f"{name}_back", (0.5, L, hb), (xb, (y0 + y1) / 2, hb / 2), concrete(0.62))
    if roof:
        box(f"{name}_roof", (rows * 1.1 + 2, L + 2, 0.3), (x0 + side * (rows * 1.1 / 2), (y0 + y1) / 2, hb + 0.2),
            M["white"])
        for y in range(int(y0), int(y1) + 1, 12):
            box(f"{name}_pillar{y}", (0.4, 0.4, hb), (x0 + side * 0.4, y, hb / 2), M["grey"])
        if lit:
            box(f"{name}_rooflight", (rows * 1.1, L, 0.05), (x0 + side * (rows * 1.1 / 2), (y0 + y1) / 2, hb + 0.03), M["panel"])
    rnd = random.Random(seed)
    for i in range(nflags):
        y = y0 + (i + 0.5) * L / nflags + rnd.uniform(-1, 1)
        xr = x0 + side * (rows - 1.5) * 1.1
        flag(f"{name}_flag{i}", (xr, y, 1.2 + 0.6 * rows), 2.0 + rnd.uniform(0, 0.8))


def distance_board(name, x, y, num):
    M = palette()
    box(name + "_post", (0.12, 0.12, 1.2), (x, y, 0.6), M["grey"])
    box(name + "_board", (0.06, 1.1, 0.8), (x, y, 1.5), M["white"])
    digits(name + "_n", str(num), (x - 0.04, y, 1.5), "-y", "z", 0.09, M["dark"], 0.02)


def marshal_post(name, x, y):
    M = palette()
    box(name + "_hut", (2.2, 2.2, 2.4), (x, y, 1.2), M["white"])
    box(name + "_roof", (2.6, 2.6, 0.2), (x, y, 2.5), M["orange"])
    box(name + "_window", (0.04, 1.6, 0.6), (x - 1.11, y, 1.6), mat("hutglass", (0.08, 0.1, 0.12), 0.1, coat=1))
    box(name + "_flagbox", (0.4, 0.6, 0.6), (x - 1.0, y + 1.4, 0.3), M["yellow"])


def palm(name, x, y, h=6.0):
    trunk = mat("palmtrunk", (0.45, 0.35, 0.22), 0.9)
    leaf = mat("palmleaf", (0.18, 0.42, 0.14), 0.8)
    box(name + "_trunk", (0.4, 0.4, h), (x, y, h / 2), trunk)
    for i in range(6):
        a = i * math.pi / 3
        box(f"{name}_frond{i}", (2.2, 0.5, 0.12), (x + math.cos(a) * 1.0, y + math.sin(a) * 1.0, h - 0.2), leaf,
            rot=(0, math.radians(-18), a))


def floodlight(name, x, y, h=16, face=(0, 0)):
    M = palette()
    box(name + "_pole", (0.45, 0.45, h), (x, y, h / 2), M["grey"])
    box(name + "_frame", (3.0, 0.5, 1.6), (x, y, h + 0.5), M["dark"])
    for i in range(3):
        for j in range(2):
            box(f"{name}_lamp{i}{j}", (0.8, 0.52, 0.6), (x - 1.0 + i, y - 0.01, h + 0.15 + j * 0.7), M["lamp"])


def car_pack(prefix, specs):
    """Other cars in the race (generic liveries): [(livery-ish body colour, x, y, yaw)]."""
    out = []
    for i, (body, x, y, yaw) in enumerate(specs):
        c = f1car_block(f"{prefix}{i}", body=body, halo="dark")
        c.location = (x, y, 0)
        c.rotation_euler = (0, 0, math.radians(yaw))
        out.append(c)
    return out


# ---------------------------------------------------------------- Monza
SAUSAGE = (4.6, -8.0)  # where Verstappen's car hits the yellow sausage kerb (x, y)


def monza_set(trees=True):
    """Monza, the first chicane, seen along the main straight (cars run toward +Y). Track x -6..6.
    Right of the track: kerbs, the sausage kerb, gravel trap, tyre wall, catch fence, the tifosi grandstand.
    Left: kerb, grass, tyre wall, hoardings, distance boards, a smaller stand, the park's trees beyond."""
    M = palette()
    sky_world()
    clouds((0, 40), n=14, z=40, spread=90)
    box("mz_track", (12, 420, 0.1), (0, -60, -0.05), asphalt())
    for s in (1, -1):
        box(f"mz_line{s}", (0.15, 420, 0.012), (s * 5.85, -60, 0.004), M["white"])
    box("mz_kerbR", (1.2, 40, 0.1), (6.6, 0, -0.01), kerb())
    box("mz_kerbL", (1.2, 40, 0.1), (-6.6, 6, -0.01), kerb())
    sk = mat("sausage", (0.95, 0.78, 0.05), 0.5)
    for i in range(6):  # the yellow sausage kerb, in sections
        box(f"mz_sausage{i}", (0.45, 0.9, 0.16), (SAUSAGE[0], SAUSAGE[1] - 2.5 + i * 1.0, 0.08), sk if i % 2 else M["dark"])
    box("mz_gravel", (9, 70, 0.1), (11.7, 0, -0.04), gravel())
    box("mz_grassR", (60, 420, 0.1), (46, -60, -0.07), grass())
    box("mz_runR", (9, 350, 0.1), (11.7, -100, -0.06), grass())
    box("mz_grassL", (60, 420, 0.1), (-36, -60, -0.07), grass())
    box("mz_vergeL", (6, 420, 0.1), (-9, -60, -0.05), grass())
    tyre_wall("mz_tyresR", 16.6, -60, 40)
    tyre_wall("mz_tyresL", -12.4, -80, 40)
    catch_fence("mz_fenceR", 17.4, -120, 60)
    catch_fence("mz_fenceL", -13.2, -120, 60)
    hoardings("mz_boardsR", 16.15, -60, 40, 0, 1.55)
    hoardings("mz_boardsL", -11.95, -80, 40, 3, 1.55)
    for i, (y, n) in enumerate(((-44, 150), (-32, 100), (-20, 50))):
        distance_board(f"mz_dist{i}", -7.6, y, n)
    marshal_post("mz_post", 19.5, 18)
    grandstand("mz_stand", 19.2, -100, 10, 1, rows=10, crowd=tifosi(), nflags=18, seed=2)
    grandstand("mz_stand2", -16, -100, 10, -1, rows=10, crowd=tifosi(), nflags=16, seed=3)
    # the crowd moves: bobbing cut-out cards on every row of both stands (not where shot 7's 3D fans stand), and
    # fans standing along the fences on both sides of the track
    crowd_cards("mz_cc", 19.2, -100, 10, 1, 10, skip=[(4, -24, -10)], seed=7)
    crowd_cards("mz_cc2", -16, -100, 10, -1, 10, seed=8)
    m = crowd_people(0.9)
    legs = mat("crowdlegs", (0.16, 0.16, 0.2), 0.9)
    rnd = random.Random(9)
    for side, x in ((1, 18.4), (-1, -14.4)):
        for j in range(18):
            ya = -100 + j * 6
            if side == 1 and -26 < ya < -8:
                continue  # shot 7's fans stand here; keep the view of them clear
            box(f"mz_ccl{side}_{j}",(0.3, 5.9, 1.25), (x + side * 0.05, ya + 3, 0.625), legs)
            ob = box(f"mz_ccg{side}_{j}", (0.04, 5.9, 0.9), (x, ya + 3, 1.25 + 0.4), m)
            ob["bob"] = (rnd.uniform(0, 6.28), rnd.uniform(0.04, 0.07), rnd.uniform(1.2, 2.0))
    if trees:  # the park: rows of tall trees behind the stands and along the straight
        rnd = random.Random(12)
        for i, y in enumerate(range(-240, 141, 9)):
            for j, x in enumerate((-36, -44, 44, 52)):
                if -75 < y < 15 and x > 0 and j == 2:
                    continue
                tree(f"mz_tree{i}_{j}", x + rnd.uniform(-2, 2), y + rnd.uniform(-2, 2), 7 + rnd.choice([0, 1, 2, 3]), 3 + rnd.choice([0, 0.5, 1]))
    sun("mz_sun", (58, 0, -40), 4.2, 1.2, (1.0, 0.9, 0.75))
    bpy.context.scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.4


# ---------------------------------------------------------------- Bahrain
BARRIER_X = 8.0


def bahrain_set(gap=None, top_bent=False):
    """Sakhir at night. Track along Y (x -6..6), run-off, the armco barrier at x = 8 (gap: torn there), sand,
    floodlight towers, a lit grandstand on the left, the tower and the pit building far off, palm trees, stars."""
    M = palette()
    world(0.05, (0.04, 0.06, 0.13))
    box("bh_track", (12, 400, 0.1), (0, -60, -0.05), asphalt())
    for s in (1, -1):
        box(f"bh_line{s}", (0.15, 400, 0.012), (s * 5.85, -60, 0.004), M["white"])
        box(f"bh_kerb{s}", (0.9, 400, 0.1), (s * 6.4, -60, -0.01), kerb())
    box("bh_runoff", (3, 400, 0.1), (8.4 - 1.0, -60, -0.06), concrete(0.42))
    box("bh_sandR", (80, 400, 0.1), (49, -60, -0.08), sand())
    box("bh_sandL", (80, 400, 0.1), (-47, -60, -0.08), sand())
    armco("bh_armco", -60, 60, BARRIER_X, gap=gap, top_bent=top_bent)
    hoardings("bh_boards", -7.4, -80, 40, 7, 0.6)
    grandstand("bh_stand", -12, -70, 20, -1, rows=8, crowd=crowd_night(), nflags=0, lit=True)
    for i, y in enumerate(range(-120, 61, 22)):
        floodlight(f"bh_fl{i}", -9.5, y, 18)
        floodlight(f"bh_flR{i}", 13, y + 11, 18)
    lamp = M["lamp"]
    tw = mat("tower", (0.85, 0.85, 0.82), 0.6)
    box("bh_tower", (6, 6, 36), (-70, 140, 18), tw)
    box("bh_towertop", (12, 12, 5), (-70, 140, 38), tw)
    for j in range(8):
        box(f"bh_towerwin{j}", (6.05, 6.05, 0.4), (-70, 140, 6 + j * 4), mat("winglow", (1, 0.9, 0.7), 0.3, emit=(1, 0.85, 0.6), emit_strength=3))
    box("bh_pits", (8, 160, 6), (-40, 20, 3), concrete(0.7))
    for j in range(16):
        box(f"bh_pitwin{j}", (8.05, 6, 1.2), (-40, -55 + j * 10, 3.5), mat("winglow", (1, 0.9, 0.7), 0.3))
    rnd = random.Random(5)
    for i in range(18):
        palm(f"bh_palm{i}", rnd.choice([-28, -32, 22, 26, 34]) + rnd.uniform(-2, 2), -110 + i * 11 + rnd.uniform(-3, 3), rnd.uniform(5, 8))
    star = mat("star", (1, 1, 1), 0.5, emit=(1, 1, 1), emit_strength=8)
    for i in range(70):
        a, e = rnd.uniform(0, 2 * math.pi), rnd.uniform(0.25, 1.2)
        d = 300
        box(f"bh_star{i}", (0.6, 0.6, 0.6), (d * math.cos(a) * math.cos(e), d * math.sin(a) * math.cos(e), d * math.sin(e)), star)
    for y in (-140, -100, -60, -20, 20):  # the whole straight is floodlit (shot 14 starts far up it)
        area(f"bh_flood{y}", (2, y, 22), (2, y + 4, 0), 14000, 18, color=(0.95, 0.97, 1.0))
    area("bh_rim", (-14, 10, 8), (5, 0, 1), 3000, 8, color=(0.6, 0.75, 1.0))


def gro_car(name="gro", part=None):
    return f1car_block(name, livery="gro", halo="red", part=part, driver=part != "rear")


# ---------------------------------------------------------------- studio, plinth
def studio_set(dark=False):
    M = palette()
    world(0.15 if dark else 0.6, (0.94, 0.94, 0.95))
    cyclorama(loc=(0, -22, 0), rot=0.0, material=mat("cyc_dark", (0.18, 0.18, 0.19), 0.8) if dark else None)
    if dark:
        sp = bpy.data.lights.new("st_spot", "SPOT")
        sp.energy, sp.spot_size, sp.spot_blend, sp.shadow_soft_size = 4500, math.radians(34), 0.35, 0.3
        so = link(bpy.data.objects.new("st_spot", sp))
        so.location = (0.6, -1.2, 7.0)
        look_at(so, (0, 0.2, 0.6))
        area("st_fill", (-4, -5, 2.5), (0, 0, 0.8), 180, 5)
    else:
        area("st_key", (3, -5, 6), (0, 0, 0.8), 1500, 6)
        area("st_fill", (-4, -3, 2), (0, 0, 0.8), 300, 5)


def pedestal_set():
    """A white plinth under a spotlight: the halo shown like a trophy (round and thick, on its chassis slice)."""
    studio_set(dark=True)
    M = palette()
    box("plinth", (1.0, 1.4, 1.0), (0, 0, 0.5), M["white"])
    box("plinth_cap", (1.1, 1.5, 0.06), (0, 0, 1.03), M["white"])
    h = halo_part("trophy_halo", base=False)  # straight on the platform, no mounting tile
    h.location = (0, -0.25, 1.06 + 0.02)
    h.rotation_euler = (0, 0, math.radians(-25))
    return h


def halo_alone(spin=0.0, glow=False):
    """Just the halo, floating, slowly turning, on a soft neutral background (the 'what is it' shot)."""
    M = palette()
    studio_set()
    h = halo_part("solo_halo", M["halo_glow"] if glow else M["red"], base=False)
    h.location = (0, -0.25, 1.0)
    h.rotation_euler = (0, 0, math.radians(-30 + spin))
    return h


# ---------------------------------------------------------------- team garage
TEAM = {"merc": dict(wall="blackcar", accent="teal", blanket="teal", livery="w09"),
        "haas": dict(wall="dark", accent="red", blanket="dark", livery="gro"),
        "navy": dict(wall="navy", accent="rbred", blanket="navy", livery="ver")}


def garage_set(team="merc", car=True, car_livery=None):
    """A team's garage: car on stands in the middle (nose toward the open front, +Y), team-colour back wall with
    a stripe, gantry of screens and lights overhead, tyre blankets, tool chests, epoxy floor with painted lines,
    the pit lane and the pit-wall stand outside."""
    M = palette()
    T = TEAM[team]
    wall, acc = M[T["wall"]], M[T["accent"]]
    world(0.5, (0.9, 0.92, 0.95))
    sky_world()
    box("gr_floor", (10, 9, 0.1), (0, -1.5, -0.05), concrete(0.8))
    box("gr_lane", (60, 14, 0.1), (0, 10, -0.06), concrete(0.5))
    for x in (-3.0, 3.0):
        box(f"gr_paint{x}", (0.1, 8, 0.01), (x, -1.5, 0.005), M["white"])
    box("gr_back", (10, 0.3, 4.5), (0, -6.1, 2.25), wall)
    box("gr_backstripe", (10, 0.32, 0.4), (0, -6.1, 2.8), acc)
    for s in (1, -1):
        box(f"gr_side{s}", (0.3, 9, 4.5), (s * 5.1, -1.5, 2.25), wall)
        box(f"gr_sidestripe{s}", (0.32, 9, 0.4), (s * 5.1, -1.5, 2.8), acc)
    box("gr_ceiling", (10.6, 9.4, 0.3), (0, -1.5, 4.6), M["clay2"])
    box("gr_header", (10.6, 0.4, 0.8), (0, 3.0, 4.1), wall)
    box("gr_gantry", (8, 0.3, 0.3), (0, -2.0, 3.6), M["grey"])
    for i, x in enumerate((-3, -1, 1, 3)):
        box(f"gr_gscreen{i}", (1.4, 0.06, 0.8), (x, -2.0, 3.05), data_screen())
        box(f"gr_gscreenbk{i}", (1.45, 0.08, 0.85), (x, -1.96, 3.05), M["dark"])
        box(f"gr_light{i}", (1.2, 0.5, 0.05), (x, -3.5, 4.43), M["panel"])
    for i in range(4):  # blanketed tyre sets along the back wall
        x = -4.2 + i * 0.85
        box(f"gr_blanket{i}", (0.75, 0.75, 1.45), (x, -5.4, 0.73), mat(f"blanket_{T['blanket']}", tuple(M[T["blanket"]].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value[:3]), 0.9))
        box(f"gr_blankettop{i}", (0.77, 0.77, 0.06), (x, -5.4, 1.47), M["dark"])
    for i, x in enumerate((1.6, 2.5, 3.4, 4.3)):
        box(f"gr_chest{i}", (0.8, 0.7, 1.1), (x, -5.5, 0.55), drawers(tuple(acc.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value[:3])))
        box(f"gr_chesttop{i}", (0.82, 0.72, 0.04), (x, -5.5, 1.12), M["grey"])
    for i, y in enumerate((-4.0, -2.4)):  # wall screens on the right side
        box(f"gr_wscreen{i}", (0.06, 1.2, 0.7), (4.93, y, 2.0), data_screen())
    # pit wall stand across the lane
    box("gr_pitwall", (40, 0.6, 1.1), (0, 16.5, 0.55), M["white"])
    box("gr_stand", (4, 1.5, 1.0), (0, 15.6, 1.6), M["dark"])
    box("gr_standroof", (4.6, 2.2, 0.15), (0, 15.6, 3.2), wall)
    if car:
        c = f1car_block("gr_car", livery=car_livery or T["livery"], halo="red", driver=False)
        c.location = (0, -2.2, 0.08)
        for y in (2.9 - 2.2, -2.85 - 2.2):  # car stands under the nose and the gearbox
            box(f"gr_carstand{y:.1f}", (0.5, 0.3, 0.08), (0, y, 0.04), M["dark"])
    sun("gr_sun", (55, 0, 160), 3.0, 2.0, (1, 0.95, 0.88))
    area("gr_fill", (0, 1.5, 4.0), (0, -2.5, 0.8), 900, 6)
    area("gr_fill2", (-3, -1, 3.5), (0, -3, 1), 400, 3)


# ---------------------------------------------------------------- car launch stage (2018)
def launch_set():
    """The 2018 car launch: raised stage, the new silver car on a turntable, LED wall, truss with lamps,
    photographers in front of the stage. Camera side is -Y."""
    M = palette()
    world(0.12, (0.5, 0.55, 0.62))
    box("ln_floor", (30, 30, 0.1), (0, 0, -0.05), M["dark"])
    box("ln_stage", (10, 6, 0.4), (0, 2.5, 0.2), M["clay2"])
    box("ln_edge", (10.02, 0.1, 0.12), (0, -0.5, 0.34), M["teal"])
    tt = cyl("ln_turntable", 2.6, 0.08, (0, 2.8, 0.44), M["grey"], seg=48)
    tt["smooth"] = True  # keep its top exactly at 0.48 (people stand on it); voxel steps would poke into shoes
    box("ln_led", (14, 0.3, 11), (0, 6.2, 5.9), led_wall())  # tall: fills the frame behind Wolff and the car
    for s in (1, -1):
        box(f"ln_tower{s}", (0.4, 0.4, 7), (s * 5.6, 0.0, 3.5), M["grey"])
        for j in range(3):
            box(f"ln_spot{s}{j}", (0.35, 0.45, 0.35), (s * 5.3, -0.1, 3.0 + j * 1.4), M["lamp"])
    box("ln_truss", (11.6, 0.4, 0.4), (0, 0.0, 7.0), M["grey"])
    c = f1car_block("ln_car", livery="w09", halo="red", driver=False)
    c.location = (0, 2.8, 0.48)
    c.rotation_euler = (0, 0, math.radians(-150))
    area("ln_key", (2.5, -4, 7), (0, 2.5, 1), 2600, 5, color=(1, 0.97, 0.92))
    area("ln_fill", (-5, -3, 4), (0, 2, 1), 700, 6, color=(0.8, 0.95, 1.0))
    area("ln_back", (0, 5.5, 5), (0, 1.5, 1.2), 1200, 6, color=(0.6, 1.0, 0.95))
    return c


# ---------------------------------------------------------------- the load test
READOUT = (0, -0.476, 4.5)  # centre of the load digits on the press beam's display


def press_set(ram=0.0, reading=""):
    """FIA load test: a steel press frame over the halo on a chassis slice; the ram comes down (ram 0 -> 1 is up ->
    in contact). A screen beside it shows the load."""
    M = palette()
    world(0.5, (0.9, 0.92, 0.95))
    box("lab_floor", (20, 20, 0.1), (0, 0, -0.05), concrete(0.75))
    box("lab_wall", (20, 0.3, 7), (0, 5, 3.5), concrete(0.85))
    for i in range(6):
        box(f"lab_panel{i}", (2.6, 0.32, 2.6), (-7.5 + i * 3, 5, 3.6), M["clay"])
    steel = mat("pressteel", (0.25, 0.42, 0.62), 0.45, metal=0.6)
    for s in (1, -1):
        box(f"pr_col{s}", (0.5, 0.6, 4.4), (s * 1.6, 0, 2.2), steel)
    box("pr_beam", (3.8, 0.8, 0.6), (0, 0, 4.5), steel)
    box("pr_bed", (2.8, 1.8, 0.5), (0, 0, 0.25), steel)
    box("pr_buck", (0.9, 1.6, 0.45), (0, 0.24, 0.72), M["dark"])  # chassis slice the halo is bolted to
    h = halo_part("pr_halo", base=False)
    h.location = (0, 0.0, 0.95)
    top = 0.95 + (1.015 + HALO_R - 0.56)  # top of the hoop
    box("pr_cyl", (0.7, 0.7, 1.3), (0, 0.3, 3.55), M["grey"])
    zr = top + 0.05 + (1.0 - ram) * 1.1  # the pad's underside
    box("pr_rod", (0.25, 0.25, 2.9 - zr), (0, 0.3, (zr + 0.1 + 2.9) / 2), M["chrome"])
    box("pr_pad", (0.6, 0.6, 0.1), (0, 0.3, zr + 0.05), M["dark"])
    # the load readout: a big display on the front of the press beam, facing the camera (-Y)
    box("pr_screenbezel", (1.75, 0.06, 0.8), (0, -0.43, 4.5), M["grey"])
    box("pr_screen", (1.6, 0.06, 0.66), (0, -0.45, 4.5), M["dark"])
    if reading:
        digits("pr_read", reading, READOUT, "x", "z", 0.1, mat("readout", (0.2, 1, 0.4), 0.3, emit=(0.2, 1, 0.4), emit_strength=4), 0.012)
    # bench with the control console and a gauge, beside the rig
    box("pr_bench", (1.4, 0.7, 0.9), (2.9, -0.6, 0.45), M["grey"])
    box("pr_console", (1.0, 0.5, 0.35), (2.9, -0.6, 1.07), data_screen())
    box("pr_hose", (0.08, 1.6, 0.08), (1.95, -0.2, 0.06), M["dark"])
    area("lab_key", (3, -5, 6), (0, 0, 1.5), 1800, 6)
    area("lab_fill", (-4, -3, 3), (0, 0, 1.5), 500, 5)
    return top


def hangar_set(drop=1.0):
    """The bus test as a picture: a hangar, the halo on its chassis slice on a steel stand, a red double-decker
    hanging from the overhead crane (drop 0: high above; 1: resting on the halo)."""
    M = palette()
    world(0.5, (0.9, 0.92, 0.95))
    box("hg_floor", (40, 40, 0.1), (0, 0, -0.05), concrete(0.72))
    box("hg_back", (40, 0.4, 14), (0, 12, 7), concrete(0.82))
    for i in range(7):
        box(f"hg_rib{i}", (0.5, 0.6, 14), (-15 + i * 5, 11.7, 7), M["grey"])
    yellow = M["yellow"]
    for s in (1, -1):
        box(f"hg_rail{s}", (0.6, 30, 0.6), (s * 8, 0, 11.5), yellow)
        for y in (-12, 0, 12):
            box(f"hg_col{s}{y}", (0.6, 0.6, 11.5), (s * 8, y, 5.75), M["grey"])
    box("hg_bridge", (16.6, 1.0, 0.8), (0, 0, 12.2), yellow)
    box("hg_hoist", (1.4, 1.4, 1.0), (0, 0, 11.4), M["dark"])
    box("hg_stand", (1.6, 1.6, 0.9), (0, 0, 0.45), mat("rigsteel", (0.22, 0.23, 0.25), 0.4, metal=0.8))
    box("hg_buck", (0.9, 1.6, 0.45), (0, 0.24, 1.12), M["dark"])
    h = halo_part("hg_halo", base=False)
    h.location = (0, 0.0, 1.35)
    top = 1.35 + (1.015 + HALO_R - 0.56)
    b = bus("hg_bus")
    rest_z = top - 0.2  # body underside (local 0.2) on the halo's top
    b.location = (0.0, 0.2, rest_z + (1.0 - drop) * 4.5)
    bz = b.location.z
    box("hg_spreader", (6, 0.3, 0.3), (0, 0.2, bz + 4.4 + 1.6), yellow)
    for x in (-2.8, 2.8):  # cables: spreader to the bus roof, hoist to spreader
        box(f"hg_cable{x}", (0.05, 0.05, 1.5), (x, 0.2, bz + 4.25 + 0.75), M["dark"])
    box("hg_cablemain", (0.06, 0.06, 10.9 - (bz + 6.0)), (0, 0.2, (10.9 + bz + 6.0) / 2), M["dark"])
    area("hg_key", (6, -12, 12), (0, 0, 2), 6000, 10)
    area("hg_fill", (-8, -8, 5), (0, 0, 2), 1500, 8)
    return top


# ---------------------------------------------------------------- people helpers
def person_at(name, x, y, rot, pose, outfit, z=0.0, scale=1.0, hands=None, feet=None, stance=None):
    """A block person, optionally with hands/feet solved onto world points (ik.reach) so contacts are exact.
    stance=(left, right): both feet planted flat on the floor at z, each this far ahead (+) / behind (-) the hips
    (a step or a braced stance with no floating foot)."""
    import ik
    from sets import POSE as _P
    p = dict(_P[pose]) if isinstance(pose, str) else dict(pose)
    if stance:
        # a straight leg can't also step: drop the hips just enough for the longer of the two steps (+1.5 cm)
        reach_ = 17 * 0.045
        d = max(abs(stance[0]), abs(stance[1])) + 0.05
        p["crouch"] = max(p.get("crouch", 0.0), reach_ - math.sqrt(max(0.0, reach_ ** 2 - d * d)) + 0.015)
        Mp = Matrix.Translation(V((x, y, z))) @ Matrix.Rotation(math.radians(rot), 4, "Z")
        ankle = 2 * 0.045 * scale  # the shoe is 2 px tall under the ankle
        feet = dict(feet or {})
        for k, s, d in (("L", 1, stance[0]), ("R", -1, stance[1])):
            feet.setdefault(k, tuple(Mp @ V((s * 0.1 * scale, d - 0.045 * scale, ankle))))
    if hands or feet:
        try:
            p = ik.reach(p, (x, y, z), rot, hands=hands, feet=feet, scale=scale)
        except ValueError as e:  # storyboard: keep going with the closest pose, and say so (fix by moving the person)
            print(f"REACH {name}: {e}", flush=True)
            p = ik.reach(p, (x, y, z), rot, hands=hands, feet=feet, scale=scale, tol=9.0)
    from people import person
    r = person(name, (x, y, z), rot, p, outfit, scale=scale)
    r["pose_name"] = pose if isinstance(pose, str) else "custom"
    return r
