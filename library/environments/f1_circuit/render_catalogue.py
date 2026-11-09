"""Render every prototype (the reusable modules) on its own for the model sheet: sheet/catalogue/<proto>.png

blender -b blend/circuit.blend --python render_catalogue.py
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import lighting

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sheet", "catalogue")
os.makedirs(OUT, exist_ok=True)
SKIP = ("seat",)
sc = bpy.data.scenes.new("catalogue")
bpy.context.window.scene = sc if bpy.context.window else sc
lighting.eevee(sc, 24)
w = bpy.data.worlds.new("cat_world")
sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.82, 0.84, 0.87, 1)
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9
sun = bpy.data.objects.new("cat_sun", bpy.data.lights.new("cat_sun", "SUN"))
sun.data.energy = 3.5
sun.rotation_euler = (math.radians(50), 0, math.radians(35))
sc.collection.objects.link(sun)
cam = bpy.data.objects.new("cat_cam", bpy.data.cameras.new("cat_cam"))
sc.collection.objects.link(cam)
sc.camera = cam
sc.render.resolution_x, sc.render.resolution_y = 480, 360
sc.render.film_transparent = False
sc.render.image_settings.file_format = "PNG"
root = bpy.data.collections["circuit_protos"]
for c in sorted(root.children, key=lambda c: c.name):
    name = c.name[len("proto_"):]
    if name in SKIP or not c.objects:
        continue
    src = sorted(c.objects, key=lambda o: o.name)[0]
    ob = bpy.data.objects.new("cat_" + name, src.data)
    sc.collection.objects.link(ob)
    bb = [Vector(v) for v in src.bound_box]
    lo = Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
    hi = Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
    ctr, size = (lo + hi) / 2, (hi - lo).length
    d = Vector((0.75, 1.25, 0.65)).normalized()   # three-quarter view from the front (+Y) and right
    cam.location = ctr + d * size * 1.25
    cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 50
    cam.data.clip_end = 2000
    sc.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True, scene=sc.name)
    bpy.data.objects.remove(ob)
    print("CAT", name, flush=True)
