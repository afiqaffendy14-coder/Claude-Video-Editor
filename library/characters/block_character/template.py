"""The master block character: one template, every character. Pure python (no Blender), so tools can import it.

A character is this template plus a skin. Proportions, skin layout and UVs are the standard Minecraft player
model (Java 64x64 skin, two layers, classic 4-pixel or slim 3-pixel arms), so any skin painted in a normal skin
editor works as-is. Units: 1 skin pixel = PX metres (the house world pixel), so the 8-pixel head is 0.36 m and the
character stands 32 px = 1.44 m.

Axes match the car library: +Y forward (the way the character faces), +X the character's right, +Z up, origin on
the ground between the feet.
"""
import math

PX = 0.045

# ---------------------------------------------------------------- parts (pixel units)
# name: box (x0, x1, y0, y1, z0, z1), skin UV origin for layer 1 and layer 2, layer-2 inflation (px per side),
#       bend (z of the joint, bone above, bone below) or a single bone
def parts(model="classic"):
    aw = 3 if model == "slim" else 4
    return {
        "head":  dict(box=(-4, 4, -4, 4, 24, 32), uv=(0, 0), uv2=(32, 0), inflate=0.5, bone="head"),
        "body":  dict(box=(-4, 4, -2, 2, 12, 24), uv=(16, 16), uv2=(16, 32), inflate=0.25, bend=(18, "chest", "hips")),
        "arm_R": dict(box=(4, 4 + aw, -2, 2, 12, 24), uv=(40, 16), uv2=(40, 32), inflate=0.25,
                      bend=(18, "upper_arm.R", "forearm.R")),
        "arm_L": dict(box=(-4 - aw, -4, -2, 2, 12, 24), uv=(32, 48), uv2=(48, 48), inflate=0.25,
                      bend=(18, "upper_arm.L", "forearm.L")),
        "leg_R": dict(box=(0, 4, -2, 2, 0, 12), uv=(0, 16), uv2=(0, 32), inflate=0.25, bend=(6, "thigh.R", "shin.R")),
        "leg_L": dict(box=(-4, 0, -2, 2, 0, 12), uv=(16, 48), uv2=(0, 48), inflate=0.25, bend=(6, "thigh.L", "shin.L")),
    }


BEND_BAND = 1.0  # px either side of a joint that blends between the two bones (Mine-imator style bend)
BEND_RINGS = 5   # edge loops across the band: more = rounder outer corner
# Joints hinge on the INSIDE face of the bend (front of the elbow and waist, back of the knee), so the inside
# never folds into itself; the outside rounds off over the band. Bends only go one way: keep elbow/knee/waist >= 0.

# ---------------------------------------------------------------- bones (pixel units): head, tail, parent
def bones(model="classic"):
    ax = 5.5 if model == "slim" else 6.0  # arm centre line
    b = {
        "hips":  ((0, 0, 12), (0, 0, 18), None),
        "chest": ((0, 2, 18), (0, 0, 24), "hips"),            # hinge on the front of the waist
        "head":  ((0, 0, 24), (0, 0, 32), "chest"),
    }
    for s, k in ((1, "R"), (-1, "L")):
        b[f"upper_arm.{k}"] = ((s * ax, 0, 22), (s * ax, 0, 18), "chest")   # shoulder pivot 2 px below the top
        b[f"forearm.{k}"] = ((s * ax, 2, 18), (s * ax, 0, 13.5), f"upper_arm.{k}")  # hinge front; tail = hand centre
        b[f"thigh.{k}"] = ((s * 2, 0, 12), (s * 2, 0, 6), "hips")
        b[f"shin.{k}"] = ((s * 2, -2, 6), (s * 2, 0, 0), f"thigh.{k}")     # hinge at the back; tail = sole
    return b


# ---------------------------------------------------------------- faces (expressions)
# Each skin gets an atlas of front faces, one 8x8 tile per expression; root["face"] picks the tile (keyable).
EXPRESSIONS = ["neutral", "smile", "grin", "frown", "angry", "worried", "surprised", "shout", "blink",
               "look_left", "look_right"]

