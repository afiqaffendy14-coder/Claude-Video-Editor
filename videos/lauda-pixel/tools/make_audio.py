"""Synthesise the Lauda pixel short's music and sound into assets/audio/, timed from tools/cues.json.

Four full-length stems, all chiptune-flavoured and seeded (re-running gives identical files):
  music.wav       NES-style bed: triangle bass, pulse arpeggios, scored to each scene
  rain.wav        soft rain, muffled behind glass in the hospital, open but gentle at Fuji
  sfx-game.wav    heart-monitor beeps, coin blips, power-up, menu blips, fanfare, falling notes, whooshes
  sfx-world.wav   8-bit engines, skid, explosion, fire crackle, footsteps, helmet thud

Run from the project folder:  ../../.venv-audio/bin/python tools/make_audio.py
"""
import json
import math
import os

import numpy as np
import soundfile as sf
from scipy.signal import butter, lfilter, sosfilt

SR = 48000
HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..", "assets", "audio")
C = json.load(open(os.path.join(HERE, "cues.json")))
DUR = C["duration"]
N = int(DUR * SR)
rng = np.random.default_rng(1976)
SC = {s["id"]: s for s in C["scenes"]}


def secs(n):
    return np.arange(n) / SR


def note(name):
    names = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3, "G": -2, "G#": -1, "A": 0, "A#": 1, "Bb": 1, "B": 2}
    pitch, octave = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((names[pitch] + (octave - 4) * 12) / 12)


def pulse(f, n, duty=0.5):
    ph = np.cumsum(np.broadcast_to(f, (n,)) / SR) % 1
    return np.where(ph < duty, 1.0, -1.0)


def tri(f, n):
    ph = np.cumsum(np.broadcast_to(f, (n,)) / SR) % 1
    t = 4 * np.abs(ph - 0.5) - 1
    return np.round(t * 8) / 8  # 16-step NES triangle


def chipnoise(n, rate=8000):
    hold = max(1, int(SR / rate))
    v = rng.uniform(-1, 1, n // hold + 2)
    return np.repeat(v, hold)[:n]


def adsr(n, a=0.005, d=0.05, s=0.6, r=0.05):
    e = np.ones(n) * s
    A, D, R = int(a * SR), int(d * SR), int(r * SR)
    if A: e[:A] = np.linspace(0, 1, A)
    if D: e[A:A + D] = np.linspace(1, s, len(e[A:A + D]))
    if R and n > R: e[-R:] *= np.linspace(1, 0, R)
    return e


def lp(x, f, order=2):
    return sosfilt(butter(order, f / (SR / 2), "low", output="sos"), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f / (SR / 2), "high", output="sos"), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo / (SR / 2), hi / (SR / 2)], "band", output="sos"), x)


def place(track, start, sig, gain=1.0):
    i = int(start * SR)
    if i >= len(track) or i + len(sig) <= 0: return
    j = min(len(track), i + len(sig))
    k0 = max(0, -i)
    track[max(0, i):j] += sig[k0:k0 + (j - max(0, i))] * gain


def write(name, l, r=None, peak_db=-1.5):
    st = np.stack([l, l if r is None else r], axis=1)
    st = st / (np.max(np.abs(st)) + 1e-9) * (10 ** (peak_db / 20))
    sf.write(os.path.join(OUT, name), st.astype(np.float32), SR, subtype="PCM_16")
    print("wrote", name, f"{len(l) / SR:.2f}s")


os.makedirs(OUT, exist_ok=True)

# ------------------------------------------------------------------ music
BEAT = 60 / 84
music = np.zeros(N)


def tone(start, dur, f, wave="pulse", vol=0.3, duty=0.25, env=(0.005, 0.06, 0.55, 0.06)):
    n = int(dur * SR)
    if n <= 0: return
    sig = tri(f, n) if wave == "tri" else pulse(f, n, duty)
    place(music, start, sig * adsr(n, *env) * vol)


def arp(start, end, chord, step=BEAT / 2, vol=0.16, duty=0.25, octave_up=False):
    t, i = start, 0
    seq = chord + chord[-2:0:-1]
    while t < end - 0.01:
        f = note(seq[i % len(seq)]) * (2 if octave_up else 1)
        tone(t, min(step * 0.9, end - t), f, vol=vol, duty=duty)
        t += step; i += 1


def bass(start, end, root, step=BEAT, vol=0.42):
    t = start
    while t < end - 0.01:
        tone(t, min(step * 0.95, end - t), note(root), wave="tri", vol=vol, env=(0.003, 0.05, 0.8, 0.03))
        t += step


