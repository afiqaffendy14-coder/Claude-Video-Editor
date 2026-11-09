"""Animation test for "Phone me in nine years": renders every frame of the 22 shots (30 fps, 48.30 s).

Each shot (or part of a shot) builds its set and every prop once, voxelises them, then for each frame:
  - moves what moves (karts, cars, the book, the trophy, the flag, the rain, the camera),
  - rebuilds the people in a pose that changes continuously with time (IK keeps hands on what they touch),
  - renders, and deletes the people again.
Motion never holds still: breathing, small head turns, eased moves between the storyboard's key poses.

Run: blender -b --factory-startup --python blender/ham_anim.py -- <frames_dir> [shot ids...]   (frames f00000.png)
     ENGINE=eevee|cycles (default cycles), SAMPLES (default 16), PCT (resolution %, default 50 of 1080x1920)
     CHECK=1 runs the collision check on three frames per part and writes out/anim_check.json
Frames already on disk are skipped, so a stopped render picks up where it left off.
"""
import json, math, os, random, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from mathutils import Matrix, Vector
import lib
from lib import V, reset, palette, setup_render, camera, box
import sets as S
import halo_sets as H
import ham_sets as A
from ham_sets import KID, TEEN, BOSS
import voxel
import ik
import people

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 30
TIMING = json.load(open(os.path.join(ROOT, "tools", "timing.json")))
WORDS = [w for l in TIMING["lines"] for w in l["words"]]
END = 48.30 + 5 / 30
# exposure per shot (stops): the boards' 0.4, lifted where the night interiors read too dark, eased on the white garage
EXPO = {1: 0.95, 2: 1.35, 3: 0.55, 4: 0.5, 5: 0.9, 6: 1.25, 7: 0.4, 21: 0.9, 19: 0.4, 20: 0.45}
EXPO_PART = {"1a": 0.35, "7c": 1.25, "19b": -0.35}


# ---------------------------------------------------------------- small maths
def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def ramp(t, a, b):
    """0 before a, 1 after b, eased between."""
    return ease((t - a) / max(1e-6, b - a))


def mix(a, b, w):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a + (b - a) * w
    if isinstance(a, (tuple, list)):
        return tuple(mix(x, y, w) for x, y in zip(a, b))
    return b if w > 0.5 else a


def mixpose(p, q, w):
    """Blend two poses (missing keys fall back to standing)."""
    P = {**voxel.STAND, **p}
    Q = {**voxel.STAND, **q}
    out = {}
    for k in set(P) | set(Q):
        out[k] = mix(P.get(k, Q.get(k)), Q.get(k, P.get(k)), w)
    return out


def wobble(t, f, a, ph=0.0):
    return a * math.sin(2 * math.pi * f * t + ph)


def lerpv(a, b, w):
    return tuple(x + (y - x) * w for x, y in zip(a, b))


def word(text, after=0.0):
    """Start time of a spoken word (first match after `after`)."""
    for w in WORDS:
        if w["start"] >= after - 1e-3 and w["w"].strip(",.:;'\"").lower() == text.lower():
            return w["start"]
    raise KeyError(text)


def alive(p, t, ph=0.0, head=1.0):
    """Breathing and small head turns, so nobody freezes."""
    p = dict(p)
    h = p.get("head", (0, 0))
    p["head"] = (h[0] + head * wobble(t, 0.23, 3.0, ph), h[1] + head * wobble(t, 0.31, 1.5, ph + 1))
    p["lean"] = p.get("lean", 0) + wobble(t, 0.27, 0.8, ph + 2)
    return p


def solve(name, x, y, rot, pose, z=0.0, scale=1.0, hands=None, feet=None):
    pose = dict(S.POSE[pose]) if isinstance(pose, str) else dict(pose)
    if hands or feet:
        try:
            pose = ik.reach(pose, (x, y, z), rot, hands=hands, feet=feet, scale=scale)
        except ValueError as e:
            print(f"REACH {name}: {e}", flush=True)
            pose = ik.reach(pose, (x, y, z), rot, hands=hands, feet=feet, scale=scale, tol=9.0)
    return pose


def person(name, x, y, rot, pose, outfit, z=0.0, scale=1.0, hands=None, feet=None):
    p = solve(name, x, y, rot, pose, z, scale, hands, feet)
    return people.person(name, (x, y, z), rot, p, outfit, scale=scale)


def cam(loc, target, lens=35, dof=None, fstop=2.8, roll=0.0):
    camera(V(loc), V(target), lens, dof, fstop, roll)


def head_point(build, name, off):
    """A point in a person's head frame (local +Y out of the face, +Z up, origin at the head's centre), found by
    building a throwaway copy of them in the same pose (arms don't move the head)."""
    root = build(name + "_probe")
    bpy.context.view_layer.update()
    h = bpy.data.objects[name + "_probe_head"]
    p = h.matrix_world @ V(off)
    for o in [root] + list(root.children_recursive):
        bpy.data.objects.remove(o, do_unlink=True)
    return p


LIVERY = {"redm": "rosso", "green_it": "silver_arrow", "grey": "midnight", "orange": "papaya"}


def shake(t, amp=0.004, ph=0.0):
    return (wobble(t, 0.9, amp, ph) + wobble(t, 2.3, amp * 0.4, ph + 1), 0.0, wobble(t, 1.3, amp, ph + 2))


def addv(a, b):
    return tuple(x + y for x, y in zip(a, b))


def spin_wheels(root, dist):
    """The library kart's round wheels roll with the distance travelled."""
    A.kart_roll(root, dist)


# ---------------------------------------------------------------- shot parts
class Part:
    """One continuous piece of a shot: a set built once, then a frame function. Shot 6, 16 and 19 have two parts
    (a jump in time inside the shot); shot 7 has three stacked panels rendered at 540x320 each."""

    def __init__(self, shot, label, t0, t1, static, frame, res=(1080, 1920), panel=None):
        self.shot, self.label, self.t0, self.t1 = shot, label, t0, t1
        self.static, self.frame, self.res, self.panel = static, frame, res, panel


PARTS = []


def part(shot, label, t0, t1, res=(1080, 1920), panel=None):
    def deco(cls):
        PARTS.append(Part(shot, label, t0, t1, cls.static, cls.frame, res, panel))
        return cls
    return deco


FS = 5 / 30  # round 5: 5 frames of air before "At the track" (tools/shift_after.py); times after 16.95 s move by FS
SHOT_T = {1: (0.00, 3.51), 2: (3.51, 6.39), 3: (6.39, 8.12), 4: (8.12, 10.55), 5: (10.55, 12.28), 6: (12.28, 14.45), 7: (14.45, 17.07 + FS), 8: (17.07 + FS, 19.72 + FS), 9: (19.72 + FS, 22.47 + FS), 10: (22.47 + FS, 25.77 + FS), 11: (25.77 + FS, 28.87 + FS), 12: (28.87 + FS, 30.53 + FS), 13: (30.53 + FS, 31.18 + FS), 14: (31.18 + FS, 32.01 + FS), 15: (32.01 + FS, 32.79 + FS), 16: (32.79 + FS, 35.31 + FS), 17: (35.31 + FS, 38.35 + FS), 18: (38.35 + FS, 40.08 + FS), 19: (40.08 + FS, 43.04 + FS), 20: (43.04 + FS, 45.10 + FS), 21: (45.10 + FS, 46.28 + FS), 22: (46.28 + FS, END)}


def whole(n, **kw):
    return part(n, "", SHOT_T[n][0], SHOT_T[n][1], **kw)


def split(n, label, w0, w1, **kw):
    a, b = SHOT_T[n]
    return part(n, label, a + (b - a) * w0, a + (b - a) * w1, **kw)


# ---------------------------------------------------------------- 1995: the ask (meeting frame turned side-on)
TURN = Matrix.Rotation(math.radians(-90), 4, "Z")
BOSS_XY = (0.0, 0.62)


def turn(objs):
    bpy.context.view_layer.update()
    for ob in objs:
        if not ob.parent:
            ob.matrix_world = TURN @ ob.matrix_world
    bpy.context.view_layer.update()


