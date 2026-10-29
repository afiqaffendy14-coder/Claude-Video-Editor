// The 36 shots of the v3 short, pixel style. Each shot draws one frame from its local time u
// (seconds since the cut) and the film time t. Many reuse the v2 scenes at a chosen moment;
// the close-ups are drawn here.
import {
  LW, LH, P, dith, hash, clamp01, lerp, outCubic, inOut, mix, Sprite, carSprite, helmetSprite,
  drawFire, drawText, textWidth, box, runnerSprite,
} from "./engine.js";
import {
  makeScenes, rainSurface, buildFuji, FUJI_TOP, FUJI_CAM_LOW, drawPitLight, drawRival, drawSpray,
  scoreBoxes, MECH, HERO_STOP_X, HERO_Y, buildHospital, drawWindowGlass, drawECG, HELMET_POS,
} from "./scenes.js";

const cueOf = (arr) => (n) => (arr[n] ?? 999);

// ------------------------------------------------------------------ close-up helpers

function stormBackdrop(S, t, glow = true) {
  for (let y = 0; y < LH; y++) for (let x = 0; x < LW; x++) S.px(x, y, dith(x, y, y / 340) ? P.sky2 : dith(x, y, 0.5) ? P.sky1 : P.sky0);
  if (glow) for (let r = 34; r > 0; r--) for (let a = 0; a < 80; a++) { // out-of-focus red pit light
    const gx = 34 + Math.cos(a / 80 * Math.PI * 2) * r, gy = 70 + Math.sin(a / 80 * Math.PI * 2) * r;
    if (dith(Math.round(gx), Math.round(gy), 0.32 * (1 - r / 34))) S.px(gx, gy, P.lampGlow);
  }
  for (let i = 0; i < 9; i++) { // bokeh of distant lamps
    const bx = 20 + hash(i, 2) * 150, by = 30 + hash(i, 5) * 120, r = 3 + hash(i, 7) * 4;
    for (let y = -r; y <= r; y++) for (let x = -r; x <= r; x++) if (x * x + y * y <= r * r && dith(bx + x, by + y, 0.35)) S.px(bx + x, by + y, "#56606e");
  }
}

// A big head in a balaclava, eyes in the slit (burn scars around them after 1 August).
function bigFace(S, cx, cy, t, { lookX = 0, down = 0, scars = true } = {}) {
  const sp = new Sprite(110, 150);
  sp.rect(10, 112, 90, 38, P.red); sp.rect(10, 112, 90, 3, P.redH); // suit shoulders
  sp.rect(38, 104, 34, 12, P.white); // collar
  sp.rect(42, 92, 26, 16, P.knit); // neck
  sp.ellipse(55, 60, 33, 42, P.knit);
  for (let y = 22; y < 100; y++) for (let x = 24; x < 88; x++) if (sp.get(x, y) === P.knit && (x + y * 3) % 7 === 0) sp.set(x, y, P.knitD); // knit texture
  const ey = 52 + down;
  sp.rect(30, ey - 7, 50, 14, P.skin); // eye slit
  if (scars) for (let y = ey - 7; y < ey + 7; y++) for (let x = 30; x < 80; x++) {
    const h = hash(Math.floor(x / 2), Math.floor(y / 2));
    if (h < 0.22) sp.set(x, y, "#9e3326"); else if (h < 0.32) sp.set(x, y, "#d88a78");
  }
  for (const ex of [42, 67]) {
    sp.ellipse(ex, ey, 6, 3, "#efe9e1");
    sp.rect(ex - 2 + lookX, ey - 2, 4, 4, "#3a2a20"); sp.rect(ex - 1 + lookX, ey - 1, 2, 2, P.ink);
    sp.set(ex + 1 + lookX, ey - 2, "#ffffff");
    sp.rect(ex - 7, ey - 5, 14, 1, "#7a4a38"); // lid line
  }
  sp.outline(P.out).blit(S, cx - 55, cy - 60);
}

