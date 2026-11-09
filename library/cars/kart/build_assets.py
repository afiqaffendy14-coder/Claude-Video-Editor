"""Save every livery as a ready-to-append .blend (library/cars/kart/blend/<livery>.blend).

blender -b --factory-startup --python build_assets.py -- [livery ...]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kart_blueprint as bp  # noqa: E402
import kart_blender  # noqa: E402

a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
for livery in a or list(bp.LIVERIES):
    print("saved", kart_blender.save_blend(livery), flush=True)
