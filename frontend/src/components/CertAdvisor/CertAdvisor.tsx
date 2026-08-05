/**
 * CertAdvisor — 4-question certification advisor questionnaire.
 *
 * 👤 Human-in-the-loop note (step 2.3):
 * The question wording and recommendation weighting are owned by Ayan.
 * This component faithfully submits the four QuestionnaireAnswers fields
 * defined in the backend schema and renders what the agent returns.
 * If you want to reorder questions, rename labels, or add validation
 * logic, do it here and in `prompts/certification_advisor.md`.
 */

import { useState } from "react";
import {
  useAdviseMutation,
  useCertificationGoals,
  useCertifications,
  useUpdateGoalMutation,
} from "../../hooks";
import type {
  AdvisorResponse,
  CertificationGoal,
  ProviderPreference,
  QuestionnaireAnswers,
} from "../../api/types";

interface Props {
  practitionerId: string;
}

type Step = "questionnaire" | "result";

const PROVIDERS: { value: ProviderPreference | ""; label: string }[] = [
  { value: "", label: "No preference" },
  { value: "anthropic", label: "Anthropic" },
  { value: "aws", label: "Amazon Web Services" },
  { value: "google", label: "Google Cloud" },
  { value: "microsoft", label: "Microsoft Azure" },
];

const FOCUS_AREAS: { value: QuestionnaireAnswers["focus_area"]; label: string; desc: string }[] = [
  { value: "advising", label: "Advising / consulting", desc: "Working with clients on AI strategy without writing code" },
  { value: "building", label: "Building / development", desc: "Developing AI-powered applications and integrations" },
  { value: "architecting", label: "Architecting / design", desc: "Designing systems, patterns, and enterprise AI architecture" },
];

const EXPERIENCE_LEVELS: { value: QuestionnaireAnswers["experience_level"]; label: string }[] = [
  { value: "new", label: "New to AI / generative AI" },
  { value: "some", label: "Some experience (side projects, courses)" },
  { value: "experienced", label: "Experienced practitioner" },
];

function GoalStatusPill({ status }: { status: CertificationGoal["status"] }) {
  const map: Record<CertificationGoal["status"], string> = {
    recommended: "badge-blue",
    selected: "badge-green",
    in_progress: "badge-orange",
    achieved: "badge-green",
    abandoned: "badge-gray",
  };
  return (
    <span className={`badge ${map[status]}`}>
      {status.replace("_", " ")}
    </span>
  );
}

