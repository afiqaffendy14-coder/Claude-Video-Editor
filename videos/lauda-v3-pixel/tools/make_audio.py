"""Music and sound for the Lauda v3 short, timed to the 36 shots in scene/timeline.js.

  python tools/make_audio.py pixel   -> chiptune score + 8-bit effects  (this project)
  python tools/make_audio.py 3d      -> dark cinematic score + natural effects (../lauda-v3-3d)

Writes music.wav, rain.wav and sfx.wav (stereo, 48 kHz, full length) into the project's
assets/audio/. Everything is synthesised and seeded, so re-running gives identical files.
Run with the audio venv:  ../../.venv-audio/bin/python tools/make_audio.py pixel
"""
import json, math, os, re, sys
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

STYLE = sys.argv[1] if len(sys.argv) > 1 else "pixel"
CHIP = STYLE == "pixel"
SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets", "audio") if CHIP else os.path.join(HERE, "..", "..", "lauda-v3-3d", "assets", "audio")
src = open(os.path.join(HERE, "..", "scene", "timeline.js")).read()
DUR = float(re.search(r"DURATION = ([0-9.]+)", src).group(1))
SHOTS = {s["id"]: s for s in json.loads(re.search(r"SHOTS = (\[.*?\]);", src, re.S).group(1))}
N = int(DUR * SR)
rng = np.random.default_rng(1976 if CHIP else 2026)
st = lambda i: SHOTS[i]["start"]
en = lambda i: SHOTS[i]["end"]

def secs(n): return np.arange(n) / SR
def lp(x, f, o=2): return sosfilt(butter(o, min(f, SR * 0.45) / (SR / 2), "low", output="sos"), x)
def hp(x, f, o=2): return sosfilt(butter(o, f / (SR / 2), "high", output="sos"), x)
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo / (SR / 2), min(hi, SR * 0.45) / (SR / 2)], "band", output="sos"), x)
def note(name):
    names = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3, "G": -2, "G#": -1, "A": 0, "A#": 1, "Bb": 1, "B": 2}
    return 440.0 * 2 ** ((names[name[:-1]] + (int(name[-1]) - 4) * 12) / 12)
def pulse(f, n, duty=0.5): ph = np.cumsum(np.broadcast_to(f, (n,)) / SR) % 1; return np.where(ph < duty, 1.0, -1.0)
def tri(f, n):
    ph = np.cumsum(np.broadcast_to(f, (n,)) / SR) % 1; t = 4 * np.abs(ph - 0.5) - 1
    return np.round(t * 8) / 8 if CHIP else t
