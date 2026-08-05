import { useState } from "react";
import { useApproveNudge, useNudges } from "../hooks";
import type { Nudge } from "../api/types";

const statusBadge = (status: Nudge["status"]) => {
  if (status === "approved") return <span className="badge badge-green">approved</span>;
  if (status === "sent") return <span className="badge badge-blue">sent</span>;
  return <span className="badge badge-gray">drafted</span>;
};

export default function NudgesPage() {
  const [statusFilter, setStatusFilter] = useState<string>("drafted");
  const { data: nudges, isLoading } = useNudges({ status: statusFilter || undefined });
  const approve = useApproveNudge();

  return (
    <div style={{ maxWidth: 860, margin: "0 auto", padding: "2rem 1rem" }}>
      <h1>Nudge Approval</h1>
      <p style={{ color: "var(--text-muted)", marginBottom: "1.5rem" }}>
        Review AI-composed nudges before they reach practitioners. Nothing
        sends automatically — approval is required here first.
      </p>

      {/* Filter */}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.25rem" }}>
        {["drafted", "approved", "sent", ""].map((s) => (
          <button
            key={s || "all"}
            className={`btn btn-outline${statusFilter === s ? " btn-primary" : ""}`}
            style={statusFilter === s ? { background: "var(--primary)", color: "#fff" } : {}}
            onClick={() => setStatusFilter(s)}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      {isLoading && (
        <div style={{ textAlign: "center", padding: "3rem" }}>
          <span className="spinner" />
        </div>
      )}

      {nudges && nudges.length === 0 && (
        <div className="empty-state">No nudges matching this filter.</div>
      )}

      {nudges && nudges.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {nudges.map((n) => (
            <div key={n.id} className="card">
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  gap: "1rem",
                  flexWrap: "wrap",
                }}
              >
                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      display: "flex",
                      gap: "0.5rem",
                      alignItems: "center",
                      marginBottom: "0.5rem",
                    }}
                  >
                    {statusBadge(n.status)}
                    <span className="badge badge-orange">{n.nudge_type.replace("_", " ")}</span>
                    <span className="badge badge-gray">{n.channel}</span>
                  </div>
                  <p style={{ margin: 0, fontSize: "0.875rem" }}>{n.content}</p>
                  {n.composer_reasoning && (
                    <p
                      style={{
                        marginTop: "0.625rem",
                        marginBottom: 0,
                        fontSize: "0.8125rem",
                        color: "var(--text-muted)",
                        fontStyle: "italic",
                      }}
                    >
                      Reasoning: {n.composer_reasoning}
                    </p>
                  )}
                  <p
                    style={{
                      marginTop: "0.5rem",
                      marginBottom: 0,
                      fontSize: "0.75rem",
                      color: "var(--text-muted)",
                    }}
                  >
                    Created {new Date(n.created_at).toLocaleDateString()}
                    {n.sent_at
                      ? ` · Sent ${new Date(n.sent_at).toLocaleDateString()}`
                      : ""}
                  </p>
                </div>
                {n.status === "drafted" && (
                  <button
                    className="btn btn-primary"
                    style={{ flexShrink: 0 }}
                    disabled={approve.isPending}
                    onClick={() => approve.mutate(n.id)}
                  >
                    {approve.isPending && approve.variables === n.id ? (
                      <span className="spinner" />
                    ) : null}
                    Approve
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
