"""Props: the generic modern F1 car (no logos), pit equipment, hospital equipment.

Every builder returns a root empty; place it with .location / .rotation_euler. Cars face +Y.
"""
import math
import bpy
from mathutils import Vector, Matrix
from lib import (V, link, mat, box, cyl, sphere, torus, loft, superellipse, tube, subsurf, smooth, bevel,
                 autosmooth, mesh_obj, palette, group)


# ---------------------------------------------------------------- F1 car
def wheel(name, r=0.36, w=0.36, side=1, nut="yellow"):
    M = palette()
    parts = []
    # tyre: rounded cylinder, axis X
    t = cyl(name + "_tyre", r, w, material=M["rubber"], seg=48, rot=(0, math.pi / 2, 0), bev=0.07)
    parts.append(t)
    # coloured sidewall band (outer face), the only tyre colour (style guide)
    band = torus(name + "_band", r * 0.8, 0.012, material=M[nut], rot=(0, math.pi / 2, 0))
    band.location = (side * (w / 2 + 0.002), 0, 0)
    band.scale = (1, 1, 0.6)
    parts.append(band)
    rim = cyl(name + "_rim", r * 0.62, w * 0.9, material=M["dark"], seg=36, rot=(0, math.pi / 2, 0))
    rim.location = (side * 0.01, 0, 0)
    parts.append(rim)
    cover = cyl(name + "_cover", r * 0.6, 0.02, material=M["grey"], seg=36, rot=(0, math.pi / 2, 0), bev=0.008)
    cover.location = (side * (w / 2 - 0.02), 0, 0)
    parts.append(cover)
    n = cyl(name + "_nut", 0.045, 0.06, material=M["red"], seg=6, rot=(0, math.pi / 2, 0), bev=0.006)
    n.location = (side * (w / 2 + 0.01), 0, 0)
    parts.append(n)
    return group(name, parts)


