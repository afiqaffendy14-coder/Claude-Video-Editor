"""Build the whole circuit in Blender from layout.py / plan.py / site.py, or load the saved one.

    import sys; sys.path.insert(0, r"<Claude-Video-Editor>/library/environments/f1_circuit")
    import circuit_blender as cb
    cb.load_circuit()                     # append blend/circuit.blend into the current scene
    cb.set_time("night")                  # day | golden | overcast | night
    x, y, yaw = cb.lap_frame(s=350.0, offset=-2.0)   # place / animate cars on the lap (s in metres)

Everything is grouped under the collection "circuit" in sub-collections (track, kerbs, ground, barriers,
trackside, pit, stands, crowd, operations, paddock, venue, vegetation, vehicles, lighting) so a shot can hide
whole groups. Repeated pieces are Geometry Nodes instances of prototypes ("circuit_protos").
"""
import math
import os
import sys
import time
import numpy as np
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import layout as L
import plan as P
import ground as S
import blocks as B
import terrain
import props as PR
import buildings as BD
import lighting

BLEND = os.path.join(HERE, "blend", "circuit.blend")
ROOT = "circuit"
FOOT = []          # placed footprints: (name, rect, kind) for overlap checks
LOG = []


def log(*a):
    msg = " ".join(str(x) for x in a)
    LOG.append(msg)
    print(msg, flush=True)


# ---------------------------------------------------------------- public helpers (also used by shots)
def lap_frame(s, offset=0.0):
    """World (x, y, yaw) on the lap, `offset` m left of the centre line. A car at yaw faces along the lap
    (the car libraries face +Y, so rotate the car by yaw - pi/2)."""
    x, y, h = L.frame(s, offset)
    return x, y, h


def car_yaw(h):
    return h - math.pi / 2


def grid_slot(n):
    pos, x, y, h = L.grid()[n - 1]
    return x, y, car_yaw(h)


def pit_box(team):
    """Centre of a team's pit box (team index or key) and the yaw of a car parked nose-out (facing the exit)."""
    i = team if isinstance(team, int) else [t[0] for t in P.TEAMS].index(team)
    _, x0, x1 = L.garages()[i]
    return (x0 + x1) / 2, (L.GARAGE_Y + L.PIT_Y - 1.25) / 2, car_yaw(0.0)


def set_time(mode="day", scene=None):
    return lighting.set_time(scene or bpy.context.scene, mode)


def set_flag(post, colour=None):
    """Light a marshal post's digital flag panel: colour 'yellow', 'double_yellow', 'green', 'red', 'blue',
    'white' or None (off). Keyframe-able: the panel object's ["flag_rgb"] and ["flag_on"] custom properties."""
    ob = bpy.data.objects.get(f"flag_panel_{post:02d}")
    cols = {"yellow": (1.0, 0.8, 0.0), "double_yellow": (1.0, 0.8, 0.0), "green": (0.1, 1.0, 0.2),
            "red": (1.0, 0.05, 0.02), "blue": (0.1, 0.35, 1.0), "white": (1, 1, 1)}
    if ob is None:
        return None
    ob["flag_rgb"] = cols.get(colour, (0, 0, 0))
    ob["flag_on"] = 0.0 if colour is None else 6.0
    ob.update_tag()
    return ob


def garage_door(team, bay, open_=1.0):
    ob = bpy.data.objects.get(f"garage_door_{P.TEAMS[team][0]}_{bay}")
    if ob:
        ob.scale.z = 1.0 - 0.96 * open_
    return ob


def load_circuit(scene=None, time_of_day=None, cameras_too=True):
    """Append the saved circuit (blend/circuit.blend) into the scene: the "circuit" collection with everything,
    its sky and sun. Returns the collection. time_of_day: None keeps the saved lighting (day)."""
    sc = scene or bpy.context.scene
    with bpy.data.libraries.load(BLEND, link=False) as (src, dst):
        dst.collections = [ROOT]
        dst.worlds = ["circuit_sky"]
    coll = dst.collections[0]
    sc.collection.children.link(coll)
    sc.world = dst.worlds[0]
    if not cameras_too:
        cc = bpy.data.collections.get("circuit_cameras")
        if cc:
            for ob in list(cc.objects):
                bpy.data.objects.remove(ob)
    lighting.eevee(sc)
    if time_of_day:
        set_time(time_of_day, sc)
    for ob in coll.all_objects:
        if ob.type == "CAMERA" and ob.name == "cam_establishing" and sc.camera is None:
            sc.camera = ob
    return coll


# ---------------------------------------------------------------- placement utilities
def rot2(yaw, x, y):
    c, s = math.cos(yaw), math.sin(yaw)
    return c * x - s * y, s * x + c * y


def resample(pts, step):
    """Polyline -> equal chords near `step` long: mids (n x 2), headings (n), lengths (n), param (n, 0..1 along)."""
    pts = np.asarray(pts, float)
    d = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(d)])
    tot = cum[-1]
    n = max(1, int(round(tot / step)))
    t = np.linspace(0, tot, n + 1)
    Pp = np.stack([np.interp(t, cum, pts[:, 0]), np.interp(t, cum, pts[:, 1])], 1)
    a, b = Pp[:-1], Pp[1:]
    mid = (a + b) / 2
    h = np.arctan2(b[:, 1] - a[:, 1], b[:, 0] - a[:, 0])
    ln = np.linalg.norm(b - a, axis=1)
    return mid, h, ln, ((t[:-1] + t[1:]) / 2) / max(tot, 1e-9)


def runs(mask):
    """Index ranges [a, b) where mask is True."""
    m = np.concatenate([[False], mask, [False]]).astype(int)
    d = np.diff(m)
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))