def pad(start, end, chord, vol=0.05):
    for nm in chord:
        tone(start, end - start, note(nm), vol=vol, duty=0.125, env=(0.6, 0.2, 0.8, 0.5))


s = SC
# hook: low and still
bass(0.2, s["hook"]["end"], "D2", step=BEAT * 2, vol=0.35); pad(0.2, s["hook"]["end"], ["D3", "F3", "A3"])
# comeback: still, then it lifts into F major as he races again
cut = C["gridIdle"][0]
bass(s["comeback"]["start"], cut, "D2", step=BEAT * 2, vol=0.3); pad(s["comeback"]["start"], cut, ["D3", "F3", "A3"])
bass(cut, s["loop"]["start"] + 0.5, "F2", step=BEAT / 2); arp(cut, s["loop"]["start"] + 0.5, ["F4", "A4", "C5"], vol=0.15)
# loop: the music drops out to a single low note
tone(C["musicDrop"][0], s["ring"]["start"] - C["musicDrop"][0], note("D1") * 2, wave="tri", vol=0.3, env=(0.01, 0.3, 0.5, 0.8))
# ring: tense minor pulse
bass(s["ring"]["start"], s["crash"]["start"], "D2", step=BEAT / 2, vol=0.36)
arp(s["ring"]["start"], s["crash"]["start"], ["D4", "F4", "A4"], vol=0.12)
# crash: keeps driving until the impact, then silence and a low drone
bass(s["crash"]["start"], C["impact"], "D2", step=BEAT / 4, vol=0.36)
arp(s["crash"]["start"], C["impact"], ["D4", "F4", "A4", "C5"], step=BEAT / 4, vol=0.1)
tone(C["impact"] + 0.6, s["crash"]["end"] - C["impact"] - 0.6, note("A1") * 2, wave="tri", vol=0.28, env=(0.4, 0.2, 0.7, 0.4))
# hospital: sparse descending notes
for k, nm in enumerate(["D3", "C3", "Bb2", "A2"]):
    tone(s["hospital"]["start"] + k * BEAT * 2, BEAT * 1.9, note(nm), wave="tri", vol=0.32, env=(0.01, 0.2, 0.6, 0.3))
pad(s["hospital"]["start"], s["hospital"]["end"], ["D3", "F3", "A3"], vol=0.035)
# Monza: hope — Bb, F, C, Dm arpeggios
m0, m1 = s["monza"]["start"], s["monza"]["end"]
for k, (root, ch) in enumerate([("Bb2", ["Bb3", "D4", "F4"]), ("F2", ["F3", "A3", "C4"]), ("C3", ["C4", "E4", "G4"]), ("D2", ["D4", "F4", "A4"])]):
    a = m0 + k * (m1 - m0) / 4; b = m0 + (k + 1) * (m1 - m0) / 4
    bass(a, b, root, step=BEAT / 2, vol=0.34); arp(a, b, ch, vol=0.13)
# Fuji and the pits: tense Dm–Bb–Gm–A cycle, stops for the falling notes
f0, f1 = s["fuji"]["start"], C["sad"] - 0.1
prog = [("D2", ["D4", "F4", "A4"]), ("Bb1", ["Bb3", "D4", "F4"]), ("G1", ["G3", "Bb3", "D4"]), ("A1", ["A3", "C#4", "E4"])]
t, k = f0, 0
while t < f1:
    root, ch = prog[k % 4]
    e = min(f1, t + BEAT * 4)
    bass(t, e, root, step=BEAT / 2, vol=0.34); arp(t, e, ch, vol=0.1)
    t, k = e, k + 1
# end: slow chords resolving to D minor, fading out
e0, e1 = s["end"]["start"], DUR
for k, ch in enumerate([["D3", "F3", "A3"], ["Bb2", "D3", "F3"], ["F3", "A3", "C4"], ["A2", "D3", "E3"], ["D3", "F3", "A3"]]):
    a = e0 + k * (e1 - e0) / 5
    pad(a, a + (e1 - e0) / 5 + 0.3, ch, vol=0.06)
    tone(a, (e1 - e0) / 5, note(ch[0]) / 2, wave="tri", vol=0.3, env=(0.05, 0.3, 0.6, 0.4))
music *= np.interp(secs(N), [0, 0.4, DUR - 1.6, DUR], [0, 1, 1, 0])
write("music.wav", music, np.roll(music, 200), peak_db=-3)

