// Fuji, 1976 — animated 16-bit pixel scene. Everything is drawn on a 180×320 grid with a
// fixed palette and scaled ×6 with hard edges. renderAt(t) draws any frame from t alone.

export const LW = 180, LH = 320, SCALE = 6;
const WORLD_TOP = 60; // extra sky above the scene for the opening tilt-down
const WH = LH + WORLD_TOP;

const P = {
  sky0: "#1f2530", sky1: "#262d39", sky2: "#2e3643", sky3: "#37404e", sky4: "#424c5b", sky5: "#4e5969", sky6: "#5b6777",
  cloud: "#1b2029", cloudHi: "#323a47",
  fujiL: "#2c3440", fuji: "#353e4b", fujiR: "#414b59", snow: "#c9d1da", snowS: "#8f9aa6", snowD: "#6c7784",
  trees: "#232b2c", treesHi: "#2d3737",
  stand: "#2a2f37", standHi: "#3b424c", roof: "#4b535e",
  asphalt: "#30353d", asphaltHi: "#3b414a", wet: "#272c33", wetHi: "#3a4350", line: "#cdd3d9",
  wall: "#7d848d", wallHi: "#a2a9b1", wallLo: "#535a63", post: "#1c2026", wire: "#4a515b",
  out: "#111317", red: "#c41e27", redD: "#86131a", redH: "#ec5248", white: "#e6eaee", whiteD: "#a9b1ba",
  grey: "#6a727d", greyD: "#3b414a", metal: "#a2aab4", tyre: "#17191d", tyreHi: "#363a41", visor: "#0d0f12",
  knit: "#e8e6e1", knitD: "#b8b4ad", skin: "#b4876a", coat: "#2a2e34", coatHi: "#3c424a",
  rain: "#7f8b98", rainHi: "#aab5c1", spray: "#9aa4ae", lamp: "#ff3b2e", lampGlow: "#7a2a28",
  ink: "#101215", paper: "#eef1f4",
};

const BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]];
const dith = (x, y, t) => (BAYER[y & 3][x & 3] + 0.5) / 16 < t;
const hash = (a, b) => {
  let h = (a * 374761393 + b * 668265263) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
};
const clamp01 = (v) => Math.min(1, Math.max(0, v));
const outCubic = (x) => 1 - Math.pow(1 - x, 3);
const inOut = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const lerp = (a, b, k) => a + (b - a) * k;

function mix(a, b, t) {
  const pa = parseInt(a.slice(1), 16), pb = parseInt(b.slice(1), 16);
  const ch = (s) => Math.round(((pa >> s) & 255) * (1 - t) + ((pb >> s) & 255) * t);
  return "#" + ((1 << 24) | (ch(16) << 16) | (ch(8) << 8) | ch(0)).toString(16).slice(1);
}

// A drawing surface with an integer y offset (world → screen) and pixel helpers.
function surface(ctx) {
  const s = { ctx, oy: 0 };
  s.px = (x, y, c) => {
    x = Math.round(x); y = Math.round(y) + s.oy;
    if (x >= 0 && y >= 0 && x < ctx.canvas.width && y < ctx.canvas.height) { ctx.fillStyle = c; ctx.fillRect(x, y, 1, 1); }
  };
  s.rect = (x, y, w, h, c) => { ctx.fillStyle = c; ctx.fillRect(Math.round(x), Math.round(y) + s.oy, Math.round(w), Math.round(h)); };
  return s;
}

// ------------------------------------------------------------------ sprites

