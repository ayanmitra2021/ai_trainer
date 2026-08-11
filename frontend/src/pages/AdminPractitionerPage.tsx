/**
 * AdminPractitionerPage — Step 9.2.
 *
 * Read-only view of a single practitioner for Admin / Leadership users.
 * Displays:
 *   1. A read-only profile panel (name, cert code + full name, date last saved).
 *   2. The Skill Radar in read-only mode — no "Regenerate path", no "Edit profile →".
 *
 * There is deliberately no tab strip — only the Skill Radar is shown.
 * Route: /admin/practitioners/:id  (RequireAdmin-guarded in App.tsx)
 */

import { Link, useParams } from "react-router-dom";
import {
  useCertifications,
  usePractitioner,
  useProfiles,
} from "../hooks";
import SkillRadar from "../components/SkillRadar";

export default function AdminPractitionerPage() {
  const { id = "" } = useParams<{ id: string }>();

  const { data: person, isLoading: personLoading } = usePractitioner(id);
  const { data: profilesList, isLoading: profilesLoading } = useProfiles(id);
  const { data: certifications } = useCertifications();

  const activeProfile = profilesList?.find((p) => p.is_active);
  const certFull = certifications?.find(
    (c) => c.id === activeProfile?.certification_id,
  );

  if (personLoading || profilesLoading) {
    return (
      <div style={{ textAlign: "center", padding: "4rem" }}>
        <span className="spinner" />
      </div>
    );
  }

  if (!person) {
    return (
      <div style={{ maxWidth: 600, margin: "3rem auto", padding: "0 1rem" }}>
        <div className="card">
          <p>Practitioner not found.</p>
          <Link to="/">← Back to list</Link>
        </div>
      </div>
    );
  }

  const initial = person.name.trim()[0]?.toUpperCase() ?? "P";

  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: "2rem 1rem" }}>
      {/* ── Back link + page header ────────────────────────────────────── */}
      <div style={{ marginBottom: "1.5rem" }}>
        <Link
          to="/"
          style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}
        >
          ← All practitioners
        </Link>
        <h1 style={{ marginTop: "0.5rem", marginBottom: "0.25rem" }}>
          {person.name}
        </h1>
        <p
          style={{
            color: "var(--text-muted)",
            margin: 0,
            fontSize: "0.875rem",
          }}
        >
          {[person.email, person.role, person.practice, person.seniority_level]
            .filter(Boolean)
            .join(" · ")}
        </p>
      </div>

      {/* ── Read-only profile panel ────────────────────────────────────── */}
      {activeProfile ? (
        <div
          data-testid="readonly-profile-panel"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.875rem",
            padding: "0.875rem 1rem",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderLeft: "3px solid var(--primary)",
            borderRadius: "8px",
            marginBottom: "1.5rem",
            boxShadow: "0 0 20px rgba(77, 171, 247, 0.06)",
          }}
        >
          {/* Avatar */}
          <div
            style={{
              width: 38,
              height: 38,
              borderRadius: "50%",
              background: "var(--primary)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              fontWeight: 700,
              fontSize: "1rem",
              flexShrink: 0,
              boxShadow: "0 0 12px rgba(77, 171, 247, 0.4)",
            }}
          >
            {initial}
          </div>

          {/* Profile details */}
          <div style={{ flex: 1, minWidth: 0 }}>
            {/* Profile name + cert badge */}
            <div
              style={{
                fontWeight: 600,
                fontSize: "0.9rem",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                flexWrap: "wrap",
              }}
            >
              <span data-testid="profile-name">{activeProfile.name}</span>
              {activeProfile.certification_code && (
                <span
                  data-testid="cert-code"
                  style={{
                    fontSize: "0.7rem",
                    padding: "0.15rem 0.5rem",
                    borderRadius: "999px",
                    background: "var(--primary)",
                    color: "#fff",
                    fontWeight: 600,
                    letterSpacing: "0.03em",
                  }}
                >
                  {activeProfile.certification_code}
                </span>
              )}
            </div>

            {/* Full cert name */}
            {certFull && (
              <div
                style={{
                  fontSize: "0.8125rem",
                  color: "var(--text-muted)",
                  marginTop: "0.15rem",
                }}
              >
                <span data-testid="cert-full-name">{certFull.name}</span>
              </div>
            )}

            {/* Last saved date */}
            <div
              style={{
                fontSize: "0.75rem",
                color: "var(--text-muted)",
                marginTop: "0.2rem",
              }}
            >
              Last saved:{" "}
              {new Date(activeProfile.updated_at).toLocaleDateString()}
            </div>
          </div>

          {/* Read-only badge */}
          <span
            style={{
              flexShrink: 0,
              fontSize: "0.7rem",
              padding: "0.2rem 0.6rem",
              borderRadius: "999px",
              background: "rgba(77, 171, 247, 0.12)",
              color: "var(--primary)",
              fontWeight: 600,
              border: "1px solid rgba(77, 171, 247, 0.3)",
            }}
          >
            Read-only
          </span>
        </div>
      ) : (
        <div
          data-testid="readonly-profile-panel"
          className="card"
          style={{
            marginBottom: "1.5rem",
            color: "var(--text-muted)",
            fontSize: "0.875rem",
          }}
        >
          No active profile for this practitioner.
        </div>
      )}

      {/* ── Skill Radar — read-only, no tab strip ─────────────────────── */}
      <div data-testid="skill-radar-section">
        <SkillRadar practitionerId={id} readOnly />
      </div>
    </div>
  );
}