def f1car(name="car", body="red", driver=True):
    import lib
    if lib.STYLE.get("voxel"):
        return f1car_block(name, body, driver)
    M = palette()
    B = M[body]
    C = M["dark"]  # carbon parts
    P = []
    # nose + monocoque + engine cover, one loft along Y: (y, z, half-width, half-height, squareness)
    S = [(2.72, 0.25, 0.05, 0.035, 2.2), (2.45, 0.29, 0.1, 0.06, 2.4), (2.0, 0.34, 0.15, 0.1, 2.6),
         (1.45, 0.38, 0.22, 0.15, 2.8), (0.95, 0.43, 0.27, 0.19, 3.0), (0.5, 0.45, 0.32, 0.21, 3.2),
         (0.0, 0.45, 0.36, 0.21, 3.2), (-0.45, 0.5, 0.34, 0.27, 3.0), (-1.0, 0.5, 0.26, 0.25, 2.8),
         (-1.6, 0.44, 0.17, 0.18, 2.6), (-2.05, 0.38, 0.09, 0.1, 2.4), (-2.3, 0.34, 0.045, 0.05, 2.2)]
    mono = loft(name + "_mono", [superellipse(0, y, z, w, h, 28, p, "XZ") for y, z, w, h, p in S], B)
    subsurf(mono, 2)
    P.append(mono)
    # cockpit opening (dark) and the driver's helmet
    cp = sphere(name + "_cockpit", 1, (0, 0.18, 0.62), C, scale=(0.24, 0.5, 0.06))
    P.append(cp)
    if driver:
        P.append(sphere(name + "_helmet", 0.135, (0, 0.05, 0.72), M["yellow"], scale=(0.95, 1.05, 1)))
        P.append(sphere(name + "_hvisor", 0.1, (0, 0.14, 0.74), C, scale=(1.05, 0.5, 0.42)))
    # halo
    P.append(tube(name + "_halo", [V((0, 0.82, 0.6)), V((0, 0.66, 0.8)), V((0.25, 0.25, 0.84)), V((0.29, -0.1, 0.8)),
                                   V((0.27, -0.28, 0.66))], 0.03, C))
    P.append(tube(name + "_haloL", [V((0, 0.66, 0.8)), V((-0.25, 0.25, 0.84)), V((-0.29, -0.1, 0.8)),
                                    V((-0.27, -0.28, 0.66))], 0.03, C))
    # airbox above the driver's head
    ab = loft(name + "_airbox", [superellipse(0, y, z, w, h, 20, 2.6, "XZ") for y, z, w, h in
                                 [(-0.12, 0.86, 0.09, 0.08), (-0.3, 0.87, 0.11, 0.1), (-0.7, 0.78, 0.09, 0.1),
                                  (-1.2, 0.66, 0.04, 0.06)]], B)
    subsurf(ab, 2)
    P.append(ab)
    P.append(sphere(name + "_intake", 1, (0, -0.1, 0.87), C, scale=(0.07, 0.03, 0.06)))
    # sidepods
    for s in (1, -1):
        sp = loft(name + f"_pod{s}", [superellipse(s * x, y, z, w, h, 24, p, "XZ") for x, y, z, w, h, p in
                                      [(0.36, 0.74, 0.37, 0.05, 0.1, 2.4), (0.44, 0.58, 0.37, 0.16, 0.15, 3.4),
                                       (0.46, 0.0, 0.35, 0.2, 0.16, 3.4), (0.38, -0.75, 0.32, 0.15, 0.13, 3.0),
                                       (0.24, -1.4, 0.28, 0.07, 0.08, 2.4)]], B)
        subsurf(sp, 2)
        P.append(sp)
        P.append(box(name + f"_inlet{s}", (0.2, 0.04, 0.16), (s * 0.46, 0.68, 0.38), C, bev=0.03))
        # mirrors
        P.append(box(name + f"_mirror{s}", (0.14, 0.05, 0.06), (s * 0.48, 0.62, 0.66), B, bev=0.02))
        P.append(tube(name + f"_mstalk{s}", [V((s * 0.3, 0.62, 0.55)), V((s * 0.42, 0.62, 0.64))], 0.012, C))
    # engine cover fin
    P.append(box(name + "_fin", (0.02, 1.2, 0.16), (0, -1.15, 0.72), B, bev=0.008, rot=(math.radians(-6), 0, 0)))
    # floor (carbon), with a slight taper
    fl = mesh_obj(name + "_floor", [V((-0.25, 1.4, 0.06)), V((0.25, 1.4, 0.06)), V((0.68, 0.85, 0.06)), V((0.7, -1.2, 0.06)),
                                   V((0.45, -2.05, 0.06)), V((-0.45, -2.05, 0.06)), V((-0.7, -1.2, 0.06)), V((-0.68, 0.85, 0.06))],
                  [tuple(range(8))], C)
    sol = fl.modifiers.new("thick", "SOLIDIFY")
    sol.thickness = 0.02
    bevel(fl, 0.008, 2)
    P.append(fl)
    # front wing: three stacked elements + endplates
    for i, (y, z, d) in enumerate([(2.82, 0.1, 0.3), (2.62, 0.16, 0.2), (2.48, 0.22, 0.14)]):
        P.append(box(name + f"_fw{i}", (1.86 - i * 0.12, d, 0.014), (0, y, z), C if i == 0 else B, bev=0.006,
                     rot=(math.radians(-8 - i * 6), 0, 0)))
    for s in (1, -1):
        P.append(box(name + f"_fwep{s}", (0.018, 0.5, 0.17), (s * 0.93, 2.66, 0.16), C, bev=0.008))
    # nose pylons
    for s in (1, -1):
        P.append(box(name + f"_pylon{s}", (0.02, 0.18, 0.1), (s * 0.06, 2.55, 0.17), C, bev=0.005))
    # rear wing: two elements, endplates, swan-neck pillar
    P.append(box(name + "_rw0", (1.0, 0.36, 0.03), (0, -2.42, 0.86), C, bev=0.01, rot=(math.radians(-10), 0, 0)))
    P.append(box(name + "_rw1", (1.0, 0.2, 0.025), (0, -2.58, 0.98), B, bev=0.01, rot=(math.radians(-24), 0, 0)))
    for s in (1, -1):
        P.append(box(name + f"_rwep{s}", (0.025, 0.62, 0.5), (s * 0.51, -2.45, 0.8), B, bev=0.012))
    P.append(box(name + "_rwpillar", (0.03, 0.12, 0.45), (0, -2.3, 0.62), C, bev=0.01))
    # diffuser / beam wing
    P.append(box(name + "_beam", (0.8, 0.14, 0.025), (0, -2.35, 0.4), C, bev=0.008, rot=(math.radians(-12), 0, 0)))
    # wheels and suspension
    for (y, x, w, r, nm) in [(1.8, 0.8, 0.31, 0.36, "f"), (-1.78, 0.78, 0.41, 0.37, "r")]:
        for s in (1, -1):
            wh = wheel(name + f"_w{nm}{s}", r, w, s)
            wh.location = (s * x, y, r)
            P.append(wh)
            for dz, dy in ((0.14, 0.1), (-0.04, -0.1)):
                P.append(tube(name + f"_arm{nm}{s}{dz}", [V((s * 0.2, y + dy, 0.3 + dz)), V((s * (x - 0.12), y, r + dz * 0.6))],
                              0.018, C))
    return group(name, P)


