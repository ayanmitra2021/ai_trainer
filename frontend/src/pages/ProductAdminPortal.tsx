/**
 * ProductAdminPortal — Phase 22.7
 *
 * Full product-admin SaaS management console with slate/grey palette.
 * Completely visually distinct from the org-admin experience.
 *
 * Tabs: Dashboard · Plans · Organizations · Practitioners · Usage Analytics · Earnings
 */

import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { productAdmin } from "../api";
import { useSession } from "../context/SessionContext";
import type {
  AgentAnalytics,
  Organization,
  PlanDistribution,
  ProductAdminPractitioner,
  SubscriptionPlan,
  UsageAnalytics,
} from "../api/types";

// ── Palette ───────────────────────────────────────────────────────────────────

const PA = {
  sidebar: "#1e293b",
  sidebarText: "#cbd5e1",
  sidebarActive: "#f1f5f9",
  sidebarActiveBg: "rgba(241,245,249,0.12)",
  sidebarBorder: "rgba(255,255,255,0.08)",
  bg: "#f8fafc",
  surface: "#ffffff",
  border: "#e2e8f0",
  text: "#1e293b",
  muted: "#64748b",
  primary: "#334155",
  primaryHover: "#1e293b",
  accent: "#3b82f6",
  success: "#059669",
  danger: "#dc2626",
  dangerBg: "#fef2f2",
};

// ── Types ─────────────────────────────────────────────────────────────────────

type AdminTab = "dashboard" | "plans" | "orgs" | "practitioners" | "analytics" | "earnings" | "guide";

// ── Slide-over panel ──────────────────────────────────────────────────────────

function SlideOver({
  title,
  open,
  onClose,
  children,
}: {
  title: string;
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
}) {
  if (!open) return null;
  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: "fixed",
          inset: 0,
          zIndex: 100,
          background: "rgba(0,0,0,0.35)",
        }}
      />
      {/* Panel */}
      <div
        style={{
          position: "fixed",
          top: 0,
          right: 0,
          bottom: 0,
          zIndex: 101,
          width: "min(480px, 100vw)",
          background: PA.surface,
          borderLeft: `1px solid ${PA.border}`,
          boxShadow: "-8px 0 32px rgba(0,0,0,0.12)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "1rem 1.25rem",
            borderBottom: `1px solid ${PA.border}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexShrink: 0,
          }}
        >
          <span style={{ fontWeight: 700, fontSize: "1rem", color: PA.text }}>{title}</span>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              fontSize: "1rem",
              color: PA.muted,
              padding: "0.2rem 0.4rem",
              borderRadius: 4,
            }}
          >
            ✕
          </button>
        </div>
        {/* Body */}
        <div style={{ flex: 1, overflowY: "auto", padding: "1.25rem" }}>
          {children}
        </div>
      </div>
    </>
  );
}

// ── Form helpers ──────────────────────────────────────────────────────────────

const fldStyle: React.CSSProperties = {
  width: "100%",
  padding: "0.5rem 0.75rem",
  fontSize: "0.875rem",
  border: `1px solid ${PA.border}`,
  borderRadius: "6px",
  background: PA.surface,
  color: PA.text,
  boxSizing: "border-box",
  fontFamily: "inherit",
  marginBottom: "0.75rem",
  outline: "none",
};

const lblStyle: React.CSSProperties = {
  fontSize: "0.8125rem",
  fontWeight: 500,
  color: PA.muted,
  display: "block",
  marginBottom: "0.25rem",
};

const btnPrimary: React.CSSProperties = {
  padding: "0.5rem 1.1rem",
  background: PA.primary,
  color: "#fff",
  border: "none",
  borderRadius: "6px",
  fontSize: "0.875rem",
  fontWeight: 600,
  cursor: "pointer",
  fontFamily: "inherit",
};

const btnOutline: React.CSSProperties = {
  padding: "0.5rem 1.1rem",
  background: "transparent",
  color: PA.primary,
  border: `1px solid ${PA.border}`,
  borderRadius: "6px",
  fontSize: "0.875rem",
  fontWeight: 500,
  cursor: "pointer",
  fontFamily: "inherit",
};

const btnDanger: React.CSSProperties = {
  padding: "0.35rem 0.75rem",
  background: "transparent",
  color: PA.danger,
  border: `1px solid #fca5a5`,
  borderRadius: "6px",
  fontSize: "0.8125rem",
  fontWeight: 500,
  cursor: "pointer",
  fontFamily: "inherit",
};

// ── Stat tile ─────────────────────────────────────────────────────────────────

function StatTile({ label, value, icon }: { label: string; value: string | number; icon: string }) {
  return (
    <div
      style={{
        background: PA.surface,
        border: `1px solid ${PA.border}`,
        borderRadius: 10,
        padding: "1.1rem 1.25rem",
        display: "flex",
        alignItems: "center",
        gap: "1rem",
        flex: "1 1 180px",
        minWidth: 160,
      }}
    >
      <span style={{ fontSize: "1.75rem", lineHeight: 1 }}>{icon}</span>
      <div>
        <div style={{ fontSize: "1.5rem", fontWeight: 800, color: PA.text, lineHeight: 1.2 }}>
          {value}
        </div>
        <div style={{ fontSize: "0.78rem", color: PA.muted, marginTop: "0.2rem" }}>{label}</div>
      </div>
    </div>
  );
}

// ── Tier badge ────────────────────────────────────────────────────────────────

function TierBadge({ tier }: { tier: string }) {
  const color =
    tier === "enterprise" ? "#7c3aed" : tier === "paid" ? "#2563eb" : "#64748b";
  return (
    <span
      style={{
        display: "inline-block",
        padding: "0.15rem 0.5rem",
        borderRadius: 999,
        fontSize: "0.72rem",
        fontWeight: 700,
        background: `${color}18`,
        color,
        textTransform: "capitalize",
        border: `1px solid ${color}33`,
      }}
    >
      {tier}
    </span>
  );
}

// ── Table wrapper ─────────────────────────────────────────────────────────────

function DataTable({ headers, children }: { headers: string[]; children: React.ReactNode }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          fontSize: "0.85rem",
          border: `1px solid ${PA.border}`,
          borderRadius: 8,
          overflow: "hidden",
        }}
      >
        <thead>
          <tr style={{ background: "#f1f5f9" }}>
            {headers.map((h) => (
              <th
                key={h}
                style={{
                  padding: "0.55rem 0.85rem",
                  textAlign: "left",
                  fontWeight: 600,
                  color: PA.muted,
                  fontSize: "0.78rem",
                  borderBottom: `1px solid ${PA.border}`,
                  whiteSpace: "nowrap",
                }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

// ── Dashboard tab ─────────────────────────────────────────────────────────────

function DashboardTab() {
  const [dist, setDist] = useState<PlanDistribution | null>(null);
  const [agents, setAgents] = useState<AgentAnalytics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      productAdmin.getPlanDistribution(),
      productAdmin.getAgentAnalytics(),
    ])
      .then(([d, a]) => {
        setDist(d);
        setAgents(a);
      })
      .finally(() => setLoading(false));
  }, []);

  const totalOrgs = dist?.plan_distribution?.reduce((s, r) => s + r.org_count, 0) ?? 0;
  const totalPractitioners = dist?.plan_distribution?.reduce((s, r) => s + r.practitioner_count, 0) ?? 0;
  const activePlans = dist?.plan_distribution?.length ?? 0;
  const totalAgentRuns = agents?.by_agent?.reduce((s, a) => s + a.run_count, 0) ?? 0;

  if (loading) {
    return <div style={{ padding: "2rem", color: PA.muted, textAlign: "center" }}>Loading dashboard…</div>;
  }

  return (
    <div>
      <h2 style={{ fontSize: "1.1rem", fontWeight: 700, color: PA.text, marginBottom: "1.25rem" }}>
        Dashboard Overview
      </h2>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem", marginBottom: "2rem" }}>
        <StatTile label="Total Organizations" value={totalOrgs} icon="🏢" />
        <StatTile label="Total Practitioners" value={totalPractitioners} icon="👥" />
        <StatTile label="Active Plan Tiers" value={activePlans} icon="📋" />
        <StatTile
          label={`Agent Runs (${agents?.period_days ?? 30}d)`}
          value={totalAgentRuns.toLocaleString()}
          icon="⚙️"
        />
      </div>
      {dist && (
        <div style={{ marginBottom: "2rem" }}>
          <h3 style={{ fontSize: "0.9rem", fontWeight: 700, color: PA.muted, marginBottom: "0.75rem" }}>
            New Enrollments (Last 30 Days)
          </h3>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.5rem",
              padding: "0.5rem 1rem",
              background: "rgba(59,130,246,0.08)",
              border: "1px solid rgba(59,130,246,0.2)",
              borderRadius: 8,
              fontSize: "1.1rem",
              fontWeight: 700,
              color: PA.accent,
            }}
          >
            {dist.new_enrollments_last_30d}
            <span style={{ fontSize: "0.8rem", fontWeight: 400, color: PA.muted }}>practitioners enrolled</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Plans tab helpers ─────────────────────────────────────────────────────────

/** Render -1 (unlimited sentinel) as a styled "∞ Unlimited" label. */
function LimitCell({ value }: { value: number }) {
  if (value === -1) {
    return (
      <span style={{ color: PA.success, fontWeight: 600, fontSize: "0.8rem" }}>∞ Unlimited</span>
    );
  }
  return <span style={{ color: PA.muted }}>{value}</span>;
}

/** Number input with an "Unlimited" toggle checkbox beside it. */
function LimitField({
  label,
  value,
  onChange,
  unlimited,
  onUnlimitedChange,
  defaultValue = 1,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  unlimited: boolean;
  onUnlimitedChange: (v: boolean) => void;
  defaultValue?: number;
}) {
  return (
    <div style={{ marginBottom: "0.75rem" }}>
      <label style={lblStyle}>{label}</label>
      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
        <input
          style={{ ...fldStyle, marginBottom: 0, flex: 1, opacity: unlimited ? 0.4 : 1 }}
          type="number"
          min={1}
          value={unlimited ? defaultValue : value}
          onChange={(e) => onChange(+e.target.value)}
          disabled={unlimited}
          required={!unlimited}
        />
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.4rem",
            fontSize: "0.8125rem",
            fontWeight: 600,
            color: unlimited ? PA.success : PA.muted,
            cursor: "pointer",
            whiteSpace: "nowrap",
            userSelect: "none",
          }}
        >
          <input
            type="checkbox"
            checked={unlimited}
            onChange={(e) => onUnlimitedChange(e.target.checked)}
            style={{ accentColor: PA.success }}
          />
          Unlimited
        </label>
      </div>
    </div>
  );
}

