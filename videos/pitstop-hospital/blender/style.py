"""Style frames: the same two hero shots at two low-poly densities, to pick the look before building the film.
Run: .venv-blender/bin/python style.py  -> boards/style/{pit,icu}_low{1,2}.png
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import lib
from lib import V, reset, setup_render, camera, render
import sets as S

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "boards", "style")
os.makedirs(OUT, exist_ok=True)
FRAMES = {
    "pit": (lambda: S.pit_set(), ((-3.0, -8.6, 4.3), (1.0, 1.2, 0.2), 26)),
    "pitv": (lambda: S.pit_set(crew_skip=("FR", "RR", "RL", "jacks", "stab", "wing")), ((-3.4, 6.0, 1.25), (0, 0.5, 0.45), 30, 6.6, 3.5)),
    "icuv": (lambda: S.icu_set("order"), ((0.35, 1.95, 2.85), (0, -0.5, 0.7), 18, 2.1, 4.0)),
    "icuh": (lambda: S.icu_set("order", skip=("o1", "o3")), ((1.75, 1.05, 1.9), (-0.15, -0.15, 0.95), 26, 2.0, 2.8)),
    "icu": (lambda: S.icu_set("order"), ((0.6, 1.9, 1.5), (0, -0.4, 0.95), 30)),
}
for lv in [a for a in sys.argv[1:]] or ("1", "2"):
    for key, (build, (loc, tgt, lens, *dof)) in FRAMES.items():
        if os.environ.get("KEYS") and key not in os.environ["KEYS"].split():
            continue
        reset()
        lib.STYLE["voxel"] = lv == "vox"
        lib.STYLE["low"] = 0 if lv == "vox" else int(lv)
        setup_render(720, 1280, 32, os.path.join(OUT, f"{key}_low{lv}.png"))
        build()
        if lv == "vox":
            import time, voxel
            t = time.time()
            voxel.voxelize_scene()
            print("voxelized in", round(time.time() - t, 1), "s", flush=True)
        camera(V(loc), V(tgt), lens, *(dof or [None]))
        render()
        print("STYLE", key, lv, flush=True)
