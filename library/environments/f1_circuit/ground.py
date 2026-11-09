"""The ground as blocks: a 1 m raster of surface types and heights for the whole world, with 0.25 m sub-blocks
along the track and pit lane for kerbs and paint. Plus the barrier lines. Pure numpy, no Blender.

Every surface is a flat block top; nothing is laid on top of anything else (paint and kerbs are their own
sub-blocks), so there is no z-fighting. Heights change only in whole steps (gravel and water sit lower, the hills
outside the venue rise in 1 m terraces), and every step gets a side face.
"""
import math
import numpy as np
import layout as L
import plan as P

# ---------------------------------------------------------------- surface types
GRASS, GRASS2, TRACK, RUNOFF, GRAVEL, PIT, ROAD, CONCRETE, PAVING, PARKING, WATER, SAND, DIRT, HILL = range(1, 15)
WHITE, YELLOW, KERB_R, KERB_W, GREEN, BLUE, BLACK, RED = range(20, 28)
TEAM0 = 30   # 30..39 pit box paint in team colours
NAMES = {GRASS: "grass", GRASS2: "grass_mown", TRACK: "asphalt", RUNOFF: "runoff", GRAVEL: "gravel", PIT: "pit_asphalt",
         ROAD: "road", CONCRETE: "concrete", PAVING: "paving", PARKING: "parking", WATER: "lakebed", SAND: "sand",
         DIRT: "dirt", HILL: "hill_grass", WHITE: "paint_white", YELLOW: "paint_yellow", KERB_R: "kerb_red",
         KERB_W: "kerb_white", GREEN: "paint_green", BLUE: "paint_blue", BLACK: "paint_black", RED: "paint_red"}
for _i, _t in enumerate(P.TEAMS):
    NAMES[TEAM0 + _i] = "paint_team_" + _t[0]
HEIGHT = {GRAVEL: -0.08, WATER: -0.9, SAND: -0.04}   # everything else tops out at z = 0 (hills set their own)

# ---------------------------------------------------------------- world grid
RES = 1.0
SUB = 4                                   # 0.25 m sub-blocks for paint and kerbs
_sm = L.sample(2.0)
TB = (_sm["x"].min(), _sm["x"].max(), _sm["y"].min(), _sm["y"].max())
VENUE = (math.floor(TB[0] - 230), math.ceil(TB[1] + 230), math.floor(TB[2] - 230), math.ceil(TB[3] + 330))
HILLS = 520                               # hill ring width beyond the venue
X0, Y0 = VENUE[0] - HILLS, VENUE[2] - HILLS
NX, NY = int(VENUE[1] + HILLS - X0), int(VENUE[3] + HILLS - Y0)


def cell_xy(ix, iy):
    return X0 + (ix + 0.5) * RES, Y0 + (iy + 0.5) * RES


def ij(x, y):
    return np.floor((np.asarray(x) - X0) / RES).astype(int), np.floor((np.asarray(y) - Y0) / RES).astype(int)


# ---------------------------------------------------------------- smooth noise (plane waves; deterministic)
def noise(x, y, seed, wl, n=6):
    rng = np.random.default_rng(seed)
    out = np.zeros(np.broadcast(x, y).shape)
    for _ in range(n):
        a = rng.uniform(0, 2 * math.pi)
        k = 2 * math.pi / (wl * rng.uniform(0.7, 1.3))
        out += np.sin(k * (np.cos(a) * x + np.sin(a) * y) + rng.uniform(0, 6.3))
    return out / math.sqrt(n / 2)


