# Reusable library

Everything here already exists and is tested. Import it; don't rebuild it. **Start with the master assets in
`library/`** (below); the per-video modules further down are under `videos/pitstop-hospital/` unless noted.

## Master assets (`library/`; each folder's README shows how to load it)
One blueprint per asset, shared by every video: load it, never remodel a car, kart, person or track inside a video
folder. Change the blueprint in `library/` and rebuild. Same axes and scale everywhere (+Y forward, +Z up, 1 skin
pixel = 4.5 cm, block character 1.44 m tall).
| What | Where | Use |
|---|---|---|
| 2026 F1 car | `library/cars/f1_2026/` | `car_blender.load_car(name, livery=)`: silver_arrow, rosso, papaya, midnight; `["steer"]`, `bake_roll` |
| Go-kart | `library/cars/kart/` | `kart_blender.load_kart(name, livery=, condition="beat_up")` (the fifth-hand kart), `tyre="wet"` |
| Block character | `library/characters/block_character/` | `make_character(name, skin=, helmet=, pose=, face=)`, `set_pose`, `set_face`, `ik_hand`, `seat_in_car`; new person = new skin in `skins.py` |
| Grand Prix circuit | `library/environments/f1_circuit/` | `circuit_blender.load_circuit(time_of_day=)`, 20 camera presets, `lap_frame`, `grid_slot`, `pit_box`, flags, garage doors |
Each folder has `sheet/*-preview.jpg` (what it looks like). Full model-sheet renders stay on the laptop only.

## Pipeline
| What | Where | Notes |
|---|---|---|
| Bake shots to .blend | `blender/bake.py` | per-shot choreography in `shot_fx()` |
| Characters (rigged, IK) | `blender/rig.py`, `blender/voxel.py` (`block_person`) | outfits: scrubs, surgeon, doctor, crew, leader |
| Choreography | `blender/choreo.py` | `Performer`: walk/step_to (planted feet), ease/overshoot/wob |
| Behaviours | `blender/bake.py` | `operate` (surgeon at work), `run_with` (sprint), `busy` (frantic work at a station), `unplug_fx` |
| Station solver | `blender/pitstop.py` | `solve_root`, `match_lr`, `Station` (stances + steps) |
| Validator | `blender/validate.py` | clipping, reach, foot slide, floor, teleport per frame |
| Previews | `blender/preview.py` | small stills per shot |
| GPU render (resumable) | `blender/render.py`, `go.bat`, `redo.bat` | EEVEE default; broken frames auto-fixed |
| Captions / SFX / compose | `tools/captions.mjs`, `tools/sfx.py`, `tools/compose.py` | grade in `boards/grade.sh` |
| Voice fit + timings | `tools/fit_vo.py`, `tools/vo_timing.py` | |
| Thumbnail | `tools/thumb.mjs` | two stills + title |

## Sets (`blender/sets.py`, dressing in `blender/dress.py`)
- `pit_set`: pit box, garage, pit wall, grandstand, sky/clouds; phases ready/arrive/swap/go.
- `icu_set`: intensive-care room with window and city; modes empty/chaos/order.
- `theatre_set`: operating theatre and table with baby.
- `corridor_set`: hospital corridor with the cot team.
- `viewing_room`: staff room with sofa and TV; `exterior_set`: London street and hospital front.

## Props (`blender/props.py`, plus shot-specific ones in `blender/shots.py`)
- F1 car (block style, yellow helmet driver), wheels, wheel gun (+ T-handle in `pitstop.add_t_handle`), jacks,
  lollipop board.
- Cot with baby, ECG monitor (scrolling trace), IV stand/line, ventilator, clipboard, phone, syringe.
- Two-part line connector and soft tubes (`shots.soft_line`, hookable).

## Camera
- `anim.MOVES` (push/truck/crane/orbit/spin/follow) and `camera_path`.
- `bake.SHAKE` (handheld noise) and `bake.RUN_CAM` (camera travels with runners).

## From video 2 (paths under `videos/halo/`; see its HANDOFF.md)
Generalised shared modules: prefer these copies over pitstop-hospital's.
| What | Where | Notes |
|---|---|---|
| GPU setup | `blender/lib.py` (`lib.gpu()`) | Cycles on OptiX/CUDA (this laptop: CUDA) |
| Characters | `blender/voxel.py` (`block_person`) | outfits carry their own skin/hair/helmet colour; headset |
| Cars | `blender/props.py` | `f1car_block(halo=, helmet=, part="front"/"rear")`, `halo_part()`; wings, suspension, numbers |
| Hands and props | `blender/choreo.py` | `Performer` hands ride on chest/head; `carry_props`; `gesture`, `head_keys`, `body_keys` |
| Exact contact | `blender/ik.py` | hand/foot contact for still poses |
| Static collision check | `blender/check.py` | per storyboard frame -> `boards/check.json` |
| Crash physics | `blender/halo_anim.py` | `Crash` clock (ballistic arc, roll, rebound, slide), `tau_of`, `CrashDebris`, `Explosion`, `split_state` |
| Final look | `blender/look.py` | AgX exposure per set, box-volume haze, rim lights; used by `render.py` unless PREVIEW |
| Finish | `tools/finish.py` | per-scene grade, bloom, vignette, grain, captions, VO + ducked SFX, phone-safe MP4 |
| SFX | `tools/sfx_sources.json`, `tools/sfx_mix.py` | ElevenLabs sound effects placed on the film's clocks |
| Thumbnail render | `blender/thumb_roman.py`, `blender/thumb_shot.py` | dedicated hero render for the thumbnail |

Sets and props (`blender/halo_sets.py`): Monza (grandstand, tifosi, flags, chicane and sausage kerbs, gravel, park
trees), Bahrain at night (armco, split car, fire), studio, bus test rig, pedestal, car launch stage, pit wall, moving
crowd cards (`crowd_cards`), red-X fan boards; chainsaw, extinguisher + foam, sign, double-decker bus, armco, fire.
