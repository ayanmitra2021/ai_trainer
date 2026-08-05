/**
 * TrendDashboard — visualises correlation (trained vs adopted) gaps over time.
 *
 * Groups correlation snapshots by skill_id and draws one line per skill
 * on a shared time axis. Skills with has_adoption_gap=true are highlighted.
 */

import { useCorrelationSnapshots, useSkills } from "../../hooks";
import type { CorrelationSnapshot } from "../../api/types";

interface Props {
  practitionerId: string;
}

// Chart dimensions
const W = 560;
const H = 260;
const PAD = { top: 20, right: 20, bottom: 40, left: 46 };
const INNER_W = W - PAD.left - PAD.right;
const INNER_H = H - PAD.top - PAD.bottom;

// Stable colour palette (cycles for >8 skills)
const PALETTE = [
  "#4dabf7", "#69db7c", "#ffa94d", "#ff6b6b",
  "#cc5de8", "#22b8cf", "#a9e34b", "#f06595",
];

function GapLineChart({
  bySkill,
  skillNames,
}: {
  bySkill: Map<string, CorrelationSnapshot[]>;
  skillNames: Map<string, string>;
}) {
  const allDates = [...bySkill.values()]
    .flat()
    .map((s) => new Date(s.computed_at).getTime());

  if (allDates.length === 0) return null;

  const minT = Math.min(...allDates);
  const maxT = Math.max(...allDates);
  const tRange = maxT - minT || 1;

  const scaleX = (t: number) => ((t - minT) / tRange) * INNER_W;
  const scaleY = (v: number) => INNER_H - v * INNER_H;

  // Y axis ticks (0, 0.25, 0.5, 0.75, 1.0)
  const yTicks = [0, 0.25, 0.5, 0.75, 1.0];

  // X axis ticks — up to 4 evenly spaced date labels
  const dateRange = maxT - minT;
  const xTickTs = [minT, minT + dateRange * 0.33, minT + dateRange * 0.67, maxT];

  const skillIds = [...bySkill.keys()];

  return (
    <svg
      width={W}
      height={H}
      viewBox={`0 0 ${W} ${H}`}
      style={{ display: "block", maxWidth: "100%", overflow: "visible" }}
      role="img"
      aria-label="Adoption gap trend chart"
    >
      <g transform={`translate(${PAD.left},${PAD.top})`}>
        {/* Grid lines */}
        {yTicks.map((t) => (
          <g key={t}>
            <line
              x1={0}
              y1={scaleY(t)}
              x2={INNER_W}
              y2={scaleY(t)}
              stroke="var(--border)"
              strokeWidth={1}
              strokeDasharray={t === 0 ? undefined : "3,3"}
            />
            <text
              x={-8}
              y={scaleY(t)}
              dominantBaseline="middle"
              textAnchor="end"
              fontSize={10}
              fill="var(--text-muted)"
            >
              {(t * 100).toFixed(0)}%
            </text>
          </g>
        ))}

        {/* X axis date labels */}
        {xTickTs.map((ts) => (
          <text
            key={ts}
            x={scaleX(ts)}
            y={INNER_H + 22}
            textAnchor="middle"
            fontSize={10}
            fill="var(--text-muted)"
          >
            {new Date(ts).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
          </text>
        ))}

        {/* Axis labels */}
        <text
          x={INNER_W / 2}
          y={INNER_H + 36}
          textAnchor="middle"
          fontSize={11}
          fill="var(--text-muted)"
        >
          Date
        </text>
        <text
          x={-INNER_H / 2}
          y={-36}
          transform="rotate(-90)"
          textAnchor="middle"
          fontSize={11}
          fill="var(--text-muted)"
        >
          Gap score
        </text>

        {/* Lines */}
        {skillIds.map((skillId, idx) => {
          const snaps = bySkill
            .get(skillId)!
            .sort(
              (a, b) =>
                new Date(a.computed_at).getTime() -
                new Date(b.computed_at).getTime(),
            );
          const color = PALETTE[idx % PALETTE.length];
          const points = snaps
            .map(
              (s) =>
                `${scaleX(new Date(s.computed_at).getTime())},${scaleY(s.gap_score)}`,
            )
            .join(" ");

          return (
            <g key={skillId}>
              <polyline
                points={points}
                fill="none"
                stroke={color}
                strokeWidth={2.5}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              {/* Dots */}
              {snaps.map((s, i) => (
                <circle
                  key={i}
                  cx={scaleX(new Date(s.computed_at).getTime())}
                  cy={scaleY(s.gap_score)}
                  r={4}
                  fill={color}
                >
                  <title>
                    {skillNames.get(skillId) ?? skillId}:{" "}
                    {(s.gap_score * 100).toFixed(1)}% gap on{" "}
                    {new Date(s.computed_at).toLocaleDateString()}
                  </title>
                </circle>
              ))}
            </g>
          );
        })}
      </g>
    </svg>
  );
}

export default function TrendDashboard({ practitionerId }: Props) {
  const { data: snapshots, isLoading } = useCorrelationSnapshots(practitionerId);
  const { data: allSkills } = useSkills();

  const skillNames = new Map(allSkills?.map((s) => [s.id, s.name]) ?? []);

  if (isLoading) {
    return (
      <div style={{ textAlign: "center", padding: "3rem" }}>
        <span className="spinner" />
      </div>
    );
  }

  if (!snapshots || snapshots.length === 0) {
    return (
      <div className="empty-state">
        <p>No correlation data yet.</p>
        <p style={{ fontSize: "0.875rem" }}>
          Run the nightly pulse from the Nudges page or via the API to generate
          adoption signals.
        </p>
      </div>
    );
  }

  // Group by skill
  const bySkill = new Map<string, CorrelationSnapshot[]>();
  for (const s of snapshots) {
    if (!bySkill.has(s.skill_id)) bySkill.set(s.skill_id, []);
    bySkill.get(s.skill_id)!.push(s);
  }

  // Skills with a gap (at least one snapshot where has_adoption_gap)
  const gapSkillIds = new Set(
    snapshots.filter((s) => s.has_adoption_gap).map((s) => s.skill_id),
  );

  const skillIds = [...bySkill.keys()];

  return (
    <div>
      <h2>Adoption trends</h2>
      <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
        Gap score = trained score minus adoption score for each skill. Higher = wider gap.
      </p>

      {/* Chart */}
      <div className="card" style={{ overflowX: "auto" }}>
        <GapLineChart bySkill={bySkill} skillNames={skillNames} />
        {/* Legend */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "0.875rem",
            marginTop: "1rem",
            fontSize: "0.8125rem",
          }}
        >
          {skillIds.map((id, idx) => (
            <span key={id} style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
              <svg width={12} height={3}>
                <rect
                  width={12}
                  height={3}
                  fill={PALETTE[idx % PALETTE.length]}
                  rx={1.5}
                />
              </svg>
              {skillNames.get(id) ?? id.slice(0, 8)}
              {gapSkillIds.has(id) && (
                <span className="badge badge-orange" style={{ fontSize: "0.7rem", padding: "0.1em 0.45em" }}>
                  gap
                </span>
              )}
            </span>
          ))}
        </div>
      </div>

      {/* Per-skill detail cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
          gap: "0.75rem",
          marginTop: "1.25rem",
        }}
      >
        {snapshots
          .filter(
            (s, i, arr) =>
              arr.findIndex((x) => x.skill_id === s.skill_id) === i,
          )
          .sort((a, b) => b.gap_score - a.gap_score)
          .map((s) => (
            <div key={s.skill_id} className="card">
              <div style={{ fontWeight: 600, marginBottom: "0.375rem" }}>
                {skillNames.get(s.skill_id) ?? s.skill_id.slice(0, 8)}
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr 1fr",
                  gap: "0.5rem",
                  fontSize: "0.8125rem",
                  textAlign: "center",
                  marginBottom: "0.75rem",
                }}
              >
                {[
                  { label: "Trained", value: s.trained_score },
                  { label: "Adopted", value: s.adoption_score },
                  { label: "Gap", value: s.gap_score },
                ].map(({ label, value }) => (
                  <div key={label}>
                    <div style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>{label}</div>
                    <div style={{ fontWeight: 600 }}>{(value * 100).toFixed(0)}%</div>
                  </div>
                ))}
              </div>
              {s.has_adoption_gap && (
                <span className="badge badge-orange">adoption gap</span>
              )}
              {s.reasoning && (
                <p
                  style={{
                    marginTop: "0.625rem",
                    marginBottom: 0,
                    fontSize: "0.8125rem",
                    color: "var(--text-muted)",
                    lineHeight: 1.5,
                  }}
                >
                  {s.reasoning}
                </p>
              )}
            </div>
          ))}
      </div>
    </div>
  );
}
