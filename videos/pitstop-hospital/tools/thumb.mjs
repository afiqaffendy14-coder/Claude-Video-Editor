// Shorts thumbnail (1080x1920): two graded stills split on a slant, the title big across the seam.
// Run: node tools/thumb.mjs <top.png> <bottom.png> <out.png>
import { writeFileSync } from "fs";
import { createRequire } from "module";
import { execSync } from "child_process";
import { dirname, join, resolve } from "path";
import { fileURLToPath } from "url";
const here = dirname(fileURLToPath(import.meta.url));
const { chromium } = createRequire(import.meta.url)(join(execSync("npm root -g").toString().trim(), "playwright"));
const [top, bottom, out] = process.argv.slice(2).map((p) => resolve(p));
const font = "file://" + join(here, "../assets/fonts/montserrat-latin-900-normal.woff2");
const html = `<!doctype html><html><head><style>
@font-face { font-family: M; src: url(${font}); font-weight: 900; }
html, body { margin: 0; width: 1080px; height: 1920px; overflow: hidden; background: #111; }
.box { position: absolute; left: 0; width: 1080px; height: 1060px; overflow: hidden; }
.box img { position: absolute; }
.top { top: 0; clip-path: polygon(0 0, 100% 0, 100% 86%, 0 100%); }
.top img { width: 1300px; left: -110px; top: -700px; }
.bot { top: 860px; clip-path: polygon(0 15%, 100% 0, 100% 100%, 0 100%); }
.bot img { width: 1150px; left: -35px; top: -470px; }
.seam { position: absolute; left: -40px; right: -40px; top: 952px; height: 18px; background: #e10600; transform: rotate(-8.6deg); box-shadow: 0 0 30px rgba(0,0,0,.6); }
.t { position: absolute; left: 40px; right: 40px; top: 50%; transform: translateY(-50%) rotate(-4deg); text-align: center;
     font: 900 104px/1.02 M, sans-serif; color: #fff; text-transform: uppercase; letter-spacing: -1px;
     -webkit-text-stroke: 22px #000; paint-order: stroke fill; filter: drop-shadow(0 10px 18px rgba(0,0,0,.7)); }
.t .f { color: #ffd60a; font-size: 142px; display: block; margin-top: 4px; }
</style></head><body>
<div class="box bot"><img src="file://${bottom}"></div><div class="box top"><img src="file://${top}"></div><div class="seam"></div>
<div class="t">Why did surgeons<span class="f">call Ferrari?</span></div>
</body></html>`;
const page_file = join(dirname(out), "thumb.html");
writeFileSync(page_file, html);
const b = await chromium.launch();
const page = await b.newPage({ viewport: { width: 1080, height: 1920 } });
await page.goto("file://" + page_file);
await page.evaluate(() => document.fonts.ready);
await page.screenshot({ path: out });
await b.close();
console.log("wrote", out);
