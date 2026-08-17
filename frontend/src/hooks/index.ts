/** TanStack Query hooks for every domain. */

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  attempts,
  certDomains,
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
  MockExamQuestion,
  MockExamSession,
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

export const useLearningPaths = (
  practitioner_id: string,
  /** Phase 17.10: optional poll interval (ms) or false to disable; supports callback form */
  refetchInterval?: number | false | ((data: unknown) => number | false),
) =>
  useQuery({
    queryKey: ["practitioners", practitioner_id, "learning-paths"],
    queryFn: () => learningPaths.list(practitioner_id),
    enabled: !!practitioner_id,
    ...(refetchInterval !== undefined && { refetchInterval }),
  });

export const useGenerateLearningPath = (practitioner_id: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => learningPaths.generate(practitioner_id),
    onSuccess: () => {
      // The workflow re-runs Skill Profiler as its first step, so both the
      // skill-profile snapshot and the learning-path list need to be refreshed.
      // Phase 17: quiz batch is now generated as part of path generation, so
      // invalidate items so the Quiz tab picks up new questions immediately.
      qc.invalidateQueries({
        queryKey: ["practitioners", practitioner_id, "learning-paths"],
      });
      qc.invalidateQueries({
        queryKey: ["practitioners", practitioner_id, "skill-profile"],
      });
      qc.invalidateQueries({ queryKey: ["items"] });
    },
  });
};

/**
 * Phase 17.8: admin override — kept for manual/debugging use only.
 * Normal generation goes through useGenerateLearningPath → background task.
 */
export const useGenerateQuizBatch = (practitioner_id: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (path_id: string) =>
      learningPaths.generateQuizBatch(practitioner_id, path_id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["items"] });
      qc.invalidateQueries({
        queryKey: ["practitioners", practitioner_id, "learning-paths"],
      });
    },
  });
};

/**
 * Phase 17.9: retry quiz generation for all skills with status="failed".
 * After mutation succeeds the learning-paths list is invalidated so the
 * QuizRunner picks up the updated quiz_status values via its polling loop.
 */
export const useRetryQuizGeneration = (practitioner_id: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => learningPaths.retryQuizGeneration(practitioner_id),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["practitioners", practitioner_id, "learning-paths"],
      });
      qc.invalidateQueries({ queryKey: ["items"] });
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

// ── Certification Domain Scores (Phase 10) ────────────────────────────────────

export const useCertDomainScores = (
  practitionerId: string,
  certificationId: string | undefined,
) =>
  useQuery({
    queryKey: ["cert-domain-scores", practitionerId, certificationId],
    queryFn: () => practitioners.certDomainScores(practitionerId, certificationId!),
    enabled: !!practitionerId && !!certificationId,
  });

// ── Cert Domain Admin Hooks (Phase 10) ───────────────────────────────────────

export const useCertDomainVersions = () =>
  useQuery({
    queryKey: ["cert-domain-versions"],
    queryFn: certDomains.listVersions,
  });

export const useCertDomainProposals = (status?: string) =>
  useQuery({
    queryKey: ["cert-domain-proposals", status],
    queryFn: () => certDomains.listProposals(status),
  });

export const useTriggerCertDomainDiscover = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      certCode,
      certName,
      providerName,
      knownSourceUrl,
      refreshReason,
    }: {
      certCode: string;
      certName: string;
      providerName: string;
      knownSourceUrl?: string;
      refreshReason?: string;
    }) => certDomains.discover(certCode, certName, providerName, knownSourceUrl, refreshReason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cert-domain-proposals"] });
    },
  });
};

export const useTriggerCertDomainDiscoverAll = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: certDomains.discoverAll,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cert-domain-proposals"] });
    },
  });
};

export const useApproveCertDomainProposal = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (proposalId: string) => certDomains.approveProposal(proposalId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cert-domain-proposals"] });
      qc.invalidateQueries({ queryKey: ["cert-domain-versions"] });
    },
  });
};

