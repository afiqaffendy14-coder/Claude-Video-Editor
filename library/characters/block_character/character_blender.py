"""Build the master block character in Blender: a rigged, skinned Minecraft-style person from template.py + a skin.

    import sys; sys.path.insert(0, r"<Claude-Video-Editor>/library/characters/block_character")
    import character_blender as ch
    p = ch.make_character("toto", skin="driver_silver_arrow", helmet=True, pose="idle", face="smile")
    p.location = (1, 0, 0)                 # the root is an armature object: move/turn it like any object
    ch.set_pose(p, "wave", frame=24)       # named pose or a dict of joint values (template.POSES), keyed
    ch.set_face(p, "grin", frame=30)       # expressions switch instantly (constant keys)
    ch.set_skin(p, "driver_rosso")         # same rig, new skin
    ch.ik_hand(p, "R", some_object)        # hand follows an object (IK, elbow pole kept down)
    ch.seat_in_car(p, car_root)            # driver pose at the car's seat, hands on the steering-wheel grips

One skin pixel = template.PX metres. Parts deform with the bones; elbows, knees and the waist bend over a
two-pixel band, like Mine-imator. Layer 2 (hair, collars, cuffs) is a slightly bigger shell with see-through
pixels, exactly like the game.
"""
import math
import os
import sys
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import template as T  # noqa: E402
import skins as SK  # noqa: E402

PX = T.PX
SKIN_DIR = os.path.join(HERE, "skins")
HELMET_DIR = os.path.join(HERE, "helmets")
N_FACES = len(T.EXPRESSIONS)


# ---------------------------------------------------------------- geometry
def _cuboid(box, uv, inflate, cuts, tex=64):
    """Quads for one cuboid in the Minecraft UV layout. Returns [(corners[4], uvs[4], z_of_corners)].
    Side faces are split at the z values in `cuts` so bends deform smoothly."""
    x0, x1, y0, y1, z0, z1 = box
    w, h, d = x1 - x0, z1 - z0, y1 - y0
    u, v = uv
    i = inflate
    X0, X1, Y0, Y1, Z0, Z1 = x0 - i, x1 + i, y0 - i, y1 + i, z0 - i, z1 + i
    zs = sorted({Z0, Z1, *[c for c in cuts if Z0 < c < Z1]})
    tvz = lambda z: v + d + (Z1 - z) / (Z1 - Z0) * h            # texture row for a height on a side face
    sides = {  # pos(s, z) across the face from its texture-left column; texture u0
        "front": (lambda s, z: (X1 - s * (X1 - X0), Y1, z), u + d, w),
        "back": (lambda s, z: (X0 + s * (X1 - X0), Y0, z), u + 2 * d + w, w),
        "right": (lambda s, z: (X1, Y0 + s * (Y1 - Y0), z), u, d),
        "left": (lambda s, z: (X0, Y1 - s * (Y1 - Y0), z), u + d + w, d),
    }
    out = []
    for name, (pos, tu0, tw) in sides.items():
        for za, zb in zip(zs[:-1], zs[1:]):
            q = [(0, za), (1, za), (1, zb), (0, zb)]
            out.append((name, [pos(s, z) for s, z in q], [(tu0 + s * tw, tvz(z)) for s, z in q]))
    top = lambda s, t: (X1 - s * (X1 - X0), Y0 + t * (Y1 - Y0), Z1)
    bot = lambda s, t: (X1 - s * (X1 - X0), Y1 - t * (Y1 - Y0), Z0)
    q = [(0, 0), (1, 0), (1, 1), (0, 1)]
    out.append(("top", [top(s, t) for s, t in q], [(u + d + s * w, v + t * d) for s, t in q]))
    out.append(("bottom", [bot(s, t) for s, t in q], [(u + d + w + s * w, v + t * d) for s, t in q]))
    # outward winding
    cen = Vector(((X0 + X1) / 2, (Y0 + Y1) / 2, (Z0 + Z1) / 2))
    fixed = []
    for name, cs, uvs in out:
        a, b, c = (Vector(p) for p in cs[:3])
        n = (b - a).cross(c - a)
        if n.dot(Vector(cs[0]) - cen) < 0:
            cs, uvs = cs[::-1], uvs[::-1]
        fixed.append((name, cs, [(tu / tex, 1 - tv / tex) for tu, tv in uvs]))
    return fixed


def _weights(part, z):
    """{bone: weight} for a point at height z (px) on a part."""
    if "bone" in part:
        return {part["bone"]: 1.0}
    j, above, below = part["bend"]
    lo = min(1.0, max(0.0, (j + T.BEND_BAND - z) / (2 * T.BEND_BAND)))
    return {k: w for k, w in ((above, 1 - lo), (below, lo)) if w > 1e-6}


