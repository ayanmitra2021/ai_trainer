/** Typed API functions for every backend endpoint. */

import { api } from "./client";
import type {
  AdvisorResponse,
  Attempt,
  AttemptCreate,
  Certification,
  CertificationGoal,
  CorrelationSnapshot,
  GenerateLearningPathResponse,
  Item,
  LearningPath,
  Nudge,
  Practitioner,
  PractitionerCreate,
  QuestionnaireAnswers,
  Rollup,
  Skill,
  SkillSnapshot,
  SkillTreeNode,
} from "./types";

// ── Practitioners ──────────────────────────────────────────────────────────────

export const practitioners = {
  list: () => api.get<Practitioner[]>("/practitioners"),
  get: (id: string) => api.get<Practitioner>(`/practitioners/${id}`),
  create: (body: PractitionerCreate) =>
    api.post<Practitioner>("/practitioners", body),
  skillProfile: (id: string) =>
    api.get<SkillSnapshot[]>(`/practitioners/${id}/skill-profile`),
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
  rollups: (params?: { scope?: string; scope_ref?: string }) => {
    const q = new URLSearchParams();
    if (params?.scope) q.set("scope", params.scope);
    if (params?.scope_ref) q.set("scope_ref", params.scope_ref);
    const qs = q.toString() ? `?${q.toString()}` : "";
    return api.get<Rollup[]>(`/rollups${qs}`);
  },
  getRollup: (rollup_id: string) => api.get<Rollup>(`/rollups/${rollup_id}`),
};

export type { ApiError } from "./client";
