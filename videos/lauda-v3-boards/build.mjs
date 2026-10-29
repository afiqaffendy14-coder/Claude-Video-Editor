// Builds the side-by-side storyboard (pixel | Three.js) for the v3 short, in two pages.
import { readdirSync, writeFileSync } from "node:fs";
import { readFileSync } from "node:fs";
import { SHOTS, DURATION } from "../lauda-v3-pixel/scene/timeline.js";
const WORDS = JSON.parse(readFileSync("../lauda-v3-pixel/tools/timing.json")).lines.flatMap((l) => l.words);

const still = (dir, i) => {
  const f = readdirSync(dir).find((n) => n.startsWith(`frame-${String(i).padStart(2, "0")}-`));
  return f;
};
const said = (s) => WORDS.filter((w) => w.start >= s.start - 1e-3 && w.start < s.end - 1e-3).map((w) => w.w).join(" ");
const card = (s, i) => `<div class="card">
  <div class="pair">
    <figure><img src="../lauda-v3-pixel/boards/stills/${still("../lauda-v3-pixel/boards/stills", i)}"/><figcaption>PIXEL</figcaption></figure>
    <figure><img src="../lauda-v3-3d/boards/stills/${still("../lauda-v3-3d/boards/stills", i)}"/><figcaption>THREE.JS</figcaption></figure>
  </div>
  <div class="head"><span class="n">${String(s.n).padStart(2, "0")}</span><span class="t">${s.start.toFixed(2)}–${s.end.toFixed(2)}s · ${(s.end - s.start).toFixed(1)}s</span></div>
  <p class="vo">“${said(s)}”</p>
  <p class="d">${s.desc}</p>
</div>`;
const page = (from, to, label) => `<!doctype html><html><head><meta charset="UTF-8"><title>Lauda v3 Storyboard</title><style>
@font-face { font-family: M; src: url(../lauda-v3-pixel/assets/fonts/montserrat-latin-900-normal.woff2); font-weight: 900; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #f2f2f0; font-family: Inter, system-ui, sans-serif; color: #141414; padding: 36px; width: 2400px; }
h1 { font: 900 40px M, sans-serif; letter-spacing: -0.01em; } header p { color: #555; font-size: 18px; margin-top: 8px; }
.grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 18px; margin-top: 24px; }
.card { background: #fff; border-radius: 16px; padding: 12px; box-shadow: 0 5px 18px rgba(0,0,0,.07); }
.pair { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; } figure { position: relative; }
img { width: 100%; display: block; border-radius: 7px; } figcaption { position: absolute; left: 5px; top: 5px; background: rgba(0,0,0,.75); color: #fff; font: 800 10px Inter, sans-serif; padding: 2px 6px; border-radius: 4px; letter-spacing: .05em; }
.head { display: flex; justify-content: space-between; align-items: baseline; margin-top: 10px; }
.n { font: 900 22px M, sans-serif; } .t { font-size: 13px; font-weight: 700; color: #c41e27; }
.vo { margin-top: 6px; font-size: 14px; font-style: italic; line-height: 1.4; } .d { margin-top: 6px; font-size: 12.5px; line-height: 1.45; color: #555; }
</style></head><body><header><h1>Lauda v3 — storyboard ${label} (pixel | Three.js)</h1>
<p>${DURATION}s · 36 hard cuts, every 0.9–3.0s · continuous voiceover · Montserrat Black captions with a black outline · both styles, every shot</p></header>
<div class="grid">${SHOTS.slice(from, to).map((s, k) => card(s, from + k)).join("\n")}</div></body></html>`;
writeFileSync("storyboard-1.html", page(0, 18, "1/2 (shots 1–18)"));
writeFileSync("storyboard-2.html", page(18, 36, "2/2 (shots 19–36)"));
console.log("ok");
