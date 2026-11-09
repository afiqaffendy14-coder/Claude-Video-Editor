"""2026 F1 hero car: the voxel blueprint (the single source of truth for every view, sheet and video).

Pure numpy, no Blender. build(**opts) returns the voxel grid:
  m    (NX, NY, NZ) uint8  material id per voxel (0 = empty), see MATS
  part (NX, NY, NZ) uint8  which object the voxel belongs to, see PARTS
  rgb  (NX, NY, NZ, 3)     linear colour per voxel (the pixel texture: one texel per voxel)

Scale: one voxel = 2.25 cm = half the house world pixel (voxel.PX = 4.5 cm), so the car sits on the same grid as
every set and character, at twice the detail. Axes: +Y forward, +X the driver's right, +Z up, ground at z = 0,
origin halfway along the wheelbase. Real 2026 dimensions: wheelbase 3.375 m, width 1.89 m, tyres 0.72 m tall
(front 0.27 m wide, rear 0.36 m wide), 18-inch rims, height 1.0 m.
"""
import math
import numpy as np

VOX = 0.0225
NX, NY, NZ = 88, 240, 46
X0, Y0, Z0 = -NX / 2 * VOX, -116 * VOX, 0.0

xs = X0 + (np.arange(NX) + 0.5) * VOX
ys = Y0 + (np.arange(NY) + 0.5) * VOX
zs = Z0 + (np.arange(NZ) + 0.5) * VOX
X, Y, Z = xs[:, None, None], ys[None, :, None], zs[None, None, :]
AX = np.abs(X)
SHAPE = (NX, NY, NZ)

# wheels: axles on voxel boundaries so every tyre is a symmetric circle
WB_HALF = 75 * VOX            # 1.6875 -> wheelbase 3.375 m
R_TYRE = 16 * VOX             # 0.36
WHEELS = {  # name: (centre x, centre y, width, front?)
    "FL": (-36 * VOX, WB_HALF, 12 * VOX, True), "FR": (36 * VOX, WB_HALF, 12 * VOX, True),
    "RL": (-34 * VOX, -WB_HALF, 16 * VOX, False), "RR": (34 * VOX, -WB_HALF, 16 * VOX, False),
}

# ---------------------------------------------------------------- parts (become separate Blender objects)
BODY, SUSP, STEER = 1, 2, 4
PARTS = {"body": [BODY], "suspension": [SUSP], "steering_wheel": [STEER]}
WHEEL_PART = {}
for n, w in enumerate(WHEELS):
    WHEEL_PART[w] = dict(tyre=10 + n, rim=20 + n, disc=40 + n, brake=30 + n)
    for k, v in WHEEL_PART[w].items():
        PARTS[f"{k}_{w}"] = [v]


def _hex(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]


# ---------------------------------------------------------------- materials: id -> look
# metal, rough, emit (strength), noise (pixel-texture amplitude)
MATS = {
    1: dict(name="silver_paint", hex="#AEB3B9", metal=0.85, rough=0.25, noise=0.05),
    2: dict(name="black_paint", hex="#111214", metal=0.1, rough=0.22, noise=0.10),
    3: dict(name="carbon", hex="#121316", hex2="#1C1E22", metal=0.0, rough=0.42, noise=0.06),
    4: dict(name="teal", hex="#00A19B", metal=0.15, rough=0.3, noise=0.06),
    5: dict(name="decal_white", hex="#EEEEEE", metal=0.0, rough=0.35, noise=0.04),
    6: dict(name="tread", hex="#2B2B2D", metal=0.0, rough=0.88, noise=0.12),
    7: dict(name="sidewall", hex="#19191B", metal=0.0, rough=0.62, noise=0.08),
    8: dict(name="rim", hex="#141416", metal=0.55, rough=0.3, noise=0.06),
    9: dict(name="wheel_nut", hex="#B6E61E", metal=0.2, rough=0.35, noise=0.05),
    10: dict(name="compound_band", hex="#FFD100", metal=0.0, rough=0.5, noise=0.04),
    11: dict(name="plank", hex="#6B4F33", metal=0.0, rough=0.7, noise=0.14),
    12: dict(name="titanium", hex="#8E949A", metal=0.9, rough=0.32, noise=0.06),
    13: dict(name="brake_disc", hex="#3B3431", metal=0.1, rough=0.7, noise=0.14),
    14: dict(name="caliper", hex="#2C2E33", metal=0.35, rough=0.4, noise=0.06),
    15: dict(name="rain_light", hex="#FF2A1F", metal=0.0, rough=0.3, emit=6.0, noise=0.03),
    16: dict(name="helmet_base", hex="#E6E8EA", metal=0.2, rough=0.22, noise=0.04),
    17: dict(name="visor", hex="#0C1116", metal=0.6, rough=0.08, noise=0.03),
    18: dict(name="cavity", hex="#050506", metal=0.0, rough=0.8, noise=0.05),
    19: dict(name="star_grey", hex="#B4BAC1", metal=0.5, rough=0.3, noise=0.04),
    20: dict(name="exhaust", hex="#9A9AA4", metal=0.9, rough=0.3, noise=0.04),
    21: dict(name="radiator", hex="#2A2C2F", hex2="#121314", metal=0.4, rough=0.5, noise=0.04),
    22: dict(name="mirror_glass", hex="#A9BCCB", metal=1.0, rough=0.05, noise=0.02),
    23: dict(name="pad", hex="#2B2F36", metal=0.0, rough=0.75, noise=0.08),
    24: dict(name="screen", hex="#2BE0B2", metal=0.0, rough=0.3, emit=2.5, noise=0.05),
    25: dict(name="button_red", hex="#E8322A", metal=0.0, rough=0.4, noise=0.03),
    26: dict(name="button_yellow", hex="#F6C21C", metal=0.0, rough=0.4, noise=0.03),
    27: dict(name="button_blue", hex="#2A7BEA", metal=0.0, rough=0.4, noise=0.03),
    28: dict(name="cockpit", hex="#0B0C0E", metal=0.0, rough=0.7, noise=0.08),
    29: dict(name="helmet_accent", hex="#00A19B", metal=0.2, rough=0.22, noise=0.04),
    30: dict(name="helmet_dark", hex="#15171A", metal=0.2, rough=0.25, noise=0.04),
    31: dict(name="tread_dark", hex="#121213", metal=0.0, rough=0.9, noise=0.05),
    32: dict(name="wing_paint", hex="#111214", metal=0.1, rough=0.22, noise=0.10),
    33: dict(name="halo_paint", hex="#111214", metal=0.1, rough=0.22, noise=0.10),
    34: dict(name="accent2", hex="#FFCC00", metal=0.1, rough=0.3, noise=0.05),
    35: dict(name="lower_paint", hex="#1C1D20", metal=0.1, rough=0.3, noise=0.08),
}
SILVER, BLACK, CARBON, TEAL, WHITE, TREAD, SIDEWALL, RIM, NUT, BAND, PLANK, TITAN, DISC, CALIPER, RAIN, \
    HELM, VISOR, CAVITY, STAR, EXHAUST, RADIATOR, MIRROR, PAD, SCREEN, BRED, BYEL, BBLUE, COCKPIT, HELM_ACC, \
    HELM_DARK, TREAD_DARK, WING, HALO, ACCENT2, LOWER = range(1, 36)
