# Handoff: "Imagine a Formula One car landing on your head" (the halo short)

Second Short on the pit-stop pipeline (`../pitstop-hospital`): same blocky voxel look, rigs, narrator and render
scripts. Built on the owner's laptop (RTX 3050 6 GB, Windows 11, Blender 5.2.3 LTS, Node 26, ffmpeg).

## Decisions the owner has made (keep these)
- Topic: the halo, for a broad audience. Hook picked from four options: "car on your head".
- Script: v2 in `../../scripts/f1-halo.md` (facts and sources there). The narrator never says the halo "saved lives"
  on its own authority; only the people involved say it, and the script names them.
- Voiceover: ElevenLabs "F1 Narrator" (`T6dmRMFpaA2PwnRdtyjv`, eleven_v4), **take 2**, pauses capped to ~0.18 s,
  no tempo change, exactly 60.0 s: `assets/audio/narrator/vo_60.wav` (= `v2_take2_60.wav`).
  Word timings: `tools/timing.json` (Scribe timings, script words, so captions use British spelling).
- Shots: about 20-25, simple; props designed for the short blocky arms (one grip point per prop).
- Feedback is batched: show a whole stage (script, VO, storyboard, animation) and collect notes in one go.

## Owner's storyboard-v1 notes (applied in v2; keep applying them)
- Halo: thick and round like the real one (smooth 10 cm tube in the real shape, hoop + centre pillar), never a
  square bar; obvious (red). When explaining it: highlight it on the car, then show just the halo.
- More detail everywhere: cars (wings, suspension, numbers, accents), helmets, the bus, every background.
  Monza must look like Monza (tifosi, flags, chicane kerbs, sausage kerbs, gravel, park trees); garages/launch
  backgrounds must look like real F1 places.
- Show how things happen, not just results: the launch onto Hamilton's car, the swerve into the barrier, the car
  splitting, the climb out, the tyre being pushed off. Shot 1 and the last shot: race POV through the halo, aligned.
- Hamilton must look like Hamilton; Wolff shown clearly.
- Poses and layout first; lighting/colour/cinematics later.
- Animation: natural body language, anticipation, secondary motion (head turns, gestures, reactions),
  exaggeration only where comic/impactful, real momentum and weight, idle life, characters react.
- Physics above all: no clipping, real contact (hands, feet, held props), no foot slide/floating, no teleports;
  adjust a move rather than let it clip. Tools: `ik.py` (exact hand/foot contact for still poses),
  `check.py` (static collision check per storyboard frame, written to boards/check.json), `validate.py` (per frame,
  baked shots), `halo_sets.Contact/settle` (cars resting on each other with real contact).

## Look
- Halo in red is the film's one accent. Cars: Hamilton silver + yellow helmet, Verstappen navy + orange helmet,
  Grosjean white + steel-blue helmet; generic, no logos. Real people as block characters only.
- Crashes abstract: block flames, no injuries.

## Files
- `blender/halo_sets.py`: Monza (crash tableau), Bahrain night (armco, split car, fire), studio, bus test rig,
  pedestal, car launch stage, grandstand fans with red-X boards, pit wall. Props: chainsaw, extinguisher + foam,
  sign, bus, armco, fire.
- `blender/shots.py`: the 24 shots (`SHOTS`), cut on take-2 word starts.
  `blender -b --factory-startup --python blender/shots.py -- board [ids]` renders 540x960 stills on the GPU (~4 s each).
- Shared with the pit-stop film, generalised here: `lib.gpu()` (Cycles on OptiX/CUDA), new palette colours,
  outfits with their own skin/hair/helmet colour and a headset (`voxel.block_person`), `props.f1car_block(halo=,
  helmet=, part="front"|"rear")`, `props.halo_part()`.
- `boards/build.mjs`: storyboard pages from `boards/graded/` (stills through the `grade.sh` look).

## Machine notes
- NVIDIA driver 528.92 is too old for OptiX; Cycles uses CUDA (denoiser OpenImageDenoise). EEVEE is unaffected.
- `boards/aux` (pit-stop film) is a reserved name on Windows; the zip extracts it as `boards/_aux`.
- git is not installed on the laptop; the repo was downloaded as a zip of the branch.

## Status
- Storyboard v1 rendered (24 stills), awaiting the owner's batched notes. Next: animation (bake per shot with the
  rigs), previews on the GPU, then one final render.
- Animation test v1 (out/blend, out/halo-animation-test-phone.mp4) and storyboard v3 (boards/storyboard-v3-*.png,
  boards/shot-list.md, from the test's frames) sent.
- Animation test v2 (out/blend4, out/pframes4, out/halo-animation-test-v2.mp4): the owner's movement notes on v1.
  - Monza crash clock (`halo_anim.Crash`) rebuilt as one continuous move: speeds carried through the kerb, a real
    ballistic arc (g = 9.81) with a quaternion roll-over, a damped landing rebound and jolt, arc-length slide into
    the gravel ending with zero speed and deceleration, both cars clamped to the ground. Braking before the kerb
    fixed (it ran backwards). Shot 3 ends on the instant shot 4 starts; shot 4 is real time.
  - Loop: shot 1 ramps from real time into 0.23x slow motion; one onboard vibration on the crash clock runs
    through 25 -> 1.
  - Shot 5 -> 6: shot 6 opens on shot 5's last frame in the gravel; the cars fall away block by block, the halo
    glows and turns alone.
  - Hands (`choreo.Performer`): body-relative hands now ride on the chest (or the head, for chin/neck/headset), with
    crouch and rig scale included; carried props (helmet, signs, saw) ride with the chest (`carry_props`);
    gestures are splines (`gesture`, `head_keys`, `body_keys`). Walkers bend their knees (no over-long strides).
  - New framing: 3 (from the grandstand, long lens), 7 (close on the tifosi), 9/10 (Wolff behind the car's cockpit),
    11 (load display on the press beam), 12 (low, bus coming down), 14 (lit straight, chase cam keeps the car).
  - Car: steering wheel inside the cockpit with gloves on it, rear floor clear of the tyres. Bus: door clear of
    the arch, flush windscreens, wheels on the ground line, more detail.
  - Validator: all character shots clean except an 8 mm foot slide (s10) and a 1-frame shin/rail touch (s17).
- Test v3 (out/blend5): moving crowds (bobbing cut-out cards, `halo_sets.crowd_cards`), the crash never stops
  (longer slide, TAB moved; `halo_anim.tau_of` maps every crash shot onto the clock), debris (`CrashDebris`),
  shot 14 explosion + split + torn barrier continuing into 15 (`split_state`, `Explosion`), elbow poles.
- FINAL (out/blend6, out/frames_final, out/halo-final.mp4):
  - Shot 7: the 2018 car passes the camera, then a push-in/zoom to the tifosi with UGLY and X signs.
  - `blender/look.py` (applied by render.py unless PREVIEW): AgX per-environment exposure, box-volume haze (a world
    volume blacks out the sun and sky in EEVEE), softer lights, rim lights on characters. Full res, 48 samples,
    motion blur (shutter 0.3), ~4-6 s/frame on the laptop GPU.
  - `tools/finish.py`: per-scene ffmpeg grade + bloom + vignette + grain, Montserrat captions
    (`tools/captions.mjs` -> assets/captions_1080), voiceover + sound design (sidechain ducked), phone-safe MP4.
  - Sound: ElevenLabs sound effects (tools/sfx_sources.json; files in assets/audio/sfx_src, lengths set with
    the node's duration_seconds), mixed by `tools/sfx_mix.py` on the film's clocks -> assets/audio/sfx_final.wav.
