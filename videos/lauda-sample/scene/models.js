// Models for the Lauda films: a 1976-style F1 car, a full-face helmet, a driver bust with
// posable arms, pit crew, the circuit (grid, pit wall, garages, start gantry, grandstand
// crowd, billboards, tyre barriers) and a garage set. Surfaces are smooth with creased
// normals so hard edges stay sharp, on physically based materials.
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { mergeGeometries, toCreasedNormals } from "three/addons/utils/BufferGeometryUtils.js";

export const ACCENT = "#c8161d";
export const RIVAL = "#8c8e90";
export const GROUND = "#ecebe8";

const lerp = (a, b, k) => a + (b - a) * k;

// ---------------------------------------------------------------- materials

export const paint = (color) =>
  new THREE.MeshPhysicalMaterial({ color, roughness: 0.32, metalness: 0.05, clearcoat: 1, clearcoatRoughness: 0.06 });
export const std = (color, roughness = 0.7, metalness = 0, extra = {}) =>
  new THREE.MeshStandardMaterial({ color, roughness, metalness, ...extra });

const M = {
  carbon: std("#141414", 0.42, 0.25),
  satin: std("#1d1d1d", 0.6, 0.1),
  rubber: std("#161616", 0.88, 0),
  steel: std("#c2c2bd", 0.28, 1),
  alu: std("#9c9c98", 0.42, 0.85),
  exhaust: std("#6e6258", 0.38, 0.9),
  white: std("#f3f3f0", 0.6, 0),
  glass: new THREE.MeshPhysicalMaterial({ color: "#c9d2d6", roughness: 0.05, metalness: 0, transparent: true, opacity: 0.32, side: THREE.DoubleSide }),
  visor: new THREE.MeshPhysicalMaterial({ color: "#0b0b0c", roughness: 0.06, metalness: 0.6, clearcoat: 1, clearcoatRoughness: 0.03 }),
};

// ---------------------------------------------------------------- geometry helpers

export const crease = (geo, deg = 32) => toCreasedNormals(geo, THREE.MathUtils.degToRad(deg));
export const rbox = (w, h, d, r = 0.012, seg = 2) => new RoundedBoxGeometry(w, h, d, seg, Math.min(r, w / 2.1, h / 2.1, d / 2.1));

export function shadowed(obj) {
  obj.traverse((o) => {
    if (o.isMesh) {
      o.castShadow = true;
      o.receiveShadow = true;
    }
  });
  return obj;
}

const put = (parent, geo, material, x = 0, y = 0, z = 0, rx = 0, ry = 0, rz = 0) => {
  const m = new THREE.Mesh(geo, material);
  m.position.set(x, y, z);
  m.rotation.set(rx, ry, rz);
  parent.add(m);
  return m;
};

// Loft cross-sections along +z into a closed hull. Section: { z, w, h, y, p } where p is
// squareness (2 ellipse … 10 near-box). Returns creased-normal geometry.
export function loft(sections, n = 24, deg = 30) {
  const pos = [];
  const idx = [];
  sections.forEach((s) => {
    const p = s.p ?? 4;
    for (let k = 0; k < n; k++) {
      const a = (k / n) * Math.PI * 2 + Math.PI / n;
      const c = Math.cos(a), si = Math.sin(a);
      const x = (s.w / 2) * Math.sign(c) * Math.pow(Math.abs(c), 2 / p);
      let y = (s.h / 2) * Math.sign(si) * Math.pow(Math.abs(si), 2 / p);
      if (s.flat && y < 0) y *= s.flat;
      pos.push(x, s.y + y, s.z);
    }
  });
  for (let i = 0; i < sections.length - 1; i++) {
    for (let k = 0; k < n; k++) {
      const a = i * n + k, b = i * n + ((k + 1) % n), c = (i + 1) * n + k, d = (i + 1) * n + ((k + 1) % n);
      idx.push(a, b, c, b, d, c); // outward-facing winding
    }
  }
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
  return crease(g, deg);
}

export function rod(a, b, r, material, radial = 10) {
  const dir = new THREE.Vector3().subVectors(b, a);
  const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, dir.length(), radial), material);
  m.position.copy(a).addScaledVector(dir, 0.5);
  m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
  return m;
}

// Wing element: an airfoil extruded across x, leading edge to −z.
function airfoil(chord, thick, span, material, aoa = 0) {
  const s = new THREE.Shape();
  const N = 18;
  const top = [], bot = [];
  for (let i = 0; i <= N; i++) {
    const x = i / N;
    const t = thick * (1.25 * Math.sqrt(x) - 0.95 * x + 0.12 * x * x - 0.42 * x * x * x);
    top.push([x * chord, Math.max(t, 0.0015)]);
    bot.push([x * chord, -Math.max(t * 0.3, 0.001)]);
  }
  s.moveTo(top[0][0], top[0][1]);
  top.forEach((p) => s.lineTo(p[0], p[1]));
  bot.reverse().forEach((p) => s.lineTo(p[0], p[1]));
  const g = new THREE.ExtrudeGeometry(s, { depth: span, bevelEnabled: true, bevelSize: 0.003, bevelThickness: 0.003, bevelSegments: 1, curveSegments: 1 });
  g.translate(-chord / 2, 0, -span / 2);
  g.rotateY(Math.PI / 2);
  g.rotateX(aoa);
  return new THREE.Mesh(crease(g, 40), material);
}

