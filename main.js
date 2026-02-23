import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.158/build/three.module.js';
import { OrbitControls } from 'https://cdn.jsdelivr.net/npm/three@0.158/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'https://cdn.jsdelivr.net/npm/three@0.158/examples/jsm/loaders/GLTFLoader.js';
import { vertexShader, fragmentShader } from './shader.js';

let scene, camera, renderer, controls;
let structureLayer = [];
let spatialLayer = [];

init();
animate();

function init() {

  scene = new THREE.Scene();

  camera = new THREE.PerspectiveCamera(
    60,
    window.innerWidth / window.innerHeight,
    0.1,
    1000
  );
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
}

function animate() {
  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}

function onResize() {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}

/* Layer Controls */

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