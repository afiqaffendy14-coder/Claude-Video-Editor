"""Search for a clean contact pose: build a minimal scene (just what the person touches), try parameter
combinations, run the collision check on each, and print the clean ones (fewest clips first).

    blender -b --factory-startup --python blender/posefind.py -- climb_a
"""
import itertools, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import bpy
import lib
from lib import reset
import halo_sets as H
from halo_sets import person_at
import check

BX, RAIL_TOP, Y = H.BARRIER_X, 1.24, 3.0


def climb_a(dist, lean, hz, knee):
    H.armco("bh_armco", -10, 10, BX, gap=(-1.2, 1.2), top_bent=True)
    lib.box("ground", (20, 20, 0.1), (0, 0, -0.05), lib.palette()["clay"])
    p = person_at("gro", BX + dist, Y, 90, dict(lean=lean, head=(0, -14), face="worried", legL=knee), "driver_white_h",
                  hands={"L": (BX + 0.02, Y + 0.26, RAIL_TOP + hz), "R": (BX + 0.02, Y - 0.26, RAIL_TOP + hz)})
    p["foot_free"] = "L"


SEARCH = {
    "climb_a": (climb_a, dict(dist=(0.36, 0.42, 0.48), lean=(0, 8, 16), hz=(0.09, 0.12, 0.15),
                              knee=((35, 4, 70), (50, 4, 95), (25, 4, 50)))),
}

if __name__ == "__main__":
    name = sys.argv[sys.argv.index("--") + 1]
    fn, space = SEARCH[name]
    keys = list(space)
    results = []
    for combo in itertools.product(*[space[k] for k in keys]):
        kw = dict(zip(keys, combo))
        reset()
        lib.STYLE["voxel"] = True
        try:
            fn(**kw)
        except ValueError as e:
            continue
        clips, feet = check.check_scene()
        results.append((len(clips) + len(feet), kw, clips[:4]))
    results.sort(key=lambda r: r[0])
    for n, kw, c in results[:8]:
        print("POSE", n, kw, c, flush=True)
