"""Core Blender helpers for the clay-render look: scene reset, materials, primitives, lofts, tubes.

Everything is built from code so a shot can be rebuilt deterministically; see people.py, props.py, sets.py.
"""
import math
import bpy
import addon_utils
import bmesh
from mathutils import Vector, Matrix, Euler

V = Vector

# Look switch. LOW = 0: smooth clay. LOW = 1: low poly, game-like but not choppy. LOW = 2: chunkier low poly.
# Every primitive below reads it, so the whole film changes style from one place.
STYLE = {"low": 0}
DECIMATE = {1: 0.45, 2: 0.55}  # level 2 skips the subdivision, so it starts from far fewer faces


def low():
    return STYLE["low"]


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable("cycles")
    MAT.clear()


# ---------------------------------------------------------------- materials
MAT = {}


def mat(name, color, rough=0.6, metal=0.0, coat=0.0, emit=None, emit_strength=0.0, alpha=1.0, transmission=0.0):
    if name in MAT:
        return MAT[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    if transmission:
        b.inputs["Transmission Weight"].default_value = transmission
        b.inputs["IOR"].default_value = 1.45
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    MAT[name] = m
    return m


def palette():
    """The channel palette (style guide): clay whites and greys, one red accent, muted scrubs."""
    return dict(
        clay=mat("clay", (0.80, 0.80, 0.78), 0.65),
        clay2=mat("clay2", (0.62, 0.62, 0.60), 0.6),
        grey=mat("grey", (0.32, 0.32, 0.31), 0.55),
        dark=mat("dark", (0.045, 0.045, 0.05), 0.45),
        rubber=mat("rubber", (0.02, 0.02, 0.022), 0.8),
        red=mat("red", (0.62, 0.012, 0.012), 0.32, coat=0.6),
        redm=mat("redm", (0.55, 0.02, 0.02), 0.6),  # matte red: fire suits
        scrubs=mat("scrubs", (0.06, 0.32, 0.38), 0.75),
        gown=mat("gown", (0.14, 0.40, 0.50), 0.8),
        glove=mat("glove", (0.72, 0.80, 0.84), 0.45),
        skin=mat("skin", (0.74, 0.56, 0.45), 0.55),
        babyskin=mat("babyskin", (0.80, 0.60, 0.50), 0.5),
        white=mat("white", (0.92, 0.92, 0.91), 0.5),
        blanket=mat("blanket", (0.85, 0.86, 0.88), 0.9),
        steel=mat("steel", (0.75, 0.76, 0.78), 0.28, metal=1.0),
        chrome=mat("chrome", (0.9, 0.9, 0.92), 0.12, metal=1.0),
        glass=mat("glass", (0.92, 0.96, 1.0), 0.08, alpha=0.18),
        screen=mat("screen", (0.01, 0.012, 0.015), 0.25),
        yellow=mat("yellow", (0.85, 0.62, 0.02), 0.5),
        tube=mat("tube", (0.85, 0.9, 0.92), 0.2, transmission=0.6),
        lamp=mat("lamp", (1, 1, 1), 0.3, emit=(1, 0.97, 0.92), emit_strength=6),
        panel=mat("panel", (1, 1, 1), 0.3, emit=(1, 1, 1), emit_strength=2.5),
        green=mat("green", (0.05, 0.6, 0.25), 0.4, emit=(0.15, 1.0, 0.45), emit_strength=3),
    )


# ---------------------------------------------------------------- objects
def link(ob, coll=None):
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def mesh_obj(name, verts, faces, material=None, smooth=False, coll=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    ob = link(bpy.data.objects.new(name, me), coll)
    if material:
        me.materials.append(material)
    if smooth:
        for p in me.polygons:
            p.use_smooth = not low()
    return ob


def bevel(ob, width=0.01, segments=3, limit="ANGLE"):
    m = ob.modifiers.new("bevel", "BEVEL")
    m.width = width
    m.segments = 1 if low() else segments
    m.limit_method = limit
    m.harden_normals = False
    return ob


def subsurf(ob, levels=2):
    """Smooth look: subdivide. Low poly: one subdivision then collapse-decimate into flat facets."""
    m = ob.modifiers.new("subsurf", "SUBSURF")
    m.levels = m.render_levels = (1 if low() == 1 else 0) if low() else levels
    if low():
        d = ob.modifiers.new("decimate", "DECIMATE")
        d.decimate_type = "COLLAPSE"
        d.ratio = DECIMATE[low()]
        smooth(ob)
    return ob


def smooth(ob):
    """Smooth shading, or flat facets in low-poly mode."""
    for p in ob.data.polygons:
        p.use_smooth = not low()
    return ob


def box(name, size, loc=(0, 0, 0), material=None, bev=0.0, rot=(0, 0, 0), coll=None, seg=3):
    """Axis box of full size (sx, sy, sz) centred at loc, optional rounded edges."""
    sx, sy, sz = (s / 2 for s in size)
    v = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
         (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = mesh_obj(name, v, f, material, coll=coll)
    ob.location = loc
    ob.rotation_euler = rot
    if bev:
        bevel(ob, min(bev, min(size) / 2 - 1e-4), seg)
        smooth(ob)
    return ob


def cyl(name, r, h, loc=(0, 0, 0), material=None, seg=32, rot=(0, 0, 0), bev=0.0, r2=None, coll=None, cap=True):
    """Cylinder (or cone frustum with r2) along local Z, base at -h/2."""
    r2 = r if r2 is None else r2
    seg = lowseg(seg, 14, 10)
    v, f = [], []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        v.append((r * math.cos(a), r * math.sin(a), -h / 2))
        v.append((r2 * math.cos(a), r2 * math.sin(a), h / 2))
    for i in range(seg):
        j = (i + 1) % seg
        f.append((2 * i, 2 * j, 2 * j + 1, 2 * i + 1))
    if cap:
        f.append(tuple(2 * i for i in reversed(range(seg))))
        f.append(tuple(2 * i + 1 for i in range(seg)))
    ob = mesh_obj(name, v, f, material, smooth=True, coll=coll)
    ob.location = loc
    ob.rotation_euler = rot
    if bev:
        bevel(ob, bev, 3)
    autosmooth(ob)
    return ob


def lowseg(seg, lo1=12, lo2=8, floor=6):
    """Segment count for round things: unchanged when smooth, capped when low poly."""
    if not low():
        return seg
    return max(floor if seg >= floor else seg, min(seg, lo1 if low() == 1 else lo2))


def sphere(name, r, loc=(0, 0, 0), material=None, scale=(1, 1, 1), seg=32, rings=16, coll=None, rot=(0, 0, 0)):
    if low():
        seg, rings = (14, 8) if low() == 1 else (10, 6)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new(name, me), coll)
    if material:
        me.materials.append(material)
    smooth(ob)
    ob.location = loc
    ob.scale = scale
    ob.rotation_euler = rot
    return ob


def torus(name, R, r, loc=(0, 0, 0), material=None, rot=(0, 0, 0), seg=48, rseg=16, coll=None):
    if low():
        seg, rseg = (18, 6) if low() == 1 else (12, 4)
    v, f = [], []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        for j in range(rseg):
            b = 2 * math.pi * j / rseg
            v.append(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b)))
    for i in range(seg):
        for j in range(rseg):
            a, b = i * rseg + j, ((i + 1) % seg) * rseg + j
            c, d = ((i + 1) % seg) * rseg + (j + 1) % rseg, i * rseg + (j + 1) % rseg
            f.append((a, b, c, d))
    ob = mesh_obj(name, v, f, material, smooth=True, coll=coll)
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def autosmooth(ob, angle=40):
    """Smooth shading with sharp edges kept above `angle` degrees (flat facets in low-poly mode)."""
    if low():
        return smooth(ob)
    try:
        with bpy.context.temp_override(object=ob, selected_editable_objects=[ob], active_object=ob):
            bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))
    except Exception:
        smooth(ob)
    return ob


