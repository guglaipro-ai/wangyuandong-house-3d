// 170 cm 第一人稱漫遊：碰撞、上下樓梯、觸控搖桿與滑鼠視角。
// 眼高依人體計測比例 ≈ 身高 × 0.93（170 cm → 158 cm）。
import * as THREE from 'three';

export const STATURE = 1.70;
export const EYE = 1.58;
const RADIUS = 0.22;        // 肩寬約 44 cm 的碰撞半徑
const STEP = 0.25;          // 可跨越高度：樓梯級高 15.6 cm、玄關台階 14 cm、榻榻米平台 17 cm；茶几、床不可踩上
const WALK = 1.3;           // 一般步行速度 m/s
const RUN = 2.6;
const CELL = 1.0;
const SKIP_KINDS = new Set(['decor', 'ceiling', 'room']);
const FLOOR_BASE = [0.6, 4.8, 8.4, 11.7, 14.8];
const FLOOR_ZH = ['一樓', '二樓', '三樓', '四樓', '屋頂'];
const PLAN = (x, z) => [x + 7.18, z + 8.3];
const WORLD = (x, y) => [x - 7.18, y - 8.3];

// 起點：平面座標(公尺)、腳底高度、面向（0 = 朝平面 -y，即朝建築後方）
export const STARTS = {
  gate: { label: '大門口（戶外）', plan: [8.35, 17.3], feet: 0.02, yaw: 0 },
  f1: { label: '一樓 展覽空間', plan: [5.4, 14.6], feet: 0.62, yaw: 0 },
  f2: { label: '二樓 客廳', plan: [10.6, 11.2], feet: 4.82, yaw: 0.25 },
  f3: { label: '三樓 起居室', plan: [10.2, 9.2], feet: 8.42, yaw: 0.35 },
  f4: { label: '四樓 露台', plan: [3.4, 11.3], feet: 11.72, yaw: 0 },
};

function pointInPoly(x, y, poly) {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i], [xj, yj] = poly[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

// Ericson, Real-Time Collision Detection 5.1.5
function closestOnTri(p, a, b, c, out) {
  const ab = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], ac = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
  const ap = [p[0] - a[0], p[1] - a[1], p[2] - a[2]];
  const dot = (u, v) => u[0] * v[0] + u[1] * v[1] + u[2] * v[2];
  const d1 = dot(ab, ap), d2 = dot(ac, ap);
  if (d1 <= 0 && d2 <= 0) return set(out, a);
  const bp = [p[0] - b[0], p[1] - b[1], p[2] - b[2]];
  const d3 = dot(ab, bp), d4 = dot(ac, bp);
  if (d3 >= 0 && d4 <= d3) return set(out, b);
  const vc = d1 * d4 - d3 * d2;
  if (vc <= 0 && d1 >= 0 && d3 <= 0) { const v = d1 / (d1 - d3); return lerp(out, a, ab, v); }
  const cp = [p[0] - c[0], p[1] - c[1], p[2] - c[2]];
  const d5 = dot(ab, cp), d6 = dot(ac, cp);
  if (d6 >= 0 && d5 <= d6) return set(out, c);
  const vb = d5 * d2 - d1 * d6;
  if (vb <= 0 && d2 >= 0 && d6 <= 0) { const w = d2 / (d2 - d6); return lerp(out, a, ac, w); }
  const va = d3 * d6 - d5 * d4;
  if (va <= 0 && d4 - d3 >= 0 && d5 - d6 >= 0) {
    const w = (d4 - d3) / ((d4 - d3) + (d5 - d6));
    out[0] = b[0] + (c[0] - b[0]) * w; out[1] = b[1] + (c[1] - b[1]) * w; out[2] = b[2] + (c[2] - b[2]) * w; return out;
  }
  const denom = 1 / (va + vb + vc), v = vb * denom, w = vc * denom;
  out[0] = a[0] + ab[0] * v + ac[0] * w; out[1] = a[1] + ab[1] * v + ac[1] * w; out[2] = a[2] + ab[2] * v + ac[2] * w; return out;
  function set(o, s) { o[0] = s[0]; o[1] = s[1]; o[2] = s[2]; return o; }
  function lerp(o, s, d, t) { o[0] = s[0] + d[0] * t; o[1] = s[1] + d[1] * t; o[2] = s[2] + d[2] * t; return o; }
}

