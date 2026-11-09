"""Buildings and big structures, blocky: pit building (garage bays per team), race control, media centre, medical
centre, fire station, helipad, team motorhomes, grandstand sections, giant screens, viewing platforms, spectator
bridges, the start gantry, entrance arch, VIP terrace, town buildings, hotel, fan zone.

Prototype conventions as in props.py (origin on the ground, +Y = front). Garage bays: origin at the centre of the
bay's front edge (the pit lane side), the bay runs back along -Y.
"""
import math
import numpy as np
import blocks as B
from blocks import MeshBuilder as MB
import plan as P
import layout as L
from props import M, team_mat, colour_mat, sign_mat, fence_mat

BAY_W = L.GARAGE_W / 2      # 11 m: two bays per team
BAY_D = 26.0
GF, F1, F2, ROOF = 6.0, 10.4, 14.8, 15.4   # floor levels (top of slabs)


def _screen_mat(name, seed=0, emit=1.4):
    """A data screen (timing / telemetry look) as pixels."""
    rng = np.random.default_rng(seed)
    img = np.zeros((18, 32, 3), np.float32)
    img[:] = (0.04, 0.06, 0.1)
    for r in range(2, 17, 3):
        w = rng.integers(6, 28)
        img[r, 2:2 + w] = (0.3, 0.8, 1.0) if r % 2 else (0.95, 0.85, 0.3)
    img[1, :] = (0.8, 0.1, 0.1)
    return B.image_material(name, img, 0.3, emit)


# ================================================================ pit building
def garage_bay():
    """One 11 m garage bay with the two floors above it; variant = team (signage, colours, kit)."""
    for i, (key, name, main, acc) in enumerate(P.TEAMS):
        tm, ta = team_mat(i, "main"), team_mat(i, "acc")
        b = MB()
        w, d = BAY_W, BAY_D
        x0, x1 = -w / 2, w / 2
        # floor (epoxy, team stripe), no bottom face (sits on the ground slab)
        b.box((0, -7.0, 0.025), (w, 14.0, 0.05), M("floor_epoxy"), skip=("-z",))
        b.box((0, -1.0, 0.055), (w - 1.0, 0.3, 0.01), ta, skip=("-z",))
        # side wall on the -x edge only (the next bay supplies the other), end walls added by the building
        b.box((x0 + 0.15, -d / 2, ROOF / 2), (0.3, d, ROOF), M("concrete"), faces={"+x": tm})
        # back partition of the garage with team panel + screens, rooms behind it
        b.box((0, -14.15, GF / 2), (w - 0.3, 0.3, GF), tm)
        b.box((0, -14.0, 3.0), (6.0, 0.02, 1.5), sign_mat(f"garage_wall_{key}", name, 6.0, 1.5, main, acc),
              uvfit=("+y",))
        for k in range(3):
            b.box((-3.0 + 3.0 * k, -13.95, 4.6), (2.0, 0.1, 1.1), M("black"), faces={"+y": _screen_mat(f"scr_{key}_{k}", k + 3 * i)},
                  uvfit=("+y",))
        # ceiling slab of the garage and the floors above
        for z, t in ((GF, 0.4), (F1, 0.4), (F2, 0.2)):
            b.box((0.15, -d / 2, z - t / 2), (w - 0.3, d, t), M("concrete"))
        b.box((0.15, -d / 2, ROOF - 0.3), (w - 0.3, d, 0.6), M("roof"))
        # front: lintel over the garage opening with the team sign box
        b.box((0.15, -0.3, 5.3), (w - 0.3, 0.6, 1.0), M("concrete_dark"))
        b.box((0, 0.35, 5.3), (8.0, 0.7, 1.0), tm, faces={"+y": sign_mat(f"garage_sign_{key}", name, 8.0, 1.0, main, acc)},
              uvfit=("+y",))
        b.box((x1 - 0.5, -0.4, 2.4), (0.6, 0.8, 4.8), M("concrete"))           # pillar
        # first floor: offices behind a glass band
        b.box((0.15, -0.6, (GF + F1 - 0.4) / 2), (w - 0.3, 0.2, F1 - 0.4 - GF), M("glass"))
        # second floor: hospitality with a balcony over the pit lane
        b.box((0.15, -0.6, (F1 + F2 - 0.2) / 2), (w - 0.3, 0.2, F2 - 0.2 - F1), M("glass_dark"))
        b.box((0.15, 1.2, F1 + 0.1), (w - 0.3, 3.6, 0.2), M("concrete"))
        b.box((0.15, 2.95, F1 + 0.75), (w - 0.3, 0.06, 1.1), M("glass"))
        b.box((0.15, 2.95, F1 + 1.32), (w - 0.3, 0.1, 0.06), M("steel"))
        # roof fascia
        b.box((0.15, 0.1, ROOF + 0.6), (w - 0.3, 0.4, 1.2), ta)
        # back wall to the paddock: team colour panel, doors
        b.box((0.15, -d + 0.15, ROOF / 2), (w - 0.3, 0.3, ROOF), M("concrete"), faces={"-y": tm})
        b.box((0, -d - 0.02, 1.25), (2.2, 0.04, 2.5), M("grey"))
        b.box((0, -d - 0.02, F1 - 2.0), (8.0, 0.04, 2.0), M("glass"))
        # interior kit along the side walls (tool cabinets, tyre racks), ceiling lights, overhead gantry
        for y in (-4.0, -7.0, -10.0):
            b.box((x0 + 1.15, y, 0.6), (1.4, 1.6, 1.1), tm, faces={"+x": ta})
        for y in (-5.0, -10.0):
            b.box((x1 - 1.0, y, 1.05), (1.0, 2.6, 2.0), M("steel"))
            for k in range(2):
                b.box((x1 - 1.0, y - 0.65 + 1.3 * k, 1.6), (0.75, 0.75, 0.7), M("tyre_side"))
                b.box((x1 - 1.0, y - 0.65 + 1.3 * k, 0.55), (0.75, 0.75, 0.7), M("tyre_side"))
        for y in (-3.0, -7.0, -11.0):
            b.box((0, y, GF - 0.45), (6.0, 0.4, 0.1), M("lamp"))
        b.box((0, -6.0, GF - 1.4), (0.3, 8.0, 0.3), M("steel_dark"))
        for y in (-3.5, -8.5):
            b.box((0, y, GF - 1.9), (1.2, 0.08, 0.7), M("black"), faces={"+y": _screen_mat(f"gscr_{key}", i)}, uvfit=("+y",))
        B.proto("garage_bay", b, i)


