// The ten scenes of the Lauda short. Each scene builds its static layers once and draws a
// frame from its local time u; `cue(n)` gives the local start time of the scene's n-th line.
import {
  LW, LH, P, dith, hash, clamp01, lerp, outCubic, inOut, seeded, mix, surface, makeCanvas, Sprite,
  carSprite, laudaSprite, mechanicSprite, runnerSprite, helmetSprite, drawFire, makeRain, drawRain,
  drawText, textWidth, box,
} from "./engine.js";

export const RAIN = makeRain(900, 42);
export const rainSurface = (S, t, count, region) => drawRain(S, RAIN, t, count, { region });

// ------------------------------------------------------------------ hospital room

export const HELMET_POS = [8, 112]; // shared by the hook and the final frame, so the film loops

export function buildHospital() {
  const c = makeCanvas(LW + 12, LH);
  const S = surface(c.getContext("2d"));
  for (let y = 0; y < 170; y++) for (let x = 0; x < LW + 12; x++) {
    const k = y / 170;
    S.px(x, y, dith(x, y, k * 0.9) ? P.room2 : dith(x, y, 0.5 + k * 0.4) ? P.room1 : P.room0);
  }
  // window with mullions; the glass is redrawn live for rain and passing days
  S.rect(10, 24, 58, 74, P.greyD);
  S.rect(12, 26, 54, 70, P.night);
  S.rect(38, 26, 2, 70, P.greyD); S.rect(12, 60, 54, 2, P.greyD);
  // curtain folds
  for (let y = 20; y < 112; y++) for (let x = 68; x < 78; x++) S.px(x, y, (x % 3 === 0) ? "#1a2336" : dith(x, y, 0.5) ? "#253150" : "#1f2a44");
  // wall monitor on an arm (bed sits below it)
  S.rect(150, 48, 22, 2, P.greyD);
  S.rect(110, 26, 46, 34, "#2a3036"); S.rect(110, 26, 46, 1, "#3d454d");
  S.rect(113, 29, 40, 26, P.screen);
  // IV stand at the foot of the bed: a saline bag and a darker bag of blood
  S.rect(176, 30, 1, 140, P.metal); S.rect(166, 30, 14, 1, P.metal);
  S.rect(166, 32, 6, 12, "#c9d6df"); S.rect(167, 37, 4, 6, "#9fb4c2");
  S.rect(174, 32, 6, 12, "#5e0f12"); S.rect(175, 34, 4, 9, "#8a161b"); S.px(176, 35, "#c23a3a");
  // a cold pool of light over the patient
  for (let y = 70; y < 170; y++) for (let x = 54; x < 180; x++) {
    const d = ((x - 108) / 64) ** 2 + ((y - 128) / 46) ** 2;
    if (d < 1 && dith(x, y, (1 - d) * 0.5)) S.px(x, y, mix(P.room2, "#3c5560", 0.55));
  }
  // bed frame, mattress, rails
  S.rect(54, 116, 4, 54, P.metal); S.rect(54, 116, 4, 1, P.white);
  S.rect(54, 150, 126, 5, P.greyD); S.rect(54, 150, 126, 1, P.metal);
  S.rect(58, 142, 122, 8, P.sheetD);
  for (let x = 60; x < 180; x += 7) S.rect(x, 155, 1, 15, P.greyD);
  S.rect(62, 166, 2, 4, P.tyre); S.rect(172, 166, 2, 4, P.tyre);
  // sheet over the body, with folds
  const sheetTop = (x) => 132 - Math.round(5 * Math.exp(-(((x - 116) / 14) ** 2)) + 3 * Math.exp(-(((x - 160) / 10) ** 2)));
  for (let x = 98; x < 180; x++) for (let y = sheetTop(x); y < 147; y++) S.px(x, y, y === sheetTop(x) ? P.sheetH : (x % 9 === 0 && y > sheetTop(x) + 2) ? P.sheetD : dith(x, y, 0.3) ? P.sheetD : P.sheet);
  // pillow
  const pillow = new Sprite(44, 16);
  pillow.ellipse(22, 8, 21, 7, P.sheetH); pillow.rect(4, 10, 36, 3, P.sheet);
  pillow.outline(P.out).blit(S, 58, 128);
  // the patient, lying face-up: head in profile (crown on the pillow, chin to the right),
  // bandaged and burned, under an oxygen mask, a bandaged arm on the sheet
  const pat = new Sprite(124, 72);
  // burns in patches (3×2-pixel blocks) over skin, so the face shape still reads
  const burn = (x, y) => {
    const h = hash(Math.floor(x / 3) * 7 + 3, Math.floor(y / 2) * 13 + 1), fine = hash(x, y);
    if (h < 0.28) return fine < 0.7 ? "#9e3326" : "#6a2219";
    if (h < 0.42) return fine < 0.6 ? "#4a1913" : "#2e100c";
    if (h < 0.55) return "#d88a78";
    return fine < 0.85 ? P.skin : "#c9967a";
  };
  pat.ellipse(60, 52, 13, 6, P.white); // gauze over neck and shoulder
  pat.ellipse(28, 40, 18, 13, "skull"); // head lying face-up: crown on the pillow (left), chin right
  pat.poly([[34, 30], [37, 21], [40, 21], [42, 30]], "face"); // nose pointing up
  pat.poly([[41, 30], [45, 29], [48, 32], [49, 37], [44, 40]], "face"); // lips and chin
  pat.poly([[44, 38], [50, 40], [56, 48], [46, 50]], "face"); // throat
  for (let y = 0; y < pat.h; y++) for (let x = 0; x < pat.w; x++) {
    const c = pat.get(x, y);
    if (c === "skull") pat.set(x, y, x < 25 ? ((x + y) % 4 === 0 ? "#c7ccd1" : P.white) : burn(x, y));
    else if (c === "face") pat.set(x, y, burn(x, y));
  }
  for (let y = 26; y < 36; y++) for (let x = 24; x < 31; x++) if (pat.get(x, y)) pat.set(x, y, (x + y) % 4 ? P.white : "#c7ccd1"); // forehead wrap
  for (const [bx, by, r] of [[14, 36, 3], [21, 30, 2], [12, 46, 2], [27, 29, 2]]) // blood soaking through
    for (let y = -r; y <= r; y++) for (let x = -r; x <= r; x++) if (x * x + y * y <= r * r && pat.get(bx + x, by + y)) pat.set(bx + x, by + y, x * x + y * y < r ? "#6e0c0c" : "#9e2a26");
  // profile edge in a darker skin tone so forehead, nose, lips and chin read clearly
  for (let y = 1; y < pat.h - 1; y++) for (let x = 1; x < pat.w - 1; x++) {
    const c = pat.get(x, y);
    if (c && c !== P.white && c !== "#c7ccd1" && !pat.get(x, y - 1)) pat.set(x, y, "#7a4a38");
  }
  pat.ellipse(29, 44, 3, 4, "#a8705a"); pat.set(29, 44, "#5a3326"); // ear
  pat.rect(44, 31, 3, 1, "#5a1f18"); // cracked lips at the mask's edge
  pat.rect(31, 32, 5, 1, P.ink); pat.rect(30, 31, 7, 1, "#8c2f24"); pat.rect(31, 33, 5, 1, "#a83a2c"); // swollen shut eye
  pat.ellipse(41, 26, 6, 4, "#7fa79b"); pat.ellipse(41, 26, 4, 2, "#557f73"); pat.rect(36, 25, 11, 1, "#c9ddd7"); // oxygen mask
  for (let i = 0; i < 12; i++) pat.set(36 - i, 29 + Math.round(i * 0.5), "#8fb3a8"); // mask strap
  pat.thick(66, 54, 100, 58, 3, P.white); // bandaged arm
  for (let x = 68; x < 100; x += 3) pat.rect(x, 55 + Math.round((x - 66) * 0.12), 1, 4, "#c7ccd1");
  pat.ellipse(105, 59, 5, 3, P.skin);
  for (let y = 55; y < 64; y++) for (let x = 99; x < 112; x++) if (pat.get(x, y) === P.skin) pat.set(x, y, burn(x, y));
  pat.rect(92, 56, 5, 2, "#e8e8e8"); // tape over the IV line
  pat.outline(P.out).blit(S, 50, 82);
  // oxygen tube to the wall, IV line to the drip
  for (let i = 0; i <= 40; i++) { const k = i / 40; S.px(lerp(91, 106, k), lerp(105, 60, k) + Math.sin(k * 6) * 2, "#8fb3a8"); }
  for (let i = 0; i <= 60; i++) { const k = i / 60; S.px(lerp(144, 170, k), lerp(138, 44, k) - Math.sin(k * 3.14) * 10, "#a8b8c2"); }
  S.rect(104, 58, 4, 3, P.greyD);
  // floor tiles
  for (let y = 170; y < LH; y++) for (let x = 0; x < LW + 12; x++) S.px(x, y, (x % 16 === 0 || y % 12 === 0) ? "#151a1f" : dith(x, y, 0.3) ? "#1d242a" : "#1a2026");
  // bedside table
  S.rect(4, 148, 48, 4, "#4a4f55"); S.rect(4, 148, 48, 1, "#6a7076");
  S.rect(8, 152, 40, 18, "#33383e"); S.rect(10, 158, 36, 1, "#24282d");
  return c;
}

