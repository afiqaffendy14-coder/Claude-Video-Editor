"""Racing go-kart (senior sprint kart, CIK-style bodywork): the voxel blueprint, the single source of truth for every
view, sheet and video. Same construction as the F1 car (library/cars/f1_2026/blueprint.py), at the same detail.

Pure numpy, no Blender. build(**opts) returns the voxel grid:
  m    (NX, NY, NZ) uint8  material id per voxel (0 = empty), see MATS
  part (NX, NY, NZ) uint8  which object the voxel belongs to, see PARTS
  rgb  (NX, NY, NZ, 3)     linear colour per voxel (one texel per voxel)

Scale: one voxel = 1.125 cm = a quarter of the house world pixel (4.5 cm), half the F1 car's voxel. A kart is a third
the length of an F1 car, so this keeps it at the F1 car's detail (tyres ~12 voxels in radius against the F1's 16).
Axes: +Y forward, +X the driver's right, +Z up, ground at z = 0, origin halfway along the wheelbase.
Real senior kart: wheelbase 1.04 m, length 1.82 m, width 1.40 m, front tyres 10x4.50-5, rear 11x7.10-5, 5" rims,
50 mm rear axle, 2-stroke water-cooled engine on the driver's right, radiator on the left.
The cockpit (seat, wheel, pedals) is placed for the master block character: see SEAT and fit_check.py.
"""
import math
import numpy as np

VOX = 0.01125
NX, NY, NZ = 128, 168, 56
X0, Y0, Z0 = -64 * VOX, -84 * VOX, 0.0

xs = X0 + (np.arange(NX) + 0.5) * VOX
ys = Y0 + (np.arange(NY) + 0.5) * VOX
zs = Z0 + (np.arange(NZ) + 0.5) * VOX
X, Y, Z = xs[:, None, None], ys[None, :, None], zs[None, None, :]
AX = np.abs(X)
SHAPE = (NX, NY, NZ)

# wheels: axles on voxel boundaries so every tyre is a symmetric circle
WB_HALF = 46 * VOX            # 0.5175 -> wheelbase 1.035 m
R_FRONT = 11 * VOX            # 0.124 -> 0.25 m tall (10")
R_REAR = 12 * VOX             # 0.135 -> 0.27 m tall (11")
WHEELS = {  # name: (centre x, centre y, radius, width, front?)
    "FL": (-48 * VOX, WB_HALF, R_FRONT, 10 * VOX, True), "FR": (48 * VOX, WB_HALF, R_FRONT, 10 * VOX, True),
    "RL": (-54 * VOX, -WB_HALF, R_REAR, 16 * VOX, False), "RR": (54 * VOX, -WB_HALF, R_REAR, 16 * VOX, False),
}
KINGPIN_X = 0.42              # front wheels steer about the kingpins (x = +-0.42, y = WB_HALF)

# ---------------------------------------------------------------- parts (become separate Blender objects)
BODY, STEER, AXLE, RBUMP = 1, 4, 5, 6
PARTS = {"body": [BODY], "steering_wheel": [STEER], "rear_axle": [AXLE], "rear_bumper": [RBUMP]}
WHEEL_PART = {}
for n, w in enumerate(WHEELS):
    WHEEL_PART[w] = dict(tyre=10 + n, rim=20 + n, spindle=30 + n)
    for k, v in WHEEL_PART[w].items():
        PARTS[f"{k}_{w}"] = [v]


def _hex(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]


# ---------------------------------------------------------------- materials: id -> look
MATS = {
    1: dict(name="body_main", hex="#AEB3B9", metal=0.1, rough=0.3, noise=0.05),
    2: dict(name="body_accent", hex="#111214", metal=0.05, rough=0.32, noise=0.08),
    3: dict(name="pin", hex="#00A19B", metal=0.05, rough=0.3, noise=0.05),
    4: dict(name="bumper", hex="#18191B", metal=0.0, rough=0.55, noise=0.10),
    5: dict(name="decal_white", hex="#EEEEEE", metal=0.0, rough=0.35, noise=0.04),
    6: dict(name="frame", hex="#C9CDD2", metal=0.9, rough=0.22, noise=0.05),
    7: dict(name="chrome", hex="#D5D8DC", metal=1.0, rough=0.12, noise=0.04),
    8: dict(name="aluminium", hex="#A7ABB0", metal=0.85, rough=0.35, noise=0.06),
    9: dict(name="rim", hex="#8E949A", metal=0.85, rough=0.3, noise=0.05),
    10: dict(name="tread", hex="#2B2B2D", metal=0.0, rough=0.88, noise=0.12),
    11: dict(name="sidewall", hex="#19191B", metal=0.0, rough=0.62, noise=0.08),
    12: dict(name="seat", hex="#0E0F11", metal=0.1, rough=0.18, noise=0.05),
    13: dict(name="engine_cast", hex="#9DA1A6", metal=0.7, rough=0.45, noise=0.10),
    14: dict(name="engine_dark", hex="#26282C", metal=0.4, rough=0.4, noise=0.06),
    15: dict(name="exhaust", hex="#B9BCC2", metal=0.95, rough=0.22, noise=0.04),
    16: dict(name="fuel_tank", hex="#E4E2DA", metal=0.0, rough=0.35, noise=0.04),
    17: dict(name="fuel", hex="#D9A441", metal=0.0, rough=0.3, noise=0.04),
    18: dict(name="radiator", hex="#2A2C2F", hex2="#121314", metal=0.4, rough=0.5, noise=0.04),
    19: dict(name="hose", hex="#141416", metal=0.0, rough=0.7, noise=0.06),
    20: dict(name="chain", hex="#3A3B3E", hex2="#77797D", metal=0.8, rough=0.4, noise=0.05),
    21: dict(name="sprocket", hex="#00A19B", metal=0.7, rough=0.3, noise=0.05),
    22: dict(name="brake_disc", hex="#4A4441", metal=0.4, rough=0.6, noise=0.14),
    23: dict(name="caliper", hex="#00A19B", metal=0.5, rough=0.3, noise=0.05),
    24: dict(name="screen", hex="#2BE0B2", metal=0.0, rough=0.3, emit=2.5, noise=0.05),
    25: dict(name="grip", hex="#1D1E21", metal=0.0, rough=0.9, noise=0.10),
    26: dict(name="number_plate", hex="#F6C21C", metal=0.0, rough=0.4, noise=0.03),
    27: dict(name="number_ink", hex="#111214", metal=0.0, rough=0.4, noise=0.03),
    28: dict(name="transponder", hex="#F2D21B", metal=0.0, rough=0.4, noise=0.04),
    29: dict(name="cavity", hex="#050506", metal=0.0, rough=0.8, noise=0.05),
    30: dict(name="rubber", hex="#202022", metal=0.0, rough=0.8, noise=0.08),
    31: dict(name="tread_dark", hex="#121213", metal=0.0, rough=0.9, noise=0.05),
    32: dict(name="floor_tray", hex="#9EA2A7", hex2="#B4B8BC", metal=0.8, rough=0.4, noise=0.04),
    33: dict(name="nut", hex="#E8C547", metal=0.8, rough=0.3, noise=0.04),
    34: dict(name="button_red", hex="#E8322A", metal=0.0, rough=0.4, noise=0.03),
    35: dict(name="accent2", hex="#FFC906", metal=0.05, rough=0.3, noise=0.05),
    36: dict(name="spark_plug", hex="#ECECEC", metal=0.0, rough=0.3, noise=0.03),
    37: dict(name="lower_paint", hex="#111214", metal=0.05, rough=0.32, noise=0.08),
    38: dict(name="hub", hex="#B9862E", metal=0.85, rough=0.3, noise=0.05),
    # wear (condition="beat_up")
    39: dict(name="patch_panel", hex="#D9B13A", metal=0.05, rough=0.45, noise=0.07),
    40: dict(name="scratch", hex="#BDBCB4", metal=0.0, rough=0.6, noise=0.10),
    41: dict(name="duct_tape", hex="#9A9EA3", metal=0.35, rough=0.45, noise=0.08),
    42: dict(name="rust", hex="#6E3517", metal=0.2, rough=0.85, noise=0.18),
    43: dict(name="rust_light", hex="#7E4424", metal=0.2, rough=0.8, noise=0.16),
    44: dict(name="zip_tie", hex="#0D0D0E", metal=0.0, rough=0.5, noise=0.04),
    45: dict(name="rim_odd", hex="#B08D3A", metal=0.75, rough=0.4, noise=0.08),
    46: dict(name="scuff", hex="#4E5055", metal=0.0, rough=0.7, noise=0.10),
    47: dict(name="soot", hex="#1E1915", metal=0.1, rough=0.9, noise=0.16),
}
(MAIN, ACC, PIN, BUMPER, WHITE, FRAME, CHROME, ALU, RIM, TREAD, SIDEWALL, SEATM, CAST, DARK, EXHAUST, TANK, FUEL,
 RADIATOR, HOSE, CHAIN, SPROCKET, DISC, CALIPER, SCREEN, GRIP, PLATE, INK, TRANSP, CAVITY, RUBBER, TREAD_DARK,
 TRAY, NUT, BRED, ACCENT2, PLUG, LOWER, HUB, PATCH, SCRATCH, TAPE, RUST, RUST2, ZIP, RIM2, SCUFF, SOOT) = range(1, 48)
# Paint slots a livery recolours: MAIN (bodywork), ACC (second bodywork colour), PIN (pin lines), BUMPER, FRAME,
# RIM, HUB, SPROCKET, CALIPER, LOWER (lower bodywork, when the pattern asks), ACCENT2 (nose tip), PLATE/INK, WHITE.

