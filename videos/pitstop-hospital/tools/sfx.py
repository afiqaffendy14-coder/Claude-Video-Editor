"""Synthesised sound design (no credits used): whooshes on the cuts, heart-monitor beeps, wheel-gun rattles,
air hiss, room tone, city ambience, a low hit on "But the danger isn't over". Everything is built from
noise and sine waves in numpy, so it is ours to use.

Run: ../../.venv-audio/bin/python tools/sfx.py <out.wav> <t_from> <t_to>
Scenes are read from boards/shots.json (cut times) so the sounds follow the edit.
"""
import json, os, sys
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

SR = 44100
HERE = os.path.dirname(__file__)
out, t_from, t_to = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
dur = t_to - t_from
N = int(dur * SR)
mix = np.zeros((N, 2))
rng = np.random.default_rng(7)
SHOTS = json.load(open(os.path.join(HERE, "..", "boards", "shots.json")))


def band(x, lo, hi, order=4):
    sos = butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return sosfilt(sos, x)


def lowpass(x, f, order=4):
    return sosfilt(butter(order, f, btype="low", fs=SR, output="sos"), x)


def place(sig, t, gain=1.0, pan=0.0):
    """Add a mono or stereo signal at film time t (seconds)."""
    i = int((t - t_from) * SR)
    if sig.ndim == 1:
        sig = np.stack([sig * (1 - max(pan, 0)), sig * (1 + min(pan, 0))], axis=1)
    a, b = max(i, 0), min(i + len(sig), N)
    if b > a:
        mix[a:b] += sig[a - i:b - i] * gain


def env(n, attack, release):
    e = np.ones(n)
    a, r = int(attack * SR), int(release * SR)
    e[:a] = np.linspace(0, 1, a) if a else 1
    e[n - r:] *= np.linspace(1, 0, r) if r else 1
    return e


def whoosh(length=0.45, up=True):
    n = int(length * SR)
    x = rng.standard_normal(n)
    # sweep a band-pass across the noise by blending a few fixed bands
    out_ = np.zeros(n)
    centres = [400, 900, 1800, 3200]
    for k, c in enumerate(centres if up else centres[::-1]):
        w = np.exp(-((np.linspace(0, 1, n) - (k + 0.5) / len(centres)) ** 2) / 0.02)
        out_ += band(x, c * 0.7, c * 1.4) * w
    return out_ * env(n, 0.15, 0.2) * 0.6


def beep(freq=960, length=0.12):
    n = int(length * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * freq * t) * env(n, 0.005, 0.06) * 0.35


def heartbeat():
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    thump = np.sin(2 * np.pi * 55 * t) * np.exp(-t * 18)
    thump2 = np.sin(2 * np.pi * 48 * t) * np.exp(-np.clip(t - 0.22, 0, None) * 20) * (t > 0.22)
    return (thump + 0.7 * thump2) * 0.9


def wheel_gun(length=0.32):
    """Rattling impact wrench: a fast train of clicks over compressed-air noise."""
    n = int(length * SR)
    x = np.zeros(n)
    rate = 34  # hits per second
    for k in range(int(length * rate)):
        i = int(k / rate * SR)
        m = min(int(0.012 * SR), n - i)
        x[i:i + m] += rng.standard_normal(m) * np.exp(-np.arange(m) / (0.003 * SR))
    x = band(x, 600, 6000) * 1.4 + band(rng.standard_normal(n), 2000, 8000) * 0.15
    return x * env(n, 0.005, 0.05)


def hiss(length, lo=2500, hi=9000):
    n = int(length * SR)
    return band(rng.standard_normal(n), lo, hi) * env(n, 0.05, 0.2)


def rumble(length, f=70):
    n = int(length * SR)
    t = np.arange(n) / SR
    return (lowpass(rng.standard_normal(n), 140) * 1.2 + 0.25 * np.sin(2 * np.pi * f * t)) * env(n, 0.2, 0.3)


def sub_hit():
    n = int(1.4 * SR)
    t = np.arange(n) / SR
    f = 60 * np.exp(-t * 1.2) + 30
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 2.2) * 1.0


cuts = [s["start"] for s in SHOTS if t_from < s["start"] < t_to]
for c in cuts:  # whoosh just before each cut, landing on it
    place(whoosh(0.4, up=True), c - 0.3, 0.45)

def clatter():
    """A small plastic object hitting the floor and skittering."""
    n = int(0.5 * SR)
    x = np.zeros(n)
    for k, (dt, g) in enumerate([(0.0, 1.0), (0.07, 0.5), (0.13, 0.35), (0.2, 0.2)]):
        i = int(dt * SR)
        m = min(int(0.03 * SR), n - i)
        x[i:i + m] += rng.standard_normal(m) * np.exp(-np.arange(m) / (0.004 * SR)) * g
    return band(x, 1200, 7000) * 1.2


def ring():
    """Phone dialling: two-tone ringback."""
    n = int(1.4 * SR)
    t = np.arange(n) / SR
    tone = (np.sin(2 * np.pi * 400 * t) + np.sin(2 * np.pi * 450 * t)) * 0.18
    gate = ((t % 0.6) < 0.4).astype(float)
    return tone * gate * env(n, 0.01, 0.05)


