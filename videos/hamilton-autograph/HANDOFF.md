# Handoff: "Phone me in nine years" (Lewis Hamilton autograph short)

Brief: `BRIEF.md`. Script (locked, v6): `../../scripts/f1-hamilton-autograph.md`. Pipeline copied from `../halo`
(read `../halo/HANDOFF.md`); this folder's own additions are listed below.

## Decisions the owner has made
- Voiceover: **take 1** (`assets/audio/narrator/take1.mp3`, ElevenLabs flow `NkjgAmgXwWK962b76Jcl`).

## Voiceover and timing
- `tools/cap_vo.py`: pauses capped at 0.18 s, a 0.5 s beat before the reveal line, no tempo change →
  `assets/audio/narrator/vo.wav` (48.10 s, loudness −16 LUFS) plus its `.map.json`.
  `../../.venv-audio/Scripts/python tools/cap_vo.py assets/audio/narrator/take1.mp3 assets/audio/narrator/vo.wav 0.18 54.8 0.5`
- Scribe words: `tools/words_take1.json`. `tools/vo_timing.py` moves them through the map onto the script's own
  words (`tools/lines.json`, British spelling; Scribe's "fifth" + "hand" merged) → `tools/timing.json`.
- Film length 48.30 s (hard cut 0.28 s after "Hamilton.").

## Storyboard (stage 1)
- `blender/ham_sets.py`: sets (awards ballroom, kitchen, shed, office job, street at dusk, kart track and podium,
  trophy shelf, boss's office, Brazil 2008 in the rain, pit wall), props (red autograph book with written page
  textures, box-built go-kart, trophy, chequered flag, rain), people helpers (`seated`, `allow`, `kart_driver`,
  `car_driver`). Library cars via `car()`; 2008-inspired liveries `chrome08` and `blanco08` are added to the
  blueprint's LIVERIES at run time (the library files are untouched).
- `blender/ham_shots.py`: the 22 shots. `blender -b --factory-startup --python blender/ham_shots.py -- board [ids]`,
  then `-- json`, then `.venv-tools/Scripts/python tools/board_prep.py` (stacks shot 7's panels, grades) and
  `node boards/build.mjs` → `boards/storyboard-v1-1.png`, `-2.png`. Shot list: `boards/shot-list.md`.
- `tools/make_tex.py`: autograph page stages (`page_0`–`page_6`), clocks, chequered flag, contract, bills.
- Edits to shared copies in this folder: `voxel.py` (formal shirt and tie, hi-vis vest, chest panel, `head_k` for
  children), `people.py` (this film's outfits), `lib.py` (palette), `halo_sets.person_at` (logs `REACH` and keeps
  the closest pose instead of stopping), `check.py` (registered contact between two people is allowed).

## Owner's notes on storyboard v1 (applied in the animation test)
- Loved the composition, colour and shading, including the dark scenes; only the too-dark shots get lifted (not
  too bright, not too dark): per-shot exposure in `ham_anim.EXPO` (shots 1, 2, 5, 6, 7c, 21 up; 19b down).
- Shot 1: no lower captions; a title box at the top: "How a 10-year-old Black boy asked an F1 boss for a job"
  (the owner wrote "Ferrari boss": Dennis ran McLaren, so the box says "an F1 boss", like the script).
- Shot 3: no captions (the page shows the words). Ages: a small "(age 13)" / "(age 23)" line under the caption,
  no big stamps. All in `tools/captions.mjs`.
- Shot 17 looked empty: Interlagos now has stands on both sides, boards, fences, light poles, marshal posts, TV
  towers, a footbridge, hills and São Paulo's towers; light rain spray (droplets) behind the cars.

## Animation test (stage 2)
- `blender/ham_anim.py`: every shot as parts (static set built once + a frame function). People are rebuilt each
  frame in poses that move with time (`alive`, `mixpose`, IK); karts, cars, book, trophy, flag, rain and camera
  move. `blender -b --factory-startup --python blender/ham_anim.py -- out/frames_test [ids]` (Cycles, 16 samples,
  540x960; `STEP=n` for a quick look, `CHECK=1` writes `out/anim_check.json`). About 3.5 s a frame.
- `tools/compose_test.py out/frames_test assets/captions_1080 out/hamilton-animation-test.mp4` stacks shot 7's
  panels, grades, scales to 1080x1920, adds the overlays and the voiceover (+ a phone copy).

- Every preview goes out with a storyboard made from its own frames, plus `boards/shot-list.md`:
  `python tools/board_from_video.py out/<video>.mp4 boards/shots_v2.json boards/v2`, then
  `VER=v2 IMG=v2 BURNED=1 NOTE="..." node boards/build.mjs` → `boards/storyboard-v2-1.png`, `-2.png`.
  Use the next version number (v3 for the lighting pass, and so on) with its own `shots_vN.json`.

## Owner's notes on the animation test (round 2), applied
- Karts: `ham_sets.kart()` loads the library kart (`library/cars/kart`, `kart_blender.load_kart`) at cadet size
  `KART_S = 0.8`. "battered" = livery `fifth_hand` (comes battered); "new" = `fifth_hand` with condition new (his
  dad's fix-up); other kids pass `livery=` (`ham_anim.LIVERY`: kid_red→rosso, kid_green→silver_arrow,
  kid_grey→midnight, kid_yellowsuit→papaya). `kart_roll` drives the rig's round wheels; `kart_driver` seats a kid
  from `kart_blueprint.HIP/SEAT`. In the shed the kart sits on a kart stand (`KART_STAND`). Kart shots are wider.
- Shot 1: two moving clips cut on "Formula" (1.76 s): 1a the hook framing with the camera arcing in, the boy on
  tiptoe; 1b from behind the boy, looking up past the book at the boss reaching for it. Title: a Minecraft-style
  tooltip box with a hand-drawn 5x7 pixel font, "A 10-year-old Black boy asked an F1 boss for a job." ("F1 boss" in
  gold), top at 12.5 %, bottom at 27.4 % (heads below). `tools/title_mc.py` overwrites captions.mjs's title.png.
- Shot 4: he rubs one eye with the heel of his hand (`head_point` finds a point in front of a person's face).
- Shot 7b: an estate agent's FOR SALE board knocked into a front lawn with a mallet (`street_job_set`, `POST`,
  `mallet()`, `assets/tex/forsale.png` from `tools/make_forsale.py`). 7c: scrubbing plates at a restaurant sink at
  23:00 (`dish_job_set`, `plate()`, `sponge()`, outfit `dad_apron`), seen from over the sink. Sources: Wikipedia
  "Anthony Hamilton (racing manager)" (up to four jobs, including double-glazing sales, washing dishes and putting
  up estate agents' boards).
- Shot 9: the kids and parents turn away and walk off one by one. Shot 10: closer, lighter (`s10_face` light),
  tears (pose `tears`, drawn in `voxel.py`), then the wipe. Shot 11: the dad turned 45° to camera, mouth moving.
  Shot 16b: they face each other, bodies turned toward camera. Shot 20: fist pumped in front of the chest, lit
  (`pw_fist`). Captions: no age labels.
- Ending: from "Hamilton" (47.56 s) a real photo fades in over 0.5 s and holds to 49.50 s (`tools/compose_test.py`:
  9:16 crop at x 52 %, slow push). Photo: `assets/photo/hamilton_2008_rickman.jpg`, CC BY 2.0, Alistair Rickman,
  5 Nov 2008. The credit (`assets/photo/CREDIT.txt`) must go in the description.

## Owner's notes on round 2 (round 3), applied
- Round 2 was "a downgrade" in places: shots 5, 6, 9, 10 and 21 are back to the round-1 framing and look (shot 10
  keeps the first animation, with a soft key `s10_face` at 22 W between too dark and too bright, and tears).
- Title: "a F1 boss" (as the voiceover says "a Formula One boss"), gold border. Shot 1a: over the boss's shoulder,
  panning onto the boy in the middle of the frame; 1b: the side view.
- Shot 7b: a full overhead sledgehammer swing (`POST_TOP`, `MALLET_L`), the post sinks a little per hit, wood chips,
  no clipping. 7c: scrubbing a plate under the running tap (`dj_stream`, suds), no clipping.
- Karts: `KART_S = 0.92` (cadet size); shot 8's karts face the kids; shot 11's kart is parked well back. Shot 16b:
  a normal handshake distance. Shot 17: the cars a car's width apart.
- Sound: real recordings only (the owner doesn't want ElevenLabs or synthesised sounds): Mixkit Sound Effects Free
  License (YouTube OK, no credit needed), `assets/audio/sfx_mixkit` + `SOURCES.json`, mixed by
  `tools/sfx_mix_ham.py` → `assets/audio/sfx_mix.wav` (about -30 LUFS, ducked under the voice).
  `SFX=assets/audio/sfx_mix.wav python tools/compose_test.py ...` mixes it in (+3 dB, limiter).

## Owner's notes on round 3 (round 4), applied
- 1a: `EXPO_PART["1a"] = 0.35` and a dimmer `aw_lift2` (the boy's skin read far too light); his hands hold the book
  by its edges (his forearm went through it).
- 6a: the dad tightens the rear wheel nut with a spanner (`A.spanner`, the kart's `sh_kart_wheel_RR` hub).
- 7b: a claw hammer (`A.hammer`) rigid in his right hand: the hand moves on an arc around his right shoulder (in the
  post's plane), the hammer keeps a fixed angle to the forearm (`ctx["ham_alpha"]`, set at the impact pose), five
  phases every 0.8 s, the face lands on the post top (`POST_TOP = 0.893`), the post never moves. `HAMCAM=front|q`
  renders the check views; CHECK=1 reports no clipping.
- 9: they start facing the boy, turn round one by one (0.7 s) and walk off slowly at a speed matched to their steps;
  the boy and camera stay still. 10: hiding tears (glance, eyes shut via pose `eyes_closed`, turn away, one wipe,
  breath, straighten); his dad stands facing away by the van's far end. 21: the book at 2.6x on the wall beside the
  kart, both whole in frame, with `sh_bookspot`.
- Sound: hammer hits retimed (14.75, 15.55, 16.35 s); a spanner sound (Mixkit 853) replaces the sanding.

## Round 5 and stage 3 (lighting and grade)
- "At the track" was swallowed: `tools/shift_after.py 16.95 5` put 5 frames of silence into vo.wav before "At" and
  moved everything after 16.95 s by 5/30 s (timing.json, `ham_anim.SHOT_T` via `FS`, END, frames renamed +5,
  captions END, compose ANIM/FADE/END, the sound's `SHIFT`). Backups in out/before_shift. Film length 49.67 s.
- Shot 10: boy at (-7.55, 5.6) turned -135, dad at (-6.95, 7.75) facing away, camera (-7.05, 3.55) on the thirds;
  the near gazebo is removed for this shot. Tears: a small drop under the outer corner of each eye (voxel.py).
- Title box top at 23.5 % (`title_mc.TOP`); shot 1's camera targets raised so the heads clear it.
- Grade: `tools/grade_frames.py out/frames_test out/frames_graded [shots]` = boards/grade.sh + a scene colour +
  a gamma that puts the shot's mean luma into its scene's band (`SCENE`; `GAMMA` keeps shots 1 and 10 as set) +
  bloom and grain. Then `GRADED=1 SFX=assets/audio/sfx_mix.wav python tools/compose_test.py out/frames_graded ...`.

## Status
- Stage 3 sent: out/hamilton-graded-v1(-phone).mp4 (49.67 s, with sound), boards/storyboard-v6-1/-2.png, boards/shot-list.md (v6). Owner: "It's perfect". Stage 4 running: `PCT=100 SAMPLES=24 blender ... ham_anim.py -- out/frames_final` (about 12 s a frame,
  ~5 h, log out/final_render.log). Then `grade_frames.py out/frames_final out/frames_final_graded`, then
  `GRADED=1 SFX=assets/audio/sfx_mix.wav compose_test.py out/frames_final_graded assets/captions_1080 out/hamilton-final.mp4`.
  The voice is now compressed and the mix levelled to -14 LUFS (owner couldn't hear it in the car).
  After that: stage 6 (title, description with sources + AI voice + the photo credit, thumbnail without his name or face).
- 2026-11-09, stages 4 and 6 done. Final: `out/hamilton-final.mp4` (1080x1920, 30 fps, 49.67 s, -14.5 LUFS integrated,
  true peak -0.6 dBTP, 33.8 MiB) and `out/hamilton-final-phone.mp4` (21.1 MiB). Shot 7's panels were stacked into
  `out/frames_final` before grading (the stacking code from compose_test.py). Storyboard `boards/storyboard-v7-1/-2.png`
  (from the final MP4, `shots_v7.json`). Thumbnail `out/hamilton-thumbnail.png` uses the film's own graded frame
  f00242 (end of shot 3); `blender/thumb_ham.py`'s separate hero render was not used (the signature didn't draw and
  the Standard view washed the page out). Title, description and tags: `out/youtube-metadata.md`.
- Thumbnail changed on the owner's request to young Hamilton with the boss: `blender/thumb_pair.py` (shot 1b's set and
  poses, both turned toward a camera between them, the book lowered to his chest so his face shows, a soft key on his
  face), graded with the ballroom grade at gamma 1.04 (skin matches shot 1a), text by `tools/thumb.mjs`.