// ── Plans tab ─────────────────────────────────────────────────────────────────

function PlansTab() {
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [formOpen, setFormOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<SubscriptionPlan | null>(null);
  const [formErr, setFormErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Form state — numeric limits (store the bounded value; unlimited flag is separate)
  const [fName, setFName] = useState("");
  const [fTier, setFTier] = useState<"free" | "paid" | "enterprise">("free");
  const [fMaxProfiles, setFMaxProfiles] = useState(2);
  const [fMaxProfilesUnlimited, setFMaxProfilesUnlimited] = useState(false);
  const [fMaxPaths, setFMaxPaths] = useState(2);
  const [fMaxPathsUnlimited, setFMaxPathsUnlimited] = useState(false);
  const [fMaxExams, setFMaxExams] = useState(2);
  const [fMaxExamsUnlimited, setFMaxExamsUnlimited] = useState(false);
  const [fMaxPractitioners, setFMaxPractitioners] = useState(10);
  const [fMaxPractitionersUnlimited, setFMaxPractitionersUnlimited] = useState(false);
  const [fRecycling, setFRecycling] = useState(false);
  const [fNudges, setFNudges] = useState(false);
  const [fTeams, setFTeams] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    productAdmin.listPlans().then(setPlans).finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const openNew = () => {
    setEditTarget(null);
    setFName(""); setFTier("free");
    setFMaxProfiles(2); setFMaxProfilesUnlimited(false);
    setFMaxPaths(2); setFMaxPathsUnlimited(false);
    setFMaxExams(2); setFMaxExamsUnlimited(false);
    setFMaxPractitioners(10); setFMaxPractitionersUnlimited(false);
    setFRecycling(false); setFNudges(false); setFTeams(false);
    setFormErr(null);
    setFormOpen(true);
  };

  const openEdit = (p: SubscriptionPlan) => {
    setEditTarget(p);
    setFName(p.name); setFTier(p.tier);
    setFMaxProfilesUnlimited(p.max_profiles_per_practitioner === -1);
    setFMaxProfiles(p.max_profiles_per_practitioner === -1 ? 2 : p.max_profiles_per_practitioner);
    setFMaxPathsUnlimited(p.max_learning_paths === -1);
    setFMaxPaths(p.max_learning_paths === -1 ? 2 : p.max_learning_paths);
    setFMaxExamsUnlimited(p.max_mock_exams_per_profile === -1);
    setFMaxExams(p.max_mock_exams_per_profile === -1 ? 2 : p.max_mock_exams_per_profile);
    setFMaxPractitionersUnlimited(p.max_practitioners_per_org === -1);
    setFMaxPractitioners(p.max_practitioners_per_org === -1 ? 100 : p.max_practitioners_per_org);
    setFRecycling(p.allow_cert_recycling);
    setFNudges(p.nudges_enabled); setFTeams(p.teams_notifications_enabled);
    setFormErr(null);
    setFormOpen(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormErr(null);
    setSaving(true);
    const body: Partial<SubscriptionPlan> = {
      name: fName,
      tier: fTier,
      max_profiles_per_practitioner: fMaxProfilesUnlimited ? -1 : fMaxProfiles,
      max_learning_paths: fMaxPathsUnlimited ? -1 : fMaxPaths,
      max_mock_exams_per_profile: fMaxExamsUnlimited ? -1 : fMaxExams,
      max_practitioners_per_org: fMaxPractitionersUnlimited ? -1 : fMaxPractitioners,
      allow_cert_recycling: fRecycling,
      nudges_enabled: fNudges,
      teams_notifications_enabled: fTeams,
    };
    try {
      if (editTarget) {
        await productAdmin.updatePlan(editTarget.id, body);
      } else {
        await productAdmin.createPlan(body);
      }
      setFormOpen(false);
      load();
    } catch (err: unknown) {
      setFormErr((err as Error).message ?? "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleDeactivate = async (id: string, name: string) => {
    if (!window.confirm(`Deactivate plan "${name}"? Orgs on this plan will keep their current access.`)) return;
    await productAdmin.deactivatePlan(id);
    load();
  };

  // Sort plans by name for consistent display
  const sortedPlans = [...plans].sort((a, b) => a.name.localeCompare(b.name));

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem" }}>
        <h2 style={{ fontSize: "1.1rem", fontWeight: 700, color: PA.text }}>Subscription Plans</h2>
        <button style={btnPrimary} onClick={openNew}>+ New Plan</button>
      </div>

      {loading ? (
        <div style={{ color: PA.muted, padding: "2rem", textAlign: "center" }}>Loading…</div>
      ) : sortedPlans.length === 0 ? (
        <div style={{ color: PA.muted, padding: "2rem", textAlign: "center" }}>No plans found.</div>
      ) : (
        <DataTable headers={["Name", "Tier", "Profiles", "Paths", "Exams", "Pract./Org", "Nudges", "Status", "Actions"]}>
          {sortedPlans.map((p) => (
            <tr key={p.id} style={{ borderTop: `1px solid ${PA.border}` }}>
              <td style={{ padding: "0.6rem 0.85rem", fontWeight: 600, color: PA.text }}>{p.name}</td>
              <td style={{ padding: "0.6rem 0.85rem" }}><TierBadge tier={p.tier} /></td>
              <td style={{ padding: "0.6rem 0.85rem" }}><LimitCell value={p.max_profiles_per_practitioner} /></td>
              <td style={{ padding: "0.6rem 0.85rem" }}><LimitCell value={p.max_learning_paths} /></td>
              <td style={{ padding: "0.6rem 0.85rem" }}><LimitCell value={p.max_mock_exams_per_profile} /></td>
              <td style={{ padding: "0.6rem 0.85rem" }}><LimitCell value={p.max_practitioners_per_org} /></td>
              <td style={{ padding: "0.6rem 0.85rem" }}>
                {p.nudges_enabled ? "✅" : "—"}
              </td>
              <td style={{ padding: "0.6rem 0.85rem" }}>
                <span style={{ color: p.is_active ? PA.success : PA.danger, fontWeight: 600, fontSize: "0.8rem" }}>
                  {p.is_active ? "Active" : "Inactive"}
                </span>
              </td>
              <td style={{ padding: "0.6rem 0.85rem" }}>
                <div style={{ display: "flex", gap: "0.4rem" }}>
                  <button style={btnOutline} onClick={() => openEdit(p)}>Edit</button>
                  {p.is_active && (
                    <button style={btnDanger} onClick={() => handleDeactivate(p.id, p.name)}>
                      Deactivate
                    </button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </DataTable>
      )}

      <SlideOver title={editTarget ? "Edit Plan" : "New Plan"} open={formOpen} onClose={() => setFormOpen(false)}>
        <form onSubmit={handleSave}>
          {formErr && (
            <div style={{ padding: "0.6rem", background: PA.dangerBg, borderRadius: 6, color: PA.danger, fontSize: "0.8125rem", marginBottom: "1rem" }}>
              {formErr}
            </div>
          )}
          <label style={lblStyle}>Plan Name</label>
          <input style={fldStyle} value={fName} onChange={(e) => setFName(e.target.value)} required />

          <label style={lblStyle}>Tier</label>
          <select
            style={fldStyle}
            value={fTier}
            onChange={(e) => setFTier(e.target.value as "free" | "paid" | "enterprise")}
          >
            <option value="free">Free</option>
            <option value="paid">Paid</option>
            <option value="enterprise">Enterprise</option>
          </select>

          <LimitField
            label="Max Profiles per Practitioner"
            value={fMaxProfiles} onChange={setFMaxProfiles}
            unlimited={fMaxProfilesUnlimited} onUnlimitedChange={setFMaxProfilesUnlimited}
            defaultValue={2}
          />
          <LimitField
            label="Max Learning Paths"
            value={fMaxPaths} onChange={setFMaxPaths}
            unlimited={fMaxPathsUnlimited} onUnlimitedChange={setFMaxPathsUnlimited}
            defaultValue={2}
          />
          <LimitField
            label="Max Mock Exams per Profile"
            value={fMaxExams} onChange={setFMaxExams}
            unlimited={fMaxExamsUnlimited} onUnlimitedChange={setFMaxExamsUnlimited}
            defaultValue={2}
          />
          <LimitField
            label="Max Practitioners per Org"
            value={fMaxPractitioners} onChange={setFMaxPractitioners}
            unlimited={fMaxPractitionersUnlimited} onUnlimitedChange={setFMaxPractitionersUnlimited}
            defaultValue={100}
          />

          {/* Capability checkboxes — explicit dark text for legibility */}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", margin: "0.25rem 0 1.25rem" }}>
            {(
              [
                { label: "Allow cert recycling", checked: fRecycling, onChange: setFRecycling },
                { label: "Nudges enabled", checked: fNudges, onChange: setFNudges },
                { label: "Teams notifications enabled", checked: fTeams, onChange: setFTeams },
              ] as const
            ).map(({ label, checked, onChange }) => (
              <label
                key={label}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.625rem",
                  cursor: "pointer",
                  fontSize: "0.875rem",
                  fontWeight: 500,
                  color: PA.text,        // explicit dark colour — fixes barely-readable issue
                  userSelect: "none",
                }}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(e) => onChange(e.target.checked)}
                  style={{ width: 16, height: 16, accentColor: PA.primary, flexShrink: 0 }}
                />
                {label}
              </label>
            ))}
          </div>

          <div style={{ display: "flex", gap: "0.75rem" }}>
            <button type="submit" style={btnPrimary} disabled={saving}>
              {saving ? "Saving…" : "Save Plan"}
            </button>
            <button type="button" style={btnOutline} onClick={() => setFormOpen(false)}>Cancel</button>
          </div>
        </form>
      </SlideOver>
    </div>
  );
}

// ── Organizations tab ─────────────────────────────────────────────────────────

function OrgsTab() {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [formOpen, setFormOpen] = useState(false);
  const [formErr, setFormErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [newCode, setNewCode] = useState<string | null>(null);
  // Tracks which org's enrollment code is currently revealed
  const [revealedOrgId, setRevealedOrgId] = useState<string | null>(null);

  const [fName, setFName] = useState("");
  const [fPlanId, setFPlanId] = useState("");
  const [fBillingEmail, setFBillingEmail] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([productAdmin.listOrgs(), productAdmin.listPlans()])
      .then(([o, p]) => { setOrgs(o); setPlans(p); })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const openNew = () => {
    setFName(""); setFPlanId(plans[0]?.id ?? ""); setFBillingEmail("");
    setFormErr(null); setNewCode(null);
    setFormOpen(true);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormErr(null);
    setSaving(true);
    try {
      const created = await productAdmin.createOrg({
        name: fName,
        plan_id: fPlanId,
        billing_email: fBillingEmail || undefined,
      });
      setNewCode(created.enrollment_code ?? null);
      load();
    } catch (err: unknown) {
      setFormErr((err as Error).message ?? "Create failed");
    } finally {
      setSaving(false);
    }
  };

  const handleRegenCode = async (id: string, name: string) => {
    if (!window.confirm(`Regenerate enrollment code for "${name}"? The old code will stop working immediately.`)) return;
    const result = await productAdmin.regenerateCode(id);
    alert(`New enrollment code for ${name}: ${result.code}`);
    load();
  };

  const handleToggleActive = async (org: Organization) => {
    if (org.is_active) {
      if (!window.confirm(`Deactivate org "${org.name}"? All their practitioners will be unable to log in.`)) return;
      await productAdmin.deactivateOrg(org.id);
    } else {
      await productAdmin.reactivateOrg(org.id);
    }
    load();
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem" }}>
        <h2 style={{ fontSize: "1.1rem", fontWeight: 700, color: PA.text }}>Organizations</h2>
        <button style={btnPrimary} onClick={openNew}>+ New Organization</button>
      </div>

      {loading ? (
        <div style={{ color: PA.muted, padding: "2rem", textAlign: "center" }}>Loading…</div>
      ) : orgs.length === 0 ? (
        <div style={{ color: PA.muted, padding: "2rem", textAlign: "center" }}>No organizations found.</div>
      ) : (
        <DataTable headers={["Name", "Plan", "Practitioners", "Code", "Status", "Actions"]}>
          {[...orgs].sort((a, b) => a.name.localeCompare(b.name)).map((o) => {
            const isRevealed = revealedOrgId === o.id;
            return (
              <tr key={o.id} style={{ borderTop: `1px solid ${PA.border}` }}>
                <td style={{ padding: "0.6rem 0.85rem", fontWeight: 600, color: PA.text }}>{o.name}</td>
                <td style={{ padding: "0.6rem 0.85rem" }}>
                  {o.plan_name && <span style={{ marginRight: "0.4rem", fontSize: "0.85rem", color: PA.text, fontWeight: 500 }}>{o.plan_name}</span>}
                  {o.plan_tier && <TierBadge tier={o.plan_tier} />}
                </td>
                <td style={{ padding: "0.6rem 0.85rem", color: PA.muted }}>{o.practitioner_count ?? "—"}</td>
                <td style={{ padding: "0.6rem 0.85rem" }}>
                  {o.enrollment_code ? (
                    <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
                      <code style={{
                        fontSize: "0.78rem",
                        background: "#f1f5f9",
                        padding: "0.15rem 0.4rem",
                        borderRadius: 4,
                        letterSpacing: isRevealed ? "0.04em" : "0.12em",
                        color: isRevealed ? PA.text : PA.muted,
                        minWidth: "7rem",
                        display: "inline-block",
                        userSelect: isRevealed ? "text" : "none",
                      }}>
                        {isRevealed ? o.enrollment_code : "••••••••••••••••"}
                      </code>
                      <button
                        onClick={() => setRevealedOrgId(isRevealed ? null : o.id)}
                        title={isRevealed ? "Hide code" : "Reveal code"}
                        style={{
                          background: "none",
                          border: "none",
                          cursor: "pointer",
                          fontSize: "1rem",
                          padding: "0.1rem 0.25rem",
                          opacity: 0.7,
                          lineHeight: 1,
                        }}
                      >
                        {isRevealed ? "🙈" : "👁"}
                      </button>
                    </div>
                  ) : (
                    <span style={{ color: PA.muted }}>—</span>
                  )}
                </td>
                <td style={{ padding: "0.6rem 0.85rem" }}>
                  <span style={{ color: o.is_active ? PA.success : PA.danger, fontWeight: 600, fontSize: "0.8rem" }}>
                    {o.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td style={{ padding: "0.6rem 0.85rem" }}>
                  <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                    <button
                      style={btnOutline}
                      onClick={() => handleRegenCode(o.id, o.name)}
                      title="Regenerate enrollment code"
                    >
                      ↻ Code
                    </button>
                    <button
                      style={o.is_active ? btnDanger : { ...btnOutline, color: PA.success, borderColor: "#86efac" }}
                      onClick={() => handleToggleActive(o)}
                    >
                      {o.is_active ? "Deactivate" : "Reactivate"}
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </DataTable>
      )}

      <SlideOver title="New Organization" open={formOpen} onClose={() => { setFormOpen(false); setNewCode(null); }}>
        {newCode ? (
          <div>
            <div
              style={{
                padding: "1rem",
                background: "rgba(5,150,105,0.08)",
                border: "1px solid rgba(5,150,105,0.25)",
                borderRadius: 8,
                marginBottom: "1.25rem",
              }}
            >
              <div style={{ fontWeight: 700, color: PA.success, marginBottom: "0.5rem" }}>✅ Organization created!</div>
              <p style={{ fontSize: "0.875rem", color: PA.text, margin: "0 0 0.75rem" }}>
                Share this enrollment code with the org admin:
              </p>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                <code
                  style={{
                    fontSize: "1.1rem",
                    fontWeight: 800,
                    background: "#f1f5f9",
                    padding: "0.4rem 0.8rem",
                    borderRadius: 6,
                    letterSpacing: "0.08em",
                    color: PA.text,
                  }}
                >
                  {newCode}
                </code>
                <button
                  style={btnOutline}
                  onClick={() => navigator.clipboard.writeText(newCode)}
                >
                  📋 Copy
                </button>
              </div>
            </div>
            <button style={btnPrimary} onClick={() => { setFormOpen(false); setNewCode(null); }}>Done</button>
          </div>
        ) : (
          <form onSubmit={handleCreate}>
            {formErr && (
              <div style={{ padding: "0.6rem", background: PA.dangerBg, borderRadius: 6, color: PA.danger, fontSize: "0.8125rem", marginBottom: "1rem" }}>
                {formErr}
              </div>
            )}
            <label style={lblStyle}>Organization Name</label>
            <input style={fldStyle} value={fName} onChange={(e) => setFName(e.target.value)} required />

            <label style={lblStyle}>Plan</label>
            <select style={fldStyle} value={fPlanId} onChange={(e) => setFPlanId(e.target.value)} required>
              {[...plans].filter((p) => p.is_active).sort((a, b) => a.name.localeCompare(b.name)).map((p) => (
                <option key={p.id} value={p.id}>{p.name} ({p.tier})</option>
              ))}
            </select>

            <label style={lblStyle}>Billing Email (optional)</label>
            <input
              style={fldStyle}
              type="email"
              value={fBillingEmail}
              onChange={(e) => setFBillingEmail(e.target.value)}
              placeholder="billing@example.com"
            />

            <div style={{ display: "flex", gap: "0.75rem" }}>
              <button type="submit" style={btnPrimary} disabled={saving}>
                {saving ? "Creating…" : "Create Organization"}
              </button>
              <button type="button" style={btnOutline} onClick={() => setFormOpen(false)}>Cancel</button>
            </div>
          </form>
        )}
      </SlideOver>
    </div>
  );
}

// ── Practitioners tab ─────────────────────────────────────────────────────────

type PractSortCol = "name" | "email" | "org_name" | "plan_tier" | "is_active";

function PractitionersTab() {
  const [practitioners, setPractitioners] = useState<ProductAdminPractitioner[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterActive, setFilterActive] = useState<boolean | undefined>(undefined);
  const [search, setSearch] = useState("");
  const [sortCol, setSortCol] = useState<PractSortCol>("name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 20;

  const load = useCallback((isActive?: boolean) => {
    setLoading(true);
    productAdmin
      .listPractitioners(isActive !== undefined ? { is_active: isActive } : undefined)
      .then(setPractitioners)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(filterActive); setPage(0); }, [load, filterActive]);
  useEffect(() => { setPage(0); }, [search, sortCol, sortDir]);

  const handleToggle = async (p: ProductAdminPractitioner) => {
    if (p.is_active) {
      if (!window.confirm(`Deactivate ${p.name}? They won't be able to log in.`)) return;
      await productAdmin.deactivatePractitioner(p.id);
    } else {
      await productAdmin.reactivatePractitioner(p.id);
    }
    load(filterActive);
  };

  const handleSort = (col: PractSortCol) => {
    if (sortCol === col) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortCol(col); setSortDir("asc"); }
  };

  // Filter by search query across name / email / org
  const q = search.trim().toLowerCase();
  const filtered = practitioners.filter((p) =>
    !q ||
    p.name.toLowerCase().includes(q) ||
    p.email.toLowerCase().includes(q) ||
    (p.org_name ?? "").toLowerCase().includes(q)
  );

  // Sort
  const sorted = [...filtered].sort((a, b) => {
    const av = a[sortCol] ?? "";
    const bv = b[sortCol] ?? "";
    const cmp =
      typeof av === "boolean"
        ? (av === bv ? 0 : av ? -1 : 1) // active first when asc
        : String(av).localeCompare(String(bv));
    return sortDir === "asc" ? cmp : -cmp;
  });

  // Paginate
  const pageCount = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const safePageIdx = Math.min(page, pageCount - 1);
  const paged = sorted.slice(safePageIdx * PAGE_SIZE, (safePageIdx + 1) * PAGE_SIZE);

  // Sortable column header
  const SortTh = ({ col, label, right }: { col: PractSortCol; label: string; right?: boolean }) => (
    <th
      onClick={() => handleSort(col)}
      style={{
        padding: "0.55rem 0.85rem",
        textAlign: right ? "right" : "left",
        fontWeight: 600,
        color: sortCol === col ? PA.accent : PA.muted,
        fontSize: "0.78rem",
        borderBottom: `1px solid ${PA.border}`,
        whiteSpace: "nowrap",
        cursor: "pointer",
        userSelect: "none",
      }}
    >
      {label}{" "}
      {sortCol === col
        ? sortDir === "asc" ? "▲" : "▼"
        : <span style={{ opacity: 0.3 }}>↕</span>}
    </th>
  );

  const pageBtnStyle = (disabled: boolean): React.CSSProperties => ({
    ...btnOutline,
    padding: "0.3rem 0.6rem",
    opacity: disabled ? 0.35 : 1,
    cursor: disabled ? "default" : "pointer",
    pointerEvents: disabled ? "none" : "auto",
  });

  return (
    <div>
      {/* Header + active filter */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.75rem" }}>
        <h2 style={{ fontSize: "1.1rem", fontWeight: 700, color: PA.text }}>Practitioners</h2>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          {([
            { label: "All", value: undefined },
            { label: "Active", value: true },
            { label: "Inactive", value: false },
          ] as const).map(({ label, value }) => (
            <button
              key={label}
              style={{
                ...btnOutline,
                background: filterActive === value ? PA.primary : "transparent",
                color: filterActive === value ? "#fff" : PA.primary,
              }}
              onClick={() => setFilterActive(value as boolean | undefined)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Search bar + result count */}
      <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap" }}>
        <input
          type="search"
          placeholder="Search by name, email or org…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ ...fldStyle, flex: "1 1 260px", maxWidth: 380, marginBottom: 0 }}
        />
        <span style={{ fontSize: "0.8rem", color: PA.muted, whiteSpace: "nowrap" }}>
          {filtered.length === practitioners.length
            ? `${practitioners.length} practitioners`
            : `${filtered.length} of ${practitioners.length}`}
        </span>
      </div>

      {loading ? (
        <div style={{ color: PA.muted, padding: "2rem", textAlign: "center" }}>Loading…</div>
      ) : filtered.length === 0 ? (
        <div style={{ color: PA.muted, padding: "2rem", textAlign: "center" }}>
          {q ? `No practitioners match "${search}".` : "No practitioners found."}
        </div>
      ) : (
        <>
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: "0.85rem",
                border: `1px solid ${PA.border}`,
                borderRadius: 8,
                overflow: "hidden",
              }}
            >
              <thead>
                <tr style={{ background: "#f1f5f9" }}>
                  <SortTh col="name" label="Name" />
                  <SortTh col="email" label="Email" />
                  <SortTh col="org_name" label="Org" />
                  <SortTh col="plan_tier" label="Plan" />
                  <SortTh col="is_active" label="Status" />
                  <th style={{ padding: "0.55rem 0.85rem", textAlign: "left", fontWeight: 600, color: PA.muted, fontSize: "0.78rem", borderBottom: `1px solid ${PA.border}`, whiteSpace: "nowrap" }}>
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {paged.map((p) => (
                  <tr key={p.id} style={{ borderTop: `1px solid ${PA.border}` }}>
                    <td style={{ padding: "0.6rem 0.85rem", fontWeight: 600, color: PA.text }}>{p.name}</td>
                    <td style={{ padding: "0.6rem 0.85rem", color: PA.muted, fontSize: "0.8125rem" }}>{p.email}</td>
                    <td style={{ padding: "0.6rem 0.85rem", color: PA.muted }}>{p.org_name ?? "—"}</td>
                    <td style={{ padding: "0.6rem 0.85rem" }}><TierBadge tier={p.plan_tier ?? "free"} /></td>
                    <td style={{ padding: "0.6rem 0.85rem" }}>
                      <span style={{ color: p.is_active ? PA.success : PA.danger, fontWeight: 600, fontSize: "0.8rem" }}>
                        {p.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td style={{ padding: "0.6rem 0.85rem" }}>
                      <button
                        style={p.is_active ? btnDanger : { ...btnOutline, color: PA.success, borderColor: "#86efac" }}
                        onClick={() => handleToggle(p)}
                      >
                        {p.is_active ? "Deactivate" : "Reactivate"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {pageCount > 1 && (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "0.4rem", marginTop: "1rem", fontSize: "0.85rem" }}>
              <button style={pageBtnStyle(safePageIdx === 0)} onClick={() => setPage(0)}>«</button>
              <button style={pageBtnStyle(safePageIdx === 0)} onClick={() => setPage((p) => Math.max(0, p - 1))}>‹ Prev</button>
              <span style={{ color: PA.muted, padding: "0 0.5rem" }}>
                Page {safePageIdx + 1} of {pageCount}
              </span>
              <button style={pageBtnStyle(safePageIdx === pageCount - 1)} onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}>Next ›</button>
              <button style={pageBtnStyle(safePageIdx === pageCount - 1)} onClick={() => setPage(pageCount - 1)}>»</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── Analytics tab ─────────────────────────────────────────────────────────────

function AnalyticsTab() {
  const [usage, setUsage] = useState<UsageAnalytics | null>(null);
  const [agents, setAgents] = useState<AgentAnalytics | null>(null);
  const [dist, setDist] = useState<PlanDistribution | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      productAdmin.getUsageAnalytics(),
      productAdmin.getAgentAnalytics(),
      productAdmin.getPlanDistribution(),
    ])
      .then(([u, a, d]) => { setUsage(u); setAgents(a); setDist(d); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div style={{ color: PA.muted, padding: "2rem", textAlign: "center" }}>Loading analytics…</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
      {/* Plan Distribution */}
      {dist && (
        <div>
          <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: PA.text, marginBottom: "0.75rem" }}>Plan Distribution</h3>
          <DataTable headers={["Tier", "Plan Name", "Orgs", "Practitioners"]}>
            {dist.plan_distribution.map((r, i) => (
              <tr key={i} style={{ borderTop: `1px solid ${PA.border}` }}>
                <td style={{ padding: "0.6rem 0.85rem" }}><TierBadge tier={r.tier} /></td>
                <td style={{ padding: "0.6rem 0.85rem", color: PA.text }}>{r.plan_name}</td>
                <td style={{ padding: "0.6rem 0.85rem", color: PA.muted }}>{r.org_count}</td>
                <td style={{ padding: "0.6rem 0.85rem", color: PA.muted }}>{r.practitioner_count}</td>
              </tr>
            ))}
          </DataTable>
        </div>
      )}

      {/* Agent Utilization */}
      {agents && (
        <div>
          <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: PA.text, marginBottom: "0.75rem" }}>
            Agent Utilization (Last {agents.period_days} days)
          </h3>
          <DataTable headers={["Agent", "Runs", "Success", "Failed", "Avg Latency", "p95 Latency"]}>
            {agents.by_agent.map((a, i) => (
              <tr key={i} style={{ borderTop: `1px solid ${PA.border}` }}>
                <td style={{ padding: "0.6rem 0.85rem", fontWeight: 500, color: PA.text, fontFamily: "monospace", fontSize: "0.8rem" }}>
                  {a.agent_name}
                </td>
                <td style={{ padding: "0.6rem 0.85rem", color: PA.muted }}>{a.run_count.toLocaleString()}</td>
                <td style={{ padding: "0.6rem 0.85rem", color: PA.success }}>{a.success_count.toLocaleString()}</td>
                <td style={{ padding: "0.6rem 0.85rem", color: a.failure_count > 0 ? PA.danger : PA.muted }}>
                  {a.failure_count.toLocaleString()}
                </td>
                <td style={{ padding: "0.6rem 0.85rem", color: PA.muted }}>{a.avg_latency_ms.toFixed(0)}ms</td>
                <td style={{ padding: "0.6rem 0.85rem", color: PA.muted }}>{a.p95_latency_ms.toFixed(0)}ms</td>
              </tr>
            ))}
          </DataTable>
        </div>
      )}

      {/* Usage by Tier */}
      {usage && (
        <div>
          <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: PA.text, marginBottom: "0.75rem" }}>Usage by Tier</h3>
          <DataTable headers={["Tier", "Plan", "Orgs", "Practitioners", "Active", "Quizzes", "Lessons", "Exams"]}>
            {usage.by_plan_tier.map((r, i) => (
              <tr key={i} style={{ borderTop: `1px solid ${PA.border}` }}>
                <td style={{ padding: "0.6rem 0.85rem" }}><TierBadge tier={r.tier} /></td>
                <td style={{ padding: "0.6rem 0.85rem", color: PA.text }}>{r.plan_name}</td>
                <td style={{ padding: "0.6rem 0.85rem", color: PA.muted }}>{r.org_count}</td>
                <td style={{ padding: "0.6rem 0.85rem", color: PA.muted }}>{r.practitioner_count}</td>
                <td style={{ padding: "0.6rem 0.85rem", color: PA.muted }}>{r.active_practitioner_count}</td>
                <td style={{ padding: "0.6rem 0.85rem", color: PA.muted }}>{r.total_quiz_attempts.toLocaleString()}</td>
                <td style={{ padding: "0.6rem 0.85rem", color: PA.muted }}>{r.total_lesson_reads.toLocaleString()}</td>
                <td style={{ padding: "0.6rem 0.85rem", color: PA.muted }}>{r.total_mock_exams_completed.toLocaleString()}</td>
              </tr>
            ))}
          </DataTable>
        </div>
      )}
    </div>
  );
}

// ── Earnings tab ──────────────────────────────────────────────────────────────

function EarningsTab() {
  return (
    <div
      style={{
        padding: "2.5rem 1.5rem",
        background: PA.surface,
        border: `1px solid ${PA.border}`,
        borderRadius: 12,
        textAlign: "center",
        maxWidth: 520,
        margin: "2rem auto",
      }}
    >
      <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>💳</div>
      <h2 style={{ fontSize: "1.15rem", fontWeight: 700, color: PA.text, marginBottom: "0.5rem" }}>
        Payment integration coming soon
      </h2>
      <p style={{ fontSize: "0.9rem", color: PA.muted, lineHeight: 1.6 }}>
        Earnings data will appear here once billing is configured. Payment integration is planned for a future
        release.
      </p>
    </div>
  );
}

// ── Guide tab ─────────────────────────────────────────────────────────────────

// Design atoms — mirrors GuidePage.tsx but wired to the PA colour palette

function PAQuickRead({ text }: { text: string }) {
  const [collapsed, setCollapsed] = React.useState(false);
  return (
    <div style={{ background: "rgba(51,65,85,0.06)", border: "1px solid rgba(51,65,85,0.18)", borderRadius: 10, padding: "1rem 1.25rem", marginBottom: "1.75rem" }}>
      <button
        onClick={() => setCollapsed((c) => !c)}
        style={{ display: "flex", alignItems: "center", gap: "0.5rem", background: "none", border: "none", cursor: "pointer", width: "100%", padding: 0 }}
      >
        <span style={{ fontSize: "1.05rem" }}>⚡</span>
        <span style={{ fontWeight: 700, fontSize: "0.82rem", color: PA.primary, flex: 1, textAlign: "left" }}>2-MIN QUICK READ</span>
        <span style={{ fontSize: "0.75rem", color: PA.muted }}>{collapsed ? "▶ expand" : "▼ collapse"}</span>
      </button>
      {!collapsed && (
        <p style={{ margin: "0.65rem 0 0 1.6rem", fontSize: "0.9rem", color: PA.text, lineHeight: 1.7 }}>{text}</p>
      )}
    </div>
  );
}

function PASecHeading({ children }: { children: React.ReactNode }) {
  return (
    <h2 style={{ fontSize: "1.4rem", fontWeight: 800, color: PA.primary, borderLeft: `4px solid ${PA.accent}`, paddingLeft: "0.75rem", marginTop: 0, marginBottom: "0.4rem", lineHeight: 1.3 }}>
      {children}
    </h2>
  );
}

function PASubHead({ children }: { children: React.ReactNode }) {
  return (
    <h3 style={{ fontSize: "1rem", fontWeight: 700, color: PA.text, marginTop: "1.5rem", marginBottom: "0.4rem", borderBottom: `1px solid ${PA.border}`, paddingBottom: "0.25rem" }}>
      {children}
    </h3>
  );
}

function PATip({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ background: "rgba(51,65,85,0.05)", border: "1px solid rgba(51,65,85,0.15)", borderLeft: `3px solid ${PA.accent}`, borderRadius: "0 8px 8px 0", padding: "0.7rem 1rem", margin: "1rem 0", fontSize: "0.875rem", color: PA.text, lineHeight: 1.65 }}>
      <span style={{ fontWeight: 700, color: PA.accent }}>💡 Tip:&nbsp;</span>{children}
    </div>
  );
}

function PAWarn({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ background: "rgba(217,119,6,0.05)", border: "1px solid rgba(217,119,6,0.2)", borderLeft: "3px solid #d97706", borderRadius: "0 8px 8px 0", padding: "0.7rem 1rem", margin: "1rem 0", fontSize: "0.875rem", color: PA.text, lineHeight: 1.65 }}>
      <span style={{ fontWeight: 700, color: "#d97706" }}>⚠️ Note:&nbsp;</span>{children}
    </div>
  );
}

function PASteps({ steps }: { steps: string[] }) {
  return (
    <ol style={{ margin: "0.4rem 0 0.9rem 0", padding: 0, listStyle: "none", fontSize: "0.9rem" }}>
      {steps.map((step, i) => (
        <li key={i} style={{ display: "flex", alignItems: "flex-start", marginBottom: "0.6rem", lineHeight: 1.65, color: PA.text }}>
          <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: 22, height: 22, borderRadius: "50%", background: PA.primary, color: "#fff", fontSize: "0.72rem", fontWeight: 700, marginRight: "0.6rem", marginTop: "0.15rem", flexShrink: 0 }}>
            {i + 1}
          </span>
          <span dangerouslySetInnerHTML={{ __html: step }} />
        </li>
      ))}
    </ol>
  );
}

function PABullets({ items }: { items: string[] }) {
  return (
    <ul style={{ margin: "0.4rem 0 0.9rem 1.1rem", padding: 0, lineHeight: 1.75, fontSize: "0.9rem", color: PA.text }}>
      {items.map((item, i) => (
        <li key={i} style={{ marginBottom: "0.3rem" }} dangerouslySetInnerHTML={{ __html: item }} />
      ))}
    </ul>
  );
}

function PATable({ rows }: { rows: { label: string; value: string }[] }) {
  return (
    <div style={{ overflowX: "auto", margin: "0.5rem 0 1rem" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem", border: `1px solid ${PA.border}`, borderRadius: 8, overflow: "hidden" }}>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td style={{ padding: "0.4rem 0.75rem", fontWeight: 600, fontSize: "0.85rem", color: PA.text, whiteSpace: "nowrap", verticalAlign: "top", borderBottom: `1px solid ${PA.border}` }} dangerouslySetInnerHTML={{ __html: r.label }} />
              <td style={{ padding: "0.4rem 0.75rem", fontSize: "0.85rem", color: PA.muted, borderBottom: `1px solid ${PA.border}` }} dangerouslySetInnerHTML={{ __html: r.value }} />
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Guide section content ──────────────────────────────────────────────────────

const guideLoginContent = (
  <>
    <PASubHead>Navigating to the portal</PASubHead>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: PA.text }}>
      The product admin portal lives at a separate URL from the practitioner portal. Practitioners and org admins cannot reach these pages.
    </p>
    <PATable rows={[
      { label: "Portal URL", value: "http://localhost:5173/product-admin" },
      { label: "Default email", value: "product@mastery-pulse.io" },
      { label: "Default password", value: "Welcome1! (must change on first login)" },
    ]} />

    <PASubHead>First login — forced password change</PASubHead>
    <PASteps steps={[
      "Navigate to <code>/product-admin</code> and sign in with the default credentials.",
      "A password-change screen appears immediately — the seeded account has <code>must_change_password = true</code>. All data routes return 403 until this step is completed.",
      "Enter and confirm a new password (minimum 8 characters), then click <strong>Change password</strong>.",
      "You land on the Dashboard. The 30-day rotation clock starts from this moment.",
    ]} />

    <PASubHead>30-day password rotation</PASubHead>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: PA.text }}>
      At login, if the account's last password change was more than 30 days ago — or the timestamp is missing — the server sets <code>must_change_password = true</code>. The portal immediately redirects to the change-password screen before any data is accessible.
    </p>
    <PAWarn>
      The portal has no "skip" path. Until the password is changed, every product-admin route returns 403.
    </PAWarn>
  </>
);

const guideDashboardContent = (
  <>
    <PASubHead>Stat tiles</PASubHead>
    <PABullets items={[
      "<strong>Total Plans</strong> — count of all subscription plans in the catalog.",
      "<strong>Organizations</strong> — count of all tenant organizations.",
      "<strong>Practitioners</strong> — total practitioner accounts across all orgs.",
      "<strong>Est. MRR</strong> — monthly recurring revenue estimate (per-seat prices × practitioner counts by tier).",
    ]} />

    <PASubHead>Plan distribution chart</PASubHead>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: PA.text }}>
      A bar chart beneath the tiles shows how practitioners and organizations are distributed across plan tiers (Free, Paid, Enterprise). Hover a bar to see the org count and active practitioner count for that tier.
    </p>
    <PATip>
      With the default seed data, you will see Deloitte Consulting (Enterprise Unlimited) and Free Tier (Free). All existing practitioners are backfilled into Deloitte Consulting by migration 024.
    </PATip>
  </>
);

const guidePlansContent = (
  <>
    <PASubHead>Reading the plans grid</PASubHead>
    <PABullets items={[
      "Plans are sorted alphabetically by name.",
      "Limits of <code>-1</code> display as <strong>∞ Unlimited</strong> in green — never show raw <code>-1</code> to users.",
      "The tier badge is colour-coded: purple = enterprise, blue = paid, grey = free.",
      "Feature columns (Cert Recycling, Nudges, Teams Notify) use ✓ / — symbols.",
    ]} />

    <PASubHead>Create a plan</PASubHead>
    <PASteps steps={[
      "Click <strong>+ New Plan</strong>.",
      "Fill in Name and Tier (free / paid / enterprise).",
      "For each numeric limit, enter a number <em>or</em> check <strong>Unlimited</strong> — checking sends <code>-1</code> and greys out the number input.",
      "Toggle feature flags: Allow cert recycling · Enable nudges · Teams notifications.",
      "Click <strong>Create Plan</strong>. The plan row appears in the grid immediately.",
    ]} />

    <PASubHead>Edit a plan</PASubHead>
    <PASteps steps={[
      "Click <strong>Edit</strong> on any plan row.",
      "Adjust values using the same unlimited-checkbox controls as create.",
      "Click <strong>Save</strong>.",
    ]} />
    <PAWarn>
      Edits apply to all organizations on that plan immediately. Reducing a limit below an org's current usage blocks new resource creation for affected practitioners — existing data is never deleted.
    </PAWarn>

    <PASubHead>Deactivate a plan</PASubHead>
    <PATable rows={[
      { label: "No active orgs on the plan", value: "Plan goes Inactive. Disappears from the org-creation dropdown." },
      { label: "Active orgs present", value: "409 error: <em>\"Cannot deactivate plan — N organization(s) are currently on it.\"</em> Migrate those orgs to a different plan first." },
    ]} />
  </>
);

const guideOrgsContent = (
  <>
    <PASubHead>Reading the organizations grid</PASubHead>
    <PABullets items={[
      "Organizations are sorted alphabetically by name.",
      "<strong>Plan</strong> — plan name plus a colour-coded tier badge.",
      "<strong>Practitioners</strong> — live count of practitioners assigned to the org.",
      "<strong>Code</strong> — enrollment code hidden as <code>••••••••••••••••</code>. Click <strong>👁</strong> to reveal; click <strong>🙈</strong> to hide. Only one org's code is revealed at a time.",
      "<strong>Status</strong> — Active / Inactive.",
    ]} />

    <PASubHead>Create an organization</PASubHead>
    <PASteps steps={[
      "Click <strong>+ New Organization</strong>.",
      "Enter an Organization Name.",
      "Select a Plan from the dropdown (sorted alphabetically, active plans only).",
      "Optionally enter a Billing Email.",
      "Click <strong>Create Organization</strong>.",
    ]} />
    <div style={{ background: "rgba(5,150,105,0.06)", border: "1px solid rgba(5,150,105,0.2)", borderLeft: `3px solid ${PA.success}`, borderRadius: "0 8px 8px 0", padding: "0.7rem 1rem", margin: "1rem 0", fontSize: "0.875rem", color: PA.text, lineHeight: 1.65 }}>
      <span style={{ fontWeight: 700, color: PA.success }}>✅ Expected:&nbsp;</span>
      A success screen shows the new org's enrollment code in full. Copy it with the <strong>📋 Copy</strong> button. This is the only time the code appears automatically in plaintext — after dismissing, use the eye icon on the grid row.
    </div>

    <PASubHead>Enrollment codes</PASubHead>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: PA.text }}>
      Each organization has exactly one active 16-character uppercase hex enrollment code. Practitioners enter it on the login screen (under <em>"Have an enrollment code?"</em>) to self-assign to the org on first login.
    </p>
    <PAWarn>
      Codes are immutable. An org's code cannot be edited in place. To replace it — e.g. after a security event — click <strong>↻ Code</strong> to regenerate. The previous code stops working immediately. Practitioners who have already enrolled are unaffected; only new sign-ups need the new code.
    </PAWarn>

    <PASubHead>Deactivate / reactivate an org</PASubHead>
    <PATable rows={[
      { label: "Enterprise org deactivated", value: "Enterprise-tier message shown. All active sessions for every practitioner in that org are deleted (force-logout). New logins return 403." },
      { label: "Free / Paid org deactivated", value: "Standard message. Same force-logout behaviour." },
      { label: "Reactivate", value: "Click Reactivate on the row. Practitioners can log in again immediately (new sessions required)." },
    ]} />
  </>
);

const guidePractitionersContent = (
  <>
    <PASubHead>Search</PASubHead>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: PA.text }}>
      Type into the search bar to filter in real time across <strong>name</strong>, <strong>email</strong>, and <strong>org name</strong>. The count badge (<em>12 of 847</em>) updates as you type. Clearing the field restores the full list instantly.
    </p>

    <PASubHead>Sort columns</PASubHead>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: PA.text }}>
      Click any column header — <strong>Name, Email, Org, Plan, Status</strong> — to sort ascending (▲). Click again to reverse (▼). The active column is highlighted in blue. Changing the sort resets to page 1.
    </p>

    <PASubHead>Active / Inactive filter</PASubHead>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: PA.text }}>
      The <strong>All / Active / Inactive</strong> toggle in the header filters at the API level and stacks with the search bar. For example: filter to "Active" then search "deloitte" to find active Deloitte practitioners.
    </p>

    <PASubHead>Pagination</PASubHead>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: PA.text }}>
      20 rows per page. Use <strong>«/»</strong> to jump to first/last, <strong>‹ Prev / Next ›</strong> to step through. The indicator shows <em>Page 3 of 42</em>. Searching or sorting always resets to page 1.
    </p>

    <PASubHead>Deactivate / reactivate a practitioner</PASubHead>
    <PASteps steps={[
      "Locate the practitioner (use search if needed).",
      "Click <strong>Deactivate</strong> and confirm the prompt.",
      "Status changes to Inactive. Active sessions are deleted — the practitioner is force-logged out. Future logins return 403.",
      "To restore access, click <strong>Reactivate</strong>.",
    ]} />
    <PATip>
      Deactivation is non-destructive. All profiles, quiz history, lessons, and exam records are preserved and visible again after reactivation.
    </PATip>
  </>
);

