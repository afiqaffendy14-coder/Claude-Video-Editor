// Writes boards/storyboard.html and STORYBOARD.md from the schedule and the scene notes.
import { writeFileSync } from "node:fs";
import { SCENES, LINES, DURATION } from "../scene/schedule.js";

const notes = {
  hook: { name: "The hook", stills: ["0.6", "2.8"], scene: "Hospital at night, close on the bed: his head bandaged with blood soaking through, burns across his face, an oxygen mask, a bandaged arm with a burned hand, a blood bag on the drip. The scorched helmet sits on the bedside table; rain on the window.", sound: "8-bit heart-monitor beeps, soft rain behind glass, chiptune bed fades in" },
  comeback: { name: "42 days later", stills: ["4.4", "6.4"], scene: "Days flicker past the window as a DAY counter runs 0 → 42 (it turns red at 42). Cut to the sunny Monza grid: his red #1 shakes on its idle.", sound: "coin blip per counter tick, power-up jingle on 42, chiptune engine idle" },
  loop: { name: "The open loop", stills: ["7.4", "9.4"], scene: "He launches off screen. The empty grid holds and the colour drains away to dark.", sound: "engine launch and fade, the music drops out" },
  ring: { name: "The Green Hell", stills: ["10.6", "14.8"], scene: "The Nürburgring from above: dark forested hills and fog, his tiny red car snaking along the track.", sound: "distant engine echo through the hills, low drone" },
  crash: { name: "Lap two", stills: ["16.9", "20.6"], scene: "Side view at the barrier. The car wobbles, hits the armco, flames rise (the screen shakes). Other cars stop; three drivers run to him. Shown as fire, never injuries.", sound: "skid, 8-bit explosion on impact, fire crackle, footsteps" },
  hospital: { name: "Fighting", stills: ["22.5", "26.8"], scene: "Close on the heart monitor: a fast, irregular trace and a red alarm light, steadying to a calm rhythm and a green light on \"fights for his life\".", sound: "fast irregular monitor beeps that settle into a steady beat" },
  monza: { name: "Monza", stills: ["29.0", "32.6"], scene: "Close-up: a small fresh stain on the balaclava as his gloves pull the helmet down over it. Cut to the Monza straight: he crosses the line and the pit board flips to P4.", sound: "padded helmet thud, engine pass, small 3-note fanfare on P4" },
  fuji: { name: "Japan", stills: ["34.2", "39.6"], scene: "The camera tilts down from the storm and Mount Fuji to the circuit. Hunt's white car blasts past; score boxes LAUDA 68 / HUNT 65 pop in. The rain doubles on \"brutal\".", sound: "rain (kept soft), white car pass-by, menu blip on the score boxes" },
  pits: { name: "The decision", stills: ["42.6", "45.4"], scene: "His car turns into the pits and stops by the mechanic. He climbs out and walks away with his helmet. Hunt's car passes again; the boxes flip to HUNT 69 / LAUDA 68.", sound: "downshift and brakes, engine cut, splashing steps, score-flip blip, a falling 3-note phrase on \"By one point\"" },
  end: { name: "Knowing when to get out", stills: ["50.4", "57.2"], scene: "He walks out past the red pit light; only his car is left. The final shot is his helmet on the wet pit wall, framed exactly like the first shot so the video loops. \"FOLLOW FOR MORE F1 STORIES\" for the last second.", sound: "rain, the music resolving softly, last monitor-style beep echo" },
};

const fmt = (s) => s.toFixed(1);
const cards = SCENES.map((s, i) => {
  const n = notes[s.id];
  const lines = LINES.filter((l) => l.scene === s.id).map((l) => l.text).join(" ");
  const imgs = n.stills.map((at, k) => `<figure><img src="stills/frame-${String(i * 2 + k).padStart(2, "0")}-at-${+at}s.png" alt="" /><figcaption>${at}s</figcaption></figure>`).join("");
  return `<div class="frame">
  <div class="stills">${imgs}</div>
  <div class="title">${String(i + 1).padStart(2, "0")}: ${n.name}</div>
  <div class="time">${fmt(s.start)} to ${fmt(s.end)}s</div>
  <p class="vo">“${lines}”</p>
  <p class="words">${n.scene}</p>
  <p class="meta"><b>Sound:</b> ${n.sound}</p>
</div>`;
}).join("\n");

writeFileSync(new URL("../boards/storyboard.html", import.meta.url), `<!doctype html>
<html lang="en"><head><meta charset="UTF-8" /><title>Lauda Pixel Storyboard</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #f3f3f1; color: #141414; font-family: Inter, system-ui, sans-serif; padding: 40px; width: 2000px; }
  h1 { font-size: 38px; font-weight: 900; letter-spacing: -0.02em; }
  header p { color: #666; font-size: 17px; margin-top: 8px; }
  .grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 22px; margin-top: 28px; }
  .frame { background: #fff; border-radius: 18px; padding: 14px; box-shadow: 0 6px 22px rgba(0,0,0,.07); }
  .stills { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  figure { position: relative; } img { width: 100%; display: block; border-radius: 8px; image-rendering: pixelated; }
  figcaption { position: absolute; left: 6px; top: 6px; background: rgba(0,0,0,.72); color: #fff; font-size: 11px; font-weight: 700; padding: 2px 7px; border-radius: 5px; }
  .title { margin-top: 12px; font-size: 19px; font-weight: 800; }
  .time { font-size: 14px; font-weight: 700; color: #c41e27; margin-top: 2px; }
  .vo { margin-top: 8px; font-size: 14px; font-style: italic; line-height: 1.45; color: #222; }
  .words { margin-top: 8px; font-size: 13px; line-height: 1.5; color: #444; }
  .meta { margin-top: 8px; font-size: 12px; line-height: 1.45; color: #666; } .meta b { color: #141414; }
</style></head><body>
<header><h1>Lauda: the full short, pixel style (${DURATION}s, 1080×1920)</h1>
<p>Ten scenes, each cut just before its line · captions highlight the word being spoken · on-screen text otherwise limited to the DAY counter, P4 and the score boxes · two real frames per scene</p></header>
<div class="grid">
${cards}
</div></body></html>`);

writeFileSync(new URL("../STORYBOARD.md", import.meta.url), `---\nformat: 1080x1920\nduration: ${DURATION}s\nmessage: "The bravest thing Niki Lauda ever did was get out of the car"\n---\n\n` +
  SCENES.map((s, i) => { const n = notes[s.id]; return `## Frame ${i + 1}: ${n.name} (${fmt(s.start)}-${fmt(s.end)}s)\n\n- status: animated\n- scene: ${n.scene}\n- voiceover: ${LINES.filter((l) => l.scene === s.id).map((l) => l.text).join(" ")}\n- sound: ${n.sound}\n`; }).join("\n"));
console.log("board written");
