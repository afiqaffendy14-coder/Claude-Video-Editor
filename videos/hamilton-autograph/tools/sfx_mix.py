"""The sound design for the halo short, built on the film's own clocks so every sound lands on its frame.

Sparse on purpose: a sound only where it adds something (the crash, the cars, the crowd booing, the chainsaw, the
press, the bus, the barrier, the fire, the climb, the spotlight, the radio), nothing under the talking shots, and
all of it well under the narrator. Spot effects are placed at the exact event times taken from the animation (the
crash clock tau -> film time, the shot-14 impact, the climb's landing...), impacts aligned by their loudest
transient; slow-motion shots get the same sounds slowed and pitched down; passing cars pan across.

Two libraries, the same mix:
  python tools/sfx_mix.py assets/audio/sfx_src mp3 <out.wav>     (ElevenLabs sound effects)
  python tools/sfx_mix.py assets/audio/sfx_synth wav <out.wav>   (our own, from tools/sfx_synth.py)
"""
import json, os, subprocess, sys
import numpy as np
import soundfile as sf

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC, EXT, out = sys.argv[1], sys.argv[2], sys.argv[3]
DUR = 60.0
N = int(DUR * SR)
mix = np.zeros((N, 2), np.float32)
rng = np.random.default_rng(5)
SHOTS = {s["n"]: (s["start"], s["end"]) for s in json.load(open(os.path.join(ROOT, "boards", "shots.json")))}


def load(name):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(SRC, f"{name}.{EXT}"), "-f", "f32le", "-ac", "2",
                          "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
    return x / max(1e-6, np.abs(x).max())  # peak-normalised; levels are set where each sound is placed


S = {k: load(k) for k in ("onboard", "passby", "kerb", "landing", "gravel", "crowd", "boo", "reveal", "chainsaw",
                          "press", "crane", "pack", "barrier", "fire", "climb", "spotlight", "radio", "boom", "night")}
BED, FX = 1.0, 1.0  # the gains below are the mix (all well under the narrator)


def env_peak(x):
    """Time (s) of the loudest moment (the transient an impact should be aligned on)."""
    e = np.abs(x).mean(axis=1)
    k = int(0.01 * SR)
    e = np.convolve(e, np.ones(k) / k, mode="same")
    return int(np.argmax(e)) / SR


def slow(x, factor):
    """Slow motion: play slower and lower (tape-style), factor < 1."""
    n = int(len(x) / factor)
    t = np.linspace(0, len(x) - 1, n)
    return np.stack([np.interp(t, np.arange(len(x)), x[:, c]) for c in range(2)], axis=1).astype(np.float32)


def fftconv(a, b):
    n = len(a) + len(b) - 1
    m = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(a, m) * np.fft.rfft(b, m), m)[:n]