def boss_person(pose, hands=None, outfit="dennis_tux"):
    return person("dennis", BOSS_XY[0], BOSS_XY[1], 180, pose, outfit, scale=BOSS, hands=hands)


def s01_people(ctx, t, lift, reach):
    """The ask, in the meeting frame: the boy holds the book up (lift: how high), the boss leans in and reaches."""
    b = ctx["book"]
    c = (0.0, -0.17, 0.98 + lift + wobble(t, 1.1, 0.004))
    # bigger than life and turned toward the camera, so the red book reads in the first frame
    b.matrix_world = Matrix.Translation(V(c)) @ Matrix.Rotation(math.radians(22), 4, "Y") @ Matrix.Rotation(math.radians(-55), 4, "X") @ Matrix.Scale(1.4, 4)
    bpy.context.view_layer.update()
    M = b.matrix_world
    kp = alive(dict(S.POSE["offer"], head=(0, -12 - 6 * lift / 0.06)), t, 0.3, 0.5)
    kid = person("boy", 0.0, -0.42, 0, kp, "boy_blazer", z=0.03 * lift / 0.06, scale=KID,
                 hands={"L": tuple(M @ V((0.118, -0.03, -0.04))), "R": tuple(M @ V((-0.118, -0.03, -0.04)))})
    bp = mixpose(dict(S.POSE["look_down"], head=(0, 14)), dict(S.POSE["look_down"], head=(0, 26), lean=10,
                                                                   armL=(48, -4, 55)), reach)
    dn = boss_person(alive(bp, t, 1.0, 0.6))
    turn([b, kid, dn])


def s01_static(ctx):
    A.awards_set()
    A.lamp_point("aw_lift", (1.2, -1.6, 1.6), 25, (1.0, 0.85, 0.7), 0.6)  # a soft lift on the pair's faces
    A.lamp_point("aw_lift2", (-1.4, 0.9, 1.5), 8, (1.0, 0.85, 0.7), 0.6)
    ctx["book"] = A.book("book")


@split(1, "a", 0.0, 0.5)
class S01a:
    """First frame = the hook: over the towering boss's shoulder, looking down at the tiny boy holding the book up
    to him. The camera pans off the book onto the boy and settles with him in the middle of the frame."""
    static = s01_static

    def frame(ctx, t, k):
        s01_people(ctx, t, 0.06 * ramp(t, 0.2, 1.2), 0.0)
        e = ease(k)
        tgt = lerpv((-0.2, 0.05, 1.38), (-0.42, 0.0, 1.24), e)
        cam(addv((1.45 - 0.1 * e, 1.2 - 0.06 * e, 2.1 - 0.05 * e), shake(t, 0.002)), tgt, 42, 2.3, 8.0)


@split(1, "b", 0.5, 1.0)
class S01b:
    """Side on (the storyboard's hook framing): the boy on his toes, the boss leaning down and reaching for the
    book. The camera arcs in."""
    static = s01_static

    def frame(ctx, t, k):
        s01_people(ctx, t + 1.76, 0.06, ramp(t, 0.1, 1.6))
        e = ease(k)
        cam(addv((0.45 - 0.35 * e, -3.0 + 0.3 * e, 0.6 + 0.04 * e), shake(t, 0.003)), (0.12, 0.0, 1.55), 28, 2.9, 3.2)


def writing_book(ctx, page):
    b = ctx.get("book")
    if not b or ctx.get("page") != page:
        if b:
            for o in [b] + list(b.children_recursive):
                bpy.data.objects.remove(o, do_unlink=True)
        b = A.book("book", True, page)
        dyn_texture(b)
        ctx["book"], ctx["page"] = b, page
    return b


def place_book(b, t):
    c = (0.04, 0.26, 1.3 + wobble(t, 0.7, 0.004))
    b.matrix_world = Matrix.Translation(V(c)) @ Matrix.Rotation(math.radians(180), 4, "Z") @ Matrix.Rotation(math.radians(-38), 4, "X")
    bpy.context.view_layer.update()
    return b.matrix_world


# nib positions on the written page (book frame), word by word: the pen ends each word as it is spoken
def page_xy(px, py):
    return (0.104 + (px / 1024 - 0.5) * 0.2, (0.5 - py / 768) * 0.15)


NIB = [page_xy(110, 250), page_xy(470, 255), page_xy(640, 255), page_xy(840, 255), page_xy(330, 450), page_xy(700, 450),
       page_xy(880, 620)]


def pen_at(ctx, M, nib_local, lift=0.0):
    p = ctx["pen"]
    nib = M @ V((nib_local[0], nib_local[1], 0.012 + lift))
    grip = nib + M.to_3x3() @ V((0.12, -0.13, 0.06))  # the hand sits off the page's lower-right corner
    d = (grip - nib).normalized()
    p.location = tuple(nib + d * 0.07)  # the pen runs from the nib up into the hand
    p.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    bpy.context.view_layer.update()
    return grip


def unturn_all(objs):
    """Put the meeting-frame objects back before they are re-placed this frame."""
    for ob in objs:
        if ob and not ob.parent:
            ob.matrix_world = TURN.inverted() @ ob.matrix_world


@whole(2)
class S02:
    def static(ctx):
        A.awards_set()
        A.lamp_point("aw_lift", (-0.3, -0.6, 1.9), 30, (1.0, 0.85, 0.7), 0.5)
        ctx["pen"] = A.pen("pen")

    def frame(ctx, t, k):
        page = "page_0"
        b = writing_book(ctx, page)
        M = place_book(b, t)
        # the pen comes to the page and makes the first stroke at the start of the line
        w = ramp(t, 0.4, 2.0)
        nib = mix((NIB[0][0] - 0.03, NIB[0][1] + 0.02), NIB[0], w)
        grip = pen_at(ctx, M, nib, 0.02 * (1 - w) + 0.004 * max(0, math.sin(t * 9)))
        pose = alive(dict(S.POSE["write"], head=(0, 22 + 6 * w)), t, 0.4, 0.4)
        dn = boss_person(pose, hands={"R": tuple(M @ V((-0.18, -0.02, -0.01))), "L": tuple(grip)})
        kid = person("boy", -0.26, -0.36, 10, alive(S.POSE["tiptoe"], t, 2.0), "boy_blazer", scale=KID)
        turn([b, ctx["pen"], dn, kid])
        cam(addv((-0.8 + 0.08 * k, -0.5 + 0.05 * k, 1.02), shake(t, 0.002)), (0.5, 0.05, 1.42), 30 + 4 * k, 1.45, 2.8)

    def after(ctx):
        unturn_all([ctx.get("book"), ctx["pen"]])


@whole(3)
class S03:
    def static(ctx):
        A.awards_set()
        ctx["pen"] = A.pen("pen")

    def frame(ctx, t, k):
        T = SHOT_T[3][0] + t
        times = [word("phone", 6.0), word("me", 6.5), word("in", 6.8), word("nine", 7.0), word("years", 7.3)]
        times.append(times[-1] + 0.32)  # the signature, right after "years"
        n = sum(1 for x in times if T >= x)
        b = writing_book(ctx, f"page_{n}")
        M = place_book(b, t)
        if n == 0:
            nib = NIB[0]
        else:  # the pen travels to the end of the word that is being written
            i = min(n, len(NIB) - 1)
            a = times[n - 1]
            z = times[n] if n < len(times) else a + 0.4
            nib = mix(NIB[i - 1], NIB[i], ease((T - a) / max(0.05, z - a)))
        grip = pen_at(ctx, M, nib, 0.0)
        dn = boss_person(alive(dict(S.POSE["write"], head=(0, 28)), t, 0.4, 0.3),
                         hands={"R": tuple(M @ V((-0.18, -0.02, -0.01))), "L": tuple(grip)})
        turn([b, ctx["pen"], dn])
        M = b.matrix_world
        nrm = M.to_3x3() @ V((0, 0, 1))
        c = M @ V((0.09, 0.0, 0.0))
        cpos = c + nrm * (0.52 - 0.04 * k)
        cam(tuple(cpos), tuple(c), 35, (cpos - c).length, 4.0)
        cm = bpy.data.objects["cam"]
        up = M.to_3x3() @ V((0, 1, 0))
        d = (c - cpos).normalized()
        cm.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()
        cy = cm.matrix_world.to_3x3() @ V((0, 1, 0))
        cm.rotation_euler.rotate_axis("Z", -math.atan2(cy.cross(up).dot(d), cy.dot(up)))
        L = bpy.data.objects.get("page_light") or A.spot("page_light", (0, 0, 0), (0, 0, 0), 60, 30, 0.6, (1, 0.9, 0.75), 0.1)
        L.location = tuple(c + nrm * 0.6 + V((0, -0.3, 0.3)))
        A.look_at(L, tuple(c))

    def after(ctx):
        unturn_all([ctx.get("book"), ctx["pen"]])