# Liveries are data: a new team is a new entry here, the geometry never changes. Same four teams as the F1 cars,
# "inspired" colours only, no real logos. paint: slot -> (hex, metal, rough)
LIVERIES = {
    "silver_arrow": dict(  # Mercedes-inspired: silver bodywork, black lower half, teal pin lines, chrome frame
        number="63", patterns=("lower",),
        paint={MAIN: ("#AEB3B9", 0.55, 0.28), ACC: ("#111214", 0.05, 0.3), PIN: ("#00A19B", 0.05, 0.3),
               LOWER: ("#111214", 0.05, 0.3), FRAME: ("#C9CDD2", 0.9, 0.22), RIM: ("#8E949A", 0.85, 0.3),
               HUB: ("#00A19B", 0.7, 0.3), SPROCKET: ("#00A19B", 0.7, 0.3), CALIPER: ("#00A19B", 0.5, 0.3),
               WHITE: ("#EEEEEE", 0.0, 0.35)},
        decals=dict(pod="KYNEX", nose="ORVA", bumper="KYNEX"),
    ),
    "rosso": dict(  # Ferrari-inspired: red bodywork, black lower half, white pin lines, red frame, gold rims
        number="16", patterns=("lower",),
        paint={MAIN: ("#D10A11", 0.15, 0.25), ACC: ("#141416", 0.05, 0.3), PIN: ("#F2F2F2", 0.0, 0.3),
               LOWER: ("#141416", 0.05, 0.3), FRAME: ("#C3070E", 0.5, 0.25), RIM: ("#C9A44A", 0.85, 0.3),
               HUB: ("#C9A44A", 0.85, 0.3), SPROCKET: ("#C9A44A", 0.8, 0.3), CALIPER: ("#FFD400", 0.4, 0.3),
               WHITE: ("#F2F2F2", 0.0, 0.35), ACCENT2: ("#FFD400", 0.05, 0.3)},
        decals=dict(pod="VELTRO", nose="TEKNA", bumper="VELTRO"),
    ),
    "papaya": dict(  # McLaren-inspired: papaya bodywork, anthracite lower half and frame, black rims
        number="81", patterns=("lower",),
        paint={MAIN: ("#FF7A00", 0.05, 0.28), ACC: ("#1E1F22", 0.05, 0.3), PIN: ("#1E1F22", 0.05, 0.3),
               LOWER: ("#1E1F22", 0.05, 0.3), FRAME: ("#2A2C30", 0.6, 0.3), RIM: ("#1E1F22", 0.7, 0.3),
               HUB: ("#FF7A00", 0.6, 0.3), SPROCKET: ("#FF7A00", 0.6, 0.3), CALIPER: ("#FF7A00", 0.4, 0.3),
               WHITE: ("#F2F2F2", 0.0, 0.35)},
        decals=dict(pod="ORVA", nose="KYNEX", bumper="ORVA"),
    ),
    "midnight": dict(  # Red Bull-inspired: matte navy bodywork and frame, red pin lines, yellow nose tip
        number="3", patterns=("nose_tip",),
        paint={MAIN: ("#1C2445", 0.15, 0.55), ACC: ("#1C2445", 0.15, 0.55), PIN: ("#E1062C", 0.05, 0.35),
               FRAME: ("#1C2445", 0.5, 0.4), RIM: ("#C9CDD2", 0.85, 0.3), HUB: ("#E1062C", 0.6, 0.3),
               SPROCKET: ("#E1062C", 0.6, 0.3), CALIPER: ("#E1062C", 0.4, 0.3), ACCENT2: ("#FFC906", 0.05, 0.35),
               WHITE: ("#F2F2F2", 0.0, 0.4)},
        decals=dict(pod="TEKNA", nose="VELTRO", bumper="TEKNA"),
    ),
    "fifth_hand": dict(  # a club kart on its fifth owner: faded blue, white trim, yellow pins, red frame gone rusty,
        number="7", patterns=(), condition="battered",  # a yellow replacement pod, the nose long gone
        paint={MAIN: ("#2F62A8", 0.05, 0.4), ACC: ("#E8E6DE", 0.0, 0.45), PIN: ("#F2C200", 0.05, 0.4),
               FRAME: ("#9C2219", 0.3, 0.45), RIM: ("#A7ABB0", 0.7, 0.4), HUB: ("#8E949A", 0.7, 0.4),
               SPROCKET: ("#8E949A", 0.7, 0.4), CALIPER: ("#3B3E44", 0.4, 0.45), PATCH: ("#E0B32A", 0.05, 0.45),
               WHITE: ("#F2F2EE", 0.0, 0.45), SEATM: ("#4F5843", 0.1, 0.4)},
        decals=dict(pod="RAPIDO", nose="MOTO", bumper="GARAGE"),
    ),
}
TITLES = {"silver_arrow": "Silver Arrow livery (Mercedes-inspired)", "rosso": "Rosso livery (Ferrari-inspired)",
          "papaya": "Papaya livery (McLaren-inspired)", "midnight": "Midnight livery (Red Bull-inspired)",
          "fifth_hand": "Fifth-hand club kart (beat up)"}
for _k, _t in TITLES.items():
    LIVERIES[_k]["title"] = _t
TYRES = ("slick", "wet")
CONDITIONS = ("new", "beat_up", "battered")   # any livery; fifth_hand comes battered (years of club racing)
WORN_MATS = (MAIN, ACC, PIN, LOWER, ACCENT2, PATCH, BUMPER, WHITE, PLATE, SEATM, TANK, INK)


def mat_spec(mid, livery="silver_arrow", condition="new"):
    """A material slot's look for this livery (colour, metal, rough). Beaten up: duller, rougher finishes."""
    d = dict(MATS[mid])
    L = LIVERIES[livery]
    if mid in L["paint"]:
        d["hex"], d["metal"], d["rough"] = L["paint"][mid]
    if condition in ("beat_up", "battered"):
        if mid in (CHROME, FRAME, EXHAUST, ALU, RIM, HUB, SPROCKET, CAST):
            d["metal"], d["rough"] = d["metal"] * 0.7, min(0.8, d["rough"] + 0.25)
        elif mid in WORN_MATS:
            d["rough"] = min(0.85, d["rough"] + 0.25)
    return d


def driver_skin(livery):
    """The block-character skin that drives this livery (character library skins.SKINS)."""
    return {"fifth_hand": "karter_fifth_hand"}.get(livery, "driver_" + livery)


def default_condition(livery):
    return LIVERIES[livery].get("condition", "new")


def blobs(seed, wl=0.12, n=5):
    """Smooth 0..1 noise over the grid (a few random plane waves), for rust, fade and dirt patches."""
    rng = np.random.default_rng(seed)
    f = np.zeros(SHAPE, np.float32)
    for _ in range(n):
        k = rng.normal(size=3)
        k = k / np.linalg.norm(k) * 2 * np.pi / (wl * rng.uniform(0.7, 1.3))
        f += np.sin(X * k[0] + Y * k[1] + Z * k[2] + rng.uniform(0, 2 * np.pi)).astype(np.float32)
    return np.clip(0.5 + 0.5 * f / np.sqrt(n) * 1.3, 0, 1)


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
    "V": ["#.#", "#.#", ".#."], "E": ["###", "##.", "###"], "L": ["#..", "#..", "###"], "O": ["###", "#.#", "###"],
    " ": [".", ".", "."],
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
    """A profile along the kart: values at stations yp, linear in between (shape 1, NY, 1)."""
    yp, vp = np.asarray(yp, float), np.asarray(vp, float)
    o = np.argsort(yp)
    return np.interp(ys, yp[o], vp[o])[None, :, None]


def between(a, lo, hi):
    return (a >= lo) & (a <= hi)


def to_i(v, axis):
    o = (X0, Y0, Z0)[axis]
    return int(math.floor((v - o) / VOX))


def irange(lo, hi, axis):
    n = SHAPE[axis]
    o = (X0, Y0, Z0)[axis]
    return max(0, int(math.floor((lo - o) / VOX))), min(n, int(math.ceil((hi - o) / VOX)) + 1)


def tube(points, r, rz=None, r1=None):
    """Voxels within an elliptic radius (r sideways, rz vertical) of a polyline. r1: radius at the far end
    (linear taper along each segment from r to r1 over the whole line)."""
    rz = rz or r
    out = np.zeros(SHAPE, bool)
    lens = [np.linalg.norm(np.subtract(b, a)) for a, b in zip(points[:-1], points[1:])]
    total, run = sum(lens), 0.0
    for (a, b), ln in zip(zip(points[:-1], points[1:]), lens):
        a, b = np.array(a, float), np.array(b, float)
        ra = r if r1 is None else r + (r1 - r) * run / total
        rb = r if r1 is None else r + (r1 - r) * (run + ln) / total
        run += ln
        rm = max(ra, rb, rz)
        lo, hi = np.minimum(a, b) - rm, np.maximum(a, b) + rm
        (i0, i1), (j0, j1), (k0, k1) = (irange(lo[n], hi[n], n) for n in range(3))
        px, py, pz = xs[i0:i1, None, None], ys[None, j0:j1, None], zs[None, None, k0:k1]
        ab = b - a
        t = np.clip(((px - a[0]) * ab[0] + (py - a[1]) * ab[1] + (pz - a[2]) * ab[2]) / max(ab @ ab, 1e-12), 0, 1)
        dx, dy, dz = px - (a[0] + t * ab[0]), py - (a[1] + t * ab[1]), pz - (a[2] + t * ab[2])
        rr = ra + (rb - ra) * t
        k = (rz / r) if r1 is None else 1.0
        out[i0:i1, j0:j1, k0:k1] |= (dx * dx + dy * dy) / rr ** 2 + dz * dz / (rr * k) ** 2 <= 1.0
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


