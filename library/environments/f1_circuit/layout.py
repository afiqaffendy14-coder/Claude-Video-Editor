"""The circuit as data: centre line, widths, corners, run-off, kerbs, pit lane, zones. Pure numpy, no Blender.

One layout, every video. Units are metres. Axes match the car and character libraries: +X east, +Y north, +Z up,
ground at z = 0. The main straight runs east along y = 0 and the lap runs clockwise.

The track is a chain of primitives (straights and constant-radius arcs), so the distance from any point to the
track is exact and cheap: `nearest(x, y)` gives the lap distance s, the signed lateral offset (+ = left of the
driving direction) and which primitive is nearest. Everything else (surfaces, kerbs, barriers, props) is placed
from s and offset.
"""
import math
import numpy as np

# ---------------------------------------------------------------- the lap
# ("S", length, label) straight;  ("C", radius, degrees (+ left / - right), label) arc.
# The two straights marked adjustable get their lengths solved so the lap closes exactly.
TRACK = [
    ("S", 980.0, "main straight"),
    ("C", 30.0, -90.0, "T1"),
    ("S", 95.0, ""),
    ("C", 42.0, 70.0, "T2"),
    ("S", 150.0, ""),
    ("C", 160.0, -70.0, "T3"),
    ("S", 230.0, ""),
    ("C", 24.0, -180.0, "T4"),
    ("S", 170.0, ""),
    ("C", 48.0, 90.0, "T5"),
    ("S", 70.0, ""),
    ("C", 48.0, 90.0, "T6"),
    ("S", None, ""),                    # adjustable (runs south)
    ("C", 28.0, -90.0, "T7"),
    ("S", 70.0, ""),
    ("C", 80.0, 45.0, "T8"),
    ("C", 80.0, -45.0, "T9"),
    ("S", None, "back straight"),       # adjustable (runs west)
    ("C", 22.0, -90.0, "T10"),
    ("S", 110.0, ""),
    ("C", 150.0, 30.0, "T11"),
    ("C", 150.0, -30.0, "T12"),
    ("S", 150.0, ""),
    ("C", 16.0, 45.0, "T13"),
    ("S", 18.0, ""),
    ("C", 16.0, -45.0, "T14"),
    ("S", 200.0, ""),
    ("C", 65.0, -90.0, "T15"),
]
START = (-420.0, 0.0)          # where the main straight begins (just after T13)
WIDTH = 13.0                    # normal track width
WIDTH_AT = {"main straight": 15.0, "T4": 15.0, "T1": 14.0, "T10": 14.0}

# per corner: outside run-off (kind, width in m beyond the kerb), inside verge width, braking boards, sausage kerb
# kinds: gravel (trap with a 3 m asphalt strip before it), asphalt (painted run-off), grass
CORNERS = {
    "T1": dict(out=("asphalt", 55), inside=10, boards=True, name="Turn 1"),
    "T2": dict(out=("gravel", 30), inside=8, name="Turn 2"),
    "T3": dict(out=("gravel", 60), inside=10, name="Turn 3 (fast sweeper)"),
    "T4": dict(out=("asphalt", 45), inside=7, boards=True, name="Turn 4 (hairpin)"),
    "T5": dict(out=("gravel", 25), inside=8, name="Turn 5"),
    "T6": dict(out=("gravel", 30), inside=8, name="Turn 6"),
    "T7": dict(out=("asphalt", 45), inside=9, name="Turn 7"),
    "T8": dict(out=("gravel", 35), inside=8, name="Turn 8 (esses)"),
    "T9": dict(out=("gravel", 35), inside=8, name="Turn 9 (esses)"),
    "T10": dict(out=("asphalt", 55), inside=9, boards=True, name="Turn 10 (heavy braking)"),
    "T11": dict(out=("gravel", 45), inside=10, name="Turn 11 (fast S)"),
    "T12": dict(out=("gravel", 45), inside=10, name="Turn 12 (fast S)"),
    "T13": dict(out=("asphalt", 30), inside=6, boards=True, sausage=True, name="Turn 13 (chicane)"),
    "T14": dict(out=("asphalt", 30), inside=6, sausage=True, name="Turn 14 (chicane)"),
    "T15": dict(out=("gravel", 40), inside=9, name="Turn 15 (last corner)"),
}
VERGE = 9.0              # grass between the track and the barrier along straights
KERB_W = 1.5             # kerb width (red/white, 1 m stripes)
STRIPE = 1.0