# ---------------------------------------------------------------- pit equipment
def wheel_gun(name):
    M = palette()
    P = [cyl(name + "_body", 0.06, 0.38, material=M["grey"], rot=(math.pi / 2, 0, 0), bev=0.01),
         cyl(name + "_nose", 0.045, 0.1, (0, 0.22, 0), M["chrome"], rot=(math.pi / 2, 0, 0)),
         box(name + "_grip", (0.04, 0.06, 0.18), (0, -0.05, -0.12), M["dark"], bev=0.015),
         box(name + "_handle", (0.04, 0.12, 0.05), (0, 0.06, 0.09), M["dark"], bev=0.015)]
    return group(name, P)


def lollipop(name):
    import lib
    M = palette()
    if lib.STYLE.get("voxel"):  # pixel disc built row by row, white bar across the middle
        px = 0.045
        P = [box(name + "_pole", (px, px, 1.5), (0, 0, 0.75), M["grey"])]
        r = 6
        for j in range(-r, r):
            half = int(math.sqrt(max(0, r * r - (j + 0.5) ** 2)) + 0.5)
            if half <= 0:
                continue
            m = M["white"] if j in (-1, 0) else M["red"]
            P.append(box(name + f"_row{j}", (2 * half * px, 0.03, px), (0, 0, 1.55 + (j + 0.5) * px), m))
        return group(name, P)
    P = [cyl(name + "_pole", 0.018, 1.6, (0, 0, 0.8), M["grey"]),
         cyl(name + "_disc", 0.26, 0.03, (0, 0, 1.55), M["red"], rot=(math.pi / 2, 0, 0), bev=0.01)]
    return group(name, P)


def jack(name, length=1.4):
    M = palette()
    P = [box(name + "_bar", (0.08, length, 0.08), (0, -length / 2, 0.12), M["grey"], bev=0.02),
         box(name + "_head", (0.5, 0.12, 0.1), (0, 0.02, 0.16), M["dark"], bev=0.02),
         box(name + "_handle", (0.5, 0.06, 0.05), (0, -length, 0.14), M["dark"], bev=0.02)]
    for s in (1, -1):
        P.append(cyl(name + f"_wheel{s}", 0.06, 0.04, (s * 0.12, -0.15, 0.06), M["rubber"], rot=(0, math.pi / 2, 0)))
    return group(name, P)


def tyre_loose(name, r=0.36, w=0.36):
    return wheel(name, r, w, 1)


