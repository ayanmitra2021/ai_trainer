/**
 * SkillRadar — SVG spider/radar chart with premium glow aesthetics.
 *
 * Readable radar chart with:
 *  - Glowing primary-color mastery polygon (SVG filter)
 *  - Subtly colored grid rings for a "tech" feel
 *  - Cert progress card + top-gaps panel
 *  - Full learning-journey section
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
  /**
   * Step 9.2 — when true, all interactive controls are hidden:
   *   - ProfileBanner (with "Edit profile →") is not rendered.
   *   - "Regenerate path" / "Generate path" button is not rendered.
   *   - Learning Journey section is not rendered.
   * Used by AdminPractitionerPage for the read-only admin view.
   */
  readOnly?: boolean;
}

// ── Radar geometry ─────────────────────────────────────────────────────────────
const SIZE = 420;
const CENTER = SIZE / 2;
const RADIUS = 160;
const LEVELS = 5;

const polar = (angle: number, r: number) => ({
  x: CENTER + r * RADIUS * Math.cos(angle - Math.PI / 2),
  y: CENTER + r * RADIUS * Math.sin(angle - Math.PI / 2),
});

// ── Sub-components ─────────────────────────────────────────────────────────────

function RadarGrid({ n }: { n: number }) {
  const axes = Array.from({ length: n }, (_, i) => (2 * Math.PI * i) / n);
  return (
    <g>
      {/* Concentric rings */}
      {Array.from({ length: LEVELS }, (_, i) => {
        const r = ((i + 1) / LEVELS) * RADIUS;
        const opacity = 0.12 + i * 0.04;
        return (
          <circle
            key={i}
            cx={CENTER} cy={CENTER} r={r}
            fill="none"
            stroke="#4dabf7"
            strokeWidth={i === LEVELS - 1 ? 1.5 : 1}
            strokeOpacity={opacity}
          />
        );
      })}
      {/* Axis spokes */}
      {axes.map((angle, i) => {
        const end = polar(angle, 1);
        return (
          <line
            key={i}
            x1={CENTER} y1={CENTER}
            x2={end.x} y2={end.y}
            stroke="#4dabf7"
            strokeWidth={1}
            strokeOpacity={0.18}
          />
        );
      })}
      {/* Outermost-ring end caps */}
      {axes.map((angle, i) => {
        const end = polar(angle, 1);
        return <circle key={`cap-${i}`} cx={end.x} cy={end.y} r={2.5} fill="#4dabf7" fillOpacity={0.35} />;
      })}
    </g>
  );
}

function RadarPolygon({
  scores, fillColor, fillOpacity, strokeColor, strokeWidth, glowId,
}: {
  scores: number[];
  fillColor: string;
  fillOpacity: number;
  strokeColor: string;
  strokeWidth: number;
  glowId?: string;
}) {
  const n = scores.length;
  const points = scores.map((s, i) => {
    const angle = (2 * Math.PI * i) / n;
    const p = polar(angle, Math.max(s, 0.02)); // keep tiny non-zero so shape is visible
    return `${p.x},${p.y}`;
  });
  return (
    <polygon
      points={points.join(" ")}
      fill={fillColor}
      fillOpacity={fillOpacity}
      stroke={strokeColor}
      strokeWidth={strokeWidth}
      strokeLinejoin="round"
      filter={glowId ? `url(#${glowId})` : undefined}
    />
  );
}

function AxisLabels({ labels }: { labels: { name: string; score: number }[] }) {
  const n = labels.length;
  return (
    <g>
      {labels.map(({ name, score }, i) => {
        const angle = (2 * Math.PI * i) / n;
        const p = polar(angle, 1.22);
        const textAnchor =
          Math.abs(p.x - CENTER) < 8 ? "middle" : p.x < CENTER ? "end" : "start";
        const displayName = name.length > 16 ? name.slice(0, 15) + "…" : name;
        return (
          <text
            key={i}
            x={p.x} y={p.y}
            textAnchor={textAnchor}
            dominantBaseline="middle"
            fontSize={11.5}
            fontWeight={500}
            fill="var(--text)"
          >
            {displayName}
            <tspan x={p.x} dy="1.3em" fill="var(--text-muted)" fontSize={10} fontWeight={400}>
              {(score * 100).toFixed(0)}%
            </tspan>
          </text>
        );
      })}
    </g>
  );
}

// ── Guidance copy ──────────────────────────────────────────────────────────────

function guidanceMessage(pct: number): string {
  if (pct < 0.4) return "Keep building — take more quizzes and update your skill self-assessment to give the radar a fuller picture.";
  if (pct < 0.7) return "Good progress. Focus on the weakest skills shown above and keep answering quizzes in those areas.";
  if (pct < 0.9) return "You're getting close. Review the remaining gaps and aim for a practice run soon.";
  return "Strong profile — you look ready to schedule your certification exam.";
}

