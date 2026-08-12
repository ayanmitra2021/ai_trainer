/**
 * CertDomainManagementPage — admin page for managing certification exam domains.
 *
 * Route: /admin/cert-domains
 * Access: admin and leadership; leadership users see read-only view.
 *
 * Features:
 *  - Current Versions panel per cert
 *  - "Refresh all certs" button (admin only)
 *  - Proposals panel with side-by-side diff, Approve/Reject actions
 *  - Version history collapsible per cert
 *  - New cert proposals (certification_id = null) in own section
 */

import { useState } from "react";
import { useSession } from "../context/SessionContext";
import {
  useApproveCertDomainProposal,
  useCertDomainProposals,
  useCertDomainVersions,
  useRejectCertDomainProposal,
  useTriggerCertDomainDiscoverAll,
} from "../hooks";
import type {
  CertificationDomainProposal,
  CertificationDomainVersion,
  ProposedDomain,
} from "../api/types";

// ── Helpers ───────────────────────────────────────────────────────────────────

function confidenceFromSourceNotes(sourceNotes: string): "high" | "medium" | "low" {
  const lower = sourceNotes.toLowerCase();
  if (lower.includes("high confidence") || lower.includes("confidence: high")) return "high";
  if (lower.includes("medium confidence") || lower.includes("confidence: medium")) return "medium";
  return "low";
}

function extractSourceUrl(sourceNotes: string): string | null {
  const match = sourceNotes.match(/https?:\/\/[^\s)]+/);
  return match ? match[0] : null;
}

function ConfidenceBadge({ notes }: { notes: string }) {
  const level = confidenceFromSourceNotes(notes);
  const map = {
    high: { label: "High confidence", cls: "badge-green" },
    medium: { label: "Medium confidence", cls: "badge-orange" },
    low: { label: "Low confidence", cls: "badge-red" },
  } as const;
  const { label, cls } = map[level];
  return <span className={`badge ${cls}`}>{label}</span>;
}

// ── Domain list display ────────────────────────────────────────────────────────

