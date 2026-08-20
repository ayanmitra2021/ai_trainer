/** Typed API functions for every backend endpoint. */

import { api } from "./client";
import type {
  AdoptionTrendsResponse,
  AdminLoginRequest,
  AdminLoginResponse,
  AdminUserCreate,
  AdminUserResponse,
  AgentAnalytics,
  AdvisorResponse,
  Attempt,
  AttemptCreate,
  Certification,
  CertificationDomainProposal,
  CertificationDomainScore,
  CertificationDomainVersion,
  CertificationGoal,
  ChangePasswordRequest,
  ComposePreviewResponse,
  CorrelationSnapshot,
  GenerateLearningPathResponse,
  Item,
  LearningPath,
  MasteryHistoryResponse,
  MeResponse,
  MockExamQuestion,
  MockExamSession,
  MockExamSessionSummary,
  Nudge,
  NudgeCategory,
  NudgeExtended,
  NudgeMarkReadResponse,
  ObservabilityReport,
  ActivitySummaryResponse,
  Organization,
  OrgNotificationSettings,
  PlanDistribution,
  Practitioner,
  PractitionerCreate,
  PractitionerLoginRequest,
  PractitionerLoginResponse,
  PractitionerLookupResponse,
  PreviewRecipientsResponse,
  ProductAdminLoginRequest,
  ProductAdminLoginResponse,
  ProductAdminPractitioner,
  ProfileCreate,
  ProfileDetail,
  ProfileSkillUpsert,
  ProfileSkillUpsertResponse,
  ProfileUpdate,
  PractitionerProfile,
  QuestionnaireAnswers,
  SelfAssessmentRequest,
  SelfAssessmentResponse,
  SendNudgesRequest,
  SendNudgesResponse,
  SentCampaignSummary,
  Skill,
  SkillSnapshot,
  SkillTreeNode,
  SubscriptionPlan,
  UnreadCountResponse,
  UsageAnalytics,
} from "./types";

// ── Practitioners ──────────────────────────────────────────────────────────────

export const practitioners = {
  list: () => api.get<Practitioner[]>("/practitioners"),
  get: (id: string) => api.get<Practitioner>(`/practitioners/${id}`),
  create: (body: PractitionerCreate) =>
    api.post<Practitioner>("/practitioners", body),
  skillProfile: (id: string) =>
    api.get<SkillSnapshot[]>(`/practitioners/${id}/skill-profile`),
  submitSelfAssessment: (id: string, body: SelfAssessmentRequest) =>
    api.post<SelfAssessmentResponse>(`/practitioners/${id}/self-assessment`, body),
  certDomainScores: (practitionerId: string, certificationId: string) =>
    api.get<CertificationDomainScore[]>(
      `/practitioners/${practitionerId}/certification-domain-scores?certification_id=${encodeURIComponent(certificationId)}`
    ),
  // Phase 21: admin account management + activity summary
  deactivate: (id: string) =>
    api.patch<void>(`/practitioners/${id}/deactivate`, {}),
  reactivate: (id: string) =>
    api.patch<void>(`/practitioners/${id}/reactivate`, {}),
  activitySummary: (id: string) =>
    api.get<ActivitySummaryResponse>(`/practitioners/${id}/activity-summary`),
  mockExams: {
    start: (practitionerId: string) =>
      api.post<MockExamSession>(`/practitioners/${practitionerId}/mock-exams`, {}),
    getActive: (practitionerId: string) =>
      api.get<MockExamSession>(`/practitioners/${practitionerId}/mock-exams/active`),
    getById: (practitionerId: string, sessionId: string) =>
      api.get<MockExamSession>(`/practitioners/${practitionerId}/mock-exams/${sessionId}`),
    pause: (practitionerId: string, sessionId: string) =>
      api.patch<MockExamSession>(`/practitioners/${practitionerId}/mock-exams/${sessionId}/pause`, {}),
    resume: (practitionerId: string, sessionId: string) =>
      api.patch<MockExamSession>(`/practitioners/${practitionerId}/mock-exams/${sessionId}/resume`, {}),
    answer: (practitionerId: string, sessionId: string, questionId: string, selectedIndex: number) =>
      api.post<MockExamQuestion>(`/practitioners/${practitionerId}/mock-exams/${sessionId}/answer/${questionId}`, { selected_index: selectedIndex }),
    complete: (practitionerId: string, sessionId: string) =>
      api.post<MockExamSession>(`/practitioners/${practitionerId}/mock-exams/${sessionId}/complete`, {}),
    abandon: (practitionerId: string, sessionId: string, reason: string) =>
      api.post<MockExamSession>(`/practitioners/${practitionerId}/mock-exams/${sessionId}/abandon`, { reason }),
    list: (practitionerId: string) =>
      api.get<MockExamSessionSummary[]>(`/practitioners/${practitionerId}/mock-exams`),
  },
};