def local(origin, u, v, w):
    """Coordinates of every voxel centre in a tilted frame (u, v, w unit vectors)."""
    dx, dy, dz = X - origin[0], Y - origin[1], Z - origin[2]
    return tuple(dx * e[0] + dy * e[1] + dz * e[2] for e in (u, v, w))


def cyl_x(cx, cy, cz, r, x0, x1):
    """A cylinder along X (axles, hubs, discs)."""
    return ((Y - cy) ** 2 + (Z - cz) ** 2 <= r * r) & between(X, x0, x1)


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


# ---------------------------------------------------------------- cockpit layout (for the block character)
# The driver: hips at HIP, back reclined 20 degrees, legs forward either side of the steering column, feet on the
# pedals, hands at 9 and 3 on the wheel. character_blender.seat_in_car reads SEAT.
RECLINE = math.radians(20)
HIP = np.array((0.0, -0.16, 0.175))
SPINE = np.array((0.0, -math.sin(RECLINE), math.cos(RECLINE)))      # up the driver's back
FWD = np.array((0.0, math.cos(RECLINE), math.sin(RECLINE)))         # out of the driver's chest
WHEEL_HUB = np.array((0.0, 0.0, 0.48))                                    # steering-wheel hub
COL_LOW = np.array((0.0, 0.40, 0.075))                              # lower column bearing on the front cross tube
COL_DIR = (COL_LOW - WHEEL_HUB) / np.linalg.norm(COL_LOW - WHEEL_HUB)           # down the column (forward, down)
WHEEL_UP = np.cross(COL_DIR, (1.0, 0.0, 0.0))                       # 12 o'clock on the steering wheel
WHEEL_UP /= np.linalg.norm(WHEEL_UP)
if WHEEL_UP[2] < 0:
    WHEEL_UP = -WHEEL_UP
WHEEL_R = 0.17                                                      # rim half-width at 9 and 3 o'clock
WHEEL_RB = 0.135                                                    # rim half-height (butterfly shape)


