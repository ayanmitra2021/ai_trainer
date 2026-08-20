/**
 * AdminPractitionerPage — Phase 21.
 *
 * Read-only view of a single practitioner for Admin / Leadership users.
 *
 * Tabs:
 *   1. Skill Radar  — read-only radar, cert domain bar, no edit controls
 *   2. Activity     — 4 summary cards + per-skill table + mock exam history
 *
 * Header also shows a Deactivate / Reactivate button (admin-only).
 *
 * Route: /admin/practitioners/:id  (RequireAdmin-guarded in App.tsx)
 */

import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  useActivitySummary,
  useCertifications,
  useDeactivatePractitioner,
  usePractitioner,
  useProfiles,
  useReactivatePractitioner,
} from "../hooks";
import { useSession } from "../context/SessionContext";
import SkillRadar from "../components/SkillRadar";

// ── helpers ───────────────────────────────────────────────────────────────────

function fmtSeconds(s: number): string {
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function StatusBadge({ status }: { status: string }) {
  const colour: Record<string, string> = {
    completed: "var(--success, #16a34a)",
    abandoned: "var(--danger, #dc2626)",
    in_progress: "var(--primary)",
    paused: "var(--text-muted)",
    generating: "var(--accent)",
    failed: "var(--danger, #dc2626)",
  };
  return (
    <span
      style={{
        fontSize: "0.7rem",
        padding: "0.15rem 0.55rem",
        borderRadius: "999px",
        border: `1px solid ${colour[status] ?? "var(--border)"}`,
        color: colour[status] ?? "var(--text-muted)",
        fontWeight: 600,
        textTransform: "capitalize",
        whiteSpace: "nowrap",
      }}
    >
      {status.replace("_", " ")}
    </span>
  );
}

// ── Summary card component ────────────────────────────────────────────────────

function SummaryCard({
  label,
  value,
  sub,
  colour = "var(--primary)",
}: {
  label: string;
  value: string | number;
  sub?: string;
  colour?: string;
}) {
  return (
    <div
      style={{
        flex: "1 1 160px",
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderTop: `3px solid ${colour}`,
        borderRadius: "8px",
        padding: "0.875rem 1rem",
      }}
    >
      <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginBottom: "0.3rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
        {label}
      </div>
      <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text)" }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
          {sub}
        </div>
      )}
    </div>
  );
}

// ── Activity tab ──────────────────────────────────────────────────────────────

