"""Lay out the circuit model sheet from the plan, the views and the module catalogue (Pillow, no Blender).

.venv-tools/Scripts/python library/environments/f1_circuit/compose_sheet.py
-> sheet/model-sheet.png (+ model-sheet-preview.jpg for phones)
"""
import math
import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout as L
import plan as P
import ground as S

SHEET = os.path.join(HERE, "sheet")
VIEWS = os.path.join(SHEET, "views")
CAT = os.path.join(SHEET, "catalogue")
W = 3600
M = 70
BG, INK, SUB, ACC = (236, 236, 232), (22, 22, 26), (95, 98, 105), (200, 16, 46)


def font(size, bold=False):
    for f in (("bahnschrift.ttf",), ("arialbd.ttf" if bold else "arial.ttf",)):
        try:
            return ImageFont.truetype(f[0], size)
        except OSError:
            continue
    return ImageFont.load_default()


F_T, F_H, F_L, F_S = font(78, True), font(40, True), font(30), font(23)


def section(d, y, num, title, note=""):
    d.rectangle([M, y, M + 8, y + 44], fill=ACC)
    d.text((M + 24, y - 2), f"{num:02d}  {title}", font=F_H, fill=INK)
    if note:
        d.text((M + 24 + d.textlength(f"{num:02d}  {title}", font=F_H) + 30, y + 8), note, font=F_S, fill=SUB)
    return y + 66


def paste_fit(img, path, box, label=None, d=None):
    x0, y0, x1, y1 = box
    if not os.path.exists(path):
        return
    im = Image.open(path).convert("RGB")
    w, h = x1 - x0, y1 - y0
    s = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * s + 0.5), int(im.height * s + 0.5)), Image.LANCZOS)
    cx, cy = (im.width - w) // 2, (im.height - h) // 2
    img.paste(im.crop((cx, cy, cx + w, cy + h)), (x0, y0))
    if label and d:
        tw = d.textlength(label, font=F_S)
        d.rectangle([x0, y1 - 36, x0 + tw + 24, y1], fill=(20, 20, 24))
        d.text((x0 + 12, y1 - 32), label, font=F_S, fill=(255, 255, 255))


