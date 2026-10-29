// Pixel engine for the Lauda short: a 180×320 grid, a fixed palette, ordered dithering,
// auto-outlined sprites, a 5×7 pixel font, and the recurring characters and props.
// Everything is a pure function of its inputs so any frame can be drawn on its own.

export const LW = 180, LH = 320, SCALE = 6;
// Platform UI covers the frame below y≈221 (1330 px): captions sit just above it,
// action stays above the captions.
export const CAPTION_TOP = 192;

export const P = {
  out: "#111317", ink: "#101215", paper: "#eef1f4",
  red: "#c41e27", redD: "#86131a", redH: "#ec5248", lamp: "#ff3b2e", lampGlow: "#7a2a28", hot: "#ff6b5e",
  white: "#e6eaee", whiteD: "#a9b1ba", grey: "#6a727d", greyD: "#3b414a", metal: "#a2aab4",
  tyre: "#17191d", tyreHi: "#363a41", visor: "#0d0f12", glint: "#8fa3b8",
  knit: "#e8e6e1", knitD: "#b8b4ad", skin: "#b4876a", coat: "#2a2e34", coatHi: "#3c424a",
  // storm / Fuji
  sky0: "#1f2530", sky1: "#262d39", sky2: "#2e3643", sky3: "#37404e", sky4: "#424c5b", sky5: "#4e5969", sky6: "#5b6777",
  cloud: "#1b2029", cloudHi: "#323a47",
  fujiL: "#2c3440", fuji: "#353e4b", fujiR: "#414b59", snow: "#c9d1da", snowS: "#8f9aa6", snowD: "#6c7784",
  trees: "#232b2c", treesHi: "#2d3737", stand: "#2a2f37", standHi: "#3b424c", roof: "#4b535e",
  asphalt: "#30353d", asphaltHi: "#3b414a", wet: "#272c33", wetHi: "#3a4350", line: "#cdd3d9",
  wall: "#7d848d", wallHi: "#a2a9b1", wallLo: "#535a63", post: "#1c2026", wire: "#4a515b",
  rain: "#7f8b98", rainHi: "#aab5c1", spray: "#9aa4ae",
  // hospital night
  room0: "#141c22", room1: "#1b252c", room2: "#223039", night: "#0b1119", nightHi: "#16202c",
  sheet: "#b9c1c8", sheetD: "#7f8a94", sheetH: "#dfe5ea", ecg: "#5bff8a", ecgD: "#1f5a35", screen: "#071009",
  // Monza sun
  blue0: "#3d7cc9", blue1: "#5a95d8", blue2: "#7fb0e4", blue3: "#a9cdf0", cloudW: "#f4f7fb", cloudS: "#c9d9ea",
  pine: "#24402c", pineHi: "#35593d", trunk: "#5a4030", grass: "#4b7a3a", grassHi: "#5f9147", grassD: "#36592a",
  tarmac: "#5d636b", tarmacHi: "#6c727a", kerbW: "#eef1f4",
  // Nürburgring forest
  hill0: "#1e2b24", hill1: "#26372d", hill2: "#304537", fog: "#5c6a70", fogHi: "#76858a", forest: "#1b2a21", forestHi: "#2a4031",
  armco: "#9aa3ab", armcoD: "#5f6770",
  flame0: "#fff1a8", flame1: "#ffc23a", flame2: "#ff7a1c", flame3: "#d43a14", smoke: "#2b2e33", smokeHi: "#454a51",
};

const BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]];
export const dith = (x, y, t) => (BAYER[(((Math.floor(y) % 4) + 4) % 4)][(((Math.floor(x) % 4) + 4) % 4)] + 0.5) / 16 < t;
export const hash = (a, b) => {
  let h = (a * 374761393 + b * 668265263) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
};
export const clamp01 = (v) => Math.min(1, Math.max(0, v));
export const lerp = (a, b, k) => a + (b - a) * k;
export const outCubic = (x) => 1 - Math.pow(1 - clamp01(x), 3);
export const inOut = (x) => { x = clamp01(x); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
export const seeded = (s) => () => ((s = (s * 16807) % 2147483647) / 2147483647);

export function mix(a, b, t) {
  const pa = parseInt(a.slice(1, 7), 16), pb = parseInt(b.slice(1, 7), 16);
  const ch = (s) => Math.round(((pa >> s) & 255) * (1 - t) + ((pb >> s) & 255) * t);
  return "#" + ((1 << 24) | (ch(16) << 16) | (ch(8) << 8) | ch(0)).toString(16).slice(1);
}

// A drawing surface over a 2D context with an integer camera offset.
export function surface(ctx) {
  const s = { ctx, ox: 0, oy: 0 };
  const W = ctx.canvas.width, H = ctx.canvas.height;
  s.px = (x, y, c) => {
    x = Math.round(x) + s.ox; y = Math.round(y) + s.oy;
    if (x >= 0 && y >= 0 && x < W && y < H) { ctx.fillStyle = c; ctx.fillRect(x, y, 1, 1); }
  };
  s.rect = (x, y, w, h, c) => { ctx.fillStyle = c; ctx.fillRect(Math.round(x) + s.ox, Math.round(y) + s.oy, Math.round(w), Math.round(h)); };
  s.dithRect = (x, y, w, h, c, d) => { for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) if (dith(x + i, y + j, d)) s.px(x + i, y + j, c); };
  s.line = (x0, y0, x1, y1, c) => {
    const n = Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0), 1);
    for (let i = 0; i <= n; i++) s.px(lerp(x0, x1, i / n), lerp(y0, y1, i / n), c);
  };
  return s;
}

export function makeCanvas(w = LW, h = LH) {
  const c = document.createElement("canvas");
  c.width = w; c.height = h;
  return c;
}

// ------------------------------------------------------------------ sprites

export class Sprite {
  constructor(w, h) { this.w = w; this.h = h; this.d = new Array(w * h).fill(null); }
  set(x, y, c) { x = Math.round(x); y = Math.round(y); if (x >= 0 && y >= 0 && x < this.w && y < this.h) this.d[y * this.w + x] = c; }
  get(x, y) { return x >= 0 && y >= 0 && x < this.w && y < this.h ? this.d[y * this.w + x] : null; }
  rect(x, y, w, h, c) { for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) this.set(x + i, y + j, c); }
  circle(cx, cy, r, c) { for (let y = -r; y <= r; y++) for (let x = -r; x <= r; x++) if (x * x + y * y <= r * r + r * 0.6) this.set(cx + x, cy + y, c); }
  ellipse(cx, cy, rx, ry, c) { for (let y = -ry; y <= ry; y++) for (let x = -rx; x <= rx; x++) if ((x / rx) ** 2 + (y / ry) ** 2 <= 1.05) this.set(cx + x, cy + y, c); }
  poly(pts, c) {
    const ys = pts.map((p) => p[1]);
    for (let y = Math.floor(Math.min(...ys)); y <= Math.ceil(Math.max(...ys)); y++) {
      const xs = [];
      for (let i = 0; i < pts.length; i++) {
        const [x1, y1] = pts[i], [x2, y2] = pts[(i + 1) % pts.length];
        if ((y1 <= y + 0.5 && y2 > y + 0.5) || (y2 <= y + 0.5 && y1 > y + 0.5)) xs.push(x1 + ((y + 0.5 - y1) / (y2 - y1)) * (x2 - x1));
      }
      xs.sort((a, b) => a - b);
      for (let k = 0; k + 1 < xs.length; k += 2) for (let x = Math.round(xs[k]); x < Math.round(xs[k + 1]); x++) this.set(x, y, c);
    }
  }
  thick(x0, y0, x1, y1, r, c) {
    const n = Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0), 1) * 2;
    for (let i = 0; i <= n; i++) this.circle(lerp(x0, x1, i / n), lerp(y0, y1, i / n), r, c);
  }
  outline(c = P.out) {
    const add = [];
    for (let y = 0; y < this.h; y++) for (let x = 0; x < this.w; x++) {
      if (this.get(x, y)) continue;
      if (this.get(x + 1, y) || this.get(x - 1, y) || this.get(x, y + 1) || this.get(x, y - 1)) add.push([x, y]);
    }
    add.forEach(([x, y]) => this.set(x, y, c));
    return this;
  }
  bottom() {
    let b = this.h - 1;
    while (b > 0 && !this.d.slice(b * this.w, b * this.w + this.w).some(Boolean)) b--;
    return b;
  }
  blit(S, x0, y0, { clipBelow = Infinity, tint = null, flipX = false } = {}) {
    for (let y = 0; y < this.h; y++) {
      if (y0 + y >= clipBelow) break;
      for (let x = 0; x < this.w; x++) {
        const c = this.get(flipX ? this.w - 1 - x : x, y);
        if (c) S.px(x0 + x, y0 + y, tint ? mix(c, tint[0], tint[1]) : c);
      }
    }
  }
  reflect(S, x0, y0, ground, strength = 0.55) {
    const b = this.bottom();
    const base = y0 + b;
    for (let y = 0; y <= b; y++) {
      const ry = base + (b - y) + 1;
      if ((ry - base) % 3 === 2) continue;
      const shift = (ry >> 1) % 2 ? 1 : 0;
      for (let x = 0; x < this.w; x++) {
        const c = this.get(x, y);
        if (!c) continue;
        const fade = strength * (1 - (ry - base) / (this.h * 1.4));
        if (fade > 0 && dith(x0 + x, ry, fade + 0.15)) S.px(x0 + x + shift, ry, mix(c, ground, 0.45));
      }
    }
  }
}