// ── Skills ─────────────────────────────────────────────────────────────────────

export const skills = {
  list: () => api.get<Skill[]>("/skills"),
  tree: () => api.get<SkillTreeNode[]>("/skills/tree"),
};

// ── Certifications ─────────────────────────────────────────────────────────────

export const certifications = {
  list: () => api.get<Certification[]>("/certifications"),
  advise: (practitioner_id: string, answers: QuestionnaireAnswers) =>
    api.post<AdvisorResponse>("/certification-advisor", {
      practitioner_id,
      answers,
    }),
  goals: (practitioner_id: string) =>
    api.get<CertificationGoal[]>(
      `/practitioners/${practitioner_id}/certification-goals`,
    ),
  updateGoal: (
    practitioner_id: string,
    goal_id: string,
    status: string,
  ) =>
    api.patch<CertificationGoal>(
      `/practitioners/${practitioner_id}/certification-goals/${goal_id}`,
      { status },
    ),
};

// ── Learning Paths ─────────────────────────────────────────────────────────────

export const learningPaths = {
  generate: (practitioner_id: string) =>
    api.post<GenerateLearningPathResponse>("/learning-paths/generate", {
      practitioner_id,
    }),
  list: (practitioner_id: string) =>
    api.get<LearningPath[]>(`/practitioners/${practitioner_id}/learning-paths`),
  /** Phase 17.8: admin override — synchronously regenerates all skills in a path. */
  generateQuizBatch: (practitioner_id: string, path_id: string) =>
    api.post<{ quiz_generating: boolean; skills_queued: number }>(
      `/practitioners/${practitioner_id}/learning-paths/${path_id}/quiz-batch`,
      {}
    ),
  /** Phase 17.9: retry quiz generation for all failed skills in the latest path. */
  retryQuizGeneration: (practitioner_id: string) =>
    api.post<{ message: string; retried: number }>(
      `/practitioners/${practitioner_id}/quiz-generation/retry`,
      {}
    ),
};

// ── Items ──────────────────────────────────────────────────────────────────────

export const items = {
  /** Get quiz items for a specific skill (added in Phase 4). */
  listBySkill: (skill_id: string) =>
    api.get<Item[]>(`/items?skill_id=${encodeURIComponent(skill_id)}`),
};

// ── Attempts ───────────────────────────────────────────────────────────────────

export const attempts = {
  submit: (body: AttemptCreate) => api.post<Attempt>("/attempts", body),
  get: (attempt_id: string) => api.get<Attempt>(`/attempts/${attempt_id}`),
  listByPractitioner: (practitioner_id: string) =>
    api.get<Attempt[]>(`/practitioners/${practitioner_id}/attempts`),
};

// ── Pulse ──────────────────────────────────────────────────────────────────────