# ---------------------------------------------------------------- rasterisers
def raster_rect(T, r, value, pad=0.0):
    """Paint an oriented rectangle into a world raster."""
    pts = np.array(P.corners(dict(r, w=r["w"] + 2 * pad, d=r["d"] + 2 * pad)))
    i0, j0 = ij(pts[:, 0].min(), pts[:, 1].min())
    i1, j1 = ij(pts[:, 0].max(), pts[:, 1].max())
    i0, j0, i1, j1 = max(i0, 0), max(j0, 0), min(i1 + 1, NX), min(j1 + 1, NY)
    xs, ys = cell_xy(np.arange(i0, i1), np.arange(j0, j1))
    Xg, Yg = np.meshgrid(xs, ys)
    c, s = math.cos(r["yaw"]), math.sin(r["yaw"])
    u = (Xg - r["cx"]) * c + (Yg - r["cy"]) * s
    v = -(Xg - r["cx"]) * s + (Yg - r["cy"]) * c
    m = (np.abs(u) <= r["w"] / 2 + pad) & (np.abs(v) <= r["d"] / 2 + pad)
    T[j0:j1, i0:i1][m] = value
    return m


def raster_polyline(T, pts, width, value, where=None):
    pts = np.asarray(pts, float)
    hw = width / 2
    for a, b in zip(pts[:-1], pts[1:]):
        lo, hi = np.minimum(a, b) - hw - 1, np.maximum(a, b) + hw + 1
        i0, j0 = ij(*lo)
        i1, j1 = ij(*hi)
        i0, j0, i1, j1 = max(i0, 0), max(j0, 0), min(i1 + 1, NX), min(j1 + 1, NY)
        if i1 <= i0 or j1 <= j0:
            continue
        xs, ys = cell_xy(np.arange(i0, i1), np.arange(j0, j1))
        Xg, Yg = np.meshgrid(xs, ys)
        ab = b - a
        t = np.clip(((Xg - a[0]) * ab[0] + (Yg - a[1]) * ab[1]) / max(ab @ ab, 1e-9), 0, 1)
        d = np.hypot(Xg - a[0] - t * ab[0], Yg - a[1] - t * ab[1])
        m = d <= hw
        if where is not None:
            m &= where(T[j0:j1, i0:i1])
        T[j0:j1, i0:i1][m] = value


# ---------------------------------------------------------------- fields over the venue
def fields(x, y):
    S, LAT, D, I = L.nearest(x, y)
    PS, PLAT, PD, PI = L.nearest(x, y, L.PIT)
    return dict(S=S, LAT=LAT, D=D, I=I, PS=PS, PLAT=PLAT, PD=PD)


# ---------------------------------------------------------------- barriers
def barrier_offsets(F, ds=1.0, reach=140):
    """For each side, the barrier's offset from the centre line along the lap, clamped so it never crosses into
    another part of the track's ground (back-to-back walls 5 m apart where two legs run close) or onto the pit
    lane. Returns s, {side: (offset, blocked_by_pit)}."""
    s = np.arange(0, L.LAP, ds)
    out = {}
    D, PD, PS = F["grid_D"], F["grid_PD"], F["grid_PS"]
    for side in (1, -1):
        kind, wid = L.runoff(s, side)
        edge = L.width(s) / 2
        want = edge + wid + 1.5
        cx, cy, h = np.array([L.frame(v) for v in s]).T
        nx, ny = -np.sin(h) * side, np.cos(h) * side
        gap = np.full(s.shape, float(reach))
        pit = np.zeros(s.shape, bool)
        for k in range(1, reach):
            dist = edge + k
            px, py = cx + nx * dist, cy + ny * dist
            ii, jj = ij(px, py)
            ii = np.clip(ii - F["vi0"], 0, D.shape[1] - 1)
            jj = np.clip(jj - F["vj0"], 0, D.shape[0] - 1)
            d2 = D[jj, ii]
            pd = PD[jj, ii] - L.pit_width(PS[jj, ii]) / 2
            hit_other = (d2 < dist - 1.5) & (gap == reach)
            gap = np.where(hit_other, k, gap)
            hit_pit = (pd < 2.0) & (gap == reach) & (k + edge < want + 3)
            pit |= hit_pit
            gap = np.where(hit_pit, k, gap)
        off = np.minimum(want, edge + gap - 2.5)
        # smooth: a running minimum then a moving average, so the line never jogs
        n = 9
        pad = np.concatenate([off[-n:], off, off[:n]])
        rm = np.min(np.lib.stride_tricks.sliding_window_view(pad, 2 * n + 1), axis=1)
        k = 15
        pad = np.concatenate([rm[-k:], rm, rm[:k]])
        sm = np.convolve(pad, np.ones(2 * k + 1) / (2 * k + 1), mode="valid")
        off = np.minimum(sm, off)
        # the pit: the right side is open from the pit entry to the pit exit (the pit wall takes over)
        if side == -1:
            ent = L.PIT_ENTRY_S - 2.0
            ext = L.s_at_x_main(L.PIT_EXIT_X + 60.0)
            pit |= (s > ent) | (s < ext)
        out[side] = (off, pit)
    return s, out