// 1976-style F1 car, side view, nose left.
export function carSprite(body, bodyD, bodyH, s = 1, driver = null, wheelPhase = 0) {
  const S = (v) => Math.round(v * s);
  const sp = new Sprite(S(52) + 2, S(18) + 2);
  const o = 1;
  sp.rect(o + S(41), o + S(1), S(10), S(2), body);
  sp.rect(o + S(41), o + S(1), S(10), 1, bodyH);
  sp.rect(o + S(49), o + S(0), Math.max(1, S(2)), S(7), P.greyD);
  sp.rect(o + S(44), o + S(3), Math.max(1, S(1)), S(5), P.grey);
  sp.poly([[o + S(1), o + S(13)], [o + S(12), o + S(10.5)], [o + S(20), o + S(9)], [o + S(23), o + S(7)], [o + S(31), o + S(7)], [o + S(35), o + S(8)], [o + S(42), o + S(8.5)], [o + S(46), o + S(10)], [o + S(46), o + S(14)], [o + S(2), o + S(14.5)]], body);
  for (let x = S(3); x < S(45); x++) sp.set(o + x, o + S(14), bodyD);
  for (let x = S(13); x < S(42); x++) { const y = x < S(23) ? o + S(10.5 - (x - S(13)) * 0.15) : o + S(8); if (sp.get(o + x, y + 1)) sp.set(o + x, y + 1, bodyH); }
  sp.rect(o + S(21), o + S(10), S(16), S(3), body);
  sp.rect(o + S(21), o + S(10), Math.max(1, S(1.5)), S(3), P.out);
  sp.rect(o + S(25), o + S(6), S(6), Math.max(1, S(1.5)), P.out);
  sp.set(o + S(23), o + S(5), P.whiteD); sp.set(o + S(24), o + S(5), P.whiteD); sp.set(o + S(23), o + S(6), P.whiteD);
  sp.rect(o + S(31), o + S(4), Math.max(1, S(1)), S(3), P.metal);
  if (driver) { sp.circle(o + S(28), o + S(4.5), Math.max(1, S(2)), driver); sp.set(o + S(26.5), o + S(4.5), P.visor); }
  sp.rect(o + S(36), o + S(10), S(6), S(2), P.metal);
  sp.rect(o + S(46), o + S(11), S(3), Math.max(1, S(1)), P.grey);
  sp.circle(o + S(32), o + S(10.5), Math.max(1, S(1.6)), P.white);
  sp.set(o + S(32), o + S(10), P.out); sp.set(o + S(32), o + S(11), P.out);
  sp.rect(o + S(0), o + S(14), S(9), Math.max(1, S(1.5)), body);
  sp.rect(o + S(0), o + S(12), Math.max(1, S(1.2)), S(4), P.greyD);
  const wheel = (cx, cy, r) => {
    sp.circle(o + S(cx), o + S(cy), S(r), P.tyre);
    sp.circle(o + S(cx), o + S(cy), Math.max(1, S(r * 0.45)), P.grey);
    sp.set(o + S(cx), o + S(cy), P.metal);
    const a = wheelPhase / r;
    sp.set(o + S(cx + Math.cos(a) * r * 0.45), o + S(cy + Math.sin(a) * r * 0.45), P.metal);
    sp.set(o + S(cx - r * 0.6), o + S(cy - r * 0.7), P.tyreHi);
  };
  wheel(41, 12.5, 5.2);
  wheel(9.5, 13.5, 4.2);
  return sp.outline(P.out);
}

