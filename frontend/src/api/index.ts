/** Typed API functions for every backend endpoint. */

import { api } from "./client";
import type {
  AdoptionTrendsResponse,
  AdminLoginRequest,
  AdminLoginResponse,
  AdminUserCreate,
  AdminUserResponse,
  AdvisorResponse,
  Attempt,
  AttemptCreate,
  Certification,
  CertificationGoal,
  ChangePasswordRequest,
  ComposePreviewResponse,
  CorrelationSnapshot,
  GenerateLearningPathResponse,
  Item,
  LearningPath,
  MasteryHistoryResponse,
  MeResponse,
  Nudge,
  NudgeCategory,
  NudgeExtended,
  NudgeMarkReadResponse,
  ObservabilityReport,
  Practitioner,
  PractitionerCreate,
  PractitionerLoginRequest,
  PractitionerLoginResponse,
  PractitionerLookupResponse,
  PreviewRecipientsResponse,
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
  UnreadCountResponse,
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

export type { ApiError } from "./client";