def garage_door():
    """Roller door for one bay (separate object per bay): origin at the top of the opening; scale Z 1 = closed,
    0.04 = rolled up (open)."""
    b = MB()
    for k in range(12):
        b.box((0, 0.05, -0.2 - 0.4 * k), (9.4, 0.08, 0.38), M("steel"))
    b.box((0, 0.2, 0.2), (9.8, 0.5, 0.4), M("steel_dark"))
    return b


def building_end(name, label, floors, w, d, colour, sign_side="+y", top="glass"):
    """Generic block building (race control, media centre...): window bands per floor, sign on the front."""
    b = MB()
    fh = 4.0
    H = floors * fh
    b.box((0, 0, H / 2), (w, d, H), B.material(name + "_facade", colour, "window", 0.5, col2="#2C4A60"),
          faces={"+z": M("roof")})
    for k in range(1, floors):
        b.box((0, 0, k * fh), (w + 0.2, d + 0.2, 0.3), M("concrete"))
    if label:
        sm = sign_mat(name, label, min(w - 2, 3.0 * len(label) * 0.45 + 2), 2.0, "#111111", "#FFFFFF")
        sw = min(w - 2, 3.0 * len(label) * 0.45 + 2)
        b.box((0, d / 2 + 0.2, H - 2.0), (sw, 0.3, 2.0), M("black"), faces={"+y": sm}, uvfit=("+y",))
    return b, H


def race_control():
    """Race control tower: five floors with a glass control room on top, cantilevered over the pit lane."""
    b, H = building_end("race_control", "RACE CONTROL", 4, 30.0, 24.0, "#D9D9D4")
    top = H
    b.box((0, 2.0, top + 2.5), (32.0, 28.0, 5.0), M("glass_dark"), faces={"+z": M("roof"), "-z": M("concrete")})
    b.box((0, 2.0, top + 5.2), (33.0, 29.0, 0.4), M("roof"))
    b.box((0, 16.6, top + 0.6), (32.0, 0.1, 1.2), M("steel"))
    b.box((10.0, 0, top + 6.5), (0.3, 0.3, 2.6), M("steel"))           # antenna mast
    b.box((10.0, 0, top + 8.0), (1.2, 0.2, 0.6), M("white"))
    return b


