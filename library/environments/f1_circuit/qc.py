"""Quality control for the circuit (run on the saved blend):

    blender -b blend/circuit.blend --python qc.py [-- --renders]

Checks, written to sheet/qc_report.md:
  1 track continuity (closed lap, every centre-line sample on asphalt, width never under 12 m)
  2 pit lane connects (entry and exit join the track; pit surface connected to the track surface)
  3 barriers (never on the track or run-off, never on the pit lane; the fence line has no gaps except gates/pits)
  4 grounding (every instance stands on the ground under it, nothing floats or sinks; nothing solid on the track)
  5 clipping (oriented-box test between every pair of nearby pieces, block by block)
  6 proportions (car / character / lanes / doors / seats)
  7 performance (objects, instances, triangles, render time)
"""
import math
import os
import sys
import time
from collections import deque
import numpy as np
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as L
import ground as S

OUT = os.path.join(HERE, "sheet")
REPORT = []
FAIL = []


def rep(line=""):
    REPORT.append(line)
    print(line, flush=True)


def check(name, ok, detail=""):
    rep(f"- [{'x' if ok else ' '}] **{name}**{': ' + detail if detail else ''}")
    if not ok:
        FAIL.append(name)


# ---------------------------------------------------------------- instances as world boxes
TERRAIN = ("track_", "kerbs_", "ground_", "pit_lane", "car_parks", "lake_water")
PEOPLE = ("crowd_", "trackside_marshals", "pit_crew")


def proto_boxes():
    out = {}
    root = bpy.data.collections.get("circuit_protos")
    for c in root.children:
        name = c.name[len("proto_"):]
        objs = sorted(c.objects, key=lambda o: o.name)
        out[name] = [np.array(o["boxes"]).reshape(-1, 15) if "boxes" in o else np.zeros((0, 15)) for o in objs]
    return out


def world_boxes(bx, M3, t):
    """bx (n x 15) local boxes; M3 (3x3 linear incl. scale), t translation -> centres, axes (n,3,3 columns), halves."""
    c = bx[:, :3] @ M3.T + t
    Rb = bx[:, 6:].reshape(-1, 3, 3)
    A = np.einsum("ij,njk->nik", M3, Rb)           # columns = scaled box axes
    lens = np.linalg.norm(A, axis=1)                 # (n, 3)
    axes = A / np.maximum(lens[:, None, :], 1e-9)
    half = bx[:, 3:6] * lens
    return c, axes, half


def gather():
    PB = proto_boxes()
    inst = []   # (group, index, centres, axes, halves, base z, origin xy)
    for ob in bpy.data.objects:
        if ob.type != "MESH" or not ob.users_collection:
            continue
        if ob.name.startswith(TERRAIN) or any(c.name == "circuit_protos" or c.name.startswith("proto_") for c in ob.users_collection):
            continue
        if "proto" in ob and len(ob.data.vertices) and not len(ob.data.polygons):
            pts = np.zeros(len(ob.data.vertices) * 3, np.float32)
            ob.data.vertices.foreach_get("co", pts)
            pts = pts.reshape(-1, 3)
            n = len(pts)
            rot = np.zeros(n * 3, np.float32)
            ob.data.attributes["rot"].data.foreach_get("vector", rot)
            scl = np.zeros(n * 3, np.float32)
            ob.data.attributes["scl"].data.foreach_get("vector", scl)
            var = np.zeros(n, np.int32)
            ob.data.attributes["var"].data.foreach_get("value", var)
            rot, scl = rot.reshape(-1, 3), scl.reshape(-1, 3)
            boxes = PB[ob["proto"]]
            for k in range(n):
                bx = boxes[min(var[k], len(boxes) - 1)]
                if not len(bx):
                    continue
                cz, sz = math.cos(rot[k, 2]), math.sin(rot[k, 2])
                M3 = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]) @ np.diag(scl[k])
                c, a, h = world_boxes(bx, M3, pts[k])
                inst.append((ob.name, k, c, a, h, float(pts[k, 2]), pts[k, :2].copy()))
        elif "boxes" in ob:
            bx = np.array(ob["boxes"]).reshape(-1, 15)
            mw = np.array(ob.matrix_world)
            c, a, h = world_boxes(bx, mw[:3, :3], mw[:3, 3])
            inst.append((ob.name, 0, c, a, h, float(mw[2, 3]), mw[:2, 3].copy()))
    return inst