def pit_wall_line(ds=1.0):
    """The pit wall runs midway between the track's right edge and the pit lane wherever there is room."""
    t = np.arange(0, L.PIT_LEN, ds)
    pts, keep = [], []
    for v in t:
        i = max(j for j, pr in enumerate(L.PIT) if pr.s0 <= v + 1e-9)
        pr = L.PIT[i]
        p, h, _ = pr.at(np.array([v - pr.s0]))
        p, h = p[0], float(h[0])
        n = np.array([-math.sin(h), math.cos(h)])          # left of the pit lane = toward the track
        lw = L.pit_width(v) / 2
        S, LAT, D, _ = L.nearest(np.array([p[0]]), np.array([p[1]]))
        gap = D[0] - L.width(S[0]) / 2 - lw
        off = lw + gap / 2
        pts.append(p + n * off)
        keep.append(gap > 3.0)
    return t, np.array(pts), np.array(keep)


def polyline_from(s, off, side, ds=1.0):
    pts = []
    for v, o in zip(s, off):
        x, y, _ = L.frame(v, side * o)
        pts.append((x, y))
    return np.array(pts)


# ---------------------------------------------------------------- the build
def build(verbose=True):
    T = np.full((NY, NX), GRASS, np.uint8)
    H = np.zeros((NY, NX), np.float32)
    vi0, vj0 = ij(VENUE[0], VENUE[2])
    vi1, vj1 = ij(VENUE[1], VENUE[3])
    xs, ys = cell_xy(np.arange(vi0, vi1), np.arange(vj0, vj1))
    Xv, Yv = np.meshgrid(xs, ys)
    F = fields(Xv.ravel(), Yv.ravel())
    F = {k: v.reshape(Xv.shape) for k, v in F.items()}
    F.update(grid_D=F["D"], grid_PD=F["PD"], grid_PS=F["PS"], vi0=vi0, vj0=vj0)
    if verbose:
        print("fields", Xv.shape)

    # ---- hills outside the venue: 1 m terraces rising with distance from the venue edge
    Xa, Ya = np.meshgrid(*cell_xy(np.arange(NX), np.arange(NY)))
    dx = np.maximum(np.maximum(VENUE[0] - Xa, Xa - VENUE[1]), 0)
    dy = np.maximum(np.maximum(VENUE[2] - Ya, Ya - VENUE[3]), 0)
    dout = np.hypot(dx, dy)
    town = (Xa > P.TOWN["x0"] - 40) & (Xa < P.TOWN["x1"] + 40) & (Ya > VENUE[3] - 10)
    rise = np.clip((dout - 60) / 260, 0, 1) ** 1.4
    hh = rise * (30 + 20 * noise(Xa, Ya, 3, 380) + 6 * noise(Xa, Ya, 4, 120))
    hh = np.where(town, np.clip((dout - 420) / 200, 0, 1) * hh, hh)
    H[:] = np.floor(np.clip(hh, 0, None)).astype(np.float32)
    T[H > 0] = HILL
    # mown grass stripes inside the venue
    stripe = ((np.floor(Xa / 8) + np.floor(Ya / 8)) % 2 == 0)
    inv = dout == 0
    T[inv & stripe] = GRASS2

    # ---- venue: town ground, roads, car parks, plazas, building pads (drawn before the track so the track wins)
    TV = T[vj0:vj1, vi0:vi1]
    for r in P.CAR_PARKS:
        raster_rect(T, r, PARKING)
    raster_rect(T, P.ENTRANCE["plaza"], PAVING)
    raster_rect(T, P.FAN_ZONE, PAVING)
    pb = P.PIT_BUILDING
    raster_rect(T, P.rect((pb["x0"] + pb["x1"]) / 2, pb["y_front"] - pb["depth"] / 2, pb["x1"] - pb["x0"], pb["depth"]), CONCRETE)
    pd = P.PADDOCK
    raster_rect(T, P.rect((pd["x0"] + pd["x1"]) / 2, (pd["y0"] + pd["y1"]) / 2, pd["x1"] - pd["x0"], pd["y1"] - pd["y0"]), CONCRETE)
    for r in (P.MEDICAL, P.FIRE_STATION, P.HOSPITALITY_VIP, P.HOTEL):
        raster_rect(T, r, CONCRETE, pad=3.0)
    raster_rect(T, P.rect(P.HELIPAD[0], P.HELIPAD[1], 26, 26), CONCRETE)
    for st in P.stands():
        raster_rect(T, st["rect"], CONCRETE, pad=2.0)
    # the lake
    cx, cy, rx, ry = P.LAKE
    e = ((Xa - cx) / rx) ** 2 + ((Ya - cy) / ry) ** 2
    T[(e < 1.25) & (e >= 1.0)] = SAND
    T[e < 1.0] = WATER

    # ---- the track and its run-off, from the fields
    S, LAT, D = F["S"], F["LAT"], F["D"]
    w2 = L.width(S) / 2
    a = D - w2
    s_b, bo = barrier_offsets(F)
    off_l, off_r = bo[1][0], bo[-1][0]
    bar = np.where(LAT > 0, np.interp(S, s_b, off_l), np.interp(S, s_b, off_r)) - w2
    kind = np.zeros(S.shape, int)
    wid = np.zeros(S.shape)
    for side in (1, -1):
        k, wd = L.runoff(S, side)
        m = np.sign(LAT) == side
        kind = np.where(m, k, kind)
        wid = np.where(m, wd, wid)
    wid = np.minimum(wid, bar - 3.0)          # 3 m of grass before the barrier (tyre walls stand there)
    inside_bar = a < bar
    V = TV
    m = inside_bar & (a >= 0)
    V[m & ~np.isin(V, (WATER, SAND))] = GRASS
    V[m & (a < 1.5)] = RUNOFF                                   # asphalt shoulder all round
    V[m & (kind == 2) & (a < wid)] = RUNOFF
    V[m & (kind == 1) & (a >= 4.5) & (a < wid)] = GRAVEL
    V[m & (kind == 1) & (a < 4.5)] = RUNOFF
    V[a < 0] = TRACK
    # the pit lane and its aprons
    PD_, PS_ = F["PD"], F["PS"]
    pw = L.pit_width(PS_) / 2
    V[(PD_ < pw) & (a >= 0)] = PIT
    sc = P.SAFETY_CAR_BAY
    raster_rect(T, sc, PIT)
    # concrete between the track and the pit lane along the pit straight (pit wall and team stands stand here)
    ys = (np.abs(Yv - (L.PIT_WALL_Y - 1.5)) < 4.0) & (Xv > L.PIT_X[0] + 10) & (Xv < L.PIT_X[1] + 20) & (a >= 1.5) & ~((PD_ < pw))
    V[ys] = CONCRETE
    # ---- service roads: outside the barrier on the left (outside of the loop), and the paddock street
    rl = polyline_from(s_b, off_l + 6.5, 1)
    raster_polyline(T, rl[::4], 5.0, ROAD, where=lambda t: np.isin(t, (GRASS, GRASS2, PARKING)))
    raster_polyline(T, [(pd["x0"] - 40, pd["y1"] - 6), (pd["x1"] + 60, pd["y1"] - 6)], 9.0, ROAD,
                    where=lambda t: t != PIT)
    raster_polyline(T, [(pd["x1"] + 60, pd["y1"] - 6), (pd["x1"] + 60, P.MEDICAL["cy"]), (P.MEDICAL["cx"] - 30, P.MEDICAL["cy"]),
                        (P.MEDICAL["cx"] - 30, P.FIRE_STATION["cy"] - 20), (300, P.FIRE_STATION["cy"] - 20),
                        (300, -280)], 7.0, ROAD, where=lambda t: np.isin(t, (GRASS, GRASS2)))
    # town streets
    tw = P.TOWN
    for gx in np.arange(tw["x0"], tw["x1"], 120.0):
        raster_polyline(T, [(gx, tw["y0"]), (gx, tw["y1"])], 8.0, ROAD, where=lambda t: t != HILL)
    for gy in np.arange(tw["y0"], tw["y1"], 110.0):
        raster_polyline(T, [(tw["x0"], gy), (tw["x1"], gy)], 8.0, ROAD, where=lambda t: t != HILL)
    raster_polyline(T, [(P.ENTRANCE["gate"][0], P.ENTRANCE["gate"][1] + 20), (P.ENTRANCE["gate"][0], tw["y0"])],
                    12.0, ROAD, where=lambda t: t != HILL)

    for code, h in HEIGHT.items():
        H[(T == code) & (H == 0)] = h

    # ---- fine sub-blocks: kerbs and paint along the track and pit lane
    band = (a < 3.75) | (PD_ < pw + 1.0) | (V == PARKING)
    assert not np.isin(V[band], (GRAVEL, WATER, SAND, HILL)).any()
    fj, fi = np.nonzero(band)
    fi_w, fj_w = fi + vi0, fj + vj0
    sub = (np.arange(SUB) + 0.5) / SUB * RES
    cx_, cy_ = cell_xy(fi_w, fj_w)
    bx = (cx_ - 0.5 * RES)[:, None, None] + sub[None, None, :]
    by = (cy_ - 0.5 * RES)[:, None, None] + sub[None, :, None]
    bx, by = np.broadcast_to(bx, (len(fi), SUB, SUB)), np.broadcast_to(by, (len(fi), SUB, SUB))
    FS = fields(bx.ravel(), by.ravel())
    FS = {k: v.reshape(bx.shape) for k, v in FS.items()}
    base = np.broadcast_to(V[fj, fi][:, None, None], bx.shape).copy()
    sub_t = paint(base, bx, by, FS)
    if verbose:
        print("fine cells", len(fi))
    return dict(T=T, H=H, fine_i=fi_w, fine_j=fj_w, fine=sub_t, F=F, s_b=s_b, bo=bo)