def medical_centre():
    b = MB()
    w, d, h = 34.0, 22.0, 5.0
    b.box((0, 0, h / 2), (w, d, h), M("white"), faces={"+z": M("roof")})
    b.box((0, 0, 3.8), (w + 0.1, d + 0.1, 0.6), M("green"))
    # a white cross on green (the medical sign), the name, and the ambulance canopy at the front
    cross = np.full((16, 16, 3), B.hexrgb("#00843D"), np.float32)
    cross[5:11, 2:14] = 1.0
    cross[2:14, 5:11] = 1.0
    cm = B.image_material("medical_cross", cross)
    b.box((-12.0, d / 2 + 0.15, 2.4), (2.4, 0.2, 2.4), M("green"), faces={"+y": cm}, uvfit=("+y",))
    b.box((3.0, d / 2 + 0.15, 4.4), (18.0, 0.2, 1.2), M("green"),
          faces={"+y": sign_mat("medical", "MEDICAL CENTRE", 18.0, 1.2, "#00843D", "#FFFFFF")}, uvfit=("+y",))
    b.box((3.0, d / 2 + 4.0, 4.0), (14.0, 8.0, 0.3), M("roof"))
    for x in (-3.8, 9.8):
        b.box((x, d / 2 + 7.6, 2.0), (0.3, 0.3, 4.0), M("steel"))
    b.box((3.0, d / 2 + 0.05, 1.5), (5.0, 0.1, 3.0), M("glass"))
    for x in (-10, 12):
        b.box((x, d / 2 + 0.05, 2.0), (4.0, 0.1, 1.4), M("glass"))
    return b


def fire_station():
    b = MB()
    w, d, h = 26.0, 18.0, 7.0
    red = colour_mat("#B3171C", "concrete", 0.6)
    b.box((0, 0, h / 2), (w, d, h), red, faces={"+z": M("roof")})
    for k in range(3):
        b.box((-8.0 + 8.0 * k, d / 2 + 0.05, 2.4), (6.0, 0.1, 4.8), M("steel"))
    b.box((0, d / 2 + 0.15, 6.0), (16.0, 0.2, 1.2), red,
          faces={"+y": sign_mat("fire_rescue", "FIRE + RESCUE", 16.0, 1.2, "#B3171C", "#FFFFFF")}, uvfit=("+y",))
    return b


def helipad():
    img = np.full((48, 48, 3), B.hexrgb("#4A4D52"), np.float32)
    yy, xx = np.mgrid[:48, :48]
    r = np.hypot(xx - 23.5, yy - 23.5)
    img[(r > 19) & (r < 21)] = (0.95, 0.95, 0.9)
    img[12:36, 15:19] = (0.95, 0.95, 0.9)
    img[12:36, 29:33] = (0.95, 0.95, 0.9)
    img[22:26, 15:33] = (0.95, 0.95, 0.9)
    m = B.image_material("helipad", img)
    b = MB()
    b.box((0, 0, 0.075), (22.0, 22.0, 0.15), M("concrete"), faces={"+z": m}, uvfit=("+z",), skip=("-z",))
    b.box((13.0, 13.0, 2.0), (0.1, 0.1, 4.0), M("steel"))
    b.box((13.0, 13.8, 3.8), (0.3, 1.6, 0.3), M("orange"))
    return b


def motorhome():
    """Team hospitality unit (18 x 14 m, two floors + roof terrace), variant per team."""
    for i, (key, name, main, acc) in enumerate(P.TEAMS):
        tm, ta = team_mat(i, "main"), team_mat(i, "acc")
        b = MB()
        b.box((0, 0, 1.9), (18.0, 14.0, 3.8), M("glass_dark"), faces={"+z": tm})
        b.box((0, 0, 4.0), (18.4, 14.4, 0.4), tm)
        b.box((0, 0, 6.0), (18.0, 14.0, 3.6), M("glass"), faces={"-y": tm, "+x": tm, "-x": tm})
        b.box((0, 0, 8.0), (18.4, 14.4, 0.4), tm)
        b.box((0, 7.25, 7.0), (12.0, 0.2, 1.2), tm, faces={"+y": sign_mat(f"mh_{key}", name, 12.0, 1.2, main, acc)},
              uvfit=("+y",))
        b.box((0, 7.0, 8.7), (18.0, 0.08, 1.0), M("glass"))
        for x in (-5, 0, 5):   # parasols on the roof terrace
            b.box((x, 2.0, 9.2), (0.1, 0.1, 2.0), M("steel"))
            b.box((x, 2.0, 10.2), (3.0, 3.0, 0.15), ta)
        b.box((0, 9.0, 0.2), (14.0, 4.0, 0.4), M("wood"), skip=("-z",))   # front deck
        B.proto("motorhome", b, i)


