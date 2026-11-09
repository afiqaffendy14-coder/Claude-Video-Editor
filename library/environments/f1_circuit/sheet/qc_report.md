# Circuit QC report

Lap 4322.4 m, 15 corners, pit lane 914 m, world 2849 x 2333 m.

## 1. Track continuity
- [x] **Lap closes**: layout solver closes the chain to 1e-6 m and 360 degrees (asserted)
- [x] **Centre line on asphalt everywhere**: 0 of 8653 samples off the asphalt
- [x] **Track width 12 m or more**: min 13.0 m, max 19.2 m (1 m blocks)
- [x] **Driveable surface is one piece (track + pit lane)**: 1 component(s)

## 2. Pit lane
- [x] **Pit lane centre line on its road**: 0 samples off
- [x] **Pit entry leaves from the track**: entry centre -4.0 m from the track edge (negative = on the track)
- [x] **Pit exit rejoins the track**: exit centre -2.5 m from the track edge
- [x] **Pit surface joins the track surface**: pit pieces 1, all in the track's component: True

## 3-5. Barriers, grounding, clipping
55112 placed pieces (instances + objects) gathered with their blocks.
- [x] **Barriers never on the track or kerbs (>= 1.5 m from the edge)**: 0 pieces too close
- [x] **Fence line continuous (open only at gates and the pit entry/exit)**: 2 open ends outside gates: [[336.0, -18.0], [-477.3, -218.3]]
- [x] **Everything stands on the ground (no floating or sunk pieces)**: 0 pieces
- [x] **Nothing solid on the racing surface**: 0 pieces
- [x] **No clipping between pieces**: 2635 close pairs tested block by block; 0 overlapping
- [x] **People do not clip into seats, platforms or posts**: 0 of 4000 sampled

## 6. Proportions
| item | size | note |
|---|---|---|
| block character | 1.44 m tall | 1 skin px = 4.5 cm; world texel 6.25 cm |
| F1 car (library) | 5.6 x 2.0 m | grid slot 8 m pitch, staggered |
| track width | 13 m (main straight 15 m) | real F1: 12-15 m |
| pit lane | 13 m (fast lane + working lane) | box 8 m long per team |
| garage | 11 m bay x 14 m deep, door 4.8 m | two bays per team |
| kerb | 1.5 m wide, 1 m stripes | flush (cars roll over) |
| concrete wall / fence | 1.15 m / +3.6 m with catch panel | fence on every barrier |
| grandstand row | 0.8 m tread, 0.45 m rise, 0.5 m seat pitch | seat top 0.5 m |
| floodlight mast | 22 m | lamp bank toward the track |

## 7. Performance
- objects in the file: 818 (terrain 182, instancers 75)
- instances drawn: 55202; triangles drawn: 7.4 M (unique mesh data is much smaller: 2.5 M)
- materials: 354, images: 353 (all 16 px/m pixel textures)
- lights: 160 (floodlight spots only switch on at night)
- 1080p EEVEE, 48 samples, cam_establishing: 7.2 s per frame
- 1080p EEVEE, 48 samples, cam_pit_lane: 3.8 s per frame

**Result: PASS** (199 s)
