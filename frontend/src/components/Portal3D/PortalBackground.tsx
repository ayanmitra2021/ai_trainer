"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { useRef, useMemo } from "react";
import * as THREE from "three";
import { ThreeDErrorBoundary } from "../ThreeDErrorBoundary";

interface PortalRingProps {
  index: number;
  color: string;
  speed?: number;
}

function PortalRing({ index, color, speed = 1 }: PortalRingProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const initialRotation = useMemo(() => Math.random() * Math.PI * 2, []);
  const initialScale = useMemo(() => 0.8 + Math.random() * 0.4, []);

  useFrame((state) => {
    const t = state.clock.getElapsedTime() * speed;
    if (meshRef.current) {
      meshRef.current.rotation.z = initialRotation + t * 0.3;
      meshRef.current.rotation.x = Math.sin(t * 0.5) * 0.3;
      meshRef.current.rotation.y = Math.cos(t * 0.7) * 0.2;
      const pulse = 1 + Math.sin(t * 2 + index) * 0.15;
      meshRef.current.scale.setScalar(initialScale * pulse);
      const opacity = 0.15 + Math.sin(t * 3 + index * 1.5) * 0.1;
      if (meshRef.current.material instanceof THREE.Material) {
        meshRef.current.material.opacity = opacity;
      }
    }
  });

  return (
    <mesh ref={meshRef}>
      <torusGeometry args={[4 + index * 0.8, 0.04, 16, 64]} />
      <meshBasicMaterial
        color={color}
        transparent
        opacity={0.2}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

interface ParticleFieldProps {
  count?: number;
}

function ParticleField({ count = 500 }: ParticleFieldProps) {
  const pointsRef = useRef<THREE.Points>(null);
  const positions = useMemo(() => {
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count * 3; i += 3) {
      const radius = 2 + Math.random() * 8;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      arr[i] = radius * Math.sin(phi) * Math.cos(theta);
      arr[i + 1] = radius * Math.sin(phi) * Math.sin(theta);
      arr[i + 2] = radius * Math.cos(phi);
    }
    return arr;
  }, [count]);

  const velocities = useMemo(() => {
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count * 3; i += 3) {
      arr[i] = (Math.random() - 0.5) * 0.002;
      arr[i + 1] = (Math.random() - 0.5) * 0.002;
      arr[i + 2] = (Math.random() - 0.5) * 0.002;
    }
    return arr;
  }, [count]);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (pointsRef.current?.geometry.attributes.position) {
      const pos = pointsRef.current.geometry.attributes.position.array as Float32Array;
      for (let i = 0; i < count * 3; i += 3) {
        pos[i] += velocities[i];
        pos[i + 1] += velocities[i + 1];
        pos[i + 2] += velocities[i + 2];
        const dist = Math.sqrt(pos[i] ** 2 + pos[i + 1] ** 2 + pos[i + 2] ** 2);
        if (dist > 12) {
          const radius = 2 + Math.random() * 2;
          const theta = Math.random() * Math.PI * 2;
          const phi = Math.acos(2 * Math.random() - 1);
          pos[i] = radius * Math.sin(phi) * Math.cos(theta);
          pos[i + 1] = radius * Math.sin(phi) * Math.sin(theta);
          pos[i + 2] = radius * Math.cos(phi);
        }
      }
      pointsRef.current.geometry.attributes.position.needsUpdate = true;
    }
    if (pointsRef.current) {
      pointsRef.current.rotation.y = t * 0.02;
      pointsRef.current.rotation.x = Math.sin(t * 0.1) * 0.1;
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        color="#4dabf7"
        size={0.03}
        transparent
        opacity={0.6}
        sizeAttenuation
      />
    </points>
  );
}

function EnergyCore() {
  const coreRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (coreRef.current) {
      coreRef.current.rotation.y = t * 0.2;
      coreRef.current.rotation.x = t * 0.1;
      const pulse = 1 + Math.sin(t * 2) * 0.2;
      coreRef.current.scale.setScalar(pulse);
      if (coreRef.current.material instanceof THREE.MeshBasicMaterial) {
        coreRef.current.material.opacity = 0.3 + Math.sin(t * 3) * 0.15;
      }
    }
  });

  return (
    <group>
      <mesh ref={coreRef}>
        <sphereGeometry args={[0.6, 32, 32]} />
        <meshBasicMaterial
          color="#4dabf7"
          transparent
          opacity={0.4}
          side={THREE.DoubleSide}
        />
      </mesh>
      <mesh>
        <sphereGeometry args={[0.8, 24, 24]} />
        <meshBasicMaterial
          color="#74c0fc"
          transparent
          opacity={0.15}
          side={THREE.DoubleSide}
          wireframe
        />
      </mesh>
    </group>
  );
}

function DataStreams() {
  const streamsRef = useRef<THREE.Group>(null);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (streamsRef.current) {
      streamsRef.current.rotation.y = t * 0.05;
      streamsRef.current.children.forEach((child, i) => {
        if (child instanceof THREE.Mesh) {
          child.rotation.z = t * 0.3 + i * 0.5;
          child.position.y = Math.sin(t * 2 + i) * 0.5;
        }
      });
    }
  });

  return (
    <group ref={streamsRef}>
      {[0, 1, 2].map((i) => (
        <mesh key={i}>
          <cylinderGeometry args={[0.02, 0.02, 3, 8]} />
          <meshBasicMaterial
            color={["#4dabf7", "#69db7c", "#ffa94d"][i]}
            transparent
            opacity={0.4}
          />
        </mesh>
      ))}
    </group>
  );
}

export function PortalBackgroundCanvas() {
  return (
    <Canvas
      camera={{ position: [0, 0, 15], fov: 50 }}
      style={{ position: "fixed", top: 0, left: 0, width: "100%", height: "100%", zIndex: -1, pointerEvents: "none" }}
      gl={{ antialias: true, alpha: true, preserveDrawingBuffer: false }}
      onCreated={({ gl }) => { gl.setClearColor(0x000000, 0); }}
    >
      <fog attach="fog" args={["#0a0a0f", 8, 25]} />

      <ambientLight color="#4dabf7" intensity={0.3} />
      <directionalLight position={[5, 10, 7]} color="#ffffff" intensity={0.5} />
      <pointLight position={[0, 0, 5]} color="#4dabf7" intensity={0.8} decay={2} distance={20} />

      <EnergyCore />
      <DataStreams />
      <ParticleField count={800} />
      {[0, 1, 2, 3, 4].map((i) => (
        <PortalRing key={i} index={i} color="#4dabf7" speed={0.5 + i * 0.15} />
      ))}
      {[0, 1, 2].map((i) => (
        <PortalRing key={`outer-${i}`} index={i} color="#69db7c" speed={0.3 + i * 0.1} />
      ))}
    </Canvas>
  );
}

export function PortalBackground() {
  return (
    <ThreeDErrorBoundary>
      <PortalBackgroundCanvas />
    </ThreeDErrorBoundary>
  );
}