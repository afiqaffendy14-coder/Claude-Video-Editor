"""Shot list for "Why would a children's heart surgeon ask Ferrari for help?" (60.0 s, 35 hard cuts, blocky style).

Cut times follow the narrator's word timings (tools/timing.json, take 1).
Run: .venv-blender/bin/python shots.py board [ids...]   -> boards/stills/sNN.png (540x960 stills)
     .venv-blender/bin/python shots.py json              -> boards/shots.json (for the storyboard pages)
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import bpy
import lib
from lib import V, reset, palette, setup_render, camera, render, box, mat
from props import clipboard
import sets as S
import voxel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STILLS = os.path.join(ROOT, "boards", "stills")
AUX = os.path.join(ROOT, "boards", "aux")


def dollhouse():
    """Cutaway: hide ceilings and ceiling lights so straight-down shots can see into a room."""
    for ob in bpy.data.objects:
        if any(k in ob.name for k in ("ceiling", "_light", "th_panel", "cor_light", "ceil_glow")):
            ob.hide_render = True


def cam(loc, target, lens=35, dof=None, fstop=2.8, roll=0.0):
    camera(V(loc), V(target), lens, dof, fstop, roll)


def floor(name, material):
    o = bpy.data.objects.get(name)
    if o:
        o.data.materials[0] = material


# ------------------------------------------------------------------ shots
def pit_top(h, lens=32, y=0.4, phase="ready"):
    def b():
        S.pit_set(phase=phase)
        cam((0, y, h), (0, y, 0), lens)
    return b


def surgeon(c):
    """A masked heart surgeon leaning over the cot, seen from the baby's side (opens and closes the film)."""
    def b():
        S.icu_set("empty")
        S.P("surg", 0.0, -0.5, 0, "work", "surgeon")
        cam(*c)
    return b


def falling():
    """Mid-handover, everyone busy at the cot: a syringe slips off the edge and a line tugged loose falls to the floor."""
    S.icu_set("chaos")
    remove("c3", "c5")
    M = palette()
    px = voxel.PX
    from lib import tube
    # the syringe, mid-fall, tumbling off the cot's edge
    tilt = (math.radians(35), math.radians(-20), math.radians(30))
    box("syr_barrel", (1.2 * px, 6 * px, 1.2 * px), (0.48, -0.42, 0.62), M["white"], rot=tilt)
    box("syr_plunger", (0.6 * px, 3 * px, 0.6 * px), (0.53, -0.3, 0.66), M["grey"], rot=tilt)
    box("syr_tip", (0.4 * px, 1.5 * px, 0.4 * px), (0.43, -0.54, 0.58), M["steel"], rot=tilt)
    # a line pulled loose: hanging over the cot side and pooling on the floor, its connector open
    line = mat("ivline_soft", (0.45, 0.75, 1.0), 0.25)
    t = tube("loose_line", [V((0.3, 0.1, 0.86)), V((0.4, -0.02, 0.8)), V((0.45, -0.12, 0.45)), V((0.5, -0.25, 0.06)),
                            V((0.75, -0.45, 0.02)), V((0.95, -0.4, 0.02))], 0.007, line)
    t["smooth"] = True
    box("loose_conn", (1.4 * px, 2.2 * px, 1.4 * px), (0.97, -0.4, 0.03), M["white"])
    box("loose_cap", (1.0 * px, 0.8 * px, 1.0 * px), (1.03, -0.36, 0.03), M["yellow"])
    cam((1.85, -1.75, 1.05), (0.4, -0.15, 0.6), 30, 2.3, 2.8, -5)


def exterior():
    S.exterior_set()
    cam((14, -10, 1.6), (12, 30, 10), 22)


def theatre_top():
    import dress
    S.theatre_set(lamps_aside=True)
    floor("th_floor", dress.vinyl())
    remove("surg3", "nurse1")  # keep the foot of the table clear so the baby reads
    cam((0.3, -1.25, 2.5), (0, 0.5, 1.08), 30, 2.25, 2.8, 4)


def theatre_monitor():
    import dress
    S.theatre_set()
    floor("th_floor", dress.vinyl())
    cam((1.33, 0.22, 1.78), (0.95, 1.25, 1.75), 40, dof=1.1, fstop=2.4)


def corridor(cot_y, c, dim=False):
    def b():
        import dress
        S.corridor_set(cot_y=cot_y, dim=dim)
        floor("cor_floor", dress.vinyl())
        cam(*c)
    return b


def icu(mode, c, skip=(), top=False):
    def b():
        S.icu_set(mode, skip=skip)
        if top:
            dollhouse()
        cam(*c)
    return b


