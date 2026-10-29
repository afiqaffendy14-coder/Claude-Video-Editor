// Low-poly models for the Lauda films: a 1970s F1 car, a full-face helmet, a driver bust
// with arms, and the grid / pit wall / grandstand set. Everything is flat-shaded so the
// facets read like a video game, but built from enough pieces to look like the real thing.
import * as THREE from "../lib/three.module.js";

export const ACCENT = "#d7262b";
export const RIVAL = "#9a9a98";
export const GROUND = "#f2f2f0";

const lerp = (a, b, k) => a + (b - a) * k;

export function mat(color, extra = {}) {
  return new THREE.MeshStandardMaterial({ color, flatShading: true, roughness: 0.82, metalness: 0, ...extra });
}

const DARK = mat("#262626");
const METAL = mat("#8a8a86", { roughness: 0.45, metalness: 0.35 });
const CARBON = mat("#3a3a38", { roughness: 0.6 });
const OFFWHITE = mat("#f4f4f1");

export function shadowed(obj) {
  obj.traverse((o) => {
    if (o.isMesh) {
      o.castShadow = true;
      o.receiveShadow = true;
    }
  });
  return obj;
}

// Loft: connect cross-sections along +z into a closed faceted hull.
// Each section: { z, w, h, y, p } — width, height, centre height, squareness (2 = ellipse, 4+ = boxy).
export function loft(sections, n = 12) {
  const pos = [];
  const idx = [];
  const ring = (s) => {
    const pts = [];
    const p = s.p ?? 3;
    for (let k = 0; k < n; k++) {
      const a = (k / n) * Math.PI * 2;
      const c = Math.cos(a), si = Math.sin(a);
      const x = (s.w / 2) * Math.sign(c) * Math.pow(Math.abs(c), 2 / p);
      let y = (s.h / 2) * Math.sign(si) * Math.pow(Math.abs(si), 2 / p);
      if (s.flat && y < 0) y *= s.flat; // flatter floor
      pts.push([x, s.y + y, s.z]);
    }
    return pts;
  };
  sections.forEach((s) => ring(s).forEach((q) => pos.push(...q)));
  for (let i = 0; i < sections.length - 1; i++) {
    for (let k = 0; k < n; k++) {
      const a = i * n + k, b = i * n + ((k + 1) % n), c = (i + 1) * n + k, d = (i + 1) * n + ((k + 1) % n);
      idx.push(a, c, b, b, c, d);
    }
  }
  // end caps
  for (const [i, flip] of [[0, true], [sections.length - 1, false]]) {
    const s = sections[i];
    const ci = pos.length / 3;
    pos.push(0, s.y, s.z);
    for (let k = 0; k < n; k++) {
      const a = i * n + k, b = i * n + ((k + 1) % n);
      flip ? idx.push(ci, b, a) : idx.push(ci, a, b);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

// A rod between two points (suspension arms, fence rails, exhaust stubs).
export function rod(a, b, r, material, radial = 6) {
  const dir = new THREE.Vector3().subVectors(b, a);
  const len = dir.length();
  const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, len, radial), material);
  m.position.copy(a).addScaledVector(dir, 0.5);
  m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
  return m;
}

// A wing element: an airfoil extruded across x. Leading edge points to −z.
function airfoil(chord, thick, span, material, aoa = 0) {
  const s = new THREE.Shape();
  const N = 8;
  const top = [], bot = [];
  for (let i = 0; i <= N; i++) {
    const x = i / N; // 0 trailing … 1 leading
    const t = thick * (1.2 * Math.sqrt(x) - 0.9 * x + 0.1 * x * x - 0.4 * x * x * x);
    top.push([x * chord, Math.max(t, 0.002)]);
    bot.push([x * chord, -Math.max(t * 0.35, 0.001)]);
  }
  s.moveTo(top[0][0], top[0][1]);
  top.forEach((p) => s.lineTo(p[0], p[1]));
  bot.reverse().forEach((p) => s.lineTo(p[0], p[1]));
  const g = new THREE.ExtrudeGeometry(s, { depth: span, bevelEnabled: false, curveSegments: 1 });
  g.translate(-chord / 2, 0, -span / 2);
  g.rotateY(Math.PI / 2); // span → x, leading edge → −z
  g.rotateX(aoa);
  return new THREE.Mesh(g, material);
}

function numberDecal(text) {
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const g = c.getContext("2d");
  g.fillStyle = "#ffffff";
  g.beginPath();
  g.arc(64, 64, 60, 0, Math.PI * 2);
  g.fill();
  g.fillStyle = "#141414";
  g.font = "900 76px Inter, sans-serif";
  g.textAlign = "center";
  g.textBaseline = "middle";
  g.fillText(text, 64, 70);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return new THREE.MeshStandardMaterial({ map: tex, transparent: true, roughness: 0.8, polygonOffset: true, polygonOffsetFactor: -2 });
}

// ---------------------------------------------------------------- helmet

// Full-face helmet facing +z, centred on its own origin. r ≈ 0.155 m at life size.
export function buildHelmet(r = 0.155, color = ACCENT) {
  const g = new THREE.Group();
  const shell = mat(color, { side: THREE.DoubleSide, roughness: 0.5 });
  g.add(new THREE.Mesh(new THREE.SphereGeometry(r, 18, 13, 0, Math.PI * 2, 0, 2.25), shell));
  // chin bar: the shell continues lower at the front
  g.add(new THREE.Mesh(new THREE.SphereGeometry(r * 0.995, 12, 3, Math.PI / 2 - 1.0, 2.0, 2.2, 0.45), shell));
  // visor + its pivots
  g.add(new THREE.Mesh(new THREE.SphereGeometry(r * 1.025, 16, 4, Math.PI / 2 - 1.0, 2.0, 1.18, 0.6), mat("#151515", { roughness: 0.25, metalness: 0.2 })));
  for (const sx of [-1, 1]) {
    const pivot = new THREE.Mesh(new THREE.CylinderGeometry(r * 0.13, r * 0.13, r * 0.08, 8).rotateZ(Math.PI / 2), CARBON);
    pivot.position.set(sx * r * 1.0, -r * 0.05, r * 0.08);
    g.add(pivot);
  }
  // white stripe front-to-back over the crown
  const stripe = OFFWHITE;
  g.add(new THREE.Mesh(new THREE.SphereGeometry(r * 1.006, 2, 10, Math.PI / 2 - 0.11, 0.22, 0.04, 1.12), stripe));
  g.add(new THREE.Mesh(new THREE.SphereGeometry(r * 1.006, 2, 14, -Math.PI / 2 - 0.11, 0.22, 0.04, 2.15), stripe));
  // rubber trim around the opening
  const trim = new THREE.Mesh(new THREE.TorusGeometry(r * Math.sin(2.25), r * 0.06, 4, 20), DARK);
  trim.rotation.x = Math.PI / 2;
  trim.position.y = r * Math.cos(2.25);
  g.add(trim);
  return shadowed(g);
}

// ---------------------------------------------------------------- car

// 1970s-style F1 car, forward −z, ~4.3 m long. Returns a group with userData.wheels.
export function buildCar(color, number) {
  const car = new THREE.Group();
  const body = mat(color, { roughness: 0.55 });

  // Tub + nose + engine cover as one lofted hull
  const hull = loft(
    [
      { z: -2.18, w: 0.16, h: 0.1, y: 0.3, p: 2.4 },
      { z: -2.0, w: 0.3, h: 0.17, y: 0.31, p: 2.6 },
      { z: -1.6, w: 0.42, h: 0.24, y: 0.33, p: 2.8, flat: 0.7 },
      { z: -1.1, w: 0.52, h: 0.3, y: 0.36, p: 3, flat: 0.6 },
      { z: -0.6, w: 0.6, h: 0.38, y: 0.4, p: 3.2, flat: 0.6 },
      { z: -0.1, w: 0.66, h: 0.42, y: 0.42, p: 3.4, flat: 0.6 },
      { z: 0.45, w: 0.68, h: 0.4, y: 0.42, p: 3.4, flat: 0.6 },
      { z: 0.95, w: 0.6, h: 0.42, y: 0.46, p: 3, flat: 0.6 },
      { z: 1.35, w: 0.42, h: 0.34, y: 0.45, p: 2.8, flat: 0.6 },
      { z: 1.62, w: 0.26, h: 0.2, y: 0.42, p: 2.6 },
    ],
    14,
  );
  car.add(new THREE.Mesh(hull, body));

  // Cockpit opening, coaming and windscreen
  const opening = new THREE.Mesh(loft([
    { z: -0.32, w: 0.3, h: 0.04, y: 0.635, p: 4 },
    { z: 0.0, w: 0.42, h: 0.05, y: 0.64, p: 4 },
    { z: 0.32, w: 0.4, h: 0.05, y: 0.63, p: 4 },
  ], 10), DARK);
  car.add(opening);
  const screen = new THREE.Mesh(
    new THREE.CylinderGeometry(0.24, 0.24, 0.16, 10, 1, true, -0.9, 1.8),
    new THREE.MeshStandardMaterial({ color: "#b9c3c8", transparent: true, opacity: 0.45, roughness: 0.1, side: THREE.DoubleSide, flatShading: true }),
  );
  screen.rotation.x = -0.55;
  screen.position.set(0, 0.68, -0.18);
  car.add(screen);

  // Sidepods with dark radiator inlets
  for (const sx of [-1, 1]) {
    const pod = new THREE.Mesh(loft([
      { z: -0.35, w: 0.34, h: 0.2, y: 0.3, p: 4 },
      { z: 0.0, w: 0.4, h: 0.26, y: 0.31, p: 4 },
      { z: 0.85, w: 0.42, h: 0.28, y: 0.32, p: 4 },
      { z: 1.2, w: 0.28, h: 0.18, y: 0.29, p: 3.5 },
    ], 10), body);
    pod.position.x = sx * 0.5;
    car.add(pod);
    const inlet = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.17, 0.02), DARK);
    inlet.position.set(sx * 0.5, 0.31, -0.36);
    car.add(inlet);
    for (let i = 0; i < 4; i++) {
      const slat = new THREE.Mesh(new THREE.BoxGeometry(0.29, 0.012, 0.03), METAL);
      slat.position.set(sx * 0.5, 0.25 + i * 0.04, -0.37);
      car.add(slat);
    }
    // cooling duct on the cockpit side
    const duct = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.05, 0.22), DARK);
    duct.position.set(sx * 0.3, 0.6, 0.55);
    duct.rotation.x = -0.15;
    car.add(duct);
  }

  // Front wing: two blades either side of the nose with endplates
  for (const sx of [-1, 1]) {
    const blade = airfoil(0.42, 0.05, 0.62, body, -0.12);
    blade.position.set(sx * 0.5, 0.17, -1.98);
    car.add(blade);
    const plate = new THREE.Mesh(new THREE.BoxGeometry(0.025, 0.2, 0.46), body);
    plate.position.set(sx * 0.82, 0.21, -1.98);
    car.add(plate);
  }

  // Rear wing on twin pillars, with big endplates
  const rearWing = airfoil(0.5, 0.07, 1.1, body, -0.2);
  rearWing.position.set(0, 0.98, 1.95);
  car.add(rearWing);
  const flap = airfoil(0.18, 0.03, 1.08, body, -0.55);
  flap.position.set(0, 1.03, 2.2);
  car.add(flap);
  for (const sx of [-1, 1]) {
    const plate = new THREE.Mesh(new THREE.BoxGeometry(0.025, 0.36, 0.7), DARK);
    plate.position.set(sx * 0.56, 0.96, 2.02);
    car.add(plate);
    car.add(rod(new THREE.Vector3(sx * 0.12, 0.5, 1.6), new THREE.Vector3(sx * 0.12, 0.96, 1.95), 0.02, CARBON));
  }

  // Exposed engine: cylinder banks, airbox intakes, exhausts, gearbox, oil cooler
  for (const sx of [-1, 1]) {
    const bank = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.12, 0.62), METAL);
    bank.position.set(sx * 0.24, 0.5, 1.15);
    bank.rotation.z = sx * 0.25;
    car.add(bank);
    for (let i = 0; i < 4; i++) {
      const trumpet = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.03, 0.08, 6), METAL);
      trumpet.position.set(sx * 0.18, 0.6, 0.92 + i * 0.15);
      car.add(trumpet);
    }
    // two exhaust pipes per side sweeping back to the tail
    for (const dz of [0, 0.08]) {
      const curve = new THREE.CatmullRomCurve3([
        new THREE.Vector3(sx * 0.32, 0.42, 0.95 + dz),
        new THREE.Vector3(sx * 0.36, 0.36, 1.35 + dz),
        new THREE.Vector3(sx * 0.26, 0.38, 1.85),
        new THREE.Vector3(sx * 0.22, 0.42, 2.05),
      ]);
      car.add(new THREE.Mesh(new THREE.TubeGeometry(curve, 10, 0.028, 6), mat("#5b5b57", { metalness: 0.4, roughness: 0.4 })));
    }
  }
  const gearbox = new THREE.Mesh(loft([
    { z: 1.55, w: 0.3, h: 0.24, y: 0.36, p: 4 },
    { z: 2.0, w: 0.22, h: 0.18, y: 0.35, p: 4 },
  ], 8), CARBON);
  car.add(gearbox);
  const cooler = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.12, 0.05), METAL);
  cooler.position.set(0, 0.5, 2.08);
  car.add(cooler);

  // Roll hoop + mirrors
  const hoop = new THREE.Mesh(new THREE.TorusGeometry(0.17, 0.022, 5, 10, Math.PI), METAL);
  hoop.position.set(0, 0.66, 0.38);
  car.add(hoop);
  for (const sx of [-1, 1]) {
    car.add(rod(new THREE.Vector3(sx * 0.3, 0.6, -0.28), new THREE.Vector3(sx * 0.42, 0.74, -0.3), 0.012, DARK));
    const mirror = new THREE.Mesh(new THREE.BoxGeometry(0.13, 0.07, 0.04), body);
    mirror.position.set(sx * 0.46, 0.76, -0.3);
    car.add(mirror);
  }

  // Driver in the cockpit: helmet and shoulders
  const shoulders = new THREE.Mesh(new THREE.SphereGeometry(0.2, 10, 6, 0, Math.PI * 2, 0, Math.PI / 2), mat(number === "1" ? ACCENT : "#c9c9c6"));
  shoulders.scale.set(1.1, 0.5, 0.7);
  shoulders.position.set(0, 0.62, 0.15);
  car.add(shoulders);
  const helmet = buildHelmet(0.145, number === "1" ? ACCENT : "#e9e9e6");
  helmet.position.set(0, 0.8, 0.12);
  car.add(helmet);

  // Wheels with suspension
  car.userData.wheels = [];
  const wheel = (rOut, w, x, z) => {
    const g = new THREE.Group();
    const rIn = rOut * 0.6;
    const prof = [
      new THREE.Vector2(rIn, -w / 2),
      new THREE.Vector2(rOut - 0.05, -w / 2),
      new THREE.Vector2(rOut - 0.01, -w / 2 + 0.04),
      new THREE.Vector2(rOut, -w / 4),
      new THREE.Vector2(rOut, w / 4),
      new THREE.Vector2(rOut - 0.01, w / 2 - 0.04),
      new THREE.Vector2(rOut - 0.05, w / 2),
      new THREE.Vector2(rIn, w / 2),
    ];
    const tyre = new THREE.Mesh(new THREE.LatheGeometry(prof, 20).rotateZ(Math.PI / 2), mat("#232323", { side: THREE.DoubleSide, roughness: 0.95 }));
    g.add(tyre);
    const outer = Math.sign(x) * (w / 2);
    // sidewall lettering band
    const band = new THREE.Mesh(new THREE.TorusGeometry(rOut * 0.82, 0.012, 3, 24).rotateY(Math.PI / 2), mat("#d9d9d4"));
    band.position.x = outer + Math.sign(x) * 0.003;
    g.add(band);
    // rim: dished face, star spokes, hub nut
    const dish = new THREE.Mesh(new THREE.CylinderGeometry(rIn, rIn * 0.7, w * 0.3, 16).rotateZ(Math.PI / 2), mat("#4a4a47", { metalness: 0.4, roughness: 0.5 }));
    dish.position.x = outer - Math.sign(x) * w * 0.15;
    g.add(dish);
    const spokes = new THREE.Group();
    for (let i = 0; i < 6; i++) {
      const s = new THREE.Mesh(new THREE.BoxGeometry(0.02, rIn * 1.7, 0.035), METAL);
      s.rotation.x = (i / 6) * Math.PI;
      spokes.add(s);
    }
    spokes.position.x = outer - Math.sign(x) * 0.01;
    g.add(spokes);
    const nut = new THREE.Mesh(new THREE.CylinderGeometry(rIn * 0.22, rIn * 0.22, 0.06, 6).rotateZ(Math.PI / 2), METAL);
    nut.position.x = outer;
    g.add(nut);
    // brake disc on the inboard side
    const disc = new THREE.Mesh(new THREE.CylinderGeometry(rIn * 0.85, rIn * 0.85, 0.02, 16).rotateZ(Math.PI / 2), mat("#6a6a66", { metalness: 0.5 }));
    disc.position.x = -Math.sign(x) * (w / 2 - 0.03);
    g.add(disc);
    g.position.set(x, rOut, z);
    g.userData.r = rOut;
    car.add(g);
    car.userData.wheels.push(g);

    // upright + upper/lower wishbones back to the chassis
    const upright = new THREE.Mesh(new THREE.BoxGeometry(0.05, rOut * 0.9, 0.08), CARBON);
    upright.position.set(x - Math.sign(x) * (w / 2 + 0.04), rOut, z);
    car.add(upright);
    const ux = x - Math.sign(x) * (w / 2 + 0.05);
    for (const [hy, spread] of [[rOut + 0.12, 0.22], [rOut - 0.12, 0.28]]) {
      const outerPt = new THREE.Vector3(ux, hy, z);
      const inX = Math.sign(x) * 0.22;
      car.add(rod(outerPt, new THREE.Vector3(inX, hy + 0.02, z - spread), 0.013, DARK));
      car.add(rod(outerPt, new THREE.Vector3(inX, hy + 0.02, z + spread), 0.013, DARK));
    }
  };
  wheel(0.3, 0.27, -0.84, -1.38);
  wheel(0.3, 0.27, 0.84, -1.38);
  wheel(0.4, 0.46, -0.86, 1.32);
  wheel(0.4, 0.46, 0.86, 1.32);

  // Number roundels: nose top and both flanks of the engine cover
  const decal = numberDecal(number);
  const top = new THREE.Mesh(new THREE.PlaneGeometry(0.24, 0.24), decal);
  top.rotation.x = -Math.PI / 2 + 0.18;
  top.position.set(0, 0.48, -1.35);
  car.add(top);
  for (const sx of [-1, 1]) {
    const side = new THREE.Mesh(new THREE.PlaneGeometry(0.26, 0.26), decal);
    side.rotation.y = sx * Math.PI / 2;
    side.position.set(sx * 0.335, 0.47, 0.3);
    car.add(side);
  }
  return shadowed(car);
}

