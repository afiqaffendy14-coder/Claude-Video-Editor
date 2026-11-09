"""Sound effects for "Phone me in nine years": real recordings from Mixkit (assets/audio/sfx_mixkit, Sound Effects
Free License: fine for YouTube, no credit needed; SOURCES.json lists each item). No synthesised or AI sounds.

Sparse and quiet: a sound only where the picture has it (the ballroom, the pen, the clock, the sanding, the three
jobs, the paddock, the karts, the cheers, the rain and the F1 cars). Each sound is placed at its frame (the pen on
each written word, the sledgehammer on each hit), set to a quiet RMS level and ducked under the voice.

Run: ../../.venv-audio/Scripts/python tools/sfx_mix_ham.py assets/audio/sfx_mix.wav
"""
import json, os, subprocess, sys
import numpy as np
import soundfile as sf

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "assets", "audio", "sfx_mixkit")
END = 49.5 + 5 / 30
SHIFT_AT, SHIFT = 16.95, 5 / 30  # round 5: 5 frames of air before "At the track"
N = int(END * SR)
mix = np.zeros((N, 2), np.float32)
WORDS = [w for l in json.load(open(os.path.join(HERE, "timing.json"), encoding="utf-8"))["lines"] for w in l["words"]]


def word(text, after=0.0):
    return next(w["start"] for w in WORDS if w["start"] >= after and w["w"].lower().strip(".,:!?\"") == text)


def load(name):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(SRC, f"{name}.mp3"), "-f", "f32le", "-ac", "2",
                          "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


S = {}


def snd(name):
    if name not in S:
        S[name] = load(name)
    return S[name]


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)


def lowpass(x, hz):
    a = np.exp(-2 * np.pi * hz / SR)
    y = np.zeros_like(x)
    acc = np.zeros(2, np.float32)
    for i in range(len(x)):  # one pole, fine for these short clips
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def lowpass_fast(x, hz):
    """One-pole low-pass via FFT on long beds."""
    f = np.fft.rfftfreq(len(x), 1 / SR)
    h = 1 / np.sqrt(1 + (f / hz) ** 2)
    return np.stack([np.fft.irfft(np.fft.rfft(x[:, c]) * h, len(x)) for c in range(2)], 1).astype(np.float32)


def highpass_fast(x, hz):
    f = np.fft.rfftfreq(len(x), 1 / SR)
    h = (f / hz) / np.sqrt(1 + (f / hz) ** 2)
    return np.stack([np.fft.irfft(np.fft.rfft(x[:, c]) * h, len(x)) for c in range(2)], 1).astype(np.float32)


