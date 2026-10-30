"""Blocky (voxel) look: block people, a world-aligned voxel grid for every curved prop, pixel-noise textures.

Turn it on with lib.STYLE["voxel"] = True before building a set, then call voxelize_scene() after building.
Boxes stay boxes (they already read as blocks) and get the pixel texture; every other mesh or curve
(car body, wheels, cot, monitors, tubes) is rebuilt as cubes on one world grid of size PX, so block size
is the same everywhere in the frame.
"""
import math
import random
import bpy
import bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
import lib
from lib import V, link, box, palette, mat

PX = 0.045  # one "pixel" / block edge in metres: an 8-pixel head is 0.36 m


# ---------------------------------------------------------------- pixel textures
def noise_image(name="px_noise", size=64, seed=7):
    """Fine pixel noise for people and props: one texel per block."""
    img = bpy.data.images.get(name)
    if img:
        return img
    img = bpy.data.images.new(name, size, size, alpha=False)
    rnd = random.Random(seed)
    px = []
    for _ in range(size * size):
        v = 0.93 + 0.07 * rnd.random()
        if rnd.random() < 0.05:
            v -= 0.05
        px += [v, v, v, 1.0]
    img.pixels = px
    img.pack()
    return img


def tile_image(name="px_tile", size=16, seed=3):
    """One 1 m building block: 16 x 16 texels, soft noise, a slightly darker one-texel edge."""
    img = bpy.data.images.get(name)
    if img:
        return img
    img = bpy.data.images.new(name, size, size, alpha=False)
    rnd = random.Random(seed)
    px = []
    for y in range(size):
        for x in range(size):
            v = 0.94 + 0.06 * rnd.random()
            if x == 0 or y == 0:
                v -= 0.1
            elif x == size - 1 or y == size - 1:
                v -= 0.04
            px += [v, v, v, 1.0]
    img.pixels = px
    img.pack()
    return img


def px_material(m, kind="fine"):
    """Same material, base colour multiplied by a pixel texture (closest-pixel sampling, box projection).
    kind 'fine': one texel per block (people, props). kind 'tile': 1 m building blocks (floors, walls)."""
    if m is None or m.name.startswith("px_"):
        return m
    name = f"px_{kind}_" + m.name
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    b0 = m.node_tree.nodes.get("Principled BSDF")
    if b0 is None or b0.inputs["Emission Strength"].default_value > 0:
        return m  # lights and screens keep their clean glow
    pm = m.copy()
    pm.name = name
    nt = pm.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    s = 1.0 / (64 * PX) if kind == "fine" else 1.0
    mp.inputs["Scale"].default_value = (s, s, s)
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = noise_image() if kind == "fine" else tile_image()
    tx.interpolation = "Closest"
    tx.projection = "BOX"
    tx.projection_blend = 0.0
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    mix.inputs["A"].default_value = b.inputs["Base Color"].default_value
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], tx.inputs["Vector"])
    nt.links.new(tx.outputs["Color"], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return pm


# ---------------------------------------------------------------- voxelizer
def _is_box(ob):
    return ob.type == "MESH" and len(ob.data.vertices) == 8 and len(ob.data.polygons) == 6


def voxelize_object(ob, b=PX):
    """Rebuild one object as world-aligned cubes of edge b (a shell of cells within ~half a block of its surface)."""
    deps = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(deps)
    try:
        me = ev.to_mesh()
    except RuntimeError:
        return None
    mw = ob.matrix_world.copy()
    verts = [mw @ v.co for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    pmat = [p.material_index for p in me.polygons]
    ev.to_mesh_clear()
    if not polys:
        return None
    bvh = BVHTree.FromPolygons(verts, polys, all_triangles=False)
    lo = Vector((min(v.x for v in verts), min(v.y for v in verts), min(v.z for v in verts)))
    hi = Vector((max(v.x for v in verts), max(v.y for v in verts), max(v.z for v in verts)))
    i0 = [math.floor(lo[k] / b) - 1 for k in range(3)]
    i1 = [math.floor(hi[k] / b) + 1 for k in range(3)]
    cells = {}
    lim = 0.62 * b
    for i in range(i0[0], i1[0] + 1):
        for j in range(i0[1], i1[1] + 1):
            for k in range(i0[2], i1[2] + 1):
                c = Vector(((i + 0.5) * b, (j + 0.5) * b, (k + 0.5) * b))
                hit = bvh.find_nearest(c, lim)
                if hit[0] is not None:
                    cells[(i, j, k)] = pmat[hit[2]]
    if not cells:
        return None
    bm = bmesh.new()
    vcache = {}

    def vert(x, y, z):
        key = (x, y, z)
        if key not in vcache:
            vcache[key] = bm.verts.new((x * b, y * b, z * b))
        return vcache[key]

    dirs = [((1, 0, 0), [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)]),
            ((-1, 0, 0), [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)]),
            ((0, 1, 0), [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)]),
            ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
            ((0, 0, 1), [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]),
            ((0, 0, -1), [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)])]
    for (i, j, k), mi in cells.items():
        for d, quad in dirs:
            if (i + d[0], j + d[1], k + d[2]) in cells:
                continue
            f = bm.faces.new([vert(i + q[0], j + q[1], k + q[2]) for q in quad])
            f.material_index = mi
    me2 = bpy.data.meshes.new(ob.name + "_vox")
    bm.to_mesh(me2)
    bm.free()
    vo = link(bpy.data.objects.new(ob.name + "_vox", me2))
    for slot in ob.material_slots:
        me2.materials.append(px_material(slot.material))
    if not ob.material_slots:
        me2.materials.append(px_material(palette()["clay"]))
    for p in me2.polygons:
        p.use_smooth = False
    return vo