# ------------------------------------------------------------------ rain (soft, steady, never harsh)
brown = np.cumsum(rng.standard_normal(N)); brown = hp(brown, 60) ; brown /= np.max(np.abs(brown))
glass = lp(brown, 650, 3)
open_ = lp(brown, 1800, 3) + lp(hp(rng.standard_normal(N), 900), 2600) * 0.08
t = secs(N)
g_env = np.zeros(N); o_env = np.zeros(N)
for a, b, kind in C["rain"]:
    e = np.interp(t, [a - 0.3, a + 0.4, b - 0.3, b + 0.2], [0, 1, 1, 0])
    if kind == "glass": g_env = np.maximum(g_env, e)
    else: o_env = np.maximum(o_env, e)
o_env *= np.interp(t, [C["rainHeavy"] - 0.2, C["rainHeavy"] + 0.6], [0.8, 1.0])
o_env *= np.interp(t, [C["finalShot"] - 0.4, C["finalShot"]], [1.0, 0.7])
rain = glass * g_env * 0.7 + open_ * o_env
write("rain.wav", rain, np.roll(rain, 410), peak_db=-6)

# ------------------------------------------------------------------ video-game sfx
game = np.zeros(N)


def blip(f, dur, duty=0.5, vol=1.0):
    n = int(dur * SR)
    return pulse(f, n, duty) * adsr(n, 0.002, 0.02, 0.7, 0.02) * vol


for at, alarm in C["beeps"]:
    place(game, at, blip(988, 0.09, 0.5, 0.55))
    if alarm: place(game, at + 0.12, blip(1175, 0.06, 0.5, 0.35))
for at in C["coins"]:
    place(game, at, np.concatenate([blip(988, 0.035, 0.5, 0.35), blip(1319, 0.06, 0.5, 0.35)]))
place(game, C["powerUp"], np.concatenate([blip(note(n), 0.055, 0.25, 0.6) for n in ["C5", "E5", "G5", "C6", "E6", "G6"]] + [blip(note("C7"), 0.16, 0.25, 0.5)]))
for at in C["whoosh"]:
    n = int(0.24 * SR)
    sw = bp(chipnoise(n, 12000), 500, 4000) * np.sin(np.linspace(0, math.pi, n)) ** 2
    place(game, at - 0.12, sw * 0.5)
place(game, C["scorePop"], np.concatenate([blip(784, 0.05, 0.25, 0.5), blip(1047, 0.09, 0.25, 0.5)]))
place(game, C["scoreFlip"], np.concatenate([blip(1047, 0.05, 0.25, 0.5), blip(784, 0.05, 0.25, 0.5), blip(1047, 0.1, 0.25, 0.5)]))
place(game, C["fanfare"], np.concatenate([blip(note("G5"), 0.11, 0.25, 0.55), blip(note("B5"), 0.11, 0.25, 0.55), blip(note("D6"), 0.32, 0.25, 0.55)]))
for k, nm in enumerate(["E4", "C4", "A3"]):  # falling three-note phrase on "By one point"
    n = int(0.32 * SR)
    place(game, C["sad"] + k * 0.3, tri(note(nm), n) * adsr(n, 0.005, 0.1, 0.7, 0.12) * 0.9)
for k in range(4):  # the heart monitor, one last time, echoing away
    place(game, C["endBeep"] + k * 0.28, blip(988, 0.09, 0.5, 0.5 * 0.45 ** k))
write("sfx-game.wav", game, np.roll(game, 120), peak_db=-2)

# ------------------------------------------------------------------ world sfx (8-bit engines etc.)
world_l = np.zeros(N); world_r = np.zeros(N)


def engine(f, n, duty=0.3):
    vib = 1 + 0.015 * np.sin(2 * math.pi * 23 * secs(n))
    return lp(pulse(np.asarray(f) * vib, n, duty) + 0.3 * pulse(np.asarray(f) * 2.01 * vib, n, 0.5), 3500)


def put(start, sig, pan=0.0, gain=1.0):
    pan = np.broadcast_to(np.asarray(pan, dtype=float), sig.shape)
    a = (pan + 1) * math.pi / 4
    place(world_l, start, sig * np.cos(a), gain)
    place(world_r, start, sig * np.sin(a), gain)


def pass_by(start, dur, f0, peak, pan_from=0.8, pan_to=-0.8, gain=0.8):
    n = int(dur * SR); tt = secs(n)
    s_ = (tt - peak) / 0.3
    f = f0 * (1 - 0.12 * np.tanh(s_))
    amp = 1 / (1 + s_ * s_)
    spray = bp(chipnoise(n, 9000), 1500, 6000) * 0.4
    put(start, (engine(f, n) + spray) * amp, np.interp(tt, [0, dur], [pan_from, pan_to]), gain)


