"""Set dressing for the blocky look: sky, clouds, track and grandstand, a team garage, a lived-in ICU.

Called from sets.py when lib.STYLE["voxel"] is on. Everything here is boxes on (roughly) the block grid,
plus pixel-image materials made in code, so it all matches the voxel world.
"""
import math
import random
import bpy
from lib import V, box, cyl, palette, mat, link, area, sun
from voxel import PX


# ---------------------------------------------------------------- pixel-image materials
def _img(name, w, h, fn):
    img = bpy.data.images.get(name)
    if img:
        return img
    img = bpy.data.images.new(name, w, h, alpha=False)
    px = []
    for y in range(h):
        for x in range(w):
            r, g, b = fn(x, y)
            px += [r, g, b, 1.0]
    img.pixels = px
    img.pack()
    return img


def pixmat(name, img, tile=1.0, rough=0.7, emit=0.0):
    """Material whose colour is a pixel image, box-projected in object space, `tile` metres per image."""
    full = "px_custom_" + name
    if full in bpy.data.materials:
        return bpy.data.materials[full]
    m = bpy.data.materials.new(full)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = rough
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / tile, 1 / tile, 1 / tile)
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = img
    tx.interpolation = "Closest"
    tx.projection = "BOX"
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], tx.inputs["Vector"])
    nt.links.new(tx.outputs["Color"], b.inputs["Base Color"])
    if emit:
        nt.links.new(tx.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = emit
    return m


def _noisy(base, amt, rnd):
    v = 1 - amt + amt * rnd.random()
    return tuple(c * v for c in base)


def asphalt():
    rnd = random.Random(11)
    return pixmat("asphalt", _img("asphalt", 16, 16, lambda x, y: _noisy((0.16, 0.16, 0.17), 0.25, rnd)), 1.0, 0.85)


def concrete(shade=0.62):
    rnd = random.Random(12)
    def f(x, y):
        c = _noisy((shade, shade, shade * 1.02), 0.12, rnd)
        return tuple(v * 0.9 for v in c) if x == 0 or y == 0 else c
    return pixmat(f"concrete{shade}", _img(f"concrete{shade}", 16, 16, f), 1.0, 0.8)


def vinyl():
    """Hospital floor: two-tone 0.5 m vinyl tiles."""
    rnd = random.Random(13)
    def f(x, y):
        light = ((x // 8) + (y // 8)) % 2 == 0
        base = (0.80, 0.86, 0.84) if light else (0.62, 0.74, 0.72)
        return _noisy(base, 0.06, rnd)
    return pixmat("vinyl", _img("vinyl", 16, 16, f), 1.0, 0.45)


def crowd():
    rnd = random.Random(14)
    cols = [(0.75, 0.05, 0.04), (0.9, 0.9, 0.88), (0.1, 0.1, 0.12), (0.9, 0.75, 0.1), (0.15, 0.3, 0.7), (0.8, 0.45, 0.3)]
    def f(x, y):
        if y % 4 == 3:
            return (0.35, 0.35, 0.36)  # row step
        c = cols[rnd.randrange(len(cols))] if rnd.random() < 0.85 else (0.5, 0.5, 0.52)
        return c
    return pixmat("crowd", _img("crowd", 32, 32, f), 2.0, 0.9)


def kerb():
    def f(x, y):
        return (0.85, 0.06, 0.05) if (y // 8) % 2 == 0 else (0.92, 0.92, 0.9)
    return pixmat("kerb", _img("kerb", 4, 16, f), 2.0, 0.6)


def leaves():
    rnd = random.Random(15)
    return pixmat("leaves", _img("leaves", 16, 16, lambda x, y: _noisy((0.2, 0.48, 0.18), 0.35, rnd)), 1.0, 0.9)


def bark():
    rnd = random.Random(16)
    return pixmat("bark", _img("bark", 16, 16, lambda x, y: _noisy((0.36, 0.25, 0.16), 0.3, rnd)), 1.0, 0.9)


def drawers(color=(0.62, 0.02, 0.02)):
    def f(x, y):
        if y % 4 == 0:
            return (0.05, 0.05, 0.05)
        if y % 4 == 2 and 6 <= x <= 9:
            return (0.75, 0.75, 0.76)
        return color
    return pixmat("drawers", _img("drawers", 16, 16, f), 0.8, 0.45)


def data_screen():
    rnd = random.Random(17)
    def f(x, y):
        if y in (3, 4) and x < 12:
            return (0.1, 0.9, 0.4)
        if y % 3 == 0 and rnd.random() < 0.6:
            return (0.9, 0.9, 0.95) if rnd.random() < 0.5 else (0.95, 0.2, 0.15)
        return (0.02, 0.03, 0.05)
    return pixmat("datascreen", _img("datascreen", 16, 12, f), 0.6, 0.3, emit=1.5)


# ---------------------------------------------------------------- sky
def sky_world(horizon=(0.7, 0.82, 0.95), zenith=(0.22, 0.48, 0.92), strength=1.0):
    sc = bpy.context.scene
    w = bpy.data.worlds.new("sky")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (*horizon, 1)
    ramp.color_ramp.elements[1].position = 0.22
    ramp.color_ramp.elements[1].color = (*zenith, 1)
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength
    return w


def clouds(center=(0, 0), seed=5, n=12, z=26, spread=70):
    rnd = random.Random(seed)
    m = mat("cloud", (1, 1, 1), 1.0)
    for i in range(n):  # one flat slab per cloud (overlapping slabs shade each other black)
        cx = center[0] + rnd.uniform(-spread, spread)
        cy = center[1] + rnd.uniform(20, spread * 1.6)
        box(f"cloud{i}", (rnd.choice([10, 14, 18, 24]), rnd.choice([6, 8, 10]), 2.0), (cx, cy, z + rnd.choice([0, 3, 6])), m)


def tree(name, x, y, h=4, r=2):
    box(name + "_trunk", (0.5, 0.5, h), (x, y, h / 2), bark())
    L = leaves()
    box(name + "_leaf", (r * 2, r * 2, r * 1.5), (x, y, h + r * 0.4), L)
    box(name + "_leaf2", (r * 1.2, r * 1.2, r), (x, y, h + r * 1.3), L)


# ---------------------------------------------------------------- pit lane
def pit_dress():
    M = palette()
    sky_world()
    clouds((10, 0))
    # surfaces: darker concrete pit lane, light epoxy garage, the box itself painted
    for ob in ("pit_floor",):
        bpy.data.objects[ob].data.materials[0] = concrete(0.5)
    bpy.data.objects["gar_floor"].data.materials[0] = concrete(0.78)
    box("box_paint", (3.2, 7.6, 0.006), (0, 0, 0.002), mat("boxpaint", (0.36, 0.36, 0.38), 0.7))
    box("box_red", (3.2, 0.25, 0.008), (0, 3.6, 0.004), M["red"])
    for y in (-1.78, 1.8):  # wheel position marks
        for s in (1, -1):
            box("wheelmark", (0.5, 0.08, 0.008), (s * 0.8, y + 0.5, 0.005), M["white"])
            box("wheelmark", (0.5, 0.08, 0.008), (s * 0.8, y - 0.5, 0.005), M["white"])
    for ob in bpy.data.objects:
        if ob.name.startswith("pit_line") or ob.name.startswith("fast_lane_line"):
            ob.data.materials[0] = M["white"]
    # track beyond the pit wall: asphalt, red/white kerb, grass verge
    box("track", (14, 80, 0.1), (15, 0, -0.04), asphalt())
    box("kerb", (0.8, 80, 0.12), (8.6, 0, 0.0), kerb())
    box("grass", (40, 80, 0.1), (42, 0, -0.06), pixmat("grass", _img("grass", 16, 16, lambda x, y, r=random.Random(18): _noisy((0.3, 0.58, 0.22), 0.25, r)), 1.0, 0.9))
    box("verge", (2, 80, 0.1), (23, 0, -0.05), concrete(0.7))
    # pit wall: white with a red top band, team stand with screens
    bpy.data.objects["pit_wall"].data.materials[0] = M["white"]
    box("wall_band", (0.62, 80, 0.2), (7.5, 0, 1.0), M["red"])
    box("stand_base", (1.6, 4.0, 1.2), (6.6, 1.0, 0.6), M["dark"])
    box("stand_roof", (2.0, 4.4, 0.15), (6.6, 1.0, 2.6), M["red"])
    for y in (-0.5, 0.5, 1.5, 2.5):
        box("stand_post", (0.08, 0.08, 1.4), (7.4, y, 1.9), M["grey"])
    for i, y in enumerate((-0.4, 0.6, 1.6, 2.6)):
        box(f"stand_screen{i}", (0.06, 0.7, 0.45), (5.85, y - 0.1, 1.55), data_screen())
    # grandstand across the track: stepped, crowd texture on the risers, roof on pillars
    C = crowd()
    for i in range(6):
        box(f"gs_step{i}", (1.2, 60, 0.6 * (i + 1)), (26 + i * 1.2, 0, 0.3 * (i + 1)), concrete(0.68))
        box(f"gs_crowd{i}", (0.05, 60, 0.5), (25.43 + i * 1.2, 0, 0.6 * i + 0.3 + 0.32), C)
    box("gs_back", (0.4, 60, 6), (33.4, 0, 3), concrete(0.6))
    box("gs_roof", (9, 62, 0.4), (29.5, 0, 7.4), M["white"])
    for y in range(-28, 29, 8):
        box("gs_pillar", (0.4, 0.4, 7.2), (25.6, y, 3.6), M["grey"])
    box("gs_banner", (0.1, 60, 1.0), (25.45, 0, 6.7), M["red"])
    for i, y in enumerate(range(-36, 37, 9)):
        tree(f"tree{i}", 38 + (i % 2) * 3, y, 4 + (i % 3), 2 + (i % 2) * 0.5)
    # garage: team band on the back wall, red tool chests, blanketed tyre stacks, data screens
    box("gar_band", (0.05, 12, 0.8), (-10.33, 0, 2.6), M["red"])
    box("gar_band2", (0.05, 12, 0.1), (-10.33, 0, 3.1), M["white"])
    for i, y in enumerate((-5.0, -4.2, 4.2, 5.0)):
        box(f"chest{i}", (0.7, 0.75, 1.1), (-9.9, y, 0.55), drawers())
        box(f"chesttop{i}", (0.72, 0.77, 0.04), (-9.9, y, 1.12), M["grey"])
    for i in range(3):
        box(f"blanket{i}", (0.78, 0.74, 1.45), (-9.7, -3.5 + i * 0.8, 0.73), mat("blanket_red", (0.7, 0.04, 0.03), 0.9))
        box(f"blankettop{i}", (0.8, 0.76, 0.06), (-9.7, -3.5 + i * 0.8, 1.47), M["dark"])
    for ob in list(bpy.data.objects):
        if ob.name.startswith("stack"):
            bpy.data.objects.remove(ob, do_unlink=True)
    for i in range(3):
        box(f"gar_screen{i}", (0.05, 0.9, 0.55), (-10.28, 1.5 + i * 1.1, 2.4), data_screen())
    for y in (-2.5, 0, 2.5):
        box("rig_glow", (0.36, 0.36, 0.02), (-3.6, y, 3.62), mat("rigglow", (1, 1, 1), 0.3, emit=(1, 0.95, 0.85), emit_strength=8))
    # light: warm afternoon sun, cool sky fill
    sun("pit_sun", (40, 0, -55), 4.2, 1.5, (1.0, 0.9, 0.75))


# ---------------------------------------------------------------- ICU
def icu_dress():
    M = palette()
    sky_world((0.95, 0.88, 0.78), (0.35, 0.58, 0.92), 1.6)
    bpy.data.objects["icu_floor"].data.materials[0] = vinyl()
    # front wall rebuilt with a real window opening; city blocks and trees outside
    for n in ("icu_front", "icu_window"):
        o = bpy.data.objects.get(n)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)
    wall = bpy.data.materials["icu_wall"]
    box("front_l", (2.8, 0.2, 3.2), (-2.6, -3.8, 1.6), wall)
    box("front_r", (2.8, 0.2, 3.2), (2.6, -3.8, 1.6), wall)
    box("front_lo", (2.4, 0.2, 0.9), (0, -3.8, 0.45), wall)
    box("front_hi", (2.4, 0.2, 0.7), (0, -3.8, 2.85), wall)
    box("sill", (2.5, 0.35, 0.08), (0, -3.68, 0.92), M["white"])
    box("mullion", (0.08, 0.1, 1.6), (0, -3.8, 1.7), M["white"])
    rnd = random.Random(21)
    for i in range(10):
        h = rnd.choice([8, 12, 16, 22, 28])
        box(f"city{i}", (rnd.choice([4, 6, 8]), 6, h), (-20 + i * 4.5, -20 - rnd.uniform(0, 12), h / 2),
            concrete(rnd.choice([0.75, 0.82, 0.9])))
    for i in range(4):
        tree(f"street_tree{i}", -6 + i * 4, -9, 3, 1.5)
    box("street", (60, 30, 0.1), (0, -20, -0.06), asphalt())
    # dado band, curtains on rails, ceiling lights, bedside cabinet, sink
    box("dado", (7.9, 0.04, 1.0), (0, 2.08, 0.5), mat("dado", (0.24, 0.42, 0.44), 0.7))
    for s in (1, -1):
        box("dado_s", (0.04, 6, 1.0), (s * 3.08, -0.8, 0.5), mat("dado", (0.24, 0.42, 0.44), 0.7))
        box("curtain", (0.12, 1.4, 2.2), (s * 2.4, 1.2, 1.5), pixmat("curtain", _img("curtain", 8, 16,
            lambda x, y: (0.55, 0.78, 0.82) if x % 4 < 2 else (0.48, 0.7, 0.75)), 0.6, 0.9))
        box("rail", (0.06, 3.0, 0.06), (s * 2.4, 0.5, 2.65), M["steel"])
    for x in (-1.2, 1.2):
        box("ceil_glow", (0.9, 0.5, 0.04), (x, -0.8, 3.14), mat("icu_glow2", (1, 1, 1), 0.3, emit=(1.0, 0.95, 0.88), emit_strength=4))
    box("cabinet", (0.6, 0.5, 0.85), (1.9, 1.75, 0.43), drawers((0.85, 0.87, 0.86)))
    box("cab_top", (0.62, 0.52, 0.04), (1.9, 1.75, 0.87), M["clay2"])
    box("sink", (0.7, 0.5, 0.25), (-2.5, -2.6, 0.95), M["white"])
    box("sink_base", (0.7, 0.5, 0.82), (-2.5, -2.6, 0.41), drawers((0.85, 0.87, 0.86)))
    # tidy the floor cables (they read as clutter in blocks)
    for n in ("cab1", "cab2"):
        o = bpy.data.objects.get(n)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)
    # light: low sun through the window, warm; soft cool fill inside
    for n in ("icu_rim", "icu_fill"):
        o = bpy.data.objects.get(n)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)
    sun("window_sun", (62, 0, 12), 4.0, 1.0, (1.0, 0.86, 0.66))
    area("icu_fill", (0, -1.5, 3.0), (0, 0.3, 0.6), 120, 2.5, color=(0.8, 0.9, 1.0))