def paint(base, X, Y, F):
    """Sub-block surface types: kerbs, white lines, start/finish, grid, DRS lines, pit lane markings."""
    t = base.copy()
    S, LAT, D = F["S"], F["LAT"], F["D"]
    w2 = L.width(S) / 2
    a = D - w2
    PS, PLAT, PD = F["PS"], F["PLAT"], F["PD"]
    pw = L.pit_width(PS) / 2
    pitm = PD < pw
    trk = a < 0
    # re-derive the base inside each 1 m block at 0.25 m so the track edge itself is smooth-stepped
    edge_zone = (a >= -1.0) & (a < 1.0) & ~np.isin(t, (PIT,))
    t[edge_zone & trk] = TRACK
    t[edge_zone & ~trk & (t == TRACK)] = RUNOFF
    t[pitm & ~trk] = PIT
    # car park bay lines: rows of 5 m bays (2.5 m wide) either side of 6 m aisles
    park = base == PARKING
    yy = np.mod(Y, 16.0)
    inbay = (yy < 5.0) | (yy >= 11.0)
    t[park & inbay & (np.mod(X, 2.5) < 0.25)] = WHITE
    # kerbs: 1 m red/white stripes along the lap, KERB_W wide outside the white line
    stripe = (np.floor(np.mod(S, L.LAP) / L.STRIPE) % 2).astype(int)
    for lab, side, s0, s1 in L.kerb_zones():
        for off in (-L.LAP, 0, L.LAP):
            ss = S - off
            m = (ss > s0) & (ss < s1) & (np.sign(LAT) == side) & (a >= 0) & (a < L.KERB_W) & ~pitm
            t[m] = np.where(stripe[m] == 0, KERB_R, KERB_W)
            # a 2 m green strip beyond outside kerbs
            g = (ss > s0) & (ss < s1) & (np.sign(LAT) == side) & (a >= L.KERB_W) & (a < L.KERB_W + 2.0) & ~pitm
            if side == -L.corner_side(lab):
                t[g & np.isin(t, (RUNOFF,))] = GREEN
    # track-limit white lines: 0.25 m just inside the edge, everywhere except across the pit entry/exit mouths
    wl = trk & (a >= -0.25)
    mouth = (PD < pw + 0.6)
    t[wl & ~mouth] = WHITE
    # start / finish: a 1 m chequered band across the track, and a solid white line just behind it
    on_main = (S < 980.0) & trk
    xm = X
    sf = on_main & (np.abs(xm - L.SF_X) < 0.5)
    chk = ((np.floor((xm - L.SF_X + 0.5) / 0.5) + np.floor(Y / 0.5)) % 2 == 0)
    t[sf] = np.where(chk[sf], WHITE, BLACK)
    t[on_main & (xm >= L.SF_X - 1.0) & (xm < L.SF_X - 0.75)] = WHITE
    # grid slots: a transverse line in front of each car and two short side ticks, staggered
    for pos, gx, gy, _ in L.grid():
        half = 2.6
        m = on_main & (np.abs(Y - gy) < half) & (xm >= gx + 2.6) & (xm < gx + 2.85)
        t[m] = WHITE
        for sy in (-1, 1):
            m = on_main & (np.abs(Y - (gy + sy * half)) < 0.125) & (xm >= gx - 1.0) & (xm < gx + 2.85)
            t[m] = WHITE
    # DRS detection and activation lines (detection: single line; activation: double line)
    for det, act, end in L.drs_zones():
        for sv, n in ((det, 1), (act, 2)):
            for k in range(n):
                ss = np.mod(S - (sv + k * 0.75), L.LAP)
                m = trk & ((ss < 0.25))
                t[m] = WHITE
    # pit lane: dividing line between fast lane and working lane, the speed-limit lines, box outlines
    full = [pr for pr in L.PIT if pr.label == "pit lane"][0]
    along = (PS > full.s0) & (PS < full.s0 + full.length) & pitm
    t[along & (np.abs(PLAT - (-1.25)) < 0.125)] = WHITE        # fast lane (track side) | working lane (garage side)
    # pit entry line: solid white along the lane's left edge where it leaves the track; exit blend line likewise
    lane_edge = (np.abs(PLAT - pw) < 0.25) | (np.abs(PLAT - (pw - 0.25)) < 0.125)
    ends = (PS < full.s0 - 40) | (PS > full.s0 + full.length + 10)
    t[lane_edge & ends & (a > -3) & (PD < pw + 0.3)] = WHITE
    for xl in L.PIT_LIMIT:
        m = pitm & (np.abs(X - xl) < 0.25) & (np.abs(Y - L.PIT_Y) < L.PIT_W / 2)
        t[m] = WHITE
        m = pitm & (np.abs(X - xl - 1.0) < 0.25) & (np.abs(Y - L.PIT_Y) < L.PIT_W / 2)
        t[m] = WHITE
    # pit boxes: one per team, outlined in the team colour on the working lane in front of each garage
    for i, x0, x1 in L.garages():
        cx = (x0 + x1) / 2
        bx0, bx1 = cx - 4.0, cx + 4.0
        by0, by1 = L.GARAGE_Y + 0.3, L.PIT_Y - 1.25 - 0.3
        inb = pitm & (X >= bx0) & (X < bx1) & (Y >= by0) & (Y < by1)
        rim = inb & ((X < bx0 + 0.25) | (X >= bx1 - 0.25) | (Y < by0 + 0.25) | (Y >= by1 - 0.25))
        t[rim] = TEAM0 + i
        # wheel position marks
        for wx in (cx - 1.8, cx + 1.8):
            for wy in (by0 + 1.2, by1 - 1.2):
                t[pitm & (np.abs(X - wx) < 0.25) & (np.abs(Y - wy) < 0.25)] = TEAM0 + i
    return t