function textTexture(draw, w = 256, h = 256) {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  draw(c.getContext("2d"), w, h);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  return tex;
}

function roundel(text) {
  const map = textTexture((g) => {
    g.fillStyle = "#ffffff";
    g.beginPath();
    g.arc(128, 128, 122, 0, Math.PI * 2);
    g.fill();
    g.fillStyle = "#111111";
    g.font = "900 150px Inter, sans-serif";
    g.textAlign = "center";
    g.textBaseline = "middle";
    g.fillText(text, 128, 140);
  });
  return new THREE.MeshStandardMaterial({ map, transparent: true, roughness: 0.35, polygonOffset: true, polygonOffsetFactor: -4 });
}

// ---------------------------------------------------------------- helmet

// Full-face helmet facing +z, origin at the centre of the head. r ≈ 0.155 m.
export function buildHelmet(r = 0.155, color = ACCENT) {
  const g = new THREE.Group();
  const shellMat = paint(color);
  shellMat.side = THREE.DoubleSide;
  const shell = put(g, new THREE.SphereGeometry(r, 64, 40, 0, Math.PI * 2, 0, 2.2), shellMat);
  shell.scale.set(0.94, 1.04, 1.08);

  // chin bar: the shell continues lower across the front
  const chin = put(g, new THREE.SphereGeometry(r, 48, 10, Math.PI / 2 - 1.15, 2.3, 2.15, 0.55), shellMat);
  chin.scale.copy(shell.scale);

  // visor over the eye port, with side pivots
  const visor = put(g, new THREE.SphereGeometry(r * 1.035, 48, 12, Math.PI / 2 - 1.05, 2.1, 1.12, 0.62), M.visor);
  visor.scale.copy(shell.scale);
  for (const sx of [-1, 1]) {
    put(g, new THREE.CylinderGeometry(r * 0.12, r * 0.12, r * 0.06, 20), M.satin, sx * r * 0.95, -r * 0.04, r * 0.1, 0, 0, Math.PI / 2);
  }
  // chin-bar vents
  for (const sx of [-1, 1]) put(g, rbox(r * 0.2, r * 0.06, r * 0.05, 0.004), M.satin, sx * r * 0.2, -r * 0.55, r * 1.02, 0.35, sx * 0.3, 0);

  // white stripe over the crown and a rubber trim ring at the opening
  const stripe = put(g, new THREE.SphereGeometry(r * 1.004, 6, 30, Math.PI / 2 - 0.1, 0.2, 0.03, 2.05), M.white);
  stripe.scale.copy(shell.scale);
  const stripeBack = put(g, new THREE.SphereGeometry(r * 1.004, 6, 30, -Math.PI / 2 - 0.1, 0.2, 0.03, 2.1), M.white);
  stripeBack.scale.copy(shell.scale);
  const trim = put(g, new THREE.TorusGeometry(r * Math.sin(2.2) * 0.98, r * 0.05, 10, 48), M.rubber, 0, r * Math.cos(2.2) * 1.04, 0, Math.PI / 2);
  trim.scale.set(0.94, 1.08, 1);
  return shadowed(g);
}

// ---------------------------------------------------------------- car