# ================================================================ spectators' structures
def grandstand_section(name, rows, roof, colour):
    """One 10 m section of a stand (+Y faces the track). Returns (builder, seat positions [(x, y, z)], depth, top)."""
    b = MB()
    depth = rows * 0.8 + 4.0
    yf = depth / 2 - 1.5
    seats = []
    concrete = M("concrete")
    fascia = colour_mat(colour, "noise", 0.5)
    seat_m = colour_mat(colour, "noise", 0.45)
    b.box((0, depth / 2 - 0.75, 0.6), (10.0, 1.5, 1.2), concrete, faces={"+y": fascia})     # front walkway
    b.box((0, depth / 2 - 0.05, 1.75), (10.0, 0.06, 1.1), M("glass"))                        # railing
    b.box((0, depth / 2 - 0.05, 2.33), (10.0, 0.08, 0.06), M("steel"))
    for k in range(rows):
        z = 1.2 + (k + 1) * 0.45
        y0 = yf - k * 0.8
        b.box((0, y0 - 0.4, z / 2), (10.0, 0.8, z), concrete, faces={"+y": M("concrete_dark")})
        for j in range(17):
            x = -4.0 + 0.5 * j + 0.25
            b.box((x, y0 - 0.35, z + 0.47), (0.44, 0.42, 0.06), seat_m)
            b.box((x, y0 - 0.54, z + 0.7), (0.44, 0.05, 0.42), seat_m)
            seats.append((x, y0 - 0.35, z))
        # aisle steps (half rise) at the -x end
        b.box((-4.6, y0 - 0.6, z + 0.12), (0.8, 0.4, 0.24), M("concrete_dark"))
    top = 1.2 + rows * 0.45
    yb = yf - rows * 0.8
    b.box((0, yb - 0.25, (top + 2.5) / 2), (10.0, 0.5, top + 2.5), concrete, faces={"-y": fascia})   # back wall
    if roof == "cantilever":
        h = top + 6.0
        b.box((-4.7, yb - 0.6, h / 2), (0.5, 0.5, h), M("steel"))
        b.box((0, (yb + depth / 2) / 2 - 0.3, h + 0.2), (10.0, depth - (depth / 2 - yb) * 0 + 1.0 - 0.0, 0.4), M("roof"),
              faces={"-z": M("steel_dark")}, rot=(math.radians(-4), 0, 0))
        b.box((-4.7, yb - 0.6 + depth * 0.25, h + 1.0), (0.4, depth * 0.55, 0.4), M("steel"), rot=(math.radians(10), 0, 0))
        b.box((0, depth / 2 + 0.4, h - 0.2), (10.0, 0.3, 1.4), fascia)
    elif roof == "flat":
        h = top + 4.5
        for x in (-4.8,):
            b.box((x, depth / 2 - 1.2, (h) / 2), (0.3, 0.3, h), M("steel"))
            b.box((x, yb - 0.6, h / 2), (0.3, 0.3, h), M("steel"))
        b.box((0, (yb + depth / 2) / 2, h + 0.15), (10.0, depth + 0.6, 0.3), M("canvas"), faces={"-z": M("steel_dark")})
        b.box((0, depth / 2 + 0.3, h), (10.0, 0.2, 0.8), fascia)
    return b, seats, depth, top


def stand_end(rows, depth):
    b = MB()
    yf = depth / 2 - 1.5
    for k in range(rows):
        z = 1.2 + (k + 1) * 0.45
        b.box((0, yf - k * 0.8 - 0.4, z / 2 + 0.6), (0.3, 0.8, z + 1.2), M("concrete"))
    b.box((0, depth / 2 - 0.75, 1.2), (0.3, 1.5, 2.4), M("concrete"))
    return b


