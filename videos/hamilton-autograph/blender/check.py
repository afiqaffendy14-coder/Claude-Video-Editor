"""Collision check for one built storyboard frame (static scene), with the same rules as validate.py:
every body part of every block person against the set, the props, the cars (halo tubes included) and the other
people. Touching is fine (parts are shrunk by validate.SHRINK); overlapping is a clip. A person may overlap only what
they hold (scene "holds") and the floor they stand on. Also reports feet floating above / sunk below what they stand on.
"""
import json
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from validate import part_bvh, mesh_bvh, inside, aabb_hit, world_aabb, family, SHRINK

V = Vector


def people():
    return [o for o in bpy.data.objects if o.get("person") and o.parent is None]


def check_scene(extra_allowed=None):
    """Returns a list of 'part x object' clips and a list of foot problems."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    roots = people()
    person_stuff = set()
    for r in roots:
        person_stuff |= family(r)
    holds = json.loads(bpy.context.scene.get("holds", "[]"))
    allowed = {r.name: set() for r in roots}
    for h in holds:
        if h["person"] in allowed and h["obj"] in bpy.data.objects:
            allowed[h["person"]] |= family(bpy.data.objects[h["obj"]])
    for pname, objs in (extra_allowed or {}).items():
        for on in objs:
            if on in bpy.data.objects and pname in allowed:
                allowed[pname] |= family(bpy.data.objects[on])
    obstacles = {}
    for o in bpy.data.objects:
        if o.type not in ("MESH", "CURVE") or o.name in person_stuff or o.hide_render:
            continue
        b, bb = mesh_bvh(o, dg)
        if not b:
            continue
        flat_floor = bb[1][2] - bb[0][2] < 0.3 and max(bb[1][0] - bb[0][0], bb[1][1] - bb[0][1]) > 1.5
        obstacles[o.name] = (b, bb, flat_floor)
    clips, feet, parts_all = [], [], {}
    for r in roots:
        parts = [o for o in r.children_recursive if o.type == "MESH"]
        for p in parts:
            bv, corners, c = part_bvh(p)
            bb = world_aabb(corners)
            parts_all[p.name] = (r.name, bv, bb)
            for on, (ob_bvh, ob_bb, flat) in obstacles.items():
                if on in allowed[r.name] or not aabb_hit(bb, ob_bb):
                    continue
                if flat and "shoe" in p.name:
                    continue  # feet stand on floors; height checked below
                if ob_bvh.overlap(bv) or inside(ob_bvh, c):
                    clips.append(f"{p.name} x {on}")
        for k in "LR":  # each shoe should rest on something: the floor or a surface right under it
            shoe = bpy.data.objects.get(f"{r.name}_shoe{k}")
            if not shoe:
                continue
            _, corners, c = part_bvh(shoe)
            zmin = min(v.z for v in corners) - SHRINK
            hit_below = None
            for on, (ob_bvh, ob_bb, flat) in obstacles.items():
                if on in allowed[r.name]:
                    continue
                h = ob_bvh.ray_cast(V((c.x, c.y, zmin + 0.02)), V((0, 0, -1)), 3.0)
                if h[0] is not None and (hit_below is None or h[0].z > hit_below):
                    hit_below = h[0].z
            ground = max(0.0, hit_below) if hit_below is not None else 0.0
            gap = zmin - ground
            if r.get("airborne") or k in str(r.get("foot_free", "")):
                continue
            if gap > 0.03 or gap < -0.03:
                feet.append(f"{shoe.name}: {gap:+.2f} m from the surface below")
    names = list(parts_all)
    for i, a in enumerate(names):
        ra, ba, bba = parts_all[a]
        for b in names[i + 1:]:
            rb, bb_, bbb = parts_all[b]
            if b in allowed.get(ra, ()) or a in allowed.get(rb, ()):
                continue  # registered contact between two people (a handshake, a hand on a shoulder)
            if ra != rb and aabb_hit(bba, bbb) and ba.overlap(bb_):
                clips.append(f"{a} x {b}")
    return clips, feet