function DomainList({
  domains,
  title,
  dimmed,
}: {
  domains: ProposedDomain[];
  title: string;
  dimmed?: boolean;
}) {
  return (
    <div style={{ flex: 1, minWidth: 0, opacity: dimmed ? 0.6 : 1 }}>
      <div
        style={{
          fontSize: "0.75rem",
          fontWeight: 600,
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          marginBottom: "0.5rem",
        }}
      >
        {title}
      </div>
      {domains.length === 0 ? (
        <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", fontStyle: "italic" }}>
          No domains
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.375rem" }}>
          {[...domains]
            .sort((a, b) => a.sequence_order - b.sequence_order)
            .map((d) => (
              <div
                key={d.sequence_order}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  gap: "0.5rem",
                  padding: "0.375rem 0.625rem",
                  background: "var(--surface-alt)",
                  borderRadius: "4px",
                  fontSize: "0.8125rem",
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <span style={{ fontWeight: 500 }}>{d.sequence_order}. {d.domain_name}</span>
                  {d.domain_description && (
                    <div
                      style={{
                        fontSize: "0.75rem",
                        color: "var(--text-muted)",
                        marginTop: "0.125rem",
                        lineHeight: 1.4,
                      }}
                    >
                      {d.domain_description.length > 100
                        ? d.domain_description.slice(0, 97) + "…"
                        : d.domain_description}
                    </div>
                  )}
                </div>
                <span
                  style={{
                    fontSize: "0.75rem",
                    padding: "0.1rem 0.4rem",
                    borderRadius: "999px",
                    background: "var(--border)",
                    color: "var(--text-muted)",
                    flexShrink: 0,
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {d.weight_pct}%
                </span>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}

// ── Reject dialog ──────────────────────────────────────────────────────────────

function RejectDialog({
  proposal,
  onClose,
  onConfirm,
  isPending,
}: {
  proposal: CertificationDomainProposal;
  onClose: () => void;
  onConfirm: (notes: string) => void;
  isPending: boolean;
}) {
  const [notes, setNotes] = useState("");
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.5)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{ maxWidth: 480, width: "90%", padding: "1.5rem" }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ marginBottom: "0.5rem" }}>Reject proposal</h3>
        <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
          Rejecting domains for <strong>{proposal.cert_code}</strong> — {proposal.cert_name}.
        </p>
        <label style={{ fontSize: "0.875rem", fontWeight: 500, display: "block", marginBottom: "0.375rem" }}>
          Rejection notes
        </label>
        <textarea
          className="form-control"
          rows={3}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Explain why these domains are being rejected…"
          style={{ resize: "vertical", marginBottom: "1rem" }}
          autoFocus
        />
        <div style={{ display: "flex", gap: "0.75rem", justifyContent: "flex-end" }}>
          <button className="btn btn-outline" onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn btn-danger"
            disabled={!notes.trim() || isPending}
            onClick={() => onConfirm(notes.trim())}
          >
            {isPending ? <><span className="spinner" /> Rejecting…</> : "Reject proposal"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Proposal card ──────────────────────────────────────────────────────────────

function ProposalCard({
  proposal,
  currentDomains,
  isAdmin,
}: {
  proposal: CertificationDomainProposal;
  currentDomains: ProposedDomain[];
  isAdmin: boolean;
}) {
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const approve = useApproveCertDomainProposal();
  const reject = useRejectCertDomainProposal();
  const sourceUrl = extractSourceUrl(proposal.source_notes);

  const handleApprove = () => {
    if (
      window.confirm(
        `Approve new domain structure for ${proposal.cert_code}?\n\nNote: Practitioners with locked profiles won't be affected — their domain version is frozen at lock time.`
      )
    ) {
      approve.mutate(proposal.id);
    }
  };

  const handleReject = (notes: string) => {
    reject.mutate(
      { proposalId: proposal.id, rejectionNotes: notes },
      { onSuccess: () => setShowRejectDialog(false) },
    );
  };

  return (
    <div
      className="card"
      style={{
        marginBottom: "1rem",
        borderLeft: "3px solid var(--primary)",
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "1rem", marginBottom: "0.875rem", flexWrap: "wrap" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap", marginBottom: "0.25rem" }}>
            <strong style={{ fontSize: "1rem" }}>{proposal.cert_code}</strong>
            <span style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>{proposal.cert_name}</span>
            <ConfidenceBadge notes={proposal.source_notes} />
            <span className="badge badge-blue">{proposal.proposed_domains.length} domains</span>
          </div>
          <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
            Proposed {new Date(proposal.created_at).toLocaleDateString()}
          </div>
        </div>
        {isAdmin && proposal.status === "pending_review" && (
          <div style={{ display: "flex", gap: "0.5rem", flexShrink: 0 }}>
            <button
              className="btn btn-outline"
              onClick={() => setShowRejectDialog(true)}
              disabled={reject.isPending || approve.isPending}
            >
              Reject
            </button>
            <button
              className="btn btn-primary"
              onClick={handleApprove}
              disabled={approve.isPending || reject.isPending}
            >
              {approve.isPending ? <><span className="spinner" /> Approving…</> : "Approve"}
            </button>
          </div>
        )}
        {!isAdmin && proposal.status === "pending_review" && (
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button className="btn btn-outline" disabled title="Admins only">Reject</button>
            <button className="btn btn-primary" disabled title="Admins only">Approve</button>
          </div>
        )}
        {proposal.status !== "pending_review" && (
          <span className={`badge ${proposal.status === "approved" ? "badge-green" : "badge-red"}`}>
            {proposal.status === "approved" ? "Approved" : "Rejected"}
          </span>
        )}
      </div>

      {/* Source notes */}
      <div
        style={{
          fontSize: "0.8125rem",
          color: "var(--text-muted)",
          marginBottom: "0.875rem",
          lineHeight: 1.5,
          padding: "0.5rem 0.75rem",
          background: "var(--surface-alt)",
          borderRadius: "var(--radius)",
          display: "flex",
          gap: "0.75rem",
          alignItems: "flex-start",
          flexWrap: "wrap",
        }}
      >
        <span style={{ flex: 1 }}>{proposal.source_notes}</span>
        {sourceUrl && (
          <a
            href={sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{ fontSize: "0.8125rem", whiteSpace: "nowrap", flexShrink: 0 }}
          >
            Verify source ↗
          </a>
        )}
      </div>

      {/* Side-by-side domain diff */}
      <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
        <DomainList
          domains={currentDomains}
          title="Current domains"
          dimmed={currentDomains.length === 0}
        />
        <div style={{ width: 1, background: "var(--border)", flexShrink: 0, alignSelf: "stretch" }} />
        <DomainList domains={proposal.proposed_domains} title="Proposed domains" />
      </div>

      {/* Rejection notes */}
      {proposal.status === "rejected" && proposal.rejection_notes && (
        <div
          style={{
            marginTop: "0.875rem",
            fontSize: "0.8125rem",
            color: "var(--danger)",
            borderTop: "1px solid var(--border)",
            paddingTop: "0.625rem",
          }}
        >
          <strong>Rejection notes:</strong> {proposal.rejection_notes}
        </div>
      )}

      {showRejectDialog && (
        <RejectDialog
          proposal={proposal}
          onClose={() => setShowRejectDialog(false)}
          onConfirm={handleReject}
          isPending={reject.isPending}
        />
      )}
    </div>
  );
}

// ── Version card ───────────────────────────────────────────────────────────────

function VersionCard({ version }: { version: CertificationDomainVersion }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        gap: "0.75rem",
        padding: "0.625rem 0.875rem",
        background: "var(--surface-alt)",
        borderRadius: "var(--radius)",
        marginBottom: "0.5rem",
        flexWrap: "wrap",
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.2rem" }}>
          <span style={{ fontWeight: 600, fontSize: "0.875rem" }}>{version.version_label}</span>
          {version.is_current && (
            <span className="badge badge-green">Current</span>
          )}
        </div>
        <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", lineHeight: 1.4 }}>
          {version.source_notes.length > 120
            ? version.source_notes.slice(0, 117) + "…"
            : version.source_notes}
        </div>
      </div>
      <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", flexShrink: 0, textAlign: "right" }}>
        {new Date(version.created_at).toLocaleDateString()}
      </div>
    </div>
  );
}

// ── Versions panel per cert ────────────────────────────────────────────────────

function CertVersionsPanel({
  certCode,
  versions,
}: {
  certCode: string;
  versions: CertificationDomainVersion[];
}) {
  const [expanded, setExpanded] = useState(false);
  const current = versions.find((v) => v.is_current);
  const sorted = [...versions].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  return (
    <div className="card" style={{ marginBottom: "0.75rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.2rem" }}>
            <strong>{certCode}</strong>
            {current && <span className="badge badge-blue">{current.version_label}</span>}
          </div>
          {current && (
            <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
              {new Date(current.created_at).toLocaleDateString()} · {current.source_notes.length > 80
                ? current.source_notes.slice(0, 77) + "…"
                : current.source_notes}
            </div>
          )}
          {!current && (
            <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>No current version</div>
          )}
        </div>
        <button
          className="btn btn-outline"
          style={{ fontSize: "0.8125rem" }}
          onClick={() => setExpanded((o) => !o)}
        >
          {expanded ? "▾ Hide history" : `▸ History (${versions.length})`}
        </button>
      </div>

      {expanded && (
        <div style={{ marginTop: "1rem", borderTop: "1px solid var(--border)", paddingTop: "0.875rem" }}>
          {sorted.map((v) => (
            <VersionCard key={v.id} version={v} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function CertDomainManagementPage() {
  const { session } = useSession();
  const isAdmin = session?.admin_role === "admin";
  const [proposalFilter, setProposalFilter] = useState<"pending_review" | "approved" | "rejected" | "all">("pending_review");

  const { data: versions, isLoading: versionsLoading } = useCertDomainVersions();
  const { data: proposals, isLoading: proposalsLoading } = useCertDomainProposals(
    proposalFilter === "all" ? undefined : proposalFilter
  );
  const discoverAll = useTriggerCertDomainDiscoverAll();

  // Group versions by cert code
  const versionsByCert = (versions ?? []).reduce<Record<string, CertificationDomainVersion[]>>(
    (acc, v) => {
      const code = v.certification_code ?? "unknown";
      if (!acc[code]) acc[code] = [];
      acc[code].push(v);
      return acc;
    },
    {}
  );

  // Split proposals: known certs vs new certs (certification_id = null)
  const knownProposals = (proposals ?? []).filter((p) => p.certification_id != null);
  const newCertProposals = (proposals ?? []).filter((p) => p.certification_id == null);

  // Build "current domains" lookup for known cert proposals (from current version's notes — no full domain list in version, so we pass empty for diff)
  // The ProposedDomain diff uses what's available — we don't have the old domain list in the version response, so we show empty for current
  const currentDomainsByCode: Record<string, ProposedDomain[]> = {};

  const handleRefreshAll = () => {
    if (!isAdmin) return;
    if (!window.confirm("Run Cert Domain Discovery for all active certifications? This may take a moment.")) return;
    discoverAll.mutate();
  };

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: "2rem 1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "1rem", marginBottom: "0.5rem" }}>
        <div>
          <h1 style={{ marginBottom: "0.25rem" }}>Cert Domain Management</h1>
          <p style={{ color: "var(--text-muted)", margin: 0 }}>
            View and approve exam domain updates discovered by the Cert Domain Discovery Agent.
          </p>
        </div>
        <button
          className="btn btn-primary"
          disabled={!isAdmin || discoverAll.isPending}
          title={!isAdmin ? "Admins only" : undefined}
          onClick={handleRefreshAll}
        >
          {discoverAll.isPending ? <><span className="spinner" /> Discovering…</> : "Refresh all certs"}
        </button>
      </div>
      {!isAdmin && (
        <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginBottom: "1.5rem" }}>
          You have read-only access. Admin actions are disabled.
        </p>
      )}
      {discoverAll.isError && (
        <div className="card" style={{ borderColor: "var(--danger)", color: "var(--danger)", marginBottom: "1rem" }}>
          Discovery failed: {(discoverAll.error as Error).message}
        </div>
      )}
      {discoverAll.isSuccess && (
        <div className="card" style={{ borderColor: "var(--success)", color: "var(--success)", marginBottom: "1rem" }}>
          Discovery complete — {(discoverAll.data as CertificationDomainProposal[])?.length ?? 0} proposal(s) created. Review them below.
        </div>
      )}

      {/* ── Current Versions ──────────────────────────────────────────── */}
      <section style={{ marginBottom: "2.5rem" }}>
        <h2 style={{ fontSize: "1.1rem", marginBottom: "0.875rem" }}>Current domain versions</h2>
        {versionsLoading ? (
          <div style={{ textAlign: "center", padding: "2rem" }}><span className="spinner" /></div>
        ) : Object.keys(versionsByCert).length === 0 ? (
          <div className="empty-state">
            No domain versions yet. Run "Refresh all certs" to discover domains.
          </div>
        ) : (
          Object.entries(versionsByCert)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([code, vers]) => (
              <CertVersionsPanel key={code} certCode={code} versions={vers} />
            ))
        )}
      </section>

      {/* ── Proposals ─────────────────────────────────────────────────── */}
      <section style={{ marginBottom: "2.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem", marginBottom: "0.875rem" }}>
          <h2 style={{ fontSize: "1.1rem", margin: 0 }}>Domain proposals</h2>
          <div style={{ display: "flex", gap: "0.375rem" }}>
            {(["pending_review", "approved", "rejected", "all"] as const).map((f) => (
              <button
                key={f}
                className={`btn ${proposalFilter === f ? "btn-primary" : "btn-outline"}`}
                style={{ fontSize: "0.8125rem", padding: "0.3rem 0.75rem" }}
                onClick={() => setProposalFilter(f)}
              >
                {f === "pending_review" ? "Pending" : f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {proposalsLoading ? (
          <div style={{ textAlign: "center", padding: "2rem" }}><span className="spinner" /></div>
        ) : knownProposals.length === 0 && newCertProposals.length === 0 ? (
          <div className="empty-state">
            No {proposalFilter !== "all" ? proposalFilter.replace("_", " ") : ""} proposals.
          </div>
        ) : (
          <>
            {knownProposals.length > 0 && (
              <div style={{ marginBottom: "1.5rem" }}>
                <h3 style={{ fontSize: "0.9rem", color: "var(--text-muted)", marginBottom: "0.75rem", fontWeight: 500 }}>
                  Known certifications ({knownProposals.length})
                </h3>
                {knownProposals.map((p) => (
                  <ProposalCard
                    key={p.id}
                    proposal={p}
                    currentDomains={currentDomainsByCode[p.cert_code] ?? []}
                    isAdmin={isAdmin}
                  />
                ))}
              </div>
            )}

            {newCertProposals.length > 0 && (
              <div>
                <h3 style={{ fontSize: "0.9rem", color: "var(--text-muted)", marginBottom: "0.75rem", fontWeight: 500 }}>
                  New certifications — not yet in catalog ({newCertProposals.length})
                </h3>
                {newCertProposals.map((p) => (
                  <ProposalCard
                    key={p.id}
                    proposal={p}
                    currentDomains={[]}
                    isAdmin={isAdmin}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
