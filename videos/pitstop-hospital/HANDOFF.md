# Handoff: "Why would a children's heart surgeon ask Ferrari for help?"

For the next Claude session (e.g. Claude Code on the owner's MSI PC with an NVIDIA GPU). Everything needed is in this
repo on branch `claude/dreamy-gauss-pyydwp`.

## What this is
A 60.0 s vertical F1 YouTube Short (1080x1920), blocky voxel 3D style rendered in Blender, about how Great Ormond
Street Hospital redesigned post-surgery handovers with help from Ferrari's pit crew.

## Decisions the owner has made (keep these)
- Script: v6 in `../../scripts/f1-pitstop-hospital.md` (facts and sources there; say "safer", never "saved lives").
- Voiceover: ElevenLabs voice "F1 Narrator" (voice id `T6dmRMFpaA2PwnRdtyjv`), take 1, pauses cut to breaths,
  exactly 60 s: `assets/audio/narrator/v6_take1_60.wav`. Word timings: `tools/timing.json`.
- Look: blocky / Minecraft-like but original characters; colour grade in `boards/grade.sh`.
- Captions: Montserrat Black, white with black outline, smaller (6.2% of width), lower third (74% down). Approved.
- 35 shots, hard cuts on the spoken words: `blender/shots.py` (`SHOTS`), storyboard `boards/storyboard-*.png`.
- Motion: one smooth continuous camera move per shot (`blender/anim.py` `MOVES`), characters move a little and
  slowly (`blender/anim_people.py`); pit crew stay at their stations doing the tyre change and only step back once
  the car has gone; hands must never clip through the car, cot, baby or table (collision check in anim_people).
- Driver helmet: full-size yellow. Lollipop pole in the lollipop man's hand. Front jack moved clear before the car leaves.
- Sound: synthesised SFX (`tools/sfx.py`, per shot) under the voiceover; no music yet.

## Pipeline (what each piece does)
1. `blender/shots.py` builds each shot (sets.py, people.py/voxel.py, props.py, dress.py), voxelises it.
2. `blender/anim.py <out_frames> <w> <h> <samples> <fps> <shot ids...>` renders animated frames `fNNNNN.png`.
3. `tools/captions.mjs <out> <w> <h> 0 60` renders caption PNGs.
4. `tools/sfx.py <out.wav> 0 60` makes the sound effects.
5. `tools/compose.py <frames> <fps> <captions> <sfx.wav> 0 60 <out.mp4> [w h]` grades, overlays captions, mixes audio.

## Rendering on the PC (next step)
The cloud box had no GPU (CPU Cycles ~0.7 s per sample per 360x640 frame). On the MSI:
- Install Blender 5.x, Python 3, Node.js, ffmpeg (winget), Playwright for Node (`npm i -g playwright && npx playwright install chromium`).
- Run Blender's Python on the scripts: `blender -b --python blender/anim.py -- <args>` (anim.py reads sys.argv; make
  it read the args after `--` when run inside Blender).
- Switch `lib.setup_render` to the GPU: Cycles with OptiX (`preferences.addons['cycles'].preferences.compute_device_type = 'OPTIX'`,
  scene.cycles.device = 'GPU', ~12-16 samples, OptiX denoiser) or, to finish in well under an hour, EEVEE.
- Goal agreed with the owner: whole minute in under ~1 hour -> EEVEE at 1080x1920, 24 fps, and ideally bake each shot's
  camera + character motion to keyframes in a .blend instead of rebuilding characters per frame in Python.
- Then captions at 1080x1920 and compose at 1080x1920.

## Status at handoff
- A low-quality 60 s test (360x640, 4 samples, 24 fps) was rendered in the cloud for motion/timing review.
- Owner feedback still to apply after that test, if any, comes from the owner.
