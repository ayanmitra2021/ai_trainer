/**
 * ProfileSkillAssessmentPage — Phase 6.5
 *
 * After the wizard saves a profile, the practitioner rates their skills here.
 * Cert-relevant skills appear first (Tier 1); all other skills below (Tier 2).
 */

import { useNavigate, useParams } from "react-router-dom";
import { useSession } from "../context/SessionContext";
import { useCertifications, useProfile, useUpsertProfileSkills } from "../hooks";
import ProfileSkillRater from "../components/ProfileBuilder/ProfileSkillRater";
import type { ProfileSkillUpsert } from "../api/types";

export default function ProfileSkillAssessmentPage() {
  const { profileId } = useParams<{ profileId: string }>();
  const { session } = useSession();
  const practitionerId = session?.practitioner_id ?? "";
  const navigate = useNavigate();

  const { data: profile, isLoading: profileLoading } = useProfile(practitionerId, profileId ?? "");
  const { data: certList } = useCertifications();
  const upsertSkills = useUpsertProfileSkills(practitionerId, profileId ?? "");

  if (profileLoading) {
    return (
      <div style={{ padding: "3rem", textAlign: "center" }}>
        <span className="spinner" />
      </div>
    );
  }

  if (!profile) {
    return <div className="card" style={{ margin: "2rem" }}>Profile not found.</div>;
  }

  const certSkillIds = new Set<string>();
  if (profile.certification_id && certList) {
    const cert = certList.find((c) => c.id === profile.certification_id);
    cert?.certification_skills.forEach((cs) => certSkillIds.add(cs.skill_id));
  }

  const existingRatings = Object.fromEntries(
    (profile.skill_assessments ?? []).map((sa) => [sa.skill_id, sa.signal_strength])
  );

  const handleSave = async (ratings: Record<string, number>) => {
    const body: ProfileSkillUpsert = {
      assessments: Object.entries(ratings).map(([skill_id, signal_strength]) => ({
        skill_id,
        signal_strength,
      })),
    };
    await upsertSkills.mutateAsync(body);
    navigate("/profile", { state: { toast: "Profile saved and activated!" } });
  };

  return (
    <div style={{ maxWidth: 780, margin: "0 auto", padding: "1.5rem" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ margin: "0 0 0.25rem" }}>Rate your skills</h1>
        <p style={{ color: "var(--text-muted)", margin: 0, fontSize: "0.875rem" }}>
          Profile: <strong>{profile.name}</strong>
          {profile.certification_code && (
            <> · Targeting <strong>{profile.certification_code}</strong></>
          )}
        </p>
      </div>

      <ProfileSkillRater
        certificationId={profile.certification_id}
        certSkillIds={certSkillIds}
        initialRatings={existingRatings}
        onSave={handleSave}
        isSaving={upsertSkills.isPending}
      />
    </div>
  );
}
