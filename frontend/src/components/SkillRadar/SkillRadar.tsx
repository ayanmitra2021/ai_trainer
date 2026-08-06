/**
 * SkillRadar — SVG spider/radar chart of mastery_score per skill.
 *
 * Phase 6.8 changes:
 *  - Active profile banner (name + cert code) shown at top.
 *  - Gate: if no active profile exists, ask the user to build one first.
 *  - Learning path moved to a full-width "Your Learning Journey" section
 *    below the radar, rendered as a graphical road (LearningPathRoad).
 *  - Self-assessment toggle and panel removed (done in 6.7).
 */

import { useNavigate } from "react-router-dom";
import {
  useGenerateLearningPath,
  useLearningPaths,
  useProfiles,
  useSkillProfile,
} from "../../hooks";
import { useSession } from "../../context/SessionContext";
import LearningPathRoad from "./LearningPathRoad";

interface Props {
  practitionerId: string;
}

const SIZE = 320;
const CENTER = SIZE / 2;
const RADIUS = 130;
const LEVELS = 4;

const polar = (angle: number, r: number) => ({
  x: CENTER + r * RADIUS * Math.cos(angle - Math.PI / 2),
  y: CENTER + r * RADIUS * Math.sin(angle - Math.PI / 2),
});

function RadarGrid({ n }: { n: number }) {
  const axes = Array.from({ length: n }, (_, i) => (2 * Math.PI * i) / n);
  return (
    <g>
      {Array.from({ length: LEVELS }, (_, i) => {
        const r = ((i + 1) / LEVELS) * RADIUS;
        return (
          <circle key={i} cx={CENTER} cy={CENTER} r={r} fill="none" stroke="var(--border)" strokeWidth={1} />
        );
      })}
      {axes.map((angle, i) => {
        const end = polar(angle, 1);
        return (
          <line key={i} x1={CENTER} y1={CENTER} x2={end.x} y2={end.y} stroke="var(--border)" strokeWidth={1} />
        );
      })}
    </g>
  );
}

function RadarPolygon({ scores, color, fillOpacity }: { scores: number[]; color: string; fillOpacity: number }) {
  const n = scores.length;
  const points = scores.map((s, i) => {
    const angle = (2 * Math.PI * i) / n;
    const p = polar(angle, s);
    return `${p.x},${p.y}`;
  });
  return (
    <polygon points={points.join(" ")} fill={color} fillOpacity={fillOpacity} stroke={color} strokeWidth={2} />
  );
}

function AxisLabels({ labels }: { labels: { name: string; score: number }[] }) {
  const n = labels.length;
  return (
    <g>
      {labels.map(({ name, score }, i) => {
        const angle = (2 * Math.PI * i) / n;
        const p = polar(angle, 1.18);
        const textAnchor = Math.abs(p.x - CENTER) < 5 ? "middle" : p.x < CENTER ? "end" : "start";
        return (
          <text key={i} x={p.x} y={p.y} textAnchor={textAnchor} dominantBaseline="middle" fontSize={11} fill="var(--text)">
            {name.length > 14 ? name.slice(0, 13) + "…" : name}
            <tspan x={p.x} dy="1.2em" fill="var(--text-muted)" fontSize={10}>
              {(score * 100).toFixed(0)}%
            </tspan>
          </text>
        );
      })}
    </g>
  );
}

function guidanceMessage(pct: number): string {
  if (pct < 0.4) return "Keep building — take more quizzes and update your skill self-assessment to give the radar a fuller picture.";
  if (pct < 0.7) return "Good progress. Focus on the weakest skills shown above and keep answering quizzes in those areas.";
  if (pct < 0.9) return "You're getting close. Review the remaining gaps and aim for a practice run soon.";
  return "Strong profile — you look ready to schedule your certification exam.";
}

