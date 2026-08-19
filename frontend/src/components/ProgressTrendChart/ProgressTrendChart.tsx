/**
 * ProgressTrendChart — mastery score over time for a practitioner.
 *
 * Redesigned (Phase 19):
 *   • Horizontal-scroll pill buttons replace the dropdown for skill filtering
 *   • Gradient area fills under each series line
 *   • Current mastery score shown as a prominent stat in the header
 *   • Latest data point is highlighted with a larger, glowing dot
 */

import { useState } from "react";
import { useMasteryHistory, useSkills } from "../../hooks";

interface Props {
  practitionerId: string;
}

const PALETTE = [
  "#4dabf7", "#69db7c", "#ffa94d", "#ff6b6b",
  "#cc5de8", "#22b8cf", "#a9e34b", "#f06595",
];

const W = 560, H = 240;
const PAD = { top: 20, right: 20, bottom: 40, left: 46 };
const IW = W - PAD.left - PAD.right;
const IH = H - PAD.top - PAD.bottom;

// ── Pill button ────────────────────────────────────────────────────────────────

function FilterPill({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        flexShrink: 0,
        padding: "0.3rem 0.875rem",
        borderRadius: "999px",
        border: `1px solid ${active ? "var(--primary)" : "var(--border)"}`,
        background: active ? "var(--primary)" : "transparent",
        color: active ? "#fff" : "var(--text-muted)",
        fontSize: "0.8125rem",
        fontWeight: active ? 600 : 400,
        cursor: "pointer",
        whiteSpace: "nowrap",
        transition: "background 0.15s, border-color 0.15s, color 0.15s",
      }}
    >
      {label}
    </button>
  );
}

// ── Main ───────────────────────────────────────────────────────────────────────