# ---------------------------------------------------------------- home
@whole(4)
class S04:
    def static(ctx):
        A.kitchen_set()

    def frame(ctx, t, k):
        w = ramp(t, 0.6, 1.1) * (1 - ramp(t, 1.8, 2.2))  # the heel of his hand to his eye, rubbing, then down
        pose = alive(dict(S.POSE["slump"], lean=14, head=(0, 14 + 4 * w)), t, 0.2, 0.3)
        eye = head_point(lambda n: A.seated(n, 0.05, -0.74, 0, pose, "dad", 0.475, ()), "dad",
                         (-0.085 + 0.02 * math.sin(2 * math.pi * 2.2 * t), 0.25, 0.035))
        hR = lerpv((-0.12, -0.34, 0.825), tuple(eye), w)
        A.seated("dad", 0.05, -0.74, 0, pose, "dad", 0.475, (), hands={"L": (0.2, -0.32, 0.825), "R": hR})
        person("boy", -2.62 + 0.05 * ramp(t, 0.8, 2.2), -1.25, -90 - 8 * ramp(t, 0.8, 2.2), alive(S.POSE["doorway"], t, 1.2),
               "boy_home", scale=KID)
        cam((0.55 - 0.12 * k, 1.2 - 0.12 * k, 1.15), (-0.85, -0.75, 1.0), 26, 2.0 - 0.15 * k, 4.0)


# ---------------------------------------------------------------- the shed
@whole(5)
class S05:
    def static(ctx):
        A.shed_set("battered", book_on_wall=False)

    def frame(ctx, t, k):  # the whole kart, three-quarter from the front, a slow push in
        e = ease(k)
        cam((1.62 - 0.32 * e, -1.5 + 0.28 * e, 1.42 - 0.06 * e), (0.0, 0.25, 0.5), 30, 2.3, 4.0)


KNEEL = dict(crouch=0.355, lean=40, legL=(0, 6, 90), legR=(0, 6, 90), head=(0, 20))


def pod_top(ctx, x, y):
    """Height of the kart's top surface under (x, y) (ray cast straight down)."""
    key = ("pod", round(x, 2), round(y, 2))
    if key not in ctx:
        dg = bpy.context.evaluated_depsgraph_get()
        hit, loc, *_ = bpy.context.scene.ray_cast(dg, V((x, y, 1.0)), V((0, 0, -1)))
        ctx[key] = loc.z if hit else 0.2
    return ctx[key]


def sanding(ctx, t, lean=40):
    s = wobble(t, 2.2, 0.09)  # the sanding block goes back and forth along the side pod
    p = dict(KNEEL, lean=lean + wobble(t, 2.2, 2.0, 0.6))
    z = pod_top(ctx, 0.1, -0.22) + 0.05
    return p, {"L": (0.22 + s, -0.26, z), "R": (-0.02 + s, -0.26, z)}


@split(6, "a", 0.0, 0.5)
class S06a:
    """The dad kneels at the rear wheel and tightens its nut with a spanner: pull, reset, pull."""
    def static(ctx):
        A.shed_set("battered")
        A.lamp_point("sh_lift", (-1.2, -1.2, 1.4), 22, (1, 0.8, 0.6), 0.5)
        ctx["spanner"] = A.spanner("spanner")

    def frame(ctx, t, k):
        hub = bpy.data.objects["sh_kart_wheel_RR"].matrix_world.translation
        nut = V((hub.x, hub.y - 0.1, hub.z))           # on the outside of the hub, toward him (-Y)
        u = (t * 1.25) % 1.0                           # pull (0.6 of the cycle), then reset the spanner
        phi = mix(132, 78, ease(u / 0.6)) if u < 0.6 else mix(78, 132, ease((u - 0.6) / 0.4))
        r = math.radians(phi)
        d = V((math.cos(r), 0, math.sin(r)))
        sp = ctx["spanner"]
        y = V((0, 1, 0))
        sp.matrix_world = Matrix.Translation(nut) @ Matrix((d, y, d.cross(y))).transposed().to_4x4()
        bpy.context.view_layer.update()
        grip = nut + d * 0.19 + V((0, -0.035, 0))
        effort = math.sin(math.pi * min(1.0, u / 0.6)) if u < 0.6 else 0.0
        p = dict(KNEEL, lean=16 + 4 * effort, head=(-6, 26))
        person("dad", hub.x + 0.32, hub.y - 0.48, 22, alive(p, t, 0.3, 0.2), "dad", hands={"R": tuple(grip)})
        A.allow("dad", "spanner", "spanner_ring", "spanner_shaft")
        cam((-2.0 + 0.06 * k, -2.25 + 0.08 * k, 1.35), (-0.3, -0.5, 0.55), 28, 2.4, 5.6)


@split(6, "b", 0.5, 1.0)
class S06b:
    def static(ctx):
        A.shed_set("new")
        A.lamp_point("sh_lift", (1.2, 1.0, 1.6), 22, (1, 0.8, 0.6), 0.5)

    def frame(ctx, t, k):
        p = alive(dict(S.POSE["stand_by"], head=(0, 14 - 4 * k), face="smile" if k > 0.4 else "neutral"), t, 0.5)
        person("dad", -1.05, -1.0, -30, p, "dad")
        cam((1.65 - 0.15 * k, 1.35 - 0.1 * k, 1.5), (-0.2, -0.45, 0.6), 28, 2.4, 4.0)


# ---------------------------------------------------------------- several jobs: three stacked panels
@split(7, "a", 0.0, 1.0, res=(1080, 640), panel=0)
class S07a:
    def static(ctx):
        A.office_job_set()

    def frame(ctx, t, k):
        tap = lambda ph: 0.012 * max(0.0, math.sin(2 * math.pi * 4.5 * t + ph))
        A.seated("dad", 0.0, -0.1, 0, alive(S.POSE["desk"], t, 0.1, 0.5), "dad_office", 0.5, (),
                 hands={"L": (0.12, 0.3, 0.815 + tap(0)), "R": (-0.12, 0.3, 0.815 + tap(1.7))})
        cam((1.55 - 0.1 * k, -1.35, 1.45), (-0.05, 0.55, 1.2), 28)


