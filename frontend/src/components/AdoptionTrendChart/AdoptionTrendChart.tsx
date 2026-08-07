/**
 * AdoptionTrendChart
 *
 * Compares a practitioner's self-assessed score (the "trained baseline" from
 * profile building) against their weekly quiz-attempt performance per skill.
 *
 * Design rationale for the three-dimensional problem (time × skill × score type):
 *   • Dimension 1 — time: X-axis of the main chart (ISO-week buckets).
 *   • Dimension 2 — skill: solved with a skill-selector card grid at the top.
 *     Cards summarise every skill at a glance; clicking one drills into the chart.
 *   • Dimension 3 — score type: two lines on the same chart:
 *       – dashed horizontal line  = self-assessed baseline (trained score)
 *       – solid polyline + dots   = weekly quiz-attempt average
 *       – shaded area between     = the gap (orange = underperforming,
 *                                           blue  = exceeding expectations)
 */

import { useState } from "react";
import { useAdoptionTrends } from "../../hooks";
import type { SkillAdoptionTrend, SkillQuizPeriod } from "../../api/types";

// ── constants ──────────────────────────────────────────────────────────────────

const W = 580;
const H = 240;
const PAD = { top: 24, right: 24, bottom: 44, left: 48 };
const IW = W - PAD.left - PAD.right;  // inner width
const IH = H - PAD.top - PAD.bottom;  // inner height

// ── colour helpers ─────────────────────────────────────────────────────────────

function gapColor(gap: number): { bg: string; text: string; label: string } {
  if (gap > 0.25)  return { bg: "#fee2e2", text: "#dc2626", label: "Large gap" };
  if (gap > 0.08)  return { bg: "#ffedd5", text: "#ea580c", label: "Some gap"  };
  if (gap > -0.08) return { bg: "#dcfce7", text: "#16a34a", label: "On track"  };
  return              { bg: "#dbeafe", text: "#2563eb", label: "Exceeding"    };
}

const DIRECTION_ICON: Record<string, string> = {
  closing:  "↑ closing",
  widening: "↓ widening",
  stable:   "→ stable",
  no_data:  "—",
};
const DIRECTION_COLOR: Record<string, string> = {
  closing:  "#16a34a",
  widening: "#dc2626",
  stable:   "#6b7280",
  no_data:  "#9ca3af",
};

// ── SkillSummaryCard ───────────────────────────────────────────────────────────

function SkillSummaryCard({
  skill,
  isSelected,
  onClick,
}: {
  skill: SkillAdoptionTrend;
  isSelected: boolean;
  onClick: () => void;
}) {
  const { bg, text, label } = gapColor(skill.current_gap);
  const latestQuiz = skill.quiz_performance.at(-1);

  return (
    <button
      onClick={onClick}
      style={{
        textAlign: "left",
        padding: "0.75rem",
        borderRadius: "8px",
        border: isSelected
          ? "2px solid var(--primary)"
          : "1px solid var(--border)",
        background: isSelected ? "var(--primary-subtle, #eff6ff)" : "var(--surface)",
        cursor: "pointer",
        minWidth: 160,
        flex: "1 1 160px",
      }}
    >
      {/* Skill name */}
      <div style={{ fontWeight: 600, fontSize: "0.8125rem", marginBottom: "0.375rem", color: "var(--text)" }}>
        {skill.skill_name}
      </div>

      {/* Score row */}
      <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: "0.375rem" }}>
        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
          Baseline {pct(skill.self_assessed_score)}
        </span>
        {latestQuiz && (
          <>
            <span style={{ color: "var(--text-muted)", fontSize: "0.7rem" }}>·</span>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              Quiz {pct(latestQuiz.avg_score)}
            </span>
          </>
        )}
      </div>

      {/* Gap badge */}
      <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
        <span style={{ fontSize: "0.6875rem", padding: "0.15em 0.55em", borderRadius: "999px", background: bg, color: text, fontWeight: 600 }}>
          {skill.has_quiz_data ? label : "No quizzes yet"}
        </span>
        {skill.has_quiz_data && (
          <span style={{ fontSize: "0.6875rem", color: DIRECTION_COLOR[skill.gap_direction], fontWeight: 500 }}>
            {DIRECTION_ICON[skill.gap_direction]}
          </span>
        )}
      </div>
    </button>
  );
}

// ── helpers ───────────────────────────────────────────────────────────────────

function pct(v: number) {
  return `${Math.round(v * 100)}%`;
}

// ── DetailChart SVG ───────────────────────────────────────────────────────────

