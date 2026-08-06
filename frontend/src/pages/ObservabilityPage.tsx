/**
 * ObservabilityPage — Step 5.1
 *
 * Admin-only internal dashboard over agent_runs.
 * Shows cost, latency, error rate, per-agent breakdown, and recent errors.
 */

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { observability } from "../api";
import type { AgentStats, RecentError } from "../api/types";

const cardStyle: React.CSSProperties = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: "8px",
  padding: "1.25rem",
};

const statStyle: React.CSSProperties = {
  fontSize: "2rem",
  fontWeight: 700,
  lineHeight: 1.1,
};

function StatTile({
  label,
  value,
  danger,
}: {
  label: string;
  value: string;
  danger?: boolean;
}) {
  return (
    <div style={{ ...cardStyle, flex: 1, minWidth: "140px" }}>
      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "0.375rem" }}>
        {label}
      </div>
      <div style={{ ...statStyle, color: danger ? "#ef4444" : "var(--text)" }}>{value}</div>
    </div>
  );
}

function AgentTable({ agents }: { agents: AgentStats[] }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)", textAlign: "left" }}>
            {["Agent", "Runs", "Errors", "Error rate", "Avg latency (ms)", "Avg tokens in", "Avg tokens out"].map(
              (h) => (
                <th key={h} style={{ padding: "0.5rem 0.75rem", fontWeight: 600, color: "var(--text-muted)" }}>
                  {h}
                </th>
              )
            )}
          </tr>
        </thead>
        <tbody>
          {agents.map((a) => (
            <tr key={a.agent_name} style={{ borderBottom: "1px solid var(--border)" }}>
              <td style={{ padding: "0.5rem 0.75rem", fontWeight: 500 }}>{a.agent_name}</td>
              <td style={{ padding: "0.5rem 0.75rem" }}>{a.run_count}</td>
              <td style={{ padding: "0.5rem 0.75rem", color: a.error_count > 0 ? "#ef4444" : undefined }}>
                {a.error_count}
              </td>
              <td style={{ padding: "0.5rem 0.75rem" }}>{(a.error_rate * 100).toFixed(1)}%</td>
              <td style={{ padding: "0.5rem 0.75rem" }}>
                {a.avg_latency_ms != null ? a.avg_latency_ms.toFixed(0) : "—"}
              </td>
              <td style={{ padding: "0.5rem 0.75rem" }}>
                {a.avg_tokens_input != null ? a.avg_tokens_input.toFixed(0) : "—"}
              </td>
              <td style={{ padding: "0.5rem 0.75rem" }}>
                {a.avg_tokens_output != null ? a.avg_tokens_output.toFixed(0) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ErrorList({ errors }: { errors: RecentError[] }) {
  if (errors.length === 0) {
    return <p style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>No errors in this window.</p>;
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
      {errors.map((e) => (
        <div
          key={e.id}
          style={{
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: "6px",
            padding: "0.75rem 1rem",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.25rem" }}>
            <span style={{ fontWeight: 600, fontSize: "0.85rem" }}>{e.agent_name}</span>
            <span style={{ fontSize: "0.75rem", color: "#6b7280" }}>
              {new Date(e.started_at).toLocaleString()}
            </span>
          </div>
          <div style={{ fontSize: "0.8125rem", color: "#dc2626", fontFamily: "monospace" }}>
            {e.error_message ?? "(no message)"}
          </div>
          {e.workflow_run_id && (
            <div style={{ fontSize: "0.75rem", color: "#9ca3af", marginTop: "0.25rem" }}>
              workflow: {e.workflow_run_id}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default function ObservabilityPage() {
  const [hours, setHours] = useState(24);

  const { data, isLoading, error } = useQuery({
    queryKey: ["observability", hours],
    queryFn: () => observability.agentRuns(hours),
    refetchInterval: 30_000,
  });

  return (
    <div style={{ padding: "1.5rem", maxWidth: "1200px", margin: "0 auto" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.5rem" }}>
        <div>
          <h1 style={{ fontSize: "1.25rem", fontWeight: 700 }}>Observability</h1>
          <p style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>
            Agent cost, latency &amp; error rate — admin only
          </p>
        </div>
        <select
          value={hours}
          onChange={(e) => setHours(Number(e.target.value))}
          style={{
            padding: "0.375rem 0.625rem",
            borderRadius: "6px",
            border: "1px solid var(--border)",
            fontSize: "0.875rem",
            background: "var(--surface)",
            color: "var(--text)",
            cursor: "pointer",
          }}
        >
          {[1, 6, 24, 48, 168].map((h) => (
            <option key={h} value={h}>
              Last {h === 168 ? "7 days" : `${h}h`}
            </option>
          ))}
        </select>
      </div>

      {isLoading && <p style={{ color: "var(--text-muted)" }}>Loading…</p>}
      {error && (
        <p style={{ color: "#ef4444" }}>
          Failed to load observability data. Make sure you are logged in as an admin.
        </p>
      )}

      {data && (
        <>
          {/* Summary tiles */}
          <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "1.5rem" }}>
            <StatTile label="Total runs" value={String(data.total_runs)} />
            <StatTile
              label="Errors"
              value={String(data.error_count)}
              danger={data.error_count > 0}
            />
            <StatTile
              label="Error rate"
              value={`${(data.error_rate * 100).toFixed(1)}%`}
              danger={data.error_rate > 0.05}
            />
            <StatTile
              label="Avg latency"
              value={data.avg_latency_ms != null ? `${data.avg_latency_ms.toFixed(0)} ms` : "—"}
            />
          </div>

          {/* Per-agent table */}
          <div style={{ ...cardStyle, marginBottom: "1.5rem" }}>
            <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>
              By agent
            </h2>
            {data.by_agent.length === 0 ? (
              <p style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>
                No agent runs in this window.
              </p>
            ) : (
              <AgentTable agents={data.by_agent} />
            )}
          </div>

          {/* Recent errors */}
          <div style={cardStyle}>
            <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>
              Recent errors
            </h2>
            <ErrorList errors={data.recent_errors} />
          </div>
        </>
      )}
    </div>
  );
}