def giant_screen():
    """12 x 7 m LED screen on a truss (front +Y), showing a race feed."""
    img = np.zeros((56, 96, 3), np.float32)
    img[:] = (0.25, 0.5, 0.85)                  # sky
    img[30:, :] = (0.3, 0.55, 0.25)             # grass
    img[34:46, :] = (0.18, 0.18, 0.2)           # track
    img[34, :] = img[45, :] = (0.9, 0.9, 0.9)
    img[37:43, 30:52] = (0.85, 0.85, 0.88)      # a silver car
    img[36:38, 34:40] = (0.1, 0.1, 0.1)
    img[39:44, 32:36] = img[39:44, 46:50] = (0.05, 0.05, 0.05)
    img[2:24, 2:26] = (0.05, 0.05, 0.08)        # timing tower
    for r in range(4, 24, 4):
        img[r:r + 2, 4:22] = (0.9, 0.9, 0.9)
        img[r:r + 2, 4:6] = (0.8, 0.1, 0.1)
    img[1::2, :] *= 0.85
    m = B.image_material("giant_screen", img, 0.3, emit=2.0)
    b = MB()
    b.box((0, 0, 9.5), (12.6, 0.8, 7.6), M("black"), faces={"+y": m}, uvfit=("+y",))
    for x in (-5.0, 5.0):
        b.box((x, -0.8, 3.0), (0.6, 0.6, 6.0), M("galv"))
        for z in (1.5, 3.5, 5.5):
            b.box((x, -0.8, z), (0.7, 1.6, 0.12), M("galv"), rot=(math.radians(35), 0, 0))
    b.box((0, -0.8, 6.0), (10.6, 0.5, 0.5), M("galv"))
    return b


def viewing_platform():
    """12 x 6 m scaffold platform, 3 m high, with railings and stairs (general admission)."""
    b = MB()
    for x in np.arange(-6, 6.01, 3):
        for y in (-3, 0, 3):
            b.box((x, y, 1.5), (0.1, 0.1, 3.0), M("galv"))
    for z in (1.0, 2.0):
        for y in (-3, 3):
            b.box((0, y, z), (12.0, 0.06, 0.06), M("galv"))
    b.box((0, 0, 3.05), (12.4, 6.4, 0.1), M("wood"))
    for y in (-3.15, 3.15):
        b.box((0, y, 4.05), (12.4, 0.06, 0.06), M("galv"))
        b.box((0, y, 3.6), (12.4, 0.04, 0.04), M("galv"))
    b.box((6.2, 0, 4.05), (0.06, 6.4, 0.06), M("galv"))
    for k in range(12):   # stairs on the -x end
        b.box((-6.6 - 0.25 * k, 0, 0.125 + 0.25 * k), (0.28, 1.2, 0.25), M("wood"))
    b.box((0, 3.3, 2.0), (12.0, 0.02, 1.2), colour_mat("#1F4E9C"),
          faces={"+y": sign_mat("platform_ga", "GENERAL ADMISSION", 12.0, 1.2, "#1F4E9C", "#FFFFFF")}, uvfit=("+y",))
    return b


def spectator_bridge(half_span, sponsor=0):
    """Footbridge across the track (local X across the track, +Y along it). Deck 7 m above the ground."""
    b = MB()
    L_ = 2 * half_span
    z0 = 7.0
    text, bg, fg = P.SPONSORS[sponsor]
    sm = sign_mat(f"bridge_{sponsor}", text, L_ * 0.6, 1.6, bg, fg)
    b.box((0, 0, z0 + 0.3), (L_, 4.0, 0.6), M("steel_dark"))
    for sy in (-1, 1):
        b.box((0, sy * 2.0, z0 + 1.6), (L_, 0.25, 2.0), colour_mat(bg, "noise", 0.5),
              faces={("+y" if sy > 0 else "-y"): sm}, uvfit=("+y", "-y"))
    b.box((0, 0, z0 + 2.9), (L_, 4.4, 0.25), M("roof"))
    for sx in (-1, 1):   # stair towers
        x = sx * (half_span + 3.0)
        b.box((x, 0, (z0 + 3.0) / 2), (6.0, 6.0, z0 + 3.0), M("concrete"), faces={"+z": M("roof")})
        for k in range(8):
            b.box((x + sx * 3.05, -2.4 + 0.6 * k, 0.45 + k * 0.9), (0.1, 0.5, 0.06), M("glass"))
        b.box((x, 3.05, 1.2), (1.6, 0.1, 2.4), M("glass_dark"))
    return b


