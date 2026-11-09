"""Lay the character renders out as one model sheet (PNG) plus a phone-size JPG.

.venv-tools/Scripts/python library/characters/block_character/compose_sheet.py
-> sheet/model-sheet.png, sheet/model-sheet-preview.jpg, skins/_layout_guide.png
"""
import json
import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import template as T  # noqa: E402
import skins as SK  # noqa: E402

R = os.path.join(HERE, "sheet", "renders")
FIT = os.path.join(HERE, "..", "..", "cars", "f1_2026", "sheet", "fit")
A = json.load(open(os.path.join(R, "anchors.json")))
W, M, G = 5200, 80, 70
BG = (205, 208, 212)
PANEL = (196, 199, 204)
INK = (28, 31, 35)
SUB = (88, 94, 101)
TEAL = (0, 161, 155)
L2 = (232, 120, 30)
FONT = "C:/Windows/Fonts/bahnschrift.ttf"


def font(size, weight="Regular"):
    f = ImageFont.truetype(FONT, size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


F_TITLE, F_H, F_LBL, F_NOTE, F_SMALL, F_TINY = (font(96, "Bold"), font(40, "Bold"), font(32, "SemiBold"), font(28),
                                                font(24, "SemiBold"), font(19, "SemiBold"))


def load(name, folder=R):
    return Image.open(os.path.join(folder, name + ".png")).convert("RGBA")


def crop(im, pad=24):
    a = np.array(im)[:, :, 3]
    ys, xs = np.where(a > 8)
    box = (max(0, xs.min() - pad), max(0, ys.min() - pad), min(im.width, xs.max() + pad), min(im.height, ys.max() + pad))
    return im.crop(box), box


def fit_h(im, h):
    return im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)


def label(d, x, y, num, title, note=None):
    chip = f"{num:02d}"
    w = d.textlength(chip, font=F_H) + 26
    d.rounded_rectangle((x, y, x + w, y + 52), 8, fill=TEAL)
    d.text((x + 13, y + 5), chip, font=F_H, fill=(255, 255, 255))
    d.text((x + w + 18, y + 6), title, font=F_H, fill=INK)
    if note:
        d.text((x + w + 18 + d.textlength(title, font=F_H) + 24, y + 15), note, font=F_NOTE, fill=SUB)


def centred(d, cx, y, text, f=F_LBL, fill=INK):
    d.text((cx - d.textlength(text, font=f) / 2, y), text, font=f, fill=fill)


def dim_v(d, x, y0, y1, text, side=1):
    d.line((x, y0, x, y1), fill=INK, width=3)
    for y in (y0, y1):
        d.line((x - 14, y, x + 14, y), fill=INK, width=3)
    tw = d.textlength(text, font=F_SMALL)
    ym = (y0 + y1) / 2
    tx = x + 20 if side > 0 else x - 20 - tw
    d.rectangle((tx - 6, ym - 18, tx + tw + 6, ym + 18), fill=BG)
    d.text((tx, ym - 14), text, font=F_SMALL, fill=INK)


def dim_h(d, x0, x1, y, text):
    d.line((x0, y, x1, y), fill=INK, width=3)
    for x in (x0, x1):
        d.line((x, y - 14, x, y + 14), fill=INK, width=3)
    tw = d.textlength(text, font=F_SMALL)
    d.rectangle(((x0 + x1) / 2 - tw / 2 - 8, y - 18, (x0 + x1) / 2 + tw / 2 + 8, y + 18), fill=BG)
    d.text(((x0 + x1) / 2 - tw / 2, y - 14), text, font=F_SMALL, fill=INK)


# ---------------------------------------------------------------- skin layout guide
REGIONS = [("HEAD", "head", 1), ("HAT", "head", 2), ("BODY", "body", 1), ("JACKET", "body", 2),
           ("R ARM", "arm_R", 1), ("R SLEEVE", "arm_R", 2), ("L ARM", "arm_L", 1), ("L SLEEVE", "arm_L", 2),
           ("R LEG", "leg_R", 1), ("R TROUSERS", "leg_R", 2), ("L LEG", "leg_L", 1), ("L TROUSERS", "leg_L", 2)]


