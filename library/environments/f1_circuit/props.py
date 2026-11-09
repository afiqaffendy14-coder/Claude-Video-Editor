"""Prototype props for the circuit, all blocky. Each is built once and then instanced (blocks.scatter) or linked.

Convention for every prototype: origin on the ground at the centre of its footprint, local +X along its length
(the barrier/line direction), local +Y = its front (toward the track or the viewer), +Z up. Lengths are in metres;
the block character is 1.44 m tall (1 skin px = 4.5 cm), the F1 car 5.6 m long.
"""
import math
import numpy as np
import blocks as B
from blocks import MeshBuilder as MB
import plan as P

_M = {}


def M(name):
    """Shared materials by name."""
    if name in _M:
        return _M[name]
    spec = {
        "concrete": ("#CFCFC8", "concrete", 0.85), "concrete_dark": ("#8E8E88", "concrete", 0.9),
        "wall_white": ("#ECECE6", "concrete", 0.7), "wall_red": ("#C21F1A", "concrete", 0.7),
        "steel": ("#8C9096", "metal", 0.45, 0.8), "steel_dark": ("#3C3F44", "metal", 0.5, 0.7),
        "galv": ("#B4B8BC", "metal", 0.35, 0.9), "rubber": ("#1D1D1F", "tread", 0.9),
        "belt_red": ("#C21F1A", "noise", 0.7), "belt_white": ("#E8E8E2", "noise", 0.7),
        "belt_blue": ("#1F4FA0", "noise", 0.7), "yellow": ("#F2C200", "noise", 0.6),
        "orange": ("#E8742A", "noise", 0.7), "white": ("#F0F0EC", "noise", 0.6), "black": ("#18181A", "noise", 0.6),
        "glass": ("#2C4A60", "glass", 0.08, 0.2), "glass_dark": ("#1A2733", "glass", 0.1, 0.2),
        "grey": ("#7A7C80", "noise", 0.7), "dark": ("#2A2B2E", "noise", 0.7), "wood": ("#9A7048", "bark", 0.85),
        "bark": ("#6B4A2E", "bark", 0.95), "birch": ("#E2DDD0", "bark", 0.9), "leaves": ("#3E7F2E", "leaves", 0.9),
        "leaves_dark": ("#2E6324", "leaves", 0.9), "leaves_light": ("#5E9B3A", "leaves", 0.9),
        "pine": ("#25502A", "leaves", 0.9), "hedge": ("#356E2A", "leaves", 0.95),
        "lamp": ("#FFF6DC", "flat", 0.3, 0.0, 6.0), "lamp_off": ("#E8E6DA", "flat", 0.3),
        "red_light": ("#FF2A1A", "flat", 0.3, 0.0, 4.0), "green_light": ("#3AFF5A", "flat", 0.3, 0.0, 4.0),
        "amber_light": ("#FFB000", "flat", 0.3, 0.0, 4.0), "blue_light": ("#2A6BFF", "flat", 0.3, 0.0, 4.0),
        "led_off": ("#101114", "led", 0.4), "tyre_side": ("#1E1E20", "tread", 0.9), "canvas": ("#F4F2EA", "noise", 0.9),
        "seat_grey": ("#55595F", "noise", 0.6), "floor_epoxy": ("#5C5F66", "noise", 0.35),
        "roof": ("#E6E6E2", "metal", 0.5, 0.3), "brick": ("#9A5A42", "tile", 0.9), "skin1": ("#E0B394", "flat", 0.7),
        "jeans": ("#2F4A78", "noise", 0.8), "trousers": ("#2A2A2E", "noise", 0.8), "khaki": ("#9E8A62", "noise", 0.8),
        "hair_dark": ("#2B1D14", "noise", 0.9), "hair_brown": ("#6A4428", "noise", 0.9),
        "hair_blond": ("#D9B65E", "noise", 0.9), "red": ("#C8102E", "noise", 0.6), "green": ("#1E7A3C", "noise", 0.6),
        "blue": ("#1F4E9C", "noise", 0.6), "car_glass": ("#1C2630", "glass", 0.05, 0.3),
        "chrome": ("#D8DCE0", "metal", 0.15, 1.0), "tarmac_line": ("#EDEDE8", "flat", 0.6),
    }[name]
    col, kind, rough = spec[:3]
    metal = spec[3] if len(spec) > 3 else 0.0
    emit = spec[4] if len(spec) > 4 else 0.0
    _M[name] = B.material(name, col, kind, rough, metal, emit)
    return _M[name]


def team_mat(i, which="main"):
    key, name, main, acc = P.TEAMS[i]
    col = main if which == "main" else acc
    return B.material(f"team_{key}_{which}", col, "noise", 0.5)


def colour_mat(hexcol, kind="noise", rough=0.6, emit=0.0):
    return B.material("col_" + hexcol.lstrip("#") + ("_e" if emit else "") + ("" if kind == "noise" else "_" + kind),
                      hexcol, kind, rough, 0.0, emit)


def sign_mat(name, text, w, h, bg, fg, emit=0.0, border=None, scale=None):
    return B.image_material("sign_" + name, B.sign_image(text, w, h, bg, fg, scale=scale, border=border), 0.6, emit)