export default function ProgressTrendChart({ practitionerId }: Props) {
  const [days, setDays] = useState(30);
  const [skillId, setSkillId] = useState<string | undefined>(undefined);
  const { data: history, isLoading } = useMasteryHistory(practitionerId, { skill_id: skillId, days });
  const { data: allSkills } = useSkills();

  if (isLoading) {
    return <div style={{ textAlign: "center", padding: "2rem" }}><span className="spinner" /></div>;
  }

  const points = history?.points ?? [];

  if (points.length < 2) {
    return (
      <div className="empty-state" style={{ marginTop: "1.5rem" }}>
        Keep going — your progress chart fills in as you complete quizzes and update your profile.
      </div>
    );
  }

  // Group by skill_id; sort each series by time
  const bySkill = new Map<string, { score: number; ts: number }[]>();
  for (const p of points) {
    if (!bySkill.has(p.skill_id)) bySkill.set(p.skill_id, []);
    bySkill.get(p.skill_id)!.push({ score: p.mastery_score, ts: new Date(p.recorded_at).getTime() });
  }

  const allTs = points.map((p) => new Date(p.recorded_at).getTime());
  const minT = Math.min(...allTs);
  const maxT = Math.max(...allTs);
  const tRange = maxT - minT || 1;

  const scaleX = (t: number) => ((t - minT) / tRange) * IW;
  const scaleY = (v: number) => IH - v * IH;

  const skillNames = new Map(allSkills?.map((s) => [s.id, s.name]) ?? []);
  const skillIds   = [...bySkill.keys()];
  const yTicks     = [0, 0.25, 0.5, 0.75, 1.0];

  // Latest mastery score (avg of most-recent point per skill)
  const latestScores: number[] = [];
  for (const [, pts] of bySkill) {
    const sorted = [...pts].sort((a, b) => b.ts - a.ts);
    if (sorted.length > 0) latestScores.push(sorted[0].score);
  }
  const latestAvg = latestScores.length > 0
    ? Math.round((latestScores.reduce((a, b) => a + b, 0) / latestScores.length) * 100)
    : null;

  return (
    <div style={{ marginTop: "1.5rem" }}>
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        marginBottom: "0.875rem",
        flexWrap: "wrap",
        gap: "0.75rem",
      }}>
        <div>
          <h3 style={{ margin: "0 0 0.2rem" }}>Mastery progress</h3>
          {latestAvg != null && (
            <div style={{ display: "flex", alignItems: "baseline", gap: "0.375rem" }}>
              <span style={{
                fontSize: "1.75rem",
                fontWeight: 800,
                color: "var(--primary)",
                lineHeight: 1,
                fontVariantNumeric: "tabular-nums",
              }}>
                {latestAvg}%
              </span>
              <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
                {skillId ? "current" : "avg mastery"}
              </span>
            </div>
          )}
        </div>

        {/* Time-range toggle */}
        <div style={{ display: "flex", gap: "0.375rem", alignSelf: "flex-start" }}>
          {[30, 90].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              style={{
                padding: "0.3rem 0.75rem",
                borderRadius: "6px",
                border: `1px solid ${days === d ? "var(--primary)" : "var(--border)"}`,
                background: days === d ? "var(--primary)" : "transparent",
                color: days === d ? "#fff" : "var(--text-muted)",
                fontSize: "0.8125rem",
                fontWeight: 600,
                cursor: "pointer",
                transition: "background 0.15s, border-color 0.15s, color 0.15s",
              }}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* ── Skill filter pill row ────────────────────────────────────────── */}
      <div style={{
        display: "flex",
        gap: "0.4rem",
        overflowX: "auto",
        paddingBottom: "0.5rem",
        marginBottom: "0.875rem",
        scrollbarWidth: "none",
        /* WebKit scrollbar hidden via inline style — CSS-in-JS can't target pseudo */
      } as React.CSSProperties}>
        <FilterPill label="All skills" active={!skillId} onClick={() => setSkillId(undefined)} />
        {allSkills?.map((s) => (
          <FilterPill
            key={s.id}
            label={s.name}
            active={skillId === s.id}
            onClick={() => setSkillId(s.id)}
          />
        ))}
      </div>

      {/* ── Chart ───────────────────────────────────────────────────────── */}
      <div
        className="card"
        style={{ overflowX: "auto", padding: "0.875rem 0.875rem 0.75rem" }}
      >
        <svg
          width={W}
          height={H}
          viewBox={`0 0 ${W} ${H}`}
          style={{ display: "block", width: "100%", maxWidth: "100%" }}
        >
          <defs>
            {skillIds.map((sid, idx) => {
              const color = PALETTE[idx % PALETTE.length];
              return (
                <linearGradient key={sid} id={`ag-${idx}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%"   stopColor={color} stopOpacity="0.22" />
                  <stop offset="100%" stopColor={color} stopOpacity="0.01" />
                </linearGradient>
              );
            })}
            <filter id="pt-glow" x="-60%" y="-120%" width="220%" height="340%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          <g transform={`translate(${PAD.left},${PAD.top})`}>
            {/* Gridlines + y-axis labels */}
            {yTicks.map((t) => (
              <g key={t}>
                <line
                  x1={0} y1={scaleY(t)} x2={IW} y2={scaleY(t)}
                  stroke="var(--border)"
                  strokeWidth={1}
                  strokeDasharray={t === 0 ? undefined : "3,3"}
                />
                <text
                  x={-8} y={scaleY(t)}
                  dominantBaseline="middle"
                  textAnchor="end"
                  fontSize={10}
                  fill="var(--text-muted)"
                >
                  {(t * 100).toFixed(0)}%
                </text>
              </g>
            ))}

            {/* Area fills (behind lines) */}
            {skillIds.map((sid, idx) => {
              const pts = [...(bySkill.get(sid) ?? [])].sort((a, b) => a.ts - b.ts);
              if (pts.length < 2) return null;
              const first = pts[0];
              const last  = pts[pts.length - 1];
              const topPts = pts.map((p) => `${scaleX(p.ts)},${scaleY(p.score)}`).join(" ");
              const areaPoints = `${topPts} ${scaleX(last.ts)},${IH} ${scaleX(first.ts)},${IH}`;
              return (
                <polygon key={`area-${sid}`} points={areaPoints} fill={`url(#ag-${idx})`} />
              );
            })}

            {/* Lines + dots */}
            {skillIds.map((sid, idx) => {
              const pts   = [...(bySkill.get(sid) ?? [])].sort((a, b) => a.ts - b.ts);
              const color = PALETTE[idx % PALETTE.length];
              const polyPoints = pts.map((p) => `${scaleX(p.ts)},${scaleY(p.score)}`).join(" ");

              return (
                <g key={sid}>
                  <polyline
                    points={polyPoints}
                    fill="none"
                    stroke={color}
                    strokeWidth={2.5}
                    strokeLinejoin="round"
                    strokeLinecap="round"
                  />
                  {pts.map((p, i) => {
                    const isLast = i === pts.length - 1;
                    return (
                      <circle
                        key={i}
                        cx={scaleX(p.ts)}
                        cy={scaleY(p.score)}
                        r={isLast ? 5.5 : 3}
                        fill={color}
                        fillOpacity={isLast ? 1 : 0.75}
                        filter={isLast ? "url(#pt-glow)" : undefined}
                      >
                        <title>
                          {skillNames.get(sid) ?? sid}: {(p.score * 100).toFixed(1)}%
                        </title>
                      </circle>
                    );
                  })}
                </g>
              );
            })}
          </g>
        </svg>

        {/* Series legend */}
        {skillIds.length > 1 && (
          <div style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "0.75rem",
            marginTop: "0.625rem",
            paddingTop: "0.5rem",
            borderTop: "1px solid var(--border)",
            fontSize: "0.8125rem",
          }}>
            {skillIds.map((sid, idx) => (
              <span
                key={sid}
                style={{ display: "flex", alignItems: "center", gap: "0.375rem", color: "var(--text-muted)" }}
              >
                <svg width={14} height={4}>
                  <rect width={14} height={4} fill={PALETTE[idx % PALETTE.length]} rx={2} />
                </svg>
                {skillNames.get(sid) ?? sid.slice(0, 8)}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
