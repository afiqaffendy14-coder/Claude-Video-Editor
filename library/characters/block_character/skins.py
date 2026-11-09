"""Skins for the master block character: a skin is a short spec here, painted into a standard 64x64 Minecraft skin.

    .venv-tools/Scripts/python library/characters/block_character/skins.py      # (re)paints every skin
    -> skins/<name>.png        the skin (standard Java layout, layer 1 + layer 2), editable in any skin editor
       skins/<name>_faces.png  one 8x8 front face per template.EXPRESSIONS entry (what root["face"] switches)
       helmets/<team>.png      helmet textures, painted in the hat area of a 64x64 skin

A hand-painted skin also works: drop <name>.png into skins/ and add a spec with "png": True. Its faces atlas is
then made from its own face (eyes/brows/mouth are redrawn at the standard positions using the spec's colours).
No real logos or likenesses: team kits are colour schemes matching the car liveries.
"""
import os
import sys
import zlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import template as T  # noqa: E402

TONES = {"light": "#F2C9A5", "fair": "#E3B08A", "medium": "#C98E62", "tan": "#A8704A", "brown": "#7E4E2E",
         "dark": "#5A3520"}

# team kits: suit main, panel, accent, gloves/boots (match the car liveries); helmet = the driver's own design
# (main, stripe, trim), deliberately contrasting with the car so the helmet reads in the cockpit
TEAMS = {
    "silver_arrow": dict(main="#1A1B1F", panel="#A9AEB5", accent="#00A19B", glove="#1A1B1F", boot="#121316",
                         helmet=("#F2C200", "#16171A", "#00A19B")),
    "rosso": dict(main="#C8090F", panel="#141416", accent="#FFD400", glove="#C8090F", boot="#141416",
                  helmet=("#F2F2F2", "#D10A11", "#1F4FA8")),
    "papaya": dict(main="#FF7A00", panel="#1E1F22", accent="#3FA9F5", glove="#1E1F22", boot="#1E1F22",
                   helmet=("#C6F000", "#1E1F22", "#FF7A00")),
    "midnight": dict(main="#1C2445", panel="#E1062C", accent="#FFC906", glove="#1C2445", boot="#10142A",
                     helmet=("#E9EAEC", "#E1062C", "#1C2445")),
    # club karter on a fifth-hand kart: an old grey hand-me-down suit, orange second-hand helmet
    "fifth_hand": dict(main="#5B6770", panel="#E0B32A", accent="#B3261E", glove="#2B2B2E", boot="#2B2B2E",
                       helmet=("#E8742A", "#F2F2EE", "#1E1F22")),
}

SKINS = {
    "base": dict(title="Template (casual)", model="classic", tone="medium", eyes="#3B6EA8",
                 hair=("short", "#4A2F1E"), outfit=dict(kind="tee", top="#E9E9E6", legs="#3B5B8E", shoes="#2B2B2E")),
    "driver_silver_arrow": dict(title="Driver, Silver Arrow team", model="classic", tone="tan", eyes="#3A2A1E",
                                hair=("short", "#20160F"), outfit=dict(kind="race_suit", team="silver_arrow"),
                                helmet="silver_arrow", beard="#20160F"),
    "driver_rosso": dict(title="Driver, Rosso team", model="classic", tone="fair", eyes="#4C7A3C",
                         hair=("swept", "#3A2416"), outfit=dict(kind="race_suit", team="rosso"), helmet="rosso"),
    "driver_papaya": dict(title="Driver, Papaya team", model="classic", tone="light", eyes="#3B6EA8",
                          hair=("curly", "#8A5A2B"), outfit=dict(kind="race_suit", team="papaya"), helmet="papaya"),
    "driver_midnight": dict(title="Driver, Midnight team", model="classic", tone="light", eyes="#2E5C8A",
                            hair=("buzz", "#5B4630"), outfit=dict(kind="race_suit", team="midnight"),
                            helmet="midnight"),
    "mechanic_silver_arrow": dict(title="Mechanic, Silver Arrow team (slim arms)", model="slim", tone="brown",
                                  eyes="#2A1C12", hair=("long", "#161009"),
                                  outfit=dict(kind="team_kit", team="silver_arrow")),
    "karter_fifth_hand": dict(title="Club karter (fifth-hand kart)", model="classic", tone="brown", eyes="#2A1C12",
                              hair=("curly", "#1A120C"), outfit=dict(kind="race_suit", team="fifth_hand"),
                              helmet="fifth_hand"),
    "marshal": dict(title="Track marshal", model="classic", tone="dark", eyes="#2A1C12", hair=("buzz", "#111111"),
                    outfit=dict(kind="overalls", top="#FF6A13", legs="#FF6A13", shoes="#2B2B2E")),
}


