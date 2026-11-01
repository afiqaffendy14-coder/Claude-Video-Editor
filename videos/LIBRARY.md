# Reusable library

Everything here already exists and is tested. Import it; don't rebuild it. Paths are under `videos/pitstop-hospital/`.

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
