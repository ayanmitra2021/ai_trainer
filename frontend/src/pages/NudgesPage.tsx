import { useState, useEffect } from "react";
import { useSession } from "../context/SessionContext";
import {
  useGenerateNudgeCategories,
  useNudgeCategories,
  useSendNudges,
  useSentCampaigns,
} from "../hooks";
import type { ComposePreviewResponse, NudgeCategory, OrgNotificationSettings, RecipientPreview, SentCampaignSummary } from "../api/types";
import { notificationSettings, pulse } from "../api";

// ── Section 1 & 2: Category selection ────────────────────────────────────────

function CategoryCard({
  cat,
  isSelected,
  onSelect,
}: {
  cat: NudgeCategory;
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <div
      className="card"
      style={{
        border: isSelected ? "2px solid var(--primary)" : undefined,
        cursor: "pointer",
      }}
      onClick={onSelect}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, marginBottom: "0.25rem" }}>
            {cat.title || cat.description.slice(0, 50)}
          </div>
          <p style={{ margin: 0, fontSize: "0.875rem", color: "var(--text-muted)" }}>
            {cat.description}
          </p>
          {cat.tone_hint && (
            <p style={{ margin: "0.5rem 0 0", fontSize: "0.8125rem", fontStyle: "italic", color: "var(--text-muted)" }}>
              Tone: {cat.tone_hint}
            </p>
          )}
        </div>
        {cat.estimated_reach != null && (
          <span className="badge badge-blue" style={{ marginLeft: "1rem", flexShrink: 0 }}>
            ~{cat.estimated_reach} recipients
          </span>
        )}
      </div>
    </div>
  );
}

// ── Section 3: Recipient table ────────────────────────────────────────────────

