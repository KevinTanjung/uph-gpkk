import * as THREE from 'three';
import { OrbitControls } from 'three/examples/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/loaders/GLTFLoader.js';
import { vertexShader, fragmentShader } from './shader.js';

let scene, camera, renderer, controls;
let structureLayer = [];
let spatialLayer = [];
let allMeshes = [];
let selectedObject = null;

const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

let wireframeMode = false;
let lastTime = performance.now();
let frameCount = 0;

init();
animate();

function init() {

  scene = new THREE.Scene();

  camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.set(5, 5, 10);

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  document.body.appendChild(renderer.domElement);

  controls = new OrbitControls(camera, renderer.domElement);

  const loader = new GLTFLoader();

  loader.load('model.gltf', (gltf) => {

    gltf.scene.traverse((child) => {
      if (child.isMesh) {

        const material = new THREE.ShaderMaterial({
          vertexShader,
          fragmentShader,
          uniforms: {
            lightPosition: { value: new THREE.Vector3(10, 10, 10) },
            baseColor: { value: new THREE.Color(0xaaaaaa) }
          }
        });

        child.material = material;
        allMeshes.push(child);

        if (child.name.includes("column") || child.name.includes("beam")) {
          structureLayer.push(child);
        } else {
          spatialLayer.push(child);
        }
      }
    });

    scene.add(gltf.scene);
  });

  window.addEventListener('resize', onResize);
  window.addEventListener('click', onMouseClick);
}

function animate() {
  requestAnimationFrame(animate);

  updateFPS();

  renderer.render(scene, camera);
}

/* ===========================
   Object Selection (Raycasting)
   =========================== */

function onMouseClick(event) {

  mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
  mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

  raycaster.setFromCamera(mouse, camera);
  const intersects = raycaster.intersectObjects(allMeshes);

  if (intersects.length > 0) {

    if (selectedObject) {
      selectedObject.material.uniforms.baseColor.value.set(0xaaaaaa);
    }

    selectedObject = intersects[0].object;
    selectedObject.material.uniforms.baseColor.value.set(0xff0000);
  }
}

/* ===========================
   Wireframe Toggle
   =========================== */

document.getElementById("wireframeBtn").onclick = () => {
  wireframeMode = !wireframeMode;
  allMeshes.forEach(mesh => {
    mesh.material.wireframe = wireframeMode;
  });
};

/* ===========================
   FPS Counter
   =========================== */

function updateFPS() {
  frameCount++;
  const now = performance.now();
  const delta = now - lastTime;

  if (delta >= 1000) {
    const fps = (frameCount / delta) * 1000;
    document.getElementById("fps").innerText = "FPS: " + fps.toFixed(1);
    frameCount = 0;
    lastTime = now;
  }
}

/* ===========================
   Mesh Simplification (Basic)
   =========================== */

document.getElementById("simplifyBtn").onclick = () => {

  allMeshes.forEach(mesh => {

    const geometry = mesh.geometry;

    if (!geometry.index) return;

    const positionAttr = geometry.attributes.position;
    const count = positionAttr.count;

    const newPositions = [];

    for (let i = 0; i < count; i += 2) {
      newPositions.push(
        positionAttr.getX(i),
        positionAttr.getY(i),
        positionAttr.getZ(i)
      );
    }

    const simplified = new THREE.BufferGeometry();
    simplified.setAttribute(
      'position',
      new THREE.Float32BufferAttribute(newPositions, 3)
    );

    simplified.computeVertexNormals();

    mesh.geometry.dispose();
    mesh.geometry = simplified;
  });

  console.log("Mesh simplified (vertex decimation applied)");
};

/* ===========================
   Layer Controls
   =========================== */

document.getElementById("structureBtn").onclick = () => {
  structureLayer.forEach(o => o.visible = true);
  spatialLayer.forEach(o => o.visible = false);
};

document.getElementById("spatialBtn").onclick = () => {
  structureLayer.forEach(o => o.visible = false);
  spatialLayer.forEach(o => o.visible = true);
};

document.getElementById("combinedBtn").onclick = () => {
  structureLayer.forEach(o => o.visible = true);
  spatialLayer.forEach(o => o.visible = true);
};

function onResize() {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}