def fence_mat():
    return B.material("fence_wire", "#9AA0A6", "mesh", 0.5, 0.7, alpha=B.wire_alpha())


# ================================================================ barriers
def concrete_wall():
    """2 m concrete wall chunk, 1.1 m high, stepped (blocky Jersey) profile. v0 white, v1 red/white."""
    for v, face in enumerate(("wall_white", "wall_red")):
        b = MB()
        b.box((0, 0, 0.175), (2.0, 0.7, 0.35), M("concrete"))
        b.box((0, 0, 0.725), (2.0, 0.45, 0.75), M(face), faces={"-y": M("concrete")})
        b.box((0, 0, 1.125), (2.0, 0.5, 0.05), M("concrete_dark"))
        B.proto("concrete_wall", b, v)


def debris_fence():
    """4 m debris fence panel standing on a wall top (origin = wall top): posts, wire panel, cables, angled catch
    panel leaning toward the track (+Y)."""
    b = MB()
    fm = fence_mat()
    b.box((-2.0 + 0.08, 0, 2.0), (0.16, 0.16, 4.0), M("galv"))
    # brace leaning back from the post
    b.box((-2.0 + 0.08, -0.55, 1.2), (0.1, 0.1, 2.6), M("galv"), rot=(math.radians(-25), 0, 0))
    b.box((0, 0.0, 1.8), (4.0, 0.02, 3.6), fm)
    for z in (0.3, 1.6, 2.9):
        b.box((0, 0.03, z), (4.0, 0.03, 0.03), M("steel_dark"))
    b.box((0, 0.32, 3.95), (4.0, 0.02, 0.8), fm, rot=(math.radians(-45), 0, 0))
    b.box((-2.0 + 0.08, 0.3, 3.95), (0.1, 0.1, 0.9), M("galv"), rot=(math.radians(-45), 0, 0))
    B.proto("debris_fence", b, 0)


def armco():
    """4 m triple-rail armco on posts (rails face +Y)."""
    b = MB()
    b.box((-1.9, -0.05, 0.55), (0.12, 0.18, 1.1), M("galv"))
    for z in (0.35, 0.65, 0.95):
        b.box((0, 0.08, z), (4.0, 0.06, 0.26), M("galv"))
        b.box((0, 0.13, z), (4.0, 0.04, 0.1), M("galv"))
    B.proto("armco", b, 0)


def tyre_wall():
    """2 m tyre barrier module: 3 rows of tyre stacks bolted together behind a conveyor belt.
    v0 red belt, v1 white belt, v2 blue belt (alternate along the run)."""
    top = B.image_material("tyre_top", _tyre_top_img())
    for v, belt in enumerate(("belt_red", "belt_white", "belt_blue")):
        b = MB()
        for row in range(3):
            for k in range(3):
                x = -0.66 + k * 0.66
                y = 0.55 - row * 0.62
                b.box((x, y, 0.5), (0.62, 0.6, 1.0), M("tyre_side"), faces={"+z": top}, uvfit=("+z",))
        b.box((0, 0.88, 0.52), (2.0, 0.04, 0.96), M(belt))
        B.proto("tyre_wall", b, v)


def _tyre_top_img():
    img = np.full((10, 10, 3), 0.11, np.float32)
    yy, xx = np.mgrid[:10, :10]
    r = np.hypot(xx - 4.5, yy - 4.5)
    img[r < 2.2] = 0.03
    img[(r > 3.6) & (r < 4.6)] *= 1.5
    return img


def gate():
    """4 m service gate in a wall line: two posts and a wire gate (closed), a small 'SERVICE' plate."""
    b = MB()
    for x in (-1.95, 1.95):
        b.box((x, 0, 1.4), (0.18, 0.18, 2.8), M("galv"))
    b.box((0, 0, 1.3), (3.7, 0.04, 2.2), fence_mat())
    b.box((0, 0, 0.25), (3.7, 0.06, 0.06), M("galv"))
    b.box((0, 0, 2.4), (3.7, 0.06, 0.06), M("galv"))
    b.box((0, 0.04, 1.6), (0.9, 0.02, 0.3), sign_mat("service", "SERVICE", 0.9, 0.3, "#1F4E9C", "#FFFFFF"),
          uvfit=("+y",))
    B.proto("gate", b, 0)


def sausage_kerb():
    b = MB()
    for k in range(3):
        b.box((-0.5 + k * 0.5, 0, 0.06), (0.46, 0.5, 0.12), M("yellow"))
        b.box((-0.5 + k * 0.5, 0, 0.15), (0.3, 0.3, 0.06), M("yellow"))
    B.proto("sausage_kerb", b, 0)


# ================================================================ trackside furniture
def fence_banner():
    """6 m sponsor banner fixed to the debris fence (origin = wall top), one variant per sponsor."""
    for v, (text, bg, fg) in enumerate(P.SPONSORS):
        b = MB()
        mt = sign_mat(f"banner_{v}", text, 6.0, 1.2, bg, fg)
        b.box((0, 0.13, 0.95), (5.9, 0.02, 1.2), M("canvas"), faces={"+y": mt}, uvfit=("+y",))
        B.proto("fence_banner", b, v)


