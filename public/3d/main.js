import * as THREE from 'three';

// ---- Content (copied from ../index.html, ../about-me.html, ../projects.html) ----
const ROOMS = {
  lobby: { name: 'Lobby', page: '../index.html', pos: [0, 0], doors: { n: 'journey', e: 'projects', w: 'contact' },
    photos: [['image1.jpg', 'Portrait of Jargal Boldbaatar'], ['meWithHorse.jpg', 'Jargal with a horse in the countryside'], ['IMG_2135.jpg', 'Green Mongolian landscape'], ['IMG_2162.jpg', 'Open field in the countryside']],
    panels: [
      { meta: 'Personal website', title: 'Engineering ideas into motion.', body: 'I am Jargal Boldbaatar, a mechatronics student building at the intersection of automation, robotics, and curiosity.\nThis space is where I collect the things I am learning, the values that shape me, and the direction I want my work to go next.' },
      { meta: 'At a glance', title: 'GMIT · 3 Focuses', body: 'GMIT — Engineering student in Mongolia\n3 Focuses — Automation, robotics, entrepreneurship\nLearning by building — Web, systems thinking, and real-world problem solving\nOrigin — Khentii to Ulaanbaatar\nMission — Build useful things and keep growing' },
      { meta: 'Current direction · 01', title: 'Automation', body: 'I am drawn to systems that reduce friction, improve reliability, and turn repetitive work into something smarter.' },
      { meta: 'Current direction · 02', title: 'Robotics', body: 'Robotics excites me because it combines hardware, software, and engineering design into one living problem.' },
      { meta: 'Current direction · 03', title: 'Entrepreneurship', body: 'I want to build ideas that matter in the real world, not just in theory, and learn how to turn them into value.' },
      { meta: 'Where I come from', title: 'A countryside childhood shaped how I think.', body: 'I grew up in a nomadic family and spent much of my childhood close to nature. That background taught me patience, adaptability, and respect for practical work.\nLater, school in Khentii and Baganuur expanded my world, and university gave that curiosity a technical direction.' },
      { meta: 'Milestones', title: 'A short timeline of the path so far', body: '2005 — Born and raised close to nature. My early years were shaped by the countryside, family, and the rhythm of a nomadic life.\n2018 — A bigger world in Baganuur. Moving for school gave me new environments, new discipline, and a broader view of what I could become.\n2023 — Engineering at GMIT. University turned my interest in how things work into a serious commitment to engineering and innovation.' },
    ] },
  journey: { name: 'Journey', page: '../about-me.html', pos: [0, -30], doors: { s: 'lobby' },
    photos: [['meWithHorse.jpg', 'Jargal in the countryside with a horse'], ['imOfPrSch7.jpg', 'Primary school memory'], ['imOfPrSch8.jpg', 'Primary school group photo'], ['imOfBa64.jpg', 'Baganuur memory'], ['imOfBa13.jpg', 'Portrait from Baganuur years'], ['IMG_6923.jpg', 'Image from countryside'], ['IMG_6931.jpg', 'Mountain landscape'], ['IMG_2135.jpg', 'Green field in the countryside'], ['IMG_2162.jpg', 'Open countryside landscape']],
    panels: [
      { meta: 'Personal journey', title: 'From the countryside to engineering.', body: 'My story begins in Khentii, moves through Baganuur, and continues today at GMIT University.' },
      { meta: '2005', title: 'Childhood in the countryside', body: 'I was born on June 13, 2005. I grew up surrounded by open land, animals, and the pace of rural life, especially during school holidays.' },
      { meta: '2009', title: 'First steps in education', body: 'My educational journey began at Kherlen 4th Kindergarten, and in 2011 I continued at Kherlen 4th School in Khentii Province.' },
      { meta: '2018', title: 'Learning in Baganuur', body: 'I moved to Baganuur, a district of Ulaanbaatar, where I studied at Bolovsrol Complex School and completed high school.', link: ['Bolovsrol Complex School', 'https://www.bolovsrolts.edu.mn/#'] },
      { meta: '2023', title: 'Engineering at GMIT', body: 'I began my undergraduate studies at GMIT University, focusing on engineering, automation, robotics, and innovation-driven entrepreneurship.', link: ['GMIT University', 'https://www.gmit.edu.mn/eng/'] },
      { meta: 'Roots', title: 'The places that shaped me still travel with me.', body: 'These photos represent more than memories. They reflect school life in Khentii and Baganuur, time in the countryside, and the background that continues to shape my perspective.\nI carry that sense of place into how I learn, how I work, and how I imagine the future.' },
      { meta: 'What stays with me', title: 'The qualities I want my work to reflect', body: '01 Curiosity — I like understanding why things work, not only how to use them.\n02 Consistency — Progress matters most when it is built through steady effort over time.\n03 Practical ambition — I want to aim high while staying grounded in useful, real-world outcomes.' },
    ] },
  // Projects content is read at runtime from ../projects.html (single source); see loadProjects().
  projects: { name: 'Projects', page: '../projects.html', pos: [30, 0], doors: { w: 'lobby' }, panels: [], pedestals: [] },
  contact: { name: 'Contact', page: '../index.html#contact', pos: [-30, 0], doors: { e: 'lobby' },
    panels: [
      { meta: "Let's connect", title: "I'm building this chapter in public.", body: '' },
      { meta: 'Email', title: 'jargal0660@gmail.com', body: 'jargal0660@gmail.com', link: ['Send email', 'mailto:jargal0660@gmail.com'] },
      { meta: 'Instagram', title: 'Instagram', body: 'instagram.com/j_rg_l_', link: ['Instagram', 'https://instagram.com/j_rg_l_'] },
      { meta: 'Jargal Boldbaatar', title: 'Built with curiosity and consistency.', body: '' },
    ] },
};

