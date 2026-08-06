import React, { useEffect, useState } from "react";
import { adminUsers } from "../api";
import type { AdminUserResponse } from "../api/types";
import { ApiError } from "../api/client";

const pageStyle: React.CSSProperties = {
  maxWidth: "860px",
  margin: "0 auto",
  padding: "2rem 1.5rem",
};

const headerRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  marginBottom: "1.5rem",
};

const cardStyle: React.CSSProperties = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: "8px",
  overflow: "hidden",
  boxShadow: "var(--shadow)",
};

const tableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: "0.875rem",
};

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "0.75rem 1rem",
  borderBottom: "1px solid var(--border)",
  fontWeight: 600,
  color: "var(--text-muted)",
  fontSize: "0.75rem",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  background: "var(--surface-alt, var(--surface))",
};

const tdStyle: React.CSSProperties = {
  padding: "0.75rem 1rem",
  borderBottom: "1px solid var(--border)",
  color: "var(--text)",
  verticalAlign: "middle",
};

const badgeStyle = (role: string): React.CSSProperties => ({
  display: "inline-block",
  padding: "0.2rem 0.55rem",
  borderRadius: "999px",
  fontSize: "0.75rem",
  fontWeight: 600,
  background: role === "admin" ? "var(--primary-muted, #e0e7ff)" : "#f0fdf4",
  color: role === "admin" ? "var(--primary, #4f46e5)" : "#166534",
});

const warnBadgeStyle: React.CSSProperties = {
  display: "inline-block",
  padding: "0.2rem 0.55rem",
  borderRadius: "999px",
  fontSize: "0.75rem",
  fontWeight: 600,
  background: "#fef9c3",
  color: "#854d0e",
};

const btnPrimaryStyle: React.CSSProperties = {
  padding: "0.5rem 1.1rem",
  borderRadius: "6px",
  border: "none",
  background: "var(--primary, #4f46e5)",
  color: "#fff",
  fontWeight: 600,
  fontSize: "0.875rem",
  cursor: "pointer",
};

const btnDangerStyle: React.CSSProperties = {
  padding: "0.25rem 0.7rem",
  borderRadius: "5px",
  border: "1px solid #fca5a5",
  background: "transparent",
  color: "#dc2626",
  fontSize: "0.8125rem",
  cursor: "pointer",
};

// ── Add user modal ─────────────────────────────────────────────────────────────

interface AddUserModalProps {
  onClose: () => void;
  onCreated: (user: AdminUserResponse) => void;
}

