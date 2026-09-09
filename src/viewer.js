/* eslint-disable */
// 龍泉畫苑 — 離線獨立住宅 GLB 檢視器
// 由打包工具 (esbuild) 內嵌 three 與 GLB，之後成為單一離線檔案。
// 僅實作此檔；HTML DOM (#controls / #status / #canvas / #model-data) 由父層提供。

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

// ---------------------------------------------------------------------------
// 常數
// ---------------------------------------------------------------------------
const GROUP_NAMES = ['SITE', 'FLOOR_1', 'FLOOR_2', 'FLOOR_3', 'FLOOR_4', 'ROOF'];
const FLOOR_GROUPS = ['FLOOR_1', 'FLOOR_2', 'FLOOR_3', 'FLOOR_4'];
// 會被剖面 (cutaway) 裁切的 mesh 種類 — 依 userData.kind 判斷
const CLIPPABLE_KINDS = new Set(['wall', 'door', 'window', 'column']);
const CUTAWAY_OFFSET = 1.25; // 樓層底部往上 1.25 公尺
const PIXEL_RATIO_CAP = 1.5;
const STYLE_NAMES = {original:'原始空屋',bohemian:'波西米亞',industrial:'工業 Loft',eclectic:'折衷混搭',wabisabi:'侘寂'};
let activeStyle='original';
let styleSelect=null;
let pendingStyle='original';

// ---------------------------------------------------------------------------
// DOM 參照
// ---------------------------------------------------------------------------
const controlsEl = document.getElementById('controls');
const statusEl = document.getElementById('status');
const canvasEl = document.getElementById('canvas');

function setStatus(msg, isError) {
  if (statusEl) {
    statusEl.textContent = msg;
    statusEl.classList.toggle('error', !!isError);
  }
  if (isError) console.error('[houseViewer]', msg);
}

function fatal(msg, err) {
  setStatus(msg, true);
  if(styleSelect){styleSelect.disabled=false;styleSelect.value=activeStyle;}
  if (err) console.error(err);
}

