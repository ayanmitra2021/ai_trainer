/**
 * NotificationConfigPage — Phase 22.10
 *
 * Enterprise-only page for configuring Teams/email notification settings.
 * Visible only when session.identity_type === "admin" and plan_tier === "enterprise".
 */

import React, { useState, useEffect } from "react";
import { useSession } from "../context/SessionContext";
import { notificationSettings } from "../api";
import type { OrgNotificationSettings } from "../api/types";

// ── Loading skeleton ───────────────────────────────────────────────────────────

function SettingsSkeleton() {
  return (
    <div style={{ opacity: 0.5, padding: "2rem 1rem" }}>
      <div style={{ height: 20, background: "var(--border)", borderRadius: 4, width: "40%", marginBottom: "1rem" }} />
      <div style={{ height: 14, background: "var(--border)", borderRadius: 4, width: "70%", marginBottom: "0.5rem" }} />
      <div style={{ height: 14, background: "var(--border)", borderRadius: 4, width: "50%", marginBottom: "1.5rem" }} />
      <div style={{ height: 40, background: "var(--border)", borderRadius: 6, marginBottom: "0.75rem" }} />
    </div>
  );
}

// ── Teams section ──────────────────────────────────────────────────────────────

function TeamsSection({
  settings,
  onSaved,
}: {
  settings: OrgNotificationSettings;
  onSaved: (updated: OrgNotificationSettings) => void;
}) {
  const [webhookUrl, setWebhookUrl] = useState(settings.teams_webhook_url ?? "");
  const [channelName, setChannelName] = useState(settings.teams_channel_name ?? "");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [saveErr, setSaveErr] = useState<string | null>(null);
  const [testMsg, setTestMsg] = useState<string | null>(null);
  const [testErr, setTestErr] = useState<string | null>(null);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaveMsg(null);
    setSaveErr(null);
    try {
      const updated = await notificationSettings.update({
        teams_webhook_url: webhookUrl || null,
        teams_channel_name: channelName || null,
      });
      onSaved(updated);
      setSaveMsg("Settings saved.");
    } catch (err: unknown) {
      setSaveErr((err as Error).message ?? "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestMsg(null);
    setTestErr(null);
    try {
      const result = await notificationSettings.testTeams();
      if (result.success) {
        setTestMsg("✅ Test card delivered — check your Teams channel.");
      } else {
        setTestErr(result.error ?? "Test failed");
      }
    } catch (err: unknown) {
      setTestErr((err as Error).message ?? "Test failed");
    } finally {
      setTesting(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    width: "100%",
    padding: "0.5rem 0.75rem",
    fontSize: "0.875rem",
    border: "1px solid var(--border)",
    borderRadius: "6px",
    background: "var(--surface)",
    color: "var(--text)",
    boxSizing: "border-box",
    fontFamily: "inherit",
    marginBottom: "0.75rem",
  };

  return (
    <div className="card" style={{ marginBottom: "1.5rem" }}>
      <h2 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "0.4rem" }}>💬 Teams Integration</h2>
      <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", marginBottom: "1.25rem" }}>
        Connect a Microsoft Teams channel to receive nudge campaigns and direct messages.
      </p>

      <form onSubmit={handleSave}>
        <label style={{ fontSize: "0.8125rem", fontWeight: 500, color: "var(--text-muted)", display: "block", marginBottom: "0.25rem" }}>
          Webhook URL
        </label>
        <input
          style={inputStyle}
          type="url"
          placeholder="https://outlook.office.com/webhook/…"
          value={webhookUrl}
          onChange={(e) => setWebhookUrl(e.target.value)}
        />

        <label style={{ fontSize: "0.8125rem", fontWeight: 500, color: "var(--text-muted)", display: "block", marginBottom: "0.25rem" }}>
          Channel name (display only)
        </label>
        <input
          style={inputStyle}
          type="text"
          placeholder="e.g. mastery-pulse-nudges"
          value={channelName}
          onChange={(e) => setChannelName(e.target.value)}
        />

        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "center" }}>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={saving}
          >
            {saving ? <><span className="spinner" /> Saving…</> : "Save"}
          </button>
          <button
            type="button"
            className="btn btn-outline"
            disabled={testing || !webhookUrl.trim()}
            onClick={handleTest}
          >
            {testing ? <><span className="spinner" /> Testing…</> : "Test Connection"}
          </button>
        </div>
      </form>

      {saveMsg && (
        <p style={{ marginTop: "0.75rem", fontSize: "0.8125rem", color: "#059669", fontWeight: 600 }}>
          {saveMsg}
        </p>
      )}
      {saveErr && (
        <p style={{ marginTop: "0.75rem", fontSize: "0.8125rem", color: "#dc2626" }}>{saveErr}</p>
      )}
      {testMsg && (
        <p style={{ marginTop: "0.75rem", fontSize: "0.8125rem", color: "#059669", fontWeight: 600 }}>
          {testMsg}
        </p>
      )}
      {testErr && (
        <p style={{ marginTop: "0.75rem", fontSize: "0.8125rem", color: "#dc2626" }}>{testErr}</p>
      )}
    </div>
  );
}