# ---------------------------------------------------------------- the pit lane (right of the main straight)
PIT_Y = -24.0            # pit lane centre line
PIT_W = 13.0             # fast lane + working lane
PIT_WALL_Y = -12.5       # pit wall centre (track edge is at -7.5)
GARAGE_Y = -31.5         # garage fronts
PIT_X = (-420.0, 100.0)  # straight part of the pit lane (garages from GARAGE_X)
GARAGE_X0, GARAGE_N, GARAGE_W = -200.0, 10, 22.0   # ten teams, 22 m per team (two bays)
PIT_LIMIT = (-430.0, 200.0)   # speed limit lines on the pit lane

# ---------------------------------------------------------------- zones along the lap (s ranges filled in below)
SF_X = 0.0               # start/finish line x on the main straight
GRID_SLOTS = 20
GRID_PITCH = 8.0         # 8 m between grid slots, staggered left/right


# ================================================================ geometry
class Prim:
    def __init__(self, kind, p0, h0, length=0.0, radius=0.0, angle=0.0, label=""):
        self.kind, self.p0, self.h0, self.label = kind, np.array(p0, float), h0, label
        self.radius, self.angle = radius, math.radians(angle)
        self.length = length if kind == "S" else radius * abs(self.angle)
        if kind == "C":
            sgn = 1.0 if angle > 0 else -1.0
            self.sgn = sgn
            self.c = self.p0 + sgn * radius * np.array([-math.sin(h0), math.cos(h0)])
        self.s0 = 0.0

    def end(self):
        if self.kind == "S":
            return self.p0 + self.length * np.array([math.cos(self.h0), math.sin(self.h0)]), self.h0
        h1 = self.h0 + self.angle
        return self.c - self.sgn * self.radius * np.array([-math.sin(h1), math.cos(h1)]), h1

    def at(self, t):
        """Point, heading and curvature at distance t (array) along the primitive."""
        t = np.asarray(t, float)
        if self.kind == "S":
            d = np.array([math.cos(self.h0), math.sin(self.h0)])
            p = self.p0[None] + t[:, None] * d[None]
            return p, np.full(t.shape, self.h0), np.zeros(t.shape)
        h = self.h0 + self.sgn * t / self.radius
        p = self.c[None] - self.sgn * self.radius * np.stack([-np.sin(h), np.cos(h)], 1)
        return p, h, np.full(t.shape, self.sgn / self.radius)

    def nearest(self, x, y):
        """(t along, signed lateral offset +left, distance) for points x, y (arrays)."""
        if self.kind == "S":
            d = np.array([math.cos(self.h0), math.sin(self.h0)])
            n = np.array([-d[1], d[0]])
            rx, ry = x - self.p0[0], y - self.p0[1]
            t = rx * d[0] + ry * d[1]
            lat = rx * n[0] + ry * n[1]
            tc = np.clip(t, 0, self.length)
            dist = np.hypot(rx - tc * d[0], ry - tc * d[1])
            return tc, lat, dist, t
        rx, ry = x - self.c[0], y - self.c[1]
        r = np.hypot(rx, ry)
        # angle of the point around the centre, measured from the start radius, in the turning direction
        a0 = math.atan2(self.p0[1] - self.c[1], self.p0[0] - self.c[0])
        a = np.arctan2(ry, rx) - a0
        a = self.sgn * a
        a = np.mod(a + math.pi - abs(self.angle) / 2, 2 * math.pi) - math.pi + abs(self.angle) / 2
        t = a * self.radius
        tc = np.clip(t, 0, self.length)
        # lateral: + left. For a left turn the centre is on the left, so lat = R - r
        lat = self.sgn * (self.radius - r)
        ac = tc / self.radius * self.sgn + a0
        px, py = self.c[0] + self.radius * np.cos(ac), self.c[1] + self.radius * np.sin(ac)
        dist = np.hypot(x - px, y - py)
        return tc, lat, dist, t


def _chain(spec, start, h0, lengths):
    prims, p, h, k = [], np.array(start, float), h0, 0
    for item in spec:
        if item[0] == "S":
            L = item[1] if item[1] is not None else lengths[k]
            if item[1] is None:
                k += 1
            pr = Prim("S", p, h, length=L, label=item[2])
        else:
            pr = Prim("C", p, h, radius=item[1], angle=item[2], label=item[3])
        prims.append(pr)
        p, h = pr.end()
    return prims, p, h