@split(7, "b", 0.0, 1.0, res=(1080, 640), panel=1)
class S07b:
    """18:00: he knocks an estate agent's FOR SALE board into a front lawn with a mallet."""
    def static(ctx):
        A.street_job_set()
        ctx["hammer"] = A.hammer("hammer")

    def frame(ctx, t, k):
        # The hammer is rigid in his right hand. The hand moves on an arc around his right shoulder in the plane
        # of the post (shoulder rotation + a slight elbow bend), the hammer follows the forearm at a fixed angle.
        # One strike every 0.8 s: preparation 0.15, backswing 0.25, downswing 0.15, impact 0.05, recovery 0.2.
        fwd, up = V((-1, 0, 0)), V((0, 0, 1))         # he faces -X; the post is in front of his right shoulder
        nrm = fwd.cross(up)
        sh = V((A.POST[0] + 0.576, A.POST[1], 1.31))   # his right shoulder joint
        dx, dy = sh.x, A.POST[1] + 0.30               # where he stands (feet planted all shot)
        imp = (-50.0, 0.46)                            # (angle, reach) of the hand at impact

        def hand_at(th, rr):
            a = math.radians(th)
            return sh + (fwd * math.cos(a) + up * math.sin(a)) * rr

        u = ((t + 0.25) % 0.8) / 0.8 * 0.8
        if u < 0.15:                                   # preparation: settle above and behind the impact point
            th, rr = mix(-38, -30, ease(u / 0.15)), 0.44
        elif u < 0.40:                                 # backswing: up and back around the shoulder
            x = ease((u - 0.15) / 0.25)
            th, rr = mix(-30, 100, x), mix(0.44, 0.40, x)
        elif u < 0.55:                                 # downswing: accelerating, easing just before contact
            x = (u - 0.40) / 0.15
            x = x * x * (2.2 - 1.2 * x)
            th, rr = mix(100, imp[0], x), mix(0.40, imp[1], x)
        elif u < 0.60:                                 # impact: the face rests on the post top
            th, rr = imp
        else:                                          # recovery: a small recoil, then lift away
            x = ease((u - 0.60) / 0.20)
            th, rr = mix(imp[0], -38, x), mix(imp[1], 0.44, x)
        hand = hand_at(th, rr)
        down = max(0.0, min(1.0, (100 - th) / (100 - imp[0])))
        pose = dict(S.POSE["stand_by"], lean=2 + 6 * down, head=(0, 22), armL=(8, 6, 14))
        if "ham_alpha" not in ctx:                     # the hammer's fixed angle to his forearm, set at impact
            probe = person("dad_probe", dx, dy, 90, pose, "dad_hivis", hands={"R": tuple(hand_at(*imp))})
            bpy.context.view_layer.update()
            fa = bpy.data.objects["dad_probe_faR"].matrix_world.to_3x3() @ V((0, 0, -1))
            ctx["ham_alpha"] = math.atan2(nrm.dot(fa.cross(fwd)), fa.dot(fwd))
            for o in [probe] + list(probe.children_recursive):
                bpy.data.objects.remove(o, do_unlink=True)
        person("dad", dx, dy, 90, alive(pose, t, 0.7, 0.15), "dad_hivis", hands={"R": tuple(hand)})
        bpy.context.view_layer.update()
        fa = (bpy.data.objects["dad_faR"].matrix_world.to_3x3() @ V((0, 0, -1))).normalized()
        hx = (Matrix.Rotation(ctx["ham_alpha"], 3, nrm) @ fa).normalized()
        hz = (Matrix.Rotation(math.radians(-90), 3, nrm) @ hx).normalized()   # the striking face
        hy = hz.cross(hx)
        hb = bpy.data.objects["dad_handR"]
        bb = [hb.matrix_world @ V(c) for c in hb.bound_box]
        hc = sum(bb, V((0, 0, 0))) / 8
        ctx["hammer"].matrix_world = Matrix.Translation(hc) @ Matrix((hx, hy, hz)).transposed().to_4x4()
        A.allow("dad", "hammer", "hammer_handle", "hammer_head")
        hit = 0.55 <= u < 0.62
        view = os.environ.get("HAMCAM", "")
        if view == "front":
            cam((dx - 2.6, dy - 0.1, 1.3), (dx - 0.3, dy - 0.15, 1.15), 30)
        elif view == "q":
            cam((dx - 1.9, dy - 1.9, 1.6), (dx - 0.3, dy - 0.2, 1.1), 30)
        else:
            cam(addv((0.85, -2.45, 1.3), shake(t, 0.006 if hit else 0.0015)), (0.85, 0.75, 1.18), 30)


def mat_cached(name, col):
    return bpy.data.materials.get(name) or lib.mat(name, col, 0.8)


@split(7, "c", 0.0, 1.0, res=(1080, 640), panel=2)
class S07c:
    """23:00: he scrubs plates at a restaurant sink after closing."""
    def static(ctx):
        A.dish_job_set()
        ctx["plate"] = A.plate("held_plate")
        ctx["plate"]["smooth"] = True  # moved every frame: keep it as one object (not re-voxelised)
        ctx["sponge"] = A.sponge("sponge")

    def frame(ctx, t, k):  # from over the sink: he scrubs a plate held over the basin, the yellow sponge circling
        c = V((0.0, 0.5 + wobble(t, 0.5, 0.02), 1.07 + wobble(t, 0.6, 0.008)))  # under the running tap
        n = V((0.15, -0.35, 1.0)).normalized()  # tipped toward him, as you hold a plate to scrub it
        rot = n.to_track_quat("Z", "Y").to_matrix().to_4x4()
        ctx["plate"].matrix_world = Matrix.Translation(c) @ rot
        u_ax, v_ax = rot.to_3x3() @ V((1, 0, 0)), rot.to_3x3() @ V((0, 1, 0))
        ph = 2 * math.pi * 2.4 * t
        sp = c + n * 0.027 + u_ax * 0.06 * math.cos(ph) + v_ax * 0.05 * math.sin(ph)
        ctx["sponge"].matrix_world = Matrix.Translation(sp) @ rot
        bpy.context.view_layer.update()
        p = alive(dict(S.POSE["stand_by"], lean=10, head=(0, 26), face="neutral"), t, 0.4, 0.3)
        person("dad", 0.08, 0.07, 0, p, "dad_apron", hands={"L": tuple(max((c + u_ax * 0.2, c - u_ax * 0.2), key=lambda q: q.x) - n * 0.01), "R": tuple(sp + n * 0.062)})
        A.allow("dad", "held_plate", "sponge")
        cam((0.78 - 0.04 * k, 0.8, 1.66), (-0.04, 0.16, 1.08), 18)


# ---------------------------------------------------------------- the kart track
ROW = [(-1.2, "kid_red", "redm"), (0.9, "kid_green", "green_it"), (3.0, "boy", None), (5.1, "kid_grey", "grey"),
       (-3.3, "kid_yellowsuit", "orange")]


def helmet_carry(ctx, name, x, y, rot, t, outfit="boy_suit", pose="helmet_hold", ph=0.0, head=None):
    import props
    key = name + "_helmet"
    if key not in ctx:
        hl = props.helmet(key, "white", "kartblue")
        hl.scale = (KID, KID, KID)
        ctx[key] = hl
    hl = ctx[key]
    Mp = Matrix.Translation(V((x, y, 0))) @ Matrix.Rotation(math.radians(rot), 4, "Z")
    sw = wobble(t, 0.5, 0.012, ph)
    grip = Mp @ V((0.3, 0.03 + sw, 0.6))
    hl.location = tuple(grip - V((0, 0, 0.38 * KID)))
    hl.rotation_euler = (0, 0, math.radians(rot))
    p = alive(dict(S.POSE[pose], **({"head": head} if head else {})), t, ph)
    return person(name, x, y, rot, p, outfit, scale=KID, hands={"L": tuple(grip)})


@whole(8)
class S08:
    def static(ctx):
        A.kart_track_set()
        for x, who, col in ROW:
            A.kart(f"k_{who}", "new", (x, 0.35, 0.0), 180, livery=LIVERY.get(col))

    def frame(ctx, t, k):
        rnd = random.Random(4)
        for i, (x, who, col) in enumerate(ROW):
            r = 180 + rnd.choice([-10, 0, 15])
            if who == "boy":
                helmet_carry(ctx, "boy", x, -1.25, 180, t, head=(0, 4 + 6 * k))
            else:
                person(who, x, -1.2, r, alive(S.POSE["stand_by"], t, i * 1.3), who, scale=KID)
        for i, (x, y, r, o) in enumerate(((-2.0, 2.2, 160, "parent_a"), (2.0, 2.6, 200, "parent_b"), (4.2, 2.3, 190, "parent_c"))):
            person(f"parent{i}", x, y, r, alive(S.POSE["watch"], t, i), o)
        cam((-0.2 + 0.5 * k, -4.6 + 0.2 * k, 1.05), (2.0 + 0.3 * k, -0.8, 0.75), 30, 5.0, 5.6)


