// Shorts thumbnail (1080x1920): the hero render (blender/thumb_roman.py: the halo on the front half of Grosjean's car
// in the torn barrier, the bent rail over it, the fire behind), "THIS saved F1 drivers' lives" over the grandstand
// at the top, an arrow down onto the halo.
// Run: node tools/thumb.mjs <hero.png> <out.png>
import { writeFileSync } from "fs";
import { createRequire } from "module";
import { execSync } from "child_process";
import { dirname, join, resolve } from "path";
import { fileURLToPath, pathToFileURL } from "url";
const here = dirname(fileURLToPath(import.meta.url));
const { chromium } = createRequire(import.meta.url)(join(execSync("npm root -g").toString().trim(), "playwright"));
const [hero, out] = process.argv.slice(2).map((p) => resolve(p));
const font = pathToFileURL(join(here, "../assets/fonts/montserrat-latin-900-normal.woff2")).href;
const html = `<!doctype html><html><head><meta charset="utf-8"><style>
@font-face { font-family: M; src: url(${font}); font-weight: 900; }
html, body { margin: 0; width: 1080px; height: 1920px; overflow: hidden; background: #0b0f12; }
.img { position: absolute; inset: 0; background: url(${pathToFileURL(hero).href}) center / cover;
       transform: scale(1.04); transform-origin: 50% 58%; }
.shade { position: absolute; inset: 0;
  background: linear-gradient(to bottom, rgba(5,12,14,.78) 0%, rgba(5,12,14,.45) 22%, rgba(0,0,0,0) 40%, rgba(0,0,0,0) 78%, rgba(0,0,0,.45) 100%),
              radial-gradient(ellipse at 45% 55%, rgba(0,0,0,0) 50%, rgba(0,0,0,.4) 100%); }
.q { position: absolute; left: 0; right: 0; top: 110px; text-align: center; transform: rotate(-3deg);
     font: 900 118px/0.98 M, sans-serif; color: #fff; text-transform: uppercase; letter-spacing: -3px; white-space: nowrap;
     -webkit-text-stroke: 22px #000; paint-order: stroke fill; filter: drop-shadow(0 12px 20px rgba(0,0,0,.6)); }
.q .big { display: block; color: #ffd60a; font-size: 290px; letter-spacing: 4px; margin-bottom: 6px; }
/* from the words down to the halo: THIS */
.arrow { position: absolute; left: 860px; top: 760px; width: 300px; height: 30px; background: #ffd60a; border-radius: 15px;
         transform: rotate(128deg); transform-origin: 0 50%; box-shadow: 0 0 0 8px #000; }
.arrow::after { content: ""; position: absolute; right: -18px; top: -38px; border-left: 72px solid #ffd60a;
         border-top: 53px solid transparent; border-bottom: 53px solid transparent; filter: drop-shadow(7px 0 0 #000); }
</style></head><body>
<div class="img"></div><div class="shade"></div><div class="arrow"></div>
<div class="q"><span class="big">This</span>saved F1<br>drivers' lives</div>
</body></html>`;
const page_file = join(dirname(out), "thumb.html");
writeFileSync(page_file, html);
const b = await chromium.launch(process.platform === "win32" ? { channel: "msedge" } : {});
const page = await b.newPage({ viewport: { width: 1080, height: 1920 } });
await page.goto(pathToFileURL(page_file).href);
await page.evaluate(() => document.fonts.ready);
await page.screenshot({ path: out });
await b.close();
console.log("wrote", out);