def _closed(spec, start, h0=0.0):
    """Solve the adjustable straights' lengths so the chain ends where it began."""
    n = sum(1 for it in spec if it[0] == "S" and it[1] is None)
    base = np.full(n, 100.0)
    _, e0, _ = _chain(spec, start, h0, base)
    J = []
    for i in range(n):
        b = base.copy()
        b[i] += 1.0
        _, e1, _ = _chain(spec, start, h0, b)
        J.append(e1 - e0)
    J = np.array(J).T
    sol = base + np.linalg.lstsq(J, np.array(start) - e0, rcond=None)[0]
    prims, e, h = _chain(spec, start, h0, sol)
    assert np.linalg.norm(e - np.array(start)) < 1e-6, e
    assert abs((h - h0) % (2 * math.pi)) < 1e-9 or abs((h - h0) % (2 * math.pi) - 2 * math.pi) < 1e-9
    assert (sol > 20).all(), sol
    s = 0.0
    for pr in prims:
        pr.s0 = s
        s += pr.length
    return prims, s


PRIMS, LAP = _closed(TRACK, START)
# label every primitive with its section name: corners keep their label; straights take "<prev>-<next>"
for i, pr in enumerate(PRIMS):
    if not pr.label:
        prev = next(PRIMS[j].label for j in range(i - 1, -len(PRIMS), -1) if PRIMS[j].kind == "C")
        nxt = next(PRIMS[(i + j) % len(PRIMS)].label for j in range(1, len(PRIMS)) if PRIMS[(i + j) % len(PRIMS)].kind == "C")
        pr.label = f"{prev}-{nxt}"
SECTION = [pr.label for pr in PRIMS]


def prim_of(label):
    return next(i for i, pr in enumerate(PRIMS) if pr.label == label)


def corner_range(label):
    pr = PRIMS[prim_of(label)]
    return pr.s0, pr.s0 + pr.length


def sample(ds=1.0, prims=None):
    """Dense centre line: dict of s, x, y, heading, curvature, prim index."""
    prims = prims or PRIMS
    out = {k: [] for k in ("s", "x", "y", "h", "k", "i")}
    for i, pr in enumerate(prims):
        n = max(2, int(math.ceil(pr.length / ds)))
        t = np.linspace(0, pr.length, n, endpoint=False)
        p, h, k = pr.at(t)
        out["s"].append(pr.s0 + t)
        out["x"].append(p[:, 0])
        out["y"].append(p[:, 1])
        out["h"].append(h)
        out["k"].append(k)
        out["i"].append(np.full(n, i))
    return {k: np.concatenate(v) for k, v in out.items()}


def frame(s, offset=0.0):
    """Point on the lap at distance s (wraps), `offset` metres to the left. Returns (x, y, heading radians)."""
    s = float(s) % LAP
    i = max(j for j, pr in enumerate(PRIMS) if pr.s0 <= s + 1e-9)
    pr = PRIMS[i]
    p, h, _ = pr.at(np.array([s - pr.s0]))
    p, h = p[0], float(h[0])
    return p[0] - offset * math.sin(h), p[1] + offset * math.cos(h), h


def nearest(x, y, prims=None):
    """For arrays of points: lap distance s, lateral offset (+ left), distance to the centre line, prim index."""
    prims = prims or PRIMS
    x, y = np.asarray(x, float), np.asarray(y, float)
    best = np.full(x.shape, np.inf)
    S = np.zeros(x.shape)
    LAT = np.zeros(x.shape)
    I = np.zeros(x.shape, int)
    for i, pr in enumerate(prims):
        t, lat, dist, _ = pr.nearest(x, y)
        m = dist < best
        best = np.where(m, dist, best)
        S = np.where(m, pr.s0 + t, S)
        LAT = np.where(m, lat, LAT)
        I = np.where(m, i, I)
    return S, LAT, best, I


# ---------------------------------------------------------------- widths and run-off along the lap
def _profile(points, ds=1.0):
    """Smooth periodic profile over s from (s, value) keys, linear blend."""
    pts = sorted(points)
    s = np.arange(0, LAP, ds)
    xs = np.array([p[0] for p in pts])
    vs = np.array([p[1] for p in pts])
    xs = np.concatenate([xs - LAP, xs, xs + LAP])
    vs = np.concatenate([vs, vs, vs])
    return s, np.interp(s, xs, vs)


