// Style sheet: two hero frames (pit stop, hospital handover) at two low-poly densities, with a caption sample.
import { writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { execSync } from "node:child_process";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const { chromium } = require(join(execSync("npm root -g").toString().trim(), "playwright"));
const opt = (lv, title, note) => `<section><h2>${title}</h2><p>${note}</p><div class="row">
  <figure><img src="style/pit_low${lv}.png"/><div class="cap">Twenty mechanics</div></figure>
  <figure><img src="style/icu_low${lv}.png"/><div class="cap">One leader</div></figure></div></section>`;
const html = `<!doctype html><html><head><meta charset="UTF-8"><title>Pit Stop Hospital Style</title><style>
@font-face { font-family: M; src: url(../assets/fonts/montserrat-latin-900-normal.woff2); font-weight: 900; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #f2f2f0; font-family: Inter, system-ui, sans-serif; color: #141414; padding: 40px; width: 1760px; }
h1 { font: 900 44px M, sans-serif; } header p { color: #555; font-size: 20px; margin-top: 8px; }
.opts { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; margin-top: 28px; }
h2 { font: 900 30px M, sans-serif; } section p { color: #555; font-size: 17px; margin: 6px 0 14px; line-height: 1.4; }
.row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; } figure { position: relative; }
img { width: 100%; display: block; border-radius: 12px; }
.cap { position: absolute; left: 0; right: 0; top: 60%; text-align: center; font: 900 38px/1.1 M, sans-serif; color: #fff;
  -webkit-text-stroke: 10px #000; paint-order: stroke fill; text-shadow: 0 4px 8px rgba(0,0,0,.35); }
</style></head><body><header><h1>Style test: low poly, video-game look</h1>
<p>Blender 3D · faceted shapes, flat colours, crisp sun shadows · red is the only accent (Ferrari) · teal for the hospital · Montserrat Black captions with black outline</p></header>
<div class="opts">${opt(1, "A · Smooth low poly", "More facets: rounded but clearly polygonal. Closest to a modern indie game.")}
${opt(2, "B · Chunky low poly", "Fewer, bigger facets: boxier limbs and heads. More retro, more 'game' at a glance.")}</div></body></html>`;
const f = join(here, "style.html");
writeFileSync(f, html);
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1760, height: 900 } });
await p.goto("file://" + f);
await p.evaluate(() => document.fonts.ready);
await p.screenshot({ path: join(here, "style.png"), fullPage: true });
await b.close();
console.log("ok");
