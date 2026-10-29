// The four 3D sets of the v3 short, each in its own region of one scene so a shot can show one
// set and hide the rest: Fuji in the rain (origin), the Nürburgring (x = 600), the hospital
// (x = 1200) and Monza in the sun (x = 1800). Built from the shared realistic models.
import * as THREE from "three";
import { Reflector } from "three/addons/objects/Reflector.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { ACCENT, RIVAL, buildCar, buildHelmet, buildTrack, std, paint, rbox, crease, rod, shadowed } from "./models.js";
import { buildPerson, buildDriver, headGeometry } from "./humans.js";

export const RING_X = 600, HOSP_X = 1200, MONZA_X = 1800;
const seeded = (s) => () => ((s = (s * 16807) % 2147483647) / 2147483647);
const hash = (a, b) => { let h = (a * 374761393 + b * 668265263) | 0; h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967296; };
const at = (m, x, y, z) => (m.position.set(x, y, z), m);
const canvasTex = (w, h, draw) => {
  const c = document.createElement("canvas"); c.width = w; c.height = h;
  draw(c.getContext("2d"), w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
  return t;
};

// ------------------------------------------------------------------ rain (moves with the camera)

export function buildRain(count = 9000) {
  const g = new THREE.Group();
  const geo = new THREE.BoxGeometry(0.004, 0.5, 0.004);
  const mat = new THREE.MeshBasicMaterial({ color: "#dfe7ee", transparent: true, opacity: 0.2, depthWrite: false });
  const r = seeded(77);
  const dm = new THREE.Object3D();
  for (let copy = 0; copy < 2; copy++) { // two stacked volumes so the fall can wrap seamlessly
    const m = new THREE.InstancedMesh(geo, mat, count);
    for (let i = 0; i < count; i++) {
      const d = 1.2 + Math.pow(r(), 1.3) * 26, a = (r() - 0.5) * 1.6;
      dm.position.set(Math.sin(a) * d, r() * 12, -Math.cos(a) * d);
      dm.rotation.set(0.05, 0, 0.12);
      dm.updateMatrix();
      m.setMatrixAt(i, dm.matrix);
    }
    m.position.y = copy * 12;
    g.add(m);
  }
  g.userData.update = (cam, t) => {
    g.position.set(cam.position.x, cam.position.y - 6 - ((t * 9) % 12), cam.position.z);
    g.rotation.y = Math.atan2(-(cam.userData.look?.x - cam.position.x || 0), -(cam.userData.look?.z - cam.position.z || -1)) ;
  };
  return g;
}

// ------------------------------------------------------------------ Fuji, in the rain

export function buildFujiSet(W, H) {
  const set = new THREE.Group();
  const r = seeded(1976);
  const mirror = new Reflector(new THREE.PlaneGeometry(90, 160), { textureWidth: W / 2, textureHeight: H / 2, color: 0x3a3f44, clipBias: 0.002 });
  mirror.rotation.x = -Math.PI / 2;
  mirror.position.set(0, 0, -40);
  set.add(mirror);
  const puddles = canvasTex(1024, 1024, (g, S) => {
    g.fillStyle = "rgb(205,205,205)"; g.fillRect(0, 0, S, S);
    for (let i = 0; i < 70; i++) {
      const x = r() * S, y = r() * S, rr = 20 + r() * 110;
      const rg = g.createRadialGradient(x, y, rr * 0.2, x, y, rr);
      rg.addColorStop(0, "rgba(150,150,150,1)"); rg.addColorStop(0.7, "rgba(170,170,170,0.9)"); rg.addColorStop(1, "rgba(205,205,205,0)");
      g.fillStyle = rg; g.beginPath(); g.ellipse(x, y, rr * (1 + r()), rr, r() * 3, 0, Math.PI * 2); g.fill();
    }
    const img = g.getImageData(0, 0, S, S);
    for (let i = 0; i < img.data.length; i += 4) { const n = (r() - 0.5) * 40; img.data[i] = img.data[i + 1] = img.data[i + 2] = Math.max(0, Math.min(255, img.data[i] + n)); }
    g.putImageData(img, 0, 0);
  });
  puddles.colorSpace = THREE.NoColorSpace;
  puddles.wrapS = puddles.wrapT = THREE.RepeatWrapping; puddles.repeat.set(5, 9);
  const asphalt = new THREE.Mesh(new THREE.PlaneGeometry(90, 160), new THREE.MeshPhysicalMaterial({ color: "#2c2e31", roughness: 0.5, clearcoat: 0.25, clearcoatRoughness: 0.3, envMapIntensity: 0.2, alphaMap: puddles, transparent: true, bumpMap: puddles, bumpScale: 0.6, depthWrite: false }));
  asphalt.rotation.x = -Math.PI / 2; asphalt.position.set(0, 0.003, -40); asphalt.receiveShadow = true;
  set.add(asphalt);
  const paintM = new THREE.MeshPhysicalMaterial({ color: "#d9dbdc", roughness: 0.35, clearcoat: 0.8, transparent: true, opacity: 0.85 });
  const line = (w, d, x, z) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), paintM); m.rotation.x = -Math.PI / 2; m.position.set(x, 0.005, z); set.add(m); };
  line(0.14, 160, -4.2, -40); line(0.14, 160, 3.9, -40); line(0.14, 160, 12.0, -40);
  for (let z = -110; z < 30; z += 3) line(0.12, 1.4, -1.2, z);
  // finish line across the track (chequered)
  const chk = canvasTex(256, 32, (g) => { for (let y = 0; y < 2; y++) for (let x = 0; x < 16; x++) { g.fillStyle = (x + y) % 2 ? "#111" : "#eee"; g.fillRect(x * 16, y * 16, 16, 16); } });
  const fin = new THREE.Mesh(new THREE.PlaneGeometry(8, 1), new THREE.MeshStandardMaterial({ map: chk, roughness: 0.4 }));
  fin.rotation.x = -Math.PI / 2; fin.position.set(8, 0.006, -14); set.add(fin);
  // pit wall, debris fence, pit board
  const concrete = new THREE.MeshPhysicalMaterial({ color: "#8d9093", roughness: 0.5, clearcoat: 0.4 });
  set.add(shadowed(at(new THREE.Mesh(crease(rbox(0.5, 1.05, 160, 0.03)), concrete), 3.0, 0.525, -40)));
  const steel = std("#6e7276", 0.35, 0.8);
  for (let z = -120; z < 30; z += 2.5) set.add(shadowed(rod(new THREE.Vector3(3, 1.05, z), new THREE.Vector3(3, 3.2, z), 0.045, steel, 12)));
  for (let y = 1.25; y <= 3.2; y += 0.11) set.add(rod(new THREE.Vector3(3, y, -120), new THREE.Vector3(3, y, 30), 0.006, steel, 4));
  // kerbs, tyre barrier, grandstand with crowd and umbrellas
  for (let z = -120; z < 30; z += 1) set.add(at(new THREE.Mesh(crease(rbox(0.7, 0.06, 1, 0.015)), new THREE.MeshPhysicalMaterial({ color: Math.round(z) % 2 ? "#e9e9e6" : "#55585c", roughness: 0.35, clearcoat: 0.8 })), 12.4, 0.03, z));
  const tyreGeo = new THREE.TorusGeometry(0.28, 0.13, 12, 24), tyreMat = std("#131313", 0.75);
  const tyres = new THREE.InstancedMesh(tyreGeo, tyreMat, 700); const dm = new THREE.Object3D(); let n = 0;
  for (let z = -120; z < 30 && n < 700; z += 0.64) for (let k = 0; k < 3 && n < 700; k++) { dm.position.set(13.6, 0.13 + k * 0.26, z); dm.rotation.set(Math.PI / 2, 0, 0); dm.updateMatrix(); tyres.setMatrixAt(n++, dm.matrix); }
  tyres.count = n; set.add(tyres);
  const stand = new THREE.Group();
  for (let i = 0; i < 14; i++) { const h = 0.8 + i * 0.6; stand.add(at(new THREE.Mesh(crease(rbox(1.2, h, 150, 0.02)), std("#73787d", 0.8)), 17 + i * 1.2, h / 2, -45)); }
  stand.add(at(new THREE.Mesh(crease(rbox(19, 0.4, 152, 0.05)), std("#5d6267", 0.6)), 25.5, 12.5, -45));
  const umb = new THREE.InstancedMesh(new THREE.SphereGeometry(0.45, 10, 4, 0, Math.PI * 2, 0, 1.0), std("#ffffff", 0.5), 1600);
  const tones = ["#1b1d22", "#2d3e5c", "#6a2a2a", "#3f5a3a", "#c9b04a", "#d0d4d8", "#3a3d44"];
  for (let i = 0; i < 1600; i++) { const row = i % 14; dm.position.set(17 + row * 1.2, 0.8 + row * 0.6 + 1.2, -118 + Math.floor(i / 14) * 1.3 + r() * 0.4); dm.rotation.set(0, 0, 0); dm.scale.setScalar(0.8 + r() * 0.4); dm.updateMatrix(); umb.setMatrixAt(i, dm.matrix); umb.setColorAt(i, new THREE.Color(tones[Math.floor(r() * tones.length)])); }
  dm.scale.setScalar(1);
  stand.add(umb);
  set.add(shadowed(stand));
  // garages with warm lit interiors
  const facade = new THREE.MeshPhysicalMaterial({ color: "#a7aaad", roughness: 0.6, clearcoat: 0.2 });
  const warm = new THREE.MeshStandardMaterial({ color: "#3a2a1a", emissive: "#ffcf96", emissiveIntensity: 1.6 });
  for (let i = 0; i < 16; i++) {
    const z = -80 + i * 6.5;
    set.add(at(new THREE.Mesh(crease(rbox(0.8, 4.6, 1.2, 0.03)), facade), -7.4, 2.3, z));
    const back = at(new THREE.Mesh(new THREE.PlaneGeometry(5.2, 3.4), warm), -10.5, 1.7, z + 3.25); back.rotation.y = Math.PI / 2; set.add(back);
    set.add(at(new THREE.Mesh(rbox(0.1, 1.4, 5.2, 0.01), std("#7f8386", 0.45, 0.4)), -7.5, 3.0, z + 3.25));
  }
  set.add(at(new THREE.Mesh(crease(rbox(3.2, 0.3, 110, 0.04)), facade), -6.4, 4.75, -32));
  set.add(at(new THREE.Mesh(crease(rbox(6, 6, 110, 0.04)), facade), -13.6, 3, -32));
  // Mount Fuji (concave lathe) and its snowfield, beyond the fog
  const prof = [[0, 1], [0.06, 0.985], [0.18, 0.86], [0.34, 0.64], [0.55, 0.38], [0.78, 0.15], [1, 0.02], [1.15, 0]].map(([a, b]) => new THREE.Vector2(a, b));
  const fuji = at(new THREE.Mesh(new THREE.LatheGeometry(prof, 128), new THREE.MeshBasicMaterial({ color: "#454d57", fog: false, side: THREE.DoubleSide })), -20, 0, -700);
  fuji.scale.set(330, 190, 330); set.add(fuji);
  const snowP = [[0, 1.003], [0.06, 0.988], [0.18, 0.863], [0.26, 0.75], [0.22, 0.74], [0.12, 0.8], [0, 0.82]].map(([a, b]) => new THREE.Vector2(a * 1.004, b));
  const snow = at(new THREE.Mesh(new THREE.LatheGeometry(snowP, 128), new THREE.MeshBasicMaterial({ color: "#b9c0c7", fog: false, side: THREE.DoubleSide })), -20, 0, -700);
  snow.scale.copy(fuji.scale); set.add(snow);
  // pit-exit gantry with two red lights
  const gantry = new THREE.Group(); const gMat = std("#4b4f53", 0.5, 0.4);
  gantry.add(at(new THREE.Mesh(crease(rbox(0.3, 5.8, 0.3, 0.03)), gMat), -6.2, 2.9, 0));
  gantry.add(at(new THREE.Mesh(crease(rbox(0.3, 5.8, 0.3, 0.03)), gMat), 2.6, 2.9, 0));
  gantry.add(at(new THREE.Mesh(crease(rbox(9.1, 0.35, 0.4, 0.03)), gMat), -1.8, 5.7, 0));
  const lens = new THREE.MeshStandardMaterial({ color: "#300404", emissive: "#ff2010", emissiveIntensity: 2.4 });
  for (const lx of [-0.6, 0.3]) {
    gantry.add(at(new THREE.Mesh(crease(rbox(0.5, 0.95, 0.35, 0.05)), std("#141414", 0.5)), lx, 5.0, 0.15));
    for (const ly of [5.22, 4.82]) gantry.add(at(new THREE.Mesh(new THREE.CircleGeometry(0.15, 32), lens), lx, ly, 0.33));
  }
  const glow = new THREE.PointLight(0xff3020, 30, 14, 1.8); glow.position.set(-0.15, 5, 0.8); gantry.add(glow);
  gantry.position.z = -26; set.add(shadowed(gantry));

  // cast
  const hero = buildCar(ACCENT, "1"); set.add(hero);
  const rival = buildCar(RIVAL === "#8c8e90" ? "#e9e9e6" : RIVAL, "11"); set.add(rival);
  const sprayGeo = new THREE.SphereGeometry(1, 12, 8);
  const spray = new THREE.InstancedMesh(sprayGeo, new THREE.MeshStandardMaterial({ color: "#c6ccd2", transparent: true, opacity: 0.018, roughness: 1, depthWrite: false }), 380);
  for (let i = 0; i < 380; i++) { const d = Math.pow(r(), 0.7) * 14, side = r() < 0.5 ? -0.88 : 0.88; dm.position.set(side * (1 - d / 20) + (r() - 0.5) * d * 0.45, 0.2 + r() * (0.5 + d * 0.18), 1.6 + d); dm.scale.setScalar(0.15 + d * 0.045 + r() * 0.15); dm.updateMatrix(); spray.setMatrixAt(i, dm.matrix); }
  rival.add(spray);
  const mech = buildPerson("#2f3236", { arms: { "1": { reach: 1.25, bend: 1.0, spread: 0.1, grip: 0.9 } } });
  const umbrella = new THREE.Group();
  umbrella.add(rod(new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 1.05, 0), 0.012, std("#2a2a2a", 0.4, 0.5)));
  const shade = at(new THREE.Mesh(new THREE.SphereGeometry(0.62, 48, 12, 0, Math.PI * 2, 0, 0.95), new THREE.MeshPhysicalMaterial({ color: "#191a1c", roughness: 0.3, clearcoat: 1, side: THREE.DoubleSide })), 0, 0.72, 0);
  shade.scale.y = 0.55; umbrella.add(shade);
  umbrella.position.copy(mech.userData.hands[1]); umbrella.rotation.set(0.15, 0, -0.25); mech.add(umbrella);
  mech.position.set(-2.95, 0, 0.35); mech.rotation.y = Math.PI / 2 + 0.6; set.add(mech);
  const lauda = buildPerson(ACCENT, { balaclava: true, gloves: true, arms: { "-1": { reach: 0.08, bend: 0.12, spread: 0.16, grip: 0.9 }, "1": { reach: 0.05, bend: 0.2, spread: 0.08 } } });
  const held = buildHelmet(0.155); const hp = lauda.userData.hands[-1];
  held.position.set(hp.x - 0.03, hp.y - 0.17, hp.z + 0.02); held.rotation.set(0.25, -Math.PI / 2 + 0.3, 0.15);
  lauda.add(held); lauda.userData.held = held; set.add(lauda);
  const marshal = buildPerson("#e8ad2c", { arms: { "1": { reach: 2.6, bend: 0.3, spread: 0.3, grip: 0.9 } } });
  const flagTex = canvasTex(128, 96, (g) => { for (let y = 0; y < 6; y++) for (let x = 0; x < 8; x++) { g.fillStyle = (x + y) % 2 ? "#111" : "#f2f2f2"; g.fillRect(x * 16, y * 16, 16, 16); } });
  const flag = new THREE.Group();
  flag.add(rod(new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 1.1, 0), 0.01, std("#777", 0.4, 0.6)));
  const cloth = new THREE.Mesh(new THREE.PlaneGeometry(0.8, 0.6, 12, 6), new THREE.MeshStandardMaterial({ map: flagTex, side: THREE.DoubleSide, roughness: 0.8 }));
  cloth.position.set(0.42, 0.8, 0); flag.add(cloth);
  flag.position.copy(marshal.userData.hands[1]); marshal.add(flag); marshal.userData.cloth = cloth;
  marshal.position.set(3.0, 1.05, -14); marshal.rotation.y = Math.PI / 2; set.add(marshal);
  const wallHelmet = buildHelmet(0.155); wallHelmet.position.set(2.85, 1.2, -6); wallHelmet.rotation.set(0, -1.9, 0.05); set.add(wallHelmet);
  return { group: set, hero, rival, mech, lauda, marshal, wallHelmet };
}

