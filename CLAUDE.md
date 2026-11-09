# Channel playbook: F1 YouTube Shorts (blocky 3D)

Read this first. Reference builds (each HANDOFF.md explains its scripts; reuse them, don't rebuild):
`videos/pitstop-hospital/` (video 1), `videos/halo/` (video 2) and `videos/hamilton-autograph/` (video 3, newest:
uses the `library/` assets). Halo has the generalised versions of the
shared Blender modules (`lib`, `voxel`, `props`, `choreo`) plus `look.py`, `ik.py`, `check.py`, `tools/finish.py`:
prefer halo's copy of a module; take resumable `go.bat`/`redo.bat` from pitstop-hospital.
**Master assets live in `library/`** (2026 F1 car, go-kart, block character, Grand Prix circuit; see `videos/LIBRARY.md`):
load them in every video instead of modelling new cars, people or tracks. Story shapes: `scripts/story-formats.md`.
`scripts/style-guide.md` and the CLAUDE.md/AGENTS.md inside older video folders (fuji-pixel, lauda-*, lowpoly-blue) are
the OLD HyperFrames/Three.js style: superseded by this file. New videos go in `videos/<name>/`.

## The style (keep it identical across videos)
- **Format:** 1080x1920, 30 fps, about 50-60 s; looped ending unless the story ends on a reveal (video 3: hard cut).
- **Audience:** broad, not die-hard F1 fans. Real, surprising F1 story with a human angle.
- **Look:** blocky, Minecraft-like 3D in Blender, but original characters/designs (never Minecraft's own assets).
  Pixel-textured boxes, voxelised curves, bright saturated colours, soft daylight, colour grade in `boards/grade.sh`.
  Ferrari/F1 red for crews; teal/blue for hospital-type worlds; yellow driver helmet.
- **Voice:** ElevenLabs voice "F1 Narrator" (`T6dmRMFpaA2PwnRdtyjv`), continuous narration, no silent pauses,
  natural pace; fit to 60 s with `tools/fit_vo.py`; word timings via ElevenLabs Scribe -> `tools/timing.json`.
- **Script:** hook is a question in line 1; smooth idea-to-idea transitions (never "then"/"next"); no fluff;
  facts sourced in the script file; never overclaim (e.g. "safer", not "saved lives", unless measured).
- **Captions:** Montserrat Black, white with black outline, 6.2% of width, centred at 74% height (`tools/captions.mjs`).
- **Sound:** real recorded SFX (Mixkit free licence, `videos/hamilton-autograph/tools/sfx_mix_ham.py`), not ElevenLabs
  or synthesised; no copyrighted music. Final mix about -14 LUFS so the voice is clear on a phone.
- **Hook:** the first frame already shows the hook (no establishing shot); audio starts on frame 0.
- **Camera:** one smooth eased move per shot, hard cuts on spoken words, subtle handheld shake only for urgent beats.
- **Animation:** natural, weighted, no clipping/teleporting/foot sliding, hands really hold things, no sudden stops.

## Workflow (in this order; don't reopen a finished step without the owner asking)
1. Topic + title (question hook) -> 2. script (owner approves) -> 3. voiceover (2 takes, owner picks)
4. storyboard as stills (`boards/build.mjs`) -> 5. animation: bake + `validate.py` + low-res previews
6. ONE final render (`go.bat` / `redo.bat <shots>`) -> 7. title, description, tags, thumbnail (`tools/thumb.mjs`).

## Efficiency rules (owner's usage matters)
- Work on the owner's laptop (local session) so Blender previews use the GPU; never render the film on a CPU box.
- 20-25 shots per minute, not 35. Prefer close-ups and single-subject shots; avoid crowds in tight spaces.
- Batch feedback: collect all notes with timestamps, fix in one pass, re-render only changed shots (`redo.bat`).
- Run `blender/validate.py` before any render; fix clipping/reach there, not by re-rendering.
- Model: storyboard and animation need Opus at high effort. On Sonnet/medium (tried 2026-11-03) the animation didn't
  match the storyboard. Save usage with fewer turns and batched notes, not a cheaper model.
- Short replies; don't re-explain the pipeline; don't regenerate voice/assets that were approved.

## Lessons from video 1 (build these in from the start)
- Block characters have short arms (wrist <= ~0.42 m from shoulder): place people from their hand-hold points
  (`pitstop.solve_root`) and give props handles at reachable heights (see the wheel-gun T-handle).
- People need ~0.8-0.9 m between stations; give each person a fixed station and their own frame for hand tasks.
- Cameras: check nobody stands between lens and subject; don't shoot a person bent toward the lens (shows cap only).
- Material names are shared: use unique names for new materials (e.g. `nitrile_glove`, not `glove`).
- Blender 5: F-curves live in layered-action channelbags (`bake.fcurves()`); refresh matrices
  (`view_layer.update()`) before parenting.

## Owner's notes from video 2 (halo storyboard; apply from the start)
- More detail everywhere: cars (wings, suspension, numbers), helmets, every background; real places must look real.
- Show how things happen, not just results (the launch, the swerve, the split, the climb out).
- Real people as recognisable block characters (colours, helmets); generic designs, no logos. Crashes abstract, no injuries.
- Poses and layout first, lighting and colour later. Physics above all: real contact, no clipping, foot slide or floating.
- Natural acting: anticipation, secondary motion, reactions, idle life; exaggerate only for comic or impact beats.
- Laptop: Blender 5.2.3, RTX 3050 6 GB; its NVIDIA driver is too old for OptiX, so Cycles uses CUDA (EEVEE unaffected).

## Keep this playbook current (every video)
At the end of each video, without being asked:
1. Add an entry to `videos/LOG.md` (template at the top): topic, title, decisions, what worked, what cost time.
2. Add any new reusable set/prop/character/behaviour to `videos/LIBRARY.md`.
3. If a choice is now settled (owner approved it or repeated it), promote it into this file; remove rules that changed.
4. When the owner shares stats (views, retention, likes), add them to that video's LOG entry and note what to repeat.
Keep entries short; this file stays under ~120 lines (it loads into every session).

## Posting
Title = the hook question (<= ~40 chars, emoji ok). Description: 3-4 short paragraphs, the result with numbers, source
line, 3 hashtags (#F1 #Formula1 #Shorts). Thumbnail: real frames, two-panel split, title text across the seam.