function DetailChart({ skill }: { skill: SkillAdoptionTrend }) {
  const periods = skill.quiz_performance;
  const n = periods.length;

  // Scale helpers
  const scaleX = (i: number) => (n > 1 ? (i / (n - 1)) * IW : IW / 2);
  const scaleY = (v: number) => IH - v * IH;

  // Self-assessed reference Y
  const refY = scaleY(skill.self_assessed_score);

  // Y-axis ticks
  const yTicks = [0, 0.25, 0.5, 0.75, 1.0];

  // Build SVG path strings for the quiz line and the gap area fill
  const quizPoints = periods.map((p, i) => ({ x: scaleX(i), y: scaleY(p.avg_score) }));

  // Area fill path: go along quiz line → across at self-assessed level → back
  let areaPath = "";
  if (n > 0) {
    const pts = quizPoints.map((pt, i) => `${i === 0 ? "M" : "L"}${pt.x},${pt.y}`).join(" ");
    // Close via the self-assessed horizontal line, right-to-left
    areaPath = `${pts} L${quizPoints[n - 1].x},${refY} L${quizPoints[0].x},${refY} Z`;
  }

  // Determine fill color based on overall tendency
  const avgQuiz = n > 0 ? periods.reduce((s, p) => s + p.avg_score, 0) / n : 0;
  const overallGap = skill.self_assessed_score - avgQuiz;
  const areaFill = overallGap > 0 ? "#fed7aa" : "#bbf7d0"; // orange-200 / green-200
  const areaStroke = overallGap > 0 ? "#fb923c" : "#4ade80";

  // X-axis tick every N to avoid crowding (max ~6 labels)
  const maxLabels = 6;
  const step = Math.max(1, Math.ceil(n / maxLabels));

  return (
    <div style={{ overflowX: "auto" }}>
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        style={{ display: "block", maxWidth: "100%", overflow: "visible" }}
        role="img"
        aria-label={`Skill calibration chart for ${skill.skill_name}`}
      >
        <g transform={`translate(${PAD.left},${PAD.top})`}>
          {/* Y gridlines + labels */}
          {yTicks.map((t) => (
            <g key={t}>
              <line
                x1={0} y1={scaleY(t)} x2={IW} y2={scaleY(t)}
                stroke="var(--border)" strokeWidth={1}
                strokeDasharray={t > 0 && t < 1 ? "3,3" : undefined}
              />
              <text x={-8} y={scaleY(t)} dominantBaseline="middle" textAnchor="end"
                fontSize={10} fill="var(--text-muted)">
                {Math.round(t * 100)}%
              </text>
            </g>
          ))}

          {/* X-axis labels */}
          {periods.map((p, i) => {
            if (i % step !== 0 && i !== n - 1) return null;
            return (
              <text key={i} x={scaleX(i)} y={IH + 16} textAnchor="middle"
                fontSize={10} fill="var(--text-muted)">
                {p.period_label}
              </text>
            );
          })}
          <text x={IW / 2} y={IH + 34} textAnchor="middle" fontSize={11} fill="var(--text-muted)">
            Week
          </text>

          {/* Gap area fill (between quiz line and self-assessed reference) */}
          {n > 0 && (
            <path
              d={areaPath}
              fill={areaFill}
              fillOpacity={0.45}
              stroke="none"
            />
          )}

          {/* Self-assessed reference line (dashed) */}
          <line
            x1={0} y1={refY} x2={IW} y2={refY}
            stroke="var(--text-muted)"
            strokeWidth={2}
            strokeDasharray="6,4"
          />
          <text x={IW + 4} y={refY} dominantBaseline="middle"
            fontSize={9} fill="var(--text-muted)" fontStyle="italic">
            baseline
          </text>

          {/* Quiz performance polyline */}
          {n > 1 && (
            <polyline
              points={quizPoints.map(pt => `${pt.x},${pt.y}`).join(" ")}
              fill="none"
              stroke={areaStroke}
              strokeWidth={2.5}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          )}

          {/* Quiz data points */}
          {quizPoints.map((pt, i) => (
            <g key={i}>
              <circle cx={pt.x} cy={pt.y} r={5} fill={areaStroke} stroke="white" strokeWidth={1.5}>
                <title>
                  {periods[i].period_label}: {pct(periods[i].avg_score)} quiz avg
                  ({periods[i].attempt_count} attempt{periods[i].attempt_count !== 1 ? "s" : ""})
                </title>
              </circle>
            </g>
          ))}
        </g>
      </svg>

      {/* Legend */}
      <div style={{ display: "flex", gap: "1.25rem", marginTop: "0.625rem", fontSize: "0.8rem", color: "var(--text-muted)", paddingLeft: PAD.left }}>
        <span style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
          <svg width={20} height={2}><line x1={0} y1={1} x2={20} y2={1} stroke="var(--text-muted)" strokeWidth={2} strokeDasharray="5,3" /></svg>
          Self-assessed baseline
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
          <svg width={20} height={4}><line x1={0} y1={2} x2={20} y2={2} stroke={areaStroke} strokeWidth={2.5} /></svg>
          Weekly quiz average
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
          <svg width={12} height={10}><rect width={12} height={10} fill={areaFill} fillOpacity={0.6} /></svg>
          {overallGap > 0 ? "Gap to close" : "Exceeding baseline"}
        </span>
      </div>
    </div>
  );
}