# Paint slots a livery recolours: SILVER (nose and pod tops), BLACK (body), TEAL (accent pin lines), WING, HALO,
# LOWER (lower body, when the livery's pattern asks), ACCENT2, STAR (pattern colour), WHITE (decals).

COMPOUNDS = {"soft": "#E10600", "medium": "#FFD100", "hard": "#F0F0F0", "inter": "#43B02A", "wet": "#0067AD"}

# Liveries are data: a new team is a new entry here, the geometry never changes.
# Each team is an "inspired" livery: its colours on the same car, no real logos. paint: slot -> (hex, metal, rough)
LIVERIES = {
    "silver_arrow": dict(  # Mercedes-inspired: silver nose and pod tops, black body, teal, claw stripes + stars
        number="63", patterns=("claws", "stars"),
        paint={SILVER: ("#AEB3B9", 0.85, 0.25), BLACK: ("#111214", 0.1, 0.22), TEAL: ("#00A19B", 0.15, 0.3),
               WING: ("#111214", 0.1, 0.22), HALO: ("#111214", 0.1, 0.22), STAR: ("#B4BAC1", 0.5, 0.3),
               WHITE: ("#EEEEEE", 0.0, 0.35)},
        number_top=BLACK, number_side=TEAL,
        decals=dict(sidepod="KYNEX", endplate="ORVA", halo="ORVA"),
    ),
    "rosso": dict(  # Ferrari-inspired: red body, white pin lines and decals, black lower body and wings
        number="16", patterns=("lower",),
        paint={SILVER: ("#D10A11", 0.2, 0.22), BLACK: ("#C3070E", 0.2, 0.22), TEAL: ("#F2F2F2", 0.0, 0.3),
               WING: ("#141416", 0.1, 0.25), HALO: ("#C3070E", 0.2, 0.22), LOWER: ("#141416", 0.1, 0.3),
               WHITE: ("#F2F2F2", 0.0, 0.35), ACCENT2: ("#FFD400", 0.1, 0.3)},
        number_top=WHITE, number_side=WHITE,
        decals=dict(sidepod="VELTRO", endplate="ORVA", halo="TEKNA"),
    ),
    "papaya": dict(  # McLaren-inspired: papaya body, anthracite lower body, wings and halo
        number="81", patterns=("lower",),
        paint={SILVER: ("#FF7A00", 0.1, 0.25), BLACK: ("#FF7A00", 0.1, 0.25), TEAL: ("#1E1F22", 0.1, 0.3),
               WING: ("#1E1F22", 0.1, 0.3), HALO: ("#1E1F22", 0.1, 0.3), LOWER: ("#1E1F22", 0.1, 0.3),
               WHITE: ("#1E1F22", 0.0, 0.35)},
        number_top=TEAL, number_side=WHITE,
        decals=dict(sidepod="ORVA", endplate="KYNEX", halo="TEKNA"),
    ),
    "midnight": dict(  # Red Bull-inspired: matte navy, red pin lines, yellow nose tip
        number="3", patterns=("nose_tip",),
        paint={SILVER: ("#1C2445", 0.2, 0.55), BLACK: ("#1C2445", 0.2, 0.55), TEAL: ("#E1062C", 0.1, 0.35),
               WING: ("#1C2445", 0.2, 0.55), HALO: ("#1C2445", 0.2, 0.55), ACCENT2: ("#FFC906", 0.1, 0.35),
               WHITE: ("#F2F2F2", 0.0, 0.4)},
        number_top=WHITE, number_side=WHITE,
        decals=dict(sidepod="TEKNA", endplate="VELTRO", halo="KYNEX"),
    ),
}

TITLES = {"silver_arrow": "Silver Arrow livery (Mercedes-inspired)", "rosso": "Rosso livery (Ferrari-inspired)",
          "papaya": "Papaya livery (McLaren-inspired)", "midnight": "Midnight livery (Red Bull-inspired)"}
for _k, _t in TITLES.items():
    LIVERIES[_k]["title"] = _t


def mat_spec(mid, livery="silver_arrow", compound="medium"):
    """A material slot's look for this livery (colour, metal, rough)."""
    d = dict(MATS[mid])
    L = LIVERIES[livery]
    if mid in L["paint"]:
        d["hex"], d["metal"], d["rough"] = L["paint"][mid]
    if mid == BAND:
        d["hex"] = COMPOUNDS[compound]
    return d


# ---------------------------------------------------------------- fonts (pixel, rows top -> bottom)
F35 = {
    "A": [".#.", "#.#", "###", "#.#", "#.#"], "B": ["##.", "#.#", "##.", "#.#", "##."],
    "C": [".##", "#..", "#..", "#..", ".##"], "D": ["##.", "#.#", "#.#", "#.#", "##."],
    "E": ["###", "#..", "##.", "#..", "###"], "F": ["###", "#..", "##.", "#..", "#.."],
    "G": [".##", "#..", "#.#", "#.#", ".##"], "H": ["#.#", "#.#", "###", "#.#", "#.#"],
    "I": ["###", ".#.", ".#.", ".#.", "###"], "J": ["..#", "..#", "..#", "#.#", ".#."],
    "K": ["#.#", "#.#", "##.", "#.#", "#.#"], "L": ["#..", "#..", "#..", "#..", "###"],
    "M": ["#.#", "###", "###", "#.#", "#.#"], "N": ["##.", "#.#", "#.#", "#.#", "#.#"],
    "O": [".#.", "#.#", "#.#", "#.#", ".#."], "P": ["##.", "#.#", "##.", "#..", "#.."],
    "Q": [".#.", "#.#", "#.#", "##.", ".##"], "R": ["##.", "#.#", "##.", "#.#", "#.#"],
    "S": [".##", "#..", ".#.", "..#", "##."], "T": ["###", ".#.", ".#.", ".#.", ".#."],
    "U": ["#.#", "#.#", "#.#", "#.#", "###"], "V": ["#.#", "#.#", "#.#", "#.#", ".#."],
    "W": ["#.#", "#.#", "###", "###", "#.#"], "X": ["#.#", "#.#", ".#.", "#.#", "#.#"],
    "Y": ["#.#", "#.#", ".#.", ".#.", ".#."], "Z": ["###", "..#", ".#.", "#..", "###"],
    "0": ["###", "#.#", "#.#", "#.#", "###"], "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["##.", "..#", ".#.", "#..", "###"], "3": ["##.", "..#", ".#.", "..#", "##."],
    "4": ["#.#", "#.#", "###", "..#", "..#"], "5": ["###", "#..", "##.", "..#", "##."],
    "6": [".##", "#..", "###", "#.#", "###"], "7": ["###", "..#", ".#.", ".#.", ".#."],
    "8": ["###", "#.#", "###", "#.#", "###"], "9": ["###", "#.#", "###", "..#", "##."],
    " ": ["...", "...", "...", "...", "..."], "-": ["...", "...", "###", "...", "..."],
}
F33 = {  # tiny sidewall letters
    "S": [".##", ".#.", "##."], "L": ["#..", "#..", "###"], "I": ["#", "#", "#"], "C": ["###", "#..", "###"],
    "K": ["#.#", "##.", "#.#"], " ": [".", ".", "."],
}
F57 = {
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."],
}