# ---------------------------------------------------------------- hospital equipment
def cot(name, baby=True, tubes=True):
    """Intensive-care transport cot: wheeled base, mattress, clear side panels, a tiny swaddled baby."""
    M = palette()
    P = []
    P.append(box(name + "_base", (0.75, 1.1, 0.08), (0, 0, 0.32), M["white"], bev=0.03))
    P.append(box(name + "_mattress", (0.62, 0.95, 0.09), (0, 0, 0.66), M["blanket"], bev=0.04))
    P.append(box(name + "_tray", (0.7, 1.05, 0.06), (0, 0, 0.6), M["white"], bev=0.025))
    for s in (1, -1):
        P.append(box(name + f"_side{s}", (0.015, 1.0, 0.22), (s * 0.34, 0, 0.75), M["glass"], bev=0.007))
        P.append(box(name + f"_end{s}", (0.68, 0.015, 0.22), (0, s * 0.51, 0.75), M["glass"], bev=0.007))
    for sx in (1, -1):
        for sy in (1, -1):
            P.append(cyl(name + f"_leg{sx}{sy}", 0.022, 0.3, (sx * 0.3, sy * 0.45, 0.45), M["steel"]))
            P.append(cyl(name + f"_castor{sx}{sy}", 0.05, 0.035, (sx * 0.32, sy * 0.48, 0.06), M["dark"], rot=(0, math.pi / 2, 0)))
            P.append(cyl(name + f"_post{sx}{sy}", 0.018, 0.22, (sx * 0.3, sy * 0.45, 0.2), M["steel"]))
    P.append(box(name + "_shelf", (0.6, 0.9, 0.03), (0, 0, 0.12), M["white"], bev=0.01))
    import lib
    if baby and lib.STYLE.get("voxel"):  # block baby: cube head (face up), closed eyes, rosy cheeks, knitted hat, blanket
        warm = mat("babyblanket", (0.92, 0.5, 0.08), 0.85)
        hat = mat("babyhat", (0.98, 0.9, 0.75), 0.9)
        px = 0.045
        hx, hy, hz = 0, 0.3, 0.775  # head centre; the face is the top (+Z) side
        P.append(box(name + "_head", (4 * px, 4 * px, 3 * px), (hx, hy, hz), M["babyskin"]))
        P.append(box(name + "_hat", (4 * px + 0.01, 1.5 * px, 3 * px + 0.01), (hx, hy + 1.6 * px, hz), hat))
        top = hz + 1.5 * px + 0.003
        for s in (1, -1):
            P.append(box(name + f"_eye{s}", (px, 0.4 * px, 0.006), (s * px, hy + 0.2 * px, top), M["dark"]))
            P.append(box(name + f"_cheek{s}", (px, px, 0.005), (s * 1.4 * px, hy - 0.8 * px, top), mat("cheek", (0.95, 0.5, 0.45), 0.6)))
        P.append(box(name + "_mouth", (0.8 * px, 0.4 * px, 0.006), (0, hy - 1.3 * px, top), mat("mouth", (0.42, 0.22, 0.18), 0.6)))
        P.append(box(name + "_body", (6 * px, 7 * px, 2.4 * px), (0, 0.04, 0.745), warm))
        P.append(box(name + "_fold", (6 * px + 0.01, 1 * px, 2.4 * px + 0.012), (0, 0.18, 0.75), hat))
        # breathing tube and two lines, built as thin blocks so they stay clean on the grid
        tubec = mat("tubeclear", (0.85, 0.92, 0.95), 0.2, alpha=0.75)
        P.append(box(name + "_et1", (px * 0.6, 3 * px, px * 0.6), (0.02, 0.3 - 0.05, top + 0.5 * px), tubec))
        P.append(box(name + "_et2", (px * 0.6, px * 0.6, 5 * px), (0.02, 0.3 - 0.12, top + 2.6 * px), tubec))
        P.append(box(name + "_et3", (4 * px, px * 0.6, px * 0.6), (0.11, 0.3 - 0.12, top + 5.0 * px), tubec))
        P.append(box(name + "_line1", (px * 0.4, 6 * px, px * 0.4), (-0.12, 0.05, 0.81), M["red"]))
        P.append(box(name + "_line2", (px * 0.4, px * 0.4, 6 * px), (-0.12, -0.08, 0.92), M["red"]))
        tubes = False
    elif baby:
        warm = mat("babyblanket", (0.92, 0.5, 0.08), 0.85)
        P.append(sphere(name + "_head", 0.072, (0, 0.27, 0.76), M["babyskin"], scale=(1, 1.05, 0.95)))
        P.append(sphere(name + "_hat", 0.074, (0, 0.29, 0.785), mat("babyhat", (0.98, 0.9, 0.75), 0.9), scale=(1.02, 0.8, 0.75)))
        P.append(sphere(name + "_body", 1, (0, 0.06, 0.75), warm, scale=(0.13, 0.21, 0.065)))
        P.append(sphere(name + "_blanket", 1, (0, -0.02, 0.72), warm, scale=(0.24, 0.3, 0.05)))
    if tubes:
        P.append(tube(name + "_et", [V((0, 0.33, 0.74)), V((0.05, 0.45, 0.8)), V((0.2, 0.5, 0.95))], 0.008, M["tube"]))
        P.append(tube(name + "_line1", [V((-0.05, 0.1, 0.76)), V((-0.2, 0.2, 0.85)), V((-0.33, 0.35, 1.0))], 0.004, M["tube"]))
        P.append(tube(name + "_line2", [V((0.06, 0.05, 0.76)), V((0.22, 0.0, 0.88)), V((0.33, -0.2, 1.05))], 0.004, M["red"]))
    return group(name, P)