# ---------------------------------------------------------------- poses
# A pose is a dict of friendly joint values in degrees (missing keys = standing straight):
#   lean (whole body forward, + = forward, - = recline), twist (+ = turn left), crouch (metres down),
#   waist (+ = bend forward), head (turn + left, nod + down, tilt + to its left),
#   arm_L / arm_R (fwd + = raise forward, out + = away from the body, twist), elbow_L / elbow_R (+ = bend),
#   leg_L / leg_R (fwd + = forward, out + = away), knee_L / knee_R (+ = bend).
POSES = {
    "stand": {},
    "idle": dict(arm_L=(3, 4, 0), arm_R=(-2, 4, 0), elbow_L=6, elbow_R=4, head=(6, 2, 0)),
    "walk": dict(arm_L=(-28, 3, 0), arm_R=(28, 3, 0), elbow_L=8, elbow_R=14, leg_L=(26, 0), leg_R=(-26, 0),
                 knee_R=12, head=(0, 2, 0)),
    "run": dict(lean=12, arm_L=(-55, 6, 0), arm_R=(60, 6, 0), elbow_L=70, elbow_R=85, leg_L=(48, 0), leg_R=(-40, 0),
                knee_L=40, knee_R=75, crouch=0.03, head=(0, -10, 0)),
    "sit": dict(crouch=0.27, leg_L=(90, 3), leg_R=(90, 3), knee_L=90, knee_R=90, arm_L=(28, 4, 0),
                arm_R=(28, 4, 0), elbow_L=30, elbow_R=30),
    "wave": dict(arm_R=(12, 82, 90), elbow_R=95, arm_L=(4, 4, 0), head=(-10, -4, 6), twist=-8),
    "point": dict(arm_R=(88, 6, 0), arm_L=(6, 6, 0), elbow_L=10, head=(-8, 0, 0), twist=-10, waist=-3),
    "cheer": dict(arm_L=(170, 18, 0), arm_R=(170, 18, 0), elbow_L=8, elbow_R=8, head=(0, -18, 0), lean=-4),
    "think": dict(arm_R=(62, -12, 0), elbow_R=118, arm_L=(30, -18, 0), elbow_L=75, head=(8, 14, 8), waist=4),
    "shrug": dict(arm_L=(14, 34, 0), arm_R=(14, 34, 0), elbow_L=80, elbow_R=80, head=(0, 0, 12)),
    "fist_pump": dict(arm_R=(160, 14, 0), elbow_R=12, arm_L=(30, 10, 0), elbow_L=90, lean=-6, head=(0, -14, 0),
                      leg_L=(10, 6), leg_R=(-6, 6)),
    # sat in the F1 car: reclined at the house cockpit angle; hands go on the wheel with ik_hand / seat_in_car
    "driver": dict(lean=-52, head=(0, 46, 0), leg_L=(46, 2), leg_R=(46, 2), knee_L=6, knee_R=6,
                   arm_L=(70, 10, 0), arm_R=(70, 10, 0), elbow_L=40, elbow_R=40),
    # go-kart: sat up 20 degrees back, knees either side of the steering column, feet on the pedals
    "kart": dict(lean=-20, head=(0, 16, 0), leg_L=(92, 10), leg_R=(92, 10), knee_L=52, knee_R=52,
                 arm_L=(55, 12, 0), arm_R=(55, 12, 0), elbow_L=30, elbow_R=30),
}

# degrees -> rotation about character axes (x, y, z), applied in the parent's frame
def joint_rotations(p):
    """Friendly pose dict -> {bone: [(axis, degrees), ...]} applied left to right (outermost first)."""
    g = lambda k, n, d=0.0: tuple(p.get(k, (d,) * n)) if n > 1 else p.get(k, d)
    out = {}
    out["hips"] = [("Z", g("twist", 1)), ("X", -g("lean", 1))]
    out["chest"] = [("X", -g("waist", 1))]
    turn, nod, tilt = g("head", 3)
    out["head"] = [("Z", turn), ("X", -nod), ("Y", -tilt)]
    for k, sgn in (("L", 1), ("R", -1)):
        fwd, outw, tw = (tuple(p.get("arm_" + k, (0, 0, 0))) + (0, 0, 0))[:3]
        out[f"upper_arm.{k}"] = [("X", fwd), ("Y", sgn * outw), ("Z", sgn * tw)]
        out[f"forearm.{k}"] = [("X", p.get("elbow_" + k, 0.0))]
        lf, lo = (tuple(p.get("leg_" + k, (0, 0))) + (0, 0))[:2]
        out[f"thigh.{k}"] = [("X", lf), ("Y", sgn * lo)]
        out[f"shin.{k}"] = [("X", -p.get("knee_" + k, 0.0))]
    return out


def rot3(axis, deg):
    """3x3 rotation matrix (row-major lists) about a character axis."""
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    if axis == "X":
        return [[1, 0, 0], [0, c, -s], [0, s, c]]
    if axis == "Y":
        return [[c, 0, s], [0, 1, 0], [-s, 0, c]]
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]
