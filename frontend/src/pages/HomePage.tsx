import { useState } from "react";
import { Link } from "react-router-dom";
import { useCreatePractitioner, usePractitioners } from "../hooks";
import type { PractitionerCreate } from "../api/types";

const shell: React.CSSProperties = {
  maxWidth: 860,
  margin: "0 auto",
  padding: "2rem 1rem",
};

const grid: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
  gap: "1rem",
  marginTop: "1.5rem",
};

export default function HomePage() {
  const { data: people, isLoading, isError } = usePractitioners();
  const create = useCreatePractitioner();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<PractitionerCreate>({
    name: "",
    email: "",
    role: "",
    practice: "",
    seniority_level: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await create.mutateAsync({
      name: form.name,
      email: form.email,
      role: form.role || undefined,
      practice: form.practice || undefined,
      seniority_level: form.seniority_level || undefined,
    });
    setShowForm(false);
    setForm({ name: "", email: "", role: "", practice: "", seniority_level: "" });
  };

  return (
    <div style={shell}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap" }}>
        <div>
          <h1 style={{ margin: 0 }}>Practitioners</h1>
          <p style={{ color: "var(--text-muted)", margin: "0.25rem 0 0" }}>
            Select a practitioner to view their profile.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ Add practitioner"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="card" style={{ marginTop: "1.25rem" }}>
          <h3 style={{ marginBottom: "1rem" }}>New practitioner</h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div className="form-group">
              <label htmlFor="name">Name *</label>
              <input
                id="name"
                className="form-control"
                required
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              />
            </div>
            <div className="form-group">
              <label htmlFor="email">Email *</label>
              <input
                id="email"
                type="email"
                className="form-control"
                required
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              />
            </div>
            <div className="form-group">
              <label htmlFor="role">Role</label>
              <input
                id="role"
                className="form-control"
                value={form.role}
                onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
              />
            </div>
            <div className="form-group">
              <label htmlFor="practice">Practice</label>
              <input
                id="practice"
                className="form-control"
                value={form.practice}
                onChange={(e) => setForm((f) => ({ ...f, practice: e.target.value }))}
              />
            </div>
            <div className="form-group">
              <label htmlFor="seniority">Seniority level</label>
              <input
                id="seniority"
                className="form-control"
                value={form.seniority_level}
                onChange={(e) => setForm((f) => ({ ...f, seniority_level: e.target.value }))}
              />
            </div>
          </div>
          <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.5rem" }}>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={create.isPending}
            >
              {create.isPending ? <span className="spinner" /> : null}
              Create
            </button>
          </div>
          {create.isError && (
            <p style={{ color: "var(--danger)", marginTop: "0.75rem", marginBottom: 0, fontSize: "0.875rem" }}>
              {(create.error as Error).message}
            </p>
          )}
        </form>
      )}

      {isLoading && (
        <div style={{ textAlign: "center", padding: "3rem" }}>
          <span className="spinner" />
        </div>
      )}

      {isError && (
        <div className="card" style={{ marginTop: "1.25rem", color: "var(--danger)" }}>
          Could not load practitioners. Is the backend running?
        </div>
      )}

      {people && people.length === 0 && !showForm && (
        <div className="empty-state" style={{ marginTop: "2rem" }}>
          <p>No practitioners yet.</p>
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>
            Add the first one
          </button>
        </div>
      )}

      {people && people.length > 0 && (
        <div style={grid}>
          {people.map((p) => (
            <Link
              key={p.id}
              to={`/practitioners/${p.id}/skills`}
              style={{ textDecoration: "none", color: "inherit" }}
            >
              <div
                className="card"
                style={{ cursor: "pointer", transition: "border-color 0.15s" }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.borderColor = "var(--primary)")
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.borderColor = "var(--border)")
                }
              >
                <div style={{ fontWeight: 600, marginBottom: "0.25rem" }}>
                  {p.name}
                </div>
                <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
                  {p.email}
                </div>
                {(p.role || p.practice) && (
                  <div
                    style={{
                      fontSize: "0.8125rem",
                      color: "var(--text-muted)",
                      marginTop: "0.5rem",
                    }}
                  >
                    {[p.role, p.practice].filter(Boolean).join(" · ")}
                  </div>
                )}
                {p.seniority_level && (
                  <span
                    className="badge badge-blue"
                    style={{ marginTop: "0.75rem" }}
                  >
                    {p.seniority_level}
                  </span>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