def led_board():
    """6 m digital LED advertising panel on the wall top (origin = wall top). Emissive sponsor content."""
    for v, (text, bg, fg) in enumerate(P.SPONSORS):
        b = MB()
        img = B.sign_image(text, 6.0, 0.8, bg, fg)
        img[1::2, :] *= 0.8
        mt = B.image_material(f"led_{v}", img, 0.4, emit=1.6)
        b.box((0, 0.05, 0.5), (6.0, 0.25, 0.9), M("black"), faces={"+y": mt}, uvfit=("+y",))
        b.box((0, -0.05, 0.03), (6.0, 0.4, 0.06), M("steel_dark"))
        B.proto("led_board", b, v)


def ad_board():
    """Free-standing 6 x 1 m advertising board on legs (for verges and inside corners)."""
    for v, (text, bg, fg) in enumerate(P.SPONSORS):
        b = MB()
        mt = sign_mat(f"board_{v}", text, 6.0, 1.0, bg, fg)
        b.box((0, 0, 0.8), (6.0, 0.12, 1.0), M("steel_dark"), faces={"+y": mt}, uvfit=("+y",))
        for x in (-2.6, 2.6):
            b.box((x, -0.1, 0.25), (0.1, 0.4, 0.5), M("steel_dark"))
        B.proto("ad_board", b, v)


def big_sign():
    """Big trackside billboard on two posts (6 m up), sponsor variants, for the outsides of corners."""
    for v, (text, bg, fg) in enumerate(P.SPONSORS):
        b = MB()
        mt = sign_mat(f"bill_{v}", text, 12.0, 3.0, bg, fg)
        b.box((0, 0, 7.5), (12.0, 0.3, 3.0), M("steel_dark"), faces={"+y": mt}, uvfit=("+y",))
        for x in (-4.0, 4.0):
            b.box((x, -0.2, 3.0), (0.4, 0.4, 6.0), M("steel"))
        B.proto("big_sign", b, v)


def distance_board():
    """Braking marker boards: v0 300, v1 200, v2 100 (white board, black numbers, on a post)."""
    for v, n in enumerate(("300", "200", "100")):
        b = MB()
        mt = sign_mat(f"dist_{n}", n, 1.6, 1.1, "#F4F4F0", "#111111", border="#111111")
        b.box((0, 0, 1.55), (1.6, 0.1, 1.1), M("white"), faces={"+y": mt, "-y": mt}, uvfit=("+y", "-y"))
        b.box((0, -0.12, 0.6), (0.14, 0.14, 1.2), M("steel"))
        B.proto("distance_board", b, v)


def drs_board():
    """v0 'DRS' activation board, v1 'DRS DETECT' board."""
    for v, txt in enumerate(("DRS", "DETECT")):
        b = MB()
        mt = sign_mat(f"drs_{v}", txt, 1.8, 1.0, "#1F4E9C" if v == 0 else "#F4F4F0", "#FFFFFF" if v == 0 else "#1F4E9C",
                      border="#FFFFFF")
        b.box((0, 0, 1.6), (1.8, 0.1, 1.0), M("white"), faces={"+y": mt, "-y": mt}, uvfit=("+y", "-y"))
        b.box((0, -0.12, 0.6), (0.14, 0.14, 1.2), M("steel"))
        B.proto("drs_board", b, v)


def pit_signs():
    """v0 'PIT 80' limit sign, v1 'PIT IN', v2 'PIT OUT', v3 'END 80'."""
    for v, (txt, bg, fg) in enumerate((("80", "#FFFFFF", "#111111"), ("PIT IN", "#1F4E9C", "#FFFFFF"),
                                        ("PIT OUT", "#1F4E9C", "#FFFFFF"), ("END 80", "#FFFFFF", "#111111"))):
        b = MB()
        mt = sign_mat(f"pit_{v}", txt, 1.4, 1.0, bg, fg, border="#C8102E" if v in (0, 3) else "#FFFFFF")
        b.box((0, 0, 2.2), (1.4, 0.1, 1.0), M("white"), faces={"+y": mt}, uvfit=("+y",))
        b.box((0, -0.1, 0.9), (0.14, 0.14, 1.8), M("steel"))
        B.proto("pit_sign", b, v)


def pit_exit_light():
    """Pit exit traffic light: v0 green, v1 red (lit)."""
    for v, lit in enumerate(("green_light", "red_light")):
        b = MB()
        b.box((0, 0, 1.4), (0.18, 0.18, 2.8), M("steel_dark"))
        b.box((0, 0.05, 3.2), (0.5, 0.3, 1.0), M("black"))
        b.box((0, 0.21, 3.45), (0.28, 0.04, 0.28), M("red_light" if v == 1 else "led_off"))
        b.box((0, 0.21, 2.95), (0.28, 0.04, 0.28), M("green_light" if v == 0 else "led_off"))
        B.proto("pit_exit_light", b, v)


