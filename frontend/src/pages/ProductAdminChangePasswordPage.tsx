/**
 * ProductAdminChangePasswordPage — Phase 22.7
 *
 * Forced first-login password change for product admins.
 * Calls /product-admin/change-password instead of the regular admin endpoint.
 */

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { productAdmin } from "../api";
import { useSession } from "../context/SessionContext";

const PA_PRIMARY = "#334155";
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
  fontFamily: "inherit",
};

const labelStyle: React.CSSProperties = {
  fontSize: "0.8125rem",
  fontWeight: 500,
  color: PA_MUTED,
  display: "block",
  marginBottom: "0.25rem",
};

export default function ProductAdminChangePasswordPage() {
  const navigate = useNavigate();
  const { refresh } = useSession();

  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (newPw !== confirmPw) {
      setError("New passwords do not match");
      return;
    }
    if (newPw.length < 8) {
      setError("New password must be at least 8 characters");
      return;
    }

    setLoading(true);
    try {
      await productAdmin.changePassword({ current_password: currentPw, new_password: newPw });
      await refresh();
      navigate("/product-admin", { replace: true });
    } catch (err: unknown) {
      setError((err as Error).message ?? "Password change failed");
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
        background: "#f8fafc",
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
        <h1 style={{ fontSize: "1.25rem", fontWeight: 700, color: PA_TEXT, marginBottom: "0.25rem" }}>
          Set your password
        </h1>
        <p style={{ fontSize: "0.875rem", color: PA_MUTED, marginBottom: "1.5rem" }}>
          Your account is set up with a temporary password. Choose a new one to continue.
        </p>

        {error && (
          <div
            style={{
              padding: "0.5rem 0.75rem",
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
          <label style={labelStyle}>Current password</label>
          <input
            style={inputStyle}
            type="password"
            value={currentPw}
            onChange={(e) => setCurrentPw(e.target.value)}
            required
          />
          <label style={labelStyle}>New password</label>
          <input
            style={inputStyle}
            type="password"
            value={newPw}
            onChange={(e) => setNewPw(e.target.value)}
            placeholder="At least 8 characters"
            required
          />
          <label style={labelStyle}>Confirm new password</label>
          <input
            style={inputStyle}
            type="password"
            value={confirmPw}
            onChange={(e) => setConfirmPw(e.target.value)}
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
              fontFamily: "inherit",
            }}
          >
            {loading ? "Saving…" : "Set password & continue"}
          </button>
        </form>
      </div>
    </div>
  );
}
