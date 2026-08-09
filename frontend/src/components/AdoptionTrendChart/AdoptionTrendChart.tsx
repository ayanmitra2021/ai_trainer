/**
 * AdoptionTrendChart — skill calibration: self-assessed baseline vs. quiz performance.
 *
 * Layout:
 *   • Skill summary cards (all skills, gap-colour coded)
 *   • Detail chart for the selected skill: dashed baseline + glowing quiz line + gap fill
 *
 * No Three.js — intentionally SVG so the data stays readable.
 * Premium aesthetic comes from glassmorphism cards, glow SVG filters, and gradient fills.
 */

import { useState } from "react";
import { useAdoptionTrends } from "../../hooks";
import { SkillAdoptionTrend } from "../../api/types";

interface Props {
  practitionerId: string;
}

// ── Gap classification ─────────────────────────────────────────────────────────

type GapLevel = "exceeding" | "on-track" | "moderate" | "significant";

function classifyGap(gap: number): GapLevel {
  if (gap < -0.05) return "exceeding";
  if (gap < 0.08) return "on-track";
  if (gap < 0.18) return "moderate";
  return "significant";
}

function gapPalette(level: GapLevel) {
  switch (level) {
    case "exceeding":
      return { border: "#22c55e", bg: "rgba(34,197,94,0.09)", text: "#16a34a", label: "Exceeding", fill: "#22c55e" };
    case "on-track":
      return { border: "#4dabf7", bg: "rgba(77,171,247,0.09)", text: "#3b82f6", label: "On track", fill: "#4dabf7" };
    case "moderate":
      return { border: "#f59e0b", bg: "rgba(245,158,11,0.09)", text: "#d97706", label: "Moderate gap", fill: "#f59e0b" };
    case "significant":
      return { border: "#ef4444", bg: "rgba(239,68,68,0.09)", text: "#dc2626", label: "Gap — needs work", fill: "#ef4444" };
  }
}

function directionIcon(direction: SkillAdoptionTrend["gap_direction"]) {
  if (direction === "closing") return { icon: "↘", color: "#22c55e", tip: "Gap closing" };
  if (direction === "widening") return { icon: "↗", color: "#ef4444", tip: "Gap widening" };
  if (direction === "stable") return { icon: "→", color: "#4dabf7", tip: "Stable" };
  return { icon: "·", color: "var(--text-muted)", tip: "No quiz data" };
}

// ── Skill summary card ─────────────────────────────────────────────────────────

