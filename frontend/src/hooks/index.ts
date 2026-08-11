/** TanStack Query hooks for every domain. */

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  attempts,
  certifications,
  items,
  learningPaths,
  practitioners,
  profiles,
  pulse,
  skills,
} from "../api";
import type {
  Attempt,
  AttemptCreate,
  PractitionerCreate,
  ProfileCreate,
  ProfileSkillUpsert,
  ProfileUpdate,
  QuestionnaireAnswers,
  SelfAssessmentRequest,
  SendNudgesRequest,
} from "../api/types";

// ── Practitioners ──────────────────────────────────────────────────────────────

export const usePractitioners = () =>
  useQuery({ queryKey: ["practitioners"], queryFn: practitioners.list });

export const usePractitioner = (id: string) =>
  useQuery({
    queryKey: ["practitioners", id],
    queryFn: () => practitioners.get(id),
    enabled: !!id,
  });

export const useSkillProfile = (id: string) =>
  useQuery({
    queryKey: ["practitioners", id, "skill-profile"],
    queryFn: () => practitioners.skillProfile(id),
    enabled: !!id,
  });

export const useSubmitSelfAssessment = (practitioner_id: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SelfAssessmentRequest) =>
      practitioners.submitSelfAssessment(practitioner_id, body),
    onSuccess: () => {
      // The radar will update on the next "Regenerate path" click — no automatic
      // re-profile per the design note in CLAUDE.md.
      // Invalidate the skill-profile cache so stale data isn't shown after regen.
      qc.invalidateQueries({
        queryKey: ["practitioners", practitioner_id, "skill-profile"],
      });
    },
  });
};

export const useCreatePractitioner = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: PractitionerCreate) => practitioners.create(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["practitioners"] }),
  });
};

// ── Skills ─────────────────────────────────────────────────────────────────────

export const useSkills = () =>
  useQuery({ queryKey: ["skills"], queryFn: skills.list });

export const useSkillTree = () =>
  useQuery({ queryKey: ["skills", "tree"], queryFn: skills.tree });

// ── Certifications ─────────────────────────────────────────────────────────────

export const useCertifications = () =>
  useQuery({ queryKey: ["certifications"], queryFn: certifications.list });

export const useAdviseMutation = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      practitioner_id,
      answers,
    }: {
      practitioner_id: string;
      answers: QuestionnaireAnswers;
    }) => certifications.advise(practitioner_id, answers),
    onSuccess: (_data, { practitioner_id }) => {
      qc.invalidateQueries({
        queryKey: ["practitioners", practitioner_id, "goals"],
      });
    },
  });
};

export const useCertificationGoals = (practitioner_id: string) =>
  useQuery({
    queryKey: ["practitioners", practitioner_id, "goals"],
    queryFn: () => certifications.goals(practitioner_id),
    enabled: !!practitioner_id,
  });

export const useUpdateGoalMutation = (practitioner_id: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      goal_id,
      status,
    }: {
      goal_id: string;
      status: string;
    }) => certifications.updateGoal(practitioner_id, goal_id, status),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: ["practitioners", practitioner_id, "goals"],
      }),
  });
};

// ── Learning Paths ─────────────────────────────────────────────────────────────

export const useLearningPaths = (practitioner_id: string) =>
  useQuery({
    queryKey: ["practitioners", practitioner_id, "learning-paths"],
    queryFn: () => learningPaths.list(practitioner_id),
    enabled: !!practitioner_id,
  });

export const useGenerateLearningPath = (practitioner_id: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => learningPaths.generate(practitioner_id),
    onSuccess: () => {
      // The workflow re-runs Skill Profiler as its first step, so both the
      // skill-profile snapshot and the learning-path list need to be refreshed.
      qc.invalidateQueries({
        queryKey: ["practitioners", practitioner_id, "learning-paths"],
      });
      qc.invalidateQueries({
        queryKey: ["practitioners", practitioner_id, "skill-profile"],
      });
    },
  });
};

// ── Items ──────────────────────────────────────────────────────────────────────

export const useItemsBySkill = (skill_id: string) =>
  useQuery({
    queryKey: ["items", "skill", skill_id],
    queryFn: () => items.listBySkill(skill_id),
    enabled: !!skill_id,
  });

// ── Attempts ───────────────────────────────────────────────────────────────────

export const usePractitionerAttempts = (practitioner_id: string) =>
  useQuery({
    queryKey: ["practitioners", practitioner_id, "attempts"],
    queryFn: () => attempts.listByPractitioner(practitioner_id),
    enabled: !!practitioner_id,
    // Keep previous data while refetching so quiz UI doesn't flash empty
    placeholderData: (prev) => prev,
  });

export const useSubmitAttempt = (practitioner_id: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AttemptCreate) => attempts.submit(body),
    onSuccess: (newAttempt: Attempt) => {
      // Append the new attempt into the cached list immediately — no round-trip
      qc.setQueryData<Attempt[]>(
        ["practitioners", practitioner_id, "attempts"],
        (old = []) => {
          // Replace any earlier attempt for the same item, then prepend the new one
          const filtered = old.filter((a) => a.item_id !== newAttempt.item_id);
          return [newAttempt, ...filtered];
        },
      );
      // Skill profile will update after the user clicks "Regenerate path"
      // (per the design note in CLAUDE.md — don't re-profile on every answer)
    },
  });
};