@whole(9)
class S09:
    def static(ctx):
        A.kart_track_set()
        A.kart("k_boy", "new", (2.0, 0.3, 0.0), 10)

    def frame(ctx, t, k):
        boy = V((0.9, -0.6, 0))
        base = [(-2.6, 3.6, "kid_red"), (-2.0, 3.9, "kid_green"), (-1.4, 3.5, "parent_a"),
                (-3.1, 4.2, "parent_b"), (-1.0, 4.3, "kid_grey"), (-2.3, 4.6, "parent_c")]
        cx = sum(b[0] for b in base) / 6
        cy = sum(b[1] for b in base) / 6
        for i, (x, y, o) in enumerate(base):
            kid = o.startswith("kid")
            x, y = cx + (x - cx) * 1.35, cy + (y - cy) * 1.35          # a little more room between them
            away = V((x - boy.x, y - boy.y, 0)).normalized()
            face_boy = math.degrees(math.atan2(away.x, -away.y))       # rot that faces him
            turn_dir = 1 if i % 2 else -1
            t0 = 0.25 + [0.0, 0.2, 0.1, 0.35, 0.28, 0.45][i]            # still, then each turns at their own time
            w = ease(max(0.0, min(1.0, (t - t0) / 0.7)))                # 0.7 s to turn round
            rot = face_boy + turn_dir * 180 * w
            cad, stride = (0.85, 15) if kid else (0.65, 15)
            leg = 0.855 * (KID if kid else 1.0)
            v = cad * 4 * leg * math.sin(math.radians(stride))          # walking speed that matches the steps
            tw = t0 + 0.6
            u = max(0.0, t - tw)
            acc = 0.5
            dist = v * (u * u / (2 * acc) if u < acc else u - acc / 2)  # eases into the walk
            px, py = x + away.x * dist, y + away.y * dist
            sc = KID if kid else 1.0
            if t < t0:
                p = dict(S.POSE["stand_by"], head=(0, 4))
            elif u <= 0.0:                                              # turning: small steps on the spot
                p = A_walk(t - t0, 1.3, 7)
                p["head"] = (0, 2)
            else:
                g = min(1.0, u / acc)
                p = A_walk(u, cad, stride * g)
                p["head"] = (0, 3)
            person(f"g{i}", px, py, rot, alive(p, t, i * 0.9, 0.3), o, scale=sc)
        helmet_carry(ctx, "boy", 0.9, -0.6, 20, 0.0, head=(0, 8))     # he does not move at all
        cam((2.375, -2.725, 1.25), (-1.3, 3.4, 0.9), 30, 5.0, 4.0)


@whole(10)
class S10:
    def static(ctx):
        A.kart_track_set()
        for o in list(bpy.data.objects):  # the near gazebo's legs would stand between them in this framing
            if o.name.startswith(("kt_gzleg0", "kt_gzroof0")):
                bpy.data.objects.remove(o, do_unlink=True)

    def frame(ctx, t, k):
        # He fights the tears: head down, a glance at his dad (who is facing away, over by the end of the van),
        # a held breath with his eyes shut, then he turns his face away from his dad, wipes the corner of his eye
        # once, breathes, straightens up and looks away as if he is fine. No sobbing, no big movements.
        bx, by, rot = -7.55, 5.6, -135
        if "s10_light" not in ctx:
            ctx["s10_light"] = lib.area("s10_face", (-6.6, 4.4, 1.5), (bx, by, 1.05), 22, 1.4, color=(1.0, 0.9, 0.8))
        glance = ramp(t, 0.3, 0.5) * (1 - ramp(t, 0.65, 0.85))
        turn_away = ramp(t, 1.6, 1.85)
        settle = ramp(t, 2.5, 3.0)
        yaw = 50 * glance - 28 * turn_away + 12 * settle + 1.2 * math.sin(2 * math.pi * 6 * t) * ramp(t, 0.9, 1.1) * (1 - ramp(t, 1.5, 1.6))
        pitch = 18 + 8 * ramp(t, 0.8, 1.2) * (1 - turn_away) - 12 * settle
        breath = 0.6 * math.sin(math.pi * max(0.0, min(1.0, (t - 0.95) / 0.5))) + 0.6 * math.sin(math.pi * max(0.0, min(1.0, (t - 2.5) / 0.5)))
        base = dict(S.POSE["stand_by"], head=(yaw, pitch), armL=(8, 4, 14), armR=(8, 4, 14), lean=-2 * breath,
                    face="worried" if t < 2.5 else "neutral")
        base["eyes_closed"] = 1.05 < t < 1.42
        base["tears"] = 0.35 * ramp(t, 0.6, 1.4) * (1 - ramp(t, 2.1, 2.25))
        up = ramp(t, 1.8, 1.94) * (1 - ramp(t, 2.32, 2.46))     # one hand to the corner of his eye, then down
        p = dict(base)
        if up > 0.01:
            wipe = 0.012 * math.sin(2 * math.pi * 3.0 * max(0.0, t - 2.0)) * ramp(t, 1.98, 2.05) * (1 - ramp(t, 2.25, 2.3))
            eye = head_point(lambda n: people.person(n, (bx, by, 0), rot, dict(base), "boy_suit", scale=KID),
                             "boy", (-0.045 + wipe, 0.2, 0.01))
            sol = solve("boy", bx, by, rot, dict(base, armR=S.POSE["wipe"]["armR"]), scale=KID, hands={"R": tuple(eye)})
            p["armR"] = mix(base["armR"], sol["armR"], up)
        people.person("boy", (bx, by, 0), rot, p, "boy_suit", scale=KID)
        person("dad", -6.95, 7.75, 20, alive(dict(S.POSE["stand_by"], head=(10, 4)), t, 1.3, 0.4), "dad_coat")
        cam(addv((-7.05, 3.55, 1.15), (0.0, 0.06 * k, 0.0)), (-7.28, 5.9, 0.62), 32, 2.1, 2.8)


def A_walk(t, speed=1.6, stride=24):
    a = math.sin(2 * math.pi * speed * t)
    return dict(legL=(stride * a, 4, 10 + 14 * max(0, -a)), legR=(-stride * a, 4, 10 + 14 * max(0, a)),
                armL=(-18 * a, 6, 15), armR=(18 * a, 6, 15), crouch=0.02 + 0.015 * abs(a), head=(0, 4))


@whole(11)
class S11:
    def static(ctx):
        A.kart_track_set()
        A.kart("k_boy", "new", (5.6, 3.4, 0.0), -20)

    def frame(ctx, t, k):
        bx, by = 2.6, 0.0
        T = SHOT_T[11][0] + t
        tr = word("track", 27.0)
        w = ramp(T, tr - 0.35, tr + 0.1)  # on "track" he points off at the circuit
        nod = ramp(T, tr + 0.05, tr + 0.3) * max(0.0, math.sin(2 * math.pi * 1.6 * (T - tr)))
        person("boy", bx, by, 0, alive(dict(S.POSE["stand_by"], head=(18 * w, 4 + 12 * nod)), t, 0.2, 0.5), "boy_suit", scale=KID)
        talk = T < tr + 0.25 and math.sin(2 * math.pi * 4.2 * T) > 0.1
        kneel = alive(dict(S.POSE["kneel"], lean=15, head=(25 + 20 * w, -10 + 4 * w), face="open" if talk else "neutral"), t, 1.1, 0.6)
        kneel["armL"] = mix(kneel.get("armL", (60, -10, 40)), (75, 55, 5), w)
        person("dad", bx + 0.58, by + 0.12, 45, kneel, "dad_coat", hands={"R": (bx + 0.19, by, 0.92)})
        cam((bx - 0.75 + 0.08 * k, by + 2.45 - 0.15 * k, 1.1), (bx + 0.25, by + 0.2, 0.8), 30, 2.5, 4.0)


def kart_pos(root, x, y, yaw=0.0):
    root.location = (x, y, 0.0)
    root.rotation_euler = (0, 0, math.radians(yaw))
    bpy.context.view_layer.update()