// ---------------------------------------------------------------------------
// base64 -> ArrayBuffer
// ---------------------------------------------------------------------------
function base64ToArrayBuffer(b64) {
  const clean = (b64 || '').replace(/[\s]/g, '');
  const binary = atob(clean);
  const len = binary.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

// ---------------------------------------------------------------------------
// WebGL 支援偵測
// ---------------------------------------------------------------------------
function webglAvailable() {
  try {
    const c = document.createElement('canvas');
    return !!(
      window.WebGLRenderingContext &&
      (c.getContext('webgl2') || c.getContext('webgl') || c.getContext('experimental-webgl'))
    );
  } catch (e) {
    return false;
  }
}

// ---------------------------------------------------------------------------
// 主要狀態
// ---------------------------------------------------------------------------
let renderer, scene, camera, controls, gltf;
let rootModel = null;
const groupObjects = {}; // name -> Object3D
let roomLabelDefs = []; // { object, el, worldPos, floorName }
let labelLayer = null; // HTML overlay 容器

let cutawayEnabled = false;
let cutawayFloor = 'FLOOR_1';
let sectionEnabled = false; // 進階：局部裁面 (local clipping plane)
const sectionPlane = new THREE.Plane(new THREE.Vector3(0, -1, 0), 0);

let showRoomLabels = false;
let soloFloorForLabels = null; // 標籤 solo 模式時暫存原本可見狀態

let needsRender = true;
function requestRender() {
  needsRender = true;
}

// 儲存每個樓層群組的底部世界高度
const floorBaseY = {};
let modelBox = new THREE.Box3();

// ---------------------------------------------------------------------------
// 初始化
// ---------------------------------------------------------------------------
function init() {
  if (!controlsEl || !statusEl || !canvasEl) {
    fatal('缺少必要的 DOM 容器 (#controls / #status / #canvas)。');
    return;
  }
  if (!webglAvailable()) {
    fatal('您的瀏覽器或裝置不支援 WebGL，無法顯示 3D 模型。');
    return;
  }

  setStatus('正在初始化檢視器…');

  try {
    renderer = new THREE.WebGLRenderer({
      canvas: canvasEl,
      antialias: true,
      alpha: false,
      powerPreference: 'high-performance',
    });
  } catch (e) {
    fatal('無法建立 WebGL 繪圖環境。', e);
    return;
  }

  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, PIXEL_RATIO_CAP));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.localClippingEnabled = true;

  renderer.domElement.addEventListener('webglcontextlost', (ev) => {
    ev.preventDefault();
    fatal('WebGL 繪圖環境已中斷 (context lost)，請重新整理頁面。');
  });

  scene = new THREE.Scene();
  // 中性暖色背景
  scene.background = new THREE.Color(0xf3ede2);

  camera = new THREE.PerspectiveCamera(50, getAspect(), 0.1, 5000);
  camera.position.set(18, 14, 22);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.screenSpacePanning = false;
  controls.minDistance = 1;
  controls.maxDistance = 500;
  controls.maxPolarAngle = Math.PI * 0.495;
  // 觸控：單指旋轉、雙指縮放/平移
  controls.touches = {
    ONE: THREE.TOUCH.ROTATE,
    TWO: THREE.TOUCH.DOLLY_PAN,
  };
  controls.addEventListener('change', requestRender);

  // 燈光（唯一允許建立的物件類型）
  const hemiLight = new THREE.HemisphereLight(0xfff4e2, 0x5b5349, 0.9);
  hemiLight.position.set(0, 50, 0);
  scene.add(hemiLight);

  const dirLight = new THREE.DirectionalLight(0xfff1dc, 1.1);
  dirLight.position.set(30, 45, 20);
  dirLight.castShadow = false;
  scene.add(dirLight);

  const dirLight2 = new THREE.DirectionalLight(0xdfe6ef, 0.35);
  dirLight2.position.set(-25, 20, -18);
  scene.add(dirLight2);

  buildUI();
  buildLabelLayer();
  loadModel();

  // 尺寸監看
  if (typeof ResizeObserver !== 'undefined') {
    const ro = new ResizeObserver(() => onResize());
    ro.observe(canvasEl.parentElement || canvasEl);
  }
  window.addEventListener('resize', onResize);
  document.addEventListener('fullscreenchange', () => {
    onResize();
    updateFullscreenLabel();
  });

  onResize();
  animate();

  window.houseViewer = { scene, camera, controls, gltf: null, render: renderOnce };
}

function getContainer() {
  return canvasEl.parentElement || canvasEl;
}

function getAspect() {
  const el = getContainer();
  const w = el.clientWidth || window.innerWidth;
  const h = el.clientHeight || window.innerHeight;
  return w / Math.max(1, h);
}

// ---------------------------------------------------------------------------
// 模型載入
// ---------------------------------------------------------------------------
async function loadModel(style='original') {
  pendingStyle=style;
  if(styleSelect)styleSelect.disabled=true;
  setStatus('正在載入'+STYLE_NAMES[style]+'…');
  const dataEl = document.getElementById(style==='original'?'model-data':'model-'+style);
  let buffer;
  try {
    if(dataEl?.textContent?.trim())buffer=base64ToArrayBuffer(dataEl.textContent);
    else{
      const response=await fetch('styles/'+style+'.glb');
      if(!response.ok)throw new Error('HTTP '+response.status);
      buffer=await response.arrayBuffer();
    }
  } catch (e) {
    fatal('方案載入失敗，請確認網路後重新選取。', e);
    return;
  }

  setStatus('正在解析模型…');
  const loader = new GLTFLoader();
  try {
    loader.parse(
      buffer,
      '',
      (result) => {
        try {
          onModelLoaded(result);
        } catch (e) {
          fatal('模型載入後處理發生錯誤。', e);
        }
      },
      (err) => {
        fatal('模型解析失敗，GLB 檔可能已損毀。', err);
      }
    );
  } catch (e) {
    fatal('模型解析時發生例外。', e);
  }
}