def monitor(name, w=0.42, h=0.3, wave=True):
    M = palette()
    P = [box(name + "_case", (w, 0.06, h), (0, 0, 0), M["white"], bev=0.02),
         box(name + "_screen", (w * 0.86, 0.01, h * 0.78), (0, 0.031, 0), M["screen"], bev=0.004)]
    if wave:
        pts = []
        for i in range(25):
            x = -w * 0.38 + i * w * 0.76 / 24
            z = 0.06 * h / 0.3 if i in (9, 19) else (-0.03 if i in (10, 20) else 0)
            pts.append(V((x, 0.038, h * 0.12 + z)))
        P.append(tube(name + "_ecg", pts, 0.0025, M["green"], res=2))
        P.append(box(name + "_line2", (w * 0.6, 0.004, 0.004), (0, 0.038, -h * 0.15), M["green"]))
    return group(name, P)


def iv_pole(name, h=1.9):
    M = palette()
    P = [cyl(name + "_pole", 0.012, h, (0, 0, h / 2), M["steel"]),
         box(name + "_hook", (0.25, 0.012, 0.012), (0, 0, h), M["steel"]),
         box(name + "_bag", (0.09, 0.03, 0.15), (0.1, 0, h - 0.12), M["tube"], bev=0.015)]
    for i in range(5):
        a = 2 * math.pi * i / 5
        P.append(box(name + f"_foot{i}", (0.28, 0.025, 0.02), (0.14 * math.cos(a), 0.14 * math.sin(a), 0.05), M["steel"],
                     rot=(0, 0, a)))
    return group(name, P)


def vent(name):
    """Ventilator cart: wheeled body with a screen and hose."""
    M = palette()
    P = [box(name + "_body", (0.4, 0.35, 0.9), (0, 0, 0.6), M["white"], bev=0.03),
         box(name + "_screen", (0.3, 0.02, 0.22), (0, 0.18, 1.0), M["screen"], bev=0.01),
         box(name + "_panel", (0.3, 0.02, 0.1), (0, 0.18, 0.75), M["clay2"], bev=0.01)]
    for sx in (1, -1):
        for sy in (1, -1):
            P.append(cyl(name + f"_c{sx}{sy}", 0.04, 0.03, (sx * 0.15, sy * 0.13, 0.05), M["dark"], rot=(0, math.pi / 2, 0)))
    return group(name, P)


def op_table(name):
    M = palette()
    P = [box(name + "_top", (0.6, 1.9, 0.1), (0, 0, 0.95), M["clay2"], bev=0.04),
         box(name + "_pad", (0.56, 1.85, 0.06), (0, 0, 1.02), M["dark"], bev=0.03),
         cyl(name + "_column", 0.12, 0.8, (0, 0, 0.5), M["white"]),
         box(name + "_foot", (0.55, 0.9, 0.1), (0, 0, 0.05), M["white"], bev=0.04)]
    return group(name, P)


def surgical_lamp(name, arm_len=1.0):
    M = palette()
    P = [cyl(name + "_dish", 0.38, 0.12, (0, 0, 0), M["white"], r2=0.3, bev=0.02),
         cyl(name + "_glow", 0.3, 0.02, (0, 0, -0.065), M["lamp"]),
         cyl(name + "_arm", 0.03, arm_len, (0, 0, 0.06 + arm_len / 2), M["white"])]
    return group(name, P)


def drapes(name, l=1.6, w=0.95):
    M = palette()
    d = box(name, (w, l, 0.06), (0, 0, 0), M["gown"], bev=0.025)
    return d


def clipboard(name, ticks=0, rows=5):
    M = palette()
    P = [box(name + "_board", (0.24, 0.32, 0.012), (0, 0, 0), M["clay2"], bev=0.004),
         box(name + "_paper", (0.21, 0.28, 0.004), (0, -0.01, 0.008), M["white"]),
         box(name + "_clip", (0.09, 0.03, 0.02), (0, 0.15, 0.012), M["steel"], bev=0.005)]
    for i in range(rows):
        y = 0.09 - i * 0.05
        P.append(box(name + f"_box{i}", (0.022, 0.022, 0.004), (-0.075, y - 0.01, 0.011), M["grey"]))
        P.append(box(name + f"_line{i}", (0.12, 0.008, 0.003), (0.02, y - 0.01, 0.011), M["clay2"]))
        if i < ticks:
            P.append(box(name + f"_tick{i}", (0.026, 0.026, 0.006), (-0.075, y - 0.01, 0.013), M["red"], bev=0.004))
    return group(name, P)


