"""Shot list for "The Pit Stop That Made a Children's Hospital Safer" (60.0 s, 36 hard cuts).

Run: .venv-blender/bin/python shots.py board [ids...]   -> boards/stills/sNN.png (540x960 stills, mid-shot)
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from lib import V, reset, palette, setup_render, camera, render, box, sphere, cyl, tube, mat
from people import person
from props import clipboard, wheel
import sets as S

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STILLS = os.path.join(ROOT, "boards", "stills")
AUX = os.path.join(ROOT, "boards", "aux")


def dollhouse():
    """Cutaway: hide ceilings and ceiling lights so straight-down shots can see into a room."""
    for ob in bpy.data.objects:
        if any(k in ob.name for k in ("ceiling", "_light", "th_panel", "cor_light")):
            ob.hide_render = True


def cam(loc, target, lens=35, dof=None, fstop=2.8, roll=0.0):
    camera(V(loc), V(target), lens, dof, fstop, roll)


# ------------------------------------------------------------------ shots
def s_pit_top(h=11.0, crew=True):
    def b():
        S.pit_set(crew=crew)
        cam((0, 0.4, h), (0, 0.4, 0), 32)
    return b


def s02():
    S.icu_set("empty")
    cam((0.5, -0.3, 1.2), (0, 0.5, 0.74), 45, dof=0.95, fstop=2.0)


def s03():
    S.exterior_set()
    cam((14, -10, 1.6), (12, 30, 10), 22)


def s04():
    S.theatre_set(lamps_aside=True)
    dollhouse()
    cam((0, 0.1, 4.3), (0, 0.1, 0), 20)


def s05():
    S.theatre_set()
    cam((1.12, 0.66, 1.72), (0.95, 1.25, 1.75), 55, dof=0.62, fstop=2.0)


def s06():
    S.corridor_set(cot_y=-6.5, dim=True)
    cam((0.55, -10.8, 1.55), (0, 18, 1.3), 30)


def s07():
    S.corridor_set(cot_y=0)
    cam((0.75, -0.35, 0.16), (0.3, 0.5, 0.1), 24, dof=0.45, fstop=2.8)


def s08():
    S.corridor_set(cot_y=0)
    cam((1.35, -2.3, 1.45), (0, 0.6, 0.9), 24)


def s09():
    S.corridor_set(cot_y=2)
    dollhouse()
    cam((0, 2.2, 9.5), (0, 2.2, 0), 22)


def s10():
    S.icu_set("empty")
    cam((0.32, 0.22, 0.95), (0.03, 0.62, 0.77), 70, dof=0.5, fstop=2.0)


def s11():
    S.icu_set("chaos")
    cam((0.45, 1.05, 1.75), (0.92, 1.95, 1.8), 45, dof=1.0, fstop=2.8)


def s12():
    S.icu_set("chaos")
    cam((0.15, -0.35, 2.15), (0, 0.35, 0.8), 26)


def s13():
    S.icu_set("chaos")
    dollhouse()
    cam((0, 0.15, 4.6), (0, 0.15, 0), 22)


def s14():
    S.icu_set("chaos")
    M = palette()
    for i, (x, y, r) in enumerate([(0.25, -0.75, 20), (0.05, -0.95, -35), (0.45, -1.05, 60)]):
        box(f"sheet{i}", (0.21, 0.29, 0.003), (x, y, 0.004 + i * 0.002), M["white"], rot=(0, 0, math.radians(r)))
    cb = clipboard("cb", ticks=0)
    cb.location = (-0.05, -0.65, 0.02)
    cb.rotation_euler = (0, 0, math.radians(-20))
    cam((0.55, -1.55, 0.28), (0.15, -0.8, 0.02), 40, dof=0.85, fstop=2.0)


def s15():
    S.viewing_room(os.path.join(AUX, "tv_pit.png"))
    cam((0.1, -2.6, 1.45), (0, 2.4, 1.45), 28)


def s16():
    S.pit_set(car_y=-5.5)
    cam((2.2, 7.5, 0.9), (0, -2.5, 0.5), 35)


def s17():
    S.pit_set()
    cam((7.5, 8.0, 6.2), (0, 0.2, 0.3), 30)


def s18():
    S.pit_set()
    cam((1.62, 1.12, 0.52), (1.08, 1.8, 0.4), 60, dof=0.82, fstop=2.0)


def s19():
    S.pit_set()
    cam((0, 0.4, 8.0), (0, 0.4, 0), 24)


def s20():
    S.pit_set()
    cam((2.65, -3.3, 0.5), (1.2, 1.9, 0.6), 28)


def s21():
    S.ferrari_room(os.path.join(AUX, "tv_chaos.png"))
    S.P("visA", -3.0, 0.6, 210, "talk", "doctor")
    S.P("visB", -2.4, 0.9, 200, "watch", "suit")
    S.P("host", -3.3, -0.6, 20, dict(armR=(50, 10, 20)), "engineer")
    cam((-0.2, 3.0, 1.6), (-3.5, -0.5, 1.0), 30)


def s22():
    S.ferrari_room(os.path.join(AUX, "tv_chaos.png"))
    cam((0.1, -2.3, 1.6), (0, 3.0, 1.55), 30)


def s23():
    S.ferrari_room(os.path.join(AUX, "tv_chaos.png"))
    cam((0.0, 1.55, 1.9), (0, 3.0, 1.9), 33)


def s24():
    S.pit_set()
    cam((0, 0.25, 0.86), (-0.6, 3.5, 1.7), 32, dof=3.5, fstop=4)


def s25():
    S.pit_set()
    cam((0.6, 1.9, 1.35), (-0.85, 4.6, 1.45), 42, dof=3.0, fstop=2.8)


def s26():
    S.icu_set("order")
    cam((0.05, 2.0, 1.75), (0, -0.75, 1.3), 50, dof=2.75, fstop=2.8)


def s27():
    S.icu_set("order")
    dollhouse()
    cam((0, 0.0, 4.6), (0, 0.0, 0), 22)


def s28():
    S.icu_set("order")
    cam((1.05, -0.35, 1.25), (0.45, 0.45, 0.85), 45, dof=1.1, fstop=2.0)


def s29():
    S.icu_set("order")
    cb = clipboard("cb", ticks=4)
    cb.location = (0.0, -0.08, 0.72)
    cb.rotation_euler = (math.radians(4), 0, math.radians(8))
    cam((0.12, -0.5, 1.05), (0, -0.08, 0.72), 60, dof=0.52, fstop=2.0)


def s30():
    S.icu_set("order")
    cam((2.3, -2.6, 1.7), (0, 0.3, 0.9), 30)


def s31():
    S.chart_set(5.42, 3.15)
    cam((0, -6.5, 1.6), (0, 0, 0.9), 42)


def s32():
    S.chart_set(2.09, 1.07)
    cam((0, -6.5, 1.6), (0, 0, 0.5), 42)


def s33():
    S.pit_set(car_y=4.5)
    cam((1.7, -0.6, 0.4), (0, 7, 0.5), 24)


def s34():
    S.pit_set(car=False)
    cam((1.6, 8.5, 1.6), (0, 0, 1.0), 32)


def s35():
    S.icu_set("order")
    M = palette()
    # the baby's hand around a gloved finger, just above the blanket
    sphere("bhand", 0.018, (0.05, 0.42, 0.76), M["babyskin"], scale=(1, 1.2, 0.8))
    sphere("gfinger", 1, (0.09, 0.43, 0.77), M["glove"], scale=(0.075, 0.016, 0.016))
    sphere("glove_hand", 1, (0.19, 0.44, 0.78), M["glove"], scale=(0.05, 0.075, 0.03))
    cam((-0.05, 0.22, 0.86), (0.07, 0.42, 0.76), 85, dof=0.27, fstop=1.8)


SHOTS = [  # n, start, end, builder, description
    (1, 0.00, 1.85, s_pit_top(11), "Top-down pit stop: red car in its box, twenty crew around it. Cold open."),
    (2, 1.85, 3.65, s02, "Low, shallow-focus: a tiny baby asleep in an intensive-care cot. The other half of the question."),
    (3, 3.65, 5.50, s03, "Street level, London: the hospital's long facade, a clock tower in the haze."),
    (4, 5.50, 6.90, s04, "Cutaway top-down: surgical team around the operating table under the lamps."),
    (5, 6.90, 8.15, s05, "Macro: heart monitor, steady green trace."),
    (6, 8.20, 9.60, s06, "Dim corridor: the team pushes the cot toward the intensive care doors far ahead."),
    (7, 9.60, 10.85, s07, "Floor-level: cot castors rolling."),
    (8, 10.85, 12.60, s08, "Tracking: the moving team, IV pole, ventilator, hand-bag breathing."),
    (9, 12.60, 14.20, s09, "Cutaway top-down: corridor route, theatre → intensive care (arrow overlay)."),
    (10, 14.20, 15.60, s10, "Macro: the breathing tube at the baby's face."),
    (11, 15.60, 17.10, s11, "Hands reaching for the monitor cables."),
    (12, 17.10, 18.70, s12, "High angle: lines and cables crossing over the cot, many hands."),
    (13, 18.70, 20.40, s13, "Cutaway top-down: eight people crowd one cot, no pattern."),
    (14, 20.40, 22.30, s14, "Floor-level: dropped clipboard and loose notes between shoes: details get lost."),
    (15, 22.30, 23.90, s15, "From behind: two doctors watch a Ferrari pit stop on a staff-room screen."),
    (16, 23.90, 25.55, s16, "Head-on, low: the red car arrives into its box, crew waiting."),
    (17, 25.55, 26.90, s17, "High three-quarter: the whole crew at work (counter: 20)."),
    (18, 26.90, 28.60, s18, "Macro: wheel gun on the front-left nut (timer overlay)."),
    (19, 28.60, 30.30, s19, "Top-down: every crew member in a fixed spot (role markers overlay)."),
    (20, 30.30, 31.90, s20, "Low tracking past the right side: one job each."),
    (21, 31.90, 33.80, s21, "The doctors visit the engineers in red, a red car on display."),
    (22, 33.80, 35.50, s22, "Engineers study the hospital handover footage on the wall screen."),
    (23, 35.50, 37.10, s23, "Screen close-up: the crowded handover, problems circled in red (overlay)."),
    (24, 37.10, 39.10, s24, "Driver's eye through the halo: the lollipop board ahead."),
    (25, 39.10, 40.70, s25, "The lollipop man: one person in charge of the stop."),
    (26, 40.70, 42.40, s26, "Match cut: the anaesthetist at the cot, hand raised, leading the handover."),
    (27, 42.40, 43.80, s27, "Cutaway top-down: five staff in fixed positions (numbered role markers overlay)."),
    (28, 43.80, 45.20, s28, "Hands connect the monitor lines one by one."),
    (29, 45.20, 47.55, s29, "Macro: the handover checklist, red ticks."),
    (30, 47.55, 50.35, s30, "Calm, ordered handover (overlay: −42% technical errors)."),
    (31, 50.35, 51.70, s31, "Clay bars: errors per handover 5.42 → 3.15."),
    (32, 51.70, 53.05, s32, "Clay bars: missing information 2.09 → 1.07, almost half."),
    (33, 53.05, 54.70, s33, "Low tracking: the car leaves its box at speed."),
    (34, 54.70, 56.40, s34, "The crew steps back in the empty box."),
    (35, 56.40, 58.10, s35, "Macro: the baby's hand around a gloved finger."),
    (36, 58.10, 60.00, s_pit_top(8.5), "Top-down pit stop again, pushing in: the loop back to the question."),
]


def aux():
    """Images shown on screens inside other shots (16:9)."""
    os.makedirs(AUX, exist_ok=True)
    for name, build, c in [("tv_pit", lambda: S.pit_set(car_y=-1.0), ((0, -8.5, 7.5), (0, 0.5, 0), 30)),
                           ("tv_chaos", lambda: S.icu_set("chaos"), ((0.2, -3.2, 2.6), (0, 0.4, 0.8), 24))]:
        reset()
        setup_render(960, 540, 24, os.path.join(AUX, name + ".png"))
        build()
        cam(*c)
        render()


def board(ids=None):
    os.makedirs(STILLS, exist_ok=True)
    if not ids or 15 in ids or 21 in ids or 22 in ids or 23 in ids:
        if not (os.path.exists(os.path.join(AUX, "tv_pit.png")) and os.path.exists(os.path.join(AUX, "tv_chaos.png"))):
            aux()
    for n, t0, t1, build, desc in SHOTS:
        if ids and n not in ids:
            continue
        reset()
        setup_render(540, 960, 24, os.path.join(STILLS, f"s{n:02d}.png"))
        build()
        render()
        print(f"BOARD s{n:02d} done", flush=True)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.endswith(".py")]
    if args and args[0] == "board":
        board([int(a) for a in args[1:]] or None)
    elif args and args[0] == "aux":
        aux()


def dump_json():
    import json
    out = [dict(n=n, start=t0, end=t1, desc=d) for n, t0, t1, _, d in SHOTS]
    json.dump(out, open(os.path.join(ROOT, "boards", "shots.json"), "w"), indent=1)


if __name__ == "__main__" and "json" in sys.argv:
    dump_json()