export const pulse = {
  correlationSnapshots: (
    practitioner_id: string,
    params?: { skill_id?: string; gaps_only?: boolean },
  ) => {
    const q = new URLSearchParams();
    if (params?.skill_id) q.set("skill_id", params.skill_id);
    if (params?.gaps_only != null)
      q.set("gaps_only", String(params.gaps_only));
    const qs = q.toString() ? `?${q.toString()}` : "";
    return api.get<CorrelationSnapshot[]>(
      `/practitioners/${practitioner_id}/correlation-snapshots${qs}`,
    );
  },
  nudges: (params?: { practitioner_id?: string; status?: string }) => {
    const q = new URLSearchParams();
    if (params?.practitioner_id)
      q.set("practitioner_id", params.practitioner_id);
    if (params?.status) q.set("status", params.status);
    const qs = q.toString() ? `?${q.toString()}` : "";
    return api.get<Nudge[]>(`/nudges${qs}`);
  },
  approveNudge: (nudge_id: string) =>
    api.post<Nudge>(`/nudges/${nudge_id}/approve`, {}),
  generateCategories: () => api.get<NudgeCategory[]>("/nudges/generate-categories"),
  listCategories: () => api.get<NudgeCategory[]>("/nudges/categories"),
  previewRecipients: (category_id: string) =>
    api.post<PreviewRecipientsResponse>(`/nudges/categories/${category_id}/preview-recipients`, {}),
  composeCampaign: (category_id: string) =>
    api.post<ComposePreviewResponse>(`/nudges/categories/${category_id}/compose`, {}),
  sendNudges: (body: SendNudgesRequest) => api.post<SendNudgesResponse>("/nudges/send", body),
  sentCampaigns: () => api.get<SentCampaignSummary[]>("/nudges/sent"),
  practitionerNudges: (practitioner_id: string) =>
    api.get<NudgeExtended[]>(`/practitioners/${practitioner_id}/nudges`),
  markNudgeRead: (nudge_id: string) =>
    api.patch<NudgeMarkReadResponse>(`/nudges/${nudge_id}/read`, {}),
  unreadNudgeCount: (practitioner_id: string) =>
    api.get<UnreadCountResponse>(`/practitioners/${practitioner_id}/nudges/unread-count`),
  masteryHistory: (practitioner_id: string, params?: { skill_id?: string; days?: number }) => {
    const q = new URLSearchParams();
    if (params?.skill_id) q.set("skill_id", params.skill_id);
    if (params?.days) q.set("days", String(params.days));
    const qs = q.toString() ? `?${q.toString()}` : "";
    return api.get<MasteryHistoryResponse>(`/practitioners/${practitioner_id}/mastery-history${qs}`);
  },
  adoptionTrends: (practitioner_id: string, days = 90) =>
    api.get<AdoptionTrendsResponse>(
      `/practitioners/${practitioner_id}/adoption-trends?days=${days}`
    ),
  // Phase 9.1: rollups() and getRollup() removed — rollups table dropped.
  // Phase 22.11: send a message to the org's configured Teams channel
  sendTeamsMessage: (message: string) =>
    api.post<{ success: boolean }>("/admin/nudges/send-teams", { message }),
};

// ── Profiles ───────────────────────────────────────────────────────────────────

export const profiles = {
  list: (practitioner_id: string) =>
    api.get<PractitionerProfile[]>(`/practitioners/${practitioner_id}/profiles`),
  create: (practitioner_id: string, body: ProfileCreate) =>
    api.post<PractitionerProfile>(`/practitioners/${practitioner_id}/profiles`, body),
  get: (practitioner_id: string, profile_id: string) =>
    api.get<ProfileDetail>(`/practitioners/${practitioner_id}/profiles/${profile_id}`),
  update: (practitioner_id: string, profile_id: string, body: ProfileUpdate) =>
    api.patch<PractitionerProfile>(`/practitioners/${practitioner_id}/profiles/${profile_id}`, body),
  activate: (practitioner_id: string, profile_id: string) =>
    api.patch<PractitionerProfile>(`/practitioners/${practitioner_id}/profiles/${profile_id}/activate`, {}),
  delete: (practitioner_id: string, profile_id: string) =>
    api.delete<void>(`/practitioners/${practitioner_id}/profiles/${profile_id}`),
  upsertSkillAssessments: (practitioner_id: string, profile_id: string, body: ProfileSkillUpsert) =>
    api.post<ProfileSkillUpsertResponse>(`/practitioners/${practitioner_id}/profiles/${profile_id}/skill-assessments`, body),
};

// ── Auth ───────────────────────────────────────────────────────────────────────

export const auth = {
  practitionerLogin: (body: PractitionerLoginRequest) =>
    api.post<PractitionerLoginResponse>("/auth/practitioner-login", body),
  adminLogin: (body: AdminLoginRequest) =>
    api.post<AdminLoginResponse>("/auth/admin-login", body),
  logout: () => api.post<void>("/auth/logout", {}),
  me: () => api.get<MeResponse>("/auth/me"),
  changePassword: (body: ChangePasswordRequest) =>
    api.post<void>("/auth/change-password", body),
  lookupEmail: (email: string) =>
    api.get<PractitionerLookupResponse>(
      `/auth/lookup-email?email=${encodeURIComponent(email)}`
    ),
};

// ── Admin Users ────────────────────────────────────────────────────────────────

export const adminUsers = {
  list: () => api.get<AdminUserResponse[]>("/admin-users"),
  create: (body: AdminUserCreate) =>
    api.post<AdminUserResponse>("/admin-users", body),
  delete: (id: string) => api.delete<void>(`/admin-users/${id}`),
};

// ── Observability ───────────────────────────────────────────────────────────────

export const observability = {
  agentRuns: (hours?: number) => {
    const qs = hours != null ? `?hours=${hours}` : "";
    return api.get<ObservabilityReport>(`/observability/agent-runs${qs}`);
  },
};

// ── Cert Domain Management (Phase 10) ─────────────────────────────────────────