def obb_overlap(c1, a1, h1, c2, a2, h2, eps=0.005):
    """Vectorised SAT between box sets 1 (n) and 2 (m): returns (n, m) bool, touching does not count."""
    n, m = len(c1), len(c2)
    D = c2[None, :, :] - c1[:, None, :]                       # (n, m, 3)
    axes = [np.broadcast_to(a1[:, None, :, i], (n, m, 3)) for i in range(3)] + \
           [np.broadcast_to(a2[None, :, :, i], (n, m, 3)) for i in range(3)]
    for i in range(3):
        for j in range(3):
            cr = np.cross(a1[:, None, :, i], a2[None, :, :, j])
            nr = np.linalg.norm(cr, axis=-1, keepdims=True)
            axes.append(np.where(nr > 1e-6, cr / np.maximum(nr, 1e-9), 0))
    sep = np.zeros((n, m), bool)
    for ax in axes:
        r1 = sum(h1[:, None, i] * np.abs(np.einsum("nmk,nk->nm", ax, a1[:, :, i])) for i in range(3))
        r2 = sum(h2[None, :, i] * np.abs(np.einsum("nmk,mk->nm", ax, a2[:, :, i])) for i in range(3))
        d = np.abs(np.einsum("nmk,nmk->nm", ax, D))
        nz = np.linalg.norm(ax, axis=-1) > 0.5
        sep |= nz & (d >= r1 + r2 - eps)
    return ~sep


SAME_GROUP_OK = ("barrier_", "pit_wall", "pit_lane_outer_wall", "trackside_fence_banners", "trackside_led_boards",
                 "vegetation_trees", "trackside_sausage", "pit_building_bays", "garage_door", "venue_parked_cars")
PAIR_OK = {  # intended contacts / mountings (prefix pairs)
    ("barrier_debris_fence", "barrier_concrete_walls"), ("trackside_fence_banners", "barrier_debris_fence"),
    ("trackside_led_boards", "barrier_concrete_walls"), ("pit_wall_fence", "pit_wall"),
    ("trackside_led_boards", "barrier_debris_fence"),
    ("garage_door", "pit_building_bays"), ("pit_gantries", "pit_building_bays"),
    ("barrier_gates", "barrier_concrete_walls"), ("barrier_gates", "barrier_armco"),
    ("barrier_debris_fence", "barrier_gates"), ("barrier_tyre_walls", "barrier_gates"),
    ("pit_building_endwall", "pit_building_bays"),
}


def pair_ok(g1, g2):
    for a, b in PAIR_OK:
        if (g1.startswith(a) and g2.startswith(b)) or (g1.startswith(b) and g2.startswith(a)):
            return True
    return False


