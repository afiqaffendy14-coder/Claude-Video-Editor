#!/bin/bash
# Colour grade for every frame (stills now, video frames later): lifted shadows, a touch more saturation,
# cool shadows / warm highlights, gentle vignette.  Usage: boards/grade.sh in.png out.png
GRADE="curves=all='0/0.035 0.25/0.28 0.5/0.53 1/1',eq=contrast=1.04:saturation=1.15,colorbalance=rs=-0.02:bs=0.03:rh=0.03:gh=0.01:bh=-0.025,vignette=angle=PI/9"
ffmpeg -v error -y -i "$1" -vf "$GRADE" "$2"