def text_bitmap(text, font=F35, scale=1, spacing=1):
    glyphs = [np.array([[c == "#" for c in row] for row in font.get(ch) or font[" "]]) for ch in text]
    h = glyphs[0].shape[0]
    cols = []
    for i, g in enumerate(glyphs):
        cols.append(g)
        if i < len(glyphs) - 1:
            cols.append(np.zeros((h, spacing), bool))
    bm = np.concatenate(cols, axis=1)
    return np.kron(bm, np.ones((scale, scale), bool)).astype(bool)


# ---------------------------------------------------------------- helpers
def fy(yp, vp):
    """A profile along the car: values at stations yp, linear in between (shape 1, NY, 1)."""
    yp, vp = np.asarray(yp, float), np.asarray(vp, float)
    o = np.argsort(yp)
    return np.interp(ys, yp[o], vp[o])[None, :, None]


def between(a, lo, hi):
    return (a >= lo) & (a <= hi)


def smoothstep(e0, e1, v):
    t = np.clip((v - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def to_i(v, axis):
    o = (X0, Y0, Z0)[axis]
    return int(math.floor((v - o) / VOX))


def irange(lo, hi, axis):
    n = SHAPE[axis]
    o = (X0, Y0, Z0)[axis]
    return max(0, int(math.floor((lo - o) / VOX))), min(n, int(math.ceil((hi - o) / VOX)) + 1)


def tube(points, r, rz=None):
    """Voxels within an elliptic radius (r sideways, rz vertical) of a polyline."""
    rz = rz or r
    out = np.zeros(SHAPE, bool)
    rm = max(r, rz)
    for a, b in zip(points[:-1], points[1:]):
        a, b = np.array(a, float), np.array(b, float)
        lo, hi = np.minimum(a, b) - rm, np.maximum(a, b) + rm
        (i0, i1), (j0, j1), (k0, k1) = (irange(lo[n], hi[n], n) for n in range(3))
        px, py, pz = xs[i0:i1, None, None], ys[None, j0:j1, None], zs[None, None, k0:k1]
        ab = b - a
        t = np.clip(((px - a[0]) * ab[0] + (py - a[1]) * ab[1] + (pz - a[2]) * ab[2]) / (ab @ ab), 0, 1)
        dx, dy, dz = px - (a[0] + t * ab[0]), py - (a[1] + t * ab[1]), pz - (a[2] + t * ab[2])
        out[i0:i1, j0:j1, k0:k1] |= (dx * dx + dy * dy) / r ** 2 + dz * dz / rz ** 2 <= 1.0
    return out


def catmull(pts, n=10):
    """Smooth a control polyline (Catmull-Rom), so stepped curves follow a real curve."""
    P = [np.array(p, float) for p in pts]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return out


def mirror(pts):
    return [(-x, y, z) for x, y, z in pts]


class Grid:
    def __init__(self):
        self.m = np.zeros(SHAPE, np.uint8)
        self.p = np.zeros(SHAPE, np.uint8)

    def put(self, mask, mat, part=BODY):
        mask = np.broadcast_to(mask, SHAPE)
        self.m[mask] = mat
        self.p[mask] = part

    def add(self, mask, mat, part=BODY):
        """Fill only empty voxels (never overwrite another part)."""
        mask = np.broadcast_to(mask, SHAPE) & (self.m == 0)
        self.m[mask] = mat
        self.p[mask] = part

    def cut(self, mask):
        mask = np.broadcast_to(mask, SHAPE)
        self.m[mask] = 0
        self.p[mask] = 0

    def paint(self, mask, mat, parts=(BODY,), only=None):
        sel = np.broadcast_to(mask, SHAPE) & (self.m > 0)
        if parts is not None:
            sel &= np.isin(self.p, parts)
        if only is not None:
            sel &= np.isin(self.m, only)
        self.m[sel] = mat

    def stamp(self, bm, centre, right, up, mat, depth=None, parts=(BODY,), only=None):
        """Paint a 2D bitmap onto the surface. right/up are signed axes like '+x', '-y'; the bitmap is projected
        along the remaining axis, limited to `depth` (lo, hi) metres on that axis."""
        ax = {"x": 0, "y": 1, "z": 2}
        ra, rs = ax[right[1]], (1 if right[0] == "+" else -1)
        ua, us = ax[up[1]], (1 if up[0] == "+" else -1)
        da = 3 - ra - ua
        c = [to_i(centre[n], n) for n in range(3)]
        h, w = bm.shape
        mask = np.zeros(SHAPE, bool)
        lo, hi = irange(*(depth if depth else (-9, 9)), da)
        for r_, c_ in zip(*np.nonzero(bm)):
            idx = [0, 0, 0]
            idx[ra] = c[ra] + rs * (c_ - w // 2)
            idx[ua] = c[ua] + us * (h // 2 - r_)
            if not (0 <= idx[ra] < SHAPE[ra] and 0 <= idx[ua] < SHAPE[ua]):
                continue
            sl = [None, None, None]
            sl[ra], sl[ua], sl[da] = idx[ra], idx[ua], slice(lo, hi)
            mask[tuple(sl)] = True
        self.paint(mask, mat, parts, only)


# ---------------------------------------------------------------- the car
def build(livery="silver_arrow", number=None, compound="medium"):
    L = LIVERIES[livery]
    number = number or L["number"]
    pats = L["patterns"]
    g = Grid()
    PAINT = (SILVER, BLACK, TEAL)

    # ---- survival cell and nose (one swept, rounded section from the nose tip to behind the cockpit)
    cy = [-0.40, -0.10, 0.20, 0.60, 0.90, 1.20, 1.50, 1.80, 2.10, 2.40, 2.66]
    ch_w = fy(cy, [0.31, 0.33, 0.33, 0.32, 0.28, 0.24, 0.205, 0.155, 0.12, 0.09, 0.06])
    ch_b = fy(cy, [0.08, 0.08, 0.08, 0.08, 0.10, 0.13, 0.18, 0.19, 0.17, 0.14, 0.12])
    ch_t = fy(cy, [0.74, 0.74, 0.74, 0.72, 0.68, 0.63, 0.58, 0.50, 0.40, 0.31, 0.22])
    ch_c, ch_h = (ch_b + ch_t) / 2, (ch_t - ch_b) / 2
    chassis = ((AX / ch_w) ** 3.6 + (np.abs(Z - ch_c) / ch_h) ** 3.6 <= 1) & between(Y, -0.40, 2.66)
    g.put(chassis, BLACK)

    # ---- sidepods: undercut below, rounded shoulder above, downwash ramp to the coke-bottle waist
    sy = [-1.55, -1.20, -0.80, -0.20, 0.30, 0.48]
    sp_w = fy(sy, [0.27, 0.38, 0.52, 0.66, 0.68, 0.66])
    sp_t = fy(sy, [0.36, 0.42, 0.50, 0.60, 0.63, 0.60])
    sp_b = fy(sy, [0.10, 0.10, 0.14, 0.20, 0.27, 0.30])
    sp_m = sp_b + 0.62 * (sp_t - sp_b)
    up_t = np.clip((Z - sp_m) / (sp_t - sp_m), 0, 1)
    lo_t = np.clip((sp_m - Z) / (sp_m - sp_b), 0, 1)
    sp_xo = np.where(Z >= sp_m, sp_w * np.cbrt(np.clip(1 - up_t ** 3, 0, 1)), sp_w * (1 - 0.32 * lo_t ** 1.5))
    sidepod = (AX <= sp_xo) & between(Z, sp_b, sp_t) & between(Y, -1.55, 0.48)
    g.add(sidepod, BLACK)
    # inlets: a deep mouth in each pod front, radiator at the back of it
    inlet = (Y > 0.255) & between(AX, 0.33, sp_xo - 0.035) & between(Z, sp_b + 0.06, sp_t - 0.035)
    g.cut(inlet & sidepod)
    in_xz = between(AX, 0.3075, sp_xo - 0.0125) & between(Z, sp_b + 0.0375, sp_t - 0.0125)
    g.paint(sidepod & (Y > 0.2325) & in_xz, CAVITY)
    g.paint(sidepod & between(Y, 0.2325, 0.2575) & between(AX, 0.33, sp_xo - 0.035)
            & between(Z, sp_b + 0.06, sp_t - 0.035), RADIATOR)

    # ---- engine cover, airbox and roll structure
    ey = [-2.32, -2.05, -1.60, -1.10, -0.80, -0.58, -0.42, -0.29]
    ec_w = fy(ey, [0.08, 0.10, 0.14, 0.19, 0.21, 0.185, 0.16, 0.15])
    ec_t = fy(ey, [0.46, 0.50, 0.58, 0.72, 0.85, 0.95, 0.975, 0.95])
    ec_b = 0.20
    cover = ((AX / ec_w) ** 2.2 + (np.abs(Z - ec_b) / (ec_t - ec_b)) ** 2.2 <= 1) & (Z >= ec_b) & between(Y, -2.32, -0.29)
    g.add(cover, BLACK)
    intake = (Y > -0.52) & ((AX / 0.075) ** 2 + ((Z - 0.875) / 0.075) ** 2 <= 1) & (AX > 0.0225)
    g.cut(intake & cover)
    g.paint((Y > -0.55) & ((AX / 0.10) ** 2 + ((Z - 0.875) / 0.10) ** 2 <= 1) & (Y < -0.30) & (AX > 0.0225)
            & ((AX / 0.0975) ** 2 + ((Z - 0.875) / 0.0975) ** 2 <= 1.0), CAVITY, only=(BLACK,))
    # ear intakes either side of the airbox
    ear = between(Y, -0.54, -0.29) & between(AX, 0.10, 0.165) & between(Z, 0.70, 0.765)
    g.paint(ear & between(Y, -0.54, -0.42), CAVITY)
    # T-camera on a short stalk
    g.put(between(Y, -0.43, -0.375) & (AX < 0.09) & between(Z, 0.975, 1.005), BLACK)
    g.put(between(Y, -0.43, -0.375) & (AX < 0.0225) & between(Z, 0.95, 0.98), BLACK)
    # short fin along the spine
    fin_top = fy([-2.05, -1.60, -1.00, -0.60], [0.60, 0.70, 0.84, 0.94])
    g.add(between(Y, -2.05, -0.60) & (AX < 0.0225) & (Z <= fin_top) & (Z > 0.3), BLACK)
    # engine-cover cooling louvres and the rear outlet
    louv = between(Y, -1.15, -0.72) & ((np.floor((Y + 1.15) / VOX).astype(int) % 3) == 0)
    g.paint(louv & between(Z, ec_t - 0.13, ec_t - 0.05) & cover, CAVITY)
    g.paint(between(Y, -2.33, -2.27) & (AX < ec_w - 0.03) & (Z > 0.40) & cover, CAVITY)

    # ---- gearbox, rear crash structure, rain light, exhaust
    g.add(between(Y, -2.05, -1.50) & (AX < 0.14) & between(Z, 0.20, 0.46), CARBON)
    g.add(between(Y, -2.50, -2.05) & (AX < fy([-2.5, -2.05], [0.07, 0.12])) & between(Z, 0.24, 0.42), CARBON)
    g.put(between(Y, -2.53, -2.49) & (AX < 0.055) & between(Z, 0.31, 0.38), RAIN)
    exhaust = tube([(0, -2.05, 23 * VOX), (0, -2.44, 23 * VOX)], 0.05)
    g.put(exhaust, EXHAUST)
    g.cut(exhaust & (Y < -2.36) & (X ** 2 + (Z - 23 * VOX) ** 2 < 0.03 ** 2))
    g.paint(exhaust & (Y < -2.30) & (X ** 2 + (Z - 23 * VOX) ** 2 < 0.04 ** 2), CAVITY, only=(EXHAUST,))

    # ---- floor: lifted venturi entry, fences, edge wing, plank with skid blocks, diffuser
    fl_w = fy([-1.42, -1.20, -0.60, 0.60, 1.00, 1.30], [0.50, 0.56, 0.74, 0.76, 0.66, 0.40])
    lift = fy([0.85, 1.30], [0.0, 0.11])
    floor = between(Y, -1.42, 1.30) & (AX <= fl_w) & between(Z, 0.045 + lift, 0.09 + lift)
    g.add(floor, CARBON)
    g.add(between(Y, -1.00, 0.60) & between(AX, fl_w - 0.045, fl_w) & between(Z, 0.09, 0.135), CARBON)
    for xf in (0.18, 0.315, 0.45):
        g.add(between(Y, 0.95, 1.30) & between(AX, xf, xf + 0.0225) & between(Z, 0.045, 0.09 + lift), CARBON)
    g.add(between(Y, -1.05, 1.15) & (AX < 0.1575) & between(Z, 0.0225, 0.045), PLANK)
    for yb in (1.0, 0.25, -0.75):
        g.paint(between(Y, yb - 0.045, yb + 0.045) & (AX < 0.0675) & (Z < 0.045), TITAN, only=(PLANK,))
    for yb in (0.62, -0.30):
        g.paint(between(Y, yb - 0.012, yb + 0.012) & (AX < 0.0225) & (Z < 0.045), CAVITY, only=(PLANK,))
    roof = fy([-2.30, -1.40], [0.28, 0.06])
    g.add(between(Y, -2.30, -1.40) & (AX < 0.52) & between(Z, roof, roof + 0.045), CARBON)
    g.add(between(Y, -2.30, -1.40) & between(AX, 0.4975, 0.52) & between(Z, 0.03, roof), CARBON)
    for xf in (0.09, 0.2475, 0.3825):
        g.add(between(Y, -2.30, -1.55) & between(AX, xf, xf + 0.0225) & between(Z, 0.03, roof), CARBON)
    g.add(between(Y, -2.33, -2.30) & (AX < 0.52) & between(Z, 0.28, 0.35), CARBON)  # gurney at the exit

    # ---- front wing: main plane + two flaps sweeping up to complex endplates
    rise = 0.10 * smoothstep(0.25, 0.80, AX)

    def element(ya, yb, z0, z1, t0, t1, k, span):
        t = (ya - Y) / (ya - yb)
        zl = z0 + (z1 - z0) * np.clip(t, 0, 1) ** 1.3 + rise * k
        th = t0 * (1 - t) + t1 * t
        return between(t, 0, 1) & (Z >= zl) & (Z <= zl + th) & (AX <= span)

    fw_main = element(2.76, 2.46, 0.07, 0.105, 0.05, 0.03, 1.0, 0.87)
    fw_f1 = element(2.50, 2.32, 0.135, 0.19, 0.035, 0.025, 1.15, 0.865)
    fw_f2 = element(2.36, 2.20, 0.205, 0.27, 0.03, 0.025, 1.3, 0.865)
    for el in (fw_main, fw_f1, fw_f2):
        g.put(el, WING)
    ep_top = fy([2.18, 2.30, 2.55, 2.79], [0.30, 0.37, 0.33, 0.15])
    g.put(between(AX, 0.855, 0.90) & between(Y, 2.18, 2.79) & between(Z, 0.03, ep_top), WING)
    g.put(between(AX, 0.90, 0.945) & between(Y, 2.30, 2.74) & between(Z, 0.03, 0.075), WING)   # footplate
    g.put(between(AX, 0.90, 0.935) & between(Y, 2.42, 2.62) & between(Z, 0.20, 0.225), WING)   # canard
    for xf in (0.5625, 0.6975):  # strakes under the main plane
        g.add(between(AX, xf, xf + 0.0225) & between(Y, 2.48, 2.74) & between(Z, 0.03, 0.10), CARBON)
    g.paint(between(AX, 0.855, 0.90) & between(Y, 2.18, 2.60) & (Z > ep_top - 0.05), TEAL)  # endplate teal tip
    g.paint(fw_f2 & between(AX, 0.76, 0.855), TEAL)
    # pitot and nose camera pods
    g.put(between(Y, 2.30, 2.40) & between(AX, 0.0675, 0.135) & between(Z, 0.30, 0.345), BLACK)
    g.put(between(Y, 1.92, 2.00) & between(AX, 0.135, 0.18) & between(Z, 0.40, 0.445), BLACK)

    # ---- suspension (aero-section carbon wishbones), front pushrod, rear pullrod
    fy_ = WB_HALF
    for s in (1, -1):
        def rod(a, b, r=0.02, rz=0.014):
            g.add(tube([(s * a[0], a[1], a[2]), (s * b[0], b[1], b[2])], r, rz), CARBON, SUSP)
        rod((0.19, fy_ + 0.27, 0.52), (0.64, fy_, 0.53))
        rod((0.21, fy_ - 0.29, 0.55), (0.64, fy_, 0.53))
        rod((0.12, fy_ + 0.32, 0.25), (0.66, fy_, 0.20))
        rod((0.17, fy_ - 0.34, 0.22), (0.66, fy_, 0.20))
        rod((0.64, fy_ - 0.02, 0.21), (0.18, fy_ - 0.07, 0.56), 0.017, 0.017)
        rod((0.15, fy_ + 0.13, 0.40), (0.65, fy_ + 0.11, 0.40), 0.015, 0.015)
        ry = -WB_HALF
        rod((0.12, ry + 0.24, 0.48), (0.60, ry, 0.52))
        rod((0.12, ry - 0.26, 0.46), (0.60, ry, 0.52))
        rod((0.12, ry + 0.29, 0.22), (0.61, ry, 0.18))
        rod((0.12, ry - 0.31, 0.22), (0.61, ry, 0.18))
        rod((0.60, ry + 0.03, 0.50), (0.13, ry + 0.07, 0.24), 0.017, 0.017)
        rod((0.12, ry - 0.16, 0.33), (0.60, ry - 0.16, 0.33), 0.015, 0.015)
        g.add(tube([(s * 0.10, ry, 0.33), (s * 0.58, ry, 0.36)], 0.028), TITAN, SUSP)  # driveshaft

    # ---- rear wing: twin pylons, main plane, flap, endplates with rain lights
    for s in (1, -1):
        g.put(between(Y, -2.40, -2.20) & between(s * X, 0.0675, 0.09) & between(Z, 0.40, 0.81), CARBON)
    t = (-2.16 - Y) / 0.30
    zl = 0.79 + 0.06 * np.clip(t, 0, 1) ** 1.5
    rw_main = between(t, 0, 1) & (Z >= zl) & (Z <= zl + 0.055 * (1 - t) + 0.025) & (AX < 0.50)
    t = (-2.32 - Y) / 0.18
    zl = 0.885 + 0.07 * np.clip(t, 0, 1)
    rw_flap = between(t, 0, 1) & (Z >= zl) & (Z <= zl + 0.03) & (AX < 0.50)
    g.put(rw_main, WING)
    g.put(rw_flap, WING)
    g.put(between(Y, -2.36, -2.22) & (AX < 0.045) & between(Z, 0.775, 0.80), CARBON)  # actuator pod
    ep = between(AX, 0.50, 0.545) & between(Y, -2.52, -2.12) & between(Z, 0.48, 0.99)
    ep &= ~((Y > -2.24) & (Z > 0.87) & ((Y + 2.24) ** 2 + (Z - 0.87) ** 2 > 0.12 ** 2))
    ep &= ~((Z < 0.64) & (Y > -2.30 - (0.64 - Z) * 0.9))
    g.put(ep, WING)
    g.put(between(AX, 0.50, 0.545) & between(Y, -2.53, -2.505) & between(Z, 0.60, 0.86), RAIN)
    g.paint(rw_flap & (Y < -2.475), TEAL)

    # ---- cockpit: opening, seat, headrest, steering wheel
    opening = (((AX / 0.27) ** 6 + ((Y - 0.26) / 0.52) ** 6) <= 1)
    g.cut(opening & (Z > 0.50))
    rim = (((AX / 0.30) ** 6 + ((Y - 0.26) / 0.55) ** 6) <= 1) & (Z > 0.48)
    g.paint(rim, BLACK, only=PAINT)
    g.paint(opening & (Z <= 0.53), COCKPIT)
    g.add(opening & between(AX, 0.225, 0.28) & (Y < 0.16) & between(Z, 0.50, 0.70), PAD)  # headrest wings
    sw = between(Y, 0.42, 0.465)
    g.put(sw & (AX < 0.105) & between(Z, 0.645, 0.71), CARBON, STEER)
    g.put(sw & between(AX, 0.09, 0.14) & between(Z, 0.62, 0.72), PAD, STEER)
    g.put(between(Y, 0.465, 0.56) & (AX < 0.0225) & between(Z, 0.655, 0.69), CARBON, STEER)  # column
    g.paint(between(Y, 0.415, 0.44) & (AX < 0.045) & between(Z, 0.67, 0.70), SCREEN, parts=(STEER,))
    for (bx, bz, bm_) in ((-0.07, 0.66, BRED), (0.07, 0.66, BYEL), (-0.07, 0.695, BBLUE), (0.07, 0.695, BRED)):
        g.paint(between(Y, 0.415, 0.44) & (np.abs(X - bx) < 0.012) & (np.abs(Z - bz) < 0.012), bm_, parts=(STEER,))

    # ---- halo: titanium hoop + centre pillar, round section, slightly flattened fairing, small top fin
    hoop = [(0.31, -0.30, 0.70), (0.315, -0.25, 0.80), (0.315, -0.16, 0.875), (0.31, 0.00, 0.90),
            (0.30, 0.16, 0.905), (0.26, 0.30, 0.905), (0.18, 0.42, 0.905), (0.08, 0.51, 0.905), (0.0, 0.55, 0.902)]
    pillar = [(0.0, 0.55, 0.902), (0.0, 0.62, 0.885), (0.0, 0.69, 0.845), (0.0, 0.75, 0.79), (0.0, 0.79, 0.70)]
    halo = tube(catmull(hoop, 8), 0.052, 0.044) | tube(catmull(mirror(hoop), 8), 0.052, 0.044)
    halo |= tube(catmull(pillar, 8), 0.05, 0.05)
    g.put(halo, HALO)
    halo_fin = between(Y, -0.10, 0.02) & between(AX, 0.30, 0.325) & between(Z, 0.92, 0.95)
    g.put(halo_fin, HALO)

    # ---- mirrors on twin stalks
    for s in (1, -1):
        g.add(tube([(s * 0.31, 0.56, 0.66), (s * 0.43, 0.51, 0.74)], 0.014), CARBON)
        g.add(tube([(s * 0.52, 0.40, 0.60), (s * 0.50, 0.49, 0.72)], 0.014), CARBON)
        mir = between(s * X, 0.38, 0.545) & between(Y, 0.47, 0.535) & between(Z, 0.71, 0.785)
        g.put(mir, BLACK)
        g.paint(mir & (Y < 0.4925) & between(s * X, 0.40, 0.525) & between(Z, 0.72, 0.775), MIRROR)
        g.paint(mir & (Z > 0.77), TEAL)

    # ---- wheels, brakes, brake ducts
    for name, (wx, wy, ww, front) in WHEELS.items():
        wheel(g, name, wx, wy, R_TYRE, ww, front, compound)

    # ================================================================ livery (paint only)
    # silver nose and cockpit top with a one-voxel teal pin line on the shoulder
    bnd = ch_c + 0.50 * ch_h
    nose_zone = chassis & (Y > -0.12)
    g.paint(nose_zone & (Z > bnd + VOX), SILVER, only=(BLACK,))
    g.paint(nose_zone & between(Z, bnd, bnd + VOX), TEAL, only=(BLACK,))
    g.paint(rim & (Z > 0.53), BLACK, only=(SILVER, TEAL))
    # silver pod tops ending in four diagonal black claw stripes, teal outline below
    sb = sp_b + 0.84 * (sp_t - sp_b)
    pod_top = sidepod & (Z > sb + VOX) & (Y > -0.82) & ~chassis
    g.paint(pod_top, SILVER, only=(BLACK,))
    g.paint(sidepod & between(Z, sb, sb + VOX) & (Y > -0.82) & ~chassis, TEAL, only=(BLACK,))
    if "claws" in pats:
        d = Y + 0.55 * (AX - 0.30)
        claws = between(d, -0.80, -0.16) & (np.mod(d + 0.80, 0.16) < 0.06)
        g.paint(sidepod & claws, BLACK, only=(SILVER,))
        g.paint(sidepod & (d < -0.80), BLACK, only=(SILVER, TEAL))
    if "lower" in pats:  # two-tone: dark lower body
        lo_z = np.where(sidepod, sp_b + 0.42 * (sp_t - sp_b), ch_c - 0.35 * ch_h)
        g.paint((Z < lo_z) & (Y < 1.9), LOWER, only=(BLACK,))
        g.paint(cover & (Z < 0.36), LOWER, only=(BLACK,))
    if "nose_tip" in pats:
        g.paint(chassis & (Y > 2.36), ACCENT2, only=(SILVER, BLACK, TEAL))
    # star field on the engine cover (generic four-point pixel stars), denser toward the front
    rng = np.random.default_rng(63)
    n_stars = (16, 12) if "stars" in pats else (0, 0)
    star_s = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool)
    star_b = np.array([[0, 0, 1, 0, 0], [0, 0, 1, 0, 0], [1, 1, 1, 1, 1], [0, 0, 1, 0, 0], [0, 0, 1, 0, 0]], bool)
    for _ in range(n_stars[0]):
        yy = -0.62 - 1.05 * rng.random() ** 1.5
        zz = 0.58 + 0.30 * rng.random()
        big = True
        for s in ("+", "-"):
            g.stamp(star_b if big else star_s, (0.0, yy, zz), ("-" if s == "+" else "+") + "y", "+z", STAR,
                    depth=(0.03, 0.24) if s == "+" else (-0.24, -0.03), only=(BLACK,))
    for _ in range(n_stars[1]):
        yy = -0.62 - 1.2 * rng.random() ** 1.4
        xx = (rng.random() - 0.5) * 0.24
        g.stamp(star_s, (xx, yy, 0.6), "-y", "+x", STAR, depth=(0.5, 1.0), only=(BLACK,))
    # race number: nose top (reads from the front) and both sides of the engine cover in teal
    g.stamp(text_bitmap(number, F57), (0.0, 1.32, 0.66), "-x", "-y", L["number_top"], depth=(0.45, 0.75), only=(SILVER, TEAL))
    g.stamp(text_bitmap(number, F57), (0.0, -1.40, 0.50), "+y", "+z", L["number_side"], depth=(0.02, 0.4), only=(BLACK, LOWER))
    g.stamp(text_bitmap(number, F57), (0.0, -1.40, 0.50), "-y", "+z", L["number_side"], depth=(-0.4, -0.02), only=(BLACK, LOWER))
    # sponsor-style decals (placeholder words: any text can go in LIVERIES[...]['decals'])
    D = L["decals"]
    big = text_bitmap(D["sidepod"], F35, scale=2, spacing=1)
    g.stamp(big, (0.0, -0.28, 0.41), "+y", "+z", WHITE, depth=(0.40, 0.99), only=(BLACK,))
    g.stamp(big, (0.0, -0.28, 0.41), "-y", "+z", WHITE, depth=(-0.99, -0.40), only=(BLACK,))
    for s in (1, -1):
        g.stamp(text_bitmap(D["endplate"]), (0.0, -2.33, 0.76), "-y" if s < 0 else "+y", "+z", WHITE,
                depth=(-0.6, -0.49) if s < 0 else (0.49, 0.6), only=(WING,))
    g.stamp(text_bitmap(D["halo"]), (0.0, 0.49, 0.95), "-x", "-y", WHITE, depth=(0.9, 1.0), only=(HALO,))

    return dict(m=g.m, part=g.p, rgb=colours(g.m, compound, livery), compound=compound, number=number, livery=livery)


def wheel(g, name, cx, cy, R, W, front, compound):
    P = WHEEL_PART[name]
    s = 1 if cx > 0 else -1           # outward
    hw = W / 2
    margin = 0.13
    (i0, i1) = irange(min(cx - s * (hw + margin), cx + s * hw), max(cx - s * (hw + margin), cx + s * hw), 0)
    (j0, j1), (k0, k1) = irange(cy - R - 0.05, cy + R + 0.05, 1), irange(0, 2 * R + 0.1, 2)
    px, py, pz = xs[i0:i1, None, None], ys[None, j0:j1, None], zs[None, None, k0:k1]
    u = s * (px - cx)
    dy, dz = py - cy, pz - R
    r = np.sqrt(dy * dy + dz * dz)
    th = np.arctan2(dz, dy)
    sub = (slice(i0, i1), slice(j0, j1), slice(k0, k1))

    def put(mask, mat, part):
        full = np.zeros(SHAPE, bool)
        full[sub] = np.broadcast_to(mask, full[sub].shape)
        g.put(full, mat, part)

    def paint(mask, mat, part):
        full = np.zeros(SHAPE, bool)
        full[sub] = np.broadcast_to(mask, full[sub].shape)
        g.paint(full, mat, parts=(part,))

    au = np.abs(u)
    # tyre: rounded shoulders, bead at the 18-inch rim
    rc = 0.05 if front else 0.055
    a = au - (hw - rc)
    rlim = np.where(a > 0, R - rc + np.sqrt(np.clip(rc * rc - a * a, 0, None)), R)
    tyre = (au <= hw) & (r <= rlim) & (r >= 0.228)
    put(tyre, SIDEWALL, P["tyre"])
    paint(tyre & (r > rlim - 0.03) & (au < hw - 0.02), TREAD, P["tyre"])
    # outer sidewall: compound-colour arcs front and back, 'SLICK' lettering top and bottom (3x3 pixel letters,
    # tops toward the tread, reading left to right from outside the car)
    side = tyre & (au > hw - 0.03)
    arcs = np.abs(np.cos(th)) > 0.72
    paint(side & between(r, 0.2985, 0.3175) & arcs & (u > 0), BAND, P["tyre"])
    rmid = 0.265
    for centre in (np.pi / 2, -np.pi / 2):
        rel = np.mod(th - centre + np.pi, 2 * np.pi) - np.pi
        bm = text_bitmap("SLICK", F33)
        col = np.floor(-s * rel * 0.265 / VOX + 0.5).astype(int) + bm.shape[1] // 2
        row = np.floor((0.2985 - r) / VOX).astype(int)                 # 0 = outermost row
        ok = between(col, 0, bm.shape[1] - 1) & between(row, 0, 2) & between(r, 0.231, 0.2985)
        hit = np.zeros(ok.shape, bool)
        cc, rr = np.clip(col, 0, bm.shape[1] - 1), np.clip(row, 0, 2)
        hit[ok] = bm[rr[ok], cc[ok]]
        paint(side & (u > 0) & ok & hit, WHITE, P["tyre"])
    # wear-indicator dimples in the tread
    for ang in (0.3, 2.4, 4.5):
        for uu in (-W / 4, 0, W / 4):
            paint(tyre & (r > R - 0.03) & (np.abs(np.mod(th - ang + np.pi, 2 * np.pi) - np.pi) < 0.03)
                  & (np.abs(u - uu) < 0.012), TREAD_DARK, P["tyre"])
    # rim: barrel, recessed 10-spoke face, hub, nut
    put((r >= 0.205) & (r < 0.228) & (au <= hw - 0.012), RIM, P["rim"])
    put((r >= 0.188) & (r < 0.228) & between(u, hw - 0.075, hw - 0.012), RIM, P["rim"])
    n = 10
    ang = np.mod(th + np.pi / n, 2 * np.pi / n) - np.pi / n
    spoke = (r * np.abs(np.sin(ang)) < 0.014 + 0.022 * (1 - r / 0.205)) & between(r, 0.05, 0.205)
    put(spoke & between(u, hw - 0.075, hw - 0.04), RIM, P["rim"])
    put((r < 0.066) & between(u, hw - 0.095, hw - 0.035), RIM, P["rim"])
    put((r < 0.04) & between(u, hw - 0.035, hw - 0.012), NUT, P["rim"])
    # brake disc (spins with the wheel)
    rd = 0.165 if front else 0.150
    disc = between(r, 0.095, rd) & between(u, hw - 0.14, hw - 0.105)
    put(disc, DISC, P["disc"])
    holes = (np.mod(np.floor(th * 0.13 / VOX), 2) == 0) & (np.mod(np.floor((r - 0.095) / VOX), 2) == 1)
    paint(disc & holes, CAVITY, P["disc"])
    put((r < 0.085) & between(u, hw - 0.14, hw - 0.095), CALIPER, P["disc"])   # bell
    # static brake parts: upright, caliper, inner drum cover, duct
    put((r < 0.09) & between(u, -hw + 0.03, hw - 0.145), CARBON, P["brake"])
    cal = between(th, 0.55 * np.pi, 0.95 * np.pi) & between(r, 0.115, 0.20) & between(u, hw - 0.17, hw - 0.08)
    put(cal, CALIPER, P["brake"])
    paint(cal & (u > hw - 0.10) & between(r, 0.145, 0.17) & between(th, 0.62 * np.pi, 0.88 * np.pi), TEAL, P["brake"])
    put((r < 0.205) & between(u, -hw, -hw + 0.03), CARBON, P["brake"])
    if front:
        duct = between(u, -hw - 0.055, -hw) & between(dy, -0.10, 0.17) & between(dz, -0.04, 0.16)
        put(duct, CARBON, P["brake"])
        put(between(u, -hw - 0.07, -hw) & between(dy, -0.05, 0.20) & between(dz, 0.16, 0.185), CARBON, P["brake"])
        paint(duct & (dy > 0.13) & between(u, -hw - 0.045, -hw - 0.012) & between(dz, 0.02, 0.13), CAVITY,
              P["brake"])
    else:
        put(between(u, -hw - 0.05, -hw) & between(dy, -0.20, 0.20) & between(dz, -0.20, 0.26), CARBON, P["brake"])
        for zz in (0.14, 0.20, 0.26):
            put(between(u, -hw - 0.115, -hw) & between(dy, -0.22, 0.12) & between(dz, zz, zz + 0.0225), CARBON,
                P["brake"])
        paint(between(u, -hw - 0.05, -hw - 0.02) & between(dy, 0.17, 0.20) & between(dz, -0.10, 0.10), CAVITY,
              P["brake"])


def colours(m, compound="medium", livery="silver_arrow"):
    """Per-voxel linear colour: the material's colour plus a deterministic pixel texture (one texel per voxel)."""
    I, J, K = np.indices(SHAPE)
    h = ((I * 73856093) ^ (J * 19349663) ^ (K * 83492791)) & 0xFFFF
    noise = h / 65535.0
    rgb = np.zeros(SHAPE + (3,), np.float32)
    for mid in MATS:
        d = mat_spec(mid, livery, compound)
        sel = m == mid
        if not sel.any():
            continue
        base = np.array(_hex(d["hex"]), np.float32)
        amp = d.get("noise", 0.06)
        f = (1 - amp) + 2 * amp * noise[sel]
        c = base[None, :] * f[:, None]
        if "hex2" in d:  # weave / grille: checker of two tones
            alt = np.array(_hex(d["hex2"]), np.float32)
            chk = ((I + J + K)[sel] % 2 == 0)
            c[chk] = alt[None, :] * f[chk][:, None]
        if d["name"] == "exhaust":  # heat tint toward the tip
            tint = np.clip((-2.05 - ys[J[sel]]) / 0.39, 0, 1)
            gold, blue = np.array(_hex("#C9A44A")), np.array(_hex("#4B4F9C"))
            c = (c * (1 - tint[:, None]) + (blue * (1 - tint[:, None]) + gold * tint[:, None]) * tint[:, None])
        rgb[sel] = c
    return rgb


# parts of the car the sheet points at (metres)
ANCHORS = {
    "front_wing": (-0.62, 2.47, 0.21), "nose": (0.0, 2.15, 0.36), "front_suspension": (-0.42, 1.80, 0.53),
    "cockpit": (-0.14, 0.40, 0.70), "halo": (-0.30, 0.10, 0.905), "sidepod": (-0.62, -0.25, 0.52),
    "sidepod_inlet": (-0.50, 0.40, 0.45), "air_intake": (0.0, -0.29, 0.875), "floor": (-0.70, -0.45, 0.10),
    "rear_wing": (-0.30, -2.36, 0.93), "rear_suspension": (-0.40, -1.62, 0.47), "diffuser": (-0.30, -2.24, 0.22),
    "slick_tyre": (-0.945, 1.6875, 0.36), "front_brake_duct": (-0.70, 1.85, 0.45),
    "rear_brake_duct": (-0.56, -1.72, 0.58), "engine_cover": (-0.15, -1.15, 0.70), "mirror": (-0.46, 0.50, 0.75),
    "t_cam": (0.0, -0.40, 0.99), "rain_light": (0.0, -2.52, 0.345), "exhaust": (0.0, -2.42, 0.52),
    "plank": (0.0, 0.25, 0.02), "endplate": (-0.88, 2.30, 0.30), "number": (0.0, 1.32, 0.62),
}

# Where a block driver sits (house character, voxel.block_person at scale 1, helmet 0.405 m square):
# neck on the seat line, helmet top level with the halo, hands on the grips. Checked by fit_check.py.
SEAT = dict(neck=(0.0, 0.0, 0.53), grips=((-0.115, 0.44, 0.67), (0.115, 0.44, 0.67)),
            helmet_box=((-0.2025, -0.2225, 0.53), (0.2025, 0.1825, 0.95)))
