/**
 * MockExamHistory — shows on the Adoption Trends tab.
 *
 * Two sections:
 *   1. Exam Confidence Score — circular gauge + trend arrow based on all completed exams
 *   2. Exam History table   — all sessions (completed, abandoned, in_progress, etc.)
 *                             with an Abandon button + reason dialog for live sessions
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAbandonMockExam, useMockExamList } from "../../hooks";
import type { MockExamSessionSummary } from "../../api/types";

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

const STATUS_META: Record<
  string,
  { label: string; color: string; bg: string }
> = {
  in_progress: { label: "In Progress", color: "var(--primary)", bg: "color-mix(in srgb, var(--primary) 12%, var(--surface))" },
  generating:  { label: "Generating", color: "var(--text-muted)", bg: "var(--surface-alt)" },
  paused:      { label: "Paused", color: "var(--warning, #f59e0b)", bg: "color-mix(in srgb, var(--warning, #f59e0b) 12%, var(--surface))" },
  completed:   { label: "Completed", color: "var(--success)", bg: "color-mix(in srgb, var(--success) 12%, var(--surface))" },
  failed:      { label: "Failed", color: "var(--danger)", bg: "color-mix(in srgb, var(--danger) 10%, var(--surface))" },
  abandoned:   { label: "Abandoned", color: "var(--text-muted)", bg: "var(--surface-alt)" },
};

// ── Confidence score computation ──────────────────────────────────────────────

function computeConfidence(
  sessions: MockExamSessionSummary[],
): { weightedAvg: number; trend: "up" | "down" | "stable" | null } {
  const completed = sessions
    .filter((s) => s.status === "completed" && s.score != null)
    .sort((a, b) => a.started_at.localeCompare(b.started_at)); // oldest first

  if (completed.length === 0) return { weightedAvg: 0, trend: null };

  // Exponential recency weights: weight(i) = 2^i, normalised
  const n = completed.length;
  const rawWeights = completed.map((_, i) => Math.pow(2, i));
  const total = rawWeights.reduce((a, b) => a + b, 0);
  const weights = rawWeights.map((w) => w / total);

  const weightedAvg = completed.reduce(
    (acc, s, i) => acc + (s.score ?? 0) * weights[i],
    0,
  );

  let trend: "up" | "down" | "stable" | null = null;
  if (n >= 2) {
    const last = completed[n - 1].score ?? 0;
    const prev = completed[n - 2].score ?? 0;
    const delta = last - prev;
    trend = delta > 0.02 ? "up" : delta < -0.02 ? "down" : "stable";
  }

  return { weightedAvg, trend };
}

// ── Circular confidence gauge ─────────────────────────────────────────────────

function ConfidenceGauge({
  pct,
  passPct,
  trend,
}: {
  pct: number;
  passPct: number;
  trend: "up" | "down" | "stable" | null;
}) {
  const r = 42;
  const circ = 2 * Math.PI * r;
  const filled = (pct / 100) * circ;
  const isReady = pct >= passPct;

  const gaugeColor = pct < 40
    ? "var(--danger)"
    : pct < passPct
    ? "var(--warning, #f59e0b)"
    : "var(--success)";

  const trendIcon =
    trend === "up" ? "↑" : trend === "down" ? "↓" : trend === "stable" ? "→" : "";
  const trendColor =
    trend === "up" ? "var(--success)" : trend === "down" ? "var(--danger)" : "var(--text-muted)";

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "0.5rem",
      }}
    >
      <svg width={110} height={110} viewBox="-5 -5 110 110">
        {/* Track */}
        <circle cx="50" cy="50" r={r} fill="none" stroke="var(--border)" strokeWidth={10} />
        {/* Pass threshold marker */}
        <circle
          cx="50"
          cy="50"
          r={r}
          fill="none"
          stroke="color-mix(in srgb, var(--success) 40%, transparent)"
          strokeWidth={2}
          strokeDasharray={`2 ${circ - 2}`}
          strokeDashoffset={circ / 4 - (passPct / 100) * circ}
          transform="rotate(-90 50 50)"
        />
        {/* Progress arc */}
        <circle
          cx="50"
          cy="50"
          r={r}
          fill="none"
          stroke={gaugeColor}
          strokeWidth={10}
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circ - filled}`}
          strokeDashoffset={circ / 4}
          transform="rotate(-90 50 50)"
          style={{ transition: "stroke-dasharray 0.6s ease" }}
        />
        {/* Center label */}
        <text
          x="50"
          y="46"
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize="18"
          fontWeight="700"
          fill={gaugeColor}
          fontVariantNumeric="tabular-nums"
        >
          {pct}%
        </text>
        {trend && (
          <text
            x="50"
            y="63"
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize="13"
            fontWeight="600"
            fill={trendColor}
          >
            {trendIcon}
          </text>
        )}
      </svg>

      {isReady && (
        <span
          style={{
            fontSize: "0.75rem",
            fontWeight: 700,
            padding: "0.2rem 0.7rem",
            borderRadius: "999px",
            background: "color-mix(in srgb, var(--success) 14%, var(--surface))",
            border: "1.5px solid var(--success)",
            color: "var(--success)",
            letterSpacing: "0.04em",
            textTransform: "uppercase",
          }}
        >
          Exam Ready ✓
        </span>
      )}
    </div>
  );
}

// ── Abandon dialog ────────────────────────────────────────────────────────────

function AbandonDialog({
  session,
  practitionerId,
  onClose,
  onAbandoned,
}: {
  session: MockExamSessionSummary;
  practitionerId: string;
  onClose: () => void;
  onAbandoned: () => void;
}) {
  const [reason, setReason] = useState("");
  const abandonMutation = useAbandonMockExam(practitionerId, session.id);

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.55)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: "1rem",
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "12px",
          padding: "1.75rem",
          maxWidth: 440,
          width: "100%",
          boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
        }}
      >
        <h3 style={{ margin: "0 0 0.5rem", fontSize: "1.0625rem" }}>Abandon this exam?</h3>
        <p style={{ margin: "0 0 1.25rem", fontSize: "0.875rem", color: "var(--text-muted)", lineHeight: 1.6 }}>
          Unanswered questions will be reused in your next exam, and any questions you got wrong will be offered again for remediation.
        </p>
        <label style={{ display: "block", marginBottom: "1rem" }}>
          <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text)", display: "block", marginBottom: "0.375rem" }}>
            Reason for abandoning <span style={{ color: "var(--danger)" }}>*</span>
          </span>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. Running out of time, need more preparation…"
            rows={3}
            style={{
              width: "100%",
              boxSizing: "border-box",
              padding: "0.625rem 0.75rem",
              borderRadius: "6px",
              border: "1.5px solid var(--border)",
              background: "var(--surface-alt)",
              color: "var(--text)",
              fontSize: "0.875rem",
              resize: "vertical",
              fontFamily: "inherit",
            }}
          />
        </label>
        <div style={{ display: "flex", gap: "0.75rem", justifyContent: "flex-end" }}>
          <button className="btn btn-outline" onClick={onClose}>Cancel</button>
          <button
            className="btn btn-primary"
            style={{ background: "var(--danger)", borderColor: "var(--danger)" }}
            disabled={!reason.trim() || abandonMutation.isPending}
            onClick={async () => {
              await abandonMutation.mutateAsync(reason.trim());
              onAbandoned();
            }}
          >
            {abandonMutation.isPending ? <><span className="spinner" /> Abandoning…</> : "Yes, Abandon"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  practitionerId: string;
}

export default function MockExamHistory({ practitionerId }: Props) {
  const navigate = useNavigate();
  const { data: sessions = [], isLoading } = useMockExamList(practitionerId);
  const [abandonTarget, setAbandonTarget] = useState<MockExamSessionSummary | null>(null);

  if (isLoading) {
    return (
      <div style={{ padding: "2rem 1rem" }}>
        <span className="spinner" />
      </div>
    );
  }

  // Completed exams for the confidence score
  const completed = sessions.filter((s) => s.status === "completed" && s.score != null);
  const passPct = completed.length > 0 ? completed[0].exam_passing_score_pct : 70;
  const { weightedAvg, trend } = computeConfidence(sessions);
  const confidencePct = Math.round(weightedAvg * 100);

  return (
    <div style={{ padding: "1.5rem 0" }}>
      {/* ── Section header ─────────────────────────────────────────────────── */}
      <h3
        style={{
          fontSize: "1rem",
          fontWeight: 700,
          margin: "0 0 1.25rem",
          color: "var(--text)",
        }}
      >
        Mock Exam Performance
      </h3>

      {sessions.length === 0 ? (
        <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
          No mock exams taken yet. Generate your first exam from the Skill Radar tab.
        </p>
      ) : (
        <div style={{ display: "flex", gap: "2rem", flexWrap: "wrap", alignItems: "flex-start" }}>

          {/* ── Confidence gauge ───────────────────────────────────────────── */}
          <div
            style={{
              flexShrink: 0,
              padding: "1.25rem 1.5rem",
              borderRadius: "10px",
              border: "1px solid var(--border)",
              background: "var(--surface-alt)",
              textAlign: "center",
              minWidth: 160,
            }}
          >
            <p
              style={{
                margin: "0 0 0.875rem",
                fontSize: "0.75rem",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                color: "var(--text-muted)",
              }}
            >
              Confidence Score
            </p>
            {completed.length === 0 ? (
              <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", margin: 0 }}>
                No completed<br />exams yet
              </p>
            ) : (
              <>
                <ConfidenceGauge
                  pct={confidencePct}
                  passPct={passPct}
                  trend={trend}
                />
                <p
                  style={{
                    margin: "0.75rem 0 0",
                    fontSize: "0.75rem",
                    color: "var(--text-muted)",
                  }}
                >
                  Pass threshold: {passPct}%
                  <br />
                  Based on {completed.length} exam{completed.length > 1 ? "s" : ""}
                </p>
              </>
            )}
          </div>

          {/* ── History table ──────────────────────────────────────────────── */}
          <div style={{ flex: 1, minWidth: 0, overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: "0.8125rem",
              }}
            >
              <thead>
                <tr>
                  {["Date", "Certification", "Status", "Score", "Answered", "Time", "Abandon Reason", ""].map((h) => (
                    <th
                      key={h}
                      style={{
                        padding: "0.5rem 0.75rem",
                        textAlign: "left",
                        fontWeight: 600,
                        fontSize: "0.75rem",
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                        color: "var(--text-muted)",
                        borderBottom: "1px solid var(--border)",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sessions.map((s) => {
                  const meta = STATUS_META[s.status] ?? STATUS_META.failed;
                  const scorePct = s.score != null ? Math.round(s.score * 100) : null;
                  const isLive = ["generating", "in_progress", "paused"].includes(s.status);

                  return (
                    <tr
                      key={s.id}
                      style={{ borderBottom: "1px solid var(--border)" }}
                    >
                      {/* Date */}
                      <td style={{ padding: "0.625rem 0.75rem", whiteSpace: "nowrap", color: "var(--text-muted)" }}>
                        {formatDate(s.started_at)}
                      </td>

                      {/* Certification */}
                      <td style={{ padding: "0.625rem 0.75rem", whiteSpace: "nowrap", color: "var(--text)", fontWeight: 500 }}>
                        {s.certification_code}
                      </td>

                      {/* Status badge */}
                      <td style={{ padding: "0.625rem 0.75rem" }}>
                        <span
                          style={{
                            display: "inline-block",
                            padding: "0.2rem 0.6rem",
                            borderRadius: "999px",
                            fontSize: "0.75rem",
                            fontWeight: 600,
                            background: meta.bg,
                            color: meta.color,
                            whiteSpace: "nowrap",
                          }}
                        >
                          {meta.label}
                        </span>
                      </td>

                      {/* Score */}
                      <td
                        style={{
                          padding: "0.625rem 0.75rem",
                          fontVariantNumeric: "tabular-nums",
                          fontWeight: 600,
                          color: scorePct == null
                            ? "var(--text-muted)"
                            : scorePct >= s.exam_passing_score_pct
                            ? "var(--success)"
                            : "var(--danger)",
                        }}
                      >
                        {scorePct != null ? `${scorePct}%` : "—"}
                      </td>

                      {/* Answered */}
                      <td style={{ padding: "0.625rem 0.75rem", fontVariantNumeric: "tabular-nums", color: "var(--text-muted)" }}>
                        {s.answered_count}/{s.total_count}
                      </td>

                      {/* Time */}
                      <td style={{ padding: "0.625rem 0.75rem", whiteSpace: "nowrap", color: "var(--text-muted)" }}>
                        {s.time_elapsed_seconds > 0 ? formatDuration(s.time_elapsed_seconds) : "—"}
                      </td>

                      {/* Abandon reason */}
                      <td
                        style={{
                          padding: "0.625rem 0.75rem",
                          color: "var(--text-muted)",
                          maxWidth: 220,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                        title={s.abandoned_reason ?? undefined}
                      >
                        {s.abandoned_reason ?? "—"}
                      </td>

                      {/* Actions */}
                      <td style={{ padding: "0.625rem 0.75rem", whiteSpace: "nowrap" }}>
                        {isLive && (
                          <div style={{ display: "flex", gap: "0.5rem" }}>
                            <button
                              className="btn btn-outline"
                              style={{ fontSize: "0.75rem", padding: "0.25rem 0.625rem" }}
                              onClick={() => navigate(`/mock-exam/${s.id}`)}
                            >
                              Resume →
                            </button>
                            <button
                              className="btn btn-outline"
                              style={{
                                fontSize: "0.75rem",
                                padding: "0.25rem 0.625rem",
                                color: "var(--danger)",
                                borderColor: "var(--danger)",
                              }}
                              onClick={() => setAbandonTarget(s)}
                            >
                              Abandon
                            </button>
                          </div>
                        )}
                        {s.status === "completed" && (
                          <button
                            className="btn btn-outline"
                            style={{ fontSize: "0.75rem", padding: "0.25rem 0.625rem" }}
                            onClick={() => navigate(`/mock-exam/${s.id}`)}
                          >
                            Review
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Abandon dialog ─────────────────────────────────────────────────── */}
      {abandonTarget && (
        <AbandonDialog
          session={abandonTarget}
          practitionerId={practitionerId}
          onClose={() => setAbandonTarget(null)}
          onAbandoned={() => setAbandonTarget(null)}
        />
      )}
    </div>
  );
}
