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
  useActiveMockExam,
  useCertifications,
  useGenerateLearningPath,
  useLearningPaths,
  useProfiles,
  useSkillProfile,
  useStartMockExam,
} from "../../hooks";
import { useSession } from "../../context/SessionContext";
import type { SkillSnapshot } from "../../api/types";
import LearningPathRoad from "./LearningPathRoad";
import CertDomainGapChart from "../CertDomainGapChart";

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

// ── Zone thresholds (mastery score 0–1) ────────────────────────────────────────
// Layer 2 — Blue excellence: ≥ 80 % — performing above the optimal target
const ZONE_EXCELLENCE = 0.80;
// Layer 1 — Green target: 55–80 % — the optimal zone every practitioner aims for
const ZONE_TARGET = 0.55;
// Layer 3 — Orange needs work: < 55 % — significant improvement needed

const polar = (angle: number, r: number) => ({
  x: CENTER + r * RADIUS * Math.cos(angle - Math.PI / 2),
  y: CENTER + r * RADIUS * Math.sin(angle - Math.PI / 2),
});

// ── Sub-components ─────────────────────────────────────────────────────────────

function RadarGrid({ n }: { n: number }) {
  const axes = Array.from({ length: n }, (_, i) => (2 * Math.PI * i) / n);
  // Build SVG polygon points string at a given radius fraction (0–1)
  const pts = (r: number) =>
    axes.map((a) => { const p = polar(a, r); return `${p.x},${p.y}`; }).join(" ");

  return (
    <g>
      {/* ── Zone backgrounds (drawn outermost → innermost so each covers the
           previous polygon's center, creating colored annular rings) ────── */}
      {/* Layer 2 — Blue excellence: 80 %–100 % */}
      <polygon points={pts(1.0)} fill="#3b82f6" fillOpacity={0.09} />
      {/* Layer 1 — Green target: 55 %–80 % (covers centre of blue ring) */}
      <polygon points={pts(ZONE_EXCELLENCE)} fill="#22c55e" fillOpacity={0.11} />
      {/* Layer 3 — Orange needs work: 0 %–55 % (covers centre of green ring) */}
      <polygon points={pts(ZONE_TARGET)} fill="#f97316" fillOpacity={0.14} />

      {/* ── Glowing zone boundary strokes ─────────────────────────────────── */}
      {/* Outer boundary (blue zone ceiling) */}
      <polygon points={pts(1.0)} fill="none"
        stroke="#3b82f6" strokeWidth={1.5} strokeOpacity={0.50}
        filter="url(#zone-glow-blue)" />
      {/* 80 % threshold (green/blue boundary) */}
      <polygon points={pts(ZONE_EXCELLENCE)} fill="none"
        stroke="#22c55e" strokeWidth={2} strokeOpacity={0.65}
        filter="url(#zone-glow-green)" />
      {/* 55 % threshold (orange/green boundary) */}
      <polygon points={pts(ZONE_TARGET)} fill="none"
        stroke="#f97316" strokeWidth={2} strokeOpacity={0.65}
        filter="url(#zone-glow-orange)" />

      {/* ── Fine radial grid rings (very faint — orientation only) ────────── */}
      {Array.from({ length: LEVELS }, (_, i) => {
        const r = ((i + 1) / LEVELS) * RADIUS;
        return (
          <circle key={i} cx={CENTER} cy={CENTER} r={r}
            fill="none" stroke="var(--text)" strokeWidth={0.5} strokeOpacity={0.07} />
        );
      })}

      {/* ── Axis spokes ─────────────────────────────────────────────────────── */}
      {axes.map((angle, i) => {
        const end = polar(angle, 1);
        return (
          <line key={i} x1={CENTER} y1={CENTER} x2={end.x} y2={end.y}
            stroke="var(--text)" strokeWidth={0.75} strokeOpacity={0.14} />
        );
      })}

      {/* ── Outermost end caps ───────────────────────────────────────────────── */}
      {axes.map((angle, i) => {
        const end = polar(angle, 1);
        return <circle key={`cap-${i}`} cx={end.x} cy={end.y} r={2.5}
          fill="#3b82f6" fillOpacity={0.45} />;
      })}
    </g>
  );
}

