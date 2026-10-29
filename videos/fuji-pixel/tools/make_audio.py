"""Synthesise the Fuji pixel short's music bed and sound effects into assets/audio/.

Seeded, so re-running gives identical files. Times inside each file are relative to the
clip's data-start in index.html.
  music-bed.wav   dark D-minor drone, swelling into "By one point", 10 s
  sfx-rain.wav    rain on asphalt, heavier from 3.95 s ("the rain is brutal"), 10 s
  sfx-pass-a/b    the white car screaming past right-to-left with spray (two takes)
  sfx-arrive.wav  Lauda's car downshifting into the pits, brakes, engine cut
  sfx-steps.wav   splashing footsteps as he walks away
  sfx-impact.wav  low hit under "LOST BY 1 POINT"

Run:  ../../.venv-audio/bin/python tools/make_audio.py
"""
import math
import os

import numpy as np
import soundfile as sf

SR = 48000
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "audio")
rng = np.random.default_rng(1976)


def t_axis(sec):
    return np.arange(int(sec * SR)) / SR


def biquad(x, kind, f0, q=0.707):
    f0 = np.broadcast_to(np.asarray(f0, dtype=float), x.shape)
    y = np.zeros_like(x)
    x1 = x2 = y1 = y2 = 0.0
    for i in range(len(x)):
        w = 2 * math.pi * min(f0[i], SR * 0.45) / SR
        cw, alpha = math.cos(w), math.sin(w) / (2 * q)
        if kind == "lp":
            b0, b1, b2 = (1 - cw) / 2, 1 - cw, (1 - cw) / 2
        elif kind == "hp":
            b0, b1, b2 = (1 + cw) / 2, -(1 + cw), (1 + cw) / 2
        else:
            b0, b1, b2 = alpha, 0.0, -alpha
        a0, a1, a2 = 1 + alpha, -2 * cw, 1 - alpha
        yi = (b0 * x[i] + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2) / a0
        x2, x1, y2, y1 = x1, x[i], y1, yi
        y[i] = yi
    return y


def env(t, points):
    ts, gs = zip(*points)
    return np.interp(t, ts, gs)


def engine(t, f, rasp=0.4, harmonics=(1, 2, 3, 4, 6, 8)):
    f = np.broadcast_to(f, t.shape)
    phase = 2 * math.pi * np.cumsum(f) / SR
    sig = sum(np.sin(h * phase) / (1 + 0.6 * k) for k, h in enumerate(harmonics))
    grit = biquad(rng.standard_normal(len(t)), "bp", np.clip(f * 5, 300, 7000), 1.5) * rasp
    return np.tanh(1.5 * (sig * 0.45 + grit))


def pan(mono, p):
    p = np.broadcast_to(np.asarray(p, dtype=float), mono.shape)
    a = (p + 1) * math.pi / 4
    return np.stack([mono * np.cos(a), mono * np.sin(a)], axis=1)


def write(name, data, peak_db=-1.5):
    data = data / (np.max(np.abs(data)) + 1e-9) * (10 ** (peak_db / 20))
    sf.write(os.path.join(OUT, name), data.astype(np.float32), SR, subtype="PCM_16")
    print("wrote", name, f"{len(data) / SR:.2f}s")


os.makedirs(OUT, exist_ok=True)

# Music bed: low D-minor drone with slow movement, swelling to the final line.
t = t_axis(10)
bed = np.zeros_like(t)
for f, g in [(36.71, 0.9), (73.42, 0.8), (110.0, 0.5), (146.83, 0.35), (174.61, 0.28)]:
    wob = 1 + 0.003 * np.sin(2 * math.pi * 0.13 * t + f)
    bed += g * (np.sin(2 * math.pi * f * wob * t) + 0.3 * np.sin(4 * math.pi * f * wob * t))
bed = biquad(bed, "lp", 700)
bed *= 0.75 + 0.25 * np.sin(2 * math.pi * 0.25 * t - 1.2)  # slow breathing
bed *= env(t, [(0, 0), (1.5, 0.75), (7.3, 0.85), (8.85, 1.0), (8.95, 0.7), (9.4, 0.6), (10, 0)])
write("music-bed.wav", np.stack([bed, np.roll(bed, 240)], axis=1), peak_db=-3)

