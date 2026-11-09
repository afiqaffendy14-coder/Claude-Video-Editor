"""Cap the narration's pauses (never the words), no tempo change.

Every pause longer than CAP is cut to CAP. Pauses that start after `--beat-after` seconds in the source (the
pause before the reveal line) keep up to BEAT instead. Writes the same time map as fit_vo.py, so vo_timing.py
can move Scribe's word timings across.
Run: ../../.venv-audio/Scripts/python tools/cap_vo.py in.mp3 out.wav [cap=0.18] [beat_src_time=-1] [beat=0.45]
"""
import json, subprocess, sys
import numpy as np, soundfile as sf

src, dst = sys.argv[1], sys.argv[2]
CAP = float(sys.argv[3]) if len(sys.argv) > 3 else 0.18
BEAT_AT = float(sys.argv[4]) if len(sys.argv) > 4 else -1.0  # source time (s) inside the pause that gets the beat
BEAT = float(sys.argv[5]) if len(sys.argv) > 5 else 0.45

tmpin = dst + ".src.wav"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-ac", "1", tmpin], check=True)
y, sr = sf.read(tmpin)
win = int(0.01 * sr)
env = np.sqrt(np.convolve(y ** 2, np.ones(win) / win, mode="same"))
loud = env > 10 ** (-38 / 20) * env.max()
idx = np.where(loud)[0]
head = max(0, idx[0] - int(0.02 * sr))  # audio starts on frame 0: only 20 ms of lead-in
tail = min(len(y), idx[-1] + int(0.06 * sr))
y, loud = y[head:tail], loud[head:tail]
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
out, prev, tmap, pos = [], 0, [], 0
fade = int(0.008 * sr)
for a, b in runs:
    out.append(y[prev:a]); tmap.append((prev, a, pos)); pos += a - prev
    is_beat = BEAT_AT >= 0 and (a + head) / sr <= BEAT_AT <= (b + head) / sr
    keep = int(min((b - a) / sr, BEAT if is_beat else CAP) * sr)
    tmap.append((a, b, pos, keep)); pos += keep
    seg = np.concatenate([y[a:a + keep // 2], y[b - (keep - keep // 2):b]])
    if len(seg) > 2 * fade:
        seg[keep // 2 - fade:keep // 2 + fade] *= np.concatenate([np.linspace(1, 0, fade), np.linspace(0, 1, fade)])
    out.append(seg); prev = b
out.append(y[prev:]); tmap.append((prev, len(y), pos))
z = np.concatenate(out)
tmp = dst + ".tmp.wav"
sf.write(tmp, z, sr, subtype="PCM_16")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af", "loudnorm=I=-16:TP=-1.5:LRA=7", "-ar", str(sr), dst], check=True)
json.dump({"sr": sr, "head": int(head), "tempo": 1.0, "map": [[int(v) for v in t] for t in tmap]}, open(dst + ".map.json", "w"))
print(f"{len(runs)} pauses capped at {CAP}s (beat {BEAT}s at src {BEAT_AT}s); {len(y)/sr:.2f}s -> {len(z)/sr:.2f}s")