def _under_person(ob):
    while ob:
        if ob.get("person"):
            return True
        ob = ob.parent
    return False


def voxelize_scene(b=PX):
    """Boxes: drop bevels, add pixel texture. Everything else: rebuild as voxels and delete the original."""
    todo = []
    for ob in list(bpy.data.objects):
        if ob.type not in ("MESH", "CURVE"):
            continue
        if _is_box(ob) or _under_person(ob):
            for m in list(ob.modifiers):
                if m.type == "BEVEL":
                    ob.modifiers.remove(m)
            for p in ob.data.polygons:
                p.use_smooth = False
            kind = "tile" if (not _under_person(ob) and max(ob.dimensions) > 1.5) else "fine"
            for slot in ob.material_slots:
                slot.material = px_material(slot.material, kind)
            continue
        if ob.type == "MESH" and max(ob.dimensions) > 20:  # backdrops: texture only
            for slot in ob.material_slots:
                slot.material = px_material(slot.material, "tile")
            continue
        todo.append(ob)
    bpy.context.view_layer.update()
    for ob in todo:
        voxelize_object(ob, b)
    for ob in todo:
        bpy.data.objects.remove(ob, do_unlink=True)


# ---------------------------------------------------------------- block people
R = lambda axis, deg: Matrix.Rotation(math.radians(deg), 3, axis)
STAND = dict(crouch=0, lean=0, twist=0, head=(0, 0), armL=(0, 6, 0), armR=(0, 6, 0), legL=(0, 2, 0), legR=(0, 2, 0))


def _seg(name, a, frame, length, t, material, start_ext=0.0):
    """A limb block running from a along the frame's -Z for `length`, cross-section t x t."""
    ob = box(name, (t, t, length + start_ext), (0, 0, 0), material)
    c = a + frame @ V((0, 0, -(length - start_ext) / 2))
    ob.matrix_world = Matrix.Translation(c) @ frame.to_4x4()
    return ob


def _boxat(name, size, frame, origin, offset, material):
    ob = box(name, size, (0, 0, 0), material)
    ob.matrix_world = Matrix.Translation(origin + frame @ V(offset)) @ frame.to_4x4()
    return ob


