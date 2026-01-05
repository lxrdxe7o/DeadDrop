/**
 * EncryptionMesh - 3D Interactive Background
 * 
 * A Three.js-powered particle network that represents encryption nodes.
 * Reacts subtly to mouse movement for an immersive experience.
 */

import { useEffect, useRef, useCallback } from 'react';
import * as THREE from 'three';

// Configuration
const CONFIG = {
  particleCount: 80,
  connectionDistance: 150,
  mouseInfluence: 0.0003,
  particleSpeed: 0.15,
  colors: {
    primary: 0x00d4ff,    // Electric cyan
    secondary: 0xa855f7,  // Purple
    background: 0x050508, // Void black
  },
};

interface Particle {
  position: THREE.Vector3;
  velocity: THREE.Vector3;
  originalY: number;
}

export function EncryptionMesh() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mouseRef = useRef({ x: 0, y: 0 });
  const sceneRef = useRef<{
    scene: THREE.Scene;
    camera: THREE.PerspectiveCamera;
    renderer: THREE.WebGLRenderer;
    particles: Particle[];
    particlesMesh: THREE.Points;
    linesMesh: THREE.LineSegments;
    animationId: number;
  } | null>(null);

  const createParticles = useCallback((count: number, bounds: { x: number; y: number; z: number }) => {
    const particles: Particle[] = [];
    
    for (let i = 0; i < count; i++) {
      const x = (Math.random() - 0.5) * bounds.x;
      const y = (Math.random() - 0.5) * bounds.y;
      const z = (Math.random() - 0.5) * bounds.z - 200;
      
      particles.push({
        position: new THREE.Vector3(x, y, z),
        velocity: new THREE.Vector3(
          (Math.random() - 0.5) * CONFIG.particleSpeed,
          (Math.random() - 0.5) * CONFIG.particleSpeed,
          (Math.random() - 0.5) * CONFIG.particleSpeed * 0.5
        ),
        originalY: y,
      });
    }
    
    return particles;
  }, []);

  const updateConnections = useCallback((
    particles: Particle[],
    lineGeometry: THREE.BufferGeometry
  ) => {
    const positions: number[] = [];
    const colors: number[] = [];
    
    const colorPrimary = new THREE.Color(CONFIG.colors.primary);
    const colorSecondary = new THREE.Color(CONFIG.colors.secondary);
    
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const distance = particles[i].position.distanceTo(particles[j].position);
        
        if (distance < CONFIG.connectionDistance) {
          
          positions.push(
            particles[i].position.x, particles[i].position.y, particles[i].position.z,
            particles[j].position.x, particles[j].position.y, particles[j].position.z
          );
          
          // Gradient color based on position
          const mixFactor = (particles[i].position.y + 300) / 600;
          const color = colorPrimary.clone().lerp(colorSecondary, mixFactor);
          
          colors.push(
            color.r, color.g, color.b,
            color.r, color.g, color.b
          );
        }
      }
    }
    
    lineGeometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    lineGeometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    lineGeometry.attributes.position.needsUpdate = true;
    lineGeometry.attributes.color.needsUpdate = true;
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const width = window.innerWidth;
    const height = window.innerHeight;

    // Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(CONFIG.colors.background);
    scene.fog = new THREE.Fog(CONFIG.colors.background, 100, 600);

    // Camera
    const camera = new THREE.PerspectiveCamera(75, width / height, 1, 1000);
    camera.position.z = 300;

    // Renderer
    const renderer = new THREE.WebGLRenderer({ 
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance'
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // Create particles
    const bounds = { x: 800, y: 600, z: 400 };
    const particles = createParticles(CONFIG.particleCount, bounds);

    // Particle geometry
    const particleGeometry = new THREE.BufferGeometry();
    const particlePositions = new Float32Array(particles.length * 3);
    const particleSizes = new Float32Array(particles.length);
    
    particles.forEach((p, i) => {
      particlePositions[i * 3] = p.position.x;
      particlePositions[i * 3 + 1] = p.position.y;
      particlePositions[i * 3 + 2] = p.position.z;
      particleSizes[i] = Math.random() * 3 + 2;
    });
    
    particleGeometry.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
    particleGeometry.setAttribute('size', new THREE.BufferAttribute(particleSizes, 1));

    // Custom shader for glowing particles
    const particleMaterial = new THREE.ShaderMaterial({
      uniforms: {
        color: { value: new THREE.Color(CONFIG.colors.primary) },
        time: { value: 0 },
      },
      vertexShader: `
        attribute float size;
        varying float vAlpha;
        void main() {
          vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = size * (300.0 / -mvPosition.z);
          gl_Position = projectionMatrix * mvPosition;
          vAlpha = 1.0 - smoothstep(100.0, 500.0, -mvPosition.z);
        }
      `,
      fragmentShader: `
        uniform vec3 color;
        varying float vAlpha;
        void main() {
          float dist = length(gl_PointCoord - vec2(0.5));
          if (dist > 0.5) discard;
          float alpha = smoothstep(0.5, 0.0, dist) * vAlpha;
          gl_FragColor = vec4(color, alpha * 0.8);
        }
      `,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    const particlesMesh = new THREE.Points(particleGeometry, particleMaterial);
    scene.add(particlesMesh);

    // Line connections
    const lineGeometry = new THREE.BufferGeometry();
    const lineMaterial = new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.3,
      blending: THREE.AdditiveBlending,
    });
    const linesMesh = new THREE.LineSegments(lineGeometry, lineMaterial);
    scene.add(linesMesh);

    // Mouse movement handler
    const handleMouseMove = (event: MouseEvent) => {
      mouseRef.current.x = (event.clientX / width) * 2 - 1;
      mouseRef.current.y = -(event.clientY / height) * 2 + 1;
    };
    window.addEventListener('mousemove', handleMouseMove);

    // Resize handler
    const handleResize = () => {
      const newWidth = window.innerWidth;
      const newHeight = window.innerHeight;
      camera.aspect = newWidth / newHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(newWidth, newHeight);
    };
    window.addEventListener('resize', handleResize);

    // Animation loop
    let time = 0;
    const animate = () => {
      time += 0.01;
      
      // Update particle positions
      const positions = particleGeometry.attributes.position.array as Float32Array;
      
      particles.forEach((p, i) => {
        // Apply velocity
        p.position.add(p.velocity);
        
        // Mouse influence
        p.position.x += mouseRef.current.x * CONFIG.mouseInfluence * (p.position.z + 300);
        p.position.y += mouseRef.current.y * CONFIG.mouseInfluence * (p.position.z + 300);
        
        // Subtle floating motion
        p.position.y += Math.sin(time + i * 0.1) * 0.1;
        
        // Boundary wrapping
        if (p.position.x > bounds.x / 2) p.position.x = -bounds.x / 2;
        if (p.position.x < -bounds.x / 2) p.position.x = bounds.x / 2;
        if (p.position.y > bounds.y / 2) p.position.y = -bounds.y / 2;
        if (p.position.y < -bounds.y / 2) p.position.y = bounds.y / 2;
        if (p.position.z > -50) p.position.z = -bounds.z - 200;
        if (p.position.z < -bounds.z - 200) p.position.z = -50;
        
        // Update geometry
        positions[i * 3] = p.position.x;
        positions[i * 3 + 1] = p.position.y;
        positions[i * 3 + 2] = p.position.z;
      });
      
      particleGeometry.attributes.position.needsUpdate = true;
      (particleMaterial.uniforms.time as { value: number }).value = time;
      
      // Update connections
      updateConnections(particles, lineGeometry);
      
      // Subtle camera movement
      camera.position.x += (mouseRef.current.x * 20 - camera.position.x) * 0.02;
      camera.position.y += (mouseRef.current.y * 20 - camera.position.y) * 0.02;
      camera.lookAt(scene.position);
      
      renderer.render(scene, camera);
      sceneRef.current!.animationId = requestAnimationFrame(animate);
    };

    sceneRef.current = {
      scene,
      camera,
      renderer,
      particles,
      particlesMesh,
      linesMesh,
      animationId: 0,
    };

    animate();

    // Cleanup
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      
      if (sceneRef.current) {
        cancelAnimationFrame(sceneRef.current.animationId);
        sceneRef.current.renderer.dispose();
        sceneRef.current.particlesMesh.geometry.dispose();
        (sceneRef.current.particlesMesh.material as THREE.Material).dispose();
        sceneRef.current.linesMesh.geometry.dispose();
        (sceneRef.current.linesMesh.material as THREE.Material).dispose();
      }
      
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [createParticles, updateConnections]);

  return <div ref={containerRef} className="three-canvas" />;
}

export default EncryptionMesh;
