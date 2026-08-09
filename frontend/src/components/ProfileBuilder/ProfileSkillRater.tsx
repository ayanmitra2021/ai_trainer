/**
 * ProfileSkillRater — Phase 6.5
 *
 * Two-tier skill rating: Tier 1 = certification-relevant skills first,
 * Tier 2 = all other skills. 5-level system matching SelfAssessmentPanel.
 */

import React, { useState } from "react";
import { useSkills } from "../../hooks";

const LEVELS = [
  { label: "None", value: 0.0 },
  { label: "Beginner", value: 0.25 },
  { label: "Familiar", value: 0.5 },
  { label: "Proficient", value: 0.75 },
  { label: "Expert", value: 1.0 },
] as const;

function nearestLevel(score: number): number {
  return LEVELS.reduce((best, lvl) =>
    Math.abs(lvl.value - score) < Math.abs(best.value - score) ? lvl : best
  ).value;
}

function LevelPicker({
  value,
  onChange,
}: {
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div style={{ display: "flex", gap: "0.375rem", flexWrap: "wrap" }}>
      {LEVELS.map((lvl) => (
        <button
          key={lvl.value}
          type="button"
          onClick={() => onChange(lvl.value)}
          style={{
            fontSize: "0.75rem",
            padding: "0.25rem 0.625rem",
            borderRadius: "999px",
            border: `1px solid ${value === lvl.value ? "var(--primary)" : "var(--border)"}`,
            background: value === lvl.value ? "var(--primary)" : "transparent",
            color: value === lvl.value ? "#fff" : "var(--text)",
            cursor: "pointer",
            transition: "all 0.15s",
          }}
        >
          {lvl.label}
        </button>
      ))}
    </div>
  );
}

interface Props {
  certificationId?: string;
  certSkillIds: Set<string>;
  initialRatings: Record<string, number>;
  onSave: (ratings: Record<string, number>) => Promise<void>;
  isSaving: boolean;
}

export default function ProfileSkillRater({
  certSkillIds,
  initialRatings,
  onSave,
  isSaving,
}: Props) {
  const { data: allSkills } = useSkills();

  const [ratings, setRatings] = useState<Record<string, number>>(() => {
    const init: Record<string, number> = {};
    if (allSkills) {
      allSkills.forEach((s) => {
        init[s.id] = nearestLevel(initialRatings[s.id] ?? 0.0);
      });
    }
    return init;
  });

  // Reinitialize once skills load
  React.useEffect(() => {
    if (!allSkills) return;
    setRatings((prev) => {
      const next = { ...prev };
      allSkills.forEach((s) => {
        if (!(s.id in next)) {
          next[s.id] = nearestLevel(initialRatings[s.id] ?? 0.0);
        }
      });
      return next;
    });
  }, [allSkills, initialRatings]);

  if (!allSkills) {
    return <div style={{ textAlign: "center", padding: "2rem" }}><span className="spinner" /></div>;
  }

  const certSkills = allSkills.filter((s) => certSkillIds.has(s.id));
  const otherSkills = allSkills.filter((s) => !certSkillIds.has(s.id));

  const setRating = (skillId: string, value: number) => {
    setRatings((prev) => ({ ...prev, [skillId]: value }));
  };

  const renderSkillRow = (skill: { id: string; name: string; category: string }) => (
    <div
      key={skill.id}
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "0.625rem 0.75rem",
        borderRadius: "var(--radius)",
        background: "var(--surface-alt, #f9fafb)",
        flexWrap: "wrap",
        gap: "0.5rem",
      }}
    >
      <div>
        <span style={{ fontSize: "0.9375rem", color: "var(--text)" }}>{skill.name}</span>
        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginLeft: "0.5rem" }}>
          {skill.category}
        </span>
      </div>
      <LevelPicker
        value={ratings[skill.id] ?? 0}
        onChange={(v) => setRating(skill.id, v)}
      />
    </div>
  );

  return (
    <div>
      {certSkills.length > 0 && (
        <div style={{ marginBottom: "1.5rem" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              marginBottom: "0.75rem",
            }}
          >
            <h3 style={{ margin: 0 }}>Certification skills</h3>
            <span className="badge badge-blue">cert</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {certSkills.map(renderSkillRow)}
          </div>
        </div>
      )}

      {otherSkills.length > 0 && (
        <div>
          {certSkills.length > 0 && (
            <div
              style={{
                borderTop: "1px solid var(--border)",
                paddingTop: "1.25rem",
                marginBottom: "0.75rem",
              }}
            >
              <h3 style={{ margin: "0 0 0.75rem" }}>Other skills</h3>
            </div>
          )}
          {certSkills.length === 0 && (
            <h3 style={{ marginBottom: "0.75rem" }}>All skills</h3>
          )}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {otherSkills.map(renderSkillRow)}
          </div>
        </div>
      )}

      <button
        className="btn btn-primary"
        style={{ marginTop: "1.5rem" }}
        disabled={isSaving}
        onClick={() => onSave(ratings)}
      >
        {isSaving ? <><span className="spinner" /> Saving…</> : "Save assessment"}
      </button>
    </div>
  );
}