function onModelLoaded(result) {
  const replacement=!!rootModel;
  if(rootModel){
    scene.remove(rootModel);
    rootModel.traverse(o=>{if(o.isMesh){o.geometry?.dispose();const mats=Array.isArray(o.material)?o.material:[o.material];mats.forEach(m=>m?.dispose());}});
    if(labelLayer)labelLayer.innerHTML='';
    GROUP_NAMES.forEach(n=>delete groupObjects[n]);
  }
  activeStyle=pendingStyle;
  if(styleSelect){styleSelect.value=activeStyle;styleSelect.disabled=false;}
  gltf = result;
  rootModel = result.scene || (result.scenes && result.scenes[0]);
  if (!rootModel) {
    fatal('GLB 內未包含任何場景。');
    return;
  }
  scene.add(rootModel);
  rootModel.traverse(o => {
    if (o.isMesh && o.material) o.material = Array.isArray(o.material) ? o.material.map(m=>m.clone()) : o.material.clone();
  });

  // 蒐集群組
  rootModel.updateWorldMatrix(true, true);
  GROUP_NAMES.forEach((name) => {
    const obj = rootModel.getObjectByName(name);
    if (obj) {
      groupObjects[name] = obj;
      obj.visible = true; // 初始全部可見
    }
  });

  // 蒐集房間標籤節點 ROOM_*
  roomLabelDefs = [];
  rootModel.traverse((o) => {
    if (o.name && /^ROOM_/i.test(o.name)) {
      const worldPos = new THREE.Vector3();
      o.getWorldPosition(worldPos);
      const label =
        (o.userData && (o.userData.label || o.userData.name)) ||
        o.name.replace(/^ROOM_/i, '').replace(/_/g, ' ');
      roomLabelDefs.push({
        object: o,
        label: String(label),
        worldPos,
        floorName: findFloorGroupOf(o),
        el: null,
      });
    }
  });

  computeFloorBases();
  createLabelElements();

  // 置中與鏡頭
  modelBox.setFromObject(rootModel);
  frameModel();

  // 套用初始剖面/裁面狀態
  applyClipping();

  setStatus(STYLE_NAMES[activeStyle]+' · '+(activeStyle==='original'?'原建築配置':'家具與材質配置提案'));
  window.houseViewer = { scene, camera, controls, gltf, render: renderOnce, style:activeStyle };
  const link=document.getElementById('download');
  if(link){const embed=document.getElementById(activeStyle==='original'?'model-data':'model-'+activeStyle);link.href=embed?'data:model/gltf-binary;base64,'+embed.textContent.trim():'styles/'+activeStyle+'.glb';link.download=activeStyle==='original'?'house.glb':'house-'+activeStyle+'.glb';}
  if(replacement && activeStyle!=='original')soloFloor('FLOOR_2');
  else if(replacement)showAll();
  requestRender();
}

function findFloorGroupOf(obj) {
  let p = obj;
  while (p) {
    if (p.name && GROUP_NAMES.indexOf(p.name) !== -1) return p.name;
    p = p.parent;
  }
  return null;
}

function computeFloorBases() {
  GROUP_NAMES.forEach((name) => {
    const obj = groupObjects[name];
    if (!obj) return;
    const box = new THREE.Box3().setFromObject(obj);
    if (box.isEmpty()) return;
    floorBaseY[name] = Number.isFinite(obj.userData.base) ? obj.userData.base : box.min.y;
  });
  // 若某樓層缺資料，用等距推估
  const known = FLOOR_GROUPS.filter((n) => floorBaseY[n] != null).map((n) => floorBaseY[n]);
  if (known.length >= 2) {
    const step = (Math.max.apply(null, known) - Math.min.apply(null, known)) / (known.length - 1);
    FLOOR_GROUPS.forEach((n, i) => {
      if (floorBaseY[n] == null) floorBaseY[n] = Math.min.apply(null, known) + step * i;
    });
  }
}