export default function CertAdvisor({ practitionerId }: Props) {
  const { data: certs } = useCertifications();
  const { data: goals, isLoading: goalsLoading } = useCertificationGoals(practitionerId);
  const advise = useAdviseMutation();
  const updateGoal = useUpdateGoalMutation(practitionerId);

  const [step, setStep] = useState<Step>("questionnaire");
  const [result, setResult] = useState<AdvisorResponse | null>(null);
  const [answers, setAnswers] = useState<QuestionnaireAnswers>({
    provider_preference: null,
    writes_code: false,
    focus_area: "advising",
    experience_level: "new",
  });

  const certByCode = (code: string) =>
    certs?.find((c) => c.code === code);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await advise.mutateAsync({ practitioner_id: practitionerId, answers });
    setResult(res);
    setStep("result");
  };

  const handleAccept = async (goalId: string) => {
    await updateGoal.mutateAsync({ goal_id: goalId, status: "selected" });
  };

  if (step === "result" && result) {
    const primary = certByCode(result.recommendation.primary_recommendation_code);
    const alt = result.recommendation.alternative_code
      ? certByCode(result.recommendation.alternative_code)
      : null;

    return (
      <div>
        <h2>Recommendation</h2>

        {/* Primary recommendation */}
        <div className="card" style={{ marginBottom: "1rem" }}>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap" }}>
            <div>
              <span className="badge badge-blue" style={{ marginBottom: "0.5rem" }}>Primary recommendation</span>
              <h3 style={{ margin: "0.25rem 0" }}>
                {primary ? `${primary.name} (${primary.code})` : result.recommendation.primary_recommendation_code}
              </h3>
              {primary && (
                <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", margin: "0.25rem 0 0" }}>
                  {primary.provider.name} · {primary.level} · {primary.typical_audience}
                </p>
              )}
            </div>
            <button
              className="btn btn-primary"
              disabled={updateGoal.isPending}
              onClick={() => handleAccept(result.goal_id)}
            >
              Accept this recommendation
            </button>
          </div>
          <p style={{ marginTop: "1rem", marginBottom: 0, fontSize: "0.875rem", lineHeight: 1.6 }}>
            {result.recommendation.primary_rationale}
          </p>
        </div>

        {/* Alternative */}
        {alt && result.recommendation.alternative_rationale && (
          <div className="card" style={{ marginBottom: "1rem" }}>
            <span className="badge badge-gray" style={{ marginBottom: "0.5rem" }}>Alternative</span>
            <h3 style={{ margin: "0.25rem 0" }}>
              {alt.name} ({alt.code})
            </h3>
            <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
              {alt.provider.name} · {alt.level}
            </p>
            <p style={{ marginTop: "0.75rem", marginBottom: 0, fontSize: "0.875rem", lineHeight: 1.6 }}>
              {result.recommendation.alternative_rationale}
            </p>
          </div>
        )}

        <button
          className="btn btn-outline"
          style={{ marginTop: "0.5rem" }}
          onClick={() => { setStep("questionnaire"); setResult(null); }}
        >
          Retake questionnaire
        </button>
      </div>
    );
  }

  return (
    <div>
      <h2>Certification Advisor</h2>
      <p style={{ color: "var(--text-muted)", marginBottom: "1.5rem" }}>
        Four questions to recommend the best-fit certification from our catalog.
      </p>

      <form onSubmit={handleSubmit}>
        {/* Q1 — Provider preference */}
        <div className="card" style={{ marginBottom: "1rem" }}>
          <p style={{ fontWeight: 600, marginBottom: "0.75rem" }}>
            1. Do you have a preference for a specific cloud or AI provider?
          </p>
          <div className="radio-group">
            {PROVIDERS.map((p) => (
              <label
                key={p.value}
                className={`radio-option${answers.provider_preference === (p.value || null) ? " selected" : ""}`}
              >
                <input
                  type="radio"
                  name="provider"
                  value={p.value}
                  checked={answers.provider_preference === (p.value || null)}
                  onChange={() =>
                    setAnswers((a) => ({
                      ...a,
                      provider_preference: (p.value as ProviderPreference) || null,
                    }))
                  }
                />
                {p.label}
              </label>
            ))}
          </div>
        </div>

        {/* Q2 — Coding background */}
        <div className="card" style={{ marginBottom: "1rem" }}>
          <p style={{ fontWeight: 600, marginBottom: "0.75rem" }}>
            2. Does your day-to-day work involve writing code?
          </p>
          <div className="radio-group">
            {([true, false] as const).map((v) => (
              <label
                key={String(v)}
                className={`radio-option${answers.writes_code === v ? " selected" : ""}`}
              >
                <input
                  type="radio"
                  name="writes_code"
                  value={String(v)}
                  checked={answers.writes_code === v}
                  onChange={() => setAnswers((a) => ({ ...a, writes_code: v }))}
                />
                {v ? "Yes, I write code regularly" : "No, I am non-technical or business-focused"}
              </label>
            ))}
          </div>
        </div>

        {/* Q3 — Focus area */}
        <div className="card" style={{ marginBottom: "1rem" }}>
          <p style={{ fontWeight: 600, marginBottom: "0.75rem" }}>
            3. Which best describes your primary focus with AI?
          </p>
          <div className="radio-group">
            {FOCUS_AREAS.map((f) => (
              <label
                key={f.value}
                className={`radio-option${answers.focus_area === f.value ? " selected" : ""}`}
              >
                <input
                  type="radio"
                  name="focus_area"
                  value={f.value}
                  checked={answers.focus_area === f.value}
                  onChange={() => setAnswers((a) => ({ ...a, focus_area: f.value }))}
                />
                <span>
                  <strong>{f.label}</strong>
                  <span style={{ display: "block", color: "var(--text-muted)", fontSize: "0.8125rem" }}>
                    {f.desc}
                  </span>
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Q4 — Experience level */}
        <div className="card" style={{ marginBottom: "1.5rem" }}>
          <p style={{ fontWeight: 600, marginBottom: "0.75rem" }}>
            4. How would you describe your current AI experience level?
          </p>
          <div className="radio-group">
            {EXPERIENCE_LEVELS.map((e) => (
              <label
                key={e.value}
                className={`radio-option${answers.experience_level === e.value ? " selected" : ""}`}
              >
                <input
                  type="radio"
                  name="experience_level"
                  value={e.value}
                  checked={answers.experience_level === e.value}
                  onChange={() =>
                    setAnswers((a) => ({ ...a, experience_level: e.value }))
                  }
                />
                {e.label}
              </label>
            ))}
          </div>
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          disabled={advise.isPending}
        >
          {advise.isPending ? <><span className="spinner" /> Getting recommendation…</> : "Get recommendation"}
        </button>
        {advise.isError && (
          <p style={{ color: "var(--danger)", marginTop: "0.75rem", fontSize: "0.875rem" }}>
            {(advise.error as Error).message}
          </p>
        )}
      </form>

      {/* Past goals */}
      {!goalsLoading && goals && goals.length > 0 && (
        <div style={{ marginTop: "2rem" }}>
          <h3>Certification goals</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.625rem" }}>
            {goals.map((g) => (
              <div key={g.id} className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem" }}>
                <div>
                  <span style={{ fontWeight: 600 }}>{g.certification_code}</span>
                  <span style={{ marginLeft: "0.75rem" }}>
                    <GoalStatusPill status={g.status} />
                  </span>
                  <p style={{ margin: "0.25rem 0 0", fontSize: "0.8125rem", color: "var(--text-muted)" }}>
                    Recommended {new Date(g.recommended_at).toLocaleDateString()}
                  </p>
                </div>
                {g.status === "recommended" && (
                  <button
                    className="btn btn-outline"
                    disabled={updateGoal.isPending}
                    onClick={() => handleAccept(g.id)}
                  >
                    Select this goal
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
