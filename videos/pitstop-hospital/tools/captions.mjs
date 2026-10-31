// Caption overlays: one transparent PNG per chunk (up to 3 words, a chunk ends at punctuation), Montserrat Black,
// white with a black outline, placed in the middle band. Writes <out>/cNN.png and <out>/captions.json.
//   node tools/captions.mjs <out_dir> <width> <height> [t_from] [t_to]
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { execSync } from "node:child_process";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const { chromium } = require(join(execSync("npm root -g").toString().trim(), "playwright"));
const [outArg, W, H, from = "0", to = "60"] = process.argv.slice(2);
const out = resolve(outArg);
mkdirSync(out, { recursive: true });
const words = JSON.parse(readFileSync(join(here, "timing.json"))).lines.flatMap((l) => l.words);
const chunks = [];
let cur = [];
for (const w of words) {
  cur.push(w);
  if (cur.length === 3 || /[,.?!…:]$/.test(w.w)) { chunks.push(cur); cur = []; }
}
if (cur.length) chunks.push(cur);
const list = chunks.map((c, i) => ({
  text: c.map((w) => w.w).join(" ").replace(/[,.:]$/, ""),
  start: c[0].start,
  end: i + 1 < chunks.length ? chunks[i + 1][0].start : 60,
})).filter((c) => c.end > +from && c.start < +to);
const font = "file://" + join(here, "../assets/fonts/montserrat-latin-900-normal.woff2");
const size = Math.round(+W * 0.062);  // smaller, lower third (approved in the caption preview)
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: +W, height: +H } });
const meta = [];
for (const [i, c] of list.entries()) {
  const html = join(out, "cap.html");  // loaded from disk so the local font file is allowed to load
  writeFileSync(html, `<!doctype html><html><head><style>
    @font-face { font-family: M; src: url(${font}); font-weight: 900; }
    html, body { margin: 0; background: transparent; width: ${W}px; height: ${H}px; }
    div { position: absolute; left: 8%; right: 8%; top: 74%; transform: translateY(-50%); text-align: center; font: 900 ${size}px/1.1 M, sans-serif;
      color: #fff; -webkit-text-stroke: ${Math.round(size * 0.22)}px #000; paint-order: stroke fill;
      text-shadow: 0 ${Math.round(size * 0.1)}px ${Math.round(size * 0.2)}px rgba(0,0,0,.35); }
  </style></head><body><div>${c.text}</div></body></html>`);
  await page.goto("file://" + html);
  await page.evaluate(() => document.fonts.ready);
  const f = join(out, `c${String(i).padStart(2, "0")}.png`);
  await page.screenshot({ path: f, omitBackground: true });
  meta.push({ file: f, start: c.start, end: c.end, text: c.text });
}
await browser.close();
writeFileSync(join(out, "captions.json"), JSON.stringify(meta, null, 1));
console.log(meta.length, "captions");
