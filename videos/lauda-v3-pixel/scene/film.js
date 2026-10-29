// Pixel film: picks the shot for time t (hard cuts only), draws it on the 180×320 grid, scales
// it ×6 and lays the captions over the top at full resolution.
import { LW, LH, SCALE, P, surface, makeCanvas } from "./engine.js";
import { makeShots } from "./shots.js";
import { SHOTS, DURATION } from "./timeline.js";
import { drawCaption, loadCaptionFont } from "./captions.js";

export { DURATION };

export async function createFilm(canvas) {
  await loadCaptionFont();
  const shots = makeShots();
  const frame = makeCanvas();
  const fctx = frame.getContext("2d", { willReadFrequently: true });
  const S = surface(fctx);
  canvas.width = LW * SCALE; canvas.height = LH * SCALE;
  const out = canvas.getContext("2d");
  out.imageSmoothingEnabled = false;
  return function renderAt(t) {
    t = Math.max(0, Math.min(DURATION - 1e-3, t));
    const shot = SHOTS.find((s) => t >= s.start && t < s.end) || SHOTS[SHOTS.length - 1];
    fctx.fillStyle = P.ink;
    fctx.fillRect(0, 0, LW, LH);
    S.ox = 0; S.oy = 0;
    shots[shot.id](S, t - shot.start, t);
    out.imageSmoothingEnabled = false;
    out.drawImage(frame, 0, 0, LW * SCALE, LH * SCALE);
    drawCaption(out, t);
  };
}