function SkillCard({
  skill,
  isSelected,
  onClick,
}: {
  skill: SkillAdoptionTrend;
  isSelected: boolean;
  onClick: () => void;
}) {
  const level = classifyGap(skill.current_gap);
  const pal = gapPalette(level);
  const dir = directionIcon(skill.gap_direction);
  const baselinePct = (skill.self_assessed_score * 100).toFixed(0);
  const latestQuiz = skill.has_quiz_data
    ? skill.quiz_performance[skill.quiz_performance.length - 1]?.avg_score
    : null;
  const latestPct = latestQuiz != null ? (latestQuiz * 100).toFixed(0) : null;

  return (
    <button
      onClick={onClick}
      style={{
        display: "block",
        width: "100%",
        textAlign: "left",
        cursor: "pointer",
        background: isSelected ? pal.bg : "var(--surface)",
        border: `1px solid ${isSelected ? pal.border : "var(--border)"}`,
        borderLeft: `3px solid ${pal.border}`,
        borderRadius: "10px",
        padding: "0.875rem 1rem",
        marginBottom: "0.625rem",
        transition: "box-shadow 0.2s, border-color 0.2s",
        boxShadow: isSelected ? `0 0 20px ${pal.fill}30` : "none",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.375rem" }}>
        <span style={{ fontWeight: 600, fontSize: "0.875rem", color: "var(--text)" }}>
          {skill.skill_name}
        </span>
        <span
          title={dir.tip}
          style={{ color: dir.color, fontWeight: 700, fontSize: "1rem", marginLeft: "0.5rem", flexShrink: 0 }}
        >
          {dir.icon}
        </span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
        {/* Baseline bar */}
        <div style={{ flex: 1, height: 6, background: "var(--border)", borderRadius: 3, overflow: "hidden", position: "relative" }}>
          <div
            style={{
              position: "absolute",
              left: 0,
              top: 0,
              height: "100%",
              width: `${baselinePct}%`,
              background: "var(--border)",
              borderRadius: 3,
            }}
          />
          {latestQuiz != null && (
            <div
              style={{
                position: "absolute",
                left: 0,
                top: 0,
                height: "100%",
                width: `${latestPct}%`,
                background: `linear-gradient(90deg, ${pal.fill}, ${pal.fill}bb)`,
                borderRadius: 3,
                transition: "width 0.4s ease",
                boxShadow: `0 0 6px ${pal.fill}66`,
              }}
            />
          )}
        </div>
        <span style={{ fontSize: "0.75rem", color: pal.text, fontWeight: 600, whiteSpace: "nowrap" }}>
          {latestPct != null ? `${latestPct}% quiz` : `${baselinePct}% baseline`}
        </span>
        <span
          style={{
            fontSize: "0.7rem",
            padding: "0.1rem 0.5rem",
            borderRadius: "999px",
            background: pal.bg,
            color: pal.text,
            border: `1px solid ${pal.border}44`,
            whiteSpace: "nowrap",
            fontWeight: 500,
          }}
        >
          {pal.label}
        </span>
      </div>
    </button>
  );
}

// ── Detail chart (SVG line chart) ──────────────────────────────────────────────

const W = 580;
const H = 220;
const PAD = { top: 28, right: 24, bottom: 48, left: 52 };
const INNER_W = W - PAD.left - PAD.right;
const INNER_H = H - PAD.top - PAD.bottom;

function pctX(i: number, total: number) {
  return PAD.left + (total <= 1 ? 0.5 : i / (total - 1)) * INNER_W;
}
function pctY(score: number) {
  return PAD.top + (1 - Math.min(1, Math.max(0, score))) * INNER_H;
}

function DetailChart({ skill }: { skill: SkillAdoptionTrend }) {
  const level = classifyGap(skill.current_gap);
  const pal = gapPalette(level);
  const perf = skill.quiz_performance;
  const n = perf.length;
  const baseline = skill.self_assessed_score;
  const yBase = pctY(baseline);

  // Y-axis ticks: 0, 25, 50, 75, 100
  const yTicks = [0, 0.25, 0.5, 0.75, 1.0];
  // X-axis labels: show at most 6 evenly-spaced
  const xLabels = n === 0 ? [] : (() => {
    const step = Math.ceil(n / 6);
    return perf.filter((_, i) => i % step === 0 || i === n - 1);
  })();

  // Build quiz polyline & gap fill polygon
  let quizPoints = "";
  let gapPolygon = "";

  if (n > 0) {
    const pts = perf.map((p, i) => ({ x: pctX(i, n), y: pctY(p.avg_score) }));
    quizPoints = pts.map((p) => `${p.x},${p.y}`).join(" ");

    // Gap fill: along quiz line forward, then back along baseline
    const fwd = pts.map((p) => `${p.x},${p.y}`).join(" ");
    const bwd = `${pts[n - 1].x},${yBase} ${pts[0].x},${yBase}`;
    gapPolygon = `${fwd} ${bwd}`;
  }

  const noData = !skill.has_quiz_data || n === 0;

  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderTop: `2px solid ${pal.border}`,
        borderRadius: "10px",
        padding: "1.25rem 1.25rem 0.875rem",
        boxShadow: `0 0 30px ${pal.fill}12`,
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem", flexWrap: "wrap", gap: "0.5rem" }}>
        <div>
          <h3 style={{ margin: 0, fontSize: "1rem" }}>{skill.skill_name}</h3>
          <p style={{ margin: "0.15rem 0 0", fontSize: "0.8125rem", color: "var(--text-muted)" }}>
            Baseline (self-assessed) vs. quiz performance over time
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
          <LegendItem color={pal.fill} dashed label={`Baseline ${(baseline * 100).toFixed(0)}%`} />
          <LegendItem color={pal.fill} dashed={false} label={`Quiz avg ${skill.has_quiz_data ? (perf[perf.length - 1]?.avg_score * 100).toFixed(0) + "%" : "—"}`} />
        </div>
      </div>

      {noData ? (
        <div
          style={{
            height: H,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--text-muted)",
            fontSize: "0.875rem",
            border: "2px dashed var(--border)",
            borderRadius: "8px",
          }}
        >
          No quiz attempts yet. Take quizzes for this skill to see performance data.
        </div>
      ) : (
        <svg
          width="100%"
          viewBox={`0 0 ${W} ${H}`}
          style={{ display: "block", overflow: "visible" }}
          role="img"
          aria-label={`${skill.skill_name} quiz performance chart`}
        >
          <defs>
            {/* Glow filter for quiz line */}
            <filter id="line-glow" x="-20%" y="-80%" width="140%" height="260%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="3.5" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            {/* Gap fill gradient */}
            <linearGradient id={`gap-grad-${skill.skill_id}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={pal.fill} stopOpacity="0.28" />
              <stop offset="100%" stopColor={pal.fill} stopOpacity="0.04" />
            </linearGradient>
          </defs>

          {/* Y-axis gridlines and labels */}
          {yTicks.map((v) => {
            const y = pctY(v);
            return (
              <g key={v}>
                <line
                  x1={PAD.left} y1={y} x2={W - PAD.right} y2={y}
                  stroke="var(--border)"
                  strokeWidth={1}
                  strokeOpacity={v === 0 || v === 1 ? 0.5 : 0.3}
                />
                <text
                  x={PAD.left - 6} y={y}
                  textAnchor="end"
                  dominantBaseline="middle"
                  fontSize={10}
                  fill="var(--text-muted)"
                >
                  {(v * 100).toFixed(0)}%
                </text>
              </g>
            );
          })}

          {/* Gap fill polygon (between quiz line and baseline) */}
          {n > 0 && (
            <polygon
              points={gapPolygon}
              fill={`url(#gap-grad-${skill.skill_id})`}
            />
          )}

          {/* Baseline dashed line */}
          <line
            x1={PAD.left} y1={yBase} x2={W - PAD.right} y2={yBase}
            stroke={pal.fill}
            strokeWidth={1.5}
            strokeDasharray="6 4"
            strokeOpacity={0.7}
          />

          {/* Quiz performance polyline (glowing) */}
          {n > 0 && (
            <>
              <polyline
                points={quizPoints}
                fill="none"
                stroke={pal.fill}
                strokeWidth={2.5}
                strokeLinejoin="round"
                strokeLinecap="round"
                filter="url(#line-glow)"
              />
              {/* Dots at data points */}
              {perf.map((p, i) => (
                <g key={i}>
                  <circle
                    cx={pctX(i, n)} cy={pctY(p.avg_score)}
                    r={4}
                    fill={pal.fill}
                    fillOpacity={0.9}
                    filter="url(#line-glow)"
                  />
                  <circle
                    cx={pctX(i, n)} cy={pctY(p.avg_score)}
                    r={2}
                    fill="var(--bg)"
                  />
                </g>
              ))}
            </>
          )}

          {/* X-axis labels */}
          {xLabels.map((p, i) => {
            const origIdx = perf.indexOf(p);
            return (
              <text
                key={i}
                x={pctX(origIdx, n)}
                y={H - 8}
                textAnchor="middle"
                fontSize={9.5}
                fill="var(--text-muted)"
              >
                {p.period_label.length > 12 ? p.period_label.slice(0, 11) + "…" : p.period_label}
              </text>
            );
          })}

          {/* Y-axis label */}
          <text
            x={12} y={PAD.top + INNER_H / 2}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={9.5}
            fill="var(--text-muted)"
            transform={`rotate(-90, 12, ${PAD.top + INNER_H / 2})`}
          >
            Score
          </text>

          {/* Attempt count as tiny bar along x-axis */}
          {perf.map((p, i) => {
            const maxAttempts = Math.max(...perf.map((d) => d.attempt_count), 1);
            const barH = Math.round((p.attempt_count / maxAttempts) * 10);
            const x = pctX(i, n);
            const y = PAD.top + INNER_H + 4;
            return (
              <rect
                key={`bar-${i}`}
                x={x - 2} y={y + (10 - barH)}
                width={4} height={barH}
                fill={pal.fill}
                fillOpacity={0.4}
                rx={1}
              />
            );
          })}
        </svg>
      )}

      {/* Attempt note */}
      {!noData && (
        <p style={{ margin: "0.25rem 0 0", fontSize: "0.75rem", color: "var(--text-muted)" }}>
          Mini-bars below x-axis show relative attempt volume per period.
          {skill.quiz_performance.reduce((sum, p) => sum + p.attempt_count, 0)} total attempt
          {skill.quiz_performance.reduce((sum, p) => sum + p.attempt_count, 0) !== 1 ? "s" : ""} across {n} period{n !== 1 ? "s" : ""}.
        </p>
      )}
    </div>
  );
}

