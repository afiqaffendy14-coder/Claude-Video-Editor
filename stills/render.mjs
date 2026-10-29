// Render a still page to PNG:  node stills/render.mjs fuji-1976 [quality] [out.png]
// Serves the repo over HTTP (ES modules need it), opens the page headless, waits for
// window.__done, then saves the canvas pixels.
import { createServer } from "node:http";
import { readFile, writeFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { createRequire } from "node:module";
import { execSync } from "node:child_process";

// Playwright from the project if installed, else the machine's global install.
const require = createRequire(import.meta.url);
let chromium;
try {
  ({ chromium } = require("playwright"));
} catch {
  ({ chromium } = require(join(execSync("npm root -g").toString().trim(), "playwright")));
}

const [name = "fuji-1976", q = "1", out = `out/${name}.png`] = process.argv.slice(2);
const root = new URL("..", import.meta.url).pathname;
const types = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".json": "application/json", ".png": "image/png", ".wav": "audio/wav" };
const server = createServer(async (req, res) => {
  try {
    const path = normalize(join(root, decodeURIComponent(new URL(req.url, "http://x").pathname)));
    if (!path.startsWith(root)) throw new Error("outside root");
    res.writeHead(200, { "content-type": types[extname(path)] || "application/octet-stream" });
    res.end(await readFile(path));
  } catch {
    res.writeHead(404).end();
  }
}).listen(0);
const port = server.address().port;

const browser = await chromium.launch({ args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
const page = await browser.newPage();
page.on("console", (m) => m.type() === "error" && console.error("page:", m.text()));
page.on("pageerror", async (e) => {
  console.error("page error:", e.message);
  await browser.close();
  server.close();
  process.exit(1);
});
const t0 = Date.now();
await page.goto(`http://localhost:${port}/stills/${name}/index.html?q=${q}`);
await page.waitForFunction(() => window.__done === true, null, { timeout: 30 * 60 * 1000, polling: 1000 });
const data = await page.evaluate(() => document.getElementById("c").toDataURL("image/png"));
await writeFile(join(root, out), Buffer.from(data.split(",")[1], "base64"));
console.log(`saved ${out} in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
await browser.close();
server.close();
