// Turns the schedule into absolute sound cue times (tools/cues.json). The beat formulas mirror
// scene/scenes.js so every sound lands on its picture.
import { writeFileSync } from "node:fs";
import { SCENES, LINES, DURATION } from "../scene/schedule.js";

const sc = Object.fromEntries(SCENES.map((s) => [s.id, s]));
const cue = (id, n) => LINES.filter((l) => l.scene === id)[n].start; // absolute
const inOut = (x) => { x = Math.min(1, Math.max(0, x)); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const C = { duration: DURATION, scenes: SCENES, beeps: [], coins: [], whoosh: [] };

// heart monitor: hook (54 bpm), comeback hospital part (72), hospital scene (104 irregular → 64)
for (let t = 0.35; t < sc.hook.end; t += 60 / 54) C.beeps.push([+t.toFixed(3), 0]);
const cbCut = cue("comeback", 1) - 0.15;
for (let t = sc.comeback.start + 0.2; t < cbCut; t += 60 / 72) C.beeps.push([+t.toFixed(3), 0]);
const recover = cue("hospital", 2);
for (let t = sc.hospital.start + 0.15, i = 0; t < sc.hospital.end; i++) {
  C.beeps.push([+t.toFixed(3), t < recover ? 1 : 0]);
  t += t < recover ? (60 / 104) * (0.8 + 0.45 * ((i * 37) % 7) / 7) : 60 / 64;
}
// DAY counter: a coin blip each time the number changes, power-up on 42
const u0 = sc.comeback.start, span = Math.max(0.3, cbCut - u0 - 0.45);
let last = 0;
for (let t = u0; t < cbCut; t += 1 / 120) {
  const day = Math.min(42, Math.round(42 * inOut((t - u0 - 0.15) / span)));
  if (day !== last && (!C.coins.length || t - C.coins[C.coins.length - 1] > 0.035)) C.coins.push(+t.toFixed(3));
  if (day === 42 && !C.powerUp) C.powerUp = +t.toFixed(3);
  last = day;
}
C.gridIdle = [cbCut, sc.loop.start + 0.25];
C.launch = sc.loop.start + 0.25;
C.musicDrop = [sc.loop.start + 0.5, sc.ring.start];
C.ring = [sc.ring.start, sc.ring.end];
// crash
const impact = cue("crash", 1) + 0.95, stop = cue("crash", 2) - 0.35;
Object.assign(C, { crashApproach: [sc.crash.start, impact], skid: impact - 0.55, impact, fire: [impact, sc.crash.end], otherCar: stop - 0.6, runners: [stop, stop + 0.9] });
// Monza
const mzFinish = cue("monza", 1) - 0.15;
Object.assign(C, { helmetSeat: sc.monza.start + 0.4 + (mzFinish - sc.monza.start - 0.9), monzaPass: mzFinish, fanfare: mzFinish + 0.35 });
// Fuji / pits / end
C.rival1 = cue("fuji", 1) - 0.5;
C.scorePop = cue("fuji", 1) + 0.2;
C.rainHeavy = cue("fuji", 2);
C.arrive = cue("pits", 1) - 0.6;
C.engineCut = cue("pits", 2) - 0.35;
C.rival2 = cue("pits", 3) - 0.6;
C.scoreFlip = cue("pits", 3);
C.sad = cue("pits", 4);
const finalShot = cue("end", 2) - 0.3;
C.steps = [];
for (let t = cue("pits", 2); t < finalShot - 0.6; t += 0.36) C.steps.push(+t.toFixed(3));
C.finalShot = finalShot;
C.endBeep = finalShot + 0.25;
C.rain = [[0, cbCut, "glass"], [sc.hospital.start, sc.hospital.end, "glass"], [sc.fuji.start, DURATION, "open"]];
SCENES.slice(1).forEach((s) => C.whoosh.push(s.start));
writeFileSync(new URL("./cues.json", import.meta.url), JSON.stringify(C, null, 1));
console.log("cues:", C.beeps.length, "beeps,", C.coins.length, "coins, impact", impact.toFixed(2), "steps", C.steps.length);