def track_camera():
    """TV camera position: v0 on a 3 m scaffold platform with an umbrella, v1 on a ground tripod behind the fence."""
    for v in range(2):
        b = MB()
        h = 3.0 if v == 0 else 0.0
        if v == 0:
            for x in (-0.9, 0.9):
                for y in (-0.9, 0.9):
                    b.box((x, y, 1.5), (0.08, 0.08, 3.0), M("galv"))
            for z in (1.0, 2.0):
                b.box((0, 0.9, z), (1.9, 0.06, 0.06), M("galv"))
                b.box((0, -0.9, z), (1.9, 0.06, 0.06), M("galv"))
            b.box((0, 0, 3.0), (2.0, 2.0, 0.1), M("wood"))
            b.box((0, 0.98, 3.5), (2.0, 0.05, 0.05), M("galv"))
            b.box((0.7, -0.5, 4.6), (0.06, 0.06, 3.2), M("steel"))
            b.box((0.7, -0.5, 6.2), (2.4, 2.4, 0.15), M("orange"))
        for a in (0, 2.1, 4.2):
            b.box((0.25 * math.sin(a), 0.25 * math.cos(a), h + 0.6), (0.05, 0.05, 1.2), M("dark"))
        b.box((0, 0, h + 1.35), (0.3, 0.6, 0.35), M("dark"))
        b.box((0, 0.5, h + 1.4), (0.2, 0.5, 0.2), M("black"))
        b.box((0, 0.76, h + 1.4), (0.16, 0.02, 0.16), M("glass"))
        B.proto("track_camera", b, v)


def cctv():
    b = MB()
    b.box((0, 0, 3.5), (0.16, 0.16, 7.0), M("steel"))
    b.box((0, 0.25, 7.0), (0.12, 0.5, 0.12), M("steel"))
    b.box((0, 0.5, 6.8), (0.25, 0.4, 0.25), M("white"))
    b.box((0, 0.71, 6.8), (0.15, 0.02, 0.15), M("glass_dark"))
    B.proto("cctv", b, 0)


def floodlight():
    """22 m floodlight mast with a lamp bank facing +Y (the track)."""
    b = MB()
    b.box((0, 0, 11.0), (0.7, 0.7, 22.0), M("galv"))
    b.box((0, 0, 0.4), (1.4, 1.4, 0.8), M("concrete"))
    b.box((0, 0.2, 22.8), (5.0, 0.4, 2.2), M("steel_dark"))
    for i in range(5):
        for j in range(2):
            b.box((-2.0 + i, 0.45, 22.3 + j * 1.0), (0.8, 0.12, 0.8), M("lamp"), rot=(math.radians(-20), 0, 0))
    B.proto("floodlight", b, 0)


def street_light():
    b = MB()
    b.box((0, 0, 4.0), (0.16, 0.16, 8.0), M("steel_dark"))
    b.box((0, 0.6, 7.95), (0.14, 1.3, 0.14), M("steel_dark"))
    b.box((0, 1.15, 7.85), (0.35, 0.5, 0.12), M("lamp"))
    B.proto("street_light", b, 0)


def flag_pole():
    """10 m flag poles with flags in sponsor/team colours (variants)."""
    cols = ["#C8102E", "#1F4E9C", "#F2C200", "#00843D", "#FFFFFF", "#111111", "#E85D04", "#6A1B9A"]
    for v, c in enumerate(cols):
        b = MB()
        b.box((0, 0, 5.0), (0.12, 0.12, 10.0), M("white"))
        b.box((0.9, 0, 9.2), (1.6, 0.04, 1.1), colour_mat(c))
        b.box((0.9, 0, 9.2), (1.6, 0.05, 0.25), colour_mat(cols[(v + 3) % len(cols)]))
        B.proto("flag_pole", b, v)


def marshal_post():
    """Marshal post hut behind the barrier, facing +Y: platform, roof, window, steps, extinguishers.
    The flag light panel is a separate object (see circuit_blender) so its colour can be animated."""
    b = MB()
    b.box((0, 0, 0.5), (3.0, 2.6, 1.0), M("concrete"))
    b.box((0, -0.3, 1.0 + 1.2), (3.0, 2.0, 2.4), M("white"), faces={"+y": M("white")})
    b.box((0, 0.71, 2.6), (2.6, 0.04, 0.9), M("glass"))
    b.box((0, 0.2, 3.5), (3.6, 3.0, 0.2), M("orange"))
    b.box((1.2, 1.24, 1.55), (0.06, 0.06, 1.1), M("galv"))
    b.box((-1.2, 1.24, 1.55), (0.06, 0.06, 1.1), M("galv"))
    b.box((0, 1.24, 2.1), (2.5, 0.06, 0.06), M("galv"))
    for k in range(4):   # steps on the side
        b.box((1.85, -0.6 + k * 0.0, 0.125 + k * 0.25), (0.7, 0.9, 0.25), M("concrete_dark"))
    for x in (-1.1, -0.8):   # extinguishers
        b.box((x, 1.12, 1.25), (0.2, 0.2, 0.5), M("red"))
        b.box((x, 1.12, 1.55), (0.08, 0.08, 0.1), M("black"))
    b.box((0, -1.32, 2.0), (1.0, 0.04, 2.0), M("grey"))   # door at the back
    B.proto("marshal_post", b, 0)