// ── Pulse ──────────────────────────────────────────────────────────────────────

export const useCorrelationSnapshots = (
  practitioner_id: string,
  params?: { skill_id?: string; gaps_only?: boolean },
) =>
  useQuery({
    queryKey: ["practitioners", practitioner_id, "correlation-snapshots", params],
    queryFn: () => pulse.correlationSnapshots(practitioner_id, params),
    enabled: !!practitioner_id,
  });

export const useNudges = (params?: {
  practitioner_id?: string;
  status?: string;
}) =>
  useQuery({
    queryKey: ["nudges", params],
    queryFn: () => pulse.nudges(params),
  });

export const useApproveNudge = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (nudge_id: string) => pulse.approveNudge(nudge_id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["nudges"] }),
  });
};

// Phase 9.1: useRollups hook removed — rollups table dropped and /rollups
// API endpoints removed. Leadership users navigate to /nudges instead.

// ── Profiles ───────────────────────────────────────────────────────────────────

export const useProfiles = (practitioner_id: string) =>
  useQuery({
    queryKey: ["practitioners", practitioner_id, "profiles"],
    queryFn: () => profiles.list(practitioner_id),
    enabled: !!practitioner_id,
  });

export const useProfile = (practitioner_id: string, profile_id: string) =>
  useQuery({
    queryKey: ["practitioners", practitioner_id, "profiles", profile_id],
    queryFn: () => profiles.get(practitioner_id, profile_id),
    enabled: !!practitioner_id && !!profile_id,
  });

export const useCreateProfile = (practitioner_id: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ProfileCreate) => profiles.create(practitioner_id, body),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["practitioners", practitioner_id, "profiles"] }),
  });
};

export const useUpdateProfile = (practitioner_id: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ profile_id, body }: { profile_id: string; body: ProfileUpdate }) =>
      profiles.update(practitioner_id, profile_id, body),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["practitioners", practitioner_id, "profiles"] }),
  });
};

export const useActivateProfile = (practitioner_id: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (profile_id: string) => profiles.activate(practitioner_id, profile_id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["practitioners", practitioner_id, "profiles"] });
      qc.invalidateQueries({ queryKey: ["practitioners", practitioner_id, "skill-profile"] });
    },
  });
};

export const useDeleteProfile = (practitioner_id: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (profile_id: string) => profiles.delete(practitioner_id, profile_id),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["practitioners", practitioner_id, "profiles"] }),
  });
};

export const useUpsertProfileSkills = (practitioner_id: string, profile_id: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ProfileSkillUpsert) =>
      profiles.upsertSkillAssessments(practitioner_id, profile_id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["practitioners", practitioner_id, "profiles"] });
      qc.invalidateQueries({ queryKey: ["practitioners", practitioner_id, "profiles", profile_id] });
    },
  });
};

// ── Phase 7 — Smart Nudge Campaigns ───────────────────────────────────────────

export const useNudgeCategories = () =>
  useQuery({ queryKey: ["nudge-categories"], queryFn: pulse.listCategories });

export const useGenerateNudgeCategories = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: pulse.generateCategories,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["nudge-categories"] }),
  });
};

export const usePreviewRecipients = (category_id: string | null) =>
  useQuery({
    queryKey: ["nudge-recipients", category_id],
    queryFn: () => pulse.previewRecipients(category_id!),
    enabled: !!category_id,
  });

export const useComposeCampaign = () =>
  useMutation({ mutationFn: (category_id: string) => pulse.composeCampaign(category_id) });

export const useSendNudges = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SendNudgesRequest) => pulse.sendNudges(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sent-campaigns"] }),
  });
};

export const useSentCampaigns = () =>
  useQuery({ queryKey: ["sent-campaigns"], queryFn: pulse.sentCampaigns });

export const usePractitionerNudges = (practitioner_id: string) =>
  useQuery({
    queryKey: ["practitioner-nudges", practitioner_id],
    queryFn: () => pulse.practitionerNudges(practitioner_id),
    enabled: !!practitioner_id,
  });

export const useMarkNudgeRead = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (nudge_id: string) => pulse.markNudgeRead(nudge_id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["practitioner-nudges"] });
      qc.invalidateQueries({ queryKey: ["unread-nudge-count"] });
    },
  });
};

export const useUnreadNudgeCount = (practitioner_id: string | undefined) =>
  useQuery({
    queryKey: ["unread-nudge-count", practitioner_id],
    queryFn: () => pulse.unreadNudgeCount(practitioner_id!),
    enabled: !!practitioner_id,
    refetchInterval: 60_000, // Poll every 60 seconds
  });

export const useMasteryHistory = (
  practitioner_id: string,
  params?: { skill_id?: string; days?: number }
) =>
  useQuery({
    queryKey: ["mastery-history", practitioner_id, params],
    queryFn: () => pulse.masteryHistory(practitioner_id, params),
    enabled: !!practitioner_id,
  });

export const useAdoptionTrends = (practitioner_id: string, days = 90) =>
  useQuery({
    queryKey: ["adoption-trends", practitioner_id, days],
    queryFn: () => pulse.adoptionTrends(practitioner_id, days),
    enabled: !!practitioner_id,
    staleTime: 30_000, // Re-fetch if data is older than 30 seconds
  });
