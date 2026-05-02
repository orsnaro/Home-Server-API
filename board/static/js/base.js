// 3D JS magic (Three.js) background for all pages
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ alpha: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.getElementById('threejs-bg').appendChild(renderer.domElement);
camera.position.z = 5;
const cubes = [];
// --- Optimized Cube Logic ---
for (let i = 0; i < 15; i++) {
  const geometry = new THREE.BoxGeometry(0.5, 0.5, 0.5); // Smaller cubes
  const material = new THREE.MeshStandardMaterial({ 
    color: 0x6a1b9a, 
    metalness: 0.3, 
    roughness: 0.7,
    transparent: true,
    opacity: 0.4 // More subtle
  });
  const cube = new THREE.Mesh(geometry, material);
  cube.position.x = (Math.random() - 0.5) * 12;
  cube.position.y = (Math.random() - 0.5) * 10;
  cube.position.z = (Math.random() - 0.5) * 6 - 5; // Push further back
  cubes.push(cube);
  scene.add(cube);
}
const light = new THREE.PointLight(0xffffff, 0.8, 100);
light.position.set(0, 5, 10);
scene.add(light);
const ambientLight = new THREE.AmbientLight(0x404040, 0.5); // Add ambient light
scene.add(ambientLight);

function animate() {
  requestAnimationFrame(animate);
  cubes.forEach((cube, i) => {
    cube.rotation.x += 0.005 + i * 0.0005;
    cube.rotation.y += 0.005 + i * 0.0005;
  });
  renderer.render(scene, camera);
}
animate();
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

// Sidebar Toggle Logic
const menuToggle = document.getElementById('menuToggle');
const sidebar = document.getElementById('sidebar');

if (menuToggle && sidebar) {
    menuToggle.onclick = (e) => {
        e.stopPropagation();
        sidebar.classList.toggle('active');
        menuToggle.textContent = sidebar.classList.contains('active') ? '✕' : '☰';
    };

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 1024 && 
            !sidebar.contains(e.target) && 
            !menuToggle.contains(e.target) && 
            sidebar.classList.contains('active')) {
            sidebar.classList.remove('active');
            menuToggle.textContent = '☰';
        }
    });
}

// Dark mode toggle
const darkToggle = document.getElementById('darkToggle');
function setDarkMode(on) {
  if (on) {
    document.body.classList.add('dark');
    darkToggle.textContent = '☀️';
    localStorage.setItem('darkMode', '1');
  } else {
    document.body.classList.remove('dark');
    darkToggle.textContent = '🌙';
    localStorage.setItem('darkMode', '0');
  }
}
darkToggle.onclick = () => setDarkMode(!document.body.classList.contains('dark'));
// Load preference: default to dark mode unless explicitly set to light
if (localStorage.getItem('darkMode') === '0') {
  setDarkMode(false);
} else {
  setDarkMode(true);
}

// Highlight active nav item
const currentPath = window.location.pathname;
document.querySelectorAll('.nav-item').forEach(item => {
    const itemPath = item.getAttribute('href');
    if (itemPath === currentPath || (currentPath === '/' && itemPath.includes('home'))) {
        item.classList.add('active');
    }
});