// ── NoQuizState ───────────────────────────────────────────────────────────────

function NoQuizState({ skillName }: { skillName: string }) {
  return (
    <div style={{
      padding: "2rem",
      textAlign: "center",
      border: "1px dashed var(--border)",
      borderRadius: "8px",
      color: "var(--text-muted)",
      fontSize: "0.875rem",
    }}>
      <div style={{ fontSize: "1.5rem", marginBottom: "0.5rem" }}>📊</div>
      <strong>{skillName}</strong>
      <p style={{ margin: "0.5rem 0 0" }}>
        No quiz attempts yet for this skill. The chart appears as you take quizzes
        on your learning path.
      </p>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  practitionerId: string;
}

export default function AdoptionTrendChart({ practitionerId }: Props) {
  const { data, isLoading } = useAdoptionTrends(practitionerId);
  const [selectedSkillId, setSelectedSkillId] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div style={{ textAlign: "center", padding: "2rem" }}>
        <span className="spinner" />
      </div>
    );
  }

  if (!data || data.skills.length === 0) {
    return (
      <div style={{ marginTop: "2rem" }}>
        <h3 style={{ marginBottom: "0.5rem" }}>Skill Calibration</h3>
        <div className="empty-state">
          No skill data yet. Build your profile and generate a learning path to see your
          skill calibration chart.
        </div>
      </div>
    );
  }

  // Default: first skill with quiz data, then just the first skill
  const resolvedSkill =
    data.skills.find((s) => s.skill_id === selectedSkillId) ??
    data.skills.find((s) => s.has_quiz_data) ??
    data.skills[0];

  const { bg, text } = gapColor(resolvedSkill.current_gap);

  return (
    <div style={{ marginTop: "2rem" }}>
      <div style={{ marginBottom: "1rem" }}>
        <h3 style={{ marginBottom: "0.25rem" }}>Skill Calibration</h3>
        <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", margin: 0 }}>
          Compares your self-assessed baseline (set during profile building) against
          your actual weekly quiz performance. The gap should narrow as you practise.
        </p>
      </div>

      {/* Skill summary cards */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.625rem", marginBottom: "1.25rem" }}>
        {data.skills.map((s) => (
          <SkillSummaryCard
            key={s.skill_id}
            skill={s}
            isSelected={s.skill_id === resolvedSkill.skill_id}
            onClick={() => setSelectedSkillId(s.skill_id)}
          />
        ))}
      </div>

      {/* Detail panel for selected skill */}
      <div className="card">
        {/* Panel header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem", flexWrap: "wrap", gap: "0.5rem" }}>
          <div>
            <span style={{ fontWeight: 700, fontSize: "1rem" }}>{resolvedSkill.skill_name}</span>
            <span style={{ marginLeft: "0.75rem", fontSize: "0.8125rem", color: "var(--text-muted)" }}>
              Self-assessed: <strong>{pct(resolvedSkill.self_assessed_score)}</strong>
            </span>
            {resolvedSkill.quiz_performance.length > 0 && (
              <span style={{ marginLeft: "0.75rem", fontSize: "0.8125rem", color: "var(--text-muted)" }}>
                Latest quiz avg:{" "}
                <strong>{pct(resolvedSkill.quiz_performance.at(-1)!.avg_score)}</strong>
              </span>
            )}
          </div>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            {resolvedSkill.has_quiz_data && (
              <span style={{ fontSize: "0.8125rem", padding: "0.2em 0.65em", borderRadius: "999px", background: bg, color: text, fontWeight: 600 }}>
                {resolvedSkill.current_gap > 0
                  ? `${pct(resolvedSkill.current_gap)} gap`
                  : `${pct(Math.abs(resolvedSkill.current_gap))} ahead`}
              </span>
            )}
            {resolvedSkill.has_quiz_data && (
              <span style={{ fontSize: "0.8125rem", color: DIRECTION_COLOR[resolvedSkill.gap_direction], fontWeight: 500 }}>
                {DIRECTION_ICON[resolvedSkill.gap_direction]}
              </span>
            )}
          </div>
        </div>

        {/* Chart or placeholder */}
        {resolvedSkill.has_quiz_data ? (
          <DetailChart skill={resolvedSkill} />
        ) : (
          <NoQuizState skillName={resolvedSkill.skill_name} />
        )}
      </div>
    </div>
  );
}
