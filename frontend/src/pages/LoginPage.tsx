/**
 * LoginPage — Step 5.2 (updated Phase 7)
 *
 * Practitioner form field order: email → name → role → practice → seniority level.
 * On email blur, calls GET /auth/lookup-email — if the email is already in the DB
 * all other fields are pre-filled (user can still edit/override them).
 *
 * Admin toggle reveals a separate email + password form.
 */

import React, { useRef, useState } from "react";
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

  // Practitioner fields
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [practice, setPractice] = useState("");
  const [seniorityLevel, setSeniorityLevel] = useState("");
  const [prefilled, setPrefilled] = useState(false);
  const [lookingUp, setLookingUp] = useState(false);

  // Enrollment code (Phase 22) — collapsible
  const [showCodeField, setShowCodeField] = useState(false);
  const [enrollmentCode, setEnrollmentCode] = useState("");

  // Admin fields
  const [adminEmail, setAdminEmail] = useState("");
  const [password, setPassword] = useState("");

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Track the last email we looked up so we don't repeat the same call
  const lastLookedUpEmail = useRef("");

  const handleEmailBlur = async () => {
    const trimmed = email.trim().toLowerCase();
    if (!trimmed || trimmed === lastLookedUpEmail.current) return;
    lastLookedUpEmail.current = trimmed;

    setLookingUp(true);
    try {
      const result = await auth.lookupEmail(trimmed);
      if (result.found) {
        setName(result.name);
        setRole(result.role);
        setPractice(result.practice);
        setSeniorityLevel(result.seniority_level);
        setPrefilled(true);
      } else {
        setPrefilled(false);
      }
    } catch {
      // Lookup failure is non-fatal — user can still fill the form manually
    } finally {
      setLookingUp(false);
    }
  };

  const handlePractitionerLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await auth.practitionerLogin({
        name,
        email: email.trim().toLowerCase(),
        role,
        practice,
        seniority_level: seniorityLevel,
        ...(enrollmentCode.trim() ? { enrollment_code: enrollmentCode.trim().toUpperCase() } : {}),
      });
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
      const res = await auth.adminLogin({ email: adminEmail, password });
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
        <h1 style={{ fontSize: "1.375rem", fontWeight: 700, marginBottom: "0.25rem" }}>
          Mastery Pulse
        </h1>
        <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", marginBottom: "1.5rem" }}>
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

            {/* ── Email first so lookup can fire on blur ── */}
            <label style={labelStyle}>Work email *</label>
            <div style={{ position: "relative", marginBottom: "0.75rem" }}>
              <input
                style={{ ...inputStyle, marginBottom: 0, paddingRight: lookingUp ? "2rem" : undefined }}
                type="email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  // Reset prefill state when the email changes
                  if (e.target.value.trim().toLowerCase() !== lastLookedUpEmail.current) {
                    setPrefilled(false);
                  }
                }}
                onBlur={handleEmailBlur}
                placeholder="you@example.com"
                required
                autoComplete="email"
              />
              {lookingUp && (
                <span
                  style={{
                    position: "absolute",
                    right: "0.625rem",
                    top: "50%",
                    transform: "translateY(-50%)",
                    fontSize: "0.75rem",
                    color: "var(--text-muted)",
                  }}
                >
                  <span className="spinner" style={{ width: 12, height: 12 }} />
                </span>
              )}
            </div>

            {prefilled && (
              <p
                style={{
                  fontSize: "0.75rem",
                  color: "var(--primary)",
                  margin: "-0.25rem 0 0.75rem",
                }}
              >
                ✓ Fields pre-filled from your account — update anything that's changed.
              </p>
            )}

            {/* ── Name ── */}
            <label style={labelStyle}>Full name *</label>
            <input
              style={inputStyle}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Alex Rivera"
              required
              autoComplete="name"
            />

            {/* ── Role ── */}
            <label style={labelStyle}>Role (optional)</label>
            <input
              style={inputStyle}
              value={role}
              onChange={(e) => setRole(e.target.value)}
              placeholder="e.g. Solutions Architect"
            />

            {/* ── Practice ── */}
            <label style={labelStyle}>Practice (optional)</label>
            <input
              style={inputStyle}
              value={practice}
              onChange={(e) => setPractice(e.target.value)}
              placeholder="e.g. Cloud & Infrastructure"
            />

            {/* ── Seniority level ── */}
            <label style={labelStyle}>Seniority level (optional)</label>
            <input
              style={inputStyle}
              value={seniorityLevel}
              onChange={(e) => setSeniorityLevel(e.target.value)}
              placeholder="e.g. Senior, Manager, Director"
            />

            {/* ── Enrollment code (collapsible) ── */}
            <div style={{ marginTop: "0.25rem", marginBottom: "0.75rem" }}>
              <button
                type="button"
                onClick={() => {
                  setShowCodeField((v) => !v);
                  if (showCodeField) setEnrollmentCode("");
                }}
                style={{
                  background: "none",
                  border: "none",
                  padding: 0,
                  fontSize: "0.8125rem",
                  color: "var(--primary)",
                  cursor: "pointer",
                  textDecoration: "underline",
                  fontFamily: "inherit",
                }}
              >
                {showCodeField ? "▲ Hide enrollment code" : "▼ Have an enrollment code?"}
              </button>
              {showCodeField && (
                <div style={{ marginTop: "0.5rem" }}>
                  <label style={labelStyle}>Enrollment code</label>
                  <input
                    style={inputStyle}
                    value={enrollmentCode}
                    onChange={(e) => setEnrollmentCode(e.target.value)}
                    placeholder="e.g. ABCD1234EFGH5678"
                    maxLength={16}
                    autoComplete="off"
                    spellCheck={false}
                  />
                  <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", margin: "-0.5rem 0 0" }}>
                    Enter the 16-character code from your organisation administrator to join their workspace.
                    Leave blank to continue on the free plan.
                  </p>
                </div>
              )}
            </div>

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
              value={adminEmail}
              onChange={(e) => setAdminEmail(e.target.value)}
              placeholder="admin@example.com"
              required
              autoComplete="email"
            />
            <label style={labelStyle}>Password</label>
            <input
              style={inputStyle}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
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