export function drawWindowGlass(S, t, dayCycle = 0) {
  // night sky, or cycling day/night while days pass
  const light = dayCycle ? (Math.sin(t * dayCycle) * 0.5 + 0.5) : 0;
  for (let y = 26; y < 96; y++) for (let x = 12; x < 66; x++) {
    if (x === 38 || x === 39 || y === 60 || y === 61) continue;
    const base = mix(P.night, "#6f8fb3", light);
    S.px(x, y, dith(x, y, 0.3 + (y - 26) / 140) ? mix(base, P.nightHi, 0.6) : base);
  }
  for (let i = 0; i < 18; i++) { // distant city lights
    const x = 13 + Math.floor(hash(i, 5) * 52), y = 80 + Math.floor(hash(i, 9) * 15);
    if (x !== 38 && x !== 39 && hash(i, Math.floor(t * 2)) < 0.85) S.px(x, y, i % 3 ? "#c9a85a" : "#7fa0c8");
  }
  rainSurface(S, t, 520, [12, 26, 66, 96]);
}

export function drawECG(S, t, x0, y0, w, h, { bpm = 70, irregular = 0, thick = 1 } = {}) {
  const period = 60 / bpm;
  const scroll = t * 40;
  let prevY = 0;
  for (let x = 0; x < w; x++) {
    const tt = (x + scroll) / 40;
    const ph = ((tt % period) + period) % period / period;
    const jitter = irregular ? (hash(Math.floor(tt / period), 3) - 0.5) * irregular : 0;
    let v = 0;
    if (ph > 0.1 && ph < 0.14) v = -0.25;
    else if (ph > 0.18 && ph < 0.2) v = 0.25;
    else if (ph >= 0.2 && ph < 0.235) v = -1 - jitter;
    else if (ph >= 0.235 && ph < 0.26) v = 0.45;
    else if (ph > 0.45 && ph < 0.55) v = -0.18 * Math.sin((ph - 0.45) / 0.1 * Math.PI);
    const y = Math.round(y0 + h / 2 + v * (h / 2 - 2));
    const fade = (w - x) / w; // newest trace brightest at the right edge
    const col = fade < 0.25 ? P.ecg : mix(P.ecg, P.ecgD, Math.min(0.8, fade));
    const from = x === 0 ? y : prevY; // join each sample to the last so spikes are solid lines
    for (let yy = Math.min(from, y); yy <= Math.max(from, y); yy++) for (let k = 0; k < thick; k++) S.px(x0 + x + k, yy, col);
    prevY = y;
  }
}

