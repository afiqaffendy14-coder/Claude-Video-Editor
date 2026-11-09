"""Shot 1's title box in a Minecraft look: a dark tooltip panel with a gold pixel border and cut corners, the
words in a 5x7 pixel font with the game's hard drop shadow. "F1 boss" in gold. Overwrites the title.png that
tools/captions.mjs writes (same 1080x1920 transparent frame, shown 0-3.51 s).

Run after captions.mjs:  .venv-tools/Scripts/python tools/title_mc.py assets/captions_1080
"""
import os
import sys
from PIL import Image, ImageDraw

LINES = [[("A 10-year-old Black boy", "w")], [("asked a ", "w"), ("F1 boss", "g")], [("for a job.", "w")]]
TOP = 0.235       # the box's top edge, as a share of the frame height: lower, toward the middle, clear of the heads
U = 7              # one font pixel, in screen pixels
COL = {"w": ((255, 255, 255), (63, 63, 63)), "g": ((255, 170, 0), (63, 42, 0))}  # text, shadow

G = {  # 8 rows: 0-6 the body, 7 descenders
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#", "....."],
    "B": ["####.", "#...#", "####.", "#...#", "#...#", "#...#", "####.", "....."],
    "F": ["#####", "#....", "###..", "#....", "#....", "#....", "#....", "....."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", "#####", "....."],
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###.", "....."],
    "-": [".....", ".....", ".....", "#####", ".....", ".....", ".....", "....."],
    "a": [".....", ".....", ".###.", "....#", ".####", "#...#", ".####", "....."],
    "b": ["#....", "#....", "#.##.", "##..#", "#...#", "#...#", "####.", "....."],
    "c": [".....", ".....", ".###.", "#...#", "#....", "#...#", ".###.", "....."],
    "d": ["....#", "....#", ".##.#", "#..##", "#...#", "#...#", ".####", "....."],
    "e": [".....", ".....", ".###.", "#...#", "#####", "#....", ".####", "....."],
    "f": ["..##", ".#..", "####", ".#..", ".#..", ".#..", ".#..", "...."],
    "j": ["....#", ".....", "....#", "....#", "....#", "....#", "#...#", ".###."],
    "k": ["#...", "#...", "#..#", "#.#.", "##..", "#.#.", "#..#", "...."],
    "l": ["#.", "#.", "#.", "#.", "#.", "#.", ".#", ".."],
    "n": [".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#", "....."],
    "o": [".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###.", "....."],
    "r": [".....", ".....", "#.##.", "##..#", "#....", "#....", "#....", "....."],
    "s": [".....", ".....", ".####", "#....", ".###.", "....#", "####.", "....."],
    "y": [".....", ".....", "#...#", "#...#", "#...#", ".####", "....#", "####."],
    ".": ["#", "#", "#", "#", "#", "#", "#", "#"],
    " ": ["...", "...", "...", "...", "...", "...", "...", "..."],
}
G["."] = ["."] * 6 + ["#", "."]


def width(text):
    return sum(len(G[c][0]) + 1 for c in text) - 1


def draw_text(d, x0, y0, text, col):
    x = x0
    for c in text:
        g = G[c]
        for ry, row in enumerate(g):
            for rx, ch in enumerate(row):
                if ch == "#":
                    for (ox, oy), cc in (((1, 1), col[1]), ((0, 0), col[0])):  # shadow first, then the letter
                        px, py = x + (rx + ox) * U, y0 + (ry + oy) * U
                        d.rectangle((px, py, px + U - 1, py + U - 1), fill=cc)
        x += (len(g[0]) + 1) * U
    return x


def main(out_dir):
    W, H = 1080, 1920
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lw = [sum(width(t) for t, _ in line) for line in LINES]
    pad_x, pad_y, lh = 6, 5, 11                     # in font pixels: padding, line height
    bw = (max(lw) + 2 * pad_x) * U
    bh = (len(LINES) * lh - 2 + 2 * pad_y) * U
    x0, y0 = (W - bw) // 2, int(H * TOP)
    # the tooltip panel: dark purple-black, its corner pixels cut, a 1-pixel purple border inset by 1 pixel
    bg = (16, 0, 16, 240)
    d.rectangle((x0 + U, y0, x0 + bw - U - 1, y0 + bh - 1), fill=bg)
    d.rectangle((x0, y0 + U, x0 + bw - 1, y0 + bh - U - 1), fill=bg)
    top, bot = (255, 214, 64), (196, 128, 0)   # a gold border (bright at the top, darker at the bottom)
    for i in range(bh // U - 2):  # the border fades from bright purple at the top to dark at the bottom
        f = i / max(1, bh // U - 3)
        c = tuple(int(top[j] + (bot[j] - top[j]) * f) for j in range(3)) + (255,)
        y = y0 + (i + 1) * U
        d.rectangle((x0 + U, y, x0 + 2 * U - 1, y + U - 1), fill=c)
        d.rectangle((x0 + bw - 2 * U, y, x0 + bw - U - 1, y + U - 1), fill=c)
    d.rectangle((x0 + U, y0 + U, x0 + bw - U - 1, y0 + 2 * U - 1), fill=top + (255,))
    d.rectangle((x0 + U, y0 + bh - 2 * U, x0 + bw - U - 1, y0 + bh - U - 1), fill=bot + (255,))
    for i, line in enumerate(LINES):
        x = x0 + (bw - lw[i] * U) // 2
        y = y0 + (pad_y + i * lh) * U
        for text, c in line:
            x = draw_text(d, x, y, text, COL[c]) + U
    im.save(os.path.join(out_dir, "title.png"))
    print("title", x0, y0, bw, bh, f"bottom at {100 * (y0 + bh) / H:.1f}%")


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]))
