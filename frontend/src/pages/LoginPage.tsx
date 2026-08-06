/**
 * LoginPage — Step 5.2
 *
 * Landing page. Default: practitioner form (name, email, org level).
 * Toggle "I'm an admin / leadership member" reveals the admin form (email + password).
 *
 * On success, the session is refreshed and the router redirects the user:
 *   - practitioner → /practitioners/:id/skills  (their own tabs)
 *   - admin with must_change_password → /change-password
 *   - admin (normal) → /  (full practitioners list + admin nav)
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

export default function LoginPage() {
  const navigate = useNavigate();
  const { refresh } = useSession();

  const [isAdmin, setIsAdmin] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [orgLevel, setOrgLevel] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handlePractitionerLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await auth.practitionerLogin({ name, email, org_level: orgLevel });
      await refresh();
      navigate(`/practitioners/${res.practitioner_id}/skills`);
    } catch (err: unknown) {
      setError((err as Error).message ?? "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const handleAdminLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await auth.adminLogin({ email, password });
      await refresh();
      if (res.must_change_password) {
        navigate("/change-password");
      } else {
        navigate("/");
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
        <h1
          style={{
            fontSize: "1.375rem",
            fontWeight: 700,
            marginBottom: "0.25rem",
          }}
        >
          Mastery Pulse
        </h1>
        <p
          style={{
            fontSize: "0.875rem",
            color: "var(--text-muted)",
            marginBottom: "1.5rem",
          }}
        >
          {isAdmin ? "Admin / leadership sign-in" : "Welcome — enter your details to continue"}
        </p>

        {/* Admin toggle */}
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            fontSize: "0.8125rem",
            color: "var(--text-muted)",
            marginBottom: "1.25rem",
            cursor: "pointer",
          }}
        >
          <input
            type="checkbox"
            checked={isAdmin}
            onChange={(e) => {
              setIsAdmin(e.target.checked);
              setError(null);
            }}
          />
          I'm an admin / leadership member
        </label>

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

        {!isAdmin ? (
          <form onSubmit={handlePractitionerLogin}>
            <label style={labelStyle}>Full name</label>
            <input
              style={inputStyle}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Alex Rivera"
              required
            />
            <label style={labelStyle}>Work email</label>
            <input
              style={inputStyle}
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
            />
            <label style={labelStyle}>Org level (optional)</label>
            <input
              style={inputStyle}
              value={orgLevel}
              onChange={(e) => setOrgLevel(e.target.value)}
              placeholder="e.g. Senior Consultant"
            />
            <button style={btnStyle} type="submit" disabled={loading}>
              {loading ? "Signing in…" : "Continue"}
            </button>
          </form>
        ) : (
          <form onSubmit={handleAdminLogin}>
            <label style={labelStyle}>Email</label>
            <input
              style={inputStyle}
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@example.com"
              required
            />
            <label style={labelStyle}>Password</label>
            <input
              style={inputStyle}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <button style={btnStyle} type="submit" disabled={loading}>
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
