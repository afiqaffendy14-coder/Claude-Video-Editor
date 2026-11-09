"""Lay the driver review renders out as one sheet: sheet/drivers-sheet.png (+ phone JPG).

.venv-tools/Scripts/python library/characters/block_character/compose_drivers.py
"""
import os
import sys
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from compose_sheet import (BG, INK, SUB, F_TITLE, F_LBL, F_NOTE, F_SMALL, label, crop, fit_h, centred)  # noqa: E402

D = os.path.join(HERE, "sheet", "drivers")
W, M = 5200, 80
TEAMS = [("silver_arrow", "SILVER ARROW", "yellow helmet"), ("rosso", "ROSSO", "white helmet"),
         ("papaya", "PAPAYA", "lime helmet"), ("midnight", "MIDNIGHT", "white helmet")]


def load(n):
    return Image.open(os.path.join(D, n + ".png")).convert("RGBA")


def main():
    sheet = Image.new("RGBA", (W, 7000), BG + (255,))
    d = ImageDraw.Draw(sheet)
    d.text((M, 60), "RACE DRIVERS  ·  HELMETS ON  ·  IN THE CAR", font=F_TITLE, fill=INK)
    for i, s in enumerate(["Master block character + team skin + helmet. Same rig as every other character.",
                           "Suits match the car livery; each helmet is the driver's own design so it reads in the cockpit."]):
        tw = d.textlength(s, font=F_NOTE)
        d.text((W - M - tw, 62 + i * 44), s, font=F_NOTE, fill=INK if i == 0 else SUB)
    y = 230
    d.line((M, y - 30, W - M, y - 30), fill=INK, width=4)

    label(d, M, y, 1, "HELMETS ON", "make_character(name, skin='driver_rosso', helmet=True)")
    y += 90
    st = crop(load("standing"), 20)[0]
    st = fit_h(st, 1000)
    sheet.alpha_composite(st, (M, y))
    x0 = M + st.width + 60
    cw = (W - M - x0) / 4
    for i, (t, name, helm) in enumerate(TEAMS):
        im = load("helmet_" + t)
        im = im.resize((round(cw - 30), round(cw - 30)), Image.LANCZOS)
        cx = x0 + i * cw + cw / 2
        sheet.alpha_composite(im, (round(cx - im.width / 2), y + 60))
        centred(d, cx, y + 80 + im.height, name, F_LBL)
        centred(d, cx, y + 122 + im.height, helm, F_SMALL, SUB)
    y += 1000 + 110

    label(d, M, y, 2, "SEATED IN THEIR TEAM CARS", "seat_in_car(driver, car): driver pose, hands on the grips")
    y += 90
    cw = (W - 2 * M - 60) / 2
    for i, (t, name, helm) in enumerate(TEAMS):
        r, c = divmod(i, 2)
        im = load("car_" + t)
        im = im.resize((round(cw), round(im.height * cw / im.width)), Image.LANCZOS)
        xx, yy = M + c * (cw + 60), y + r * (im.height + 90)
        sheet.alpha_composite(im, (round(xx), yy))
        centred(d, xx + cw / 2, yy + im.height + 14, f"{name}  ·  {helm}")
    y += 2 * (round(1000 * cw / 1500) + 90) + 40

    label(d, M, y, 3, "ONBOARD + HANDS ON THE WHEEL", "the grips are parented to the steering wheel")
    y += 90
    cw = (W - 2 * M - 120) / 3
    for i, (n, t) in enumerate((("tcam", "T-CAM VIEW"), ("xray", "X-RAY: STEER 0°"),
                                ("xray_steer", "X-RAY: STEER 25° (HANDS FOLLOW)"))):
        im = load(n)
        im = im.resize((round(cw), round(im.height * cw / im.width)), Image.LANCZOS)
        xx = M + i * (cw + 60)
        sheet.alpha_composite(im, (round(xx), y))
        centred(d, xx + cw / 2, y + im.height + 14, t)
    y += round(1000 * cw / 1500) + 80
    d.text((M, y), "X-ray views hide the bodywork to show the seated pose: reclined at the cockpit angle, legs down "
                   "the nose, elbows tucked inside the tub. fit_check.py: nothing pokes out, the helmet clears the halo.",
           font=F_NOTE, fill=SUB)
    y += 90
    out = sheet.crop((0, 0, W, y)).convert("RGB")
    out.save(os.path.join(HERE, "sheet", "drivers-sheet.png"))
    out.resize((W // 2, y // 2), Image.LANCZOS).save(os.path.join(HERE, "sheet", "drivers-sheet-preview.jpg"), quality=88)
    print("drivers sheet", W, y)


if __name__ == "__main__":
    main()