function frameModel(targetObject = null, top = false) {
  if (targetObject) modelBox.setFromObject(targetObject);
  else {
    modelBox.makeEmpty();
    FLOOR_GROUPS.concat('ROOF').forEach(n=>{if(groupObjects[n])modelBox.union(new THREE.Box3().setFromObject(groupObjects[n]));});
  }
  if (modelBox.isEmpty()) return;
  const size = modelBox.getSize(new THREE.Vector3());
  const center = modelBox.getCenter(new THREE.Vector3());
  const maxDim = Math.max(size.x, size.y, size.z);
  const fitDist = maxDim / (2 * Math.tan((Math.PI * camera.fov) / 360)) / Math.min(1,camera.aspect);
  const dir = top ? new THREE.Vector3(0,1,.001) : new THREE.Vector3(1,0.82,1).normalize();

  controls.target.copy(center);
  camera.position.copy(center).add(dir.multiplyScalar(fitDist * 1.65));
  camera.near = Math.max(0.05, maxDim / 1000);
  camera.far = maxDim * 50;
  camera.updateProjectionMatrix();
  controls.maxDistance = maxDim * 12;
  controls.update();
  requestRender();
}

// ---------------------------------------------------------------------------
// UI
// ---------------------------------------------------------------------------
function el(tag, props, children) {
  const n = document.createElement(tag);
  if (props) Object.keys(props).forEach((k) => {
    if (k === 'class') n.className = props[k];
    else if (k === 'text') n.textContent = props[k];
    else n.setAttribute(k, props[k]);
  });
  (children || []).forEach((c) => n.appendChild(c));
  return n;
}

const groupCheckboxes = {};
let fullscreenBtn = null;
let cutawayToggle = null;
let cutawaySlider = null;
let cutawayFloorSelect = null;
let sectionToggle = null;
let labelToggle = null;

