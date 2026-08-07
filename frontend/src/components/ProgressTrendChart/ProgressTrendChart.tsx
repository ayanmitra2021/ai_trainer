/**
 * ProgressTrendChart — mastery score over time for a practitioner.
 * Shows aggregate average by default; supports per-skill + 30/90 day toggle.
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

const W = 560, H = 220;
const PAD = { top: 20, right: 20, bottom: 40, left: 46 };
const IW = W - PAD.left - PAD.right;
const IH = H - PAD.top - PAD.bottom;

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

  // Group by skill_id for multi-line
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
  const skillIds = [...bySkill.keys()];

  const yTicks = [0, 0.25, 0.5, 0.75, 1.0];

  return (
    <div style={{ marginTop: "1.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem", flexWrap: "wrap", gap: "0.5rem" }}>
        <h3 style={{ margin: 0 }}>Mastery progress</h3>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <select
            className="input"
            style={{ fontSize: "0.8125rem", padding: "0.25rem 0.5rem" }}
            value={skillId ?? ""}
            onChange={(e) => setSkillId(e.target.value || undefined)}
          >
            <option value="">All skills (avg)</option>
            {allSkills?.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          {[30, 90].map((d) => (
            <button
              key={d}
              className={`btn btn-outline${days === d ? " btn-primary" : ""}`}
              style={days === d ? { background: "var(--primary)", color: "#fff", fontSize: "0.8125rem" } : { fontSize: "0.8125rem" }}
              onClick={() => setDays(d)}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      <div className="card" style={{ overflowX: "auto" }}>
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ display: "block", maxWidth: "100%" }}>
          <g transform={`translate(${PAD.left},${PAD.top})`}>
            {yTicks.map((t) => (
              <g key={t}>
                <line x1={0} y1={scaleY(t)} x2={IW} y2={scaleY(t)} stroke="var(--border)" strokeWidth={1} strokeDasharray={t === 0 ? undefined : "3,3"} />
                <text x={-8} y={scaleY(t)} dominantBaseline="middle" textAnchor="end" fontSize={10} fill="var(--text-muted)">{(t * 100).toFixed(0)}%</text>
              </g>
            ))}
            {skillIds.map((sid, idx) => {
              const pts = bySkill.get(sid)!.sort((a, b) => a.ts - b.ts);
              const color = PALETTE[idx % PALETTE.length];
              const polyPoints = pts.map((p) => `${scaleX(p.ts)},${scaleY(p.score)}`).join(" ");
              return (
                <g key={sid}>
                  <polyline points={polyPoints} fill="none" stroke={color} strokeWidth={2.5} strokeLinejoin="round" strokeLinecap="round" />
                  {pts.map((p, i) => (
                    <circle key={i} cx={scaleX(p.ts)} cy={scaleY(p.score)} r={4} fill={color}>
                      <title>{skillNames.get(sid) ?? sid}: {(p.score * 100).toFixed(1)}%</title>
                    </circle>
                  ))}
                </g>
              );
            })}
          </g>
        </svg>
        {/* Legend */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", marginTop: "0.75rem", fontSize: "0.8125rem" }}>
          {skillIds.map((sid, idx) => (
            <span key={sid} style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
              <svg width={12} height={3}><rect width={12} height={3} fill={PALETTE[idx % PALETTE.length]} rx={1.5} /></svg>
              {skillNames.get(sid) ?? sid.slice(0, 8)}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