def dropped_notes():
    S.icu_set("chaos")
    M = palette()
    for i, (x, y, r) in enumerate([(0.25, -0.75, 20), (0.05, -0.95, -35), (0.45, -1.05, 60)]):
        box(f"sheet{i}", (0.21, 0.29, 0.006), (x, y, 0.004 + i * 0.004), M["white"], rot=(0, 0, math.radians(r)))
    cb = clipboard("cb", ticks=0)
    cb.location = (-0.05, -0.65, 0.02)
    cb.rotation_euler = (0, 0, math.radians(-20))
    cam((-0.55, -1.45, 0.38), (0.05, -0.75, 0.0), 32, dof=0.95, fstop=2.2)


def viewing():
    S.viewing_room(os.path.join(AUX, "tv_pit.png"))
    cam((0.1, -2.6, 1.45), (0, 2.4, 1.45), 28)


def remove(*names):
    """Delete people/props (root empty and everything under it) that would block a close-up."""
    for n in names:
        root = bpy.data.objects.get(n)
        if not root:
            continue
        for ob in [root] + list(root.children_recursive):
            bpy.data.objects.remove(ob, do_unlink=True)


def pit(c, drop=(), **kw):
    def b():
        S.pit_set(**kw)
        remove(*drop)
        cam(*c)
    return b


def leaving():
    """Board up, the car pulls out of the box toward the fast lane; the crew has stepped back on both sides."""
    S.pit_set(phase="go", crew_skip=("FL", "RL", "stab", "wing"))
    car = bpy.data.objects["car"]
    car.location = (2.4, 5.4, 0)
    car.rotation_euler = (0, 0, math.radians(-35))
    cam((-1.3, -1.2, 0.65), (2.0, 5.2, 0.6), 26, 7.2, 4.0, -6)


def phone_call():
    """Staff room: a phone on the table, screen lit, the doctor's hand reaching for it."""
    S.viewing_room(os.path.join(AUX, "tv_pit.png"))
    M = palette()
    box("table", (1.0, 0.6, 0.05), (0.9, -1.2, 0.5), M["white"])
    box("table_leg", (0.06, 0.06, 0.48), (0.9, -1.2, 0.24), M["grey"])
    box("phone", (0.08, 0.16, 0.012), (0.85, -1.2, 0.531), M["dark"], rot=(0, 0, math.radians(15)))
    box("phone_screen", (0.07, 0.145, 0.004), (0.85, -1.2, 0.539), mat("phoneglow", (1, 1, 1), 0.3, emit=(0.6, 0.95, 0.7), emit_strength=3),
        rot=(0, 0, math.radians(15)))
    S.P("caller", 1.15, -1.75, 30, dict(lean=25, armR=(75, 5, 25), head=(0, 30)), "doctor")
    px = voxel.PX
    box("reach_hand", (2.2 * px, 3 * px, 1.4 * px), (1.0, -1.32, 0.56), M["skin"], rot=(0, 0, math.radians(35)))
    box("reach_sleeve", (2.6 * px, 6 * px, 2.2 * px), (1.1, -1.48, 0.58), M["scrubs"], rot=(0, 0, math.radians(35)))
    from lib import area
    area("phone_key", (0.5, -1.0, 1.6), (0.85, -1.2, 0.53), 60, 1.0)
    cam((0.5, -1.55, 0.82), (0.88, -1.22, 0.53), 45, dof=0.5, fstop=2.0)


def ferrari(c):
    def b():
        S.ferrari_room(os.path.join(AUX, "tv_chaos.png"))
        cam(*c)
    return b


def checklist():
    S.icu_set("order")
    cb = clipboard("cb", ticks=4)
    cb.location = (0.0, -0.08, 0.76)
    cb.rotation_euler = (math.radians(4), 0, math.radians(8))
    cam((0.12, -0.5, 1.08), (0, -0.08, 0.76), 60, dof=0.52, fstop=2.0)


def chart(before, after):
    def b():
        S.chart_set(before, after)
        cam((0, -(2.4 + before * 0.42), 0.55 + before * 0.12), (0, 0, before * 0.16 + 0.05), 32)
    return b


def tiny_hand():
    S.icu_set("empty")
    M = palette()
    px = voxel.PX
    y = 0.44
    box("bhand", (1.4 * px, 1.4 * px, 1.2 * px), (0.12, y, 0.8), M["babyskin"])
    box("gfinger", (3.5 * px, 0.8 * px, 0.8 * px), (0.2, y, 0.805), M["glove"])
    box("glove_hand", (2.4 * px, 3 * px, 1.6 * px), (0.32, y, 0.815), M["glove"])
    box("glove_cuff", (2.6 * px, 3.2 * px, 1.8 * px), (0.42, y, 0.815), M["gown"])
    cam((0.35, 0.05, 1.15), (0.2, y, 0.8), 50, dof=0.53, fstop=2.0)


