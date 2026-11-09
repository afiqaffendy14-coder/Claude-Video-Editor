"""Camera presets for the circuit. They are ordinary cameras (named cam_*) in the collection circuit_cameras:
nothing is locked; move them, copy them, or make your own with `aim()`.

    import cameras; cameras.use("cam_T1_track_level")
"""
import math
import bpy
from mathutils import Vector
import layout as L
import plan as P


def aim(name, loc, target, lens=35.0, coll=None, ortho=None, clip_end=6000.0):
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_start = 0.1
    cd.clip_end = clip_end
    cd.sensor_width = 36
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    ob = bpy.data.objects.get(name) or bpy.data.objects.new(name, cd)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    if coll is not None and ob.name not in coll.objects:
        coll.objects.link(ob)
    return ob


def _f(s, off=0.0, z=0.0):
    x, y, h = L.frame(s, off)
    return (x, y, z), h


def presets():
    out = {}
    sf = L.SF_S
    # wide establishing: high over the north-west, the main straight, pits and grandstand in view
    out["cam_establishing"] = ((-760.0, 420.0, 230.0), (80.0, -120.0, 0.0), 30.0)
    # aerial: straight down over the whole circuit (orthographic)
    out["cam_aerial_top"] = ((190.0, -370.0, 1500.0), (190.0, -369.9, 0.0), 50.0)
    # track level on the main straight looking back at the grid and the start gantry
    out["cam_grid_track_level"] = ((60.0, -3.0, 0.7), (-120.0, 1.0, 1.2), 40.0)
    # three-quarter over the front of the grid
    out["cam_grid_three_quarter"] = ((-22.0, 22.0, 10.0), (-55.0, -2.0, 0.5), 32.0)
    # pit lane: down the fast lane past the garages, and straight into a garage
    out["cam_pit_lane"] = ((-185.0, -19.5, 1.7), (0.0, -27.0, 2.0), 30.0)
    gx = (L.garages()[1][1] + L.garages()[1][2]) / 2
    out["cam_garage"] = ((gx - 2.0, L.PIT_Y + 2.0, 1.6), (gx + 1.0, L.GARAGE_Y - 12.0, 1.8), 24.0)
    # side view along the pit wall
    out["cam_pit_wall"] = ((-60.0, -6.0, 2.2), (-40.0, -14.5, 2.0), 35.0)
    # T1: low on the inside at the apex, looking back up the braking zone
    a, b = L.corner_range("T1")
    p, h = _f(b + 25, L.width(b) / 2 + 9.0, 1.3)
    q, _ = _f((a + b) / 2 - 6, -2.0, 0.4)
    out["cam_T1_track_level"] = (p, q, 32.0)
    # hairpin from above and behind the outside run-off
    a, b = L.corner_range("T4")
    p, h = _f((a + b) / 2, 70.0, 45.0)
    q, _ = _f((a + b) / 2, 0.0, 0.0)
    out["cam_hairpin_aerial"] = (p, q, 30.0)
    # chicane kerbs close up
    a, b = L.corner_range("T13")
    p, h = _f(a - 12, -(L.width(a) / 2 + 2.0), 0.45)
    q, _ = _f(b + 6, 2.0, 0.0)
    out["cam_chicane_kerbs"] = (p, q, 24.0)
    # grandstand point of view: upper rows of the main grandstand looking across at the pits
    out["cam_grandstand_pov"] = ((-40.0, 42.0, 13.0), (-60.0, -30.0, 4.0), 28.0)
    # back straight side-on with its stand behind
    bs = L.PRIMS[L.BACK]
    p, h = _f(bs.s0 + bs.length * 0.62, -16.0, 2.0)
    q, _ = _f(bs.s0 + bs.length * 0.62, 8.0, 1.5)
    out["cam_back_straight_side"] = (p, q, 30.0)
    # esses three-quarter from up high
    a, b = L.corner_range("T8")
    p, h = _f(a, -60.0, 28.0)
    q, _ = _f(b, 0.0, 0.0)
    out["cam_esses_three_quarter"] = (p, q, 28.0)
    # from the spectator bridge down the main straight toward T1
    s_br = P.BRIDGES[0][1]
    p, h = _f(s_br + 3.0, 0.0, 10.6)
    q, _ = _f(s_br + 200.0, 0.0, 0.0)
    out["cam_bridge_view"] = (p, q, 35.0)
    # last corner, low on the outside, cars coming at camera onto the main straight
    a, b = L.corner_range("T15")
    p, h = _f(b + 60, 4.0, 3.0)
    q, _ = _f((a + b) / 2, 0.0, 1.0)
    out["cam_last_corner"] = (p, q, 40.0)
    # paddock street between garages and motorhomes
    out["cam_paddock"] = ((-215.0, -66.0, 1.7), (-60.0, -64.0, 3.0), 28.0)
    return out


def add_presets(coll):
    obs = []
    for name, (loc, tgt, lens) in presets().items():
        obs.append(aim(name, loc, tgt, lens, coll, ortho=2050.0 if name == "cam_aerial_top" else None))
    sc = bpy.context.scene
    sc.camera = bpy.data.objects["cam_establishing"]
    return obs


def use(name, scene=None):
    sc = scene or bpy.context.scene
    sc.camera = bpy.data.objects[name]
    return sc.camera