// 1976-style F1 car, forward −z, about 4.3 m long. userData.wheels holds the spinning groups.
export function buildCar(color, number) {
  const car = new THREE.Group();
  const body = paint(color);

  // Tub, nose and engine cover: one hull with crisp shoulders
  put(car, loft([
    { z: -2.15, w: 0.34, h: 0.08, y: 0.25, p: 8 },
    { z: -1.95, w: 0.4, h: 0.13, y: 0.27, p: 8 },
    { z: -1.45, w: 0.48, h: 0.21, y: 0.3, p: 8, flat: 0.8 },
    { z: -0.95, w: 0.56, h: 0.3, y: 0.34, p: 8, flat: 0.7 },
    { z: -0.5, w: 0.66, h: 0.4, y: 0.39, p: 8, flat: 0.7 },
    { z: -0.1, w: 0.74, h: 0.45, y: 0.41, p: 9, flat: 0.7 },
    { z: 0.4, w: 0.78, h: 0.43, y: 0.41, p: 9, flat: 0.7 },
    { z: 0.8, w: 0.7, h: 0.4, y: 0.41, p: 8, flat: 0.7 },
    { z: 1.2, w: 0.52, h: 0.32, y: 0.4, p: 7 },
    { z: 1.5, w: 0.32, h: 0.22, y: 0.38, p: 6 },
  ], 28, 28), body);

  // Cockpit opening + padded coaming
  put(car, loft([
    { z: -0.34, w: 0.32, h: 0.05, y: 0.62, p: 6 },
    { z: 0.0, w: 0.46, h: 0.06, y: 0.635, p: 6 },
    { z: 0.34, w: 0.44, h: 0.06, y: 0.625, p: 6 },
  ], 20), M.satin);
  const screen = put(car, new THREE.CylinderGeometry(0.26, 0.26, 0.17, 32, 1, true, -0.95, 1.9), M.glass, 0, 0.67, -0.22, -0.6);
  screen.rotation.y = Math.PI;

  // NACA ducts and mirrors on the cockpit flanks
  for (const sx of [-1, 1]) {
    put(car, rbox(0.03, 0.06, 0.24, 0.008), M.carbon, sx * 0.36, 0.5, -0.05, 0, sx * 0.1, 0);
    car.add(rod(new THREE.Vector3(sx * 0.33, 0.6, -0.3), new THREE.Vector3(sx * 0.46, 0.75, -0.32), 0.011, M.carbon));
    put(car, rbox(0.15, 0.08, 0.05, 0.015), body, sx * 0.5, 0.77, -0.32);
    put(car, rbox(0.13, 0.065, 0.006, 0.003), M.steel, sx * 0.5, 0.77, -0.297);
  }

  // Sidepods: long sharp boxes, dark recessed radiator inlets with vanes, top louvres
  for (const sx of [-1, 1]) {
    put(car, crease(rbox(0.44, 0.27, 1.5, 0.035, 3), 35), body, sx * 0.56, 0.3, 0.35);
    put(car, rbox(0.36, 0.2, 0.04, 0.01), M.carbon, sx * 0.56, 0.31, -0.39);
    for (let i = 0; i < 5; i++) put(car, rbox(0.35, 0.008, 0.03, 0.002), M.alu, sx * 0.56, 0.24 + i * 0.035, -0.405);
    for (let i = 0; i < 6; i++) put(car, rbox(0.3, 0.006, 0.025, 0.002), M.carbon, sx * 0.56, 0.437, 0.55 + i * 0.07);
  }

  // Full-width front wing on the nose, with endplates and mounts
  const fw = airfoil(0.5, 0.05, 1.86, body, -0.1);
  fw.position.set(0, 0.19, -2.02);
  car.add(fw);
  for (const sx of [-1, 1]) {
    put(car, crease(rbox(0.02, 0.24, 0.58, 0.006)), M.carbon, sx * 0.94, 0.22, -2.02);
    put(car, rbox(0.04, 0.08, 0.2, 0.008), M.carbon, sx * 0.12, 0.23, -1.98);
  }

  // Exposed flat-12: finned heads, intake trumpets, exhausts, gearbox, coilovers, oil cooler
  for (const sx of [-1, 1]) {
    put(car, crease(rbox(0.15, 0.12, 0.72, 0.012)), M.alu, sx * 0.31, 0.43, 1.12);
    for (let i = 0; i < 9; i++) put(car, rbox(0.17, 0.008, 0.012, 0.002), M.alu, sx * 0.31, 0.5, 0.8 + i * 0.08);
    for (let i = 0; i < 6; i++) {
      put(car, new THREE.CylinderGeometry(0.024, 0.03, 0.1, 16, 1, true), M.steel, sx * 0.16, 0.66, 0.85 + i * 0.1);
      put(car, new THREE.TorusGeometry(0.026, 0.005, 6, 16), M.steel, sx * 0.16, 0.71, 0.85 + i * 0.1, Math.PI / 2);
    }
    for (let k = 0; k < 3; k++) {
      const curve = new THREE.CatmullRomCurve3([
        new THREE.Vector3(sx * 0.36, 0.38, 0.85 + k * 0.18),
        new THREE.Vector3(sx * 0.42, 0.3, 1.1 + k * 0.12),
        new THREE.Vector3(sx * 0.33, 0.32, 1.65),
        new THREE.Vector3(sx * 0.24, 0.36, 2.02),
      ]);
      car.add(new THREE.Mesh(new THREE.TubeGeometry(curve, 40, 0.027, 12), M.exhaust));
    }
    put(car, new THREE.CylinderGeometry(0.045, 0.04, 0.12, 20, 1, true), M.exhaust, sx * 0.24, 0.36, 2.08, Math.PI / 2);
    // coilover: spring helix around a damper
    const pts = [];
    for (let i = 0; i <= 120; i++) {
      const a = i * 0.42;
      pts.push(new THREE.Vector3(Math.cos(a) * 0.035, i * 0.0022, Math.sin(a) * 0.035));
    }
    const spring = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 240, 0.006, 6), M.steel);
    spring.position.set(sx * 0.2, 0.32, 1.62);
    spring.rotation.z = sx * 0.6;
    car.add(spring);
  }
  put(car, crease(rbox(0.34, 0.26, 0.6, 0.02)), M.carbon, 0, 0.36, 1.82);
  put(car, rbox(0.46, 0.14, 0.05, 0.01), M.alu, 0, 0.52, 2.12);
  for (let i = 0; i < 6; i++) put(car, rbox(0.44, 0.006, 0.054, 0.002), M.carbon, 0, 0.47 + i * 0.02, 2.12);

  // Rear wing on a central pillar with tall endplates
  const rw = airfoil(0.56, 0.075, 1.12, body, -0.18);
  rw.position.set(0, 1.0, 2.0);
  car.add(rw);
  const flap = airfoil(0.2, 0.03, 1.1, body, -0.5);
  flap.position.set(0, 1.05, 2.28);
  car.add(flap);
  for (const sx of [-1, 1]) put(car, crease(rbox(0.02, 0.44, 0.82, 0.006)), body, sx * 0.57, 0.98, 2.05);
  put(car, crease(rbox(0.05, 0.5, 0.16, 0.01)), M.carbon, 0, 0.72, 1.92, -0.25);

  // Roll hoop
  put(car, new THREE.TorusGeometry(0.17, 0.02, 10, 24, Math.PI), M.steel, 0, 0.66, 0.36);

  // Driver in the cockpit, looking forward (−z)
  put(car, new THREE.SphereGeometry(0.2, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2), std(number === "1" ? ACCENT : "#bdbdba", 0.8), 0, 0.61, 0.15).scale.set(1.1, 0.5, 0.72);
  const helmet = buildHelmet(0.145, number === "1" ? ACCENT : "#e9e9e6");
  helmet.position.set(0, 0.79, 0.1);
  helmet.rotation.y = Math.PI;
  car.add(helmet);

  // Wheels and suspension
  car.userData.wheels = [];
  const wheel = (rOut, w, x, z) => {
    const g = new THREE.Group();
    const rIn = rOut * 0.62;
    const prof = [];
    for (let i = 0; i <= 14; i++) {
      const t = i / 14;
      const y = lerp(-w / 2, w / 2, t);
      const bulge = Math.pow(Math.sin(Math.PI * t), 0.25);
      prof.push(new THREE.Vector2(lerp(rIn + 0.03, rOut, bulge), y));
    }
    prof.unshift(new THREE.Vector2(rIn, -w / 2));
    prof.push(new THREE.Vector2(rIn, w / 2));
    g.add(new THREE.Mesh(new THREE.LatheGeometry(prof, 72).rotateZ(Math.PI / 2), M.rubber));
    const out = Math.sign(x);
    // sidewall lettering band
    put(g, new THREE.TorusGeometry(rOut * 0.84, 0.008, 4, 72), std("#d7d7d2", 0.6), out * (w / 2 - 0.006), 0, 0, 0, Math.PI / 2);
    // five-spoke star rim with lip, dished centre and nut
    put(g, new THREE.CylinderGeometry(rIn, rIn, w * 0.86, 48, 1, true), M.alu, 0, 0, 0, 0, 0, Math.PI / 2).material.side = THREE.DoubleSide;
    put(g, new THREE.TorusGeometry(rIn, 0.012, 8, 48), M.steel, out * w * 0.43, 0, 0, 0, Math.PI / 2);
    put(g, new THREE.CylinderGeometry(rIn * 0.9, rIn * 0.9, 0.01, 48), M.carbon, out * w * 0.2, 0, 0, 0, 0, Math.PI / 2);
    const star = new THREE.Group();
    for (let i = 0; i < 5; i++) {
      const sp = put(star, crease(rbox(0.035, rIn * 0.95, 0.06, 0.01)), M.alu, 0, rIn * 0.46, 0);
      const holder = new THREE.Group();
      holder.add(sp);
      holder.rotation.x = (i / 5) * Math.PI * 2;
      star.add(holder);
    }
    star.position.x = out * w * 0.32;
    g.add(star);
    put(g, new THREE.CylinderGeometry(rIn * 0.24, rIn * 0.28, 0.08, 6), M.steel, out * w * 0.38, 0, 0, 0, 0, Math.PI / 2);
    // brake disc and caliper inboard
    put(g, new THREE.CylinderGeometry(rIn * 0.82, rIn * 0.82, 0.022, 40), std("#7d7d78", 0.35, 0.8), -out * (w / 2 - 0.04), 0, 0, 0, 0, Math.PI / 2);
    g.position.set(x, rOut, z);
    g.userData.r = rOut;
    car.add(g);
    car.userData.wheels.push(g);
    put(car, crease(rbox(0.05, 0.14, 0.09, 0.01)), M.carbon, x - out * (w / 2 + 0.03), rOut + rIn * 0.4, z - 0.04);

    const ux = x - out * (w / 2 + 0.05);
    put(car, crease(rbox(0.05, rOut * 0.95, 0.08, 0.01)), M.carbon, ux, rOut, z);
    for (const [hy, spread] of [[rOut + 0.12, 0.22], [rOut - 0.12, 0.3]]) {
      const o = new THREE.Vector3(ux, hy, z);
      const inX = out * 0.24;
      car.add(rod(o, new THREE.Vector3(inX, hy + 0.02, z - spread), 0.012, M.steel));
      car.add(rod(o, new THREE.Vector3(inX, hy + 0.02, z + spread), 0.012, M.steel));
    }
  };
  wheel(0.3, 0.27, -0.86, -1.36);
  wheel(0.3, 0.27, 0.86, -1.36);
  wheel(0.405, 0.47, -0.88, 1.3);
  wheel(0.405, 0.47, 0.88, 1.3);

  // Number roundels on the nose and engine-cover flanks
  const decal = roundel(number);
  put(car, new THREE.CircleGeometry(0.12, 40), decal, 0, 0.405, -1.3, -Math.PI / 2 + 0.17);
  for (const sx of [-1, 1]) put(car, new THREE.CircleGeometry(0.13, 40), decal, sx * 0.392, 0.45, 0.32, 0, sx * Math.PI / 2, 0);

  return shadowed(car);
}