def _width_keys():
    keys = []
    for pr in PRIMS:
        w = WIDTH_AT.get(pr.label, WIDTH)
        keys += [(pr.s0 + min(25, pr.length * 0.3), w), (pr.s0 + pr.length - min(25, pr.length * 0.3), w)]
    return keys


_WS, _WV = _profile(_width_keys())


def width(s):
    return np.interp(np.mod(s, LAP), _WS, _WV)


def corner_side(label):
    """+1 if the corner turns left (inside = left), -1 if right."""
    return int(PRIMS[prim_of(label)].sgn)


def runoff(s, side):
    """Run-off beyond the track edge at lap distance s on `side` (+1 left, -1 right): (kind index, width).
    kind: 0 grass, 1 gravel, 2 asphalt."""
    s = np.mod(np.asarray(s, float), LAP)
    kind = np.zeros(s.shape, int)
    wid = np.full(s.shape, VERGE)
    for lab, c in CORNERS.items():
        a, b = corner_range(lab)
        cs = corner_side(lab)
        if side == -cs:   # outside of this corner
            k, w = c["out"]
            ki = {"grass": 0, "gravel": 1, "asphalt": 2}[k]
            # the trap starts at mid-entry and runs well past the exit (cars run wide on exit)
            L = b - a
            a0, b0 = a - 0.4 * L - 25, b + 0.6 * L + 35
            blend = 30.0
            for off in (-LAP, 0, LAP):
                ss = s - off
                inside = (ss > a0) & (ss < b0)
                fade = np.clip(np.minimum(ss - a0, b0 - ss) / blend, 0, 1)
                ww = VERGE + (w - VERGE) * fade
                upd = inside & (ww > wid)
                kind = np.where(inside & (fade > 0.25), ki, kind)
                wid = np.where(upd, ww, wid)
        else:
            w = c["inside"]
            for off in (-LAP, 0, LAP):
                ss = s - off
                inside = (ss > a - 15) & (ss < b + 15)
                wid = np.where(inside, np.minimum(wid, w), wid)
    return kind, wid


def kerb_zones():
    """List of (label, side, s0, s1): inside kerb along the apex, outside kerb on the exit (and entry for chicanes)."""
    out = []
    for lab, c in CORNERS.items():
        a, b = corner_range(lab)
        cs = corner_side(lab)
        L = b - a
        out.append((lab, cs, a - 0.1 * L - 4, b + 0.1 * L + 4))           # inside, apex
        out.append((lab, -cs, a + 0.45 * L, b + min(40, 0.4 * L + 12)))   # outside, exit
        if L < 40 or c.get("sausage"):
            out.append((lab, -cs, a - 18, a + 0.2 * L))                    # outside, entry
    return out


# ---------------------------------------------------------------- zones
def s_at_x_main(x):
    """Lap distance of a point x on the main straight (y = 0)."""
    return x - START[0]


SF_S = s_at_x_main(SF_X)
BACK = prim_of("back straight")


def drs_zones():
    """(detection s, activation s, end s) for the main straight and the back straight."""
    main = (corner_range("T14")[1] + 40, SF_S + 120, corner_range("T1")[0] - 120)
    b = PRIMS[BACK]
    back = (corner_range("T9")[0] - 30, b.s0 + 80, b.s0 + b.length - 120)
    return [main, back]


def braking_boards():
    """[(corner, s of the 100/200/300 m boards, side)] before each heavy-braking corner."""
    out = []
    for lab, c in CORNERS.items():
        if c.get("boards"):
            a, _ = corner_range(lab)
            out.append((lab, [(d, a - d) for d in (300, 200, 100)], -corner_side(lab)))
    return out


def grid():
    """Grid slots behind the start line: [(pos, x, y, heading)], pole on the left (the inside of T1 is right,
    so pole is on the... racing line side: left of the track here, as at most tracks the pole side is set by T1)."""
    out = []
    w = WIDTH_AT["main straight"]
    for n in range(GRID_SLOTS):
        x = SF_X - 8.0 - n * GRID_PITCH
        y = (-1 if n % 2 == 0 else 1) * w * 0.22   # pole on the right: the inside of T1
        out.append((n + 1, x, y, 0.0))
    return out


