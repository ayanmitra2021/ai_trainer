"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import { useRef, useMemo, useState } from "react";
import * as THREE from "three";
import { ThreeDErrorBoundary } from "../ThreeDErrorBoundary";

interface SkillData {
  skill_id: string;
  skill_name: string;
  mastery_score: number;
  confidence: number;
  category: string;
}

interface SkillRadar3DProps {
  skills: SkillData[];
  practitionerId: string;
  onSkillClick?: (skill: SkillData) => void;
}

const CATEGORIES = [
  { name: "AI/ML Foundations", color: "#4dabf7", angle: 0 },
  { name: "Model Development", color: "#69db7c", angle: Math.PI * 2 / 3 },
  { name: "Production & Ops", color: "#ffa94d", angle: Math.PI * 4 / 3 },
];

function SkillNode({
  skill,
  index,
  total,
  radius,
  onClick,
  isSelected,
}: {
  skill: SkillData;
  index: number;
  total: number;
  radius: number;
  onClick: () => void;
  isSelected: boolean;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const groupRef = useRef<THREE.Group>(null);
  const baseAngle = useMemo(() => (index / total) * Math.PI * 2 - Math.PI / 2, [index, total]);
  const baseY = useMemo(() => {
    const catIndex = CATEGORIES.findIndex(c => c.name === skill.category);
    return catIndex >= 0 ? (catIndex - 1) * 2.5 : 0;
  }, [skill.category]);

  const color = useMemo(() => {
    const cat = CATEGORIES.find(c => c.name === skill.category);
    return cat?.color || "#4dabf7";
  }, [skill.category]);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (groupRef.current) {
      const floatY = Math.sin(t * 2 + index) * 0.15;
      groupRef.current.position.y = baseY + floatY;
      groupRef.current.rotation.y = t * 0.15;
    }
    if (meshRef.current) {
      const pulse = 1 + Math.sin(t * 3 + index) * (isSelected ? 0.2 : 0.1);
      meshRef.current.scale.setScalar(pulse);
      if (meshRef.current.material instanceof THREE.MeshBasicMaterial) {
        const targetOpacity = isSelected ? 0.9 : 0.5;
        meshRef.current.material.opacity += (targetOpacity - meshRef.current.material.opacity) * 0.1;
      }
    }
  });

  const size = 0.15 + skill.mastery_score * 0.35;

  return (
    <group ref={groupRef} position={[Math.cos(baseAngle) * radius, baseY, Math.sin(baseAngle) * radius]}>
      <mesh
        ref={meshRef}
        onClick={onClick}
        onPointerOver={() => {}}
        onPointerOut={() => {}}
        scale={size}
      >
        <sphereGeometry args={[1, 16, 16]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={0.5}
          side={THREE.DoubleSide}
        />
      </mesh>
      <mesh
        scale={size * 1.3}
      >
        <sphereGeometry args={[1, 16, 16]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={0.15}
          side={THREE.DoubleSide}
        />
      </mesh>
      <Html
        transform
        position={[0, size * 1.5, 0]}
        style={{
          pointerEvents: "none",
          fontSize: "10px",
          color: "#fff",
          textShadow: "0 0 4px #000",
          whiteSpace: "nowrap",
          textAlign: "center",
          fontWeight: 600,
        }}
      >
        {skill.skill_name.length > 12 ? skill.skill_name.slice(0, 11) + "…" : skill.skill_name}
      </Html>
      <Html
        transform
        position={[0, -size * 1.5, 0]}
        style={{
          pointerEvents: "none",
          fontSize: "9px",
          color: color,
          textShadow: "0 0 4px #000",
          fontWeight: 700,
        }}
      >
        {Math.round(skill.mastery_score * 100)}%
      </Html>
    </group>
  );
}

interface CategoryRingProps {
  category: { name: string; color: string; angle: number };
  radius: number;
  yPosition: number;
}

function CategoryRing({ category, radius, yPosition }: CategoryRingProps) {
  const ringRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (ringRef.current) {
      ringRef.current.rotation.z = t * 0.1;
      if (ringRef.current.material instanceof THREE.MeshBasicMaterial) {
        ringRef.current.material.opacity = 0.1 + Math.sin(t * 2) * 0.05;
      }
    }
  });

  return (
    <mesh
      ref={ringRef}
      position={[0, yPosition, 0]}
      rotation={[-Math.PI / 2, 0, 0]}
    >
      <torusGeometry args={[radius + 0.5, 0.05, 16, 64]} />
      <meshBasicMaterial
        color={category.color}
        transparent
        opacity={0.15}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

interface ConnectingLinesProps {
  skills: SkillData[];
  radius: number;
}

function ConnectingLines({ skills, radius }: ConnectingLinesProps) {
  const lineRef = useRef<THREE.Line>(null);
  const positions = useMemo(() => {
    const arr = new Float32Array(skills.length * 3 * 2 * 3);
    let idx = 0;
    skills.forEach((skill, i) => {
      const angle = (i / skills.length) * Math.PI * 2 - Math.PI / 2;
      const catIndex = CATEGORIES.findIndex(c => c.name === skill.category);
      const y = catIndex >= 0 ? (catIndex - 1) * 2.5 : 0;
      const nextIndex = (i + 1) % skills.length;
      const nextAngle = (nextIndex / skills.length) * Math.PI * 2 - Math.PI / 2;
      const nextCatIndex = CATEGORIES.findIndex(c => c.name === skills[nextIndex].category);
      const nextY = nextCatIndex >= 0 ? (nextCatIndex - 1) * 2.5 : 0;

      arr[idx++] = Math.cos(angle) * radius;
      arr[idx++] = y;
      arr[idx++] = Math.sin(angle) * radius;

      arr[idx++] = Math.cos(nextAngle) * radius;
      arr[idx++] = nextY;
      arr[idx++] = Math.sin(nextAngle) * radius;
    });
    return arr;
  }, [skills, radius]);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (lineRef.current?.material instanceof THREE.LineBasicMaterial) {
      lineRef.current.material.opacity = 0.1 + Math.sin(t * 3) * 0.05;
    }
  });

  const line = useMemo(() => {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const material = new THREE.LineBasicMaterial({ color: "#4dabf7", transparent: true, opacity: 0.15 });
    return new THREE.Line(geometry, material);
  }, [positions]);

  return (
    <primitive
      ref={lineRef}
      object={line}
      dispose={null}
    />
  );
}