const guideAnalyticsContent = (
  <>
    <PASubHead>Usage by plan tier</PASubHead>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: PA.text }}>
      A table grouped by plan tier. Per tier: org count, total practitioners, active practitioners (logged in at least once), quiz attempts, lesson reads, mock exams completed.
    </p>

    <PASubHead>Agent performance</PASubHead>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: PA.text }}>
      One row per AI agent showing run count, failure count (highlighted red when non-zero), average latency, and P95 latency. Use this panel to spot agents with elevated error rates or latency regressions before practitioners notice.
    </p>

    <PASubHead>Plan distribution</PASubHead>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: PA.text }}>
      Org and practitioner counts per plan, plus new enrollments in the last 30 days. Useful for tracking growth and identifying which plans are driving adoption.
    </p>
    <PATip>
      All three panels load in parallel when you open the Analytics tab. If any panel is blank, check the API and browser console for errors — each panel has an independent data fetch.
    </PATip>
  </>
);

const guideSecurityContent = (
  <>
    <PASubHead>Access isolation</PASubHead>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: PA.text }}>
      The product admin portal is completely separate from the practitioner and org-admin portals. Role enforcement lives in API middleware — session tokens from other identity types cannot access these routes even if the URL is known.
    </p>

    <PASubHead>Access control checks</PASubHead>
    <PATable rows={[
      { label: "Practitioner session → product-admin route", value: "403 Product admin access required" },
      { label: "Org admin session → product-admin route", value: "403 Product admin access required" },
      { label: "must_change_password = true → any data route", value: "403 until password is changed" },
      { label: "Login 31+ days after last password change", value: "200 login; must_change_password: true in response; portal → change-password screen" },
      { label: "Deactivate org → practitioner logs in", value: "403 with org-deactivation message; all their sessions already deleted" },
      { label: "Deactivate practitioner → they log in", value: "403 account suspended; session deleted" },
      { label: "Use a retired enrollment code", value: "400 Invalid or expired enrollment code" },
      { label: "Deactivate a plan with active orgs", value: "409 with count of blocking orgs" },
      { label: "Create resource exceeding plan limit", value: "402 plan limit reached (enforced before the route handler runs)" },
    ]} />

    <PASubHead>Regression smoke-check</PASubHead>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: PA.text }}>Run from <code>backend/</code>:</p>
    <pre style={{ background: "#1e293b", color: "#e2e8f0", borderRadius: 8, padding: "1rem 1.25rem", overflowX: "auto", fontSize: "0.8rem", lineHeight: 1.65, margin: "0.75rem 0" }}>
      <code>{`py -m pytest tests/scenarios/test_phase22_multi_tenant.py -v   # 34 scenarios\npy -m pytest tests/scenarios/ -q --tb=no                       # full suite (255 tests)`}</code>
    </pre>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: PA.muted }}>Expected: zero failures.</p>
  </>
);

