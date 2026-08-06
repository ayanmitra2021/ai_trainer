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
  pulse,
  skills,
} from "../api";
import type {
  AttemptCreate,
  PractitionerCreate,
  QuestionnaireAnswers,
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

export const useSubmitAttempt = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AttemptCreate) => attempts.submit(body),
    onSuccess: (data) => {
      qc.invalidateQueries({
        queryKey: ["practitioners", data.practitioner_id, "skill-profile"],
      });
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

export const useRollups = (params?: {
  scope?: string;
  scope_ref?: string;
}) =>
  useQuery({
    queryKey: ["rollups", params],
    queryFn: () => pulse.rollups(params),
  });