def skin_guide(skin="base", s=11, face_labels=True):
    """The 64x64 skin scaled up, with every region outlined and named. Orange = layer 2 (see-through shell)."""
    im = Image.open(os.path.join(HERE, "skins", skin + ".png")).convert("RGBA")
    big = im.resize((64 * s, 64 * s), Image.NEAREST)
    chk = Image.new("RGBA", big.size, (0, 0, 0, 0))
    dc = ImageDraw.Draw(chk)
    for y in range(64):
        for x in range(64):
            c = (176, 180, 186, 255) if (x + y) % 2 else (186, 190, 196, 255)
            dc.rectangle((x * s, y * s, x * s + s - 1, y * s + s - 1), fill=c)
    chk.alpha_composite(big)
    d = ImageDraw.Draw(chk)
    P = T.parts("classic")
    for name, part, layer in REGIONS:
        x0, x1, y0, y1, z0, z1 = P[part]["box"]
        w, h, dd = x1 - x0, z1 - z0, y1 - y0
        u, v = P[part]["uv"] if layer == 1 else P[part]["uv2"]
        col = INK if layer == 1 else L2
        d.rectangle((u * s, v * s, (u + 2 * dd + 2 * w) * s - 1, (v + dd + h) * s - 1), outline=col, width=3)
        for fname, (fx, fy, fw, fh) in SK.regions(u, v, w, h, dd).items():
            d.rectangle((fx * s, fy * s, (fx + fw) * s - 1, (fy + fh) * s - 1), outline=col + (150,) if len(col) == 3 else col, width=1)
        tw = d.textlength(name, font=F_TINY)
        tx, ty = u * s + 4, (v + dd + h) * s - 24
        d.rectangle((tx - 2, ty, tx + tw + 4, ty + 22), fill=(255, 255, 255, 215))
        d.text((tx, ty), name, font=F_TINY, fill=col)
    return chk


