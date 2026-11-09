"""Blueprint -> rigged Blender go-kart. Use load_kart() in shots; it appends the saved .blend (fast) or builds it.

    import sys; sys.path.insert(0, "<repo>/library/cars/kart")
    import kart_blender as kart
    root = kart.load_kart("k1", livery="papaya")        # silver_arrow, rosso, papaya, midnight
    root.location = (0, 3, 0)
    root["steer"] = 15            # front-wheel degrees, + = turn left; front wheels and steering wheel follow
    kart.bake_roll(root, 1, 120)  # after animating root's motion: wheels roll with the distance travelled

Hierarchy (collection "Kart_<livery>", marked as an asset in its .blend):
  <root> empty, origin on the ground halfway along the wheelbase, +Y forward. Props: steer (deg), distance (m)
    body, rear_bumper (separate, so a shot can knock it off)
    column (empty on the steering column axis) -> steering_wheel (turns about the column with steer)
    steer_FL / steer_FR (kingpins, turn with steer) -> spindle_FL, wheel_FL (spins) -> tyre_FL, rim_FL
    rear_axle (spins: axle, hubs, sprocket, brake disc) -> wheel_RL / wheel_RR -> tyre_RL, rim_RL ...
No driver: seat the master block character with character_blender.seat_in_car(person, root).
"""
import math
import os
import sys
import numpy as np
import bpy
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import kart_blueprint as bp  # noqa: E402

BLEND_DIR = os.path.join(HERE, "blend")
STEER_RATIO = 2.6                       # steering-wheel degrees per front-wheel degree (karts are direct)
COLUMN = Matrix(((1, 0, 0), tuple(bp.WHEEL_UP), tuple(-bp.COL_DIR))).transposed()   # local Z = column, to driver


