// People for the Lauda films: an anatomical head, lofted torso and limbs, jointed hands and
// fabric-textured clothing. buildDriver() is the waist-up driver who pulls his helmet on;
// buildPerson() is a full-height crew member in overalls.
import * as THREE from "three";
import { loft, crease, rbox, shadowed, std, ACCENT } from "./models.js";
import { buildHelmet } from "./models.js";

const lerp = (a, b, k) => a + (b - a) * k;
const gauss = (dx, dy, sx, sy) => Math.exp(-((dx / sx) ** 2 + (dy / sy) ** 2));

// ---------------------------------------------------------------- fabric texture

let fabricTex = null;
function fabricBump() {
  if (fabricTex) return fabricTex;
  const S = 512;
  const c = document.createElement("canvas");
  c.width = c.height = S;
  const g = c.getContext("2d");
  const img = g.createImageData(S, S);
  let seed = 11;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  // tileable value noise at two scales + a fine twill weave
  const grid = (n) => Array.from({ length: n * n }, rnd);
  const g1 = grid(8), g2 = grid(32);
  const sample = (gr, n, x, y) => {
    const fx = (x / S) * n, fy = (y / S) * n;
    const x0 = Math.floor(fx), y0 = Math.floor(fy);
    const tx = fx - x0, ty = fy - y0;
    const at = (i, j) => gr[((j % n) + n) % n * n + (((i % n) + n) % n)];
    const sx = tx * tx * (3 - 2 * tx), sy = ty * ty * (3 - 2 * ty);
    return lerp(lerp(at(x0, y0), at(x0 + 1, y0), sx), lerp(at(x0, y0 + 1), at(x0 + 1, y0 + 1), sx), sy);
  };
  for (let y = 0; y < S; y++) {
    for (let x = 0; x < S; x++) {
      const folds = sample(g1, 8, x, y) * 0.55 + sample(g2, 32, x, y) * 0.25;
      const weave = ((x + y) % 4 < 2 ? 0.12 : 0) + ((x - y + S) % 6 < 1 ? 0.05 : 0);
      const v = Math.min(255, Math.max(0, (folds + weave) * 255));
      const i = (y * S + x) * 4;
      img.data[i] = img.data[i + 1] = img.data[i + 2] = v;
      img.data[i + 3] = 255;
    }
  }
  g.putImageData(img, 0, 0);
  fabricTex = new THREE.CanvasTexture(c);
  fabricTex.wrapS = fabricTex.wrapT = THREE.RepeatWrapping;
  fabricTex.repeat.set(3, 3);
  return fabricTex;
}

function cloth(color, sheenColor = "#ffffff", roughness = 0.85) {
  return new THREE.MeshPhysicalMaterial({
    color,
    roughness,
    sheen: 0.5,
    sheenRoughness: 0.7,
    sheenColor: new THREE.Color(sheenColor),
    bumpMap: fabricBump(),
    bumpScale: 0.35,
  });
}
const skinMat = () => new THREE.MeshPhysicalMaterial({ color: "#c4977b", roughness: 0.52, sheen: 0.25, sheenColor: new THREE.Color("#ffd9c4") });

// ---------------------------------------------------------------- anatomy

