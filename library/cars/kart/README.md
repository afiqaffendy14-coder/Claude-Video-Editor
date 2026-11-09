# Racing go-kart (voxel, Minecraft style)

One blueprint, every video, built the same way as the F1 cars (`../f1_2026`). Don't remodel a kart per video:
append it from here. Change the blueprint (or add a livery) here and rebuild.

Senior sprint kart with CIK-style bodywork: tube frame, front fairing, nassau panel, side pods, rear bumper, bucket
seat, 2-stroke water-cooled engine on the right with a radiator on the left, expansion-chamber exhaust and silencer,
chain drive, solid rear axle with a vented disc, fuel tank between the legs, pedals, butterfly wheel with a data
logger, and a transponder on the seat.

- Voxel 1.125 cm = a quarter of the house world pixel (half the F1 car's), so it has the same detail as the F1 car.
- Real size: wheelbase 1.035 m, width 1.40 m, length 1.81 m, front tyres 10×4.50-5, rear 11×7.10-5, 5" rims.
- Axes match the car and character libraries: +Y forward, +X the driver's right, +Z up, origin on the ground halfway
  along the wheelbase.

## Use a kart in a shot

```python
import sys; sys.path.insert(0, r"<Claude-Video-Editor>/library/cars/kart")
import kart_blender as kart
root = kart.load_kart("k1", livery="papaya")   # silver_arrow | rosso | papaya | midnight
root.location = (0, 3, 0)                      # animate the root like any object
root["steer"] = 15                             # degrees, + = left: front wheels (on their kingpins) + wheel follow
kart.bake_roll(root, 1, 120)                   # wheels and rear axle roll with the real distance travelled
```

`load_kart` appends `blend/<livery>.blend`. A different `number=`, `tyre="wet"` (grooved rain tyres) or
`condition=` builds that kart fresh from the blueprint instead.

### Condition: new or beat up

`condition="beat_up"` gives any livery the fifth-hand treatment on the same geometry:
- **Body:** broken corners and chips, a cracked nose taped up, scratches and side scrapes, peeling decals, a
  crooked nassau panel, a rear bumper sagging on the right, and a yellow replacement pod on the right with a
  hand-painted number.
- **Metal:** rust on the frame, chain, silencer and brake disc.
- **Wheels:** chunked rear treads, the right rear tyre from another set, and an odd gold front-left rim.
- **Cockpit:** taped grips and a taped seat crack, zip ties, and no data logger or transponder.
- **Finish:** sun-faded paint, dirt low down and behind the wheels, and oil stains by the engine.

`condition="battered"` is years of it, on top of all that: rust over every metal part, a burnt black-and-rust
exhaust, grime everywhere, yellowed plastics, soot round the engine, and the front fairing gone (bare brackets and an
old tube bumper instead), with bigger broken chunks and a taped split pod.

It's all deterministic, so the kart looks the same in every video. `livery="fifth_hand"` is the club kart that
comes battered: faded blue, white trim, an olive fibreglass seat, a red frame gone rusty, #7. Its driver is the `karter_fifth_hand` skin:
an old grey suit and an orange second-hand helmet.

```python
old = kart.load_kart("old", livery="fifth_hand")               # the saved beat-up club kart
tired = kart.load_kart("t", livery="rosso", condition="beat_up")  # a team kart after five owners
``` The rear bumper is its own object (`<name>_rear_bumper`), so a shot can
knock it off.

### Driver

```python
sys.path.insert(0, r"<Claude-Video-Editor>/library/characters/block_character")
import character_blender as ch
d = ch.make_character("toto", skin="driver_papaya", helmet=True)
ch.seat_in_car(d, root)        # same call as the F1 car: kart pose, hands at 9 and 3, elbows down
```

Each livery's driver skin is `kart_blueprint.driver_skin(livery)`. `seat_in_car` sees the kart (`root["vehicle"] == "kart"`) and reads `kart_blueprint.SEAT`: the neck point, the
grips, the `kart` pose (sat up 20 degrees, knees either side of the column, feet on the pedals) and the elbow poles.
The hands stay on the wheel when it steers. The seat sits 4 cm higher than a real kart's because the block
character's legs are short; that keeps the heels off the floor tray.

## Liveries (team-inspired, no real logos)

| key | look | number |
|---|---|---|
| `silver_arrow` | silver bodywork, black lower half, teal pin lines, chrome frame | 63 |
| `rosso` | red bodywork, black lower half, white pin lines, red frame, gold rims | 16 |
| `papaya` | papaya bodywork, anthracite lower half and frame, black rims | 81 |
| `midnight` | matte navy bodywork and frame, red pin lines, yellow nose tip | 3 |
| `fifth_hand` | beat-up club kart: faded blue, white trim, yellow pins, rusty red frame, yellow odd pod | 7 |

A new team is a new entry in `kart_blueprint.LIVERIES`; the shape never changes. Then run `build_assets.py`.

## Files

| File | What it does |
|---|---|
| `kart_blueprint.py` | The kart as voxels: geometry, liveries, numbers, decals, cockpit layout (`SEAT`). Pure numpy. |
| `kart_blender.py` | Builds the rigged Blender kart; `load_kart`, `bake_roll`, `save_blend`. |
| `build_assets.py` | Saves every livery to `blend/<livery>.blend` (marked as an asset). |
| `fit_check.py` | Seats the master block character and reports any part of it inside the kart. Run it after any cockpit change. |
| `render_sheet.py` / `compose_sheet.py` | The model sheet: `sheet/<livery>/model-sheet.png` (+ phone JPG). |
| `render_lineup.py` | All five liveries with their drivers, appended from the .blends: `sheet/lineup.png`. |

```
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python library/cars/kart/build_assets.py
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python library/cars/kart/fit_check.py -- [--skin driver_rosso --livery rosso] [--steer 20] [--render]
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python library/cars/kart/render_sheet.py -- --livery rosso [--scale 0.5] [--samples 96]
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python library/cars/kart/render_lineup.py
.venv-tools/Scripts/python library/cars/kart/compose_sheet.py rosso
```
