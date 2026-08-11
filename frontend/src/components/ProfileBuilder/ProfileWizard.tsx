/**
 * ProfileWizard — Phase 6.4
 *
 * Multi-step wizard: About you → Certification choice → Confirm.
 * Creates (or updates) a PractitionerProfile at the end of Step 3.
 */

import React, { useState } from "react";
import {
  useAdviseMutation,
  useCertifications,
  useCreateProfile,
  useProfile,
  useUpdateProfile,
} from "../../hooks";
import type { AdvisorOutput, QuestionnaireAnswers } from "../../api/types";

interface Props {
  practitionerId: string;
  editProfileId: string | null;
  onComplete: (profileId: string) => void;
  onCancel: () => void;
}

const STEPS = ["About you", "Certification", "Confirm"];

function ProgressBar({ step, total }: { step: number; total: number }) {
  return (
    <div style={{ marginBottom: "1.5rem" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: "0.5rem",
        }}
      >
        {STEPS.map((label, i) => (
          <span
            key={i}
            style={{
              fontSize: "0.8125rem",
              fontWeight: i === step ? 600 : 400,
              color: i === step ? "var(--primary)" : i < step ? "var(--text)" : "var(--text-muted)",
            }}
          >
            {i + 1}. {label}
          </span>
        ))}
      </div>
      <div className="progress">
        <div
          className="progress-bar"
          style={{ width: `${((step + 1) / total) * 100}%`, transition: "width 0.3s ease" }}
        />
      </div>
    </div>
  );
}

