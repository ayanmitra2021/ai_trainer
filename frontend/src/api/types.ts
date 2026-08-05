/** TypeScript types mirroring the backend Pydantic schemas. */

// ── Practitioners ─────────────────────────────────────────────────────────────

export interface Practitioner {
  id: string;
  name: string;
  email: string;
  role?: string;
  practice?: string;
  seniority_level?: string;
  created_at: string;
}

export interface PractitionerCreate {
  name: string;
  email: string;
  role?: string;
  practice?: string;
  seniority_level?: string;
}

export interface SkillSnapshot {
  skill_id: string;
  skill_name: string;
  mastery_score: number;
  confidence: number;
  last_computed_at: string;
}

// ── Skills ────────────────────────────────────────────────────────────────────

export interface Skill {
  id: string;
  name: string;
  category: string;
  parent_skill_id?: string;
  description?: string;
}

export interface SkillTreeNode extends Skill {
  children: SkillTreeNode[];
}

// ── Certifications ────────────────────────────────────────────────────────────

export interface CertificationProvider {
  id: string;
  name: string;
  website?: string;
}

export interface CertificationSkillWeight {
  skill_id: string;
  weight: number;
}

export interface Certification {
  id: string;
  code: string;
  name: string;
  level: string;
  requires_coding_background: boolean;
  typical_audience?: string;
  focus_area?: string;
  exam_format?: string;
  eligibility_notes?: string;
  external_url?: string;
  is_active: boolean;
  last_verified_at?: string;
  provider: CertificationProvider;
  certification_skills: CertificationSkillWeight[];
}

export type ProviderPreference = "anthropic" | "aws" | "google" | "microsoft";

export interface QuestionnaireAnswers {
  provider_preference?: ProviderPreference | null;
  writes_code: boolean;
  focus_area: "advising" | "building" | "architecting";
  experience_level: "new" | "some" | "experienced";
}

export interface AdvisorOutput {
  primary_recommendation_code: string;
  primary_rationale: string;
  alternative_code?: string;
  alternative_rationale?: string;
}

export interface AdvisorResponse {
  practitioner_id: string;
  advisor_response_id: string;
  goal_id: string;
  recommendation: AdvisorOutput;
}

export type GoalStatus =
  | "recommended"
  | "selected"
  | "in_progress"
  | "achieved"
  | "abandoned";

export interface CertificationGoal {
  id: string;
  practitioner_id: string;
  certification_id: string;
  certification_code: string;
  status: GoalStatus;
  recommended_at: string;
  selected_at?: string;
  achieved_at?: string;
}

// ── Learning Paths ────────────────────────────────────────────────────────────

export interface LearningPathItem {
  id: string;
  skill_id: string;
  sequence_order: number;
  resource_type: "item_set" | "scenario_lab" | "external_reading";
  status: "pending" | "in_progress" | "done";
  rationale?: string;
}

export interface LearningPath {
  id: string;
  practitioner_id: string;
  generated_at: string;
  status: "draft" | "active" | "completed";
  workflow_run_id?: string;
  items: LearningPathItem[];
}

export interface GenerateLearningPathResponse {
  workflow_run_id: string;
  learning_path_id: string;
  status: string;
}

// ── Items & Attempts ──────────────────────────────────────────────────────────

export interface MCQAnswerKey {
  options: string[];
  correct_index: number;
  trap_index?: number;
}

export interface FreeTextAnswerKey {
  model_answer: string;
  key_points: string[];
}

export interface Item {
  id: string;
  skill_id: string;
  item_type: "mcq" | "free_text" | "scenario";
  prompt: string;
  answer_key: MCQAnswerKey | FreeTextAnswerKey | Record<string, unknown>;
  trap_explanation?: string;
  difficulty: number;
  calibration_stats?: Record<string, unknown>;
  created_at: string;
}

export interface AttemptCreate {
  practitioner_id: string;
  item_id: string;
  response: { selected_index: number } | { text: string };
}

export interface Attempt {
  id: string;
  practitioner_id: string;
  item_id: string;
  response: Record<string, unknown>;
  score: number;
  grader_rationale: string;
  is_trap_selected?: boolean;
  attempted_at: string;
}

// ── Pulse ─────────────────────────────────────────────────────────────────────

export interface CorrelationSnapshot {
  id: string;
  practitioner_id: string;
  skill_id: string;
  trained_score: number;
  adoption_score: number;
  gap_score: number;
  has_adoption_gap: boolean;
  reasoning?: string;
  computed_at: string;
}

export interface Nudge {
  id: string;
  practitioner_id: string;
  nudge_type: "gap_alert" | "encouragement" | "reminder";
  channel: "email" | "in_app";
  content: string;
  status: "drafted" | "approved" | "sent";
  created_at: string;
  sent_at?: string;
  composer_reasoning?: string;
}

export interface Rollup {
  id: string;
  scope: "team" | "practice";
  scope_ref: string;
  period_start: string;
  period_end: string;
  metrics?: Record<string, unknown>;
  narrative?: string;
  min_cohort_size_met: boolean;
  created_at: string;
}

export interface NightlyPulseRequest {
  practitioner_ids: string[];
  scope: string;
  scope_ref: string;
  period_start: string;
  period_end: string;
}