function RecipientTable({
  recipients,
  excluded,
  onToggle,
}: {
  recipients: RecipientPreview[];
  excluded: Set<string>;
  onToggle: (id: string) => void;
}) {
  const allChecked = recipients.every((r) => !excluded.has(r.id));
  const selectedCount = recipients.filter((r) => !excluded.has(r.id)).length;

  const toggleAll = () => {
    if (allChecked) {
      recipients.forEach((r) => onToggle(r.id));
    } else {
      recipients.filter((r) => excluded.has(r.id)).forEach((r) => onToggle(r.id));
    }
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
        <span style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>
          <strong>{selectedCount}</strong> of {recipients.length} practitioners selected
        </span>
        <button className="btn btn-outline" style={{ fontSize: "0.8125rem" }} onClick={toggleAll}>
          {allChecked ? "Deselect all" : "Select all"}
        </button>
      </div>
      <div style={{ maxHeight: 280, overflowY: "auto", border: "1px solid var(--border)", borderRadius: "0.5rem" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "var(--surface-alt, #f9fafb)" }}>
              <th style={{ padding: "0.5rem 0.75rem", textAlign: "left", fontSize: "0.8125rem", fontWeight: 600 }}>Include</th>
              <th style={{ padding: "0.5rem 0.75rem", textAlign: "left", fontSize: "0.8125rem", fontWeight: 600 }}>Name</th>
              <th style={{ padding: "0.5rem 0.75rem", textAlign: "left", fontSize: "0.8125rem", fontWeight: 600 }}>Email</th>
              <th style={{ padding: "0.5rem 0.75rem", textAlign: "left", fontSize: "0.8125rem", fontWeight: 600 }}>Profile</th>
            </tr>
          </thead>
          <tbody>
            {recipients.map((r) => (
              <tr
                key={r.id}
                style={{
                  borderTop: "1px solid var(--border)",
                  opacity: excluded.has(r.id) ? 0.45 : 1,
                }}
              >
                <td style={{ padding: "0.5rem 0.75rem" }}>
                  <input
                    type="checkbox"
                    checked={!excluded.has(r.id)}
                    onChange={() => onToggle(r.id)}
                  />
                </td>
                <td style={{ padding: "0.5rem 0.75rem", fontSize: "0.875rem" }}>{r.name}</td>
                <td style={{ padding: "0.5rem 0.75rem", fontSize: "0.875rem", color: "var(--text-muted)" }}>{r.email}</td>
                <td style={{ padding: "0.5rem 0.75rem", fontSize: "0.8125rem", color: "var(--text-muted)" }}>{r.action_profile_summary}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Sent history panel ────────────────────────────────────────────────────────

function SentHistoryPanel({ campaigns }: { campaigns: SentCampaignSummary[] }) {
  const [open, setOpen] = useState(false);
  if (campaigns.length === 0) return null;
  return (
    <div className="card" style={{ marginTop: "1.5rem" }}>
      <button
        className="btn btn-outline"
        style={{ width: "100%", textAlign: "left" }}
        onClick={() => setOpen((o) => !o)}
      >
        {open ? "▾" : "▸"} Previous nudge campaigns ({campaigns.length})
      </button>
      {open && (
        <div style={{ marginTop: "1rem" }}>
          {campaigns.map((c, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "0.5rem 0",
                borderTop: i > 0 ? "1px solid var(--border)" : undefined,
                fontSize: "0.875rem",
              }}
            >
              <div>
                <strong>{c.category_title || "Custom campaign"}</strong>
                {c.subject && (
                  <span style={{ color: "var(--text-muted)", marginLeft: "0.5rem" }}>
                    — {c.subject}
                  </span>
                )}
              </div>
              <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", color: "var(--text-muted)", fontSize: "0.8125rem" }}>
                <span>{c.recipient_count} sent</span>
                <span>{new Date(c.sent_at).toLocaleDateString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main NudgesPage ────────────────────────────────────────────────────────────

export default function NudgesPage() {
  const { session } = useSession();
  const isLeadership = session?.admin_role === "leadership";

  const generateCategories = useGenerateNudgeCategories();
  const { data: savedCategories } = useNudgeCategories();

  const [selectedCat, setSelectedCat] = useState<NudgeCategory | null>(null);
  const [customDesc, setCustomDesc] = useState("");
  const [recipients, setRecipients] = useState<RecipientPreview[]>([]);
  const [excluded, setExcluded] = useState<Set<string>>(new Set());
  const [compose, setCompose] = useState<ComposePreviewResponse | null>(null);
  const [editSubject, setEditSubject] = useState("");
  const [editBody, setEditBody] = useState("");
  const [sending, setSending] = useState(false);
  const [sentBanner, setSentBanner] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [composeLoading, setComposeLoading] = useState(false);

  const sendNudges = useSendNudges();
  const { data: sentCampaigns } = useSentCampaigns();

  // Phase 22.11: Teams section state
  const isEnterprise = session?.plan_tier === "enterprise";
  const [orgNotifSettings, setOrgNotifSettings] = useState<OrgNotificationSettings | null>(null);
  const [teamsMsg, setTeamsMsg] = useState("");
  const [teamsSending, setTeamsSending] = useState(false);
  const [teamsSuccess, setTeamsSuccess] = useState(false);
  const [teamsError, setTeamsError] = useState<string | null>(null);

  useEffect(() => {
    if (!isEnterprise) return;
    notificationSettings.get().then(setOrgNotifSettings).catch(() => {});
  }, [isEnterprise]);

  const hasTeams = !!orgNotifSettings?.teams_webhook_url;

  const handleSendTeams = async () => {
    if (!teamsMsg.trim()) return;
    setTeamsSending(true);
    setTeamsSuccess(false);
    setTeamsError(null);
    try {
      await pulse.sendTeamsMessage(teamsMsg);
      setTeamsSuccess(true);
      setTeamsMsg("");
    } catch (err: unknown) {
      setTeamsError((err as Error).message ?? "Failed to send Teams message");
    } finally {
      setTeamsSending(false);
    }
  };

  // Display categories: generated + saved
  const displayCategories = generateCategories.data || savedCategories || [];

  const handleSelectCategory = async (cat: NudgeCategory) => {
    setSelectedCat(cat);
    setCompose(null);
    setSentBanner(null);
    setExcluded(new Set());
    setPreviewLoading(true);
    try {
      const preview = await pulse.previewRecipients(cat.id);
      setRecipients(preview.recipients);
    } catch {
      setRecipients([]);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleCompose = async () => {
    if (!selectedCat) return;
    setComposeLoading(true);
    try {
      const result = await pulse.composeCampaign(selectedCat.id);
      setCompose(result);
      setEditSubject(result.subject);
      setEditBody(result.body);
    } finally {
      setComposeLoading(false);
    }
  };

  const handleCustomApply = async () => {
    if (!customDesc.trim()) return;
    // Synthesize a local category object for the UI flow
    const fakeCat: NudgeCategory = {
      id: "custom-" + Date.now(),
      title: "Custom",
      description: customDesc,
      criteria: { custom_description: customDesc },
      is_custom: true,
      created_at: new Date().toISOString(),
    };
    setSelectedCat(fakeCat);
    setPreviewLoading(true);
    try {
      const allResult = await pulse.previewRecipients(fakeCat.id).catch(() => ({ recipients: [], total: 0 }));
      setRecipients(allResult.recipients);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleToggleExclude = (id: string) => {
    setExcluded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSend = async () => {
    if (!selectedCat) return;
    const included = recipients.filter((r) => !excluded.has(r.id));
    if (!window.confirm(`Send nudge to ${included.length} practitioners?`)) return;
    setSending(true);
    try {
      const result = await sendNudges.mutateAsync({
        category_id: selectedCat.id,
        message_subject: editSubject,
        message_body: editBody,
        recipient_overrides: [...excluded].map((id) => ({ practitioner_id: id, include: false })),
      });
      setSentBanner(`Sent to ${result.sent_count} practitioners`);
      setSelectedCat(null);
      setCompose(null);
      setRecipients([]);
    } finally {
      setSending(false);
    }
  };

  const selectedCount = recipients.filter((r) => !excluded.has(r.id)).length;

  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: "2rem 1rem" }}>
      <h1>Nudge Campaigns</h1>
      <p style={{ color: "var(--text-muted)", marginBottom: "2rem" }}>
        Generate contextual nudge categories from real usage data, then review and send
        targeted, encouraging messages to practitioners.
      </p>

      {sentBanner && (
        <div className="card" style={{ background: "var(--success, #d1fae5)", marginBottom: "1.5rem", color: "#065f46" }}>
          {sentBanner}
        </div>
      )}

      {/* Section 1 — Generate categories */}
      <section style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>1. Generate nudge categories</h2>
        <button
          className="btn btn-primary"
          disabled={generateCategories.isPending || isLeadership}
          title={isLeadership ? "Admins only" : undefined}
          onClick={() => generateCategories.mutate()}
        >
          {generateCategories.isPending ? <><span className="spinner" /> Generating...</> : "Generate Nudge Categories"}
        </button>
        {isLeadership && (
          <span style={{ marginLeft: "0.75rem", fontSize: "0.8125rem", color: "var(--text-muted)" }}>
            (Admins only)
          </span>
        )}
        {displayCategories.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.625rem", marginTop: "1rem" }}>
            {displayCategories.map((cat) => (
              <CategoryCard
                key={cat.id}
                cat={cat}
                isSelected={selectedCat?.id === cat.id}
                onSelect={() => !isLeadership && handleSelectCategory(cat)}
              />
            ))}
          </div>
        )}
      </section>

      {/* Section 2 — Custom category */}
      {!isLeadership && (
        <section style={{ marginBottom: "2rem" }}>
          <h2 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>2. Or describe your own category</h2>
          <div style={{ display: "flex", gap: "0.75rem" }}>
            <input
              className="input"
              style={{ flex: 1 }}
              placeholder="e.g. Practitioners who haven't started their certification path"
              value={customDesc}
              onChange={(e) => setCustomDesc(e.target.value)}
            />
            <button
              className="btn btn-outline"
              disabled={!customDesc.trim()}
              onClick={handleCustomApply}
            >
              Apply
            </button>
          </div>
        </section>
      )}

      {/* Section 3 — Recipient table */}
      {selectedCat && (
        <section style={{ marginBottom: "2rem" }}>
          <h2 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>3. Matching practitioners</h2>
          {previewLoading ? (
            <div style={{ textAlign: "center", padding: "2rem" }}><span className="spinner" /></div>
          ) : recipients.length === 0 ? (
            <div className="empty-state">No practitioners match this category.</div>
          ) : (
            <RecipientTable
              recipients={recipients}
              excluded={excluded}
              onToggle={handleToggleExclude}
            />
          )}
        </section>
      )}

      {/* Section 4 — Compose message */}
      {selectedCat && recipients.length > 0 && !isLeadership && (
        <section style={{ marginBottom: "2rem" }}>
          <h2 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>4. Compose message</h2>
          {!compose && (
            <button className="btn btn-outline" disabled={composeLoading} onClick={handleCompose}>
              {composeLoading ? <><span className="spinner" /> Composing...</> : "Generate message"}
            </button>
          )}
          {compose && (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <div>
                <label style={{ fontSize: "0.8125rem", fontWeight: 600 }}>Subject</label>
                <input
                  className="input"
                  style={{ width: "100%", marginTop: "0.25rem" }}
                  value={editSubject}
                  onChange={(e) => setEditSubject(e.target.value)}
                />
              </div>
              <div>
                <label style={{ fontSize: "0.8125rem", fontWeight: 600 }}>Body</label>
                <textarea
                  className="input"
                  style={{ width: "100%", minHeight: 160, marginTop: "0.25rem", resize: "vertical" }}
                  value={editBody}
                  onChange={(e) => setEditBody(e.target.value)}
                />
              </div>
              <p style={{ fontSize: "0.8125rem", fontStyle: "italic", color: "var(--text-muted)", margin: 0 }}>
                Tone check: {compose.tone_check}
              </p>
              {isEnterprise && hasTeams && (
                <div
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "0.35rem",
                    padding: "0.3rem 0.7rem",
                    borderRadius: 999,
                    background: "rgba(34,197,94,0.1)",
                    border: "1px solid rgba(34,197,94,0.3)",
                    fontSize: "0.78rem",
                    fontWeight: 600,
                    color: "#15803d",
                  }}
                >
                  Will deliver via 📧 Email + 💬 Teams
                </div>
              )}
              <button className="btn btn-outline" style={{ alignSelf: "flex-start" }} onClick={handleCompose}>
                Regenerate message
              </button>
            </div>
          )}
        </section>
      )}

      {/* Section 5 — Send */}
      {compose && !isLeadership && (
        <section style={{ marginBottom: "2rem" }}>
          <h2 style={{ fontSize: "1rem", marginBottom: "0.75rem" }}>5. Send</h2>
          <button
            className="btn btn-primary"
            disabled={sending || selectedCount === 0}
            onClick={handleSend}
          >
            {sending ? <><span className="spinner" /> Sending...</> : `Send nudge to ${selectedCount} practitioners`}
          </button>
        </section>
      )}

      {/* Sent history */}
      {sentCampaigns && <SentHistoryPanel campaigns={sentCampaigns} />}

      {/* Phase 22.11: Teams direct message — enterprise + Teams configured only */}
      {isEnterprise && hasTeams && (
        <section style={{ marginTop: "2.5rem", paddingTop: "2rem", borderTop: "1px solid var(--border)" }}>
          <h2 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>📤 Send message directly to Teams</h2>
          <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", marginBottom: "0.75rem" }}>
            Post a standalone message to your organisation's Teams channel (outside a nudge campaign).
          </p>
          <div>
            <textarea
              className="input"
              style={{ width: "100%", minHeight: 100, resize: "vertical", boxSizing: "border-box" }}
              maxLength={1000}
              placeholder="Type your Teams message here…"
              value={teamsMsg}
              onChange={(e) => { setTeamsMsg(e.target.value); setTeamsSuccess(false); setTeamsError(null); }}
            />
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textAlign: "right", marginBottom: "0.5rem" }}>
              {teamsMsg.length}/1000
            </div>
            <button
              className="btn btn-primary"
              disabled={teamsSending || !teamsMsg.trim()}
              onClick={handleSendTeams}
            >
              {teamsSending ? <><span className="spinner" /> Sending…</> : "Send to Teams"}
            </button>
            {teamsSuccess && (
              <div
                style={{
                  marginTop: "0.75rem",
                  padding: "0.6rem 0.9rem",
                  borderRadius: 8,
                  background: "#d1fae5",
                  color: "#065f46",
                  fontSize: "0.875rem",
                  fontWeight: 600,
                }}
              >
                ✅ Message sent to Teams channel
              </div>
            )}
            {teamsError && (
              <div
                style={{
                  marginTop: "0.75rem",
                  padding: "0.6rem 0.9rem",
                  borderRadius: 8,
                  background: "#fef2f2",
                  color: "#dc2626",
                  fontSize: "0.875rem",
                }}
              >
                {teamsError}
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