export function spinWheels(car, distance) {
  for (const w of car.userData.wheels) w.rotation.x = -distance / w.userData.r;
}

// ---------------------------------------------------------------- people

// Driver from the waist up, facing +z. userData.pose(helmetY, spin) seats the helmet and
// solves both arms so the gloves grip it.
export function buildDriver(suit = ACCENT) {
  const d = new THREE.Group();
  const suitMat = new THREE.MeshPhysicalMaterial({ color: suit, roughness: 0.82, sheen: 0.6, sheenRoughness: 0.6, sheenColor: new THREE.Color("#ff8a8a") });
  const balaclava = new THREE.MeshPhysicalMaterial({ color: "#efefec", roughness: 0.92, sheen: 0.4, sheenColor: new THREE.Color("#ffffff") });

  const torso = loft([
    { z: 0.0, w: 0.33, h: 0.22, y: 0, p: 2.4 },
    { z: 0.12, w: 0.35, h: 0.235, y: 0.008, p: 2.4 },
    { z: 0.26, w: 0.41, h: 0.255, y: 0.016, p: 2.6 },
    { z: 0.36, w: 0.455, h: 0.245, y: 0.012, p: 2.8 },
    { z: 0.43, w: 0.43, h: 0.215, y: 0.004, p: 2.8 },
    { z: 0.48, w: 0.3, h: 0.17, y: 0, p: 2.4 },
    { z: 0.51, w: 0.15, h: 0.125, y: 0, p: 2.2 },
  ], 40, 70);
  torso.rotateX(-Math.PI / 2);
  d.add(new THREE.Mesh(torso, suitMat));

  // suit details
  put(d, new THREE.CylinderGeometry(0.17, 0.168, 0.045, 40), M.satin, 0, 0.05, 0).scale.z = 0.66;
  put(d, rbox(0.012, 0.36, 0.012, 0.004), M.steel, 0, 0.26, 0.128, -0.07);
  put(d, new THREE.CylinderGeometry(0.074, 0.086, 0.055, 32), M.white, 0, 0.51, 0);
  for (const sx of [-1, 1]) put(d, rbox(0.11, 0.012, 0.055, 0.005), M.white, sx * 0.16, 0.448, 0, 0, 0, -sx * 0.26);
  put(d, rbox(0.085, 0.045, 0.008, 0.003), M.white, 0.09, 0.36, 0.126, -0.13);
  put(d, rbox(0.3, 0.01, 0.006, 0.002), M.white, 0, 0.2, 0.118, -0.04);

  // neck and head in a balaclava with an eye opening
  put(d, new THREE.CylinderGeometry(0.054, 0.062, 0.1, 32), balaclava, 0, 0.565, 0);
  const head = put(d, new THREE.SphereGeometry(0.1, 48, 32), balaclava, 0, 0.665, 0);
  head.scale.set(0.86, 1.1, 0.97);
  const eyes = put(d, new THREE.SphereGeometry(0.1008, 32, 4, Math.PI / 2 - 0.62, 1.24, 1.38, 0.2), std("#8a6650", 0.6), 0, 0.665, 0);
  eyes.scale.copy(head.scale);

  const helmet = buildHelmet(0.155);
  d.add(helmet);

  // arms: shoulder, upper arm, elbow, forearm, cuff, glove
  const glove = new THREE.MeshPhysicalMaterial({ color: "#2a2a2a", roughness: 0.75, sheen: 0.3 });
  const arm = (sx) => {
    const parts = {
      shoulder: new THREE.Mesh(new THREE.SphereGeometry(0.054, 32, 20), suitMat),
      upper: new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.057, 1, 28), suitMat),
      elbow: new THREE.Mesh(new THREE.SphereGeometry(0.049, 28, 18), suitMat),
      fore: new THREE.Mesh(new THREE.CylinderGeometry(0.037, 0.047, 1, 28), suitMat),
      cuff: new THREE.Mesh(new THREE.CylinderGeometry(0.043, 0.043, 0.045, 28), glove),
      hand: new THREE.Group(),
    };
    put(parts.hand, rbox(0.032, 0.088, 0.082, 0.014, 3), glove);
    for (let i = 0; i < 4; i++) {
      const f = put(parts.hand, new THREE.CapsuleGeometry(0.0095, 0.045 - Math.abs(i - 1.5) * 0.006, 4, 10), glove, -sx * 0.013, 0.07, -0.029 + i * 0.0195);
      f.rotation.z = sx * 0.45;
    }
    const thumb = put(parts.hand, new THREE.CapsuleGeometry(0.01, 0.035, 4, 10), glove, -sx * 0.014, 0.004, 0.052);
    thumb.rotation.x = 0.7;
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
  d.userData.pose = (helmetY, spin = 0) => {
    helmet.position.set(0, helmetY, 0.005);
    helmet.rotation.set(0, spin, 0);
    for (const sx of [-1, 1]) {
      const p = arms[sx];
      const S = new THREE.Vector3(sx * 0.2, 0.425, -0.005);
      const H = new THREE.Vector3(sx * 0.178, helmetY - 0.06, 0.03);
      const toH = new THREE.Vector3().subVectors(H, S);
      const dist = Math.min(toH.length(), L1 + L2 - 1e-3);
      const dir = toH.normalize();
      const a = (L1 * L1 - L2 * L2 + dist * dist) / (2 * dist);
      const h = Math.sqrt(Math.max(L1 * L1 - a * a, 0));
      const pole = new THREE.Vector3(sx, -0.35, 0.45);
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
      p.hand.rotation.set(0, 0, sx * -0.15);
    }
  };
  d.userData.pose(0.9);
  return shadowed(d);
}