# ---------------------------------------------------------------- the kart
def build(livery="silver_arrow", number=None, tyre="slick", condition=None):
    L = LIVERIES[livery]
    number = number or L["number"]
    condition = condition or default_condition(livery)
    worn = condition in ("beat_up", "battered")
    heavy = condition == "battered"
    pats = L["patterns"]
    g = Grid()

    # ---- chassis: 30 mm chrome-moly tube frame (one tube = ~3 voxels across), riding 3 cm off the ground
    zf = 0.045
    rt = 0.0155
    for s in (1, -1):
        def rail(pts, r=rt, mat=FRAME):
            g.add(tube([(s * x, y, z) for x, y, z in pts], r), mat)
        rail(catmull([(0.42, 0.50, zf), (0.375, 0.36, zf), (0.33, 0.14, zf), (0.31, -0.30, zf), (0.275, -0.48, zf),
                      (0.27, -0.64, zf)], 6))                                         # outer main rail
        rail(catmull([(0.13, 0.75, zf), (0.17, 0.64, zf), (0.285, 0.50, zf), (0.30, 0.36, zf), (0.25, 0.16, zf),
                      (0.235, 0.0, zf), (0.235, -0.62, zf)], 6))                       # inner rail (footwell)
        rail([(0.17, 0.64, zf), (0.42, 0.535, zf)])                                   # kingpin brace
        rail([(0.25, 0.16, zf), (0.32, 0.02, zf)])                                    # side diagonal
        rail([(0.235, -0.20, zf), (0.31, -0.36, zf)])
        # kingpin C-bracket: two plates welded to the frame corner
        for zc in (0.065, 0.185):
            g.add(between(s * X, 0.385, 0.445) & between(Y, WB_HALF - 0.025, WB_HALF + 0.025)
                  & between(Z, zc - 0.009, zc + 0.009), FRAME)
        g.add(between(s * X, 0.37, 0.39) & between(Y, WB_HALF - 0.025, WB_HALF + 0.025) & between(Z, 0.05, 0.19), FRAME)
        # rear bearing hangers (axle carriers) and seat-stay towers
        g.add(between(s * X, 0.255, 0.285) & between(Y, -WB_HALF - 0.04, -WB_HALF + 0.04) & between(Z, 0.03, 0.17),
              FRAME)
        g.add(cyl_x(0, -WB_HALF, R_REAR, 0.042, s * 0.25 - 0.02, s * 0.25 + 0.02) & (s * X > 0), ALU)
    g.add(tube([(-0.13, 0.75, zf), (0.13, 0.75, zf)], rt), FRAME)                      # front cross tubes
    g.add(tube([(-0.40, 0.475, zf), (0.40, 0.475, zf)], rt), FRAME)
    g.add(tube([(-0.235, -0.62, zf), (0.235, -0.62, zf)], rt), FRAME)                  # rear cross tube
    g.add(between(X, -0.04, 0.04) & between(Y, COL_LOW[1] - 0.03, COL_LOW[1] + 0.035) & between(Z, 0.03, 0.10),
          FRAME)                                                                       # lower column bracket

    # ---- floor tray (aluminium checker plate) under the legs, heel stops
    tray_w = fy([0.0, 0.40, 0.72], [0.215, 0.20, 0.13])
    g.add(between(Y, 0.04, 0.72) & (AX <= tray_w) & between(Z, 0.0225, 0.034), TRAY)
    for s in (1, -1):
        g.add(between(s * X, 0.12, 0.25) & between(Y, 0.27, 0.30) & between(Z, 0.034, 0.06), RUBBER)

    # ---- bucket seat: fibreglass shell reclined 20 degrees, sized to the block driver (body 8 px = 0.36 m wide)
    a, b, _ = local(HIP, SPINE, FWD, (1, 0, 0))
    seat_w = np.where(a > 0.30, 0.205 - 0.6 * np.clip(a - 0.30, 0, None) ** 1.5, 0.205)
    back = between(b, -0.12, -0.0975) & between(a, -0.075, 0.42) & (AX <= seat_w)
    pz0, pz1 = 0.0575, 0.08                                                            # seat pan, on the rails
    pan = between(Z, pz0, pz1) & between(Y, -0.27, 0.04) & (AX <= fy([-0.27, 0.04], [0.205, 0.185]))
    pan |= between(Z, pz0, pz1) & between(b, -0.12, 0.0) & (AX <= 0.205) & (a < 0.0)
    side = between(AX, 0.19, 0.2125) & between(b, -0.12, 0.03) & between(a, -0.12, 0.16) & (Z >= pz0)
    side |= between(AX, 0.19, 0.2125) & between(Y, -0.27, -0.13) & between(Z, pz0, 0.125)
    back &= Z >= pz0
    seat = back | pan | side
    g.add(seat, SEATM)
    for s in (1, -1):                                                                  # seat mounting brackets
        for yb in (-0.20, -0.02):
            g.add(between(s * X, 0.17, 0.25) & between(Y, yb - 0.012, yb + 0.012) & between(Z, 0.045, pz0), ALU)
    g.paint(seat & (AX > 0.19) & between(a, 0.14, 0.16), PIN, only=(SEATM,))           # pin line on the bolsters
    # seat stays: back of the seat to the rear bearing towers, sides to the main rails
    for s in (1, -1):
        top = HIP + 0.30 * SPINE - 0.125 * FWD
        g.add(tube([(s * 0.13, top[1], top[2]), (s * 0.27, -WB_HALF + 0.02, 0.165)], 0.009), CHROME)
        mid = HIP + 0.10 * SPINE - 0.125 * FWD
        g.add(tube([(s * 0.17, mid[1], mid[2]), (s * 0.31, -0.30, 0.05)], 0.009), CHROME)
        g.add(tube([(s * 0.205, -0.05, 0.05), (s * 0.31, 0.06, 0.05)], 0.008), CHROME)
    # transponder on the back of the seat (lap timing), with its strap
    tp = HIP + 0.12 * SPINE - 0.14 * FWD
    ta, tb, tc = local(tp, SPINE, FWD, (1, 0, 0))
    g.add(between(ta, -0.03, 0.03) & between(tb, -0.03, 0.0) & between(tc, -0.16, -0.08), TRANSP)
    g.add(between(ta, -0.01, 0.01) & between(tb, -0.006, 0.0) & between(tc, -0.20, 0.02), RUBBER)

    # ---- rear axle assembly (spins as one: 50 mm axle, hubs, sprocket, brake disc)
    axy, axz = -WB_HALF, R_REAR
    g.put(cyl_x(0, axy, axz, 0.025, -0.60, 0.60), ALU, AXLE)
    th = np.arctan2(Z - axz, Y - axy)
    rr = np.sqrt((Y - axy) ** 2 + (Z - axz) ** 2)
    for s in (1, -1):
        g.put(cyl_x(0, axy, axz, 0.052, s * 0.46 - 0.035, s * 0.46 + 0.035) & (s * X > 0), HUB, AXLE)    # hub
        g.paint(cyl_x(0, axy, axz, 0.052, -1, 1) & between(s * X, 0.44, 0.45) & (rr > 0.045), DARK, parts=(AXLE,))
    # sprocket (78-tooth look) on the right, inboard of the right rear hub
    sx = 0.415
    teeth = 0.082 + 0.008 * (np.cos(th * 39) > 0)
    spr = between(X, sx - 0.006, sx + 0.006) & (rr <= teeth)
    g.put(spr, SPROCKET, AXLE)
    g.paint(spr & between(rr, 0.035, 0.065) & (np.mod(np.floor(th / (np.pi / 3)), 2) == 0), CAVITY, parts=(AXLE,))
    g.put(cyl_x(0, axy, axz, 0.036, sx - 0.02, sx + 0.02), ALU, AXLE)                    # sprocket carrier
    # ventilated brake disc on the left, with its carrier
    dx_ = -0.12
    disc = cyl_x(0, axy, axz, 0.096, dx_ - 0.009, dx_ + 0.009) & (rr > 0.03)
    g.put(disc, DISC, AXLE)
    g.paint(disc & between(rr, 0.05, 0.09) & (np.mod(np.floor(th * 0.07 / VOX), 3) == 0)
            & (np.mod(np.floor((rr - 0.05) / VOX), 2) == 0), CAVITY, parts=(AXLE,))
    g.put(cyl_x(0, axy, axz, 0.04, dx_ - 0.02, dx_ + 0.02), ALU, AXLE)
    # brake caliper on top of the disc, bolted to a bracket off the rear cross tube
    cal = between(X, dx_ - 0.03, dx_ + 0.03) & between(rr, 0.07, 0.115) & between(th, 0.45 * np.pi, 0.85 * np.pi)
    g.put(cal & ~disc, CALIPER)
    g.add(between(X, dx_ - 0.015, dx_ + 0.015) & between(Y, -0.64, -0.56) & between(Z, 0.04, 0.20) & (rr > 0.10),
          ALU)
    g.add(tube([(dx_, -0.50, 0.24), (dx_ + 0.02, -0.40, 0.21), (-0.06, -0.30, 0.08)], 0.006), HOSE)  # brake line

    # ---- engine on the driver's right: crankcase, water-cooled cylinder, head, plug, carb, airbox, clutch, chain
    ex = 0.345                                                                         # engine centre line
    g.add(between(X, 0.24, 0.32) & between(Y, -0.36, -0.10) & between(Z, 0.035, 0.065), ALU)   # engine mount
    crank = (((X - ex) / 0.075) ** 4 + ((Y + 0.24) / 0.12) ** 4 + ((Z - 0.13) / 0.07) ** 4) <= 1
    g.add(crank, CAST)
    cyl = ((X - ex) ** 2 + ((Y + 0.27) / 1.15) ** 2 <= 0.055 ** 2) & between(Z, 0.17, 0.27)
    g.add(cyl, CAST)
    g.paint(cyl & (np.mod(np.floor(Z / VOX), 2) == 0) & ((X - ex) ** 2 + ((Y + 0.27) / 1.15) ** 2 > 0.045 ** 2),
            DARK)                                                                      # cooling-jacket ribs
    head = ((X - ex) ** 2 + ((Y + 0.27) / 1.15) ** 2 <= 0.062 ** 2) & between(Z, 0.27, 0.305)
    g.add(head, DARK)
    g.add(((X - ex) ** 2 + (Y + 0.27) ** 2 <= 0.012 ** 2) & between(Z, 0.305, 0.33), PLUG)        # spark plug
    g.add(tube([(ex, -0.27, 0.335), (ex - 0.02, -0.27, 0.36), (ex - 0.07, -0.25, 0.36)], 0.011), HOSE)  # plug cap/lead
    g.add(cyl_x(0, -0.20, 0.10, 0.055, 0.40, 0.43), DARK)                              # clutch drum (outboard)
    g.add(cyl_x(0, -0.20, 0.10, 0.025, 0.43, 0.445), ALU)
    # carburettor + intake silencer (airbox) in front of the engine, beside the driver's right hip
    g.add(between(X, 0.28, 0.33) & between(Y, -0.12, -0.08) & between(Z, 0.10, 0.17), ALU)
    box = (((X - 0.34) / 0.065) ** 4 + ((Y + 0.01) / 0.085) ** 4 + ((Z - 0.12) / 0.06) ** 4) <= 1
    g.add(box, BUMPER)
    g.paint(box & (Y > 0.06) & (np.mod(np.floor(Z / VOX), 2) == 0) & between(Z, 0.08, 0.16), CAVITY)  # intake slots
    # chain: top and bottom runs from the clutch sprocket to the axle sprocket, plus a guard over the top run
    for zr, r_ in ((0.10 + 0.028, axz + 0.086), (0.10 - 0.028, axz - 0.086)):
        g.add(tube([(sx, -0.20, zr), (sx, axy, r_)], 0.006, 0.0045), CHAIN)
    g.add(between(X, sx - 0.01, sx + 0.01) & (rr <= 0.092) & (rr > 0.084) & (th > 0) & ~(np.abs(Y - axy) < 0.0), CHAIN)
    gz = fy([-0.20, axy], [0.10 + 0.028, axz + 0.086]) + 0.022                         # follows the top run
    guard = between(X, sx - 0.022, sx + 0.022) & between(Y, axy, -0.24) & between(Z, gz, gz + VOX)
    guard |= between(X, sx - 0.022, sx + 0.022) & (Y < axy) & between(rr, 0.108, 0.108 + VOX) & (th > 0.3)
    guard |= between(X, sx + 0.012, sx + 0.022) & between(Y, axy, -0.24) & between(Z, gz - 0.035, gz)
    g.add(guard, BUMPER)
    # exhaust: header out of the back of the cylinder, expansion chamber behind the seat, silencer to the left
    hdr = [(ex, -0.33, 0.235), (0.33, -0.42, 0.25), (0.26, -0.50, 0.28), (0.12, -0.555, 0.30), (-0.04, -0.565, 0.30),
           (-0.18, -0.55, 0.29), (-0.25, -0.53, 0.285)]
    pipe = catmull(hdr, 6)
    n = len(pipe)
    rad = [0.022 + 0.034 * math.sin(math.pi * min(1.0, i / (n * 0.8))) for i in range(n)]
    ex_mask = np.zeros(SHAPE, bool)
    for i in range(n - 1):
        ex_mask |= tube([pipe[i], pipe[i + 1]], rad[i], r1=None)
    g.add(ex_mask, EXHAUST)
    sil = tube([(-0.25, -0.53, 0.285), (-0.33, -0.66, 0.30)], 0.042)
    g.add(sil, CHROME)
    g.paint(sil & (Y < -0.645), DARK)
    g.add(tube([(-0.335, -0.665, 0.30), (-0.36, -0.705, 0.305)], 0.016), EXHAUST)
    g.cut(tube([(-0.345, -0.68, 0.302), (-0.37, -0.72, 0.307)], 0.009))
    g.add(tube([(-0.30, -0.60, 0.26), (-0.27, -0.62, 0.06)], 0.005), CHROME)           # silencer spring stay

    # ---- radiator on the driver's left with its hoses to the engine
    rad_m = between(X, -0.435, -0.405) & between(Y, -0.30, -0.04) & between(Z, 0.10, 0.40)
    g.add(rad_m, RADIATOR)
    g.paint(rad_m & ((Z > 0.385) | (Z < 0.115) | (Y > -0.055) | (Y < -0.285)), ALU)
    g.add(between(X, -0.43, -0.41) & between(Y, -0.29, -0.05) & between(Z, 0.40, 0.42), DARK)   # blind roller
    g.add(((X + 0.42) ** 2 + (Y + 0.08) ** 2 <= 0.014 ** 2) & between(Z, 0.40, 0.435), DARK)     # filler cap
    for s_ in (1, -1):
        g.add(tube([(-0.42, -0.17 + s_ * 0.11, 0.10), (-0.42, -0.17 + s_ * 0.13, 0.05), (-0.31, -0.17 + s_ * 0.13,
                                                                                            zf)], 0.006), CHROME)
    g.add(tube(catmull([(-0.42, -0.29, 0.11), (-0.33, -0.40, 0.09), (0.0, -0.40, 0.085), (0.22, -0.38, 0.08),
                        (0.28, -0.30, 0.09)], 6), 0.011), HOSE)
    g.add(tube(catmull([(-0.42, -0.29, 0.38), (-0.30, -0.44, 0.37), (0.05, -0.47, 0.36), (0.26, -0.40, 0.33),
                        (0.31, -0.29, 0.285)], 6), 0.011), HOSE)

    # ---- fuel tank between the legs: translucent white, fuel level showing, black cap and breather
    tank = (((X / 0.04) ** 4 + ((Y - 0.27) / 0.10) ** 4 + ((Z - 0.095) / 0.06) ** 4) <= 1)
    g.add(tank, TANK)
    g.paint(tank & (Z < 0.10), FUEL)
    g.add(((X ** 2 + (Y - 0.31) ** 2) <= 0.018 ** 2) & between(Z, 0.15, 0.17), DARK)
    g.add(tube([(0.0, 0.31, 0.17), (0.0, 0.35, 0.21), (0.0, 0.39, 0.20)], 0.004), HOSE)
    g.add(tube([(0.0, 0.18, 0.05), (0.10, 0.0, 0.04), (0.24, -0.08, 0.06), (0.30, -0.10, 0.12)], 0.004), HOSE)

    # ---- pedals: brake left, throttle right, faces square to the driver's shins
    shin = np.array((0.0, 0.978, -0.208))
    pup = np.array((0.0, 0.208, 0.978))
    for s, pad in ((-1, RUBBER), (1, RUBBER)):
        pc = (s * 0.185, 0.424, 0.135)
        u_, v_, w_ = local(pc, (1, 0, 0), pup, shin)
        face = between(u_, -0.035, 0.035) & between(v_, -0.05, 0.05) & between(w_, -0.006, 0.006)
        g.add(face, ALU)
        g.paint(face & (np.mod(np.floor((v_ + 0.05) / 0.02), 2) == 0) & (w_ < 0.0), pad)
        g.add(tube([(s * 0.185, 0.445, 0.05), (s * 0.185, 0.418, 0.10)], 0.008), ALU)    # pedal arm
        g.add(between(s * X, 0.165, 0.205) & between(Y, 0.425, 0.465) & between(Z, 0.034, 0.055), ALU)  # pivot
    g.add(tube([(-0.185, 0.45, 0.04), (-0.285, 0.42, 0.04), (-0.29, 0.34, 0.045), (-0.235, -0.40, 0.065)], 0.005),
          CHROME)                                                                      # brake rod
    g.add(tube([(0.185, 0.45, 0.04), (0.285, 0.42, 0.04), (0.29, 0.34, 0.05), (0.30, -0.08, 0.13)], 0.004), HOSE)  # throttle

    # ---- steering column, track rods, steering wheel (part STEER, turns about the column)
    g.add(tube([tuple(COL_LOW), tuple(WHEEL_HUB + COL_DIR * 0.03)], 0.011), CHROME)
    g.add(tube([tuple(COL_LOW + (0, 0, -0.01)), tuple(COL_LOW + (0, 0.045, -0.02))], 0.012), ALU)   # pitman arm
    for s in (1, -1):
        g.add(tube([(s * 0.03, COL_LOW[1] + 0.04, 0.065), (s * 0.39, WB_HALF - 0.055, 0.09)], 0.007), CHROME)
        for p_ in ((s * 0.03, COL_LOW[1] + 0.04, 0.065), (s * 0.39, WB_HALF - 0.055, 0.09)):
            g.add(tube([p_, p_], 0.012), ALU)                                         # rod ends
    a, b, c = local(WHEEL_HUB, (1, 0, 0), WHEEL_UP, -COL_DIR)                               # c: toward the driver
    rho = ((np.abs(a) / WHEEL_R) ** 4 + (np.abs(b) / WHEEL_RB) ** 4) ** 0.25
    ring = (np.abs(rho - 1.0) * 0.14 <= 0.0115) & between(c, -0.0115, 0.0115)
    g.put(ring, GRIP, STEER)
    grip = ring & (np.abs(a) > 0.13) & (np.abs(b) < 0.08)
    g.put(grip | ((np.abs(rho - 1.0) * 0.14 <= 0.0155) & between(c, -0.0155, 0.0155) & (np.abs(a) > 0.14)
                  & (np.abs(b) < 0.065)), GRIP, STEER)
    g.paint(ring & ~grip & (b > 0.11) & (np.abs(a) < 0.02), PIN, parts=(STEER,))                           # top-centre marker
    spokes = between(c, -0.03, -0.012) & (rho < 1.0) & (
        (np.abs(b) < 0.016) | ((np.abs(a) < 0.018) & (b < 0)))
    g.put(spokes & (rho > 0.25), ALU, STEER)
    hubm = between(c, -0.04, -0.008) & (a ** 2 + b ** 2 <= 0.045 ** 2)
    g.put(hubm, ALU, STEER)
    disp = between(a, -0.032, 0.032) & between(b, -0.012, 0.06) & between(c, -0.008, 0.016)  # data logger
    g.put(disp, BUMPER, STEER)
    g.paint(disp & between(a, -0.024, 0.024) & between(b, 0.014, 0.05) & (c > 0.004), SCREEN, parts=(STEER,))
    for bx in (-0.016, 0.016):
        g.paint(disp & (np.abs(a - bx) < 0.006) & between(b, -0.008, 0.004) & (c > 0.004), BRED, parts=(STEER,))
    g.put(between(c, -0.06, -0.035) & (a ** 2 + b ** 2 <= 0.022 ** 2), DARK, STEER)  # column boss

    # ---- front spindles (part spindle_*, steer about the kingpin): kingpin, stub axle, steering arm
    for name, (wx, wy, R, W, front) in WHEELS.items():
        if not front:
            continue
        s = 1 if wx > 0 else -1
        P = WHEEL_PART[name]
        g.put(tube([(s * KINGPIN_X, wy - 0.012, 0.05), (s * KINGPIN_X, wy + 0.008, 0.20)], 0.011), CHROME, P["spindle"])
        g.put(tube([(s * KINGPIN_X, wy, R), (s * (abs(wx) + W / 2 + 0.01), wy, R)], 0.009), CHROME, P["spindle"])
        g.put(tube([(s * KINGPIN_X, wy, 0.09), (s * 0.39, wy - 0.055, 0.09)], 0.008), CHROME, P["spindle"])
        g.put(between(s * X, KINGPIN_X - 0.005, KINGPIN_X + 0.05) & between(Y, wy - 0.02, wy + 0.02)
              & between(Z, R - 0.03, R + 0.03), CAST, P["spindle"])

    # ---- bodywork: front fairing (nose), nassau panel, side pods, rear bumper (CIK-style plastics)
    # front fairing: wide, low, rising to a lip in front of the nassau, two scoops, mounted on a chrome kit
    nw = fy([0.66, 0.70, 0.86, 0.93], [0.47, 0.50, 0.48, 0.40])
    ntop = fy([0.66, 0.69, 0.76, 0.88, 0.935], [0.125, 0.185, 0.17, 0.095, 0.05])
    corner = (AX - (nw - 0.07)) / 0.07
    ycorner = (Y - 0.865) / 0.07
    round_ = np.where((corner > 0) & (ycorner > 0), corner ** 2 + ycorner ** 2 <= 1, True)
    nose = between(Y, 0.66, 0.935) & (AX <= nw) & between(Z, 0.025, ntop) & round_
    nose &= ~(between(AX, 0.0, 0.17) & (Y < 0.70) & (Z > 0.06))                        # nassau slot
    g.add(nose, MAIN)
    g.paint(nose & (Z < 0.06), ACC)
    g.paint(nose & between(Z, 0.06, 0.07), PIN)
    for s in (1, -1):                                                                  # scoops
        sc = between(s * X, 0.24, 0.36) & between(Y, 0.80, 0.86) & (Z > ntop - 0.025)
        g.cut(sc & nose)
        g.paint(between(s * X, 0.23, 0.37) & between(Y, 0.79, 0.87) & (Z > ntop - 0.04), CAVITY, only=(MAIN,))
        g.add(tube([(s * 0.13, 0.75, zf), (s * 0.30, 0.72, 0.06), (s * 0.40, 0.66, 0.06)], 0.008), CHROME)
    # nassau panel: shield in front of the driver's shins, leaning back, number plate on its face
    nc = np.array((0.0, 0.49, 0.22))
    ntilt = math.radians(25)
    nup = np.array((0.0, -math.sin(ntilt), math.cos(ntilt)))
    nfwd = np.array((0.0, math.cos(ntilt), math.sin(ntilt)))
    crook = math.radians(7 if worn else 0)                                            # knocked crooked
    nx_ = np.cos(crook) * np.array((1.0, 0, 0)) + np.sin(crook) * nup
    nup = -np.sin(crook) * np.array((1.0, 0, 0)) + np.cos(crook) * nup
    u_, v_, w_ = local(nc, nx_, nup, nfwd)
    half = 0.13 + 0.06 * np.clip((v_ + 0.13) / 0.26, 0, 1)
    nas = between(v_, -0.14, 0.13) & (np.abs(u_) <= half) & between(w_, -0.0115, 0.0115)
    nas |= between(v_, 0.10, 0.13) & (np.abs(u_) <= half) & between(w_, -0.03, 0.0115)  # top lip
    g.add(nas, MAIN)
    g.paint(nas & (v_ > 0.10), ACC)
    g.paint(nas & between(v_, 0.09, 0.10), PIN)
    plate_n = nas & between(v_, -0.10, 0.07) & (np.abs(u_) <= 0.10) & (w_ > 0.0)
    g.paint(plate_n, PLATE)
    g.add(tube([tuple(WHEEL_HUB + COL_DIR * 0.20), tuple(nc + nup * 0.04 - nfwd * 0.012)], 0.007), ALU)  # upper bracket
    g.add(tube([(0.0, 0.53, 0.06), (0.0, 0.70, 0.06)], 0.008), CHROME)                 # lower nassau clip
    # side pods: low wings between the wheels, rising toward the back, mounted on chrome side bars
    for s in (1, -1):
        g.add(tube([(s * 0.31, 0.30, zf), (s * 0.50, 0.28, 0.06)], 0.009), CHROME)
        g.add(tube([(s * 0.31, -0.30, zf), (s * 0.50, -0.30, 0.06)], 0.009), CHROME)
    po = fy([-0.37, -0.30, 0.25, 0.37], [0.62, 0.665, 0.65, 0.58])
    pi_ = fy([-0.37, 0.37], [0.445, 0.445])
    pt = fy([-0.37, -0.32, 0.0, 0.30, 0.37], [0.19, 0.215, 0.18, 0.14, 0.10])
    pb = 0.045
    prof = np.clip((AX - pi_) / (po - pi_), 0, 1)
    pod_top = pt - 0.05 * prof ** 2                                                    # top rolls down to the edge
    pod = between(Y, -0.37, 0.37) & between(AX, pi_, po) & between(Z, pb, pod_top)
    g.add(pod, MAIN)
    pod_side = pod & (AX > po - 0.03)
    if "lower" in pats:
        g.paint(pod & (Z < pb + 0.45 * (pod_top - pb)), LOWER)
        g.paint(pod & between(Z, pb + 0.45 * (pod_top - pb), pb + 0.45 * (pod_top - pb) + VOX), PIN)
    g.paint(pod & (Z > pod_top - 0.0115) & (AX > po - 0.02), PIN)                      # edge pin line
    if "claws" in pats:
        d = Y + 0.6 * (AX - 0.45)
        g.paint(pod & between(d, -0.33, -0.06) & (np.mod(d + 0.33, 0.09) < 0.035) & (Z > pod_top - 0.02),
                ACC, only=(MAIN, PIN))
    g.paint(pod & between(Y, -0.37, -0.355), ACC)
    # side number plates on the back of each pod's outer face
    side_plate = pod_side & between(Y, -0.33, -0.16) & between(Z, 0.07, 0.17)
    g.paint(side_plate, PLATE)
    # rear bumper: full-width plastic guard behind the rear wheels on chrome bars, number panel in the middle
    for s in (1, -1):
        g.add(tube([(s * 0.27, -0.62, zf), (s * 0.27, -0.72, 0.07)], 0.009), CHROME)
        g.add(tube([(s * 0.235, -0.62, zf), (s * 0.45, -0.70, 0.06), (s * 0.60, -0.70, 0.06)], 0.009), CHROME)
    rb_w = 0.70
    rx = (AX - (rb_w - 0.07)) / 0.07
    ry_ = (-0.80 - Y) / 0.07
    rround = np.where((rx > 0) & (ry_ > 0), rx ** 2 + ry_ ** 2 <= 1, True)
    rtop = fy([-0.87, -0.82, -0.72, -0.68], [0.14, 0.215, 0.20, 0.12])
    if worn:                                                                           # bent: sags on the right
        rtop = rtop - 0.03 * np.clip(X / 0.70, 0, 1) ** 2
    rbump = between(Y, -0.87, -0.68) & (AX <= rb_w) & between(Z, 0.035, rtop) & rround
    g.add(rbump, BUMPER, RBUMP)
    g.paint(rbump & (np.mod(np.floor((Y + 0.87) / VOX), 3) == 0) & between(Y, -0.80, -0.70) & (Z > rtop - 0.02)
            & (AX < 0.62), CAVITY, parts=(RBUMP,))                                                     # moulded ribs
    g.paint(rbump & (AX > rb_w - 0.04), MAIN, parts=(RBUMP,))
    g.paint(rbump & between(AX, rb_w - 0.05, rb_w - 0.04), PIN, parts=(RBUMP,))
    rplate = rbump & (Y < -0.855) & (AX <= 0.10) & between(Z, 0.075, 0.185)
    g.paint(rplate, PLATE, parts=(RBUMP,))

    # ---- wheels
    for name, (wx, wy, R, W, front) in WHEELS.items():
        wheel(g, name, wx, wy, R, W, front, tyre)

    # ================================================================ livery (paint only)
    if "nose_tip" in pats:
        g.paint(nose & (Y > 0.86), ACCENT2, only=(MAIN, PIN))
    # numbers: nassau (front), both pods (sides), rear bumper (back) — black on the number plates
    num = text_bitmap(number, F57)
    up_n = np.array((0.0, 0.0, 1.0))
    # nassau: stamp along the panel normal in its own frame
    h, w = num.shape
    ps = 1.5 * VOX                                       # number pixel on the nassau (reads from the front)
    mask = np.zeros(SHAPE, bool)
    for r_, c_ in zip(*np.nonzero(num)):
        uu = -(c_ - (w - 1) / 2) * ps
        vv = -0.015 + ((h - 1) / 2 - r_) * ps
        mask |= between(u_, uu - ps / 2, uu + ps / 2) & between(v_, vv - ps / 2, vv + ps / 2)
    g.paint(mask & plate_n, INK)
    big = np.kron(num, np.ones((1, 1), bool))
    for s in (1, -1):
        g.stamp(big, (s * 0.66, -0.245, 0.122), ("+y" if s > 0 else "-y"), "+z", INK,
                depth=(s * 0.55, s * 0.70) if s > 0 else (-0.70, -0.55), only=(PLATE,))
    g.stamp(big, (0.0, -0.87, 0.13), "+x", "+z", INK, depth=(-0.88, -0.85), only=(PLATE,), parts=(RBUMP,))
    # sponsor-style decals (placeholder words)
    D = L["decals"]
    word = text_bitmap(D["pod"], F35, scale=1, spacing=1)
    for s in (1, -1):
        g.stamp(word, (s * 0.54, 0.06, 0.20), "+y" if s > 0 else "-y", "-x" if s > 0 else "+x", WHITE,
                depth=(0.08, 0.26), only=(MAIN, PIN))
    g.stamp(text_bitmap(D["nose"], F35, scale=2), (0.0, 0.775, 0.20), "-x", "-y", WHITE, depth=(0.10, 0.25),
            only=(MAIN, ACCENT2))
    g.stamp(text_bitmap(D["bumper"], F35, scale=1), (-0.40, -0.835, 0.20), "+x", "+y", WHITE, depth=(0.18, 0.24),
            only=(BUMPER,), parts=(RBUMP,))
    g.stamp(text_bitmap(D["bumper"], F35, scale=1), (0.40, -0.835, 0.20), "+x", "+y", WHITE, depth=(0.18, 0.24),
            only=(BUMPER,), parts=(RBUMP,))

    if worn:
        beat_up(g, dict(nose=nose, pod=pod, nas=nas, seat=seat, disp=disp, ntop=ntop, number=number), heavy)
    rgb = colours(g.m, livery, condition)
    if worn:
        rgb = weather(rgb, g.m, g.p, heavy)
    return dict(m=g.m, part=g.p, rgb=rgb, tyre=tyre, number=number, livery=livery, condition=condition)