# ---------------------------------------------------------------- colour helpers
def rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)


def shade(c, k):
    return np.clip(np.asarray(c, float) * k, 0, 255)


# ---------------------------------------------------------------- face regions of a cuboid
def regions(u, v, w, h, d):
    """Texture rectangles (u0, v0, width, height) of each face, Minecraft layout. Columns run as seen from outside."""
    return {"top": (u + d, v, w, d), "bottom": (u + d + w, v, w, d), "right": (u, v + d, d, h),
            "front": (u + d, v + d, w, h), "left": (u + d + w, v + d, d, h), "back": (u + 2 * d + w, v + d, w, h)}


class Skin:
    def __init__(self, seed):
        self.a = np.zeros((64, 64, 4), float)
        self.rng = np.random.default_rng(seed)

    def px(self, x, y, c, jitter=0.035):
        k = 1 + self.rng.normal(0, jitter)
        self.a[y, x, :3] = shade(c, k)
        self.a[y, x, 3] = 255

    def rect(self, x, y, w, h, c, jitter=0.035, fade=0.0):
        for j in range(h):
            for i in range(w):
                self.px(x + i, y + j, shade(c, 1 - fade * j / max(1, h - 1)), jitter)

    def cuboid(self, uv, dims, c, faces=None, rows=None, fade=0.05):
        """Fill faces of a cuboid. rows=(r0, r1) limits side faces to those rows (top..bottom)."""
        w, h, d = dims
        for f, (x, y, rw, rh) in regions(*uv, w, h, d).items():
            if faces and f not in faces:
                continue
            if f in ("top", "bottom"):
                if rows is None or (f == "top" and rows[0] == 0) or (f == "bottom" and rows[1] >= h):
                    self.rect(x, y, rw, rh, shade(c, 0.9 if f == "bottom" else 1.04))
                continue
            r0, r1 = rows or (0, h)
            for j in range(r0, min(r1, h)):
                self.rect(x, y + j, rw, 1, shade(c, 1 - fade * j / max(1, h - 1)))

    def face_px(self, uv, dims, face, col, row, c, jitter=0.035):
        x, y, _, _ = regions(*uv, *dims)[face]
        self.px(x + col, y + row, c, jitter)


def dims_of(part, model):
    x0, x1, y0, y1, z0, z1 = T.parts(model)[part]["box"]
    return (x1 - x0, z1 - z0, y1 - y0)


# ---------------------------------------------------------------- faces
def seed(*parts):
    return zlib.crc32("|".join(map(str, parts)).encode())


FRINGE = {  # front-face hair pixels per style: row -> columns
    "short": {0: range(8), 1: (0, 1, 6, 7)}, "swept": {0: range(8), 1: (0, 1, 2, 3, 4)},
    "curly": {0: range(8), 1: (0, 1, 2, 5, 6, 7), 2: (0, 7)}, "buzz": {0: range(8)},
    "long": {0: range(8), 1: (0, 1, 6, 7), **{r: (0, 7) for r in range(2, 8)}}, "bald": {},
}
FEATURES = [(2, 1), (2, 2), (2, 5), (2, 6), (3, 1), (3, 2), (3, 5), (3, 6), (4, 1), (4, 2), (4, 5), (4, 6),
            (5, 2), (5, 5), (6, 2), (6, 3), (6, 4), (6, 5), (7, 2), (7, 3), (7, 4), (7, 5)]