// ── Main ───────────────────────────────────────────────────────────────────────

export default function SkillRadar({ practitionerId, readOnly = false }: Props) {
  const { data: snapshots, isLoading, isError } = useSkillProfile(practitionerId);
  const { data: paths } = useLearningPaths(practitionerId);
  const { data: profilesList, isLoading: profilesLoading } = useProfiles(practitionerId);
  const generatePath = useGenerateLearningPath(practitionerId);
  const { session } = useSession();
  const navigate = useNavigate();

  const activeProfile = profilesList?.find((p) => p.is_active);
  const certCode = activeProfile?.certification_code ?? session?.active_certification_code;

  if (profilesLoading || isLoading) {
    return <div style={{ textAlign: "center", padding: "3rem" }}><span className="spinner" /></div>;
  }

  if (!activeProfile) {
    if (readOnly) {
      return (
        <div className="card" style={{ textAlign: "center", padding: "2rem", color: "var(--text-muted)" }}>
          No active profile for this practitioner.
        </div>
      );
    }
    return (
      <div className="card card-3d" style={{ textAlign: "center", padding: "3rem 2rem", maxWidth: 520, margin: "0 auto" }}>
        <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>🎯</div>
        <h2 style={{ marginBottom: "0.5rem" }}>Set up a profile first</h2>
        <p style={{ color: "var(--text-muted)", marginBottom: "1.75rem", lineHeight: 1.6 }}>
          Your skill radar and learning journey are personalised to your active profile and
          certification goal. Create a profile to unlock the dashboard.
        </p>
        <button className="btn btn-primary btn-3d" onClick={() => navigate("/profile")}>
          Build your profile →
        </button>
      </div>
    );
  }

  if (isError) {
    return <div className="card" style={{ color: "var(--danger)" }}>Could not load skill profile.</div>;
  }

  if (!snapshots || snapshots.length === 0) {
    return (
      <div>
        {!readOnly && <ProfileBanner profile={activeProfile} onEdit={() => navigate("/profile")} />}
        <div className="empty-state">
          {readOnly ? (
            <p style={{ marginBottom: "0.5rem" }}>No skill data yet for this practitioner.</p>
          ) : (
            <>
              <p style={{ marginBottom: "0.5rem" }}>No skill data yet. Generate your learning path to build the radar.</p>
              <button className="btn btn-primary btn-3d" disabled={generatePath.isPending} onClick={() => generatePath.mutate()}>
                {generatePath.isPending ? <><span className="spinner" /> Generating…</> : "Generate learning path"}
              </button>
              {generatePath.isError && (
                <p style={{ color: "var(--danger)", marginTop: "0.75rem", fontSize: "0.875rem" }}>
                  {(generatePath.error as Error).message}
                </p>
              )}
            </>
          )}
        </div>
      </div>
    );
  }

  const labels = snapshots.map((s) => ({ name: s.skill_name, score: s.mastery_score }));
  const masteryScores = snapshots.map((s) => s.mastery_score);
  const confidenceScores = snapshots.map((s) => s.confidence);
  const activePath = paths?.find((p) => p.status === "active");

  const certMastery =
    snapshots.length > 0
      ? snapshots.reduce((sum, s) => sum + s.mastery_score, 0) / snapshots.length
      : null;

  const radarTitle = certCode ? `Skill radar — ${certCode}` : "Skill radar";

  return (
    <div>
      {/* ProfileBanner is suppressed in read-only (admin) mode — the admin page
          renders its own read-only profile panel above the radar. */}
      {!readOnly && <ProfileBanner profile={activeProfile} onEdit={() => navigate("/profile")} />}

      {/* ── Radar + side panel ─────────────────────────────────────────── */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: "2rem", flexWrap: "wrap" }}>

        {/* Radar card */}
        <div
          className="card-3d"
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "12px",
            padding: "1.5rem",
            boxShadow: "0 0 40px rgba(77, 171, 247, 0.08)",
          }}
        >
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
            style={{ display: "block", maxWidth: "100%", overflow: "visible" }}
            role="img"
            aria-label="Skill mastery radar chart"
          >
            <defs>
              {/* Glow filter for mastery polygon */}
              <filter id="radar-glow" x="-30%" y="-30%" width="160%" height="160%">
                <feGaussianBlur in="SourceGraphic" stdDeviation="5" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              {/* Subtle glow for confidence layer */}
              <filter id="conf-glow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            <RadarGrid n={snapshots.length} />

            {/* Confidence polygon (dim, no glow) */}
            <RadarPolygon
              scores={confidenceScores}
              fillColor="#4dabf7"
              fillOpacity={0.07}
              strokeColor="#4dabf7"
              strokeWidth={1}
              glowId="conf-glow"
            />

            {/* Mastery polygon (bright, glowing) */}
            <RadarPolygon
              scores={masteryScores}
              fillColor="#4dabf7"
              fillOpacity={0.28}
              strokeColor="#4dabf7"
              strokeWidth={2.5}
              glowId="radar-glow"
            />

            <AxisLabels labels={labels} />

            {/* Center dot */}
            <circle cx={CENTER} cy={CENTER} r={4} fill="#4dabf7" fillOpacity={0.6} />
          </svg>

          {/* Legend */}
          <div style={{ display: "flex", gap: "1.25rem", fontSize: "0.8125rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
            <span style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
              <svg width={14} height={14}>
                <rect width={14} height={14} rx={3} fill="#4dabf7" fillOpacity={0.55} />
              </svg>
              Mastery
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
              <svg width={14} height={14}>
                <rect width={14} height={14} rx={3} fill="#4dabf7" fillOpacity={0.12} />
              </svg>
              Confidence
            </span>
          </div>
        </div>

        {/* Side panel */}
        <div style={{ flex: 1, minWidth: 220 }}>
          {/* Cert mastery */}
          {certCode && certMastery !== null && (
            <div
              className="card-3d"
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: "12px",
                padding: "1.25rem",
                marginBottom: "1.25rem",
                borderTop: "2px solid #4dabf7",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", color: "var(--text-muted)", marginBottom: "0.375rem" }}>
                <span>Readiness toward <strong style={{ color: "var(--primary)" }}>{certCode}</strong></span>
                <span style={{ fontVariantNumeric: "tabular-nums", fontWeight: 600, color: "var(--text)" }}>
                  {(certMastery * 100).toFixed(0)}%
                </span>
              </div>
              {/* Enhanced progress bar */}
              <div className="progress-3d" style={{ marginBottom: "0.75rem" }}>
                <div className="progress-bar-3d" style={{ width: `${certMastery * 100}%` }} />
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
          <div style={{ display: "flex", flexDirection: "column", gap: "0.625rem" }}>
            {[...snapshots]
              .sort((a, b) => a.mastery_score - b.mastery_score)
              .slice(0, 5)
              .map((s) => {
                const pct = s.mastery_score * 100;
                const barColor =
                  pct < 30 ? "#dc2626" : pct < 60 ? "#ea580c" : "#16a34a";
                return (
                  <div key={s.skill_id}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", marginBottom: "0.25rem" }}>
                      <span style={{ color: "var(--text)" }}>{s.skill_name}</span>
                      <span style={{ color: barColor, fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>
                        {pct.toFixed(0)}%
                      </span>
                    </div>
                    <div style={{ height: 6, background: "var(--border)", borderRadius: 3, overflow: "hidden" }}>
                      <div
                        style={{
                          height: "100%",
                          width: `${pct}%`,
                          background: `linear-gradient(90deg, ${barColor}, ${barColor}aa)`,
                          borderRadius: 3,
                          transition: "width 0.5s ease",
                          boxShadow: `0 0 6px ${barColor}66`,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      </div>

      {/* ── Learning Journey — hidden in read-only (admin) view ──────── */}
      {!readOnly && (
        <div style={{ marginTop: "2.5rem" }}>
          <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem", marginBottom: "1rem" }}>
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
                className="btn btn-primary btn-3d"
                disabled={generatePath.isPending}
                onClick={() => generatePath.mutate()}
              >
                {generatePath.isPending ? <><span className="spinner" /> Generating…</> : activePath ? "Regenerate path" : "Generate path"}
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
            <div style={{ border: "2px dashed var(--border)", borderRadius: "12px", padding: "2.5rem", textAlign: "center", color: "var(--text-muted)", fontSize: "0.875rem" }}>
              Click "Generate path" to map your journey to {certCode ?? "certification"}.
            </div>
          )}
        </div>
      )}
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
        borderLeft: "3px solid var(--primary)",
        borderRadius: "8px",
        marginBottom: "1.5rem",
        boxShadow: "0 0 20px rgba(77, 171, 247, 0.06)",
      }}
    >
      <div style={{ width: 38, height: 38, borderRadius: "50%", background: "var(--primary)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontWeight: 700, fontSize: "1rem", flexShrink: 0, boxShadow: "0 0 12px rgba(77, 171, 247, 0.4)" }}>
        {initial}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, fontSize: "0.9rem", display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
          {profile.name}
          {profile.certification_code && (
            <span style={{ fontSize: "0.7rem", padding: "0.15rem 0.5rem", borderRadius: "999px", background: "var(--primary)", color: "#fff", fontWeight: 600, letterSpacing: "0.03em" }}>
              {profile.certification_code}
            </span>
          )}
        </div>
        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.1rem" }}>
          Active profile · radar and path are scoped to this context
        </div>
      </div>
      <button className="btn btn-outline btn-3d" style={{ fontSize: "0.8125rem", flexShrink: 0 }} onClick={onEdit}>
        Edit profile →
      </button>
    </div>
  );
}
