// Assembles the film: picks the scene for time t, draws it, dissolves between scenes, and
// overlays the karaoke captions. renderAt(t) is a pure function of t.
import { LW, LH, SCALE, CAPTION_TOP, P, dith, surface, makeCanvas, drawText, textWidth, wrapWords } from "./engine.js";
import { makeScenes } from "./scenes.js";
import { SCENES, LINES, DURATION } from "./schedule.js";

export { DURATION };

export function createFilm(canvas) {
  const scenes = makeScenes();
  const frame = makeCanvas();
  const fctx = frame.getContext("2d");
  const S = surface(fctx);
  canvas.width = LW * SCALE; canvas.height = LH * SCALE;
  const out = canvas.getContext("2d");
  out.imageSmoothingEnabled = false;

  const linesOf = (id) => LINES.filter((l) => l.scene === id);
  const pits = SCENES.find((s) => s.id === "pits");
  const pitsLines = linesOf("pits");
  const pitsWalkStart = pitsLines[2].start - pits.start;
  const pitsDur = { dur: pits.end - pits.start, walkStart: pitsWalkStart, walkTotal: pits.end - pits.start - pitsWalkStart + 3.2 };

  function captions(t) {
    const line = LINES.find((l, i) => t >= l.start - 0.05 && t < Math.min(l.start + l.speech + 0.3, LINES[i + 1] ? LINES[i + 1].start - 0.02 : Infinity));
    if (!line) return;
    const words = line.words.map((w) => w.w.toUpperCase().replace("…", "..."));
    let active = 0;
    line.words.forEach((w, i) => { if (t >= w.start) active = i; });
    const rows = wrapWords(words, 27);
    let index = 0;
    rows.forEach((row, r) => {
      const text = row.join(" ");
      const x0 = Math.round((LW - textWidth(text)) / 2), y0 = CAPTION_TOP + r * 11;
      for (let y = y0 - 3; y < y0 + 10; y++) for (let x = x0 - 4; x < x0 + textWidth(text) + 5; x++) if (dith(x, y, 0.7)) S.px(x, y, P.ink);
      let cx = x0;
      row.forEach((w) => {
        const i = index++;
        drawText(S, w, cx, y0, 1, i === active ? P.hot : i < active ? P.paper : "#9aa3ad", P.ink);
        cx += (w.length + 1) * 6;
      });
    });
  }

  function renderAt(t) {
    t = Math.max(0, Math.min(DURATION - 1e-3, t));
    const si = SCENES.findIndex((s) => t >= s.start && t < s.end);
    const sc = SCENES[si < 0 ? SCENES.length - 1 : si];
    const u = t - sc.start;
    const sl = linesOf(sc.id);
    const ctx = { t, dur: sc.end - sc.start, cue: (n) => (sl[n] ? sl[n].start - sc.start : 0), pitsDur };
    fctx.fillStyle = P.ink;
    fctx.fillRect(0, 0, LW, LH);
    S.ox = 0; S.oy = 0;
    scenes[sc.id](S, u, ctx);
    S.ox = 0; S.oy = 0;
    if (si > 0 && u < 0.16) { // pixel dissolve in from black
      const k = u / 0.16;
      for (let y = 0; y < LH; y++) for (let x = 0; x < LW; x++) if (!dith(x, y, k)) S.px(x, y, P.ink);
    }
    captions(t);
    out.drawImage(frame, 0, 0, LW * SCALE, LH * SCALE);
  }
  return renderAt;
}