class Sprite {
  constructor(w, h) { this.w = w; this.h = h; this.d = new Array(w * h).fill(null); }
  set(x, y, c) { x = Math.round(x); y = Math.round(y); if (x >= 0 && y >= 0 && x < this.w && y < this.h) this.d[y * this.w + x] = c; }
  get(x, y) { return x >= 0 && y >= 0 && x < this.w && y < this.h ? this.d[y * this.w + x] : null; }
  rect(x, y, w, h, c) { for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) this.set(x + i, y + j, c); }
  circle(cx, cy, r, c) { for (let y = -r; y <= r; y++) for (let x = -r; x <= r; x++) if (x * x + y * y <= r * r + r * 0.6) this.set(cx + x, cy + y, c); }
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
  outline(c) {
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
  blit(S, x0, y0, clipBelow = Infinity) {
    for (let y = 0; y < this.h; y++) {
      if (y0 + y >= clipBelow) break;
      for (let x = 0; x < this.w; x++) { const c = this.get(x, y); if (c) S.px(x0 + x, y0 + y, c); }
    }
  }
  // Puddle reflection hanging from the lowest painted row: flipped, darkened, rippled.
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

// 1976-style F1 car, side view, nose left. wheelPhase spins the rim marker.
function carSprite(body, bodyD, bodyH, s = 1, driver = null, wheelPhase = 0) {
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
    sp.set(o + S(cx + Math.cos(a) * r * 0.45), o + S(cy + Math.sin(a) * r * 0.45), P.metal); // spinning rim marker
    sp.set(o + S(cx - r * 0.6), o + S(cy - r * 0.7), P.tyreHi);
    sp.set(o + S(cx - r * 0.75), o + S(cy - r * 0.45), P.tyreHi);
  };
  wheel(41, 12.5, 5.2);
  wheel(9.5, 13.5, 4.2);
  return sp.outline(P.out);
}

// Lauda walking left in his balaclava, helmet in his near hand. step alternates the stride.
function laudaSprite(s = 1, step = 0) {
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
  R(5, 9, 6, 11, P.red);
  R(5, 9, 1, 11, P.redH);
  R(5, 17, 6, 1.2, P.out);
  R(6.5, 11, 3, 1.2, P.white);
  Pl([[5, 10], [6.5, 10], [4.2 + step, 17], [3 + step, 17]], P.redD);
  const sw = step ? -0.8 : 0;
  Pl([[9, 10], [11, 10], [12.2 + sw, 19], [10.2 + sw, 19]], P.red);
  R(11, 11.5, 0.9, 3, P.white);
  R(10 + sw, 19, 3, 2, P.coat);
  sp.circle(Math.round(S(12 + sw)), Math.round(S(24)), Math.round(S(3)), P.red);
  R(9 + sw, 23, 3, 2, P.visor);
  R(10.5 + sw, 21, 3.5, 0.9, P.white);
  R(7, 7, 3, 2, P.knit);
  sp.circle(Math.round(S(8)), Math.round(S(4)), Math.round(S(3)), P.knit);
  R(10, 3, 1, 3, P.knitD);
  R(5.2, 3, 2, 1, P.skin);
  return sp.outline(P.out);
}

function mechanicSprite(s = 1) {
  const S = (v) => v * s;
  const sp = new Sprite(Math.ceil(S(22)) + 2, Math.ceil(S(34)) + 2);
  const R = (x, y, w, h, c) => sp.rect(Math.round(S(x)), Math.round(S(y)), Math.max(1, Math.round(S(w))), Math.max(1, Math.round(S(h))), c);
  sp.poly([[S(2), S(7)], [S(11), S(1)], [S(20), S(7)]], P.coat);
  R(2, 7, 18, 1, P.post);
  R(11, 0, 0.8, 15, P.grey);
  sp.circle(Math.round(S(13)), Math.round(S(11)), Math.round(S(2)), P.skin);
  R(12, 9.5, 3, 1, P.post);
  R(10, 14, 6, 10, P.coat);
  R(10, 14, 1, 10, P.coatHi);
  R(11, 24, 2, 7, P.greyD); R(13, 24, 2, 7, P.coat);
  R(10, 31, 3, 2, P.out); R(13, 31, 3, 2, P.out);
  return sp.outline(P.out);
}

// ------------------------------------------------------------------ pixel font (5×7)

