"""2D textures for the Blender props: the autograph page (writing appears word by word), clock faces, the chequered
flag, the contract and bills. Run: .venv-tools/Scripts/python videos/hamilton-autograph/tools/make_tex.py"""
import math, os, random
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "tex")
os.makedirs(OUT, exist_ok=True)
INK = (28, 48, 150)
PAPER = (246, 238, 214)
HAND = "C:/Windows/Fonts/segoeprb.ttf"


def paper(w, h, seed=1, col=PAPER):
    im = Image.new("RGB", (w, h), col)
    d = ImageDraw.Draw(im)
    rnd = random.Random(seed)
    for _ in range(w * h // 60):  # paper grain
        x, y = rnd.randrange(w), rnd.randrange(h)
        v = rnd.randint(-10, 4)
        d.point((x, y), tuple(max(0, min(255, c + v)) for c in col))
    return im, d


def signature(d, x0, y0, w, seed=3, upto=1.0):
    """A made-up scribble (not anyone's real signature): a looping pen line drawn up to `upto` of its length."""
    rnd = random.Random(seed)
    pts, x, y = [], x0, y0
    n = 140
    for i in range(n):
        t = i / n
        x = x0 + t * w + 26 * math.sin(t * 31) * (1 - t * 0.4)
        y = y0 + 34 * math.sin(t * 19 + 1.3) * math.exp(-t * 1.2) + 10 * math.sin(t * 57)
        pts.append((x, y))
    pts = pts[: max(2, int(len(pts) * upto))]
    d.line(pts, fill=INK, width=7, joint="curve")
    if upto >= 1.0:
        d.line([(x0 - 10, y0 + 58), (x0 + w * 0.95, y0 + 46)], fill=INK, width=6)  # underline flourish


def autograph_pages():
    f1 = ImageFont.truetype(HAND, 118)
    words = ["Phone", "me", "in", "9", "years"]
    for k in range(len(words) + 2):
        im, d = paper(1024, 768, 2)
        shown = words[:min(k, len(words))]
        line1 = " ".join(shown[:3])
        line2 = " ".join(shown[3:])
        d.text((90, 140), line1, font=f1, fill=INK)
        d.text((260, 330), line2, font=f1, fill=INK)
        if k == len(words) + 1:
            signature(d, 520, 600, 380)
        im.rotate(-2.0, resample=Image.BICUBIC, fillcolor=PAPER).save(os.path.join(OUT, f"page_{k}.png"))


def clock(hh, name):
    S = 256
    im = Image.new("RGB", (S, S), (40, 40, 42))
    d = ImageDraw.Draw(im)
    d.ellipse((8, 8, S - 8, S - 8), fill=(236, 234, 226), outline=(20, 20, 20), width=10)
    for i in range(12):
        a = i / 12 * 2 * math.pi
        r0, r1 = (S / 2 - 30, S / 2 - 16)
        d.line([(S / 2 + r0 * math.sin(a), S / 2 - r0 * math.cos(a)), (S / 2 + r1 * math.sin(a), S / 2 - r1 * math.cos(a))],
               fill=(20, 20, 20), width=8 if i % 3 == 0 else 4)
    ah = (hh % 12) / 12 * 2 * math.pi
    d.line([(S / 2, S / 2), (S / 2 + 62 * math.sin(ah), S / 2 - 62 * math.cos(ah))], fill=(15, 15, 15), width=14)
    d.line([(S / 2, S / 2), (S / 2, S / 2 - 96)], fill=(15, 15, 15), width=8)  # minute hand on 12
    d.ellipse((S / 2 - 12, S / 2 - 12, S / 2 + 12, S / 2 + 12), fill=(170, 20, 20))
    im.save(os.path.join(OUT, f"clock_{name}.png"))


def chequer():
    S, n = 256, 6
    im = Image.new("RGB", (S, S), (240, 240, 240))
    d = ImageDraw.Draw(im)
    c = S / n
    for i in range(n):
        for j in range(n):
            if (i + j) % 2:
                d.rectangle((i * c, j * c, (i + 1) * c, (j + 1) * c), fill=(14, 14, 14))
    im.save(os.path.join(OUT, "chequer.png"))


def contract(signed):
    im, d = paper(512, 720, 5, (244, 244, 240))
    rnd = random.Random(8)
    d.rectangle((60, 60, 300, 84), fill=(40, 40, 40))  # heading bar, no words
    for i in range(18):  # lines of print
        y = 130 + i * 26
        d.rectangle((60, y, 60 + rnd.randint(300, 390), y + 9), fill=(120, 120, 120))
    for x in (60, 290):
        d.line([(x, 640), (x + 170, 640)], fill=(40, 40, 40), width=3)
    if signed:
        signature(d, 300, 600, 150, seed=9)
        signature(d, 70, 605, 150, seed=4)
    im.save(os.path.join(OUT, f"contract_{int(signed)}.png"))


def bill(i):
    im, d = paper(256, 340, 10 + i, (240, 240, 236))
    d.rectangle((24, 24, 150, 44), fill=(60, 60, 60))
    for k in range(7):
        d.rectangle((24, 80 + k * 24, 24 + 150 + (k * 37) % 60, 88 + k * 24), fill=(140, 140, 140))
    d.rectangle((24, 270, 232, 312), outline=(190, 20, 20), width=6)  # red box: amount due
    d.rectangle((40, 284, 140, 298), fill=(190, 20, 20))
    im.save(os.path.join(OUT, f"bill_{i}.png"))


autograph_pages()
for hh, n in ((9, "0900"), (18, "1800"), (23, "2300")):
    clock(hh, n)
chequer()
contract(False); contract(True)
for i in range(3):
    bill(i)
print(sorted(os.listdir(OUT)))
