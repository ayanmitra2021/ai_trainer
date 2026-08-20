/**
 * ProductAdminLoginPage — Phase 22.7
 *
 * Slate/grey palette login page for Product Admins.
 * Calls /product-admin/login, then refreshes session and navigates to /product-admin.
 */

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { productAdmin } from "../api";
import { useSession } from "../context/SessionContext";

const PA_PRIMARY = "#334155";
const PA_BG = "#f8fafc";
const PA_SURFACE = "#ffffff";
const PA_BORDER = "#e2e8f0";
const PA_TEXT = "#1e293b";
const PA_MUTED = "#64748b";

const inputStyle: React.CSSProperties = {
  display: "block",
  width: "100%",
  padding: "0.5rem 0.75rem",
  fontSize: "0.875rem",
  border: `1px solid ${PA_BORDER}`,
  borderRadius: "6px",
  background: PA_SURFACE,
  color: PA_TEXT,
  marginBottom: "0.75rem",
  boxSizing: "border-box",
  outline: "none",
  fontFamily: "inherit",
};

const labelStyle: React.CSSProperties = {
  fontSize: "0.8125rem",
  fontWeight: 500,
  color: PA_MUTED,
  display: "block",
  marginBottom: "0.25rem",
};

export default function ProductAdminLoginPage() {
  const navigate = useNavigate();
  const { refresh } = useSession();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const resp = await productAdmin.login({ email, password });
      await refresh();
      if (resp.must_change_password) {
        navigate("/product-admin/change-password", { replace: true });
      } else {
        navigate("/product-admin", { replace: true });
      }
    } catch (err: unknown) {
      setError((err as Error).message ?? "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: PA_BG,
      }}
    >
      <div
        style={{
          width: 380,
          background: PA_SURFACE,
          border: `1px solid ${PA_BORDER}`,
          borderRadius: "12px",
          padding: "2rem",
          boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
        }}
      >
        {/* Header */}
        <div style={{ marginBottom: "1.75rem", textAlign: "center" }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: 48,
              height: 48,
              borderRadius: 12,
              background: PA_PRIMARY,
              color: "#fff",
              fontSize: "1.5rem",
              marginBottom: "0.85rem",
            }}
          >
            🛡️
          </div>
          <h1 style={{ fontSize: "1.25rem", fontWeight: 700, color: PA_TEXT, margin: 0, lineHeight: 1.3 }}>
            Product Admin Portal
          </h1>
          <p style={{ fontSize: "0.83rem", color: PA_MUTED, margin: "0.4rem 0 0" }}>
            Mastery Pulse operations access only
          </p>
        </div>

        {error && (
          <div
            style={{
              padding: "0.6rem 0.75rem",
              background: "#fef2f2",
              border: "1px solid #fca5a5",
              borderRadius: "6px",
              fontSize: "0.8125rem",
              color: "#dc2626",
              marginBottom: "1rem",
            }}
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <label style={labelStyle}>Email</label>
          <input
            style={inputStyle}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="admin@mastery-pulse.io"
            required
            autoFocus
          />
          <label style={labelStyle}>Password</label>
          <input
            style={inputStyle}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "0.625rem",
              background: loading ? "#94a3b8" : PA_PRIMARY,
              color: "#fff",
              border: "none",
              borderRadius: "6px",
              fontSize: "0.9rem",
              fontWeight: 600,
              cursor: loading ? "not-allowed" : "pointer",
              marginTop: "0.5rem",
              transition: "background 0.15s",
              fontFamily: "inherit",
            }}
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
