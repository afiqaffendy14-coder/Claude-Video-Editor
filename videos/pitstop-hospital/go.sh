#!/usr/bin/env bash
# One command: bake the 35 shots, render them on the GPU, then grade + captions + voiceover + SFX into the final MP4.
#   ./go.sh            (EEVEE, fastest)        ./go.sh cycles   (path traced, slower)
set -euo pipefail
cd "$(dirname "$0")"
ENGINE="${1:-eevee}"
BLENDER="${BLENDER:-$(command -v blender || echo /Applications/Blender.app/Contents/MacOS/Blender)}"
echo "[0/3] Checking for broken frames from an earlier run..."
"$BLENDER" -b --factory-startup --python tools/frames_fix.py -- out/frames ${REDO:-}
echo "[1/3] Baking the 35 shots..."
"$BLENDER" -b --factory-startup --python blender/bake.py -- out/blend
echo "[2/3] Rendering 1800 frames with $ENGINE (re-run to resume if interrupted)..."
"$BLENDER" -b --python blender/render.py -- out/blend out/frames "$ENGINE"
echo "[3/3] Grading, captions, voiceover and sound..."
"$BLENDER" -b --factory-startup --python tools/compose.py -- out/frames 30 assets/captions_1080 assets/audio/sfx_full.flac 0 60 out/pitstop-hospital-final.mp4 1080 1920
echo "DONE: $(pwd)/out/pitstop-hospital-final.mp4"
