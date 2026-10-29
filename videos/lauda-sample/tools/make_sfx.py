"""Synthesise the sample's sound effects into assets/audio/ (48 kHz stereo WAV).

Every sound is built from noise and harmonics, seeded, so re-running gives identical files:
  sfx-engine-idle.wav   grid idle (shot 1) that turns muffled for the garage (shot 2)
  sfx-ticks.wav         one soft tick per day as the counter runs 0 -> 42
  sfx-whoosh-a/b.wav    air whooshes peaking on the two cuts (two different takes)
  sfx-helmet.wav        fabric rustle as the helmet is pulled on, padded thud as it seats
  sfx-launch.wav        sub hit on the cut, wheelspin squeal, flat-12 revving away

Run with the project's audio venv:  ../../.venv-audio/bin/python tools/make_sfx.py
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
    """RBJ cookbook biquad (lowpass / highpass / bandpass), f0 may be an array per sample."""
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
        else:  # band-pass, constant peak gain
            b0, b1, b2 = alpha, 0.0, -alpha
        a0, a1, a2 = 1 + alpha, -2 * cw, 1 - alpha
        yi = (b0 * x[i] + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2) / a0
        x2, x1, y2, y1 = x1, x[i], y1, yi
        y[i] = yi
    return y


def env(t, points):
    """Piecewise-linear envelope from (time, gain) points."""
    ts, gs = zip(*points)
    return np.interp(t, ts, gs)


def engine(t, f_fund, roughness=0.35, harmonics=(1, 2, 3, 4, 5, 6, 8, 10)):
    """Flat-12 style tone: harmonics of a firing frequency with jittered phase and a rasp."""
    f = np.broadcast_to(f_fund, t.shape)
    phase = 2 * math.pi * np.cumsum(f) / SR
    jitter = biquad(rng.standard_normal(len(t)), "lp", 30) * 6
    sig = np.zeros_like(t)
    for k, h in enumerate(harmonics):
        sig += np.sin(h * phase + jitter * (k + 1) * 0.05) / (1 + 0.55 * k)
    rasp = biquad(rng.standard_normal(len(t)), "bp", np.clip(f * 6, 200, 6000), 1.2) * roughness
    return np.tanh(1.6 * (sig * 0.5 + rasp))


def stereo(mono, width=0.0, pan=0.0):
    l = mono * (1 - max(pan, 0))
    r = mono * (1 + min(pan, 0))
    if width:
        d = int(SR * 0.0006 * width)
        r = np.concatenate([np.zeros(d), r[:-d]]) if d else r
    return np.stack([l, r], axis=1)


def write(name, data, peak_db=-1.5):
    data = data / (np.max(np.abs(data)) + 1e-9) * (10 ** (peak_db / 20))
    sf.write(os.path.join(OUT, name), data.astype(np.float32), SR, subtype="PCM_16")
    print("wrote", name, f"{len(data) / SR:.2f}s")


os.makedirs(OUT, exist_ok=True)

# Idle on the grid (0–1.9 s), then heard through the garage wall (1.9–3.3 s), swelling.
t = t_axis(3.3)
idle_f = 38 + 2.5 * np.sin(2 * math.pi * 0.9 * t) + 1.5 * np.sin(2 * math.pi * 2.3 * t)
idle = engine(t, idle_f, roughness=0.3)
muffled = biquad(idle, "lp", 380, 0.8)
mix = np.where(t < 1.9, idle, muffled * 1.8)
mix *= env(t, [(0, 0), (0.08, 0.9), (1.85, 1.0), (1.9, 0.75), (3.05, 1.0), (3.3, 0.0)])
write("sfx-engine-idle.wav", stereo(mix, width=1.0))

# Counter ticks: one per day change, timed to the counter's power2.inOut tween (0.35–1.35 s).
t = t_axis(1.5)
ticks = np.zeros_like(t)
click = biquad(rng.standard_normal(int(0.006 * SR)), "hp", 2500) * np.hanning(int(0.006 * SR))
ease = lambda x: 2 * x * x if x < 0.5 else 1 - ((-2 * x + 2) ** 2) / 2
last = 0
for i, ti in enumerate(t):
    if ti < 0.35 or ti > 1.35:
        continue
    n = round(42 * ease((ti - 0.35) / 1.0))
    if n != last:
        s = i
        ticks[s : s + len(click)] += click[: len(t) - s] * (0.6 + 0.4 * (n % 2))
        last = n
write("sfx-ticks.wav", stereo(ticks, width=0.5), peak_db=-6)

# Whooshes: band-passed noise sweeping up then down, peaking 0.3 s in (placed 0.3 s before each cut).
for name, seed_shift, f_lo, f_hi in [("sfx-whoosh-a.wav", 0, 300, 2600), ("sfx-whoosh-b.wav", 1, 220, 3400)]:
    t = t_axis(0.55)
    sweep = np.interp(t, [0, 0.3, 0.55], [f_lo, f_hi, f_lo * 1.4])
    noise = rng.standard_normal(len(t))
    w = biquad(noise, "bp", sweep, 0.9) * env(t, [(0, 0), (0.3, 1), (0.55, 0)]) ** 1.5
    write(name, stereo(w, width=2.0), peak_db=-4)

# Helmet: knit/fabric rustle while it is pulled down (0–0.75 s), then a padded thud at 0.85 s.
t = t_axis(1.3)
rustle = biquad(rng.standard_normal(len(t)), "bp", 1800 + 900 * np.sin(2 * math.pi * 7 * t), 0.7)
rustle *= env(t, [(0, 0), (0.1, 0.35), (0.6, 0.45), (0.8, 0.1), (0.85, 0)])
thud_t = np.clip(t - 0.85, 0, None)
thud = (np.sin(2 * math.pi * 95 * thud_t) * np.exp(-thud_t * 28) + biquad(rng.standard_normal(len(t)), "lp", 900) * np.exp(-thud_t * 60) * 0.5) * (t >= 0.85)
write("sfx-helmet.wav", stereo(rustle * 0.6 + thud, width=0.8), peak_db=-3)

# Launch (shot 3, 1.7 s): sub hit on the cut, wheelspin squeal, revs climbing as the car pulls away.
t = t_axis(1.7)
rev_f = 55 + 210 * (1 - np.exp(-t * 2.2))  # rpm climb
doppler = 1 - 0.05 * np.clip((t - 0.6) / 1.1, 0, 1)  # pitch sags as it recedes
roar = engine(t, rev_f * doppler, roughness=0.55, harmonics=(1, 2, 3, 4, 6, 8, 12))
distance = env(t, [(0, 0.55), (0.12, 1.0), (0.7, 1.0), (1.7, 0.3)])
roar = biquad(roar, "lp", np.interp(t, [0, 0.7, 1.7], [9000, 7000, 2200])) * distance
squeal_f = 2600 + 400 * np.sin(2 * math.pi * 11 * t)
squeal = biquad(rng.standard_normal(len(t)), "bp", squeal_f, 6) * env(t, [(0, 0), (0.05, 1), (0.55, 0.7), (0.75, 0)]) * 2.5
sub_t = t
sub = np.sin(2 * math.pi * (48 - 18 * sub_t) * sub_t) * np.exp(-sub_t * 9) * 1.4
write("sfx-launch.wav", stereo(roar + squeal * 0.5 + sub, width=1.5), peak_db=-1.5)