def start_gantry(width_left, width_right, lights_x=0.0):
    """Start/finish gantry over the main straight (local X along the track, +Y to the left of the driving
    direction). Supports at y=+width_left and y=-width_right; five red light columns facing the grid (-X)."""
    b = MB()
    z = 6.5
    span = width_left + width_right
    yc = (width_left - width_right) / 2
    b.box((0, yc + 0.65, z + 0.75), (1.4, span + 1.3, 1.5), M("steel_dark"))
    for y in (width_left + 1.3, -width_right):
        b.box((0, y, z / 2), (1.0, 1.0, z), M("steel_dark"))
    for k in range(5):
        y = -2.6 + 1.3 * k
        b.box((-0.75, y, z + 0.75), (0.15, 0.9, 1.3), M("black"))
        for j in range(4):
            mat = M("red_light") if j < 2 else M("led_off")
            b.box((-0.84, y, z + 0.25 + 0.3 * j), (0.03, 0.5, 0.22), mat)
    for sy in (-1, 1):
        t, bg, fg = P.SPONSORS[1 if sy > 0 else 2]
        sm = sign_mat(f"gantry_{sy}", t, 4.0, 1.2, bg, fg)
        b.box((-0.72, yc + sy * 5.6, z + 0.75), (0.04, 4.0, 1.2), M("black"), faces={"-x": sm}, uvfit=("-x",))
    tm = B.image_material("gantry_timing", B.sign_image("LAP 1/57", 4.0, 1.0, "#05070A", "#FFD200"), 0.3, 1.5)
    b.box((0.72, yc, z + 0.75), (0.04, 4.0, 1.0), M("black"), faces={"+x": tm}, uvfit=("+x",))
    fin = sign_mat("finish", "FINISH", 6.0, 1.0, "#FFFFFF", "#111111")
    b.box((0.72, yc + 6.0, z + 0.75), (0.04, 5.0, 1.0), M("black"), faces={"+x": fin}, uvfit=("+x",))
    return b


def entrance_arch():
    """Main gate: a 34 m portal with the GRAND PRIX sign, turnstiles and ticket booths (+Y = outward, the town)."""
    b = MB()
    for x in (-16, 16):
        b.box((x, 0, 7.0), (2.0, 2.0, 14.0), M("steel_dark"))
    sm = sign_mat("gp_arch", "GRAND PRIX", 30.0, 4.0, "#C8102E", "#FFFFFF")
    b.box((0, 0, 13.0), (34.0, 1.6, 4.0), M("steel_dark"), faces={"+y": sm, "-y": sm}, uvfit=("+y", "-y"))
    for k in range(10):   # turnstiles
        x = -11.25 + 2.5 * k
        b.box((x, -8.0, 0.55), (0.3, 1.4, 1.1), M("steel"))
        b.box((x + 0.6, -8.0, 0.95), (0.9, 0.06, 0.06), M("steel"))
    for x in (-24, 24):   # ticket booths
        b.box((x, -2.0, 1.4), (5.0, 3.0, 2.8), M("white"), faces={"+y": M("glass")})
        b.box((x, -2.0, 3.0), (5.6, 3.6, 0.3), M("red"))
        b.box((x, -0.45, 2.4), (4.0, 0.1, 0.5), sign_mat("tickets", "TICKETS", 4.0, 0.5, "#C8102E", "#FFFFFF"),
              uvfit=("+y",))
    return b


def vip_terrace():
    """Three-storey glass hospitality building with terraces stepping toward the track (+Y)."""
    b = MB()
    for k in range(3):
        y = -k * 3.0
        b.box((0, y - 9.0 + 12.0, 2.0 + 4.0 * k), (50.0, 24.0 - 6.0 * k, 4.0), M("glass_dark"),
              faces={"+z": M("concrete")})
        b.box((0, y + 12.05 - 0.0, 4.6 + 4.0 * k), (50.0, 0.06, 1.1), M("glass"))
    b.box((0, -6.0, 13.0), (50.0, 12.0, 2.0), M("white"),
          faces={"+y": sign_mat("vip", "VIP TERRACE", 50.0, 2.0, "#111111", "#E8C04A")}, uvfit=("+y",))
    return b


