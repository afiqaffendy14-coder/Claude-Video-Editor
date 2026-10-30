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
    "pit": (lambda: S.pit_set(), ((5.2, 7.6, 3.6), (0, 0.4, 0.2), 32)),
    "icu": (lambda: S.icu_set("order"), ((0.6, 1.9, 1.5), (0, -0.4, 0.95), 30)),
}
for lv in [int(a) for a in sys.argv[1:]] or (1, 2):
    for key, (build, (loc, tgt, lens)) in FRAMES.items():
        if os.environ.get("KEYS") and key not in os.environ["KEYS"]:
            continue
        reset()
        lib.STYLE["low"] = lv
        setup_render(720, 1280, 32, os.path.join(OUT, f"{key}_low{lv}.png"))
        build()
        camera(V(loc), V(tgt), lens)
        render()
        print("STYLE", key, lv, flush=True)