function buildUI() {
  controlsEl.innerHTML = '';
  const styleSection=el('div',{class:'hv-section hv-style'},[el('h3',{text:'風格與家具 · 3D 切換'})]);
  styleSelect=el('select',{id:'hv-style','aria-label':'風格與家具方案'});
  Object.entries(STYLE_NAMES).forEach(([value,text])=>styleSelect.appendChild(el('option',{value,text})));
  styleSelect.addEventListener('change',()=>loadModel(styleSelect.value));
  styleSection.appendChild(styleSelect);
  styleSection.appendChild(makeButton('二樓室內視角',()=>{
    soloFloor('FLOOR_2');
    cutawayEnabled=false;sectionEnabled=false;cutawayToggle.checked=false;sectionToggle.checked=false;applyClipping();
    showRoomLabels=false;labelToggle.checked=false;updateLabels();
    camera.position.set(.27,6.4,2.5);controls.target.set(3.12,5.85,-.8);controls.update();requestRender();
  }));
  controlsEl.appendChild(styleSection);

  // --- 群組顯示 ---
  const groupSection = el('div', { class: 'hv-section' }, [
    el('h3', { text: '樓層與區塊顯示' }),
  ]);
  groupSection.classList.add('hv-groups');
  const groupLabelZh = {
    SITE: '基地', FLOOR_1: '一樓', FLOOR_2: '二樓', FLOOR_3: '三樓', FLOOR_4: '四樓', ROOF: '屋頂',
  };
  GROUP_NAMES.forEach((name) => {
    const cb = el('input', { type: 'checkbox', id: 'hv-grp-' + name });
    cb.checked = true;
    cb.addEventListener('change', () => {
      const obj = groupObjects[name];
      if (obj) obj.visible = cb.checked;
      updateLabels();
      requestRender();
    });
    groupCheckboxes[name] = cb;
    const row = el('label', { class: 'hv-row' }, [cb, el('span', { text: groupLabelZh[name] })]);
    groupSection.appendChild(row);
  });
  controlsEl.appendChild(groupSection);

  // --- 快速檢視按鈕 ---
  const viewSection = el('div', { class: 'hv-section' }, [el('h3', { text: '快速檢視' })]);
  viewSection.appendChild(makeButton('顯示全部', () => showAll()));
  viewSection.appendChild(makeButton('只看一樓', () => soloFloor('FLOOR_1')));
  viewSection.appendChild(makeButton('只看二樓', () => soloFloor('FLOOR_2')));
  viewSection.appendChild(makeButton('只看三樓', () => soloFloor('FLOOR_3')));
  viewSection.appendChild(makeButton('只看四樓', () => soloFloor('FLOOR_4')));
  viewSection.appendChild(makeButton('重設視角', () => frameModel()));
  viewSection.appendChild(makeButton('俯視', () => {
    const visible=FLOOR_GROUPS.filter(n=>groupObjects[n]?.visible);
    frameModel(visible.length===1?groupObjects[visible[0]]:null,true);
  }));
  controlsEl.appendChild(viewSection);

  // --- 剖面 (cutaway) ---
  const cutSection = el('div', { class: 'hv-section' }, [el('h3', { text: '查看室內' })]);
  cutawayToggle = el('input', { type: 'checkbox', id: 'hv-cutaway' });
  cutawayToggle.addEventListener('change', () => {
    cutawayEnabled = cutawayToggle.checked;
    applyClipping();
    requestRender();
  });
  cutSection.appendChild(
    el('label', { class: 'hv-row' }, [cutawayToggle, el('span', { text: '剖開牆面' })])
  );

  cutawayFloorSelect = el('select', { id: 'hv-cutaway-floor' });
  FLOOR_GROUPS.forEach((n, i) => {
    const opt = el('option', { value: n, text: ['一樓', '二樓', '三樓', '四樓'][i] });
    cutawayFloorSelect.appendChild(opt);
  });
  cutawayFloorSelect.addEventListener('change', () => {
    cutawayFloor = cutawayFloorSelect.value;
    applyClipping();
    requestRender();
  });
  cutSection.appendChild(el('label', { class: 'hv-row' }, [el('span', { text: '剖切樓層：' }), cutawayFloorSelect]));

  cutawaySlider = el('input', { type: 'range', id: 'hv-cutaway-h', min: '0', max: '3', step: '0.05', value: String(CUTAWAY_OFFSET) });
  cutawaySlider.addEventListener('input', () => {
    applyClipping();
    requestRender();
  });
  cutSection.appendChild(
    el('label', { class: 'hv-row' }, [el('span', { text: '保留牆高' }), cutawaySlider])
  );

  sectionToggle = el('input', { type: 'checkbox', id: 'hv-section' });
  sectionToggle.addEventListener('change', () => {
    sectionEnabled = sectionToggle.checked;
    applyClipping();
    requestRender();
  });
  cutSection.appendChild(
    el('label', { class: 'hv-row' }, [sectionToggle, el('span', { text: '同時剖開欄杆與其他構件' })])
  );
  controlsEl.appendChild(cutSection);

  // --- 房間標籤 ---
  const labelSection = el('div', { class: 'hv-section' }, [el('h3', { text: '房間資訊' })]);
  labelToggle = el('input', { type: 'checkbox', id: 'hv-labels' });
  labelToggle.addEventListener('change', () => {
    showRoomLabels = labelToggle.checked;
    updateLabels();
    requestRender();
  });
  labelSection.appendChild(
    el('label', { class: 'hv-row' }, [labelToggle, el('span', { text: '顯示房間標籤' })])
  );
  controlsEl.appendChild(labelSection);

  // --- 全螢幕 ---
  const fsSupported =
    document.fullscreenEnabled ||
    getContainer().requestFullscreen ||
    getContainer().webkitRequestFullscreen;
  if (fsSupported) {
    const fsSection = el('div', { class: 'hv-section' });
    fullscreenBtn = makeButton('全螢幕', () => toggleFullscreen());
    fsSection.appendChild(fullscreenBtn);
    controlsEl.appendChild(fsSection);
  }
}

