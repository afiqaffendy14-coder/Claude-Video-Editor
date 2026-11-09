"""Lay the rendered kart views out as one model sheet (PNG) plus a phone-size JPG, in the F1 sheet's style.

.venv-tools/Scripts/python library/cars/kart/compose_sheet.py [livery]
"""
import json
import os
import sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kart_blueprint as bp  # noqa: E402

LIV = sys.argv[1] if len(sys.argv) > 1 else "silver_arrow"
R = os.path.join(HERE, "sheet", LIV, "renders")
A = json.load(open(os.path.join(R, "anchors.json")))
LV = bp.LIVERIES[LIV]
COND = bp.default_condition(LIV)
WORN = COND != "new"
W, M, G, PAD = 5200, 80, 80, 130
BG, INK, SUB, TEAL, LINE = (205, 208, 212), (28, 31, 35), (88, 94, 101), (0, 161, 155), (40, 44, 49)
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
    "side_left": [("front_fairing", "FRONT FAIRING", "top", -40), ("nassau", "NASSAU PANEL", "top", 40),
                  ("steering_wheel", "STEERING WHEEL", "top", -60), ("seat", "BUCKET SEAT", "top", 90),
                  ("silencer", "SILENCER", "top", -40), ("rear_bumper", "REAR BUMPER", "top", 130),
                  ("front_tyre", "FRONT TYRE 10×4.50-5", "bottom", -150), ("frame", "TUBE FRAME Ø30 mm", "bottom", 70),
                  ("side_pod", "SIDE POD", "bottom", 90), ("number_side", "RACE NUMBER", "bottom", 80),
                  ("rear_tyre", "REAR TYRE 11×7.10-5", "bottom", 210)],
    "front": [("data_logger", "DATA LOGGER", "top", 0), ("airbox", "AIRBOX", "top", -90),
              ("number_front", "NASSAU NUMBER", "bottom", -60), ("kingpin", "KINGPIN + STUB AXLE", "bottom", 200)],
    "rear": [("silencer", "SILENCER", "top", -40), ("transponder", "TRANSPONDER", "top", 140),
             ("engine", "ENGINE", "top", 60), ("rear_bumper", "REAR BUMPER", "bottom", -40),
             ("brake_disc", "BRAKE DISC", "bottom", 40), ("sprocket", "SPROCKET + CHAIN", "bottom", 120)],
    "top": [("fuel_tank", "FUEL TANK", "top", -150), ("airbox", "AIRBOX + CARB", "top", -60),
            ("engine", "ENGINE (2-STROKE, WATER-COOLED)", "top", 140), ("pedals", "PEDALS", "bottom", -40),
            ("steering_wheel", "STEERING WHEEL", "bottom", -150), ("radiator", "RADIATOR", "bottom", 60),
            ("seat", "SEAT", "bottom", 180)],
    "bottom": [("floor_tray", "FLOOR TRAY", "top", 0), ("frame", "FRAME", "top", 120),
               ("rear_axle", "REAR AXLE Ø50 mm", "bottom", 0)],
}

if WORN:  # parts the beat-up kart has lost or changed
    _swap = {"DATA LOGGER": "BARE HUB (NO LOGGER)", "TRANSPONDER": "TRANSPONDER GONE", "SIDE POD": "SIDE POD (FADED)",
             "RACE NUMBER": "PEELING NUMBER", "FRONT FAIRING": "FAIRING GONE, TUBE BUMPER" if COND == "battered" else "FAIRING (BROKEN CORNER)"}
    CALLOUTS = {v: [(a_, _swap.get(t, t), s_, dx) for a_, t, s_, dx in L_] for v, L_ in CALLOUTS.items()}


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
        end_y = ty + 34 if side == "top" else ty - 4
        d.line((ax, ay, tx, end_y), fill=LINE, width=3)
        d.ellipse((ax - 8, ay - 8, ax + 8, ay + 8), outline=(255, 255, 255), width=3, fill=TEAL)
        d.text((tx - tw / 2, ty), text, font=F_CALL, fill=INK)
        d.line((tx - tw / 2, end_y, tx + tw / 2, end_y), fill=TEAL, width=3)