export function spinWheels(car, distance) {
  for (const w of car.userData.wheels) w.rotation.x = -distance / w.userData.r;
}

// ---------------------------------------------------------------- driver bust

// Driver from the waist up with posable arms. Units in metres; faces +z.
// Call driver.userData.pose(helmetY) to place the helmet and solve the arms so the
// gloves grip it.
export function buildDriver(suit = ACCENT) {
  const d = new THREE.Group();
  const suitMat = mat(suit, { roughness: 0.9 });

  // torso lofted bottom → top (z of the loft becomes height)
  const torsoGeo = loft([
    { z: 0.0, w: 0.33, h: 0.22, y: 0, p: 2.6 },
    { z: 0.15, w: 0.36, h: 0.24, y: 0.01, p: 2.6 },
    { z: 0.3, w: 0.42, h: 0.26, y: 0.015, p: 2.8 },
    { z: 0.4, w: 0.46, h: 0.24, y: 0.01, p: 3.2 },
    { z: 0.46, w: 0.36, h: 0.19, y: 0, p: 2.6 },
    { z: 0.5, w: 0.16, h: 0.13, y: 0, p: 2.2 },
  ], 14);
  torsoGeo.rotateX(-Math.PI / 2);
  d.add(new THREE.Mesh(torsoGeo, suitMat));

  // suit details: belt, zip, collar, epaulettes, chest patch
  const belt = new THREE.Mesh(new THREE.CylinderGeometry(0.172, 0.17, 0.05, 14), DARK);
  belt.scale.z = 0.66;
  belt.position.y = 0.05;
  d.add(belt);
  const zip = new THREE.Mesh(new THREE.BoxGeometry(0.012, 0.36, 0.01), DARK);
  zip.position.set(0, 0.25, 0.13);
  zip.rotation.x = -0.06;
  d.add(zip);
  const collar = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.085, 0.05, 12), OFFWHITE);
  collar.position.y = 0.505;
  d.add(collar);
  for (const sx of [-1, 1]) {
    const ep = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.012, 0.05), OFFWHITE);
    ep.position.set(sx * 0.16, 0.452, 0);
    ep.rotation.z = -sx * 0.25;
    d.add(ep);
  }
  const patch = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.04, 0.01), OFFWHITE);
  patch.position.set(0.09, 0.36, 0.125);
  patch.rotation.x = -0.12;
  d.add(patch);

  // neck + head in a fireproof balaclava (eye slit only)
  const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.062, 0.1, 10), OFFWHITE);
  neck.position.y = 0.56;
  d.add(neck);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.1, 14, 11), OFFWHITE);
  head.scale.set(0.88, 1.1, 0.98);
  head.position.y = 0.665;
  d.add(head);
  const slit = new THREE.Mesh(new THREE.SphereGeometry(0.101, 12, 2, Math.PI / 2 - 0.7, 1.4, 1.35, 0.22), mat("#7a5a48"));
  slit.scale.copy(head.scale);
  slit.position.copy(head.position);
  d.add(slit);

  const helmet = buildHelmet(0.155);
  d.add(helmet);

  // arms: shoulder ball, upper arm, elbow ball, forearm, gloved hand
  const arm = (sx) => {
    const parts = {
      shoulder: new THREE.Mesh(new THREE.SphereGeometry(0.062, 10, 8), suitMat),
      upper: new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.056, 1, 9), suitMat),
      elbow: new THREE.Mesh(new THREE.SphereGeometry(0.048, 9, 7), suitMat),
      fore: new THREE.Mesh(new THREE.CylinderGeometry(0.038, 0.047, 1, 9), suitMat),
      cuff: new THREE.Mesh(new THREE.CylinderGeometry(0.044, 0.044, 0.05, 9), OFFWHITE),
      hand: new THREE.Group(),
    };
    // glove: palm, four fingers curled over, thumb; palm faces −x for the right hand
    const glove = mat("#3a3a38", { roughness: 0.9 });
    const palm = new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.09, 0.085), glove);
    parts.hand.add(palm);
    for (let i = 0; i < 4; i++) {
      const f = new THREE.Mesh(new THREE.BoxGeometry(0.022, 0.06, 0.019), glove);
      f.position.set(-sx * 0.012, 0.07, -0.03 + i * 0.021);
      f.rotation.z = sx * 0.35;
      parts.hand.add(f);
    }
    const thumb = new THREE.Mesh(new THREE.BoxGeometry(0.022, 0.05, 0.02), glove);
    thumb.position.set(-sx * 0.015, 0.0, 0.055);
    thumb.rotation.x = 0.6;
    parts.hand.add(thumb);
    Object.values(parts).forEach((p) => d.add(p));
    return parts;
  };
  const arms = { "-1": arm(-1), "1": arm(1) };

  const Y = new THREE.Vector3(0, 1, 0);
  const place = (mesh, a, b) => {
    const dir = new THREE.Vector3().subVectors(b, a);
    mesh.position.copy(a).addScaledVector(dir, 0.5);
    mesh.scale.set(1, dir.length(), 1);
    mesh.quaternion.setFromUnitVectors(Y, dir.normalize());
  };

  const L1 = 0.29, L2 = 0.27;
  d.userData.pose = (helmetY, helmetSpin = 0) => {
    helmet.position.set(0, helmetY, 0.005);
    helmet.rotation.set(0, helmetSpin, 0);
    for (const sx of [-1, 1]) {
      const p = arms[sx];
      const S = new THREE.Vector3(sx * 0.2, 0.425, -0.005);
      const H = new THREE.Vector3(sx * 0.175, helmetY - 0.06, 0.03);
      // two-bone IK, elbow pushed outward, slightly down and forward
      const toH = new THREE.Vector3().subVectors(H, S);
      const dist = Math.min(toH.length(), L1 + L2 - 1e-3);
      const dir = toH.normalize();
      const a = (L1 * L1 - L2 * L2 + dist * dist) / (2 * dist);
      const h = Math.sqrt(Math.max(L1 * L1 - a * a, 0));
      const pole = new THREE.Vector3(sx * 1, -0.35, 0.45);
      pole.addScaledVector(dir, -pole.dot(dir)).normalize();
      const E = S.clone().addScaledVector(dir, a).addScaledVector(pole, h);
      const handPos = S.clone().addScaledVector(dir, dist);
      p.shoulder.position.copy(S);
      place(p.upper, S, E);
      p.elbow.position.copy(E);
      const wrist = E.clone().lerp(handPos, 0.86);
      place(p.fore, E, wrist);
      p.cuff.position.copy(wrist);
      p.cuff.quaternion.copy(p.fore.quaternion);
      p.hand.position.copy(handPos).add(new THREE.Vector3(0, 0.02, 0));
      // fingers point up the helmet's side, palm toward its centre
      p.hand.rotation.set(0, 0, sx * -0.15);
    }
  };
  d.userData.pose(0.9);
  return shadowed(d);
}