// Lauda walking left in his balaclava, helmet in his near hand. step alternates the stride.
export function laudaSprite(s = 1, step = 0, helmet = true) {
  const S = (v) => v * s;
  const sp = new Sprite(Math.ceil(S(16)) + 2, Math.ceil(S(36)) + 2);
  const R = (x, y, w, h, c) => sp.rect(Math.round(S(x)), Math.round(S(y)), Math.max(1, Math.round(S(w))), Math.max(1, Math.round(S(h))), c);
  const Pl = (pts, c) => sp.poly(pts.map(([x, y]) => [S(x), S(y)]), c);
  if (step === 0) {
    Pl([[8, 19], [11, 19], [12.5, 31], [9.5, 31]], P.redD);
    Pl([[5, 19], [8, 19], [6, 31], [3, 31]], P.red);
    R(9.5, 31, 4, 2, P.out); R(2, 31, 4.5, 2, P.out);
  } else {
    Pl([[7, 19], [10, 19], [9.5, 31], [6.5, 31]], P.redD);
    Pl([[5.5, 19], [8.5, 19], [8.5, 31], [5.5, 31]], P.red);
    R(6, 31, 4.5, 2, P.out); R(4.5, 31, 4.5, 2, P.out);
  }
  R(5, 9, 6, 11, P.red); R(5, 9, 1, 11, P.redH); R(5, 17, 6, 1.2, P.out); R(6.5, 11, 3, 1.2, P.white);
  Pl([[5, 10], [6.5, 10], [4.2 + step, 17], [3 + step, 17]], P.redD);
  const sw = step ? -0.8 : 0;
  Pl([[9, 10], [11, 10], [12.2 + sw, 19], [10.2 + sw, 19]], P.red);
  R(11, 11.5, 0.9, 3, P.white);
  R(10 + sw, 19, 3, 2, P.coat);
  if (helmet) {
    sp.circle(Math.round(S(12 + sw)), Math.round(S(24)), Math.round(S(3)), P.red);
    R(9 + sw, 23, 3, 2, P.visor);
    R(10.5 + sw, 21, 3.5, 0.9, P.white);
  }
  R(7, 7, 3, 2, P.knit);
  sp.circle(Math.round(S(8)), Math.round(S(4)), Math.round(S(3)), P.knit);
  R(10, 3, 1, 3, P.knitD);
  R(5.2, 3, 2, 1, P.skin);
  return sp.outline(P.out);
}

export function mechanicSprite(s = 1) {
  const S = (v) => v * s;
  const sp = new Sprite(Math.ceil(S(22)) + 2, Math.ceil(S(34)) + 2);
  const R = (x, y, w, h, c) => sp.rect(Math.round(S(x)), Math.round(S(y)), Math.max(1, Math.round(S(w))), Math.max(1, Math.round(S(h))), c);
  sp.poly([[S(2), S(7)], [S(11), S(1)], [S(20), S(7)]], P.coat);
  R(2, 7, 18, 1, P.post); R(11, 0, 0.8, 15, P.grey);
  sp.circle(Math.round(S(13)), Math.round(S(11)), Math.round(S(2)), P.skin);
  R(12, 9.5, 3, 1, P.post); R(10, 14, 6, 10, P.coat); R(10, 14, 1, 10, P.coatHi);
  R(11, 24, 2, 7, P.greyD); R(13, 24, 2, 7, P.coat);
  R(10, 31, 3, 2, P.out); R(13, 31, 3, 2, P.out);
  return sp.outline(P.out);
}

