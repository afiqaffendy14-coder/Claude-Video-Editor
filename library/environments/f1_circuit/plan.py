"""The venue plan: where every building, stand, road, car park and prop group sits. Pure python/numpy.

Coordinates are metres in the circuit frame (see layout.py). Placement helpers work in lap terms
(`along(s, offset)`) so things stay attached to the track if the layout changes.
Every footprint is an oriented rectangle (cx, cy, w along its local x, d along local y, yaw) so overlap checks are exact.
"""
import math
import numpy as np
import layout as L

# ---------------------------------------------------------------- teams (no real names or logos)
TEAMS = [  # key, display name, main colour, accent
    ("silver_arrow", "SILVER ARROW", "#C9CDD2", "#00A19B"),
    ("rosso", "ROSSO", "#C8102E", "#F2D000"),
    ("papaya", "PAPAYA", "#FF8000", "#1E73BE"),
    ("midnight", "MIDNIGHT", "#1B2A4A", "#E10600"),
    ("verde", "VERDE", "#0E5C3B", "#D6E04A"),
    ("azure", "AZURE", "#2E8FD8", "#F5F5F5"),
    ("volt", "VOLT", "#F2D33A", "#202124"),
    ("viola", "VIOLA", "#5B2C83", "#F28AC0"),
    ("bronzo", "BRONZO", "#8A5A2B", "#F0E2C0"),
    ("neve", "NEVE", "#ECEDEF", "#D11F3C"),
]

SPONSORS = [  # invented brands for boards, banners and LED panels: (text, background, text colour)
    ("NOVA FUEL", "#0A3D91", "#FFD200"), ("KRONOS", "#111111", "#F2F2F2"), ("BLOCK COLA", "#C8102E", "#FFFFFF"),
    ("ORBIT AIR", "#FFFFFF", "#1C4E9C"), ("PIXEL TYRES", "#F2C200", "#111111"), ("VOLTA", "#00843D", "#FFFFFF"),
    ("SUMMIT BANK", "#222A3A", "#7FD1FF"), ("TERRA", "#E85D04", "#FFFFFF"), ("ZEPHYR", "#6A1B9A", "#FFFFFF"),
    ("APEX", "#F5F5F5", "#D00000"), ("CUBE TEL", "#00B4D8", "#0B132B"), ("RAPIDO", "#FFE600", "#D00000"),
]


def along(s, offset=0.0):
    """(x, y, heading) on the lap."""
    return L.frame(s, offset)


def rect(cx, cy, w, d, yaw=0.0):
    return dict(cx=cx, cy=cy, w=w, d=d, yaw=yaw)


def corners(r):
    c, s = math.cos(r["yaw"]), math.sin(r["yaw"])
    pts = []
    for u, v in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        x, y = u * r["w"] / 2, v * r["d"] / 2
        pts.append((r["cx"] + c * x - s * y, r["cy"] + s * x + c * y))
    return pts


def facing(px, py, tx, ty):
    """Yaw so that a structure's local +Y (its front) points from (px, py) toward (tx, ty)."""
    return math.atan2(ty - py, tx - px) - math.pi / 2


# ---------------------------------------------------------------- pit complex
PIT_BUILDING = dict(x0=L.GARAGE_X0 - 34.0, x1=L.GARAGE_X0 + L.GARAGE_N * L.GARAGE_W + 34.0,
                    y_front=L.GARAGE_Y, depth=26.0)
# ends of the pit building: media centre (west), race control tower (east)
MEDIA = rect(L.GARAGE_X0 - 17.0, L.GARAGE_Y - 13.0, 34.0, 26.0)
RACE_CONTROL = rect(L.GARAGE_X0 + L.GARAGE_N * L.GARAGE_W + 17.0, L.GARAGE_Y - 13.0, 34.0, 26.0)

PADDOCK = dict(x0=PIT_BUILDING["x0"], x1=PIT_BUILDING["x1"], y0=L.GARAGE_Y - 26.0 - 70.0, y1=L.GARAGE_Y - 26.0)


def motorhomes():
    """Team hospitality units facing the back of the garages across the paddock street."""
    out = []
    y = PADDOCK["y1"] - 22.0 - 8.0
    for i in range(len(TEAMS)):
        x = L.GARAGE_X0 + (i + 0.5) * L.GARAGE_W
        out.append((i, rect(x, y, 18.0, 14.0, 0.0)))
    return out


def transporters():
    """Two team trucks per team parked behind the motorhomes."""
    out = []
    y = PADDOCK["y0"] + 10.0
    for i in range(len(TEAMS)):
        for j in range(2):
            x = L.GARAGE_X0 + (i + 0.25 + 0.5 * j) * L.GARAGE_W
            out.append((i, rect(x, y, 3.2, 16.5, 0.0)))
    return out


MEDICAL = rect(150.0, -112.0, 34.0, 22.0)
HELIPAD = (205.0, -112.0)
FIRE_STATION = rect(150.0, -150.0, 26.0, 18.0)
SAFETY_CAR_BAY = rect(165.0, -28.5, 40.0, 13.0)   # apron off the pit exit lane