def _exposed(mask):
    """Voxels of mask with at least one empty neighbour (the visible skin)."""
    pad = np.pad(mask, 1)
    inner = pad[1:-1, 1:-1, 1:-1]
    nb = (pad[2:, 1:-1, 1:-1] & pad[:-2, 1:-1, 1:-1] & pad[1:-1, 2:, 1:-1] & pad[1:-1, :-2, 1:-1]
          & pad[1:-1, 1:-1, 2:] & pad[1:-1, 1:-1, :-2])
    return inner & ~nb


def _sphere(c, r):
    return (X - c[0]) ** 2 + (Y - c[1]) ** 2 + (Z - c[2]) ** 2 <= r * r


def beat_up(g, k, heavy=False):
    """A fifth-hand kart: chips and broken corners, a cracked nose taped up, scratches and side scrapes, peeling
    decals, a mismatched replacement pod with a hand-painted number, rust on the frame, chain and exhaust, chunked
    and mismatched tyres, an odd rim, taped grips, no data logger, no transponder, zip ties. Deterministic."""
    rng = np.random.default_rng(5)
    BODYM = [MAIN, ACC, PIN, LOWER, ACCENT2, WHITE, PLATE, INK]

    def shell():
        return ((np.isin(g.m, BODYM) & (g.p == BODY)) | ((g.p == RBUMP) & (g.m > 0))) | (g.m == PATCH)
    # replacement right side pod: plain yellow, no plate, number painted on by hand
    rp = k["pod"] & (X > 0)
    g.paint(rp, PATCH, only=[MAIN, ACC, PIN, LOWER, WHITE, PLATE, INK])
    g.stamp(text_bitmap(k["number"], F57), (0.66, -0.23, 0.115), "+y", "+z", INK, depth=(0.55, 0.70), only=(PATCH,))
    # peeling decals: patches of the white lettering gone back to the base colour
    peel = blobs(11, 0.05) > 0.68
    g.paint(peel, MAIN, only=[WHITE])
    g.paint(peel, BUMPER, parts=(RBUMP,), only=[WHITE])
    # broken corners and chips (cut, then the raw plastic shows round the break)
    breaks = [((-0.43, 0.905, 0.07), 0.045), ((0.66, -0.85, 0.15), 0.04), ((-0.62, 0.30, 0.13), 0.025)]
    exp = np.argwhere(_exposed(shell()) & (Z > 0.06))
    for i in rng.choice(len(exp), 10, replace=False):
        breaks.append(((xs[exp[i][0]], ys[exp[i][1]], zs[exp[i][2]]), VOX * rng.uniform(1.2, 1.9)))
    for c, r in breaks:
        g.cut(_sphere(c, r) & shell())
        g.paint(_sphere(c, r + 0.9 * VOX), SCRATCH, parts=(BODY,), only=BODYM + [PATCH])
        g.paint(_sphere(c, r + 0.9 * VOX), SCUFF, parts=(RBUMP,), only=[BUMPER])
    # crack across the nose, taped over with duct tape
    top = k["ntop"]
    for x_, y_, _z in catmull([(0.10, 0.705, 0), (0.16, 0.745, 0), (0.14, 0.785, 0), (0.22, 0.83, 0),
                               (0.20, 0.87, 0)], 8):
        g.paint((np.abs(X - x_) < 0.007) & (np.abs(Y - y_) < 0.007) & (Z > top - 0.03), CAVITY,
                only=[MAIN, ACC, PIN, WHITE, SCRATCH])
    tape = k["nose"] & (Z > top - 0.03)
    g.paint(tape & between(X, 0.09, 0.27) & between(Y, 0.765, 0.80), TAPE, only=[MAIN, ACC, PIN, WHITE, CAVITY, SCRATCH])
    g.paint(tape & between(X, 0.16, 0.20) & between(Y, 0.70, 0.83), TAPE, only=[MAIN, ACC, PIN, WHITE, CAVITY, SCRATCH])
    # scratches on the bodywork: short strokes that follow the surface
    expo = _exposed(shell())
    cand = np.argwhere(expo & (Z > 0.07))
    for i in rng.choice(len(cand), 32, replace=False):
        i0, j0, k0 = (int(v) for v in cand[i])
        ang = rng.uniform(0, np.pi) if rng.random() < 0.5 else rng.normal(0, 0.25)
        for t in range(int(rng.integers(3, 9))):
            ii, jj = int(round(i0 + t * np.sin(ang))), int(round(j0 + t * np.cos(ang)))
            if not (0 <= ii < NX and 0 <= jj < NY):
                break
            lo = max(0, k0 - 3)
            col = np.nonzero(expo[ii, jj, lo:k0 + 4])[0]
            if not len(col):
                break
            k0 = lo + int(col[np.argmin(np.abs(col + lo - k0))])
            g.m[ii, jj, k0] = SCUFF if g.m[ii, jj, k0] in (BUMPER, SCUFF) else SCRATCH
    # long scrapes along both pods' outer faces
    sk = shell()
    for s, z0, y0, ln in ((1, 0.09, -0.30, 0.42), (1, 0.12, -0.10, 0.30), (-1, 0.10, -0.25, 0.50),
                          (-1, 0.075, 0.05, 0.25)):
        for jj in range(to_i(y0, 1), to_i(y0 + ln, 1)):
            for dk in (0, 1):
                kk = to_i(z0 + 0.012 * np.sin(jj * 0.7), 2) + dk
                row = np.nonzero(sk[:, jj, kk])[0]
                row = row[xs[row] * s > 0]
                if len(row) and (dk == 0 or rng.random() < 0.5):
                    g.m[row.max() if s > 0 else row.min(), jj, kk] = SCRATCH
    # tyre rubber smeared on the rear bumper by other karts
    for _ in range(9):
        c = (rng.uniform(-0.6, 0.6), rng.uniform(-0.86, -0.70))
        g.paint(((X - c[0]) / 0.05) ** 2 + ((Y - c[1]) / 0.012) ** 2 <= 1, RUBBER, parts=(RBUMP,), only=[BUMPER])
    # rust: on the frame (worst low down), the chrome bars, chain, silencer and brake disc
    rb = blobs(21, 0.07)
    if heavy:   # years outside: rust everywhere metal, the exhaust burnt black and brown
        rb2 = blobs(23, 0.05)
        g.paint((rb > 0.42) | ((Z < 0.06) & (rb > 0.3)), RUST, only=[FRAME])
        g.paint((rb2 > 0.55) & (g.m == FRAME), RUST2, only=[FRAME])
        g.paint(rb > 0.45, RUST, only=[CHROME])
        g.paint(rb2 > 0.6, RUST2, only=[CHROME])
        g.paint(True, RUST2, only=[CHAIN])
        g.paint(rb2 > 0.45, RUST, only=[EXHAUST])
        g.paint(True, SOOT, only=[EXHAUST])
        g.paint((rb > 0.4) & (X < -0.2) & (Y < -0.5), RUST, only=[CHROME])
        g.paint(True, RUST, parts=(AXLE,), only=[DISC])
        g.paint(rb2 > 0.5, RUST2, parts=(AXLE,), only=[SPROCKET, HUB, ALU])
        g.paint(rb > 0.55, RUST2, only=[CALIPER, ALU])
        # the front fairing is long gone: bare fairing brackets and an old tube bumper instead
        g.cut(k["nose"] & (g.p == BODY) & ~np.isin(g.m, [CHROME, FRAME, ALU, ZIP]))
        for s in (1, -1):                                          # old front bumper loop, painted like the frame
            g.add(tube(catmull([(s * 0.13, 0.75, 0.045), (s * 0.24, 0.80, 0.06), (s * 0.20, 0.86, 0.07),
                                (0.0, 0.875, 0.075)], 6), 0.012), FRAME)
        g.paint((blobs(24, 0.06) > 0.40) & (Y > 0.62), RUST, only=[FRAME])
        g.paint((Y > 0.62) & (blobs(25, 0.05) > 0.3), RUST, only=[CHROME])
        g.paint((Y > 0.62), RUST2, only=[CHROME])
        # more damage to the pods and bumper: big broken chunks, a split taped up on the left pod
        for c, r in (((-0.60, 0.33, 0.12), 0.04), ((-0.66, -0.05, 0.10), 0.03), ((0.60, 0.34, 0.11), 0.035),
                     ((-0.40, -0.86, 0.12), 0.035), ((0.25, -0.86, 0.18), 0.03)):
            g.cut(_sphere(c, r) & ((g.p == RBUMP) | ((g.p == BODY) & np.isin(g.m, [MAIN, ACC, PIN, PATCH, WHITE,
                                                                                      PLATE, INK, SCRATCH]))))
        for x_, y_, _z in catmull([(-0.47, -0.10, 0), (-0.53, -0.04, 0), (-0.51, 0.03, 0), (-0.60, 0.09, 0)], 8):
            g.paint((np.abs(X - x_) < 0.007) & (np.abs(Y - y_) < 0.007), CAVITY, only=[MAIN, PIN, WHITE, SCRATCH])
        g.paint(k["pod"] & between(X, -0.62, -0.46) & between(Y, -0.04, 0.01) & (Z > 0.12), TAPE,
                only=[MAIN, PIN, WHITE, SCRATCH, CAVITY])
    else:
        g.paint((rb > 0.68) | ((Z < 0.05) & (rb > 0.55)), RUST, only=[FRAME])
        g.paint(rb > 0.70, RUST2, only=[CHROME])
        g.paint(rb > 0.55, RUST2, only=[CHAIN])
        g.paint((rb > 0.68) & (X < -0.2) & (Y < -0.5), RUST2, only=[CHROME, EXHAUST])
        g.paint(blobs(22, 0.05) > 0.66, RUST, parts=(AXLE,), only=[DISC])
    # tyres: chunked rear treads, the right rear from another set (no bands), an odd front-left rim
    for name, (cx, cy, R_, W_, front) in WHEELS.items():
        if front:
            continue
        for _ in range(10):
            th = rng.uniform(0, 2 * np.pi)
            c = (cx + rng.uniform(-W_ / 2.5, W_ / 2.5), cy + R_ * np.cos(th), R_ + R_ * np.sin(th))
            g.cut(_sphere(c, VOX * rng.uniform(1.0, 1.6)) & (g.p == WHEEL_PART[name]["tyre"]))
    g.paint(True, SIDEWALL, parts=(WHEEL_PART["RR"]["tyre"],), only=[WHITE])
    g.paint(True, RIM2, parts=(WHEEL_PART["FL"]["rim"],), only=[RIM, HUB])
    # seat: scuffs and a cracked back edge taped up; the pin line long worn off
    a, b, _ = local(HIP, SPINE, FWD, (1, 0, 0))
    g.paint(k["seat"], SEATM, only=[PIN])
    g.paint(k["seat"] & between(a, 0.30, 0.38) & between(X, -0.20, -0.09), TAPE, only=[SEATM])
    sx = np.argwhere(_exposed(g.m == SEATM) & (np.abs(X) > 0.15))                 # scuffs on the bolsters
    for i in rng.choice(len(sx), 14, replace=False):
        g.paint(_sphere((xs[sx[i][0]], ys[sx[i][1]], zs[sx[i][2]]), VOX * rng.uniform(0.8, 1.6)), SCUFF, only=[SEATM])
    # steering wheel: grips wrapped in tape, data logger gone (bare hub); transponder gone
    sa, sb, sc = local(WHEEL_HUB, (1, 0, 0), WHEEL_UP, -COL_DIR)
    g.paint((np.abs(sa) > 0.12) & (np.mod(np.floor((sb + 0.2) / (2 * VOX)), 2) == 0), TAPE, parts=(STEER,),
            only=[GRIP])
    g.cut(k["disp"] & (g.p == STEER))
    g.cut(g.m == TRANSP)
    # zip ties holding the nose and the crooked nassau on
    for c in ((-0.40, 0.655, 0.06), (0.40, 0.655, 0.06), (0.0, 0.62, 0.06), (-0.12, 0.47, 0.10), (0.12, 0.47, 0.10)):
        g.add((np.abs(X - c[0]) < 0.006) & (np.abs(Y - c[1]) < 0.012) & (np.abs(Z - c[2]) < 0.017), ZIP)
    # a corner of the nassau gone
    g.cut(_sphere((0.17, 0.42, 0.34), 0.035) & k["nas"])


