"""The final look, applied to each baked shot just before it renders (render.py): lighting, atmosphere and
tone mapping per environment, so the bakes stay untouched.

Per environment: AgX tone mapping with its own exposure; softer sun/area shadows; a thin volumetric haze for
atmospheric perspective (and visible shafts from the sun, the floodlights and the spotlight); a rim light behind
the characters, from the side opposite the camera, to lift them off the background. The colour grade, bloom,
vignette and grain are done afterwards per scene in tools/finish.py.
"""
import math, os
import bpy
from mathutils import Vector

V = Vector

MONZA = {1, 2, 3, 4, 5, 6, 7, 20, 21, 22, 25}
BAHRAIN = {13, 14, 15, 16, 17}
GARAGE = {8, 18, 23}
LAUNCH = {9, 10, 24}
ENV = {**{n: "monza" for n in MONZA}, **{n: "bahrain" for n in BAHRAIN}, **{n: "garage" for n in GARAGE},
       **{n: "launch" for n in LAUNCH}, 11: "lab", 12: "hangar", 19: "pedestal"}

# exposure (stops), haze density, haze colour, haze anisotropy, rim light (energy W, colour) per environment
PROFILE = {
    "monza":    dict(expo=-0.1, haze=0.00045, hcol=(1.0, 0.92, 0.8), aniso=0.55, rim=(380, (1.0, 0.86, 0.68))),
    "bahrain":  dict(expo=0.0, haze=0.0016, hcol=(0.75, 0.82, 1.0), aniso=0.5, rim=(600, (0.7, 0.82, 1.0))),
    "garage":   dict(expo=-0.85, haze=0.0018, hcol=(0.95, 0.97, 1.0), aniso=0.3, rim=(320, (0.85, 0.95, 1.0))),
    "launch":   dict(expo=-0.95, haze=0.0022, hcol=(0.9, 1.0, 0.98), aniso=0.4, rim=(420, (1.0, 0.85, 0.7))),
    "lab":      dict(expo=-0.1, haze=0.0012, hcol=(0.95, 0.97, 1.0), aniso=0.3, rim=None),
    "hangar":   dict(expo=-0.75, haze=0.0007, hcol=(1.0, 0.97, 0.92), aniso=0.4, rim=None),
    "pedestal": dict(expo=0.1, haze=0.006, hcol=(1.0, 0.95, 0.88), aniso=0.6, rim=None),
}


def _look(vs, names):
    for n in names:
        try:
            vs.look = n
            return n
        except TypeError:
            continue
    return None


def haze(sc, density, colour, aniso, size=(220.0, 220.0, 45.0)):
    """A thin haze in a big box around the camera: distance fades toward the haze colour, and lights show their
    shafts. (A box, not a world volume: in EEVEE a world volume swallows the sun and the sky completely.)"""
    mid = (sc.frame_start + sc.frame_end) // 2
    sc.frame_set(mid)
    c = sc.camera.matrix_world.translation
    sx, sy, sz = (s / 2 for s in size)
    vs = [(x, y, z) for x in (-sx, sx) for y in (-sy, sy) for z in (-0.5, sz * 2 - 0.5)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    me = bpy.data.meshes.new("look_haze")
    me.from_pydata(vs, [], faces)
    ob = bpy.data.objects.new("look_haze", me)
    sc.collection.objects.link(ob)
    ob.location = (c.x, c.y, 0.0)
    m = bpy.data.materials.new("look_haze")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = density
    vol.inputs["Color"].default_value = (*colour, 1.0)
    vol.inputs["Anisotropy"].default_value = aniso
    nt.links.new(vol.outputs[0], out.inputs["Volume"])
    me.materials.append(m)
    ob.visible_shadow = False


def soften_lights(sc, env):
    for o in sc.objects:
        if o.type != "LIGHT":
            continue
        L = o.data
        if L.type == "SUN":
            L.angle = math.radians(2.5)  # soft-edged shadows, still clearly directional
        elif L.type == "AREA":
            L.size = max(L.size, 2.0)
        elif L.type in ("POINT", "SPOT"):
            L.shadow_soft_size = max(L.shadow_soft_size, 0.4)


def rim_lights(sc, env):
    """One rim light per character, behind them on the far side from the camera, pointing at the shoulders."""
    prof = PROFILE[env]
    if not prof["rim"]:
        return
    energy, col = prof["rim"]
    cam = sc.camera
    mid = (sc.frame_start + sc.frame_end) // 2
    sc.frame_set(mid)
    people = [o for o in sc.objects if o.get("rig")]
    for p in people[:6]:
        c = p.matrix_world.translation + V((0, 0, 1.35))
        away = c - cam.matrix_world.translation
        away.z = 0
        if away.length < 1e-3:
            continue
        away.normalize()
        side = V((-away.y, away.x, 0)) * 0.8
        pos = c + away * 2.2 + side + V((0, 0, 1.4))
        ld = bpy.data.lights.new(p.name + "_rim", "AREA")
        ld.energy, ld.color, ld.size = energy, col, 1.2
        ld.volume_factor = 0.0  # lights the person, not the haze (no glowing squares in the background)
        lo = bpy.data.objects.new(p.name + "_rim", ld)
        sc.collection.objects.link(lo)
        lo.location = pos
        d = c - pos
        lo.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def apply(sc, n):
    env = ENV.get(n, "monza")
    prof = PROFILE[env]
    vs = sc.view_settings
    try:
        vs.view_transform = "AgX"
    except TypeError:
        pass
    _look(vs, ["AgX - Medium High Contrast", "Medium High Contrast", "AgX - Base Contrast"])
    vs.exposure = prof["expo"]
    e = sc.eevee
    for attr, val in (("use_volumetric_shadows", os.environ.get("VSHADOW", "1") == "1"),("volumetric_tile_size", "8"), ("volumetric_samples", 48),
                      ("volumetric_end", 120.0), ("volumetric_shadow_samples", 8), ("use_gtao", True),
                      ("gtao_distance", 0.6), ("use_shadows", True), ("shadow_ray_count", 2), ("shadow_step_count", 8)):
        if hasattr(e, attr):
            try:
                setattr(e, attr, val)
            except (TypeError, ValueError):
                pass
    hz = prof["haze"] * float(os.environ.get("HAZE", "1"))
    if hz > 0:
        indoor = env in ("garage", "launch", "lab", "hangar", "pedestal")
        haze(sc, hz, prof["hcol"], prof["aniso"], (40.0, 40.0, 16.0) if indoor else (220.0, 220.0, 45.0))
    soften_lights(sc, env)
    rim_lights(sc, env)
    return env
