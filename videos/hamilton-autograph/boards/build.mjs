// Storyboard pages for the Hamilton autograph short (v1): every shot's still or key frames (a, b, c: how the action happens),
// the caption on screen at that moment (Montserrat Black, black outline), the voiceover said during the shot, the
// shot description, and the collision check result for its frames.
//   node boards/build.mjs   (after blender/shots.py board + json, and the stills graded into boards/graded)
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { createRequire } from "node:module";
import { execSync } from "node:child_process";
import { join, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const { chromium } = require(join(execSync("npm root -g").toString().trim(), "playwright"));
// VER=v2 IMG=v2 BURNED=1 node boards/build.mjs : a board for a video preview, from frames taken out of the MP4
// (tools/board_from_video.py), with the captions already burned in and the descriptions from shots_<VER>.json.
const VER = process.env.VER || "v1", IMG = process.env.IMG || "graded", BURNED = !!process.env.BURNED;
const NOTE = process.env.NOTE || "poses and layout only (lighting and grade come later) · every frame collision-checked";
const SHOTS = JSON.parse(readFileSync(join(here, existsSync(join(here, `shots_${VER}.json`)) ? `shots_${VER}.json` : "shots.json")));
const WORDS = JSON.parse(readFileSync(join(here, "../tools/timing.json"))).lines.flatMap((l) => l.words);
const CHECK = VER === "v1" && existsSync(join(here, "check.json")) ? JSON.parse(readFileSync(join(here, "check.json"))) : {};

// caption chunks: up to 3 words, a chunk ends at punctuation
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
const AGE = BURNED ? {} : { 1: "AGE 10", 16: "AGE 13", 17: "AGE 23" };  // on-screen stamps, separate from the captions

const checkNote = (s) => {
  const rs = s.keys.map((k) => CHECK[pad(s.n) + k]).filter(Boolean);
  if (!rs.length) return "";
  const clips = rs.reduce((a, r) => a + r.clips.length, 0), feet = rs.reduce((a, r) => a + r.feet.length, 0);
  return clips + feet === 0 ? `<span class="ok">collision check: clean</span>` : `<span class="bad">check: ${clips} clip(s), ${feet} foot issue(s)</span>`;
};

const card = (s) => {
  const n = s.keys.length;
  const frames = s.keys.map((k, i) => {
    const t = s.start + (s.end - s.start) * (n === 1 ? 0.5 : (i + 0.5) / n);
    return `<figure><img src="${IMG}/s${pad(s.n)}${k}.png"/>${BURNED ? "" : `<div class="cap">${chunkAt(t)}</div>`}${k ? `<span class="key">${k}</span>` : ""}${AGE[s.n] ? `<div class="age">${AGE[s.n]}</div>` : ""}</figure>`;
  }).join("");
  return `<div class="card" style="grid-column: span ${n}">
  <div class="frames" style="grid-template-columns: repeat(${n}, 1fr)">${frames}</div>
  <div class="head"><span class="n">${pad(s.n)}</span><span class="t">${s.start.toFixed(2)}–${s.end.toFixed(2)}s · ${(s.end - s.start).toFixed(1)}s</span></div>
  <p class="vo">“${said(s)}”</p>
  <p class="d">${s.desc}</p>
  <p class="c">${checkNote(s)}</p>
</div>`;
};
const page = (list, label) => `<!doctype html><html><head><meta charset="UTF-8"><title>Phone me in nine years: storyboard ${VER}</title><style>
@font-face { font-family: M; src: url(../assets/fonts/montserrat-latin-900-normal.woff2); font-weight: 900; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #f2f2f0; font-family: Inter, system-ui, sans-serif; color: #141414; padding: 36px; width: 2400px; }
h1 { font: 900 40px M, sans-serif; } header p { color: #555; font-size: 18px; margin-top: 8px; }
.grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 18px; margin-top: 24px; }
.card { background: #fff; border-radius: 16px; padding: 12px; box-shadow: 0 5px 18px rgba(0,0,0,.07); }
.frames { display: grid; gap: 8px; }
figure { position: relative; } img { width: 100%; display: block; border-radius: 8px; }
.key { position: absolute; top: 8px; left: 8px; background: rgba(0,0,0,.65); color: #fff; font: 900 16px M, sans-serif; padding: 2px 9px; border-radius: 6px; }
.cap { position: absolute; left: 0; right: 0; top: 74%; text-align: center; font: 900 22px/1.1 M, sans-serif; color: #fff;
  -webkit-text-stroke: 6px #000; paint-order: stroke fill; text-shadow: 0 3px 6px rgba(0,0,0,.35); padding: 0 8px; }
.age { position: absolute; left: 0; right: 0; top: 9%; text-align: center; font: 900 54px/1 M, sans-serif; color: #ffd21f;
  -webkit-text-stroke: 9px #000; paint-order: stroke fill; letter-spacing: 1px; }
.head { display: flex; justify-content: space-between; align-items: baseline; margin-top: 10px; }
.n { font: 900 22px M, sans-serif; } .t { font-size: 13px; font-weight: 700; color: #c41e27; }
.vo { margin-top: 6px; font-size: 14px; font-style: italic; line-height: 1.4; } .d { margin-top: 6px; font-size: 12.5px; line-height: 1.45; color: #555; }
.c { margin-top: 6px; font-size: 12px; font-weight: 700; } .ok { color: #1f7a3a; } .bad { color: #c41e27; }
</style></head><body><header><h1>Phone me in nine years — storyboard ${VER} ${label}</h1>
<p>${SHOTS[SHOTS.length - 1].end.toFixed(1)} s · 22 shots cut on the spoken words (take 1) · a, b = key frames of the action · shot 7 is a three-panel split screen · ${BURNED ? "frames taken from the video, captions as they appear on screen" : "AGE stamps in yellow, captions in white"} · ${NOTE}</p></header>
<div class="grid">${list.map(card).join("\n")}</div></body></html>`;

// split into pages of about three rows (18 columns of 6)
const pages = [];
let pg = [], cols = 0;
for (const s of SHOTS) {
  const w = s.keys.length;
  if (cols + w > 18 && pg.length) { pages.push(pg); pg = []; cols = 0; }
  pg.push(s); cols += w;
}
if (pg.length) pages.push(pg);

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
console.log("ok", pages.length);
