"""Ground meshes from the site raster: merged block tops (greedy rectangles) plus side faces wherever the height
steps. Split into reusable, separately adjustable objects:

  track_<section>   asphalt, white lines, run-off strip and paint of one straight or corner
  kerbs_<section>   the red/white kerbs of that section
  pit_lane          pit lane road, lines and the team boxes
  ground_<i>_<j>    everything else in 256 m tiles (grass, gravel, roads, car parks, plazas, hills)
  lake_water        the lake surface
"""
import math
import numpy as np
import bpy
import layout as L
import ground as S
import blocks as B

TILE = 256

STYLE = {  # surface type -> material args (colour, pattern, roughness)
    S.GRASS: ("#5E9E3F", "grass", 0.95), S.GRASS2: ("#54933A", "grass", 0.95), S.TRACK: ("#3A3B3F", "asphalt", 0.8),
    S.RUNOFF: ("#4C4F57", "asphalt", 0.82), S.GRAVEL: ("#C9B48A", "gravel", 1.0), S.PIT: ("#45464B", "asphalt", 0.7),
    S.ROAD: ("#505154", "asphalt", 0.85), S.CONCRETE: ("#A9A9A3", "concrete", 0.85), S.PAVING: ("#B49A80", "tile", 0.85),
    S.PARKING: ("#5A5B5E", "asphalt", 0.85), S.WATER: ("#6B5A3E", "gravel", 1.0), S.SAND: ("#D8C79A", "gravel", 1.0),
    S.DIRT: ("#7A5A3A", "gravel", 1.0), S.HILL: ("#5A9A3A", "grass", 0.95),
    S.WHITE: ("#EDEDE8", "flat", 0.6), S.YELLOW: ("#F2C200", "flat", 0.6), S.KERB_R: ("#C8241E", "flat", 0.55),
    S.KERB_W: ("#EDEDE8", "flat", 0.55), S.GREEN: ("#2E8B4A", "noise", 0.7), S.BLUE: ("#1F5FB0", "noise", 0.7),
    S.BLACK: ("#16171A", "flat", 0.6), S.RED: ("#B3171C", "flat", 0.6),
}


def surf_mat(t):
    if t >= S.TEAM0:
        import plan as P
        key, _, col, _ = P.TEAMS[t - S.TEAM0]
        return B.material("paint_team_" + key, col, "flat", 0.6)
    col, kind, rough = STYLE[t]
    return B.material(S.NAMES[t], col, kind, rough)


def side_mat(t):
    if t == S.HILL or t == S.GRASS or t == S.GRASS2:
        return B.material("hill_side", "#5A9A3A", "dirtside", 0.95, col2="#7A5636")
    if t == S.GRAVEL:
        return B.material("gravel_side", "#9C8A68", "gravel", 1.0)
    return B.material("earth_side", "#7A5636", "gravel", 1.0)


# ---------------------------------------------------------------- greedy rectangles
def rects(K):
    """Merge equal keys (>= 0) of a 2D int array into rectangles: list of (r0, r1, c0, c1, key)."""
    rows, cols = K.shape
    out, open_ = [], {}
    for r in range(rows):
        row = K[r]
        d = np.flatnonzero(row[1:] != row[:-1]) + 1
        st = np.concatenate([[0], d])
        en = np.concatenate([d, [cols]])
        cur = {}
        for s_, e_, k in zip(st.tolist(), en.tolist(), row[st].tolist()):
            if k < 0:
                continue
            cur[(s_, e_, k)] = open_.pop((s_, e_, k), r)
        for (s_, e_, k), r0 in open_.items():
            out.append((r0, r, s_, e_, k))
        open_ = cur
    for (s_, e_, k), r0 in open_.items():
        out.append((r0, rows, s_, e_, k))
    return out


class Groups:
    """Quads collected per output object."""
    def __init__(self):
        self.g = {}

    def add(self, name, quad, mat, uv=None):
        self.g.setdefault(name, B.MeshBuilder()).quad(quad, mat, uv)

    def top(self, name, x0, y0, x1, y1, z, mat):
        self.add(name, [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], mat)

    def build(self, coll_for):
        obs = {}
        for name, mb in sorted(self.g.items()):
            obs[name] = mb.build(name, coll_for(name))
        return obs


