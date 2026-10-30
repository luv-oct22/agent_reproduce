from __future__ import annotations

import json
import os
import tempfile


_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Simulation Viewer</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #1a1a2e; color: #eee; font-family: 'Segoe UI', sans-serif; overflow: hidden; }
  #container { width: 100vw; height: 100vh; }
  #controls {
    position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%);
    background: rgba(0,0,0,0.7); padding: 12px 24px; border-radius: 12px;
    display: flex; align-items: center; gap: 16px; backdrop-filter: blur(8px);
  }
  #controls button {
    background: #16213e; color: #eee; border: 1px solid #0f3460; padding: 6px 16px;
    border-radius: 6px; cursor: pointer; font-size: 14px;
  }
  #controls button:hover { background: #0f3460; }
  #controls button.active { background: #e94560; border-color: #e94560; }
  #slider { width: 300px; accent-color: #e94560; }
  #info {
    position: absolute; top: 20px; left: 20px;
    background: rgba(0,0,0,0.7); padding: 12px 18px; border-radius: 8px;
    font-size: 13px; line-height: 1.6; backdrop-filter: blur(8px);
  }
  #speed-label { font-size: 12px; color: #aaa; }
</style>
</head>
<body>
<div id="container"></div>
<div id="info">
  <div>Step: <span id="step-val">0</span> / <span id="total-val">0</span></div>
  <div>Time: <span id="time-val">0.000</span>s</div>
</div>
<div id="controls">
  <button id="btn-play">Play</button>
  <button id="btn-reset">Reset</button>
  <input type="range" id="slider" min="0" max="100" value="0">
  <span id="speed-label">1x</span>
  <button id="btn-slower">-</button>
  <button id="btn-faster">+</button>
</div>

<script type="importmap">
{ "imports": { "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
               "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/" } }
</script>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const DATA = __DATA__;
const MARKERS = __MARKERS__;
const history = DATA.history;
const totalSteps = history.length;
const objNames = DATA.object_names;

document.getElementById('total-val').textContent = totalSteps - 1;
document.getElementById('slider').max = totalSteps - 1;

// Scene
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1a1a2e);
scene.fog = new THREE.Fog(0x1a1a2e, 30, 80);

// Camera
const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 200);
camera.position.set(5, 5, 8);

// Renderer
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
renderer.shadowMap.enabled = true;
document.getElementById('container').appendChild(renderer.domElement);

// Controls
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.target.set(2.5, 0, 1);

// Lights
const ambient = new THREE.AmbientLight(0x404060, 1.5);
scene.add(ambient);
const dirLight = new THREE.DirectionalLight(0xffffff, 2);
dirLight.position.set(10, 15, 10);
dirLight.castShadow = true;
scene.add(dirLight);
const hemi = new THREE.HemisphereLight(0x6060ff, 0x404040, 0.5);
scene.add(hemi);

// Ground grid
const grid = new THREE.GridHelper(40, 40, 0x333355, 0x222244);
grid.rotation.x = Math.PI / 2;
scene.add(grid);

// Axes helper
const axes = new THREE.AxesHelper(3);
scene.add(axes);

// Objects
const COLORS = [0x4fc3f7, 0x81c784, 0xffb74d, 0xce93d8, 0xef5350];
const meshes = {};
const trails = {};

objNames.forEach((name, i) => {
  const color = COLORS[i % COLORS.length];
  const geo = new THREE.SphereGeometry(0.12, 24, 24);
  const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.3, metalness: 0.4 });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.castShadow = true;
  scene.add(mesh);
  meshes[name] = mesh;

  const trailGeo = new THREE.BufferGeometry();
  const trailMat = new THREE.LineBasicMaterial({ color, opacity: 0.5, transparent: true });
  const trailLine = new THREE.Line(trailGeo, trailMat);
  scene.add(trailLine);
  trails[name] = trailLine;
});