// Head shaped from a dense sphere: narrow sides, tapered jaw and chin, fuller cranium,
// brow ridge, cheekbones, eye sockets and a nose. Faces +z, ~0.24 m tall.
export function headGeometry(r = 0.1, detail = 1, colorAt = null) {
  const g = new THREE.SphereGeometry(r, 72 * detail, 56 * detail);
  const p = g.attributes.position;
  const v = new THREE.Vector3();
  const colors = colorAt ? new Float32Array(p.count * 3) : null;
  for (let i = 0; i < p.count; i++) {
    v.fromBufferAttribute(p, i).divideScalar(r);
    const { x, y, z } = v;
    if (colors) colorAt(x, y, z).toArray(colors, i * 3);
    let sx = 0.8, sy = 1.08, sz = 0.98;
    if (y < -0.25) {
      const k = Math.min(1, (-y - 0.25) / 0.75);
      sx *= lerp(1, 0.66, k * k); // jaw narrows to the chin
      sz *= lerp(1, z > 0 ? 1.04 : 0.8, k);
    }
    if (z < 0 && y > -0.2) sz *= 1.06; // occiput
    if (y > 0.5) sx *= lerp(1, 0.93, (y - 0.5) / 0.5);
    let bump = 0;
    if (z > 0) {
      bump += 0.2 * gauss(x, y + 0.14, 0.1, 0.24) * z; // nose
      bump += 0.08 * gauss(x, y + 0.36, 0.07, 0.05) * z; // nose tip / philtrum
      bump += 0.05 * gauss(x, y - 0.24, 0.5, 0.07) * z; // brow ridge
      bump -= 0.06 * (gauss(x - 0.33, y - 0.08, 0.13, 0.09) + gauss(x + 0.33, y - 0.08, 0.13, 0.09)) * z; // eye sockets
      bump += 0.05 * (gauss(x - 0.58, y + 0.12, 0.16, 0.12) + gauss(x + 0.58, y + 0.12, 0.16, 0.12)); // cheekbones
      bump += 0.04 * gauss(x, y + 0.82, 0.18, 0.1) * z; // chin
      bump += 0.025 * gauss(x, y + 0.56, 0.22, 0.05) * z; // lips
    }
    p.setXYZ(i, x * sx * r * (1 + bump), y * sy * r * (1 + bump * 0.3), z * sz * r * (1 + bump));
  }
  if (colors) g.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  g.computeVertexNormals();
  return g;
}

// A limb segment lofted along +y from 0 to 1 (scale y to its length). Sections give the
// cross-section width (x) and depth (z) at fraction t, with an optional forward bulge.
function limbGeometry(sections, n = 28) {
  const geo = loft(sections.map((s) => ({ z: s.t, w: s.w, h: s.d, y: -(s.f ?? 0), p: 2.3 })), n, 80);
  geo.rotateX(-Math.PI / 2); // loft z → +y, loft y → −z
  return geo;
}

const UPPER_ARM = [
  { t: 0, w: 0.1, d: 0.1 },
  { t: 0.3, w: 0.098, d: 0.104, f: 0.008 },
  { t: 0.62, w: 0.088, d: 0.09, f: 0.004 },
  { t: 1, w: 0.078, d: 0.076 },
];
const FOREARM = [
  { t: 0, w: 0.08, d: 0.076 },
  { t: 0.22, w: 0.088, d: 0.08 },
  { t: 0.6, w: 0.07, d: 0.062 },
  { t: 1, w: 0.058, d: 0.044 },
];
const THIGH = [
  { t: 0, w: 0.19, d: 0.19 },
  { t: 0.35, w: 0.17, d: 0.175, f: 0.01 },
  { t: 0.8, w: 0.115, d: 0.12 },
  { t: 1, w: 0.105, d: 0.11 },
];
const CALF = [
  { t: 0, w: 0.105, d: 0.11 },
  { t: 0.3, w: 0.11, d: 0.12, f: -0.012 },
  { t: 0.75, w: 0.075, d: 0.08 },
  { t: 1, w: 0.065, d: 0.07 },
];

const Y = new THREE.Vector3(0, 1, 0);
function place(mesh, a, b) {
  const dir = new THREE.Vector3().subVectors(b, a);
  mesh.position.copy(a);
  mesh.scale.set(1, dir.length(), 1);
  mesh.quaternion.setFromUnitVectors(Y, dir.normalize());
}

