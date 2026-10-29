"""Trim each voice line to its speech and butt-join them into one continuous assets/audio/vo.wav.

Writes tools/timing.json: each line's start/end in the joined file and per-word start times
(spread by letter count, with a beat after punctuation). Gap between lines is GAP seconds.
Run: ../../.venv-audio/bin/python tools/join_vo.py [speed]
"""
import json, os, re, sys
import numpy as np, soundfile as sf

HERE = os.path.dirname(__file__)
GAP = 0.03
lines = json.load(open(os.path.join(HERE, "lines.json")))
out, timing, t = [], [], 0.0
SR = None
for i, text in enumerate(lines):
    y, SR = sf.read(os.path.join(HERE, "..", "assets", "audio", "raw", f"l{i+1:02d}.wav"))
    if y.ndim > 1: y = y.mean(axis=1)
    thr = 10 ** (-40 / 20) * np.max(np.abs(y))
    idx = np.where(np.abs(y) > thr)[0]
    a, b = max(0, idx[0] - int(0.015 * SR)), min(len(y), idx[-1] + int(0.03 * SR))
    seg = y[a:b]
    fade = int(0.006 * SR); seg[:fade] *= np.linspace(0, 1, fade); seg[-fade:] *= np.linspace(1, 0, fade)
    words = text.split()
    # spoken length: letters, plus extra for numbers read as words ("1976" = nineteen seventy-six)
    weight = lambda w: len(re.sub(r"[^A-Za-z0-9'ü]", "", w)) + (14 if re.search(r"\d", w) else 0) + 1.5 + (2.5 if re.search(r"[,.…]$", w) else 0)
    tot, acc, wt = sum(weight(w) for w in words), 0, []
    dur = len(seg) / SR
    for w in words:
        wt.append({"w": w, "start": round(t + acc / tot * dur, 3)}); acc += weight(w)
    timing.append({"i": i + 1, "text": text, "start": round(t, 3), "end": round(t + dur, 3), "words": wt})
    out += [seg, np.zeros(int(GAP * SR))]
    t += dur + GAP
vo = np.concatenate(out)
vo = vo / np.max(np.abs(vo)) * 10 ** (-1.5 / 20)
sf.write(os.path.join(HERE, "..", "assets", "audio", "vo.wav"), vo.astype(np.float32), SR, subtype="PCM_16")
json.dump({"duration": round(t, 3), "lines": timing}, open(os.path.join(HERE, "timing.json"), "w"), indent=1)
for l in timing: print(f'{l["start"]:6.2f}-{l["end"]:6.2f}  {l["text"]}')
print("total speech", round(t, 2))
