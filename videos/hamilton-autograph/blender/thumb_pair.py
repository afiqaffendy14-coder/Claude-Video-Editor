"""Thumbnail hero: the ask. The ten-year-old holds the red autograph book up to the towering boss, who leans down
and reaches for it, both faces turned to each other and seen three-quarter. Shot 1b's set, poses and lights, with a
low camera between them (the boy's eye height, so the boss towers). AgX like the film (the grade is applied after).

Run: blender -b --factory-startup --python blender/thumb_pair.py -- out/thumb_pair.png
Env: PCT (default 100), SAMPLES (default 128), CAM="x,y,z,tx,ty,tz,lens" to try a camera.
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector as V
import ham_anim as HA
import lib, voxel

out = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
P = next(p for p in HA.PARTS if p.shot == 1 and p.label == "b")
lib.reset()
lib.STYLE["voxel"] = True
lib.STYLE["low"] = 0
sc = HA.setup_render(540, 960, 16, "")
ctx = {}
P.static(ctx)
voxel.voxelize_scene()
HA.setup(sc, 1080, 1920, 0.6)
sc.render.resolution_percentage = int(os.environ.get("PCT", 100))
sc.cycles.samples = int(os.environ.get("SAMPLES", 128))
t = P.t1 - P.t0 - 0.05                     # the end of 1b: the boss leaning right down, his hand at the book
sc.frame_set(int(round(P.t1 * HA.FPS)) - 1)
# shot 1b's last pose, but the book lowered to his chest (in the film it is up at his face, which hides it here)
from mathutils import Matrix
BZ = float(os.environ.get("BOOKZ", 0.84))
b = ctx["book"]
b.matrix_world = (Matrix.Translation(V((0.0, -0.17, BZ))) @ Matrix.Rotation(math.radians(22), 4, "Y")
                  @ Matrix.Rotation(math.radians(-40), 4, "X") @ Matrix.Scale(1.4, 4))
bpy.context.view_layer.update()
M = b.matrix_world
tt = t + 1.76
kp = HA.alive(dict(HA.S.POSE["offer"], head=(0, -24)), tt, 0.3, 0.5)
kid = HA.person("boy", 0.0, -0.42, 0, kp, "boy_blazer", scale=HA.KID,
                hands={"L": tuple(M @ V((0.118, -0.03, -0.04))), "R": tuple(M @ V((-0.118, -0.03, -0.04)))})
bp = dict(HA.S.POSE["look_down"], head=(0, 26), lean=10, armL=(48, -4, 55))
dn = HA.boss_person(HA.alive(bp, tt, 1.0, 0.6))
HA.turn([b, kid, dn])
bpy.context.view_layer.update()
# a thumbnail cheat: both turned toward the camera (on the -Y side) so their faces read; the boy and his book as one
from mathutils import Matrix
ANG = math.radians(float(os.environ.get("TURN", 35)))
def spin(objs, about, a):
    p = V(about)
    m = Matrix.Translation(p) @ Matrix.Rotation(a, 4, "Z") @ Matrix.Translation(-p)
    for ob in objs:
        ob.matrix_world = m @ ob.matrix_world
boy, boss, book = (bpy.data.objects[n] for n in ("boy", "dennis", "book"))
spin([boy, book], boy.matrix_world.translation.copy(), -math.radians(float(os.environ.get("TURNB", 45))))
spin([boss], boss.matrix_world.translation.copy(), ANG)
hb = boy.matrix_world.translation
HA.A.lamp_point("th_boyface", (hb.x + 0.25, hb.y - 0.75, 1.35), float(os.environ.get("FACEW", 14)), (1.0, 0.86, 0.72), 0.5)  # a soft key on his face
bpy.context.view_layer.update()
for o in list(bpy.data.objects):
    if o.get("person"):
        voxel.texture_person(o)
    elif (o.type == "MESH" or o.children) and not o.get("textured") and not o.get("smooth") and o.parent is None:
        HA.dyn_texture(o)
c = [float(v) for v in os.environ.get("CAM", "0.22,-2.3,1.35,0.15,0.0,1.12,24").split(",")]
loc, tgt = V(c[:3]), V(c[3:6])
HA.cam(tuple(loc), tuple(tgt), c[6], (tgt - loc).length, 5.6)
bpy.context.view_layer.update()
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print("THUMB", out)
