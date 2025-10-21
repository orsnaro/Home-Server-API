// 3D JS magic (Three.js) background for all pages
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    document.getElementById('threejs-bg').appendChild(renderer.domElement);
    camera.position.z = 5;
    const cubes = [];
    for (let i = 0; i < 12; i++) {
      const geometry = new THREE.BoxGeometry();
      const material = new THREE.MeshStandardMaterial({ color: 0x6a1b9a, metalness: 0.5, roughness: 0.5 });
      const cube = new THREE.Mesh(geometry, material);
      cube.position.x = (Math.random() - 0.5) * 8;
      cube.position.y = (Math.random() - 0.5) * 6;
      cube.position.z = (Math.random() - 0.5) * 4;
      cubes.push(cube);
      scene.add(cube);
    }
    const light = new THREE.PointLight(0xffffff, 1, 100);
    light.position.set(0, 0, 10);
    scene.add(light);
    function animate() {
      requestAnimationFrame(animate);
      cubes.forEach((cube, i) => {
        cube.rotation.x += 0.01 + i * 0.001;
        cube.rotation.y += 0.01 + i * 0.001;
      });
      renderer.render(scene, camera);
    }
    animate();
    window.addEventListener('resize', () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    });

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