if __name__ == "__main__":
    import time, sys
    t0 = time.time()
    R = build()
    print(f"world {NX}x{NY} at {RES} m, venue {VENUE}, {time.time() - t0:.1f}s")
    if len(sys.argv) > 1:
        from PIL import Image
        pal = {GRASS: (86, 150, 60), GRASS2: (78, 140, 54), TRACK: (45, 45, 48), RUNOFF: (90, 92, 98), GRAVEL: (205, 185, 140),
               PIT: (60, 60, 64), ROAD: (70, 70, 72), CONCRETE: (170, 170, 165), PAVING: (180, 150, 120),
               PARKING: (95, 95, 95), WATER: (40, 90, 150), SAND: (220, 200, 150), DIRT: (120, 90, 60), HILL: (70, 130, 50)}
        T = R["T"]
        img = np.zeros(T.shape + (3,), np.uint8)
        for k, c in pal.items():
            img[T == k] = c
        sh = (R["H"] * 4).clip(0, 120).astype(np.uint8)
        img = np.clip(img.astype(int) + sh[..., None] // 3, 0, 255).astype(np.uint8)
        # fine: take the dominant sub type of kerbs/paint
        fine = R["fine"]
        pal2 = {KERB_R: (220, 30, 30), KERB_W: (240, 240, 240), WHITE: (250, 250, 250), GREEN: (40, 170, 70),
                BLACK: (0, 0, 0), RED: (200, 0, 0), BLUE: (30, 80, 200), YELLOW: (240, 200, 0)}
        for k, c in pal2.items():
            m = (fine == k).any(axis=(1, 2))
            img[R["fine_j"][m], R["fine_i"][m]] = c
        for i in range(10):
            m = (fine == TEAM0 + i).any(axis=(1, 2))
            img[R["fine_j"][m], R["fine_i"][m]] = (255, 0, 255)
        # barrier lines
        for side, col in ((1, (255, 255, 0)), (-1, (0, 255, 255))):
            off, pit = R["bo"][side]
            pts = polyline_from(R["s_b"], off, side)
            ii, jj = ij(pts[:, 0], pts[:, 1])
            img[jj[~pit], ii[~pit]] = col
        Image.fromarray(img[::-1]).save(sys.argv[1])
        crop = img[::-1]
        vi0, vj0 = ij(-480, 60)
        vi1, vj1 = ij(-300, -120)
        Image.fromarray(img[vj1:vj0, vi0:vi1][::-1]).resize(((vi1 - vi0) * 4, (vj0 - vj1) * 4), Image.NEAREST).save(sys.argv[1].replace(".png", "_pitentry.png"))
        vi0, vj0 = ij(-60, 10)
        vi1, vj1 = ij(60, -60)
        Image.fromarray(img[vj1:vj0, vi0:vi1][::-1]).resize(((vi1 - vi0) * 6, (vj0 - vj1) * 6), Image.NEAREST).save(sys.argv[1].replace(".png", "_grid.png"))