function RadarPolygon({
  scores, fillColor, fillOpacity, strokeColor, strokeWidth, glowId, strokeDasharray,
}: {
  scores: number[];
  fillColor: string;
  fillOpacity: number;
  strokeColor: string;
  strokeWidth: number;
  glowId?: string;
  strokeDasharray?: string;
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
      strokeDasharray={strokeDasharray}
      filter={glowId ? `url(#${glowId})` : undefined}
    />
  );
}

function AxisLabels({
  labels,
}: {
  labels: {
    name: string;
    score: number;
    mastery_delta?: number | null;
    trend?: "improving" | "declining" | "stable" | "new";
  }[];
}) {
  const n = labels.length;
  return (
    <g>
      {labels.map(({ name, score, mastery_delta, trend }, i) => {
        const angle = (2 * Math.PI * i) / n;
        const p = polar(angle, 1.22);
        const textAnchor =
          Math.abs(p.x - CENTER) < 8 ? "middle" : p.x < CENTER ? "end" : "start";
        const displayName = name.length > 16 ? name.slice(0, 15) + "…" : name;

        // Trend chip — only show when meaningfully improving or declining
        const showTrendUp = trend === "improving" && mastery_delta != null && mastery_delta > 0.01;
        const showTrendDown = trend === "declining" && mastery_delta != null && mastery_delta < -0.01;

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
            {showTrendUp && (
              <tspan
                x={p.x}
                dy="1.2em"
                fontSize={9}
                fontWeight={600}
                fill="var(--color-trend-up, #22c55e)"
              >
                ↑ +{(mastery_delta! * 100).toFixed(0)}%
              </tspan>
            )}
            {showTrendDown && (
              <tspan
                x={p.x}
                dy="1.2em"
                fontSize={9}
                fontWeight={600}
                fill="var(--color-trend-down, #f59e0b)"
              >
                ↓ {(mastery_delta! * 100).toFixed(0)}%
              </tspan>
            )}
          </text>
        );
      })}
    </g>
  );
}

// ── Phase 13.4: Domain coloring helpers ────────────────────────────────────────

interface DomainEntry {
  id: string;
  name: string;
  weight_pct: number;
  color: string;
}

function getDomainColor(rankIndex: number, _totalDomains: number): string {
  // Interpolate from dark blue (#1a56db) to light blue (#93c5fd) based on rank
  // rankIndex 0 = highest weight → darkest color
  const colors = ["#1a56db", "#2563eb", "#3b82f6", "#60a5fa", "#93c5fd"];
  const idx = Math.min(rankIndex, colors.length - 1);
  return colors[idx];
}

const SUPP_COLOR = "#9ca3af"; // neutral grey for supplementary skills

function computeDomainColors(snapshots: SkillSnapshot[]): Map<string, string> {
  // Collect distinct domains sorted by weight desc
  const domainMap = new Map<string, number>(); // domain_id → weight_pct
  for (const s of snapshots) {
    if (s.certification_domain_id && s.domain_weight_pct != null) {
      if (!domainMap.has(s.certification_domain_id)) {
        domainMap.set(s.certification_domain_id, s.domain_weight_pct);
      }
    }
  }
  // Sort by weight descending
  const sorted = [...domainMap.entries()].sort((a, b) => b[1] - a[1]);
  const colorMap = new Map<string, string>();
  sorted.forEach(([domainId], idx) => {
    colorMap.set(domainId, getDomainColor(idx, sorted.length));
  });
  return colorMap;
}

function DomainLegend({ entries }: { entries: DomainEntry[] }) {
  if (entries.length === 0) return null;
  return (
    <div style={{ marginTop: "0.75rem", display: "flex", flexDirection: "column", gap: "0.35rem" }}>
      <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "0.1rem" }}>
        Exam domains
      </div>
      {entries.map((e) => (
        <div key={e.id} style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.8125rem" }}>
          <div style={{ width: 10, height: 10, borderRadius: 2, background: e.color, flexShrink: 0 }} />
          <span style={{ color: "var(--text)" }}>{e.name}</span>
          <span style={{ color: "var(--text-muted)", marginLeft: "auto", fontVariantNumeric: "tabular-nums" }}>
            {e.weight_pct.toFixed(0)}%
          </span>
        </div>
      ))}
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.8125rem" }}>
        <div style={{ width: 10, height: 10, borderRadius: 2, background: SUPP_COLOR, flexShrink: 0 }} />
        <span style={{ color: "var(--text-muted)" }}>Supplementary</span>
      </div>
    </div>
  );
}