def flag_panel_mesh(mat):
    """Digital marshalling light panel on a post (separate object per post; `mat` reads the flag colour)."""
    b = MB()
    b.box((0, 0, 1.6), (0.14, 0.14, 3.2), M("steel_dark"))
    b.box((0, 0.1, 3.4), (1.1, 0.15, 0.8), M("black"))
    b.box((0, 0.18, 3.4), (0.95, 0.02, 0.65), mat, uvfit=("+y",))
    return b


def fire_point():
    """Trackside fire point: red cabinet with extinguishers and a hose reel."""
    b = MB()
    b.box((0, 0, 0.8), (1.0, 0.5, 1.6), M("red"))
    b.box((0, 0.26, 1.0), (0.8, 0.02, 1.0), sign_mat("fire", "FIRE", 0.8, 1.0, "#C8102E", "#FFFFFF"), uvfit=("+y",))
    for x in (-0.75, 0.75):
        b.box((x, 0.1, 0.3), (0.22, 0.22, 0.6), M("red"))
    B.proto("fire_point", b, 0)


# ================================================================ people (block character proportions, 4.5 cm px)
SKINS = ["#F1C7A5", "#E0B394", "#C68E68", "#9C6A45", "#6E4A31", "#4A3022"]
HAIRS = ["hair_dark", "hair_brown", "hair_blond", "hair_dark", "black"]
SHIRTS = ["#C8102E", "#1F4E9C", "#FFFFFF", "#F2C200", "#00843D", "#FF8000", "#111111", "#6A1B9A", "#00A19B",
          "#E85D9A", "#8A5A2B", "#7FD1FF"]
PANTS = ["jeans", "trousers", "khaki"]


def _face_img(skin):
    img = np.broadcast_to(B.hexrgb(skin), (8, 8, 3)).copy()
    img[3, 1:3] = (0.95, 0.95, 0.95)
    img[3, 5:7] = (0.95, 0.95, 0.95)
    img[3, 2] = (0.15, 0.2, 0.35)
    img[3, 5] = (0.15, 0.2, 0.35)
    img[6, 3:5] = B.hexrgb(skin) * 0.7
    img[0:2, :] = (0.17, 0.12, 0.08)
    return img


def person(b, pose, skin, hair, shirt, pants, cap=None, off=(0, 0, 0)):
    """Add a block person to builder b. pose: 'sit' (on a seat at z 0.5), 'stand', 'cheer'."""
    px = 0.045
    o = np.asarray(off, float)
    sk = colour_mat(skin, "flat", 0.7)
    face = B.image_material("face_" + skin.lstrip("#"), _face_img(skin))
    sh = colour_mat(shirt)
    pm = M(pants)
    hm = M(hair)
    if pose == "sit":
        hip = 0.5
        for sx in (-1, 1):
            b.box(o + (sx * 4 * px / 2 * 1, 0.27 - 0.15 + 0.03, hip + 0.09), (4 * px, 12 * px, 4 * px), pm)
            b.box(o + (sx * 2 * px, 0.39 - 0.09, hip / 2), (4 * px, 4 * px, hip), pm)
        base = hip + 4 * px
        ty = -0.09
    else:
        for sx in (-1, 1):
            b.box(o + (sx * 2 * px, 0, 6 * px), (4 * px, 4 * px, 12 * px), pm)
        base = 12 * px
        ty = 0.0
    b.box(o + (0, ty, base + 6 * px), (8 * px, 4 * px, 12 * px), sh)
    for sx in (-1, 1):
        if pose == "cheer":
            b.box(o + (sx * 6 * px, ty, base + 12 * px + 5 * px), (4 * px, 4 * px, 12 * px), sh,
                  faces={"+z": sk})
        else:
            b.box(o + (sx * 6 * px, ty, base + 6 * px), (4 * px, 4 * px, 12 * px), sh, faces={"-z": sk})
    hc = o + (0, ty, base + 12 * px + 4 * px)
    b.box(hc, (8 * px, 8 * px, 8 * px), sk, faces={"+y": face, "+z": hm, "-y": hm}, uvfit=("+y",))
    if cap:
        b.box(hc + (0, 0.02, 4 * px + 0.03), (8.4 * px, 8.4 * px, 0.06), colour_mat(cap))
        b.box(hc + (0, 4 * px + 0.08, 4 * px + 0.01), (7 * px, 0.16, 0.03), colour_mat(cap))


def spectators():
    """24 seated and 24 standing spectator variants (mixed skin, hair, shirts; some caps, some cheering)."""
    rng = np.random.default_rng(11)
    for pose, name, n in (("sit", "spectator_sit", 24), ("stand", "spectator_stand", 24)):
        for v in range(n):
            b = MB()
            p = pose if not (pose == "stand" and v % 4 == 3) else "cheer"
            if pose == "sit" and v % 6 == 5:
                p = "sit"
            person(b, p, SKINS[v % len(SKINS)], HAIRS[(v * 7) % len(HAIRS)], SHIRTS[(v * 5) % len(SHIRTS)],
                   PANTS[(v * 3) % len(PANTS)], cap=SHIRTS[(v * 11 + 3) % len(SHIRTS)] if v % 3 == 0 else None,
                   off=(0, 0.04, 0) if pose == "sit" else (0, 0, 0))
            B.proto(name, b, v)
    # a few marshals in orange overalls and team crew in team kit
    for v in range(2):
        b = MB()
        person(b, "stand", SKINS[v * 2], "hair_dark", "#E8742A", "orange")
        B.proto("marshal", b, v)
    for i in range(len(P.TEAMS)):
        b = MB()
        key, _, main, acc = P.TEAMS[i]
        person(b, "stand", SKINS[i % len(SKINS)], HAIRS[i % len(HAIRS)], main, "trousers", cap=acc)
        B.proto("crew", b, i)


