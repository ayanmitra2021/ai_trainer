/**
 * ChangePasswordPage — Step 5.2
 *
 * Forced first-login password change for admins.
 * Blocks all other navigation until completed.
 * Shown when must_change_password is true immediately after admin login.
 */

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { auth } from "../api";
import { useSession } from "../context/SessionContext";

const inputStyle: React.CSSProperties = {
  display: "block",
  width: "100%",
  padding: "0.5rem 0.75rem",
  fontSize: "0.875rem",
  border: "1px solid var(--border)",
  borderRadius: "6px",
  background: "var(--surface)",
  color: "var(--text)",
  marginBottom: "0.75rem",
  boxSizing: "border-box",
};

const labelStyle: React.CSSProperties = {
  fontSize: "0.8125rem",
  fontWeight: 500,
  color: "var(--text-muted)",
  display: "block",
  marginBottom: "0.25rem",
};

const btnStyle: React.CSSProperties = {
  width: "100%",
  padding: "0.625rem",
  background: "var(--primary)",
  color: "#fff",
  border: "none",
  borderRadius: "6px",
  fontSize: "0.9rem",
  fontWeight: 600,
  cursor: "pointer",
  marginTop: "0.5rem",
};

export default function ChangePasswordPage() {
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
      await auth.changePassword({
        current_password: currentPw,
        new_password: newPw,
      });
      // Refresh session so must_change_password reflects the cleared state
      await refresh();
      navigate("/");
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
        background: "var(--bg)",
      }}
    >
      <div
        style={{
          width: 380,
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "12px",
          padding: "2rem",
          boxShadow: "var(--shadow)",
        }}
      >
        <h1 style={{ fontSize: "1.25rem", fontWeight: 700, marginBottom: "0.25rem" }}>
          Set your password
        </h1>
        <p
          style={{
            fontSize: "0.875rem",
            color: "var(--text-muted)",
            marginBottom: "1.5rem",
          }}
        >
          Your account is set up with a temporary password. Choose a new one to continue.
        </p>

        {error && (
          <p
            style={{
              fontSize: "0.8125rem",
              color: "#ef4444",
              marginBottom: "1rem",
              padding: "0.5rem",
              background: "#fef2f2",
              borderRadius: "4px",
            }}
          >
            {error}
          </p>
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
          <button style={btnStyle} type="submit" disabled={loading}>
            {loading ? "Saving…" : "Set password & continue"}
          </button>
        </form>
      </div>
    </div>
  );
}