def f1car_block(name="car", body="red", driver=True):
    """The car built from blocks on purpose (blocky style): stepped nose, slab sidepods, plank wings, voxel wheels."""
    M = palette()
    B, C, W = M[body], M["dark"], M["white"]
    P = []

    def b(n, size, loc, m=B, rot=(0, 0, 0)):
        P.append(box(name + "_" + n, size, loc, m, rot=rot))

    b("floor", (1.4, 3.7, 0.05), (0, -0.3, 0.07), C)
    # monocoque: stepped blocks from nose to tail
    for i, (w, l, h, y, z) in enumerate([(0.16, 0.5, 0.1, 2.55, 0.27), (0.24, 0.5, 0.16, 2.1, 0.31),
                                         (0.34, 0.6, 0.22, 1.55, 0.36), (0.46, 0.7, 0.28, 0.95, 0.41),
                                         (0.58, 1.2, 0.3, 0.1, 0.45), (0.5, 0.9, 0.34, -0.9, 0.48),
                                         (0.34, 0.6, 0.26, -1.6, 0.43), (0.2, 0.45, 0.18, -2.1, 0.38)]):
        b(f"mono{i}", (w, l, h), (0, y, z))
    b("nose_stripe", (0.245, 0.5, 0.012), (0, 2.1, 0.395), W)
    b("cockpit", (0.36, 0.62, 0.02), (0, 0.3, 0.605), C)
    b("airbox", (0.24, 0.7, 0.22), (0, -0.45, 0.76))
    b("intake", (0.14, 0.02, 0.12), (0, -0.09, 0.79), C)
    b("fin", (0.03, 1.0, 0.16), (0, -1.15, 0.72))
    if driver:
        b("helmet", (0.22, 0.24, 0.2), (0, 0.12, 0.7), M["yellow"])
        b("hvisor", (0.18, 0.02, 0.06), (0, 0.245, 0.72), C)
    # halo: three bars and a pillar
    b("halo_pillar", (0.05, 0.05, 0.22), (0, 0.78, 0.68), C)
    b("halo_top", (0.05, 0.35, 0.05), (0, 0.6, 0.81), C)
    for s in (1, -1):
        b(f"halo_side{s}", (0.05, 0.55, 0.05), (s * 0.24, 0.18, 0.81), C)
    b("halo_back", (0.53, 0.05, 0.05), (0, -0.08, 0.81), C)
    for s in (1, -1):
        b(f"pod{s}", (0.4, 1.5, 0.3), (s * 0.48, -0.05, 0.37))
        b(f"podtail{s}", (0.26, 0.6, 0.2), (s * 0.4, -1.05, 0.32))
        b(f"inlet{s}", (0.3, 0.03, 0.18), (s * 0.48, 0.71, 0.38), C)
        b(f"mirror{s}", (0.14, 0.05, 0.07), (s * 0.45, 0.62, 0.66))
        b(f"mstalk{s}", (0.12, 0.03, 0.03), (s * 0.34, 0.62, 0.6), C)
        b(f"fwep{s}", (0.04, 0.5, 0.2), (s * 0.94, 2.66, 0.17), C)
        b(f"rwep{s}", (0.05, 0.62, 0.56), (s * 0.52, -2.42, 0.72))
        for nm, y in (("f", 1.8), ("r", -1.78)):  # suspension arms as flat dark planks
            b(f"arm{nm}{s}", (0.5, 0.06, 0.04), (s * 0.5, y, 0.36), C)
    b("fw_main", (1.9, 0.36, 0.04), (0, 2.76, 0.11), C)
    b("fw_flap", (1.7, 0.18, 0.04), (0, 2.6, 0.19))
    b("fw_flap2", (1.5, 0.12, 0.04), (0, 2.49, 0.25))
    b("rw_main", (1.04, 0.32, 0.05), (0, -2.42, 0.84), C)
    b("rw_flap", (1.04, 0.2, 0.05), (0, -2.55, 0.97))
    b("rw_pillar", (0.04, 0.12, 0.4), (0, -2.3, 0.6), C)
    b("beam", (0.8, 0.14, 0.04), (0, -2.35, 0.4), C)
    for (y, x, w, r, nm) in [(1.8, 0.8, 0.31, 0.36, "f"), (-1.78, 0.78, 0.41, 0.37, "r")]:
        for s in (1, -1):
            wh = wheel(name + f"_w{nm}{s}", r, w, s)
            wh.location = (s * x, y, r)
            P.append(wh)
    return group(name, P)
