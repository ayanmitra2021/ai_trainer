"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import { useRef, useMemo, useState } from "react";
import * as THREE from "three";
import { ThreeDErrorBoundary } from "../ThreeDErrorBoundary";

interface SkillCalibrationData {
  skill_id: string;
  skill_name: string;
  category: string;
  self_assessed_score: number;
  quiz_performance: Array<{
    period_label: string;
    avg_score: number;
    attempt_count: number;
  }>;
  current_gap: number;
  gap_direction: "closing" | "widening" | "stable" | "no_data";
  has_quiz_data: boolean;
}

interface SkillCalibration3DProps {
  skills: SkillCalibrationData[];
  practitionerId: string;
}

const CATEGORIES = [
  { name: "AI/ML Foundations", color: "#4dabf7", xOffset: -6 },
  { name: "Model Development", color: "#69db7c", xOffset: 0 },
  { name: "Production & Ops", color: "#ffa94d", xOffset: 6 },
];

function SkillColumn({
  skill,
  index,
  total,
  xPosition,
  onClick,
  isSelected,
}: {
  skill: SkillCalibrationData;
  index: number;
  total: number;
  xPosition: number;
  onClick: () => void;
  isSelected: boolean;
}) {
  const groupRef = useRef<THREE.Group>(null);
  const baselineRef = useRef<THREE.Mesh>(null);
  const currentRef = useRef<THREE.Mesh>(null);
  const gapRef = useRef<THREE.Mesh>(null);

  const latestQuiz = skill.quiz_performance[skill.quiz_performance.length - 1];
  const currentScore = latestQuiz?.avg_score ?? 0;
  const baselineScore = skill.self_assessed_score;
  const gap = baselineScore - currentScore;

  const baselineHeight = baselineScore * 4;
  const currentHeight = currentScore * 4;
  const gapHeight = Math.abs(gap) * 4;

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (groupRef.current) {
      groupRef.current.rotation.y = Math.sin(t * 0.5 + index) * 0.1;
      groupRef.current.position.y = Math.sin(t * 2 + index * 0.5) * 0.1;
    }
    if (baselineRef.current && baselineRef.current.material instanceof THREE.Material) {
      baselineRef.current.material.opacity = 0.3 + Math.sin(t * 2 + index) * 0.1;
    }
    if (currentRef.current && currentRef.current.material instanceof THREE.Material) {
      currentRef.current.material.opacity = 0.7 + Math.sin(t * 3 + index) * 0.1;
    }
    if (gapRef.current && gap !== 0 && gapRef.current.material instanceof THREE.Material) {
      gapRef.current.material.opacity = isSelected ? 0.6 : 0.3;
      gapRef.current.scale.y = 0.5 + Math.sin(t * 4 + index) * 0.1;
    }
  });

  const getGapColor = () => {
    if (gap > 0.25) return "#dc2626";
    if (gap > 0.08) return "#ea580c";
    if (gap > -0.08) return "#16a34a";
    return "#2563eb";
  };

  return (
    <group
      ref={groupRef}
      position={[xPosition, 0, index * 3 - (total - 1) * 1.5]}
      onClick={onClick}
    >
      <group position={[-1.5, 0, 0]}>
        <mesh ref={baselineRef} position={[0, baselineHeight / 2, 0]} scale={[0.6, baselineHeight, 0.6]}>
          <boxGeometry args={[1, 1, 1]} />
          <meshPhysicalMaterial
            color="#4dabf7"
            transparent
            opacity={0.3}
            transmission={0.5}
            roughness={0.1}
            metalness={0.2}
          />
        </mesh>
        <mesh position={[0, baselineHeight + 0.3, 0]} scale={0.5}>
          <octahedronGeometry args={[1, 0]} />
          <meshBasicMaterial color="#4dabf7" transparent opacity={0.8} />
        </mesh>
        <Html
          transform
          position={[0, baselineHeight + 0.8, 0]}
          style={{
            pointerEvents: "none",
            fontSize: "10px",
            color: "#4dabf7",
            textShadow: "0 0 4px #000",
            whiteSpace: "nowrap",
            textAlign: "center",
            fontWeight: 600,
          }}
        >
          Baseline: {Math.round(baselineScore * 100)}%
        </Html>
      </group>

      <group position={[0, 0, 0]}>
        <mesh ref={currentRef} position={[0, currentHeight / 2, 0]} scale={[0.8, currentHeight, 0.8]}>
          <boxGeometry args={[1, 1, 1]} />
          <meshPhysicalMaterial
            color={getGapColor()}
            transparent
            opacity={0.7}
            transmission={0.3}
            roughness={0.2}
            metalness={0.3}
            clearcoat={0.5}
            clearcoatRoughness={0.1}
          />
        </mesh>
        {skill.has_quiz_data && (
          <mesh position={[0, currentHeight + 0.4, 0]} scale={0.6}>
            <sphereGeometry args={[1, 16, 16]} />
            <meshBasicMaterial color={getGapColor()} transparent opacity={0.9} />
          </mesh>
        )}
        <Html
          transform
          position={[0, currentHeight + 1, 0]}
          style={{
            pointerEvents: "none",
            fontSize: "11px",
            color: getGapColor(),
            textShadow: "0 0 4px #000",
            whiteSpace: "nowrap",
            textAlign: "center",
            fontWeight: 700,
          }}
        >
          {skill.has_quiz_data ? `Quiz: ${Math.round(currentScore * 100)}%` : "No quiz data"}
        </Html>
      </group>

      <group position={[1.5, 0, 0]}>
        {gap !== 0 && (
          <mesh
            ref={gapRef}
            position={[0, Math.min(baselineScore, currentScore) * 4 + gapHeight / 2, 0]}
            scale={[0.5, gapHeight, 0.5]}
          >
            <boxGeometry args={[1, 1, 1]} />
            <meshPhysicalMaterial
              color={getGapColor()}
              transparent
              opacity={0.4}
              transmission={0.6}
              roughness={0.1}
              metalness={0.1}
            />
          </mesh>
        )}
        <Html
          transform
          position={[0, -1, 0]}
          style={{
            pointerEvents: "none",
            fontSize: "10px",
            color: getGapColor(),
            textShadow: "0 0 4px #000",
            whiteSpace: "nowrap",
            textAlign: "center",
            fontWeight: 600,
          }}
        >
          {gap > 0
            ? `Gap: ${Math.round(gap * 100)}%`
            : gap < 0
            ? `Ahead: ${Math.round(Math.abs(gap) * 100)}%`
            : "On track"}
        </Html>
      </group>

      <Html
        transform
        position={[0, -2.5, 0]}
        style={{
          pointerEvents: "none",
          fontSize: "12px",
          color: "#fff",
          textShadow: "0 0 4px #000",
          whiteSpace: "nowrap",
          textAlign: "center",
          fontWeight: 600,
        }}
      >
        {skill.skill_name.length > 14 ? skill.skill_name.slice(0, 13) + "…" : skill.skill_name}
      </Html>

      {isSelected && (
        <mesh position={[0, 2.5, 0]} scale={1.2}>
          <torusGeometry args={[1.2, 0.05, 16, 32]} />
          <meshBasicMaterial color={getGapColor()} transparent opacity={0.5} />
        </mesh>
      )}
    </group>
  );
}

