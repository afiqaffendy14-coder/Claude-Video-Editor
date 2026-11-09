"""Our own sound effects for the halo short, synthesised from scratch (oscillators, filtered noise, simple
physical models) so they are entirely ours to use. Writes one WAV per sound into assets/audio/sfx_synth/, with
the same names as the ElevenLabs set, so tools/sfx_mix.py can mix either library with identical timing.

Run: python tools/sfx_synth.py
"""
import os
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

SR = 48000
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "audio", "sfx_synth")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(11)


def t_(d):
    return np.arange(int(d * SR)) / SR


def bp(x, lo, hi, o=4):
    return sosfilt(butter(o, [lo, hi], btype="band", fs=SR, output="sos"), x)


def lp(x, f, o=4):
    return sosfilt(butter(o, f, btype="low", fs=SR, output="sos"), x)


def hp(x, f, o=4):
    return sosfilt(butter(o, f, btype="high", fs=SR, output="sos"), x)


def noise(d):
    return rng.standard_normal(int(d * SR))


def env(n, a, r):
    e = np.ones(n)
    ai, ri = int(a * SR), int(r * SR)
    if ai:
        e[:ai] = np.linspace(0, 1, ai)
    if ri:
        e[-ri:] *= np.linspace(1, 0, ri)
    return e


def osc(freq, harmonics):
    """Additive oscillator following a frequency curve (array), harmonics = [(n, amp)]."""
    ph = 2 * np.pi * np.cumsum(freq) / SR
    return sum(a * np.sin(n * ph + n * 0.7) for n, a in harmonics)


def damped(f, d, tau, amp=1.0):
    t = t_(d)
    return amp * np.sin(2 * np.pi * f * t) * np.exp(-t / tau)


def put(dst, src, t, g=1.0):
    i = int(t * SR)
    m = min(len(src), len(dst) - i)
    if m > 0:
        dst[i:i + m] += src[:m] * g


def stereo(x, width=0.0, pan=0.0):
    """Mono -> stereo, optionally decorrelated (width) and panned."""
    d = int(0.011 * SR)
    r = np.concatenate([np.zeros(d), x[:-d]]) if width else x
    l_, r_ = x * (1 - width * 0.3) + r * width * 0.3, r * (1 - width * 0.3) + x * width * 0.3
    return np.stack([l_ * min(1, 1 - pan), r_ * min(1, 1 + pan)], axis=1)


def save(name, x):
    x = np.asarray(x, np.float64)
    if x.ndim == 1:
        x = stereo(x)
    x = x / max(1e-9, np.abs(x).max()) * 0.95
    sf.write(os.path.join(OUT, name + ".wav"), x.astype(np.float32), SR)
    print("synth", name, round(len(x) / SR, 2), "s")


def engine(rpm, grit=0.25):
    """A turbo V6 at a given rpm curve: 3 firing pulses per revolution, rich harmonics, intake noise, turbo whine."""
    f0 = rpm / 60 * 3
    x = osc(f0, [(1, 1.0), (2, 0.6), (3, 0.45), (4, 0.3), (5, 0.22), (6, 0.15), (8, 0.08)])
    x = np.tanh(1.6 * x)  # a little saturation: the rasp
    x += grit * bp(noise(len(f0) / SR), 300, 4000) * (0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(f0) / SR))
    x += 0.05 * np.sin(2 * np.pi * np.cumsum(f0 * 6.5) / SR)  # turbo / MGU-H whine
    return lp(x, 7000)


# ---------------------------------------------------------------- the cars
def onboard():
    d = 7.0
    t = t_(d)
    rpm = 11800 + 250 * np.sin(t * 2.1)
    for t0 in (4.2, 4.65, 5.05, 5.4):  # braking: four quick downshifts, each with a throttle blip
        k = t > t0
        rpm = np.where(k, rpm - 1300 + 900 * np.exp(-(t - t0) / 0.05) * k, rpm)
    x = engine(rpm, 0.35)
    wind = lp(noise(d), 900) * 0.35  # helmet buffeting
    x = x * env(len(t), 0.05, 0.3) + wind
    return stereo(x, width=0.6)


def passby(d=4.0, t_close=1.5, v=55.0, dist=4.0, rpm0=11500, brake=2.4):
    """A car flashing past: Doppler pitch, 1/r loudness, a left-to-right pan, then braking."""
    t = t_(d)
    x_pos = v * (t - t_close)
    r = np.sqrt(x_pos ** 2 + dist ** 2)
    radial = v * x_pos / r
    doppler = 343 / (343 + radial)
    rpm = rpm0 - 2500 * np.clip((t - brake) / 0.6, 0, 1)
    sig = engine(rpm * doppler, 0.3) * (dist / r) ** 1.1
    pan = np.clip(x_pos / 25, -0.9, 0.9)
    return np.stack([sig * np.minimum(1, 1 - pan), sig * np.minimum(1, 1 + pan)], axis=1)


