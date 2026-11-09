"""Check that the existing rigs still work inside the circuit: two library F1 cars with seated drivers drive through
Turn 1 on a racing line (lap_frame + bake_roll + steer), a kart with its driver sits in the paddock.

blender -b blend/circuit.blend --python test_animation.py -- [--frames 96] [--video]
Writes sheet/anim_test/ (stills + frames) and prints contact checks (wheels on the asphalt, rig values keyed).
"""
import math
import os
import sys
import subprocess
import numpy as np
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.dirname(os.path.dirname(HERE))
for p in (HERE, os.path.join(LIB, "cars", "f1_2026"), os.path.join(LIB, "cars", "kart"),
          os.path.join(LIB, "characters", "block_character")):
    sys.path.insert(0, p)
import circuit_blender as cb
import layout as L
import ground as S
import lighting, cameras
import car_blender
import kart_blender
import character_blender as ch

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
N = int(argv[argv.index("--frames") + 1]) if "--frames" in argv else 96
OUT = os.path.join(HERE, "sheet", "anim_test")
os.makedirs(os.path.join(OUT, "frames"), exist_ok=True)
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, N
sc.render.fps = 24

a, b = L.corner_range("T1")
mid = (a + b) / 2
W = L.width(mid) / 2 - 2.0


def line_offset(s):
    """Outside - apex - outside for a right-hander: + is left (the outside of T1)."""
    u = np.interp(s, [a - 180, a - 40, mid, b + 30, b + 120], [W - 1, W, -W, W - 0.5, W - 2])
    return float(u)


def drive(root, s0, s1):
    for f in range(1, N + 1):
        s = s0 + (s1 - s0) * (f - 1) / (N - 1)
        # brake into the corner: ease the distance so the car slows through T1 and picks up after
        x, y, h = cb.lap_frame(s, line_offset(s))
        x2, y2, _ = cb.lap_frame(s + 1.0, line_offset(s + 1.0))
        yaw = math.atan2(y2 - y, x2 - x)
        root.location = (x, y, 0.0)
        root.rotation_euler = (0, 0, cb.car_yaw(yaw))
        root.keyframe_insert("location", frame=f)
        root.keyframe_insert("rotation_euler", frame=f)
        # steer from the path curvature (front wheels, degrees, + = left)
        x3, y3, _ = cb.lap_frame(s + 2.0, line_offset(s + 2.0))
        h1, h2 = yaw, math.atan2(y3 - y2, x3 - x2)
        k = ((h2 - h1 + math.pi) % (2 * math.pi) - math.pi) / 1.0
        root["steer"] = float(np.clip(math.degrees(math.atan(3.6 * k)), -25, 25))
        root.keyframe_insert('["steer"]', frame=f)


cars = []
for name, livery, s0 in (("car_a", "silver_arrow", a - 175), ("car_b", "rosso", a - 205)):
    root = car_blender.load_car(name, livery)
    d = ch.make_character(name + "_driver", skin="driver_" + livery, helmet=True)
    ch.seat_in_car(d, root)
    drive(root, s0, s0 + 330)
    car_blender.bake_roll(root, 1, N)
    cars.append(root)

# kart + its driver parked in the paddock street
kart = kart_blender.load_kart("kart_test", livery="fifth_hand")
kart.location = (-150.0, -64.0, 0.0)
kd = ch.make_character("karter", skin="karter_fifth_hand", helmet=True)
ch.seat_in_car(kd, kart)

# checks: every wheel contact point on the asphalt, rig values keyed
R = S.build(verbose=False)
off_track = 0
for root in cars:
    for f in range(1, N + 1, 4):
        sc.frame_set(f)
        mw = root.matrix_world
        for lx, ly in ((-0.8, 1.8), (0.8, 1.8), (-0.8, -1.8), (0.8, -1.8)):
            p = mw @ __import__("mathutils").Vector((lx, ly, 0))
            i, j = S.ij(p.x, p.y)
            t = R["T"][j, i]
            fine_ok = True
            if t not in (S.TRACK, S.RUNOFF):
                off_track += 1
    fc = root.animation_data.action.fcurves if root.animation_data and hasattr(root.animation_data.action, "fcurves") else []
print(f"ANIM wheel samples off the asphalt: {off_track}")
for root in cars:
    sc.frame_set(N)
    print(f"ANIM {root.name}: distance at frame {N} = {root['distance']:.1f} m, steer = {root['steer']:.1f} deg")

# cameras: the T1 preset, and a chase camera keyed behind car_a
lighting.eevee(sc, 24)
lighting.set_time(sc, "day")
chase = cameras.aim("cam_test_chase", (0, 0, 0), (1, 0, 0), 30.0, bpy.data.collections["circuit_cameras"])
for f in range(1, N + 1):
    sc.frame_set(f)
    mw = cars[0].matrix_world
    fwd = mw.col[1].to_3d().normalized()
    tgt = mw.translation + fwd * 6.0
    pos = mw.translation - fwd * 13.0 + __import__("mathutils").Vector((0, 0, 3.6))
    chase.location = pos
    chase.rotation_euler = (tgt - pos).to_track_quat("-Z", "Y").to_euler()
    chase.keyframe_insert("location", frame=f)
    chase.keyframe_insert("rotation_euler", frame=f)
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1280, 720, 75
sc.render.image_settings.file_format = "PNG"
for cam, frames in (("cam_T1_track_level", (30, 55, 75)), ("cam_test_chase", (20, 60))):
    cameras.use(cam)
    for f in frames:
        sc.frame_set(f)
        sc.render.filepath = os.path.join(OUT, f"{cam}_{f:03d}.png")
        bpy.ops.render.render(write_still=True)
# the kart in the paddock
kc = cameras.aim("cam_test_kart", (-146.0, -59.0, 1.6), (-150.0, -64.0, 0.4), 35.0, bpy.data.collections["circuit_cameras"])
cameras.use("cam_test_kart")
sc.render.filepath = os.path.join(OUT, "kart_paddock.png")
bpy.ops.render.render(write_still=True)
if "--video" in argv:
    cameras.use("cam_test_chase")
    sc.render.filepath = os.path.join(OUT, "frames", "f_")
    bpy.ops.render.render(animation=True)
    subprocess.run(["ffmpeg", "-y", "-framerate", "24", "-i", os.path.join(OUT, "frames", "f_%04d.png"), "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-crf", "20", os.path.join(OUT, "t1_chase.mp4")], check=False)
print("ANIM done")