function makeButton(label, onClick) {
  const b = el('button', { type: 'button', class: 'hv-btn', text: label });
  b.addEventListener('click', onClick);
  return b;
}

// ---------------------------------------------------------------------------
// 檢視操作
// ---------------------------------------------------------------------------
function showAll() {
  cutawayEnabled=false;sectionEnabled=false;cutawayToggle.checked=false;sectionToggle.checked=false;
  applyClipping();frameModel();
  soloFloorForLabels = null;
  GROUP_NAMES.forEach((name) => {
    const obj = groupObjects[name];
    if (obj) obj.visible = true;
    if (groupCheckboxes[name]) groupCheckboxes[name].checked = true;
  });
  updateLabels();
  requestRender();
}

function soloFloor(floorName) {
  soloFloorForLabels = null;
  GROUP_NAMES.forEach((name) => {
    const visible = name === floorName || name === 'SITE';
    const obj = groupObjects[name];
    if (obj) obj.visible = visible;
    if (groupCheckboxes[name]) groupCheckboxes[name].checked = visible;
  });
  cutawayFloor=floorName;cutawayFloorSelect.value=floorName;
  cutawayEnabled=true;cutawayToggle.checked=true;sectionEnabled=false;sectionToggle.checked=false;
  showRoomLabels=true;labelToggle.checked=true;applyClipping();
  frameModel(groupObjects[floorName],true);
  updateLabels();
  requestRender();
}

// ---------------------------------------------------------------------------
// 剖面 / 裁切
// ---------------------------------------------------------------------------
function applyClipping() {
  if (!rootModel) return;

  const base = floorBaseY[cutawayFloor] != null ? floorBaseY[cutawayFloor] : 0;
  const sliderH = cutawaySlider ? parseFloat(cutawaySlider.value) : CUTAWAY_OFFSET;
  const cutHeight = base + (isFinite(sliderH) ? sliderH : CUTAWAY_OFFSET);

  // 進階水平裁面：對整個模型使用 local clipping plane
  sectionPlane.constant = cutHeight;
  const globalPlanes = sectionEnabled ? [sectionPlane] : [];

  rootModel.traverse((o) => {
    if (!o.isMesh || !o.material) return;
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    const kind = o.userData && o.userData.kind;
    const isClippable = kind && CLIPPABLE_KINDS.has(String(kind).toLowerCase());

    mats.forEach((m) => {
      // 進階裁面：作用於所有幾何
      if (sectionEnabled) {
        m.clippingPlanes = globalPlanes;
        m.clipShadows = true;
      } else if (cutawayEnabled && isClippable) {
        // cutaway：只裁切 牆/門/窗/柱
        m.clippingPlanes = [sectionPlane];
      } else {
        m.clippingPlanes = null;
      }
      m.needsUpdate = true;
    });
  });
}

// ---------------------------------------------------------------------------
// 房間標籤 (投影 HTML)
// ---------------------------------------------------------------------------
function buildLabelLayer() {
  labelLayer = el('div', { class: 'hv-label-layer' });
  labelLayer.style.position = 'absolute';
  labelLayer.style.left = '0';
  labelLayer.style.top = '0';
  labelLayer.style.right = '0';
  labelLayer.style.bottom = '0';
  labelLayer.style.overflow = 'hidden';
  labelLayer.style.pointerEvents = 'none';
  const parent = getContainer();
  if (getComputedStyle(parent).position === 'static') parent.style.position = 'relative';
  parent.appendChild(labelLayer);
}

function createLabelElements() {
  if (!labelLayer) return;
  roomLabelDefs.forEach((def) => {
    const d = el('div', { class: 'hv-room-label', text: def.label });
    d.style.position = 'absolute';
    d.style.transform = 'translate(-50%, -50%)';
    d.style.display = 'none';
    d.style.pointerEvents = 'none';
    d.style.whiteSpace = 'nowrap';
    labelLayer.appendChild(d);
    def.el = d;
  });
}

