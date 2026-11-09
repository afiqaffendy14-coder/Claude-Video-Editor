# Brief: "Phone me in nine years" (Lewis Hamilton) — animation

The script is LOCKED. Use the **FINAL (v6)** section of `../../scripts/f1-hamilton-autograph.md` and don't change
the wording. The facts, sources and reveal notes are in the same file.

## Setup
- Read `../halo/HANDOFF.md` and `../LIBRARY.md` first (use the dreamy-gauss copy if one is missing).
- Copy and adapt the halo pipeline: `blender/look.py`, `tools/finish.py`, `tools/captions.mjs`, `tools/sfx_mix.py`,
  `tools/sfx_synth.py`, `tools/thumb.mjs`, `tools/vo_timing.py`.
- Import cars from `../../library/cars/f1_2026/` (`car_blender.load_car`). Never model cars in this folder.

## Voiceover
- ElevenLabs "F1 Narrator" (`T6dmRMFpaA2PwnRdtyjv`, eleven_v4). Both takes are already saved as
  `assets/audio/narrator/take1.mp3` and `take2.mp3` (about 58.6 s each, raw; ElevenLabs flow `NkjgAmgXwWK962b76Jcl`).
  Ask the owner which take they chose. Each take has about 10.7 s of pause above 0.18 s: trim most of it, but
  keep a slightly longer beat before the final reveal line.
- Cap pauses at about 0.18 s with no tempo change. Make Scribe word timings so captions use the script's British
  spelling.
- Until the take is chosen, do the work that doesn't depend on timing: shot list, sets, characters and poses.

## Stages
Show the owner one whole stage at a time and take notes in one batch:
1. Numbered storyboard and shot list (about 15–20 shots, cut on the voiceover's word starts).
2. Animation test.
3. Lighting and grade.
4. Final render.
5. Sound: two versions, ElevenLabs and synthesised effects. ElevenLabs is the lead.
6. Title, description and thumbnail.

Done means a 1080x1920 30 fps phone-safe MP4 under 30 MiB, plus the posting kit.

## Rules for this video
- **No loop.** End on the name reveal and cut hard. The first and last shots do NOT match.
- **The boy stays anonymous until the last line.** No number 44 and no signature helmet before the final shot. The
  final shot is the grown driver taking off his helmet as "Lewis Hamilton" is spoken, then cut.
- **The title and thumbnail must not show his name or face.** Ideas: the title "He Was 10. The F1 Boss Wrote Him a
  Deadline." and a thumbnail of the autograph page with "PHONE ME IN 9 YEARS" in handwriting.
- **The first 3 seconds carry the hook** (this channel loses viewers early). The first frame is the tiny block boy
  looking up at the towering boss, holding out the autograph book. Add a big on-screen "AGE 10" text separate from
  the captions, start the audio on frame 0, and use no establishing shot or slow push-in.
- **The racism beat is restrained.** Tell it in his own words, with nothing staged beyond, say, a crowd turned away
  from him and the boy hiding tears. No caricature.
- "Again, and again, and again" is a quick trophy and finish-line montage. The 2008 climax is the pass two corners
  from the end in the rain, then the title by one point.
- The usual house-style corrections apply: no clipping, natural hands and elbows, motion that carries on, dark and
  moody indoor and night scenes, clear crowd signs, and quiet, fitting sound effects.