def pack():
    d = 3.5
    out = np.zeros((int(d * SR), 2))
    for i, (tc, dist, rpm) in enumerate(((0.9, 6, 11800), (1.2, 4, 11500), (1.45, 8, 12000), (1.8, 5, 11600))):
        out += passby(d, tc, 60, dist, rpm, 9) * (0.8 if i else 1.0)
    return out


# ---------------------------------------------------------------- impacts
def thump(d=1.5, f0=70, f1=35, tau=0.25):
    t = t_(d)
    f = f1 + (f0 - f1) * np.exp(-t / 0.08)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / tau)


def crack(d=0.15, lo=1500, hi=7000, tau=0.02):
    return bp(noise(d), lo, hi) * np.exp(-t_(d) / tau)


def kerb():
    x = np.zeros(int(2.0 * SR))
    put(x, thump(1.0, 90, 45, 0.12), 0.0, 1.0)
    put(x, crack(0.2, 1200, 6000, 0.03), 0.0, 0.8)
    for k in range(6):  # the plastic kerb rattling under the tyres
        put(x, crack(0.05, 800, 4000, 0.01), 0.05 + k * 0.045, 0.45 * (1 - k / 7))
    return stereo(x, 0.4)


def landing():
    d = 3.0
    x = np.zeros(int(d * SR))
    put(x, thump(1.6, 80, 32, 0.35), 0.0, 1.0)
    for k in range(18):  # carbon fibre cracking and splintering
        put(x, crack(0.12, rng.uniform(900, 2500), rng.uniform(4000, 9000), rng.uniform(0.01, 0.04)),
            rng.uniform(0, 0.35), rng.uniform(0.3, 0.8))
    for f in (310, 470, 820, 1270, 1730):  # bodywork and wishbones ringing
        put(x, damped(f, 1.2, 0.18, 0.12), rng.uniform(0, 0.05))
    for k in range(25):  # bits landing and skittering
        put(x, crack(0.04, 1500, 6000, 0.006), 0.4 + rng.exponential(0.5), rng.uniform(0.05, 0.2))
    return stereo(x, 0.7)


def boom():
    d = 4.0
    t = t_(d)
    f = 30 + 35 * np.exp(-t / 0.3)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 1.1)
    x += 0.4 * lp(noise(d), 180) * np.exp(-t / 0.9)
    return stereo(x * env(len(t), 0.005, 0.5), 0.5)


def barrier():
    d = 4.0
    t = t_(d)
    x = np.zeros(len(t))
    put(x, thump(1.5, 85, 30, 0.3), 0.0, 1.0)
    put(x, crack(0.3, 600, 8000, 0.06), 0.0, 1.0)
    for f in (520, 760, 1090, 1440, 2210):  # the armco ringing and tearing
        put(x, damped(f, 1.5, 0.25, 0.18), rng.uniform(0, 0.08))
    for k in range(12):
        put(x, crack(0.1, 400, 3000, 0.03), rng.uniform(0.02, 0.4), 0.5)
    # the fuel igniting: a roaring whoosh that swells and dies away
    whoosh_ = lp(noise(d), 1200) * np.clip((t - 0.08) / 0.25, 0, 1) * np.exp(-np.clip(t - 0.3, 0, None) / 0.9)
    x += 1.2 * whoosh_ + 0.5 * lp(noise(d), 120) * np.exp(-t / 1.4)
    return stereo(x, 0.8)


def gravel():
    """Granular gravel: thousands of stone clicks, thinning as the cars slow, over a scrape."""
    d = 6.0
    t = t_(d)
    x = np.zeros(len(t))
    density = 900 * np.exp(-t / 2.2) + 60
    n = int(np.trapezoid(density, t))
    times = np.sort(rng.uniform(0, d, n))
    keep = rng.uniform(0, 1, n) < np.interp(times, t, density) / density.max()
    for tt in times[keep]:
        i = int(tt * SR)
        m = min(int(0.004 * SR), len(x) - i)
        x[i:i + m] += rng.standard_normal(m) * np.exp(-np.arange(m) / (0.0008 * SR)) * rng.uniform(0.2, 1)
    x = bp(x, 900, 7000)
    x += 0.5 * bp(noise(d), 120, 900) * np.exp(-t / 2.5)  # the floor and tyres scrubbing
    return stereo(x * env(len(t), 0.02, 0.6), 0.8)