// Two-bone IK: elbow/knee position for root S reaching target H, bent toward `pole`.
function solve(S, H, L1, L2, pole) {
  const toH = new THREE.Vector3().subVectors(H, S);
  const dist = Math.min(toH.length(), L1 + L2 - 1e-4);
  const dir = toH.normalize();
  const a = (L1 * L1 - L2 * L2 + dist * dist) / (2 * dist);
  const h = Math.sqrt(Math.max(L1 * L1 - a * a, 0));
  const pp = pole.clone().addScaledVector(dir, -pole.dot(dir)).normalize();
  return { E: S.clone().addScaledVector(dir, a).addScaledVector(pp, h), end: S.clone().addScaledVector(dir, dist) };
}

// Gloved or bare hand. Palm faces −x·side; fingers point +y and curl by `curl` (radians/joint).
function buildHand(material, side, curl = 0.55) {
  const hand = new THREE.Group();
  const palm = new THREE.Mesh(crease(rbox(0.03, 0.09, 0.084, 0.013, 4), 60), material);
  hand.add(palm);
  const lens = [0.044, 0.05, 0.047, 0.038];
  for (let f = 0; f < 4; f++) {
    let parent = new THREE.Group();
    parent.position.set(0, 0.045, -0.03 + f * 0.0198);
    hand.add(parent);
    let L = lens[f];
    for (let j = 0; j < 3; j++) {
      const seg = new THREE.Group();
      seg.rotation.z = side * curl * (j === 0 ? 0.7 : 1);
      const bone = new THREE.Mesh(new THREE.CapsuleGeometry(0.0092 - j * 0.0009, L * 0.42, 6, 12), material);
      bone.position.y = L * 0.25;
      seg.add(bone);
      parent.add(seg);
      const next = new THREE.Group();
      next.position.y = L * 0.5;
      seg.add(next);
      parent = next;
      L *= 0.72;
    }
  }
  const thumb = new THREE.Group();
  thumb.position.set(-side * 0.008, -0.01, 0.045);
  thumb.rotation.set(0.9, 0, side * 0.5);
  const t1 = new THREE.Mesh(new THREE.CapsuleGeometry(0.011, 0.028, 6, 12), material);
  t1.position.y = 0.02;
  thumb.add(t1);
  const t2 = new THREE.Mesh(new THREE.CapsuleGeometry(0.0095, 0.022, 6, 12), material);
  t2.position.set(0, 0.045, 0.004);
  t2.rotation.x = 0.3;
  thumb.add(t2);
  hand.add(thumb);
  return hand;
}

// ---------------------------------------------------------------- driver