# grid idle at Monza, then the launch
a, b = C["gridIdle"]
n = int((b - a) * SR); put(a, engine(np.full(n, 55.0), n) * np.interp(secs(n), [0, 0.1, b - a], [0, 1, 1]) * 0.5)
n = int(1.4 * SR); tt = secs(n)
put(C["launch"], engine(60 + 170 * (1 - np.exp(-tt * 2.5)), n) * np.interp(tt, [0, 0.1, 0.8, 1.4], [0.5, 1, 0.6, 0]), np.interp(tt, [0, 1.4], [0, -0.9]))
# the Ring: a distant engine echoing through the hills
a, b = C["ring"]; n = int((b - a) * SR); tt = secs(n)
put(a, lp(engine(150 + 30 * np.sin(tt * 1.3), n), 900) * 0.22 * np.interp(tt, [0, 0.4, b - a - 0.3, b - a], [0, 1, 1, 0]))
# crash: approach, skid, explosion, fire, the other car, running feet
a, b = C["crashApproach"]; n = int((b - a) * SR); tt = secs(n)
put(a, engine(160 + 70 * tt / (b - a), n) * np.interp(tt, [0, b - a], [0.4, 1]), np.interp(tt, [0, b - a], [0.8, -0.2]))
n = int(0.55 * SR); put(C["skid"], hp(chipnoise(n, 16000), 2500) * np.linspace(0.3, 1, n) * 0.6, -0.2)
n = int(1.0 * SR); tt = secs(n)
boom = np.zeros(n)
for k, rate in enumerate(np.geomspace(9000, 600, 10)):
    seg = slice(int(k * n / 10), int((k + 1) * n / 10))
    boom[seg] = chipnoise(seg.stop - seg.start, rate)
boom = boom * np.exp(-tt * 3.2) + tri(60 - 30 * tt, n) * np.exp(-tt * 5) * 0.8
put(C["impact"], boom * 1.2, -0.2)
a, b = C["fire"]; n = int((b - a) * SR); crackle = np.zeros(n)
for k in rng.integers(0, n - 300, int((b - a) * 40)):
    crackle[k:k + 200] += chipnoise(200, 20000) * rng.uniform(0.2, 0.8) * np.exp(-np.arange(200) / 40)
put(a, (lp(chipnoise(n, 3000), 1200) * 0.25 + crackle) * np.interp(secs(n), [0, 0.3, b - a - 0.4, b - a], [0, 0.9, 0.6, 0]), -0.2)
n = int(1.2 * SR); tt = secs(n)
put(C["otherCar"], engine(200 - 140 * np.clip(tt / 0.7, 0, 1), n) * np.interp(tt, [0, 0.7, 0.9, 1.2], [0.5, 0.8, 0.2, 0]) + hp(chipnoise(n, 16000), 2500) * np.interp(tt, [0.3, 0.4, 0.7, 0.75], [0, 0.4, 0.4, 0]), 0.5)
a, b = C["runners"]
for k, at in enumerate(np.arange(a, b + 0.6, 0.11)):
    n = int(0.05 * SR); put(at, lp(chipnoise(n, 7000), 2500) * np.exp(-np.arange(n) / 500) * 0.35, 0.3 - k * 0.03)
# Monza: helmet seating thud, the pass
n = int(0.25 * SR); tt = secs(n)
put(C["helmetSeat"], tri(110 - 60 * tt / 0.25, n) * np.exp(-tt * 14) * 0.9 + lp(chipnoise(n, 4000), 900) * np.exp(-tt * 30) * 0.5)
pass_by(C["monzaPass"], 1.1, 230, 0.45)
# Fuji: Hunt passes twice; Lauda's car arrives, brakes, cuts out; wet footsteps
pass_by(C["rival1"], 1.9, 240, 0.85, gain=0.6)
pass_by(C["rival2"], 1.9, 250, 0.75, gain=0.45)
n = int((C["engineCut"] - C["arrive"]) * SR); tt = secs(n)
rpm = np.interp(tt, [0, 0.45, 0.5, 0.95, 1.0, 1.7, tt[-1]], [210, 150, 185, 120, 150, 70, 55])
put(C["arrive"], engine(rpm, n) * np.interp(tt, [0, 0.15, tt[-1] - 0.05, tt[-1]], [0.3, 0.8, 0.5, 0]), np.interp(tt, [0, 1.7], [0.8, 0.1]))
n = int(0.12 * SR); put(C["engineCut"], tri(np.full(n, 70.0), n) * np.exp(-secs(n) * 40) * 0.8, 0.1)
for k, at in enumerate(C["steps"]):
    n = int(0.09 * SR)
    put(at, bp(chipnoise(n, 10000), 800, 5000) * np.exp(-secs(n) * 45) * (0.32 if k % 2 else 0.26), np.interp(k, [0, len(C["steps"])], [0.1, -0.6]))
write("sfx-world.wav", world_l, world_r, peak_db=-1.5)