def saw(f, n): ph = np.cumsum(np.broadcast_to(f, (n,)) / SR) % 1; return 2 * ph - 1
def noise(n, rate=None):
    if CHIP and rate: hold = max(1, int(SR / rate)); return np.repeat(rng.uniform(-1, 1, n // hold + 2), hold)[:n]
    return rng.standard_normal(n)
def adsr(n, a=0.005, d=0.05, s=0.6, r=0.05):
    e = np.ones(n) * s; A, D, R = int(a * SR), int(d * SR), int(r * SR)
    if A: e[:A] = np.linspace(0, 1, A)
    if D: e[A:A + D] = np.linspace(1, s, len(e[A:A + D]))
    if R and n > R: e[-R:] *= np.linspace(1, 0, R)
    return e
def place(tr, start, sig, gain=1.0):
    i = int(start * SR)
    if i >= len(tr) or i + len(sig) <= 0: return
    j = min(len(tr), i + len(sig)); k0 = max(0, -i)
    tr[max(0, i):j] += sig[k0:k0 + (j - max(0, i))] * gain
def write(name, l, r=None, peak_db=-1.5):
    x = np.stack([l, l if r is None else r], axis=1); x = x / (np.max(np.abs(x)) + 1e-9) * 10 ** (peak_db / 20)
    sf.write(os.path.join(OUT, name), x.astype(np.float32), SR, subtype="PCM_16"); print("wrote", STYLE, name)

os.makedirs(OUT, exist_ok=True)

# ------------------------------------------------------------------ music
BEAT = 60 / 92
music = np.zeros(N)
def tone(start, dur, f, kind="lead", vol=0.3, env=(0.005, 0.06, 0.55, 0.06)):
    n = int(dur * SR)
    if n <= 0: return
    if CHIP: sig = tri(f, n) if kind == "bass" else pulse(f, n, 0.25 if kind == "lead" else 0.125)
    else:
        if kind == "bass": sig = np.sin(2 * math.pi * np.cumsum(np.full(n, f)) / SR) + 0.3 * tri(f * 2, n)
        else: sig = lp(saw(f, n) + saw(f * 1.006, n) + 0.6 * saw(f * 0.497, n), 900 if kind == "pad" else 2200)
        env = (max(env[0], 0.02), env[1], env[2], max(env[3], 0.12))
    place(music, start, sig * adsr(n, *env) * vol)
def arp(a, b, chord, step=BEAT / 2, vol=0.14):
    seq, t, i = chord + chord[-2:0:-1], a, 0
    while t < b - 0.01:
        tone(t, min(step * 0.9, b - t), note(seq[i % len(seq)]), "lead", vol if CHIP else vol * 0.45); t += step; i += 1
def bass(a, b, root, step=BEAT, vol=0.4):
    t = a
    while t < b - 0.01: tone(t, min(step * 0.95, b - t), note(root), "bass", vol, (0.003, 0.05, 0.8, 0.03)); t += step
def pad(a, b, chord, vol=0.05):
    for nm in chord: tone(a, b - a, note(nm), "pad", vol if CHIP else vol * 1.6, (0.5, 0.2, 0.8, 0.5))
def section(a, b, prog, step_bass=BEAT / 2, arp_on=True, vol_arp=0.12):
    t, k = a, 0
    while t < b - 0.01:
        root, ch = prog[k % len(prog)]; e = min(b, t + BEAT * 4)
        bass(t, e, root, step_bass, 0.34); pad(t, e, ch, 0.03)
        if arp_on: arp(t, e, ch, vol=vol_arp)
        t, k = e, k + 1

Dm, Bb, Gm, A, F, C = ("D2", ["D4", "F4", "A4"]), ("Bb1", ["Bb3", "D4", "F4"]), ("G1", ["G3", "Bb3", "D4"]), ("A1", ["A3", "C#4", "E4"]), ("F2", ["F3", "A3", "C4"]), ("C2", ["C4", "E4", "G4"])
section(0.0, st("rewind"), [Dm, Bb, Gm, A])                     # the walk-away: tense, driving
sweep_n = int((st("ringAerial") - st("rewind")) * SR)             # rewind: pitch falls away
place(music, st("rewind"), (pulse if CHIP else saw)(np.linspace(900, 120, sweep_n), sweep_n) * np.linspace(0.25, 0, sweep_n) * (1 if CHIP else 0.35))
section(st("ringAerial"), st("snaps") + 0.92, [Dm, Dm, Bb, A], step_bass=BEAT / 4, vol_arp=0.1)  # the Ring, racing
tone(st("snaps") + 1.5, en("dragOut") - st("snaps") - 1.5, note("D1") * 2, "bass", 0.32, (0.4, 0.3, 0.6, 0.6))  # silence after impact, a low drone
for k, nm in enumerate(["D3", "C3", "Bb2", "A2"]):              # hospital: sparse falling notes
    tone(st("burned") + k * BEAT * 2, BEAT * 1.9, note(nm), "bass", 0.3, (0.01, 0.2, 0.6, 0.3))
pad(st("burned"), st("racingAgain"), ["D3", "F3", "A3"], 0.03)
section(st("racingAgain"), st("forward"), [F, C, Bb, F], vol_arp=0.12)  # Monza: hope
section(st("forward"), st("onePoint"), [Dm, Bb, Gm, A], vol_arp=0.1)   # Japan again
for k, nm in enumerate(["E4", "C4", "A3"]):                      # "By one point": three falling notes
    tone(st("onePoint") + k * 0.3, 0.32, note(nm), "lead" if CHIP else "pad", 0.32 if CHIP else 0.2, (0.005, 0.1, 0.7, 0.12))
for k, ch in enumerate([["D3", "F3", "A3"], ["Bb2", "D3", "F3"], ["F3", "A3", "C4"], ["A2", "C#3", "E3"]]):  # the meaning: slow, resolving
    a = st("worthMore") + k * (DUR - st("worthMore")) / 4
    pad(a, a + (DUR - st("worthMore")) / 4 + 0.3, ch, 0.06); tone(a, (DUR - st("worthMore")) / 4, note(ch[0]) / 2, "bass", 0.28, (0.05, 0.3, 0.6, 0.4))
music *= np.interp(secs(N), [0, 0.15, DUR - 0.25, DUR], [0.6, 1, 1, 0.8])  # loops cleanly: no fade to silence
write("music.wav", music, np.roll(music, 220), -3)

# ------------------------------------------------------------------ rain (soft, behind the voice)
FUJI = ["walkaway", "helmetHand", "faceLook", "fujiWide", "finalRace", "scores", "pitIn", "climbOut", "stands", "rewind", "forward", "rainHeavy", "povSpray", "fireOnce", "parks", "huntTitle", "onePoint", "worthMore", "bravest", "stop", "thatsWhy"]
brown = hp(np.cumsum(rng.standard_normal(N)), 60); brown /= np.max(np.abs(brown))
open_ = lp(brown, 1800, 3) + lp(hp(rng.standard_normal(N), 900), 2600) * 0.08
t = secs(N); envr = np.zeros(N)
for sid in FUJI:
    a, b = st(sid), en(sid); envr[int(a * SR):int(b * SR)] = 1.4 if sid in ("rainHeavy", "povSpray") else 1.0
envr = lp(envr, 6)  # short ramps at the cuts
glass = lp(brown, 650, 3) * np.interp(t, [st("burned") - 0.05, st("burned"), en("fortyTwo"), en("fortyTwo") + 0.05], [0, 0.6, 0.6, 0])
write("rain.wav", open_ * envr + glass, np.roll(open_ * envr + glass, 410), -6)

# ------------------------------------------------------------------ sound effects
L, R = np.zeros(N), np.zeros(N)
def put(start, sig, pan=0.0, gain=1.0):
    pan = np.broadcast_to(np.asarray(pan, dtype=float), sig.shape); a = (pan + 1) * math.pi / 4
    place(L, start, sig * np.cos(a), gain); place(R, start, sig * np.sin(a), gain)
def beep(f, d, vol=1.0):
    n = int(d * SR)
    return (pulse(f, n, 0.5) if CHIP else np.sin(2 * math.pi * f * secs(n)) * 0.9) * adsr(n, 0.002, 0.02, 0.7, 0.02) * vol
def engine(f, n, rough=0.4):
    f = np.broadcast_to(np.asarray(f, dtype=float), (n,))
    if CHIP:
        vib = 1 + 0.015 * np.sin(2 * math.pi * 23 * secs(n))
        return lp(pulse(f * vib, n, 0.3) + 0.3 * pulse(f * 2.01 * vib, n), 3500)
    ph = 2 * math.pi * np.cumsum(f) / SR
    sig = sum(np.sin(h * ph) / (1 + 0.6 * k) for k, h in enumerate((1, 2, 3, 4, 6, 8)))
    return np.tanh(1.5 * (sig * 0.45 + bp(noise(n), 300, 6000) * rough))
def pass_by(start, dur, f0, peak, pan_from=0.8, pan_to=-0.8, gain=0.8):
    n = int(dur * SR); tt = secs(n); s = (tt - peak) / 0.3
    put(start, (engine(f0 * (1 - 0.12 * np.tanh(s)), n) + bp(noise(n, 9000), 1500, 6000) * 0.4) / (1 + s * s), np.interp(tt, [0, dur], [pan_from, pan_to]), gain)
def steps(a, b, gain=0.3):
    for k, at in enumerate(np.arange(a, b, 0.36)):
        n = int(0.09 * SR); put(at, bp(noise(n, 10000), 800, 5000) * np.exp(-secs(n) * 45), 0.1, gain * (0.85 + 0.15 * (k % 2)))
def tape(start, dur, up):
    n = int(dur * SR); f = np.linspace(200, 1400, n) if up else np.linspace(1400, 160, n)
    whirr = bp(noise(n, 12000), 300, 5000) * 0.3 + (pulse(f, n, 0.5) if CHIP else saw(f, n)) * 0.15
    put(start, whirr * np.interp(secs(n), [0, 0.05, dur - 0.1, dur], [0, 1, 1, 0]), 0, 0.9)

# Fuji: footsteps, the white car passing, the scores, his car pulling in, climbing out
steps(st("walkaway") + 0.1, en("walkaway"))
pass_by(st("finalRace") - 0.2, 1.6, 250, 0.7, gain=0.55)
pass_by(st("scores") + 0.2, 1.8, 240, 0.9, gain=0.45)
put(st("scores") + 0.3, np.concatenate([beep(784, 0.05, 0.5), beep(1047, 0.09, 0.5)]))
n = int((en("pitIn") - st("pitIn")) * SR); tt = secs(n)
put(st("pitIn"), engine(np.interp(tt, [0, tt[-1]], [190, 70]), n) * np.interp(tt, [0, 0.1, tt[-1] - 0.05, tt[-1]], [0.4, 0.8, 0.5, 0]), np.interp(tt, [0, tt[-1]], [0.7, 0]))
n = int(0.12 * SR); put(en("pitIn") - 0.05, tri(np.full(n, 70.0), n) * np.exp(-secs(n) * 40) * 0.8)  # engine cut
n = int(0.4 * SR); put(st("climbOut") + 0.2, lp(noise(n, 4000), 1500) * np.exp(-secs(n) * 8) * 0.35)  # suit rustle
tape(st("rewind"), en("rewind") - st("rewind"), up=False)
# the Ring: engine echoing through the hills, the approach, the skid, the impact, the fire
n = int((en("greenHell") - st("ringAerial")) * SR); tt = secs(n)
put(st("ringAerial"), lp(engine(160 + 25 * np.sin(tt * 1.3), n), 900) * np.interp(tt, [0, 1.62, 1.7, tt[-1]], [0.25, 0.25, 0.7, 0.8]), np.sin(tt * 0.7) * 0.5)
IMPACT = st("snaps") + 0.92
n = int((IMPACT - st("lapTwo")) * SR); tt = secs(n)
put(st("lapTwo"), engine(np.interp(tt, [0, tt[-1]], [200, 250]), n) * 0.8, np.interp(tt, [0, tt[-1]], [0.6, -0.2]))
n = int(0.55 * SR); put(IMPACT - 0.55, hp(noise(n, 16000), 2500) * np.linspace(0.3, 1, n) * 0.6, -0.2)
n = int(1.2 * SR); tt = secs(n)
if CHIP:
    boom = np.concatenate([noise(n // 10, r) for r in np.geomspace(9000, 600, 10)])[:n]
    boom = np.pad(boom, (0, n - len(boom)))
else:
    boom = lp(noise(n), 2500) + lp(noise(n), 400) * 2
put(IMPACT, (boom * np.exp(-tt * 3.0) + tri(60 - 30 * tt, n) * np.exp(-tt * 5) * 0.9) * 1.2, -0.2)
a, b = IMPACT, en("dragOut"); n = int((b - a) * SR); crackle = np.zeros(n)
for k in rng.integers(0, n - 300, int((b - a) * 40)): crackle[k:k + 200] += noise(200, 20000) * rng.uniform(0.2, 0.8) * np.exp(-np.arange(200) / 40)
put(a, (lp(noise(n, 3000), 1200) * 0.3 + crackle) * np.interp(secs(n), [0, 0.3, b - a - 0.3, b - a], [0, 0.9, 0.7, 0]), -0.2, 0.9)
steps(st("dragOut") + 0.2, en("dragOut"), 0.25)
# the hospital: the heart monitor (slow, then racing with an alarm, then steadier), the days ticking past
def monitor(a, b, bpm, alarm=False):
    t0, k = a + 0.1, 0
    while t0 < b:
        put(t0, beep(988, 0.09, 0.5))
        if alarm: put(t0 + 0.12, beep(1175, 0.06, 0.35))
        t0 += 60 / bpm * (0.85 + 0.3 * ((k * 37) % 7) / 7 if alarm else 1); k += 1
monitor(st("burned"), en("burned"), 52)
monitor(st("lungs"), en("doctors"), 112, alarm=True)
monitor(st("fortyTwo"), en("fortyTwo"), 72)
for k in range(18):  # the DAY counter running to 42
    at = st("fortyTwo") + 0.12 + k * (en("fortyTwo") - st("fortyTwo") - 0.3) / 18
    put(at, np.concatenate([beep(988, 0.03, 0.3), beep(1319, 0.05, 0.3)]) if CHIP else beep(2200, 0.02, 0.25))
put(en("fortyTwo") - 0.12, np.concatenate([beep(note(n_), 0.05, 0.5) for n_ in ["C5", "E5", "G5", "C6", "E6"]]) if CHIP else beep(1760, 0.25, 0.3))
# Monza: idle and rev, the helmet thud, the pass, the P4 fanfare
n = int((en("racingAgain") - st("racingAgain")) * SR); tt = secs(n)
put(st("racingAgain"), engine(np.interp(tt, [0, 0.6, 0.8, tt[-1]], [60, 60, 140, 90]), n) * 0.6)
for at in (st("helmetOn") + 1.7, st("comingBack") + 0.9):
    n = int(0.25 * SR); tt = secs(n); put(at, tri(110 - 60 * tt / 0.25, n) * np.exp(-tt * 14) * 0.9 + lp(noise(n, 4000), 900) * np.exp(-tt * 30) * 0.5)
pass_by(st("fourth") - 0.1, 1.3, 230, 0.5, gain=0.7)
put(st("fourth") + 0.45, np.concatenate([beep(note("G5"), 0.11, 0.5), beep(note("B5"), 0.11, 0.5), beep(note("D6"), 0.3, 0.5)]))
tape(st("forward"), en("forward") - st("forward"), up=True)
# Japan: the storm, the car in the spray, the memory of fire, parking and walking away, Hunt's flag, the scores flip
pass_by(st("rainHeavy") - 0.1, 1.8, 245, 0.6, gain=0.6)
n = int((en("povSpray") - st("povSpray")) * SR); tt = secs(n)
put(st("povSpray"), engine(np.full(n, 230.0) + 8 * np.sin(tt * 3), n) * 0.55 + bp(noise(n, 9000), 1500, 7000) * 0.35)
n = int((en("fireOnce") - st("fireOnce")) * SR); put(st("fireOnce"), lp(noise(n, 3000), 900) * np.sin(np.linspace(0, math.pi, n)) * 0.5)
n = int(0.12 * SR); put(st("parks") + 0.4, tri(np.full(n, 70.0), n) * np.exp(-secs(n) * 40) * 0.7)
steps(st("parks") + 1.0, en("parks"))
pass_by(st("huntTitle") - 0.1, 1.6, 255, 0.5, gain=0.6)
put(st("onePoint"), np.concatenate([beep(1047, 0.05, 0.5), beep(784, 0.05, 0.5), beep(1047, 0.1, 0.5)]))
put(st("onePoint") + 0.1, (tri(np.full(int(0.5 * SR), 55.0), int(0.5 * SR)) * np.exp(-secs(int(0.5 * SR)) * 5)) * 0.8)  # a low thud under it
for k in range(3):  # the monitor beep, once more, echoing away on "knowing when to stop"
    put(st("stop") + 0.4 + k * 0.28, beep(988, 0.09, 0.45 * 0.45 ** k))
steps(st("thatsWhy"), DUR - 0.05)
write("sfx.wav", L, R, -1.5)