interface PAGuideSection {
  id: string;
  icon: string;
  title: string;
  quickRead: string;
  content: React.ReactNode;
}

const PA_GUIDE_SECTIONS: PAGuideSection[] = [
  {
    id: "g-login",
    icon: "🔐",
    title: "Login & Password",
    quickRead: "Navigate to /product-admin and sign in with product@mastery-pulse.io / Welcome1!. A password-change screen appears on first login — you cannot skip it. After you change the password, the 30-day rotation clock starts. If you log in more than 30 days later, the same screen appears again.",
    content: guideLoginContent,
  },
  {
    id: "g-dashboard",
    icon: "📊",
    title: "Dashboard",
    quickRead: "Four stat tiles show total plans, organizations, practitioners, and estimated MRR. A plan-distribution bar chart below shows how practitioners and orgs are spread across Free / Paid / Enterprise tiers.",
    content: guideDashboardContent,
  },
  {
    id: "g-plans",
    icon: "📋",
    title: "Subscription Plans",
    quickRead: "Plans grid is sorted by name. -1 limits display as ∞ Unlimited. Create plans with the unlimited checkbox per limit field. Deactivating a plan with active orgs returns 409 — migrate those orgs first.",
    content: guidePlansContent,
  },
  {
    id: "g-orgs",
    icon: "🏢",
    title: "Organizations",
    quickRead: "Orgs are sorted by name. The Code column is hidden by default — click 👁 to reveal the 16-char enrollment code. Creating an org auto-generates a code shown once in full on the success screen. Deactivating an org force-logs out all its practitioners immediately.",
    content: guideOrgsContent,
  },
  {
    id: "g-practitioners",
    icon: "👥",
    title: "Practitioners",
    quickRead: "20 rows per page. Type in the search bar to filter by name, email, or org in real time. Click any column header to sort. The Active/Inactive toggle stacks with search. Deactivating force-logs out the practitioner; all data is preserved.",
    content: guidePractitionersContent,
  },
  {
    id: "g-analytics",
    icon: "📈",
    title: "Analytics",
    quickRead: "Three panels: Usage by plan tier (quiz/lesson/exam counts), Agent performance (run/failure/latency per AI agent), and Plan distribution (orgs + practitioners per plan + new enrollments last 30 days). All panels load in parallel.",
    content: guideAnalyticsContent,
  },
  {
    id: "g-security",
    icon: "🛡️",
    title: "Security & Access",
    quickRead: "Product admin sessions are fully isolated — practitioner and org-admin tokens cannot access these routes. Force-logout fires on org or practitioner deactivation. Plan limit enforcement returns 402. Retiring an enrollment code (regenerate) invalidates the old one immediately.",
    content: guideSecurityContent,
  },
];