def dim_h(d, x0, x1, y, text, ticks=18):
    d.line((x0, y, x1, y), fill=SUB, width=2)
    for x in (x0, x1):
        d.line((x, y - ticks, x, y + ticks), fill=SUB, width=2)
    tw = d.textlength(text, font=F_SMALL)
    d.rectangle(((x0 + x1) / 2 - tw / 2 - 10, y - 16, (x0 + x1) / 2 + tw / 2 + 10, y + 16), fill=BG)
    d.text(((x0 + x1) / 2 - tw / 2, y - 14), text, font=F_SMALL, fill=SUB)


def rgb_of(mid):
    hx = bp.mat_spec(mid, LIV)["hex"]
    return hx, tuple(int(hx[k:k + 2], 16) for k in (1, 3, 5))


def main():
    views = {v: load(v) for v in A}
    sl = views["side_left"]
    col2 = M + sl.width + G
    rw = W - M - col2                                   # right column width
    H_HEAD = 330
    y = H_HEAD
    pos = {}
    for key, h in (("A", sl.height), ("B", sl.height), ("C", views["top"].height), ("D", views["bottom"].height)):
        pos[key] = y + 60 + PAD
        y += 60 + PAD + h + PAD + 30
    y_ortho_end = y
    sheet = Image.new("RGB", (W, 16000), BG)
    d = ImageDraw.Draw(sheet)

    # header
    d.text((M, 60), f"KART-26  ·  {LIV.upper().replace('_', ' ')}  ·  GO-KART MODEL SHEET", font=F_TITLE, fill=INK)
    kind = (f"Fifth-hand club kart, same blueprint with condition='{COND}'" if WORN else
            "Senior racing kart in Minecraft-style voxel construction")
    d.text((M, 180), f"{kind}  ·  {LV['title']}  ·  #{LV['number']}", font=F_LBL, fill=SUB)
    d.text((M, 230), "Every view is rendered from one voxel blueprint (library/cars/kart/kart_blueprint.py): "
                     "identical geometry, livery and scale in every view and every video.", font=F_NOTE, fill=SUB)
    spec = ["VOXEL 1.125 cm  =  ¼ house world pixel  (½ the F1 car's)",
            "WHEELBASE 1.035 m   ·   WIDTH 1.40 m   ·   LENGTH 1.81 m",
            "TYRES 10×4.50-5 FRONT  ·  11×7.10-5 REAR  ·  5\" RIMS", "ORTHO VIEWS 950 px/m   ·   v1  ·  2026-11-08"]
    for i, s in enumerate(spec):
        tw = d.textlength(s, font=F_NOTE)
        d.text((W - M - tw, 70 + i * 48), s, font=F_NOTE, fill=INK if i == 0 else SUB)
    d.line((M, H_HEAD - 30, W - M, H_HEAD - 30), fill=INK, width=4)

    def place(v, x, yy, num, title, note=None):
        im = views[v]
        label(d, x, yy - PAD - 60, num, title, note)
        sheet.paste(im, (x, yy), im)
        callouts(d, v, x, yy, PAD, im.height)
        return im

    ppm = A["side_left"]["ppm"]
    # row A: left side, front, rear
    ya = pos["A"]
    place("side_left", M, ya, 1, "LEFT SIDE", "orthographic")
    fa = M + sl.width / 2 - (bp.WB_HALF - bp.WB_HALF * 0 - 0.03) * ppm
    ra = M + sl.width / 2 + (bp.WB_HALF + 0.03) * ppm
    fw = views["front"]
    place("front", col2, ya, 3, "FRONT", "orthographic")
    place("rear", col2 + fw.width + G, ya, 4, "REAR", "orthographic")
    dim_h(d, col2 + fw.width / 2 - 0.6975 * ppm, col2 + fw.width / 2 + 0.6975 * ppm, ya + fw.height + 40, "1.40 m")
    dim_h(d, M + fa, M + ra, ya + sl.height + 40, "WHEELBASE 1.035 m")
    # row B: right side; 3/4 front-left beside rows B and C
    yb = pos["B"]
    place("side_right", M, yb, 2, "RIGHT SIDE", "orthographic")
    qh = round(rw * 1050 / 1800)
    q = views["q_front_left"].resize((rw, qh), Image.LANCZOS)
    label(d, col2, yb - PAD - 60, 7, "FRONT-LEFT THREE-QUARTER")
    sheet.paste(q, (col2, yb - PAD + 20), q)
    # row C: top (with overall length), row D: underside + 3/4 rear-left
    yc = pos["C"]
    tp = place("top", M, yc, 5, "TOP", "orthographic, nose left")
    dim_h(d, M + tp.width / 2 - (0.935 - bp.ANCHORS["seat"][1] * 0 - 0.03) * ppm,
          M + tp.width / 2 + (0.87 + 0.03) * ppm, yc + tp.height + 40, "LENGTH 1.81 m")
    yd = pos["D"]
    place("bottom", M, yd, 6, "UNDERSIDE", "orthographic, nose left")
    yq = yb - PAD + 20 + qh + 120
    label(d, col2, yq - 70, 8, "REAR-LEFT THREE-QUARTER")
    q = views["q_rear_left"].resize((rw, qh), Image.LANCZOS)
    sheet.paste(q, (col2, yq), q)

    # palette + parts under the rear three-quarter
    x0, yy = col2, yq + qh + 140
    d.text((x0, yy - 70), "PALETTE + PARTS", font=F_H, fill=INK)
    extra = [(bp.LOWER, "lower bodywork")] if "lower" in LV["patterns"] else []
    extra += [(bp.ACCENT2, "nose tip")] if "nose_tip" in LV["patterns"] else []
    sw = [(bp.MAIN, "bodywork"), (bp.ACC, "bodywork trim"), (bp.PIN, "pin line")] + extra + [
        (bp.FRAME, "frame"), (bp.RIM, "rim"), (bp.HUB, "hubs + sprocket"), (bp.BUMPER, "bumper / plastics"),
        (bp.SEATM, "seat (fibreglass)"), (bp.CAST, "engine casting"), (bp.EXHAUST, "exhaust"), (bp.TREAD, "tread"),
        (bp.SIDEWALL, "sidewall"), (bp.PLATE, "number plate"), (bp.TRANSP, "transponder"), (bp.FUEL, "fuel"),
        (bp.RADIATOR, "radiator (2-tone)")]
    if WORN:
        sw = [x for x in sw if x[0] not in (bp.TRANSP, bp.HUB)] + [
            (bp.PATCH, "replacement pod"), (bp.SCRATCH, "scratches / raw plastic"), (bp.TAPE, "duct tape"),
            (bp.RUST, "rust"), (bp.RIM2, "odd rim")] + ([(bp.SOOT, "soot")] if COND == "battered" else [])
    for i, (mid, name) in enumerate(sw):
        cx, cy = x0 + (i % 2) * 520, yy + (i // 2) * 72
        hx, rgb = rgb_of(mid)
        d.rectangle((cx, cy, cx + 54, cy + 54), fill=rgb, outline=INK, width=2)
        if "hex2" in bp.MATS[mid]:
            alt = tuple(int(bp.MATS[mid]["hex2"][k:k + 2], 16) for k in (1, 3, 5))
            for a in range(0, 54, 9):
                for b in range(0, 54, 9):
                    if (a + b) // 9 % 2:
                        d.rectangle((cx + a, cy + b, cx + a + 8, cy + b + 8), fill=alt)
        d.text((cx + 72, cy + 2), name, font=F_LBL, fill=INK)
        d.text((cx + 72, cy + 34), hx.upper(), font=F_SMALL, fill=SUB)
    pal_end = yy + ((len(sw) + 1) // 2) * 72
    px = x0 + 1080
    lines = ["OBJECTS (Blender)", "body · rear_bumper", "steering_wheel (turns about the column)",
             "steer_FL/FR  (kingpins)  → spindle,", "  wheel → tyre · rim", "rear_axle (spins: axle, hubs,",
             "  sprocket, disc) → tyre · rim RL/RR", "", "OPTIONS", "number · livery · tyres slick | wet", "condition new | beat_up | battered", "",
             "DECALS", "placeholder sponsor words, no real logos", "", "DRIVER",
             "seat_in_car(driver, kart): kart pose,", "hands at 9 and 3 · fit_check.py: clean"]
    for i, s in enumerate(lines):
        bold = s in ("OBJECTS (Blender)", "OPTIONS", "DECALS", "DRIVER")
        d.text((px, yy + i * 46), s, font=F_LBL if bold else F_NOTE, fill=INK if bold else SUB)
    pal_end = max(pal_end, yy + len(lines) * 46)

    # with the driver
    y = max(y_ortho_end, pal_end) + 60
    label(d, M, y, 9, "WITH DRIVER", "master block character + team skin + helmet, seated by seat_in_car")
    y += 80
    cw = (W - 2 * M - G) // 2
    for i, v in enumerate(("d_front_left", "d_rear_right")):
        im = views[v].resize((cw, round(cw * views[v].height / views[v].width)), Image.LANCZOS)
        tile = Image.new("RGB", im.size, (196, 199, 204))
        tile.paste(im, (0, 0), im)
        sheet.paste(tile, (M + i * (cw + G), y))
    y += round(cw * 1300 / 1800) + 120

    # close-ups
    closes = [("c_cockpit", "COCKPIT", "taped grips, data logger gone (bare hub), scuffed seat, fuel tank, pedals"),
              ("c_engine", "ENGINE", "oily, sooty engine bay, rusted chain, burnt black-and-rust exhaust"),
              ("c_rear_axle", "REAR AXLE", "bumper hidden: rusty disc and chain, chunked rear tyres, rusty frame"),
              ("c_front_end", "FRONT END", "fairing gone: bare brackets, rusty tube bumper, zip ties, crooked nassau"),
              ("c_wheel", "WHEEL", "odd gold rim from another kart, dusty tyre, grime"),
              ("c_seat", "SEAT + RADIATOR", "seat crack taped, scuffs, transponder gone, rust on the stays")] if WORN else [
              ("c_cockpit", "COCKPIT", "butterfly wheel + data logger, column, fuel tank, pedals, floor tray"),
              ("c_engine", "ENGINE", "2-stroke, water-cooled: head + plug, carb + airbox, exhaust header"),
              ("c_rear_axle", "REAR AXLE", "bumper hidden: Ø50 mm axle, bearing hangers, vented disc + caliper, sprocket"),
              ("c_front_end", "FRONT END", "fairing, nassau + number, kingpin, stub axle, track rods"),
              ("c_wheel", "WHEEL", "5\" rim, six lightening holes, hub, valve, sidewall bands"),
              ("c_seat", "SEAT + RADIATOR", "fibreglass bucket, transponder, radiator + hoses, silencer")]
    tw_, th_ = 1600, 1200
    for i, (v, t, note) in enumerate(closes):
        r, c = divmod(i, 3)
        x = M + c * (tw_ + 80)
        yy = y + r * (70 + th_ + 90) + 70
        label(d, x, yy - 70, 10 + i, t)
        d.text((x, yy + th_ + 10), note, font=F_SMALL, fill=SUB)
        tile = Image.new("RGB", (tw_, th_), (190, 193, 198))
        im = views[v]
        tile.paste(im, (0, 0), im)
        sheet.paste(tile, (x, yy))
    y += 2 * (70 + th_ + 90) + 20
    lp = os.path.join(HERE, "sheet", "lineup.png")
    if os.path.exists(lp):                          # all four liveries, from render_lineup.py
        im = Image.open(lp).convert("RGBA")
        bb = im.getchannel("A").point(lambda v: 255 if v > 250 else 0).getbbox()
        im = im.crop((max(0, bb[0] - 60), max(0, bb[1] - 60), min(im.width, bb[2] + 60), min(im.height, bb[3] + 90)))
        im = im.resize((W - 2 * M, round(im.height * (W - 2 * M) / im.width)), Image.LANCZOS)
        label(d, M, y, 16, "LIVERIES", "same blueprint: four team liveries + the fifth-hand club kart")
        tile = Image.new("RGB", im.size, (196, 199, 204))
        tile.paste(im, (0, 0), im)
        sheet.paste(tile, (M, y + 80))
        y += 80 + im.height + 40
    H = y + 40
    sheet = sheet.crop((0, 0, W, H))
    out = os.path.join(HERE, "sheet", LIV)
    sheet.save(os.path.join(out, "model-sheet.png"), optimize=True)
    sheet.resize((W // 2, H // 2), Image.LANCZOS).save(os.path.join(out, "model-sheet-preview.jpg"), quality=88)
    print("sheet", W, H)


main()
