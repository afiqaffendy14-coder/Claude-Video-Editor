# Video log

One entry per video, newest first. Short bullets; this is what future sessions read to repeat what works.

<!-- Template
## NN. Title (YYYY-MM-DD) - folder
- Topic / angle:
- Title, thumbnail:
- Decisions (voice take, shots, style changes):
- Worked well:
- Cost time (and the fix for next time):
- Stats (fill in later): views, avg % viewed, likes, subs gained. What to repeat:
-->

## 03. He Was 10. The F1 Boss Wrote Him a Deadline. (2026-11-09) - videos/hamilton-autograph
- **Topic / angle:** 10-year-old Lewis Hamilton asks McLaren boss Ron Dennis for a job; Dennis writes "phone me in
  nine years" in his autograph book. The boy stays anonymous (no 44, no helmet) until "Lewis Hamilton" is the last word.
- **Title, thumbnail:** title and thumbnail never name him or show the grown driver; thumbnail = young Hamilton with
  the boss (`blender/thumb_pair.py`). Kit in `videos/hamilton-autograph/posting/`.
- **Decisions:**
  - script v6 (`scripts/f1-hamilton-autograph.md`), "rollercoaster" story shape (`scripts/story-formats.md`);
  - VO take 1, pauses capped at 0.18 s with a 0.5 s beat before the reveal; film 49.67 s, NO loop, hard cut on the name;
  - 22 shots; first frame is the hook (boy looking up at the boss) with a Minecraft-style tooltip title at the top;
  - real recorded SFX only (Mixkit free licence), the owner rejected ElevenLabs and synthesised sounds;
  - final mix -14 LUFS (owner couldn't hear the voice in the car at lower levels);
  - a real CC BY photo of Hamilton fades in on the name (credit in the description).
- **Worked well:** library kart and cars (`library/`) instead of per-video models; extra liveries added at run time;
  a storyboard rebuilt from each preview's own frames (`tools/board_from_video.py`) for batched notes.
- **Cost time (and the fix for next time):**
  - round 2 changed framings the owner already liked ("a downgrade"). Fix: only change what a note asks for.
  - hand/tool contact (hammer, plate, book) took rounds. Fix: rigid tool angle to the forearm, check views + CHECK=1.
  - a VO word got swallowed under a cut. Fix: `tools/shift_after.py` inserts frames and shifts everything after.
- **Files:** finished film `out/hamilton-final.mp4` (+ phone copy), laptop only.
- **Stats:** (fill in after posting)

## 02. Toto Wolff Wanted to Chainsaw This Off. It Saved Hamilton's Life (2026-11) - videos/halo
- **Topic / angle:** the halo: hated when it arrived in 2018 (Wolff: "If you give me a chainsaw, I would take it off"),
  then it shielded Grosjean (Bahrain 2020) and pushed Verstappen's tyre off Hamilton's helmet (Monza 2021).
- **Title, thumbnail:** the title is a statement, not a question; the hook line is "Imagine a Formula One car landing on
  your head" (owner picked it from four options). Thumbnail: a dedicated render of Grosjean's car in the torn barrier,
  red halo, "THIS SAVED F1 DRIVERS' LIVES" with an arrow. Kit in `videos/halo/posting/`.
- **Decisions:**
  - script v2 (`scripts/f1-halo.md`); "saved his life" only in the words of the people involved, never the narrator's;
  - ElevenLabs "F1 Narrator", take 2, pauses capped at ~0.18 s, exactly 60.0 s;
  - 24 shots; red halo as the film's only accent colour; generic cars by colour, no logos;
  - ElevenLabs sound effects mixed by `tools/sfx_mix.py` (instead of video 1's synthesised SFX).
- **Worked well:** one continuous physical crash clock (real arc, roll, rebound, slide to a stop) that every crash shot
  samples; shot 6 opening on shot 5's last frame; moving crowd cards; `look.py` + `finish.py` for the final look.
- **Cost time (and the fix for next time):**
  - storyboard v1 too plain: the owner asked for much more detail and to show how things happen. Fix: the
    "Owner's notes from video 2" in `CLAUDE.md`, applied from storyboard v1.
  - several animation test rounds (v1-v3) before the final. Fix: lock poses/physics with `check.py`, `ik.py` and
    `validate.py` before any test render.
- **Files:** finished film `out/halo-final.mp4` (and an alternative voice version B), kept on the laptop only; the
  original working folder with every frame is the old zip copy, `Downloads\f1 video\Claude-Video-Editor\videos\halo`.
- **Stats:** (fill in after posting)

## 01. Why Did Surgeons Call Ferrari? 🏎️❤️ (2026-11) - videos/pitstop-hospital
- **Topic / angle:** Great Ormond Street Hospital redesigned post-surgery handovers with Ferrari's pit crew
  (errors -42%, omissions -49%; Catchpole et al. 2007). Broad audience; human story via F1.
- **Title, thumbnail:** question hook = first VO line. Thumbnail: surgeon on top, pit stop below, title across the seam.
- **Decisions:**
  - script v6 (no "then"/"next");
  - VO take 1 fitted to 60 s;
  - 35 shots, hard cuts on words, captions at 74% height;
  - loop: shot 35 flows into shot 1.
- **Worked well:**
  - surgeon open/close loop;
  - top-down pit stop and ICU shots;
  - the close-up insert of the line unplugging (much clearer than a wide shot);
  - corridor sprint with handheld shake.
- **Cost time (and the fix for next time):**
  - the pit stop with ~20 crew: short arms and crowding meant many staging passes. Fix: solve stations from hold
    points, give props handles, fewer people.
  - cameras placed behind people's heads. Fix: check lens-to-subject is clear before animating.
  - CPU-only cloud renders. Fix: preview and render on the laptop GPU.
  - one-second glitch in the final (likely a broken frame). `go.bat` now auto-repairs broken frames.
- **Stats:** (fill in after posting)