class Footprints:
    """Grid hash of placed oriented rectangles for clearance checks."""
    def __init__(self, cell=20.0):
        self.cell, self.items, self.grid = cell, [], {}

    def add(self, name, r, kind="prop"):
        k = len(self.items)
        self.items.append((name, r, kind))
        pts = np.array(P.corners(r))
        for gx in range(int(pts[:, 0].min() // self.cell), int(pts[:, 0].max() // self.cell) + 1):
            for gy in range(int(pts[:, 1].min() // self.cell), int(pts[:, 1].max() // self.cell) + 1):
                self.grid.setdefault((gx, gy), []).append(k)

    def hits(self, r, ignore_kind=()):
        pts = np.array(P.corners(r))
        seen = set()
        out = []
        for gx in range(int(pts[:, 0].min() // self.cell), int(pts[:, 0].max() // self.cell) + 1):
            for gy in range(int(pts[:, 1].min() // self.cell), int(pts[:, 1].max() // self.cell) + 1):
                for k in self.grid.get((gx, gy), []):
                    if k in seen:
                        continue
                    seen.add(k)
                    name, r2, kind = self.items[k]
                    if kind in ignore_kind:
                        continue
                    if rect_overlap(r, r2):
                        out.append(name)
        return out


def rect_overlap(a, b, eps=0.01):
    """Separating-axis test for two oriented rectangles (shrunk by eps so touching is not overlapping)."""
    pa, pb = np.array(P.corners(a)), np.array(P.corners(b))
    for r in (a, b):
        c, s = math.cos(r["yaw"]), math.sin(r["yaw"])
        for ax in ((c, s), (-s, c)):
            ax = np.array(ax)
            A, Bp = pa @ ax, pb @ ax
            if A.max() - eps <= Bp.min() or Bp.max() - eps <= A.min():
                return False
    return True


FP = Footprints()


def ground_type(x, y):
    i, j = S.ij(x, y)
    return int(_R["T"][np.clip(j, 0, S.NY - 1), np.clip(i, 0, S.NX - 1)])


def ground_z(x, y):
    i, j = S.ij(x, y)
    return float(_R["H"][np.clip(j, 0, S.NY - 1), np.clip(i, 0, S.NX - 1)])


def free(r, allowed, ignore_kind=()):
    """True if rect r sits only on allowed ground types (corners + centre) and hits no placed footprint."""
    for x, y in P.corners(r) + [(r["cx"], r["cy"])]:
        if ground_type(x, y) not in allowed:
            return False
    return not FP.hits(r, ignore_kind)


SOFT = (S.GRASS, S.GRASS2, S.CONCRETE, S.PAVING, S.HILL, S.DIRT)
_R = {}


# ================================================================ the build
def build_circuit(time_of_day="day", save=True, quick=False):
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    FP.items.clear()
    FP.grid.clear()
    B.MATS.clear()
    PR._M.clear()
    root = B.collection(ROOT)
    C = {k: B.collection(f"circuit_{k}", root) for k in
         ("track", "kerbs", "ground", "barriers", "trackside", "pit", "stands", "crowd", "operations", "paddock",
          "venue", "vegetation", "vehicles", "lighting", "cameras")}

    log("site raster ...")
    R = S.build(verbose=False)
    _R.update(R)
    log(f"  {time.time() - t0:.0f}s")

    def coll_for(name):
        if name.startswith("track_"):
            return C["track"]
        if name.startswith("kerbs_"):
            return C["kerbs"]
        if name == "pit_lane":
            return C["pit"]
        return C["ground"]

    obs = terrain.build(R, coll_for)
    log(f"terrain: {len(obs)} objects, {sum(len(o.data.polygons) for o in obs.values())} faces, {time.time() - t0:.0f}s")

    log("prototypes ...")
    for f in (PR.concrete_wall, PR.debris_fence, PR.armco, PR.tyre_wall, PR.gate, PR.sausage_kerb, PR.fence_banner,
              PR.led_board, PR.ad_board, PR.big_sign, PR.distance_board, PR.drs_board, PR.pit_signs,
              PR.pit_exit_light, PR.track_camera, PR.cctv, PR.floodlight, PR.street_light, PR.flag_pole,
              PR.marshal_post, PR.fire_point, PR.spectators, PR.seat_row_seat, PR.trees, PR.hedge, PR.road_cars,
              PR.service_cars, PR.transporter, PR.pit_kit, BD.garage_bay, BD.motorhome):
        f()
    for m in bpy.data.materials:
        if m.name in ("c_lamp", "c_red_light", "c_green_light", "c_amber_light", "c_blue_light"):
            m["lamp"] = True
    log(f"  {len(bpy.data.collections['circuit_protos'].children)} prototype groups, {time.time() - t0:.0f}s")

    place_buildings(C)
    place_stands(C)
    place_barriers(C, R)
    place_trackside(C, R)
    place_pit(C)
    place_operations(C)
    place_venue(C)
    place_vegetation(C, R)
    _night_windows()
    lighting.eevee(sc)
    set_time(time_of_day, sc)
    import cameras
    cameras.add_presets(C["cameras"])
    _closeup_cameras(C["cameras"])
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    log(f"build done in {time.time() - t0:.0f}s")
    sc["circuit_footprints"] = len(FP.items)
    if save:
        os.makedirs(os.path.dirname(BLEND), exist_ok=True)
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
        log("saved", BLEND)
    return C


def _closeup_cameras(coll):
    """Close-up presets that depend on placed pieces: a marshal post, a tyre wall, the main grandstand crowd."""
    import cameras
    n, s = post_positions()[4]
    x, y, yw = _behind(s, 1, 2.5)
    fx, fy = rot2(yw, 0, 1.0)
    sx, sy = rot2(yw, 1.0, 0)
    cameras.aim("cam_marshal_post", (x + fx * 4.5 - sx * 11, y + fy * 4.5 - sy * 11, 4.2), (x - sx * 1.2, y - sy * 1.2, 2.2), 32.0, coll)
    a, b = L.corner_range("T10")
    cs = L.corner_side("T10")
    sm = b + 8
    bx, by, byaw = _behind(sm, -cs, -1.4)
    px_, py_, _ = _behind(sm + 7, -cs, -9.0)
    cameras.aim("cam_tyre_wall", (px_, py_, 1.4), (bx, by, 0.6), 30.0, coll)
    cameras.aim("cam_crowd_close", (-75.0, 19.6, 3.2), (-62.0, 32.0, 4.5), 30.0, coll)
    gx = (L.garages()[3][1] + L.garages()[3][2]) / 2
    cameras.aim("cam_pit_box", (gx + 9.0, L.PIT_Y + 3.0, 3.2), (gx, L.GARAGE_Y - 3.0, 1.0), 26.0, coll)


def _night_windows():
    """Facade materials get an emission link (off by day) so windows light up at night."""
    for m in bpy.data.materials:
        if not any(k in m.name for k in ("facade", "house_wall", "flats_", "office_", "c_glass")):
            continue
        nt = m.node_tree
        b = nt.nodes.get("Principled BSDF")
        tx = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None)
        if b is None or tx is None:
            continue
        nt.links.new(tx.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = 0.0
        m["emit_base"] = 0.0
        m["night_window"] = True


# ---------------------------------------------------------------- buildings
def place_buildings(C):
    pb = P.PIT_BUILDING
    # garage bays: two per team, team 0 at the west end
    pos, yaw, var = [], [], []
    for i, x0, x1 in L.garages():
        for k in range(2):
            x = x0 + BD.BAY_W * (k + 0.5)
            pos.append((x, L.GARAGE_Y, 0))
            var.append(i)
            ob = BD.garage_door().build(f"garage_door_{P.TEAMS[i][0]}_{k}", C["pit"])
            ob.location = (x, L.GARAGE_Y, 4.8)
            ob.scale.z = 0.04      # open (rolled up)
            ob["open"] = 1.0
    B.scatter("pit_building_bays", "garage_bay", pos, var=var, coll=C["pit"])
    gx0 = L.GARAGE_X0
    gx1 = L.GARAGE_X0 + L.GARAGE_N * L.GARAGE_W
    FP.add("pit_building", P.rect((gx0 + gx1) / 2, L.GARAGE_Y - BD.BAY_D / 2, gx1 - gx0, BD.BAY_D), "building")
    # end wall of the last bay (each bay only builds its -x wall)
    mb = B.MeshBuilder()
    mb.box((gx1 - 0.15, L.GARAGE_Y - BD.BAY_D / 2, BD.ROOF / 2), (0.3, BD.BAY_D, BD.ROOF), PR.M("concrete"))
    mb.build("pit_building_endwall", C["pit"])
    # media centre (west) and race control tower (east)
    b, H = BD.building_end("media_centre", "MEDIA CENTRE", 4, 30.0, 24.0, "#CBD0D6")
    ob = b.build("media_centre", C["operations"])
    ob.location = (P.MEDIA["cx"] - 1.0, P.MEDIA["cy"] - 0.0, 0)
    FP.add("media_centre", P.rect(P.MEDIA["cx"] - 1.0, P.MEDIA["cy"], 30.0, 24.0), "building")
    ob = BD.race_control().build("race_control", C["operations"])
    ob.location = (P.RACE_CONTROL["cx"] + 1.0, P.RACE_CONTROL["cy"] - 2.0, 0)
    FP.add("race_control", P.rect(P.RACE_CONTROL["cx"] + 1.0, P.RACE_CONTROL["cy"] - 2.0, 30.0, 24.0), "building")
    # giant screen on the pit building roof, facing the main grandstand
    ob = BD.giant_screen().build("screen_pit_roof", C["venue"])
    ob.location = (-60.0, L.GARAGE_Y - 6.0, BD.ROOF)
    # paddock: motorhomes and transporters
    mh = P.motorhomes()
    B.scatter("paddock_motorhomes", "motorhome", [(r["cx"], r["cy"], 0) for _, r in mh], var=[i for i, _ in mh],
              coll=C["paddock"])
    for i, r in mh:
        FP.add(f"motorhome_{i}", P.rect(r["cx"], r["cy"] + 2.0, 18.4, 18.4), "building")
    tr = P.transporters()
    B.scatter("paddock_transporters", "transporter", [(r["cx"], r["cy"], 0) for _, r in tr],
              yaw=[0.0] * len(tr), var=[i for i, _ in tr], coll=C["paddock"])
    for k, (i, r) in enumerate(tr):
        FP.add(f"transporter_{k}", P.rect(r["cx"], r["cy"] + 1.2, 2.6, 18.6), "vehicle")
    # paddock flags and lights
    fl = [(x, P.PADDOCK["y1"] - 12.5, 0) for x in np.arange(P.PADDOCK["x0"] + 20, P.PADDOCK["x1"] - 10, 22.0) + 11.0]
    B.scatter("paddock_flags", "flag_pole", fl, var=[k % 8 for k in range(len(fl))], coll=C["paddock"])
    # paddock street lights (with real lamps for night shots)
    pl = [(x, P.PADDOCK["y1"] - 1.2, 0, math.pi) for x in np.arange(P.PADDOCK["x0"] + 9, P.PADDOCK["x1"] - 5, 22.0)]
    B.scatter("paddock_street_lights", "street_light", [p[:3] for p in pl], yaw=[p[3] for p in pl], coll=C["paddock"])
    lighting.flood_spots([(x, y - 1.15, 7.8, math.pi) for x, y, z, _ in pl], C["lighting"], energy=6000.0, reach=3.0,
                         prefix="paddock_lamp")
    # medical centre, helipad, fire station
    for name, fn, r in (("medical_centre", BD.medical_centre, P.MEDICAL), ("fire_station", BD.fire_station, P.FIRE_STATION)):
        ob = fn().build(name, C["operations"])
        ob.location = (r["cx"], r["cy"], 0)
        FP.add(name, r, "building")
    ob = BD.helipad().build("helipad", C["operations"])
    ob.location = (P.HELIPAD[0], P.HELIPAD[1], 0)
    FP.add("helipad", P.rect(P.HELIPAD[0], P.HELIPAD[1], 22, 22), "building")
    # VIP terrace beyond T1, the hotel
    for name, fn, r in (("vip_terrace", BD.vip_terrace, P.HOSPITALITY_VIP), ("hotel", BD.hotel, P.HOTEL)):
        ob = fn().build(name, C["venue"])
        ob.location = (r["cx"], r["cy"], 0)
        ob.rotation_euler.z = r["yaw"]
        FP.add(name, r, "building")


# ---------------------------------------------------------------- stands, crowd, screens
def place_stands(C):
    rng = np.random.default_rng(5)
    for st in P.stands():
        r = st["rect"]
        b, seats, depth, top = BD.grandstand_section(st["name"], st["rows"], st["roof"], st["colour"])
        B.proto("stand_" + st["name"], b, 0)
        B.proto("stand_end_" + st["name"], BD.stand_end(st["rows"], depth), 0)
        n = st["n"]
        secs = [(-r["w"] / 2 + 5 + 10 * k, 0.0) for k in range(n)]
        pos = [(r["cx"] + rot2(r["yaw"], x, y)[0], r["cy"] + rot2(r["yaw"], x, y)[1], 0) for x, y in secs]
        B.scatter(st["name"], "stand_" + st["name"], pos, yaw=[r["yaw"]] * n, coll=C["stands"])
        ends = [(r["cx"] + rot2(r["yaw"], sx * (r["w"] / 2 + 0.15), 0)[0],
                 r["cy"] + rot2(r["yaw"], sx * (r["w"] / 2 + 0.15), 0)[1], 0) for sx in (-1, 1)]
        B.scatter(st["name"] + "_ends", "stand_end_" + st["name"], ends, yaw=[r["yaw"]] * 2, coll=C["stands"])
        FP.add(st["name"], P.rect(r["cx"], r["cy"], r["w"] + 0.6, r["d"] + 1.0, r["yaw"]), "building")
        # crowd: ~75% of seats taken
        cp, cy_, cv = [], [], []
        for x, y in secs:
            for sx, sy, sz in seats:
                if rng.random() > 0.75:
                    continue
                wx, wy = rot2(r["yaw"], x + sx, y + sy)
                cp.append((r["cx"] + wx, r["cy"] + wy, sz))
                cy_.append(r["yaw"])
                cv.append(int(rng.integers(0, 24)))
        B.scatter("crowd_" + st["name"], "spectator_sit", cp, yaw=cy_, var=cv, coll=C["crowd"])
        # a giant screen past one end of every stand but the main one, turned toward the seats
        if st["name"] != "main_grandstand":
            lx, ly = r["w"] / 2 + 12.0, r["d"] / 2 - 2.0
            sx_, sy_ = rot2(r["yaw"], lx, ly)
            px, py = r["cx"] + sx_, r["cy"] + sy_
            yaw = P.facing(px, py, r["cx"], r["cy"])
            fr = P.rect(px, py, 12.6, 3.0, yaw)
            if free(fr, SOFT):
                ob = BD.giant_screen().build("screen_" + st["name"], C["venue"])
                ob.location = (px, py, 0)
                ob.rotation_euler.z = yaw
                FP.add("screen_" + st["name"], fr, "building")
        # flags on the back of the stand
        fl = []
        for k in range(0, n, 2):
            x = -r["w"] / 2 + 5 + 10 * k
            wx, wy = rot2(r["yaw"], x, -r["d"] / 2 - 1.2)
            fl.append((r["cx"] + wx, r["cy"] + wy, 0))
        B.scatter(st["name"] + "_flags", "flag_pole", fl, yaw=[r["yaw"]] * len(fl),
                  var=[(k + len(st["name"])) % 8 for k in range(len(fl))], coll=C["stands"])
    log(f"stands: {len(P.stands())}, crowd objects {len([o for o in C['crowd'].objects])}")


# ---------------------------------------------------------------- barriers
def _near_stand_s():
    out = []
    for st in P.stands():
        r = st["rect"]
        s, _, _, _ = L.nearest(np.array([r["cx"]]), np.array([r["cy"]]))
        out.append(float(s[0]))
    return out


def place_barriers(C, R):
    s_b = R["s_b"]
    stand_s = _near_stand_s()
    lap = L.LAP

    def near_stand(s):
        d = np.min([np.abs(((s - v + lap / 2) % lap) - lap / 2) for v in stand_s], axis=0)
        return d < 220

    def concrete_s(s, side=1):
        # concrete (+ tyres) wherever there is a gravel/asphalt run-off or spectators; armco on the plain verges
        return near_stand(s) | (s < 1000) | (s > lap - 150) | (L.runoff(s, side)[0] > 0)
    gates = [((s_ + 14.0) % lap) for _, s_ in post_positions()]
    walls, fences, armcos, tyres, gate_pts, banners, leds = [], [], [], [], [], [], []
    for side in (1, -1):
        off, pit = R["bo"][side]
        rr = runs(~pit)
        idx_runs = [np.arange(a, b) for a, b in rr]
        if len(rr) > 1 and rr[0][0] == 0 and rr[-1][1] == len(s_b):      # join the run across the start line
            idx_runs = [np.concatenate([idx_runs[-1], idx_runs[0]])] + idx_runs[1:-1]
        elif len(rr) == 1 and rr[0] == (0, len(s_b)):
            idx_runs = [np.concatenate([idx_runs[0], idx_runs[0][:1]])]   # closed loop
        for ix in idx_runs:
            ss = s_b[ix].astype(float)
            ss = ss + lap * np.concatenate([[0], np.cumsum(np.diff(ss) < -lap / 2)])   # unwrap
            if len(ss) < 4:
                continue
            pts = np.array([L.frame(v, side * o)[:2] for v, o in zip(ss, off[ix])])
            # gate centres: snapped to the nearest 4 m fence chord, so wall, tyres and fence leave one 4 m gap
            fm, _, _, fu = resample(pts, 4.0)
            fsm = np.interp(fu, np.linspace(0, 1, len(ss)), ss)
            gate_s = []
            if side == 1:
                for gs in gates:
                    dd = np.abs(((fsm - gs + lap / 2) % lap) - lap / 2)
                    if dd.min() < 2.5:
                        gate_s.append(fsm[int(np.argmin(dd))])
            for step, kind in ((2.0, "wall"), (4.0, "fence"), (6.0, "banner")):
                mid, h, ln, u = resample(pts, step)
                sm = np.interp(u, np.linspace(0, 1, len(ss)), ss)
                yaw = h + (math.pi if side > 0 else 0.0)
                conc = concrete_s(sm % lap, side)
                g = np.zeros(len(sm), bool)
                for gs in gate_s:
                    g |= np.abs(sm - gs) < (0.01 if kind == "fence" else 2.0 if kind == "wall" else 5.0)
                sm = sm % lap
                for k in range(len(sm)):
                    x, y = mid[k]
                    if kind == "wall":
                        if g[k]:
                            continue
                        if conc[k]:
                            walls.append((x, y, 0, yaw[k], ln[k] / 2.0 * 1.01, int(k % 2 == 1 and near_stand(sm[k]))))
                        kind_ro, _ = L.runoff(np.array([sm[k]]), side)
                        if kind_ro[0] > 0 and concrete_s(np.array([sm[k] - 2.5, sm[k] + 2.5]) % lap, side).all():
                            tx, ty = rot2(yaw[k], 0, 1.45 if conc[k] else 2.25)
                            tyres.append((x + tx, y + ty, 0, yaw[k], ln[k] / 2.0 * 1.01, k % 3))
                    elif kind == "fence":
                        if g[k]:
                            gate_pts.append((x, y, 0, yaw[k]))
                            continue
                        fences.append((x, y, 1.15 if conc[k] else 0.0, yaw[k], ln[k] / 4.0))
                        if not conc[k]:
                            ax, ay = rot2(yaw[k], 0, 0.6)
                            armcos.append((x + ax, y + ay, 0, yaw[k], ln[k] / 4.0 * 1.01))
                    else:
                        if g[k] or not conc[k] or abs(ln[k] - 6.0) > 0.6:
                            continue
                        on_main = sm[k] < 1000
                        (leds if (on_main and side == 1) else banners).append(
                            (x, y, 1.15, yaw[k], int((k * 7 + side) % len(P.SPONSORS))))
    # dedupe gates (fence chords inside one gap)
    gp, last = [], None
    for p in gate_pts:
        if last is None or math.hypot(p[0] - last[0], p[1] - last[1]) > 6:
            gp.append(p)
        last = p

    def sc(name, proto, items, scale_x=True, var_idx=None, ztake=True):
        if not items:
            return None
        pos = [(it[0], it[1], it[2]) for it in items]
        yaw = [it[3] for it in items]
        scl = [(it[4], 1, 1) for it in items] if scale_x else None
        var = [it[var_idx] for it in items] if var_idx is not None else None
        return B.scatter(name, proto, pos, yaw=yaw, scale=scl, var=var, coll=C["barriers"])

    sc("barrier_concrete_walls", "concrete_wall", walls, var_idx=5)
    sc("barrier_armco", "armco", armcos)
    sc("barrier_tyre_walls", "tyre_wall", tyres, var_idx=5)
    sc("barrier_debris_fence", "debris_fence", fences)
    sc("barrier_gates", "gate", gp, scale_x=False)
    sc("trackside_fence_banners", "fence_banner", banners, scale_x=False, var_idx=4)
    led_items = []
    for x, y, z, yaw, v in leds:
        ox, oy = rot2(yaw, 0, 0.24)
        led_items.append((x + ox, y + oy, z, yaw, v))
    sc("trackside_led_boards", "led_board", led_items, scale_x=False, var_idx=4)
    R["gates"] = gp
    _R["gates"] = gp
    log(f"barriers: walls {len(walls)}, armco {len(armcos)}, tyre modules {len(tyres)}, fence {len(fences)}, "
        f"gates {len(gp)}, banners {len(banners)}, LED {len(leds)}")
    # pit wall: concrete + fence along the gap between the track and the pit lane, team stands on its pit side
    t, pts, keep = S.pit_wall_line()
    pw, pf, pb = [], [], []
    for a, b in runs(keep):
        if b - a < 6:
            continue
        for step, out in ((2.0, pw), (4.0, pf)):
            mid, h, ln, u = resample(pts[a:b], step)
            for k in range(len(mid)):
                out.append((mid[k][0], mid[k][1], 1.15 if out is pf else 0.0, h[k], ln[k] / step * 1.01))
    B.scatter("pit_wall", "concrete_wall", [p[:3] for p in pw], yaw=[p[3] for p in pw],
              scale=[(p[4], 1, 1) for p in pw], coll=C["pit"])
    B.scatter("pit_wall_fence", "debris_fence", [p[:3] for p in pf], yaw=[p[3] for p in pf],
              scale=[(p[4], 1, 1) for p in pf], coll=C["pit"])
    # walls on the outer (right) side of the pit entry and exit lanes
    side_pts = []
    for v in np.arange(0, L.PIT_LEN, 1.0):
        i = max(j for j, pr in enumerate(L.PIT) if pr.s0 <= v + 1e-9)
        pr = L.PIT[i]
        if pr.label == "pit lane":
            continue
        p, h, _ = pr.at(np.array([v - pr.s0]))
        p, h = p[0], float(h[0])
        o = L.pit_width(v) / 2 + 1.2
        side_pts.append((p[0] + o * math.sin(h), p[1] - o * math.cos(h), v))
    side_pts = np.array(side_pts)
    seg = []
    for a, b in runs((side_pts[:, 0] < P.SAFETY_CAR_BAY["cx"] - 22) | (side_pts[:, 0] > P.SAFETY_CAR_BAY["cx"] + 22)
                     | (side_pts[:, 1] < -60)):
        if b - a < 6:
            continue
        # break where the entry and exit runs are separate (jump in v)
        sub = side_pts[a:b]
        brk = np.flatnonzero(np.diff(sub[:, 2]) > 2) + 1
        for part in np.split(sub, brk):
            if len(part) < 6:
                continue
            mid, h, ln, u = resample(part[:, :2], 2.0)
            for k in range(len(mid)):
                if ground_type(*mid[k]) == S.TRACK:
                    continue
                seg.append((mid[k][0], mid[k][1], 0, h[k] + math.pi, ln[k] / 2.0 * 1.01))
    B.scatter("pit_lane_outer_wall", "concrete_wall", [p[:3] for p in seg], yaw=[p[3] for p in seg],
              scale=[(p[4], 1, 1) for p in seg], coll=C["pit"])


# ---------------------------------------------------------------- trackside furniture
def _behind(s, side, extra):
    """Point behind the barrier at lap distance s on side, `extra` m beyond it, and the yaw facing the track."""
    off, _ = _R["bo"][side]
    o = float(np.interp(s % L.LAP, _R["s_b"], off)) + extra
    x, y, h = L.frame(s, side * o)
    return x, y, h + (math.pi if side > 0 else 0.0)


def post_positions():
    """Marshal post lap positions, nudged (up to 40 m) to where the barrier runs parallel to the track."""
    off = _R["bo"][1][0]
    grad = np.abs(np.gradient(off))
    out = []
    for n, s in P.marshal_posts():
        cand = np.arange(s - 40, s + 41, 2.0) % L.LAP
        g = np.array([np.max(np.interp((c + np.arange(-8, 9, 1.0)) % L.LAP, _R["s_b"], grad)) for c in cand])
        out.append((n, float(cand[int(np.argmin(g + 0.0005 * np.abs(np.arange(-40, 41, 2.0))))])))
    return out


def place_trackside(C, R):
    # braking boards
    pos, yaw, var = [], [], []
    for lab, items, side in L.braking_boards():
        for d, s in items:
            o = L.width(s) / 2 + 3.0
            x, y, h = L.frame(s, side * o)
            if ground_type(x, y) not in (S.GRASS, S.GRASS2, S.RUNOFF):
                continue
            pos.append((x, y, 0))
            yaw.append(h + math.pi / 2)      # board faces the oncoming cars
            var.append({300: 0, 200: 1, 100: 2}[d])
    B.scatter("trackside_braking_boards", "distance_board", pos, yaw=yaw, var=var, coll=C["trackside"])
    # DRS boards (detection and activation)
    pos, yaw, var = [], [], []
    for det, act, end in L.drs_zones():
        for s, v in ((det, 1), (act, 0)):
            x, y, h = L.frame(s - 2.0, L.width(s) / 2 + 3.0)
            pos.append((x, y, 0))
            yaw.append(h + math.pi / 2)
            var.append(v)
    B.scatter("trackside_drs_boards", "drs_board", pos, yaw=yaw, var=var, coll=C["trackside"])
    # sausage kerbs behind the apex kerbs of the chicane
    pos, yaw = [], []
    for lab in ("T13", "T14"):
        a, b = L.corner_range(lab)
        cs = L.corner_side(lab)
        for s in np.arange(a - 2, b + 3, 1.5):
            x, y, h = L.frame(s, cs * (L.width(s) / 2 + L.KERB_W + 0.4))
            pos.append((x, y, 0))
            yaw.append(h)
    B.scatter("trackside_sausage_kerbs", "sausage_kerb", pos, yaw=yaw, coll=C["trackside"])
    # marshal posts with flag panels and fire points, on the outside (left) between barrier and service road
    panel_mat = _flag_panel_material()
    post = None
    pts = []
    for n, s in post_positions():
        x, y, yw = _behind(s, 1, 2.5)
        r = P.rect(x, y, 3.0, 2.8, yw)
        pts.append((x, y, 0, yw))
        FP.add(f"marshal_post_{n:02d}", r, "prop")
        mb = PR.flag_panel_mesh(panel_mat)
        ob = mb.build(f"flag_panel_{n:02d}", C["trackside"])
        px, py = rot2(yw, -2.65, 0.6)
        ob.location = (x + px, y + py, 0)
        ob.rotation_euler.z = yw
        ob["flag_rgb"] = (0.0, 0.0, 0.0)
        ob["flag_on"] = 0.0
        num = PR.sign_mat(f"post_{n:02d}", f"{n}", 0.8, 0.6, "#FFFFFF", "#111111", border="#111111")
        nb = B.MeshBuilder()
        nb.box((0, 0, 0), (0.8, 0.06, 0.6), PR.M("white"), faces={"+y": num}, uvfit=("+y",))
        ob2 = nb.build(f"marshal_post_number_{n:02d}", C["trackside"])
        nx_, ny_ = rot2(yw, 0.0, 1.2)
        ob2.location = (x + nx_, y + ny_, 3.9)
        ob2.rotation_euler.z = yw
    B.scatter("trackside_marshal_posts", "marshal_post", [p[:3] for p in pts], yaw=[p[3] for p in pts],
              coll=C["trackside"])
    fp = []
    for x, y, z, yw in pts:
        ox, oy = rot2(yw, 2.9, 0.4)
        fp.append((x + ox, y + oy, 0, yw))
    B.scatter("trackside_fire_points", "fire_point", [p[:3] for p in fp], yaw=[p[3] for p in fp], coll=C["trackside"])
    # marshals standing at each post
    mp = []
    for x, y, z, yw in pts:
        ox, oy = rot2(yw, -0.6, 0.92)
        mp.append((x + ox, y + oy, 1.0, yw))
    B.scatter("trackside_marshals", "marshal", [p[:3] for p in mp], yaw=[p[3] for p in mp],
              var=[k % 2 for k in range(len(mp))], coll=C["crowd"])
    # CCTV every 150 m, TV camera towers at the corners, floodlights every 75 m both sides
    cc = []
    for s in np.arange(30, L.LAP, 150.0):
        x, y, yw = _behind(s, 1, 2.0)
        r = P.rect(x, y, 0.6, 0.6, yw)
        if free(r, SOFT + (S.ROAD,)):
            cc.append((x, y, 0, yw))
            FP.add(f"cctv_{s:.0f}", r)
    B.scatter("ops_cctv", "cctv", [p[:3] for p in cc], yaw=[p[3] for p in cc], coll=C["operations"])
    cams, cvar = [], []
    for lab in L.CORNERS:
        a, b = L.corner_range(lab)
        cs = L.corner_side(lab)
        for s, ex in (((a + b) / 2, 13.5), (a - 60, 13.5)):
            x, y, yw = _behind(s, 1 if cs < 0 else -1, ex if cs < 0 else 3.0)
            r = P.rect(x, y, 2.6, 2.6, yw)
            if free(r, SOFT):
                cams.append((x, y, 0, yw))
                cvar.append(0)
                FP.add(f"tv_camera_{lab}_{s:.0f}", r)
    B.scatter("trackside_tv_cameras", "track_camera", [p[:3] for p in cams], yaw=[p[3] for p in cams], var=cvar,
              coll=C["trackside"])
    fl = []
    for side, ex in ((1, 13.0), (-1, 4.0)):
        for s in np.arange(20 if side > 0 else 57, L.LAP, 75.0):
            x, y, yw = _behind(s, side, ex)
            r = P.rect(x, y, 5.0, 1.6, yw)
            if free(r, SOFT):
                fl.append((x, y, 0, yw))
                FP.add(f"floodlight_{side}_{s:.0f}", r)
    B.scatter("lighting_floodlights", "floodlight", [p[:3] for p in fl], yaw=[p[3] for p in fl], coll=C["lighting"])
    spots = []
    for x, y, z, yw in fl:
        ox, oy = rot2(yw, 0, 0.6)
        spots.append((x + ox, y + oy, 23.0, yw))
    lighting.flood_spots(spots, C["lighting"])
    # roof-mounted floodlights on every stand and along the pit building roof (where masts cannot stand)
    roof = []
    for st in P.stands():
        r = st["rect"]
        hgt = 1.2 + st["rows"] * 0.45 + (6.0 if st["roof"] == "cantilever" else 4.5 if st["roof"] == "flat" else 3.0)
        for k in range(0, st["n"], 2):
            wx, wy = rot2(r["yaw"], -r["w"] / 2 + 5 + 10 * k, r["d"] / 2)
            roof.append((r["cx"] + wx, r["cy"] + wy, hgt, r["yaw"]))
    for x in np.arange(L.GARAGE_X0 - 20, L.GARAGE_X0 + L.GARAGE_N * L.GARAGE_W + 30, 22.0):
        roof.append((x, L.GARAGE_Y + 1.0, BD.ROOF + 1.5, 0.0))
    lighting.flood_spots(roof, C["lighting"], energy=70000.0, reach=30.0, prefix="roof_spot")
    # big billboards on the outside of a few corners, ad boards along the inside of the long straights
    bb = []
    for k, lab in enumerate(("T1", "T4", "T10", "T3", "T11", "T15")):
        a, b = L.corner_range(lab)
        cs = L.corner_side(lab)
        x, y, yw = _behind((a + b) / 2 + 20, -cs, 20.0)
        r = P.rect(x, y, 12.0, 1.0, yw)
        if free(r, SOFT):
            bb.append((x, y, 0, yw, k * 2 % len(P.SPONSORS)))
            FP.add(f"billboard_{lab}", r)
    B.scatter("trackside_billboards", "big_sign", [p[:3] for p in bb], yaw=[p[3] for p in bb], var=[p[4] for p in bb],
              coll=C["trackside"])
    # start/finish gantry
    offl = float(np.interp(L.SF_S, _R["s_b"], _R["bo"][1][0]))
    g = BD.start_gantry(offl, abs(L.PIT_WALL_Y) + 1.2).build("start_gantry", C["trackside"])
    g.location = (L.SF_X + 1.5, 0, 0)
    log(f"trackside: boards, {len(pts)} marshal posts, {len(cc)} cctv, {len(cams)} tv cams, {len(fl)} floodlights")


def _flag_panel_material():
    m = bpy.data.materials.new("c_flag_panel")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    a1 = nt.nodes.new("ShaderNodeAttribute")
    a1.attribute_type = "OBJECT"
    a1.attribute_name = "flag_rgb"
    a2 = nt.nodes.new("ShaderNodeAttribute")
    a2.attribute_type = "OBJECT"
    a2.attribute_name = "flag_on"
    b.inputs["Base Color"].default_value = (0.02, 0.02, 0.025, 1)
    nt.links.new(a1.outputs["Color"], b.inputs["Emission Color"])
    nt.links.new(a2.outputs["Fac"], b.inputs["Emission Strength"])
    b.inputs["Roughness"].default_value = 0.3
    return m


# ---------------------------------------------------------------- pit lane dressing
def place_pit(C):
    gar = L.garages()
    stand, gant, tyres, cab, jacks, guns, crew = [], [], [], [], [], [], []
    for i, x0, x1 in gar:
        cx = (x0 + x1) / 2
        stand.append((cx, L.PIT_WALL_Y - 1.6, 0, 0.0, i))
        gant.append((cx, L.GARAGE_Y + 0.4, 0, 0.0, i))
        for k in range(3):
            tyres.append((x0 + 1.2 + 1.0 * k, L.GARAGE_Y + 1.0, 0, 0.0, i))
        jacks.append((cx + 1.6, L.GARAGE_Y + 2.6, 0, 0.0, i))
        guns.append((cx + 3.2, L.GARAGE_Y + 1.0, 0, 0.0, i))
        crew.append((cx - 3.5, L.GARAGE_Y + 2.6, 0, math.pi * 0.0, i))
        crew.append((x1 - 2.5, L.GARAGE_Y + 1.8, 0, math.pi * 0.15, i))
    for name, proto, items in (("pit_wall_stands", "pit_wall_stand", stand), ("pit_gantries", "pit_gantry", gant),
                               ("pit_tyre_sets", "tyre_set", tyres), ("pit_jacks", "jack", jacks),
                               ("pit_wheel_guns", "wheel_gun", guns)):
        B.scatter(name, proto, [p[:3] for p in items], yaw=[p[3] for p in items], var=[p[4] for p in items],
                  coll=C["pit"])
    B.scatter("pit_crew", "crew", [p[:3] for p in crew], yaw=[p[3] for p in crew], var=[p[4] for p in crew],
              coll=C["crowd"])
    # signs: PIT IN at the entry, 80 at the limit lines, PIT OUT + exit light at the end
    ex, ey, eh = L.frame(L.PIT_ENTRY_S - 60, -(L.width(0) / 2 + 3.0))
    sg = [(ex, ey, 0, eh + math.pi / 2, 1)]
    for xl, v in ((L.PIT_LIMIT[0] + 3, 0), (L.PIT_LIMIT[1] + 3, 3)):
        sg.append((xl, L.PIT_Y - L.PIT_W / 2 - 1.2, 0, math.pi / 2, v))
    last = L.PIT[-1]
    (px, py), ph = last.end()
    sg.append((px - 40, py - 4.5, 0, math.pi / 2, 2))
    B.scatter("pit_signs", "pit_sign", [p[:3] for p in sg], yaw=[p[3] for p in sg], var=[p[4] for p in sg],
              coll=C["pit"])
    lx, ly = L.PIT_X[1] + 60, None
    t_ = np.array([last.s0 - 20.0])
    p_, h_, _ = L.PIT[-2].at(np.array([L.PIT[-2].length * 0.4]))
    B.scatter("pit_exit_light", "pit_exit_light", [(p_[0][0], p_[0][1] - 5.5, 0)], yaw=[math.pi / 2], var=[0],
              coll=C["pit"])


# ---------------------------------------------------------------- race operations
def place_operations(C):
    # safety car + medical car in their bay, ambulance at the medical centre, fire truck, recovery trucks
    sb = P.SAFETY_CAR_BAY
    veh = [(sb["cx"] - 8, sb["cy"], 0, 0.0, 0), (sb["cx"] + 2, sb["cy"], 0, 0.0, 1),
           (P.MEDICAL["cx"] + 3, P.MEDICAL["cy"] + 11 + 4.5, 0, math.pi / 2, 2),
           (P.FIRE_STATION["cx"], P.FIRE_STATION["cy"] + 9 + 5.0, 0, 0.0, 3)]
    for x, y, z, yw, v in veh:
        FP.add(f"service_vehicle_{v}", P.rect(x, y, 2.6, 7.0, yw), "vehicle")
    # recovery trucks and cranes parked on the service road near the gates, facing along the road
    gates = _R.get("gates", [])
    for k, (gx, gy, _, gyaw) in enumerate(gates[::3]):
        ox, oy = rot2(gyaw, 0, -6.5)
        x, y = gx + ox, gy + oy
        if ground_type(x, y) == S.ROAD:
            yw = gyaw + math.pi / 2
            if free(P.rect(x, y, 2.6, 8.0, yw), SOFT + (S.ROAD,)):
                veh.append((x, y, 0, yw, 4 if k % 2 == 0 else 5))
                FP.add(f"recovery_{k}", P.rect(x, y, 2.6, 8.0, yw), "vehicle")
    B.scatter("ops_service_vehicles", "service_vehicle", [p[:3] for p in veh], yaw=[p[3] for p in veh],
              var=[p[4] for p in veh], coll=C["operations"])
    log(f"operations: {len(veh)} service vehicles")


# ---------------------------------------------------------------- venue: entrance, bridges, platforms, car parks, town
def place_venue(C):
    rng = np.random.default_rng(9)
    gx, gy = P.ENTRANCE["gate"]
    ob = BD.entrance_arch().build("entrance_arch", C["venue"])
    ob.location = (gx, gy, 0)
    FP.add("entrance_arch", P.rect(gx, gy - 4, 60, 12), "building")
    pl = P.ENTRANCE["plaza"]
    fl = [(x, pl["cy"] - pl["d"] / 2 + 2, 0) for x in np.arange(pl["cx"] - 70, pl["cx"] + 71, 14.0)]
    B.scatter("venue_entrance_flags", "flag_pole", fl, var=[k % 8 for k in range(len(fl))], coll=C["venue"])
    # spectator bridges
    for k, (name, s, _) in enumerate(P.BRIDGES):
        ol = float(np.interp(s, _R["s_b"], _R["bo"][1][0]))
        orr = float(np.interp(s, _R["s_b"], _R["bo"][-1][0]))
        half = max(ol, orr) + 10.0
        x, y, h = L.frame(s, 0.0)
        ob = BD.spectator_bridge(half, sponsor=k * 3 + 1).build(name, C["venue"])
        ob.location = (x, y, 0)
        # local X across the track: rotate so +X is the track's left normal
        ob.rotation_euler.z = h + math.pi / 2
        for sx in (-1, 1):
            tx, ty = rot2(h + math.pi / 2, sx * (half + 3.0), 0)
            FP.add(f"{name}_tower_{sx}", P.rect(x + tx, y + ty, 6.0, 6.0, h), "building")
    # GA viewing platforms on the outside of the esses and the fast S
    vp = []
    for lab in ("T8", "T11", "T12", "T5"):
        a, b = L.corner_range(lab)
        cs = L.corner_side(lab)
        side = -cs
        ex = 16.0 if side > 0 else 6.0
        x, y, yw = _behind((a + b) / 2, side, ex)
        r = P.rect(x, y, 13.5, 6.6, yw)
        if free(r, SOFT):
            ob = BD.viewing_platform().build(f"viewing_platform_{lab}", C["venue"])
            ob.location = (x, y, 0)
            ob.rotation_euler.z = yw
            FP.add(f"viewing_platform_{lab}", r, "building")
            for k in range(14):
                lx, ly = rng.uniform(-5.5, 5.5), rng.uniform(-2.5, 2.8)
                wx, wy = rot2(yw, lx, ly)
                vp.append((x + wx, y + wy, 3.1, yw + rng.uniform(-0.3, 0.3), int(rng.integers(0, 24))))
    B.scatter("crowd_platforms", "spectator_stand", [p[:3] for p in vp], yaw=[p[3] for p in vp],
              var=[p[4] for p in vp], coll=C["crowd"])
    # GA crowd standing on the grass banks behind the fences at the hairpin and chicane
    ga = []
    for lab in ("T4", "T13", "T10", "T2"):
        a, b = L.corner_range(lab)
        cs = L.corner_side(lab)
        for s in np.arange(a - 40, b + 40, 1.2):
            for row in range(3):
                x, y, yw = _behind(s, -cs, (11.0 if cs > 0 else 11.5) + row * 0.9 + rng.uniform(-0.2, 0.2))
                if ground_type(x, y) in (S.GRASS, S.GRASS2) and rng.random() < 0.55 and not FP.hits(P.rect(x, y, 0.5, 0.5)):
                    ga.append((x, y, 0, yw + rng.uniform(-0.25, 0.25), int(rng.integers(0, 24))))
    B.scatter("crowd_general_admission", "spectator_stand", [p[:3] for p in ga], yaw=[p[3] for p in ga],
              var=[p[4] for p in ga], coll=C["crowd"])
    # fan zone: stage, marquees, food stalls; stalls and toilets behind the big stands
    fz = P.FAN_ZONE
    ob = BD.stage().build("fan_zone_stage", C["venue"])
    ob.location = (fz["cx"], fz["cy"] + 22, 0)
    ob.rotation_euler.z = math.pi
    FP.add("fan_zone_stage", P.rect(fz["cx"], fz["cy"] + 22, 17, 11), "building")
    for k, (dx, dy) in enumerate(((-40, -20), (-10, -20), (20, -20), (45, 5))):
        ob = BD.marquee(20, 12, ("#F4F2EA", "#F4F2EA", "#C8102E", "#1F4E9C")[k]).build(f"fan_zone_marquee_{k}", C["venue"])
        ob.location = (fz["cx"] + dx, fz["cy"] + dy, 0)
        FP.add(f"fan_zone_marquee_{k}", P.rect(fz["cx"] + dx, fz["cy"] + dy, 20, 12), "building")
    stall_cols = ["#C8102E", "#1F4E9C", "#00843D", "#F2C200", "#E85D04"]
    for k, col in enumerate(stall_cols):
        B.proto("food_stall", BD.stall(col), k)
    stl = []
    for st in P.stands():
        r = st["rect"]
        for k in range(0, st["n"], 3):
            lx = -r["w"] / 2 + 5 + 10 * k
            wx, wy = rot2(r["yaw"], lx, -r["d"] / 2 - 7.0)
            yw = r["yaw"] + math.pi
            rr = P.rect(r["cx"] + wx, r["cy"] + wy, 4.8, 4.0, yw)
            if free(rr, SOFT + (S.PARKING, S.ROAD)):
                stl.append((r["cx"] + wx, r["cy"] + wy, 0, yw, k % 5))
                FP.add(f"stall_{st['name']}_{k}", rr)
    for k in range(6):
        stl.append((fz["cx"] - 50 + 20 * k, fz["cy"] - 33, 0, 0.0, k % 5))
    B.scatter("venue_food_stalls", "food_stall", [p[:3] for p in stl], yaw=[p[3] for p in stl], var=[p[4] for p in stl],
              coll=C["venue"])
    # fan zone crowd
    fc = [(fz["cx"] + rng.uniform(-25, 25), fz["cy"] + rng.uniform(0, 14), 0, math.pi * 0.0 + rng.uniform(-0.4, 0.4),
           int(rng.integers(0, 24))) for _ in range(140)]
    B.scatter("crowd_fan_zone", "spectator_stand", [p[:3] for p in fc], yaw=[p[3] for p in fc], var=[p[4] for p in fc],
              coll=C["crowd"])
    # car parks: road cars on ~65% of the bays
    cars = []
    for r in P.CAR_PARKS:
        x0, x1 = r["cx"] - r["w"] / 2, r["cx"] + r["w"] / 2
        y0, y1 = r["cy"] - r["d"] / 2, r["cy"] + r["d"] / 2
        for xb in np.arange(math.ceil(x0 / 2.5) * 2.5, x1 - 2.5, 2.5):
            for yb in np.arange(math.floor(y0 / 16) * 16, y1, 16.0):
                for yc, yw in ((yb + 2.5, 0.0), (yb + 13.5, math.pi)):
                    x, y = xb + 1.375, yc
                    if not (x0 + 1.5 < x < x1 - 1.5 and y0 + 2.6 < y < y1 - 2.6):
                        continue
                    if ground_type(x - 1, y - 2.4) != S.PARKING or ground_type(x + 1, y + 2.4) != S.PARKING:
                        continue
                    if rng.random() < 0.65:
                        cars.append((x, y, 0, yw + rng.uniform(-0.03, 0.03), int(rng.integers(0, len(PR.CAR_COLS)))))
    B.scatter("venue_parked_cars", "road_car", [p[:3] for p in cars], yaw=[p[3] for p in cars], var=[p[4] for p in cars],
              coll=C["vehicles"])
    for r in P.CAR_PARKS:
        FP.add("car_park", r, "ground")
    # street lights along the car parks and the entrance road
    sl = []
    for r in P.CAR_PARKS:
        for x in np.arange(r["cx"] - r["w"] / 2 + 10, r["cx"] + r["w"] / 2, 40.0):
            sl.append((x, r["cy"] + r["d"] / 2 + 1.5, 0, math.pi))
    for y in np.arange(140, P.TOWN["y0"], 30.0):
        sl.append((gx + 7.5, y, 0, math.pi / 2))
    B.scatter("venue_street_lights", "street_light", [p[:3] for p in sl], yaw=[p[3] for p in sl], coll=C["lighting"])
    # the town: buildings in the blocks between the streets
    kinds = ("house", "house", "house", "flats", "shop", "office")
    protos = {}
    town = []
    tw = P.TOWN
    k = 0
    for bx in np.arange(tw["x0"], tw["x1"] - 1, 120.0):
        for by in np.arange(tw["y0"], tw["y1"] - 1, 110.0):
            cxb, cyb = bx + 60, by + 55
            dist_c = abs(cxb - (gx)) / 1000
            for (ox, oy) in ((-30, -25), (0, -25), (30, -25), (-30, 25), (0, 25), (30, 25)):
                kind = kinds[int(rng.integers(0, len(kinds)))] if rng.random() > dist_c * 0.3 else "house"
                if abs(cxb - gx) < 300 and rng.random() < 0.35:
                    kind = "office"
                var = int(rng.integers(0, 4))
                key = (kind, var)
                if key not in protos:
                    b, wd = BD.town_building(kind, var * 7 + len(kind))
                    protos[key] = (len(protos), wd)
                    B.proto("town_building", b, protos[key][0])
                v, (w, d) = protos[key]
                x, y = cxb + ox + rng.uniform(-3, 3), cyb + oy + rng.uniform(-3, 3)
                yw = 0.0 if oy < 0 else math.pi
                r = P.rect(x, y, w + 2, d + 2, yw)
                if free(r, (S.GRASS, S.GRASS2, S.HILL)) and ground_z(x, y) == 0 and all(ground_z(*c) == 0 for c in P.corners(r)):
                    town.append((x, y, 0, yw, v))
                    FP.add(f"town_{k}", r, "building")
                    k += 1
    B.scatter("venue_town", "town_building", [p[:3] for p in town], yaw=[p[3] for p in town], var=[p[4] for p in town],
              coll=C["venue"])
    log(f"venue: {len(cars)} parked cars, {len(town)} town buildings, {len(ga) + len(vp) + len(fc)} standing fans")


# ---------------------------------------------------------------- vegetation
def place_vegetation(C, R):
    T, H = R["T"], R["H"]
    rng = np.random.default_rng(17)
    grassy = np.isin(T, (S.GRASS, S.GRASS2, S.HILL))
    # clearance: no tree within 8 m of anything that is not grass (integral image box count)
    bad = (~grassy).astype(np.int32)
    k = 8
    ii = np.pad(bad, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    ny, nx = T.shape

    def boxsum(j, i):
        j0, j1 = np.clip(j - k, 0, ny), np.clip(j + k + 1, 0, ny)
        i0, i1 = np.clip(i - k, 0, nx), np.clip(i + k + 1, 0, nx)
        return ii[j1, i1] - ii[j0, i1] - ii[j1, i0] + ii[j0, i0]

    n_try = 90000
    xs = rng.uniform(S.X0 + 5, S.X0 + nx - 5, n_try)
    ys = rng.uniform(S.Y0 + 5, S.Y0 + ny - 5, n_try)
    i, j = S.ij(xs, ys)
    keep = grassy[j, i] & (boxsum(j, i) == 0)
    # density: forest bands on the hills, clumps in the venue, none in the town streets' blocks
    dens = 0.5 + 0.5 * S.noise(xs, ys, 21, 260)
    venue = (xs > S.VENUE[0]) & (xs < S.VENUE[1]) & (ys > S.VENUE[2]) & (ys < S.VENUE[3])
    town = (xs > P.TOWN["x0"]) & (xs < P.TOWN["x1"]) & (ys > P.TOWN["y0"] - 20) & (ys < P.TOWN["y1"])
    p = np.where(venue, 0.12 * np.clip(dens - 0.35, 0, 1) * 2.5, np.clip(dens, 0, 1) ** 1.5 * 0.9)
    p = np.where(town, 0.05, p)
    keep &= rng.random(n_try) < p
    # keep trees well away from the track (beyond barrier + 18 m) and off footprints
    F = R["F"]
    li, lj = i - F["vi0"], j - F["vj0"]
    inside = (li >= 0) & (lj >= 0) & (li < F["D"].shape[1]) & (lj < F["D"].shape[0])
    dtr = np.full(n_try, 1e9)
    dtr[inside] = F["D"][lj[inside], li[inside]]
    keep &= dtr > 60
    pts = []
    for x, y, ok in zip(xs, ys, keep):
        if not ok:
            continue
        if FP.hits(P.rect(x, y, 6, 6)):
            continue
        pts.append((x, y))
    pts = np.array(pts)
    z = np.array([ground_z(x, y) for x, y in pts])
    var = rng.integers(0, 9, len(pts))
    hill = z > 0
    pine = hill & (rng.random(len(pts)) < 0.55)
    var[pine] = rng.choice([3, 4], pine.sum())
    yaw = rng.choice([0, math.pi / 2, math.pi, 3 * math.pi / 2], len(pts))
    B.scatter("vegetation_trees", "tree", np.c_[pts, z], yaw=yaw, var=var, coll=C["vegetation"])
    log(f"vegetation: {len(pts)} trees")