function LegendItem({ color, dashed, label }: { color: string; dashed: boolean; label: string }) {
  return (
    <span style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.75rem", color: "var(--text-muted)" }}>
      <svg width={22} height={8}>
        <line
          x1={0} y1={4} x2={22} y2={4}
          stroke={color}
          strokeWidth={dashed ? 1.5 : 2}
          strokeDasharray={dashed ? "5 3" : undefined}
        />
        {!dashed && <circle cx={11} cy={4} r={3} fill={color} />}
      </svg>
      {label}
    </span>
  );
}

// ── No quiz state ──────────────────────────────────────────────────────────────

function NoQuizState() {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "0.75rem",
        padding: "3rem 1.5rem",
        border: "2px dashed var(--border)",
        borderRadius: "12px",
        textAlign: "center",
        color: "var(--text-muted)",
      }}
    >
      <div style={{ fontSize: "2.5rem" }}>📊</div>
      <p style={{ margin: 0, maxWidth: 420, lineHeight: 1.6 }}>
        No skill data yet. Build your profile and generate a learning path, then take quizzes
        to see your self-assessed baseline vs. actual quiz performance here.
      </p>
    </div>
  );
}

// ── Main ───────────────────────────────────────────────────────────────────────

export default function AdoptionTrendChart({ practitionerId }: Props) {
  const { data, isLoading } = useAdoptionTrends(practitionerId);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div style={{ textAlign: "center", padding: "2rem" }}>
        <span className="spinner" />
      </div>
    );
  }

  const skills = data?.skills ?? [];

  if (skills.length === 0) {
    return (
      <div style={{ marginTop: "2rem" }}>
        <h3 style={{ marginBottom: "0.75rem" }}>Skill calibration</h3>
        <NoQuizState />
      </div>
    );
  }

  // Auto-select first skill with quiz data, or just first skill
  const effectiveId =
    selectedId ?? (skills.find((s) => s.has_quiz_data)?.skill_id ?? skills[0]?.skill_id ?? null);

  const selectedSkill = skills.find((s) => s.skill_id === effectiveId) ?? null;

  // Sort: with-data first, then by gap descending
  const sorted = [...skills].sort((a, b) => {
    if (a.has_quiz_data !== b.has_quiz_data) return a.has_quiz_data ? -1 : 1;
    return b.current_gap - a.current_gap;
  });

  const withDataCount = skills.filter((s) => s.has_quiz_data).length;
  const avgGap =
    withDataCount > 0
      ? skills
          .filter((s) => s.has_quiz_data)
          .reduce((sum, s) => sum + s.current_gap, 0) / withDataCount
      : null;

  return (
    <div style={{ marginTop: "2rem" }}>
      {/* Section header */}
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", flexWrap: "wrap", gap: "0.5rem", marginBottom: "1rem" }}>
        <div>
          <h3 style={{ margin: 0, marginBottom: "0.2rem" }}>Skill calibration</h3>
          <p style={{ margin: 0, fontSize: "0.8125rem", color: "var(--text-muted)" }}>
            Self-assessed baseline vs. quiz performance · {skills.length} skill{skills.length !== 1 ? "s" : ""}
            {withDataCount > 0 && (
              <> · avg gap{" "}
                <strong style={{ color: avgGap != null && avgGap < 0 ? "#22c55e" : avgGap != null && avgGap > 0.15 ? "#ef4444" : "#f59e0b" }}>
                  {avgGap != null ? `${avgGap > 0 ? "+" : ""}${(avgGap * 100).toFixed(0)}%` : "—"}
                </strong>
              </>
            )}
          </p>
        </div>
        {/* Legend dots */}
        <div style={{ display: "flex", gap: "0.875rem", fontSize: "0.75rem", color: "var(--text-muted)", flexWrap: "wrap" }}>
          {(["exceeding", "on-track", "moderate", "significant"] as GapLevel[]).map((level) => {
            const p = gapPalette(level);
            return (
              <span key={level} style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: p.fill, display: "inline-block", boxShadow: `0 0 5px ${p.fill}88` }} />
                {p.label}
              </span>
            );
          })}
        </div>
      </div>

      <div style={{ display: "flex", gap: "1.5rem", alignItems: "flex-start", flexWrap: "wrap" }}>
        {/* Skill list */}
        <div style={{ minWidth: 220, flex: "0 0 280px" }}>
          {sorted.map((s) => (
            <SkillCard
              key={s.skill_id}
              skill={s}
              isSelected={s.skill_id === effectiveId}
              onClick={() => setSelectedId(s.skill_id)}
            />
          ))}
        </div>

        {/* Detail chart */}
        <div style={{ flex: 1, minWidth: 300 }}>
          {selectedSkill ? (
            <DetailChart skill={selectedSkill} />
          ) : (
            <div style={{ color: "var(--text-muted)", padding: "2rem", textAlign: "center", fontSize: "0.875rem" }}>
              Select a skill to see its chart.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