def _mesh(name, model, layer, face_slot=False, only=None, inflate_extra=0.0, uv_override=None):
    P = T.parts(model)
    verts, faces, uvs, mats, groups = [], [], [], [], {}
    for pk, part in P.items():
        if only and pk not in only:
            continue
        uv = uv_override or (part["uv"] if layer == 1 else part["uv2"])
        infl = (0.0 if layer == 1 else part["inflate"]) + inflate_extra
        cuts = []
        if "bend" in part:
            j = part["bend"][0]
            n = T.BEND_RINGS
            cuts = [j - T.BEND_BAND + 2 * T.BEND_BAND * k / (n - 1) for k in range(n)]
        for fname, cs, fuv in _cuboid(part["box"], uv, infl, cuts):
            idx = []
            for c, t in zip(cs, fuv):
                vi = len(verts)
                verts.append(Vector(c) * PX)
                uvs.append(t)
                for b, w in _weights(part, c[2]).items():
                    groups.setdefault(b, []).append((vi, w))
                idx.append(vi)
            faces.append(idx)
            mats.append(1 if (face_slot and pk == "head" and fname == "front") else 0)
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    uvl = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            uvl.data[li].uv = uvs[me.loops[li].vertex_index]
        poly.use_smooth = False
    me.polygons.foreach_set("material_index", mats)
    if face_slot:  # the head-front face samples the expression atlas instead (tile 0 in u, full height)
        hp = P["head"]
        for poly in me.polygons:
            if poly.material_index != 1:
                continue
            for li in poly.loop_indices:
                x, y, z = verts[me.loops[li].vertex_index] / PX
                x0, x1 = hp["box"][0], hp["box"][1]
                z0, z1 = hp["box"][4], hp["box"][5]
                uvl.data[li].uv = ((x1 - x) / (x1 - x0) / N_FACES, (z - z0) / (z1 - z0))
    ob = bpy.data.objects.new(name, me)
    for b, lst in groups.items():
        vg = ob.vertex_groups.new(name=b)
        for vi, w in lst:
            vg.add([vi], w, "REPLACE")
    return ob


# ---------------------------------------------------------------- materials
def _image(path):
    return bpy.data.images.load(path, check_existing=True)