// ── Email section ──────────────────────────────────────────────────────────────

function EmailSection({
  settings,
  onSaved,
}: {
  settings: OrgNotificationSettings;
  onSaved: (updated: OrgNotificationSettings) => void;
}) {
  const [emailEnabled, setEmailEnabled] = useState(settings.email_enabled);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);
  const [saveErr, setSaveErr] = useState<string | null>(null);

  const handleSave = async () => {
    setSaving(true);
    setSaveMsg(null);
    setSaveErr(null);
    try {
      const updated = await notificationSettings.update({ email_enabled: emailEnabled });
      onSaved(updated);
      setSaveMsg("Settings saved.");
    } catch (err: unknown) {
      setSaveErr((err as Error).message ?? "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card">
      <h2 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "0.4rem" }}>📧 Email Notifications</h2>
      <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", marginBottom: "1.25rem" }}>
        Toggle email delivery for nudge campaigns. Disable if your org prefers Teams-only delivery.
      </p>

      <label
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
          cursor: "pointer",
          marginBottom: "1rem",
        }}
      >
        <input
          type="checkbox"
          checked={emailEnabled}
          onChange={(e) => setEmailEnabled(e.target.checked)}
          style={{ width: 18, height: 18, cursor: "pointer" }}
        />
        <span style={{ fontSize: "0.9rem", fontWeight: 500 }}>
          Enable email nudges for practitioners
        </span>
      </label>

      <button
        className="btn btn-primary"
        disabled={saving}
        onClick={handleSave}
      >
        {saving ? <><span className="spinner" /> Saving…</> : "Save"}
      </button>

      {saveMsg && (
        <p style={{ marginTop: "0.75rem", fontSize: "0.8125rem", color: "#059669", fontWeight: 600 }}>
          {saveMsg}
        </p>
      )}
      {saveErr && (
        <p style={{ marginTop: "0.75rem", fontSize: "0.8125rem", color: "#dc2626" }}>{saveErr}</p>
      )}
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function NotificationConfigPage() {
  const { session } = useSession();
  const [settings, setSettings] = useState<OrgNotificationSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadErr, setLoadErr] = useState<string | null>(null);

  const isEnterprise = session?.plan_tier === "enterprise";

  useEffect(() => {
    if (!isEnterprise) return;
    notificationSettings
      .get()
      .then(setSettings)
      .catch((err: unknown) => setLoadErr((err as Error).message ?? "Failed to load settings"))
      .finally(() => setLoading(false));
  }, [isEnterprise]);

  if (!isEnterprise) {
    return (
      <div style={{ maxWidth: 640, margin: "3rem auto", padding: "0 1rem" }}>
        <div
          style={{
            padding: "1.5rem",
            background: "rgba(100,116,139,0.08)",
            border: "1px solid var(--border)",
            borderRadius: 10,
            textAlign: "center",
            color: "var(--text-muted)",
          }}
        >
          🔒 Notification configuration is available on the Enterprise plan. Contact your product admin to upgrade.
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: "2rem 1rem" }}>
      <h1 style={{ fontSize: "1.5rem", fontWeight: 800, marginBottom: "0.4rem" }}>Notification Settings</h1>
      <p style={{ color: "var(--text-muted)", marginBottom: "2rem", fontSize: "0.9rem" }}>
        Configure Teams integration and email delivery for nudge campaigns.
      </p>

      {loading && <SettingsSkeleton />}

      {loadErr && (
        <div
          style={{
            padding: "1rem",
            background: "#fef2f2",
            border: "1px solid #fca5a5",
            borderRadius: 8,
            color: "#dc2626",
            fontSize: "0.875rem",
          }}
        >
          {loadErr}
        </div>
      )}

      {settings && (
        <>
          <TeamsSection settings={settings} onSaved={setSettings} />
          <EmailSection settings={settings} onSaved={setSettings} />
        </>
      )}
    </div>
  );
}