// ── Phase 14.5: Scoring status badge ──────────────────────────────────────────

function ScoringStatusBadge({ status }: { status: string | undefined }) {
  if (!status || status === "lm_scored") return null;
  if (status === "degraded") {
    return (
      <div
        role="status"
        style={{
          color: "#b45309",
          fontSize: "0.8rem",
          marginTop: "0.5rem",
          display: "flex",
          alignItems: "center",
          gap: "0.25rem",
        }}
      >
        <span>⚠️</span>
        <span>Scores estimated from self-assessment — take quizzes to refine</span>
      </div>
    );
  }
  // 'pending' (rare after Phase 14.3)
  return (
    <div
      role="status"
      style={{ color: "#6b7280", fontSize: "0.8rem", marginTop: "0.5rem" }}
    >
      ⏳ Scoring in progress…
    </div>
  );
}

// ── Guidance copy ──────────────────────────────────────────────────────────────

function guidanceMessage(pct: number): string {
  // Phase 9.4: guidance is based solely on quiz-derived mastery.
  if (pct < 0.4) return "Keep building — take more quizzes and click 'Regenerate path' to see your mastery levels grow.";
  if (pct < 0.7) return "Good progress. Focus on the weakest skills shown above and keep answering quizzes in those areas.";
  if (pct < 0.9) return "You're getting close. Review the remaining gaps and aim for a practice run soon.";
  return "Strong profile — you look ready to schedule your certification exam.";
}

// ── Main ───────────────────────────────────────────────────────────────────────