async function loadProjects() {
  const r = ROOMS.projects;
  try {
    const res = await fetch('../projects.html', { cache: 'no-cache' });
    if (!res.ok) throw new Error(res.status);
    const doc = new DOMParser().parseFromString(await res.text(), 'text/html');
    const txt = el => (el ? el.textContent.replace(/\s+/g, ' ').trim() : '');
    const hero = doc.querySelector('.page-hero-copy');
    if (hero) r.panels.push({ meta: txt(hero.querySelector('.eyebrow')), title: txt(hero.querySelector('h1')), body: txt(hero.querySelector('.hero-lead')) });
    for (const sec of doc.querySelectorAll('main section')) {
      const head = sec.querySelector('.section-heading'); if (!head) continue;
      r.panels.push({ meta: txt(head.querySelector('.eyebrow')), title: txt(head.querySelector('h2')), body: '' });
      for (const art of sec.querySelectorAll('article')) {
        const link = art.querySelector('a[href]');
        r.pedestals.push({ meta: txt(art.querySelector('.status-tag')), title: txt(art.querySelector('h3')),
          body: [...art.querySelectorAll('p')].map(txt).join('\n'), link: link ? [txt(link), new URL(link.getAttribute('href'), res.url).href] : undefined });
      }
    }
  } catch (e) {
    console.warn('Could not load projects.html', e);
    r.panels.push({ meta: 'Projects', title: 'Projects', body: 'Open the original Projects page to read them.' });
  }
}
await loadProjects();

const ACCENT = 0x00e676, H = 9, WALL_H = 7.5, DOOR = 2.2, T = 0.4;

// ---- Setup ----
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
document.body.prepend(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x000000);
scene.fog = new THREE.Fog(0x000000, 18, 45);
const camera = new THREE.PerspectiveCamera(65, innerWidth / innerHeight, 0.1, 100);
scene.add(new THREE.HemisphereLight(0xffffff, 0x101010, 1.1));
const sun = new THREE.DirectionalLight(0xffffff, 0.8); sun.position.set(10, 20, 8); scene.add(sun);

