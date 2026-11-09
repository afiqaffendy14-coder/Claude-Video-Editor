// Shorts thumbnail (1080x1920) for "Phone me in nine years". The hero is blender/thumb_pair.py (graded with the
// ballroom grade into out/thumb_pair_graded.png): the block boy holding his red autograph book, looking up at the
// towering boss who leans down to him. No name, no real face. Over the dark ceiling at the top: "AGE 10" in yellow and
// "asked an F1 boss for a job" in white, with an arrow down onto the boy.
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
html, body { margin: 0; width: 1080px; height: 1920px; overflow: hidden; background: #0b0a0c; }
/* push in on the page a little and move it up under the words */
.img { position: absolute; inset: 0; background: url(${pathToFileURL(hero).href}) center / cover;
       transform: translateY(125px) scale(1.03); transform-origin: 50% 60%; filter: saturate(1.08) contrast(1.04); }
.shade { position: absolute; inset: 0;
  background: linear-gradient(to bottom, rgba(6,4,6,.82) 0%, rgba(6,4,6,.55) 24%, rgba(0,0,0,0) 36%, rgba(0,0,0,0) 72%, rgba(0,0,0,.55) 100%),
              radial-gradient(ellipse at 55% 50%, rgba(0,0,0,0) 48%, rgba(0,0,0,.45) 100%); }
.q { position: absolute; left: 0; right: 0; top: 90px; text-align: center; transform: rotate(-3deg);
     font: 900 92px/1.0 M, sans-serif; color: #fff; text-transform: uppercase; letter-spacing: -2px; white-space: nowrap;
     -webkit-text-stroke: 20px #000; paint-order: stroke fill; filter: drop-shadow(0 12px 20px rgba(0,0,0,.6)); }
.q .big { display: block; color: #ffd60a; font-size: 250px; letter-spacing: 2px; margin-bottom: 10px; }
.arrow { position: absolute; left: 150px; top: 615px; width: 270px; height: 30px; background: #ffd60a; border-radius: 15px;
         transform: rotate(78deg); transform-origin: 0 50%; box-shadow: 0 0 0 8px #000; }
.arrow::after { content: ""; position: absolute; right: -18px; top: -38px; border-left: 72px solid #ffd60a;
         border-top: 53px solid transparent; border-bottom: 53px solid transparent; filter: drop-shadow(7px 0 0 #000); }
</style></head><body>
<div class="img"></div><div class="shade"></div><div class="arrow"></div>
<div class="q"><span class="big">Age 10</span>asked an F1 boss<br>for a job</div>
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