// ---------------------------------------------------------------- track set

export function buildTrack(scene) {
  const lineMat = new THREE.MeshBasicMaterial({ color: "#d2d2ce" });
  const flat = (w, d, x, z, m = lineMat, y = 0.004) => {
    const p = new THREE.Mesh(new THREE.PlaneGeometry(w, d), m);
    p.rotation.x = -Math.PI / 2;
    p.position.set(x, y, z);
    scene.add(p);
    return p;
  };

  const ground = new THREE.Mesh(new THREE.PlaneGeometry(500, 500), mat(GROUND, { roughness: 1 }));
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  scene.add(ground);

  // asphalt band a touch darker than the infield, with edge lines
  const asphalt = flat(7.0, 200, 0, -40, mat("#e6e6e3", { roughness: 1 }), 0.001);
  asphalt.receiveShadow = true;
  flat(0.12, 200, -3.4, -40);
  flat(0.12, 200, 3.4, -40);
  // rubber laid down on the racing line
  const rubber = new THREE.MeshBasicMaterial({ color: "#d9d9d5", transparent: true, opacity: 0.7 });
  for (const x of [-1.5, 1.5]) for (const dx of [-0.86, 0.86]) flat(0.35, 200, x + dx, -40, rubber, 0.002);

  // grid slots: staggered boxes with a short painted number line
  for (let i = -8; i <= 4; i++) {
    const x = i % 2 ? 1.5 : -1.5;
    const z = i * 7;
    flat(1.9, 0.09, x, z - 2.55);
    flat(0.09, 0.8, x - 0.95, z - 2.2);
    flat(0.09, 0.8, x + 0.95, z - 2.2);
  }

  // kerb blocks along the far edge (grey/white, red stays reserved for the hero)
  for (let z = -120; z < 40; z += 1.2) {
    const k = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.05, 1.2), mat(Math.round(z / 1.2) % 2 ? "#ffffff" : "#c4c4c0"));
    k.position.set(3.75, 0.025, z);
    k.receiveShadow = true;
    scene.add(k);
  }

  // pit wall with posts and a three-rail fence
  const concrete = mat("#e0e0dc");
  const wall = new THREE.Mesh(new THREE.BoxGeometry(0.45, 1.0, 180), concrete);
  wall.position.set(-3.9, 0.5, -40);
  scene.add(shadowed(wall));
  const steel = mat("#b8b8b4", { metalness: 0.3, roughness: 0.5 });
  for (let z = -130; z < 50; z += 3) {
    scene.add(shadowed(rod(new THREE.Vector3(-3.9, 1.0, z), new THREE.Vector3(-3.9, 2.6, z), 0.035, steel)));
  }
  for (const y of [1.5, 2.05, 2.6]) {
    scene.add(rod(new THREE.Vector3(-3.9, y, -130), new THREE.Vector3(-3.9, y, 50), 0.02, steel));
  }

  // grandstand: stepped terraces, seat rows, pillars and a cantilever roof
  const stand = new THREE.Group();
  const terrace = mat("#dadad6");
  const seat = mat("#cfcfcb");
  for (let i = 0; i < 12; i++) {
    const h = 0.6 + i * 0.55;
    const step = new THREE.Mesh(new THREE.BoxGeometry(1.1, h, 160), terrace);
    step.position.set(-11 - i * 1.1, h / 2, -40);
    stand.add(step);
    const row = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.22, 160), seat);
    row.position.set(-10.75 - i * 1.1, h + 0.11, -40);
    stand.add(row);
  }
  for (let z = -115; z < 40; z += 12) {
    const pillar = new THREE.Mesh(new THREE.BoxGeometry(0.4, 10.5, 0.4), terrace);
    pillar.position.set(-24.2, 5.25, z);
    stand.add(pillar);
  }
  const roof = new THREE.Mesh(new THREE.BoxGeometry(15, 0.3, 160), mat("#e4e4e0"));
  roof.position.set(-17.5, 10.6, -40);
  roof.rotation.z = -0.06;
  stand.add(roof);
  scene.add(shadowed(stand));
}