def weather(rgb, m, p, heavy=False):
    """Colour-only wear: sun-faded, patchy paint; dirt and grit low down and behind the wheels; oil by the engine.
    heavy: years of it - yellowed plastics, grime over everything, dusty tyres, soot round the exhaust."""
    rgb = rgb.copy()
    fade = blobs(41, 0.18)
    sel = np.isin(m, WORN_MATS + (SCRATCH, TAPE, SCUFF))
    c = rgb[sel]
    lum = (c @ np.array([0.2126, 0.7152, 0.0722], np.float32))[:, None]
    k = 0.08 + 0.14 * fade[sel][:, None]
    c = c * (1 - k) + (lum * 1.05 + 0.012) * k                                          # sun-faded
    c *= (0.90 + 0.14 * blobs(42, 0.06)[sel])[:, None]
    rgb[sel] = c
    dirt = np.array(_hex("#6B5E4E"), np.float32)
    grit = blobs(43, 0.04)
    low = np.clip((0.12 - Z) / 0.12, 0, 1) * (0.35 + 0.5 * grit)
    near_rear = (np.abs(np.abs(X) - 0.6) < 0.16) & between(Y, -0.80, -0.30) & (Z < 0.22) & (grit > 0.55)
    w = np.clip(low + 0.45 * near_rear, 0, 0.8)
    w = np.where(np.isin(m, [SIDEWALL, TREAD, TREAD_DARK]), np.minimum(w, 0.03 if heavy else 0.25), w)
    w = np.where(m > 0, w, 0).astype(np.float32)[..., None]
    rgb = rgb * (1 - w) + dirt * w
    oil = between(X, 0.18, 0.50) & between(Y, -0.45, 0.0) & (Z < 0.26) & (blobs(44, 0.05) > 0.6)
    oil |= between(X, -0.25, 0.25) & between(Y, 0.0, 0.7) & (Z < 0.04) & (blobs(45, 0.08) > 0.68)
    rgb[np.broadcast_to(oil, SHAPE)] *= 0.45
    if heavy:
        filled = m > 0
        # light plastics yellowed and stained
        body = np.isin(m, WORN_MATS + (SCRATCH, TAPE, SCUFF))
        lum = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        yel = (body & (lum > 0.25)).astype(np.float32)[..., None] * (0.35 + 0.4 * blobs(46, 0.12))[..., None]
        rgb = rgb * (1 - yel) + rgb * np.array((1.0, 0.86, 0.58), np.float32) * yel
        rgb[body] *= 0.86
        # grime over everything, heavier low down and in streaks
        grime = np.array(_hex("#3B332A"), np.float32)
        gb = blobs(47, 0.05)
        tyre = np.isin(m, [SIDEWALL, TREAD, TREAD_DARK])
        w = np.clip(0.06 + 0.22 * gb + 0.40 * np.clip((0.16 - Z) / 0.16, 0, 1), 0, 0.8)
        w = np.where(tyre, np.minimum(w, 0.02), w)
        w = np.where(filled, w, 0).astype(np.float32)[..., None]
        rgb = rgb * (1 - w) + grime * w
        # dusty tyres
        dust = np.array(_hex("#827666"), np.float32)
        dw = (0.01 + 0.03 * blobs(48, 0.03))[tyre][:, None]
        rgb[tyre] = rgb[tyre] * (1 - dw) + dust * dw
        # soot behind and above the exhaust, burnt engine area
        soot = (between(Y, -0.78, -0.30) & between(Z, 0.14, 0.48) & between(X, -0.48, 0.50)
                & (blobs(49, 0.08) > 0.35))
        soot |= between(X, 0.22, 0.48) & between(Y, -0.42, -0.08) & (blobs(50, 0.05) > 0.35)
        rgb[np.broadcast_to(soot, SHAPE) & filled] *= 0.5
    return rgb.astype(np.float32)


