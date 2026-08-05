/**
 * SkillRadar — SVG spider/radar chart of mastery_score per skill.
 *
 * Renders one axis per skill at evenly-spaced angles. Each axis runs
 * from the center (score = 0) to the outer ring (score = 1). The polygon
 * plots mastery scores; confidence is shown as a lighter inner polygon.
 */

import {
  useGenerateLearningPath,
  useLearningPaths,
  useSkillProfile,
} from "../../hooks";

interface Props {
  practitionerId: string;
}

const SIZE = 320;
const CENTER = SIZE / 2;
const RADIUS = 130;
const LEVELS = 4; // concentric rings

/** Convert polar coords (angle in radians, r 0-1) to SVG x,y. */
const polar = (angle: number, r: number) => ({
  x: CENTER + r * RADIUS * Math.cos(angle - Math.PI / 2),
  y: CENTER + r * RADIUS * Math.sin(angle - Math.PI / 2),
});

function RadarGrid({ n }: { n: number }) {
  const axes = Array.from({ length: n }, (_, i) => (2 * Math.PI * i) / n);
  return (
    <g>
      {/* Concentric rings */}
      {Array.from({ length: LEVELS }, (_, i) => {
        const r = ((i + 1) / LEVELS) * RADIUS;
        return (
          <circle
            key={i}
            cx={CENTER}
            cy={CENTER}
            r={r}
            fill="none"
            stroke="var(--border)"
            strokeWidth={1}
          />
        );
      })}
      {/* Axis spokes */}
      {axes.map((angle, i) => {
        const end = polar(angle, 1);
        return (
          <line
            key={i}
            x1={CENTER}
            y1={CENTER}
            x2={end.x}
            y2={end.y}
            stroke="var(--border)"
            strokeWidth={1}
          />
        );
      })}
    </g>
  );
}

function RadarPolygon({
  scores,
  color,
  fillOpacity,
}: {
  scores: number[];
  color: string;
  fillOpacity: number;
}) {
  const n = scores.length;
  const points = scores.map((s, i) => {
    const angle = (2 * Math.PI * i) / n;
    const p = polar(angle, s);
    return `${p.x},${p.y}`;
  });
  return (
    <polygon
      points={points.join(" ")}
      fill={color}
      fillOpacity={fillOpacity}
      stroke={color}
      strokeWidth={2}
    />
  );
}

function AxisLabels({
  labels,
}: {
  labels: { name: string; score: number }[];
}) {
  const n = labels.length;
  return (
    <g>
      {labels.map(({ name, score }, i) => {
        const angle = (2 * Math.PI * i) / n;
        const p = polar(angle, 1.18);
        const textAnchor =
          Math.abs(p.x - CENTER) < 5
            ? "middle"
            : p.x < CENTER
            ? "end"
            : "start";
        return (
          <text
            key={i}
            x={p.x}
            y={p.y}
            textAnchor={textAnchor}
            dominantBaseline="middle"
            fontSize={11}
            fill="var(--text)"
          >
            {name.length > 14 ? name.slice(0, 13) + "…" : name}
            <tspan
              x={p.x}
              dy="1.2em"
              fill="var(--text-muted)"
              fontSize={10}
            >
              {(score * 100).toFixed(0)}%
            </tspan>
          </text>
        );
      })}
    </g>
  );
}