// ------------------------------------------------------------------ Monza (sun)

export function buildMonza() {
  const c = makeCanvas();
  const S = surface(c.getContext("2d"));
  const bands = [P.blue0, P.blue1, P.blue2, P.blue3];
  for (let y = 0; y < 120; y++) {
    const k = (y / 120) * 3, i = Math.floor(k);
    for (let x = 0; x < LW; x++) S.px(x, y, dith(x, y, k - i) ? bands[Math.min(i + 1, 3)] : bands[i]);
  }
  const r = seeded(9);
  for (let k = 0; k < 5; k++) { // cumulus
    const cx = r() * LW, cy = 18 + r() * 50, rw = 14 + r() * 18;
    for (let y = -8; y < 6; y++) for (let x = -rw; x <= rw; x++) {
      const d = (x / rw) ** 2 + ((y + 1) / 7) ** 2 + (hash(Math.round(x + cx), 1) - 0.5) * 0.2;
      if (d < 1) S.px(cx + x, cy + y, y > 2 ? P.cloudS : P.cloudW);
    }
  }
  // umbrella pines and a grandstand
  for (let i = 0; i < 9; i++) {
    const x = 6 + i * 22 + Math.floor(r() * 8), top = 82 + Math.floor(r() * 10);
    S.rect(x + 7, top + 8, 2, 120 - top, P.trunk);
    for (let y = 0; y < 10; y++) for (let dx = -10; dx <= 10; dx++) if ((dx / 10) ** 2 + ((y - 4) / 5) ** 2 < 1) S.px(x + 8 + dx, top + y, y < 4 && dith(dx, y, 0.6) ? P.pineHi : P.pine);
  }
  S.rect(0, 106, LW, 22, "#c7cdd3"); S.rect(0, 106, LW, 2, "#e1e5e9");
  const crowd = ["#d23b2f", "#f2f2f2", "#2d5fa8", "#f4c542", "#2e2e2e", "#3d8c4f"];
  for (let y = 110; y < 126; y += 2) for (let x = (y / 2) % 2; x < LW; x += 2) if (r() < 0.85) S.px(x, y, crowd[Math.floor(r() * crowd.length)]);
  for (let x = 0; x < LW; x += 18) S.rect(x, 104, 1, 24, "#9aa3ab");
  S.rect(0, 128, LW, 6, P.grass); S.rect(0, 128, LW, 1, P.grassHi);
  for (let y = 134; y < 196; y++) for (let x = 0; x < LW; x++) S.px(x, y, dith(x, y, 0.25) ? P.tarmacHi : P.tarmac);
  S.rect(0, 135, LW, 1, P.kerbW); S.rect(0, 190, LW, 1, P.kerbW);
  for (let x = 0; x < LW; x += 8) S.rect(x, 191, 4, 4, x % 16 ? P.kerbW : P.red);
  for (let y = 195; y < LH; y++) for (let x = 0; x < LW; x++) S.px(x, y, dith(x, y, 0.3) ? P.grassHi : y % 7 === 0 ? P.grassD : P.grass);
  return c;
}

// ------------------------------------------------------------------ Nürburgring

export const RING_PATH = [[-14, 186], [30, 176], [78, 184], [122, 166], [118, 140], [70, 132], [56, 112], [96, 98], [150, 94], [196, 80]];
export function ringPoint(k) {
  const n = RING_PATH.length - 1, f = clamp01(k) * n, i = Math.min(n - 1, Math.floor(f)), u = f - i;
  const p0 = RING_PATH[Math.max(0, i - 1)], p1 = RING_PATH[i], p2 = RING_PATH[i + 1], p3 = RING_PATH[Math.min(n, i + 2)];
  const cr = (a, b, c, d) => 0.5 * (2 * b + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u * u + (-a + 3 * b - 3 * c + d) * u * u * u);
  return [cr(p0[0], p1[0], p2[0], p3[0]), cr(p0[1], p1[1], p2[1], p3[1])];
}
export function buildRing() {
  const c = makeCanvas();
  const S = surface(c.getContext("2d"));
  for (let y = 0; y < 90; y++) for (let x = 0; x < LW; x++) S.px(x, y, dith(x, y, y / 90) ? P.fogHi : P.fog);
  const r = seeded(31);
  const ridge = (base, amp, freq, col, colHi, seedOff) => {
    for (let x = 0; x < LW; x++) {
      const top = Math.round(base - amp * (0.6 * Math.sin(x * freq + seedOff) + 0.4 * Math.sin(x * freq * 2.7 + seedOff * 2)));
      for (let y = top; y < LH; y++) S.px(x, y, y < top + 2 || dith(x, y, 0.2) ? colHi : col);
    }
  };
  ridge(70, 10, 0.03, P.hill0, P.hill1, 1);
  ridge(92, 12, 0.045, P.hill1, P.hill2, 3);
  ridge(118, 10, 0.05, P.forest, P.forestHi, 5);
  // forest canopy texture: little pointed trees everywhere below the far ridge
  for (let i = 0; i < 900; i++) {
    const x = Math.floor(r() * LW), y = 74 + Math.floor(r() * 140);
    const h = 2 + Math.floor((y - 70) / 40);
    for (let k = 0; k < h; k++) for (let dx = -Math.floor(k / 2); dx <= Math.floor(k / 2); dx++) S.px(x + dx, y + k, k === 0 ? P.forestHi : dith(x, y + k, 0.5) ? P.hill2 : P.forest);
  }
  // the track: a grey ribbon, wider in the foreground
  for (let s = 0; s <= 900; s++) {
    const [x, y] = ringPoint(s / 900);
    const w = Math.max(1.5, (y - 70) / 22);
    for (let dy = -w; dy <= w; dy++) S.px(x, y + dy, Math.abs(dy) > w - 1 ? P.armco : dith(x, y + dy, 0.3) ? "#4d545c" : "#40464e");
  }
  // low fog bank
  for (let y = 60; y < 104; y++) for (let x = 0; x < LW; x++) if (dith(x, y, 0.35 * (1 - Math.abs(y - 84) / 22))) S.px(x, y, P.fogHi);
  return c;
}