def footsteps(length, rate=1.6):
    n = int(length * SR)
    x = np.zeros(n)
    for k in range(int(length * rate * 2)):
        i = int(k / (rate * 2) * SR)
        m = min(int(0.06 * SR), n - i)
        x[i:i + m] += lowpass(rng.standard_normal(m), 900) * np.exp(-np.arange(m) / (0.012 * SR)) * 0.8
    return x


def engine(length, rising=False, falling=False):
    n = int(length * SR)
    t = np.arange(n) / SR
    k = t / length
    f = 90 + (160 * k if rising else 0) - (40 * k if falling else 0)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * 0.5 + 0.35 * np.sin(2 * ph) + 0.2 * np.sign(np.sin(3 * ph))
    x = lowpass(x, 1800) + band(rng.standard_normal(n), 200, 2000) * 0.1
    g = np.ones(n) if not (rising or falling) else (0.4 + 0.6 * k if rising else 1.0 - 0.75 * k)
    return x * g * env(n, 0.05, 0.15)


def thunk():
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 140 * t) * np.exp(-t * 30) + band(rng.standard_normal(n), 300, 2500) * np.exp(-t * 60) * 0.4)


# what each shot sounds like (by shot number; see boards/shots.json)
HOSPITAL = {1, 4, 5, 8, 9, 11, 12, 13, 25, 26, 27, 28, 29, 34, 35}
PIT_WORK = {2, 16, 17, 18, 19, 24}
CORRIDOR = {6, 7, 10}
for s in SHOTS:
    a, b = max(s["start"], t_from), min(s["end"], t_to)
    if b <= a:
        continue
    n = s["n"]
    if n in HOSPITAL:  # monitor beeps + room tone
        t = a + 0.15
        while t < b:
            place(beep(), t, 0.5 if n == 5 else 0.28, pan=0.25)
            t += 0.75
        place(hiss(b - a, 300, 1200) * 0.15, a, 1.0)
    if n in CORRIDOR:  # castors rolling, footsteps, a monitor carried along
        place(rumble(b - a, 35) * 0.35 + footsteps(b - a) * 0.5, a, 1.0)
        place(beep(), a + 0.3, 0.2)
    if n in PIT_WORK:  # wheel guns, air, engine idling
        place(rumble(b - a, 55) * 0.5 + engine(b - a) * 0.25, a, 1.0)
        for k, t in enumerate(np.arange(a + 0.12, b - 0.2, 0.33 if n != 24 else 0.6)):
            place(wheel_gun(), t, 0.5, pan=(-0.5 if k % 2 else 0.5))
        place(hiss(0.5), a + 0.05, 0.3)
    if n == 15:  # the car arrives
        place(engine(b - a, falling=True) * 0.8, a, 1.0)
    if n == 23:  # in the cockpit: engine close, guns outside
        place(engine(b - a) * 0.6, a, 1.0)
        for t in np.arange(a + 0.2, b - 0.2, 0.45):
            place(wheel_gun(), t, 0.3)
    if n == 32:  # the car leaves
        place(engine(b - a, rising=True) * 0.9, a, 1.0)
    if n == 33:  # quiet box, crowd far away
        place(hiss(b - a, 400, 2500) * 0.12 + rumble(b - a, 40) * 0.2, a, 1.0)
    if n == 3:  # London street
        place(rumble(b - a, 40) * 0.5 + hiss(b - a, 500, 3000) * 0.08, a, 1.0)
        place(whoosh(1.2, up=False) * 0.3, a + 0.6, 1.0, pan=-0.6)
    if n == 13:  # the syringe lands
        place(clatter(), a + 0.95, 0.8, pan=0.3)
    if n == 14:  # the pit stop on the staff-room TV, muffled
        for t in np.arange(a + 0.1, b - 0.2, 0.33):
            place(lowpass(wheel_gun(), 1200), t, 0.35)
    if n == 20:  # dialling Ferrari
        place(ring(), a + 0.1, 0.5)
    if n in (21, 22):  # engineering office: room tone, keys
        place(hiss(b - a, 200, 900) * 0.1, a, 1.0)
        for t in np.arange(a + 0.2, b, 0.23):
            place(thunk() * 0.15, t, 0.4)
    if n in (30, 31):  # the block chart: blocks thunk into place
        for t in np.arange(a + 0.1, min(b, a + 1.2), 0.2):
            place(thunk(), t, 0.6)
    if n == 5:  # "But the danger isn't over": low hit + heartbeat
        place(sub_hit(), a, 0.8)
        for t in np.arange(a + 0.1, b, 0.85):
            place(heartbeat(), t, 0.7)
    if n == 34:  # a soft heartbeat under the tiny hand
        for t in np.arange(a + 0.1, b, 0.85):
            place(heartbeat(), t, 0.4)

peak = np.abs(mix).max()
if peak > 0:
    mix *= 0.8 / peak
sf.write(out, mix.astype(np.float32), SR, subtype="PCM_16")
print("sfx", out, round(dur, 2), "s")