const wallMat = new THREE.MeshStandardMaterial({ color: 0x141414, roughness: 0.9 });
const floorMat = new THREE.MeshStandardMaterial({ color: 0x0a0a0a, roughness: 1 });
const accentMat = new THREE.MeshStandardMaterial({ color: ACCENT, emissive: ACCENT, emissiveIntensity: 0.8 });
const colliders = []; // {x0,x1,z0,z1}
function box(x0, x1, z0, z1, h = WALL_H, mat = wallMat, y0 = 0, collide = true) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(x1 - x0, h, z1 - z0), mat);
  m.position.set((x0 + x1) / 2, y0 + h / 2, (z0 + z1) / 2); scene.add(m);
  if (collide) colliders.push({ x0, x1, z0, z1 });
  return m;
}

// ---- Text textures ----
function wrap(ctx, text, maxW) {
  const lines = [];
  for (const para of text.split('\n')) {
    let line = '';
    for (const w of para.split(' ')) {
      const t = line ? line + ' ' + w : w;
      if (ctx.measureText(t).width > maxW && line) { lines.push(line); line = w; } else line = t;
    }
    lines.push(line);
  }
  return lines;
}
function panelTexture(p, w = 1024, h = 640) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const g = c.getContext('2d');
  g.fillStyle = '#0a0a0a'; g.fillRect(0, 0, w, h);
  g.strokeStyle = '#00e676'; g.lineWidth = 6; g.strokeRect(3, 3, w - 6, h - 6);
  g.fillStyle = '#00e676'; g.font = '600 30px monospace'; g.fillText(p.meta.toUpperCase(), 40, 64);
  g.fillStyle = '#fff'; g.font = '700 50px system-ui, sans-serif';
  let y = 130; for (const l of wrap(g, p.title, w - 80)) { g.fillText(l, 40, y); y += 58; }
  let size = 30; g.font = `${size}px system-ui, sans-serif`;
  let lines = wrap(g, p.body, w - 80);
  while (y + 20 + lines.length * size * 1.35 > h - 30 && size > 18) { size -= 2; g.font = `${size}px system-ui, sans-serif`; lines = wrap(g, p.body, w - 80); }
  g.fillStyle = '#d0d0d0'; y += 20;
  for (const l of lines) { g.fillText(l, 40, y); y += size * 1.35; }
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 4;
  return tex;
}
function signTexture(text) {
  const c = document.createElement('canvas'); c.width = 512; c.height = 128;
  const g = c.getContext('2d'); g.fillStyle = '#000'; g.fillRect(0, 0, 512, 128);
  g.fillStyle = '#00e676'; g.font = '700 56px monospace'; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.fillText(text, 256, 66);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

// ---- Build world ----
const readables = []; // {pos: Vector3, data}
const photoJobs = {}, loadedRooms = new Set();
const frameMat = new THREE.MeshStandardMaterial({ color: 0x1a1a1a, roughness: 0.6 });
async function loadImage(url, maxW = 1024) {
  const blob = await (await fetch(url)).blob();
  try { return await createImageBitmap(blob, { resizeWidth: maxW, resizeQuality: 'high', imageOrientation: 'flipY' }); }
  catch { return await createImageBitmap(blob, { imageOrientation: 'flipY' }); }
}
function captionTexture(text) {
  const c = document.createElement('canvas'); c.width = 768; c.height = 80;
  const g = c.getContext('2d'); g.fillStyle = '#000'; g.fillRect(0, 0, 768, 80);
  g.fillStyle = '#ffffff'; g.font = '30px system-ui, sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(text, 384, 42);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
function loadPhotos(id) {
  if (loadedRooms.has(id) || !photoJobs[id]) return; loadedRooms.add(id);
  for (const { ph: [file, alt], s } of photoJobs[id]) {
    loadImage('img/' + file).then(bmp => {
      const a = bmp.width / bmp.height; let w = 3.6, h = w / a; if (h > 2.5) { h = 2.5; w = h * a; }
      const tex = new THREE.Texture(bmp); tex.colorSpace = THREE.SRGBColorSpace; tex.flipY = false; tex.needsUpdate = true;
      const g = new THREE.Group(); g.position.set(s.px, 6.05, s.pz); g.rotation.y = s.rot;
      const fr = new THREE.Mesh(new THREE.BoxGeometry(w + 0.24, h + 0.24, 0.08), frameMat); g.add(fr);
      const edge = new THREE.Mesh(new THREE.PlaneGeometry(w + 0.1, h + 0.1), accentMat); edge.position.z = 0.045; g.add(edge);
      const pic = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: tex })); pic.position.z = 0.05; g.add(pic);
      const cap = new THREE.Mesh(new THREE.PlaneGeometry(3.6, 0.375), new THREE.MeshBasicMaterial({ map: captionTexture(alt) })); cap.position.set(0, -h / 2 - 0.42, 0.05); g.add(cap);
      scene.add(g);
    }).catch(e => console.warn('photo failed', file, e));
  }
}
const SIDES = { n: [0, -1], s: [0, 1], e: [1, 0], w: [-1, 0] };
function sign(text, x, z, rotY) {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(3, 0.75), new THREE.MeshBasicMaterial({ map: signTexture(text) }));
  m.position.set(x, 3.4, z); m.rotation.y = rotY; scene.add(m);
}
for (const [id, r] of Object.entries(ROOMS)) {
  const [cx, cz] = r.pos;
  const f = new THREE.Mesh(new THREE.PlaneGeometry(2 * H, 2 * H), floorMat);
  f.rotation.x = -Math.PI / 2; f.position.set(cx, 0, cz); scene.add(f);
  const grid = new THREE.GridHelper(2 * H, 18, 0x0f3d24, 0x0f3d24); grid.position.set(cx, 0.01, cz); scene.add(grid);
  const light = new THREE.PointLight(ACCENT, 25, 22, 1.5); light.position.set(cx, 4, cz); scene.add(light);
  // room name on floor
  const nm = new THREE.Mesh(new THREE.PlaneGeometry(6, 1.5), new THREE.MeshBasicMaterial({ map: signTexture(r.name), transparent: true, opacity: 0.85 }));
  nm.rotation.x = -Math.PI / 2; nm.position.set(cx, 0.02, cz + 2); scene.add(nm);
  // walls with door gaps
  for (const [s, [dx, dz]] of Object.entries(SIDES)) {
    const door = r.doors[s];
    if (dz) { // north/south wall along x
      const z = cz + dz * H, z0 = z - T / 2, z1 = z + T / 2;
      if (door) { box(cx - H, cx - DOOR, z0, z1); box(cx + DOOR, cx + H, z0, z1); box(cx - DOOR, cx + DOOR, z0, z1, WALL_H - 3.8, wallMat, 3.8, false);
        sign(ROOMS[door].name + (dz < 0 ? ' ↑' : ' ↓'), cx, z - dz * 0.25, dz < 0 ? 0 : Math.PI);
      } else box(cx - H, cx + H, z0, z1);
    } else {
      const x = cx + dx * H, x0 = x - T / 2, x1 = x + T / 2;
      if (door) { box(x0, x1, cz - H, cz - DOOR); box(x0, x1, cz + DOOR, cz + H); box(x0, x1, cz - DOOR, cz + DOOR, WALL_H - 3.8, wallMat, 3.8, false);
        sign(ROOMS[door].name, x - dx * 0.25, cz, dx > 0 ? -Math.PI / 2 : Math.PI / 2);
      } else box(x0, x1, cz - H, cz + H);
    }
    // accent strip along floor
  }
  // panel slots: 2 per wall, ordered so the far wall fills first
  const slots = [];
  for (const s of ['n', 'e', 'w', 's']) for (const o of [-5.2, 5.2]) {
    const [dx, dz] = SIDES[s];
    const px = dz ? cx + o : cx + dx * (H - T / 2 - 0.05), pz = dz ? cz + dz * (H - T / 2 - 0.05) : cz + o;
    slots.push({ px, pz, rot: Math.atan2(-dx, -dz), nx: -dx, nz: -dz });
  }
  r.panels.forEach((p, i) => {
    const s = slots[i]; if (!s) return;
    const m = new THREE.Mesh(new THREE.PlaneGeometry(6, 3.75), new THREE.MeshBasicMaterial({ map: panelTexture(p) }));
    m.position.set(s.px, 2.3, s.pz); m.rotation.y = s.rot; scene.add(m);
    readables.push({ pos: new THREE.Vector3(s.px + s.nx * 1.5, 0, s.pz + s.nz * 1.5), data: p });
  });
  // framed photos above the panels (lazy-loaded per room)
  const pslots = [];
  for (const s of ['n', 'e', 'w', 's']) for (const o of [-6, 0, 6]) {
    const [dx, dz] = SIDES[s];
    pslots.push({ px: dz ? cx + o : cx + dx * (H - T / 2 - 0.08), pz: dz ? cz + dz * (H - T / 2 - 0.08) : cz + o, rot: Math.atan2(-dx, -dz) });
  }
  if (r.photos) photoJobs[id] = r.photos.map((ph, i) => ({ ph, s: pslots[i] }));
  // pedestals (projects)
  (r.pedestals || []).forEach((p, i) => {
    const col = i % 4, row = Math.floor(i / 4);
    const x = cx - 5.4 + col * 3.6, z = cz - 2.6 + row * 5.4;
    box(x - 0.6, x + 0.6, z - 0.6, z + 0.6, 1.1, wallMat);
    box(x - 0.62, x + 0.62, z - 0.62, z + 0.62, 0.06, accentMat, 1.1, false);
    const tex = panelTexture(p, 768, 640);
    for (const rot of [0, Math.PI]) {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(2.6, 2.17), new THREE.MeshBasicMaterial({ map: tex, side: THREE.FrontSide }));
      m.position.set(x, 2.35, z); m.rotation.y = rot; scene.add(m);
    }
    readables.push({ pos: new THREE.Vector3(x, 0, z), data: p, r: 2.2 });
  });
}
// corridors between connected rooms
const done = new Set();
for (const [id, r] of Object.entries(ROOMS)) for (const [s, to] of Object.entries(r.doors)) {
  const key = [id, to].sort().join(); if (done.has(key)) continue; done.add(key);
  const [dx, dz] = SIDES[s], [cx, cz] = r.pos, [tx, tz] = ROOMS[to].pos;
  if (dz) {
    const za = Math.min(cz + dz * H, tz - dz * H), zb = Math.max(cz + dz * H, tz - dz * H);
    box(cx - DOOR - T, cx - DOOR, za, zb, 4.5); box(cx + DOOR, cx + DOOR + T, za, zb, 4.5);
    const f = new THREE.Mesh(new THREE.PlaneGeometry(2 * DOOR, zb - za), floorMat); f.rotation.x = -Math.PI / 2; f.position.set(cx, 0, (za + zb) / 2); scene.add(f);
    box(cx - 0.05, cx + 0.05, za, zb, 0.02, accentMat, 0.01, false);
    const l = new THREE.PointLight(0xffffff, 6, 10); l.position.set(cx, 3, (za + zb) / 2); scene.add(l);
  } else {
    const xa = Math.min(cx + dx * H, tx - dx * H), xb = Math.max(cx + dx * H, tx - dx * H);
    box(xa, xb, cz - DOOR - T, cz - DOOR, 4.5); box(xa, xb, cz + DOOR, cz + DOOR + T, 4.5);
    const f = new THREE.Mesh(new THREE.PlaneGeometry(xb - xa, 2 * DOOR), floorMat); f.rotation.x = -Math.PI / 2; f.position.set((xa + xb) / 2, 0, cz); scene.add(f);
    box(xa, xb, cz - 0.05, cz + 0.05, 0.02, accentMat, 0.01, false);
    const l = new THREE.PointLight(0xffffff, 6, 10); l.position.set((xa + xb) / 2, 3, cz); scene.add(l);
  }
}