def main():
    sec = {}
    # ------------------------------------------------ assets
    ortho = {v: load(v) for v in ("front", "right", "back", "left")}
    OH = ortho["front"].height
    rig = {v: load("rig_" + v) for v in ("front", "right")}
    per = {v: crop(load(v))[0] for v in ("three_quarter", "back_three_quarter")}
    layers = [crop(load("layers_" + v))[0] for v in ("layer1", "layer2", "helmet")]
    poses = [(p, crop(load("pose_" + p))[0]) for p in ("idle", "walk", "run", "sit", "wave", "point", "cheer", "think",
                                                       "shrug", "fist_pump")]
    faces = load("faces")
    lineup = load("lineup")
    in_car = load("in_car")
    xray = load("fit_xray_side", FIT)

    H = 9800
    sheet = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(sheet)
    d.text((M, 60), "BLOCK CHARACTER  ·  MASTER TEMPLATE  ·  MODEL SHEET", font=F_TITLE, fill=INK)
    notes = ["One rig + one skin = one character. Change the skin, never the model.",
             "Standard Minecraft player model and 64×64 skin (classic or slim arms, two layers).",
             "1 skin pixel = 4.5 cm (house world pixel)  ·  height 32 px = 1.44 m  ·  head 8 px = 0.36 m"]
    for i, s in enumerate(notes):
        tw = d.textlength(s, font=F_NOTE)
        d.text((W - M - tw, 52 + i * 44), s, font=F_NOTE, fill=INK if i == 0 else SUB)
    y = 230
    d.line((M, y - 30, W - M, y - 30), fill=INK, width=4)

    # ------------------------------------------------ 01 turnaround
    label(d, M, y, 1, "TURNAROUND", "template skin 'base', standing")
    y += 90
    tH = 1250
    sc = tH / OH
    x = M + 330
    ppm = 900 * sc
    top_pad = 40
    for v in ("front", "right", "back", "left"):
        im, box = crop(ortho[v], pad=10)
        im = im.resize((round(im.width * sc), round(im.height * sc)), Image.LANCZOS)
        oy = y + top_pad + round(box[1] * sc)
        sheet.alpha_composite(im, (x, oy))
        centred(d, x + im.width / 2, y + top_pad + tH + 18, v.upper(), F_LBL)
        if v == "front":
            ground = y + top_pad + (OH / 2 + 0.79 * 900) * sc
            zpx = lambda z: ground - z * ppm
            xl = x - 60
            dim_v(d, xl, zpx(0), zpx(32 * T.PX), "32 px  1.44 m", -1)
            xr = x + im.width + 40
            dim_v(d, xr, zpx(24 * T.PX), zpx(32 * T.PX), "HEAD 8 px")
            dim_v(d, xr, zpx(12 * T.PX), zpx(24 * T.PX), "BODY 12 px")
            dim_v(d, xr, zpx(0), zpx(12 * T.PX), "LEGS 12 px")
            cx = x + im.width / 2
            dim_h(d, cx - 8 * T.PX * ppm, cx + 8 * T.PX * ppm, zpx(12 * T.PX) + 34, "16 px  0.72 m")
            x = xr + 230
        else:
            x += im.width + 120
    x += 40
    for v in ("three_quarter", "back_three_quarter"):
        im = fit_h(per[v], tH - 40)
        sheet.alpha_composite(im, (x, y + top_pad + 20))
        centred(d, x + im.width / 2, y + top_pad + tH + 18, "3/4 FRONT" if v == "three_quarter" else "3/4 BACK")
        x += im.width + 60
    y += tH + top_pad + 110

    # ------------------------------------------------ 02 rig | 03 skin | 04 layers
    label(d, M, y, 2, "RIG", "11 bones · bends at elbows, knees, waist")
    rx = M + 230
    ry = y + 90
    rH = 1150
    rsc = rH / OH
    for v in ("front", "right"):
        im, box = crop(rig[v], pad=10)
        im = im.resize((round(im.width * rsc), round(im.height * rsc)), Image.LANCZOS)
        ox, oy = rx + 20, ry + round(box[1] * rsc)
        sheet.alpha_composite(im, (ox, oy))
        J = A["rig"][v]
        tr = lambda p: (ox + (p[0] - box[0]) * rsc, oy + (p[1] - box[1]) * rsc)
        for b, (h, t) in J.items():
            hp, tp = tr(h), tr(t)
            d.line((*hp, *tp), fill=TEAL, width=7)
        for b, (h, t) in J.items():
            hp = tr(h)
            r_ = 13 if b.split(".")[0] in ("forearm", "shin", "chest") else 9
            col = L2 if b.split(".")[0] in ("forearm", "shin", "chest") else TEAL
            d.ellipse((hp[0] - r_, hp[1] - r_, hp[0] + r_, hp[1] + r_), fill=col, outline=(255, 255, 255), width=3)
        if v == "front":
            for b, txt, dx, dy in (("head", "head", 70, -60), ("chest", "chest", 120, -110), ("hips", "hips", -160, 40),
                                   ("upper_arm.R", "upper_arm", -190, -40), ("forearm.R", "forearm", -170, 50),
                                   ("thigh.L", "thigh", 90, 0), ("shin.L", "shin", 90, 30)):
                hp, tp = tr(J[b][0]), tr(J[b][1])
                mx, my = (hp[0] + tp[0]) / 2, (hp[1] + tp[1]) / 2
                d.line((mx, my, mx + dx, my + dy), fill=INK, width=2)
                tw = d.textlength(txt, font=F_SMALL)
                tx = mx + dx + (6 if dx > 0 else -tw - 6)
                d.text((tx, my + dy - 14), txt, font=F_SMALL, fill=INK)
        centred(d, ox + im.width / 2, ry + rH + 10, v.upper())
        rx = ox + im.width + 90
    ny = ry + rH + 70
    for i, s in enumerate(["orange joints = bends (2 px band, hinged on the inside: no folds)",
                           "forearm / shin tips = hand centre / sole (IK targets)",
                           "pose by name or joint angles · hands to objects with ik_hand()"]):
        d.text((M + 20, ny + i * 40), s, font=F_NOTE, fill=SUB)

    sx = rx + 60
    label(d, sx, y, 3, "SKIN", "standard 64×64")
    g = skin_guide("base", 11)
    sheet.alpha_composite(g, (sx, y + 90))
    gy = y + 90 + g.height + 20
    d.rectangle((sx, gy + 6, sx + 30, gy + 30), outline=INK, width=4)
    d.text((sx + 42, gy), "layer 1 (solid)", font=F_NOTE, fill=INK)
    d.rectangle((sx + 290, gy + 6, sx + 320, gy + 30), outline=L2, width=4)
    d.text((sx + 332, gy), "layer 2 (see-through shell)", font=F_NOTE, fill=INK)
    fa = Image.open(os.path.join(HERE, "skins", "base_faces.png")).convert("RGBA")
    fa = fa.resize((fa.width * 7, fa.height * 7), Image.NEAREST)
    sheet.alpha_composite(fa, (sx, gy + 60))
    d.text((sx, gy + 60 + fa.height + 10), "+ faces strip: one 8×8 front face per expression", font=F_NOTE, fill=SUB)

    lx = sx + g.width + 110
    label(d, lx, y, 4, "LAYERS")
    lw = (W - M - lx) // 3
    lh = 1000
    for i, (im, t) in enumerate(zip(layers, ("LAYER 1", "+ LAYER 2", "+ HELMET"))):
        im = fit_h(im, lh)
        if im.width > lw - 10:
            im = im.resize((lw - 10, round(im.height * (lw - 10) / im.width)), Image.LANCZOS)
        cx = lx + i * lw + lw / 2
        sheet.alpha_composite(im, (round(cx - im.width / 2), y + 100 + lh - im.height))
        centred(d, cx, y + 120 + lh, t)
    for i, s in enumerate(["layer 2: hair volume, collar, belt, glove cuffs, boot tops",
                           "helmet: optional, painted like a hat layer (helmets/<team>.png),",
                           "replaces the hair shell; sized for the F1 cockpit and halo"]):
        d.text((lx, y + 190 + lh + i * 40), s, font=F_NOTE, fill=SUB)
    y = max(ny + 140, y + 190 + lh + 160, gy + 60 + fa.height + 80)

    # ------------------------------------------------ 05 expressions
    label(d, M, y, 5, "EXPRESSIONS", "root['face'] = index · keyable, switches instantly")
    y += 90
    n = A["faces"]["n"]
    sp = A["faces"]["spacing_px"]
    fw = A["faces"]["width"]
    # heads sit on z 1.08..1.44 m; the render centre is z 1.26, 800 px per metre
    top = round(faces.height / 2 - (1.47 - 1.26) * 800)
    bot = round(faces.height / 2 - (1.07 - 1.26) * 800)
    cell = (W - 2 * M) / n
    for i, e in enumerate(T.EXPRESSIONS):
        cxp = fw / 2 + (i - (n - 1) / 2) * sp   # camera at +Y: image left = +X, the heads were placed at -x
        tile = faces.crop((round(cxp - sp * 0.42), top, round(cxp + sp * 0.42), bot))
        tile = fit_h(tile, 380)
        cx = M + cell * i + cell / 2
        sheet.alpha_composite(tile, (round(cx - tile.width / 2), y))
        centred(d, cx, y + 395, f"{i}  {e.replace('_', ' ')}", F_SMALL)
    y += 490

    # ------------------------------------------------ 06 poses
    label(d, M, y, 6, "POSE LIBRARY", "template.POSES · set_pose(p, 'wave', frame=24)")
    y += 90
    ph = 900
    cell = (W - 2 * M) / 5
    for i, (p, im) in enumerate(poses):
        r, c = divmod(i, 5)
        im = fit_h(im, ph)
        if im.width > cell - 20:
            im = im.resize((round(cell - 20), round(im.height * (cell - 20) / im.width)), Image.LANCZOS)
        cx = M + c * cell + cell / 2
        yy = y + r * (ph + 90)
        sheet.alpha_composite(im, (round(cx - im.width / 2), yy + ph - im.height))
        centred(d, cx, yy + ph + 12, p.replace("_", " ").upper())
    y += 2 * (ph + 90) + 50

    # ------------------------------------------------ 07 lineup
    label(d, M, y, 7, "SAME RIG, DIFFERENT SKINS", "set_skin(p, 'driver_rosso') · team kits match the car liveries")
    y += 80
    top_solid = int(np.where((np.array(lineup)[:, :, 3] > 250).any(axis=1))[0].min()) - 40   # shadows are see-through
    lineup = lineup.crop((0, max(0, top_solid), lineup.width, lineup.height))
    lsc = (W - 2 * M) / lineup.width
    li = lineup.resize((W - 2 * M, round(lineup.height * lsc)), Image.LANCZOS)
    sheet.alpha_composite(li, (M, y))
    for e in A["lineup"]:
        cx = M + e["px"] * lsc
        words = e["title"].split(", ")
        for k, wtxt in enumerate(words[:2]):
            centred(d, cx, y + li.height + 6 + k * 36, wtxt.replace(" (slim arms)", ""), F_SMALL if k else F_LBL,
                    INK if k == 0 else SUB)
        if "slim" in e["title"]:
            centred(d, cx, y + li.height + 78, "slim arms", F_SMALL, L2)
    y += li.height + 150

    # ------------------------------------------------ 08 fits the car | 09 make a new character
    label(d, M, y, 8, "FITS THE CAR", "seat_in_car(p, car): hands follow the steering wheel")
    y += 90
    ch_ = 760
    a = fit_h(in_car, ch_)
    sheet.alpha_composite(a, (M, y))
    c2 = fit_h(load("in_car_close"), ch_)
    sheet.alpha_composite(c2, (M + a.width + 40, y))
    b = fit_h(crop(xray, 10)[0], ch_ - 60)
    bx = M + a.width + c2.width + 100
    sheet.alpha_composite(b, (bx, y + 30))
    centred(d, M + a.width / 2, y + ch_ + 10, "SEATED, HELMET ON")
    centred(d, M + a.width + 40 + c2.width / 2, y + ch_ + 10, "HELMET UNDER THE HALO")
    centred(d, bx + b.width / 2, y + ch_ + 10, "X-RAY: BODYWORK HIDDEN")
    for i, s in enumerate(["fit_check.py: nothing pokes out, helmet clears the halo,",
                           "hands on the grips, elbows tucked inside the tub"]):
        d.text((M, y + ch_ + 60 + i * 40), s, font=F_NOTE, fill=SUB)
    nx = bx + b.width + 110
    label(d, nx, y - 90, 9, "NEW CHARACTER = NEW SKIN")
    steps = [("1", "Add a spec to skins.SKINS", "skin tone, eyes, hair, outfit, team, helmet, classic/slim"),
             ("", "or paint a 64×64 PNG", "any Minecraft skin editor; set \"png\": True"),
             ("2", "Run skins.py", "paints skins/<name>.png + its faces strip"),
             ("3", "make_character('name', skin=...)", "same rig, poses, faces and IK for every character"),
             ("", "Never edit the model", "proportions and joints live in template.py only")]
    yy = y
    for num, t1, t2 in steps:
        if num:
            d.rounded_rectangle((nx, yy, nx + 52, yy + 52), 8, fill=TEAL)
            centred(d, nx + 26, yy + 6, num, F_H, (255, 255, 255))
        d.text((nx + 76, yy + 4), t1, font=F_LBL, fill=INK)
        d.text((nx + 76, yy + 46), t2, font=F_NOTE, fill=SUB)
        yy += 112
    y += ch_ + 160

    H = y + 40
    sheet = sheet.crop((0, 0, W, H)).convert("RGB")
    out = os.path.join(HERE, "sheet")
    sheet.save(os.path.join(out, "model-sheet.png"))
    sheet.resize((W // 2, H // 2), Image.LANCZOS).save(os.path.join(out, "model-sheet-preview.jpg"), quality=88)
    skin_guide("base", 16).save(os.path.join(HERE, "skins", "_layout_guide.png"))
    print("sheet", W, H)


if __name__ == "__main__":
    main()