# ---------------------------------------------------------------- pit lane centre line (its own primitive chain)
def _pit_prims():
    # entry: leave the track's right edge 150 m before T15, ease right with an S, then run round the inside of T15
    # on an arc concentric with it (radius R15 - |PIT_Y|), which lands the lane exactly on y = PIT_Y heading east.
    t15 = PRIMS[prim_of("T15")]
    R = t15.radius - abs(PIT_Y)
    xs = t15.c[0] - R                       # x of the lane centre when it starts the concentric arc
    a0, _ = corner_range("T15")
    S_LEN = 150.0
    ex, ey, eh = frame(a0 - S_LEN, -(WIDTH / 2 - 3.5))
    dx = xs - ex                            # lateral shift to the right (east), heading north
    Rs = 170.0
    a = math.degrees(math.acos(1 - dx / (2 * Rs)))
    prims, p, h = [], np.array([ex, ey]), math.pi / 2
    for ang in (-a, a):
        pr = Prim("C", p, h, radius=Rs, angle=ang, label="pit entry")
        prims.append(pr)
        p, h = pr.end()
    gap = t15.c[1] - p[1]                   # straight up to the arc start
    if gap > 0.01:
        pr = Prim("S", p, h, length=gap, label="pit entry")
        prims.append(pr)
        p, h = pr.end()
    pr = Prim("C", p, h, radius=R, angle=-90.0, label="pit entry")
    prims.append(pr)
    p, h = pr.end()
    h = 0.0
    # straight east until x = PIT_X[1] with a lateral dog-leg to PIT_Y if needed
    dy = PIT_Y - p[1]
    assert abs(h) < 1e-9
    # join with a gentle S: two arcs of radius R and angle a with lateral offset dy
    R = 120.0
    a = math.degrees(math.acos(1 - abs(dy) / (2 * R))) if abs(dy) > 1e-6 else 0.0
    sg = 1 if dy > 0 else -1
    if a > 0:
        for ang in (sg * a, -sg * a):
            pr = Prim("C", p, h, radius=R, angle=ang, label="pit entry")
            prims.append(pr)
            p, h = pr.end()
    pr = Prim("S", p, 0.0, length=PIT_X[1] - p[0], label="pit lane")
    prims.append(pr)
    p, h = pr.end()
    # exit: a long gentle left blend that meets the track's right edge before T1's braking zone
    R = 400.0
    target = -WIDTH_AT["main straight"] / 2 + 3.0
    dy = target - p[1]
    a = math.degrees(math.acos(1 - abs(dy) / (2 * R)))
    for ang in (a, -a):
        pr = Prim("C", p, h, radius=R, angle=ang, label="pit exit")
        prims.append(pr)
        p, h = pr.end()
    s = 0.0
    for pr in prims:
        pr.s0 = s
        s += pr.length
    return prims, s


PIT, PIT_LEN = _pit_prims()
PIT_ENTRY_S = corner_range("T15")[0] - 150     # lap distance where the pit entry leaves the track
PIT_EXIT_X = PIT[-1].end()[0][0]               # main-straight x where the exit lane meets the track


def pit_width(t):
    """Pit lane road width along its own length: narrow single lane at entry/exit, full width along the garages."""
    full = [pr for pr in PIT if pr.label == "pit lane"][0]
    a, b = full.s0, full.s0 + full.length
    return np.interp(t, [0, a - 60, a, b, b + 80, PIT_LEN], [7, 7, PIT_W, PIT_W, 7, 6])


def garages():
    """[(team index, x0, x1)] garage bays along the pit straight (x0 < x1), team 0 nearest the pit exit."""
    return [(i, GARAGE_X0 + i * GARAGE_W, GARAGE_X0 + (i + 1) * GARAGE_W) for i in range(GARAGE_N)]


if __name__ == "__main__":
    print(f"lap {LAP:.1f} m, {len(PRIMS)} primitives")
    for pr in PRIMS:
        print(f"  {pr.label:18s} {pr.kind} s0={pr.s0:7.1f} L={pr.length:6.1f}" + (f" R={pr.radius:.0f}" if pr.kind == "C" else ""))
    print("pit lane", round(PIT_LEN, 1), "exit x", round(PIT_EXIT_X, 1))
    print("drs", [tuple(round(v) for v in z) for z in drs_zones()])