def wheel(g, name, cx, cy, R, W, front, tyre="slick"):
    P = WHEEL_PART[name]
    s = 1 if cx > 0 else -1           # outward
    hw = W / 2
    (i0, i1) = irange(cx - hw - 0.03, cx + hw + 0.03, 0)
    (j0, j1), (k0, k1) = irange(cy - R - 0.02, cy + R + 0.02, 1), irange(0, 2 * R + 0.04, 2)
    px, py, pz = xs[i0:i1, None, None], ys[None, j0:j1, None], zs[None, None, k0:k1]
    u = s * (px - cx)
    dy, dz = py - cy, pz - R
    r = np.sqrt(dy * dy + dz * dz)
    th = np.arctan2(dz, dy)
    sub = (slice(i0, i1), slice(j0, j1), slice(k0, k1))

    def full(mask):
        f = np.zeros(SHAPE, bool)
        f[sub] = np.broadcast_to(mask, f[sub].shape)
        return f

    def put(mask, mat, part):
        g.put(full(mask), mat, part)

    def paint(mask, mat, part):
        g.paint(full(mask), mat, parts=(part,))

    au = np.abs(u)
    r_bead = 0.0675
    # tyre: balloon sidewalls, rounded shoulders
    rc = 0.03
    a = au - (hw - rc)
    rlim = np.where(a > 0, R - rc + np.sqrt(np.clip(rc * rc - a * a, 0, None)), R)
    bulge = hw + 0.004 * np.clip(1 - np.abs(r - (r_bead + R) / 2) / 0.04, 0, 1)
    tyre_m = (au <= bulge) & (r <= rlim) & (r >= r_bead)
    put(tyre_m, SIDEWALL, P["tyre"])
    tread = tyre_m & (r > rlim - 0.012) & (au < hw - 0.01)
    paint(tread, TREAD, P["tyre"])
    if tyre == "wet":  # directional V grooves
        ang = th * R
        v = np.mod(ang + 0.6 * au, 0.05)
        paint(tread & (v < 0.0115) & (au < hw - 0.012), TREAD_DARK, P["tyre"])
        paint(tread & (au < 0.006), TREAD_DARK, P["tyre"])
    # outer sidewall: two white arcs (front and back) and a ring at the bead, like a kart tyre's brand band
    side = tyre_m & (au > hw - 0.012) & (u > 0)
    arcs = np.abs(np.cos(th)) > 0.62
    paint(side & between(r, R - 0.034, R - 0.034 + VOX) & arcs, WHITE, P["tyre"])
    paint(side & between(r, R - 0.034 - 2 * VOX, R - 0.034 - VOX) & arcs & (np.abs(np.cos(th)) > 0.75), WHITE,
          P["tyre"])
    # rim: barrel, outer lip, recessed face with six lightening holes, three studs (rear) or a centre nut (front)
    put((r >= r_bead - 0.012) & (r < r_bead) & (au <= hw - 0.004), RIM, P["rim"])
    put((r >= r_bead - 0.012) & (r < r_bead + 0.006) & between(u, hw - 0.012, hw), RIM, P["rim"])   # lip
    put((r < r_bead - 0.012) & between(u, hw - 0.03, hw - 0.018), RIM, P["rim"])                   # face
    hole_c = np.mod(th + np.pi / 6, np.pi / 3) - np.pi / 6
    holes = ((r * np.sin(hole_c)) ** 2 + (r * np.cos(hole_c) - 0.038) ** 2) <= 0.0105 ** 2
    g.paint(full(holes & between(u, hw - 0.031, hw - 0.017) & (r < r_bead - 0.012)), CAVITY, parts=(P["rim"],))
    put((r < 0.03) & between(u, hw - 0.036, hw - 0.012), HUB, P["rim"])
    if front:
        put((r < 0.015) & between(u, hw - 0.012, hw + 0.004), NUT, P["rim"])
        put((r < 0.02) & between(u, -hw - 0.004, hw - 0.03), ALU, P["rim"])                    # bearing hub
    else:
        stud_c = np.mod(th, 2 * np.pi / 3) - np.pi / 3
        studs = ((r * np.sin(stud_c)) ** 2 + (r * np.cos(stud_c) - 0.02) ** 2) <= 0.0065 ** 2
        put(studs & between(u, hw - 0.012, hw - 0.002), NUT, P["rim"])
    # valve stem
    put((np.abs(dy + 0.03) < 0.005) & (np.abs(dz - 0.045) < 0.005) & between(u, hw - 0.03, hw - 0.005), CHROME,
        P["rim"])