def reverb(x, size=0.6, wet=0.25):
    """A short room: exponentially decaying noise impulse response (stereo decorrelated), FFT convolution."""
    n = int(size * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal((n, 2)).astype(np.float32) * np.exp(-t * 6.5 / size)[:, None]
    ir[0] = 1.0
    ir /= np.abs(ir).sum(axis=0) ** 0.5
    y = np.stack([fftconv(x[:, c], ir[:, c])[:len(x) + n // 2] for c in range(2)], axis=1)
    out_ = np.zeros_like(y)
    out_[:len(x)] = x * (1 - wet)
    return (out_ + y * wet).astype(np.float32)


def fade(x, fin=0.02, fout=0.05):
    x = x.copy()
    a, b = int(fin * SR), int(fout * SR)
    if a:
        x[:a] *= np.linspace(0, 1, a)[:, None]
    if b:
        x[-b:] *= np.linspace(1, 0, b)[:, None]
    return x


def place(x, t, gain=1.0, pan=0.0, align_peak=False):
    """Add a sound at film time t (or with its loudest transient on t). pan -1 left .. +1 right."""
    if align_peak:
        t -= env_peak(x)
    i = int(round(t * SR))
    gain *= FX
    gl, gr = gain * min(1.0, 1 - pan), gain * min(1.0, 1 + pan)
    a, b = max(0, i), min(N, i + len(x))
    if b > a:
        seg = x[a - i:b - i]
        mix[a:b, 0] += seg[:, 0] * gl
        mix[a:b, 1] += seg[:, 1] * gr


def pan_sweep(x, p0, p1):
    k = np.linspace(p0, p1, len(x))
    y = x.copy()
    y[:, 0] *= np.minimum(1, 1 - k)
    y[:, 1] *= np.minimum(1, 1 + k)
    return y


def bed(name, t0, t1, gain, xf=0.25, process=None):
    """An ambience bed over [t0, t1]: the loop tiled with crossfades, faded in and out at the cuts."""
    x = S[name]
    if process:
        x = process(x)
    n = int((t1 - t0 + 2 * xf) * SR)
    y = np.zeros((n, 2), np.float32)
    pos, off = 0, int(rng.uniform(0, max(1, len(x) - SR)))
    c = int(0.3 * SR)
    while pos < n:
        seg = x[off:]
        off = 0
        if pos > 0:  # each further copy overlaps the last by the crossfade, so it must start c samples back
            pos -= c
        m = min(len(seg), n - pos)
        s = seg[:m].copy()
        if pos > 0:
            k = min(c, m)
            s[:k] *= np.linspace(0, 1, k)[:, None]
            y[pos:pos + k] *= np.linspace(1, 0, k)[:, None]
        y[pos:pos + m] += s
        pos += m
        if m <= c:  # the tail was only crossfade: done
            break
    place(fade(y, xf, xf), t0 - xf, gain * BED / FX)


def T(n, frac=0.0):
    a, b = SHOTS[n]
    return a + (b - a) * frac


# ---------------------------------------------------------------- ambience: only where the place needs it
bed("crowd", T(3), T(4, 1), 0.07)       # Monza's grandstands, faint, under the race shots
bed("crowd", T(25), 60.0, 0.06)
bed("night", T(13), T(14, 1), 0.08)     # a night circuit, faint
bed("fire", T(14, 0.73), T(17, 1), 0.14)  # the fire, from the explosion until he is out

# ---------------------------------------------------------------- the Monza crash (on the crash clock)
SLOW1, RAMP = 0.23, 0.5


def tau_shot1(t):
    if t <= 0:
        return t
    x = min(t, RAMP) / RAMP
    return SLOW1 * min(t, RAMP) + (1 - SLOW1) * RAMP * (x - (x ** 3 - x ** 4 / 2)) + SLOW1 * max(0.0, t - RAMP)


def t_of_tau1(tau):  # film time in shots 1 -> 2 (one slow motion) when the crash clock reads tau
    lo, hi = 0.0, 8.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if tau_shot1(mid) < tau:
            lo = mid
        else:
            hi = mid
    return lo


T_LAND = 0.9
# shot 25 (onboard, real time) -> shot 1 (slowing) -> shot 2 (slow): engine, the kerb strike, the landing
# shot 25 (onboard, real time) -> shot 1 (slowing) -> shot 2 (slow): engine, the kerb strike, the landing
place(fade(S["onboard"][: int(2.4 * SR)], 0.4, 0.05), T(25) - 0.1, 0.22)
place(S["kerb"], 59.92, 0.22, pan=0.4)                                   # the kerb strike, end of the loop
place(fade(slow(S["onboard"][int(2.2 * SR):], 0.55), 0.02, 0.8), 0.0, 0.16)  # into slow motion
place(slow(S["kerb"], 0.4), 0.0, 0.2, pan=0.35)
t_land1 = t_of_tau1(T_LAND)                                             # 3.08 s, early in shot 2
place(S["boom"], t_land1, 0.3, align_peak=True)
place(slow(S["landing"], 0.4), t_land1, 0.22, align_peak=True)

# shot 3: the two cars braking past the stand; shot 4 picks up the same instant, the crash in real time
place(pan_sweep(S["passby"], 0.7, -0.6), T(3) - 0.2, 0.2)
t4 = lambda tau: T(4) + (tau + 0.15)                                    # shot 4: real time from tau -0.15
place(S["kerb"], t4(0.0), 0.22, pan=0.3, align_peak=True)
place(S["landing"], t4(T_LAND), 0.32, align_peak=True)
place(fade(S["gravel"], 0.05, 0.5), t4(1.15), 0.16)
place(S["reveal"], T(6, 0.05), 0.12)                                    # the halo glows, softly

# shot 7: the 2018 car passes (~1 s in), then the booing as we push in on the UGLY signs
place(pan_sweep(S["passby"], -0.8, 0.8), T(7) + 0.4, 0.15)
place(fade(S["boo"], 0.6, 0.6), T(7) + 0.8, 0.26)

# shot 10: the chainsaw revved at the halo; 11: the press under load; 12: the bus setting down on the halo
place(fade(S["chainsaw"], 0.01, 0.4), T(10) + 0.35, 0.18, pan=0.2)
place(fade(S["press"], 0.1, 0.4), T(11) + 0.15, 0.18)
place(reverb(S["crane"], 1.2, 0.3), T(12) + 1.0, 0.24, align_peak=True)

# Bahrain: the pack, the impact and explosion (shot 14, 3.0 s in), the climb out
place(pan_sweep(S["pack"], -0.5, 0.5), T(13) + 0.1, 0.16)
place(S["barrier"], T(14) + 3.0, 0.36, align_peak=True)
place(S["boom"], T(14) + 3.0, 0.2, align_peak=True)
place(S["climb"], T(17) + 0.95, 0.22, align_peak=True)                  # landing after the vault

# shot 19: the trophy - near silence and the spotlight
place(S["spotlight"], T(19) + 0.05, 0.2)

# shot 20: back at Monza, very slow: the tyre comes down (1.54 s in)
t20 = T(20) + (T_LAND - 0.70) / 0.13
place(S["boom"], t20, 0.3, align_peak=True)
place(slow(S["landing"], 0.3), t20, 0.2, align_peak=True)
# shot 23: a team radio click as Wolff listens
place(S["radio"], T(23) + 0.1, 0.12, pan=0.3)

peak = np.abs(mix).max()
if peak > 0.9:  # only guard against clipping; the levels above are the mix
    mix *= 0.9 / peak
sf.write(out, mix, SR, subtype="PCM_16")
print("sfx", out, "peak", round(float(peak), 2))
