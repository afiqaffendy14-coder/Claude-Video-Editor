#!/bin/bash
# Generate every line of tools/lines.json at speed $1, then join into assets/audio/vo.wav
cd "$(dirname "$0")/.." && export HYPERFRAMES_PYTHON=/home/user/Claude-Video-Editor/.venv-audio/bin/python
node -e '
const {execSync}=require("child_process");const L=require(process.argv[1]);
L.forEach((t,i)=>{const f=process.argv[2]+"/l"+String(i+1).padStart(2,"0")+".wav";execSync(`npx hyperframes tts ${JSON.stringify(t)} -v bm_george -s ${process.argv[3]} -o ${f} --json`,{stdio:"ignore",cwd:"/home/user/Claude-Video-Editor"});});
' "$PWD/tools/lines.json" "$PWD/assets/audio/raw" "$1"
/home/user/Claude-Video-Editor/.venv-audio/bin/python tools/join_vo.py | tail -1