# ---------------------------------------------------------------- spectator stands (rows of 10 m sections)
def stand_along(s, offset, n, side, rows, roof, name, colour):
    """A straight stand of n 10 m sections, centred at lap distance s, `offset` m from the centre line on `side`
    (+1 left / -1 right), facing the track."""
    x, y, h = L.frame(s, side * offset)
    # local +Y (front) points to the track: the track is on the -side of this point
    yaw = h + (math.pi if side > 0 else 0.0)
    depth = rows * 0.8 + 4.0
    # move the centre back so the front edge sits at `offset`
    nx, ny = -math.sin(h) * side, math.cos(h) * side
    cx, cy = x + nx * depth / 2, y + ny * depth / 2
    return dict(name=name, rect=rect(cx, cy, n * 10.0, depth, yaw), n=n, rows=rows, roof=roof, colour=colour)


def stand_at(cx, cy, tx, ty, n, rows, roof, name, colour):
    """A stand whose front-centre faces the point (tx, ty)."""
    yaw = facing(cx, cy, tx, ty)
    depth = rows * 0.8 + 4.0
    c, s_ = math.cos(yaw), math.sin(yaw)
    bx, by = -(-s_) * depth / 2, -(c) * depth / 2     # back along -Y
    return dict(name=name, rect=rect(cx + bx, cy + by, n * 10.0, depth, yaw), n=n, rows=rows, roof=roof, colour=colour)


def _corner_mid(lab):
    a, b = L.corner_range(lab)
    return (a + b) / 2


def stands():
    out = [
        stand_along(L.s_at_x_main(-60), 23.0, 26, 1, 26, "cantilever", "main_grandstand", "#1F4E9C"),
        stand_along(L.s_at_x_main(330), 23.0, 10, 1, 18, "cantilever", "straight_stand", "#C8102E"),
    ]
    # corner stands face the apex from behind the run-off
    for lab, n, rows, roof, col, dist in (("T1", 7, 20, "flat", "#00843D", 30), ("T4", 6, 16, "none", "#E85D04", 30),
                                          ("T10", 7, 18, "flat", "#6A1B9A", 28), ("T13", 6, 16, "none", "#00A19B", 22),
                                          ("T15", 5, 14, "none", "#F2C200", 28)):
        a, b = L.corner_range(lab)
        cs = L.corner_side(lab)
        sm = (a + b) / 2
        rw = L.CORNERS[lab]["out"][1]
        x, y, h = L.frame(sm, -cs * (L.width(sm) / 2 + rw + dist))
        ax, ay, _ = L.frame(sm, cs * 2.0)
        out.append(stand_at(x, y, ax, ay, n, rows, roof, f"stand_{lab}", col))
    b = L.PRIMS[L.BACK]
    out.append(stand_along(b.s0 + b.length * 0.62, 24.0, 12, 1, 14, "flat", "back_straight_stand", "#0A3D91"))
    return out


def screens():
    """Giant screens: (name, rect, facing point) one in view of each big stand."""
    out = []
    for st in stands():
        r = st["rect"]
        # across the track from the stand, 60 m in front of its centre
        c, s_ = math.cos(r["yaw"]), math.sin(r["yaw"])
        fx, fy = -s_, c   # front direction
        dist = 70.0 if st["name"] != "main_grandstand" else 0.0
        if st["name"] == "main_grandstand":
            continue
        x, y = r["cx"] + fx * (r["d"] / 2 + dist), r["cy"] + fy * (r["d"] / 2 + dist)
        out.append((f"screen_{st['name']}", x, y, r["cx"], r["cy"]))
    return out


# ---------------------------------------------------------------- outside the track
ENTRANCE = dict(gate=(-60.0, 118.0), plaza=rect(-60.0, 100.0, 160.0, 46.0))
CAR_PARKS = [rect(-300.0, 190.0, 260.0, 110.0), rect(60.0, 200.0, 280.0, 120.0), rect(420.0, 170.0, 200.0, 110.0),
             rect(250.0, -330.0, 260.0, 120.0)]
HOSPITALITY_VIP = rect(722.0, -70.0, 50.0, 24.0, math.radians(90))        # terrace building beyond T1, facing west
LAKE = (300.0, -560.0, 150.0, 85.0)                                       # infield lake ellipse (cx, cy, rx, ry)
FAN_ZONE = rect(-160.0, -420.0, 120.0, 70.0)                              # infield fan zone with stage
BRIDGES = [  # spectator bridges: (name, s on the lap, span either side of the centre line)
    ("bridge_main", L.s_at_x_main(420.0), 24.0),
    ("bridge_back", L.PRIMS[L.BACK].s0 + 300.0, 26.0),
]
TOWN = dict(x0=-1100.0, x1=900.0, y0=480.0, y1=820.0)
HOTEL = rect(860.0, 210.0, 40.0, 30.0, math.radians(15))


def marshal_posts(spacing=260.0):
    """Marshal posts round the lap on the outside of the loop (left), numbered from the start line."""
    out = []
    s = 60.0
    n = 1
    while s < L.LAP - 40:
        out.append((n, s))
        s += spacing
        n += 1
    return out


if __name__ == "__main__":
    print(len(stands()), "stands")
    for st in stands():
        r = st["rect"]
        print(f"  {st['name']:22s} c=({r['cx']:.0f},{r['cy']:.0f}) {r['w']:.0f}x{r['d']:.0f} yaw={math.degrees(r['yaw']):.0f}")
    print(len(marshal_posts()), "marshal posts")