export default function ProfileWizard({ practitionerId, editProfileId, onComplete, onCancel }: Props) {
  const [step, setStep] = useState(0);
  const [profileName, setProfileName] = useState("");
  const [answers, setAnswers] = useState<Partial<QuestionnaireAnswers>>({
    writes_code: false,
    focus_area: "building",
    experience_level: "some",
  });
  const [selectedCertId, setSelectedCertId] = useState<string | null>(null);
  const [selectedCertCode, setSelectedCertCode] = useState<string | null>(null);
  const [recommendation, setRecommendation] = useState<AdvisorOutput | null>(null);

  const { data: certList } = useCertifications();
  const adviseMutation = useAdviseMutation();
  const createProfile = useCreateProfile(practitionerId);
  const updateProfile = useUpdateProfile(practitionerId);
  const { data: existingProfile } = useProfile(practitionerId, editProfileId ?? "");

  // Pre-populate from existing profile when in edit mode.
  // Phase 9.3: if the profile is locked, bail out immediately — BuildProfilePage
  // replaces "Edit" with "View" for locked profiles, but this guard covers any
  // code path that might still reach the wizard with a locked profile_id.
  React.useEffect(() => {
    if (editProfileId && existingProfile) {
      if (existingProfile.is_locked) {
        // Locked profile: close the wizard and let the parent handle the toast.
        onCancel();
        return;
      }
      setProfileName(existingProfile.name);
      if (existingProfile.questionnaire_snapshot) {
        setAnswers(existingProfile.questionnaire_snapshot as Partial<QuestionnaireAnswers>);
      }
      if (existingProfile.certification_id) {
        setSelectedCertId(existingProfile.certification_id);
        setSelectedCertCode(existingProfile.certification_code ?? null);
      }
    }
  }, [editProfileId, existingProfile, onCancel]);

  const handleGetRecommendation = async () => {
    const fullAnswers: QuestionnaireAnswers = {
      writes_code: answers.writes_code ?? false,
      focus_area: answers.focus_area ?? "building",
      experience_level: answers.experience_level ?? "some",
      provider_preference: answers.provider_preference ?? null,
      ai_experience_years: answers.ai_experience_years ?? null,
      primary_job_role: answers.primary_job_role ?? null,
      deploys_llms_in_production: answers.deploys_llms_in_production ?? null,
      prompt_engineering_familiarity: answers.prompt_engineering_familiarity ?? null,
      mentors_others_on_ai: answers.mentors_others_on_ai ?? null,
    };

    try {
      const result = await adviseMutation.mutateAsync({
        practitioner_id: practitionerId,
        answers: fullAnswers,
      });

      setRecommendation(result.recommendation);

      // Pre-select the recommended cert
      const recCert = certList?.find(
        (c) => c.code === result.recommendation.primary_recommendation_code
      );
      if (recCert) {
        setSelectedCertId(recCert.id);
        setSelectedCertCode(recCert.code);
      }
    } catch {
      // adviseMutation.isError + adviseMutation.error are now set — displayed below
    }
  };

  const handleFinish = async () => {
    const snapshot = {
      writes_code: answers.writes_code ?? false,
      focus_area: answers.focus_area ?? "building",
      experience_level: answers.experience_level ?? "some",
      provider_preference: answers.provider_preference ?? null,
      ai_experience_years: answers.ai_experience_years ?? null,
      primary_job_role: answers.primary_job_role ?? null,
      deploys_llms_in_production: answers.deploys_llms_in_production ?? null,
      prompt_engineering_familiarity: answers.prompt_engineering_familiarity ?? null,
      mentors_others_on_ai: answers.mentors_others_on_ai ?? null,
    };

    if (editProfileId) {
      await updateProfile.mutateAsync({
        profile_id: editProfileId,
        body: {
          name: profileName,
          certification_id: selectedCertId ?? undefined,
          questionnaire_snapshot: snapshot,
        },
      });
      onComplete(editProfileId);
    } else {
      const newProfile = await createProfile.mutateAsync({
        name: profileName,
        certification_id: selectedCertId ?? undefined,
        questionnaire_snapshot: snapshot,
      });
      onComplete(newProfile.id);
    }
  };

  const certsByProvider = React.useMemo(() => {
    if (!certList) return {} as Record<string, NonNullable<typeof certList>>;
    return certList.reduce<Record<string, NonNullable<typeof certList>>>((acc, cert) => {
      const key = cert.provider.name;
      if (!acc[key]) acc[key] = [];
      acc[key].push(cert);
      return acc;
    }, {});
  }, [certList]);

  // ── Step 1: About you ──────────────────────────────────────────────────────

  const step1Valid = profileName.trim().length > 0;

  const renderStep1 = () => (
    <div>
      <h2>About you</h2>
      <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
        Tell us about your background so we can recommend the right certification path.
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
        <div>
          <label className="form-label">Profile name *</label>
          <input
            className="form-control"
            type="text"
            placeholder="e.g. My AWS path, CCAF prep 2026"
            value={profileName}
            onChange={(e) => setProfileName(e.target.value)}
          />
        </div>

        <div>
          <label className="form-label">Do you write code?</label>
          <div style={{ display: "flex", gap: "0.75rem" }}>
            {(["Yes", "No"] as const).map((opt) => (
              <label key={opt} style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}>
                <input
                  type="radio"
                  name="writes_code"
                  checked={answers.writes_code === (opt === "Yes")}
                  onChange={() => setAnswers((a) => ({ ...a, writes_code: opt === "Yes" }))}
                />
                {opt}
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="form-label">What is your primary day-to-day focus?</label>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {(["advising", "building", "architecting"] as const).map((opt) => (
              <label key={opt} style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}>
                <input
                  type="radio"
                  name="focus_area"
                  checked={answers.focus_area === opt}
                  onChange={() => setAnswers((a) => ({ ...a, focus_area: opt }))}
                />
                {opt.charAt(0).toUpperCase() + opt.slice(1)}
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="form-label">Experience level with AI/ML</label>
          <select
            className="form-control"
            value={answers.experience_level ?? "some"}
            onChange={(e) => setAnswers((a) => ({ ...a, experience_level: e.target.value as "new" | "some" | "experienced" }))}
          >
            <option value="new">New — little to no prior experience</option>
            <option value="some">Some — familiar with basics</option>
            <option value="experienced">Experienced — working with AI/ML tools regularly</option>
          </select>
        </div>

        <div>
          <label className="form-label">Years of AI/ML experience</label>
          <select
            className="form-control"
            value={answers.ai_experience_years ?? ""}
            onChange={(e) => {
              const val = e.target.value;
              setAnswers((a) => ({ ...a, ai_experience_years: (val || null) as "none" | "under_1" | "1_to_3" | "over_3" | null }));
            }}
          >
            <option value="">— Select —</option>
            <option value="none">None</option>
            <option value="under_1">Less than 1 year</option>
            <option value="1_to_3">1–3 years</option>
            <option value="over_3">More than 3 years</option>
          </select>
        </div>

        <div>
          <label className="form-label">Primary job role</label>
          <select
            className="form-control"
            value={answers.primary_job_role ?? ""}
            onChange={(e) => {
              const val = e.target.value;
              setAnswers((a) => ({ ...a, primary_job_role: (val || null) as "developer" | "architect" | "consultant" | "manager" | "researcher" | "other" | null }));
            }}
          >
            <option value="">— Select —</option>
            <option value="developer">Developer</option>
            <option value="architect">Architect</option>
            <option value="consultant">Consultant</option>
            <option value="manager">Manager</option>
            <option value="researcher">Researcher</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div>
          <label className="form-label">Do you currently deploy LLMs in production?</label>
          <div style={{ display: "flex", gap: "0.75rem" }}>
            {[{ label: "Yes", value: true as boolean | null }, { label: "No", value: false as boolean | null }, { label: "Not sure", value: null as boolean | null }].map((opt) => (
              <label key={opt.label} style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}>
                <input
                  type="radio"
                  name="deploys_llms"
                  checked={answers.deploys_llms_in_production === opt.value}
                  onChange={() => setAnswers((a) => ({ ...a, deploys_llms_in_production: opt.value }))}
                />
                {opt.label}
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="form-label">Self-rated prompt-engineering familiarity</label>
          <select
            className="form-control"
            value={answers.prompt_engineering_familiarity ?? ""}
            onChange={(e) => {
              const val = e.target.value;
              setAnswers((a) => ({ ...a, prompt_engineering_familiarity: (val || null) as "none" | "basic" | "intermediate" | "advanced" | null }));
            }}
          >
            <option value="">— Select —</option>
            <option value="none">None — haven't tried it</option>
            <option value="basic">Basic — used it a few times</option>
            <option value="intermediate">Intermediate — comfortable with common patterns</option>
            <option value="advanced">Advanced — regularly design complex prompts</option>
          </select>
        </div>

        <div>
          <label className="form-label">Do you manage or mentor others on AI topics?</label>
          <div style={{ display: "flex", gap: "0.75rem" }}>
            {[{ label: "Yes", value: true as boolean | null }, { label: "No", value: false as boolean | null }].map((opt) => (
              <label key={opt.label} style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}>
                <input
                  type="radio"
                  name="mentors_others"
                  checked={answers.mentors_others_on_ai === opt.value}
                  onChange={() => setAnswers((a) => ({ ...a, mentors_others_on_ai: opt.value }))}
                />
                {opt.label}
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="form-label">Provider preference (optional)</label>
          <select
            className="form-control"
            value={answers.provider_preference ?? ""}
            onChange={(e) => {
              const val = e.target.value;
              setAnswers((a) => ({ ...a, provider_preference: (val || null) as "anthropic" | "aws" | "google" | "microsoft" | null }));
            }}
          >
            <option value="">No preference</option>
            <option value="anthropic">Anthropic</option>
            <option value="aws">AWS</option>
            <option value="google">Google Cloud</option>
            <option value="microsoft">Microsoft</option>
          </select>
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", marginTop: "2rem" }}>
        <button className="btn btn-outline" onClick={onCancel}>Cancel</button>
        <button
          className="btn btn-primary"
          disabled={!step1Valid}
          onClick={() => setStep(1)}
        >
          Continue →
        </button>
      </div>
    </div>
  );

  // ── Step 2: Certification choice ───────────────────────────────────────────

  const renderStep2 = () => (
    <div>
      <h2>Choose your certification</h2>
      <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
        Get a personalized recommendation, or browse the full catalog.
      </p>

      <div style={{ marginBottom: "1.5rem" }}>
        <button
          className="btn btn-primary"
          disabled={adviseMutation.isPending}
          onClick={handleGetRecommendation}
        >
          {adviseMutation.isPending ? (
            <><span className="spinner" /> Getting recommendation…</>
          ) : (
            "Get recommendation"
          )}
        </button>

        {adviseMutation.isError && (
          <p
            style={{
              marginTop: "0.75rem",
              marginBottom: 0,
              color: "var(--error, #dc2626)",
              fontSize: "0.875rem",
            }}
          >
            Could not get a recommendation — please try again. If this keeps
            happening, check that your session is still active.
          </p>
        )}
      </div>

      {recommendation && (
        <div
          className="card"
          style={{
            borderColor: "var(--primary)",
            marginBottom: "1.5rem",
            background: "color-mix(in srgb, var(--primary) 4%, var(--surface))",
          }}
        >
          <p style={{ margin: "0 0 0.25rem", fontWeight: 600, color: "var(--primary)" }}>
            Recommended: {recommendation.primary_recommendation_code}
          </p>
          <p style={{ margin: "0 0 0.75rem", fontSize: "0.875rem", lineHeight: 1.6 }}>
            {recommendation.primary_rationale}
          </p>
          {recommendation.alternative_code && (
            <p style={{ margin: 0, fontSize: "0.8125rem", color: "var(--text-muted)" }}>
              Alternative: <strong>{recommendation.alternative_code}</strong> — {recommendation.alternative_rationale}
            </p>
          )}
        </div>
      )}

      <h3 style={{ marginBottom: "0.75rem" }}>All certifications</h3>
      {certList && Object.entries(certsByProvider).map(([provider, certs]) => (
        <div key={provider} style={{ marginBottom: "1.25rem" }}>
          <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 0.5rem" }}>
            {provider}
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.375rem" }}>
            {certs.map((cert) => (
              <label
                key={cert.id}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "0.75rem",
                  padding: "0.75rem",
                  border: `1px solid ${selectedCertId === cert.id ? "var(--primary)" : "var(--border)"}`,
                  borderRadius: "var(--radius)",
                  cursor: "pointer",
                  background: selectedCertId === cert.id ? "color-mix(in srgb, var(--primary) 5%, var(--surface))" : "var(--surface)",
                }}
              >
                <input
                  type="radio"
                  name="cert"
                  checked={selectedCertId === cert.id}
                  onChange={() => { setSelectedCertId(cert.id); setSelectedCertCode(cert.code); }}
                  style={{ marginTop: "0.15rem" }}
                />
                <div>
                  <span style={{ fontWeight: 600 }}>{cert.code}</span>
                  <span style={{ color: "var(--text-muted)", marginLeft: "0.5rem", fontSize: "0.875rem" }}>
                    {cert.name}
                  </span>
                  <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginTop: "0.125rem" }}>
                    {cert.level} · {cert.requires_coding_background ? "Requires coding" : "No coding required"}
                  </div>
                </div>
              </label>
            ))}
          </div>
        </div>
      ))}

      <div style={{ display: "flex", justifyContent: "space-between", marginTop: "1.5rem" }}>
        <button className="btn btn-outline" onClick={() => setStep(0)}>← Back</button>
        <button
          className="btn btn-primary"
          onClick={() => setStep(2)}
        >
          {selectedCertCode ? `Continue with ${selectedCertCode} →` : "Continue →"}
        </button>
      </div>
    </div>
  );

  // ── Step 3: Confirm ────────────────────────────────────────────────────────

  const isSubmitting = createProfile.isPending || updateProfile.isPending;

  const renderStep3 = () => (
    <div>
      <h2>Confirm your profile</h2>
      <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
        Review your choices. You can always edit them later.
      </p>

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          <div>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Profile name</span>
            <p style={{ margin: "0.125rem 0 0", fontWeight: 600 }}>{profileName}</p>
          </div>
          <div>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Certification</span>
            <p style={{ margin: "0.125rem 0 0", fontWeight: 600 }}>
              {selectedCertCode
                ? `${selectedCertCode} — ${certList?.find((c) => c.id === selectedCertId)?.name ?? ""}`
                : "None selected"}
            </p>
          </div>
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <button className="btn btn-outline" onClick={() => setStep(1)}>← Back</button>
        <button
          className="btn btn-primary"
          disabled={isSubmitting}
          onClick={handleFinish}
        >
          {isSubmitting ? (
            <><span className="spinner" /> Saving…</>
          ) : (
            "Continue to skill rating →"
          )}
        </button>
      </div>
    </div>
  );

  return (
    <div>
      <ProgressBar step={step} total={STEPS.length} />
      {step === 0 && renderStep1()}
      {step === 1 && renderStep2()}
      {step === 2 && renderStep3()}
    </div>
  );
}