interface CategoryPlatformProps {
  category: { name: string; color: string; xOffset: number };
  xPosition: number;
}

function CategoryPlatform({ category, xPosition }: CategoryPlatformProps) {
  const platformRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (platformRef.current && platformRef.current.material instanceof THREE.MeshPhysicalMaterial) {
      platformRef.current.material.opacity = 0.15 + Math.sin(t * 2) * 0.05;
      platformRef.current.position.y = Math.sin(t * 3) * 0.05;
    }
  });

  return (
    <mesh
      ref={platformRef}
      position={[xPosition, -0.5, 0]}
      scale={[4, 0.2, 20]}
    >
      <boxGeometry args={[1, 1, 1]} />
      <meshPhysicalMaterial
        color={category.color}
        transparent
        opacity={0.15}
        roughness={0.3}
        metalness={0.2}
      />
    </mesh>
  );
}

function GridFloor() {
  const gridRef = useRef<THREE.GridHelper>(null);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (gridRef.current && gridRef.current.material instanceof THREE.Material) {
      gridRef.current.material.opacity = 0.1 + Math.sin(t * 2) * 0.05;
    }
  });

  return (
    <gridHelper
      ref={gridRef}
      args={[20, 1, "#4dabf7", "#1a1a2e"]}
      position={[0, -2.5, 0]}
    />
  );
}

