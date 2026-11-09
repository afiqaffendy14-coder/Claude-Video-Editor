"""The estate agent's board for shot 7b: FOR SALE in big red letters on white (no agency name).
Run: ../../.venv-tools/Scripts/python tools/make_forsale.py"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 800, 520
im = Image.new("RGB", (W, H), (244, 244, 240))
d = ImageDraw.Draw(im)
d.rectangle((0, 0, W - 1, 70), fill=(200, 20, 30))
d.rectangle((0, H - 70, W - 1, H - 1), fill=(200, 20, 30))
font = ImageFont.truetype(os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts", "arialbd.ttf"), 170)
for i, word in enumerate(("FOR", "SALE")):
    tw = d.textlength(word, font=font)
    d.text(((W - tw) / 2, 80 + i * 175), word, font=font, fill=(200, 20, 30))
im.save(os.path.join(ROOT, "assets", "tex", "forsale.png"))
print("ok")