export default function SkillRadar({ practitionerId }: Props) {
  const { data: snapshots, isLoading, isError } = useSkillProfile(practitionerId);
  const { data: paths } = useLearningPaths(practitionerId);
  const { data: profilesList, isLoading: profilesLoading } = useProfiles(practitionerId);
  const generatePath = useGenerateLearningPath(practitionerId);
  const { session } = useSession();
  const navigate = useNavigate();

  const activeProfile = profilesList?.find((p) => p.is_active);
  const certCode = activeProfile?.certification_code ?? session?.active_certification_code;

  // ── Loading ───────────────────────────────────────────────────────────────
  if (profilesLoading || isLoading) {
    return (
      <div style={{ textAlign: "center", padding: "3rem" }}>
        <span className="spinner" />
      </div>
    );
  }

  // ── Gate: must have an active profile ─────────────────────────────────────
  if (!activeProfile) {
    return (
      <div
        className="card"
        style={{ textAlign: "center", padding: "3rem 2rem", maxWidth: 520, margin: "0 auto" }}
      >
        <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>🎯</div>
        <h2 style={{ marginBottom: "0.5rem" }}>Set up a profile first</h2>
        <p style={{ color: "var(--text-muted)", marginBottom: "1.75rem", lineHeight: 1.6 }}>
          Your skill radar and learning journey are personalised to your active profile and
          certification goal. Create a profile to unlock the dashboard.
        </p>
        <button className="btn btn-primary" onClick={() => navigate("/profile")}>
          Build your profile →
        </button>
      </div>
    );
  }

  // ── Error ─────────────────────────────────────────────────────────────────
  if (isError) {
    return <div className="card" style={{ color: "var(--danger)" }}>Could not load skill profile.</div>;
  }

  // ── Empty skill profile (profile exists, no snapshots yet) ─────────────────
  if (!snapshots || snapshots.length === 0) {
    return (
      <div>
        <ProfileBanner profile={activeProfile} onEdit={() => navigate("/profile")} />
        <div className="empty-state">
          <p style={{ marginBottom: "0.5rem" }}>
            No skill data yet. Generate your learning path to build the radar.
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

  const labels = snapshots.map((s) => ({ name: s.skill_name, score: s.mastery_score }));
  const masteryScores = snapshots.map((s) => s.mastery_score);
  const confidenceScores = snapshots.map((s) => s.confidence);
  const activePath = paths?.find((p) => p.status === "active");

  // Cert mastery = mean mastery across all snapshot skills (proxy when cert is set)
  const certMastery =
    snapshots.length > 0
      ? snapshots.reduce((sum, s) => sum + s.mastery_score, 0) / snapshots.length
      : null;

  const radarTitle = certCode ? `Skill radar — ${certCode}` : "Skill radar";

  return (
    <div>
      {/* ── Active profile banner ──────────────────────────────────────── */}
      <ProfileBanner profile={activeProfile} onEdit={() => navigate("/profile")} />

      {/* ── Radar + side panel ────────────────────────────────────────── */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: "2rem", flexWrap: "wrap" }}>
        {/* Radar chart */}
        <div>
          <h2 style={{ marginBottom: "0.25rem" }}>{radarTitle}</h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", marginBottom: "1rem" }}>
            {snapshots.length} skill{snapshots.length !== 1 ? "s" : ""} · last updated{" "}
            {new Date(
              Math.max(...snapshots.map((s) => new Date(s.last_computed_at).getTime())),
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
            <RadarPolygon scores={confidenceScores} color="var(--primary)" fillOpacity={0.08} />
            <RadarPolygon scores={masteryScores} color="var(--primary)" fillOpacity={0.25} />
            <AxisLabels labels={labels} />
          </svg>
          {/* Legend */}
          <div style={{ display: "flex", gap: "1.25rem", fontSize: "0.8125rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
            <span style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
              <svg width={12} height={12}><rect width={12} height={12} fill="var(--primary)" opacity={0.55} rx={2} /></svg>
              Mastery
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
              <svg width={12} height={12}><rect width={12} height={12} fill="var(--primary)" opacity={0.12} rx={2} /></svg>
              Confidence
            </span>
          </div>
        </div>

        {/* Side panel: cert progress + top gaps */}
        <div style={{ flex: 1, minWidth: 220 }}>
          {/* Cert mastery card */}
          {certCode && certMastery !== null && (
            <div className="card" style={{ marginBottom: "1.25rem" }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: "0.8125rem",
                  color: "var(--text-muted)",
                  marginBottom: "0.375rem",
                }}
              >
                <span>Readiness toward {certCode}</span>
                <span style={{ fontVariantNumeric: "tabular-nums" }}>
                  {(certMastery * 100).toFixed(0)}%
                </span>
              </div>
              <div className="progress" style={{ marginBottom: "0.75rem" }}>
                <div className="progress-bar" style={{ width: `${certMastery * 100}%` }} />
              </div>
              <p style={{ margin: 0, fontSize: "0.8125rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
                {guidanceMessage(certMastery)}
              </p>
            </div>
          )}

          <h3 style={{ marginBottom: "0.125rem" }}>Top skill gaps</h3>
          <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", margin: "0 0 0.75rem" }}>
            Your 5 weakest skills by mastery score.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {[...snapshots]
              .sort((a, b) => a.mastery_score - b.mastery_score)
              .slice(0, 5)
              .map((s) => (
                <div key={s.skill_id}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", marginBottom: "0.25rem" }}>
                    <span>{s.skill_name}</span>
                    <span style={{ color: "var(--text-muted)", fontVariantNumeric: "tabular-nums" }}>
                      {(s.mastery_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="progress">
                    <div className="progress-bar" style={{ width: `${s.mastery_score * 100}%` }} />
                  </div>
                </div>
              ))}
          </div>
        </div>
      </div>

      {/* ── Learning Journey — full-width section ─────────────────────── */}
      <div style={{ marginTop: "2.5rem" }}>
        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "1rem",
            marginBottom: "1rem",
          }}
        >
          <div>
            <h2 style={{ marginBottom: "0.25rem" }}>Your learning journey</h2>
            <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", margin: 0 }}>
              {activePath
                ? `${activePath.items.length} milestone${activePath.items.length !== 1 ? "s" : ""} · generated ${new Date(activePath.generated_at).toLocaleDateString()}`
                : "Generate a personalised path toward " + (certCode ?? "your certification") + "."}
            </p>
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "0.25rem" }}>
            <button
              className="btn btn-primary"
              disabled={generatePath.isPending}
              onClick={() => generatePath.mutate()}
            >
              {generatePath.isPending ? (
                <><span className="spinner" /> Generating…</>
              ) : activePath ? (
                "Regenerate path"
              ) : (
                "Generate path"
              )}
            </button>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              Refresh after quizzes or profile edits.
            </span>
          </div>
        </div>

        {generatePath.isError && (
          <p style={{ color: "var(--danger)", marginBottom: "0.75rem", fontSize: "0.875rem" }}>
            {(generatePath.error as Error).message}
          </p>
        )}

        {activePath ? (
          <LearningPathRoad path={activePath} />
        ) : (
          <div
            style={{
              border: "2px dashed var(--border)",
              borderRadius: "12px",
              padding: "2.5rem",
              textAlign: "center",
              color: "var(--text-muted)",
              fontSize: "0.875rem",
            }}
          >
            Click "Generate path" to map your journey to {certCode ?? "certification"}.
          </div>
        )}
      </div>
    </div>
  );
}

// ── Profile banner ─────────────────────────────────────────────────────────────

interface ProfileBannerProps {
  profile: { name: string; certification_code?: string; mastery_pct?: number };
  onEdit: () => void;
}

function ProfileBanner({ profile, onEdit }: ProfileBannerProps) {
  const initial = profile.name.trim()[0]?.toUpperCase() ?? "P";
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.875rem",
        padding: "0.75rem 1rem",
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "8px",
        marginBottom: "1.5rem",
      }}
    >
      {/* Avatar initial */}
      <div
        style={{
          width: 38,
          height: 38,
          borderRadius: "50%",
          background: "var(--primary)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#fff",
          fontWeight: 700,
          fontSize: "1rem",
          flexShrink: 0,
        }}
      >
        {initial}
      </div>

      {/* Profile name + cert badge */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, fontSize: "0.9rem", display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
          {profile.name}
          {profile.certification_code && (
            <span
              style={{
                fontSize: "0.7rem",
                padding: "0.15rem 0.5rem",
                borderRadius: "999px",
                background: "var(--primary)",
                color: "#fff",
                fontWeight: 600,
                letterSpacing: "0.03em",
              }}
            >
              {profile.certification_code}
            </span>
          )}
        </div>
        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.1rem" }}>
          Active profile · radar and path are scoped to this context
        </div>
      </div>

      {/* Edit link */}
      <button
        className="btn btn-outline"
        style={{ fontSize: "0.8125rem", flexShrink: 0 }}
        onClick={onEdit}
      >
        Edit profile →
      </button>
    </div>
  );
}
