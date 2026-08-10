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
  // Phase 6.2 optional fields
  ai_experience_years?: "none" | "under_1" | "1_to_3" | "over_3" | null;
  primary_job_role?: "developer" | "architect" | "consultant" | "manager" | "researcher" | "other" | null;
  deploys_llms_in_production?: boolean | null;
  prompt_engineering_familiarity?: "none" | "basic" | "intermediate" | "advanced" | null;
  mentors_others_on_ai?: boolean | null;
}

export interface AdvisorOutput {
  primary_recommendation_code: string;
  primary_rationale: string;
  alternative_code?: string;
  alternative_rationale?: string;
  // Cert metadata — always returned so auto-create works
  cert_full_name?: string;
  cert_provider_name?: string;
  cert_level?: string;
  cert_requires_coding?: boolean;
}

export interface AdvisorResponse {
  practitioner_id: string;
  advisor_response_id: string;
  goal_id: string;
  recommendation: AdvisorOutput;
  /** True when the cert was not in the catalog and has been auto-created. */
  is_new_certification: boolean;
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
  nudge_type: "gap_alert" | "encouragement" | "reminder" | "campaign";
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

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface PractitionerLoginRequest {
  name: string;
  email: string;
  role?: string;
  practice?: string;
  seniority_level?: string;
}

export interface PractitionerLookupResponse {
  found: boolean;
  name: string;
  role: string;
  practice: string;
  seniority_level: string;
}

export interface AdminLoginRequest {
  email: string;
  password: string;
}

export interface PractitionerLoginResponse {
  identity_type: "practitioner";
  first_name: string;
  practitioner_id: string;
}

export interface AdminLoginResponse {
  identity_type: "admin";
  first_name: string;
  role: "admin" | "leadership";
  must_change_password: boolean;
}

export type LoginResponse = PractitionerLoginResponse | AdminLoginResponse;

export interface MeResponse {
  identity_type: "practitioner" | "admin";
  first_name: string;
  practitioner_id?: string;
  admin_role?: "admin" | "leadership";
  must_change_password: boolean;
  active_profile_id?: string;
  active_certification_code?: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

// ── Self Assessment ───────────────────────────────────────────────────────────

export interface SkillAssessmentItem {
  skill_id: string;
  signal_strength: number; // 0.0–1.0
}

export interface SelfAssessmentRequest {
  assessments: SkillAssessmentItem[];
}

export interface SelfAssessmentResponse {
  events_written: number;
}

// ── Admin Users ───────────────────────────────────────────────────────────────

export interface AdminUserResponse {
  id: string;
  email: string;
  first_name: string;
  role: "admin" | "leadership";
  must_change_password: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface AdminUserCreate {
  email: string;
  first_name: string;
  role: "admin" | "leadership";
  temporary_password: string;
}

// ── Observability ──────────────────────────────────────────────────────────────

export interface AgentStats {
  agent_name: string;
  run_count: number;
  error_count: number;
  error_rate: number;
  avg_latency_ms: number | null;
  avg_tokens_input: number | null;
  avg_tokens_output: number | null;
}

export interface RecentError {
  id: string;
  agent_name: string;
  error_message: string | null;
  workflow_run_id: string | null;
  started_at: string;
}

export interface ObservabilityReport {
  period_hours: number;
  total_runs: number;
  error_count: number;
  error_rate: number;
  avg_latency_ms: number | null;
  by_agent: AgentStats[];
  recent_errors: RecentError[];
}

// ── Profiles ──────────────────────────────────────────────────────────────────

export interface ProfileSkillAssessment {
  id: string;
  profile_id: string;
  skill_id: string;
  signal_strength: number;
  updated_at: string;
}

export interface PractitionerProfile {
  id: string;
  practitioner_id: string;
  name: string;
  is_active: boolean;
  certification_id?: string;
  certification_code?: string;
  questionnaire_snapshot?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  mastery_pct?: number;
}

export interface ProfileDetail extends PractitionerProfile {
  skill_assessments: ProfileSkillAssessment[];
}

export interface ProfileCreate {
  name: string;
  questionnaire_snapshot?: Record<string, unknown>;
  certification_id?: string;
}

export interface ProfileUpdate {
  name?: string;
  certification_id?: string;
  questionnaire_snapshot?: Record<string, unknown>;
}

export interface ProfileSkillUpsert {
  assessments: { skill_id: string; signal_strength: number }[];
}

export interface ProfileSkillUpsertResponse {
  rows_written: number;
}

// ── Nudge Campaign (Phase 7) ──────────────────────────────────────────────────

export interface NudgeCategory {
  id: string;
  title?: string;
  description: string;
  criteria: Record<string, unknown>;
  is_custom: boolean;
  tone_hint?: string;
  estimated_reach?: number;
  created_by_admin_id?: string;
  created_at: string;
}

export interface RecipientPreview {
  id: string;
  name: string;
  email: string;
  action_profile_summary: string;
}

export interface PreviewRecipientsResponse {
  recipients: RecipientPreview[];
  total: number;
}

export interface ComposePreviewResponse {
  subject: string;
  body: string;
  tone_check: string;
  recipients: RecipientPreview[];
}

export interface SendNudgesRequest {
  category_id: string;
  message_subject: string;
  message_body: string;
  recipient_overrides: { practitioner_id: string; include: boolean }[];
}

export interface SendNudgesResponse {
  sent_count: number;
  workflow_run_id: string;
  nudge_ids: string[];
}

export interface NudgeExtended extends Nudge {
  subject?: string;
  is_read: boolean;
  read_at?: string;
  nudge_category_id?: string;
  created_by_admin_id?: string;
}

export interface NudgeMarkReadResponse {
  id: string;
  is_read: boolean;
  read_at?: string;
}

export interface UnreadCountResponse {
  unread_count: number;
}

export interface MasteryHistoryPoint {
  skill_id: string;
  skill_name: string;
  mastery_score: number;
  recorded_at: string;
}

export interface MasteryHistoryResponse {
  points: MasteryHistoryPoint[];
  practitioner_id: string;
}

export interface SentCampaignSummary {
  category_id?: string;
  category_title?: string;
  sent_at: string;
  recipient_count: number;
  subject?: string;
}

// ── Adoption Trends (Phase 7, revised) ───────────────────────────────────────

export interface SkillQuizPeriod {
  week_start: string;    // "2026-07-06"
  period_label: string;  // "Jul 6"
  avg_score: number;     // 0.0–1.0
  attempt_count: number;
}

export interface SkillAdoptionTrend {
  skill_id: string;
  skill_name: string;
  self_assessed_score: number;         // trained / baseline
  quiz_performance: SkillQuizPeriod[]; // weekly quiz averages
  current_gap: number;                 // positive = under-performing vs baseline
  gap_direction: "closing" | "widening" | "stable" | "no_data";
  has_quiz_data: boolean;
}

export interface AdoptionTrendsResponse {
  practitioner_id: string;
  skills: SkillAdoptionTrend[];
  computed_at: string;
}
