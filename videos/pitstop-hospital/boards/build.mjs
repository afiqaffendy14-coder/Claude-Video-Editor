// Storyboard pages for the pit-stop hospital short: 36 Blender stills with the caption that is on screen
// mid-shot (Montserrat Black, black outline), the voiceover said during the shot, and the shot description.
//   node boards/build.mjs   (after blender/shots.py board + json)
import { readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { execSync } from "node:child_process";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const { chromium } = require(join(execSync("npm root -g").toString().trim(), "playwright"));
const SHOTS = JSON.parse(readFileSync(join(here, "shots.json")));
const WORDS = JSON.parse(readFileSync(join(here, "../tools/timing.json"))).lines.flatMap((l) => l.words);

// caption chunks: up to 3 words, a chunk ends at punctuation
const CHUNKS = [];
let cur = [];
for (const w of WORDS) {
  cur.push(w);
  if (cur.length === 3 || /[,.?!…]$/.test(w.w)) { CHUNKS.push(cur); cur = []; }
}
if (cur.length) CHUNKS.push(cur);
const chunkAt = (t) => {
  let best = CHUNKS[0];
  for (const c of CHUNKS) if (c[0].start <= t) best = c;
  return best.map((w) => w.w).join(" ").replace(/[,.]$/, "");
};
const said = (s) => WORDS.filter((w) => w.start >= s.start - 1e-3 && w.start < s.end - 1e-3).map((w) => w.w).join(" ");

const card = (s) => `<div class="card">
  <figure><img src="stills/s${String(s.n).padStart(2, "0")}.png"/><div class="cap">${chunkAt((s.start + s.end) / 2)}</div></figure>
  <div class="head"><span class="n">${String(s.n).padStart(2, "0")}</span><span class="t">${s.start.toFixed(2)}–${s.end.toFixed(2)}s · ${(s.end - s.start).toFixed(1)}s</span></div>
  <p class="vo">“${said(s)}”</p>
  <p class="d">${s.desc}</p>
</div>`;
const page = (from, to, label) => `<!doctype html><html><head><meta charset="UTF-8"><title>Pit Stop Hospital Storyboard</title><style>
@font-face { font-family: M; src: url(../assets/fonts/montserrat-latin-900-normal.woff2); font-weight: 900; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #f2f2f0; font-family: Inter, system-ui, sans-serif; color: #141414; padding: 36px; width: 2400px; }
h1 { font: 900 40px M, sans-serif; } header p { color: #555; font-size: 18px; margin-top: 8px; }
.grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 18px; margin-top: 24px; }
.card { background: #fff; border-radius: 16px; padding: 12px; box-shadow: 0 5px 18px rgba(0,0,0,.07); }
figure { position: relative; } img { width: 100%; display: block; border-radius: 8px; }
.cap { position: absolute; left: 0; right: 0; top: 58%; text-align: center; font: 900 25px/1.1 M, sans-serif; color: #fff;
  -webkit-text-stroke: 7px #000; paint-order: stroke fill; text-shadow: 0 3px 6px rgba(0,0,0,.35); padding: 0 8px; }
.head { display: flex; justify-content: space-between; align-items: baseline; margin-top: 10px; }
.n { font: 900 22px M, sans-serif; } .t { font-size: 13px; font-weight: 700; color: #c41e27; }
.vo { margin-top: 6px; font-size: 14px; font-style: italic; line-height: 1.4; } .d { margin-top: 6px; font-size: 12.5px; line-height: 1.45; color: #555; }
</style></head><body><header><h1>Why would a children's heart surgeon ask Ferrari for help? — storyboard ${label}</h1>
<p>60.0 s · 35 hard cuts, every 1–2.5 s · F1 Narrator voiceover (take 1), cuts on the spoken words · blocky Blender 3D · Montserrat Black captions with a black outline</p></header>
<div class="grid">${SHOTS.slice(from, to).map(card).join("\n")}</div></body></html>`;

const browser = await chromium.launch();
const pg = await browser.newPage({ viewport: { width: 2400, height: 1000 } });
for (const [i, from, to, label] of [[1, 0, 18, "1/2 (shots 1–18)"], [2, 18, 35, "2/2 (shots 19–35)"]]) {
  const f = join(here, `storyboard-${i}.html`);
  writeFileSync(f, page(from, to, label));
  await pg.goto("file://" + f);
  await pg.evaluate(() => document.fonts.ready);
  await pg.screenshot({ path: join(here, `storyboard-${i}.png`), fullPage: true });
}
await browser.close();
console.log("ok");
