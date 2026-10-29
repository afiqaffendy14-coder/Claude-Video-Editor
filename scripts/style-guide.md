# Channel Visual Style (low-poly take on Neo's "How Pit Stops Are So Fast")

Reference studied: Neo, "How Pit Stops Are So Fast" (8:49, 1920×960, 25 fps). This file describes its style; the reference video itself is not stored in the repo.

## What the reference does

- **Clay-render world.** Almost everything is matte white or light grey: track, garages, grandstands, even the background. No textures and no real-world clutter.
- **One accent colour.** Only the story subjects get colour (cyan crew suits, cyan car livery). Tyres are the only other colour (red/yellow sidewalls). Your eye always knows where to look.
- **Soft, overcast studio light.** No harsh sun. Strong ambient occlusion: soft contact shadows under feet, wheels and the car. A light haze fades distant objects to white.
- **Signature shots:**
  - straight **top-down overhead** shots (the cold open is a top-down pit stop with a running timer);
  - **macro close-ups** with very shallow focus (wheel nut, wheel gun, tyre lettering);
  - **low tracking shots** at car height;
  - driver's-eye shots through the halo.
- **Slow, smooth camera.** Gentle dollies and drifts, with slow motion at the key mechanical moments. Cuts are hard cuts. The long-form median shot is about 7.7 s; for a Short, aim for 3–5 s.
- **Minimal UI.** Small white rounded boxes with bold black numbers (the "2.22" timer), simple arrow icons in white boxes, and in-world light boards (red → green). No busy lower thirds.
- **Mood shifts by dimming the palette.** The one dark shot (crew in a dim garage) stands out because everything else is bright.

## Our low-poly version

| Element | Choice |
|---|---|
| Geometry | Flat-shaded low poly, with visible facets on cars, people and terrain. Smooth only where facets would look broken (tyre treads read fine faceted). |
| World | Off-white `#F2F2F0` ground, light grey `#D9D9D6` structures, haze to white at distance. |
| Accent | **Red `#D7262B`** for the story's hero (Lauda's car, helmet, suit). One accent per video; everything else stays grey. |
| Secondary | Rivals in mid grey `#9A9A98`. Tyres keep coloured sidewalls as a small detail. |
| Lighting | Soft overhead key + hemisphere fill, soft shadows, ambient occlusion. Drop to darker greys (never black) for danger or tension beats. |
| Camera | Top-down for openings and transitions. Macro with shallow focus for emotional details. Low tracking for speed. Slow eased moves; hard cuts. |
| UI | White rounded box, black heavy number (counters, positions, points). White arrow boxes. In-world light boards for status. |
| Type | Heavy sans for numbers (Inter 900). On-screen captions bold white with a soft shadow, kept in the upper/middle third clear of Shorts UI. |
| Format | 1080×1920 vertical, 30 fps. Keep key action inside the central 80%. |
| Safety | No team or sponsor logos. Real drivers stylised, never photoreal. Crashes shown as abstract shards, never injuries. |

## How we build it

HyperFrames + Three.js, the same stack as `videos/lowpoly-blue`: Three.js draws the low-poly scenes from timeline time, GSAP drives the white UI boxes and captions, and everything renders deterministically to MP4.
