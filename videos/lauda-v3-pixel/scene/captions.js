// Captions in the style of the reference: Montserrat Black, white, thick rounded black outline,
// one to three words at a time, centred just above the platform UI. Drawn at full 1080×1920.
import { CAPTIONS } from "./timeline.js";

export const CAPTION_FONT = "assets/fonts/montserrat-latin-900-normal.woff2";
const SIZE = 84, STROKE = 18, CENTER_Y = 1150, MAX_W = 940;

export async function loadCaptionFont() {
  const face = new FontFace("MontserratCaption", `url(${CAPTION_FONT})`, { weight: "900" });
  await face.load();
  document.fonts.add(face);
}

export function drawCaption(ctx, t) {
  const c = CAPTIONS.find((x) => t >= x.start && t < x.end);
  if (!c) return;
  const text = c.text.replace("…", "...");
  ctx.save();
  ctx.font = `900 ${SIZE}px MontserratCaption, Montserrat, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.lineJoin = "round";
  ctx.miterLimit = 2;
  // wrap to two lines if the chunk is too wide
  const words = text.split(" ");
  const rows = [];
  let row = "";
  for (const w of words) {
    const next = row ? row + " " + w : w;
    if (ctx.measureText(next).width > MAX_W && row) { rows.push(row); row = w; } else row = next;
  }
  rows.push(row);
  // a short pop on each new chunk: 0.92 → 1.0 scale over 80 ms
  const pop = Math.min(1, (t - c.start) / 0.08);
  const scale = 0.92 + 0.08 * pop;
  rows.forEach((r, i) => {
    const y = CENTER_Y + (i - (rows.length - 1) / 2) * SIZE * 1.08;
    ctx.save();
    ctx.translate(540, y);
    ctx.scale(scale, scale);
    ctx.fillStyle = "rgba(0,0,0,0.35)"; // soft drop shadow
    ctx.fillText(r, 0, 8);
    ctx.strokeStyle = "#000000";
    ctx.lineWidth = STROKE;
    ctx.strokeText(r, 0, 0);
    ctx.fillStyle = "#ffffff";
    ctx.fillText(r, 0, 0);
    ctx.restore();
  });
  ctx.restore();
}