SHOTS = [  # n, start, end, builder, description
    (1, 0.00, 1.60, surgeon(((0.18, 1.05, 1.2), (0, -0.4, 1.42), 42, 1.55, 2.2)), "A masked children's heart surgeon leans over a tiny baby in its cot. Cold open."),
    (2, 1.60, 3.40, pit_top(8, 24, phase="swap"), "...ask Ferrari for help? Top-down: the car up on its jacks, twenty crew working all four corners at once."),
    (3, 3.40, 5.60, exterior, "Street level, London: the hospital facade, a clock tower in the haze."),
    (4, 5.60, 7.84, theatre_top, "From the foot of the table: the surgical team, the baby's head and cap at the far end."),
    (5, 7.84, 9.44, theatre_monitor, "Close: the heart monitor's green trace. The danger isn't over."),
    (6, 9.44, 11.20, corridor(-6.5, ((0.55, -10.8, 1.55), (0, 18, 1.3), 30, None, 2.8, 3), True), "Dim corridor: the team wheels the cot toward intensive care."),
    (7, 11.20, 13.14, corridor(0, ((0.3, -2.5, 0.38), (0, 0.4, 0.4), 30, 2.1, 2.8)), "Low, from behind: the porter's feet and the cot's castors rolling toward intensive care."),
    (8, 13.14, 15.00, icu("empty", ((0.3, 0.25, 1.12), (0.02, 0.55, 0.82), 45, 0.48, 2.2)), "Macro: the breathing tube and lines on the baby."),
    (9, 15.00, 16.90, icu("chaos", ((0.05, 0.25, 1.95), (0, 0.5, 0.75), 34, 1.2, 2.8)), "Hands reach for the monitor cables: unplugged."),
    (10, 16.90, 18.40, corridor(0, ((1.35, -2.3, 1.45), (0, 0.6, 0.9), 24, None, 2.8, -5)), "Tracking: the cot, ventilator and IV pole on the move."),
    (11, 18.40, 20.10, icu("chaos", ((0, 0.15, 4.6), (0, 0.15, 0), 22), top=True), "Cutaway top-down: several teams crowd one tiny bed."),
    (12, 20.10, 21.40, icu("chaos", ((0.15, -0.35, 2.15), (0, 0.35, 0.8), 26, None, 2.8, 6)), "High angle: many hands at once. In that rush..."),
    (13, 21.40, 22.70, falling, "Mid-handover, everyone busy at the cot: a syringe tumbles off the edge and a line tugged loose falls to the floor."),
    (14, 22.70, 24.40, viewing, "From behind: two doctors watch a pit stop on the staff-room screen."),
    (15, 24.40, 26.20, pit(((-2.4, 5.6, 0.55), (0, -1.0, 0.6), 24, 2.2, 3.2, 6), phase="arrive", car_y=-2.6), "Low behind the lollipop man: the car rolls in, twenty crew poised."),
    (16, 26.20, 27.60, pit(((5.2, 5.6, 2.4), (0.2, 0.5, 0.4), 22, 7.0, 5.6, -4), phase="swap"), "Wide and high: car on the jacks, four tyres off at once (counter overlay: 20)."),
    (17, 27.60, 29.00, pit(((0.3, 3.85, 1.55), (1.6, 2.35, 0.7), 26, 2.05, 3.2, -6), phase="swap", drop=("wing1", "fjack", "fjack_eq")), "Close: the old front-left tyre comes away in the tyre-off man's hands."),
    (18, 29.00, 30.20, pit(((0.45, -0.4, 1.5), (1.45, 1.3, 0.7), 26, 2.05, 3.2, 5), phase="swap", drop=("stab1",)), "Low: the new tyre swings onto the hub, the gunner waiting with the wheel gun."),
    (19, 30.20, 31.37, pit(((0.9, 6.4, 1.7), (0, 1.4, 0.45), 26, 4.6, 4.0, -6), phase="swap"), "Head-on: the front jack lifts the nose, every mechanic in their own spot, nobody in anyone's way."),
    (20, 31.37, 32.92, phone_call, "Close: the doctor's hand reaches for the phone (overlay: calling Ferrari)."),
    (21, 32.92, 34.90, ferrari(((0.1, -2.3, 1.6), (0, 3.0, 1.55), 30)), "Ferrari's engineers study the hospital's handover footage."),
    (22, 34.90, 37.08, ferrari(((0.0, 1.55, 1.9), (0, 3.0, 1.9), 33)), "Screen close-up: the handover, problems circled in red (overlay)."),
    (23, 37.08, 38.90, pit(((0, 0.45, 1.03), (-0.6, 3.5, 1.7), 30, 3.3, 4.0)), "Driver's eye through the halo: the lollipop board ahead."),
    (24, 38.90, 40.40, pit(((0.4, 2.6, 1.4), (-0.8, 4.2, 1.75), 28, 2.0, 2.8), crew_skip=("jacks",)), "The lollipop man: one person in charge."),
    (25, 40.40, 41.92, icu("order", ((0.55, 1.2, 2.1), (0, -0.75, 1.45), 40, 2.15, 2.8), skip=("o1",)), "The hospital's 'lollipop man': the anaesthetist in a red cap at the foot of the cot, hand raised, team turned to him."),
    (26, 41.92, 43.60, icu("order", ((0, 0.0, 4.6), (0, 0.0, 0), 22), top=True), "Cutaway top-down: everyone in a fixed spot (numbered roles overlay)."),
    (27, 43.60, 45.00, icu("order", ((1.15, 0.6, 1.45), (0, 0.45, 0.8), 32, 1.3, 2.4, -4), skip=("o1",)), "Side angle: lines reconnected one by one, in order."),
    (28, 45.00, 46.67, checklist, "Macro: the checklist, red ticks."),
    (29, 46.67, 47.64, icu("order", ((1.75, 1.05, 1.9), (-0.15, -0.15, 0.95), 26, 2.0, 2.8, 4), skip=("o1", "o3")), "Calm, ordered handover. And it worked."),
    (30, 47.64, 50.10, chart(5.42, 3.15), "Block chart: errors per handover, 5.42 blocks to 3.15 (overlay: -42%)."),
    (31, 50.10, 52.60, chart(2.09, 1.07), "Block chart: missing information, 2.09 to 1.07, almost half."),
    (32, 52.60, 54.30, leaving, "From behind the crew: board up, the car pulls out of the box and away toward the fast lane."),
    (33, 54.30, 56.30, pit(((1.6, 8.5, 1.6), (0, 0, 1.0), 32, 7.0, 4.0, 4), car=False, phase="go"), "The empty box: crew stepping back, old tyres on the ground, the board up."),
    (34, 56.30, 58.10, tiny_hand, "Macro: the baby's hand around a gloved finger."),
    (35, 58.10, 60.00, surgeon(((0.25, 1.4, 1.25), (0, -0.4, 1.42), 36, 1.95, 2.2)), "Back on the surgeon, pushing in: the loop back to the opening question."),
]


