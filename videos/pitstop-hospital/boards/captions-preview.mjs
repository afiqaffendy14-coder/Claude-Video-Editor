// Caption position preview: the smaller caption at two heights on real frames, before the video is rendered.
import { writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { execSync } from "node:child_process";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const { chromium } = require(join(execSync("npm root -g").toString().trim(), "playwright"));
const frames = [["01", "children's heart surgeon"], ["02", "ask Ferrari for"], ["04", "just survived heart"], ["17", "twenty mechanics change"],
  ["24", "leader runs the"], ["25", "like the lollipop"], ["30", "by 42%"]];
const row = (label, note, top) => `<section><h2>${label}</h2><p>${note}</p><div class="row">${frames.map(([n, t]) =>
  `<figure><img src="graded/s${n}.png"/><div class="cap" style="top:${top}%">${t}</div><span class="n">${n}</span></figure>`).join("")}</div></section>`;
const html = `<!doctype html><html><head><meta charset="UTF-8"><title>Caption Position Preview</title><style>
@font-face { font-family: M; src: url(../assets/fonts/montserrat-latin-900-normal.woff2); font-weight: 900; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #f2f2f0; font-family: Inter, system-ui, sans-serif; color: #141414; padding: 36px; width: 2160px; }
h1 { font: 900 40px M, sans-serif; } header p { color: #555; font-size: 19px; margin-top: 8px; }
section { margin-top: 30px; } h2 { font: 900 28px M, sans-serif; } section p { color: #555; font-size: 17px; margin: 4px 0 12px; }
.row { display: grid; grid-template-columns: repeat(7, 1fr); gap: 12px; } figure { position: relative; overflow: hidden; border-radius: 10px; }
img { width: 100%; display: block; }
/* frames are 540 wide here at ~290px: 0.062 x width = the caption size on a 1080 x 1920 video (67px) */
.cap { position: absolute; left: 8%; right: 8%; text-align: center; font: 900 18px/1.1 M, sans-serif; color: #fff;
  -webkit-text-stroke: 4px #000; paint-order: stroke fill; text-shadow: 0 2px 3px rgba(0,0,0,.35); transform: translateY(-50%); }
.n { position: absolute; left: 6px; top: 6px; background: rgba(0,0,0,.7); color: #fff; font: 800 12px Inter, sans-serif; padding: 2px 6px; border-radius: 4px; }
</style></head><body><header><h1>Caption position preview</h1>
<p>Smaller captions (about 30% smaller than the test clip) · Montserrat Black, black outline · shown on real frames from 7 different shots</p></header>
${row("A · Lower third (my pick)", "Sits below the faces and the action in almost every shot, and above where YouTube Shorts / TikTok put the title and buttons.", 74)}
${row("B · Top", "Clear of the action at the bottom, but closer to faces in close-ups, and the platforms' top bar can sit near it.", 17)}
</body></html>`;
const f = join(here, "captions-preview.html");
writeFileSync(f, html);
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 2160, height: 900 } });
await p.goto("file://" + f);
await p.evaluate(() => document.fonts.ready);
await p.screenshot({ path: join(here, "captions-preview.png"), fullPage: true });
await b.close();
console.log("ok");