# ---------------------------------------------------------------- the halo, the tests
def reveal():
    d = 4.0
    t = t_(d)
    chord = [440, 554.4, 659.3, 880, 1108.7]
    x = sum(np.sin(2 * np.pi * f * t * (1 + 0.002 * np.sin(2 * np.pi * 0.3 * t + i))) / (i + 1)
            for i, f in enumerate(chord))
    x *= 0.7 + 0.3 * np.sin(2 * np.pi * 5 * t)  # a soft shimmer
    x += 0.3 * bp(noise(d), 3000, 9000) * np.exp(-((t - 0.5) / 0.5) ** 2)
    return stereo(x * env(len(t), 1.0, 1.6), 1.0)


def press():
    d = 4.0
    t = t_(d)
    hum = osc(np.full(len(t), 98.0), [(1, 1), (2, 0.5), (3, 0.25)]) * 0.25
    hiss = bp(noise(d), 2500, 7000) * 0.15 * env(len(t), 0.2, 0.4)
    x = hum + hiss
    # under load: a slow metallic groan and creaks
    f = 70 - 10 * np.clip((t - 1.4) / 2, 0, 1)
    groan = np.sin(2 * np.pi * np.cumsum(f) / SR) * lp(np.abs(noise(d)), 30) * 2.5 * np.clip((t - 1.3) / 0.4, 0, 1)
    x += 0.6 * bp(groan, 50, 600)
    for k in range(7):
        put(x, damped(rng.uniform(160, 420), 0.4, 0.06, 0.4), 1.5 + rng.uniform(0, 2.2))
    return stereo(x * env(len(t), 0.05, 0.4), 0.5)


def crane():
    d = 3.0
    t = t_(d)
    x = 0.15 * osc(260 - 30 * t / d, [(1, 1), (2, 0.4)]) * env(len(t), 0.1, 0.8)  # the hoist motor
    for k in range(10):  # chain links clinking
        put(x, damped(rng.uniform(2200, 3800), 0.15, 0.03, 0.3), rng.uniform(0, 1.9))
    put(x, thump(1.0, 70, 30, 0.35), 2.05, 1.6)  # the bus sets down on the halo
    put(x, crack(0.2, 300, 3000, 0.05), 2.05, 0.6)
    return stereo(x, 0.9)


def chainsaw():
    d = 4.0
    t = t_(d)
    put_ = np.zeros(len(t))
    put(put_, thump(0.3, 140, 90, 0.05), 0.0, 0.6)  # picked up off the case: a clunk
    rpm = np.where(t < 1.2, 0, 55 + 110 * np.clip((t - 1.4) / 0.35, 0, 1) - 60 * np.clip((t - 2.4) / 0.4, 0, 1)
                   + 110 * np.clip((t - 2.9) / 0.3, 0, 1))
    pulse = np.sign(np.sin(2 * np.pi * np.cumsum(rpm) / SR)) * (rpm > 0)  # a two-stroke: a buzzing square wave
    saw = bp(pulse, 150, 3500) + 0.3 * bp(noise(d), 1000, 6000) * (rpm > 0)
    return stereo((put_ + 0.7 * saw) * env(len(t), 0.0, 0.3), 0.4)


# ---------------------------------------------------------------- crowds, fire, ambience
def crowd(d=15.0, cheer=True):
    t = t_(d)
    x = bp(noise(d), 250, 2800) * (0.6 + 0.4 * lp(np.abs(noise(d)), 2) * 4)
    for k in range(30):  # individual voices in the mass: formant-filtered bursts
        f0 = rng.uniform(110, 260)
        st, ln = rng.uniform(0, d - 1), rng.uniform(0.3, 1.2)
        v = osc(np.full(int(ln * SR), f0), [(1, 1), (2, 0.6), (3, 0.4), (4, 0.2)])
        v = bp(v, 400, 2500) * env(len(v), 0.1, 0.2)
        put(x, v, st, 0.08)
    if cheer:
        x *= 1 + 0.5 * np.sin(2 * np.pi * t / d)  # a slow swell (and back: it loops)
    return stereo(x, 1.0)


