/**
 * RollupView — leadership aggregate view.
 *
 * Key privacy rule: when `min_cohort_size_met === false`, metrics and narrative
 * are null server-side and this component must render a clear withheld-state
 * explanation — NOT blank space, NOT a loading indicator.
 */

import { useState } from "react";
import { useRollups } from "../../hooks";
import type { Rollup } from "../../api/types";

function MetricCard({ label, value }: { label: string; value: unknown }) {
  return (
    <div
      style={{
        background: "var(--bg)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius)",
        padding: "0.875rem 1rem",
        minWidth: 110,
      }}
    >
      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "0.25rem" }}>
        {label}
      </div>
      <div style={{ fontWeight: 700, fontSize: "1.125rem" }}>
        {typeof value === "number" ? (value * 100).toFixed(1) + "%" : String(value ?? "—")}
      </div>
    </div>
  );
}

function CohortTooSmall() {
  return (
    <div
      data-testid="cohort-withheld"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "2rem",
        borderRadius: "var(--radius)",
        border: "1.5px dashed var(--border)",
        textAlign: "center",
        color: "var(--text-muted)",
        gap: "0.625rem",
      }}
    >
      <svg
        width={32}
        height={32}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </svg>
      <p style={{ fontWeight: 600, margin: 0, color: "var(--text)" }}>
        Data withheld — cohort below minimum size
      </p>
      <p style={{ margin: 0, fontSize: "0.875rem" }}>
        This rollup's team or practice has fewer practitioners than the minimum
        required for aggregate reporting. Metrics and narrative are not shown to
        protect individual privacy.
      </p>
    </div>
  );
}

function RollupCard({ rollup }: { rollup: Rollup }) {
  const metrics = rollup.metrics as Record<string, unknown> | null;

  return (
    <div className="card">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: "1rem",
          flexWrap: "wrap",
          marginBottom: "1rem",
        }}
      >
        <div>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: "0.375rem" }}>
            <span className="badge badge-blue">{rollup.scope}</span>
            <span style={{ fontWeight: 600 }}>{rollup.scope_ref}</span>
          </div>
          <p style={{ margin: 0, fontSize: "0.8125rem", color: "var(--text-muted)" }}>
            {new Date(rollup.period_start).toLocaleDateString()} –{" "}
            {new Date(rollup.period_end).toLocaleDateString()}
          </p>
        </div>
        {rollup.min_cohort_size_met ? (
          <span className="badge badge-green">cohort met</span>
        ) : (
          <span className="badge badge-gray">cohort too small</span>
        )}
      </div>

      {!rollup.min_cohort_size_met ? (
        <CohortTooSmall />
      ) : (
        <>
          {metrics && Object.keys(metrics).length > 0 && (
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "0.625rem",
                marginBottom: "1rem",
              }}
            >
              {Object.entries(metrics).map(([k, v]) => (
                <MetricCard key={k} label={k.replace(/_/g, " ")} value={v} />
              ))}
            </div>
          )}
          {rollup.narrative && (
            <p
              style={{
                margin: 0,
                fontSize: "0.9rem",
                lineHeight: 1.65,
                borderTop: "1px solid var(--border)",
                paddingTop: "0.875rem",
              }}
            >
              {rollup.narrative}
            </p>
          )}
        </>
      )}
    </div>
  );
}

export default function RollupView() {
  const [scope, setScope] = useState("");
  const [scopeRef, setScopeRef] = useState("");
  const { data: rollups, isLoading, isError } = useRollups({
    scope: scope || undefined,
    scope_ref: scopeRef || undefined,
  });

  return (
    <div>
      {/* Filters */}
      <div
        style={{
          display: "flex",
          gap: "0.75rem",
          flexWrap: "wrap",
          marginBottom: "1.5rem",
          alignItems: "flex-end",
        }}
      >
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label htmlFor="scope-filter">Scope</label>
          <select
            id="scope-filter"
            className="form-control"
            value={scope}
            onChange={(e) => setScope(e.target.value)}
            style={{ width: 140 }}
          >
            <option value="">All</option>
            <option value="team">Team</option>
            <option value="practice">Practice</option>
          </select>
        </div>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label htmlFor="scope-ref-filter">Scope reference</label>
          <input
            id="scope-ref-filter"
            className="form-control"
            value={scopeRef}
            onChange={(e) => setScopeRef(e.target.value)}
            placeholder="e.g. cloud-practice"
            style={{ width: 200 }}
          />
        </div>
      </div>

      {isLoading && (
        <div style={{ textAlign: "center", padding: "3rem" }}>
          <span className="spinner" />
        </div>
      )}

      {isError && (
        <div className="card" style={{ color: "var(--danger)" }}>
          Could not load rollups.
        </div>
      )}

      {rollups && rollups.length === 0 && (
        <div className="empty-state">
          No rollups found. Run the nightly pulse to generate them.
        </div>
      )}

      {rollups && rollups.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {rollups.map((r) => (
            <RollupCard key={r.id} rollup={r} />
          ))}
        </div>
      )}
    </div>
  );
}