interface MasteryCoreProps {
  averageMastery: number;
}

function MasteryCore({ averageMastery }: MasteryCoreProps) {
  const coreRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (coreRef.current) {
      coreRef.current.rotation.y = t * 0.3;
      coreRef.current.rotation.x = t * 0.15;
      const pulse = 1 + Math.sin(t * 2) * 0.15 * averageMastery;
      coreRef.current.scale.setScalar(pulse);
      if (coreRef.current.material instanceof THREE.MeshBasicMaterial) {
        coreRef.current.material.opacity = 0.3 + averageMastery * 0.4 + Math.sin(t * 3) * 0.1;
      }
    }
  });

  return (
    <group>
      <mesh ref={coreRef}>
        <icosahedronGeometry args={[0.8, 1]} />
        <meshBasicMaterial
          color="#4dabf7"
          transparent
          opacity={0.4}
          wireframe
        />
      </mesh>
      <mesh>
        <sphereGeometry args={[0.5, 32, 32]} />
        <meshBasicMaterial
          color="#74c0fc"
          transparent
          opacity={0.2}
        />
      </mesh>
      <Html
        transform
        position={[0, 0, 0]}
        style={{
          pointerEvents: "none",
          textAlign: "center",
          color: "#fff",
          textShadow: "0 0 8px #4dabf7",
        }}
      >
        <div style={{ fontSize: "24px", fontWeight: 800 }}>{Math.round(averageMastery * 100)}%</div>
        <div style={{ fontSize: "10px", color: "#aaa" }}>Overall Mastery</div>
      </Html>
    </group>
  );
}

export function SkillRadar3DCanvas({ skills, onSkillClick }: { skills: SkillData[]; onSkillClick?: (skill: SkillData) => void }) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);

  const averageMastery = useMemo(
    () => skills.reduce((sum, s) => sum + s.mastery_score, 0) / (skills.length || 1),
    [skills]
  );

  const radius = 4;

  return (
    <Canvas
      camera={{ position: [0, 1, 10], fov: 45 }}
      style={{ width: "100%", height: "100%", minHeight: "500px" }}
      gl={{ antialias: true, alpha: true }}
      onCreated={({ gl }) => { gl.setClearColor(0x0a0a0f, 0); }}
    >
      <fog attach="fog" args={["#0a0a0f", 5, 25]} />

      <ambientLight color="#4dabf7" intensity={0.5} />
      <directionalLight position={[5, 10, 7]} color="#ffffff" intensity={0.6} />
      <pointLight position={[0, 0, 5]} color="#4dabf7" intensity={0.8} decay={2} distance={20} />

      <MasteryCore averageMastery={averageMastery} />
      <ConnectingLines skills={skills} radius={radius} />
      {CATEGORIES.map((cat, i) => (
        <CategoryRing key={cat.name} category={cat} radius={radius} yPosition={(i - 1) * 2.5} />
      ))}
      {skills.map((skill, i) => (
        <SkillNode
          key={skill.skill_id}
          skill={skill}
          index={i}
          total={skills.length}
          radius={radius}
          onClick={() => {
            onSkillClick?.(skill);
            setSelectedIndex(i);
          }}
          isSelected={selectedIndex === i}
        />
      ))}
    </Canvas>
  );
}

export function SkillRadar3D({ skills, onSkillClick }: SkillRadar3DProps) {
  return (
    <div style={{ width: "100%", height: "500px", position: "relative" }}>
      <ThreeDErrorBoundary
        fallback={
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-muted)", fontSize: "0.875rem" }}>
            3D radar unavailable in this browser.
          </div>
        }
      >
        <SkillRadar3DCanvas skills={skills} onSkillClick={onSkillClick} />
      </ThreeDErrorBoundary>
      <div
        style={{
          position: "absolute",
          bottom: 20,
          left: 20,
          right: 20,
          display: "flex",
          justifyContent: "center",
          gap: 24,
          pointerEvents: "none",
        }}
      >
        {CATEGORIES.map((cat) => (
          <div
            key={cat.name}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              color: "#fff",
              fontSize: "12px",
              textShadow: "0 0 4px #000",
            }}
          >
            <div
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: cat.color,
                boxShadow: `0 0 8px ${cat.color}`,
              }}
            />
            <span>{cat.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}