function AddUserModal({ onClose, onCreated }: AddUserModalProps) {
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [role, setRole] = useState<"admin" | "leadership">("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const created = await adminUsers.create({
        email,
        first_name: firstName,
        role,
        temporary_password: password,
      });
      onCreated(created);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Unexpected error. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const overlayStyle: React.CSSProperties = {
    position: "fixed",
    inset: 0,
    background: "rgba(0,0,0,0.45)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 100,
  };

  const modalStyle: React.CSSProperties = {
    background: "var(--surface)",
    border: "1px solid var(--border)",
    borderRadius: "10px",
    padding: "2rem",
    width: "100%",
    maxWidth: "420px",
    boxShadow: "0 20px 40px rgba(0,0,0,0.2)",
  };

  const fieldStyle: React.CSSProperties = {
    display: "flex",
    flexDirection: "column",
    gap: "0.375rem",
    marginBottom: "1rem",
  };

  const labelStyle: React.CSSProperties = {
    fontSize: "0.8125rem",
    fontWeight: 600,
    color: "var(--text)",
  };

  const inputStyle: React.CSSProperties = {
    padding: "0.5rem 0.75rem",
    border: "1px solid var(--border)",
    borderRadius: "5px",
    fontSize: "0.875rem",
    background: "var(--surface)",
    color: "var(--text)",
  };

  const selectStyle: React.CSSProperties = { ...inputStyle };

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        <h2 style={{ marginTop: 0, marginBottom: "1.25rem", fontSize: "1.1rem" }}>
          Add admin user
        </h2>

        <form onSubmit={handleSubmit}>
          <div style={fieldStyle}>
            <label style={labelStyle}>First name</label>
            <input
              style={inputStyle}
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              required
              placeholder="e.g. Jamie"
            />
          </div>

          <div style={fieldStyle}>
            <label style={labelStyle}>Email</label>
            <input
              style={inputStyle}
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="jamie@example.com"
            />
          </div>

          <div style={fieldStyle}>
            <label style={labelStyle}>Role</label>
            <select
              style={selectStyle}
              value={role}
              onChange={(e) => setRole(e.target.value as "admin" | "leadership")}
            >
              <option value="admin">Admin — full access</option>
              <option value="leadership">Leadership — aggregates only</option>
            </select>
          </div>

          <div style={fieldStyle}>
            <label style={labelStyle}>Temporary password</label>
            <input
              style={inputStyle}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              placeholder="Min 8 characters"
            />
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              The user must change this on first login.
            </span>
          </div>

          {error && (
            <p style={{ color: "#dc2626", fontSize: "0.875rem", margin: "0 0 1rem" }}>
              {error}
            </p>
          )}

          <div style={{ display: "flex", gap: "0.75rem", justifyContent: "flex-end" }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                ...btnPrimaryStyle,
                background: "transparent",
                color: "var(--text-muted)",
                border: "1px solid var(--border)",
              }}
            >
              Cancel
            </button>
            <button type="submit" style={btnPrimaryStyle} disabled={submitting}>
              {submitting ? "Creating…" : "Create user"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUserResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    adminUsers
      .list()
      .then(setUsers)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load users"))
      .finally(() => setLoading(false));
  }, []);

  const handleCreated = (user: AdminUserResponse) => {
    setUsers((prev) => [...prev, user]);
    setShowModal(false);
  };

  const handleDelete = async (id: string, email: string) => {
    if (!window.confirm(`Remove ${email}? This cannot be undone.`)) return;
    setDeletingId(id);
    try {
      await adminUsers.delete(id);
      setUsers((prev) => prev.filter((u) => u.id !== id));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Delete failed");
    } finally {
      setDeletingId(null);
    }
  };

  const formatDate = (iso: string | null) => {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  if (loading) {
    return (
      <div style={{ padding: "2rem", color: "var(--text-muted)" }}>Loading…</div>
    );
  }

  return (
    <div style={pageStyle}>
      {showModal && (
        <AddUserModal
          onClose={() => setShowModal(false)}
          onCreated={handleCreated}
        />
      )}

      <div style={headerRowStyle}>
        <div>
          <h1 style={{ margin: 0, fontSize: "1.4rem" }}>Admin users</h1>
          <p style={{ margin: "0.25rem 0 0", color: "var(--text-muted)", fontSize: "0.875rem" }}>
            Manage admin and leadership accounts.
          </p>
        </div>
        <button style={btnPrimaryStyle} onClick={() => setShowModal(true)}>
          + Add user
        </button>
      </div>

      {error && (
        <p style={{ color: "#dc2626", marginBottom: "1rem" }}>{error}</p>
      )}

      <div style={cardStyle}>
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>Name</th>
              <th style={thStyle}>Email</th>
              <th style={thStyle}>Role</th>
              <th style={thStyle}>Status</th>
              <th style={thStyle}>Last login</th>
              <th style={thStyle}>Created</th>
              <th style={thStyle}></th>
            </tr>
          </thead>
          <tbody>
            {users.length === 0 && (
              <tr>
                <td colSpan={7} style={{ ...tdStyle, color: "var(--text-muted)", textAlign: "center" }}>
                  No admin users yet.
                </td>
              </tr>
            )}
            {users.map((u) => (
              <tr key={u.id}>
                <td style={tdStyle}>{u.first_name}</td>
                <td style={tdStyle}>{u.email}</td>
                <td style={tdStyle}>
                  <span style={badgeStyle(u.role)}>{u.role}</span>
                </td>
                <td style={tdStyle}>
                  {u.must_change_password ? (
                    <span style={warnBadgeStyle}>Pending password change</span>
                  ) : (
                    <span style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>Active</span>
                  )}
                </td>
                <td style={{ ...tdStyle, color: "var(--text-muted)" }}>
                  {formatDate(u.last_login_at)}
                </td>
                <td style={{ ...tdStyle, color: "var(--text-muted)" }}>
                  {formatDate(u.created_at)}
                </td>
                <td style={tdStyle}>
                  <button
                    style={btnDangerStyle}
                    disabled={deletingId === u.id}
                    onClick={() => handleDelete(u.id, u.email)}
                  >
                    {deletingId === u.id ? "…" : "Remove"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