// A standing crew member in overalls. Faces +z. armsUp lifts both forearms.
export function buildPerson(color = "#3b3d40", pose = {}) {
  const p = new THREE.Group();
  const cloth = std(color, 0.85);
  const skin = std("#c9a58c", 0.7);
  for (const sx of [-1, 1]) {
    put(p, new THREE.CapsuleGeometry(0.075, 0.72, 6, 16), cloth, sx * 0.1, 0.46, 0);
    put(p, rbox(0.11, 0.07, 0.25, 0.03), M.satin, sx * 0.1, 0.035, 0.04);
  }
  put(p, new THREE.CapsuleGeometry(0.17, 0.42, 8, 20), cloth, 0, 1.15, 0).scale.set(1, 1, 0.66);
  put(p, new THREE.SphereGeometry(0.105, 32, 20), skin, 0, 1.66, 0);
  put(p, new THREE.SphereGeometry(0.112, 32, 12, 0, Math.PI * 2, 0, 1.4), std("#222", 0.6), 0, 1.68, -0.005); // cap/hair
  put(p, new THREE.CylinderGeometry(0.05, 0.055, 0.08, 16), skin, 0, 1.53, 0);
  for (const sx of [-1, 1]) {
    const arm = new THREE.Group();
    arm.position.set(sx * 0.22, 1.42, 0);
    put(arm, new THREE.CapsuleGeometry(0.055, 0.25, 6, 14), cloth, 0, -0.16, 0);
    const fore = new THREE.Group();
    fore.position.y = -0.32;
    put(fore, new THREE.CapsuleGeometry(0.048, 0.24, 6, 14), cloth, 0, -0.14, 0);
    put(fore, new THREE.SphereGeometry(0.05, 16, 12), std("#2a2a2a", 0.8), 0, -0.3, 0);
    fore.rotation.x = pose.forearm ?? -0.3;
    arm.add(fore);
    arm.rotation.z = sx * (pose.spread ?? 0.12);
    arm.rotation.x = pose.reach ?? 0;
    p.add(arm);
  }
  return shadowed(p);
}

