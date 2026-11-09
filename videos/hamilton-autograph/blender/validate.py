"""Check every baked shot, frame by frame, before anything is rendered:
  * reach   - each wrist reaches its IK target (hands really grip what they hold)
  * feet    - each ankle sits on its target, planted feet do not slide, nothing sinks into the floor
  * clip    - no body part intersects the set, a prop or another character (except the prop a hand is gripping)
  * pops    - no part jumps further in one frame than it plausibly could (teleports / flicker)

Run:  validate.py <blend_dir> [shot ids...]     -> prints a report, writes <blend_dir>/validate.json
"""
import json, math, os, sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

V = Vector
SHRINK = 0.012     # parts may touch (contact is fine); only real overlap counts
REACH_TOL = 0.03   # metres between wrist and its target
SLIDE_TOL = 0.006  # metres a planted ankle may drift in one frame
POP_TOL = 0.35     # metres a body part may move in one frame (sprinting is ~0.1)
BOX_FACES = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]


def world_aabb(pts):
    xs, ys, zs = zip(*pts)
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def aabb_hit(a, b, pad=0.0):
    return all(a[0][i] - pad <= b[1][i] and b[0][i] - pad <= a[1][i] for i in range(3))


def root_of(ob):
    while ob.parent:
        ob = ob.parent
    return ob


def family(ob):
    r = root_of(ob)
    return {r.name} | {c.name for c in r.children_recursive}