// 標籤顯示規則：
//  - 需勾選「顯示房間標籤」
//  - 該房間所屬樓層群組需可見
//  - 為避免標籤穿透上方不透明樓板，採用「標籤 solo 樓層」模式：
//    僅顯示目前 solo 樓層 (若無 solo，取最上方可見樓層) 的標籤
function updateLabels() {
  if (!roomLabelDefs.length) return;

  if (!showRoomLabels) {
    roomLabelDefs.forEach((d) => {
      if (d.el) d.el.style.display = 'none';
    });
    return;
  }

  // 決定 label solo 樓層：最上方可見的樓層群組
  let soloFloorName = null;
  for (let i = FLOOR_GROUPS.length - 1; i >= 0; i--) {
    const n = FLOOR_GROUPS[i];
    const obj = groupObjects[n];
    if (obj && obj.visible) {
      soloFloorName = n;
      break;
    }
  }
  soloFloorForLabels = soloFloorName;

  roomLabelDefs.forEach((d) => {
    const floorVisible = !d.floorName || (groupObjects[d.floorName] && groupObjects[d.floorName].visible);
    const single = FLOOR_GROUPS.filter(n=>groupObjects[n]?.visible).length===1 && !groupObjects.ROOF?.visible;
    const inSoloFloor = single && d.floorName === soloFloorName;
    d._active = showRoomLabels && floorVisible && inSoloFloor;
    if (d.el && !d._active) d.el.style.display = 'none';
  });
  projectLabels();
}

const _v = new THREE.Vector3();
function projectLabels() {
  if (!showRoomLabels || !labelLayer) return;
  const parent = getContainer();
  const w = parent.clientWidth;
  const h = parent.clientHeight;

  roomLabelDefs.forEach((d) => {
    if (!d.el || !d._active) return;
    d.object.getWorldPosition(_v);
    _v.project(camera);
    const behind = _v.z > 1;
    if (behind || _v.x < -1 || _v.x > 1 || _v.y < -1 || _v.y > 1) {
      d.el.style.display = 'none';
      return;
    }
    const x = (_v.x * 0.5 + 0.5) * w;
    const y = (-_v.y * 0.5 + 0.5) * h;
    d.el.style.left = x + 'px';
    d.el.style.top = y + 'px';
    d.el.style.display = 'block';
  });
}

// ---------------------------------------------------------------------------
// 全螢幕
// ---------------------------------------------------------------------------
function toggleFullscreen() {
  const target = getContainer();
  const doc = document;
  if (!doc.fullscreenElement && !doc.webkitFullscreenElement) {
    (target.requestFullscreen || target.webkitRequestFullscreen || function () {}).call(target);
  } else {
    (doc.exitFullscreen || doc.webkitExitFullscreen || function () {}).call(doc);
  }
}

function updateFullscreenLabel() {
  if (!fullscreenBtn) return;
  const active = document.fullscreenElement || document.webkitFullscreenElement;
  fullscreenBtn.textContent = active ? '離開全螢幕' : '全螢幕';
}

// ---------------------------------------------------------------------------
// 尺寸
// ---------------------------------------------------------------------------
function onResize() {
  if (!renderer || !camera) return;
  const parent = getContainer();
  const w = parent.clientWidth || window.innerWidth;
  const h = parent.clientHeight || window.innerHeight;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, PIXEL_RATIO_CAP));
  renderer.setSize(w, h, false);
  camera.aspect = w / Math.max(1, h);
  camera.updateProjectionMatrix();
  requestRender();
}

// ---------------------------------------------------------------------------
// 繪製迴圈（按需繪製）
// ---------------------------------------------------------------------------
function renderOnce() {
  if (!renderer || !scene || !camera) return;
  renderer.render(scene, camera);
  projectLabels();
}

function animate() {
  requestAnimationFrame(animate);
  const changed = controls && controls.update();
  if (needsRender || changed) {
    renderOnce();
    needsRender = false;
  }
}

// ---------------------------------------------------------------------------
// 啟動
// ---------------------------------------------------------------------------
try {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
} catch (e) {
  fatal('檢視器初始化失敗。', e);
}