def plan_map(width_px):
    """Top-down plan of the venue from the ground raster, with corners, stands and buildings labelled."""
    R = S.build(verbose=False)
    T = R["T"]
    pal = {S.GRASS: (120, 170, 90), S.GRASS2: (112, 162, 84), S.TRACK: (55, 56, 60), S.RUNOFF: (98, 101, 110),
           S.GRAVEL: (214, 196, 150), S.PIT: (75, 76, 82), S.ROAD: (130, 130, 128), S.CONCRETE: (196, 196, 190),
           S.PAVING: (205, 180, 150), S.PARKING: (150, 150, 150), S.WATER: (70, 130, 190), S.SAND: (226, 210, 165),
           S.DIRT: (140, 110, 80), S.HILL: (98, 150, 70)}
    img = np.zeros(T.shape + (3,), np.uint8)
    for k, c in pal.items():
        img[T == k] = c
    fine = R["fine"]
    for k, c in ((S.KERB_R, (210, 40, 40)), (S.WHITE, (250, 250, 250)), (S.GREEN, (60, 160, 80))):
        m = (fine == k).mean(axis=(1, 2)) > 0.3
        img[R["fine_j"][m], R["fine_i"][m]] = c
    i0, j0 = S.ij(S.VENUE[0], S.VENUE[2])
    i1, j1 = S.ij(S.VENUE[1], S.VENUE[3])
    crop = img[j0:j1, i0:i1][::-1]
    im = Image.fromarray(crop)
    sc = width_px / im.width
    im = im.resize((width_px, int(im.height * sc)), Image.NEAREST)
    d = ImageDraw.Draw(im)

    def px(x, y):
        return ((x - S.VENUE[0]) * sc, (S.VENUE[3] - y) * sc)

    def poly(r, fill, outline=(30, 30, 30)):
        d.polygon([px(*c) for c in P.corners(r)], fill=fill, outline=outline)

    for st in P.stands():
        poly(st["rect"], (40, 80, 160))
    pb = P.PIT_BUILDING
    poly(P.rect((pb["x0"] + pb["x1"]) / 2, pb["y_front"] - 13, pb["x1"] - pb["x0"], 26), (230, 230, 230))
    for _, r in P.motorhomes():
        poly(r, (200, 200, 200))
    for r, col in ((P.MEDICAL, (60, 160, 90)), (P.FIRE_STATION, (190, 40, 40)), (P.HOSPITALITY_VIP, (230, 190, 60)),
                   (P.HOTEL, (200, 200, 220))):
        poly(r, col)
    # barrier lines
    for side in (1, -1):
        off, pit = R["bo"][side]
        pts = S.polyline_from(R["s_b"][::3], off[::3], side)
        keep = ~pit[::3]
        for a, b, k in zip(pts[:-1], pts[1:], keep[:-1]):
            if k:
                d.line([px(*a), px(*b)], fill=(240, 240, 240), width=2)
    fs = font(max(18, int(26 * sc)), True)
    for lab in L.CORNERS:
        a, b = L.corner_range(lab)
        cs = L.corner_side(lab)
        x, y, _ = L.frame((a + b) / 2, -cs * 42)
        X, Y = px(x, y)
        d.ellipse([X - 22, Y - 22, X + 22, Y + 22], fill=ACC)
        t = lab[1:]
        d.text((X - d.textlength(t, font=fs) / 2, Y - 15), t, font=fs, fill=(255, 255, 255))
    fl = font(max(16, int(22 * sc)))
    for txt, (x, y) in (("START / FINISH", (L.SF_X, 40)), ("PIT LANE + GARAGES", (-80, -48)), ("PADDOCK", (-60, -100)),
                        ("MEDICAL", (150, -132)), ("LAKE", (300, -560)), ("FAN ZONE", (-160, -460)),
                        ("ENTRANCE", (-60, 140)), ("CAR PARKS", (60, 270)), ("RACE CONTROL", (60, -10))):
        X, Y = px(x, y)
        tw = d.textlength(txt, font=fl)
        d.rectangle([X - tw / 2 - 6, Y - 4, X + tw / 2 + 6, Y + 26], fill=(20, 20, 24))
        d.text((X - tw / 2, Y - 2), txt, font=fl, fill=(255, 255, 255))
    for det, act, end in L.drs_zones():
        for s_, col in ((act, (60, 200, 255)), (end, (60, 200, 255))):
            x, y, _ = L.frame(s_)
            X, Y = px(x, y)
            d.rectangle([X - 5, Y - 5, X + 5, Y + 5], fill=col)
    # scale bar
    X0, Y0 = 30, im.height - 50
    d.rectangle([X0, Y0, X0 + 200 * sc, Y0 + 12], fill=(20, 20, 24))
    d.text((X0, Y0 - 34), "200 m", font=fl, fill=(20, 20, 24))
    return im