def seat_row_seat():
    for v, c in enumerate(["#1F4E9C", "#C8102E", "#00843D", "#E85D04", "#F2C200", "#6A1B9A", "#00A19B", "#0A3D91",
                           "#55595F"]):
        b = MB()
        m = colour_mat(c, "noise", 0.45)
        b.box((0, 0, 0.47), (0.44, 0.42, 0.06), m)
        b.box((0, -0.19, 0.7), (0.44, 0.05, 0.42), m)
        b.box((0, -0.05, 0.22), (0.06, 0.25, 0.44), M("steel_dark"))
        B.proto("seat", b, v)


# ================================================================ vegetation
def trees():
    """Blocky trees: v0-2 broadleaf (sizes), v3-4 pine, v5 birch, v6 poplar, v7 bush, v8 palm-free tall broadleaf."""
    specs = []
    b = MB()
    for v in range(9):
        b = MB()
        if v in (0, 1, 2, 8):
            h = (3.0, 4.0, 5.0, 6.0)[(0, 1, 2, 8).index(v)]
            r = (2.0, 2.5, 3.0, 3.5)[(0, 1, 2, 8).index(v)]
            lm = M(("leaves", "leaves_dark", "leaves_light", "leaves")[v % 4])
            b.box((0, 0, h / 2), (0.7, 0.7, h), M("bark"))
            b.box((0, 0, h + r * 0.4), (2 * r, 2 * r, r * 1.4), lm)
            b.box((0, 0, h + r * 1.3), (1.3 * r, 1.3 * r, r * 0.8), lm)
            b.box((r * 0.55, -r * 0.3, h + r * 0.1), (r, r, r * 0.8), lm)
        elif v in (3, 4):
            h = 9.0 if v == 3 else 13.0
            b.box((0, 0, h * 0.25), (0.6, 0.6, h * 0.5), M("bark"))
            tiers = 4 if v == 3 else 5
            for k in range(tiers):
                w = 4.4 * (1 - k / (tiers + 0.5))
                b.box((0, 0, h * 0.25 + k * h * 0.16 + 0.8), (w, w, 1.4), M("pine"))
            b.box((0, 0, h * 0.25 + tiers * h * 0.16 + 0.8), (0.8, 0.8, 1.2), M("pine"))
        elif v == 5:
            b.box((0, 0, 3.0), (0.45, 0.45, 6.0), M("birch"))
            b.box((0, 0, 6.5), (2.6, 2.6, 3.4), M("leaves_light"))
        elif v == 6:
            b.box((0, 0, 2.0), (0.5, 0.5, 4.0), M("bark"))
            b.box((0, 0, 8.0), (2.2, 2.2, 9.0), M("leaves_dark"))
        else:
            b.box((0, 0, 0.6), (1.8, 1.6, 1.2), M("hedge"))
            b.box((0.3, 0.2, 1.3), (1.0, 1.0, 0.6), M("hedge"))
        B.proto("tree", b, v)


def hedge():
    b = MB()
    b.box((0, 0, 0.7), (4.0, 1.2, 1.4), M("hedge"))
    B.proto("hedge", b, 0)


# ================================================================ vehicles (blocky, real size)
CAR_COLS = ["#C8102E", "#1F4E9C", "#F0F0EC", "#18181A", "#8C9096", "#2E6B3A", "#E8C04A", "#5A2A82", "#D9D9D2",
            "#3A3F48"]


def _car(b, body, glass, w=1.8, l=4.5, h=1.45, roof=None, light=None, text=None):
    wm = M("rubber")
    b.box((0, 0, 0.42), (w, l, 0.52), body)
    b.box((0, -0.25, 0.68 + (h - 0.68) / 2), (w - 0.14, l * 0.52, h - 0.68), glass,
          faces={"+z": roof or body})
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.box((sx * (w / 2 - 0.12), sy * l * 0.32, 0.33), (0.26, 0.66, 0.66), wm)
    b.box((0, l / 2 - 0.02, 0.52), (w * 0.8, 0.04, 0.14), M("lamp_off"))
    b.box((0, -l / 2 + 0.02, 0.52), (w * 0.8, 0.04, 0.14), colour_mat("#AA1010"))
    if light:
        b.box((0, -0.25, h + 0.08), (1.1, 0.25, 0.16), light)
    if text:
        for sx in (-1, 1):
            b.box((sx * (w / 2 + 0.005), 0, 0.45), (0.01, 2.4, 0.36), text, uvfit=("+x", "-x"))