def colours(m, livery="silver_arrow", condition="new"):
    """Per-voxel linear colour: the material's colour plus a deterministic pixel texture (one texel per voxel)."""
    I, J, K = np.indices(SHAPE)
    h = ((I * 73856093) ^ (J * 19349663) ^ (K * 83492791)) & 0xFFFF
    noise = h / 65535.0
    rgb = np.zeros(SHAPE + (3,), np.float32)
    for mid in MATS:
        d = mat_spec(mid, livery, condition)
        sel = m == mid
        if not sel.any():
            continue
        base = np.array(_hex(d["hex"]), np.float32)
        amp = d.get("noise", 0.06)
        f = (1 - amp) + 2 * amp * noise[sel]
        c = base[None, :] * f[:, None]
        if "hex2" in d:  # grille / chain / checker plate: checker of two tones
            alt = np.array(_hex(d["hex2"]), np.float32)
            chk = ((I + J + K)[sel] % 2 == 0)
            c[chk] = alt[None, :] * f[chk][:, None]
        if d["name"] == "exhaust":  # heat tint along the header
            t = np.clip((-0.33 - ys[J[sel]]) / 0.20, 0, 1) * (xs[I[sel]] > 0.15)
            gold, blue = np.array(_hex("#C9A44A")), np.array(_hex("#4B4F9C"))
            k = (1 - t)[:, None] * (xs[I[sel]] > 0.15)[:, None] * 0.75
            c = c * (1 - k) + (gold * (1 - t[:, None]) + blue * t[:, None]) * k
        rgb[sel] = c
    return rgb


# parts of the kart the sheet points at (metres)
ANCHORS = {
    "front_fairing": (-0.30, 0.80, 0.15), "nassau": (0.0, 0.50, 0.32), "steering_wheel": (-0.15, 0.03, 0.51),
    "data_logger": (0.0, -0.005, 0.515), "seat": (-0.20, -0.30, 0.30), "side_pod": (-0.60, 0.05, 0.15),
    "number_side": (-0.665, -0.245, 0.12), "rear_bumper": (-0.55, -0.80, 0.18), "engine": (0.40, -0.25, 0.20),
    "exhaust": (-0.20, -0.55, 0.32), "silencer": (-0.33, -0.66, 0.33), "radiator": (-0.44, -0.17, 0.30),
    "fuel_tank": (-0.05, 0.25, 0.12), "pedals": (-0.185, 0.412, 0.135), "frame": (-0.36, 0.30, 0.045),
    "rear_axle": (0.0, -0.5175, 0.16), "brake_disc": (-0.12, -0.5175, 0.23), "sprocket": (0.42, -0.5175, 0.22),
    "chain": (0.42, -0.36, 0.16), "front_tyre": (-0.596, 0.5175, 0.124), "rear_tyre": (-0.70, -0.5175, 0.135),
    "kingpin": (-0.42, 0.5175, 0.20), "transponder": (-0.12, -0.36, 0.20), "floor_tray": (-0.12, 0.55, 0.03),
    "track_rod": (-0.25, 0.45, 0.08), "number_front": (0.0, 0.545, 0.22), "airbox": (0.40, -0.01, 0.17),
    "rim": (-0.596, 0.5175, 0.124),
}

# Where the block driver sits (master character at scale 1, helmet on): neck point, hands at 9 and 3 on the wheel,
# elbow poles out and down. Checked by fit_check.py.
_neck = [float(v) for v in HIP + 0.54 * SPINE]
SEAT = dict(neck=tuple(_neck), pose="kart",
            grips=(tuple(float(v) for v in WHEEL_HUB - (WHEEL_R, 0, 0)), tuple(float(v) for v in WHEEL_HUB + (WHEEL_R, 0, 0))),
            poles=((-0.42, -0.05, -0.25), (0.42, -0.05, -0.25)), pole_angle=90.0)