function GuideTab() {
  const [activeId, setActiveId] = React.useState(PA_GUIDE_SECTIONS[0].id);

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      setActiveId(id);
    }
  };

  // IntersectionObserver to track active section
  React.useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) { setActiveId(entry.target.id); break; }
        }
      },
      { root: null, rootMargin: "-80px 0px -55% 0px", threshold: 0 },
    );
    PA_GUIDE_SECTIONS.forEach((s) => {
      const el = document.getElementById(s.id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, []);

  return (
    <div style={{ display: "flex", gap: 0, minHeight: "calc(100vh - 4rem)" }}>
      {/* Inner sidebar */}
      <aside
        style={{
          width: 196,
          flexShrink: 0,
          background: PA.surface,
          border: `1px solid ${PA.border}`,
          borderRadius: 10,
          position: "sticky",
          top: "1rem",
          height: "fit-content",
          maxHeight: "calc(100vh - 6rem)",
          overflowY: "auto",
          padding: "0.5rem 0",
          marginRight: "2rem",
        }}
      >
        <div style={{ padding: "0.75rem 1rem 0.6rem", borderBottom: `1px solid ${PA.border}`, marginBottom: "0.25rem" }}>
          <div style={{ fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: PA.muted }}>
            Platform Guide
          </div>
        </div>
        {PA_GUIDE_SECTIONS.map((s) => {
          const active = activeId === s.id;
          return (
            <button
              key={s.id}
              onClick={() => scrollTo(s.id)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.45rem",
                width: "100%",
                textAlign: "left",
                padding: "0.45rem 1rem 0.45rem 0.85rem",
                fontSize: "0.83rem",
                fontWeight: active ? 700 : 400,
                color: active ? PA.text : PA.muted,
                background: active ? PA.surface : "none",
                border: "none",
                borderLeft: active ? `3px solid ${PA.accent}` : "3px solid transparent",
                cursor: "pointer",
                fontFamily: "inherit",
                lineHeight: 1.4,
                transition: "color 0.1s, border-color 0.1s",
              }}
            >
              <span style={{ opacity: 0.85, fontSize: "0.95em" }}>{s.icon}</span>
              <span>{s.title}</span>
            </button>
          );
        })}
      </aside>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0, maxWidth: 740 }}>
        <div style={{ marginBottom: "2.5rem" }}>
          <div style={{ fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: PA.muted, marginBottom: "0.35rem" }}>
            Mastery Pulse · Phase 22
          </div>
          <h1 style={{ fontSize: "1.6rem", fontWeight: 800, color: PA.text, lineHeight: 1.2, marginBottom: "0.5rem" }}>
            Product Admin Guide
          </h1>
          <p style={{ fontSize: "0.95rem", color: PA.muted, lineHeight: 1.6, maxWidth: "54ch" }}>
            Step-by-step reference for managing subscription plans, organizations, practitioners, and analytics from this portal.
          </p>
        </div>

        {PA_GUIDE_SECTIONS.map((s, idx) => (
          <section
            key={s.id}
            id={s.id}
            style={{ marginBottom: "3.5rem", scrollMarginTop: "1.5rem" }}
          >
            <PASecHeading>{s.icon} {s.title}</PASecHeading>
            <PAQuickRead text={s.quickRead} />
            <div style={{ fontSize: "0.9rem", color: PA.text, lineHeight: 1.75 }}>
              {s.content}
            </div>
            {idx < PA_GUIDE_SECTIONS.length - 1 && (
              <hr style={{ marginTop: "3rem", border: "none", borderTop: `1px solid ${PA.border}` }} />
            )}
          </section>
        ))}
      </div>
    </div>
  );
}

