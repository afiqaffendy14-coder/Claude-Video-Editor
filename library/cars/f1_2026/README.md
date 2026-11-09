# 2026 F1 hero cars (voxel, Minecraft style)

One blueprint, every video. Don't remodel a car per video: append it from here. Change the blueprint (or add a
livery) here and rebuild.

## Use a car in a shot

```python
import sys; sys.path.insert(0, r"<Claude-Video-Editor>/library/cars/f1_2026")
import car_blender as car
root = car.load_car("ham", livery="rosso")     # silver_arrow | rosso | papaya | midnight
root.location = (0, 10, 0)                     # animate the root like any object
root["steer"] = 12                             # degrees, + = left: front wheels + steering wheel follow
car.bake_roll(root, 1, 120)                    # wheels roll with the real distance travelled (no tyre slide)
```

`load_car` appends `blend/<livery>.blend` (about a second). A different `number=` or `compound=` (soft, medium,
hard, inter, wet) builds that car fresh from the blueprint instead. Several cars in one scene are fine; each
gets its own copy and its own rig.

The car has no driver. Seat the master block character with
`character_blender.seat_in_car(person, root)` (see `library/characters/block_character`): it takes the driver pose
at `blueprint.SEAT` with its hands on the steering-wheel grips. The cockpit, halo and headrest are sized for it,
and `fit_check.py` proves it.

## Liveries (team-inspired, no real logos)

| key | look | default number |
|---|---|---|
| `silver_arrow` | Mercedes-inspired: silver nose and pod tops, black body, teal, claw stripes, star field | 63 |
| `rosso` | Ferrari-inspired: red body, white pin lines, black lower body and wings | 16 |
| `papaya` | McLaren-inspired: papaya body, anthracite lower body, wings and halo | 81 |
| `midnight` | Red Bull-inspired: matte navy, red pin lines, yellow nose tip | 3 |

A new team is a new entry in `blueprint.LIVERIES` (paint slots, patterns, decal words, number); the shape never
changes. Then run `build_assets.py` and `render_sheet.py --livery <key>`.

## Files

| File | What it does |
|---|---|
| `blueprint.py` | The car as voxels (2.25 cm = half the house world pixel): geometry, liveries, decals, tyre markings. Pure numpy. |
| `car_blender.py` | Builds the rigged Blender car; `load_car`, `bake_roll`, `save_blend`. |
| `build_assets.py` | Saves every livery to `blend/<livery>.blend` (marked as an asset). |
| `fit_check.py` | Seats the master block character and reports anything poking through the bodywork or touching the halo. Run it after any cockpit change. |
| `render_sheet.py` | Renders the model-sheet views to `sheet/<livery>/renders/` (Cycles, GPU). |
| `compose_sheet.py` | Lays the views out as `sheet/<livery>/model-sheet.png` (+ phone JPG). |
| `showcase.py` | EEVEE review clips: turntable, steering/rolling rig test, four-car lineup. |

```
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python library/cars/f1_2026/build_assets.py
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python library/cars/f1_2026/render_sheet.py -- --livery rosso [--scale 0.5] [--samples 80]
.venv-tools/Scripts/python library/cars/f1_2026/compose_sheet.py rosso
```

Axes: +Y forward, +X the driver's right, +Z up, origin on the ground halfway along the wheelbase.