// Markers
MARKERS.forEach(m => {
  const pos = m.position;
  const radius = m.radius || 0.3;
  const color = m.color || '#ff0000';
  const style = m.style || 'ring';

  if (style === 'open') {
    const cupHeight = radius * 2;
    const cupGroup = new THREE.Group();
    cupGroup.position.set(pos[0], pos[1], pos[2]);

    const wallGeo = new THREE.CylinderGeometry(radius, radius, cupHeight, 32, 1, true);
    const wallMat = new THREE.MeshStandardMaterial({
      color, side: THREE.DoubleSide, opacity: 0.45, transparent: true,
      roughness: 0.4, metalness: 0.2,
    });
    const wall = new THREE.Mesh(wallGeo, wallMat);
    wall.rotation.x = Math.PI / 2;
    wall.position.z = -cupHeight / 2;
    cupGroup.add(wall);

    const bottomGeo = new THREE.CircleGeometry(radius, 32);
    const bottomMat = new THREE.MeshStandardMaterial({
      color, opacity: 0.5, transparent: true, roughness: 0.4, metalness: 0.2,
    });
    const bottom = new THREE.Mesh(bottomGeo, bottomMat);
    bottom.position.z = -cupHeight;
    cupGroup.add(bottom);

    const rimGeo = new THREE.TorusGeometry(radius, 0.02, 8, 48);
    const rimMat = new THREE.MeshStandardMaterial({ color, roughness: 0.3, metalness: 0.6 });
    const rim = new THREE.Mesh(rimGeo, rimMat);
    cupGroup.add(rim);

    scene.add(cupGroup);
  } else {
    const geo = new THREE.TorusGeometry(radius, 0.02, 8, 48);
    const mat = new THREE.MeshStandardMaterial({ color, opacity: 0.7, transparent: true });
    const ring = new THREE.Mesh(geo, mat);
    ring.position.set(pos[0], pos[1], pos[2]);
    scene.add(ring);
  }

  if (m.label) {
    const canvas = document.createElement('canvas');
    canvas.width = 128; canvas.height = 32;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = color;
    ctx.font = '20px sans-serif';
    ctx.fillText(m.label, 4, 22);
    const tex = new THREE.CanvasTexture(canvas);
    const spriteMat = new THREE.SpriteMaterial({ map: tex });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.position.set(pos[0], pos[1], pos[2] + radius + 0.5);
    sprite.scale.set(1, 0.25, 1);
    scene.add(sprite);
  }
});

// Playback state
let currentStep = 0;
let playing = false;
let speed = 1;
const speeds = [0.25, 0.5, 1, 2, 4, 8];
let speedIdx = 2;
let lastTime = 0;
let accumulator = 0;

function updateScene(step) {
  currentStep = Math.max(0, Math.min(step, totalSteps - 1));
  const frame = history[currentStep];

  objNames.forEach(name => {
    const pos = frame[name].position;
    meshes[name].position.set(pos[0], pos[1], pos[2]);

    const pts = [];
    const start = Math.max(0, currentStep - 200);
    for (let s = start; s <= currentStep; s++) {
      const p = history[s][name].position;
      pts.push(new THREE.Vector3(p[0], p[1], p[2]));
    }
    trails[name].geometry.dispose();
    trails[name].geometry = new THREE.BufferGeometry().setFromPoints(pts);
  });

  document.getElementById('step-val').textContent = currentStep;
  document.getElementById('time-val').textContent = frame.time.toFixed(4);
  document.getElementById('slider').value = currentStep;
}

// Controls
const btnPlay = document.getElementById('btn-play');
btnPlay.addEventListener('click', () => {
  playing = !playing;
  btnPlay.textContent = playing ? 'Pause' : 'Play';
  btnPlay.classList.toggle('active', playing);
  lastTime = performance.now();
});

document.getElementById('btn-reset').addEventListener('click', () => {
  playing = false;
  btnPlay.textContent = 'Play';
  btnPlay.classList.remove('active');
  updateScene(0);
});

document.getElementById('slider').addEventListener('input', (e) => {
  updateScene(parseInt(e.target.value));
});

document.getElementById('btn-faster').addEventListener('click', () => {
  speedIdx = Math.min(speedIdx + 1, speeds.length - 1);
  speed = speeds[speedIdx];
  document.getElementById('speed-label').textContent = speed + 'x';
});

document.getElementById('btn-slower').addEventListener('click', () => {
  speedIdx = Math.max(speedIdx - 1, 0);
  speed = speeds[speedIdx];
  document.getElementById('speed-label').textContent = speed + 'x';
});

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

updateScene(0);

function animate(now) {
  requestAnimationFrame(animate);

  if (playing) {
    const dt = (now - lastTime) / 1000;
    lastTime = now;
    const stepsPerSec = 60 * speed;
    accumulator += dt * stepsPerSec;
    while (accumulator >= 1 && currentStep < totalSteps - 1) {
      currentStep++;
      accumulator -= 1;
    }
    if (currentStep >= totalSteps - 1) {
      playing = false;
      btnPlay.textContent = 'Play';
      btnPlay.classList.remove('active');
    }
    updateScene(currentStep);
  }

  controls.update();
  renderer.render(scene, camera);
}
requestAnimationFrame(animate);
</script>
</body>
</html>"""


class ThreeJSRenderer:

    def __init__(self, output_dir: str | None = None):
        self._output_dir = output_dir or tempfile.mkdtemp(prefix="sim_threejs_")
        os.makedirs(self._output_dir, exist_ok=True)

    def render(
        self,
        history: list[dict],
        extra_markers: list[dict] | None = None,
        filename: str = "simulation.html",
    ) -> str:
        obj_names = [k for k in history[0] if k != "time" and isinstance(history[0][k], dict)]

        data = {
            "object_names": obj_names,
            "history": history,
        }

        html = _TEMPLATE.replace("__DATA__", json.dumps(data))
        html = html.replace("__MARKERS__", json.dumps(extra_markers or []))

        path = os.path.join(self._output_dir, filename)
        with open(path, "w") as f:
            f.write(html)
        return path
