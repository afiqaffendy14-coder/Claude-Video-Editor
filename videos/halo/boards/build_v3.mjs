// Storyboard v3 + shot list for the halo short, taken from the animation test itself (out/pframes): every shot as
// three frames from its start, middle and end (how the movement plays), the caption on screen, the voiceover said
// during the shot, what happens, and the review notes (validator flags and known issues).
//   node boards/build_v3.mjs [version] [frames dir under out/]   (default: v4 from out/pframes4)
// Writes boards/storyboard-<version>-N.png and boards/shot-list.md.
import { readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { execSync } from "node:child_process";
import { join, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const { chromium } = require(join(execSync("npm root -g").toString().trim(), "playwright"));
const WORDS = JSON.parse(readFileSync(join(here, "../tools/timing.json"))).lines.flatMap((l) => l.words);
const FPS = 30;
const VER = process.argv[2] || "v4";
const FRAMES = process.argv[3] || "pframes4";

// n, start, end, setting, camera, action, notes
const SHOTS = [
  [1, 0.0, 2.95, "Monza 2021", "POV from Hamilton's cockpit, through the halo; onboard vibration",
    "Continues straight from shot 25 (the loop), then eases from real speed into slow motion: kerb fragments fly, Verstappen's car lifts off the kerb on the right and comes over, its floor and rear tyre filling the top of the frame. The crowds on both sides bob and cheer.", ""],
  [2, 2.95, 4.6, "Monza 2021", "Low close-up on the cockpit, riding with the car (the stands stream past)",
    "The same slow motion as shot 1, still moving: Verstappen's tyre comes down onto the halo, bounces, carbon bits flying; Hamilton's helmet flinches.", ""],
  [3, 4.6, 6.68, "Monza 2021", "From up in the tifosi grandstand, long lens, panning with the cars",
    "The two cars braking side by side toward the chicane, the moving crowd opposite behind them. Ends on the instant shot 4 starts.", ""],
  [4, 6.68, 9.11, "Monza 2021", "Handheld alongside the pair, both cars centred, tight; hard shake on the landing",
    "Real time, chaotic: kerb strike, Verstappen's car flies and rolls over onto Hamilton's halo, carbon fibre everywhere, both slide into the gravel spraying stones - still sliding fast when it cuts.", ""],
  [5, 9.11, 10.68, "Monza gravel", "Close on the halo, riding with the slide",
    "Slow motion, still moving: the rear tyre on the halo's hoop a hand's width above the helmet, the gravel streaming past.", ""],
  [6, 10.68, 12.79, "Monza gravel", "Same framing as shot 5's end, then pulls back round the halo",
    "Still sliding in slow motion from shot 5: the halo glows; Verstappen's car falls away block by block, then Hamilton's car and helmet; just the glowing halo is left, turning.", ""],
  [7, 12.79, 16.03, "Grandstand, 2018", "Travelling just behind a passing car's halo, looking at the stand",
    "The 2018 car with its red halo drives past the tifosi (halo in the foreground); they follow it, boo, shake their heads and wave 'no halo' signs (the halo crossed out in red).", "Validator: one fan's hand 4 cm short"],
  [8, 16.03, 17.42, "Team garage, 2018", "Mid shot over the car",
    "Two drivers look the halo over: one shrugs (hands open, shoulders up), one shakes his head; then they look at each other.", "Validator: clean"],
  [9, 17.42, 19.12, "Car launch stage, 2018", "Front 3/4 of the car, Wolff right behind its cockpit",
    "Wolff talks to the room, a hand opening as he makes his point, a glance down at the halo and back up.", "Validator: clean"],
  [10, 19.12, 21.86, "Car launch stage, 2018", "Same angle as shot 9",
    "Crouched behind the car, he lifts the chainsaw from its case with its weight, rises, turns with two steps and holds it across his body at the halo, leaning back with a grin.",
    "Validator: right foot slides 8 mm once"],
  [11, 21.86, 24.19, "FIA test rig", "Low, looking up into the press",
    "The ram comes down onto the halo; the display on the beam climbs 0t → 3t → 12t.", ""],
  [12, 24.19, 25.58, "Hangar", "Low by the stand, looking up, tilting down with the bus",
    "The crane lowers the red double-decker bus onto the halo; a small rebound, and it holds.", ""],
  [13, 25.58, 27.36, "Bahrain 2020, night", "Down the track under the floodlights",
    "Lap 1: the pack under the floodlights, Grosjean's white car among them.", ""],
  [14, 27.36, 31.48, "Bahrain 2020", "Chase camera along the left edge, braking after the hit",
    "Flat out with the pack, the white car turns sharply right across the track and into the steel barrier: an explosion, the barrier tears open, the car splits - the front half through the steel, the back half thrown spinning away.", ""],
  [15, 31.48, 34.44, "Bahrain 2020", "From above",
    "Continues shot 14: the halves still moving, the fireball dying down into the fire around the back half, debris on the run-off.", ""],
  [16, 34.44, 37.83, "Bahrain 2020", "Close on the front half",
    "The front half sits in the barrier; the top rail rides up over the halo instead of into the helmet.", ""],
  [17, 37.83, 40.71, "Bahrain 2020", "Track side of the barrier",
    "Grosjean grips the top rail, vaults over and lands in a crouch, arms coming down to his sides. A medic runs in from behind, puts a hand on his back and walks out with him.",
    "Validator: shin touches the rail for 1 frame"],
  [18, 40.71, 42.13, "Team garage, 2018", "Mid shot",
    "Grosjean sizes up the new halo, hand at his chin, a slow doubtful shake of the head.", "Validator: clean"],
  [19, 42.13, 45.49, "Studio", "Low, slow push-in",
    "The halo on a plinth under a spotlight, like a trophy.", ""],
  [20, 45.49, 48.91, "Monza 2021", "Low beside the helmet, tilted, riding with the car",
    "Back at Monza, very slow motion, both cars travelling: the rear tyre comes down onto the halo, the helmet flinches, carbon bits fly.", ""],
  [21, 48.91, 50.43, "Monza 2021", "From above, riding with the cars",
    "Still sliding forward: the tyre on the hoop is pushed off onto the engine cover, away from his head.", ""],
  [22, 50.43, 52.62, "Monza gravel", "Mid shot",
    "Hamilton, helmet in hand, rubs the back of his neck (elbow out to the side) and rolls his head, then looks back at the car and breathes out.", "Validator: clean"],
  [23, 52.62, 55.81, "Team garage, race day", "Mid shot",
    "Wolff on the radio (hand to the headset, elbow out and down), listening; a long relieved breath, free hand to his chest, two slow nods; the crew turn to him.", "Validator: clean"],
  [24, 55.81, 57.79, "Car launch stage", "Front on",
    "Wolff (elbows out to the sides) looks down at the chainsaw in his hands, hefts it a touch, then looks up at us with a grin and a small shrug.", "Validator: clean"],
  [25, 57.79, 60.0, "Monza 2021", "POV from Hamilton's cockpit; onboard vibration",
    "Braking for the chicane, Verstappen alongside on the right; his wheels hit the yellow kerb. Loops straight into shot 1.", ""],
].map(([n, start, end, set, cam, action, notes]) => ({ n, start, end, set, cam, action, notes }));

// caption chunks: up to 3 words, a chunk ends at punctuation (same as tools/preview.py)
const CHUNKS = [];
let cur = [];
for (const w of WORDS) {
  cur.push(w);
  if (cur.length === 3 || /[,.?!:…"]$/.test(w.w)) { CHUNKS.push(cur); cur = []; }
}
if (cur.length) CHUNKS.push(cur);
const chunkAt = (t) => {
  let best = CHUNKS[0];
  for (const c of CHUNKS) if (c[0].start <= t) best = c;
  return best.map((w) => w.w).join(" ").replace(/[,.:]$/, "");
};
const said = (s) => WORDS.filter((w) => w.start >= s.start - 1e-3 && w.start < s.end - 1e-3).map((w) => w.w).join(" ");
const pad = (n) => String(n).padStart(2, "0");
const KEYS = [["start", 0.12], ["mid", 0.5], ["end", 0.88]];

const card = (s) => {
  const frames = KEYS.map(([k, f]) => {
    const t = s.start + (s.end - s.start) * f;
    const fr = Math.min(1799, Math.round(t * FPS));
    return `<figure><img src="../out/${FRAMES}/f${String(fr).padStart(5, "0")}.png"/><div class="cap">${chunkAt(t)}</div>
      <span class="key">${k} · ${t.toFixed(1)}s</span></figure>`;
  }).join("");
  return `<div class="card">
  <div class="frames">${frames}</div>
  <div class="head"><span class="n">${pad(s.n)}</span><span class="set">${s.set}</span><span class="t">${s.start.toFixed(2)}–${s.end.toFixed(2)}s · ${(s.end - s.start).toFixed(1)}s</span></div>
  <p class="vo">“${said(s)}”</p>
  <p class="d"><b>Camera:</b> ${s.cam}. <b>Action:</b> ${s.action}</p>
  ${s.notes ? `<p class="c">${s.notes}</p>` : ""}
</div>`;
};
const page = (list, label) => `<!doctype html><html><head><meta charset="UTF-8"><title>Halo Storyboard ${VER}</title><style>
@font-face { font-family: M; src: url(../assets/fonts/montserrat-latin-900-normal.woff2); font-weight: 900; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #f2f2f0; font-family: Inter, system-ui, sans-serif; color: #141414; padding: 36px; width: 2400px; }
h1 { font: 900 40px M, sans-serif; } header p { color: #555; font-size: 20px; margin-top: 8px; }
.grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 22px; margin-top: 24px; }
.card { background: #fff; border-radius: 16px; padding: 14px; box-shadow: 0 5px 18px rgba(0,0,0,.07); }
.frames { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
figure { position: relative; } img { width: 100%; display: block; border-radius: 8px; }
.key { position: absolute; top: 8px; left: 8px; background: rgba(0,0,0,.65); color: #fff; font: 900 16px M, sans-serif; padding: 2px 9px; border-radius: 6px; }
.cap { position: absolute; left: 0; right: 0; top: 74%; text-align: center; font: 900 26px/1.1 M, sans-serif; color: #fff;
  -webkit-text-stroke: 7px #000; paint-order: stroke fill; padding: 0 8px; }
.head { display: flex; gap: 16px; align-items: baseline; margin-top: 12px; }
.n { font: 900 30px M, sans-serif; } .set { font-size: 18px; font-weight: 700; } .t { margin-left: auto; font-size: 17px; font-weight: 700; color: #c41e27; }
.vo { margin-top: 8px; font-size: 20px; font-style: italic; line-height: 1.4; } .d { margin-top: 8px; font-size: 18px; line-height: 1.45; color: #444; }
.c { margin-top: 8px; font-size: 16px; font-weight: 700; color: #b05a00; }
</style></head><body><header><h1>Imagine a Formula One car landing on your head: storyboard ${VER} ${label}</h1>
<p>Frames from the 60 s animation test v2 ·start / middle / end of each shot · movement pass (lighting, colour and effects come later) · orange = open review notes</p></header>
<div class="grid">${list.map(card).join("\n")}</div></body></html>`;

const PER = 8;
const pages = [];
for (let i = 0; i < SHOTS.length; i += PER) pages.push(SHOTS.slice(i, i + PER));
if (pages.length > 1 && pages[pages.length - 1].length === 1) pages[pages.length - 2].push(...pages.pop());

const browser = await chromium.launch(process.platform === "win32" ? { channel: "msedge" } : {});
const tab = await browser.newPage({ viewport: { width: 2400, height: 1000 } });
for (let i = 0; i < pages.length; i++) {
  const p = pages[i];
  const f = join(here, `storyboard-${VER}-${i + 1}.html`);
  writeFileSync(f, page(p, `${i + 1}/${pages.length} (shots ${p[0].n}–${p[p.length - 1].n})`));
  await tab.goto(pathToFileURL(f).href);
  await tab.evaluate(() => document.fonts.ready);
  await tab.screenshot({ path: join(here, `storyboard-${VER}-${i + 1}.png`), fullPage: true });
}
await browser.close();

const md = [
  `# Halo short: shot list (${VER}, from animation test v2)`,
  "",
  "60.0 s · 25 shots cut on the spoken words (take 2) · loops from shot 25 back to shot 1.",
  "",
  "| # | Time | Len | Setting | Camera | Voiceover | Action | Open notes |",
  "|---|------|-----|---------|--------|-----------|--------|------------|",
  ...SHOTS.map((s) => `| ${s.n} | ${s.start.toFixed(2)}–${s.end.toFixed(2)} | ${(s.end - s.start).toFixed(1)}s | ${s.set} | ${s.cam} | “${said(s).replace(/\|/g, "/")}” | ${s.action} | ${s.notes || "–"} |`),
  "",
].join("\n");
writeFileSync(join(here, "shot-list.md"), md);
console.log("ok", pages.length);