// ------------------------------------------------------------------ Nürburgring

export function buildRingSet() {
  const set = new THREE.Group(); set.position.x = RING_X;
  const r = seeded(31);
  const noise = (x, z) => Math.sin(x * 0.021) * 9 + Math.sin(z * 0.017 + 1.3) * 11 + Math.sin((x + z) * 0.043) * 4 + Math.sin(x * 0.09 - z * 0.07) * 1.5;
  // the winding road as a ribbon over the hills
  const path = new THREE.CatmullRomCurve3([[-160, 0, 150], [-90, 0, 120], [-40, 0, 140], [10, 0, 90], [-20, 0, 40], [30, 0, -10], [90, 0, 10], [130, 0, -60], [60, 0, -120], [120, 0, -180]].map(([x, y, z]) => new THREE.Vector3(x, y, z)));
  const samples = path.getSpacedPoints(600);
  const distToRoad = (x, z) => { let d = 1e9; for (let i = 0; i < samples.length; i += 3) d = Math.min(d, Math.hypot(x - samples[i].x, z - samples[i].z)); return d; };
  const terrainH = (x, z) => { const d = distToRoad(x, z); return noise(x, z) * Math.min(1, d / 30) + noise(x, z) * 0.15; };
  const tg = new THREE.PlaneGeometry(420, 420, 140, 140); tg.rotateX(-Math.PI / 2);
  const tp = tg.attributes.position;
  for (let i = 0; i < tp.count; i++) tp.setY(i, terrainH(tp.getX(i), tp.getZ(i)) - 0.3);
  tg.computeVertexNormals();
  set.add(shadowed(new THREE.Mesh(tg, std("#2f4a2c", 0.95))));
  const roadPts = [], roadIdx = [];
  for (let i = 0; i < samples.length; i++) {
    const p = samples[i], q = samples[Math.min(i + 1, samples.length - 1)], prev = samples[Math.max(i - 1, 0)];
    const dir = new THREE.Vector3().subVectors(q, prev).normalize(), side = new THREE.Vector3(-dir.z, 0, dir.x);
    const h = terrainH(p.x, p.z) * 0.15 + 0.05;
    for (const s of [-4.5, 4.5]) roadPts.push(p.x + side.x * s, h, p.z + side.z * s);
    if (i) { const a = (i - 1) * 2; roadIdx.push(a, a + 2, a + 1, a + 1, a + 2, a + 3); }
  }
  const rg = new THREE.BufferGeometry(); rg.setAttribute("position", new THREE.Float32BufferAttribute(roadPts, 3)); rg.setIndex(roadIdx); rg.computeVertexNormals();
  set.add(shadowed(new THREE.Mesh(rg, std("#3c4148", 0.85))));
  // conifers everywhere except the road
  const cone = mergeGeometries([
    new THREE.CylinderGeometry(0.25, 0.35, 2, 6).translate(0, 1, 0),
    new THREE.ConeGeometry(2.4, 4, 9).translate(0, 3.5, 0),
    new THREE.ConeGeometry(1.9, 3.4, 9).translate(0, 5.5, 0),
    new THREE.ConeGeometry(1.3, 3, 9).translate(0, 7.4, 0),
  ]);
  const trees = new THREE.InstancedMesh(cone, std("#ffffff", 0.9), 5200);
  const dm = new THREE.Object3D(); let n = 0;
  for (let tries = 0; tries < 30000 && n < 5200; tries++) {
    const x = (r() - 0.5) * 400, z = (r() - 0.5) * 400;
    if (distToRoad(x, z) < 8) continue;
    if (Math.abs(x) < 9 && z > 160 && z < 260) continue; // keep the crash straight clear
    dm.position.set(x, terrainH(x, z) - 0.3, z);
    dm.scale.setScalar(0.8 + r() * 0.9); dm.rotation.y = r() * 6; dm.updateMatrix();
    trees.setMatrixAt(n, dm.matrix);
    trees.setColorAt(n, new THREE.Color().setHSL(0.36 + r() * 0.05, 0.45, 0.045 + r() * 0.04));
    n++;
  }
  trees.count = n; trees.castShadow = true; set.add(trees);

  // the crash straight: road, verge, armco, close forest, at z 160–260
  const straight = new THREE.Group(); straight.position.set(0, 0, 210);
  straight.add(shadowed(at(new THREE.Mesh(new THREE.BoxGeometry(9, 0.1, 110), std("#3c4148", 0.85)), 0, 0, 0)));
  for (const sx of [-1, 1]) straight.add(at(new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.11, 110), std("#e5e5e0", 0.6)), sx * 4.3, 0.01, 0));
  straight.add(shadowed(at(new THREE.Mesh(new THREE.BoxGeometry(8, 0.2, 110), std("#3c5a30", 0.95)), -8.5, -0.02, 0)));
  const armco = std("#a9b0b6", 0.35, 0.8);
  for (const y of [0.45, 0.72]) straight.add(shadowed(at(new THREE.Mesh(crease(rbox(0.12, 0.2, 110, 0.03)), armco), -5.2, y, 0)));
  for (let z = -54; z < 55; z += 2) straight.add(shadowed(at(new THREE.Mesh(rbox(0.1, 0.9, 0.12, 0.02), std("#6d747b", 0.5, 0.6)), -5.35, 0.45, z)));
  // dense forest close on both sides of the straight, so the Green Hell rushes past
  const close = new THREE.InstancedMesh(cone, std("#ffffff", 0.9), 900);
  let cn = 0;
  for (let i = 0; i < 900; i++) {
    const side = i % 2 ? -1 : 1, x = side * (side < 0 ? 7.5 + r() * 26 : 6.5 + r() * 26), z = 150 + r() * 120;
    dm.position.set(x, 0, z); dm.scale.setScalar(0.9 + r() * 0.8); dm.rotation.y = r() * 6; dm.updateMatrix();
    close.setMatrixAt(cn, dm.matrix); close.setColorAt(cn, new THREE.Color().setHSL(0.36 + r() * 0.05, 0.45, 0.04 + r() * 0.04)); cn++;
  }
  close.castShadow = true; set.add(close);
  set.add(straight);
  const crashCar = buildCar(ACCENT, "1"); set.add(crashCar);
  const others = [buildCar("#e9e9e6", "11"), buildCar("#2d5fa8", "6")]; others.forEach((c) => set.add(c));
  const runners = ["#f4c542", "#2d5fa8", "#e9e9e6"].map((c) => { const p = buildPerson(c, { arms: { "1": { reach: 0.9, bend: 1.4 }, "-1": { reach: -0.5, bend: 1.0 } } }); set.add(p); return p; });
  // fire: additive flame cards and dark smoke puffs, animated from time
  const fire = new THREE.Group();
  const flameTex = canvasTex(64, 128, (g) => { g.scale(1, 2); const rg = g.createRadialGradient(32, 44, 1, 32, 36, 30); rg.addColorStop(0, "rgba(255,250,200,1)"); rg.addColorStop(0.3, "rgba(255,190,60,0.9)"); rg.addColorStop(0.65, "rgba(240,90,20,0.45)"); rg.addColorStop(1, "rgba(120,20,0,0)"); g.fillStyle = rg; g.fillRect(0, 0, 64, 64); }); // soft teardrop, fully transparent at the edges
  const flames = [];
  for (let i = 0; i < 40; i++) {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(0.55, 1.5), new THREE.MeshBasicMaterial({ map: flameTex, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
    m.userData = { a: hash(i, 1), b: hash(i, 2), c: hash(i, 3) }; fire.add(m); flames.push(m);
  }
  const smokes = [];
  for (let i = 0; i < 30; i++) { const m = new THREE.Mesh(new THREE.SphereGeometry(0.6, 10, 8), new THREE.MeshStandardMaterial({ color: "#2a2c30", transparent: true, opacity: 0.22, depthWrite: false, roughness: 1 })); m.userData = { a: hash(i, 7), b: hash(i, 8) }; fire.add(m); smokes.push(m); }
  const fireLight = new THREE.PointLight(0xff7a2a, 0, 18, 1.5); fireLight.position.y = 1.2; fire.add(fireLight);
  set.add(fire);
  fire.userData.update = (t, intensity, cam = null) => {
    fire.visible = intensity > 0;
    flames.forEach((m, i) => {
      const { a, b, c } = m.userData, ph = (t * (1.6 + c) + a) % 1;
      m.position.set((a - 0.5) * 2.6, 0.3 + ph * 1.6 * intensity, (b - 0.5) * 3.6);
      m.scale.set((0.8 + c) * (1 - ph * 0.6) * intensity, (1.4 + c) * (1 - ph * 0.5) * intensity, 1);
      if (cam) m.quaternion.copy(cam.quaternion); // billboard toward the lens
    });
    smokes.forEach((m) => { const { a, b } = m.userData, ph = (t * 0.35 + a) % 1; m.position.set((a - 0.5) * 2 + ph * 1.5, 2 + ph * 7 * intensity, (b - 0.5) * 3); m.scale.setScalar((0.6 + ph * 2.4) * intensity); m.material.opacity = 0.24 * (1 - ph); });
    fireLight.intensity = intensity * (22 + 8 * Math.sin(t * 23) + 6 * Math.sin(t * 37));
  };
  return { group: set, path, terrainH, crashCar, others, runners, fire };
}

// ------------------------------------------------------------------ hospital

export function buildHospitalSet() {
  const set = new THREE.Group(); set.position.x = HOSP_X;
  const wall = std("#2c3a40", 0.85), floor = std("#2a3034", 0.45, 0.1);
  const floorMesh = at(new THREE.Mesh(new THREE.PlaneGeometry(12, 8), floor), 0, 0, 0); floorMesh.rotation.x = -Math.PI / 2; floorMesh.receiveShadow = true; set.add(floorMesh);
  const back = at(new THREE.Mesh(new THREE.PlaneGeometry(12, 5), wall), 0, 2.5, -3); set.add(back);
  const side = at(new THREE.Mesh(new THREE.PlaneGeometry(8, 5), wall), -4, 2.5, 0); side.rotation.y = Math.PI / 2; set.add(side);
  // window with night city and rain on the glass
  const night = canvasTex(256, 256, (g, w, h) => { const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, "#0b1119"); gr.addColorStop(1, "#16202c"); g.fillStyle = gr; g.fillRect(0, 0, w, h); for (let i = 0; i < 70; i++) { g.fillStyle = i % 3 ? "#c9a85a" : "#7fa0c8"; g.fillRect(hash(i, 1) * w, h * 0.65 + hash(i, 2) * h * 0.3, 2, 2); } });
  const win = at(new THREE.Mesh(new THREE.PlaneGeometry(1.6, 1.4), new THREE.MeshBasicMaterial({ map: night })), -2.4, 2.2, -2.98); set.add(win);
  const frameM = std("#6a7076", 0.5, 0.3);
  set.add(at(new THREE.Mesh(rbox(1.7, 0.06, 0.06), frameM), -2.4, 1.5, -2.95)); set.add(at(new THREE.Mesh(rbox(1.7, 0.06, 0.06), frameM), -2.4, 2.9, -2.95));
  set.add(at(new THREE.Mesh(rbox(0.06, 1.46, 0.06), frameM), -2.4, 2.2, -2.95));
  const daylight = at(new THREE.Mesh(new THREE.PlaneGeometry(1.6, 1.4), new THREE.MeshBasicMaterial({ color: "#c9dcf0", transparent: true, opacity: 0 })), -2.4, 2.2, -2.97); set.add(daylight);
  // bed: frame, mattress, sheet over the body, pillow
  const bed = new THREE.Group();
  const metal = std("#b9bdc2", 0.35, 0.8);
  bed.add(shadowed(at(new THREE.Mesh(crease(rbox(1.0, 0.18, 2.1, 0.03)), std("#9fa7ae", 0.6)), 0, 0.62, 0)));
  for (const [x, z] of [[-0.45, -1], [0.45, -1], [-0.45, 1], [0.45, 1]]) bed.add(shadowed(rod(new THREE.Vector3(x, 0, z), new THREE.Vector3(x, 0.62, z), 0.02, metal)));
  bed.add(shadowed(at(new THREE.Mesh(crease(rbox(1.0, 0.5, 0.05, 0.02)), metal), 0, 0.95, -1.05)));
  const sheetM = new THREE.MeshPhysicalMaterial({ color: "#dfe5ea", roughness: 0.85, sheen: 0.4 });
  const sheet = new THREE.Mesh(new THREE.BoxGeometry(1.04, 0.16, 1.5, 20, 2, 40), sheetM);
  const sp = sheet.geometry.attributes.position;
  for (let i = 0; i < sp.count; i++) if (sp.getY(i) > 0) sp.setY(i, sp.getY(i) + 0.08 * Math.exp(-(((sp.getZ(i) + 0.3) / 0.35) ** 2)) * Math.exp(-((sp.getX(i) / 0.3) ** 2)) + 0.01 * Math.sin(sp.getZ(i) * 18));
  sheet.geometry.computeVertexNormals();
  bed.add(shadowed(at(sheet, 0, 0.78, 0.25)));
  const pillow = at(new THREE.Mesh(new THREE.SphereGeometry(0.3, 32, 16), sheetM), 0, 0.78, -0.82); pillow.scale.set(1.3, 0.35, 0.75); bed.add(shadowed(pillow));
  // the patient: burned face under an oxygen mask, crown bandaged with blood seeping through
  const burnColor = (x, y, z) => {
    if (z < 0.25) return new THREE.Color("#b4876a");
    const h = hash(Math.floor((x + 1) * 9), Math.floor((y + 1) * 9));
    return new THREE.Color(h < 0.28 ? "#8e2a1f" : h < 0.42 ? "#3a1410" : h < 0.55 ? "#d88a78" : "#b4876a");
  };
  const headMat = new THREE.MeshPhysicalMaterial({ vertexColors: true, roughness: 0.55, sheen: 0.2 });
  const head = new THREE.Mesh(headGeometry(0.1, 1, burnColor), headMat);
  head.rotation.x = -Math.PI / 2; head.position.set(0, 0.92, -0.78); bed.add(head);
  const gauze = new THREE.MeshPhysicalMaterial({ color: "#f1f1ee", roughness: 0.95, sheen: 0.5 });
  const wrap = at(new THREE.Mesh(new THREE.SphereGeometry(0.112, 32, 16, 0, Math.PI * 2, 0, 1.7), gauze), 0, 0.92, -0.8);
  wrap.rotation.x = Math.PI / 2 + 0.25; bed.add(wrap);
  for (let i = 0; i < 4; i++) { const blood = at(new THREE.Mesh(new THREE.CircleGeometry(0.018 + hash(i, 4) * 0.02, 16), new THREE.MeshStandardMaterial({ color: "#6e0c0c", roughness: 0.4, polygonOffset: true, polygonOffsetFactor: -4 })), (hash(i, 1) - 0.5) * 0.12, 0.98 + hash(i, 2) * 0.04, -0.86 - hash(i, 3) * 0.04); blood.lookAt(new THREE.Vector3(blood.position.x * 3, 2, -1.5)); bed.add(blood); }
  const mask = at(new THREE.Mesh(new THREE.SphereGeometry(0.055, 24, 12, 0, Math.PI * 2, 0, 1.5), new THREE.MeshPhysicalMaterial({ color: "#a8cfc4", transparent: true, opacity: 0.6, roughness: 0.2 })), 0, 1.02, -0.72);
  bed.add(mask);
  bed.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([new THREE.Vector3(0, 1.05, -0.72), new THREE.Vector3(0.2, 1.2, -0.9), new THREE.Vector3(0.5, 1.6, -1.2), new THREE.Vector3(0.7, 2.1, -2.9)]), 40, 0.008, 8), new THREE.MeshPhysicalMaterial({ color: "#c9e2db", transparent: true, opacity: 0.7 })));
  const arm = at(new THREE.Mesh(new THREE.CapsuleGeometry(0.045, 0.5, 6, 16), gauze), 0.32, 0.88, -0.2); arm.rotation.x = Math.PI / 2; bed.add(shadowed(arm));
  const hand = at(new THREE.Mesh(new THREE.SphereGeometry(0.05, 16, 12), new THREE.MeshStandardMaterial({ color: "#8e2a1f", roughness: 0.6 })), 0.32, 0.88, 0.1); hand.scale.set(1, 0.6, 1.4); bed.add(hand);
  bed.position.set(0.6, 0, -1.4); set.add(bed);
  // monitor with a live ECG, IV stand with saline and blood, table with the scorched helmet
  const ecgCanvas = document.createElement("canvas"); ecgCanvas.width = 512; ecgCanvas.height = 256;
  const ecgTex = new THREE.CanvasTexture(ecgCanvas); ecgTex.colorSpace = THREE.SRGBColorSpace;
  const monitor = new THREE.Group();
  monitor.add(shadowed(at(new THREE.Mesh(crease(rbox(0.8, 0.5, 0.12, 0.02)), std("#2a3036", 0.5)), 0, 0, 0)));
  monitor.add(at(new THREE.Mesh(new THREE.PlaneGeometry(0.7, 0.4), new THREE.MeshBasicMaterial({ map: ecgTex })), 0, 0, 0.062));
  monitor.position.set(1.7, 2.1, -2.7); set.add(monitor);
  const ivPole = new THREE.Group();
  ivPole.add(rod(new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 2.1, 0), 0.015, metal));
  ivPole.add(at(new THREE.Mesh(rbox(0.16, 0.24, 0.05, 0.02), new THREE.MeshPhysicalMaterial({ color: "#d9e6ee", transparent: true, opacity: 0.7, roughness: 0.2 })), -0.1, 1.9, 0));
  ivPole.add(at(new THREE.Mesh(rbox(0.16, 0.24, 0.05, 0.02), new THREE.MeshPhysicalMaterial({ color: "#5e0f12", roughness: 0.3, clearcoat: 0.5 })), 0.1, 1.9, 0));
  ivPole.position.set(1.4, 0, -0.8); set.add(ivPole);
  set.add(shadowed(at(new THREE.Mesh(crease(rbox(0.6, 0.7, 0.5, 0.02)), std("#3a3f45", 0.6)), -0.8, 0.35, -1.8)));
  const scorched = buildHelmet(0.155, "#7a1418"); scorched.position.set(-0.8, 0.87, -1.8); scorched.rotation.y = 0.9; set.add(scorched);
  const doctors = [0, 1].map((i) => { const d = buildPerson("#e8eef2", { arms: { "1": { reach: 0.6, bend: 0.9 }, "-1": { reach: 0.4, bend: 0.6 } } }); d.position.set(1.45 + i * 0.25, 0, -1.9 + i * 1.2); d.rotation.y = -Math.PI / 2 - 0.2; set.add(d); return d; });
  // X-ray lightbox (shown in its own shot)
  const xray = canvasTex(512, 640, (g, w, h) => {
    g.fillStyle = "#0b1014"; g.fillRect(0, 0, w, h);
    for (const side of [-1, 1]) { const gr = g.createRadialGradient(w / 2 + side * 110, h * 0.5, 20, w / 2 + side * 110, h * 0.5, 170); gr.addColorStop(0, "rgba(150,165,175,0.75)"); gr.addColorStop(1, "rgba(40,50,58,0.1)"); g.fillStyle = gr; g.beginPath(); g.ellipse(w / 2 + side * 110, h * 0.5, 95, 200, 0, 0, Math.PI * 2); g.fill(); }
    for (let i = 0; i < 400; i++) { g.fillStyle = `rgba(200,210,218,${0.15 + hash(i, 1) * 0.3})`; const side = i % 2 ? -1 : 1; g.beginPath(); g.arc(w / 2 + side * (50 + hash(i, 2) * 120), h * 0.25 + hash(i, 3) * h * 0.5, 4 + hash(i, 4) * 12, 0, 7); g.fill(); }
    g.strokeStyle = "rgba(225,232,238,0.85)"; g.lineWidth = 7;
    for (let i = 0; i < 9; i++) for (const side of [-1, 1]) { g.beginPath(); g.moveTo(w / 2 + side * 14, h * 0.18 + i * 42); g.quadraticCurveTo(w / 2 + side * 170, h * 0.16 + i * 42, w / 2 + side * 200, h * 0.22 + i * 44 + 30); g.stroke(); }
    g.fillStyle = "rgba(220,228,234,0.9)"; g.fillRect(w / 2 - 12, h * 0.1, 24, h * 0.8);
  });
  const lightbox = new THREE.Group();
  lightbox.add(at(new THREE.Mesh(crease(rbox(1.3, 1.6, 0.08, 0.02)), std("#c9d2d8", 0.4, 0.2)), 0, 0, 0));
  lightbox.add(at(new THREE.Mesh(new THREE.PlaneGeometry(1.15, 1.44), new THREE.MeshBasicMaterial({ map: xray })), 0, 0, 0.045));
  lightbox.position.set(-3.95, 2.0, -0.5); lightbox.rotation.y = Math.PI / 2; set.add(lightbox);
  const lamp = new THREE.SpotLight(0xd8e8ff, 40, 8, 0.6, 0.6, 1.2); lamp.position.set(0.6, 3.6, -1.2); lamp.target.position.set(0.6, 0.8, -1.4); lamp.castShadow = true;
  set.add(lamp); set.add(lamp.target);
  const alarm = new THREE.PointLight(0xff2a1a, 0, 6, 1.5); alarm.position.set(1.7, 2.5, -2.4); set.add(alarm);
  return { group: set, ecgCanvas, ecgTex, doctors, alarm, daylight, lamp, scorched, bed };
}