@whole(12)
class S12:
    def static(ctx):
        A.kart_track_set()
        M = palette()
        ctx["k"] = [A.kart("k_boy", "new", (11.2, 2.0, 0), 0), A.kart("k_red", "new", (13.2, 3.0, 0), 0, livery="rosso"),
                    A.kart("k_green", "new", (12.5, -1.6, 0), 0, livery="silver_arrow")]

    def frame(ctx, t, k):
        ys = [2.0 + 5 * t + 2.4 * t * t, 3.0 + 6 * t + 0.8 * t * t, -1.6 + 5 * t + 1.5 * t * t]
        xs = [11.2 - 0.3 * ramp(t, 0.6, 1.3), 13.2, 12.5]  # he moves across to take the inside line
        for kr, x, y, d, who, o in zip(ctx["k"], xs, ys, [ys[0] - 2.0, ys[1] - 3.0, ys[2] + 1.6], ("boy", "rival", "rival2"),
                                       ("boy_suit_h", "kid_red_h", "kid_green_h")):
            yaw = 6 * ramp(t, 0.6, 1.0) * (1 - ramp(t, 1.0, 1.4)) if who == "boy" else 0
            kart_pos(kr, x, y, yaw)
            kr["steer"] = yaw * 2
            spin_wheels(kr, d)
            A.kart_driver(who, kr, o)
        y0 = ys[0]
        cam((9.2, y0 + 3.4 - 0.4 * k, 1.45), (12.0, y0 - 0.8, 0.35), 22, 4.0, 5.6)


def flag_wave(ctx, name, base_loc, base_rot, t, marshal, mloc, mrot, mz=0.0, size=(0.7, 0.5)):
    if name not in ctx:
        ctx[name] = A.chequered_flag(name, base_loc, base_rot, size)
        dyn_texture(ctx[name])
    f = ctx[name]
    sw = wobble(t, 2.6, 28)
    f.rotation_euler = tuple(math.radians(a) for a in (base_rot[0], base_rot[1] + sw * 0.4, base_rot[2] + sw))
    bpy.context.view_layer.update()
    grip = f.matrix_world @ V((0, 0, -0.4))
    person(marshal, mloc[0], mloc[1], mrot, alive(S.POSE["flag_wave"], t, 0.2), "marshal", z=mz, hands={"L": tuple(grip)})


@whole(13)
class S13:
    def static(ctx):
        A.kart_track_set()
        ctx["k"] = A.kart("k_boy", "new", (12.0, 3.0, 0), 0)

    def frame(ctx, t, k):
        y = 3.6 + 10.5 * t
        kart_pos(ctx["k"], 12.0, y)
        spin_wheels(ctx["k"], y)
        A.kart_driver("boy", ctx["k"], "boy_suit_h")
        flag_wave(ctx, "flag", (8.3, 6.4, 1.75), (0, -30, -70), t, "marshal", (7.95, 6.4), -90)
        cam((14.9, 11.2, 1.3), (11.2 + 0.4 * k, 5.6 + 1.6 * k, 0.6), 20, 5.5, 5.6)


@whole(14)
class S14:
    def static(ctx):
        A.podium_set()
        ctx["tr"] = A.trophy("trophy", 0.42, (-2.0, 19.92, 1.5))

    def frame(ctx, t, k):
        top = 0.8 + KID * 1.305 + 0.27
        w = ramp(t, 0.0, 0.45)
        hz = mix(0.8 + KID * 1.0, top, w) + 0.02 * max(0.0, math.sin(2 * math.pi * 3.0 * t)) * w
        ty = 19.92 - 0.2 * math.sin(math.pi * w)  # an arc out in front of his face on the way up
        ctx["tr"].location = (-2.0, ty, hz - 0.12)
        person("boy", -2.0, 20.0, 180, dict(S.POSE["trophy_up"], head=(0, -4 - 10 * w)), "boy_suit", z=0.8, scale=KID,
               hands={"L": (-2.11, ty, hz), "R": (-1.89, ty, hz)})
        person("p2", -3.1, 20.0, 180, alive(S.POSE["stand_by"], t, 1), "kid_red", z=0.5, scale=KID)
        person("p3", -0.9, 20.0, 180, alive(S.POSE["stand_by"], t, 2), "kid_green", z=0.35, scale=KID)
        cam((-1.6, 16.4 + 0.3 * k, 1.15 + 0.1 * k), (-2.0, 20.0, 1.55 + 0.1 * k), 32, 3.6, 4.0)


@whole(15)
class S15:
    def static(ctx):
        A.shelf_set()

    def frame(ctx, t, k):
        cam((-1.3 + 0.45 * k, -0.75, 1.42), (0.35 + 0.3 * k, 0.15, 1.3), 30, 1.6, 2.4)


# ---------------------------------------------------------------- 1998: signed
@split(16, "a", 0.0, 0.55)
class S16a:
    def static(ctx):
        A.office_set()

    def frame(ctx, t, k):
        stroke = wobble(t, 3.0, 0.05)
        person("dennis", 0.2, 1.3, 180, alive(dict(lean=30, head=(0, 6), face="smile"), t, 0.3, 0.4), "dennis_suit",
               scale=BOSS, hands={"L": (-0.1, 1.02, 0.835), "R": (0.5, 1.02, 0.835)})
        person("boy", 0.05, -0.05, 0, alive(S.POSE["sign_desk"], t, 0.8, 0.3), "teen_blazer", scale=TEEN,
               hands={"R": (0.0 + stroke, 0.3, 0.815)})
        person("dad", -0.75, -0.55, 15, alive(S.POSE["proud"], t, 1.6), "dad_coat")
        cam((1.55 - 0.1 * k, -1.3 + 0.1 * k, 1.35), (0.05, 0.4, 1.0), 28, 2.0, 3.2)


@split(16, "b", 0.55, 1.0)
class S16b:
    def static(ctx):
        A.office_set()

    def frame(ctx, t, k):
        pump = 0.03 * math.sin(2 * math.pi * 2.4 * t)
        hand = (1.36, -0.5, 1.02 + pump)
        person("boy", 0.98, -0.6, -105, alive(dict(S.POSE["shake"], head=(0, -8)), t, 0.1, 0.3), "teen_blazer", scale=TEEN, hands={"R": hand})
        person("dennis", 1.74, -0.6, 105, alive(dict(S.POSE["shake"], head=(0, 14)), t, 0.9, 0.3), "dennis_suit", scale=BOSS,
               hands={"L": (hand[0] + 0.02, hand[1], hand[2])})
        person("dad", 0.2, -1.1, -60, alive(S.POSE["proud"], t, 1.3), "dad_coat")
        cam((1.25, -3.3 + 0.25 * k, 1.25), (1.25, -0.5, 1.2), 30, 2.8 - 0.25 * k, 3.2)


# ---------------------------------------------------------------- Brazil 2008
def cars_static(ctx, specs):
    ctx["cars"] = {}
    for name, liv, drv in specs:
        c = A.car(name, liv, (0, 0, 0), 0)
        ctx["cars"][name] = (c, drv)


def place_car(ctx, name, x, y, yaw=0.0, steer=0.0, dist=None):
    c, drv = ctx["cars"][name]
    c.location = (x, y, 0.0)
    c.rotation_euler = (0, 0, math.radians(yaw))
    c["steer"] = steer
    c["distance"] = y if dist is None else dist
    bpy.context.view_layer.update()
    for o in c.children_recursive:  # wheels spin: the library rig reads "distance" through drivers
        o.update_tag()
    pr = A.car_driver(f"{name}_d", c, drv)
    return c


def rain_follow(ctx, centre, t):
    """Rain falls past the camera: the streak sheet rides with the camera, scrolling down."""
    if "rain" not in ctx:
        ctx["rain"] = [A.rain(f"rain{i}", (0, 0, 0), (7, 8, 4), 450, 20 + i, 0.4) for i in range(2)]
    for i, r in enumerate(ctx["rain"]):
        fall = (t * 7.5 + i * 2.0) % 4.0
        r.location = (centre[0], centre[1], centre[2] + 2.0 - fall)