def road_cars():
    for v, c in enumerate(CAR_COLS):
        b = MB()
        _car(b, colour_mat(c, "noise", 0.35), M("car_glass"))
        B.proto("road_car", b, v)


def service_cars():
    """v0 safety car, v1 medical car, v2 ambulance, v3 fire truck, v4 tow truck (flatbed + crane), v5 crane truck."""
    sc = B.material("safety_car_paint", "#B8BCC2", "noise", 0.3, 0.6)
    t_sc = sign_mat("safety_car", "SAFETY CAR", 2.4, 0.36, "#B8BCC2", "#111111")
    t_md = sign_mat("medical_car", "MEDICAL", 2.4, 0.36, "#F4F4F0", "#00843D")
    b = MB(); _car(b, sc, M("car_glass"), light=M("amber_light"), text=t_sc); B.proto("service_vehicle", b, 0)
    b = MB(); _car(b, M("white"), M("car_glass"), w=1.9, l=4.7, h=1.6, light=M("blue_light"), text=t_md)
    B.proto("service_vehicle", b, 1)
    # ambulance: van body
    b = MB()
    amb = M("white")
    b.box((0, 0, 1.4), (2.1, 6.2, 2.4), amb, faces={"+y": M("glass_dark")})
    b.box((0, 0, 1.0), (2.12, 6.0, 0.3), M("green"))
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.box((sx * 0.92, sy * 2.0, 0.38), (0.3, 0.76, 0.76), M("rubber"))
    b.box((0, 0.5, 2.68), (1.2, 0.3, 0.16), M("blue_light"))
    B.proto("service_vehicle", b, 2)
    # fire truck
    b = MB()
    red = colour_mat("#B3171C", "noise", 0.4)
    b.box((0, 2.6, 1.5), (2.5, 2.4, 2.4), red, faces={"+y": M("glass_dark")})
    b.box((0, -1.2, 1.6), (2.5, 5.2, 2.6), red)
    b.box((0, -1.2, 3.05), (1.0, 5.6, 0.3), M("galv"))
    b.box((0, -1.2, 1.4), (2.52, 5.0, 0.18), M("white"))
    for sy in (2.6, -0.4, -2.6):
        for sx in (-1, 1):
            b.box((sx * 1.1, sy, 0.5), (0.36, 1.0, 1.0), M("rubber"))
    b.box((0, 2.6, 2.8), (1.4, 0.3, 0.18), M("blue_light"))
    B.proto("service_vehicle", b, 3)
    # recovery tow truck: cab + flatbed + small crane
    b = MB()
    y = colour_mat("#F2C200", "noise", 0.5)
    b.box((0, 2.8, 1.4), (2.4, 2.0, 2.2), y, faces={"+y": M("glass_dark")})
    b.box((0, -1.0, 1.05), (2.4, 5.6, 0.3), M("steel_dark"))
    b.box((0, 1.4, 2.4), (0.5, 0.5, 2.0), y)
    b.box((0, -0.1, 3.3), (0.35, 3.4, 0.35), y, rot=(math.radians(15), 0, 0))
    b.box((0, -1.7, 2.6), (0.04, 0.04, 1.4), M("black"))
    for sy in (2.8, -0.6, -2.4):
        for sx in (-1, 1):
            b.box((sx * 1.05, sy, 0.5), (0.36, 1.0, 1.0), M("rubber"))
    b.box((0, 2.8, 2.6), (1.4, 0.25, 0.16), M("amber_light"))
    B.proto("service_vehicle", b, 4)
    # crane truck (big recovery crane)
    b = MB()
    b.box((0, 3.4, 1.5), (2.5, 2.0, 2.4), y, faces={"+y": M("glass_dark")})
    b.box((0, -1.0, 1.3), (2.5, 7.0, 1.0), y)
    b.box((0, -1.0, 2.6), (1.8, 2.0, 1.6), y)
    b.box((0, 1.2, 4.6), (0.6, 7.0, 0.6), y, rot=(math.radians(-25), 0, 0))
    for sy in (3.4, 0.0, -2.0, -3.6):
        for sx in (-1, 1):
            b.box((sx * 1.1, sy, 0.55), (0.4, 1.1, 1.1), M("rubber"))
    B.proto("service_vehicle", b, 5)


def transporter():
    """Team transporter: cab + 13.6 m trailer in team colours with the team name. One variant per team."""
    for i, (key, name, main, acc) in enumerate(P.TEAMS):
        b = MB()
        tm, ta = team_mat(i, "main"), team_mat(i, "acc")
        txt = sign_mat(f"truck_{key}", name, 10.0, 1.4, main, acc)
        b.box((0, 7.6, 1.9), (2.5, 2.4, 3.0), tm, faces={"+y": M("glass_dark")})
        b.box((0, -1.2, 2.4), (2.55, 13.6, 3.0), tm, faces={"+x": txt, "-x": txt}, uvfit=("+x", "-x"))
        b.box((0, -1.2, 0.95), (2.4, 13.0, 0.3), M("steel_dark"))
        b.box((0, -1.2, 3.75), (2.56, 13.6, 0.3), ta)
        for sy in (7.6, 5.0, -5.0, -6.3, -7.6):
            for sx in (-1, 1):
                b.box((sx * 1.05, sy, 0.5), (0.4, 1.0, 1.0), M("rubber"))
        B.proto("transporter", b, i)


