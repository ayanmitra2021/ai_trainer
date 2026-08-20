/** TypeScript types mirroring the backend Pydantic schemas. */

// ── Practitioners ─────────────────────────────────────────────────────────────

export interface Practitioner {
  id: string;
  name: string;
  email: string;
  role?: string;
  practice?: string;
  seniority_level?: string;
  is_active: boolean;
  created_at: string;
}

// Phase 21: Activity summary types
export interface ActivitySkillRow {
  skill_id: string;
  skill_name: string;
  mastery_score: number;
  gap_pct: number;
  quiz_rounds: number;
  correct_count: number;
  wrong_count: number;
  correct_pct: number;
  total_lesson_seconds: number;
  lesson_count: number;
  last_lesson_read_at?: string;
}

export interface ActivityMockExamRow {
  session_id: string;
  certification_code: string;
  status: string;
  score_pct?: number;
  questions_answered: number;
  total_questions: number;
  time_spent_seconds: number;
  started_at: string;
  completed_at?: string;
  abandoned_reason?: string;
}

export interface ActivitySummaryStats {
  total_quiz_rounds: number;
  total_attempts: number;
  overall_correct_pct: number;
  total_lesson_seconds: number;
  mock_exams_completed: number;
  latest_mock_score_pct?: number;
}

