"""Clay mannequin people: a posed skeleton skinned with Blender's Skin modifier, smoothed, then dressed.

pose = dict(crouch, lean, twist, head=(yaw, pitch), armL/armR=(fwd, side, elbow), legL/legR=(fwd, side, knee))
Angles in degrees. The person faces +Y in its own frame; +X is the person's left.
"""
import math
from mathutils import Vector, Matrix
import bpy
from lib import V, link, mesh_obj, sphere, box, subsurf, smooth, cyl, palette, loft, superellipse

R = lambda axis, deg: Matrix.Rotation(math.radians(deg), 3, axis)

OUTFITS = {
    # upper body, lower body, head wear, hands, shoes
    "surgeon": dict(upper="gown", lower="gown", cap="gown", mask=True, hands="glove", shoes="white"),
    "scrubs": dict(upper="scrubs", lower="scrubs", cap="scrubs", mask=False, hands="skin", shoes="white"),
    "doctor": dict(upper="scrubs", lower="scrubs", cap=None, mask=False, hands="skin", shoes="grey", hair=True),
    "crew": dict(upper="redm", lower="redm", helmet=True, hands="dark", shoes="dark"),
    "engineer": dict(upper="redm", lower="dark", cap=None, mask=False, hands="skin", shoes="dark", hair=True),
    "suit": dict(upper="grey", lower="grey", cap=None, mask=False, hands="skin", shoes="dark", hair=True),
}

STAND = dict(crouch=0, lean=0, twist=0, head=(0, 0), armL=(0, 8, 8), armR=(0, 8, 8), legL=(0, 3, 0), legR=(0, 3, 0))


def joints(pose):
    p = {**STAND, **pose}
    T = R("Z", p["twist"]) @ R("X", -p["lean"])
    Th = R("Z", p["twist"] * 0.3)
    P = V((0, 0, 0.95 - p["crouch"]))
    J = {"pelvis": P, "waist": P + T @ V((0, 0, 0.2)), "chest": P + T @ V((0, 0, 0.4)),
         "neck": P + T @ V((0, 0, 0.56))}
    H = T @ R("Z", p["head"][0]) @ R("X", -p["head"][1])
    J["head"] = J["neck"] + H @ V((0, 0.012, 0.14))
    J["Hrot"] = H
    J["T"] = T
    for s, k in ((1, "L"), (-1, "R")):
        fwd, side, elbow = p["arm" + k]
        sh = J["chest"] + T @ V((s * 0.175, -0.005, 0.07))
        Ra = T @ R("X", fwd) @ R("Y", -s * side)
        el = sh + Ra @ V((0, 0, -0.29))
        Rf = Ra @ R("X", elbow)
        wr = el + Rf @ V((0, 0, -0.25))
        J["sh" + k], J["el" + k], J["wr" + k], J["Rf" + k] = sh, el, wr, Rf
        lf, lside, knee = p["leg" + k]
        hp = P + Th @ V((s * 0.095, 0, -0.03))
        Rl = Th @ R("X", lf) @ R("Y", -s * lside)
        kn = hp + Rl @ V((0, 0, -0.45))
        Rs = Rl @ R("X", -knee)
        an = kn + Rs @ V((0, 0, -0.43))
        J["hp" + k], J["kn" + k], J["an" + k], J["Rs" + k], J["Rl" + k] = hp, kn, an, Rs, Rl
    J["Th"] = Th
    return J


def skin_obj(name, pts, edges, radii, material):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in pts], edges, [])
    ob = link(bpy.data.objects.new(name, me))
    ob.modifiers.new("skin", "SKIN")
    for i, r in enumerate(radii):
        ob.data.skin_vertices[""].data[i].radius = (r, r)
    ob.data.skin_vertices[""].data[0].use_root = True
    subsurf(ob, 2)
    me.materials.append(material)
    smooth(ob)
    return ob


def oriented(ob, rot3, loc):
    S = Matrix.Diagonal((*ob.scale, 1.0))
    ob.matrix_world = Matrix.Translation(loc) @ rot3.to_4x4() @ S
    return ob


