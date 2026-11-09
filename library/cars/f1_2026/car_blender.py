"""Blueprint -> rigged Blender car asset. Use load_car() in shots; it appends the saved .blend (fast) or builds it.

    import sys; sys.path.insert(0, "<repo>/library/cars/f1_2026")
    import car_blender as car
    root = car.load_car("ham", livery="rosso")          # silver_arrow, rosso, papaya, midnight
    root.location = (0, 10, 0); root.rotation_euler.z = ...
    root["steer"] = 12          # degrees, + = turn left; front wheels and steering wheel follow
    car.bake_roll(root, 1, 120) # after animating root's motion: wheels roll exactly with the distance travelled

Hierarchy (collection "F1_<livery>", marked as an asset in its .blend):
  <root> empty, origin on the ground halfway along the wheelbase, +Y forward. Props: steer (deg), distance (m)
    body, suspension, steering_wheel (turns with steer)
    steer_FL / steer_FR  (front-wheel pivots, turn with steer)
      brake_FL ...        (upright, caliper, duct: steer, don't spin)
      wheel_FL            (spins with distance) -> tyre_FL, rim_FL, disc_FL
    brake_RL, wheel_RL -> tyre_RL, rim_RL, disc_RL   (and RR)
No driver: seat a house block character at blueprint.SEAT (fit_check.py proves the fit).
"""
import os
import sys
import numpy as np
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import blueprint as bp  # noqa: E402

BLEND_DIR = os.path.join(HERE, "blend")
STEER_RATIO = 4.0                       # steering-wheel degrees per front-wheel degree
WHEEL_CENTRE = (0.0, 0.4425, 0.6775)    # steering wheel hub


def _material(mid, prefix, livery="silver_arrow"):
    d = bp.mat_spec(mid, livery)
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


def voxel_mesh(name, mask, m, rgb, origin=(0.0, 0.0, 0.0), prefix="car_", livery="silver_arrow", coll=None):
    """Exposed faces of the voxels in `mask` (a closed shell per part), shared corners, colour per face."""
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
    Vi = np.concatenate(V).reshape(-1, 3)                       # integer voxel corners
    uniq, inv = np.unique(Vi, axis=0, return_inverse=True)
    co = uniq * bp.VOX + np.array([bp.X0, bp.Y0, bp.Z0]) - np.array(origin)
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
        me.materials.append(_material(mid, prefix, livery))
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


def _empty(name, coll, parent, loc, size=0.25, kind="PLAIN_AXES"):
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


def make_car(name="car", livery="silver_arrow", number=None, compound="medium", rig=True):
    d = bp.build(livery=livery, number=number, compound=compound)
    m, part, rgb = d["m"], d["part"], d["rgb"]
    coll = bpy.data.collections.new(f"F1_{livery}" if name == "car" else name)
    bpy.context.scene.collection.children.link(coll)
    root = _empty(name, coll, None, (0, 0, 0), 1.2, "ARROWS")
    root["blueprint"] = "library/cars/f1_2026"
    root["livery"], root["number"], root["compound"] = livery, d["number"], compound
    root["steer"], root["distance"] = 0.0, 0.0
    root.id_properties_ui("steer").update(min=-30, max=30, soft_min=-25, soft_max=25,
                                          description="front-wheel angle in degrees (+ = left)")
    root.id_properties_ui("distance").update(description="metres travelled; spins the wheels (see bake_roll)")
    prefix = f"{livery}_"
    objs = {"root": root}

    def mk(key, ids, origin=(0, 0, 0), parent=root):
        mask = np.isin(part, ids)
        ob = voxel_mesh(f"{name}_{key}", mask, m, rgb, origin, prefix, livery, coll)
        ob.parent = parent
        ob.location = origin if parent is root else (0, 0, 0)
        objs[key] = ob
        return ob

    mk("body", [bp.BODY])
    mk("suspension", [bp.SUSP])
    sw = mk("steering_wheel", [bp.STEER], WHEEL_CENTRE)
    if rig:
        _drive(sw, "rotation_euler", 1, root, "steer", f"-x*{STEER_RATIO}*0.0174533")
    for w, (cx, cy, ww, front) in bp.WHEELS.items():
        P = bp.WHEEL_PART[w]
        c = (cx, cy, bp.R_TYRE)
        holder = root
        if front:
            holder = _empty(f"{name}_steer_{w}", coll, root, c, 0.3)
            objs[f"steer_{w}"] = holder
            if rig:
                _drive(holder, "rotation_euler", 2, root, "steer", "x*0.0174533")
        mk(f"brake_{w}", [P["brake"]], c, holder)
        hub = _empty(f"{name}_wheel_{w}", coll, holder, (0, 0, 0) if front else c, 0.45)
        objs[f"wheel_{w}"] = hub
        if rig:
            _drive(hub, "rotation_euler", 0, root, "distance", f"-x/{bp.R_TYRE}")
        for k in ("tyre", "rim", "disc"):
            ob = voxel_mesh(f"{name}_{k}_{w}", np.isin(part, [P[k]]), m, rgb, c, prefix, livery, coll)
            ob.parent = hub
            objs[f"{k}_{w}"] = ob
    root["parts"] = ",".join(objs)
    return root, objs


def save_blend(livery="silver_arrow"):
    """Build the car in an empty file and save it as library/cars/f1_2026/blend/<livery>.blend (an asset)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    root, objs = make_car("car", livery=livery)
    coll = root.users_collection[0]
    coll.asset_mark()
    coll.asset_data.description = f"2026 F1 car, {bp.LIVERIES[livery]['title']}, #{root['number']}"
    for t in ("F1", "car", livery):
        coll.asset_data.tags.new(t)
    os.makedirs(BLEND_DIR, exist_ok=True)
    path = os.path.join(BLEND_DIR, f"{livery}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    return path


def load_car(name, livery="silver_arrow", number=None, compound="medium", scene=None):
    """Append the saved car (or build it when number/compound differ from the saved one). Returns the root."""
    scene = scene or bpy.context.scene
    path = os.path.join(BLEND_DIR, f"{livery}.blend")
    default = number in (None, bp.LIVERIES[livery]["number"]) and compound == "medium"
    if not (default and os.path.exists(path)):
        root, _ = make_car(name, livery=livery, number=number, compound=compound)
        return root
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.collections = [f"F1_{livery}"]
    coll = dst.collections[0]
    coll.name = name
    if coll.asset_data:
        coll.asset_clear()
    scene.collection.children.link(coll)
    for o in coll.objects:
        if o.name.startswith("car"):
            o.name = name + o.name[3:]
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