def main():
    H = 13000
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((M, 50), "CIRCUIT-26  ·  GRAND PRIX CIRCUIT  ·  ENVIRONMENT MODEL SHEET", font=F_T, fill=INK)
    d.text((M, 150), f"Minecraft-style block circuit for the F1 Shorts  ·  lap {L.LAP / 1000:.3f} km, {len(L.CORNERS)} corners, "
           f"clockwise  ·  1 block = 1 m, 16 px per block  ·  modular, instanced, day and night", font=F_L, fill=SUB)
    y = 230
    y = section(d, y, 1, "LAYOUT", "lap distance s drives everything: track, kerbs, run-off, barriers, props")
    mp = plan_map(2400)
    img.paste(mp, (M, y))
    fx = M + 2400 + 60
    facts = [
        ("LAP", f"{L.LAP:.0f} m, clockwise"), ("MAIN STRAIGHT", "980 m, 15 m wide, DRS"),
        ("BACK STRAIGHT", f"{L.PRIMS[L.BACK].length:.0f} m, DRS"), ("CORNERS", "hairpin T4, fast T3/T10-12,"),
        ("", "esses T8-9, chicane T13-14"), ("TRACK WIDTH", "13-15 m"), ("KERBS", "1.5 m, 1 m red/white stripes"),
        ("RUN-OFF", "gravel traps / painted asphalt"), ("BARRIERS", "concrete, armco, tyre walls,"),
        ("", "debris fence on every barrier"), ("PIT LANE", f"{L.PIT_LEN:.0f} m, {L.PIT_W:.0f} m wide, 10 boxes"),
        ("GARAGES", "10 teams x 2 bays, 3 floors"), ("GRID", f"{L.GRID_SLOTS} slots, 8 m pitch"),
        ("STANDS", f"{len(P.stands())} stands, ~20,000 spectators"), ("MARSHALS", f"{len(P.marshal_posts())} posts, digital flags"),
        ("LIGHTING", "day / golden / overcast / night"), ("", "floodlights on masts + roofs"),
    ]
    yy = y + 10
    for k, v in facts:
        if k:
            d.text((fx, yy), k, font=F_S, fill=ACC)
        d.text((fx + 260, yy), v, font=F_S, fill=INK)
        yy += 44
    legend = [((55, 56, 60), "track"), ((98, 101, 110), "asphalt run-off"), ((214, 196, 150), "gravel trap"),
              ((210, 40, 40), "kerbs"), ((40, 80, 160), "grandstands"), ((240, 240, 240), "barrier line"),
              ((60, 200, 255), "DRS activation / end"), ((75, 76, 82), "pit lane")]
    yy += 30
    for col, t in legend:
        d.rectangle([fx, yy + 4, fx + 30, yy + 30], fill=col, outline=(30, 30, 30))
        d.text((fx + 46, yy), t, font=F_S, fill=INK)
        yy += 42
    y += mp.height + 60

    y = section(d, y, 2, "DAY", "camera presets cam_* (nothing locked; aim() makes new ones)")
    day = [("cam_establishing", "establishing"), ("cam_grid_three_quarter", "grid, three-quarter"),
           ("cam_pit_lane", "pit lane"), ("cam_esses_three_quarter", "esses, aerial three-quarter"),
           ("cam_back_straight_side", "back straight, side"), ("cam_T1_track_level", "Turn 1, track level"),
           ("cam_hairpin_aerial", "hairpin, aerial"), ("cam_grid_track_level", "start gantry, track level"),
           ("cam_bridge_view", "from the spectator bridge")]
    cw, ch_ = (W - 2 * M - 2 * 24) // 3, int(((W - 2 * M - 2 * 24) // 3) * 9 / 16)
    for k, (cam, lab) in enumerate(day):
        x0 = M + (k % 3) * (cw + 24)
        y0 = y + (k // 3) * (ch_ + 24)
        paste_fit(img, os.path.join(VIEWS, f"{cam}_day.png"), (x0, y0, x0 + cw, y0 + ch_), lab, d)
    y += 3 * (ch_ + 24) + 40

    y = section(d, y, 3, "NIGHT", "set_time('night'): floodlight masts, roof lights, lit garages, windows and screens")
    night = [("cam_establishing", "establishing"), ("cam_grid_track_level", "start / finish"),
             ("cam_pit_lane", "pit lane"), ("cam_esses_three_quarter", "esses"), ("cam_back_straight_side", "back straight"),
             ("cam_paddock", "paddock")]
    for k, (cam, lab) in enumerate(night):
        x0 = M + (k % 3) * (cw + 24)
        y0 = y + (k // 3) * (ch_ + 24)
        paste_fit(img, os.path.join(VIEWS, f"{cam}_night.png"), (x0, y0, x0 + cw, y0 + ch_), lab, d)
    y += 2 * (ch_ + 24) + 40

    y = section(d, y, 4, "CLOSE-UPS", "scale: block character 1.44 m, F1 car 5.6 m")
    close = [("cam_crowd_close", "day", "grandstand crowd"), ("cam_pit_box", "day", "garage + pit box"),
             ("cam_garage", "day", "inside a garage"), ("cam_tyre_wall", "day", "tyre wall, concrete, debris fence"),
             ("cam_marshal_post", "day", "marshal post + digital flag panel"), ("cam_chicane_kerbs", "day", "chicane kerbs")]
    for k, (cam, mode, lab) in enumerate(close):
        x0 = M + (k % 3) * (cw + 24)
        y0 = y + (k // 3) * (ch_ + 24)
        paste_fit(img, os.path.join(VIEWS, f"{cam}_{mode}.png"), (x0, y0, x0 + cw, y0 + ch_), lab, d)
    y += 2 * (ch_ + 24) + 40

    y = section(d, y, 5, "WITH THE LIBRARY RIGS", "library cars + drivers driving T1 (lap_frame, bake_roll, steer), kart in the paddock")
    at = os.path.join(SHEET, "anim_test")
    shots = [("cam_test_chase_020.png", "chase, braking for T1"), ("cam_test_chase_060.png", "chase, through T1"),
             ("kart_paddock.png", "fifth-hand kart in the paddock")]
    for k, (f, lab) in enumerate(shots):
        x0 = M + k * (cw + 24)
        paste_fit(img, os.path.join(at, f), (x0, y, x0 + cw, y + ch_), lab, d)
    y += ch_ + 64

    y = section(d, y, 6, "MODULES", "each piece is a prototype, instanced on editable points (blocks.scatter)")
    names = sorted(f[:-4] for f in os.listdir(CAT) if f.endswith(".png") and not f.startswith("stand_end"))
    names = [n for n in names if not (n.startswith("stand_") and n not in ("stand_main_grandstand", "stand_stand_T1", "stand_stand_T13"))]
    cols = 10
    tw = (W - 2 * M - (cols - 1) * 14) // cols
    th = int(tw * 0.75)
    for k, n in enumerate(names):
        x0 = M + (k % cols) * (tw + 14)
        y0 = y + (k // cols) * (th + 14)
        paste_fit(img, os.path.join(CAT, n + ".png"), (x0, y0, x0 + tw, y0 + th), n.replace("stand_stand_", "stand_"), d)
    y += ((len(names) + cols - 1) // cols) * (th + 14) + 40

    y = section(d, y, 7, "QUALITY CONTROL", "qc.py on the saved blend (sheet/qc_report.md)")
    rep = os.path.join(SHEET, "qc_report.md")
    lines = [l for l in open(rep, encoding="utf8").read().splitlines() if l.startswith("- [") or l.startswith("**Result")] if os.path.exists(rep) else []
    for l in lines:
        ok = l.startswith("- [x]") or "PASS" in l
        t = l.replace("- [x] ", "").replace("- [ ] ", "").replace("**", "")
        if len(t) > 150:
            t = t[:147] + "..."
        d.text((M + 20, y), ("OK   " if ok else "FIX  ") + t, font=F_S, fill=(30, 120, 60) if ok else ACC)
        y += 36
    y += 40
    img = img.crop((0, 0, W, y))
    img.save(os.path.join(SHEET, "model-sheet.png"))
    pv = img.resize((1600, int(y * 1600 / W)), Image.LANCZOS)
    pv.save(os.path.join(SHEET, "model-sheet-preview.jpg"), quality=86)
    print("sheet", img.size)


if __name__ == "__main__":
    main()