// ------------------------------------------------------------------ crash site

export function buildCrash() {
  const c = makeCanvas();
  const S = surface(c.getContext("2d"));
  for (let y = 0; y < 70; y++) for (let x = 0; x < LW; x++) S.px(x, y, dith(x, y, y / 70) ? P.fogHi : P.fog);
  const r = seeded(55);
  for (let i = 0; i < 60; i++) { // tall conifers behind the barrier
    const x = Math.floor(r() * LW), top = 30 + Math.floor(r() * 40), w = 6 + Math.floor(r() * 6);
    for (let y = top; y < 152; y++) {
      const half = Math.min(w, Math.floor((y - top) / 2.2));
      for (let dx = -half; dx <= half; dx++) S.px(x + dx, y, dx < -half + 2 ? P.forestHi : dith(x + dx, y, 0.4) ? P.hill1 : P.forest);
    }
  }
  S.rect(0, 140, LW, 12, P.grassD);
  for (let x = 0; x < LW; x++) if (hash(x, 2) < 0.4) S.px(x, 139, P.grass);
  // armco barrier with posts
  S.rect(0, 146, LW, 6, P.armco); S.rect(0, 148, LW, 1, P.armcoD); S.rect(0, 151, LW, 1, P.armcoD);
  for (let x = 4; x < LW; x += 14) S.rect(x, 146, 2, 12, P.armcoD);
  for (let y = 152; y < 190; y++) for (let x = 0; x < LW; x++) S.px(x, y, dith(x, y, 0.2) ? P.asphaltHi : P.asphalt);
  S.rect(0, 153, LW, 1, P.line); S.rect(0, 189, LW, 1, P.line);
  for (let y = 190; y < LH; y++) for (let x = 0; x < LW; x++) S.px(x, y, dith(x, y, 0.3) ? P.grassD : "#2c4a24");
  return c;
}

// ------------------------------------------------------------------ Fuji world (storm)

export const FUJI_TOP = 60; // extra sky above scene y = 0
export function buildFuji() {
  const H = FUJI_TOP + 430;
  const c = makeCanvas(LW, H);
  const S = surface(c.getContext("2d"));
  S.oy = FUJI_TOP;
  const r = seeded(1976);
  const bands = [P.sky0, P.sky1, P.sky2, P.sky3, P.sky4, P.sky5, P.sky6];
  for (let y = -FUJI_TOP; y < 160; y++) {
    const t = clamp01((y + FUJI_TOP) / (150 + FUJI_TOP)) * 5.99, i = Math.floor(t);
    for (let x = 0; x < LW; x++) S.px(x, y, dith(x, y, t - i) ? bands[i + 1] : bands[i]);
  }
  for (let k = 0; k < 12; k++) {
    const cx = r() * LW, cy = -50 + r() * 130, rw = 30 + r() * 50, rh = 5 + r() * 8;
    for (let y = Math.floor(cy - rh); y <= cy + rh; y++) for (let x = Math.floor(cx - rw); x <= cx + rw; x++) {
      const d = ((x - cx) / rw) ** 2 + ((y - cy) / rh) ** 2;
      if (d < 1 && dith(x, y, (1 - d) * 0.8)) S.px(x, y, y < cy - rh * 0.3 && dith(x + 1, y, 0.3) ? P.cloudHi : P.cloud);
    }
  }
  const PEAK_X = 64, TOP = 70, BASE = 152, HALF = 130, Hh = BASE - TOP;
  for (let x = 0; x < LW; x++) {
    const d = Math.min(1, Math.abs(x - PEAK_X) / HALF);
    const top = BASE - Hh * Math.pow(Math.max(0, 1 - Math.max(0, d - 0.03) / 0.97), 1.7);
    const snowLine = TOP + 22 + (Math.sin(x * 0.9) + Math.sin(x * 2.3)) * 2 + r() * 3 + d * 10;
    for (let y = Math.round(top); y < BASE + 4; y++) {
      let col = x < PEAK_X ? (dith(x, y, 0.35) ? P.fujiL : P.fuji) : (dith(x, y, 0.4) ? P.fujiR : P.fuji);
      if (y < snowLine) col = x < PEAK_X - 2 ? (dith(x, y, 0.5) ? P.snowS : P.snowD) : (dith(x, y, 0.85) ? P.snow : P.snowS);
      if (dith(x, y, Math.max(0, (y - 118) / 36) * 0.75)) col = y > 140 ? P.sky6 : P.sky5;
      S.px(x, y, col);
    }
  }
  for (let x = 0; x < 108; x++) {
    const top = 150 + Math.round(Math.sin(x * 0.7) * 2 + Math.sin(x * 0.23) * 3 + r() * 2);
    for (let y = top; y < 178; y++) S.px(x, y, y === top || dith(x, y, 0.15) ? P.treesHi : P.trees);
  }
  for (let x = 98; x < LW; x++) {
    const roofY = Math.round(146 - (x - 98) * 0.12);
    for (let y = roofY; y < 178; y++) S.px(x, y, y < roofY + 2 ? P.roof : y < roofY + 5 ? P.stand : P.standHi);
    if (x % 14 === 0) for (let y = roofY + 2; y < 178; y++) S.px(x, y, P.stand);
  }
  const crowdTones = ["#1a1e24", "#2c3a52", "#4a5566", "#6d7684", "#c8ccd1", "#3a4a3e", "#b8a24a"];
  for (let row = 0; row < 9; row++) {
    const y = 154 + row * 2 + (row % 2);
    for (let x = 101 + (row % 2); x < LW; x += 2) if (r() < 0.82) S.px(x, y, crowdTones[Math.floor(r() * crowdTones.length)]);
  }
  for (let y = 178; y < 206; y++) for (let x = 0; x < LW; x++) S.px(x, y, dith(x, y, 0.18 + 0.15 * Math.sin(x * 0.05 + y)) ? P.asphaltHi : P.asphalt);
  for (let x = 0; x < LW; x++) { S.px(x, 179, P.line); if (x % 8 < 5) S.px(x, 204, P.whiteD); }
  S.rect(0, 206, LW, 9, P.wall); S.rect(0, 206, LW, 1, P.wallHi); S.rect(0, 214, LW, 1, P.wallLo);
  for (let x = 0; x < LW; x += 16) S.rect(x, 207, 1, 7, P.wallLo);
  for (let y = 215; y < 430; y++) for (let x = 0; x < LW; x++) S.px(x, y, dith(x, y, 0.12 + Math.max(0, 1 - (y - 215) / 50) * 0.5) ? P.wetHi : P.wet);
  for (let y = 215; y < 222; y++) for (let x = 0; x < LW; x++) if (dith(x, y, 0.45 - (y - 215) * 0.06)) S.px(x + ((y >> 1) & 1), y, mix(P.wall, P.wet, 0.55));
  for (let x = 0; x < LW; x++) if (x % 10 < 6) { S.px(x, 232, P.whiteD); S.px(x, 233, mix(P.whiteD, P.wet, 0.5)); }

  const f = makeCanvas(LW, H);
  const F = surface(f.getContext("2d"));
  F.oy = FUJI_TOP;
  for (let x = 0; x < LW; x++) {
    if (x % 11 === 3) for (let y = 184; y < 206; y++) F.px(x, y, P.post);
    for (const wy of [188, 194, 200]) if ((x + wy) % 2 === 0) F.px(x, wy, P.wire);
  }
  F.rect(126, 190, 14, 9, P.out);
  F.rect(128, 192, 10, 1, P.white); F.rect(128, 194, 7, 1, P.white); F.rect(128, 196, 9, 1, P.white);
  F.rect(132, 186, 1, 4, P.post);
  return { world: c, fence: f };
}