def place(name, t0, level, dur=None, src_at=0.0, fade_in=0.05, fade_out=0.15, pan=0.0, lp=None, hp=None, rate=1.0,
          active=None):
    """Put a sound at film time t0 at an RMS level (dBFS, measured over its active part), looped to fill dur."""
    x = snd(name)
    if rate != 1.0:  # play faster/slower (pitch moves with it)
        idx = np.arange(0, len(x) - 1, rate)
        x = np.stack([np.interp(idx, np.arange(len(x)), x[:, c]) for c in range(2)], 1).astype(np.float32)
    a = int(src_at * SR)
    x = x[a:]
    n = int((dur if dur else len(x) / SR) * SR)
    if n > len(x):
        x = np.concatenate([x] * (n // len(x) + 1))
    x = x[:n].copy()
    if lp:
        x = lowpass_fast(x, lp)
    if hp:
        x = highpass_fast(x, hp)
    loud = x if active is None else x[: int(active * SR)]
    x *= 10 ** ((level - rms_db(loud[np.abs(loud).max(1) > 1e-4] if len(loud) else loud)) / 20)
    fi, fo = int(fade_in * SR), int(fade_out * SR)
    env = np.ones(n, np.float32)
    if fi:
        env[:fi] = np.linspace(0, 1, fi)
    if fo:
        env[-fo:] = np.minimum(env[-fo:], np.linspace(1, 0, fo))
    x *= env[:, None]
    if pan:
        x[:, 0] *= np.sqrt(0.5 * (1 - pan)) * np.sqrt(2)
        x[:, 1] *= np.sqrt(0.5 * (1 + pan)) * np.sqrt(2)
    s = int((t0 + (SHIFT if t0 >= SHIFT_AT else 0.0)) * SR)
    e = min(N, s + n)
    if e > s:
        mix[s:e] += x[: e - s]


# ---------------------------------------------------------------- 1-3: the awards dinner
place("ballroom", 0.0, -38, dur=8.12, src_at=20.0, fade_in=0.0, fade_out=0.6, lp=5000)
place("glass", 1.1, -36, pan=-0.4)
for w in ("phone", "me", "in", "nine", "years"):  # the pen on each written word
    place("pen", word(w, 6.0) - 0.02, -30, dur=0.32, fade_out=0.08)
place("sign_fast", word("years", 6.0) + 0.3, -31, dur=0.55, fade_out=0.12)
# ---------------------------------------------------------------- 4: the kitchen at night
place("clock", 8.12, -37, dur=2.43, fade_in=0.1, fade_out=0.2)
# ---------------------------------------------------------------- 5-6: the shed
place("room_wind", 10.55, -42, dur=3.9, fade_in=0.2, fade_out=0.3, lp=2500)
for i, t in enumerate((12.3, 13.08)):  # the spanner on the wheel nut, one pull each
    place("wrench", t, -33, dur=0.45, src_at=0.4 + 1.1 * i, fade_in=0.02, fade_out=0.12)
# ---------------------------------------------------------------- 7: three jobs at once
place("typing", 14.45, -38, dur=2.62, src_at=3.0, fade_in=0.1, fade_out=0.2, pan=-0.15)
for n in range(3):  # the hammer hits, on the frames where it lands (ham_anim.S07b: 0.3 s, then every 0.8 s)
    t = 14.45 + 0.3 + n * 0.8
    place("hammer_wood", t, -29, fade_in=0.0, fade_out=0.1)
    place("wood_hit", t, -33, fade_in=0.0, fade_out=0.1)
place("sink", 14.45, -38, dur=2.62, src_at=1.0, fade_in=0.15, fade_out=0.3, pan=0.15)
place("plate", 15.9, -36, pan=0.15)
# ---------------------------------------------------------------- 8-11: the paddock (karts out on the track)
place("breeze", 17.07, -40, dur=11.8, fade_in=0.3, fade_out=0.3)
place("kart_idle", 17.07, -40, dur=11.8, fade_in=0.4, fade_out=0.2, lp=1400)
# ---------------------------------------------------------------- 12-15: racing, winning
place("kart_idle", 28.87, -31, dur=1.7, src_at=5.0, fade_in=0.05, fade_out=0.15)
place("kart_launch", 28.95, -26, dur=1.6, fade_in=0.02, fade_out=0.2)
place("kart_pass", 30.4, -26, dur=0.9, src_at=2.6, fade_in=0.05, fade_out=0.25, pan=0.3)
place("crowd_small", 30.6, -32, dur=1.4, fade_out=0.4)
place("cheer_small", 31.18, -31, dur=0.9, src_at=0.5, fade_in=0.05, fade_out=0.25)
# ---------------------------------------------------------------- 16: signed
place("signing", 33.1, -31, dur=1.0, fade_out=0.2)
# ---------------------------------------------------------------- 17-20: Brazil 2008, rain
place("rain", 35.31, -31, dur=9.8, src_at=10.0, fade_in=0.15, fade_out=0.3)
place("f1_engine", 35.31, -29, dur=4.8, fade_in=0.1, fade_out=0.3, hp=250)
place("car_by", 38.6, -25, fade_in=0.02, fade_out=0.4, pan=-0.2)
place("f1_engine", 40.08, -30, dur=1.3, src_at=2.0, fade_in=0.05, fade_out=0.4, hp=250)
place("crowd_victory", 40.5, -29, dur=0.95, src_at=0.3, fade_in=0.1, fade_out=0.15)
place("male_cheer", 41.41, -27, dur=1.63, fade_in=0.02, fade_out=0.3)
place("cheer_small", 41.5, -31, dur=1.5, src_at=1.0, fade_out=0.3)
place("rain_roof", 43.04, -34, dur=2.06, src_at=5.0, fade_in=0.1, fade_out=0.2)
# ---------------------------------------------------------------- 21: the shed again
place("room_wind", 45.1, -42, dur=1.18, src_at=6.0, fade_in=0.1, fade_out=0.2, lp=2500)
# ---------------------------------------------------------------- 22: off with the helmet, rain fades as the photo comes in
place("rain", 46.28, -33, dur=2.4, src_at=40.0, fade_in=0.1, fade_out=1.0)

# ---------------------------------------------------------------- duck under the voice
vo, sr = sf.read(os.path.join(ROOT, "assets", "audio", "narrator", "vo.wav"), dtype="float32")
if vo.ndim > 1:
    vo = vo.mean(1)
if sr != SR:
    vo = np.interp(np.arange(0, len(vo), sr / SR), np.arange(len(vo)), vo).astype(np.float32)
vo = np.pad(vo, (0, max(0, N - len(vo))))[:N]
k = int(0.05 * SR)
env = np.sqrt(np.convolve(vo ** 2, np.ones(k) / k, mode="same"))
talk = np.clip((20 * np.log10(env + 1e-9) + 45) / 15, 0, 1)        # 0 = silence, 1 = speaking
sm = int(0.12 * SR)
talk = np.convolve(talk, np.ones(sm) / sm, mode="same")
mix *= (10 ** (-6 * talk / 20))[:, None]                          # up to 6 dB down while he speaks
peak = np.abs(mix).max()
if peak > 0.5:
    mix *= 0.5 / peak
sf.write(sys.argv[1], mix, SR, subtype="FLOAT")
print("sfx", sys.argv[1], f"{END}s", f"RMS {rms_db(mix):.1f} dBFS", f"peak {20 * np.log10(np.abs(mix).max()):.1f} dBFS")