def part_bvh(ob):
    """The part's box, shrunk a little, as a BVH in world space."""
    M = ob.matrix_world
    lo = V([min(v.co[i] for v in ob.data.vertices) for i in range(3)])
    hi = V([max(v.co[i] for v in ob.data.vertices) for i in range(3)])
    c, h = (lo + hi) / 2, (hi - lo) / 2
    s = V([max(0.0, h[i] - SHRINK / max(1e-6, ob.matrix_world.to_scale()[i])) for i in range(3)])
    corners = [M @ (c + V((sx * s.x, sy * s.y, sz * s.z))) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    return BVHTree.FromPolygons(corners, BOX_FACES), corners, M @ c


def mesh_bvh(ob, dg):
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    M = ob.matrix_world
    verts = [M @ v.co for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    if not polys:
        return None, None
    return BVHTree.FromPolygons(verts, polys), world_aabb(verts)


def inside(bvh, p):
    hit = bvh.find_nearest(p)
    if hit[0] is None:
        return False
    loc, nrm = hit[0], hit[1]
    return (p - loc).dot(nrm) < -SHRINK and (p - loc).length < 0.5


def check(path):
    bpy.ops.wm.open_mainfile(filepath=path)
    sc = bpy.context.scene
    rigs = [o for o in bpy.data.objects if o.get("rig")]
    parts = {r.name: [o for o in bpy.data.objects if o.type == "MESH" and o.get("part_of") == r.name] for r in rigs}
    ik = {r.name: {k: bpy.data.objects[f"{r.name}_ik_{w}.{k}"] for w in ("hand", "foot") for k in "LR"} for r in rigs}
    targets = {r.name: {(w, k): bpy.data.objects[f"{r.name}_ik_{w}.{k}"] for w in ("hand", "foot") for k in "LR"} for r in rigs}
    rig_stuff = set()
    for r in rigs:
        rig_stuff |= {o.name for o in bpy.data.objects if o.get("part_of") == r.name} | {r.name}
    # what each rig may touch: whatever its hand targets are parented to, and props hanging off its hands
    allowed = {}
    for r in rigs:
        al = set()
        for k in "LR":
            t = targets[r.name][("hand", k)]
            if t.parent:
                al |= family(t.parent)
            al |= {c.name for c in t.children_recursive}
        for nm in r.get("holds", []):  # props the hands hold by computed targets (not parented)
            if nm in bpy.data.objects:
                al |= family(bpy.data.objects[nm])
        allowed[r.name] = al
    obstacles = []
    for o in bpy.data.objects:
        if o.type != "MESH" or o.name in rig_stuff or o.hide_render:
            continue
        if any(o.name in al for al in allowed.values()) and False:
            continue
        obstacles.append(o)
    dg = bpy.context.evaluated_depsgraph_get()
    sc.frame_set(sc.frame_start)
    static, moving = {}, []
    first = {o.name: o.matrix_world.copy() for o in obstacles}
    sc.frame_set(sc.frame_end)
    for o in obstacles:
        if (o.matrix_world.translation - first[o.name].translation).length > 1e-4 or o.matrix_world != first[o.name]:
            moving.append(o)
    sc.frame_set(sc.frame_start)
    for o in obstacles:
        if o not in moving:
            b, bb = mesh_bvh(o, dg)
            if b:
                if bb[1][2] < 0.06 and max(bb[1][0] - bb[0][0], bb[1][1] - bb[0][1]) > 1.5:  # the floor: feet stand on it, checked separately
                    continue
                static[o.name] = (b, bb)
    rep = dict(ground=0.0, ground_at="", reach=0.0, reach_at="", foot=0.0, foot_at="", slide=0.0, slide_at="", pop=0.0, pop_at="",
               clip={}, people={})
    prev_part, prev_ank, prev_tgt = {}, {}, {}
    for f in range(sc.frame_start, sc.frame_end + 1):
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        dyn = {}
        for o in moving:
            b, bb = mesh_bvh(o, dg)
            if b:
                dyn[o.name] = (b, bb)
        obs = {**static, **dyn}
        pb_cache = {}
        for r in rigs:
            M = r.matrix_world
            for k in "LR":
                wr = M @ r.pose.bones["forearm." + k].tail
                e = (wr - targets[r.name][("hand", k)].matrix_world.translation).length
                if e > rep["reach"]:
                    rep["reach"], rep["reach_at"] = e, f"{r.name}.{k} f{f}"
                an = M @ r.pose.bones["shin." + k].tail
                tg = targets[r.name][("foot", k)].matrix_world.translation.copy()
                e = (an - tg).length
                if e > rep["foot"]:
                    rep["foot"], rep["foot_at"] = e, f"{r.name}.{k} f{f}"
                key = (r.name, k)
                if key in prev_tgt and (tg - prev_tgt[key]).length < 1e-5:  # planted this frame
                    d = (an - prev_ank[key]).length
                    if d > rep["slide"]:
                        rep["slide"], rep["slide_at"] = d, f"{r.name}.{k} f{f}"
                prev_tgt[key], prev_ank[key] = tg, an
            for p in parts[r.name]:
                bv, corners, c = part_bvh(p)
                bb = world_aabb(corners)
                pb_cache[p.name] = (r.name, bv, bb)
                if p.name in prev_part:
                    d = (c - prev_part[p.name]).length
                    if d > rep["pop"]:
                        rep["pop"], rep["pop_at"] = d, f"{p.name} f{f}"
                prev_part[p.name] = c
                zmin = min(v.z for v in corners) - SHRINK
                if zmin < -0.03 and -zmin > rep["ground"]:
                    rep["ground"], rep["ground_at"] = -zmin, f"{p.name} f{f}"
                for on, (ob_bvh, ob_bb) in obs.items():
                    if on in allowed[r.name] or not aabb_hit(bb, ob_bb):
                        continue
                    if ob_bvh.overlap(bv) or inside(ob_bvh, c):
                        k2 = f"{p.name} x {on}"
                        rep["clip"].setdefault(k2, []).append(f)
        names = list(pb_cache)
        for i, a in enumerate(names):  # character against character
            ra, ba, bba = pb_cache[a]
            for b in names[i + 1:]:
                rb, bb_, bbb = pb_cache[b]
                if ra != rb and aabb_hit(bba, bbb) and ba.overlap(bb_):
                    rep["people"].setdefault(f"{a} x {b}", []).append(f)
    return rep


def spans(fs):
    out, s, p = [], fs[0], fs[0]
    for f in fs[1:]:
        if f != p + 1:
            out.append(f"{s}-{p}" if s != p else str(s))
            s = f
        p = f
    out.append(f"{s}-{p}" if s != p else str(s))
    return ",".join(out)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [a for a in sys.argv[1:] if not a.endswith(".py")]
    d = argv[0]
    ids = [int(a) for a in argv[1:]] or sorted(int(f[1:3]) for f in os.listdir(d) if f.endswith(".blend"))
    allrep = {}
    for n in ids:
        rep = check(os.path.join(d, f"s{n:02d}.blend"))
        allrep[n] = rep
        bad = []
        if rep["reach"] > REACH_TOL:
            bad.append(f"reach {rep['reach']:.3f} @ {rep['reach_at']}")
        if rep["foot"] > REACH_TOL:
            bad.append(f"foot {rep['foot']:.3f} @ {rep['foot_at']}")
        if rep["slide"] > SLIDE_TOL:
            bad.append(f"slide {rep['slide']:.3f} @ {rep['slide_at']}")
        if rep["ground"] > 0:
            bad.append(f"below floor {rep['ground']:.3f} @ {rep['ground_at']}")
        if rep["pop"] > POP_TOL:
            bad.append(f"pop {rep['pop']:.2f} @ {rep['pop_at']}")
        print(f"s{n:02d} {'OK' if not (bad or rep['clip'] or rep['people']) else 'ISSUES'}", flush=True)
        for b in bad:
            print("   ", b)
        for k, fs in sorted(rep["clip"].items(), key=lambda kv: -len(kv[1]))[:12]:
            print(f"    clip {k}: {spans(fs)}")
        for k, fs in sorted(rep["people"].items(), key=lambda kv: -len(kv[1]))[:8]:
            print(f"    people {k}: {spans(fs)}")
    json.dump(allrep, open(os.path.join(d, "validate.json"), "w"), indent=1)
