"""Lay the rendered views out as one model sheet (PNG) plus a phone-size JPG.

.venv-tools/Scripts/python library/cars/f1_2026/compose_sheet.py
"""
import json
import os
import sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blueprint as bp  # noqa: E402

LIV = sys.argv[1] if len(sys.argv) > 1 else "silver_arrow"
R = os.path.join(HERE, "sheet", LIV, "renders")
A = json.load(open(os.path.join(R, "anchors.json")))
LV = bp.LIVERIES[LIV]
W = 5200
M = 80          # outer margin
G = 80          # gap between panels
BG = (205, 208, 212)
INK = (28, 31, 35)
SUB = (88, 94, 101)
TEAL = (0, 161, 155)
LINE = (40, 44, 49)
FONT = "C:/Windows/Fonts/bahnschrift.ttf"


def font(size, weight="Regular"):
    f = ImageFont.truetype(FONT, size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


F_TITLE, F_H, F_LBL, F_NOTE, F_CALL, F_SMALL = (font(96, "Bold"), font(40, "Bold"), font(34, "SemiBold"),
                                               font(28), font(26, "SemiBold"), font(24))

# callouts: view -> [(anchor, text, 'top'|'bottom', x shift in px)]
CALLOUTS = {
    "side_left": [("front_wing", "FRONT WING", "top", -40), ("nose", "NOSE", "top", 130),
                  ("cockpit", "COCKPIT", "top", -70), ("halo", "HALO", "top", 80),
                  ("air_intake", "AIR INTAKE / ROLL HOOP", "top", 120), ("rear_wing", "REAR WING", "top", -60),
                  ("slick_tyre", "SLICK TYRE  Ø0.72 m", "bottom", -170), ("front_suspension", "FRONT SUSPENSION (PUSHROD)",
                                                                          "bottom", 360),
                  ("sidepod", "SIDEPOD", "bottom", 40), ("floor", "FLOOR / EDGE WING", "bottom", -260),
                  ("rear_suspension", "REAR SUSPENSION (PULLROD)", "bottom", 120),
                  ("diffuser", "DIFFUSER", "bottom", 160)],
    "front": [("endplate", "ENDPLATE", "top", -80), ("mirror", "MIRROR", "top", -10),
              ("front_brake_duct", "BRAKE DUCT", "bottom", 170), ("sidepod_inlet", "SIDEPOD INLET", "bottom", -190)],
    "rear": [("rain_light", "RAIN LIGHT", "bottom", 120), ("rear_brake_duct", "BRAKE DUCT + WINGLETS", "top", -60),
             ("exhaust", "EXHAUST", "top", 260)],
    "top": [("halo", "HALO (TOP)", "top", 0), ("engine_cover", "ENGINE COVER" + (" · STAR FIELD" if "stars" in bp.LIVERIES[sys.argv[1] if len(sys.argv) > 1 else "silver_arrow"]["patterns"] else ""), "top", 60),
            ("number", "RACE NUMBER", "bottom", 0)],
    "bottom": [("plank", "PLANK + TITANIUM SKID BLOCKS", "top", 0), ("diffuser", "DIFFUSER FENCES", "bottom", 0)],
}
MIRROR_X = {"top": 1, "bottom": -1}  # top/bottom anchors: use the car's centre line


def load(v):
    return Image.open(os.path.join(R, v + ".png")).convert("RGBA")


def label(d, x, y, num, title, note=None):
    chip = f"{num:02d}"
    w = d.textlength(chip, font=F_H) + 26
    d.rounded_rectangle((x, y, x + w, y + 52), 8, fill=TEAL)
    d.text((x + 13, y + 5), chip, font=F_H, fill=(255, 255, 255))
    d.text((x + w + 18, y + 6), title, font=F_H, fill=INK)
    if note:
        d.text((x + w + 18 + d.textlength(title, font=F_H) + 24, y + 15), note, font=F_NOTE, fill=SUB)


def callouts(d, v, ox, oy, pad_top, h):
    for name, text, side, dx in CALLOUTS.get(v, []):
        px, py, _ = A[v]["points"][name]
        ax, ay = ox + px, oy + py
        ty = oy - pad_top + 18 if side == "top" else oy + h + pad_top - 48
        tx = ax + dx
        tw = d.textlength(text, font=F_CALL)
        lx = min(max(tx, ax - 10), ax + 10) if abs(dx) < 1 else tx
        end_y = ty + 34 if side == "top" else ty - 4
        d.line((ax, ay, lx, end_y), fill=LINE, width=3)
        d.ellipse((ax - 8, ay - 8, ax + 8, ay + 8), outline=(255, 255, 255), width=3, fill=TEAL)
        d.text((lx - tw / 2, ty), text, font=F_CALL, fill=INK)
        d.line((lx - tw / 2, end_y, lx + tw / 2, end_y), fill=TEAL, width=3)


def dim_h(d, x0, x1, y, text, ticks=18):
    d.line((x0, y, x1, y), fill=SUB, width=2)
    for x in (x0, x1):
        d.line((x, y - ticks, x, y + ticks), fill=SUB, width=2)
    tw = d.textlength(text, font=F_SMALL)
    d.rectangle(((x0 + x1) / 2 - tw / 2 - 10, y - 16, (x0 + x1) / 2 + tw / 2 + 10, y + 16), fill=BG)
    d.text(((x0 + x1) / 2 - tw / 2, y - 14), text, font=F_SMALL, fill=SUB)


def main():
    views = {v: load(v) for v in A}
    PAD = 130  # label band above and below each orthographic view
    col2 = M + 2746 + G
    rows = [("A", 542), ("B", 542), ("C", 1051), ("D", 1051)]
    H_HEAD = 330
    y = H_HEAD
    pos = {}
    for key, h in rows:
        pos[key] = y + 60 + PAD
        y += 60 + PAD + h + PAD + 30
    y_close = y + 10
    tile_w, tile_h = 1600, 1200
    H = y_close + 2 * (60 + tile_h + G) + 120
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)

    # header
    d.text((M, 60), f"F1-26  ·  {LIV.upper().replace('_', ' ')}  ·  HERO CAR MODEL SHEET", font=F_TITLE, fill=INK)
    d.text((M, 180), f"2026 F1 car in Minecraft-style voxel construction  ·  {LV['title']}  ·  #{LV['number']}",
           font=F_LBL, fill=SUB)
    d.text((M, 230), "Every view is rendered from one voxel blueprint (library/cars/f1_2026/blueprint.py): "
                     "identical geometry, livery and scale in every view and every video.", font=F_NOTE, fill=SUB)
    spec = ["VOXEL 2.25 cm  =  ½ house world pixel", "WHEELBASE 3.375 m   ·   WIDTH 1.89 m   ·   HEIGHT 1.00 m",
            "TYRES Ø0.72 m  ·  FRONT 0.27 m / REAR 0.36 m  ·  18\" RIMS", "ORTHO VIEWS 480 px/m   ·   v2  ·  2026-11-08"]
    for i, s in enumerate(spec):
        tw = d.textlength(s, font=F_NOTE)
        d.text((W - M - tw, 70 + i * 48), s, font=F_NOTE, fill=INK if i == 0 else SUB)
    d.line((M, H_HEAD - 30, W - M, H_HEAD - 30), fill=INK, width=4)

    def place(v, x, yy, num, title, note=None, pad=PAD):
        im = views[v]
        label(d, x, yy - pad - 60, num, title, note)
        sheet.paste(im, (x, yy), im)
        callouts(d, v, x, yy, pad, im.height)
        return im

    # row A: left side, front, rear
    ya = pos["A"]
    sl = place("side_left", M, ya, 1, "LEFT SIDE", "orthographic")
    p = A["side_left"]["points"]
    ppm = A["side_left"]["ppm"]
    front_axle = sl.width / 2 - (bp.WB_HALF - 0.09) * ppm
    rear_axle = sl.width / 2 + (bp.WB_HALF + 0.09) * ppm
    place("front", col2, ya, 3, "FRONT", "orthographic")
    place("rear", col2 + 1051 + G, ya, 4, "REAR", "orthographic")
    fw = views["front"]
    dim_h(d, col2 + fw.width / 2 - 0.945 * ppm, col2 + fw.width / 2 + 0.945 * ppm, ya + fw.height + 40, "1.89 m")
    # row B: right side; 3/4 front-left beside rows B and C
    yb = pos["B"]
    place("side_right", M, yb, 2, "RIGHT SIDE", "orthographic")
    dim_h(d, M + front_axle, M + rear_axle, ya + sl.height + 40, "WHEELBASE 3.375 m")
    q = views["q_front_left"].resize((2194, 1280), Image.LANCZOS)
    label(d, col2, yb - PAD - 60, 7, "FRONT-LEFT THREE-QUARTER")
    sheet.paste(q, (col2, yb - PAD + 20), q)
    # row C: top; row D: bottom + 3/4 rear-left
    yc = pos["C"]
    place("top", M, yc, 5, "TOP", "orthographic, nose left")
    yd = pos["D"]
    place("bottom", M, yd, 6, "UNDERSIDE", "orthographic, nose left")
    q = views["q_rear_left"].resize((2194, 1280), Image.LANCZOS)
    yq = yb - PAD + 20 + 1280 + 120
    label(d, col2, yq - 70, 8, "REAR-LEFT THREE-QUARTER")
    sheet.paste(q, (col2, yq), q)
    y_pal = yq + 1280 + 120

    # close-ups
    closes = [("c_cockpit", "COCKPIT", "empty, sized for a block driver: halo, headrest, steering wheel"),
              ("c_front_wing", "FRONT WING", "main plane + 2 flaps, endplate, footplate, canard, strakes"),
              ("c_sidepod", "SIDEPOD", "inlet + radiator, undercut, silver claw livery, louvres"),
              ("c_rear_wing", "REAR WING + DIFFUSER", "flap, twin pylons, endplate lights, fences"),
              ("c_wheel", "WHEEL", "10-spoke 18\" rim, lime nut, compound band, sidewall text"),
              ("c_brake", "BRAKE ASSEMBLY", "tyre + rim hidden: drilled disc, caliper, upright, duct")]
    for i, (v, t, note) in enumerate(closes):
        r, c = divmod(i, 3)
        x = M + c * (tile_w + 80)
        yy = y_close + r * (60 + tile_h + G) + 70
        label(d, x, yy - 70, 9 + i if i < 5 else 13, t)
        d.text((x, yy + tile_h + 8), note, font=F_SMALL, fill=SUB)
        tile = Image.new("RGB", (tile_w, tile_h), (190, 193, 198))
        im = views[v]
        tile.paste(im, (0, 0), im)
        sheet.paste(tile, (x, yy))
    # palette and parts panel
    x0 = col2
    yy = y_pal + 70
    d.text((x0, yy - 70), "PALETTE + PARTS", font=F_H, fill=INK)
    extra = [(k, n) for k, n in ((bp.STAR, "star motif"), (bp.LOWER, "lower body"), (bp.ACCENT2, "nose tip"))
             if k in LV["paint"] and (k != bp.STAR or "stars" in LV["patterns"])
             and (k != bp.ACCENT2 or "nose_tip" in LV["patterns"])][:1]
    sw = [(bp.SILVER, "top paint"), (bp.BLACK, "body paint"), (bp.TEAL, "accent"), (bp.WING, "wings"),
          (bp.HALO, "halo")] + extra + [(bp.WHITE, "decals"), (bp.CARBON, "carbon (2-tone weave)"), (bp.TREAD, "tread"),
          (bp.SIDEWALL, "sidewall"), (bp.RIM, "rim"), (bp.NUT, "wheel nut"), (bp.BAND, "compound band (medium)"),
          (bp.PLANK, "plank"), (bp.TITAN, "titanium"), (bp.RAIN, "rain light")]
    for i, (mid, name) in enumerate(sw):
        cx, cy = x0 + (i % 2) * 560, yy + (i // 2) * 72
        hx = bp.mat_spec(mid, LIV)["hex"]
        rgb = tuple(int(hx[k:k + 2], 16) for k in (1, 3, 5))
        d.rectangle((cx, cy, cx + 54, cy + 54), fill=rgb, outline=INK, width=2)
        if mid == bp.CARBON:
            alt = tuple(int(bp.MATS[mid]["hex2"][k:k + 2], 16) for k in (1, 3, 5))
            for a in range(0, 54, 9):
                for b in range(0, 54, 9):
                    if (a + b) // 9 % 2:
                        d.rectangle((cx + a, cy + b, cx + a + 8, cy + b + 8), fill=alt)
        d.text((cx + 72, cy + 2), name, font=F_LBL, fill=INK)
        d.text((cx + 72, cy + 34), hx.upper(), font=F_SMALL, fill=SUB)
    px = x0 + 1160
    lines = ["OBJECTS (Blender)", "body · suspension · steering_wheel",
             "wheel_FL/FR/RL/RR  (spin at the axle)", "  → tyre · rim · disc", "brake_FL/FR/RL/RR  (steer, don't spin)",
             "", "OPTIONS", "number · livery · tyre compound", "soft · medium · hard · inter · wet",
             "", "DECALS", "placeholder sponsor words, no real logos;", "any text can be set per livery",
             "", "COCKPIT", "fits a scale-1 block character + helmet", "(seat point: blueprint.SEAT)"]
    for i, s in enumerate(lines):
        bold = s in ("OBJECTS (Blender)", "OPTIONS", "DECALS")
        d.text((px, yy + i * 46), s, font=F_LBL if bold else F_NOTE, fill=INK if bold else SUB)

    out = os.path.join(HERE, "sheet", LIV)
    sheet.save(os.path.join(out, "model-sheet.png"), optimize=True)
    sm = sheet.resize((W // 2, H // 2), Image.LANCZOS)
    sm.save(os.path.join(out, "model-sheet-preview.jpg"), quality=88)
    print("sheet", W, H)


main()