// ---- Player ----
const player = new THREE.Group();
const bodyMat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.5 });
const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.35, 0.8, 4, 12), bodyMat); body.position.y = 0.75; player.add(body);
const visor = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.12, 0.1), accentMat); visor.position.set(0, 1.2, -0.32); player.add(visor);
scene.add(player);
const RAD = 0.4;
let yaw = 0, pitch = 0.35, vy = 0, grounded = true;
const jump = () => { if (grounded && overlay.hidden) { vy = 7; grounded = false; } };

function collide(x, z) {
  for (const c of colliders) if (x > c.x0 - RAD && x < c.x1 + RAD && z > c.z0 - RAD && z < c.z1 + RAD) return true;
  return false;
}

// ---- Rooms / hash ----
const roomNameEl = document.getElementById('roomName'), origLink = document.getElementById('origLink');
let current = null;
function roomAt(x, z) {
  for (const [id, r] of Object.entries(ROOMS)) if (Math.abs(x - r.pos[0]) < H && Math.abs(z - r.pos[1]) < H) return id;
  return null;
}
function setRoom(id) {
  if (id === current) return; current = id;
  const r = ROOMS[id]; roomNameEl.textContent = r.name; origLink.href = r.page; origLink.textContent = 'Original ' + r.name + ' page';
  if (location.hash.slice(1) !== id) history.replaceState(null, '', id === 'lobby' ? location.pathname : '#' + id);
  document.title = 'Jargal | 3D · ' + r.name;
  loadPhotos(id); for (const n of Object.values(r.doors)) loadPhotos(n);
}
function teleport(id) {
  const r = ROOMS[id] || ROOMS.lobby; player.position.set(r.pos[0], 0, r.pos[1] + 1); vy = 0; grounded = true; yaw = 0; setRoom(ROOMS[id] ? id : 'lobby');
}
addEventListener('hashchange', () => { const id = location.hash.slice(1) || 'lobby'; if (id !== current) teleport(id); });
teleport(location.hash.slice(1) || 'lobby');