def _skin_material(name, img_path, alpha=False, rough=0.62, face_root=None, spec=0.35):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bs = nt.nodes["Principled BSDF"]
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = _image(img_path)
    tx.interpolation = "Closest"
    tx.extension = "CLIP" if face_root is None else "REPEAT"
    if face_root is not None:  # expression atlas: shift the UV one tile per face index
        uvn = nt.nodes.new("ShaderNodeUVMap")
        mp = nt.nodes.new("ShaderNodeMapping")
        nt.links.new(uvn.outputs["UV"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], tx.inputs["Vector"])
        fc = mp.inputs["Location"].driver_add("default_value", 0)
        drv = fc.driver
        drv.type = "SCRIPTED"
        var = drv.variables.new()
        var.name, var.type = "f", "SINGLE_PROP"
        var.targets[0].id_type = "OBJECT"
        var.targets[0].id = face_root
        var.targets[0].data_path = '["face"]'
        drv.expression = f"floor(f + 0.5) / {N_FACES}"
    nt.links.new(tx.outputs["Color"], bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = rough
    for k in ("Specular IOR Level", "Specular"):
        if k in bs.inputs:
            bs.inputs[k].default_value = spec
            break
    if alpha:
        gt = nt.nodes.new("ShaderNodeMath")
        gt.operation = "GREATER_THAN"
        gt.inputs[1].default_value = 0.5
        nt.links.new(tx.outputs["Alpha"], gt.inputs[0])
        nt.links.new(gt.outputs[0], bs.inputs["Alpha"])
        if hasattr(m, "surface_render_method"):
            m.surface_render_method = "DITHERED"
        if hasattr(m, "blend_method"):
            try:
                m.blend_method = "CLIP"
            except TypeError:
                pass
        m.use_backface_culling = False
    return m


def _skin_paths(skin):
    p = os.path.join(SKIN_DIR, skin + ".png")
    f = os.path.join(SKIN_DIR, skin + "_faces.png")
    if not os.path.exists(p):
        raise FileNotFoundError(f"no skin {p}: add it to skins.SKINS and run skins.py")
    return p, f


# ---------------------------------------------------------------- rig
def _armature(name, model, coll):
    arm = bpy.data.armatures.new(name + "_rig")
    arm.display_type = "STICK"
    ob = bpy.data.objects.new(name, arm)
    coll.objects.link(ob)
    vl = bpy.context.view_layer
    prev = vl.objects.active
    vl.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {}
    for b, (h, t, parent) in T.bones(model).items():
        e = arm.edit_bones.new(b)
        e.head, e.tail = Vector(h) * PX, Vector(t) * PX
        e.roll = 0.0
        e.use_deform = True
        eb[b] = e
    for b, (_, _, parent) in T.bones(model).items():
        if parent:
            eb[b].parent = eb[parent]
            eb[b].use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    vl.objects.active = prev
    for pb in ob.pose.bones:
        pb.rotation_mode = "QUATERNION"
    return ob


def make_character(name="person", skin="base", helmet=None, pose="stand", face="neutral", collection=None,
                   location=(0, 0, 0), rotation=0.0, layer2=True):
    """Build a character. helmet: None, True (the skin's team helmet) or a team name. Returns the root (armature)."""
    spec = SK.SKINS.get(skin, {})
    model = spec.get("model", "classic")
    if helmet is True:
        helmet = spec.get("helmet")
    coll = collection or bpy.data.collections.new(name)
    if coll.name not in bpy.context.scene.collection.children and collection is None:
        bpy.context.scene.collection.children.link(coll)
    root = _armature(name, model, coll)
    root["block_character"] = True
    root["skin"], root["model"], root["helmet"] = skin, model, helmet or ""
    root["face"] = 0
    root["faces"] = ",".join(T.EXPRESSIONS)
    root.id_properties_ui("face").update(min=0, max=N_FACES - 1, description=", ".join(T.EXPRESSIONS))
    p, f = _skin_paths(skin)
    parts = [(_mesh(name + "_body", model, 1, face_slot=True), [
        _skin_material(f"{name}_skin", p), _skin_material(f"{name}_face", f, face_root=root)])]
    if layer2:
        only = None if not helmet else [k for k in T.parts(model) if k != "head"]  # helmet replaces the hat layer
        parts.append((_mesh(name + "_layer2", model, 2, only=only), [_skin_material(f"{name}_skin2", p, alpha=True)]))
    if helmet:
        hp = os.path.join(HELMET_DIR, helmet + ".png")
        parts.append((_mesh(name + "_helmet", model, 2, only=["head"]),
                      [_skin_material(f"{name}_helmet", hp, alpha=True, rough=0.22, spec=0.6)]))
    for ob, mats in parts:
        for m in mats:
            ob.data.materials.append(m)
        coll.objects.link(ob)
        ob.parent = root
        mod = ob.modifiers.new("rig", "ARMATURE")
        mod.object = root
        mod.use_deform_preserve_volume = True
    root.location = location
    root.rotation_euler.z = math.radians(rotation)
    set_pose(root, pose)
    set_face(root, face)
    return root


def objects(root):
    return [c for c in root.children if c.type == "MESH"]


# ---------------------------------------------------------------- posing
def _char_rot(steps):
    R = Matrix.Identity(3)
    for axis, deg in steps:
        R = R @ Matrix.Rotation(math.radians(deg), 3, axis)
    return R


def pose_dict(pose):
    if isinstance(pose, str):
        return dict(T.POSES[pose])
    return dict(pose or {})


def set_pose(root, pose="stand", frame=None, blend=None):
    """Apply a named pose or a pose dict (template.POSES keys). blend=(other_pose, t) mixes two poses."""
    p = pose_dict(pose)
    if blend:
        q, t = pose_dict(blend[0]), blend[1]
        keys = set(p) | set(q)
        mix = {}
        for k in keys:
            a, b = p.get(k), q.get(k)
            if isinstance(a or b, (tuple, list)):
                n = len(a or b)
                a, b = tuple(a or (0,) * n), tuple(b or (0,) * n)
                mix[k] = tuple(x + (y - x) * t for x, y in zip(a, b))
            else:
                mix[k] = (a or 0) + ((b or 0) - (a or 0)) * t
        p = mix
    rots = T.joint_rotations(p)
    for pb in root.pose.bones:
        M = pb.bone.matrix_local.to_3x3()
        R = _char_rot(rots.get(pb.name, []))
        pb.rotation_quaternion = (M.inverted() @ R @ M).to_quaternion()
        pb.location = (0, 0, 0)
        if frame is not None:
            pb.keyframe_insert("rotation_quaternion", frame=frame)
    hips = root.pose.bones["hips"]
    drop = p.get("crouch", 0.0)
    # bone-local translation: hips points up, so local Y is world Z at rest
    hips.location = hips.bone.matrix_local.to_3x3().inverted() @ Vector((0, 0, -drop))
    if frame is not None:
        hips.keyframe_insert("location", frame=frame)
    root["pose"] = pose if isinstance(pose, str) else "custom"


def set_face(root, face="neutral", frame=None):
    root["face"] = T.EXPRESSIONS.index(face) if isinstance(face, str) else int(face)
    if frame is not None:
        root.keyframe_insert('["face"]', frame=frame)
        fc = root.animation_data.action.fcurves.find('["face"]') if hasattr(root.animation_data.action, "fcurves") else None
        for k in (fc.keyframe_points if fc else []):
            k.interpolation = "CONSTANT"
    root.update_tag()


def set_skin(root, skin):
    """Swap the skin (and its faces) on an existing character. Classic/slim must match the rig it was built with."""
    p, f = _skin_paths(skin)
    nm = root.name
    for ob in objects(root):
        for m in ob.data.materials:
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE" and not m.name.startswith(nm + "_helmet"):
                    n.image = _image(f if m.name.startswith(nm + "_face") else p)
    root["skin"] = skin


def ik_hand(root, side, target, pole=None, influence=1.0, pole_angle=-90.0):
    """Put a hand (forearm tail = hand centre) on `target` (an object). The pole keeps the elbow down and out."""
    pb = root.pose.bones[f"forearm.{side}"]
    c = pb.constraints.new("IK")
    c.target = target
    c.chain_count = 2
    c.influence = influence
    if pole is None:
        pole = bpy.data.objects.new(f"{root.name}_elbow_pole.{side}", None)
        pole.empty_display_size = 0.05
        for coll in root.users_collection:
            coll.objects.link(pole)
        s = 1 if side == "R" else -1
        pole.parent = root
        pole.location = (s * 0.55, -0.15, 0.55)
    c.pole_target = pole
    c.pole_angle = math.radians(pole_angle)
    return c


def _vehicle_blueprint(car_root):
    """The blueprint module of a library vehicle (F1 car or kart), loaded by path (both folders sit side by side)."""
    import importlib.util
    kart = car_root.get("vehicle") == "kart"
    path = os.path.join(HERE, "..", "..", "cars", *(("kart", "kart_blueprint.py") if kart else
                                                   ("f1_2026", "blueprint.py")))
    key = "vehicle_bp_kart" if kart else "vehicle_bp_f1"
    if key not in sys.modules:
        spec = importlib.util.spec_from_file_location(key, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules[key] = mod
    return sys.modules[key]


def seat_in_car(root, car_root, skin_pose=None):
    """Seat the character in a library vehicle (an F1 car from library/cars/f1_2026 or a kart from
    library/cars/kart) with its hands on the steering-wheel grips. The vehicle's blueprint.SEAT gives the neck
    point, the grips, the pose (F1: "driver", kart: "kart") and the elbow poles. The grips are parented to the
    steering wheel, so the hands follow root['steer']."""
    bp = _vehicle_blueprint(car_root)
    skin_pose = skin_pose or bp.SEAT.get("pose", "driver")
    poles = bp.SEAT.get("poles")
    bpy.context.view_layer.update()
    set_pose(root, skin_pose)
    p = pose_dict(skin_pose)
    lean = math.radians(-p.get("lean", 0.0))          # recline angle about +X
    neck_rest = Vector((0, 0, 24 * PX))
    hip = Vector((0, 0, 12 * PX))
    R = Matrix.Rotation(lean, 3, "X")
    neck_posed = hip + R @ (neck_rest - hip)
    root.parent = car_root
    root.matrix_parent_inverse.identity()
    root.location = Vector(bp.SEAT["neck"]) - neck_posed
    root.rotation_euler = (0, 0, 0)
    wheel = next((o for o in car_root.children_recursive if "steering_wheel" in o.name), None)
    for side, grip in (("L", bp.SEAT["grips"][0]), ("R", bp.SEAT["grips"][1])):
        t = bpy.data.objects.new(f"{root.name}_grip.{side}", None)
        t.empty_display_size = 0.03
        for coll in root.users_collection:
            coll.objects.link(t)
        if wheel is not None:
            t.parent = wheel
            t.matrix_parent_inverse.identity()
            t.location = wheel.matrix_world.inverted() @ (car_root.matrix_world @ Vector(grip))
        else:
            t.parent = car_root
            t.location = grip
        pole = bpy.data.objects.new(f"{root.name}_elbow_pole.{side}", None)
        for coll in root.users_collection:
            coll.objects.link(pole)
        pole.parent = car_root
        s = 1 if side == "R" else -1
        pole.location = poles[0 if side == "L" else 1] if poles else (s * 0.24, 0.22, 0.05)
        ik_hand(root, side, t, pole, pole_angle=bp.SEAT.get("pole_angle", -90.0))
    return root