def block_person(name, loc=(0, 0, 0), rot=0.0, pose=None, outfit="surgeon", scale=1.0, parent=None):
    from people import OUTFITS
    M = palette()
    o = OUTFITS[outfit]
    p = {**STAND, **(pose or {})}
    P_ = PX
    W, H, D = 9 * P_, 12 * P_, 5 * P_
    T = R("Z", p["twist"]) @ R("X", -p["lean"])
    Th = R("Z", p["twist"] * 0.3)
    leg_len = 9 * P_ + 8 * P_ + 2 * P_
    pelvis = V((0, 0, leg_len - p["crouch"]))
    parts = []
    up, lo_, skin = M[o["upper"]], M[o["lower"]], M["skin"]
    # torso
    parts.append(_boxat(name + "_torso", (W, D, H), T, pelvis, (0, 0, H / 2), up))
    if o["upper"] != o["lower"]:
        parts.append(_boxat(name + "_belt", (W + 0.004, D + 0.004, 2 * P_), T, pelvis, (0, 0, P_), lo_))
    # head
    Hr = T @ R("Z", p["head"][0]) @ R("X", -p["head"][1])
    neck = pelvis + T @ V((0, 0, H))
    hs = 8 * P_
    headwear_skin = not o.get("helmet")
    parts.append(_boxat(name + "_head", (hs, hs, hs), Hr, neck, (0, 0, hs / 2), skin))
    fz = hs / 2 + 0.003  # front face
    if o.get("helmet"):
        parts.append(_boxat(name + "_helmet", (hs + 2 * P_ * 0.5, hs + P_, hs + P_ * 0.5), Hr, neck, (0, -P_ * 0.25, hs / 2 + P_ * 0.2), M["red"]))
        parts.append(_boxat(name + "_visor", (6 * P_, 0.02, 2 * P_), Hr, neck, (0, hs / 2 + P_ * 0.5, hs / 2 + P_ * 0.5), M["dark"]))
        parts.append(_boxat(name + "_stripe", (hs + P_ + 0.006, P_ * 2, P_ * 0.6), Hr, neck, (0, 0, hs + P_ * 0.2), M["white"]))
    else:
        for s in (1, -1):  # eyes: one dark pixel each with a white pixel inside
            parts.append(_boxat(name + f"_eye{s}", (P_, 0.01, P_), Hr, neck, (s * 1.5 * P_, fz, hs / 2 + 0.5 * P_), M["dark"]))
            parts.append(_boxat(name + f"_eyew{s}", (P_, 0.01, P_), Hr, neck, (s * 2.5 * P_, fz, hs / 2 + 0.5 * P_), M["white"]))
        if o.get("mask"):
            parts.append(_boxat(name + "_mask", (6 * P_, 0.02, 3 * P_), Hr, neck, (0, fz, hs / 2 - 2 * P_), M["white"]))
            for s in (1, -1):
                parts.append(_boxat(name + f"_strap{s}", (0.01, hs * 0.6, P_ * 0.5), Hr, neck, (s * (hs / 2 + 0.003), 0.04, hs / 2 - 1.5 * P_), M["white"]))
        else:
            parts.append(_boxat(name + "_mouth", (3 * P_, 0.01, P_ * 0.6), Hr, neck, (0, fz, hs / 2 - 2 * P_), mat("mouth", (0.42, 0.22, 0.18), 0.6)))
        if o.get("cap"):
            parts.append(_boxat(name + "_cap", (hs + 0.012, hs + 0.012, 2.5 * P_), Hr, neck, (0, 0, hs - 1.0 * P_), M[o["cap"]]))
        if o.get("hair"):
            parts.append(_boxat(name + "_hair", (hs + 0.012, hs + 0.012, 1.6 * P_), Hr, neck, (0, 0, hs - 0.6 * P_), M["grey"]))
            parts.append(_boxat(name + "_hairb", (hs + 0.012, P_, hs * 0.6), Hr, neck, (0, -hs / 2, hs * 0.65), M["grey"]))
    # arms: upper, fore, hand (2-pixel cuff in glove/skin colour)
    t = 4 * P_
    for s, k in ((1, "L"), (-1, "R")):
        fwd, side, elbow = p["arm" + k]
        sh = pelvis + T @ V((s * (W / 2 + t / 2), 0, H - t / 2))
        Ra = T @ R("X", fwd) @ R("Y", -s * side)
        parts.append(_seg(name + "_ua" + k, sh, Ra, 6 * P_, t, up, start_ext=t / 2))
        el = sh + Ra @ V((0, 0, -6 * P_))
        Rf = Ra @ R("X", elbow)
        parts.append(_seg(name + "_fa" + k, el, Rf, 4 * P_, t * 0.96, up))
        wr = el + Rf @ V((0, 0, -4 * P_))
        parts.append(_seg(name + "_hand" + k, wr, Rf, 2.2 * P_, t * 0.92, M[o["hands"]]))
        # legs: thigh, shin, shoe
        lf, lside, knee = p["leg" + k]
        hp = pelvis + Th @ V((s * W / 4, 0, 0))
        Rl = Th @ R("X", lf) @ R("Y", -s * lside)
        parts.append(_seg(name + "_th" + k, hp, Rl, 9 * P_, t * 1.05, lo_))
        kn = hp + Rl @ V((0, 0, -9 * P_))
        Rs = Rl @ R("X", -knee)
        parts.append(_seg(name + "_sh" + k, kn, Rs, 8 * P_, t, lo_))
        an = kn + Rs @ V((0, 0, -8 * P_))
        yaw = Th
        parts.append(_boxat(name + "_shoe" + k, (t * 1.05, 6 * P_, 2 * P_), yaw, an, (0, P_, -P_), M[o["shoes"]]))
    root = link(bpy.data.objects.new(name, None))
    root["person"] = True
    for q in parts:
        q.parent = root
    root.location = loc
    root.rotation_euler = (0, 0, math.radians(rot))
    root.scale = (scale, scale, scale)
    if parent:
        root.parent = parent
    return root