export default function SkillRadar({ practitionerId }: Props) {
  const { data: snapshots, isLoading, isError } = useSkillProfile(practitionerId);
  const { data: paths } = useLearningPaths(practitionerId);
  const generatePath = useGenerateLearningPath(practitionerId);

  if (isLoading) {
    return (
      <div style={{ textAlign: "center", padding: "3rem" }}>
        <span className="spinner" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="card" style={{ color: "var(--danger)" }}>
        Could not load skill profile.
      </div>
    );
  }

  if (!snapshots || snapshots.length === 0) {
    return (
      <div>
        <div className="empty-state">
          <p style={{ marginBottom: "1rem" }}>
            No skill profile yet. Generate a learning path to run the profiler.
          </p>
          <button
            className="btn btn-primary"
            disabled={generatePath.isPending}
            onClick={() => generatePath.mutate()}
          >
            {generatePath.isPending ? (
              <><span className="spinner" /> Generating…</>
            ) : (
              "Generate learning path"
            )}
          </button>
          {generatePath.isError && (
            <p style={{ color: "var(--danger)", marginTop: "0.75rem", fontSize: "0.875rem" }}>
              {(generatePath.error as Error).message}
            </p>
          )}
        </div>
      </div>
    );
  }

  const labels = snapshots.map((s) => ({
    name: s.skill_name,
    score: s.mastery_score,
  }));
  const masteryScores = snapshots.map((s) => s.mastery_score);
  const confidenceScores = snapshots.map((s) => s.confidence);

  const activePath = paths?.find((p) => p.status === "active");

  return (
    <div>
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: "2rem",
          flexWrap: "wrap",
        }}
      >
        {/* Radar chart */}
        <div>
          <h2 style={{ marginBottom: "0.25rem" }}>Skill profile</h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", marginBottom: "1rem" }}>
            {snapshots.length} skill{snapshots.length !== 1 ? "s" : ""} ·
            last updated{" "}
            {new Date(
              Math.max(
                ...snapshots.map((s) => new Date(s.last_computed_at).getTime()),
              ),
            ).toLocaleDateString()}
          </p>
          <svg
            width={SIZE}
            height={SIZE}
            viewBox={`0 0 ${SIZE} ${SIZE}`}
            style={{ display: "block", maxWidth: "100%" }}
            role="img"
            aria-label="Skill radar chart"
          >
            <RadarGrid n={snapshots.length} />
            {/* Confidence (faint inner) */}
            <RadarPolygon
              scores={confidenceScores}
              color="var(--primary)"
              fillOpacity={0.08}
            />
            {/* Mastery (solid) */}
            <RadarPolygon
              scores={masteryScores}
              color="var(--primary)"
              fillOpacity={0.25}
            />
            <AxisLabels labels={labels} />
          </svg>
          {/* Legend */}
          <div
            style={{
              display: "flex",
              gap: "1.25rem",
              fontSize: "0.8125rem",
              color: "var(--text-muted)",
              marginTop: "0.5rem",
            }}
          >
            <span style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
              <svg width={12} height={12}>
                <rect width={12} height={12} fill="var(--primary)" opacity={0.55} rx={2} />
              </svg>
              Mastery
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
              <svg width={12} height={12}>
                <rect width={12} height={12} fill="var(--primary)" opacity={0.12} rx={2} />
              </svg>
              Confidence
            </span>
          </div>
        </div>

        {/* Side panel: top gaps + path actions */}
        <div style={{ flex: 1, minWidth: 220 }}>
          <h3>Top skill gaps</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {[...snapshots]
              .sort((a, b) => a.mastery_score - b.mastery_score)
              .slice(0, 5)
              .map((s) => (
                <div key={s.skill_id}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      fontSize: "0.8125rem",
                      marginBottom: "0.25rem",
                    }}
                  >
                    <span>{s.skill_name}</span>
                    <span style={{ color: "var(--text-muted)" }}>
                      {(s.mastery_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="progress">
                    <div
                      className="progress-bar"
                      style={{ width: `${s.mastery_score * 100}%` }}
                    />
                  </div>
                </div>
              ))}
          </div>

          <div style={{ marginTop: "1.5rem" }}>
            <h3>Learning path</h3>
            {activePath ? (
              <div className="card">
                <p style={{ margin: "0 0 0.5rem", fontSize: "0.875rem" }}>
                  {activePath.items.length} item
                  {activePath.items.length !== 1 ? "s" : ""}
                </p>
                <p style={{ margin: 0, fontSize: "0.8125rem", color: "var(--text-muted)" }}>
                  Generated{" "}
                  {new Date(activePath.generated_at).toLocaleDateString()}
                </p>
              </div>
            ) : (
              <p style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>
                No active path.
              </p>
            )}
            <button
              className="btn btn-primary"
              style={{ marginTop: "0.75rem" }}
              disabled={generatePath.isPending}
              onClick={() => generatePath.mutate()}
            >
              {generatePath.isPending ? (
                <><span className="spinner" /> Generating…</>
              ) : (
                "Regenerate path"
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