def person(name, loc=(0, 0, 0), rot=0.0, pose=None, outfit="surgeon", scale=1.0, parent=None):
    """Build a dressed mannequin; returns the root empty (place/rotate that)."""
    import lib
    if lib.STYLE.get("voxel"):
        from voxel import block_person
        return block_person(name, loc, rot, pose, outfit, scale, parent)
    M = palette()
    o = OUTFITS[outfit]
    J = joints(pose or {})
    parts = []
    # torso: two lofted shells (rounded sections along the spine), lean blends in from the hips up
    def torso_ring(z, w, d):
        f = max(0.0, min(1.0, z / 0.36))
        Rz = J["Th"].to_quaternion().slerp(J["T"].to_quaternion(), f).to_matrix()
        c = J["pelvis"] + Rz @ V((0, 0, z))
        return [c + Rz @ p for p in superellipse(0, 0, 0, w, d, 20, 2.6, "XY")]
    lower_secs = [(-0.13, 0.07, 0.06), (-0.08, 0.15, 0.1), (0.0, 0.17, 0.11), (0.1, 0.155, 0.1), (0.17, 0.15, 0.098)]
    upper_secs = [(0.14, 0.152, 0.1), (0.24, 0.16, 0.105), (0.34, 0.185, 0.115), (0.43, 0.195, 0.11),
                  (0.5, 0.16, 0.09), (0.545, 0.08, 0.06)]
    if o["lower"] == o["upper"]:  # one garment: a single seamless shell
        secs = lower_secs[:-1] + upper_secs[1:]
        torsos = [loft(name + "_torso", [torso_ring(*x) for x in secs], M[o["upper"]])]
    else:
        torsos = [loft(name + "_torsoLo", [torso_ring(*x) for x in lower_secs], M[o["lower"]]),
                  loft(name + "_torsoUp", [torso_ring(*x) for x in upper_secs], M[o["upper"]])]
    for t_ in torsos:
        subsurf(t_, 2)
    parts += torsos
    # limbs: skin-modifier chains rooted at the shoulder / hip
    for k in "LR":
        parts.append(skin_obj(name + "_arm" + k, [J["sh" + k], J["el" + k], J["wr" + k]], [(0, 1), (1, 2)],
                              [0.064, 0.05, 0.038], M[o["upper"]]))
        parts.append(skin_obj(name + "_leg" + k, [J["hp" + k], J["kn" + k], J["an" + k]], [(0, 1), (1, 2)],
                              [0.098, 0.068, 0.05], M[o["lower"]]))
    # neck + head
    nk = cyl(name + "_neck", 0.045, 0.12, material=M["skin"], seg=16)
    oriented(nk, J["Hrot"], J["neck"] + J["Hrot"] @ V((0, 0, 0.04)))
    parts.append(nk)
    H = J["Hrot"]
    head = sphere(name + "_head", 1, material=M["skin"])
    head.scale = (0.088, 0.1, 0.115)
    oriented(head, H, J["head"])
    parts.append(head)
    if o.get("helmet"):
        hel = sphere(name + "_helmet", 1, material=M["red"])
        hel.scale = (0.14, 0.15, 0.15)
        oriented(hel, H, J["head"] + H @ V((0, -0.005, 0.01)))
        vis = sphere(name + "_visor", 1, material=M["dark"])
        vis.scale = (0.118, 0.1, 0.05)
        oriented(vis, H, J["head"] + H @ V((0, 0.062, 0.02)))
        chin = sphere(name + "_chin", 1, material=M["red"])
        chin.scale = (0.11, 0.1, 0.06)
        oriented(chin, H, J["head"] + H @ V((0, 0.05, -0.07)))
        parts += [hel, vis, chin]
    else:
        if o.get("cap"):
            cap = sphere(name + "_cap", 1, material=M[o["cap"]])
            cap.scale = (0.097, 0.108, 0.085)
            oriented(cap, H, J["head"] + H @ V((0, -0.008, 0.045)))
            parts.append(cap)
        if o.get("hair"):
            hair = sphere(name + "_hair", 1, material=M["grey"])
            hair.scale = (0.094, 0.104, 0.09)
            oriented(hair, H, J["head"] + H @ V((0, -0.016, 0.035)))
            parts.append(hair)
        if o.get("mask"):
            mk = sphere(name + "_mask", 1, material=M["white"])
            mk.scale = (0.075, 0.05, 0.05)
            oriented(mk, H, J["head"] + H @ V((0, 0.07, -0.035)))
            parts.append(mk)
        # a hint of a nose so the head reads as a face, not an egg
        nose = sphere(name + "_nose", 1, material=M["skin"])
        nose.scale = (0.016, 0.02, 0.026)
        oriented(nose, H, J["head"] + H @ V((0, 0.098, 0.0)))
        parts.append(nose)
    # hands: mitten + thumb, along the forearm
    for k in "LR":
        Rf = J["Rf" + k]
        hd = sphere(name + "_hand" + k, 1, material=M[o["hands"]])
        hd.scale = (0.026, 0.04, 0.064)
        oriented(hd, Rf, J["wr" + k] + Rf @ V((0, 0.005, -0.048)))
        th = sphere(name + "_thumb" + k, 1, material=M[o["hands"]])
        th.scale = (0.014, 0.014, 0.03)
        oriented(th, Rf, J["wr" + k] + Rf @ V((0, 0.03, -0.03)))
        parts += [hd, th]
        # shoes: follow the shin's heading but stay flat-ish
        Rs = J["Rs" + k]
        yaw = math.atan2(-(J["Th"] @ V((0, 1, 0))).x, (J["Th"] @ V((0, 1, 0))).y)
        heading = Matrix.Rotation(yaw, 3, "Z")
        tilt = Rs @ V((0, 0, -1))
        sh = sphere(name + "_shoe" + k, 1, material=M[o["shoes"]])
        sh.scale = (0.056, 0.14, 0.052)
        oriented(sh, heading, J["an" + k] + heading @ V((0, 0.05, -0.04)))
        parts.append(sh)
    root = link(bpy.data.objects.new(name, None))
    for p_ in parts:
        p_.parent = root
    root.location = loc
    root.rotation_euler = (0, 0, math.radians(rot))
    root.scale = (scale, scale, scale)
    if parent:
        root.parent = parent
    return root
