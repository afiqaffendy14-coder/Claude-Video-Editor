"""Word timings for the fitted narration: ElevenLabs Scribe word times on the original take, moved through
fit_vo.py's time map (pauses shortened, tempo), grouped into the script's lines -> tools/timing.json.
Run: python3 tools/vo_timing.py tools/words_take1.json assets/audio/narrator/v6_take1_60.wav.map.json
"""
import json, re, sys
words = json.load(open(sys.argv[1]))
words = words.get("words", words) if isinstance(words, dict) else words
M = json.load(open(sys.argv[2]))
sr, head, tempo = M["sr"], M["head"], M["tempo"]


def out_time(t):
    s = t * sr - head
    for seg in M["map"]:
        a, b, pos = seg[0], seg[1], seg[2]
        if s < b or seg is M["map"][-1]:
            if len(seg) == 4:  # a pause shortened to `keep` samples
                frac = min(max((s - a) / max(1, b - a), 0), 1)
                return (pos + frac * seg[3]) / sr / tempo
            return (pos + max(0, s - a)) / sr / tempo
    return 0.0


W = [w for w in words if w.get("type", "word") == "word" and not re.fullmatch(r"\[.*\]", w["text"])]
lines = json.load(open("tools/lines.json"))
counts = [len(l.replace("forty-two percent", "42%").split()) for l in lines]
assert sum(counts) == len(W), (sum(counts), len(W))
out, k = [], 0
for i, (text, n) in enumerate(zip(lines, counts)):
    ws = W[k:k + n]
    k += n
    entries = [{"w": w["text"], "start": round(out_time(w["start"]), 3), "end": round(out_time(w["end"]), 3)} for w in ws]
    out.append({"i": i + 1, "text": text, "start": entries[0]["start"], "end": entries[-1]["end"], "words": entries})
json.dump({"duration": 60.0, "lines": out}, open("tools/timing.json", "w"), indent=1)
for l in out:
    print(f'{l["start"]:6.2f}-{l["end"]:6.2f}  {l["text"]}')