# Rain: broadband hiss plus a scatter of drop ticks; heavier from 3.95 s.
t = t_axis(10)
hiss = biquad(biquad(rng.standard_normal(len(t)), "hp", 450), "lp", 7500)
drops = np.zeros_like(t)
for k in rng.integers(0, len(t) - 400, 2600):
    drops[k : k + 160] += rng.uniform(0.2, 1.0) * np.exp(-np.arange(160) / 25) * rng.standard_normal(160)
drops = biquad(drops, "hp", 1500)
level = env(t, [(0, 0), (0.35, 0.65), (3.95, 0.65), (4.6, 1.0), (9.6, 1.0), (10, 0)])
rain = (hiss * 0.7 + drops * 0.5) * level
write("sfx-rain.wav", np.stack([rain, np.roll(rain, 380)], axis=1), peak_db=-6)

# Pass-by: flat-12 scream with Doppler drop, spray hiss, panned right → left; peak at 0.8 s.
for name, f0, peak in [("sfx-pass-a.wav", 330, 0.8), ("sfx-pass-b.wav", 345, 0.85)]:
    t = t_axis(1.9)
    s = (t - peak) / 0.35
    dop = 1 + 0.12 * -np.tanh(s)  # higher approaching, lower leaving
    roar = engine(t, f0 * dop, rasp=0.5)
    spray = biquad(rng.standard_normal(len(t)), "bp", 3200, 0.8) * 0.8
    amp = 1 / (1 + s * s)
    mono = (roar + spray) * amp * env(t, [(0, 0), (0.1, 1), (1.7, 1), (1.9, 0)])
    write(name, pan(mono, -np.tanh(s * 0.8) * 0.75))

# Arrival: downshifting with throttle blips, brake squeal, then the engine is switched off.
t = t_axis(2.0)
rpm = np.interp(t, [0, 0.38, 0.42, 0.75, 0.79, 1.2, 1.62, 1.65], [250, 190, 235, 160, 200, 120, 95, 0])
car = engine(t, np.maximum(rpm, 1), rasp=0.35, harmonics=(1, 2, 3, 4, 6))
car *= env(t, [(0, 0.6), (0.1, 1), (1.55, 0.7), (1.64, 0.5), (1.66, 0)])
squeal = biquad(rng.standard_normal(len(t)), "bp", 2400 + 200 * np.sin(2 * math.pi * 9 * t), 9) * env(t, [(0, 0), (0.9, 0), (1.05, 0.6), (1.5, 0.3), (1.6, 0)]) * 2
clunk_t = np.clip(t - 1.65, 0, None)
clunk = np.sin(2 * math.pi * 70 * clunk_t) * np.exp(-clunk_t * 30) * (t >= 1.65)
ping = np.zeros_like(t)  # hot engine ticking after shutdown
for k in [1.82, 1.93]:
    i = int(k * SR)
    ping[i : i + 300] += np.sin(2 * math.pi * 5200 * np.arange(300) / SR) * np.exp(-np.arange(300) / 60) * 0.15
write("sfx-arrive.wav", pan(car + squeal * 0.4 + clunk * 0.8 + ping, np.interp(t, [0, 1.65], [0.6, 0.15])))

# Footsteps through standing water, one every 0.36 s, alternating feet.
t = t_axis(3.6)
steps = np.zeros_like(t)
for n, k in enumerate(np.arange(0.05, 3.5, 0.36)):
    i = int(k * SR)
    L = int(0.16 * SR)
    burst = biquad(rng.standard_normal(L), "bp", 900 + 300 * (n % 2), 1.1) * np.exp(-np.arange(L) / (0.035 * SR))
    slap = np.sin(2 * math.pi * 120 * np.arange(L) / SR) * np.exp(-np.arange(L) / (0.012 * SR)) * 0.6
    steps[i : i + L] += (burst + slap)[: len(t) - i] * (0.85 + 0.15 * (n % 2))
write("sfx-steps.wav", pan(steps, np.interp(t, [0, 3.6], [0.1, -0.35])), peak_db=-3)

# Impact: sub drop with a short cracked transient and a dark tail.
t = t_axis(1.12)
sub = np.sin(2 * math.pi * (55 - 25 * t) * t) * np.exp(-t * 3.2)
crack = biquad(rng.standard_normal(len(t)), "lp", 2200) * np.exp(-t * 28) * 0.7
tail = biquad(rng.standard_normal(len(t)), "lp", 300) * np.exp(-t * 4) * 0.35
write("sfx-impact.wav", pan(sub + crack + tail, 0.0))
