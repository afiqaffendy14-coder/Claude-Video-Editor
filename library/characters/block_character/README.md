# Master block character (Minecraft style)

One rig and one model; every character is just a skin. Never remodel a person per video: build them from here and
change the skin.

- Standard Minecraft player model: head 8 px, body 8×12×4, arms 4×12×4 (or 3 px "slim"), legs 4×12×4.
- Standard Java 64×64 skin, two layers. Any skin from a normal skin editor works.
- 1 skin pixel = 4.5 cm (the house world pixel), so a character is 32 px = 1.44 m and the head is 0.36 m. That is
  the size the F1 car cockpit and halo are built around.
- Axes match the car library: +Y forward, +X the character's right, +Z up, origin on the ground between the feet.

## Use a character in a shot

```python
import sys; sys.path.insert(0, r"<Claude-Video-Editor>/library/characters/block_character")
import character_blender as ch
p = ch.make_character("toto", skin="driver_silver_arrow", helmet=True, pose="idle", face="smile")
p.location = (1, 0, 0)                  # the root is an armature: move/turn/animate it like any object
ch.set_pose(p, "wave", frame=24)        # a named pose or a dict of joint angles, keyed
ch.set_face(p, "grin", frame=30)        # expressions switch instantly (constant keys)
ch.set_skin(p, "driver_rosso")          # same character rig, new skin
ch.ik_hand(p, "R", some_object)         # hand follows an object; the elbow pole keeps it from flaring out
ch.seat_in_car(p, car_root)             # F1 car or kart: its seat pose, hands on the steering-wheel grips
```

`seat_in_car` parents the grip targets to the steering wheel, so the hands turn with `car_root["steer"]`.

### Poses (`template.POSES`)
stand, idle, walk, run, sit, wave, point, cheer, think, shrug, fist_pump, driver (F1), kart. A pose is a dict of friendly
joint values in degrees: `lean`, `twist`, `crouch` (metres), `waist`, `head` (turn, nod, tilt), `arm_L`/`arm_R`
(forward, out, twist), `elbow_L`/`elbow_R`, `leg_L`/`leg_R` (forward, out) and `knee_L`/`knee_R`. Bends only go
one way, so keep elbows, knees and the waist at 0 or above.

### Expressions (`template.EXPRESSIONS`, `root["face"]`)
0 neutral, 1 smile, 2 grin, 3 frown, 4 angry, 5 worried, 6 surprised, 7 shout, 8 blink, 9 look_left,
10 look_right.

## Make a new character

1. Add a spec to `skins.SKINS`: skin tone, eye colour, hair style and colour, beard, outfit kind (`race_suit`,
   `team_kit`, `tee`, `overalls`), team (the kits match the car liveries), helmet, and `classic` or `slim`.
   Or paint a 64×64 PNG in any Minecraft skin editor, save it as `skins/<name>.png` and give it a spec with
   `"png": True`. `skins/_layout_guide.png` shows where everything goes.
2. Run `skins.py`. It paints `skins/<name>.png` plus `<name>_faces.png`, the strip of expression faces.
3. Call `make_character("name", skin="<name>")`.

Helmets (`helmets/<team>.png`) are the driver's own design, kept in colours that contrast with the car so they
read in the cockpit. The skins use plain kits with no real logos. A real person appears only as a block character with their own skin.

## Files

| File | What it does |
|---|---|
| `template.py` | The master model: parts, skin UV layout, bones, bend joints, poses, expressions. Pure Python. |
| `skins.py` | Skin specs and the painter for skins, face strips and team helmets (`helmets/<team>.png`). |
| `character_blender.py` | Builds the rigged character in Blender: `make_character`, `set_pose`, `set_face`, `set_skin`, `ik_hand`, `seat_in_car`. |
| `render_sheet.py` / `compose_sheet.py` | The model sheet: `sheet/model-sheet.png` (+ phone JPG). |
| `render_drivers.py` / `compose_drivers.py` | Driver review: helmets on, each driver in their team car, T-cam and x-ray steering views: `sheet/drivers-sheet.png`. |
| `../../cars/f1_2026/fit_check.py` | Seats this character in a car and reports anything that pokes through the bodywork or touches the halo. |

```
.venv-tools/Scripts/python library/characters/block_character/skins.py
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python library/characters/block_character/render_sheet.py -- [--samples 64] [view ...]
.venv-tools/Scripts/python library/characters/block_character/compose_sheet.py
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python library/cars/f1_2026/fit_check.py -- [--skin driver_rosso --livery rosso] [--render]
```
