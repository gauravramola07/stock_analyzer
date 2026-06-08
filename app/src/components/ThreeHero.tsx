import { useEffect, useRef } from 'react';
import * as THREE from 'three';

export default function ThreeHero() {
  const containerRef = useRef<HTMLDivElement>(null);
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    if (cleanupRef.current) {
      cleanupRef.current();
      cleanupRef.current = null;
    }

    const container = containerRef.current;
    const prefersReducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setClearColor(0x030507, 1);
    container.appendChild(renderer.domElement);

    // Scene & Camera
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.set(0, 0, 8);

    // Color palettes
    const bgColors = ['#3a1752', '#0a481d', '#0a2352', '#520a0a'];
    const fgColors = ['#00d975', '#f59e0b', '#38bdf8', '#f43f5e'];

    // Panel group
    const panelGroup = new THREE.Group();
    const panels: { mesh: THREE.Mesh; baseX: number; baseY: number; baseZ: number; rx: number; ry: number }[] = [];

    const NUM_COLS = 9;
    const NUM_ROWS = 6;
    const PADDING = 0.15;
    const totalW = NUM_COLS + (NUM_COLS - 1) * PADDING;
    const totalH = NUM_ROWS + (NUM_ROWS - 1) * PADDING;
    const startX = -totalW / 2;
    const startY = -totalH / 2;

    for (let row = 0; row < NUM_ROWS; row++) {
      for (let col = 0; col < NUM_COLS; col++) {
        const panelW = Math.random() * 0.5 + 0.5;
        const panelH = Math.random() * 0.5 + 0.5;
        const x = startX + col * (1 + PADDING);
        const y = startY + row * (1 + PADDING);
        const geomX = x + panelW / 2;
        const geomY = y + panelH / 2;
        const depth = Math.random() * 0.25 + 0.05;

        const geometry = new THREE.BoxGeometry(panelW, panelH, depth);
        const bgIdx = Math.floor(Math.random() * bgColors.length);
        const fgIdx = Math.floor(Math.random() * fgColors.length);

        // Create material with color
        const baseColor = new THREE.Color(bgColors[bgIdx]);
        const material = new THREE.MeshStandardMaterial({
          color: baseColor,
          emissive: new THREE.Color(fgColors[fgIdx]),
          emissiveIntensity: 0.15,
          roughness: 0.5,
          metalness: 0.2,
        });

        const mesh = new THREE.Mesh(geometry, material);
        mesh.position.set(geomX, geomY, 0);
        panelGroup.add(mesh);

        panels.push({
          mesh,
          baseX: geomX,
          baseY: geomY,
          baseZ: 0,
          rx: Math.random() * Math.PI * 2,
          ry: Math.random() * Math.PI * 2,
        });
      }
    }

    scene.add(panelGroup);

    // Lights
    const ambientLight = new THREE.AmbientLight(0x1a3050, 0.6);
    scene.add(ambientLight);

    const pointLight1 = new THREE.PointLight(0x00d975, 0.8, 20);
    pointLight1.position.set(2, 3, 5);
    scene.add(pointLight1);

    const pointLight2 = new THREE.PointLight(0x38bdf8, 0.4, 15);
    pointLight2.position.set(-3, -2, 4);
    scene.add(pointLight2);

    // Mouse
    const mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };
    const onMouseMove = (e: MouseEvent) => {
      mouse.targetX = (e.clientX / window.innerWidth - 0.5) * 2;
      mouse.targetY = (e.clientY / window.innerHeight - 0.5) * 2;
    };
    window.addEventListener('mousemove', onMouseMove);

    // Animation
    let rafId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      rafId = requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();

      mouse.x += (mouse.targetX - mouse.x) * 0.05;
      mouse.y += (mouse.targetY - mouse.y) * 0.05;

      panelGroup.rotation.x = Math.sin(elapsed * 0.05) * 0.05 + mouse.y * 0.05;
      panelGroup.rotation.y = Math.cos(elapsed * 0.03) * 0.02 + mouse.x * 0.05;

      for (let i = 0; i < panels.length; i++) {
        const p = panels[i];
        const floatZ = Math.sin(elapsed * 0.5 + p.rx) * 0.12;
        p.mesh.position.z = p.baseZ + floatZ;
        p.mesh.rotation.x = Math.sin(elapsed * 0.2 + p.rx) * 0.015;
        p.mesh.rotation.y = Math.cos(elapsed * 0.15 + p.ry) * 0.015;
      }

      renderer.render(scene, camera);
    };

    if (!prefersReducedMotion) {
      animate();
    } else {
      renderer.render(scene, camera);
    }

    // Resize
    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener('resize', onResize);

    // Cleanup
    cleanupRef.current = () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('resize', onResize);
      renderer.dispose();
      panels.forEach((p) => {
        p.mesh.geometry.dispose();
        (p.mesh.material as THREE.Material).dispose();
      });
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };

    return () => {
      if (cleanupRef.current) {
        cleanupRef.current();
        cleanupRef.current = null;
      }
    };
  }, []);

  return (
    <div
      ref={containerRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: 0,
      }}
    />
  );
}
