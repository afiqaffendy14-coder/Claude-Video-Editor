"""Save every livery as a ready-to-append .blend (library/cars/f1_2026/blend/<livery>.blend).

blender -b --factory-startup --python build_assets.py -- [livery ...]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blueprint as bp  # noqa: E402
import car_blender  # noqa: E402

a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
for livery in a or list(bp.LIVERIES):
    print("saved", car_blender.save_blend(livery), flush=True)
