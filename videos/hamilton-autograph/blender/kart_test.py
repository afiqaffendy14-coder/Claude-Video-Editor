import os, sys, math
sys.path.insert(0, os.path.dirname(__file__))
import bpy, lib, voxel
from lib import reset, setup_render, camera, render, V
import halo_sets as H, ham_sets as A
out = sys.argv[sys.argv.index("--") + 1]
reset(); lib.STYLE["voxel"] = True
setup_render(960, 540, 24, out)
H.studio_set()
A.kart("k1", "battered", (-1.1, 0, 0), -60)
k = A.kart("k2", "new", (1.1, 0, 0), -60)
A.kart_driver("boy", k, "boy_suit_h")
voxel.voxelize_scene()
camera(V((0.2, -4.2, 1.9)), V((0, 0, 0.3)), 40)
render()