// ---- Input ----
const keys = {};
const overlay = document.getElementById('overlay'), ovBody = document.getElementById('ovBody'), prompt = document.getElementById('prompt'), readBtn = document.getElementById('readBtn');
let near = null;
const esc = s => s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function openOverlay(p) {
  ovBody.innerHTML = `<div class="meta">${esc(p.meta)}</div><h2>${esc(p.title)}</h2>` + p.body.split('\n').filter(Boolean).map(l => `<p>${esc(l)}</p>`).join('') +
    (p.link ? `<p><a href="${esc(p.link[1])}" target="_blank" rel="noopener">${esc(p.link[0])}</a></p>` : '') +
    `<p><a href="${esc(ROOMS[current].page)}">Open the original page</a></p>`;
  overlay.hidden = false;
}
const closeOverlay = () => { overlay.hidden = true; };
document.getElementById('closeOv').onclick = closeOverlay;
overlay.addEventListener('click', e => { if (e.target === overlay) closeOverlay(); });
readBtn.onclick = () => near && openOverlay(near.data);
document.getElementById('jumpBtn').addEventListener('pointerdown', e => { e.preventDefault(); jump(); });
addEventListener('keydown', e => {
  if (e.code === 'KeyE') { if (!overlay.hidden) closeOverlay(); else if (near) openOverlay(near.data); }
  if (e.code === 'Escape') closeOverlay();
  if (e.code === 'Space') { e.preventDefault(); jump(); }
  keys[e.code] = true;
  if (e.code.startsWith('Arrow')) e.preventDefault();
});
addEventListener('keyup', e => { keys[e.code] = false; });
addEventListener('blur', () => { for (const k in keys) keys[k] = false; });