// ------------------------------------------------------------------ Monza, in the sun

export function buildMonzaSet() {
  const set = new THREE.Group(); set.position.x = MONZA_X;
  buildTrack(set);
  const r = seeded(9);
  const pines = mergeGeometries([new THREE.CylinderGeometry(0.2, 0.3, 7, 6).translate(0, 3.5, 0), new THREE.SphereGeometry(3.2, 12, 8).scale(1, 0.45, 1).translate(0, 7.6, 0)]);
  const pm = new THREE.InstancedMesh(pines, std("#ffffff", 0.9), 60); const dm = new THREE.Object3D();
  for (let i = 0; i < 60; i++) { dm.position.set(35 + r() * 10, 0, -150 + i * 3.4); dm.scale.setScalar(0.8 + r() * 0.5); dm.updateMatrix(); pm.setMatrixAt(i, dm.matrix); pm.setColorAt(i, new THREE.Color(i % 7 === 0 ? "#5a4030" : "#2f5a3a")); }
  set.add(pm);
  const hero = buildCar(ACCENT, "1"); set.add(hero);
  const board = new THREE.Group();
  board.add(rod(new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 2.6, 0), 0.03, std("#777", 0.4, 0.6)));
  const p4 = canvasTex(256, 160, (g, w, h) => { g.fillStyle = "#111"; g.fillRect(0, 0, w, h); g.fillStyle = "#f4f4f2"; g.font = "900 120px Inter, sans-serif"; g.textAlign = "center"; g.textBaseline = "middle"; g.fillText("P4", w / 2, h / 2 + 6); });
  const face = at(new THREE.Mesh(new THREE.PlaneGeometry(1.2, 0.75), new THREE.MeshStandardMaterial({ map: p4, roughness: 0.6 })), 0, 2.7, 0.02);
  board.add(face); board.add(at(new THREE.Mesh(crease(rbox(1.26, 0.8, 0.04, 0.01)), std("#222", 0.5)), 0, 2.7, -0.01));
  board.position.set(-3.6, 1.05, -16); board.rotation.y = 0.9; set.add(board);
  const finish = new THREE.Mesh(new THREE.PlaneGeometry(7, 0.9), new THREE.MeshStandardMaterial({ map: canvasTex(256, 32, (g) => { for (let y = 0; y < 2; y++) for (let x = 0; x < 16; x++) { g.fillStyle = (x + y) % 2 ? "#111" : "#eee"; g.fillRect(x * 16, y * 16, 16, 16); } }), roughness: 0.5 }));
  finish.rotation.x = -Math.PI / 2; finish.position.set(0, 0.006, -16); set.add(finish);
  const driver = buildDriver(); driver.position.set(-6, 0.55, -2); set.add(driver);
  // the stain on the balaclava at the temple: the wound still bleeding under the helmet
  const stain = new THREE.Mesh(new THREE.CircleGeometry(0.025, 20), new THREE.MeshStandardMaterial({ color: "#7a0d0d", roughness: 0.5, polygonOffset: true, polygonOffsetFactor: -4 }));
  stain.position.set(0.07, 0.695, 0.055); stain.lookAt(new THREE.Vector3(0.4, 0.75, 0.4)); driver.add(stain);
  return { group: set, hero, board, face, driver };
}