// ── Sidebar nav items ─────────────────────────────────────────────────────────

const NAV_ITEMS: { tab: AdminTab; label: string; icon: string }[] = [
  { tab: "dashboard", label: "Dashboard", icon: "📊" },
  { tab: "plans", label: "Plans", icon: "📋" },
  { tab: "orgs", label: "Organizations", icon: "🏢" },
  { tab: "practitioners", label: "Practitioners", icon: "👥" },
  { tab: "analytics", label: "Usage Analytics", icon: "📈" },
  { tab: "earnings", label: "Earnings", icon: "💰" },
  { tab: "guide", label: "Guide", icon: "📘" },
];

// ── Main portal ───────────────────────────────────────────────────────────────

export default function ProductAdminPortal() {
  const { session, clear } = useSession();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<AdminTab>("dashboard");

  const handleLogout = async () => {
    await productAdmin.logout();
    clear();
    navigate("/product-admin/login", { replace: true });
  };

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: PA.bg }}>
      {/* ── Sidebar ──────────────────────────────────────────────────── */}
      <aside
        style={{
          width: 228,
          flexShrink: 0,
          background: PA.sidebar,
          display: "flex",
          flexDirection: "column",
          position: "sticky",
          top: 0,
          height: "100vh",
          overflowY: "auto",
        }}
      >
        {/* Branding */}
        <div
          style={{
            padding: "1.25rem 1rem 1rem",
            borderBottom: `1px solid ${PA.sidebarBorder}`,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                background: "rgba(255,255,255,0.12)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "1rem",
                flexShrink: 0,
              }}
            >
              🛡️
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: "0.82rem", color: PA.sidebarActive, letterSpacing: "0.03em" }}>
                Product Admin
              </div>
              <div style={{ fontSize: "0.68rem", color: PA.sidebarText, opacity: 0.7 }}>
                Mastery Pulse Operations
              </div>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: "0.5rem 0" }}>
          {NAV_ITEMS.map(({ tab, label, icon }) => {
            const isActive = activeTab === tab;
            return (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.65rem",
                  width: "100%",
                  padding: "0.55rem 1rem",
                  background: isActive ? PA.sidebarActiveBg : "none",
                  border: "none",
                  borderLeft: isActive ? "3px solid rgba(241,245,249,0.7)" : "3px solid transparent",
                  color: isActive ? PA.sidebarActive : PA.sidebarText,
                  fontWeight: isActive ? 700 : 400,
                  fontSize: "0.85rem",
                  cursor: "pointer",
                  textAlign: "left",
                  fontFamily: "inherit",
                  lineHeight: 1.4,
                  transition: "background 0.12s, color 0.12s",
                }}
              >
                <span style={{ opacity: 0.9 }}>{icon}</span>
                <span>{label}</span>
              </button>
            );
          })}
        </nav>

        {/* User info + logout */}
        <div
          style={{
            padding: "0.85rem 1rem",
            borderTop: `1px solid ${PA.sidebarBorder}`,
          }}
        >
          <div style={{ fontSize: "0.75rem", color: PA.sidebarText, marginBottom: "0.5rem", opacity: 0.8 }}>
            Signed in as <strong style={{ color: PA.sidebarActive }}>{session?.first_name}</strong>
          </div>
          <button
            onClick={handleLogout}
            style={{
              width: "100%",
              padding: "0.4rem 0.75rem",
              background: "rgba(255,255,255,0.06)",
              border: `1px solid ${PA.sidebarBorder}`,
              borderRadius: 6,
              color: PA.sidebarText,
              fontSize: "0.78rem",
              cursor: "pointer",
              fontFamily: "inherit",
              textAlign: "center",
              transition: "background 0.12s",
            }}
          >
            Log out
          </button>
        </div>
      </aside>

      {/* ── Content ──────────────────────────────────────────────────── */}
      <main style={{ flex: 1, minWidth: 0, padding: "2rem clamp(1rem, 3vw, 2.5rem)", overflowX: "hidden" }}>
        {activeTab === "dashboard" && <DashboardTab />}
        {activeTab === "plans" && <PlansTab />}
        {activeTab === "orgs" && <OrgsTab />}
        {activeTab === "practitioners" && <PractitionersTab />}
        {activeTab === "analytics" && <AnalyticsTab />}
        {activeTab === "earnings" && <EarningsTab />}
        {activeTab === "guide" && <GuideTab />}
      </main>
    </div>
  );
}
