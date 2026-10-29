// Three.js film for the v3 short: 36 hard-cut shots across four sets, each a pure function of
// time. The WebGL frame is composited onto a 2D canvas with the overlays and captions on top.
import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { GTAOPass } from "three/addons/postprocessing/GTAOPass.js";
import { BokehPass } from "three/addons/postprocessing/BokehPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { spinWheels, buildHelmet, buildCar, ACCENT } from "./models.js";
import { buildPerson, buildDriver } from "./humans.js";
import { buildRain, buildFujiSet, buildRingSet, buildHospitalSet, buildMonzaSet, RING_X, HOSP_X, MONZA_X } from "./sets.js";
import { SHOTS, DURATION } from "./timeline.js";
import { drawCaption, loadCaptionFont } from "./captions.js";

export { DURATION };
const W = 1080, H = 1920;
const V = (x, y, z) => new THREE.Vector3(x, y, z);
const clamp01 = (v) => Math.min(1, Math.max(0, v));
const lerp = (a, b, k) => a + (b - a) * k;
const outCubic = (x) => 1 - Math.pow(1 - clamp01(x), 3);
const inOut = (x) => { x = clamp01(x); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const hash = (a, b) => { let h = (a * 374761393 + b * 668265263) | 0; h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967296; };
const vlerp = (a, b, k) => new THREE.Vector3().lerpVectors(a, b, k);

function gradientTexture(stops) {
  const c = document.createElement("canvas"); c.width = 4; c.height = 512;
  const g = c.getContext("2d"), gr = g.createLinearGradient(0, 0, 0, 512);
  stops.forEach(([o, col]) => gr.addColorStop(o, col)); g.fillStyle = gr; g.fillRect(0, 0, 4, 512);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

export async function createFilm(out) {
  await loadCaptionFont();
  out.width = W; out.height = H;
  const octx = out.getContext("2d");

  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1); renderer.setSize(W, H, false);
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  const camera = new THREE.PerspectiveCamera(40, W / H, 0.03, 2500);
  camera.userData.look = V(0, 0, -1);

  const hemi = new THREE.HemisphereLight(0xb3bcc6, 0x2e3033, 1.2); scene.add(hemi);
  const key = new THREE.DirectionalLight(0xdde4ec, 1.7);
  key.castShadow = true; key.shadow.mapSize.set(2048, 2048); key.shadow.radius = 5; key.shadow.bias = -0.0003; key.shadow.normalBias = 0.02;
  scene.add(key, key.target);
  const flicker = new THREE.PointLight(0xff7a2a, 0, 4, 1.5); scene.add(flicker);

  const fuji = buildFujiSet(W, H), ring = buildRingSet(), hosp = buildHospitalSet(), monza = buildMonzaSet();
  [fuji, ring, hosp, monza].forEach((s) => scene.add(s.group));
  const rain = buildRain(); scene.add(rain);
  // close-up actors: a driver bust for faces and the visor, a climber rising from the cockpit
  const closeDriver = buildDriver(); closeDriver.position.set(-2.4, 0.55, 9); closeDriver.rotation.y = Math.PI; fuji.group.add(closeDriver);
  const climber = buildPerson(ACCENT, { balaclava: true, gloves: true, arms: { "1": { reach: 0.5, bend: 1.2, spread: 0.45 }, "-1": { reach: 0.5, bend: 1.2, spread: 0.45 } } });
  const climbHelmet = buildHelmet(0.155); climbHelmet.position.set(0, 1.715, 0.012); climber.add(climbHelmet); fuji.group.add(climber);
  const povCar = buildCar(ACCENT, "1"); fuji.group.add(povCar);

  const sets = { fuji: fuji.group, ring: ring.group, hosp: hosp.group, monza: monza.group };
  const looks = {
    fuji: () => { scene.background = gradientTexture([[0, "#4f555c"], [0.55, "#747b83"], [1, "#858c94"]]); scene.fog = new THREE.FogExp2("#7c838b", 0.026); hemi.intensity = 1.25; key.intensity = 1.7; key.color.set("#dde4ec"); scene.environmentIntensity = 0.45; renderer.toneMappingExposure = 1.0; },
    ring: () => { scene.background = gradientTexture([[0, "#5f6c72"], [1, "#8d9a9c"]]); scene.fog = new THREE.FogExp2("#7d8a8b", 0.0035); hemi.intensity = 1.4; key.intensity = 2.0; key.color.set("#f2f0e6"); scene.environmentIntensity = 0.5; renderer.toneMappingExposure = 1.05; },
    hosp: () => { scene.background = new THREE.Color("#0b1014"); scene.fog = null; hemi.intensity = 0.35; key.intensity = 0.25; key.color.set("#9fb4c8"); scene.environmentIntensity = 0.25; renderer.toneMappingExposure = 1.1; },
    monza: () => { scene.background = gradientTexture([[0, "#3d7cc9"], [0.6, "#7fb0e4"], [1, "#cfe3f5"]]); scene.fog = new THREE.Fog("#cfe3f5", 60, 220); hemi.intensity = 1.6; key.intensity = 3.0; key.color.set("#fff4e2"); scene.environmentIntensity = 0.6; renderer.toneMappingExposure = 1.0; },
  };

  const composer = new EffectComposer(renderer);
  composer.setPixelRatio(1); composer.setSize(W, H);
  composer.addPass(new RenderPass(scene, camera));
  const random = Math.random; let seed = 7;
  Math.random = () => ((seed = (seed * 16807) % 2147483647) / 2147483647); // seeded GTAO noise
  const gtao = new GTAOPass(scene, camera, W, H);
  Math.random = random;
  gtao.updateGtaoMaterial({ radius: 0.5, distanceExponent: 1.5, thickness: 1.2, scale: 1.0 });
  composer.addPass(gtao);
  const bokeh = new BokehPass(scene, camera, { focus: 5, aperture: 0.002, maxblur: 0.008 });
  composer.addPass(bokeh);
  composer.addPass(new OutputPass());

  // ---------------------------------------------------------------- animation helpers
  const PARK = V(-1.55, 0, -1.4);
  const lauda = fuji.lauda;
  const walkAt = (k) => { // Lauda's walk away from the car toward the pit exit, k in 0..1 over the film's walk shots
    lauda.position.copy(vlerp(V(-0.4, 0, 0.2), V(0.9, 0, -9), k));
    lauda.position.y = Math.abs(Math.sin(k * 60)) * 0.03;
    lauda.rotation.set(0, Math.PI + 0.12, Math.sin(k * 60) * 0.03);
  };
  const parkHero = () => { fuji.hero.position.copy(PARK); fuji.hero.rotation.set(0, -0.18, 0); spinWheels(fuji.hero, 0); fuji.hero.visible = true; };
  const rivalAt = (z, x = 8) => { fuji.rival.visible = true; fuji.rival.position.set(x, 0, z); fuji.rival.rotation.set(0, 0, 0); spinWheels(fuji.rival, -z * 1.3); };
  const ringOnPath = (car, k) => {
    const p = ring.path.getPointAt(clamp01(k)), q = ring.path.getPointAt(clamp01(k + 0.002));
    car.position.set(p.x, ring.terrainH(p.x, p.z) * 0.15 + 0.05, p.z);
    car.rotation.set(0, Math.atan2(-(q.x - p.x), -(q.z - p.z)), 0);
    spinWheels(car, k * 4000);
  };
  // the crash on the straight (ring-local z 160–260): approach, snap into the armco, fire
  const IMPACT = 3.0; // seconds into the crash sequence
  const crashState = (c) => {
    const car = ring.crashCar; car.visible = true;
    if (c < IMPACT - 0.45) { car.position.set(1.5, 0, 260 - c * 18); car.rotation.set(0, 0, 0); }
    else if (c < IMPACT) { const k = (c - (IMPACT - 0.45)) / 0.45; car.position.set(lerp(1.5, -3.6, k * k), 0, 260 - c * 18); car.rotation.set(0, lerp(0, 0.9, k), 0); }
    else { const k = outCubic((c - IMPACT) / 0.5); car.position.set(-3.6, 0, 260 - IMPACT * 18 - k * 3); car.rotation.set(0, lerp(0.9, 1.25, k), lerp(0, 0.04, k)); }
    spinWheels(car, Math.min(c, IMPACT) * 18);
    ring.fire.position.set(car.position.x, 0, car.position.z);
    ring.fire.userData.update(c, c < IMPACT ? 0 : clamp01((c - IMPACT) / 0.35), camera);
    return car;
  };
  const drawECG = (c, t, bpm, irregular = 0) => {
    const g = hosp.ecgCanvas.getContext("2d"), w = 512, h = 256;
    g.fillStyle = "#03100a"; g.fillRect(0, 0, w, h);
    g.strokeStyle = "rgba(60,255,140,0.12)"; g.lineWidth = 1;
    for (let x = 0; x < w; x += 32) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, h); g.stroke(); }
    g.strokeStyle = "#5bff8a"; g.lineWidth = 4; g.beginPath();
    const period = 60 / bpm;
    for (let x = 0; x < w; x++) {
      const tt = (x + t * 160) / 160, ph = ((tt % period) + period) % period / period;
      const j = irregular ? (hash(Math.floor(tt / period), 3) - 0.5) * irregular : 0;
      let v = 0;
      if (ph > 0.18 && ph < 0.2) v = 0.2; else if (ph >= 0.2 && ph < 0.235) v = -1 - j; else if (ph >= 0.235 && ph < 0.26) v = 0.45; else if (ph > 0.45 && ph < 0.55) v = -0.18 * Math.sin((ph - 0.45) / 0.1 * Math.PI);
      const y = h / 2 + v * (h / 2 - 20);
      x ? g.lineTo(x, y) : g.moveTo(x, y);
    }
    g.stroke();
    g.fillStyle = "#5bff8a"; g.font = "700 40px Inter, sans-serif"; g.fillText(String(Math.round(bpm)), w - 90, 50);
    hosp.ecgTex.needsUpdate = true;
  };

  // ---------------------------------------------------------------- shots
  // each: [set, (u, t, d) => { position actors; return { pos, look, fov, focus?, aperture? } }, overlay?]
  const hold = (pos, look, fov = 40) => ({ pos, look, fov });
  const SH = {
    walkaway: ["fuji", (u, t, d) => { parkHero(); walkAt(0.08 + u * 0.05); return hold(V(2.1, 1.15, 7.2), V(0.3, 1.25, -4), 38); }],
    helmetHand: ["fuji", (u) => { parkHero(); walkAt(0.17 + u * 0.03); const hw = lauda.localToWorld(lauda.userData.held.position.clone()); return { pos: hw.clone().add(V(0.95, 0.3, 1.15)), look: hw.clone().add(V(0, 0.05, 0)), fov: 32, focus: true, aperture: 0.004 }; }],
    faceLook: ["fuji", (u) => { closeDriver.userData.pose(6, 0); const f = closeDriver.localToWorld(V(0, 0.68, 0)); return { pos: f.clone().add(V(0.12 + u * 0.03, 0.02, -0.75)), look: f, fov: 28, focus: true, aperture: 0.006 }; }],
    fujiWide: ["fuji", (u) => { parkHero(); walkAt(0.2); return hold(V(9 - u * 1.5, 7.5 - u, 34), V(-12, 30, -400), 46); }],
    finalRace: ["fuji", (u) => { rivalAt(4 - u * 30); return { pos: V(12.9, 1.0, -4), look: V(6.5, 0.9, -13), fov: 40, focus: false }; }],
    scores: ["fuji", (u) => { parkHero(); walkAt(0.0); rivalAt(-30 + u * 38 - 30); fuji.rival.position.z = 20 - u * 30; return hold(V(-0.8, 1.7, 9), V(4.5, 1.3, -12), 40); }, "scores"],
    pitIn: ["fuji", (u) => { lauda.visible = false; const k = outCubic(u / 1.45); fuji.hero.visible = true; fuji.hero.position.set(lerp(1.4, PARK.x, k), 0, lerp(26, PARK.z, k)); fuji.hero.rotation.set(0, lerp(0.15, -0.18, k), 0); spinWheels(fuji.hero, k * 30); return hold(V(1.6, 0.95, -8), V(-0.6, 0.6, 8), 38); }],
    climbOut: ["fuji", (u) => { parkHero(); lauda.visible = false; climber.visible = true; const cp = fuji.hero.localToWorld(V(0, 0, 0.1)); climber.position.set(cp.x, lerp(-1.05, -0.5, outCubic(u / 1.2)), cp.z); climber.rotation.y = -0.18; return { pos: cp.clone().add(V(1.7, 1.05, 1.4)), look: cp.clone().add(V(0, 0.9, 0)), fov: 34, focus: true, aperture: 0.003 }; }],
    stands: ["fuji", (u) => { parkHero(); walkAt(0.02); lauda.rotation.y = Math.PI * 0.62; return hold(V(3.2, 1.5, 3.2), V(-0.3, 1.2, -0.4), 36); }],
    rewind: ["fuji", (u) => { parkHero(); walkAt(Math.max(0, 0.1 - u * 0.06)); lauda.rotation.y = Math.PI * 0.62; return hold(V(3.2, 1.5, 3.2), V(-0.3, 1.2, -0.4), 36); }, "rewind"],
    ringAerial: ["ring", (u) => { ringOnPath(ring.crashCar, 0.32 + u * 0.035); const c = ring.crashCar.position; return hold(V(RING_X + c.x - 60 + u * 6, 75, c.z + 90), V(RING_X + c.x, 0, c.z - 10), 42); }],
    greenHell: ["ring", (u) => { const car = ring.crashCar; car.visible = true; const z = 262 - u * 22; car.position.set(1.5, 0, z); car.rotation.set(0, 0, 0); spinWheels(car, -z * 1.4); return { pos: V(RING_X + 4.6, 0.65, z + 2.2), look: V(RING_X + 1.2, 0.7, z - 3), fov: 50, focus: false }; }],
    lapTwo: ["ring", (u) => { const car = crashState(0.6 + u); return hold(V(RING_X + 7, 0.75, car.position.z - 4), V(RING_X + car.position.x, 0.6, car.position.z), 34); }],
    snaps: ["ring", (u) => { const car = crashState(2.1 + u); return hold(V(RING_X + 4.5, 1.3, 196), V(RING_X - 1, 0.6, 204), 40); }],
    flames: ["ring", (u, t) => { const car = crashState(IMPACT + 0.3 + u); return hold(V(RING_X + 6.5, 2.4, 194 - u), V(RING_X + car.position.x, 1.0, car.position.z), 38); }],
    trapped: ["ring", (u, t) => { const car = crashState(IMPACT + 1.6 + u); ring.fire.userData.update(IMPACT + 1.6 + u, 0.5, camera); const cp = car.localToWorld(V(0, 0.75, 0.1)); return { pos: cp.clone().add(V(4.2, 1.7, -3.6)), look: cp.clone().add(V(0, 0.2, 0)), fov: 34, focus: true, aperture: 0.002 }; }],
    dragOut: ["ring", (u, t) => {
      const car = crashState(IMPACT + 3.2 + u);
      ring.others[0].visible = true; ring.others[0].position.set(1.5, 0, 214); ring.others[0].rotation.set(0, 0, 0);
      ring.others[1].visible = true; ring.others[1].position.set(-1.0, 0, 222); ring.others[1].rotation.set(0, 0.2, 0);
      ring.runners.forEach((p, i) => { p.visible = true; const k = clamp01(u / 1.6 + i * 0.12); p.position.set(lerp(1 + i, -2.4 + i * 0.6, k), 0, lerp(212 + i * 2, 202 + i * 0.8, k)); p.rotation.y = Math.atan2(-3.4, -10) + Math.PI; p.position.y = Math.abs(Math.sin(t * 9 + i)) * 0.05; });
      return hold(V(RING_X + 6.5, 2.1, 214), V(RING_X - 2.2, 0.8, 202), 40);
    }],
    burned: ["hosp", (u, t) => { drawECG(0, t, 52); const h = V(HOSP_X + 0.6, 0.95, -2.18); return { pos: h.clone().add(V(0.85 - u * 0.05, 0.75, 1.0)), look: h.clone().add(V(0, -0.05, 0.25)), fov: 36, focus: true, aperture: 0.003 }; }],
    lungs: ["hosp", (u, t) => { drawECG(0, t, 108, 0.9); return { pos: V(HOSP_X - 2.25 - u * 0.15, 2.0, -0.45), look: V(HOSP_X - 3.95, 2.0, -0.5), fov: 40, focus: false }; }],
    doctors: ["hosp", (u, t) => { drawECG(0, t, 118, 1.0); hosp.alarm.intensity = Math.floor(t * 4) % 2 ? 20 : 2; hosp.doctors.forEach((d) => (d.visible = true)); return hold(V(HOSP_X + 3.6, 1.9, 1.4), V(HOSP_X + 0.7, 0.95, -1.6), 40); }],
    fortyTwo: ["hosp", (u, t) => { drawECG(0, t, 72); hosp.daylight.material.opacity = (Math.sin(t * 22) * 0.5 + 0.5) * 0.85; return hold(V(HOSP_X - 0.1, 1.35, 0.6), V(HOSP_X - 2.2, 1.6, -2.9), 40); }, "days"],
    racingAgain: ["monza", (u, t) => { monza.hero.position.set(-1.5 + Math.sin(t * 60) * 0.004, 0, 0); monza.hero.rotation.set(0, 0, 0); return { pos: V(MONZA_X + 0.8, 0.7, -5.8), look: V(MONZA_X - 1.5, 0.55, 0.2), fov: 36, focus: true, aperture: 0.002 }; }],
    helmetOn: ["monza", (u) => { monza.driver.userData.pose(lerp(1.0, 0.615, outCubic((u - 0.2) / 1.6)), lerp(0.3, 0, outCubic(u / 1.8))); const f = monza.driver.localToWorld(V(0, 0.7, 0)); return { pos: f.clone().add(V(0.42, 0.06, 1.05)), look: f, fov: 32, focus: true, aperture: 0.004 }; }],
    fourth: ["monza", (u) => { const z = lerp(6, -22, u / 1.2); monza.hero.position.set(-1.5, 0, z); monza.hero.rotation.set(0, 0, 0); spinWheels(monza.hero, -z * 1.3); return hold(V(MONZA_X + 3.0, 1.5, -24), V(MONZA_X - 2.2, 1.0, -12), 44); }, "p4"],
    forward: ["fuji", (u) => { parkHero(); return hold(V(9, 6.5, 30 - u * 6), V(-12, 26, -400), 46); }, "forward"],
    rainHeavy: ["fuji", (u) => { parkHero(); return { pos: V(0.6, 0.22, -12 - u * 0.3), look: V(-0.2, 0.15, -24), fov: 40, focus: true, aperture: 0.004 }; }, "splashes"],
    povSpray: ["fuji", (u, t) => { fuji.hero.visible = false; const z = 10 - u * 22; rivalAt(z - 9, 8); povCar.visible = true; povCar.position.set(8, 0, z); povCar.rotation.set(0, 0, 0); spinWheels(povCar, -z * 1.3); const eye = povCar.localToWorld(V(0, 0.84, -0.12)); return { pos: eye, look: eye.clone().add(V(0, -0.05, -6)), fov: 58, focus: false }; }, "spray"],
    fireOnce: ["fuji", (u, t) => { closeDriver.userData.pose(0.615, 0); flicker.position.copy(closeDriver.localToWorld(V(0.25, 0.75, 0.5))); flicker.intensity = 6 + 4 * Math.sin(t * 19) + 3 * Math.sin(t * 31); const f = closeDriver.localToWorld(V(0, 0.68, 0)); return { pos: f.clone().add(V(-0.08, 0.03, -0.62)), look: f, fov: 30, focus: true, aperture: 0.005 }; }, "fireMemory"],
    parks: ["fuji", (u) => { parkHero(); climber.visible = u < 0.5; climber.position.set(PARK.x, lerp(-0.4, -0.1, u * 2), PARK.z + 0.1); walkAt(clamp01((u - 0.5) * 0.06)); lauda.visible = u >= 0.5; return hold(V(2.3, 2.1, 7.2), V(-1.0, 0.8, -1.2), 40); }],
    huntTitle: ["fuji", (u, t) => { rivalAt(-4 - u * 22); fuji.marshal.visible = true; fuji.marshal.userData.cloth.rotation.y = Math.sin(t * 10) * 0.7; return hold(V(11.4, 1.1, -7.5), V(7.6, 0.8, -18), 40); }],
    onePoint: ["fuji", (u) => { parkHero(); walkAt(0.45 + u * 0.05); return hold(V(2.1, 1.15, 7.2), V(0.3, 1.25, -4), 38); }, "flip"],
    worthMore: ["fuji", (u) => { closeDriver.userData.pose(6, 0); closeDriver.rotation.x = 0.12; const f = closeDriver.localToWorld(V(0, 0.68, 0)); return { pos: f.clone().add(V(-0.2 + u * 0.04, -0.02, -0.82)), look: f, fov: 26, focus: true, aperture: 0.006 }; }],
    bravest: ["fuji", (u) => { parkHero(); return { pos: V(2.25 - u * 0.05, 1.42, -5.15), look: V(2.85, 1.22, -6), fov: 34, focus: true, aperture: 0.005 }; }],
    comingBack: ["monza", (u) => { monza.driver.userData.pose(lerp(0.78, 0.615, outCubic(u / 1.0)), 0); const f = monza.driver.localToWorld(V(0, 0.7, 0)); return { pos: f.clone().add(V(-0.5, 0.02, 0.95)), look: f, fov: 30, focus: true, aperture: 0.004 }; }],
    stop: ["fuji", () => ({ pos: V(-0.4, 3.4, -20.5), look: V(-0.15, 5.0, -26), fov: 34, focus: true, aperture: 0.003 })],
    thatsWhy: ["fuji", (u) => { parkHero(); walkAt(0.08 - (1 - u) * 0.05); return hold(V(2.1, 1.15, 7.2), V(0.3, 1.25, -4), 38); }],
  };

  // ---------------------------------------------------------------- overlays (2D, over the frame)
  const box = (x, y, w, h, text, color) => {
    octx.save(); octx.fillStyle = "rgba(0,0,0,0.35)"; octx.fillRect(x + 8, y + 10, w, h);
    octx.fillStyle = "#f4f4f2"; octx.strokeStyle = "#000"; octx.lineWidth = 6; octx.beginPath(); octx.roundRect(x, y, w, h, 14); octx.fill(); octx.stroke();
    octx.font = "900 54px MontserratCaption"; octx.fillStyle = color; octx.textAlign = "center"; octx.textBaseline = "middle"; octx.fillText(text, x + w / 2, y + h / 2 + 3); octx.restore();
  };
  const overlays = {
    scores: (u) => { if (u > 0.25) { box(110, 230, 400, 96, "LAUDA 68", "#c41e27"); box(570, 230, 400, 96, "HUNT 65", "#111"); } },
    flip: (u) => { const dy = u < 0.12 ? -10 : 0; box(110, 230 + dy, 400, 96, "HUNT 69", "#111"); box(570, 230 + dy, 400, 96, "LAUDA 68", "#c41e27"); },
    days: (u) => { const d = Math.min(42, Math.round(42 * inOut((u - 0.1) / 1.1))); box(300, 420, 480, 130, `DAY ${d}`, d === 42 ? "#c41e27" : "#111"); },
    p4: (u) => { if (u > 0.45) box(700, 230, 280, 150, "P4", "#111"); },
    spray: (u, t) => { // the wall of spray in front: barely anything visible
      octx.save(); for (let i = 0; i < 70; i++) { const x = hash(i, 2) * W, y = 300 + hash(i, 3) * 900, r = 120 + hash(i, 4) * 260; const g = octx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, "rgba(205,210,215,0.32)"); g.addColorStop(1, "rgba(205,210,215,0)"); octx.fillStyle = g; octx.fillRect(x - r, y - r, r * 2, r * 2); } octx.restore();
    },
    rewind: (u, t) => tape(u, t, "◀◀", `${Math.max(0, Math.round(84 * (1 - inOut(u / 1.5))))} DAYS`),
    forward: (u, t) => tape(u, t, "▶▶", "OCT 24"),
    splashes: (u, t) => { // rings and crowns on the puddle, close to the lens
      octx.save(); octx.strokeStyle = "rgba(220,230,238,0.55)"; octx.lineWidth = 3;
      for (let i = 0; i < 40; i++) { const age = (t * 3 + hash(i, 1)) % 1, x = hash(i, Math.floor(t * 3 + hash(i, 1))) * W, y = 1300 + hash(i + 9, Math.floor(t * 3 + hash(i, 1))) * 600; octx.globalAlpha = 1 - age; octx.beginPath(); octx.ellipse(x, y, age * 70, age * 18, 0, 0, Math.PI * 2); octx.stroke(); }
      octx.restore();
    },
    fireMemory: (u, t) => { // a faint double exposure of the flames inside the visor
      octx.save(); octx.globalCompositeOperation = "screen"; octx.globalAlpha = 0.18 + 0.08 * Math.sin(t * 13);
      for (let i = 0; i < 26; i++) { const x = 200 + hash(i, 2) * 680, h = 260 + hash(i, Math.floor(t * 12)) * 380; const g = octx.createLinearGradient(x, 1100, x, 1100 - h); g.addColorStop(0, "rgba(255,120,30,1)"); g.addColorStop(1, "rgba(255,200,80,0)"); octx.fillStyle = g; octx.beginPath(); octx.ellipse(x, 1100 - h / 2, 40 + hash(i, 5) * 40, h / 2, 0, 0, Math.PI * 2); octx.fill(); }
      octx.restore();
    },
  };
  function tape(u, t, icon, label) {
    const fr = Math.floor(t * 30);
    octx.save();
    for (let k = 0; k < 10; k++) { const y = hash(k, fr) * H, h = 4 + hash(k + 9, fr) * 14; const row = octx.getImageData(0, y, W, h); octx.putImageData(row, (hash(k + 5, fr) - 0.5) * 60, y); octx.fillStyle = "rgba(220,230,240,0.35)"; octx.fillRect(0, y, W, 2); }
    octx.fillStyle = "rgba(20,40,110,0.18)"; octx.fillRect(0, 0, W, H);
    octx.font = "900 72px MontserratCaption"; octx.textBaseline = "middle"; octx.lineJoin = "round"; octx.lineWidth = 14; octx.strokeStyle = "#000"; octx.fillStyle = "#fff";
    octx.strokeText(icon, 80, 280); octx.fillText(icon, 80, 280);
    octx.textAlign = "right"; octx.strokeText(label, 1000, 280); octx.fillText(label, 1000, 280);
    octx.restore();
  }

  // ---------------------------------------------------------------- render
  return function renderAt(t) {
    t = Math.max(0, Math.min(DURATION - 1e-3, t));
    const shot = SHOTS.find((s) => t >= s.start && t < s.end) || SHOTS[SHOTS.length - 1];
    const u = t - shot.start, d = shot.end - shot.start;
    const [setName, fn, overlay] = SH[shot.id];
    Object.entries(sets).forEach(([k, g]) => (g.visible = k === setName));
    looks[setName]();
    // reset actors that some shots hide or move
    [lauda, fuji.rival, climber, povCar, fuji.marshal, fuji.hero, ring.crashCar, ...ring.others, ...ring.runners, ...hosp.doctors].forEach((o) => (o.visible = false));
    lauda.visible = true; ring.fire.userData.update(t, 0); hosp.alarm.intensity = 0; flicker.intensity = 0; closeDriver.rotation.x = 0;
    hosp.daylight.material.opacity = 0;
    const cam = fn(u, t, d);
    camera.position.copy(cam.pos); camera.fov = cam.fov || 40; camera.lookAt(cam.look); camera.userData.look = cam.look; camera.updateProjectionMatrix();
    ring.fire.children.forEach((m) => { if (m.material && m.material.blending === THREE.AdditiveBlending) m.quaternion.copy(camera.quaternion); }); // flames face the lens
    rain.visible = setName === "fuji"; rain.userData.update(camera, t);
    const anchor = setName === "fuji" ? V(0, 0, -6) : setName === "ring" ? V(RING_X, 0, 205) : setName === "hosp" ? V(HOSP_X, 0, -1) : V(MONZA_X, 0, -6);
    key.position.copy(anchor).add(setName === "monza" ? V(-14, 22, 8) : V(-6, 14, -12)); key.target.position.copy(anchor);
    Object.assign(key.shadow.camera, { left: -16, right: 16, top: 16, bottom: -16, near: 1, far: 80 }); key.shadow.camera.updateProjectionMatrix();
    bokeh.enabled = !!cam.focus;
    if (cam.focus) { bokeh.uniforms.focus.value = cam.pos.distanceTo(cam.look); bokeh.uniforms.aperture.value = cam.aperture || 0.003; }
    composer.render();
    octx.drawImage(renderer.domElement, 0, 0, W, H);
    if (overlay) overlays[overlay](u, t);
    drawCaption(octx, t);
  };
}