def boo():
    """A crowd booing: many low 'oooo' voices (formants ~300 and ~800 Hz), swelling, with whistles."""
    d = 5.0
    t = t_(d)
    x = np.zeros(len(t))
    for k in range(40):
        f0 = rng.uniform(95, 190)
        st = rng.uniform(0, 1.2)
        ln = rng.uniform(1.5, 3.5)
        n = int(ln * SR)
        vib = f0 * (1 + 0.02 * np.sin(2 * np.pi * rng.uniform(4, 6) * np.arange(n) / SR))
        v = osc(vib, [(1, 1), (2, 0.7), (3, 0.5), (4, 0.3), (5, 0.2)])
        v = bp(v, 220, 420, 2) * 1.0 + bp(v, 650, 900, 2) * 0.35  # the 'oo' vowel
        put(x, v * env(n, 0.3, 0.6), st, rng.uniform(0.4, 1.0))
    for k in range(4):  # whistles
        n = int(0.7 * SR)
        f = 2400 + 600 * np.sin(np.linspace(0, np.pi, n))
        put(x, np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.05, 0.2) * 0.15, rng.uniform(0.5, 3.5))
    x += 0.15 * bp(noise(d), 300, 1500)
    return stereo(x * env(len(t), 0.4, 0.8), 1.0)


def fire(d=10.0):
    t = t_(d)
    roar = lp(noise(d), 500) * (0.7 + 0.3 * lp(np.abs(noise(d)), 3) * 3)
    x = roar * 0.8
    for k in range(int(d * 14)):  # crackles and pops
        put(x, crack(0.02, 1500, 7000, 0.003), rng.uniform(0, d), rng.uniform(0.1, 0.6))
    return stereo(x, 1.0)


def night(d=10.0):
    t = t_(d)
    wind = lp(noise(d), 400) * (0.6 + 0.4 * np.sin(2 * np.pi * t / d))
    far = crowd(d, cheer=False)[:, 0] * 0.15
    far_engine = lp(engine(np.full(len(t), 11000.0), 0.1), 900) * 0.04 * (0.5 + 0.5 * np.sin(2 * np.pi * t / d))
    return stereo(wind + far + far_engine, 1.0)


def climb():
    d = 3.0
    x = np.zeros(int(d * SR))
    put(x, damped(1800, 0.3, 0.05, 0.5) + damped(2600, 0.3, 0.04, 0.3), 0.1)  # hands on the steel rail
    put(x, bp(noise(0.3), 300, 2500) * env(int(0.3 * SR), 0.05, 0.2) * 0.4, 0.35)  # suit scuffing over it
    put(x, thump(0.6, 110, 60, 0.08), 1.6, 1.0)  # boots landing on the asphalt
    put(x, crack(0.08, 600, 3000, 0.02), 1.6, 0.5)
    for k in range(3):
        put(x, thump(0.3, 120, 80, 0.04), 2.1 + 0.32 * k, 0.35)
    return stereo(x, 0.4)


def spotlight():
    d = 3.0
    t = t_(d)
    x = np.zeros(len(t))
    put(x, thump(0.4, 160, 90, 0.04), 0.0, 0.8)  # the clunk of the switch
    put(x, crack(0.05, 800, 5000, 0.008), 0.0, 0.5)
    hum = osc(np.full(len(t), 100.0), [(1, 1), (2, 0.5), (3, 0.3)]) * 0.12 * env(len(t), 0.1, 1.0)
    return stereo(x + hum + 0.5 * boom()[:len(t), 0], 0.6)


def radio():
    d = 2.0
    t = t_(d)
    x = bp(noise(d), 900, 3200) * 0.4 * (t < 0.18)
    x += np.sin(2 * np.pi * 1250 * t) * 0.3 * ((t > 0.2) & (t < 0.32))
    x += bp(noise(d), 600, 2800) * 0.08 * ((t > 0.35) & (t < 1.6))
    return stereo(x * env(len(t), 0.0, 0.2), 0.0)


def whoosh():
    d = 1.0
    t = t_(d)
    x = noise(d)
    out = np.zeros(len(t))
    for k, c in enumerate((400, 900, 1800, 3500)):
        w = np.exp(-((t / d - (k + 0.5) / 4) ** 2) / 0.02)
        out += bp(x, c * 0.7, c * 1.4) * w
    return stereo(out * env(len(t), 0.2, 0.3), 1.0)


for name, fn in (("onboard", onboard), ("passby", passby), ("pack", pack), ("kerb", kerb), ("landing", landing),
                 ("boom", boom), ("barrier", barrier), ("gravel", gravel), ("reveal", reveal), ("press", press),
                 ("crane", crane), ("chainsaw", chainsaw), ("crowd", crowd), ("boo", boo), ("fire", fire),
                 ("night", night), ("climb", climb), ("spotlight", spotlight), ("radio", radio), ("whoosh", whoosh)):
    save(name, fn())