# ================================================================ pit equipment
def pit_kit():
    """Per team: v = team. tyre_set (4 tyres in blankets on a trolley), tool_cabinet, jacks, wheel-gun stand,
    pit-wall stand, overhead pit gantry (boom with lights)."""
    for i, (key, name, main, acc) in enumerate(P.TEAMS):
        tm, ta = team_mat(i, "main"), team_mat(i, "acc")
        # tyre set on a trolley: four 0.72 m tyres stacked in blankets
        b = MB()
        b.box((0, 0, 0.12), (0.9, 0.9, 0.08), M("steel_dark"))
        for wx in (-0.35, 0.35):
            for wy in (-0.35, 0.35):
                b.box((wx, wy, 0.04), (0.08, 0.08, 0.08), M("black"))
        for k in range(4):
            b.box((0, 0, 0.2 + 0.36 * k + 0.17), (0.74, 0.74, 0.34), tm, faces={"+z": M("rubber")} if k == 3 else None)
            b.box((0, 0, 0.2 + 0.36 * k + 0.17), (0.76, 0.6, 0.12), ta)
        b.box((0, -0.5, 1.0), (0.6, 0.06, 0.06), M("steel"))
        B.proto("tyre_set", b, i)
        # tool cabinet
        b = MB()
        b.box((0, 0, 0.55), (1.6, 0.7, 1.1), tm)
        for k in range(5):
            b.box((0, 0.36, 0.15 + k * 0.2), (1.5, 0.02, 0.14), ta if k % 2 else M("steel_dark"))
        b.box((0, 0, 1.12), (1.62, 0.72, 0.04), M("steel"))
        B.proto("tool_cabinet", b, i)
        # front jack (long handle) and rear jack
        b = MB()
        b.box((0, 0.6, 0.12), (0.7, 0.4, 0.24), tm)
        b.box((0, -0.3, 0.55), (0.08, 1.8, 0.08), ta, rot=(math.radians(-24), 0, 0))
        b.box((0, -1.2, 0.95), (0.5, 0.08, 0.08), M("black"))
        B.proto("jack", b, i)
        # wheel gun on its stand with a hose
        b = MB()
        b.box((0, 0, 0.5), (0.1, 0.1, 1.0), M("steel_dark"))
        b.box((0, 0.1, 1.0), (0.18, 0.38, 0.2), ta)
        b.box((0, 0.3, 1.0), (0.1, 0.1, 0.1), M("black"))
        b.box((0, -0.3, 1.3), (0.05, 0.05, 0.6), M("black"))
        B.proto("wheel_gun", b, i)
        # overhead pit gantry: boom from the garage front over the box with hoses and a light
        b = MB()
        b.box((0, -0.2, 2.6), (0.3, 0.3, 5.2), M("steel_dark"))
        b.box((0, 3.0, 5.0), (0.4, 6.6, 0.35), tm)
        b.box((0, 6.2, 4.85), (1.2, 0.5, 0.25), M("lamp"))
        for x in (-0.15, 0.15):
            b.box((x, 4.2, 3.6), (0.05, 0.05, 2.6), M("black"))
        B.proto("pit_gantry", b, i)
        # pit-wall stand: desk with screens, stools, canopy in team colours (front +Y = the track)
        b = MB()
        b.box((0, 0, 1.6), (5.0, 1.6, 0.1), M("steel_dark"))
        b.box((0, 0.5, 1.95), (5.0, 0.5, 0.06), tm)
        for k in range(4):
            x = -1.8 + k * 1.2
            b.box((x, 0.6, 2.4), (0.9, 0.06, 0.55), M("black"), faces={"-y": colour_mat("#3A6FB0", "led", 0.4, 1.2)})
            b.box((x, -0.4, 2.0), (0.4, 0.4, 0.05), M("black"))
            b.box((x, -0.4, 1.8), (0.06, 0.06, 0.4), M("steel"))
        b.box((0, 0, 0.8), (5.0, 1.6, 1.6), M("steel_dark"), faces={"+y": tm, "-y": tm})
        for x in (-2.4, 2.4):
            b.box((x, -0.7, 2.6), (0.12, 0.12, 2.0), M("steel"))
        b.box((0, 0.0, 3.65), (5.4, 2.4, 0.1), ta)
        b.box((0, 0.0, 1.62), (5.0, 1.0, 0.05), M("steel_dark"))
        B.proto("pit_wall_stand", b, i)
    # generic: tyre rack (team-neutral metal), wheel trolley
    b = MB()
    for z in (0.1, 0.9, 1.7):
        b.box((0, 0, z), (2.4, 0.8, 0.06), M("steel"))
    for x in (-1.15, 1.15):
        for y in (-0.35, 0.35):
            b.box((x, y, 1.0), (0.06, 0.06, 2.0), M("steel"))
    for z in (0.13, 0.93):
        for k in range(3):
            b.box((-0.75 + k * 0.75, 0, z + 0.36), (0.7, 0.7, 0.7), M("tyre_side"))
    B.proto("tyre_rack", b, 0)