def build(R, coll_for):
    T, H = R["T"], R["H"]
    G = Groups()
    fine_mask = np.zeros(T.shape, bool)
    fine_mask[R["fine_j"], R["fine_i"]] = True

    # ---- coarse tops (1 m blocks), everything that is not a fine cell
    hkey = np.where(T == S.HILL, np.clip(H, 0, 250).astype(np.int64), 0)
    K = T.astype(np.int64) * 256 + hkey
    K[fine_mask] = -1
    for tj in range(0, S.NY, TILE):
        for ti in range(0, S.NX, TILE):
            sub = K[tj:tj + TILE, ti:ti + TILE]
            if (sub < 0).all():
                continue
            name = f"ground_{ti // TILE:02d}_{tj // TILE:02d}"
            for r0, r1, c0, c1, k in rects(sub):
                t, hz = k // 256, k % 256
                z = float(hz) if t == S.HILL else S.HEIGHT.get(t, 0.0)
                x0, y0 = S.X0 + (ti + c0) * S.RES, S.Y0 + (tj + r0) * S.RES
                x1, y1 = S.X0 + (ti + c1) * S.RES, S.Y0 + (tj + r1) * S.RES
                G.top(name, x0, y0, x1, y1, z, surf_mat(t))

    # ---- side faces where the coarse height steps (x and y neighbours), merged along the edge
    Hc = H.astype(np.float64)
    for axis in (0, 1):
        a, b = (Hc[:, :-1], Hc[:, 1:]) if axis == 1 else (Hc[:-1, :], Hc[1:, :])
        ta, tb = (T[:, :-1], T[:, 1:]) if axis == 1 else (T[:-1, :], T[1:, :])
        diff = a != b
        js, is_ = np.nonzero(diff)
        if not len(js):
            continue
        lo, hi = np.minimum(a[js, is_], b[js, is_]), np.maximum(a[js, is_], b[js, is_])
        upper_t = np.where(a[js, is_] > b[js, is_], ta[js, is_], tb[js, is_])
        a_high = a[js, is_] > b[js, is_]
        # merge consecutive edges along the edge direction with identical (lo, hi, type, facing)
        if axis == 1:      # edges between columns i and i+1, running along y (rows j)
            order = np.lexsort((js, is_, a_high, upper_t, hi, lo))
        else:
            order = np.lexsort((is_, js, a_high, upper_t, hi, lo))
        js, is_, lo, hi, upper_t, a_high = js[order], is_[order], lo[order], hi[order], upper_t[order], a_high[order]
        run_start = 0
        n = len(js)
        along = js if axis == 1 else is_
        across = is_ if axis == 1 else js
        for k in range(1, n + 1):
            brk = (k == n or along[k] != along[k - 1] + 1 or across[k] != across[k - 1] or lo[k] != lo[k - 1]
                   or hi[k] != hi[k - 1] or upper_t[k] != upper_t[k - 1] or a_high[k] != a_high[k - 1])
            if not brk:
                continue
            k0 = run_start
            run_start = k
            j0, i0 = js[k0], is_[k0]
            if axis == 1:
                x = S.X0 + (i0 + 1) * S.RES
                ya, yb = S.Y0 + along[k0] * S.RES, S.Y0 + (along[k - 1] + 1) * S.RES
                # face toward the lower side: if a (left) is high, face +x
                if a_high[k0]:
                    q = [(x, yb, lo[k0]), (x, ya, lo[k0]), (x, ya, hi[k0]), (x, yb, hi[k0])]
                    q = [(x, ya, lo[k0]), (x, yb, lo[k0]), (x, yb, hi[k0]), (x, ya, hi[k0])]
                else:
                    q = [(x, yb, lo[k0]), (x, ya, lo[k0]), (x, ya, hi[k0]), (x, yb, hi[k0])]
                ti_, tj_ = i0, j0
            else:
                y = S.Y0 + (j0 + 1) * S.RES
                xa, xb = S.X0 + along[k0] * S.RES, S.X0 + (along[k - 1] + 1) * S.RES
                if a_high[k0]:   # lower cell is +y: face +y
                    q = [(xb, y, lo[k0]), (xa, y, lo[k0]), (xa, y, hi[k0]), (xb, y, hi[k0])]
                else:
                    q = [(xa, y, lo[k0]), (xb, y, lo[k0]), (xb, y, hi[k0]), (xa, y, hi[k0])]
                ti_, tj_ = i0, j0
            name = f"ground_{ti_ // TILE:02d}_{tj_ // TILE:02d}"
            G.add(name, q, side_mat(int(upper_t[k0])))

    # ---- fine tops (0.25 m sub-blocks) along the track and the pit lane, grouped by section
    F = R["F"]
    fi, fj, fine = R["fine_i"], R["fine_j"], R["fine"]
    li, lj = fi - F["vi0"], fj - F["vj0"]
    sec = F["I"][lj, li]
    base = T[fj, fi]
    names = []
    gid = {}

    def gname(n):
        if n not in gid:
            gid[n] = len(names)
            names.append(n)
        return gid[n]

    sec_names = [p.label.replace(" ", "_").replace("-", "_") for p in L.PRIMS]
    pit_ids = gname("pit_lane")
    is_pit = np.isin(fine, (S.PIT,)) | ((fine >= S.TEAM0) & (fine < S.TEAM0 + 10))
    pit_cell = (base == S.PIT) | is_pit.any(axis=(1, 2))
    kerb = np.isin(fine, (S.KERB_R, S.KERB_W))
    grp = np.zeros(fine.shape, np.int64)
    for k in range(len(fi)):
        if pit_cell[k]:
            grp[k] = pit_ids
        elif base[k] == S.PARKING:
            grp[k] = gname("car_parks")
        else:
            grp[k] = gname("track_" + sec_names[sec[k]])
    kgrp = {g: gname("kerbs_" + names[g][6:]) for g in set(grp.ravel().tolist()) if names[g].startswith("track_")}
    grp_full = grp.copy()
    for g, kg in kgrp.items():
        grp_full[(grp == g) & kerb] = kg
    # pit-lane paint that falls in a track cell stays with the track (and vice versa): fine
    key = fine.astype(np.int64) * 1024 + grp_full
    # assemble horizontal strips of the venue at 0.25 m and merge
    SUB = S.SUB
    jmin, jmax = fj.min(), fj.max() + 1
    imin, imax = fi.min(), fi.max() + 1
    W = (imax - imin) * SUB
    STRIP = 64
    for js in range(jmin, jmax, STRIP):
        je = min(js + STRIP, jmax)
        sel = (fj >= js) & (fj < je)
        if not sel.any():
            continue
        Kf = np.full(((je - js) * SUB, W), -1, np.int64)
        for k in np.flatnonzero(sel):
            r, c = (fj[k] - js) * SUB, (fi[k] - imin) * SUB
            Kf[r:r + SUB, c:c + SUB] = key[k]
        for r0, r1, c0, c1, k in rects(Kf):
            t, g = k // 1024, k % 1024
            x0 = S.X0 + imin * S.RES + c0 * S.RES / SUB
            x1 = S.X0 + imin * S.RES + c1 * S.RES / SUB
            y0 = S.Y0 + js * S.RES + r0 * S.RES / SUB
            y1 = S.Y0 + js * S.RES + r1 * S.RES / SUB
            G.top(names[g], x0, y0, x1, y1, 0.0, surf_mat(int(t)))

    # ---- the lake surface
    wm = (T == S.WATER).astype(np.int64) - 1 + (T == S.WATER)
    wm = np.where(T == S.WATER, 1, -1)
    water = B.material("water", "#2F6E9E", "water", 0.05, spec=0.6)
    for r0, r1, c0, c1, k in rects(wm):
        G.top("lake_water", S.X0 + c0, S.Y0 + r0, S.X0 + c1, S.Y0 + r1, -0.3, water)
    return G.build(coll_for)
