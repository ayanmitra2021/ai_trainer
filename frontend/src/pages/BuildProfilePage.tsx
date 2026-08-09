/**
 * BuildProfilePage — Phase 6.3
 *
 * The default post-login page for practitioners. Shows existing profiles as cards
 * and lets them create new ones via the ProfileWizard.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSession } from "../context/SessionContext";
import {
  useActivateProfile,
  useDeleteProfile,
  useProfiles,
} from "../hooks";
import ProfileWizard from "../components/ProfileBuilder/ProfileWizard";

export default function BuildProfilePage() {
  const { session } = useSession();
  const practitionerId = session?.practitioner_id ?? "";
  const { data: profileList, isLoading } = useProfiles(practitionerId);
  const activateProfile = useActivateProfile(practitionerId);
  const deleteProfile = useDeleteProfile(practitionerId);
  const navigate = useNavigate();

  const [showWizard, setShowWizard] = useState(false);
  const [editProfileId, setEditProfileId] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div style={{ padding: "3rem", textAlign: "center" }}>
        <span className="spinner" />
      </div>
    );
  }

  const hasProfiles = profileList && profileList.length > 0;

  const handleWizardComplete = (profileId: string) => {
    setShowWizard(false);
    setEditProfileId(null);
    navigate(`/profile/${profileId}/skills`);
  };

  const handleEdit = (profileId: string) => {
    setEditProfileId(profileId);
    setShowWizard(true);
  };

  const handleActivate = async (profileId: string) => {
    await activateProfile.mutateAsync(profileId);
  };

  const handleDeleteConfirm = async (profileId: string) => {
    await deleteProfile.mutateAsync(profileId);
    setDeleteConfirmId(null);
  };

  if (showWizard) {
    return (
      <div style={{ maxWidth: 680, margin: "0 auto", padding: "1.5rem" }}>
        <ProfileWizard
          practitionerId={practitionerId}
          editProfileId={editProfileId}
          onComplete={handleWizardComplete}
          onCancel={() => { setShowWizard(false); setEditProfileId(null); }}
        />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "1.5rem" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1.5rem",
          flexWrap: "wrap",
          gap: "0.75rem",
        }}
      >
        <div>
          <h1 style={{ margin: 0 }}>My Profiles</h1>
          <p style={{ color: "var(--text-muted)", margin: "0.25rem 0 0", fontSize: "0.875rem" }}>
            Each profile captures your background, cert goal, and skill self-assessment.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => { setEditProfileId(null); setShowWizard(true); }}>
          + New profile
        </button>
      </div>

      {!hasProfiles ? (
        <div className="empty-state" style={{ padding: "4rem 2rem" }}>
          <h2 style={{ marginBottom: "0.5rem" }}>Build your first profile</h2>
          <p style={{ color: "var(--text-muted)", marginBottom: "1.5rem", maxWidth: 480, margin: "0 auto 1.5rem" }}>
            A profile links your background, a certification goal, and your skill self-assessment together.
            The Skill Radar and Quiz then read from your active profile.
          </p>
          <button className="btn btn-primary btn-lg" onClick={() => setShowWizard(true)}>
            Start →
          </button>
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
            gap: "1rem",
          }}
        >
          {profileList.map((profile) => (
            <div
              key={profile.id}
              className="card"
              style={{
                position: "relative",
                border: profile.is_active ? "2px solid var(--primary)" : undefined,
              }}
            >
              {profile.is_active && (
                <span
                  className="badge badge-blue"
                  style={{ position: "absolute", top: "0.75rem", right: "0.75rem" }}
                >
                  Active
                </span>
              )}
              <h3 style={{ margin: "0 0 0.375rem", paddingRight: "4rem" }}>{profile.name}</h3>
              <p style={{ margin: "0 0 0.5rem", fontSize: "0.875rem", color: "var(--text-muted)" }}>
                {profile.certification_code
                  ? `Certification: ${profile.certification_code}`
                  : "No certification chosen"}
              </p>

              {profile.mastery_pct != null && (
                <div style={{ marginBottom: "0.75rem" }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      fontSize: "0.75rem",
                      color: "var(--text-muted)",
                      marginBottom: "0.25rem",
                    }}
                  >
                    <span>Cert mastery</span>
                    <span>{(profile.mastery_pct * 100).toFixed(0)}%</span>
                  </div>
                  <div className="progress">
                    <div
                      className="progress-bar"
                      style={{ width: `${(profile.mastery_pct ?? 0) * 100}%` }}
                    />
                  </div>
                </div>
              )}

              <p style={{ margin: "0 0 1rem", fontSize: "0.8125rem", color: "var(--text-muted)" }}>
                Created {new Date(profile.created_at).toLocaleDateString()}
              </p>

              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                {!profile.is_active && (
                  <button
                    className="btn btn-outline"
                    style={{ fontSize: "0.8125rem" }}
                    disabled={activateProfile.isPending}
                    onClick={() => handleActivate(profile.id)}
                  >
                    Activate
                  </button>
                )}
                <button
                  className="btn btn-outline"
                  style={{ fontSize: "0.8125rem" }}
                  onClick={() => handleEdit(profile.id)}
                >
                  Edit
                </button>
                {deleteConfirmId === profile.id ? (
                  <>
                    <button
                      className="btn btn-outline"
                      style={{ fontSize: "0.8125rem", color: "var(--danger)", borderColor: "var(--danger)" }}
                      disabled={deleteProfile.isPending}
                      onClick={() => handleDeleteConfirm(profile.id)}
                    >
                      {deleteProfile.isPending ? "Deleting…" : "Confirm delete"}
                    </button>
                    <button
                      className="btn btn-outline"
                      style={{ fontSize: "0.8125rem" }}
                      onClick={() => setDeleteConfirmId(null)}
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <button
                    className="btn btn-outline"
                    style={{ fontSize: "0.8125rem", color: "var(--danger)", borderColor: "var(--danger)" }}
                    disabled={profile.is_active && profileList.length === 1}
                    title={profile.is_active ? "Activate another profile first" : "Delete this profile"}
                    onClick={() => setDeleteConfirmId(profile.id)}
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