def loft(name, sections, material=None, closed=True, smooth_=True, coll=None):
    """Skin a list of rings (each a list of 3D points, same count) into a tube; caps both ends if closed."""
    n = len(sections[0])
    v = [p for s in sections for p in s]
    f = []
    for i in range(len(sections) - 1):
        for j in range(n):
            a, b = i * n + j, i * n + (j + 1) % n
            f.append((a, b, b + n, a + n))
    if closed:
        f.append(tuple(reversed(range(n))))
        last = (len(sections) - 1) * n
        f.append(tuple(last + j for j in range(n)))
    ob = mesh_obj(name, v, f, material, smooth=smooth_, coll=coll)
    fix_normals(ob)
    return ob


def fix_normals(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()


def superellipse(cx, cy, cz, w, h, n=24, p=3.0, plane="YZ"):
    """Ring of points: a rounded-rectangle cross-section (|x/w|^p + |y/h|^p = 1) at a centre."""
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        c, s = math.cos(a), math.sin(a)
        x = w * math.copysign(abs(c) ** (2 / p), c)
        y = h * math.copysign(abs(s) ** (2 / p), s)
        if plane == "YZ":  # section across X axis (lofts that run along X)
            pts.append(V((cx, cy + x, cz + y)))
        elif plane == "XY":  # horizontal section (lofts that run up Z)
            pts.append(V((cx + x, cy + y, cz)))
        else:  # "XZ": lofts that run along Y
            pts.append(V((cx + x, cy, cz + y)))
    return pts


def tube(name, points, r=0.01, material=None, coll=None, res=6):
    """Smooth bevelled curve through points (cables, IV lines, breathing tubes)."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = 3 if not low() else (1 if low() == 1 else 0)
    cu.resolution_u = res if not low() else max(2, res // 2)
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(points) - 1)
    for bp, p in zip(sp.bezier_points, points):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    ob = link(bpy.data.objects.new(name, cu), coll)
    if material:
        cu.materials.append(material)
    return ob


def group(name, children, loc=(0, 0, 0), rot=(0, 0, 0), scale=1.0, coll=None):
    """Parent objects under an empty so a whole prop can be placed and turned as one."""
    e = link(bpy.data.objects.new(name, None), coll)
    for c in children:
        c.parent = e
    e.location = loc
    e.rotation_euler = rot
    e.scale = (scale, scale, scale)
    return e


# ---------------------------------------------------------------- render setup
def setup_render(w=540, h=960, samples=32, path="/tmp/out.png"):
    sc = bpy.context.scene
    r = sc.render
    r.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 6
    sc.cycles.diffuse_bounces = 3
    sc.cycles.glossy_bounces = 2
    sc.cycles.transmission_bounces = 4
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.blur_glossy = 1.0
    r.resolution_x, r.resolution_y = w, h
    r.resolution_percentage = 100
    r.filepath = path
    r.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - High Contrast"
    sc.view_settings.exposure = -0.3
    return sc


def world(strength=0.9, color=(0.92, 0.93, 0.95)):
    sc = bpy.context.scene
    w = bpy.data.worlds.new("world")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*color, 1)
    bg.inputs[1].default_value = strength
    return w


def area(name, loc, target, energy=500, size=4.0, color=(1, 1, 1), shape="DISK", size_y=None, coll=None):
    d = bpy.data.lights.new(name, "AREA")
    d.energy = energy
    d.color = color
    d.shape = shape
    d.size = size
    if size_y:
        d.size_y = size_y
    ob = link(bpy.data.objects.new(name, d), coll)
    ob.location = loc
    look_at(ob, target)
    return ob


def look_at(ob, target, roll=0.0):
    d = V(target) - V(ob.location)
    q = d.to_track_quat("-Z", "Y")
    ob.rotation_euler = q.to_euler()
    if roll:
        ob.rotation_euler.rotate_axis("Z", math.radians(roll))


def camera(loc, target, lens=35, dof=None, fstop=2.8, roll=0.0, name="cam"):
    cam = bpy.data.objects.get(name)
    if not cam:
        cam = link(bpy.data.objects.new(name, bpy.data.cameras.new(name)))
    cam.location = loc
    look_at(cam, target, roll)
    cam.data.lens = lens
    cam.data.sensor_width = 36
    cam.data.sensor_fit = "AUTO"
    cam.data.clip_start = 0.01
    cam.data.clip_end = 400
    cam.data.dof.use_dof = dof is not None
    if dof is not None:
        cam.data.dof.focus_distance = dof
        cam.data.dof.aperture_fstop = fstop
    bpy.context.scene.camera = cam
    return cam


def render(path=None):
    if path:
        bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def cyclorama(name="cyc", size=60, height=25, radius=6, material=None, loc=(0, 0, 0), rot=0.0):
    """Infinite-studio backdrop: a floor that curves up into a back wall (no visible horizon)."""
    material = material or palette()["clay"]
    prof = []
    for i in range(17):  # quarter circle from floor to wall
        a = math.pi / 2 * i / 16
        prof.append((size / 2 - radius + radius * math.sin(a), radius - radius * math.cos(a)))
    prof = [(-size / 2, 0.0)] + prof + [(size / 2, height)]
    v, f = [], []
    for x in (-size / 2, size / 2):
        for y, z in prof:
            v.append(V((x, y, z)))
    n = len(prof)
    for i in range(n - 1):
        f.append((i, i + 1, n + i + 1, n + i))
    ob = mesh_obj(name, v, f, material, smooth=True)
    ob.location = loc
    ob.rotation_euler = (0, 0, rot)
    return ob


def sun(name="sun", rot=(50, 0, -35), energy=3.5, angle=3.0, color=(1.0, 0.97, 0.92)):
    """Directional key light with crisp, slightly soft shadows (the game look)."""
    d = bpy.data.lights.new(name, "SUN")
    d.energy = energy
    d.angle = math.radians(angle)
    d.color = color
    ob = link(bpy.data.objects.new(name, d))
    ob.rotation_euler = tuple(math.radians(a) for a in rot)
    return ob