def _material(mid, prefix, livery="silver_arrow", condition="new"):
    d = bp.mat_spec(mid, livery, condition)
    name = f"{prefix}{d['name']}"
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    att = nt.nodes.new("ShaderNodeAttribute")
    att.attribute_name = "Col"
    att.location = (-400, 200)
    nt.links.new(att.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Metallic"].default_value = d["metal"]
    bsdf.inputs["Roughness"].default_value = d["rough"]
    if d.get("emit"):
        nt.links.new(att.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = d["emit"]
    return m


def voxel_mesh(name, mask, m, rgb, origin=(0.0, 0.0, 0.0), prefix="kart_", livery="silver_arrow", coll=None,
               frame=None, condition="new"):
    """Exposed faces of the voxels in `mask`, shared corners, colour per face. frame: a 3x3 Matrix; vertices are
    stored in that frame (for parts that turn about a tilted axis)."""
    pad = np.pad(mask, 1)
    inner = (slice(1, -1),) * 3
    V, C, M = [], [], []
    quad = np.array([(0, 0), (1, 0), (1, 1), (0, 1)])
    for a in range(3):
        b, c = (a + 1) % 3, (a + 2) % 3
        for sgn in (1, -1):
            sl = list(inner)
            sl[a] = slice(2, None) if sgn > 0 else slice(0, -2)
            idx = np.argwhere(mask & ~pad[tuple(sl)])
            if not len(idx):
                continue
            off = np.zeros((4, 3), int)
            off[:, a] = 1 if sgn > 0 else 0
            off[:, b], off[:, c] = quad[:, 0], quad[:, 1]
            if sgn < 0:
                off = off[::-1]
            V.append(idx[:, None, :] + off[None])
            C.append(rgb[tuple(idx.T)])
            M.append(m[tuple(idx.T)])
    Vi = np.concatenate(V).reshape(-1, 3)
    uniq, inv = np.unique(Vi, axis=0, return_inverse=True)
    co = uniq * bp.VOX + np.array([bp.X0, bp.Y0, bp.Z0]) - np.array(origin)
    if frame is not None:
        co = co @ np.array(frame)          # row vectors: R^T applied to each point
    C, M = np.concatenate(C), np.concatenate(M)
    nf = len(M)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(uniq))
    me.vertices.foreach_set("co", co.reshape(-1).astype(np.float32))
    me.loops.add(nf * 4)
    me.loops.foreach_set("vertex_index", inv.reshape(-1).astype(np.int32))
    me.polygons.add(nf)
    me.polygons.foreach_set("loop_start", np.arange(0, nf * 4, 4, dtype=np.int32))
    used = sorted(set(M.tolist()))
    for mid in used:
        me.materials.append(_material(mid, prefix, livery, condition))
    slot = {mid: i for i, mid in enumerate(used)}
    me.polygons.foreach_set("material_index", np.array([slot[x] for x in M.tolist()], dtype=np.int32))
    col = me.color_attributes.new("Col", "FLOAT_COLOR", "CORNER")
    rgba = np.concatenate([C, np.ones((nf, 1), np.float32)], axis=1)
    col.data.foreach_set("color", np.repeat(rgba, 4, axis=0).reshape(-1).astype(np.float32))
    me.update(calc_edges=True)
    me.validate()
    me.polygons.foreach_set("use_smooth", np.zeros(len(me.polygons), dtype=bool))  # flat: crisp voxel faces
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def _empty(name, coll, parent, loc, size=0.15, kind="PLAIN_AXES"):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type, e.empty_display_size = kind, size
    coll.objects.link(e)
    e.parent, e.location = parent, loc
    return e


def _drive(ob, path, index, root, prop, expr):
    fc = ob.driver_add(path, index)
    drv = fc.driver
    drv.type = "SCRIPTED"
    v = drv.variables.new()
    v.name, v.type = "x", "SINGLE_PROP"
    v.targets[0].id_type, v.targets[0].id = "OBJECT", root
    v.targets[0].data_path = f'["{prop}"]'
    drv.expression = expr


def make_kart(name="kart", livery="silver_arrow", number=None, tyre="slick", condition=None, rig=True):
    """condition: "new", "beat_up" (dents, scratches, tape, some rust) or "battered" (years of it: rust everywhere,
    grime, yellowed plastics, soot, fairing gone); default from the livery."""
    condition = condition or bp.default_condition(livery)
    d = bp.build(livery=livery, number=number, tyre=tyre, condition=condition)
    m, part, rgb = d["m"], d["part"], d["rgb"]
    coll = bpy.data.collections.new(f"Kart_{livery}" if name == "kart" else name)
    bpy.context.scene.collection.children.link(coll)
    root = _empty(name, coll, None, (0, 0, 0), 0.6, "ARROWS")
    root["blueprint"] = "library/cars/kart"
    root["vehicle"] = "kart"
    root["livery"], root["number"], root["tyre"], root["condition"] = livery, d["number"], tyre, condition
    root["steer"], root["distance"] = 0.0, 0.0
    root.id_properties_ui("steer").update(min=-30, max=30, soft_min=-25, soft_max=25,
                                          description="front-wheel angle in degrees (+ = left)")
    root.id_properties_ui("distance").update(description="metres travelled; spins the wheels (see bake_roll)")
    prefix = f"kart_{livery}_" + ("" if condition == "new" else condition + "_")
    objs = {"root": root}

    def mk(key, ids, origin, parent, frame=None):
        ob = voxel_mesh(f"{name}_{key}", np.isin(part, ids), m, rgb, origin, prefix, livery, coll, frame, condition)
        ob.parent = parent
        objs[key] = ob
        return ob

    mk("body", [bp.BODY], (0, 0, 0), root)
    mk("rear_bumper", [bp.RBUMP], (0, 0, 0), root)
    col = _empty(f"{name}_column", coll, root, tuple(bp.WHEEL_HUB), 0.08, "SINGLE_ARROW")
    col.rotation_euler = COLUMN.to_euler()
    objs["column"] = col
    sw = mk("steering_wheel", [bp.STEER], tuple(bp.WHEEL_HUB), col, COLUMN)
    if rig:
        _drive(sw, "rotation_euler", 2, root, "steer", f"x*{STEER_RATIO}*0.0174533")
    axle = _empty(f"{name}_rear_axle", coll, root, (0, -bp.WB_HALF, bp.R_REAR), 0.12)
    objs["rear_axle_pivot"] = axle
    if rig:
        _drive(axle, "rotation_euler", 0, root, "distance", f"-x/{bp.R_REAR}")
    mk("rear_axle", [bp.AXLE], (0, -bp.WB_HALF, bp.R_REAR), axle)
    for w, (cx, cy, R, W, front) in bp.WHEELS.items():
        P = bp.WHEEL_PART[w]
        c = (cx, cy, R)
        if front:
            kp = (math.copysign(bp.KINGPIN_X, cx), cy, R)
            holder = _empty(f"{name}_steer_{w}", coll, root, kp, 0.1)
            objs[f"steer_{w}"] = holder
            if rig:
                _drive(holder, "rotation_euler", 2, root, "steer", "x*0.0174533")
            mk(f"spindle_{w}", [P["spindle"]], kp, holder)
            hub = _empty(f"{name}_wheel_{w}", coll, holder, (cx - kp[0], 0, 0), 0.16)
            if rig:
                _drive(hub, "rotation_euler", 0, root, "distance", f"-x/{R}")
        else:
            hub = _empty(f"{name}_wheel_{w}", coll, axle, (cx, 0, 0), 0.16)
        objs[f"wheel_{w}"] = hub
        for k in ("tyre", "rim"):
            mk(f"{k}_{w}", [P[k]], c, hub)
    root["parts"] = ",".join(objs)
    return root, objs


def save_blend(livery="silver_arrow"):
    """Build the kart in an empty file and save it as library/cars/kart/blend/<livery>.blend (an asset)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    root, objs = make_kart("kart", livery=livery)
    coll = root.users_collection[0]
    coll.asset_mark()
    coll.asset_data.description = f"Go-kart, {bp.LIVERIES[livery]['title']}, #{root['number']}, {root['condition']}"
    for t in ("kart", "go-kart", livery):
        coll.asset_data.tags.new(t)
    os.makedirs(BLEND_DIR, exist_ok=True)
    path = os.path.join(BLEND_DIR, f"{livery}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    return path


def load_kart(name, livery="silver_arrow", number=None, tyre="slick", condition=None, scene=None):
    """Append the saved kart (or build it when number/tyre/condition differ from the saved one). Returns the root.
    condition="beat_up" / "battered" works on any livery; livery="fifth_hand" comes battered."""
    scene = scene or bpy.context.scene
    path = os.path.join(BLEND_DIR, f"{livery}.blend")
    default = (number in (None, bp.LIVERIES[livery]["number"]) and tyre == "slick"
               and condition in (None, bp.default_condition(livery)))
    if not (default and os.path.exists(path)):
        root, _ = make_kart(name, livery=livery, number=number, tyre=tyre, condition=condition)
        return root
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.collections = [f"Kart_{livery}"]
    coll = dst.collections[0]
    coll.name = name
    if coll.asset_data:
        coll.asset_clear()
    scene.collection.children.link(coll)
    for o in coll.objects:
        if o.name.startswith("kart"):
            o.name = name + o.name[4:]
    return [o for o in coll.objects if o.parent is None][0]


def bake_roll(root, f0, f1, scene=None):
    """Key root['distance'] from the root's actual motion (signed along its own +Y), so the tyres never slide."""
    scene = scene or bpy.context.scene
    dist, prev = 0.0, None
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        mw = root.matrix_world
        p, fwd = mw.translation.copy(), mw.col[1].to_3d().normalized()
        if prev is not None:
            dist += (p - prev).dot(fwd)
        prev = p
        root["distance"] = dist
        root.keyframe_insert('["distance"]', frame=f)