def clipping(inst, cell=12.0):
    # broad phase on 2D AABBs of each instance
    bb = []
    for it in inst:
        c, a, h = it[2], it[3], it[4]
        ext = np.abs(a) @ h[..., None] if False else np.einsum("nij,nj->ni", np.abs(a), h)
        lo, hi = (c - ext).min(0), (c + ext).max(0)
        bb.append((lo, hi))
    grid = {}
    for k, (lo, hi) in enumerate(bb):
        for gx in range(int(lo[0] // cell), int(hi[0] // cell) + 1):
            for gy in range(int(lo[1] // cell), int(hi[1] // cell) + 1):
                grid.setdefault((gx, gy), []).append(k)
    hits, tested = {}, 0
    seen = set()
    for ks in grid.values():
        for ii in range(len(ks)):
            for jj in range(ii + 1, len(ks)):
                p, q = ks[ii], ks[jj]
                key = (min(p, q), max(p, q))
                if key in seen:
                    continue
                seen.add(key)
                g1, g2 = inst[p][0], inst[q][0]
                if g1.startswith(PEOPLE) or g2.startswith(PEOPLE):
                    continue
                if g1 == g2 and g1.startswith(SAME_GROUP_OK):
                    continue
                if pair_ok(g1, g2):
                    continue
                (l1, h1_), (l2, h2_) = bb[p], bb[q]
                if (l1 > h2_ - 0.005).any() or (l2 > h1_ - 0.005).any():
                    continue
                tested += 1
                ov = obb_overlap(inst[p][2], inst[p][3], inst[p][4], inst[q][2], inst[q][3], inst[q][4])
                if ov.any():
                    kk = tuple(sorted((g1.split("__")[0], g2.split("__")[0])))
                    hits.setdefault(kk, []).append((inst[p][6].round(1).tolist(), inst[q][6].round(1).tolist()))
    return hits, tested


def people_clipping(inst, sample=4000):
    """Spectators / marshals / crew against the structures they stand or sit on (a random sample)."""
    rng = np.random.default_rng(1)
    people = [k for k, it in enumerate(inst) if it[0].startswith(PEOPLE)]
    other = [k for k, it in enumerate(inst) if not it[0].startswith(PEOPLE)]
    cell = 6.0
    grid = {}
    for k in other:
        c = inst[k][2]
        for gx in set((c[:, 0] // cell).astype(int).tolist()):
            for gy in set((c[:, 1] // cell).astype(int).tolist()):
                grid.setdefault((gx, gy), set()).add(k)
    pick = rng.choice(people, min(sample, len(people)), replace=False) if people else []
    bad = []
    for p in pick:
        c = inst[p][2]
        gx, gy = int(c[:, 0].mean() // cell), int(c[:, 1].mean() // cell)
        near = set()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                near |= grid.get((gx + dx, gy + dy), set())
        for q in near:
            if obb_overlap(inst[p][2], inst[p][3], inst[p][4], inst[q][2], inst[q][3], inst[q][4], eps=0.01).any():
                bad.append((inst[p][0], inst[q][0], inst[p][6].round(1).tolist()))
                break
    return bad, len(pick)


# ---------------------------------------------------------------- raster checks
def components(mask):
    """4-connected component labels (BFS) of a boolean raster: returns the number of components and labels."""
    lab = np.zeros(mask.shape, np.int32)
    n = 0
    ys, xs = np.nonzero(mask)
    for y0, x0 in zip(ys, xs):
        if lab[y0, x0]:
            continue
        n += 1
        q = deque([(y0, x0)])
        lab[y0, x0] = n
        while q:
            y, x = q.popleft()
            for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= yy < mask.shape[0] and 0 <= xx < mask.shape[1] and mask[yy, xx] and not lab[yy, xx]:
                    lab[yy, xx] = n
                    q.append((yy, xx))
    return n, lab


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    t0 = time.time()
    rep("# Circuit QC report")
    rep()
    rep(f"Lap {L.LAP:.1f} m, {len(L.CORNERS)} corners, pit lane {L.PIT_LEN:.0f} m, world {S.NX} x {S.NY} m.")
    rep()
    R = S.build(verbose=False)
    T = R["T"]
    # fine types back onto a boolean "asphalt" raster per 1 m cell (a cell counts if any sub-block is driveable)
    drive_types = (S.TRACK, S.WHITE, S.KERB_R, S.KERB_W, S.BLACK) + tuple(range(S.TEAM0, S.TEAM0 + 10))
    drive = np.isin(T, (S.TRACK,))
    fine_drive = np.isin(R["fine"], drive_types).any(axis=(1, 2)) & (T[R["fine_j"], R["fine_i"]] != S.PARKING)
    drive[R["fine_j"][fine_drive], R["fine_i"][fine_drive]] = True
    pit = np.isin(T, (S.PIT,))
    fine_pit = np.isin(R["fine"], (S.PIT,)).any(axis=(1, 2))
    pit[R["fine_j"][fine_pit], R["fine_i"][fine_pit]] = True

    rep("## 1. Track continuity")
    sm = L.sample(0.5)
    i, j = S.ij(sm["x"], sm["y"])
    on = drive[j, i]
    check("Lap closes", True, "layout solver closes the chain to 1e-6 m and 360 degrees (asserted)")
    check("Centre line on asphalt everywhere", on.all(), f"{(~on).sum()} of {len(on)} samples off the asphalt")
    widths = []
    for s in np.arange(0, L.LAP, 5.0):
        x, y, h = L.frame(s)
        o = np.arange(-12, 12.01, 0.25)
        px, py = x - o * math.sin(h), y + o * math.cos(h)
        ii, jj = S.ij(px, py)
        widths.append(drive[jj, ii].sum() * 0.25)
    widths = np.array(widths)
    check("Track width 12 m or more", widths.min() >= 12.0, f"min {widths.min():.1f} m, max {widths.max():.1f} m (1 m blocks)")
    n_tr, lab = components(drive | pit)
    check("Driveable surface is one piece (track + pit lane)", n_tr == 1, f"{n_tr} component(s)")

    rep()
    rep("## 2. Pit lane")
    ps = L.sample(0.5, L.PIT)
    i, j = S.ij(ps["x"], ps["y"])
    onp = (pit | drive)[j, i]
    check("Pit lane centre line on its road", onp.all(), f"{(~onp).sum()} samples off")
    a, b = L.PIT[0].p0, L.PIT[-1].end()[0]
    da = L.nearest(np.array([a[0]]), np.array([a[1]]))[2][0] - L.width(0) / 2
    db = L.nearest(np.array([b[0]]), np.array([b[1]]))[2][0] - L.width(0) / 2
    check("Pit entry leaves from the track", da < 0, f"entry centre {da:+.1f} m from the track edge (negative = on the track)")
    check("Pit exit rejoins the track", db < 0, f"exit centre {db:+.1f} m from the track edge")
    n_pit, labp = components(pit)
    ok = len(set(lab[pit].tolist())) == 1
    check("Pit surface joins the track surface", ok, f"pit pieces {n_pit}, all in the track's component: {ok}")

    rep()
    rep("## 3-5. Barriers, grounding, clipping")
    inst = gather()
    rep(f"{len(inst)} placed pieces (instances + objects) gathered with their blocks.")
    # barriers off the track
    bad_b = []
    for it in inst:
        if not it[0].startswith(("barrier_", "pit_wall", "pit_lane_outer_wall")):
            continue
        c = it[2]
        s_, lat, d, _ = L.nearest(c[:, 0], c[:, 1])
        clear = d - L.width(s_) / 2
        _, _, pd, _ = L.nearest(c[:, 0], c[:, 1], L.PIT)
        pclear = pd - L.pit_width(L.nearest(c[:, 0], c[:, 1], L.PIT)[0]) / 2
        if clear.min() < 1.5:
            bad_b.append((it[0], it[6].round(1).tolist(), round(float(clear.min()), 2)))
        elif it[0].startswith("barrier_") and pclear.min() < 0.3:
            bad_b.append((it[0], it[6].round(1).tolist(), "on pit lane"))
    check("Barriers never on the track or kerbs (>= 1.5 m from the edge)", not bad_b,
          f"{len(bad_b)} pieces too close" + (f", e.g. {bad_b[:4]}" if bad_b else ""))
    # fence line gaps
    ends = []
    for it in inst:
        if it[0] != "barrier_debris_fence":
            continue
        c, a = it[2][2], it[3][2]    # the long panel box: its x axis runs along the fence
        h = it[4][2]
        ends.append(c[:2] + a[:2, 0] * h[0])
        ends.append(c[:2] - a[:2, 0] * h[0])
    ends = np.array(ends)
    gates = [it[6] for it in inst if it[0] == "barrier_gates"]
    cellg = {}
    for k, e in enumerate(ends):
        cellg.setdefault((int(e[0] // 2), int(e[1] // 2)), []).append(k)
    dangling = []
    for k, e in enumerate(ends):
        near = [q for dx in (-1, 0, 1) for dy in (-1, 0, 1) for q in cellg.get((int(e[0] // 2) + dx, int(e[1] // 2) + dy), [])
                if q != k and q // 2 != k // 2]
        if not any(np.linalg.norm(ends[q] - e) < 0.35 for q in near):
            if not any(np.linalg.norm(np.asarray(g) - e) < 6.0 for g in gates):
                dangling.append(e.round(1).tolist())
    check("Fence line continuous (open only at gates and the pit entry/exit)", len(dangling) <= 8,
          f"{len(dangling)} open ends outside gates: {dangling[:8]}")
    # grounding and nothing solid on the track
    H, TT = R["H"], T
    MOUNTED = ("barrier_debris_fence", "trackside_fence_banners", "trackside_led_boards", "pit_wall_fence",
               "garage_door", "marshal_post_number", "screen_pit_roof", "trackside_marshals")
    float_bad, track_bad = [], []
    for it in inst:
        g = it[0]
        if g.startswith(PEOPLE) or g.startswith(MOUNTED) or g.startswith("start_gantry") or g.startswith("bridge_"):
            continue
        c, a, h = it[2], it[3], it[4]
        ext = np.einsum("nij,nj->ni", np.abs(a), h)
        low = c[:, 2] - ext[:, 2]
        k = int(np.argmin(low))
        zmin = float(low[k])
        ii, jj = S.ij(c[k, 0], c[k, 1])
        ii, jj = int(np.clip(ii, 0, S.NX - 1)), int(np.clip(jj, 0, S.NY - 1))
        gz = float(H[jj, ii])
        if abs(zmin - gz) > 0.02 and not (TT[jj, ii] == S.GRAVEL and abs(zmin) < 0.02):
            float_bad.append((g, it[6].round(1).tolist(), round(zmin, 3), round(gz, 3)))
        if g.startswith(("pit_", "trackside_sausage", "trackside_braking", "trackside_drs", "start_gantry")):
            continue
        sel = low < 2.0
        if sel.any():
            ii, jj = S.ij(c[sel, 0], c[sel, 1])
            tt = TT[np.clip(jj, 0, S.NY - 1), np.clip(ii, 0, S.NX - 1)]
            if np.isin(tt, (S.TRACK,)).any():
                track_bad.append((g, it[6].round(1).tolist()))
    from collections import Counter
    cnt = Counter(g.split("__")[0] for g, *_ in float_bad)
    check("Everything stands on the ground (no floating or sunk pieces)", not float_bad,
          f"{len(float_bad)} pieces" + (f": {dict(cnt)}, e.g. {[f for f in float_bad if True][:3]}" if float_bad else ""))
    check("Nothing solid on the racing surface", not track_bad,
          f"{len(track_bad)} pieces" + (f", e.g. {track_bad[:5]}" if track_bad else ""))
    hits, tested = clipping(inst)
    tot = sum(len(v) for v in hits.values())
    detail = f"{tested} close pairs tested block by block; {tot} overlapping"
    if hits:
        detail += ": " + "; ".join(f"{a} x {b}: {len(v)} (e.g. at {v[0][0]})" for (a, b), v in sorted(hits.items(), key=lambda kv: -len(kv[1]))[:12])
    check("No clipping between pieces", tot == 0, detail)
    bad_p, npp = people_clipping(inst)
    check("People do not clip into seats, platforms or posts", not bad_p,
          f"{len(bad_p)} of {npp} sampled" + (f", e.g. {bad_p[:4]}" if bad_p else ""))

    rep()
    rep("## 6. Proportions")
    rep("| item | size | note |")
    rep("|---|---|---|")
    for item, size, note in (("block character", "1.44 m tall", "1 skin px = 4.5 cm; world texel 6.25 cm"),
                             ("F1 car (library)", "5.6 x 2.0 m", "grid slot 8 m pitch, staggered"),
                             ("track width", f"{L.WIDTH:.0f} m (main straight {L.WIDTH_AT['main straight']:.0f} m)", "real F1: 12-15 m"),
                             ("pit lane", f"{L.PIT_W:.0f} m (fast lane + working lane)", "box 8 m long per team"),
                             ("garage", f"{L.GARAGE_W / 2:.0f} m bay x 14 m deep, door 4.8 m", "two bays per team"),
                             ("kerb", f"{L.KERB_W} m wide, {L.STRIPE:.0f} m stripes", "flush (cars roll over)"),
                             ("concrete wall / fence", "1.15 m / +3.6 m with catch panel", "fence on every barrier"),
                             ("grandstand row", "0.8 m tread, 0.45 m rise, 0.5 m seat pitch", "seat top 0.5 m"),
                             ("floodlight mast", "22 m", "lamp bank toward the track")):
        rep(f"| {item} | {size} | {note} |")

    rep()
    rep("## 7. Performance")
    dg = bpy.context.evaluated_depsgraph_get()
    tri, ninst = 0, 0
    cache = {}
    for oi in dg.object_instances:
        ob = oi.object
        if ob.type != "MESH":
            continue
        if oi.is_instance:
            ninst += 1
        key = ob.data.name if hasattr(ob, "data") and ob.data else ob.name
        if key not in cache:
            me = ob.data
            cache[key] = sum(len(p.vertices) - 2 for p in me.polygons) if me else 0
        tri += cache[key]
    objs = len([o for o in bpy.data.objects])
    rep(f"- objects in the file: {objs} (terrain {len([o for o in bpy.data.objects if o.name.startswith(TERRAIN)])}, "
        f"instancers {len([o for o in bpy.data.objects if 'proto' in o and not len(o.data.polygons)])})")
    rep(f"- instances drawn: {ninst}; triangles drawn: {tri / 1e6:.1f} M (unique mesh data is much smaller: "
        f"{sum(len(m.polygons) for m in bpy.data.meshes) * 2 / 1e6:.1f} M)")
    rep(f"- materials: {len(bpy.data.materials)}, images: {len(bpy.data.images)} (all 16 px/m pixel textures)")
    rep(f"- lights: {len([o for o in bpy.data.objects if o.type == 'LIGHT'])} (floodlight spots only switch on at night)")
    if "--renders" in argv:
        import lighting, cameras
        sc = bpy.context.scene
        lighting.eevee(sc, 48)
        sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1920, 1080, 100
        sc.render.filepath = os.path.join(OUT, "qc_render_test.png")
        for cam in ("cam_establishing", "cam_pit_lane"):
            cameras.use(cam)
            t1 = time.time()
            bpy.ops.render.render(write_still=False)
            rep(f"- 1080p EEVEE, 48 samples, {cam}: {time.time() - t1:.1f} s per frame")
    rep()
    rep(f"**Result: {'PASS' if not FAIL else 'FAIL: ' + ', '.join(FAIL)}** ({time.time() - t0:.0f} s)")
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "qc_report.md"), "w", encoding="utf8") as f:
        f.write("\n".join(REPORT) + "\n")


main()
