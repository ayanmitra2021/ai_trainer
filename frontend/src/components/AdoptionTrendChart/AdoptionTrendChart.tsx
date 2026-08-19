/**
 * AdoptionTrendChart — skill calibration: self-assessed baseline vs. quiz performance.
 *
 * Layout (redesigned Phase 19):
 *   • Compact chip grid   — all skills at a glance, gap-colour coded, 2–5 per row
 *   • Full-width chart    — detail for the selected skill below the grid
 *
 * No Three.js — intentionally SVG so the data stays readable.
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
      return { border: "#ef4444", bg: "rgba(239,68,68,0.09)", text: "#dc2626", label: "Gap", fill: "#ef4444" };
  }
}

function directionIcon(direction: SkillAdoptionTrend["gap_direction"]) {
  if (direction === "closing")  return { icon: "↘", color: "#22c55e", tip: "Gap closing" };
  if (direction === "widening") return { icon: "↗", color: "#ef4444", tip: "Gap widening" };
  if (direction === "stable")   return { icon: "→", color: "#4dabf7", tip: "Stable" };
  return { icon: "·", color: "var(--text-muted)", tip: "No quiz data" };
}

// ── Skill chip (compact grid tile) ────────────────────────────────────────────

function SkillChip({
  skill,
  isSelected,
  onClick,
}: {
  skill: SkillAdoptionTrend;
  isSelected: boolean;
  onClick: () => void;
}) {
  const level = classifyGap(skill.current_gap);
  const pal   = gapPalette(level);
  const dir   = directionIcon(skill.gap_direction);

  const baselinePct = Math.round(skill.self_assessed_score * 100);
  const latestQuiz  = skill.has_quiz_data && skill.quiz_performance.length > 0
    ? skill.quiz_performance[skill.quiz_performance.length - 1].avg_score
    : null;
  const quizPct = latestQuiz != null ? Math.round(latestQuiz * 100) : null;

  return (
    <button
      onClick={onClick}
      title={skill.skill_name}
      style={{
        textAlign: "left",
        background: isSelected
          ? `color-mix(in srgb, ${pal.fill} 11%, var(--surface))`
          : "var(--surface)",
        border: `1px solid ${isSelected ? pal.border : "var(--border)"}`,
        borderLeft: `3px solid ${pal.border}`,
        borderRadius: "8px",
        padding: "0.625rem 0.75rem",
        cursor: "pointer",
        transition: "box-shadow 0.15s, background 0.15s, border-color 0.15s",
        boxShadow: isSelected
          ? `0 0 0 1px ${pal.border}33, 0 4px 18px ${pal.fill}22`
          : "none",
        display: "flex",
        flexDirection: "column",
        gap: "0.4rem",
        minWidth: 0,
      }}
    >
      {/* Row 1: name + direction arrow */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.25rem" }}>
        <span style={{
          fontWeight: 600,
          fontSize: "0.8125rem",
          color: "var(--text)",
          lineHeight: 1.3,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          flex: 1,
          minWidth: 0,
        }}>
          {skill.skill_name}
        </span>
        <span style={{ color: dir.color, fontSize: "0.875rem", fontWeight: 700, flexShrink: 0 }} title={dir.tip}>
          {dir.icon}
        </span>
      </div>

      {/* Row 2: dual-track progress bar (baseline dim, quiz vivid) */}
      <div style={{ height: 4, background: "var(--border)", borderRadius: 2, position: "relative", overflow: "hidden" }}>
        {/* Baseline track */}
        <div style={{
          position: "absolute", left: 0, top: 0, bottom: 0,
          width: `${baselinePct}%`,
          background: `${pal.fill}40`,
          borderRadius: 2,
        }} />
        {/* Quiz score track (on top, brighter, glowing) */}
        {quizPct != null && (
          <div style={{
            position: "absolute", left: 0, top: 0, bottom: 0,
            width: `${quizPct}%`,
            background: pal.fill,
            borderRadius: 2,
            boxShadow: `0 0 5px ${pal.fill}88`,
          }} />
        )}
      </div>

      {/* Row 3: score number + status badge */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{
          fontSize: "0.75rem",
          color: pal.text,
          fontWeight: 700,
          fontVariantNumeric: "tabular-nums",
        }}>
          {quizPct != null ? `${quizPct}%` : `${baselinePct}%`}
        </span>
        <span style={{
          fontSize: "0.675rem",
          padding: "0.1rem 0.45rem",
          borderRadius: "999px",
          background: `${pal.fill}22`,
          color: pal.text,
          fontWeight: 500,
          letterSpacing: "0.01em",
          whiteSpace: "nowrap",
        }}>
          {pal.label}
        </span>
      </div>
    </button>
  );
}

// ── Detail chart (SVG, full-width) ─────────────────────────────────────────────