const FONT = {
  A: [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
  B: ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
  C: [".####", "#....", "#....", "#....", "#....", "#....", ".####"],
  D: ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
  E: ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
  F: ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
  H: ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
  I: ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"],
  J: ["..###", "...#.", "...#.", "...#.", "#..#.", "#..#.", ".##.."],
  L: ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
  N: ["#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"],
  O: [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
  P: ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
  R: ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
  S: [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
  T: ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
  U: ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
  Y: ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
  1: ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
  2: [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
  3: ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
  5: ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
  6: [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."],
  7: ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
  8: [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
  9: [".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."],
  "+": [".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."],
  " ": [".....", ".....", ".....", ".....", ".....", ".....", "....."],
};
const textWidth = (str, sc) => str.length * 6 * sc - sc;
// Draw text in screen space; `chars` reveals a typewriter prefix; colorAt(i) colours each char.
function drawText(S, str, x, y, sc, colorAt, shadow = P.ink, chars = Infinity) {
  [...str].forEach((ch, i) => {
    if (i >= chars) return;
    const g = FONT[ch] || FONT[" "];
    for (let r = 0; r < 7; r++) for (let c = 0; c < 5; c++) {
      if (g[r][c] !== "#") continue;
      if (shadow) S.rect(x + (i * 6 + c) * sc + sc, y + r * sc + sc, sc, sc, shadow);
      S.rect(x + (i * 6 + c) * sc, y + r * sc, sc, sc, colorAt(i));
    }
  });
}
function box(S, x, y, w, h, fill = P.paper) {
  S.rect(x - 1, y - 1, w + 2, h + 2, P.ink);
  S.rect(x, y, w, h, fill);
  S.rect(x, y + h, w + 1, 1, P.ink);
  S.rect(x + w, y, 1, h + 1, P.ink);
  S.rect(x + 1, y + h + 1, w + 1, 1, "#00000088");
}

// ------------------------------------------------------------------ static world

function buildWorld() {
  const c = document.createElement("canvas");
  c.width = LW; c.height = WH;
  const S = surface(c.getContext("2d"));
  S.oy = WORLD_TOP; // scene coordinates: y = 0 is the top of the original frame
  let seed = 1976;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);

  const skyBands = [P.sky0, P.sky1, P.sky2, P.sky3, P.sky4, P.sky5, P.sky6];
  for (let y = -WORLD_TOP; y < 160; y++) {
    const t = Math.min(0.999, Math.max(0, (y + WORLD_TOP) / (150 + WORLD_TOP))) * (skyBands.length - 1);
    const i = Math.floor(t), f = t - i;
    for (let x = 0; x < LW; x++) S.px(x, y, dith(x, y & 3, f) ? skyBands[Math.min(i + 1, 6)] : skyBands[i]);
  }
  for (let k = 0; k < 12; k++) {
    const cx = rnd() * LW, cy = -50 + rnd() * 130, rw = 30 + rnd() * 50, rh = 5 + rnd() * 8;
    for (let y = Math.floor(cy - rh); y <= cy + rh; y++) for (let x = Math.floor(cx - rw); x <= cx + rw; x++) {
      const d = ((x - cx) / rw) ** 2 + ((y - cy) / rh) ** 2;
      if (d < 1 && dith(x, y & 3, (1 - d) * 0.8)) S.px(x, y, y < cy - rh * 0.3 && dith(x + 1, y & 3, 0.3) ? P.cloudHi : P.cloud);
    }
  }
  const PEAK_X = 64, TOP = 70, BASE = 152, HALF = 130, H = BASE - TOP;
  for (let x = 0; x < LW; x++) {
    const d = Math.min(1, Math.abs(x - PEAK_X) / HALF);
    const top = BASE - H * Math.pow(Math.max(0, 1 - Math.max(0, d - 0.03) / 0.97), 1.7);
    const snowLine = TOP + 22 + (Math.sin(x * 0.9) + Math.sin(x * 2.3)) * 2 + rnd() * 3 + d * 10;
    for (let y = Math.round(top); y < BASE + 4; y++) {
      let col = x < PEAK_X ? (dith(x, y & 3, 0.35) ? P.fujiL : P.fuji) : (dith(x, y & 3, 0.4) ? P.fujiR : P.fuji);
      if (y < snowLine) col = x < PEAK_X - 2 ? (dith(x, y & 3, 0.5) ? P.snowS : P.snowD) : (dith(x, y & 3, 0.85) ? P.snow : P.snowS);
      if (dith(x, y & 3, Math.max(0, (y - 118) / 36) * 0.75)) col = y > 140 ? P.sky6 : P.sky5;
      S.px(x, y, col);
    }
  }
  for (let x = 0; x < 108; x++) {
    const top = 150 + Math.round(Math.sin(x * 0.7) * 2 + Math.sin(x * 0.23) * 3 + rnd() * 2);
    for (let y = top; y < 178; y++) S.px(x, y, y === top || dith(x, y & 3, 0.15) ? P.treesHi : P.trees);
  }
  for (let x = 98; x < LW; x++) {
    const roofY = Math.round(146 - (x - 98) * 0.12);
    for (let y = roofY; y < 178; y++) S.px(x, y, y < roofY + 2 ? P.roof : y < roofY + 5 ? P.stand : P.standHi);
    if (x % 14 === 0) for (let y = roofY + 2; y < 178; y++) S.px(x, y, P.stand);
  }
  const crowdTones = ["#1a1e24", "#2c3a52", "#4a5566", "#6d7684", "#c8ccd1", "#3a4a3e", "#b8a24a"];
  const crowd = [];
  for (let row = 0; row < 9; row++) {
    const y = 154 + row * 2 + (row % 2);
    for (let x = 101 + (row % 2); x < LW; x += 2) if (rnd() < 0.82) crowd.push([x, y, Math.floor(rnd() * crowdTones.length)]);
  }
  for (let y = 178; y < 206; y++) for (let x = 0; x < LW; x++) S.px(x, y, dith(x, y & 3, 0.18 + 0.15 * Math.sin(x * 0.05 + y)) ? P.asphaltHi : P.asphalt);
  for (let x = 0; x < LW; x++) { S.px(x, 179, P.line); if (x % 8 < 5) S.px(x, 204, P.whiteD); }
  // pit wall and wet pit lane
  S.rect(0, 206, LW, 9, P.wall); S.rect(0, 206, LW, 1, P.wallHi); S.rect(0, 214, LW, 1, P.wallLo);
  for (let x = 0; x < LW; x += 16) S.rect(x, 207, 1, 7, P.wallLo);
  for (let y = 215; y < LH; y++) for (let x = 0; x < LW; x++) S.px(x, y, dith(x, y & 3, 0.12 + Math.max(0, 1 - (y - 215) / 50) * 0.5) ? P.wetHi : P.wet);
  for (let y = 215; y < 222; y++) for (let x = 0; x < LW; x++) if (dith(x, y & 3, 0.45 - (y - 215) * 0.06)) S.px(x + ((y >> 1) & 1), y, mix(P.wall, P.wet, 0.55));
  for (let x = 0; x < LW; x++) if (x % 10 < 6) { S.px(x, 232, P.whiteD); S.px(x, 233, mix(P.whiteD, P.wet, 0.5)); }

  // fence layer drawn over cars on the track
  const f = document.createElement("canvas");
  f.width = LW; f.height = WH;
  const F = surface(f.getContext("2d"));
  F.oy = WORLD_TOP;
  for (let x = 0; x < LW; x++) {
    if (x % 11 === 3) for (let y = 184; y < 206; y++) F.px(x, y, P.post);
    for (const wy of [188, 194, 200]) if ((x + wy) % 2 === 0) F.px(x, wy, P.wire);
  }
  F.rect(126, 190, 14, 9, P.out);
  F.rect(128, 192, 10, 1, P.white); F.rect(128, 194, 7, 1, P.white); F.rect(128, 196, 9, 1, P.white);
  F.rect(132, 186, 1, 4, P.post);

  return { world: c, fence: f, crowd, crowdTones };
}

// ------------------------------------------------------------------ timeline

// Beats (seconds). The audio clips in index.html are placed on the same marks.
export const BEATS = {
  tiltEnd: 2.8,
  rival1: [1.55, 3.35],
  pointsIn: 2.15,
  rainUp: [3.95, 4.6],
  rainText: [4.05, 4.95],
  heroIn: [4.3, 5.95],
  climb: [6.05, 6.4],
  walk: [6.4, 10],
  rival2: [6.9, 8.5],
  flip: 7.4,
  finalText: 8.9,
};

export function createScene(canvas) {
  const { world, fence, crowd, crowdTones } = buildWorld();
  const frame = document.createElement("canvas");
  frame.width = LW; frame.height = LH;
  const fctx = frame.getContext("2d");
  const S = surface(fctx);
  canvas.width = LW * SCALE; canvas.height = LH * SCALE;
  const out = canvas.getContext("2d");
  out.imageSmoothingEnabled = false;

  const mech = mechanicSprite(1.3);
  const walkFrames = [laudaSprite(1.65, 0), laudaSprite(1.65, 1)];

  // Rain streaks in screen space: seeded base position and speed.
  const RAIN = 900;
  const drops = [];
  let seed = 42;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < RAIN; i++) drops.push({ x: rnd() * (LW + 60), y: rnd() * (LH + 20), v: 240 + rnd() * 120, near: rnd() < 0.3 });

  function drawSpray(x0, baseY, t, len = 110) {
    const fr = Math.floor(t * 30);
    for (let y = baseY - 42; y < baseY + 2; y++) for (let x = Math.max(0, Math.floor(x0)); x < Math.min(LW, x0 + len); x++) {
      const dx = x - x0, dy = baseY - y;
      const width = 3 + dx * 0.32;
      const d = dy / width;
      if (d < 1 && d > -0.15 && dith(x + fr, (y + fr) & 3, (1 - d * d) * Math.max(0, 1 - dx / len) * 0.7)) S.px(x, y, P.spray);
    }
  }

  function renderAt(t) {
    const fr = Math.floor(t * 30);
    // camera tilt: from the top of the sky down to the scene
    const camY = Math.round(lerp(0, WORLD_TOP, inOut(clamp01(t / BEATS.tiltEnd))));
    fctx.clearRect(0, 0, LW, LH);
    fctx.drawImage(world, 0, -camY);
    S.oy = WORLD_TOP - camY;

    // crowd shimmer: a few umbrellas twitch each frame
    crowd.forEach(([x, y, k], i) => { if (hash(i, fr >> 1) < 0.06) S.px(x, y, crowdTones[(k + 1) % crowdTones.length]); });

    // the white car on the track (Hunt), twice; spray trails behind it
    for (const [a, b] of [BEATS.rival1, BEATS.rival2]) {
      if (t < a || t > b + 0.4) continue;
      const k = (t - a) / (b - a);
      const x = Math.round(lerp(200, -80, k));
      drawSpray(x + 30, 201, t);
      carSprite(P.white, P.whiteD, "#ffffff", 0.8, P.whiteD, (t - a) * 400).blit(S, x, 186);
    }
    fctx.drawImage(fence, 0, -camY);

    // pit-exit light with a soft, slightly pulsing glow
    for (let y = 168; y < 300; y++) { S.px(13, y, P.post); S.px(14, y, P.greyD); }
    S.rect(9, 168, 10, 15, P.out);
    const pulse = 0.28 + 0.06 * Math.sin(t * 5);
    for (let r = 9; r >= 1; r--) for (let a = 0; a < 64; a++) {
      const gx = 14 + Math.cos((a / 64) * Math.PI * 2) * r, gy = 175 + Math.sin((a / 64) * Math.PI * 2) * r * 1.2;
      if (dith(Math.round(gx), Math.round(gy) & 3, pulse * (1 - r / 10))) S.px(gx, gy, P.lampGlow);
    }
    for (const [lx, ly] of [[11, 170], [15, 170], [11, 177], [15, 177]]) S.rect(lx, ly, 3, 3, P.lamp);
    S.px(11, 170, "#ffb2a8"); S.px(15, 170, "#ffb2a8");
    for (let y = 302; y < 318; y++) if (y % 3 !== 2) { S.px(13 + ((y >> 1) & 1), y, P.lampGlow); if (y < 310) S.px(15, y, P.lamp); }

    // mechanic waiting under his umbrella
    const mechY = 256 - mech.h;
    mech.reflect(S, 150, mechY, P.wet, 0.45);
    mech.blit(S, 150, mechY);

    // Lauda's car turns into the pits and brakes to a stop
    const heroStopX = 92, heroY = 226;
    let heroX = null, wheel = 0;
    if (t >= BEATS.heroIn[0]) {
      const k = clamp01((t - BEATS.heroIn[0]) / (BEATS.heroIn[1] - BEATS.heroIn[0]));
      heroX = Math.round(lerp(196, heroStopX, outCubic(k)));
      wheel = (196 - heroX) * 1.0;
    }
    const seated = t < BEATS.climb[0];
    const heroSprite = heroX !== null ? carSprite(P.red, P.redD, P.redH, 1.55, seated ? P.red : null, wheel) : null;

    // Lauda: rises out of the cockpit behind the car, then walks away toward us and left
    let lauda = null;
    if (t >= BEATS.climb[0]) {
      const sprite = walkFrames[t > BEATS.walk[0] ? Math.floor((t - BEATS.walk[0]) / 0.18) % 2 : 0];
      const feetY0 = 255, feetX0 = heroStopX + 34;
      let x = feetX0, feetY = feetY0;
      if (t < BEATS.climb[1]) {
        feetY = Math.round(lerp(feetY0 + 18, feetY0, outCubic((t - BEATS.climb[0]) / (BEATS.climb[1] - BEATS.climb[0]))));
      } else {
        const k = clamp01((t - BEATS.walk[0]) / (BEATS.walk[1] - BEATS.walk[0]));
        x = Math.round(lerp(feetX0, 30, k));
        feetY = Math.round(lerp(feetY0, 292, k));
      }
      const bob = t > BEATS.walk[0] && Math.floor((t - BEATS.walk[0]) / 0.18) % 2 ? 1 : 0;
      lauda = { sprite, x, y: feetY - sprite.bottom() - bob, feetY };
    }
    const carBase = heroY + (heroSprite ? heroSprite.bottom() : 0);
    const drawLauda = (clip) => {
      if (!lauda) return;
      if (lauda.feetY > carBase) lauda.sprite.reflect(S, lauda.x, lauda.y, P.wet, 0.6);
      lauda.sprite.blit(S, lauda.x, lauda.y, clip);
    };
    if (lauda && lauda.feetY <= carBase) drawLauda(t < BEATS.climb[1] ? carBase - 4 : Infinity);
    if (heroSprite) {
      heroSprite.reflect(S, heroX, heroY, P.wet);
      heroSprite.blit(S, heroX, heroY);
    }
    if (lauda && lauda.feetY > carBase) drawLauda();

    // rain in screen space: heavier from "the rain is brutal"
    S.oy = 0;
    const heavy = clamp01((t - BEATS.rainUp[0]) / (BEATS.rainUp[1] - BEATS.rainUp[0]));
    const count = Math.round(lerp(430, RAIN, heavy));
    for (let i = 0; i < count; i++) {
      const d = drops[i];
      const y = ((d.y + d.v * t) % (LH + 20)) - 10;
      const x = ((((d.x - d.v * 0.22 * t) % (LW + 60)) + LW + 60) % (LW + 60)) - 30;
      const len = d.near ? 6 : 3 + (i % 2);
      for (let k = 0; k < len; k++) S.px(x - Math.floor(k / 3), y + k, d.near ? P.rainHi : P.rain);
    }
    // splash crowns, re-seeded every two frames
    const splashes = Math.round(lerp(40, 110, heavy));
    for (let i = 0; i < splashes; i++) {
      const x = Math.floor(hash(i, fr >> 1) * LW);
      const y = 182 + Math.floor(hash(i + 999, fr >> 1) * (LH - 182)) - (WORLD_TOP - camY);
      if (y > 205 - (WORLD_TOP - camY) && y < 216 - (WORLD_TOP - camY)) continue;
      S.px(x, y, P.rainHi); S.px(x - 1, y - 1, P.rain); S.px(x + 1, y - 1, P.rain);
    }

    // ---------------- on-screen text (pixel font, typewriter reveal), all inside the safe band
    const type = (start, cps = 28) => Math.max(0, Math.floor((t - start) * cps));
    const center = (str, sc) => Math.round((LW - textWidth(str, sc)) / 2);
    if (t >= 0.2 && t < 2.0) {
      drawText(S, "FINAL RACE", center("FINAL RACE", 2), 40, 2, () => P.paper, P.ink, type(0.2, 20));
      drawText(S, "FUJI 1976", center("FUJI 1976", 1), 60, 1, () => P.whiteD, P.ink, type(0.75));
    }
    if (t >= BEATS.pointsIn && t < 10) {
      const flipped = t >= BEATS.flip;
      const pop = (start) => (t - start < 0.12 ? -2 : t - start < 0.2 ? -1 : 0);
      const dy = flipped ? pop(BEATS.flip) : pop(BEATS.pointsIn);
      const left = flipped ? ["HUNT 69", P.ink] : ["LAUDA 68", P.red];
      const right = flipped ? ["LAUDA 68", P.red] : ["HUNT 65", P.ink];
      box(S, 22, 34 + dy, 64, 13);
      drawText(S, left[0], 22 + Math.round((64 - textWidth(left[0], 1)) / 2), 37 + dy, 1, () => left[1], null);
      box(S, 94, 34 + dy, 64, 13);
      drawText(S, right[0], 94 + Math.round((64 - textWidth(right[0], 1)) / 2), 37 + dy, 1, () => right[1], null);
      if (!flipped && t > 2.45 && t < BEATS.rainText[0]) drawText(S, "+3", 72, 50, 1, () => P.lamp, P.ink);
    }
    if (t >= BEATS.rainText[0] && t < BEATS.rainText[1]) {
      drawText(S, "THE RAIN IS BRUTAL", center("THE RAIN IS BRUTAL", 1), 62, 1, () => P.paper, P.ink, type(BEATS.rainText[0], 34));
    }
    if (t >= BEATS.heroIn[0] + 0.2 && t < BEATS.climb[0]) {
      box(S, 74, 58, 32, 12);
      drawText(S, "LAP 2", 76, 61, 1, () => P.ink, null, type(BEATS.heroIn[0] + 0.2, 20));
    }
    if (t >= BEATS.finalText) {
      const shake = t - BEATS.finalText < 0.15 ? (fr % 2 ? 1 : -1) : 0;
      drawText(S, "LOST BY", center("LOST BY", 2) + shake, 60, 2, () => P.paper, P.ink, type(BEATS.finalText, 24));
      drawText(S, "1 POINT", center("1 POINT", 2) + shake, 79, 2, (i) => (i === 0 ? P.lamp : P.paper), P.ink, type(BEATS.finalText + 0.25, 24));
    }

    out.drawImage(frame, 0, 0, LW * SCALE, LH * SCALE);
  }
  return renderAt;
}