// A small running figure (driver or marshal), 2-frame cycle, facing left.
export function runnerSprite(suit, helmetC, step = 0) {
  const sp = new Sprite(12, 20);
  sp.circle(6, 3, 2, helmetC);
  sp.rect(4, 6, 5, 6, suit);
  if (step) { sp.poly([[4, 12], [6, 12], [3, 18], [1, 18]], suit); sp.poly([[6, 12], [8, 12], [10, 18], [8, 18]], mix(suit, "#000000", 0.3)); }
  else { sp.poly([[4, 12], [7, 12], [6, 18], [4, 18]], suit); sp.poly([[5, 12], [8, 12], [8, 18], [6, 18]], mix(suit, "#000000", 0.3)); }
  sp.poly([[4, 7], [5, 7], [1 + step * 2, 11], [0 + step * 2, 11]], mix(suit, "#000000", 0.3));
  sp.poly([[8, 7], [9, 7], [11 - step * 2, 10], [10 - step * 2, 10]], suit);
  return sp.outline(P.out);
}

// Lauda's full-face helmet, three-quarter view facing left. scorched adds burn marks.
export function helmetSprite(s = 1, scorched = false) {
  const S = (v) => Math.round(v * s);
  const sp = new Sprite(S(26) + 2, S(24) + 2);
  sp.ellipse(S(13) + 1, S(11) + 1, S(12), S(11), P.red);
  sp.poly([[S(2) + 1, S(13) + 1], [S(14) + 1, S(14) + 1], [S(16) + 1, S(22) + 1], [S(5) + 1, S(22) + 1]], P.red); // chin bar
  sp.ellipse(S(16) + 1, S(8) + 1, S(9), S(5), P.redH);
  sp.ellipse(S(13) + 1, S(13) + 1, S(12), S(9), P.red);
  sp.poly([[S(1) + 1, S(8) + 1], [S(15) + 1, S(8) + 1], [S(15) + 1, S(14) + 1], [S(2) + 1, S(14) + 1]], P.visor); // visor
  sp.rect(S(3) + 1, S(9) + 1, S(5), Math.max(1, S(1)), P.glint);
  sp.rect(S(9) + 1, S(10) + 1, S(2), Math.max(1, S(1)), mix(P.glint, P.visor, 0.5));
  for (let y = S(0); y < S(8); y++) sp.set(S(15) + 1 + Math.round(y * 0.15), y + 1, P.white); // stripe
  for (let y = S(14); y < S(22); y++) sp.set(S(14) + 1 - Math.round((y - S(14)) * 0.1), y + 1, P.white);
  sp.rect(S(17) + 1, S(11) + 1, Math.max(1, S(2)), Math.max(1, S(2)), P.greyD); // visor pivot
  sp.rect(S(6) + 1, S(22) + 1, S(10), Math.max(1, S(1)), P.redD);
  if (scorched) {
    const r = seeded(77);
    for (let i = 0; i < 40 * s; i++) {
      const x = 1 + Math.floor(r() * S(26)), y = 1 + Math.floor(r() * S(22));
      if (sp.get(x, y) === P.red || sp.get(x, y) === P.redH) sp.set(x, y, r() < 0.5 ? "#3a1a16" : "#5e2a22");
    }
  }
  return sp.outline(P.out);
}

// Animated fire column: flickering tongues with dithered smoke rising above.
export function drawFire(S, cx, baseY, w, h, t, intensity = 1) {
  const fr = Math.floor(t * 15);
  for (let x = -w; x <= w; x++) {
    const edge = 1 - Math.abs(x) / (w + 1);
    const colH = h * intensity * edge * (0.6 + 0.4 * hash(x + 99, fr)) * (0.85 + 0.15 * Math.sin(t * 9 + x));
    for (let y = 0; y < colH; y++) {
      const k = y / Math.max(1, colH);
      const c = k < 0.25 ? P.flame0 : k < 0.5 ? P.flame1 : k < 0.8 ? P.flame2 : P.flame3;
      if (k < 0.85 || dith(cx + x, baseY - y + fr, 0.5)) S.px(cx + x, baseY - y, c);
    }
  }
  for (let i = 0; i < 160 * intensity; i++) {
    const a = hash(i, 7), age = (t * 0.8 + hash(i, 3)) % 1;
    const x = cx + (a - 0.5) * w * 2 * (1 + age * 1.5) + Math.sin(age * 6 + i) * 3;
    const y = baseY - h * intensity * 0.8 - age * h * 2.2;
    if (dith(Math.round(x), Math.round(y), 0.9 - age)) S.px(x, y, age < 0.5 ? P.smokeHi : P.smoke);
  }
}