class TriGrid {
  constructor(roots) {
    const tris = [];
    const v = new THREE.Vector3();
    for (const root of roots) {
      if (!root) continue;
      root.updateWorldMatrix(true, true);
      root.traverse(o => {
        if (!o.isMesh || !o.geometry?.attributes?.position) return;
        let p = o, hidden = false;
        while (p) { if (p.visible === false) { hidden = true; break; } p = p.parent; }
        if (hidden || SKIP_KINDS.has(o.userData?.kind)) return;
        const pos = o.geometry.attributes.position, idx = o.geometry.index;
        const n = idx ? idx.count : pos.count;
        const tri = [0, 0, 0, 0, 0, 0, 0, 0, 0];
        for (let i = 0; i < n; i += 3) {
          for (let k = 0; k < 3; k++) {
            v.fromBufferAttribute(pos, idx ? idx.getX(i + k) : i + k).applyMatrix4(o.matrixWorld);
            tri[k * 3] = v.x; tri[k * 3 + 1] = v.y; tri[k * 3 + 2] = v.z;
          }
          // Only the reachable site matters for walking; far context is skipped to save phone memory.
          if (Math.hypot((tri[0] + tri[3] + tri[6]) / 3, (tri[2] + tri[5] + tri[8]) / 3) > 32 && Math.max(tri[1], tri[4], tri[7]) > .5) continue;
          tris.push(...tri);
        }
      });
    }
    this.t = new Float32Array(tris);
    this.count = this.t.length / 9;
    this.cells = new Map();
    this.stamp = new Uint32Array(this.count); this.mark = 1;
    const t = this.t;
    for (let i = 0; i < this.count; i++) {
      const o = i * 9;
      const x0 = Math.floor(Math.min(t[o], t[o + 3], t[o + 6]) / CELL), x1 = Math.floor(Math.max(t[o], t[o + 3], t[o + 6]) / CELL);
      const z0 = Math.floor(Math.min(t[o + 2], t[o + 5], t[o + 8]) / CELL), z1 = Math.floor(Math.max(t[o + 2], t[o + 5], t[o + 8]) / CELL);
      if ((x1 - x0) * (z1 - z0) > 4000) continue;  // 過大的遠景地面
      for (let x = x0; x <= x1; x++) for (let z = z0; z <= z1; z++) {
        const k = x * 100003 + z; let a = this.cells.get(k); if (!a) this.cells.set(k, a = []); a.push(i);
      }
    }
  }
  near(x, z, r) {
    const out = []; this.mark++;
    const x0 = Math.floor((x - r) / CELL), x1 = Math.floor((x + r) / CELL), z0 = Math.floor((z - r) / CELL), z1 = Math.floor((z + r) / CELL);
    for (let cx = x0; cx <= x1; cx++) for (let cz = z0; cz <= z1; cz++) {
      const a = this.cells.get(cx * 100003 + cz); if (!a) continue;
      for (const i of a) if (this.stamp[i] !== this.mark) { this.stamp[i] = this.mark; out.push(i); }
    }
    return out;
  }
  // 由上往下的垂直射線：回傳 <= top 的最高可站立面
  ground(x, z, top) {
    let best = -Infinity; const t = this.t;
    for (const i of this.near(x, z, 0)) {
      const o = i * 9;
      const ax = t[o], ay = t[o + 1], az = t[o + 2], bx = t[o + 3], by = t[o + 4], bz = t[o + 5], cx = t[o + 6], cy = t[o + 7], cz = t[o + 8];
      const det = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz);
      if (Math.abs(det) < 1e-10) continue;
      const l1 = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / det;
      const l2 = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / det;
      const l3 = 1 - l1 - l2;
      if (l1 < -1e-6 || l2 < -1e-6 || l3 < -1e-6) continue;
      const y = l1 * ay + l2 * by + l3 * cy;
      if (y <= top && y > best) best = y;
    }
    return best;
  }
  // 以數個球體近似人體，將位置沿水平方向推出牆面／家具
  push(pos, feet) {
    const t = this.t, out = [0, 0, 0], a = [0, 0, 0], b = [0, 0, 0], c = [0, 0, 0];
    const cand = this.near(pos.x, pos.z, RADIUS + 0.05);
    let hit = false;
    for (let iter = 0; iter < 3; iter++) {
      let moved = false;
      for (const h of [STEP + RADIUS - 0.02, 0.95, 1.45]) {
        const p = [pos.x, feet + h, pos.z];
        for (const i of cand) {
          const o = i * 9;
          if (Math.min(t[o + 1], t[o + 4], t[o + 7]) > p[1] + RADIUS || Math.max(t[o + 1], t[o + 4], t[o + 7]) < p[1] - RADIUS) continue;
          a[0] = t[o]; a[1] = t[o + 1]; a[2] = t[o + 2]; b[0] = t[o + 3]; b[1] = t[o + 4]; b[2] = t[o + 5]; c[0] = t[o + 6]; c[1] = t[o + 7]; c[2] = t[o + 8];
          closestOnTri(p, a, b, c, out);
          const dx = p[0] - out[0], dz = p[2] - out[2], dy = p[1] - out[1];
          const d2 = dx * dx + dy * dy + dz * dz;
          if (d2 >= RADIUS * RADIUS) continue;
          const hd = Math.hypot(dx, dz);
          if (hd < 1e-5) continue;
          const d = Math.sqrt(d2), need = RADIUS - d + 0.002;
          pos.x += (dx / hd) * need; pos.z += (dz / hd) * need; p[0] = pos.x; p[2] = pos.z;
          moved = hit = true;
        }
      }
      if (!moved) break;
    }
    return hit;
  }
}

