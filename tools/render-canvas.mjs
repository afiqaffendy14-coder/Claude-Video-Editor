// Direct frame capture for canvas-driven compositions (used when software-GPU capture through
// `hyperframes render` is too slow). Serves a project, seeks every frame with the same
// `hf-seek` event the HyperFrames runtime sends, reads the canvas as JPEG and pipes the frames
// into ffmpeg; then mixes the project's <audio> tags (src, data-start, data-volume) under it.
//
//   node tools/render-canvas.mjs <project-dir> <canvas-id> <out.mp4> [pages=2] [fps=30] [query]
import { createServer } from "node:http";
import { readFile, writeFile, mkdir, rm } from "node:fs/promises";
import { extname, join, normalize, resolve } from "node:path";
import { createRequire } from "node:module";
import { execSync, spawn } from "node:child_process";

const require = createRequire(import.meta.url);
const { chromium } = require(join(execSync("npm root -g").toString().trim(), "playwright"));
const [dir, canvasId, out, pagesArg = "2", fpsArg = "30", query = ""] = process.argv.slice(2);
const root = resolve(dir), PAGES = +pagesArg, FPS = +fpsArg;
const html = await readFile(join(root, "index.html"), "utf8");
const DURATION = +html.match(/data-composition-id="main"[^>]*data-duration="([0-9.]+)"/)[1];
const FRAMES = Math.round(DURATION * FPS);
const types = { ".html": "text/html", ".js": "text/javascript", ".woff2": "font/woff2", ".wav": "audio/wav", ".json": "application/json" };

const server = createServer(async (req, res) => {
  try {
    const p = normalize(join(root, decodeURIComponent(new URL(req.url, "http://x").pathname)));
    if (!p.startsWith(root)) throw new Error("outside");
    res.writeHead(200, { "content-type": types[extname(p)] || "application/octet-stream" });
    res.end(await readFile(p));
  } catch { res.writeHead(404).end(); }
}).listen(0);
const url = `http://localhost:${server.address().port}/index.html${query ? "?" + query : ""}`;

const tmp = join(root, ".hyperframes", "canvas-frames");
await rm(tmp, { recursive: true, force: true });
await mkdir(tmp, { recursive: true });
const browser = await chromium.launch({ args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
const t0 = Date.now();
let done = 0;

async function worker(w) {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on("pageerror", (e) => console.error(`page ${w} error:`, e.message));
  await page.addInitScript(() => { window.__timelines = {}; });
  await page.goto(url);
  await page.waitForFunction(() => window.__filmBuilt || window.__pixelsBuilt, null, { timeout: 300000 });
  for (let f = w; f < FRAMES; f += PAGES) {
    const b64 = await page.evaluate(([t, id]) => {
      window.dispatchEvent(new CustomEvent("hf-seek", { detail: { time: t } }));
      return document.getElementById(id).toDataURL("image/jpeg", 0.95).split(",")[1];
    }, [f / FPS, canvasId]);
    await writeFile(join(tmp, `f${String(f).padStart(5, "0")}.jpg`), Buffer.from(b64, "base64"));
    if (++done % 60 === 0) {
      const rate = done / ((Date.now() - t0) / 1000);
      console.log(`${done}/${FRAMES} frames, ${rate.toFixed(2)} fps, ~${Math.round((FRAMES - done) / rate / 60)} min left`);
    }
  }
  await page.close();
}
await Promise.all(Array.from({ length: PAGES }, (_, w) => worker(w)));
await browser.close();
server.close();

// audio: every <audio> tag with its start offset and volume, mixed without normalisation
const audio = [...html.matchAll(/<audio[^>]*src="([^"]+)"[^>]*data-start="([0-9.]+)"[^>]*?(?:data-volume="([0-9.]+)")?[^>]*><\/audio>/g)].map((m) => ({ src: join(root, m[1]), start: +m[2], vol: m[3] ? +m[3] : 1 }));
const args = ["-y", "-framerate", String(FPS), "-i", join(tmp, "f%05d.jpg")];
audio.forEach((a) => args.push("-i", a.src));
const chains = audio.map((a, i) => `[${i + 1}:a]adelay=${Math.round(a.start * 1000)}:all=1,volume=${a.vol}[a${i}]`);
const mix = `${chains.join(";")};${audio.map((_, i) => `[a${i}]`).join("")}amix=inputs=${audio.length}:normalize=0:duration=longest,atrim=0:${DURATION},alimiter=limit=0.89[aout]`;
args.push("-filter_complex", mix, "-map", "0:v", "-map", "[aout]", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", resolve(out));
await new Promise((ok, fail) => spawn("ffmpeg", args, { stdio: ["ignore", "ignore", "inherit"] }).on("exit", (c) => (c ? fail(new Error(`ffmpeg ${c}`)) : ok())));
console.log(`done: ${out} in ${((Date.now() - t0) / 60000).toFixed(1)} min`);
