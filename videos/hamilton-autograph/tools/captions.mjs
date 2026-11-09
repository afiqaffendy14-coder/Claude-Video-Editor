// Caption overlays for "Phone me in nine years": one transparent PNG per chunk (up to 3 words, a chunk ends at
// punctuation), Montserrat Black, white with a black outline, lower third.
// Owner's notes (animation stage):
//  - shot 1 (0-3.51 s): no captions below; a title box at the top instead (TITLE), so the eye stays on it;
//  - shot 3 (6.39-8.12 s): no captions: the handwriting on the page says the same words;
//  - ages are not big stamps: a small "(age 13)" / "(age 23)" line under the caption as those shots begin.
// Writes <out>/cNN.png, <out>/title.png and <out>/captions.json.
//   node tools/captions.mjs <out_dir> <width> <height>
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { execSync } from "node:child_process";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const { chromium } = require(join(execSync("npm root -g").toString().trim(), "playwright"));
const [outArg, W, H] = process.argv.slice(2);
const out = resolve(outArg);
mkdirSync(out, { recursive: true });
const END = 48.3 + 5 / 30;  // round 5: 5 frames of air before "At the track"
const TITLE = "A 10-year-old Black boy<br>asked a F1 boss<br>for a job.";  // drawn as a Minecraft-style box by tools/title_mc.py
const SILENT = [[0, 3.51], [6.39, 8.12]];          // no lower captions during these shots
const AGE = [];  // no age labels (owner: viewers can follow without them)
const quiet = (t) => SILENT.some(([a, b]) => t >= a - 1e-3 && t < b - 1e-3);

const words = JSON.parse(readFileSync(join(here, "timing.json"))).lines.flatMap((l) => l.words).filter((w) => !quiet(w.start));
const chunks = [];
let cur = [];
for (const w of words) {
  // a chunk never runs across a silent stretch or a shot that starts an age line
  if (cur.length && (SILENT.some(([a]) => cur[0].start < a - 0.02 && w.start >= a - 0.02) || AGE.some(([a]) => cur[0].start < a - 0.02 && w.start >= a - 0.02))) {
    chunks.push(cur); cur = [];
  }
  cur.push(w);
  if (cur.length === 3 || /[,.?!…:"]$/.test(w.w)) { chunks.push(cur); cur = []; }
}
if (cur.length) chunks.push(cur);
const list = chunks.map((c, i) => {
  let end = i + 1 < chunks.length ? chunks[i + 1][0].start : END;
  const gap = SILENT.find(([a]) => c[0].start < a && end > a);
  if (gap) end = gap[0];
  const age = AGE.find(([a]) => c[0].start >= a - 0.02 && (i === 0 || chunks[i - 1][0].start < a - 0.02));  // first chunk of the shot only
  return { text: c.map((w) => w.w).join(" ").replace(/[,.:]$/, "").replace(/"/g, ""), start: c[0].start, end, age: age ? age[2] : "" };
});
const font = pathToFileURL(join(here, "../assets/fonts/montserrat-latin-900-normal.woff2")).href;
const size = Math.round(+W * 0.062);
const browser = await chromium.launch(process.platform === "win32" ? { channel: "msedge" } : {});
const page = await browser.newPage({ viewport: { width: +W, height: +H } });
const shot = async (body, css, file) => {
  const html = join(out, "cap.html");  // loaded from disk so the local font file is allowed to load
  writeFileSync(html, `<!doctype html><html><head><meta charset="utf-8"><style>
    @font-face { font-family: M; src: url(${font}); font-weight: 900; }
    html, body { margin: 0; background: transparent; width: ${W}px; height: ${H}px; }
    ${css}</style></head><body>${body}</body></html>`);
  await page.goto(pathToFileURL(html).href);
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: file, omitBackground: true });
};
const capCss = `div.c { position: absolute; left: 8%; right: 8%; top: 74%; transform: translateY(-50%); text-align: center; font: 900 ${size}px/1.1 M, sans-serif;
      color: #fff; -webkit-text-stroke: ${Math.round(size * 0.22)}px #000; paint-order: stroke fill;
      text-shadow: 0 ${Math.round(size * 0.1)}px ${Math.round(size * 0.2)}px rgba(0,0,0,.35); }
    div.a { display: block; margin-top: ${Math.round(size * 0.28)}px; font-size: ${Math.round(size * 0.55)}px; -webkit-text-stroke: ${Math.round(size * 0.13)}px #000; color: #e9e9e9; }`;
const meta = [];
for (const [i, c] of list.entries()) {
  const f = join(out, `c${String(i).padStart(2, "0")}.png`);
  await shot(`<div class="c">${c.text}${c.age ? `<div class="a">${c.age}</div>` : ""}</div>`, capCss, f);
  meta.push({ file: f, start: c.start, end: c.end, text: c.text + (c.age ? " " + c.age : "") });
}
// the title box for shot 1: white card, black type, a red edge (the book's red), top of the frame
const ts = Math.round(+W * 0.058);
const title = join(out, "title.png");
await shot(`<div class="t">${TITLE}</div>`, `div.t { position: absolute; left: 7%; right: 7%; top: 5%; padding: ${Math.round(ts * 0.55)}px ${Math.round(ts * 0.6)}px;
    background: #fff; color: #111; border-radius: ${Math.round(ts * 0.35)}px; border-left: ${Math.round(ts * 0.28)}px solid #b3121a;
    font: 900 ${ts}px/1.12 M, sans-serif; text-align: center; box-shadow: 0 ${Math.round(ts * 0.2)}px ${Math.round(ts * 0.6)}px rgba(0,0,0,.45); }`, title);
meta.unshift({ file: title, start: 0, end: 3.51, text: TITLE.replaceAll("<br>", " "), kind: "title" });
await browser.close();
writeFileSync(join(out, "captions.json"), JSON.stringify(meta, null, 1));
console.log(meta.length, "overlays");
for (const m of meta) console.log(m.start.toFixed(2), m.end.toFixed(2), m.text);