// Front-on helmet, big, with visor and stripe; flames reflect in the visor when fire > 0.
function bigHelmetFront(S, cx, cy, t, { fire = 0, drops = 0 } = {}) {
  const sp = new Sprite(120, 110);
  sp.ellipse(60, 52, 54, 50, P.red);
  sp.ellipse(44, 30, 26, 16, P.redH);
  sp.rect(56, 2, 8, 46, P.white);
  sp.rect(10, 44, 100, 30, P.visor);
  sp.rect(16, 48, 30, 3, P.glint); sp.rect(16, 53, 14, 2, mix(P.glint, P.visor, 0.5));
  sp.rect(14, 88, 92, 8, P.redD); sp.rect(20, 76, 80, 12, P.red);
  sp.outline(P.out).blit(S, cx - 60, cy - 52);
  if (fire > 0) for (let x = 0; x < 96; x++) { // reflected flames dancing in the visor
    const h = (0.5 + 0.5 * hash(x, Math.floor(t * 15))) * 22 * fire;
    for (let y = 0; y < h; y++) if (dith(x, y, 0.75 - y / 40)) S.px(cx - 48 + x, cy + 20 - y, y < h * 0.4 ? P.flame1 : y < h * 0.8 ? P.flame2 : P.flame3);
  }
  for (let i = 0; i < drops; i++) { // water beading on the shell and visor
    const dx = cx - 50 + Math.floor(hash(i, 3) * 100), dy = cy - 46 + Math.floor(hash(i, 9) * 90);
    S.px(dx, dy, P.rainHi); S.px(dx, dy + 1, "#6f7c8a");
  }
}

// ------------------------------------------------------------------ the shots

