"""Review renders of the team drivers: helmets on, standing and seated in their own team's car.

blender -b --factory-startup --python render_drivers.py -- [--samples 48] [view ...]
-> sheet/drivers/*.png
"""
import math
import os
import sys
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "cars", "f1_2026"))
import importlib.util  # noqa: E402
_sp = importlib.util.spec_from_file_location("char_render_sheet", os.path.join(HERE, "render_sheet.py"))
rs = importlib.util.module_from_spec(_sp)   # this folder's sheet helpers (the car folder has one of the same name)
_sp.loader.exec_module(rs)
import character_blender as ch  # noqa: E402
import car_blender  # noqa: E402

OUT = os.path.join(HERE, "sheet", "drivers")
TEAMS = ["silver_arrow", "rosso", "papaya", "midnight"]


def main():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    samples = int(a[a.index("--samples") + 1]) if "--samples" in a else 48
    views = [x for x in a if not x.startswith("--") and not x.isdigit()]
    want = lambda v: not views or any(v.startswith(x) for x in views)
    rs.OUT = OUT
    os.makedirs(OUT, exist_ok=True)
    sc, cam, L = rs.setup()
    sc.cycles.samples = samples

    if want("standing"):
        rs.clear_chars()
        for i, t in enumerate(TEAMS):
            ch.make_character(f"d{i}", "driver_" + t, helmet=True, pose="idle", location=((i - 1.5) * -0.95, 0, 0),
                              rotation=0)
        rs.persp(cam, L, (0.9, 6.2, 1.6), (0, 0, 0.78), 50, light_scale=1.5)
        rs.shoot(sc, "standing", 2400, 1300)
    if want("helmets"):
        for t in TEAMS:
            rs.clear_chars()
            ch.make_character("d", "driver_" + t, helmet=True, pose="stand")
            rs.persp(cam, L, (0.85, 1.25, 1.42), (0, 0, 1.2), 70)
            rs.shoot(sc, "helmet_" + t, 800, 800)
    if want("car"):
        for t in TEAMS:
            rs.clear_chars()
            car = car_blender.load_car("car", t)
            d = ch.make_character("drv", "driver_" + t, helmet=True)
            ch.seat_in_car(d, car)
            rs.persp(cam, L, (-1.45, 2.35, 1.55), (0, 0.15, 0.78), 40, light_scale=1.2)   # front-left, looking in
            rs.shoot(sc, "car_" + t, 1500, 1000)
            if t != "silver_arrow":
                continue
            rs.persp(cam, L, (0.0, -0.38, 1.34), (0, 1.2, 0.35), 26)                   # T-cam over the airbox
            rs.shoot(sc, "tcam", 1500, 1000)
            body = [o for o in car.children_recursive if o.type == "MESH" and o.name.startswith("car_body")]
            for o in body:
                o.hide_render = True
            for steer, name in ((0.0, "xray"), (25.0, "xray_steer")):
                car["steer"] = steer
                bpy.context.view_layer.update()
                rs.persp(cam, L, (-1.7, 2.1, 1.5), (0, 0.15, 0.6), 40, light_scale=1.2)
                rs.shoot(sc, name, 1500, 1000)
            car["steer"] = 0.0
            for o in body:
                o.hide_render = False

if __name__ == "__main__":
    main()