export const MECH = mechanicSprite(1.3);
export const WALK = [laudaSprite(1.65, 0), laudaSprite(1.65, 1)];
export const FUJI_CAM_LOW = 150; // world-canvas y at the top of the view once tilted down (scene y 90)
export const HERO_STOP_X = 92, HERO_Y = 226;

export function drawSpray(S, x0, baseY, t, len = 110) {
  const fr = Math.floor(t * 30);
  for (let y = baseY - 42; y < baseY + 2; y++) for (let x = Math.max(0, Math.floor(x0)); x < Math.min(LW, x0 + len); x++) {
    const dx = x - x0, dy = baseY - y, d = dy / (3 + dx * 0.32);
    if (d < 1 && d > -0.15 && dith(x + fr, y + fr, (1 - d * d) * Math.max(0, 1 - dx / len) * 0.7)) S.px(x, y, P.spray);
  }
}
export function drawPitLight(S, t) {
  for (let y = 168; y < 300; y++) { S.px(13, y, P.post); S.px(14, y, P.greyD); }
  S.rect(9, 168, 10, 15, P.out);
  const pulse = 0.28 + 0.06 * Math.sin(t * 5);
  for (let rr = 9; rr >= 1; rr--) for (let a = 0; a < 64; a++) {
    const gx = 14 + Math.cos((a / 64) * Math.PI * 2) * rr, gy = 175 + Math.sin((a / 64) * Math.PI * 2) * rr * 1.2;
    if (dith(Math.round(gx), Math.round(gy), pulse * (1 - rr / 10))) S.px(gx, gy, P.lampGlow);
  }
  for (const [lx, ly] of [[11, 170], [15, 170], [11, 177], [15, 177]]) S.rect(lx, ly, 3, 3, P.lamp);
  S.px(11, 170, "#ffb2a8"); S.px(15, 170, "#ffb2a8");
  for (let y = 302; y < 318; y++) if (y % 3 !== 2) { S.px(13 + ((y >> 1) & 1), y, P.lampGlow); if (y < 310) S.px(15, y, P.lamp); }
}
export function drawRival(S, t, a, b) {
  if (t < a || t > b + 0.4) return;
  const x = Math.round(lerp(200, -80, (t - a) / (b - a)));
  drawSpray(S, x + 30, 201, t);
  carSprite(P.white, P.whiteD, "#ffffff", 0.8, P.whiteD, (t - a) * 400).blit(S, x, 186);
}
export function scoreBoxes(S, flipped, popT) {
  const dy = popT < 0.12 ? -2 : popT < 0.2 ? -1 : 0;
  const left = flipped ? ["HUNT 69", P.ink] : ["LAUDA 68", P.red];
  const right = flipped ? ["LAUDA 68", P.red] : ["HUNT 65", P.ink];
  box(S, 22, 36 + dy, 64, 13);
  drawText(S, left[0], 22 + Math.round((64 - textWidth(left[0])) / 2), 39 + dy, 1, left[1], null);
  box(S, 94, 36 + dy, 64, 13);
  drawText(S, right[0], 94 + Math.round((64 - textWidth(right[0])) / 2), 39 + dy, 1, right[1], null);
}

// ------------------------------------------------------------------ scene table