def marquee(w=20.0, d=12.0, col="#F4F2EA"):
    b = MB()
    c = colour_mat(col, "noise", 0.9)
    b.box((0, 0, 1.6), (w, d, 3.2), c)
    for k in range(4):
        b.box((0, 0, 3.2 + 0.45 * k + 0.225), (w * (1 - 0.18 * k), d * (1 - 0.22 * (k + 1)), 0.45), c)
    return b


def stall(col):
    b = MB()
    b.box((0, 0, 1.3), (4.0, 2.6, 2.6), M("white"), faces={"+y": M("dark")})
    b.box((0, 0.5, 2.8), (4.6, 3.8, 0.25), colour_mat(col, "stripes", 0.8))
    b.box((0, 1.4, 1.0), (4.0, 0.3, 0.1), M("steel"))
    return b


def stage():
    b = MB()
    b.box((0, 0, 0.75), (16.0, 10.0, 1.5), M("black"), skip=("-z",))
    for x in (-8, 8):
        b.box((x, -4.5, 5.0), (0.5, 0.5, 10.0), M("galv"))
    b.box((0, -4.5, 9.8), (16.5, 0.5, 0.5), M("galv"))
    b.box((0, -4.8, 6.0), (12.0, 0.2, 6.0), M("black"), faces={"+y": _screen_mat("stage_screen", 9, 1.8)}, uvfit=("+y",))
    return b


# ================================================================ town
def town_building(kind, seed):
    """Town buildings: 'house', 'flats', 'office', 'shop'. Window facades, flat or stepped roofs."""
    rng = np.random.default_rng(seed)
    b = MB()
    if kind == "house":
        w, d, h = rng.choice([8, 10, 12]), rng.choice([8, 9, 10]), 6.0
        wall = B.material(f"house_wall_{seed % 4}", ["#E8DCC2", "#D9C3A0", "#CFC9BE", "#E0B9A0"][seed % 4], "window", 0.8,
                          col2="#33475A")
        b.box((0, 0, h / 2), (w, d, h), wall)
        roof = colour_mat(["#8A3A2A", "#5A5F66", "#3E4A3A", "#7A4A2A"][seed % 4], "tile", 0.8)
        for k in range(4):
            b.box((0, 0, h + 0.5 * k + 0.25), (w + 0.6, d + 0.6 - 2.3 * k, 0.5), roof)
    elif kind == "flats":
        w, d, h = 16, 14, float(rng.choice([12, 16, 20]))
        wall = B.material(f"flats_{seed % 3}", ["#C9C2B4", "#B8BEC4", "#D8CFC0"][seed % 3], "window", 0.7, col2="#2C3E50")
        b.box((0, 0, h / 2), (w, d, h), wall, faces={"+z": M("roof")})
    elif kind == "office":
        w, d, h = 20, 20, float(rng.choice([28, 36, 44]))
        b.box((0, 0, h / 2), (w, d, h), B.material(f"office_{seed % 2}", ["#5E7C96", "#3D5A70"][seed % 2], "window",
                                                    0.2, 0.3, col2="#9EC3DE"), faces={"+z": M("roof")})
        b.box((0, 0, h + 1.0), (8, 8, 2.0), M("grey"))
    else:   # shop
        w, d, h = 14, 10, 5.0
        b.box((0, 0, h / 2), (w, d, h), M("white"), faces={"+y": M("glass")})
        b.box((0, d / 2 + 0.8, 3.8), (w, 1.6, 0.2), colour_mat(["#C8102E", "#1F4E9C", "#00843D"][seed % 3], "stripes", 0.8))
    return b, (w, d)


def hotel():
    b = MB()
    w, d, h = 40.0, 30.0, 48.0
    b.box((0, 0, h / 2), (w, d, h), B.material("hotel_facade", "#E6E2DA", "window", 0.4, col2="#3B6C8C"),
          faces={"+z": M("roof")})
    b.box((0, 0, h + 2.0), (w * 0.6, d * 0.6, 4.0), M("glass_dark"))
    b.box((0, d / 2 + 0.2, h - 3.0), (16.0, 0.3, 3.0), M("black"),
          faces={"+y": sign_mat("hotel", "HOTEL", 16.0, 3.0, "#111111", "#E8C04A")}, uvfit=("+y",))
    return b
