"""Fit a narration take to an exact length by shortening its pauses (never the words).

Pauses longer than a cap are cut down to the cap; the cap is searched so the take lands on TARGET seconds.
Pauses already short stay as they are, so the delivery keeps its rhythm. If even the shortest allowed pauses
leave it too long, the remainder is taken up with a gentle pitch-preserving tempo change (ffmpeg atempo).
Run: ../../.venv-audio/bin/python tools/fit_vo.py in.wav out.wav [target=59.95] [floor=0.14]
With a small floor (e.g. 0.08) every pause becomes a breath, and tempo takes up the difference to the target.
"""
import subprocess, sys
import numpy as np, soundfile as sf

src, dst = sys.argv[1], sys.argv[2]
TARGET = float(sys.argv[3]) if len(sys.argv) > 3 else 59.95
FLOOR = float(sys.argv[4]) if len(sys.argv) > 4 else 0.14  # shortest pause we allow between phrases
y, sr = sf.read(src)
if y.ndim > 1:
    y = y.mean(axis=1)
win = int(0.01 * sr)
env = np.sqrt(np.convolve(y ** 2, np.ones(win) / win, mode="same"))
loud = env > 10 ** (-38 / 20) * env.max()
idx = np.where(loud)[0]
y = y[max(0, idx[0] - int(0.02 * sr)): idx[-1] + int(0.06 * sr)]
loud = loud[max(0, idx[0] - int(0.02 * sr)): idx[-1] + int(0.06 * sr)]
# runs of silence at least 0.1 s long
runs, i, n = [], 0, len(loud)
while i < n:
    if not loud[i]:
        j = i
        while j < n and not loud[j]:
            j += 1
        if j - i >= int(0.1 * sr):
            runs.append((i, j))
        i = j
    else:
        i += 1
speech = len(y) / sr - sum((b - a) / sr for a, b in runs)
length = lambda cap: speech + sum(min((b - a) / sr, cap) for a, b in runs)
lo, hi = FLOOR, 2.0
if len(sys.argv) > 4 or length(lo) > TARGET:  # floor given: every pause cut to a breath, no search
    cap = lo
else:
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if length(mid) < TARGET else (lo, mid)
    cap = (lo + hi) / 2
out, prev = [], 0
fade = int(0.008 * sr)
for a, b in runs:
    out.append(y[prev:a])
    keep = int(min((b - a) / sr, cap) * sr)
    mid_ = (a + b) // 2
    seg = np.concatenate([y[a:a + keep // 2], y[b - (keep - keep // 2):b]])
    if len(seg) > 2 * fade:
        seg[keep // 2 - fade:keep // 2 + fade] *= np.concatenate([np.linspace(1, 0, fade), np.linspace(0, 1, fade)])
    out.append(seg)
    prev = b
out.append(y[prev:])
z = np.concatenate(out)
tmp = dst + ".tmp.wav"
sf.write(tmp, z, sr, subtype="PCM_16")
dur = len(z) / sr
tempo = dur / TARGET if abs(dur - TARGET) > 0.01 else 1.0  # gentle either way; words keep their pitch
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af", f"atempo={tempo:.5f},loudnorm=I=-16:TP=-1.5:LRA=7", "-ar", str(sr), dst], check=True)
print(f"pauses capped at {cap:.3f}s, {len(runs)} pauses, speech {speech:.2f}s, before tempo {dur:.2f}s, tempo x{tempo:.3f}")