const FLOOR_H = [4.2, 3.6, 3.3, 3.1];

export function createWalk({ camera, controls, canvas, stage, requestRender, getRoots, getRooms, onEnter, onExit, lights = [], lite = false }) {
  let lightKey = '', lightPos = new THREE.Vector3(1e9, 0, 0);
  let active = false, grid = null, feet = 0, vy = 0, yaw = 0, pitch = -0.05, saved = null, eyeY = 0;
  const pos = new THREE.Vector3();
  const vel = new THREE.Vector2();   // 水平速度 (world x, z)，加減速使起步與停步自然
  const keys = new Set();
  const joy = { id: null, x: 0, y: 0, ox: 0, oy: 0 };
  let look = null, running = false, lastRoom = '';

  const css = document.createElement('style');
  css.textContent = `.walk-hud{position:absolute;inset:0;pointer-events:none;z-index:4;display:none}.walk-hud.on{display:block}
.walk-bar{position:absolute;top:10px;right:10px;display:flex;flex-wrap:wrap;gap:6px;justify-content:flex-end;max-width:70%;pointer-events:auto}
.walk-bar button{font:12px system-ui,"Microsoft JhengHei",sans-serif;border:1px solid #c7d0c5;background:#fbfaf5ee;color:#23483b;border-radius:16px;padding:7px 11px;min-height:34px;cursor:pointer}
.walk-bar button.exit{background:#23483b;color:#fff;border-color:#23483b}
.walk-info{position:absolute;left:12px;top:10px;background:#fbfaf5e6;border:1px solid #d3d8cc;border-radius:8px;padding:6px 10px;font:12px/1.5 system-ui,"Microsoft JhengHei",sans-serif;color:#23483b}
.walk-info b{font-size:14px;display:block}
.walk-joy{position:absolute;left:22px;bottom:26px;width:118px;height:118px;border-radius:50%;background:#ffffff55;border:2px solid #ffffffaa;box-shadow:0 2px 12px #0002;pointer-events:auto;touch-action:none}
.walk-joy i{position:absolute;left:39px;top:39px;width:40px;height:40px;border-radius:50%;background:#23483bcc}
.walk-help{position:absolute;right:12px;bottom:12px;background:#fbfaf5dd;border-radius:6px;padding:5px 8px;font:11px system-ui,"Microsoft JhengHei",sans-serif;color:#51645a}
.walk-cross{position:absolute;left:50%;top:50%;width:6px;height:6px;margin:-3px;border-radius:50%;background:#ffffffcc;box-shadow:0 0 0 1px #0004}
@media(max-width:700px){.walk-bar{max-width:62%}.walk-bar button{padding:5px 8px;font-size:11px;min-height:30px}.walk-joy{width:96px;height:96px;left:14px;bottom:16px}.walk-joy i{left:28px;top:28px}.walk-help{display:none}}`;
  document.head.appendChild(css);
  const hud = document.createElement('div'); hud.className = 'walk-hud';
  hud.innerHTML = `<div class="walk-info" aria-live="polite"><b id="walk-room">—</b><span>身高 170 cm · 眼高 158 cm</span></div>
<div class="walk-bar"></div><div class="walk-cross"></div><div class="walk-joy" aria-label="移動搖桿"><i></i></div>
<div class="walk-help">W A S D／方向鍵移動 · 拖曳轉頭 · Shift 快走 · 雙擊地面前往</div>`;
  stage.appendChild(hud);
  const bar = hud.querySelector('.walk-bar'), roomEl = hud.querySelector('#walk-room'), joyEl = hud.querySelector('.walk-joy'), knob = joyEl.querySelector('i');
  const addBtn = (text, fn, cls) => { const b = document.createElement('button'); b.type = 'button'; b.textContent = text; if (cls) b.className = cls; b.addEventListener('click', fn); bar.appendChild(b); return b; };
  for (const [k, s] of Object.entries(STARTS)) addBtn(s.label.split(' ')[0].replace('（戶外）', ''), () => teleport(k));
  addBtn('離開漫遊', () => exit(), 'exit');

  function rebuild() {
    grid = new TriGrid(getRoots());
    return grid.count;
  }
  function teleport(key) {
    const s = STARTS[key];
    const [x, z] = WORLD(...s.plan);
    pos.set(x, 0, z); feet = s.feet; vy = 0; yaw = s.yaw; pitch = -0.06; vel.set(0, 0);
    if (grid) { const g = grid.ground(x, z, feet + STEP); if (g > -Infinity) feet = g; }
    apply(true); requestRender();
  }
  // 眼高平滑：上下樓梯時視線不隨每一階跳動（真人步行時頭部高度變化遠小於踏階）。
  function apply(snap = false, dt = 0) {
    const target = feet + EYE;
    if (snap || Math.abs(target - eyeY) > 0.6) eyeY = target;
    else eyeY += (target - eyeY) * (1 - Math.exp(-dt * 12));
    camera.position.set(pos.x, eyeY, pos.z);
    camera.rotation.set(pitch, yaw, 0, 'YXZ');
    camera.updateMatrixWorld();
    updateRoom();
  }
  function currentFloor() {
    let f = 0; for (let i = 0; i < FLOOR_BASE.length; i++) if (feet >= FLOOR_BASE[i] - 0.35) f = i;
    return feet < 0.45 ? -1 : f;
  }
  function updateRoom() {
    const [px, py] = PLAN(pos.x, pos.z), f = currentFloor();
    let label = f < 0 ? '戶外基地' : FLOOR_ZH[f];
    const inCore = px > 6.7 && px < 11.9 && py > 0 && py < 4.4 && !(px > 8.1 && px < 10.3 && py > 1.5 && py < 3.7);
    if (f >= 0 && inCore && f < 3) label = `${FLOOR_ZH[f]}→${FLOOR_ZH[f + 1]} · 樓梯`;
    else if (f >= 0) {
      const room = getRooms().find(r => r.floor === f + 1 && r.polygon && pointInPoly(px, py, r.polygon));
      label += ' · ' + (room ? room.label : (f === 0 && feet < 0.6 ? '門廊' : '陽台／走道'));
    }
    if (label !== lastRoom) { roomEl.textContent = label; lastRoom = label; }
    placeLights(f, px, py);
  }
  // Ceiling lights of the current room: a grid at about 1.8 m spacing inside the room
  // polygon, nearest points first (same spacing as the modelled downlights).
  function placeLights(f, px, py) {
    if (!lights.length) return;
    const room = f >= 0 && f < 4 ? getRooms().find(r => r.floor === f + 1 && r.polygon && pointInPoly(px, py, r.polygon)) : null;
    const key = room ? room.floor + room.label : 'none';
    if (key === lightKey && camera.position.distanceTo(lightPos) < 1.2) return;
    lightKey = key; lightPos.copy(camera.position);
    if (!room) { lights.forEach(l => { l.intensity = 0; }); return; }
    const xs = room.polygon.map(p => p[0]), ys = room.polygon.map(p => p[1]);
    const pts = [];
    for (let x = Math.min(...xs) + .7; x < Math.max(...xs) - .3; x += 1.8)
      for (let y = Math.min(...ys) + .7; y < Math.max(...ys) - .3; y += 1.8)
        if (pointInPoly(x, y, room.polygon)) pts.push([x, y]);
    if (!pts.length) pts.push([(Math.min(...xs) + Math.max(...xs)) / 2, (Math.min(...ys) + Math.max(...ys)) / 2]);
    pts.sort((a, b) => Math.hypot(a[0] - px, a[1] - py) - Math.hypot(b[0] - px, b[1] - py));
    const z = FLOOR_BASE[f] + FLOOR_H[f] - .55;
    lights.forEach((l, i) => {
      const p = pts[i];
      if (!p) { l.intensity = 0; return; }
      const [x, wz] = WORLD(p[0], p[1]); l.position.set(x, z, wz); l.intensity = lite ? 9 : 6;
    });
    requestRender();
  }

  function enter(key = 'gate') {
    if (active) { teleport(key); return; }
    saved = { pos: camera.position.clone(), quat: camera.quaternion.clone(), fov: camera.fov, near: camera.near, target: controls.target.clone() };
    active = true; controls.enabled = false;
    onEnter?.();
    rebuild();
    camera.fov = 68; camera.near = 0.05; camera.updateProjectionMatrix();
    hud.classList.add('on');
    teleport(key);
  }
  function exit() {
    if (!active) return;
    active = false; keys.clear(); joy.id = null; knob.style.transform = ''; lightKey = '';
    hud.classList.remove('on');
    camera.fov = saved.fov; camera.near = saved.near; camera.position.copy(saved.pos); camera.quaternion.copy(saved.quat);
    camera.updateProjectionMatrix(); controls.target.copy(saved.target); controls.enabled = true; controls.update();
    onExit?.(); requestRender();
  }

  // ---- 輸入 ----
  addEventListener('keydown', e => {
    if (!active || e.target.closest?.('input,select,textarea')) return;
    const k = e.key.toLowerCase();
    if (['w', 'a', 's', 'd', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright', 'shift'].includes(k)) { keys.add(k); e.preventDefault(); requestRender(); }
    if (k === 'escape') exit();
  });
  addEventListener('keyup', e => keys.delete(e.key.toLowerCase()));
  addEventListener('blur', () => keys.clear());
  canvas.addEventListener('pointerdown', e => {
    if (!active || look) return;
    look = { id: e.pointerId, x: e.clientX, y: e.clientY }; canvas.setPointerCapture?.(e.pointerId);
  });
  canvas.addEventListener('pointermove', e => {
    if (!active || !look || look.id !== e.pointerId) return;
    const s = e.pointerType === 'touch' ? 0.0055 : 0.0042;
    yaw -= (e.clientX - look.x) * s; pitch = Math.max(-1.35, Math.min(1.35, pitch - (e.clientY - look.y) * s));
    look.x = e.clientX; look.y = e.clientY; apply(); requestRender();
  });
  const endLook = e => { if (look && look.id === e.pointerId) look = null; };
  canvas.addEventListener('pointerup', endLook); canvas.addEventListener('pointercancel', endLook);
  canvas.addEventListener('dblclick', e => {
    if (!active) return;
    const r = canvas.getBoundingClientRect();
    const ray = new THREE.Raycaster(); vel.set(0, 0); ray.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), camera);
    const hit = ray.intersectObjects(getRoots().filter(Boolean), true).find(h => h.object.visible && h.face && h.face.normal.clone().transformDirection(h.object.matrixWorld).y > 0.7);
    if (!hit || hit.distance > 18) return;
    const g = grid.ground(hit.point.x, hit.point.z, hit.point.y + 0.05);
    if (g === -Infinity) return;
    pos.x = hit.point.x; pos.z = hit.point.z; feet = g; grid.push(pos, feet); apply(true); requestRender();
  });
  joyEl.addEventListener('pointerdown', e => {
    e.stopPropagation(); joy.id = e.pointerId; const r = joyEl.getBoundingClientRect();
    joy.ox = r.left + r.width / 2; joy.oy = r.top + r.height / 2; joyEl.setPointerCapture?.(e.pointerId); joyMove(e);
  });
  const joyMove = e => {
    if (joy.id !== e.pointerId) return;
    const max = joyEl.clientWidth / 2 - 10;
    let dx = e.clientX - joy.ox, dy = e.clientY - joy.oy; const l = Math.hypot(dx, dy);
    if (l > max) { dx *= max / l; dy *= max / l; }
    joy.x = dx / max; joy.y = dy / max; knob.style.transform = `translate(${dx}px,${dy}px)`; requestRender();
  };
  joyEl.addEventListener('pointermove', joyMove);
  const joyEnd = e => { if (joy.id === e.pointerId) { joy.id = null; joy.x = joy.y = 0; knob.style.transform = ''; } };
  joyEl.addEventListener('pointerup', joyEnd); joyEl.addEventListener('pointercancel', joyEnd);

  // ---- 每幀 ----
  function update(dt) {
    if (!active || !grid) return false;
    dt = Math.min(dt, 0.05);
    let f = 0, s = 0;
    if (keys.has('w') || keys.has('arrowup')) f += 1;
    if (keys.has('s') || keys.has('arrowdown')) f -= 1;
    if (keys.has('d')) s += 1; if (keys.has('a')) s -= 1;
    if (keys.has('arrowleft')) yaw += 1.6 * dt; if (keys.has('arrowright')) yaw -= 1.6 * dt;
    if (joy.id !== null) { f -= joy.y; s += joy.x; }
    running = keys.has('shift') || Math.hypot(joy.x, joy.y) > 0.95;
    const mag = Math.hypot(f, s);
    let moving = keys.has('arrowleft') || keys.has('arrowright');
    let tx = 0, tz = 0;
    if (mag > 0.05) {
      const sp = (running ? RUN : WALK) * Math.min(1, mag) / Math.max(1, mag);
      const sin = Math.sin(yaw), cos = Math.cos(yaw);
      // 前進方向 = 相機 -Z
      tx = (-sin * f + cos * s) * sp; tz = (-cos * f - sin * s) * sp;
    }
    // 約 0.15 s 達到步行速度、0.1 s 停下
    const k = 1 - Math.exp(-dt * (mag > 0.05 ? 14 : 20));
    vel.x += (tx - vel.x) * k; vel.y += (tz - vel.y) * k;
    if (mag <= 0.05 && vel.lengthSq() < 1e-4) vel.set(0, 0);
    if (vel.x || vel.y) {
      const ox = pos.x, oz = pos.z;
      pos.x += vel.x * dt; pos.z += vel.y * dt;
      grid.push(pos, feet);
      const g = grid.ground(pos.x, pos.z, feet + STEP);
      if (g === -Infinity || g < feet - 2.5) { pos.x = ox; pos.z = oz; vel.set(0, 0); }  // 不走出模型或掉落
      else if (dt > 0) {
        // 貼牆時只保留沿牆分量，避免持續頂牆造成抖動
        const ax = (pos.x - ox) / dt, az = (pos.z - oz) / dt;
        if (ax * ax + az * az < vel.lengthSq()) vel.set(ax, az);
      }
      moving = true;
    }
    const g = grid.ground(pos.x, pos.z, feet + STEP);
    if (g > -Infinity) {
      if (g >= feet - 0.02) {
        const before = feet;
        feet = g > feet ? Math.min(g, feet + dt * 3.2 + 0.02) : g;  // 平順上階
        vy = 0; if (Math.abs(feet - before) > 0.002 || g > feet) moving = true;
      }
      else if (vy === 0 && feet - g <= STEP + 0.02) { feet = Math.max(g, feet - dt * 3.2 - 0.02); moving = true; }  // 平順下階
      else { vy -= 9.8 * dt; feet = Math.max(g, feet + vy * dt); if (feet === g) vy = 0; moving = true; }
    }
    if (Math.abs(feet + EYE - eyeY) > 0.002) moving = true;
    apply(false, dt);
    return moving;
  }

  return {
    enter, exit, teleport, update, rebuild,
    get active() { return active; },
    state() { const [x, y] = PLAN(pos.x, pos.z); return { active, plan: [x, y], feet, eye: feet + EYE, yaw, pitch, room: lastRoom, triangles: grid?.count || 0 }; },
    press(k, on) { on ? keys.add(k) : keys.delete(k); requestRender(); },
    look(y, p = pitch) { yaw = y; pitch = p; requestRender(); },
    place(px, py, f, y = yaw, p = pitch) { const [x, z] = WORLD(px, py); pos.set(x, 0, z); feet = f; yaw = y; pitch = p; vy = 0; vel.set(0, 0); apply(true); requestRender(); },
  };
}