export const certDomains = {
  discover: (
    certCode: string,
    certName: string,
    providerName: string,
    knownSourceUrl?: string,
    refreshReason?: string,
  ) =>
    api.post<CertificationDomainProposal>("/admin/cert-domains/discover", {
      cert_code: certCode,
      cert_name: certName,
      provider_name: providerName,
      known_source_url: knownSourceUrl,
      refresh_reason: refreshReason,
    }),

  discoverAll: () =>
    api.post<CertificationDomainProposal[]>("/admin/cert-domains/discover-all", {}),

  approveProposal: (proposalId: string) =>
    api.post<unknown>(`/admin/cert-domain-proposals/${proposalId}/approve`, {}),

  rejectProposal: (proposalId: string, rejectionNotes: string) =>
    api.post<unknown>(`/admin/cert-domain-proposals/${proposalId}/reject`, {
      rejection_notes: rejectionNotes,
    }),

  listVersions: () =>
    api.get<CertificationDomainVersion[]>("/admin/cert-domain-versions"),

  listProposals: (status?: string) => {
    const qs = status ? `?status=${encodeURIComponent(status)}` : "";
    return api.get<CertificationDomainProposal[]>(`/admin/cert-domain-proposals${qs}`);
  },
};

// ── Product Admin (Phase 22.7) ─────────────────────────────────────────────────

export const productAdmin = {
  login: (body: ProductAdminLoginRequest) =>
    api.post<ProductAdminLoginResponse>("/product-admin/login", body),
  logout: () => api.post<void>("/product-admin/logout", {}),
  me: () => api.get<MeResponse>("/product-admin/me"),
  changePassword: (body: ChangePasswordRequest) =>
    api.post<void>("/product-admin/change-password", body),

  // Plans
  listPlans: () => api.get<SubscriptionPlan[]>("/product-admin/plans"),
  createPlan: (body: Partial<SubscriptionPlan>) =>
    api.post<SubscriptionPlan>("/product-admin/plans", body),
  updatePlan: (id: string, body: Partial<SubscriptionPlan>) =>
    api.patch<SubscriptionPlan>(`/product-admin/plans/${id}`, body),
  deactivatePlan: (id: string) =>
    api.delete<void>(`/product-admin/plans/${id}`),

  // Organizations
  listOrgs: () => api.get<Organization[]>("/product-admin/organizations"),
  createOrg: (body: { name: string; plan_id: string; billing_email?: string }) =>
    api.post<Organization>("/product-admin/organizations", body),
  updateOrg: (id: string, body: Partial<Organization>) =>
    api.patch<Organization>(`/product-admin/organizations/${id}`, body),
  regenerateCode: (id: string) =>
    api.post<{ code: string }>(`/product-admin/organizations/${id}/regenerate-code`, {}),
  deactivateOrg: (id: string) =>
    api.patch<void>(`/product-admin/organizations/${id}/deactivate`, {}),
  reactivateOrg: (id: string) =>
    api.patch<void>(`/product-admin/organizations/${id}/reactivate`, {}),

  // Practitioners
  listPractitioners: (params?: { org_id?: string; is_active?: boolean; plan_tier?: string }) =>
    api.get<ProductAdminPractitioner[]>(
      `/product-admin/practitioners${params ? "?" + new URLSearchParams(
        Object.entries(params)
          .filter(([, v]) => v !== undefined)
          .map(([k, v]) => [k, String(v)])
      ).toString() : ""}`
    ),
  deactivatePractitioner: (id: string) =>
    api.patch<void>(`/product-admin/practitioners/${id}/deactivate`, {}),
  reactivatePractitioner: (id: string) =>
    api.patch<void>(`/product-admin/practitioners/${id}/reactivate`, {}),

  // Analytics
  getUsageAnalytics: () => api.get<UsageAnalytics>("/product-admin/analytics/usage"),
  getAgentAnalytics: () => api.get<AgentAnalytics>("/product-admin/analytics/agents"),
  getPlanDistribution: () => api.get<PlanDistribution>("/product-admin/analytics/plans"),
};

// ── Notification Settings (Phase 22.10) ───────────────────────────────────────

export const notificationSettings = {
  get: () => api.get<OrgNotificationSettings>("/admin/notification-settings"),
  update: (body: Partial<OrgNotificationSettings>) =>
    api.put<OrgNotificationSettings>("/admin/notification-settings", body),
  testTeams: () =>
    api.post<{ success: boolean; error?: string }>("/admin/notification-settings/test-teams", {}),
};

export type { ApiError } from "./client";