// Driver from the waist up in a race suit and balaclava, facing +z.
// userData.pose(helmetY, spin) seats the helmet and solves both arms onto it.
export function buildDriver(suitColor = ACCENT) {
  const d = new THREE.Group();
  const suit = cloth(suitColor, "#ff9a9a", 0.8);
  const knit = cloth("#ecebe7", "#ffffff", 0.95);
  const glove = cloth("#262626", "#888888", 0.8);
  const white = std("#f2f2ef", 0.6);

  const torso = loft([
    { z: 0.0, w: 0.33, h: 0.21, y: 0, p: 2.4 },
    { z: 0.1, w: 0.34, h: 0.215, y: -0.005, p: 2.4 },
    { z: 0.2, w: 0.37, h: 0.235, y: -0.012, p: 2.5 },
    { z: 0.28, w: 0.41, h: 0.25, y: -0.02, p: 2.6 },
    { z: 0.35, w: 0.445, h: 0.245, y: -0.015, p: 2.7 },
    { z: 0.4, w: 0.46, h: 0.222, y: -0.005, p: 2.8 },
    { z: 0.445, w: 0.42, h: 0.19, y: 0.005, p: 2.6 },
    { z: 0.48, w: 0.3, h: 0.15, y: 0.008, p: 2.4 },
    { z: 0.515, w: 0.15, h: 0.12, y: 0.01, p: 2.2 },
  ], 48, 80);
  torso.rotateX(-Math.PI / 2);
  d.add(new THREE.Mesh(torso, suit));

  // suit details: belt with buckle, zip, quilted shoulder seams, epaulettes, chest patch, collar
  const belt = new THREE.Mesh(new THREE.CylinderGeometry(0.176, 0.174, 0.05, 48), cloth("#1d1d1d", "#666", 0.7));
  belt.scale.z = 0.64;
  belt.position.y = 0.05;
  d.add(belt);
  const buckle = new THREE.Mesh(crease(rbox(0.06, 0.04, 0.01, 0.004)), std("#b9b9b4", 0.3, 1));
  buckle.position.set(0, 0.05, 0.108);
  d.add(buckle);
  const zip = new THREE.Mesh(rbox(0.01, 0.38, 0.01, 0.003), std("#a8a8a3", 0.35, 1));
  zip.position.set(0, 0.27, 0.127);
  zip.rotation.x = -0.08;
  d.add(zip);
  for (const sx of [-1, 1]) {
    const ep = new THREE.Mesh(crease(rbox(0.11, 0.01, 0.05, 0.004)), white);
    ep.position.set(sx * 0.16, 0.452, 0.005);
    ep.rotation.z = -sx * 0.27;
    d.add(ep);
  }
  const patch = new THREE.Mesh(crease(rbox(0.085, 0.045, 0.006, 0.003)), white);
  patch.position.set(0.095, 0.37, 0.124);
  patch.rotation.x = -0.14;
  d.add(patch);
  const collar = new THREE.Mesh(new THREE.CylinderGeometry(0.074, 0.086, 0.06, 40, 1, true), cloth("#f0f0ec", "#fff", 0.85));
  collar.material.side = THREE.DoubleSide;
  collar.position.y = 0.515;
  d.add(collar);

  // neck and head under a knitted balaclava; real eyes in the opening
  const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.052, 0.06, 0.11, 32), knit);
  neck.position.y = 0.565;
  d.add(neck);
  // knit balaclava with the eye opening coloured in as skin
  const knitWhite = new THREE.Color("#ecebe7"), skinTone = new THREE.Color("#b98a6e");
  const hood = cloth("#ffffff", "#ffffff", 0.95);
  hood.vertexColors = true;
  const head = new THREE.Mesh(
    headGeometry(0.1, 1, (x, y, z) => (z > 0.45 && Math.abs(y - 0.07) < 0.13 && Math.abs(x) < 0.55 ? skinTone : knitWhite)),
    hood,
  );
  head.position.set(0, 0.665, 0);
  d.add(head);
  for (const sx of [-1, 1]) {
    const eye = new THREE.Group();
    const ball = new THREE.Mesh(new THREE.SphereGeometry(0.0115, 24, 16), std("#f4f1ea", 0.2));
    const iris = new THREE.Mesh(new THREE.SphereGeometry(0.0062, 20, 12), std("#3b2a20", 0.15));
    iris.position.z = 0.0072;
    const pupil = new THREE.Mesh(new THREE.SphereGeometry(0.0032, 12, 8), std("#050505", 0.05));
    pupil.position.z = 0.0105;
    eye.add(ball, iris, pupil);
    eye.position.set(sx * 0.032, 0.673, 0.074);
    d.add(eye);
  }

  const helmet = buildHelmet(0.155);
  d.add(helmet);

  // arms
  const arms = {};
  for (const sx of [-1, 1]) {
    const a = {
      upper: new THREE.Mesh(limbGeometry(UPPER_ARM), suit),
      elbow: new THREE.Mesh(new THREE.SphereGeometry(0.041, 28, 20), suit),
      fore: new THREE.Mesh(limbGeometry(FOREARM), suit),
      cuff: new THREE.Mesh(new THREE.CylinderGeometry(0.036, 0.034, 0.06, 28), glove),
      hand: buildHand(glove, sx, 0.62),
    };
    Object.values(a).forEach((m) => d.add(m));
    arms[sx] = a;
  }

  const L1 = 0.31, L2 = 0.26;
  d.userData.pose = (helmetY, spin = 0) => {
    helmet.position.set(0, helmetY, 0.005);
    helmet.rotation.set(0, spin, 0);
    for (const sx of [-1, 1]) {
      const a = arms[sx];
      const S = new THREE.Vector3(sx * 0.165, 0.41, -0.005);
      const H = new THREE.Vector3(sx * 0.18, helmetY - 0.065, 0.025);
      const { E, end } = solve(S, H, L1, L2, new THREE.Vector3(sx, -0.4, 0.4));
      place(a.upper, S, E);
      a.elbow.position.copy(E);
      const wrist = E.clone().lerp(end, 0.88);
      place(a.fore, E, wrist);
      a.cuff.position.copy(wrist);
      a.cuff.quaternion.copy(a.fore.quaternion);
      a.hand.position.copy(end).add(new THREE.Vector3(0, 0.015, 0));
      a.hand.rotation.set(0, 0, sx * -0.12);
    }
  };
  d.userData.pose(0.9);
  return shadowed(d);
}