def spray(ctx, car_obj, t, seed):
    """A light mist thrown up by the rear tyres: small translucent blocks, new every frame (it shimmers)."""
    m = bpy.data.materials.get("mist") or lib.mat("mist", (0.85, 0.87, 0.9), 0.5, alpha=0.35)
    rnd = random.Random(seed * 1000 + int(t * 30))
    Mw = car_obj.matrix_world
    obs = []
    for i in range(70):  # fine droplets fanning up and back off the rear tyres
        u = rnd.random() ** 1.3
        s = 0.025 + u * 0.06
        side = rnd.choice((-1, 1))
        p = Mw @ V((side * (0.75 + u * 0.55) + rnd.uniform(-0.2, 0.2), -2.0 - u * 3.0, 0.15 + u * 0.75 + rnd.uniform(-0.05, 0.15)))
        ob = box(f"spray{seed}_{i}", (s, s * 2.5, s), tuple(p), m)
        ob["smooth"] = True
        obs.append(ob)
    return obs


@whole(17)
class S17:
    def static(ctx):
        A.interlagos_set()
        cars_static(ctx, [("ham", "chrome08", "driver08_h"), ("glock", "blanco08", "driver_white_h")])

    def frame(ctx, t, k):
        hy, gy = -20.0 + 42.0 * t, -12.5 + 40.0 * t
        h = place_car(ctx, "ham", -0.7 - 0.5 * ramp(t, 1.4, 3.0), hy, -2 * ramp(t, 1.4, 2.2) * (1 - ramp(t, 2.2, 3.0)))
        g = place_car(ctx, "glock", 1.65, gy, 3 + wobble(t, 1.4, 2.0), -6 + wobble(t, 1.4, 5))  # sliding on slicks
        spray(ctx, h, t, 1); spray(ctx, g, t, 2)
        c = (2.1 - 0.2 * k, hy - 7.5 + 0.6 * k, 1.5)
        rain_follow(ctx, (c[0] - 1.5, c[1] + 4.0, 0.0), t)
        cam(addv(c, shake(t, 0.01)), (0.2, hy + 6.0, 0.5), 30, 8.0, 4.0)


@whole(18)
class S18:
    def static(ctx):
        A.interlagos_set()
        cars_static(ctx, [("ham", "chrome08", "driver08_h"), ("glock", "blanco08", "driver_white_h")])

    def frame(ctx, t, k):
        hy, gy = -1.2 + 42.0 * t, 40.2 * t
        h = place_car(ctx, "ham", -1.6, hy, -3 + 2 * k)
        g = place_car(ctx, "glock", 1.4, gy, 6 + wobble(t, 1.5, 2.0), -6)
        spray(ctx, h, t, 3); spray(ctx, g, t, 4)
        c = (-7.0, gy + 4.6, 3.2)
        rain_follow(ctx, (-5.0, gy + 2.0, 0.0), t)
        cam(addv(c, shake(t, 0.008)), (0.0, gy + 0.3, 0.4), 30, 8.5, 4.0)


@split(19, "a", 0.0, 0.45)
class S19a:
    def static(ctx):
        A.interlagos_set()
        M = palette()
        box("ig_finish", (11.7, 0.3, 0.012), (0, 0, 0.012), M["white"])
        box("ig_flagstand", (1.4, 1.4, 0.6), (-7.65, 1.2, 0.3), M["white"])
        cars_static(ctx, [("ham", "chrome08", "driver08_h")])

    def frame(ctx, t, k):
        hy = -16.0 + 40.0 * t
        h = place_car(ctx, "ham", 0.0, hy, 0)
        spray(ctx, h, t, 5)
        flag_wave(ctx, "flag", (-7.3, 1.2, 2.4), (0, 30, 70), t, "marshal", (-7.65, 1.2), -90, mz=0.6, size=(1.0, 0.7))
        rain_follow(ctx, (4.5, 1.0, 0.0), t)
        cam((6.5, 2.6, 0.6), (0.0, min(hy, 12.0) * 0.6 - 0.6, 0.75), 26, 6.6, 4.0)


@split(19, "b", 0.45, 1.0)
class S19b:
    def static(ctx):
        H.TEAM["mcl08"] = dict(wall="charcoal", accent="red", blanket="dark", livery="w09")
        H.garage_set("mcl08", car=False)

    def frame(ctx, t, k):
        for i, (x, y, r, ph) in enumerate(((-1.7, 0.6, 10, 0.0), (-0.55, 1.0, -5, 1.7), (0.85, 0.7, 5, 0.9),
                                            (1.7, 1.1, -12, 2.4), (-2.6, -0.4, 20, 3.1), (2.6, -0.2, -20, 0.5))):
            hop = abs(math.sin(2 * math.pi * 1.5 * t + ph))
            z = 0.22 * hop if i in (0, 2, 5) else 0.0
            p = dict(S.POSE["cheer"])
            p["armL"] = (150 + 20 * hop, 30, 10 + 20 * hop)
            p["armR"] = (150 + 20 * (1 - hop), 30, 10)
            if z > 0.02:
                p.update(legL=(30 * hop, 6, 50 * hop), legR=(10 * hop, 6, 40 * hop))
            person(f"crew{i}", x, y, r, p, "crew08", z=z)
        cam((0.4, 4.8 - 0.3 * k, 1.55), (0.0, -0.2, 1.45), 28, 4.8, 4.0)


@whole(20)
class S20:
    def static(ctx):
        A.pitwall_set()
        # the low sun under the roof drew a hard shadow line across his head that slid as he moved: a soft fill instead
        bpy.data.objects.remove(bpy.data.objects["pw_sun"], do_unlink=True)
        lib.area("pw_face", (0.7, 1.5, 2.5), (0.25, 0.12, 2.2), 70, 1.6, color=(1.0, 0.95, 0.9))
        lib.area("pw_fist", (0.9, 1.6, 1.9), (0.1, 0.5, 2.0), 40, 1.2, color=(1.0, 0.95, 0.9))  # the fist reads

    def frame(ctx, t, k):
        w = ramp(t, 0.95, 1.3)  # a slow breath out, then a clenched fist pumped in front of his chest
        breath = math.sin(math.pi * min(1.0, t / 0.95))
        base = dict(head=(0, 6 - 8 * breath * (1 - w) - 6 * w), face="smile" if w > 0.4 else "neutral", lean=-3 * breath * (1 - w))
        pump = 0.05 * math.sin(2 * math.pi * 2.2 * max(0.0, t - 1.3)) * w
        fist = lerpv((-0.05, 0.42, 1.6), (0.1, 0.5, 2.0 + pump), w)
        p = solve("dennis", 0.25, 0.12, 0, base, 0.6, BOSS * 0.97, {"L": (0.55, 0.42, 1.6), "R": tuple(fist)})
        people.person("dennis", (0.25, 0.12, 0.6), 0, alive(p, t, 0.4, 0.3), "dennis_team", scale=BOSS * 0.97)
        person("eng1", -1.3, 0.12, 0, alive(dict(head=(10 + 20 * w, 4)), t, 1.0), "crew08", z=0.6,
               hands={"L": (-1.15, 0.42, 1.6), "R": (-1.45, 0.42, 1.6)})
        person("eng2", 1.6, 0.12, 0, alive(dict(head=(-15 - 20 * w, 4)), t, 2.0), "crew08", z=0.6,
               hands={"L": (1.75, 0.42, 1.6), "R": (1.45, 0.42, 1.6)})
        cam((1.35 - 0.1 * k, 2.5 - 0.15 * k, 2.5), (0.3, 0.12, 2.12), 30, 2.6, 3.0)