def paint_face(spec, expr, base=None):
    """8x8 front face for one expression (rows top->bottom, column 0 = the character's right).
    base: an existing 8x8 face (hand-painted skin) to redraw the features on."""
    rng = np.random.default_rng(seed(spec.get("title"), expr))
    tone = rgb(TONES.get(spec.get("tone", "medium"), spec.get("tone", "#C98E62")))
    hair_style, hair = (spec.get("hair") or ("bald", "#000000"))
    hc = rgb(hair)
    f = np.zeros((8, 8, 3))
    if base is not None:
        f[:] = base
        cheek = base[5, 1]
        for r, c in FEATURES:      # wipe the drawn features back to skin before redrawing them
            if r >= 5 or not spec.get("keep_brows"):
                f[r, c] = shade(cheek, 1 + rng.normal(0, 0.02))
        tone = cheek
    else:
        for r in range(8):
            for c in range(8):
                f[r, c] = shade(tone, 1 + rng.normal(0, 0.03))
        f[5, 3], f[5, 4] = shade(tone, 0.9), shade(tone, 0.92)   # nose shadow
        for r, cols in FRINGE[hair_style].items():
            for c in cols:
                f[r, c] = shade(hc, 1 + rng.normal(0, 0.05))
        if spec.get("beard"):
            bc = rgb(spec["beard"])
            for c in range(1, 7):
                f[7, c] = shade(bc, 1 + rng.normal(0, 0.05))
            for c in (1, 2, 5, 6):
                f[6, c] = shade(bc, 0.97)
    white, iris = np.array([245, 245, 242.]), rgb(spec.get("eyes", "#3B6EA8"))
    brow = shade(hc if hair_style != "bald" else rgb("#3A2A20"), 0.85)
    mouth = shade(np.asarray(tone) * np.array([1.0, 0.78, 0.74]), 0.62)
    dark = np.array([40, 22, 20.])
    teeth = np.array([236, 232, 224.])
    # eyes (row 4): white outside, iris inside; looking moves both irises
    eye = {"look_left": ((1, white), (2, iris), (5, white), (6, iris)),
           "look_right": ((1, iris), (2, white), (5, iris), (6, white))}.get(
        expr, ((1, white), (2, iris), (5, iris), (6, white)))
    if expr == "blink":
        for c in (1, 2, 5, 6):
            f[4, c] = shade(tone, 0.68)
    else:
        for c, col in eye:
            f[4, c] = col
        if expr == "surprised":
            for c in (1, 2, 5, 6):
                f[3, c] = white
    # brows (row 3; raised = row 2; angled = outer up, inner down, worried = inner up)
    br = {"angry": [(2, 1), (3, 2), (3, 5), (2, 6)], "shout": [(2, 1), (3, 2), (3, 5), (2, 6)],
          "worried": [(3, 1), (2, 2), (2, 5), (3, 6)], "surprised": [(2, 1), (2, 2), (2, 5), (2, 6)]}.get(
        expr, [(3, 1), (3, 2), (3, 5), (3, 6)])
    for r, c in br:
        f[r, c] = brow
    m = {"smile": [((6, 3), mouth), ((6, 4), mouth), ((5, 2), mouth), ((5, 5), mouth)],
         "grin": [((6, 2), dark), ((6, 3), teeth), ((6, 4), teeth), ((6, 5), dark), ((5, 2), mouth), ((5, 5), mouth)],
         "frown": [((6, 3), mouth), ((6, 4), mouth), ((7, 2), mouth), ((7, 5), mouth)],
         "angry": [((6, 2), mouth), ((6, 3), mouth), ((6, 4), mouth), ((6, 5), mouth)],
         "worried": [((6, 3), mouth), ((7, 2), mouth), ((6, 4), mouth), ((7, 5), mouth)],
         "surprised": [((6, 3), dark), ((6, 4), dark), ((7, 3), dark), ((7, 4), dark)],
         "shout": [((6, 2), dark), ((6, 3), teeth), ((6, 4), teeth), ((6, 5), dark), ((7, 3), dark), ((7, 4), dark)],
         }.get(expr, [((6, 3), mouth), ((6, 4), mouth)])
    for (r, c), col in m:
        f[r, c] = col
    return f