// drag to look (mouse + touch outside joystick)
const joy = document.getElementById('joy'), knob = document.getElementById('knob');
let lookId = null, lx = 0, ly = 0, joyId = null, jx = 0, jy = 0;
const cvs = renderer.domElement;
cvs.addEventListener('pointerdown', e => { lookId = e.pointerId; lx = e.clientX; ly = e.clientY; cvs.setPointerCapture(e.pointerId); });
cvs.addEventListener('pointermove', e => {
  if (e.pointerId !== lookId) return;
  yaw -= (e.clientX - lx) * 0.005; pitch = Math.min(1.2, Math.max(-0.5, pitch + (e.clientY - ly) * 0.004)); lx = e.clientX; ly = e.clientY;
});
cvs.addEventListener('pointerup', e => { if (e.pointerId === lookId) lookId = null; });
joy.addEventListener('pointerdown', e => { joyId = e.pointerId; joy.setPointerCapture(e.pointerId); moveJoy(e); });
joy.addEventListener('pointermove', e => { if (e.pointerId === joyId) moveJoy(e); });
const endJoy = e => { if (e.pointerId === joyId) { joyId = null; jx = jy = 0; knob.style.transform = ''; } };
joy.addEventListener('pointerup', endJoy); joy.addEventListener('pointercancel', endJoy);
function moveJoy(e) {
  const b = joy.getBoundingClientRect(); let dx = e.clientX - (b.left + b.width / 2), dy = e.clientY - (b.top + b.height / 2);
  const d = Math.hypot(dx, dy), m = 45; if (d > m) { dx *= m / d; dy *= m / d; }
  jx = dx / m; jy = dy / m; knob.style.transform = `translate(${dx}px,${dy}px)`;
}