export function makeShots() {
  const sc = makeScenes();
  const fuji = buildFuji();
  const hospital = buildHospital();

  const fujiLow = (S) => { S.ctx.drawImage(fuji.world, 0, -FUJI_CAM_LOW); S.oy = FUJI_TOP - FUJI_CAM_LOW; };
  const pitsAt = (S, u, t, cues, dur = 8) => sc.pits(S, u, { cue: cueOf(cues), t, dur });

  return {
    walkaway: (S, u, t) => pitsAt(S, u, t, [0, -5, -2, 99], 1),
    helmetHand(S, u, t) {
      stormBackdrop(S, t);
      const swing = Math.round(Math.sin(t * 5.5) * 5);
      const glove = new Sprite(40, 40);
      glove.thick(20, 0, 20 + swing / 2, 24, 7, P.red); // forearm in the suit
      glove.rect(10, 22, 22, 14, P.coat); glove.rect(10, 22, 22, 2, P.coatHi);
      for (let i = 0; i < 4; i++) glove.rect(10 + i * 5, 34, 4, 6, P.coat);
      glove.outline(P.out).blit(S, 70 + swing, 18);
      bigHelmetFront(S, 90 + swing, 104, t, { drops: 26 });
      rainSurface(S, t, 700);
    },
    faceLook(S, u, t) {
      stormBackdrop(S, t);
      bigFace(S, 90, 112, t, { lookX: Math.round(lerp(-3, 3, outCubic(u / 0.5))) });
      rainSurface(S, t, 650);
    },
    fujiWide: (S, u, t) => sc.fuji(S, lerp(0.15, 1.55, u / 2.6), { cue: cueOf([0, 99, 99]), t }),
    finalRace(S, u, t) {
      S.ctx.drawImage(fuji.world, 0, -110); S.oy = FUJI_TOP - 110;
      drawRival(S, u, 0, 1.3);
      drawRival(S, u, 0.45, 1.7);
      S.ctx.drawImage(fuji.fence, 0, -110);
      drawPitLight(S, t);
      S.oy = 0; rainSurface(S, t, 620);
    },
    scores: (S, u, t) => sc.fuji(S, 3.0 + u, { cue: cueOf([0, 3.15, 99]), t }),
    pitIn: (S, u, t) => pitsAt(S, u, t, [0, 0.55, 99, 99], 8),
    climbOut(S, u, t) {
      stormBackdrop(S, t, false);
      const car = new Sprite(LW, 120); // a big slice of the cockpit side
      car.poly([[0, 60], [40, 44], [150, 40], [180, 46], [180, 100], [0, 100]], P.red);
      car.rect(0, 92, 180, 8, P.redD); car.rect(30, 46, 140, 2, P.redH);
      car.rect(60, 36, 64, 8, P.out); // cockpit opening
      car.rect(126, 18, 4, 26, P.metal); car.rect(118, 18, 12, 3, P.metal); // roll hoop
      car.circle(150, 74, 9, P.white); car.rect(149, 69, 2, 10, P.out); // roundel "1"
      car.rect(40, 62, 30, 10, P.out); for (let i = 0; i < 4; i++) car.rect(42, 63 + i * 2, 26, 1, P.metal);
      const rise = Math.round(lerp(34, 0, outCubic(u / 1.1)));
      const d = new Sprite(70, 80); // Lauda hauling himself up, helmet still on
      d.rect(18, 34, 34, 40, P.red); d.rect(18, 34, 34, 3, P.redH); d.rect(20, 60, 30, 3, P.out);
      d.thick(18, 40, 4, 64, 5, P.red); d.thick(52, 40, 66, 62, 5, P.red); // arms pushing down
      d.rect(0, 62, 9, 8, P.coat); d.rect(60, 60, 9, 8, P.coat);
      d.ellipse(35, 18, 16, 16, P.red); d.rect(20, 14, 30, 8, P.visor); d.rect(33, 2, 4, 12, P.white);
      d.outline(P.out).blit(S, 58, 64 + rise, { clipBelow: 116 });
      car.outline(P.out).blit(S, 0, 76);
      rainSurface(S, t, 700);
    },
    stands: (S, u, t) => pitsAt(S, u, t, [0, -5, -0.9, 99], 300),
    rewind(S, u, t) {
      // the previous shot running backwards, with tape tracking noise and a counter spinning down
      pitsAt(S, Math.max(0, 1.4 - u * 2.2), t, [0, -5, -0.9, 99], 300);
      const fr = Math.floor(t * 30);
      for (let k = 0; k < 6; k++) {
        const y = Math.floor(hash(k, fr) * LH), h = 1 + Math.floor(hash(k + 9, fr) * 3), shift = Math.floor((hash(k + 5, fr) - 0.5) * 12);
        const row = S.ctx.getImageData(0, y, LW, h); S.ctx.putImageData(row, shift, y);
        for (let x = 0; x < LW; x++) if (hash(x, y + fr) < 0.3) S.px(x, y, "#cfd6de");
      }
      S.dithRect(0, 0, LW, LH, "#1a2a5a", 0.25);
      const days = Math.max(0, Math.round(84 * (1 - inOut(u / 1.5))));
      drawText(S, "<<", 16, 36, 2, P.paper, P.ink);
      box(S, 58, 34, 104, 22);
      const label = `${days} DAYS`;
      drawText(S, label, 110 - Math.round(textWidth(label, 2) / 2), 38, 2, P.ink, null);
    },
    ringAerial: (S, u, t) => sc.ring(S, u + 1.2, { t, dur: 7 }),
    greenHell(S, u, t) {
      for (let y = 0; y < LH; y++) for (let x = 0; x < LW; x++) S.px(x, y, dith(x, y, y / 120) ? P.fogHi : P.fog);
      const layer = (speed, top, col, colHi, spacing, w, seed) => { // parallax conifers rushing past
        const off = (t * speed) % spacing;
        for (let i = -1; i < LW / spacing + 2; i++) {
          const x0 = Math.round(i * spacing - off + hash(i + Math.floor(t * speed / spacing), seed) * 6);
          const h = 50 + hash(i + Math.floor(t * speed / spacing), seed + 1) * 40;
          for (let y = top - h; y < 168; y++) {
            const half = Math.min(w, Math.floor((y - (top - h)) / 2));
            for (let dx = -half; dx <= half; dx++) S.px(x0 + dx, y, dx < -half + 2 ? colHi : col);
          }
        }
      };
      layer(60, 120, P.hill1, P.hill2, 26, 12, 3);
      layer(160, 140, P.forest, P.forestHi, 34, 14, 5);
      for (let y = 160; y < 200; y++) for (let x = 0; x < LW; x++) S.px(x, y, dith(x, y, 0.2) ? P.asphaltHi : P.asphalt);
      for (let x = 0; x < LW; x++) if ((x + Math.floor(t * 400)) % 12 < 6) S.px(x, 176, P.line);
      carSprite(P.red, P.redD, P.redH, 1.4, P.red, t * 900).blit(S, 60 + Math.round(Math.sin(t * 9)), 158);
      for (let i = 0; i < 14; i++) { const y = 150 + Math.floor(hash(i, Math.floor(t * 20)) * 40); S.rect(140 + hash(i, 4) * 30, y, 12 + hash(i, 6) * 20, 1, "#8a949c"); } // speed lines
      for (let y = 200; y < LH; y++) for (let x = 0; x < LW; x++) S.px(x, y, dith(x + Math.floor(t * 300), y, 0.3) ? P.grassD : "#2c4a24"); // verge rushing past
      layer(420, 210, "#0f1a14", "#1a2a20", 70, 18, 8); // foreground trunks whipping by
    },
    lapTwo: (S, u, t) => sc.crash(S, u + 1.3, { cue: cueOf([0, 2.0, 99]), t }),
    snaps: (S, u, t) => sc.crash(S, 2.0 + u, { cue: cueOf([0, 2.0, 99]), t }),
    flames: (S, u, t) => sc.crash(S, 3.9 + u, { cue: cueOf([0, 2.0, 99]), t }),
    trapped(S, u, t) {
      for (let y = 0; y < LH; y++) for (let x = 0; x < LW; x++) S.px(x, y, dith(x, y, 0.5) ? "#2a1a14" : "#1a110d");
      const car = new Sprite(LW, 110);
      car.poly([[0, 50], [50, 36], [160, 32], [180, 38], [180, 96], [0, 96]], "#7a1418");
      car.rect(54, 28, 70, 10, P.out); car.rect(130, 8, 4, 26, P.metal);
      for (let i = 0; i < 400; i++) car.set(hash(i, 1) * 180, 36 + hash(i, 2) * 60, i % 3 ? "#2a0d0b" : "#4a1a14"); // scorching
      car.outline(P.out).blit(S, 0, 96);
      helmetSprite(1.6, true).blit(S, 66, 92);
      drawFire(S, 40, 150, 34, 70, t, 1);
      drawFire(S, 140, 154, 30, 60, t + 0.4, 1);
      drawFire(S, 92, 150, 22, 44, t + 0.8, 0.9);
    },
    dragOut: (S, u, t) => sc.crash(S, 6.0 + u, { cue: cueOf([0, 2.0, 6.35]), t }),
    burned: (S, u, t) => sc.hook(S, 2.9 + u * 0.3, { t }),
    lungs(S, u, t) {
      for (let y = 0; y < LH; y++) for (let x = 0; x < LW; x++) S.px(x, y, dith(x, y, 0.5) ? P.room1 : P.room0);
      S.rect(24, 24, 132, 164, "#c9d6e2"); S.rect(28, 28, 124, 156, "#0d1418"); // lightbox with an X-ray
      const glow = 0.5 + 0.5 * Math.sin(t * 3);
      for (let i = 0; i < 9; i++) { // ribs
        for (const side of [-1, 1]) for (let k = 0; k < 40; k++) {
          const x = 90 + side * (6 + k), y = 60 + i * 13 + Math.round((k / 40) ** 2 * 10);
          S.px(x, y, "#c8d2da"); S.px(x, y + 1, "#7f8c96");
        }
      }
      S.rect(88, 50, 4, 120, "#aab6c0"); // spine
      for (const side of [-1, 1]) for (let y = 56; y < 168; y++) for (let x = 0; x < 50; x++) { // the lungs, clouded with smoke damage
        const lx = 90 + side * (12 + x), d = ((x - 22) / 24) ** 2 + ((y - 112) / 56) ** 2;
        if (d > 1) continue;
        const cloud = 0.5 + 0.5 * Math.sin(x * 0.4 + y * 0.23) * Math.cos(y * 0.17 - x * 0.2);
        if (dith(lx, y, 0.25 + cloud * 0.45)) S.px(lx, y, cloud > 0.6 ? "#9aa6b0" : "#5a6672");
      }
      for (let x = 30; x < 150; x++) if (dith(x, 180, glow)) S.px(x, 180, "#eaf2f8");
    },
    doctors(S, u, t) {
      sc.hook(S, 3.0, { t });
      const doc = (x, flip) => {
        const d = new Sprite(30, 70);
        d.circle(15, 9, 7, P.skin); d.rect(8, 2, 14, 5, "#8fb3a8"); d.rect(9, 11, 12, 4, "#8fb3a8"); // cap and mask
        d.rect(5, 18, 20, 36, "#e8eef2"); d.rect(5, 18, 2, 36, "#ffffff"); d.rect(14, 20, 2, 30, "#c9d2d8");
        d.rect(8, 54, 6, 14, "#3a4a52"); d.rect(16, 54, 6, 14, "#3a4a52");
        d.thick(6, 22, 1, 42, 3, "#e8eef2"); d.thick(24, 22, 28, 40, 3, "#e8eef2");
        d.outline(P.out).blit(S, x, 84, { flipX: flip });
      };
      doc(112, false); doc(140, true);
      if (Math.floor(t * 4) % 2) S.dithRect(0, 0, LW, 190, "#ff2a1a", 0.12); // alarm flashing in the room
      S.rect(150, 26, 6, 4, Math.floor(t * 4) % 2 ? P.lamp : P.lampGlow);
    },
    fortyTwo: (S, u, t) => sc.comeback(S, u, { cue: cueOf([0, 1.75]), t }),
    racingAgain: (S, u, t) => sc.comeback(S, 1.0 + u, { cue: cueOf([0, 0]), t }),
    helmetOn: (S, u, t) => sc.monza(S, u * 0.95, { cue: cueOf([0, 2.6]), t }),
    fourth: (S, u, t) => sc.monza(S, u, { cue: cueOf([0, 0.15]), t }),
    forward(S, u, t) {
      sc.fuji(S, 0.5 + u * 2.5, { cue: cueOf([0, 99, 99]), t });
      const fr = Math.floor(t * 30);
      for (let k = 0; k < 40; k++) { const y = Math.floor(hash(k, fr) * LH); S.rect(0, y, LW, 1, k % 3 ? "#9aa6b3" : "#dfe6ee"); } // streaking ahead
      S.dithRect(0, 0, LW, LH, "#1a2a5a", 0.2);
      drawText(S, ">>", 140, 36, 2, P.paper, P.ink);
    },
    rainHeavy(S, u, t) {
      for (let y = 0; y < LH; y++) for (let x = 0; x < LW; x++) S.px(x, y, dith(x, y, 0.35 + Math.sin(x * 0.07 + y * 0.03) * 0.1) ? P.wetHi : P.wet);
      for (let r = 30; r > 0; r--) for (let a = 0; a < 70; a++) { // red light reflected in the puddle
        const gx = 120 + Math.cos(a / 70 * Math.PI * 2) * r * 1.6, gy = 80 + Math.sin(a / 70 * Math.PI * 2) * r * 0.5;
        if (dith(Math.round(gx), Math.round(gy), 0.3 * (1 - r / 30))) S.px(gx, gy, P.lampGlow);
      }
      const fr = Math.floor(t * 30);
      for (let i = 0; i < 90; i++) { // splash crowns and rings, big because we're close
        const x = Math.floor(hash(i, fr >> 1) * LW), y = 20 + Math.floor(hash(i + 50, fr >> 1) * 170), age = (t * 4 + hash(i, 1)) % 1, r = Math.round(age * 6);
        for (let a = 0; a < 16; a++) if (dith(x, y, 1 - age)) S.px(x + Math.cos(a / 16 * 6.28) * r * 1.6, y + Math.sin(a / 16 * 6.28) * r * 0.5, P.rainHi);
        if (age < 0.3) { S.px(x, y - 2, P.rainHi); S.px(x - 1, y - 3, P.rain); S.px(x + 1, y - 3, P.rain); }
      }
      rainSurface(S, t, 900);
    },
    povSpray(S, u, t) {
      for (let y = 0; y < LH; y++) for (let x = 0; x < LW; x++) S.px(x, y, dith(x + Math.floor(t * 20), y + Math.floor(t * 40), 0.55 + 0.25 * Math.sin(y * 0.05)) ? "#8a949e" : "#6a747e");
      const tail = 0.5 + 0.5 * Math.sin(t * 8);
      for (const tx of [84, 96]) { S.rect(tx, 88, 3, 2, P.lamp); for (let r = 1; r < 8; r++) for (let a = 0; a < 20; a++) if (dith(tx + Math.cos(a) * r, 89 + Math.sin(a) * r, 0.3 * tail * (1 - r / 8))) S.px(tx + Math.cos(a) * r, 89 + Math.sin(a) * r, P.lampGlow); }
      const nose = new Sprite(LW, 140); // his own car's nose and front wheels, from the cockpit
      nose.poly([[70, 140], [82, 40], [98, 40], [110, 140]], P.red);
      nose.rect(86, 40, 8, 100, P.redH);
      nose.poly([[20, 60], [160, 60], [170, 70], [10, 70]], P.redD); // front wing
      nose.circle(26, 100, 26, P.tyre); nose.circle(154, 100, 26, P.tyre);
      nose.circle(26, 100, 9, P.grey); nose.circle(154, 100, 9, P.grey);
      nose.rect(0, 128, LW, 12, P.out); // cockpit rim
      nose.outline(P.out).blit(S, 0, 100);
      rainSurface(S, t, 900);
      for (let i = 0; i < 18; i++) { const x = hash(i, 3) * LW, y = 20 + hash(i, 6) * 160; S.px(x, y, P.rainHi); S.px(x, y + 1, "#c9d2da"); } // drops on the visor
    },
    fireOnce(S, u, t) {
      stormBackdrop(S, t);
      bigHelmetFront(S, 90, 110, t, { fire: 0.6 + 0.4 * Math.sin(t * 7), drops: 34 });
      rainSurface(S, t, 700);
    },
    parks: (S, u, t) => pitsAt(S, u, t, [0, -1.0, 0.6, 99], 6),
    huntTitle(S, u, t) {
      fujiLow(S);
      for (let y = 178; y < 206; y++) for (let x = 60; x < 66; x++) S.px(x, y, ((x >> 1) + (y >> 1)) % 2 ? P.paper : P.ink); // chequered line
      drawSpray(S, Math.round(lerp(150, -40, u / 1.5)) + 30, 201, t);
      carSprite(P.white, P.whiteD, "#ffffff", 0.8, P.whiteD, u * 600).blit(S, Math.round(lerp(150, -40, u / 1.5)), 186);
      S.ctx.drawImage(fuji.fence, 0, -FUJI_CAM_LOW);
      const wave = Math.round(Math.sin(t * 12) * 3); // marshal waving the chequered flag on the wall
      S.rect(40, 186, 4, 20, P.coat); S.rect(41, 180, 3, 6, P.skin);
      S.rect(44, 172 + wave, 1, 14, P.grey);
      for (let y = 0; y < 8; y++) for (let x = 0; x < 12; x++) S.px(45 + x, 172 + wave + y, ((x >> 1) + (y >> 1)) % 2 ? P.paper : P.ink);
      drawPitLight(S, t);
      S.oy = 0; rainSurface(S, t, 700);
    },
    onePoint: (S, u, t) => pitsAt(S, u, t, [0, -5, -3, 0], 3),
    worthMore(S, u, t) {
      stormBackdrop(S, t);
      bigFace(S, 90, 108, t, { lookX: -2, down: 2 });
      rainSurface(S, t, 760);
    },
    bravest: (S, u, t) => sc.end(S, 1.0 + u, { cue: cueOf([0, 0, 0.3]), t, dur: 99, pitsDur: { dur: 8, walkStart: 2, walkTotal: 9 } }),
    comingBack: (S, u, t) => sc.monza(S, 1.05 + u * 0.9, { cue: cueOf([0, 2.6]), t }),
    stop(S, u, t) {
      stormBackdrop(S, t, false);
      for (let r = 70; r > 0; r--) for (let a = 0; a < 140; a++) {
        const gx = 90 + Math.cos(a / 140 * Math.PI * 2) * r, gy = 96 + Math.sin(a / 140 * Math.PI * 2) * r * 1.1;
        if (dith(Math.round(gx), Math.round(gy), 0.45 * (1 - r / 70))) S.px(gx, gy, P.lampGlow);
      }
      S.rect(86, 150, 8, 60, P.post);
      const lamp = new Sprite(84, 96);
      lamp.rect(0, 0, 84, 96, "#16181c"); lamp.rect(0, 0, 84, 3, "#2a2e34");
      for (const [lx, ly] of [[20, 26], [62, 26], [20, 68], [62, 68]]) {
        lamp.circle(lx, ly, 14, "#2a0606"); lamp.circle(lx, ly, 11, P.lamp); lamp.circle(lx - 3, ly - 3, 4, "#ffb2a8");
        lamp.rect(lx - 16, ly - 18, 32, 3, "#0d0e10"); // hood
      }
      lamp.outline(P.out).blit(S, 48, 52);
      rainSurface(S, t, 760);
    },
    thatsWhy: (S, u, t) => pitsAt(S, u - 0.98, t, [0, -5, -2, 99], 1),
  };
}