export interface ActivitySummaryResponse {
  summary_stats: ActivitySummaryStats;
  skill_activity: ActivitySkillRow[];
  mock_exams: ActivityMockExamRow[];
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
  previous_mastery_score?: number | null;
  mastery_delta?: number | null;
  trend?: "improving" | "declining" | "stable" | "new";
  // Phase 13.4: domain info for domain-weighted radar coloring
  certification_domain_id?: string | null;
  certification_domain_name?: string | null;
  domain_weight_pct?: number | null;
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
  exam_question_count?: number | null;
  exam_duration_minutes?: number | null;
  exam_passing_score_pct?: number | null;
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
  /** Phase 17.5: background quiz generation state */
  quiz_status: "pending" | "ready" | "failed";
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
  /** Phase 17.7: true when background quiz generation was launched */
  quiz_generating?: boolean;
  quiz_skipped_reason?: string | null;
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

// Phase 9.1: Rollup interface removed — rollups table dropped.
// Phase 9.1: NightlyPulseRequest interface removed — nightly_pulse workflow stubbed.

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface PractitionerLoginRequest {
  name: string;
  email: string;
  role?: string;
  practice?: string;
  seniority_level?: string;
  /** Phase 22: optional enrollment code to join a specific org at first login. */
  enrollment_code?: string;
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
  identity_type: "practitioner" | "admin" | "product_admin";
  first_name: string;
  practitioner_id?: string;
  admin_role?: "admin" | "leadership";
  must_change_password: boolean;
  active_profile_id?: string;
  active_certification_code?: string;
  /** Phase 9.3: true when the active profile has been locked (skill-ratings saved). */
  active_profile_is_locked?: boolean;
  /** Phase 22: subscription plan tier for the org this session belongs to. */
  plan_tier?: "free" | "paid" | "enterprise" | null;
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
  /** Phase 9.3: true once the practitioner saves skill ratings for this profile. */
  is_locked: boolean;
  /**
   * Phase 14.4: quality of domain scoring at profile-lock time.
   * 'pending'   — Domain Scorer has not yet run (default for new profiles).
   * 'lm_scored' — Domain Scorer ran successfully via primary or fallback LLM.
   * 'degraded'  — Both providers failed; scores are mechanical estimates from
   *               self-assessment signal strengths (confidence ≤ 0.5).
   */
  domain_scoring_status?: "pending" | "lm_scored" | "degraded";
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

// ── Certification Domain Scores ────────────────────────────────────────────────

export interface CertificationDomainScore {
  id: string;
  certification_domain_id: string;
  domain_name: string;
  weight_pct: number;
  sequence_order: number;
  mastery_score: number;
  confidence: number;
  source: "self_assessment_estimate" | "quiz_derived";
  last_computed_at: string;
  previous_mastery_score?: number | null;
  mastery_delta?: number | null;
  trend: "improving" | "declining" | "stable" | "new";
}

// ── Domain Proposals ──────────────────────────────────────────────────────────

export interface ProposedDomain {
  sequence_order: number;
  domain_name: string;
  domain_description: string;
  weight_pct: number;
}

export interface CertificationDomainVersion {
  id: string;
  certification_id: string;
  certification_code?: string | null;
  version_label: string;
  is_current: boolean;
  source_notes: string;
  agent_run_id?: string | null;
  created_by_admin_id?: string | null;
  created_at: string;
}

export interface CertificationDomainProposal {
  id: string;
  certification_id?: string | null;
  cert_code: string;
  cert_name: string;
  proposed_domains: ProposedDomain[];
  source_notes: string;
  agent_run_id: string;
  status: "pending_review" | "approved" | "rejected";
  reviewed_by_admin_id?: string | null;
  reviewed_at?: string | null;
  rejection_notes?: string | null;
  created_at: string;
}

// ── Extended Item with domain awareness ───────────────────────────────────────

export interface QuizItem extends Item {
  certification_domain_id?: string | null;
  is_cert_evaluated?: boolean;
  certification_domain_name?: string | null;
  generation?: number;
  generation_refreshed?: boolean;
  new_generation?: number | null;
}

// ── Extended SkillSnapshot with trend info ────────────────────────────────────

export interface SkillSnapshotWithTrend extends SkillSnapshot {
  previous_mastery_score?: number | null;
  mastery_delta?: number | null;
  trend?: "improving" | "declining" | "stable" | "new";
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

// ── Mock Exam ─────────────────────────────────────────────────────────────────

export interface MockExamQuestion {
  id: string;
  sequence_order: number;
  certification_domain_name: string | null;
  skill_name: string | null;
  prompt: string;
  options: string[];           // 4 options
  trap_index: number | null;   // revealed after answering
  trap_explanation: string | null; // revealed after answering — shown when trap option chosen
  explanation: string | null;      // revealed after answering — shown when any wrong answer chosen
  difficulty: number;
  response: { selected_index: number } | null;
  score: number | null;        // 1.0 or 0.0 or null
  correct_index?: number;      // only present after answering (server reveals it)
  is_trap_selected?: boolean | null; // server-computed after answering
  answered_at: string | null;
}

export interface MockExamSession {
  id: string;
  certification_id: string;
  certification_code: string;
  certification_name: string;
  exam_question_count: number;
  exam_duration_minutes: number;
  exam_passing_score_pct: number;
  status: 'generating' | 'in_progress' | 'paused' | 'completed' | 'failed' | 'abandoned';
  time_elapsed_seconds: number;
  score: number | null;
  correct_count: number | null;
  total_count: number;
  started_at: string;
  completed_at: string | null;
  abandoned_reason: string | null;
  abandoned_at: string | null;
  questions: MockExamQuestion[];
}

export interface MockExamSessionSummary {
  id: string;
  certification_id: string;
  certification_code: string;
  certification_name: string;
  exam_passing_score_pct: number;
  status: 'generating' | 'in_progress' | 'paused' | 'completed' | 'failed' | 'abandoned';
  score: number | null;
  correct_count: number | null;
  total_count: number;
  answered_count: number;
  time_elapsed_seconds: number;
  started_at: string;
  completed_at: string | null;
  abandoned_reason: string | null;
  abandoned_at: string | null;
}

// ── Byte-Sized Lessons (Phase 18) ─────────────────────────────────────────────

export interface ByteSizedLesson {
  id: string;
  skill_id: string;
  skill_name: string;
  gap_pct: number;
  target_pct: number;
  what_missing: string | null;
  estimated_read_minutes: number | null;
  generation_status: "pending" | "ready" | "failed";
  path_generation_seq: number;
  total_read_seconds: number | null;
  last_read_at: string | null;
  // Only in detail response:
  content_md?: string | null;
  external_links?: Array<{ title: string; url: string; type: string }> | null;
}

export interface LessonListResponse {
  current: ByteSizedLesson[];
  history: ByteSizedLesson[];
}

// ── Phase 22: Product Admin types ─────────────────────────────────────────────

export interface SubscriptionPlan {
  id: string;
  name: string;
  tier: "free" | "paid" | "enterprise";
  max_profiles_per_practitioner: number;
  max_learning_paths: number;
  max_mock_exams_per_profile: number;
  max_practitioners_per_org: number;
  allow_cert_recycling: boolean;
  nudges_enabled: boolean;
  teams_notifications_enabled: boolean;
  is_active: boolean;
  org_count?: number;
  created_at: string;
  updated_at: string;
}

export interface Organization {
  id: string;
  name: string;
  plan_id: string;
  plan_name?: string;
  plan_tier?: string;
  billing_email?: string | null;
  is_active: boolean;
  practitioner_count?: number;
  enrollment_code?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductAdminLoginRequest {
  email: string;
  password: string;
}

export interface ProductAdminLoginResponse {
  identity_type: "product_admin";
  first_name: string;
  must_change_password: boolean;
}

export interface ProductAdminPractitioner {
  id: string;
  name: string;
  email: string;
  org_name: string;
  plan_tier: string;
  is_active: boolean;
  created_at: string;
}

export interface UsageAnalytics {
  by_plan_tier: Array<{
    tier: string;
    plan_name: string;
    org_count: number;
    practitioner_count: number;
    active_practitioner_count: number;
    total_quiz_attempts: number;
    total_lesson_reads: number;
    total_mock_exams_completed: number;
  }>;
}

export interface AgentAnalytics {
  period_days: number;
  by_agent: Array<{
    agent_name: string;
    run_count: number;
    success_count: number;
    failure_count: number;
    avg_latency_ms: number;
    p95_latency_ms: number;
  }>;
}

export interface PlanDistribution {
  plan_distribution: Array<{
    tier: string;
    plan_name: string;
    org_count: number;
    practitioner_count: number;
  }>;
  new_enrollments_last_30d: number;
}

export interface OrgNotificationSettings {
  organization_id: string;
  teams_webhook_url?: string | null;
  teams_channel_name?: string | null;
  email_enabled: boolean;
  updated_at: string;
}