# ---------------------------------------------------------------- outfits
def paint_outfit(S, spec):
    model = spec.get("model", "classic")
    o = spec["outfit"]
    P = T.parts(model)
    D = {k: dims_of(k, model) for k in P}
    tone = rgb(TONES.get(spec.get("tone", "medium"), "#C98E62"))
    kind = o["kind"]
    team = TEAMS.get(o.get("team"), {})
    if kind == "race_suit":
        main, panel, acc = rgb(team["main"]), rgb(team["panel"]), rgb(team["accent"])
        glove, boot = rgb(team["glove"]), rgb(team["boot"])
        for k in ("body", "arm_R", "arm_L", "leg_R", "leg_L"):
            S.cuboid(P[k]["uv"], D[k], main)
        bw, bh, bd = D["body"]
        uv = P["body"]["uv"]
        for c in range(bw):                       # collar band, shoulders in panel colour
            S.face_px(uv, D["body"], "front", c, 0, panel)
            S.face_px(uv, D["body"], "back", c, 0, panel)
        for c in range(bd):
            S.face_px(uv, D["body"], "right", c, 0, panel)
            S.face_px(uv, D["body"], "left", c, 0, panel)
        S.face_px(uv, D["body"], "front", 3, 0, shade(main, 0.6))
        S.face_px(uv, D["body"], "front", 4, 0, shade(main, 0.6))
        for c in range(bw):                       # chest panel band + belt
            S.face_px(uv, D["body"], "front", c, 3, panel)
            S.face_px(uv, D["body"], "back", c, 3, panel)
            S.face_px(uv, D["body"], "front", c, 6, shade(main, 0.55))
            S.face_px(uv, D["body"], "back", c, 6, shade(main, 0.55))
        for c in range(bd):
            S.face_px(uv, D["body"], "right", c, 6, shade(main, 0.55))
            S.face_px(uv, D["body"], "left", c, 6, shade(main, 0.55))
        for r in range(1, 12):                    # side stripes
            S.face_px(uv, D["body"], "right", 1, r, acc)
            S.face_px(uv, D["body"], "left", 2, r, acc)
        S.face_px(uv, D["body"], "front", 1, 2, [240, 240, 238])     # badge patches (plain blocks, no logos)
        S.face_px(uv, D["body"], "front", 2, 2, [240, 240, 238])
        S.face_px(uv, D["body"], "front", 5, 2, acc)
        S.face_px(uv, D["body"], "front", 6, 2, acc)
        for c in range(2, 6):
            S.face_px(uv, D["body"], "front", c, 8, acc)
            S.face_px(uv, D["body"], "back", c, 1, [240, 240, 238])
        S.face_px(uv, D["body"], "front", 3, 4, shade(main, 0.75))    # zip
        S.face_px(uv, D["body"], "front", 4, 5, shade(main, 0.75))
        for k, outer in (("arm_R", "right"), ("arm_L", "left")):
            w, h, d = D[k]
            S.cuboid(P[k]["uv"], D[k], panel, rows=(0, 2))
            for r in range(2, 9):
                S.face_px(P[k]["uv"], D[k], outer, d // 2, r, acc)
            S.cuboid(P[k]["uv"], D[k], shade(main, 0.6), rows=(8, 9))
            S.cuboid(P[k]["uv"], D[k], glove, rows=(9, 12))
            S.cuboid(P[k]["uv"], D[k], shade(glove, 0.8), faces=("bottom",))
        for k, outer in (("leg_R", "right"), ("leg_L", "left")):
            for r in range(0, 9):
                S.face_px(P[k]["uv"], D[k], outer, 1, r, acc)
                S.face_px(P[k]["uv"], D[k], outer, 2, r, panel)
            S.cuboid(P[k]["uv"], D[k], boot, rows=(9, 12))
            S.cuboid(P[k]["uv"], D[k], shade(boot, 0.7), faces=("bottom",))
        # layer 2: raised collar, belt, glove cuffs, boot tops
        S.cuboid(P["body"]["uv2"], D["body"], panel, rows=(0, 1), faces=("front", "back", "right", "left"))
        for c in (3, 4):
            x, y, _, _ = regions(*P["body"]["uv2"], *D["body"])["front"]
            S.a[y, x + c, 3] = 0
        S.cuboid(P["body"]["uv2"], D["body"], shade(main, 0.5), rows=(6, 7), faces=("front", "back", "right", "left"))
        for k in ("arm_R", "arm_L"):
            S.cuboid(P[k]["uv2"], D[k], shade(glove, 0.9), rows=(9, 10), faces=("front", "back", "right", "left"))
        for k in ("leg_R", "leg_L"):
            S.cuboid(P[k]["uv2"], D[k], shade(boot, 1.15), rows=(9, 10), faces=("front", "back", "right", "left"))
    elif kind == "team_kit":
        main, panel, acc = rgb(team["main"]), rgb(team["panel"]), rgb(team["accent"])
        S.cuboid(P["body"]["uv"], D["body"], main)
        for k in ("arm_R", "arm_L"):
            S.cuboid(P[k]["uv"], D[k], tone, fade=0.0)
            S.cuboid(P[k]["uv"], D[k], main, rows=(0, 4))
            S.cuboid(P[k]["uv"], D[k], acc, rows=(4, 5))
            S.cuboid(P[k]["uv"], D[k], rgb("#202124"), rows=(9, 12))     # work gloves
        uv = P["body"]["uv"]
        for c in range(D["body"][0]):
            S.face_px(uv, D["body"], "front", c, 0, acc)
            S.face_px(uv, D["body"], "back", c, 0, acc)
            S.face_px(uv, D["body"], "front", c, 4, panel)
            S.face_px(uv, D["body"], "back", c, 4, panel)
        S.face_px(uv, D["body"], "front", 5, 2, [240, 240, 238])
        S.face_px(uv, D["body"], "front", 3, 1, shade(main, 0.7))
        S.face_px(uv, D["body"], "front", 4, 1, shade(main, 0.7))
        for k in ("leg_R", "leg_L"):
            S.cuboid(P[k]["uv"], D[k], rgb("#2A2B30"))
            S.cuboid(P[k]["uv"], D[k], rgb("#151516"), rows=(10, 12))
            S.cuboid(P[k]["uv"], D[k], acc, rows=(5, 6), faces=("front",))
        S.cuboid(P["body"]["uv"], D["body"], shade(rgb("#2A2B30"), 1.0), rows=(10, 12))
        S.cuboid(P["body"]["uv2"], D["body"], acc, rows=(0, 1), faces=("front", "back", "right", "left"))
        for c in (3, 4):
            x, y, _, _ = regions(*P["body"]["uv2"], *D["body"])["front"]
            S.a[y, x + c, 3] = 0
    elif kind in ("tee", "overalls"):
        top, legs, shoes = rgb(o["top"]), rgb(o["legs"]), rgb(o["shoes"])
        S.cuboid(P["body"]["uv"], D["body"], top)
        for k in ("arm_R", "arm_L"):
            S.cuboid(P[k]["uv"], D[k], tone, fade=0.0)
            S.cuboid(P[k]["uv"], D[k], top, rows=(0, 4 if kind == "tee" else 12))
            if kind == "overalls":
                S.cuboid(P[k]["uv"], D[k], rgb("#3A3A3C"), rows=(9, 12))
        for k in ("leg_R", "leg_L"):
            S.cuboid(P[k]["uv"], D[k], legs)
            S.cuboid(P[k]["uv"], D[k], shoes, rows=(10, 12))
            S.cuboid(P[k]["uv"], D[k], shade(shoes, 0.7), faces=("bottom",))
        uv = P["body"]["uv"]
        if kind == "tee":
            S.face_px(uv, D["body"], "front", 3, 0, tone)
            S.face_px(uv, D["body"], "front", 4, 0, tone)
            for c in range(D["body"][0]):
                S.face_px(uv, D["body"], "front", c, 10, legs)
                S.face_px(uv, D["body"], "front", c, 11, legs)
                S.face_px(uv, D["body"], "back", c, 10, legs)
                S.face_px(uv, D["body"], "back", c, 11, legs)
            for c in range(D["body"][2]):
                for r in (10, 11):
                    S.face_px(uv, D["body"], "right", c, r, legs)
                    S.face_px(uv, D["body"], "left", c, r, legs)
            S.face_px(uv, D["body"], "front", 2, 10, shade(legs, 0.6))      # belt buckle line
            for k in ("leg_R", "leg_L"):                                   # jeans seams + turn-ups
                S.cuboid(P[k]["uv"], D[k], shade(legs, 0.85), rows=(9, 10))
        else:  # hi-vis overalls with reflective bands
            refl = rgb("#C9CDD2")
            for k in ("body",):
                S.cuboid(P[k]["uv"], D[k], refl, rows=(7, 8), faces=("front", "back", "right", "left"))
                S.cuboid(P[k]["uv"], D[k], refl, rows=(2, 3), faces=("front", "back", "right", "left"))
            for k in ("arm_R", "arm_L"):
                S.cuboid(P[k]["uv"], D[k], refl, rows=(6, 7))
            for k in ("leg_R", "leg_L"):
                S.cuboid(P[k]["uv"], D[k], refl, rows=(6, 7))
            for c in range(D["body"][0]):
                S.face_px(uv, D["body"], "back", c, 4, rgb("#FAFAFA"))
            S.face_px(uv, D["body"], "front", 3, 0, tone)
            S.face_px(uv, D["body"], "front", 4, 0, tone)
            S.cuboid(P["body"]["uv2"], D["body"], top, rows=(0, 1), faces=("front", "back", "right", "left"))
            for c in (3, 4):
                x, y, _, _ = regions(*P["body"]["uv2"], *D["body"])["front"]
                S.a[y, x + c, 3] = 0


def paint_head(S, spec):
    model = spec.get("model", "classic")
    P = T.parts(model)
    hd = dims_of("head", model)
    tone = rgb(TONES.get(spec.get("tone", "medium"), "#C98E62"))
    S.cuboid(P["head"]["uv"], hd, tone, fade=0.0)
    style, hair = spec.get("hair") or ("bald", "#000")
    hc = rgb(hair)
    uv, uv2 = P["head"]["uv"], P["head"]["uv2"]
    if style != "bald":
        S.cuboid(uv, hd, hc, faces=("top",))
        side_rows = {"short": 3, "swept": 3, "curly": 4, "buzz": 2, "long": 8}[style]
        back_rows = {"short": 6, "swept": 6, "curly": 6, "buzz": 4, "long": 8}[style]
        for face, n in (("right", side_rows), ("left", side_rows), ("back", back_rows)):
            S.cuboid(uv, hd, hc, faces=(face,), rows=(0, n), fade=0.08)
        for face in ("right", "left"):  # sideburn / ear shadow
            col = 2 if face == "right" else 5
            S.face_px(uv, hd, face, col, side_rows if style != "long" else 4, shade(tone, 0.85))
        # layer 2 hair volume (raised): top + upper sides/back, fringe edge on the front
        top2 = {"short": 2, "swept": 2, "curly": 3, "buzz": 0, "long": 2}[style]
        if style != "buzz":
            S.cuboid(uv2, hd, shade(hc, 1.08), faces=("top",))
            for face, n in (("right", top2), ("left", top2), ("back", top2 + (5 if style == "long" else 1))):
                S.cuboid(uv2, hd, shade(hc, 1.05), faces=(face,), rows=(0, n), fade=0.1)
            front2 = {"short": [1], "swept": [1], "curly": [1, 1], "long": [1]}[style]
            fx, fy, _, _ = regions(*uv2, *hd)["front"]
            for r, _ in enumerate(front2):
                for c in range(8):
                    if style == "swept" and c > 5:
                        continue
                    S.px(fx + c, fy + r, shade(hc, 1.06))
            if style == "curly":  # break up the curls
                for _ in range(26):
                    f = ["top", "right", "left", "back"][S.rng.integers(4)]
                    x, y, w, h = regions(*uv2, *hd)[f]
                    i, j = S.rng.integers(w), S.rng.integers(min(h, 3))
                    if S.a[y + j, x + i, 3]:
                        S.a[y + j, x + i, :3] = shade(hc, 0.8)
    face = paint_face(spec, "neutral")
    x, y, _, _ = regions(*uv, *hd)["front"]
    S.a[y:y + 8, x:x + 8, :3] = face
    S.a[y:y + 8, x:x + 8, 3] = 255


def paint_skin(name, spec):
    S = Skin(seed(name))
    paint_head(S, spec)
    paint_outfit(S, spec)
    return S.a.astype(np.uint8)


def face_atlas(spec, skin=None):
    """N x (8x8) faces side by side, in template.EXPRESSIONS order."""
    base = None
    if spec.get("png") and skin is not None:
        base = skin[8:16, 8:16, :3].astype(float)
    tiles = [base if (base is not None and e == "neutral") else paint_face(spec, e, base) for e in T.EXPRESSIONS]
    a = np.concatenate(tiles, axis=1)
    return np.dstack([a, np.full(a.shape[:2], 255.0)]).astype(np.uint8)


def paint_helmet(team):
    main, stripe, trim = (rgb(c) for c in TEAMS[team]["helmet"])
    S = Skin(seed("helmet", team))
    uv = (32, 0)
    hd = (8, 8, 8)
    S.cuboid(uv, hd, main, fade=0.06)
    R = regions(*uv, *hd)
    x, y, w, h = R["top"]
    for j in range(h):
        S.px(x + 3, y + j, stripe)
        S.px(x + 4, y + j, stripe)
        S.px(x + 1, y + j, trim)
        S.px(x + 6, y + j, trim)
    x, y, w, h = R["bottom"]
    S.rect(x, y, w, h, [30, 30, 32])
    visor = rgb("#14171B")
    x, y, w, h = R["front"]
    for c in range(1, 7):
        S.px(x + c, y + 3, visor, 0.01)
        S.px(x + c, y + 4, visor, 0.01)
    S.px(x + 5, y + 3, [92, 108, 128], 0.01)        # glint
    S.px(x + 6, y + 3, [60, 70, 84], 0.01)
    for c in range(8):
        S.px(x + c, y + 2, stripe)
    for c in range(8):                               # trim band round the chin, chin bar edge
        S.px(x + c, y + 6, trim)
        S.px(x + c, y + 7, shade(main, 0.78))
    for f in ("right", "left"):
        x, y, w, h = R[f]
        for c in range(w):
            S.px(x + c, y + 2, stripe)
            S.px(x + c, y + 6, trim)
        vc = (w - 3) if f == "right" else 0          # visor wraps round the front corners
        for c in range(vc, vc + 3):
            S.px(x + c, y + 3, visor, 0.01)
            S.px(x + c, y + 4, visor, 0.01)
    x, y, w, h = R["back"]
    for c in range(w):
        S.px(x + c, y + 2, stripe)
        S.px(x + c, y + 6, trim)
    S.px(x + 3, y + 3, trim)
    S.px(x + 4, y + 3, trim)
    return S.a.astype(np.uint8)


def main():
    from PIL import Image
    os.makedirs(os.path.join(HERE, "skins"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "helmets"), exist_ok=True)
    for name, spec in SKINS.items():
        p = os.path.join(HERE, "skins", name + ".png")
        if spec.get("png"):
            skin = np.array(Image.open(p).convert("RGBA"))
        else:
            skin = paint_skin(name, spec)
            Image.fromarray(skin, "RGBA").save(p)
        Image.fromarray(face_atlas(spec, skin), "RGBA").save(os.path.join(HERE, "skins", name + "_faces.png"))
        print("skin", name)
    for team in TEAMS:
        Image.fromarray(paint_helmet(team), "RGBA").save(os.path.join(HERE, "helmets", team + ".png"))
        print("helmet", team)


if __name__ == "__main__":
    main()
