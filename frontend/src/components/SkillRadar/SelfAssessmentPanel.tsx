/**
 * SelfAssessmentPanel — lets a practitioner rate their own skill levels.
 *
 * Ratings are written as skill_profile_events (source="self_assessment").
 * The radar updates on the next "Regenerate path" run, which re-runs the
 * Skill Profiler and incorporates all accumulated evidence.
 */

import { useEffect, useState } from "react";
import { useSkills, useSubmitSelfAssessment } from "../../hooks";
import type { SkillSnapshot } from "../../api/types";

interface Props {
  practitionerId: string;
  /** Current snapshots — used to pre-populate the sliders. */
  snapshots: SkillSnapshot[];
  onSaved: () => void;
}

// Five human-readable levels mapped to signal_strength values
const LEVELS = [
  { label: "None",       value: 0.0,  color: "#e5e7eb" },
  { label: "Beginner",   value: 0.25, color: "#fde68a" },
  { label: "Familiar",   value: 0.5,  color: "#93c5fd" },
  { label: "Proficient", value: 0.75, color: "#6ee7b7" },
  { label: "Expert",     value: 1.0,  color: "#818cf8" },
] as const;

type LevelValue = 0 | 0.25 | 0.5 | 0.75 | 1;

function nearestLevel(score: number): LevelValue {
  const values: LevelValue[] = [0, 0.25, 0.5, 0.75, 1];
  return values.reduce((best, v) =>
    Math.abs(v - score) < Math.abs(best - score) ? v : best,
  );
}

function LevelPicker({
  value,
  onChange,
}: {
  value: LevelValue;
  onChange: (v: LevelValue) => void;
}) {
  return (
    <div style={{ display: "flex", gap: "0.375rem" }}>
      {LEVELS.map((lvl) => {
        const selected = lvl.value === value;
        return (
          <button
            key={lvl.label}
            title={lvl.label}
            onClick={() => onChange(lvl.value as LevelValue)}
            style={{
              padding: "0.25rem 0.625rem",
              borderRadius: "999px",
              border: selected ? `2px solid ${lvl.color}` : "2px solid var(--border)",
              background: selected ? lvl.color : "var(--surface-alt)",
              color: selected ? "#1a1a1a" : "var(--text)",
              fontSize: "0.75rem",
              fontWeight: selected ? 700 : 400,
              cursor: "pointer",
              transition: "all 0.12s",
            }}
          >
            {lvl.label}
          </button>
        );
      })}
    </div>
  );
}

export default function SelfAssessmentPanel({ practitionerId, snapshots, onSaved }: Props) {
  const { data: allSkills, isLoading: skillsLoading } = useSkills();
  const submitAssessment = useSubmitSelfAssessment(practitionerId);

  // skill_id → chosen level value
  const [ratings, setRatings] = useState<Record<string, LevelValue>>({});
  const [saved, setSaved] = useState(false);

  // Pre-populate from current snapshots on first load
  useEffect(() => {
    if (!allSkills) return;
    const initial: Record<string, LevelValue> = {};
    allSkills.forEach((skill) => {
      const snap = snapshots.find((s) => s.skill_id === skill.id);
      initial[skill.id] = snap ? nearestLevel(snap.mastery_score) : 0;
    });
    setRatings(initial);
  }, [allSkills, snapshots]);

  if (skillsLoading) return null;
  if (!allSkills || allSkills.length === 0) return null;

  // Group skills by category
  const byCategory = allSkills.reduce<Record<string, typeof allSkills>>((acc, skill) => {
    const cat = skill.category ?? "Other";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(skill);
    return acc;
  }, {});

  const handleSave = async () => {
    const assessments = Object.entries(ratings).map(([skill_id, signal_strength]) => ({
      skill_id,
      signal_strength,
    }));
    await submitAssessment.mutateAsync({ assessments });
    setSaved(true);
    onSaved();
    setTimeout(() => setSaved(false), 4000);
  };

  return (
    <div style={{ marginTop: "2rem" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.5rem" }}>
        <div>
          <h3 style={{ margin: 0 }}>Rate your skill levels</h3>
          <p style={{ margin: "0.25rem 0 0", fontSize: "0.8125rem", color: "var(--text-muted)" }}>
            Your ratings are saved as self-assessment signals. Click{" "}
            <strong>Regenerate path</strong> above to update the radar.
          </p>
        </div>
      </div>

      {/* Legend */}
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "1.25rem" }}>
        {LEVELS.map((lvl) => (
          <span
            key={lvl.label}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.3rem",
              fontSize: "0.75rem",
              color: "var(--text-muted)",
            }}
          >
            <span
              style={{
                display: "inline-block",
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: lvl.color,
                border: "1px solid #ccc",
              }}
            />
            {lvl.label}
          </span>
        ))}
      </div>

      {/* Skills grouped by category */}
      {Object.entries(byCategory).map(([category, categorySkills]) => (
        <div key={category} style={{ marginBottom: "1.5rem" }}>
          <p
            style={{
              fontSize: "0.75rem",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              color: "var(--text-muted)",
              margin: "0 0 0.75rem",
            }}
          >
            {category}
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.625rem" }}>
            {categorySkills.map((skill) => (
              <div
                key={skill.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "1rem",
                  flexWrap: "wrap",
                  padding: "0.5rem 0.75rem",
                  borderRadius: "6px",
                  background: "var(--surface-alt)",
                  border: "1px solid var(--border)",
                }}
              >
                <span
                  style={{
                    minWidth: "180px",
                    fontSize: "0.875rem",
                    fontWeight: 500,
                    color: "var(--text)",
                  }}
                >
                  {skill.name}
                </span>
                <LevelPicker
                  value={ratings[skill.id] ?? 0}
                  onChange={(v) => setRatings((prev) => ({ ...prev, [skill.id]: v }))}
                />
              </div>
            ))}
          </div>
        </div>
      ))}

      <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginTop: "0.5rem" }}>
        <button
          className="btn btn-primary"
          onClick={handleSave}
          disabled={submitAssessment.isPending}
        >
          {submitAssessment.isPending ? (
            <><span className="spinner" /> Saving…</>
          ) : (
            "Save assessment"
          )}
        </button>
        {saved && (
          <span style={{ fontSize: "0.875rem", color: "var(--success, #16a34a)" }}>
            ✓ Saved — click <strong>Regenerate path</strong> to update your radar.
          </span>
        )}
        {submitAssessment.isError && (
          <span style={{ fontSize: "0.875rem", color: "var(--danger, #dc2626)" }}>
            Save failed. Please try again.
          </span>
        )}
      </div>
    </div>
  );
}
