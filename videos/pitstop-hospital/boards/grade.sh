#!/bin/bash
# Colour grade for every frame (stills now, video frames later): a touch more contrast and saturation,
# cool shadows / warm highlights, soft vignette.  Usage: boards/grade.sh in.png out.png
GRADE="eq=contrast=1.07:saturation=1.18:gamma=0.98,colorbalance=rs=-0.02:bs=0.035:rh=0.035:gh=0.01:bh=-0.03,vignette=angle=PI/6"
ffmpeg -v error -y -i "$1" -vf "$GRADE" "$2"