def build(builder):
    lib.STYLE["voxel"] = True
    lib.STYLE["low"] = 0
    builder()
    voxel.voxelize_scene()


def aux():
    """Images shown on screens inside other shots (16:9), in the same blocky style."""
    os.makedirs(AUX, exist_ok=True)
    for name, b, c in [("tv_pit", lambda: S.pit_set(car_y=-1.0), ((0, -8.5, 7.5), (0, 0.5, 0), 30)),
                       ("tv_chaos", lambda: S.icu_set("chaos"), ((0.2, -2.6, 2.5), (0, 0.4, 0.8), 26))]:
        reset()
        setup_render(960, 540, 24, os.path.join(AUX, name + ".png"))
        build(lambda: (b(), cam(*c)))
        render()


def board(ids=None):
    os.makedirs(STILLS, exist_ok=True)
    if not (os.path.exists(os.path.join(AUX, "tv_pit.png")) and os.path.exists(os.path.join(AUX, "tv_chaos.png"))):
        aux()
    for n, t0, t1, b, desc in SHOTS:
        if ids and n not in ids:
            continue
        reset()
        setup_render(540, 960, 24, os.path.join(STILLS, f"s{n:02d}.png"))
        build(b)
        render()
        print(f"BOARD s{n:02d} done", flush=True)


def dump_json():
    import json
    out = [dict(n=n, start=t0, end=t1, desc=d) for n, t0, t1, _, d in SHOTS]
    json.dump(out, open(os.path.join(ROOT, "boards", "shots.json"), "w"), indent=1)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.endswith(".py")]
    if args and args[0] == "board":
        board([int(a) for a in args[1:]] or None)
    elif args and args[0] == "aux":
        aux()
    elif args and args[0] == "json":
        dump_json()
