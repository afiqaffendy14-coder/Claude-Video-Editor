"""Day / golden hour / overcast / night lighting for the circuit (EEVEE or Cycles).

One sun (shadows), a gradient sky world in the house style (no world volume), raytraced AO and reflections in EEVEE.
Night: dark-blue sky, a weak moon, the floodlight masts switched on (spot lights + glowing lamp heads) and lit
windows. Call set_time(scene, mode) at any point; it only changes light values, so it can also be keyframed.
"""
import math
import bpy
from mathutils import Vector

MODES = {
    #            sun elev, azim, strength, colour,              sky horizon,          sky zenith,           sky strength, flood
    "day":      (52, 215, 4.2, (1.0, 0.95, 0.86), (0.70, 0.82, 0.95), (0.22, 0.48, 0.92), 1.0, 0.0),
    "golden":   (12, 255, 3.2, (1.0, 0.72, 0.45), (0.98, 0.72, 0.48), (0.30, 0.42, 0.70), 0.8, 0.0),
    "overcast": (60, 200, 1.2, (0.92, 0.94, 1.0), (0.78, 0.80, 0.83), (0.58, 0.62, 0.68), 1.4, 0.0),
    "night":    (35, 140, 0.12, (0.6, 0.7, 1.0), (0.06, 0.075, 0.12), (0.01, 0.015, 0.035), 1.0, 1.0),
}


def _world(sc):
    w = bpy.data.worlds.get("circuit_sky") or bpy.data.worlds.new("circuit_sky")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    if "ramp" not in nt.nodes:
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputWorld")
        bg = nt.nodes.new("ShaderNodeBackground")
        bg.name = "bg"
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.name = "ramp"
        ramp.color_ramp.elements[0].position = 0.0
        ramp.color_ramp.elements[1].position = 0.35
        nt.links.new(tc.outputs["Generated"], sep.inputs[0])
        nt.links.new(sep.outputs["Z"], ramp.inputs[0])
        nt.links.new(ramp.outputs[0], bg.inputs["Color"])
        nt.links.new(bg.outputs[0], out.inputs[0])
    return nt


def _sun(sc):
    ob = bpy.data.objects.get("circuit_sun")
    if ob is None:
        ld = bpy.data.lights.new("circuit_sun", "SUN")
        ob = bpy.data.objects.new("circuit_sun", ld)
        coll = bpy.data.collections.get("circuit_lighting") or sc.collection
        coll.objects.link(ob)
        ld.angle = math.radians(1.2)
    return ob


def eevee(sc, samples=48):
    sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in
                                                                      bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
    e = sc.eevee
    for attr, val in (("taa_render_samples", samples), ("use_raytracing", True), ("use_shadows", True),
                      ("shadow_ray_count", 1), ("shadow_step_count", 6), ("use_fast_gi", True),
                      ("fast_gi_distance", 6.0), ("clamp_surface_indirect", 10.0)):
        if hasattr(e, attr):
            setattr(e, attr, val)
    if hasattr(e, "ray_tracing_method"):
        e.ray_tracing_method = "SCREEN"
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"


def set_time(sc, mode="day"):
    elev, azim, strength, scol, hor, zen, sky, flood = MODES[mode]
    nt = _world(sc)
    r = nt.nodes["ramp"].color_ramp
    r.elements[0].color = (*hor, 1)
    r.elements[1].color = (*zen, 1)
    nt.nodes["bg"].inputs["Strength"].default_value = sky
    sun = _sun(sc)
    sun.data.energy = strength
    sun.data.color = scol
    e, a = math.radians(elev), math.radians(azim)
    d = Vector((math.cos(e) * math.sin(a), math.cos(e) * math.cos(a), math.sin(e)))   # toward the sun
    sun.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    # floodlights: spot lights on/off, lamp heads glow more at night
    for ob in bpy.data.objects:
        if ob.get("flood_light"):
            ob.hide_render = ob.hide_viewport = flood == 0
    for m in bpy.data.materials:
        base = m.get("emit_base")
        if base is None:
            continue
        b = m.node_tree.nodes.get("Principled BSDF")
        if b is None:
            continue
        night = mode == "night"
        if m.get("lamp"):
            b.inputs["Emission Strength"].default_value = base * (5.0 if night else 1.0)
        elif m.get("night_window"):
            b.inputs["Emission Strength"].default_value = 0.6 if night else 0.0
        else:
            b.inputs["Emission Strength"].default_value = base * (0.7 if night else 1.0)
    sc["circuit_time"] = mode
    return sun


def flood_spots(points, coll, energy=110000.0, reach=26.0, prefix="flood_spot"):
    """One spot light per floodlight mast: [(x, y, z, yaw)] aimed down-and-forward at the track."""
    out = []
    ld = bpy.data.lights.get(prefix) or bpy.data.lights.new(prefix, "SPOT")
    ld.energy = energy
    ld.spot_size = math.radians(95)
    ld.spot_blend = 0.6
    ld.color = (1.0, 0.96, 0.88)
    ld.shadow_soft_size = 1.5
    if hasattr(ld, "use_shadow"):
        ld.use_shadow = False
    for i, (x, y, z, yaw) in enumerate(points):
        ob = bpy.data.objects.new(f"{prefix}_{i:03d}", ld)
        ob.location = (x, y, z)
        fwd = Vector((-math.sin(yaw), math.cos(yaw), 0.0))
        tgt = Vector((x, y, 0)) + fwd * reach
        ob.rotation_euler = (tgt - Vector((x, y, z))).to_track_quat("-Z", "Y").to_euler()
        ob["flood_light"] = True
        coll.objects.link(ob)
        out.append(ob)
    return out