interface DataFlowLinesProps {
  skills: SkillCalibrationData[];
}

function DataFlowLines({ skills }: DataFlowLinesProps) {
  const lineRef = useRef<THREE.Line>(null);
  const positions = useMemo(() => {
    const arr = new Float32Array(skills.length * 6 * 2 * 3);
    let idx = 0;
    skills.forEach((skill, i) => {
      const xPos = CATEGORIES.find(c => c.name === skill.category)?.xOffset ?? 0;
      const baselineHeight = skill.self_assessed_score * 4;
      const latestQuiz = skill.quiz_performance[skill.quiz_performance.length - 1];
      const currentHeight = (latestQuiz?.avg_score ?? 0) * 4;

      const zPos = i * 3 - (skills.length - 1) * 1.5;

      arr[idx++] = xPos - 1.5;
      arr[idx++] = baselineHeight;
      arr[idx++] = zPos;

      arr[idx++] = xPos;
      arr[idx++] = currentHeight;
      arr[idx++] = zPos;

      arr[idx++] = xPos;
      arr[idx++] = currentHeight;
      arr[idx++] = zPos;

      arr[idx++] = xPos + 1.5;
      arr[idx++] = Math.min(baselineHeight, currentHeight);
      arr[idx++] = zPos;
    });
    return arr;
  }, [skills]);

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

export function SkillCalibration3DCanvas({ skills, onSkillSelect }: { skills: SkillCalibrationData[]; onSkillSelect?: (skill: SkillCalibrationData) => void }) {
  const [selectedSkillId, setSelectedSkillId] = useState<string | null>(null);

  return (
    <Canvas
      camera={{ position: [8, 6, 10], fov: 50 }}
      style={{ width: "100%", height: "100%", minHeight: "500px" }}
      gl={{ antialias: true, alpha: true }}
      onCreated={({ gl }) => { gl.setClearColor(0x0a0a0f, 0); }}
    >
      <fog attach="fog" args={["#0a0a0f", 5, 30]} />

      <ambientLight color="#ffffff" intensity={0.6} />
      <directionalLight position={[10, 15, 10]} color="#ffffff" intensity={0.8} />
      <pointLight position={[0, 5, 0]} color="#4dabf7" intensity={1} decay={2} distance={30} />
      <pointLight position={[6, 5, 0]} color="#69db7c" intensity={0.5} decay={2} distance={20} />
      <pointLight position={[-6, 5, 0]} color="#ffa94d" intensity={0.5} decay={2} distance={20} />

      <GridFloor />
      <DataFlowLines skills={skills} />
      {CATEGORIES.map((cat) => (
        <CategoryPlatform key={cat.name} category={cat} xPosition={cat.xOffset} />
      ))}
      {skills.map((skill, i) => (
        <SkillColumn
          key={skill.skill_id}
          skill={skill}
          index={i}
          total={skills.length}
          xPosition={CATEGORIES.find(c => c.name === skill.category)?.xOffset ?? 0}
          onClick={() => {
            setSelectedSkillId(skill.skill_id);
            onSkillSelect?.(skill);
          }}
          isSelected={selectedSkillId === skill.skill_id}
        />
      ))}
    </Canvas>
  );
}

export function SkillCalibration3D({ skills }: SkillCalibration3DProps) {
  const [selectedSkill, setSelectedSkill] = useState<SkillCalibrationData | null>(null);

  return (
    <div style={{ width: "100%", height: "550px", position: "relative" }}>
      <ThreeDErrorBoundary
        fallback={
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-muted)", fontSize: "0.875rem" }}>
            3D chart unavailable in this browser.
          </div>
        }
      >
        <SkillCalibration3DCanvas
          skills={skills}
          onSkillSelect={setSelectedSkill}
        />
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
          flexWrap: "wrap",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 6, color: "#fff", fontSize: "11px", textShadow: "0 0 4px #000" }}>
          <div style={{ width: 12, height: 12, borderRadius: "2px", background: "linear-gradient(180deg, #4dabf7, #1a1a2e)", boxShadow: "0 0 8px #4dabf7" }} />
          <span>Self-Assessed Baseline</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, color: "#fff", fontSize: "11px", textShadow: "0 0 4px #000" }}>
          <div style={{ width: 12, height: 12, borderRadius: "2px", background: "linear-gradient(180deg, #16a34a, #1a1a2e)", boxShadow: "0 0 8px #16a34a" }} />
          <span>Quiz Performance</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, color: "#fff", fontSize: "11px", textShadow: "0 0 4px #000" }}>
          <div style={{ width: 12, height: 12, borderRadius: "2px", background: "linear-gradient(180deg, #ea580c, #1a1a2e)", boxShadow: "0 0 8px #ea580c", opacity: 0.5 }} />
          <span>Gap / Ahead</span>
        </div>
      </div>

      {selectedSkill && (
        <div
          style={{
            position: "absolute",
            top: 20,
            right: 20,
            maxWidth: 280,
            padding: 16,
            background: "rgba(20, 20, 30, 0.9)",
            border: "1px solid rgba(77, 171, 247, 0.3)",
            borderRadius: 12,
            backdropFilter: "blur(10px)",
            boxShadow: "0 8px 32px rgba(0, 0, 0, 0.5)",
            pointerEvents: "auto",
            zIndex: 10,
          }}
        >
          <h4 style={{ margin: "0 0 12px", color: "#fff", fontSize: "14px" }}>{selectedSkill.skill_name}</h4>
          <div style={{ display: "flex", gap: 16, marginBottom: 12, fontSize: "12px" }}>
            <div style={{ color: "#4dabf7" }}>
              <strong>Baseline:</strong> {Math.round(selectedSkill.self_assessed_score * 100)}%
            </div>
            <div style={{ color: selectedSkill.current_gap > 0 ? "#ea580c" : "#16a34a" }}>
              <strong>Current:</strong> {selectedSkill.has_quiz_data ? Math.round(selectedSkill.quiz_performance[selectedSkill.quiz_performance.length - 1].avg_score * 100) + "%" : "N/A"}
            </div>
          </div>
          <div style={{ fontSize: "12px", color: selectedSkill.current_gap > 0 ? "#ea580c" : "#16a34a" }}>
            <strong>Gap:</strong> {selectedSkill.current_gap > 0 ? "Needs improvement" : "Exceeding baseline"}
            <span style={{ color: "#888", marginLeft: 8 }}>({selectedSkill.gap_direction})</span>
          </div>
          {selectedSkill.has_quiz_data && (
            <div style={{ marginTop: 12, fontSize: "11px", color: "#aaa" }}>
              Latest quiz: {selectedSkill.quiz_performance[selectedSkill.quiz_performance.length - 1].period_label} ·{" "}
              {selectedSkill.quiz_performance[selectedSkill.quiz_performance.length - 1].attempt_count} attempt(s)
            </div>
          )}
        </div>
      )}
    </div>
  );
}