// Screen-space rain: seeded streaks moving down-left.
export function makeRain(n, seed = 42) {
  const r = seeded(seed);
  return Array.from({ length: n }, () => ({ x: r() * (LW + 60), y: r() * (LH + 20), v: 230 + r() * 120, near: r() < 0.3 }));
}
export function drawRain(S, drops, t, count, { region = null, color = P.rain, colorNear = P.rainHi } = {}) {
  for (let i = 0; i < count; i++) {
    const d = drops[i];
    const y = ((d.y + d.v * t) % (LH + 20)) - 10;
    const x = ((((d.x - d.v * 0.22 * t) % (LW + 60)) + LW + 60) % (LW + 60)) - 30;
    const len = d.near ? 6 : 3 + (i % 2);
    for (let k = 0; k < len; k++) {
      const px = x - Math.floor(k / 3), py = y + k;
      if (region && (px < region[0] || px >= region[2] || py < region[1] || py >= region[3])) continue;
      S.px(px, py, d.near ? colorNear : color);
    }
  }
}

// ------------------------------------------------------------------ pixel font (5×7)

const FONT = {
  A: [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"], B: ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
  C: [".####", "#....", "#....", "#....", "#....", "#....", ".####"], D: ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
  E: ["#####", "#....", "#....", "####.", "#....", "#....", "#####"], F: ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
  G: [".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."], H: ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
  I: ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"], J: ["..###", "...#.", "...#.", "...#.", "#..#.", "#..#.", ".##.."],
  K: ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"], L: ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
  M: ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"], N: ["#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"],
  O: [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."], P: ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
  Q: [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"], R: ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
  S: [".####", "#....", "#....", ".###.", "....#", "....#", "####."], T: ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
  U: ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."], V: ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
  W: ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"], X: ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
  Y: ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."], Z: ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
  0: [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."], 1: ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
  2: [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"], 3: ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
  4: ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."], 5: ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
  6: [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."], 7: ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
  8: [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."], 9: [".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."],
  "+": [".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."], "-": [".....", ".....", ".....", "#####", ".....", ".....", "....."],
  ".": [".....", ".....", ".....", ".....", ".....", ".##..", ".##.."], ",": [".....", ".....", ".....", ".....", ".##..", "..#..", ".#..."],
  "'": [".##..", "..#..", ".#...", ".....", ".....", ".....", "....."], "?": [".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."],
  "!": ["..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."], " ": [".....", ".....", ".....", ".....", ".....", ".....", "....."],
};
export const textWidth = (str, sc = 1) => str.length * 6 * sc - sc;
export function drawText(S, str, x, y, sc, colorAt, shadow = P.ink, chars = Infinity) {
  [...str].forEach((ch, i) => {
    if (i >= chars) return;
    const g = FONT[ch] || FONT[" "];
    for (let r = 0; r < 7; r++) for (let c = 0; c < 5; c++) {
      if (g[r][c] !== "#") continue;
      if (shadow) S.rect(x + (i * 6 + c) * sc + sc, y + r * sc + sc, sc, sc, shadow);
      S.rect(x + (i * 6 + c) * sc, y + r * sc, sc, sc, typeof colorAt === "function" ? colorAt(i) : colorAt);
    }
  });
}
export function box(S, x, y, w, h, fill = P.paper) {
  S.rect(x - 1, y - 1, w + 2, h + 2, P.ink);
  S.rect(x, y, w, h, fill);
  S.rect(x + 1, y + h + 1, w + 1, 1, P.ink);
  S.rect(x + w + 1, y + 1, 1, h + 1, P.ink);
}
// Greedy wrap of words into lines of at most maxChars.
export function wrapWords(words, maxChars = 27) {
  const lines = [[]];
  let len = 0;
  for (const w of words) {
    const add = (len ? 1 : 0) + w.length;
    if (len + add > maxChars && len) { lines.push([]); len = 0; }
    lines[lines.length - 1].push(w);
    len += (lines[lines.length - 1].length > 1 ? 1 : 0) + w.length;
  }
  return lines;
}