const W = 720;
const H = 260;
const PAD = { top: 28, right: 28, bottom: 48, left: 52 };
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
  const pal   = gapPalette(level);
  const perf  = skill.quiz_performance;
  const n     = perf.length;
  const baseline = skill.self_assessed_score;
  const yBase    = pctY(baseline);

  const yTicks = [0, 0.25, 0.5, 0.75, 1.0];
  const xLabels = n === 0 ? [] : (() => {
    const step = Math.ceil(n / 6);
    return perf.filter((_, i) => i % step === 0 || i === n - 1);
  })();

  let quizPoints  = "";
  let gapPolygon  = "";

  if (n > 0) {
    const pts = perf.map((p, i) => ({ x: pctX(i, n), y: pctY(p.avg_score) }));
    quizPoints  = pts.map((p) => `${p.x},${p.y}`).join(" ");
    const fwd   = pts.map((p) => `${p.x},${p.y}`).join(" ");
    const bwd   = `${pts[n - 1].x},${yBase} ${pts[0].x},${yBase}`;
    gapPolygon  = `${fwd} ${bwd}`;
  }

  const noData = !skill.has_quiz_data || n === 0;

  return (
    <div style={{
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderTop: `2px solid ${pal.border}`,
      borderRadius: "10px",
      padding: "1.25rem 1.25rem 0.875rem",
      boxShadow: `0 0 28px ${pal.fill}10`,
    }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem", flexWrap: "wrap", gap: "0.5rem" }}>
        <div>
          <h3 style={{ margin: 0, fontSize: "1rem" }}>{skill.skill_name}</h3>
          <p style={{ margin: "0.15rem 0 0", fontSize: "0.8125rem", color: "var(--text-muted)" }}>
            Self-assessed baseline vs. quiz performance over time
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
          <LegendItem color={pal.fill} dashed label={`Baseline ${(baseline * 100).toFixed(0)}%`} />
          <LegendItem
            color={pal.fill}
            dashed={false}
            label={`Quiz avg ${skill.has_quiz_data && n > 0 ? (perf[n - 1].avg_score * 100).toFixed(0) + "%" : "—"}`}
          />
        </div>
      </div>

      {noData ? (
        <div style={{
          height: H,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--text-muted)",
          fontSize: "0.875rem",
          border: "2px dashed var(--border)",
          borderRadius: "8px",
        }}>
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
            <filter id="line-glow" x="-20%" y="-80%" width="140%" height="260%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="3.5" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <linearGradient id={`gap-grad-${skill.skill_id}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"   stopColor={pal.fill} stopOpacity="0.28" />
              <stop offset="100%" stopColor={pal.fill} stopOpacity="0.04" />
            </linearGradient>
          </defs>

          {/* Y-axis gridlines + labels */}
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
                <text x={PAD.left - 6} y={y} textAnchor="end" dominantBaseline="middle" fontSize={10} fill="var(--text-muted)">
                  {(v * 100).toFixed(0)}%
                </text>
              </g>
            );
          })}

          {/* Gap fill polygon */}
          {n > 0 && (
            <polygon points={gapPolygon} fill={`url(#gap-grad-${skill.skill_id})`} />
          )}

          {/* Baseline dashed line */}
          <line
            x1={PAD.left} y1={yBase} x2={W - PAD.right} y2={yBase}
            stroke={pal.fill} strokeWidth={1.5} strokeDasharray="6 4" strokeOpacity={0.7}
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
              {perf.map((p, i) => (
                <g key={i}>
                  <circle cx={pctX(i, n)} cy={pctY(p.avg_score)} r={4} fill={pal.fill} fillOpacity={0.9} filter="url(#line-glow)" />
                  <circle cx={pctX(i, n)} cy={pctY(p.avg_score)} r={2} fill="var(--surface)" />
                </g>
              ))}
            </>
          )}

          {/* X-axis labels */}
          {xLabels.map((p, i) => {
            const origIdx = perf.indexOf(p);
            return (
              <text key={i} x={pctX(origIdx, n)} y={H - 8} textAnchor="middle" fontSize={9.5} fill="var(--text-muted)">
                {p.period_label.length > 12 ? p.period_label.slice(0, 11) + "…" : p.period_label}
              </text>
            );
          })}

          {/* Y-axis label */}
          <text
            x={12} y={PAD.top + INNER_H / 2}
            textAnchor="middle" dominantBaseline="middle"
            fontSize={9.5} fill="var(--text-muted)"
            transform={`rotate(-90, 12, ${PAD.top + INNER_H / 2})`}
          >
            Score
          </text>

          {/* Attempt-volume mini-bars along x-axis */}
          {perf.map((p, i) => {
            const maxAttempts = Math.max(...perf.map((d) => d.attempt_count), 1);
            const barH = Math.round((p.attempt_count / maxAttempts) * 10);
            const x = pctX(i, n);
            const y = PAD.top + INNER_H + 4;
            return (
              <rect key={`bar-${i}`} x={x - 2} y={y + (10 - barH)} width={4} height={barH} fill={pal.fill} fillOpacity={0.4} rx={1} />
            );
          })}
        </svg>
      )}

      {/* Attempt note */}
      {!noData && (
        <p style={{ margin: "0.25rem 0 0", fontSize: "0.75rem", color: "var(--text-muted)" }}>
          Mini-bars below x-axis show relative attempt volume per period.{" "}
          {skill.quiz_performance.reduce((sum, p) => sum + p.attempt_count, 0)} total attempt
          {skill.quiz_performance.reduce((sum, p) => sum + p.attempt_count, 0) !== 1 ? "s" : ""} across{" "}
          {n} period{n !== 1 ? "s" : ""}.
        </p>
      )}
    </div>
  );
}