// ---------------------------------------------------------------- circuit

export function buildTrack(scene) {
  const flat = (w, d, x, z, material, y = 0.003) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), material);
    m.rotation.x = -Math.PI / 2;
    m.position.set(x, y, z);
    m.receiveShadow = true;
    scene.add(m);
    return m;
  };
  const paintLine = std("#fbfbf9", 0.55);

  flat(600, 600, 0, 0, std(GROUND, 0.95), 0);
  flat(7.2, 260, 0, -60, std("#dcdcd8", 0.9), 0.001); // asphalt
  flat(0.13, 260, -3.45, -60, paintLine);
  flat(0.13, 260, 3.45, -60, paintLine);
  const rubber = new THREE.MeshStandardMaterial({ color: "#c9c9c5", roughness: 0.95, transparent: true, opacity: 0.65 });
  for (const x of [-1.5, 1.5]) for (const dx of [-0.87, 0.87]) flat(0.34, 260, x + dx, -60, rubber, 0.002);

  // grid slots with painted position numbers
  for (let i = -10; i <= 5; i++) {
    const x = i % 2 ? 1.5 : -1.5;
    const z = i * 7;
    flat(1.95, 0.1, x, z - 2.6, paintLine);
    flat(0.1, 0.85, x - 0.97, z - 2.2, paintLine);
    flat(0.1, 0.85, x + 0.97, z - 2.2, paintLine);
    const n = String(Math.abs(i) + 1);
    const tex = textTexture((g, w, h) => {
      g.clearRect(0, 0, w, h);
      g.fillStyle = "#fbfbf9";
      g.font = "900 200px Inter, sans-serif";
      g.textAlign = "center";
      g.textBaseline = "middle";
      g.fillText(n, w / 2, h / 2 + 10);
    });
    const num = flat(0.7, 0.7, x, z - 3.2, new THREE.MeshStandardMaterial({ map: tex, transparent: true, roughness: 0.6 }), 0.004);
  }

  // kerbs on the outside edge
  for (let z = -150; z < 60; z += 1.0) {
    const k = new THREE.Mesh(crease(rbox(0.6, 0.06, 1.0, 0.015)), std(Math.round(z) % 2 ? "#ffffff" : "#b9b9b5", 0.6));
    k.position.set(3.85, 0.03, z);
    k.receiveShadow = true;
    scene.add(k);
  }

  // pit wall, debris fence, then the pit lane and garages behind it
  const concrete = std("#d6d6d2", 0.85);
  scene.add(shadowed(put(new THREE.Group(), crease(rbox(0.5, 1.05, 220, 0.03)), concrete, -3.95, 0.525, -50)));
  const steel = std("#a9a9a5", 0.45, 0.6);
  for (let z = -160; z < 60; z += 2.5) scene.add(shadowed(rod(new THREE.Vector3(-3.95, 1.05, z), new THREE.Vector3(-3.95, 3.0, z), 0.04, steel, 12)));
  for (let y = 1.3; y <= 3.0; y += 0.12) scene.add(rod(new THREE.Vector3(-3.95, y, -160), new THREE.Vector3(-3.95, y, 60), 0.006, steel, 4));

  flat(9, 220, -9, -50, std("#d4d4d0", 0.9), 0.0015); // pit lane
  flat(0.12, 220, -6.2, -50, paintLine);
  const garages = new THREE.Group();
  const wallMat = std("#e2e2de", 0.8);
  const doorMat = std("#b4b4b0", 0.55, 0.3);
  for (let i = 0; i < 18; i++) {
    const z = -100 + i * 8;
    put(garages, crease(rbox(1.0, 5, 8, 0.03)), wallMat, -14.5, 2.5, z);
    put(garages, crease(rbox(0.4, 0.9, 7.2, 0.02)), wallMat, -14.1, 4.4, z + 4);
    const door = put(garages, rbox(0.08, 3.5, 6.6, 0.01), doorMat, -14.0, 1.75, z + 4);
    door.receiveShadow = true;
    for (let s = 0; s < 14; s++) put(garages, rbox(0.03, 0.02, 6.6, 0.005), std("#9c9c98", 0.5, 0.3), -13.95, 0.2 + s * 0.24, z + 4);
    put(garages, crease(rbox(0.6, 0.5, 7.4, 0.02)), std("#cfcfcb", 0.7), -13.9, 4.0, z + 4); // header board
  }
  put(garages, crease(rbox(10, 0.4, 150, 0.05)), wallMat, -19, 5.2, -36);
  scene.add(shadowed(garages));
  // tyre stacks and trolleys in the pit lane
  const tyreGeo = new THREE.TorusGeometry(0.27, 0.13, 12, 24);
  for (let i = 0; i < 10; i++) {
    const z = -40 + i * 9.5;
    for (let k = 0; k < 4; k++) {
      const t = put(scene, tyreGeo, M.rubber, -11.8, 0.13 + k * 0.26, z, Math.PI / 2);
      t.castShadow = t.receiveShadow = true;
    }
    scene.add(shadowed(put(new THREE.Group(), crease(rbox(0.6, 0.9, 1.1, 0.03)), std("#5a5c60", 0.5, 0.4), -12.6, 0.45, z + 2)));
  }

  // start-light gantry across the straight
  const gantry = new THREE.Group();
  for (const sx of [-1, 1]) put(gantry, crease(rbox(0.35, 6.4, 0.35, 0.03)), std("#cfcfcb", 0.6, 0.2), sx * 4.6, 3.2, 0);
  put(gantry, crease(rbox(9.6, 0.45, 0.5, 0.04)), std("#cfcfcb", 0.6, 0.2), 0, 6.2, 0);
  const lamp = new THREE.MeshStandardMaterial({ color: "#2a0606", emissive: "#ff1208", emissiveIntensity: 1.6, roughness: 0.3 });
  for (let i = 0; i < 5; i++) {
    put(gantry, crease(rbox(0.36, 0.9, 0.26, 0.04)), M.carbon, -1.0 + i * 0.5, 5.55, 0.18);
    for (const ly of [5.78, 5.4]) put(gantry, new THREE.CircleGeometry(0.11, 32), lamp, -1.0 + i * 0.5, ly, 0.315);
  }
  gantry.position.z = -16;
  scene.add(shadowed(gantry));

  // outside of the circuit: tyre barrier, advertising boards, grandstand with crowd, trees
  for (let z = -160; z < 60; z += 0.62) {
    for (let k = 0; k < 3; k++) {
      const t = put(scene, tyreGeo, M.rubber, 6.2, 0.13 + k * 0.26, z, Math.PI / 2);
      t.receiveShadow = true;
    }
  }
  const boardTones = ["#f6f6f4", "#d9d9d5", "#bfc1c3", "#f6f6f4"];
  for (let i = 0; i < 26; i++) {
    const z = -150 + i * 8;
    const b = put(scene, crease(rbox(0.12, 1.1, 7.6, 0.02)), std(boardTones[i % 4], 0.6), 6.9, 0.9, z);
    b.castShadow = b.receiveShadow = true;
    put(scene, rbox(0.02, 0.18, 4.6, 0.01), std(i % 2 ? "#2a2a2a" : "#8f9193", 0.5), 6.83, 0.95, z);
  }

  const stand = new THREE.Group();
  const terrace = std("#d4d4d0", 0.85);
  for (let i = 0; i < 14; i++) {
    const h = 0.6 + i * 0.55;
    put(stand, crease(rbox(1.1, h, 170, 0.02)), terrace, 12 + i * 1.1, h / 2, -45);
  }
  for (let z = -125; z < 40; z += 12) put(stand, crease(rbox(0.45, 11, 0.45, 0.03)), terrace, 27.6, 5.5, z);
  put(stand, crease(rbox(17, 0.35, 172, 0.05)), std("#dededa", 0.7), 19.5, 11.2, -45, 0, 0, 0.06);
  scene.add(shadowed(stand));

  // crowd: thousands of seated figures, one instanced mesh, seeded tones
  const fig = mergeGeometries([
    new THREE.CapsuleGeometry(0.17, 0.32, 3, 8).translate(0, 0.33, 0),
    new THREE.SphereGeometry(0.11, 10, 8).translate(0, 0.72, 0),
  ]);
  const rows = 14, perRow = 300;
  const crowd = new THREE.InstancedMesh(fig, std("#ffffff", 0.9), rows * perRow);
  let seed = 9;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  const dummy = new THREE.Object3D();
  const tones = ["#3c3e42", "#5b5d61", "#7d7f83", "#a5a7aa", "#cfd0d2", "#f0f0ee", "#2b2c2e"];
  let n = 0;
  for (let r = 0; r < rows; r++) {
    for (let k = 0; k < perRow; k++) {
      if (rnd() < 0.18) continue; // empty seats
      dummy.position.set(12 + r * 1.1 - 0.15, 0.6 + r * 0.55, -128 + k * 0.56 + rnd() * 0.12);
      dummy.rotation.set(0, -Math.PI / 2 + (rnd() - 0.5) * 0.5, 0);
      dummy.scale.setScalar(0.9 + rnd() * 0.2);
      dummy.updateMatrix();
      crowd.setMatrixAt(n, dummy.matrix);
      crowd.setColorAt(n, new THREE.Color(tones[Math.floor(rnd() * tones.length)]));
      n++;
    }
  }
  crowd.count = n;
  crowd.castShadow = true;
  scene.add(crowd);

  const treeMat = std("#c9cec4", 0.95);
  for (let i = 0; i < 40; i++) {
    const z = -160 + i * 5.5 + rnd() * 2;
    const s = 3 + rnd() * 2.5;
    const t = put(scene, new THREE.IcosahedronGeometry(s, 2), treeMat, 33 + rnd() * 6, s * 1.4, z);
    t.scale.set(1, 1.3, 1);
    t.castShadow = true;
  }
}