export default function SkillRadar({ practitionerId, readOnly = false }: Props) {
  const { data: snapshots, isLoading, isError } = useSkillProfile(practitionerId);
  const { data: paths } = useLearningPaths(practitionerId);
  const { data: profilesList, isLoading: profilesLoading } = useProfiles(practitionerId);
  const { data: certList } = useCertifications();
  const generatePath = useGenerateLearningPath(practitionerId);
  const startMockExam = useStartMockExam(practitionerId);

  // Compute mastery early (before early-returns) so we can gate the active-session
  // query: only fire it when the CTA will actually appear (mastery ≥ 80 % and not readOnly).
  // This prevents repeated 404 noise for practitioners who haven't reached that threshold.
  const prelimCertMastery =
    snapshots && snapshots.length > 0
      ? snapshots.reduce((sum, s) => sum + s.mastery_score, 0) / snapshots.length
      : null;

  // 404 ⇒ no active session (returns null); only enabled at ≥ 80 % mastery
  const { data: activeMockExam } = useActiveMockExam(
    practitionerId,
    !readOnly && prelimCertMastery !== null && prelimCertMastery >= 0.80,
  );
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
              <p style={{ marginBottom: "0.5rem" }}>Your radar starts at zero. Answer quiz questions and click 'Regenerate path' to see your mastery levels fill in.</p>
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

  const labels = snapshots.map((s) => ({
    name: s.skill_name,
    score: s.mastery_score,
    mastery_delta: s.mastery_delta,
    trend: s.trend,
  }));
  const masteryScores = snapshots.map((s) => s.mastery_score);
  const confidenceScores = snapshots.map((s) => s.confidence);
  const activePath = paths?.find((p) => p.status === "active");

  // Phase 13.4: domain coloring
  const domainColorMap = computeDomainColors(snapshots);
  const hasDomainData = snapshots.some(s => s.certification_domain_id != null);

  // Build domain legend entries
  const domainEntries: DomainEntry[] = (() => {
    const seen = new Map<string, DomainEntry>();
    for (const s of snapshots) {
      if (s.certification_domain_id && s.certification_domain_name && s.domain_weight_pct != null) {
        if (!seen.has(s.certification_domain_id)) {
          seen.set(s.certification_domain_id, {
            id: s.certification_domain_id,
            name: s.certification_domain_name,
            weight_pct: s.domain_weight_pct,
            color: domainColorMap.get(s.certification_domain_id) ?? SUPP_COLOR,
          });
        }
      }
    }
    return [...seen.values()].sort((a, b) => b.weight_pct - a.weight_pct);
  })();

  // Re-use the value already computed above the early-returns
  const certMastery = prelimCertMastery;

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
              {/* Mastery polygon glow */}
              <filter id="radar-glow" x="-30%" y="-30%" width="160%" height="160%">
                <feGaussianBlur in="SourceGraphic" stdDeviation="5" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              {/* Confidence layer glow */}
              <filter id="conf-glow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              {/* Zone boundary glow filters — sdDev=4 gives ~12 px halo per zone ring */}
              <filter id="zone-glow-blue" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              <filter id="zone-glow-green" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              <filter id="zone-glow-orange" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            <RadarGrid n={snapshots.length} />

            {/* Confidence polygon — dashed dim line; shows algorithm certainty */}
            <RadarPolygon
              scores={confidenceScores}
              fillColor="rgba(255,255,255,0.03)"
              fillOpacity={1}
              strokeColor="rgba(255,255,255,0.35)"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              glowId="conf-glow"
            />

            {/* Mastery polygon — solid bright white stroke; marks actual skill level */}
            <RadarPolygon
              scores={masteryScores}
              fillColor="rgba(255,255,255,0.08)"
              fillOpacity={1}
              strokeColor="rgba(255,255,255,0.90)"
              strokeWidth={2.5}
              glowId="radar-glow"
            />

            <AxisLabels labels={labels} />

            {/* Phase 13.4: domain-colored vertex dots */}
            {hasDomainData && snapshots.map((s, i) => {
              const angle = (2 * Math.PI * i) / snapshots.length;
              const p = polar(angle, 1);
              const dotColor = s.certification_domain_id
                ? (domainColorMap.get(s.certification_domain_id) ?? SUPP_COLOR)
                : SUPP_COLOR;
              return (
                <circle key={`domain-dot-${i}`} cx={p.x} cy={p.y} r={5} fill={dotColor} fillOpacity={0.9}>
                  <title>{s.skill_name} — {s.certification_domain_name ?? "Supplementary"}{s.domain_weight_pct != null ? ` (${s.domain_weight_pct.toFixed(0)}%)` : ""}</title>
                </circle>
              );
            })}

            {/* Center dot */}
            <circle cx={CENTER} cy={CENTER} r={4} fill="rgba(255,255,255,0.55)" />
          </svg>

          {/* Legend — zones + polygon lines */}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginTop: "0.75rem" }}>
            {/* Zone colour bands */}
            <div style={{ display: "flex", gap: "1rem", fontSize: "0.8125rem", color: "var(--text-muted)", flexWrap: "wrap" }}>
              {[
                { color: "#3b82f6", label: "Excellence", sub: "≥ 80%" },
                { color: "#22c55e", label: "Target",     sub: "55–80%" },
                { color: "#f97316", label: "Needs work", sub: "< 55%" },
              ].map(({ color, label, sub }) => (
                <span key={label} style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
                  <span style={{
                    display: "inline-block", width: 10, height: 10, borderRadius: 2,
                    background: color, boxShadow: `0 0 5px ${color}`, flexShrink: 0,
                  }} />
                  <span>{label}</span>
                  <span style={{ opacity: 0.6 }}>({sub})</span>
                </span>
              ))}
            </div>
            {/* Polygon line types */}
            <div style={{ display: "flex", gap: "1.25rem", fontSize: "0.8125rem", color: "var(--text-muted)", flexWrap: "wrap" }}>
              <span style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                {/* Solid line swatch */}
                <svg width={24} height={10}>
                  <line x1={0} y1={5} x2={24} y2={5}
                    stroke="rgba(255,255,255,0.85)" strokeWidth={2.5} />
                </svg>
                Your mastery level
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                {/* Dashed line swatch */}
                <svg width={24} height={10}>
                  <line x1={0} y1={5} x2={24} y2={5}
                    stroke="rgba(255,255,255,0.45)" strokeWidth={1.5} strokeDasharray="4 3" />
                </svg>
                Score confidence
              </span>
            </div>
          </div>

          {/* Phase 13.4: domain legend */}
          {hasDomainData && <DomainLegend entries={domainEntries} />}

          {/* Phase 14.5: scoring quality badge */}
          <ScoringStatusBadge status={activeProfile?.domain_scoring_status} />
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

          {/* Cert domain gap chart — shown when there's an active cert with a known ID */}
          {activeProfile?.certification_id ? (
            <>
              <CertDomainGapChart
                practitionerId={practitionerId}
                certificationId={activeProfile.certification_id}
                certCode={certCode ?? activeProfile.certification_code ?? ""}
              />
              {/* Phase 14.5: scoring quality badge below the gap chart */}
              <ScoringStatusBadge status={activeProfile?.domain_scoring_status} />
            </>
          ) : (
            <>
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
                      pct < 30 ? "var(--danger)" : pct < 60 ? "var(--warning)" : "var(--success)";
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
                              background: barColor,
                              borderRadius: 3,
                              transition: "width 0.5s ease",
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
              </div>
            </>
          )}
        </div>
      </div>

      {/* ── Mock Exam CTA ─────────────────────────────────────────────── */}
      {!readOnly && certMastery !== null && certMastery >= 0.80 && certCode && (() => {
        const matchingCert = certList?.find((c) => c.code === certCode);
        const hasActiveSession =
          activeMockExam?.status === "in_progress" ||
          activeMockExam?.status === "paused";

        const openMockExam = (sessionId: string) => {
          const base = import.meta.env.BASE_URL ?? "/";
          const url = base.endsWith("/")
            ? `${base}mock-exam/${sessionId}`
            : `${base}/mock-exam/${sessionId}`;
          window.open(url, "_blank");
        };

        const handleStart = async () => {
          const newSession = await startMockExam.mutateAsync();
          openMockExam(newSession.id);
        };

        return (
          <div
            style={{
              marginTop: "2rem",
              padding: "1.5rem",
              background: "color-mix(in srgb, var(--primary) 6%, var(--surface))",
              border: "2px solid var(--primary)",
              borderRadius: "12px",
              boxShadow: "0 0 24px rgba(77, 171, 247, 0.12)",
            }}
          >
            <div style={{ display: "flex", alignItems: "flex-start", gap: "1rem", flexWrap: "wrap" }}>
              <div style={{ flex: 1, minWidth: 200 }}>
                <h3 style={{ margin: "0 0 0.375rem", color: "var(--primary)" }}>
                  🎯 You're exam-ready! Time for a mock exam.
                </h3>
                <p style={{ margin: "0 0 0.75rem", fontSize: "0.875rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
                  Your skill mastery is at{" "}
                  <strong style={{ color: "var(--text)" }}>
                    {(certMastery * 100).toFixed(0)}%
                  </strong>{" "}
                  — above the 80% readiness threshold.
                </p>
                {matchingCert &&
                  (matchingCert.exam_question_count ||
                    matchingCert.exam_duration_minutes ||
                    matchingCert.exam_passing_score_pct) && (
                    <p style={{ margin: "0 0 1rem", fontSize: "0.8125rem", color: "var(--text-muted)", fontVariantNumeric: "tabular-nums" }}>
                      {matchingCert.exam_question_count != null && (
                        <span>{matchingCert.exam_question_count} questions</span>
                      )}
                      {matchingCert.exam_duration_minutes != null && (
                        <span> · {matchingCert.exam_duration_minutes} min</span>
                      )}
                      {matchingCert.exam_passing_score_pct != null && (
                        <span> · Pass: {matchingCert.exam_passing_score_pct}%</span>
                      )}
                    </p>
                  )}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexShrink: 0 }}>
                {hasActiveSession ? (
                  <button
                    className="btn btn-primary btn-3d"
                    onClick={() => openMockExam(activeMockExam!.id)}
                  >
                    Resume Mock Exam →
                  </button>
                ) : (
                  <button
                    className="btn btn-primary btn-3d"
                    disabled={startMockExam.isPending}
                    onClick={handleStart}
                  >
                    {startMockExam.isPending ? (
                      <>
                        <span className="spinner" /> Generating exam…
                      </>
                    ) : (
                      "Start Mock Exam"
                    )}
                  </button>
                )}
              </div>
            </div>
            {startMockExam.isError && (
              <p style={{ margin: "0.5rem 0 0", fontSize: "0.8125rem", color: "var(--danger)" }}>
                {(startMockExam.error as Error).message.includes("409") ||
                (startMockExam.error as Error).message.toLowerCase().includes("active")
                  ? "You have an active exam in progress. Resume it first."
                  : (startMockExam.error as Error).message}
              </p>
            )}
          </div>
        );
      })()}

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
                Updates after you answer quizzes.
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