export function makeScenes() {
  const hospital = buildHospital();
  const monza = buildMonza();
  const ring = buildRing();
  const crash = buildCrash();
  const fuji = buildFuji();

  const blitBg = (S, canvas, ox = 0, oy = 0) => S.ctx.drawImage(canvas, -ox, -oy);

  return {
    // 1. "Doctors didn't think this man would survive." — hospital at night, scorched helmet.
    hook(S, u, { t }) {
      const pan = Math.round(lerp(10, 0, outCubic(u / 3)));
      blitBg(S, hospital, pan);
      S.ox = -pan;
      drawWindowGlass(S, t);
      drawECG(S, t, 113, 29, 40, 26, { bpm: 54 });
      helmetSprite(1.4, true).blit(S, HELMET_POS[0], HELMET_POS[1]);
      S.ox = 0;
    },

    // 2. "Forty-two days later... he was racing again." — days flick past, then the grid at Monza.
    comeback(S, u, { cue, t }) {
      const cut = cue(1) - 0.15;
      if (u < cut) {
        blitBg(S, hospital);
        drawWindowGlass(S, t, 22); // day/night flicker through the window
        drawECG(S, t, 113, 29, 40, 26, { bpm: 72 });
        helmetSprite(1.4, true).blit(S, HELMET_POS[0], HELMET_POS[1]);
        S.dithRect(0, 0, LW, LH, P.ink, 0.45);
        const day = Math.min(42, Math.round(42 * inOut((u - 0.15) / Math.max(0.3, cut - 0.45))));
        const label = `DAY ${day}`;
        box(S, 50, 70, 80, 22);
        drawText(S, label, 90 - Math.round(textWidth(label, 2) / 2), 74, 2, day === 42 ? P.red : P.ink, null);
      } else {
        blitBg(S, monza);
        const shake = (Math.floor(t * 30) % 2) * (u - cut < 1.2 ? 1 : 0);
        carSprite(P.red, P.redD, P.redH, 1.55, P.red, 0).blit(S, 60 + shake, 148);
      }
    },

    // 3. "But that's not the bravest thing he did." — he launches away; the world drains of colour.
    loop(S, u, { t }) {
      blitBg(S, monza);
      const k = clamp01((u - 0.25) / 1.1);
      const x = Math.round(60 - 260 * k * k);
      if (x > -90) carSprite(P.red, P.redD, P.redH, 1.55, P.red, k * 300).blit(S, x, 148);
      S.dithRect(0, 0, LW, LH, P.ink, clamp01((u - 0.9) / 1.4) * 0.7);
    },

    // 4. "Niki Lauda. World champion. At the track drivers call the Green Hell."
    ring(S, u, { t, dur }) {
      blitBg(S, ring);
      const [x, y] = ringPoint(lerp(0.02, 0.98, u / dur));
      for (let k = 1; k <= 6; k++) { // spray trail behind the car
        const [tx, ty] = ringPoint(lerp(0.02, 0.98, (u - k * 0.05) / dur));
        if (dith(tx, ty, 0.6 - k * 0.08)) S.px(tx, ty - 1, P.fogHi);
      }
      S.rect(x - 3, y - 3, 7, 5, P.out);
      S.rect(x - 2, y - 2, 5, 3, P.red);
      S.rect(x - 2, y - 2, 5, 1, P.redH);
      for (let y2 = 60; y2 < 110; y2++) for (let x2 = 0; x2 < LW; x2++) if (dith(x2 + Math.floor(t * 6), y2, 0.12 * (1 - Math.abs(y2 - 86) / 26))) S.px(x2, y2, P.fogHi);
    },

    // 5. "Lap two. His car hits the barrier and erupts in flames. Drivers drag him out."
    crash(S, u, { cue, t }) {
      const impact = cue(1) + 0.95;
      const shake = u > impact && u < impact + 0.35 ? Math.round((hash(Math.floor(t * 30), 1) - 0.5) * 4) : 0;
      S.ox = shake;
      blitBg(S, crash, -shake);
      let carX, carY = 162, wobble = 0;
      if (u < impact) {
        const k = clamp01(u / impact);
        carX = Math.round(lerp(200, 74, k));
        if (u > impact - 0.55) { wobble = Math.round(Math.sin(u * 40) * 2); carY = Math.round(lerp(162, 150, (u - (impact - 0.55)) / 0.55)); }
      } else { carX = 74; carY = 150; }
      if (u >= impact) drawFire(S, carX + 30, carY + 16, 16, 26, t, clamp01((u - impact) / 0.25) * (u > cue(2) + 0.6 ? 0.7 : 1));
      carSprite(P.red, P.redD, P.redH, 1.2, P.red, u * 300).blit(S, carX + wobble, carY, { tint: u > impact ? ["#2a1410", 0.35] : null });
      if (u >= impact) drawFire(S, carX + 26, carY + 14, 10, 14, t + 0.3, 0.8);
      // other drivers stop and run to him
      const stop = cue(2) - 0.35;
      if (u > stop - 0.6) {
        const k = clamp01((u - (stop - 0.6)) / 0.6);
        carSprite(P.white, P.whiteD, "#ffffff", 1.0, "#f4c542", 0).blit(S, Math.round(lerp(200, 132, outCubic(k))), 166);
      }
      if (u > stop) {
        const run = clamp01((u - stop) / 0.9);
        const step = Math.floor(t * 8) % 2;
        runnerSprite("#f4c542", "#f4c542", step).blit(S, Math.round(lerp(140, 104, run)), 164);
        runnerSprite("#2d5fa8", P.white, 1 - step).blit(S, Math.round(lerp(158, 116, run)), 166);
        runnerSprite("#e6eaee", "#3d8c4f", step).blit(S, Math.round(lerp(174, 126, run)), 163);
      }
      S.ox = 0;
    },

    // 6. "Burned. Toxic fumes in his lungs. For days, he fights for his life." — the monitor.
    hospital(S, u, { cue, t }) {
      for (let y = 0; y < LH; y++) for (let x = 0; x < LW; x++) S.px(x, y, dith(x, y, 0.5) ? P.room1 : P.room0);
      S.rect(16, 46, 148, 108, "#2a3036"); S.rect(16, 46, 148, 2, "#3d454d"); S.rect(16, 152, 148, 2, "#1d2125");
      S.rect(22, 52, 136, 92, P.screen);
      for (let y = 52; y < 144; y += 2) S.rect(22, y, 136, 1, "#06100a"); // scanlines
      const recovering = u > cue(2);
      drawECG(S, t, 24, 66, 132, 54, { bpm: recovering ? 64 : 104, irregular: recovering ? 0.1 : 0.9, thick: 2 });
      const blink = Math.floor(t * 2) % 2;
      S.rect(138, 132, 6, 6, recovering ? P.ecg : blink ? P.lamp : P.lampGlow);
      S.rect(26, 132, 3, 6, P.ecgD); S.rect(30, 130, 3, 8, P.ecgD); S.rect(34, 128, 3, 10, P.ecgD);
      S.rect(80, 154, 20, 22, "#2a3036"); S.rect(60, 176, 60, 3, "#2a3036");
    },

    // 7. "Then, at Monza, he pulls a helmet over still-bleeding wounds... and finishes fourth."
    monza(S, u, { cue, t }) {
      const finish = cue(1) - 0.15;
      if (u < finish) {
        // close-up: balaclava, a fresh stain at the temple, gloves pulling the helmet down
        for (let y = 0; y < LH; y++) for (let x = 0; x < LW; x++) S.px(x, y, dith(x, y, y / 260) ? P.blue2 : P.blue1);
        const bust = new Sprite(LW, LH);
        bust.poly([[34, 212], [52, 146], [128, 146], [146, 212]], P.red);
        bust.poly([[52, 146], [72, 140], [108, 140], [128, 146], [124, 154], [56, 154]], P.redH);
        bust.rect(84, 150, 2, 60, P.redD);
        bust.rect(70, 168, 12, 5, P.white);
        bust.rect(78, 126, 24, 16, P.knit);
        bust.ellipse(90, 104, 19, 22, P.knit);
        bust.rect(76, 100, 28, 6, P.skin);
        bust.set(83, 102, P.ink); bust.set(97, 102, P.ink);
        bust.rect(104, 92, 2, 3, P.redD); bust.set(105, 95, P.red); // still bleeding
        const k = outCubic((u - 0.4) / (finish - 0.9));
        const hy = Math.round(lerp(42, 103, k));
        const hand = (sx) => { bust.thick(90 + sx * 40, 148, 90 + sx * 33, hy + 10, 6, P.red); bust.thick(90 + sx * 33, hy + 10, 90 + sx * 26, hy + 2, 5, P.coat); };
        hand(-1); hand(1);
        bust.ellipse(90, hy, 26, 25, P.red);
        bust.ellipse(84, hy - 10, 14, 8, P.redH);
        bust.rect(66, hy - 3, 48, 11, P.visor);
        bust.rect(70, hy - 1, 14, 2, P.glint);
        bust.rect(88, hy - 25, 4, 22, P.white);
        bust.rect(70, hy + 18, 40, 4, P.redD);
        bust.outline(P.out).blit(S, 0, 0);
      } else {
        blitBg(S, monza);
        const k = clamp01((u - finish) / 1.0);
        const x = Math.round(lerp(190, -90, k));
        carSprite(P.red, P.redD, P.redH, 1.55, P.red, k * 600).blit(S, x, 148);
        for (let y = 134; y < 191; y++) if ((y >> 1) % 2 === 0) { S.px(100, y, P.white); S.px(101, y, P.ink); } else { S.px(100, y, P.ink); S.px(101, y, P.white); }
        // pit board on a pole, flipping to P4 as he passes
        S.rect(146, 64, 2, 70, P.greyD);
        const shown = u > finish + 0.35;
        box(S, 128, 50, 38, 24, shown ? P.ink : "#30353d");
        if (shown) drawText(S, "P4", 147 - Math.round(textWidth("P4", 2) / 2), 55, 2, P.paper, null);
      }
    },

    // 8. "Final race. Japan. He leads James Hunt by three points. And the rain is brutal."
    fuji(S, u, { cue, t }) {
      const camY = Math.round(lerp(0, FUJI_CAM_LOW, inOut(u / 3.0)));
      blitBg(S, fuji.world, 0, camY);
      S.oy = FUJI_TOP - camY;
      drawRival(S, u, cue(1) - 0.5, cue(1) + 1.3);
      S.ctx.drawImage(fuji.fence, 0, -camY);
      drawPitLight(S, t);
      MECH.reflect(S, 150, 256 - MECH.h, P.wet, 0.45);
      MECH.blit(S, 150, 256 - MECH.h);
      S.oy = 0;
      const heavy = clamp01((u - cue(2)) / 0.5);
      rainSurface(S, t, Math.round(lerp(380, 900, heavy)));
      if (u > cue(1) + 0.2) scoreBoxes(S, false, u - (cue(1) + 0.2));
    },

    // 9. "Lap two. Again. He pulls into the pits... and walks away. Hunt wins the title. By one point."
    pits(S, u, { cue, t, dur }) {
      blitBg(S, fuji.world, 0, FUJI_CAM_LOW);
      S.oy = FUJI_TOP - FUJI_CAM_LOW;
      drawRival(S, u, cue(3) - 0.6, cue(3) + 1.0);
      S.ctx.drawImage(fuji.fence, 0, -FUJI_CAM_LOW);
      drawPitLight(S, t);
      MECH.reflect(S, 150, 256 - MECH.h, P.wet, 0.45);
      MECH.blit(S, 150, 256 - MECH.h);
      const inA = cue(1) - 0.6, inB = cue(1) + 1.1;
      const climb = cue(2) - 0.35;
      const heroX = Math.round(lerp(196, HERO_STOP_X, outCubic((u - inA) / (inB - inA))));
      const seated = u < climb;
      const hero = u > inA ? carSprite(P.red, P.redD, P.redH, 1.55, seated ? P.red : null, (196 - heroX)) : null;
      let lauda = null;
      if (u > climb) {
        const walkStart = climb + 0.35;
        const step = u > walkStart ? Math.floor((u - walkStart) / 0.18) % 2 : 0;
        const sprite = WALK[step];
        let x = HERO_STOP_X + 34, feet = 255;
        if (u < walkStart) feet = Math.round(lerp(273, 255, outCubic((u - climb) / 0.35)));
        else { const k = clamp01((u - walkStart) / (dur - walkStart + 3.2)); x = Math.round(lerp(x, 30, k)); feet = Math.round(lerp(255, 270, k)); }
        lauda = { sprite, x, y: feet - sprite.bottom() - (u > walkStart && step ? 1 : 0), feet };
      }
      const carBase = HERO_Y + (hero ? hero.bottom() : 0);
      if (lauda && lauda.feet <= carBase) lauda.sprite.blit(S, lauda.x, lauda.y, { clipBelow: u < climb + 0.35 ? carBase - 4 : Infinity });
      if (hero) { hero.reflect(S, heroX, HERO_Y, P.wet); hero.blit(S, heroX, HERO_Y); }
      if (lauda && lauda.feet > carBase) { lauda.sprite.reflect(S, lauda.x, lauda.y, P.wet, 0.6); lauda.sprite.blit(S, lauda.x, lauda.y); }
      S.oy = 0;
      rainSurface(S, t, 760);
      const flip = cue(3);
      if (flip < 90) scoreBoxes(S, u >= flip, u >= flip ? u - flip : 1); // boxes only when the scores matter
    },

    // 10. "His life, he said, was worth more than a title. The bravest thing isn't getting back in.
    //      It's knowing when to get out." — he walks off into the rain; the helmet on the pit wall.
    end(S, u, { cue, t, dur, pitsDur }) {
      const finalShot = cue(2) - 0.3;
      if (u < finalShot) {
        blitBg(S, fuji.world, 0, FUJI_CAM_LOW);
        S.oy = FUJI_TOP - FUJI_CAM_LOW;
        S.ctx.drawImage(fuji.fence, 0, -FUJI_CAM_LOW);
        drawPitLight(S, t);
        MECH.reflect(S, 150, 256 - MECH.h, P.wet, 0.45);
        MECH.blit(S, 150, 256 - MECH.h);
        const hero = carSprite(P.red, P.redD, P.redH, 1.55, null, 0);
        hero.reflect(S, HERO_STOP_X, HERO_Y, P.wet); hero.blit(S, HERO_STOP_X, HERO_Y);
        // continue the walk from where the pits scene left him, out past the red light
        const walkStart = pitsDur.walkStart, total = pitsDur.walkTotal;
        const k0 = clamp01((pitsDur.dur - walkStart) / total);
        const k = k0 + (u / (finalShot - 0.5)) * (1.65 - k0);
        const x = Math.round(lerp(HERO_STOP_X + 34, 30, k) - Math.max(0, k - 1) * 120);
        const feet = Math.round(lerp(255, 270, Math.min(1, k)));
        const sprite = WALK[Math.floor((u + pitsDur.dur) / 0.18) % 2];
        sprite.reflect(S, x, feet - sprite.bottom(), P.wet, 0.6);
        sprite.blit(S, x, feet - sprite.bottom());
        S.oy = 0;
        rainSurface(S, t, 700);
        S.dithRect(0, 0, LW, LH, P.ink, clamp01((u - (finalShot - 0.6)) / 0.6) * 0.9);
      } else {
        // the helmet left on the wet pit wall, red light behind: the same framing as the hook
        for (let y = 0; y < 148; y++) for (let x = 0; x < LW; x++) S.px(x, y, dith(x, y, y / 200) ? P.sky2 : P.sky1);
        for (let rr = 40; rr > 0; rr -= 1) for (let a = 0; a < 90; a++) {
          const gx = 150 + Math.cos(a / 90 * Math.PI * 2) * rr, gy = 60 + Math.sin(a / 90 * Math.PI * 2) * rr;
          if (dith(Math.round(gx), Math.round(gy), 0.35 * (1 - rr / 40))) S.px(gx, gy, P.lampGlow);
        }
        S.rect(146, 56, 4, 4, P.lamp); S.rect(152, 56, 4, 4, P.lamp);
        S.rect(0, 148, LW, 6, P.wallHi); S.rect(0, 154, LW, 40, P.wall);
        for (let x = 0; x < LW; x += 22) S.rect(x, 154, 1, 40, P.wallLo);
        for (let y = 194; y < LH; y++) for (let x = 0; x < LW; x++) S.px(x, y, dith(x, y, 0.3) ? P.wetHi : P.wet);
        const helmet = helmetSprite(1.4, false);
        helmet.blit(S, HELMET_POS[0], HELMET_POS[1]);
        for (let i = 0; i < 6; i++) { // water beading on the shell
          const bx = HELMET_POS[0] + 12 + Math.floor(hash(i, 4) * 20), by = HELMET_POS[1] + 3 + Math.floor(hash(i, 8) * 8);
          S.px(bx, by, P.rainHi);
        }
        rainSurface(S, t, 620);
        if (u > dur - 1.2) {
          const msg = "FOLLOW FOR MORE F1 STORIES";
          drawText(S, msg, 90 - Math.round(textWidth(msg) / 2), 40, 1, P.paper, P.ink, Math.floor((u - (dur - 1.2)) * 40));
        }
      }
    },
  };
}