// ---- Loop ----
const clock = new THREE.Clock();
const camPos = new THREE.Vector3();
function tick() {
  const dt = Math.min(clock.getDelta(), 0.05);
  let f = 0, s = 0;
  if (overlay.hidden) {
    if (keys.KeyW || keys.ArrowUp) f += 1; if (keys.KeyS || keys.ArrowDown) f -= 1;
    if (keys.KeyD) s += 1; if (keys.KeyA) s -= 1;
    if (keys.ArrowLeft) yaw += 2.2 * dt; if (keys.ArrowRight) yaw -= 2.2 * dt;
    f -= jy; s += jx;
  }
  const len = Math.hypot(f, s);
  if (len > 0.05) {
    const sp = 5.5 * ((keys.ShiftLeft || keys.ShiftRight) ? 1.8 : 1) * dt * Math.min(1, len) / len;
    const vx = (-Math.sin(yaw) * f + Math.cos(yaw) * s) * sp, vz = (-Math.cos(yaw) * f - Math.sin(yaw) * s) * sp;
    const p = player.position;
    if (!collide(p.x + vx, p.z)) p.x += vx;
    if (!collide(p.x, p.z + vz)) p.z += vz;
    player.rotation.y = Math.atan2(-vx, -vz);
    if (grounded) body.position.y = 0.75 + Math.abs(Math.sin(clock.elapsedTime * 10)) * 0.06;
  }
  vy -= 20 * dt; player.position.y += vy * dt;
  if (player.position.y <= 0) { player.position.y = 0; vy = 0; grounded = true; }
  const id = roomAt(player.position.x, player.position.z); if (id) setRoom(id);
  near = null; let best = 1e9;
  for (const r of readables) { const d = r.pos.distanceTo(new THREE.Vector3(player.position.x, 0, player.position.z)); if (d < (r.r || 2.6) && d < best) { best = d; near = r; } }
  prompt.hidden = !near || !overlay.hidden; readBtn.hidden = !near || !matchMedia('(pointer:coarse)').matches;
  // third-person camera, pulled in if a wall is behind
  let dist = 5;
  const tx = player.position.x, tz = player.position.z;
  for (let d = 0.6; d <= 5; d += 0.2) { if (collide(tx + Math.sin(yaw) * d * Math.cos(pitch), tz + Math.cos(yaw) * d * Math.cos(pitch))) { dist = Math.max(0.6, d - 0.4); break; } }
  camPos.set(tx + Math.sin(yaw) * dist * Math.cos(pitch), 1.4 + Math.sin(pitch) * dist, tz + Math.cos(yaw) * dist * Math.cos(pitch));
  camera.position.copy(camPos); camera.position.y += player.position.y * 0.6; camera.lookAt(tx, 1.4 + player.position.y * 0.6, tz);
  renderer.render(scene, camera);
  requestAnimationFrame(tick);
}
addEventListener('resize', () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });
tick();
const ld = document.getElementById('loading'); ld.style.opacity = 0; setTimeout(() => ld.remove(), 450);
window.__game = { player, teleport, get room() { return current; } };