export const useRejectCertDomainProposal = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ proposalId, rejectionNotes }: { proposalId: string; rejectionNotes: string }) =>
      certDomains.rejectProposal(proposalId, rejectionNotes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cert-domain-proposals"] });
    },
  });
};

// ── Mock Exam (Part B) ─────────────────────────────────────────────────────────

export const useStartMockExam = (practitionerId: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => practitioners.mockExams.start(practitionerId),
    onSuccess: (data) => {
      qc.setQueryData(["mock-exam-active", practitionerId], data);
      qc.setQueryData(["mock-exam-session", data.id], data);
    },
  });
};

export const useActiveMockExam = (
  practitionerId: string,
  /** Pass false to skip the query entirely (e.g. when mastery < 80 %). */
  queryEnabled: boolean = true,
) =>
  useQuery<MockExamSession | null>({
    queryKey: ["mock-exam-active", practitionerId],
    queryFn: async () => {
      try {
        return await practitioners.mockExams.getActive(practitionerId);
      } catch (err: unknown) {
        // 404 = no active session — return null so callers get data===null,
        // not an error state.  All other errors propagate normally.
        if (err && typeof err === "object" && (err as { status?: number }).status === 404) {
          return null;
        }
        throw err;
      }
    },
    enabled: !!practitionerId && queryEnabled,
    // No retries on 404-turned-null; limit retries on genuine errors
    retry: (failureCount, error) => {
      if (error && typeof error === "object" && (error as { status?: number }).status === 404) return false;
      return failureCount < 2;
    },
    // Keep data fresh for 30 s — avoids hammering the server on every focus event
    staleTime: 30_000,
    refetchInterval: (query) => {
      const data = query.state.data as MockExamSession | null | undefined;
      // Only poll while an exam is actively running (timer ticking)
      return data?.status === "in_progress" ? 2000 : false;
    },
  });

export const useMockExamSession = (practitionerId: string, sessionId: string) =>
  useQuery({
    queryKey: ["mock-exam-session", sessionId],
    queryFn: () => practitioners.mockExams.getById(practitionerId, sessionId),
    enabled: !!practitionerId && !!sessionId,
  });

export const usePauseMockExam = (practitionerId: string, sessionId: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => practitioners.mockExams.pause(practitionerId, sessionId),
    onSuccess: (data) => {
      qc.setQueryData(["mock-exam-active", practitionerId], data);
      qc.setQueryData(["mock-exam-session", sessionId], data);
    },
  });
};

export const useResumeMockExam = (practitionerId: string, sessionId: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => practitioners.mockExams.resume(practitionerId, sessionId),
    onSuccess: (data) => {
      qc.setQueryData(["mock-exam-active", practitionerId], data);
      qc.setQueryData(["mock-exam-session", sessionId], data);
    },
  });
};

export const useAnswerMockExamQuestion = (practitionerId: string, sessionId: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ questionId, selectedIndex }: { questionId: string; selectedIndex: number }) =>
      practitioners.mockExams.answer(practitionerId, sessionId, questionId, selectedIndex),
    onSuccess: (updatedQuestion: MockExamQuestion) => {
      const patchSession = (old: MockExamSession | undefined) => {
        if (!old) return old;
        return {
          ...old,
          questions: old.questions.map((q) =>
            q.id === updatedQuestion.id ? updatedQuestion : q
          ),
        };
      };
      qc.setQueryData<MockExamSession>(["mock-exam-session", sessionId], patchSession);
      qc.setQueryData<MockExamSession>(["mock-exam-active", practitionerId], patchSession);
    },
  });
};

export const useCompleteMockExam = (practitionerId: string, sessionId: string) => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => practitioners.mockExams.complete(practitionerId, sessionId),
    onSuccess: (data) => {
      qc.setQueryData(["mock-exam-session", sessionId], data);
      qc.invalidateQueries({ queryKey: ["mock-exam-active", practitionerId] });
    },
  });
};
