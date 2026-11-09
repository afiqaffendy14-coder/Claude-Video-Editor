"""Thumbnail hero render: the autograph page, "Phone me in 9 years" and the signature, the boss's pen still on it,
the red book, the dark ballroom behind. No face, no name. Full resolution, more samples, Standard view transform
(reds stay red).

Run: blender -b --factory-startup --python blender/thumb_ham.py -- out/thumb_hero.png
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector as V
import ham_anim as HA
import lib, voxel

out = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
P = next(p for p in HA.PARTS if p.shot == 3)
lib.reset()
lib.STYLE["voxel"] = True
lib.STYLE["low"] = 0
sc = HA.setup_render(540, 960, 16, "")
ctx = {}
P.static(ctx)
voxel.voxelize_scene()
HA.setup(sc, 1080, 1920, 0.6)
sc.render.resolution_percentage = 100
sc.cycles.samples = 96
sc.view_settings.view_transform = "Standard"
t = P.t1 - P.t0 - 0.05        # the end of the shot: the whole note and the signature written
sc.frame_set(int(round(P.t1 * HA.FPS)) - 1)
P.frame(ctx, t, 1.0)
bpy.context.view_layer.update()
for o in list(bpy.data.objects):
    if o.get("person"):
        voxel.texture_person(o)
    elif (o.type == "MESH" or o.children) and not o.get("textured") and not o.get("smooth") and o.parent is None:
        HA.dyn_texture(o)
cam = bpy.data.objects["cam"]
cam.location = cam.location + (cam.location - V(ctx["book"].matrix_world.translation)) * 0.35   # a little wider
bpy.context.view_layer.update()
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print("THUMB", out)