@whole(21)
class S21:
    def static(ctx):
        A.shed_set("new")
        # the book pinned on the wall, bigger and lower, to the right of the kart and clear of it, with its own light
        b = bpy.data.objects["sh_book"]
        b.location, b.scale = (0.35, 1.83, 1.36), (2.6, 2.6, 2.6)
        bpy.data.objects["sh_pin"].location = (0.35, 1.81, 1.58)
        A.spot("sh_bookspot", (0.7, 0.5, 2.2), (0.35, 1.83, 1.36), 55, 32, 0.6, (1.0, 0.85, 0.65), 0.08)
        A.lamp_point("sh_kartlift", (1.3, -0.9, 1.3), 14, (1.0, 0.82, 0.6), 0.5)

    def frame(ctx, t, k):  # the fixed-up kart and the autograph book together, both whole, a very slow drift
        e = ease(k)
        cam((1.85 - 0.06 * e, -1.75 + 0.05 * e, 1.5), (0.15, 0.55, 0.95), 24, 2.6, 8.0)


@whole(22)
class S22:
    def static(ctx):
        import props
        A.pitwall_set()
        A.car("ham", "chrome08", (0.0, -4.4, 0.0), 90)
        props.helmet("helmet", "white", "red")
        ctx["helmet"] = bpy.data.objects["helmet"]

    def frame(ctx, t, k):
        T = SHOT_T[22][0] + t
        lw = word("lewis", 46.0)
        neck = V((0.0, -6.0, 19 * 0.045 + 12 * 0.045))
        up = ramp(T, lw - 0.62, lw - 0.25)      # both hands lift it up off his head
        side = ramp(T, lw - 0.3, lw + 0.12)     # then swing it out and down to his side: face clear on "Lewis"
        hl = ctx["helmet"]
        lift = 0.22 * up * (1 - side)
        pos = neck + V((0, 0.02, 0)) + V((0, 0, lift)) + V((0.42, -0.02, -0.55)) * side
        hl.location = tuple(pos)
        hl.rotation_euler = (math.radians(-14 * up * (1 - side)), 0, math.radians(180))
        bpy.context.view_layer.update()
        hz = pos.z + 0.17
        if side < 0.5:
            hands = {"L": (pos.x - 0.25, -6.0 + 0.02, hz), "R": (pos.x + 0.25, -6.0 + 0.02, hz)}
        else:  # one hand carries it by the chin bar (the visor faces the camera)
            hands = {"R": (pos.x, pos.y - 0.22, pos.z + 0.06)}
        face = "smile" if side > 0.6 else "neutral"
        person("lewis", 0.0, -6.0, 180, alive(dict(head=(0, -4 + 4 * side), face=face), t, 0.5, 0.4 * side), "driver08",
               hands=hands)
        rain_follow(ctx, (0.0, -7.6, 0.0), t)
        cam(addv((0.12, -7.75 + 0.06 * k, 1.6), shake(t, 0.002)), (0.0, -6.0, 1.6), 45, 1.75, 2.4)


# ---------------------------------------------------------------- the renderer
def dyn_texture(root):
    """Pixel materials (and voxels for round parts) for things built after voxelize_scene."""
    if root.get("textured"):
        return
    root["textured"] = True
    objs = [root] + list(root.children_recursive)
    if root.get("person"):
        voxel.texture_person(root)
        return
    bpy.context.view_layer.update()
    for ob in objs:
        if ob.type != "MESH" or ob.get("smooth") or len(ob.data.vertices) <= 4:
            continue
        if voxel._is_box(ob):
            voxel.texture_boxes([ob])
        else:
            voxel.voxelize_object(ob)
            bpy.data.objects.remove(ob, do_unlink=True)


def setup(sc, w, h, expo):
    engine = os.environ.get("ENGINE", "cycles")
    pct = int(os.environ.get("PCT", 50))
    r = sc.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = w, h, pct
    r.fps = FPS
    if engine == "eevee":
        r.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
        e = sc.eevee
        for a, v in (("taa_render_samples", int(os.environ.get("SAMPLES", 24))), ("use_raytracing", True), ("use_gtao", True),
                     ("use_shadows", True), ("shadow_ray_count", 2), ("shadow_step_count", 8)):
            if hasattr(e, a):
                try:
                    setattr(e, a, v)
                except (TypeError, ValueError):
                    pass
        for m in bpy.data.materials:
            if hasattr(m, "surface_render_method"):
                m.surface_render_method = "BLENDED" if m.blend_method == "BLEND" else "DITHERED"
    else:
        sc.cycles.samples = int(os.environ.get("SAMPLES", 16))
        r.use_persistent_data = False
    sc.view_settings.exposure = expo


def run(frames_dir, ids):
    os.makedirs(frames_dir, exist_ok=True)
    checks = {}
    for P in PARTS:
        if ids and P.shot not in ids:
            continue
        f0 = int(round(P.t0 * FPS))
        f1 = int(round(P.t1 * FPS)) if P.t1 < END - 1e-6 else int(round(END * FPS))
        sub = os.path.join(frames_dir, f"panel{P.panel}") if P.panel is not None else frames_dir
        os.makedirs(sub, exist_ok=True)
        todo = [f for f in range(f0, f1) if not os.path.exists(os.path.join(sub, f"f{f:05d}.png"))]
        todo = todo[::int(os.environ.get("STEP", 1))]  # STEP=n: a quick look at every n-th frame
        if not todo:
            continue
        reset()
        lib.STYLE["voxel"] = True
        lib.STYLE["low"] = 0
        sc = setup_render(540, 960, 16, "")
        ctx = {}
        P.static(ctx)
        voxel.voxelize_scene()
        expo = EXPO_PART.get(f"{P.shot}{P.label}", EXPO.get(P.shot, 0.4))
        setup(sc, P.res[0], P.res[1], expo)
        static_names = set(o.name for o in bpy.data.objects)
        dur = P.t1 - P.t0
        sample = {todo[0], todo[len(todo) // 2], todo[-1]}
        tic = time.time()
        for f in todo:
            t = (f - int(round(P.t0 * FPS))) / FPS
            k = t / dur
            before = set(o.name for o in bpy.data.objects)
            sc.frame_set(f)
            P.frame(ctx, t, k)
            bpy.context.view_layer.update()
            for o in list(bpy.data.objects):  # texture what this frame built
                if o.name not in before and o.parent is None and o.name in bpy.data.objects:
                    if o.get("person"):
                        voxel.texture_person(o)
                    elif (o.type == "MESH" or o.children) and not o.get("textured") and not o.get("smooth"):
                        dyn_texture(o)
            if os.environ.get("CHECK") and f in sample:
                import check
                clips, feet = check.check_scene()
                checks[f"{P.shot:02d}{P.label}_{f}"] = dict(clips=clips[:12], n=len(clips), feet=feet[:6])
            for o in bpy.data.objects:  # the library cars' wheels follow root["distance"] through drivers
                if o.get("blueprint"):
                    o.update_tag()
            bpy.context.view_layer.update()
            sc.render.filepath = os.path.join(sub, f"f{f:05d}.png")
            bpy.ops.render.render(write_still=True)
            after = getattr(P, "after", None)
            for o in list(bpy.data.objects):  # delete this frame's people and one-frame props
                if o.name not in before and o.name in bpy.data.objects and not any(o is v for v in ctx.values() if isinstance(v, bpy.types.Object)) \
                        and not any(o is v for v in ctx.get("rain", [])) and not _kept(o, ctx):
                    bpy.data.objects.remove(o, do_unlink=True)
            sc["holds"] = "[]"
            if f % 20 == 0:
                for me in [m for m in bpy.data.meshes if m.users == 0]:  # meshes only: palette materials are cached
                    bpy.data.meshes.remove(me)
        print(f"PART s{P.shot:02d}{P.label}: {len(todo)} frames in {time.time() - tic:.0f}s", flush=True)
    if checks:
        path = os.path.join(ROOT, "out", "anim_check.json")
        old = json.load(open(path)) if os.path.exists(path) else {}
        old.update(checks)
        json.dump(old, open(path, "w"), indent=1)


def _kept(o, ctx):
    """Objects kept between frames: anything in ctx (or parented under it)."""
    keep = [v for v in ctx.values() if isinstance(v, bpy.types.Object)]
    keep += ctx.get("rain", [])
    p = o
    while p:
        if any(p is v for v in keep):
            return True
        p = p.parent
    return False


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    run(os.path.abspath(args[0]), [int(a) for a in args[1:]])