// ---------------------------------------------------------------- crew

// Full-height crew member in overalls, facing +z, feet at y = 0.
// pose: { reach: forward lift of the arms, bend: elbow bend, spread: arms out, lean }
export function buildPerson(color = "#3b3d40", pose = {}) {
  const p = new THREE.Group();
  const overall = cloth(color, "#9aa0a6", 0.88);
  const skin = skinMat();
  const boot = std("#1a1a1a", 0.45, 0.1);

  // legs: hip → knee → ankle, slight stance
  for (const sx of [-1, 1]) {
    const hip = new THREE.Vector3(sx * 0.1, 0.93, 0);
    const knee = new THREE.Vector3(sx * 0.11, 0.5, 0.025);
    const ankle = new THREE.Vector3(sx * 0.115, 0.09, 0);
    const thigh = new THREE.Mesh(limbGeometry(THIGH), overall);
    place(thigh, hip, knee);
    const calf = new THREE.Mesh(limbGeometry(CALF), overall);
    place(calf, knee, ankle);
    const shoe = new THREE.Mesh(crease(rbox(0.095, 0.075, 0.25, 0.032, 4), 50), boot);
    shoe.position.set(sx * 0.115, 0.045, 0.045);
    const sole = new THREE.Mesh(rbox(0.1, 0.016, 0.26, 0.007), std("#0d0d0d", 0.8));
    sole.position.set(sx * 0.115, 0.008, 0.045);
    p.add(thigh, calf, shoe, sole);
  }

  // pelvis + torso
  const body = loft([
    { z: 0.86, w: 0.34, h: 0.22, y: 0, p: 2.4 },
    { z: 0.98, w: 0.33, h: 0.21, y: 0, p: 2.4 },
    { z: 1.1, w: 0.33, h: 0.21, y: -0.005, p: 2.4 },
    { z: 1.22, w: 0.37, h: 0.23, y: -0.015, p: 2.5 },
    { z: 1.32, w: 0.41, h: 0.24, y: -0.018, p: 2.6 },
    { z: 1.4, w: 0.44, h: 0.22, y: -0.008, p: 2.8 },
    { z: 1.45, w: 0.4, h: 0.19, y: 0, p: 2.6 },
    { z: 1.49, w: 0.27, h: 0.15, y: 0.005, p: 2.4 },
    { z: 1.52, w: 0.13, h: 0.11, y: 0.01, p: 2.2 },
  ], 40, 80);
  body.rotateX(-Math.PI / 2);
  p.add(new THREE.Mesh(body, overall));
  // overall details: belt, chest pockets, zip, collar
  const belt = new THREE.Mesh(new THREE.CylinderGeometry(0.178, 0.178, 0.05, 40), std("#151515", 0.5));
  belt.scale.z = 0.65;
  belt.position.y = 1.0;
  p.add(belt);
  for (const sx of [-1, 1]) {
    const pocket = new THREE.Mesh(crease(rbox(0.1, 0.11, 0.012, 0.006)), overall);
    pocket.position.set(sx * 0.1, 1.3, 0.118);
    pocket.rotation.x = -0.1;
    const flap = new THREE.Mesh(crease(rbox(0.105, 0.03, 0.014, 0.005)), overall);
    flap.position.set(sx * 0.1, 1.355, 0.12);
    p.add(pocket, flap);
  }
  const zip = new THREE.Mesh(rbox(0.008, 0.5, 0.008, 0.003), std("#9a9a96", 0.35, 1));
  zip.position.set(0, 1.25, 0.122);
  p.add(zip);
  const collar = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.085, 0.05, 32, 1, true), overall);
  collar.position.y = 1.52;
  p.add(collar);

  // neck, head, hair, ears — or a knitted balaclava for a driver
  const knit = cloth("#ecebe7", "#ffffff", 0.95);
  const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.057, 0.12, 28), pose.balaclava ? knit : skin);
  neck.position.y = 1.57;
  p.add(neck);
  if (pose.balaclava) {
    const knitWhite = new THREE.Color("#ecebe7"), skinTone = new THREE.Color("#b98a6e");
    const hood = cloth("#ffffff", "#ffffff", 0.95);
    hood.vertexColors = true;
    const head = new THREE.Mesh(
      headGeometry(0.1, 0.8, (x, y, z) => (z > 0.45 && Math.abs(y - 0.07) < 0.13 && Math.abs(x) < 0.55 ? skinTone : knitWhite)),
      hood,
    );
    head.position.set(0, 1.71, 0.01);
    p.add(head);
  } else {
    const head = new THREE.Mesh(headGeometry(0.1, 0.7), skin);
    head.position.set(0, 1.71, 0.01);
    const hair = new THREE.Mesh(new THREE.SphereGeometry(0.104, 48, 24, 0, Math.PI * 2, 0, 1.55), cloth("#2a221d", "#5a4a40", 0.9));
    hair.scale.set(0.82, 1.06, 1.02);
    hair.position.set(0, 1.725, 0.002);
    hair.rotation.x = -0.25;
    p.add(head, hair);
    for (const sx of [-1, 1]) {
      const ear = new THREE.Mesh(new THREE.SphereGeometry(0.03, 16, 12), skin);
      ear.scale.set(0.35, 1, 0.7);
      ear.position.set(sx * 0.08, 1.705, -0.005);
      p.add(ear);
    }
  }

  // arms hanging or reaching
  const hands = {};
  for (const sx of [-1, 1]) {
    const S = new THREE.Vector3(sx * 0.175, 1.415, -0.005);
    const ap = { ...pose, ...(pose.arms?.[sx] ?? {}) };
    const reach = ap.reach ?? 0.1;
    const bend = ap.bend ?? 0.25;
    const spread = ap.spread ?? 0.1;
    const upperDir = new THREE.Vector3(sx * Math.sin(spread), -Math.cos(reach), Math.sin(reach)).normalize();
    const E = S.clone().addScaledVector(upperDir, 0.29);
    const foreDir = upperDir.clone().applyAxisAngle(new THREE.Vector3(1, 0, 0), -bend).normalize();
    const W = E.clone().addScaledVector(foreDir, 0.25);
    const upper = new THREE.Mesh(limbGeometry(UPPER_ARM), overall);
    place(upper, S, E);
    const elbow = new THREE.Mesh(new THREE.SphereGeometry(0.036, 24, 16), overall);
    elbow.position.copy(E);
    const fore = new THREE.Mesh(limbGeometry(FOREARM), overall);
    place(fore, E, W);
    const hand = buildHand(pose.gloves ? cloth("#262626", "#888888", 0.8) : skin, sx, ap.grip ?? 0.35);
    hand.position.copy(W).addScaledVector(foreDir, 0.05);
    hand.quaternion.setFromUnitVectors(Y, foreDir);
    hands[sx] = hand.position.clone();
    p.add(upper, elbow, fore, hand);
  }
  p.userData.hands = hands;
  if (pose.lean) p.rotation.x = pose.lean;
  return shadowed(p);
}