// ---------------------------------------------------------------- garage set (shot 2 backdrop)

export function buildGarage(scene, x0) {
  const g = new THREE.Group();
  g.position.x = x0;
  const floor = put(g, new THREE.PlaneGeometry(14, 14), std("#5f6064", 0.35, 0.1), 0, 0, -2, -Math.PI / 2);
  floor.receiveShadow = true;
  put(g, new THREE.PlaneGeometry(14, 6), std("#3c3d40", 0.8), 0, 3, -4.5);
  for (const sx of [-1, 1]) put(g, new THREE.PlaneGeometry(14, 6), std("#36373a", 0.85), sx * 4.5, 3, -2, 0, -sx * Math.PI / 2);
  // tool wall: pegboard panel with hanging tools, a roller cabinet beneath
  put(g, crease(rbox(3.2, 1.6, 0.05, 0.01)), std("#4a4b4f", 0.6), -1.6, 1.9, -4.45);
  for (let i = 0; i < 9; i++) put(g, crease(rbox(0.05, 0.35 + (i % 3) * 0.12, 0.03, 0.01)), M.steel, -2.9 + i * 0.32, 2.0, -4.4);
  put(g, crease(rbox(2.2, 1.0, 0.6, 0.03)), std("#2c2d30", 0.4, 0.3), -1.6, 0.5, -4.1);
  for (let i = 0; i < 5; i++) put(g, rbox(2.1, 0.012, 0.01, 0.004), M.steel, -1.6, 0.2 + i * 0.18, -3.795);
  // tyre stacks and an overhead strip light
  const tyreGeo = new THREE.TorusGeometry(0.3, 0.14, 16, 32);
  for (const [tx, tz] of [[2.6, -3.6], [3.3, -2.8]]) for (let k = 0; k < 4; k++) put(g, tyreGeo, M.rubber, tx, 0.14 + k * 0.28, tz, Math.PI / 2);
  put(g, rbox(2.4, 0.06, 0.25, 0.02), new THREE.MeshStandardMaterial({ color: "#ffffff", emissive: "#ffffff", emissiveIntensity: 2.5 }), 0, 4.2, -2.5);
  scene.add(shadowed(g));
  return g;
}