function LegendItem({ color, dashed, label }: { color: string; dashed: boolean; label: string }) {
  return (
    <span style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.75rem", color: "var(--text-muted)" }}>
      <svg width={22} height={8}>
        <line x1={0} y1={4} x2={22} y2={4} stroke={color} strokeWidth={dashed ? 1.5 : 2} strokeDasharray={dashed ? "5 3" : undefined} />
        {!dashed && <circle cx={11} cy={4} r={3} fill={color} />}
      </svg>
      {label}
    </span>
  );
}

// ── No quiz state ──────────────────────────────────────────────────────────────

function NoQuizState() {
  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      gap: "0.75rem",
      padding: "3rem 1.5rem",
      border: "2px dashed var(--border)",
      borderRadius: "12px",
      textAlign: "center",
      color: "var(--text-muted)",
    }}>
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
    return <div style={{ textAlign: "center", padding: "2rem" }}><span className="spinner" /></div>;
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

  // Auto-select first skill with quiz data, else first skill
  const effectiveId =
    selectedId ??
    (skills.find((s) => s.has_quiz_data)?.skill_id ?? skills[0]?.skill_id ?? null);

  const selectedSkill = skills.find((s) => s.skill_id === effectiveId) ?? null;

  // Sort: with-data first, then by gap descending
  const sorted = [...skills].sort((a, b) => {
    if (a.has_quiz_data !== b.has_quiz_data) return a.has_quiz_data ? -1 : 1;
    return b.current_gap - a.current_gap;
  });

  const withDataCount = skills.filter((s) => s.has_quiz_data).length;
  const avgGap =
    withDataCount > 0
      ? skills.filter((s) => s.has_quiz_data).reduce((sum, s) => sum + s.current_gap, 0) / withDataCount
      : null;

  const improvingCount = skills.filter(
    (s) => s.gap_direction === "closing" && s.has_quiz_data,
  ).length;

  return (
    <div style={{ marginTop: "2rem" }}>
      {/* ── Section header ──────────────────────────────────────────────── */}
      <div style={{
        display: "flex",
        alignItems: "flex-end",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: "0.5rem",
        marginBottom: "1rem",
      }}>
        <div>
          <h3 style={{ margin: 0, marginBottom: "0.2rem" }}>Skill calibration</h3>
          <p style={{ margin: 0, fontSize: "0.8125rem", color: "var(--text-muted)" }}>
            {skills.length} skill{skills.length !== 1 ? "s" : ""}
            {avgGap != null && (
              <> · avg gap{" "}
                <strong style={{
                  color: avgGap < 0 ? "#22c55e" : avgGap > 0.15 ? "#ef4444" : "#f59e0b",
                }}>
                  {avgGap > 0 ? "+" : ""}{(avgGap * 100).toFixed(0)}%
                </strong>
              </>
            )}
            {improvingCount > 0 && (
              <> · <span style={{ color: "#22c55e" }}>↘ {improvingCount} improving</span></>
            )}
          </p>
        </div>

        {/* Gap-level legend */}
        <div style={{ display: "flex", gap: "0.875rem", fontSize: "0.75rem", color: "var(--text-muted)", flexWrap: "wrap" }}>
          {(["exceeding", "on-track", "moderate", "significant"] as GapLevel[]).map((level) => {
            const p = gapPalette(level);
            return (
              <span key={level} style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
                <span style={{
                  width: 8, height: 8, borderRadius: "50%",
                  background: p.fill, display: "inline-block",
                  boxShadow: `0 0 5px ${p.fill}88`,
                }} />
                {p.label}
              </span>
            );
          })}
        </div>
      </div>

      {/* ── Skill chip grid ─────────────────────────────────────────────── */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(168px, 1fr))",
        gap: "0.625rem",
        marginBottom: "1.25rem",
      }}>
        {sorted.map((s) => (
          <SkillChip
            key={s.skill_id}
            skill={s}
            isSelected={s.skill_id === effectiveId}
            onClick={() => setSelectedId(s.skill_id)}
          />
        ))}
      </div>

      {/* ── Full-width detail chart ──────────────────────────────────────── */}
      {selectedSkill ? (
        <DetailChart skill={selectedSkill} />
      ) : (
        <div style={{ color: "var(--text-muted)", padding: "2rem", textAlign: "center", fontSize: "0.875rem" }}>
          Select a skill above to see its chart.
        </div>
      )}
    </div>
  );
}