function ActivityTab({ practitionerId }: { practitionerId: string }) {
  const { data, isLoading, isError } = useActivitySummary(practitionerId);

  if (isLoading) {
    return (
      <div style={{ textAlign: "center", padding: "3rem" }}>
        <span className="spinner" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="card" style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
        Failed to load activity data. Please refresh.
      </div>
    );
  }

  const { summary_stats: s, skill_activity, mock_exams } = data;

  return (
    <div>
      {/* ── 4 Summary cards ─────────────────────────────────────────── */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", marginBottom: "1.5rem" }}>
        <SummaryCard
          label="Quiz Rounds"
          value={s.total_quiz_rounds}
          sub={`${s.total_attempts} total attempts`}
          colour="var(--primary)"
        />
        <SummaryCard
          label="Correct Rate"
          value={`${s.overall_correct_pct}%`}
          sub="across all skills"
          colour={s.overall_correct_pct >= 70 ? "var(--success, #16a34a)" : s.overall_correct_pct >= 50 ? "var(--warning, #d97706)" : "var(--danger, #dc2626)"}
        />
        <SummaryCard
          label="Lesson Time"
          value={fmtSeconds(s.total_lesson_seconds)}
          sub="byte-sized lessons"
          colour="var(--accent)"
        />
        <SummaryCard
          label="Mock Exams"
          value={s.mock_exams_completed}
          sub={s.latest_mock_score_pct != null ? `Latest: ${s.latest_mock_score_pct}%` : "none completed"}
          colour="var(--success, #16a34a)"
        />
      </div>

      {/* ── Per-skill activity table ─────────────────────────────────── */}
      <h3 style={{ fontSize: "0.9375rem", marginBottom: "0.5rem" }}>Skill Activity</h3>
      {skill_activity.length === 0 ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>No quiz activity yet.</p>
      ) : (
        <div style={{ overflowX: "auto", marginBottom: "2rem" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
            <thead>
              <tr style={{ background: "var(--surface)", borderBottom: "2px solid var(--border)" }}>
                {["Skill", "Mastery", "Gap", "Rounds", "✓ Correct", "✗ Wrong", "Correct %", "Lesson Time", "Lessons"].map((h) => (
                  <th
                    key={h}
                    style={{ padding: "0.5rem 0.75rem", textAlign: "left", fontWeight: 600, color: "var(--text-muted)", whiteSpace: "nowrap" }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {skill_activity.map((row, i) => (
                <tr
                  key={row.skill_id}
                  style={{ background: i % 2 === 0 ? "transparent" : "var(--surface)", borderBottom: "1px solid var(--border)" }}
                >
                  <td style={{ padding: "0.5rem 0.75rem", fontWeight: 500 }}>{row.skill_name}</td>
                  <td style={{ padding: "0.5rem 0.75rem" }}>
                    <span style={{ color: row.mastery_score >= 0.7 ? "var(--success, #16a34a)" : row.mastery_score >= 0.5 ? "var(--warning, #d97706)" : "var(--danger, #dc2626)", fontWeight: 600 }}>
                      {Math.round(row.mastery_score * 100)}%
                    </span>
                  </td>
                  <td style={{ padding: "0.5rem 0.75rem" }}>
                    <span style={{ color: row.gap_pct >= 40 ? "var(--danger, #dc2626)" : row.gap_pct >= 20 ? "var(--warning, #d97706)" : "var(--success, #16a34a)", fontWeight: 600 }}>
                      {row.gap_pct}%
                    </span>
                  </td>
                  <td style={{ padding: "0.5rem 0.75rem", textAlign: "center" }}>{row.quiz_rounds}</td>
                  <td style={{ padding: "0.5rem 0.75rem", textAlign: "center", color: "var(--success, #16a34a)", fontWeight: 600 }}>{row.correct_count}</td>
                  <td style={{ padding: "0.5rem 0.75rem", textAlign: "center", color: "var(--danger, #dc2626)", fontWeight: 600 }}>{row.wrong_count}</td>
                  <td style={{ padding: "0.5rem 0.75rem", textAlign: "center" }}>{row.correct_pct}%</td>
                  <td style={{ padding: "0.5rem 0.75rem" }}>{fmtSeconds(row.total_lesson_seconds)}</td>
                  <td style={{ padding: "0.5rem 0.75rem", textAlign: "center" }}>{row.lesson_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Mock exam history table ──────────────────────────────────── */}
      <h3 style={{ fontSize: "0.9375rem", marginBottom: "0.5rem" }}>Mock Exam History</h3>
      {mock_exams.length === 0 ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>No mock exams taken yet.</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
            <thead>
              <tr style={{ background: "var(--surface)", borderBottom: "2px solid var(--border)" }}>
                {["Cert", "Status", "Score", "Answered / Total", "Time Spent", "Started", "Completed"].map((h) => (
                  <th
                    key={h}
                    style={{ padding: "0.5rem 0.75rem", textAlign: "left", fontWeight: 600, color: "var(--text-muted)", whiteSpace: "nowrap" }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {mock_exams.map((m, i) => (
                <tr
                  key={m.session_id}
                  style={{ background: i % 2 === 0 ? "transparent" : "var(--surface)", borderBottom: "1px solid var(--border)" }}
                >
                  <td style={{ padding: "0.5rem 0.75rem", fontWeight: 600 }}>{m.certification_code}</td>
                  <td style={{ padding: "0.5rem 0.75rem" }}><StatusBadge status={m.status} /></td>
                  <td style={{ padding: "0.5rem 0.75rem", fontWeight: 600 }}>
                    {m.score_pct != null ? (
                      <span style={{ color: m.score_pct >= 70 ? "var(--success, #16a34a)" : "var(--danger, #dc2626)" }}>
                        {m.score_pct}%
                      </span>
                    ) : "—"}
                  </td>
                  <td style={{ padding: "0.5rem 0.75rem", textAlign: "center" }}>{m.questions_answered} / {m.total_questions}</td>
                  <td style={{ padding: "0.5rem 0.75rem" }}>{fmtSeconds(m.time_spent_seconds)}</td>
                  <td style={{ padding: "0.5rem 0.75rem", whiteSpace: "nowrap" }}>{fmtDate(m.started_at)}</td>
                  <td style={{ padding: "0.5rem 0.75rem", whiteSpace: "nowrap" }}>{m.completed_at ? fmtDate(m.completed_at) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Deactivate / Reactivate button with inline confirmation ───────────────────

function DeactivateButton({ practitionerId, isActive }: { practitionerId: string; isActive: boolean }) {
  const [confirming, setConfirming] = useState(false);

  const deactivate = useDeactivatePractitioner(practitionerId);
  const reactivate = useReactivatePractitioner(practitionerId);

  const mutation = isActive ? deactivate : reactivate;
  const label = isActive ? "Deactivate Account" : "Reactivate Account";
  const confirmLabel = isActive ? "Yes, deactivate" : "Yes, reactivate";
  const confirmMsg = isActive
    ? "This will block the practitioner from logging in. Their data is preserved and you can reactivate at any time."
    : "This will allow the practitioner to log in again.";

  if (confirming) {
    return (
      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.5rem",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "8px",
          padding: "0.5rem 0.75rem",
          fontSize: "0.8125rem",
        }}
      >
        <span style={{ color: "var(--text-muted)" }}>{confirmMsg}</span>
        <button
          onClick={() => {
            mutation.mutate(undefined);
            setConfirming(false);
          }}
          disabled={mutation.isPending}
          style={{
            padding: "0.3rem 0.75rem",
            borderRadius: "6px",
            background: isActive ? "var(--danger, #dc2626)" : "var(--success, #16a34a)",
            color: "#fff",
            border: "none",
            cursor: "pointer",
            fontWeight: 600,
            fontSize: "0.8125rem",
            whiteSpace: "nowrap",
          }}
        >
          {mutation.isPending ? "…" : confirmLabel}
        </button>
        <button
          onClick={() => setConfirming(false)}
          style={{
            padding: "0.3rem 0.75rem",
            borderRadius: "6px",
            background: "transparent",
            color: "var(--text-muted)",
            border: "1px solid var(--border)",
            cursor: "pointer",
            fontSize: "0.8125rem",
          }}
        >
          Cancel
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={() => setConfirming(true)}
      style={{
        padding: "0.4rem 1rem",
        borderRadius: "6px",
        background: isActive ? "transparent" : "var(--success, #16a34a)",
        color: isActive ? "var(--danger, #dc2626)" : "#fff",
        border: `1px solid ${isActive ? "var(--danger, #dc2626)" : "var(--success, #16a34a)"}`,
        cursor: "pointer",
        fontWeight: 600,
        fontSize: "0.8125rem",
      }}
    >
      {label}
    </button>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

type Tab = "radar" | "activity";

export default function AdminPractitionerPage() {
  const { id = "" } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState<Tab>("radar");

  const { data: person, isLoading: personLoading } = usePractitioner(id);
  const { data: profilesList, isLoading: profilesLoading } = useProfiles(id);
  const { data: certifications } = useCertifications();
  const { session } = useSession();

  const isFullAdmin = session?.admin_role === "admin";

  const activeProfile = profilesList?.find((p) => p.is_active);
  const certFull = certifications?.find((c) => c.id === activeProfile?.certification_id);

  if (personLoading || profilesLoading) {
    return (
      <div style={{ textAlign: "center", padding: "4rem" }}>
        <span className="spinner" />
      </div>
    );
  }

  if (!person) {
    return (
      <div style={{ maxWidth: 600, margin: "3rem auto", padding: "0 1rem" }}>
        <div className="card">
          <p>Practitioner not found.</p>
          <Link to="/">← Back to list</Link>
        </div>
      </div>
    );
  }

  const initial = person.name.trim()[0]?.toUpperCase() ?? "P";

  const tabStyle = (t: Tab): React.CSSProperties => ({
    padding: "0.5rem 1.25rem",
    borderRadius: "6px 6px 0 0",
    border: "1px solid var(--border)",
    borderBottom: activeTab === t ? "1px solid var(--surface)" : "1px solid var(--border)",
    background: activeTab === t ? "var(--surface)" : "transparent",
    color: activeTab === t ? "var(--primary)" : "var(--text-muted)",
    fontWeight: activeTab === t ? 700 : 400,
    cursor: "pointer",
    fontSize: "0.875rem",
    marginBottom: "-1px",
    position: "relative",
    zIndex: activeTab === t ? 1 : 0,
  });

  return (
    <div style={{ maxWidth: 980, margin: "0 auto", padding: "2rem 1rem" }}>
      {/* ── Back link + header ───────────────────────────────────────── */}
      <div style={{ marginBottom: "1.25rem", display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: "0.75rem" }}>
        <div>
          <Link to="/" style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
            ← All practitioners
          </Link>
          <h1 style={{ marginTop: "0.5rem", marginBottom: "0.25rem", display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
            {person.name}
            {!person.is_active && (
              <span
                style={{
                  fontSize: "0.7rem",
                  padding: "0.2rem 0.6rem",
                  borderRadius: "999px",
                  background: "rgba(220,38,38,0.1)",
                  color: "var(--danger, #dc2626)",
                  border: "1px solid rgba(220,38,38,0.3)",
                  fontWeight: 700,
                  letterSpacing: "0.03em",
                }}
              >
                ⛔ Deactivated
              </span>
            )}
          </h1>
          <p style={{ color: "var(--text-muted)", margin: 0, fontSize: "0.875rem" }}>
            {[person.email, person.role, person.practice, person.seniority_level]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </div>

        {/* Deactivate / Reactivate — full admins only */}
        {isFullAdmin && (
          <DeactivateButton practitionerId={id} isActive={person.is_active} />
        )}
      </div>

      {/* ── Read-only profile panel ──────────────────────────────────── */}
      {activeProfile ? (
        <div
          data-testid="readonly-profile-panel"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.875rem",
            padding: "0.875rem 1rem",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderLeft: "3px solid var(--primary)",
            borderRadius: "8px",
            marginBottom: "1.25rem",
            boxShadow: "0 0 20px rgba(77, 171, 247, 0.06)",
          }}
        >
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

          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 600, fontSize: "0.9rem", display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
              <span data-testid="profile-name">{activeProfile.name}</span>
              {activeProfile.certification_code && (
                <span
                  data-testid="cert-code"
                  style={{
                    fontSize: "0.7rem",
                    padding: "0.15rem 0.5rem",
                    borderRadius: "999px",
                    background: "var(--primary)",
                    color: "#fff",
                    fontWeight: 600,
                  }}
                >
                  {activeProfile.certification_code}
                </span>
              )}
            </div>
            {certFull && (
              <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginTop: "0.15rem" }}>
                <span data-testid="cert-full-name">{certFull.name}</span>
              </div>
            )}
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
              Last saved: {new Date(activeProfile.updated_at).toLocaleDateString()}
            </div>
          </div>

          <span
            style={{
              flexShrink: 0,
              fontSize: "0.7rem",
              padding: "0.2rem 0.6rem",
              borderRadius: "999px",
              background: "rgba(77, 171, 247, 0.12)",
              color: "var(--primary)",
              fontWeight: 600,
              border: "1px solid rgba(77, 171, 247, 0.3)",
            }}
          >
            Read-only
          </span>
        </div>
      ) : (
        <div
          data-testid="readonly-profile-panel"
          className="card"
          style={{ marginBottom: "1.25rem", color: "var(--text-muted)", fontSize: "0.875rem" }}
        >
          No active profile for this practitioner.
        </div>
      )}

      {/* ── Tab strip ────────────────────────────────────────────────── */}
      <div style={{ display: "flex", gap: "0.25rem", marginBottom: 0, borderBottom: "1px solid var(--border)" }}>
        <button style={tabStyle("radar")} onClick={() => setActiveTab("radar")}>
          Skill Radar
        </button>
        <button style={tabStyle("activity")} onClick={() => setActiveTab("activity")}>
          Activity
        </button>
      </div>

      {/* ── Tab panel ────────────────────────────────────────────────── */}
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderTop: "none",
          borderRadius: "0 0 8px 8px",
          padding: "1.25rem",
        }}
      >
        {activeTab === "radar" && (
          <div data-testid="skill-radar-section">
            <SkillRadar practitionerId={id} readOnly />
          </div>
        )}
        {activeTab === "activity" && <ActivityTab practitionerId={id} />}
      </div>
    </div>
  );
}
