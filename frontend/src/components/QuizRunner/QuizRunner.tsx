/** QuizRunner — interactive quiz with trap-reveal mechanic. */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useQueries } from "@tanstack/react-query";
import {
  useCertifications,
  useItemsBySkill,
  useLearningPaths,
  usePractitionerAttempts,
  useRetryQuizGeneration,
  useSkills,
  useSubmitAttempt,
} from "../../hooks";
import { items } from "../../api";
import { useSession } from "../../context/SessionContext";
import type { Attempt, MCQAnswerKey, QuizItem } from "../../api/types";

interface Props {
  practitionerId: string;
}

// ── Round-complete interstitial ────────────────────────────────────────────────

function RoundCompleteInterstitial({ onDismiss }: { onDismiss: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 2000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <div
      style={{
        border: "2px solid var(--primary)",
        borderRadius: "var(--radius)",
        padding: "1.5rem",
        background: "color-mix(in srgb, var(--primary) 6%, var(--surface))",
        textAlign: "center",
        animation: "slideIn 0.25s ease",
      }}
    >
      <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>🎯</div>
      <p style={{ fontWeight: 700, fontSize: "1rem", margin: "0 0 0.375rem", color: "var(--primary)" }}>
        Round complete!
      </p>
      <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", margin: "0 0 1rem", lineHeight: 1.5 }}>
        You've answered all available questions for this skill. New challenges are loading…
      </p>
      <button className="btn btn-outline" style={{ fontSize: "0.8125rem" }} onClick={onDismiss}>
        Continue now
      </button>
    </div>
  );
}

// ── Exam relevance badge ───────────────────────────────────────────────────────

function ExamRelevanceBadge({
  item,
  certCode,
}: {
  item: QuizItem;
  certCode?: string | null;
}) {
  if (item.is_cert_evaluated === true) {
    const tooltip =
      certCode && item.certification_domain_name
        ? `Answering this correctly improves your ${certCode} ${item.certification_domain_name} readiness score.`
        : "Answering this correctly improves your certification readiness score.";
    return (
      <span className="badge badge-blue" title={tooltip} style={{ cursor: "help" }}>
        📋 Exam relevant
      </span>
    );
  }
  if (item.is_cert_evaluated === false && item.certification_domain_id) {
    const tooltip = certCode
      ? `This topic supports understanding but isn't directly evaluated in ${certCode}.`
      : "This topic supports understanding but isn't directly evaluated in the certification exam.";
    return (
      <span className="badge badge-gray" title={tooltip} style={{ cursor: "help" }}>
        💡 Good to know
      </span>
    );
  }
  return null;
}

// ── Score impact note ─────────────────────────────────────────────────────────

function ScoreImpactNote({
  item,
  certCode,
  score,
}: {
  item: QuizItem;
  certCode?: string | null;
  score: number;
}) {
  if (item.is_cert_evaluated === true) {
    if (score >= 1) {
      return (
        <p style={{ fontSize: "0.8125rem", color: "var(--success)", margin: "0.625rem 0 0", lineHeight: 1.5 }}>
          ✅ Counts toward your {item.certification_domain_name ?? certCode ?? "certification"} readiness score.
        </p>
      );
    }
    return (
      <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", margin: "0.625rem 0 0", lineHeight: 1.5 }}>
        📋 This question counts toward your {item.certification_domain_name ?? certCode ?? "certification"} exam domain readiness.
      </p>
    );
  }
  if (item.is_cert_evaluated === false) {
    return (
      <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", margin: "0.625rem 0 0", lineHeight: 1.5 }}>
        ℹ️ Builds your understanding. Doesn't change your exam-domain readiness scores.
      </p>
    );
  }
  return null;
}

function TrapRevealPanel({
  trapExplanation,
  graderRationale,
}: {
  trapExplanation: string;
  graderRationale: string;
}) {
  return (
    <div
      data-testid="trap-reveal-panel"
      style={{
        border: "2px solid var(--warning)",
        borderRadius: "var(--radius)",
        padding: "1.25rem",
        background: "color-mix(in srgb, var(--warning) 6%, var(--surface))",
        marginTop: "1rem",
        animation: "slideIn 0.25s ease",
      }}
    >
      <p style={{ fontWeight: 700, margin: "0 0 0.5rem", color: "var(--warning)", fontSize: "0.875rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
        ⚠ Common misconception spotted
      </p>
      <p style={{ margin: "0 0 0.75rem", fontSize: "0.9375rem", lineHeight: 1.6 }}>{trapExplanation}</p>
      <p style={{ margin: 0, fontSize: "0.875rem", color: "var(--text-muted)", lineHeight: 1.5 }}>{graderRationale}</p>
    </div>
  );
}

function CorrectAnswerPanel({ graderRationale }: { graderRationale: string }) {
  return (
    <div
      data-testid="correct-answer-panel"
      style={{
        border: "2px solid var(--success)",
        borderRadius: "var(--radius)",
        padding: "1.25rem",
        background: "color-mix(in srgb, var(--success) 6%, var(--surface))",
        marginTop: "1rem",
      }}
    >
      <p style={{ fontWeight: 700, margin: "0 0 0.5rem", color: "var(--success)", fontSize: "0.875rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
        ✓ Correct
      </p>
      <p style={{ margin: 0, fontSize: "0.875rem", color: "var(--text-muted)", lineHeight: 1.5 }}>{graderRationale}</p>
    </div>
  );
}

function PartialCreditPanel({
  score,
  graderRationale,
}: {
  score: number;
  graderRationale: string;
}) {
  return (
    <div
      style={{
        border: "2px solid var(--primary)",
        borderRadius: "var(--radius)",
        padding: "1.25rem",
        background: "color-mix(in srgb, var(--primary) 6%, var(--surface))",
        marginTop: "1rem",
      }}
    >
      <p style={{ fontWeight: 700, margin: "0 0 0.5rem", color: "var(--primary)", fontSize: "0.875rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
        Partial credit — {(score * 100).toFixed(0)}%
      </p>
      <p style={{ margin: 0, fontSize: "0.875rem", color: "var(--text-muted)", lineHeight: 1.5 }}>{graderRationale}</p>
    </div>
  );
}

// ── Answered accordion ─────────────────────────────────────────────────────────

function AnsweredAccordion({
  answeredItems,
}: {
  answeredItems: { item: QuizItem; idx: number; attempt: Attempt }[];
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  if (answeredItems.length === 0) return null;

  const toggleRow = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div
      style={{
        marginTop: "1.5rem",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius)",
        overflow: "hidden",
      }}
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          width: "100%",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "0.75rem 1rem",
          background: "var(--surface-alt)",
          border: "none",
          cursor: "pointer",
          fontSize: "0.875rem",
          fontWeight: 600,
          color: "var(--text)",
        }}
      >
        <span>Answered ({answeredItems.length})</span>
        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
          {isOpen ? "▲ collapse" : "▼ expand"}
        </span>
      </button>

      {isOpen && (
        <div>
          {answeredItems.map(({ item, idx, attempt }) => {
            const isCorrect = attempt.score === 1;
            const isExpanded = expandedIds.has(item.id);
            const scoreLabel = `${(attempt.score * 100).toFixed(0)}%`;
            const key = item.answer_key as MCQAnswerKey;
            const response = attempt.response as { selected_index?: number; text?: string };
            const selectedText =
              item.item_type === "mcq" &&
              key?.options &&
              response.selected_index != null
                ? key.options[response.selected_index]
                : (response.text ?? "");
            const correctText =
              item.item_type === "mcq" && key?.options
                ? key.options[key.correct_index]
                : null;
            const showTrap = attempt.is_trap_selected === true && !!item.trap_explanation;

            return (
              <div key={item.id} style={{ borderTop: "1px solid var(--border)" }}>
                <button
                  onClick={() => toggleRow(item.id)}
                  style={{
                    width: "100%",
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    padding: "0.625rem 1rem",
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    textAlign: "left",
                    fontSize: "0.8125rem",
                    color: "var(--text)",
                  }}
                >
                  <span
                    style={{
                      color: "var(--text-muted)",
                      fontVariantNumeric: "tabular-nums",
                      minWidth: "2.75rem",
                      flexShrink: 0,
                    }}
                  >
                    [Q{idx + 1}]
                  </span>
                  <span>{isCorrect ? "✅" : "❌"}</span>
                  <span
                    style={{
                      color: isCorrect ? "var(--success)" : "var(--danger)",
                      fontWeight: 600,
                    }}
                  >
                    {isCorrect ? "Correct" : "Incorrect"}
                  </span>
                  <span style={{ color: "var(--text-muted)" }}>—</span>
                  <span style={{ color: "var(--text-muted)" }}>{scoreLabel}</span>
                  <span style={{ marginLeft: "auto", color: "var(--text-muted)", fontSize: "0.75rem" }}>
                    {isExpanded ? "▲" : "▼"}
                  </span>
                </button>

                {isExpanded && (
                  <div
                    style={{
                      padding: "0.75rem 1rem 1rem",
                      background: "var(--surface-alt)",
                      borderTop: "1px solid var(--border)",
                    }}
                  >
                    <p style={{ margin: "0 0 0.625rem", fontSize: "0.875rem", lineHeight: 1.6 }}>
                      <strong>Q:</strong> {item.prompt}
                    </p>
                    <p
                      style={{
                        margin: "0 0 0.375rem",
                        fontSize: "0.8125rem",
                        color: isCorrect ? "var(--success)" : "var(--danger)",
                      }}
                    >
                      <strong>Your answer:</strong> {selectedText}
                    </p>
                    {!isCorrect && correctText && (
                      <p
                        style={{
                          margin: "0 0 0.375rem",
                          fontSize: "0.8125rem",
                          color: "var(--success)",
                        }}
                      >
                        <strong>Correct answer:</strong> {correctText}
                      </p>
                    )}
                    {showTrap && (
                      <div
                        style={{
                          marginTop: "0.625rem",
                          padding: "0.625rem",
                          background: "color-mix(in srgb, var(--warning) 8%, var(--surface))",
                          border: "1px solid var(--warning)",
                          borderRadius: "var(--radius)",
                          fontSize: "0.8125rem",
                          lineHeight: 1.5,
                        }}
                      >
                        <strong style={{ color: "var(--warning)" }}>⚠ Trap:</strong>{" "}
                        {item.trap_explanation}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── MCQ item ──────────────────────────────────────────────────────────────────

function MCQItem({
  item,
  attempt,
  onSubmit,
  isPending,
  certCode,
}: {
  item: QuizItem;
  attempt: Attempt | null;
  onSubmit: (selectedIndex: number) => void;
  isPending: boolean;
  certCode?: string | null;
}) {
  const [selected, setSelected] = useState<number | null>(null);
  const key = item.answer_key as MCQAnswerKey;

  if (!key?.options || key.options.length === 0) {
    return (
      <div className="empty-state">
        Answer options unavailable for this item. Regenerate your learning path
        to replace it with a fresh question.
      </div>
    );
  }

  const optionStyle = (i: number): React.CSSProperties => {
    if (!attempt) return {};
    const isCorrect = i === key.correct_index;
    const isSelected = i === (attempt.response as { selected_index: number }).selected_index;
    if (isCorrect)
      return {
        borderColor: "var(--success)",
        background: "color-mix(in srgb, var(--success) 8%, var(--surface))",
      };
    if (isSelected && !isCorrect)
      return {
        borderColor: "var(--danger)",
        background: "color-mix(in srgb, var(--danger) 8%, var(--surface))",
      };
    return {};
  };

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        <ExamRelevanceBadge item={item} certCode={certCode} />
        <span className="badge badge-blue">{item.item_type.toUpperCase()}</span>
        <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
          Difficulty {(item.difficulty * 100).toFixed(0)}%
        </span>
      </div>
      <p style={{ fontSize: "1rem", lineHeight: 1.65, marginBottom: "1.25rem" }}>{item.prompt}</p>
      <div className="radio-group">
        {key.options.map((opt, i) => (
          <label
            key={i}
            className={`radio-option${selected === i && !attempt ? " selected" : ""}`}
            style={optionStyle(i)}
          >
            <input
              type="radio"
              name={`item-${item.id}`}
              value={i}
              disabled={!!attempt}
              checked={selected === i}
              onChange={() => setSelected(i)}
            />
            <span style={{ fontSize: "0.9375rem" }}>{opt}</span>
          </label>
        ))}
      </div>

      {!attempt && (
        <button
          className="btn btn-primary"
          style={{ marginTop: "1.25rem" }}
          disabled={selected === null || isPending}
          onClick={() => selected !== null && onSubmit(selected)}
        >
          {isPending ? <><span className="spinner" /> Grading…</> : "Submit answer"}
        </button>
      )}

      {attempt && (
        <>
          {attempt.is_trap_selected && item.trap_explanation ? (
            <TrapRevealPanel
              trapExplanation={item.trap_explanation}
              graderRationale={attempt.grader_rationale}
            />
          ) : attempt.score === 1 ? (
            <CorrectAnswerPanel graderRationale={attempt.grader_rationale} />
          ) : (
            <PartialCreditPanel score={attempt.score} graderRationale={attempt.grader_rationale} />
          )}
          <ScoreImpactNote item={item} certCode={certCode} score={attempt.score} />
        </>
      )}
    </div>
  );
}

// ── Free-text item ─────────────────────────────────────────────────────────────

function FreeTextItem({
  item,
  attempt,
  onSubmit,
  isPending,
  certCode,
}: {
  item: QuizItem;
  attempt: Attempt | null;
  onSubmit: (text: string) => void;
  isPending: boolean;
  certCode?: string | null;
}) {
  const [text, setText] = useState("");

  return (
    <div>
      <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1rem", flexWrap: "wrap", alignItems: "center" }}>
        <ExamRelevanceBadge item={item} certCode={certCode} />
        <span className="badge badge-gray">{item.item_type.replace("_", " ").toUpperCase()}</span>
        <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
          Difficulty {(item.difficulty * 100).toFixed(0)}%
        </span>
      </div>
      <p style={{ fontSize: "1rem", lineHeight: 1.65, marginBottom: "1.25rem" }}>{item.prompt}</p>
      <textarea
        className="form-control"
        rows={5}
        disabled={!!attempt}
        value={attempt ? String((attempt.response as { text: string }).text ?? "") : text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Write your answer here…"
        style={{ resize: "vertical" }}
      />
      {!attempt && (
        <button
          className="btn btn-primary"
          style={{ marginTop: "0.75rem" }}
          disabled={!text.trim() || isPending}
          onClick={() => onSubmit(text.trim())}
        >
          {isPending ? <><span className="spinner" /> Grading…</> : "Submit answer"}
        </button>
      )}
      {attempt && (
        <>
          {attempt.score === 1 ? (
            <CorrectAnswerPanel graderRationale={attempt.grader_rationale} />
          ) : (
            <PartialCreditPanel score={attempt.score} graderRationale={attempt.grader_rationale} />
          )}
          <ScoreImpactNote item={item} certCode={certCode} score={attempt.score} />
        </>
      )}
    </div>
  );
}

// ── SkillItemQuiz — quiz for a single skill ───────────────────────────────────

function SkillItemQuiz({
  practitionerId,
  skillId,
  skillName,
  certCode,
  attemptsByItemId,
}: {
  practitionerId: string;
  skillId: string;
  skillName: string;
  certCode?: string | null;
  /** Passed from parent QuizRunner — built from usePractitionerAttempts (deduped). */
  attemptsByItemId: Record<string, Attempt>;
}) {
  // useItemsBySkill is deduped with QuizRunner's useQueries call (same cache key).
  const { data: rawSkillItems, isLoading: itemsLoading } = useItemsBySkill(skillId);
  const submitAttempt = useSubmitAttempt(practitionerId);
  const [itemIndex, setItemIndex] = useState(0);
  const [showRoundComplete, setShowRoundComplete] = useState(false);
  const [showAllAnswered, setShowAllAnswered] = useState(false);

  const skillItems = rawSkillItems as QuizItem[] | undefined;

  const generationRefreshed = skillItems?.some((it) => it.generation_refreshed === true) ?? false;

  useEffect(() => {
    if (generationRefreshed) setShowRoundComplete(true);
  }, [generationRefreshed]);

  // Reset "all remaining answered" message whenever the user navigates to a different item.
  useEffect(() => {
    setShowAllAnswered(false);
  }, [itemIndex]);

  if (itemsLoading)
    return (
      <div style={{ textAlign: "center", padding: "2rem" }}>
        <span className="spinner" />
      </div>
    );

  if (!skillItems || skillItems.length === 0)
    return (
      <div className="empty-state">
        No question yet for <strong>{skillName}</strong>. Refreshing…
      </div>
    );

  if (showRoundComplete) {
    return <RoundCompleteInterstitial onDismiss={() => setShowRoundComplete(false)} />;
  }

  const item = skillItems[itemIndex];
  const attempt = attemptsByItemId[item.id] ?? null;
  const currentGeneration = item.generation;

  // Items belonging to the current round only — drives the "X / Y" counter so
  // that Round 3 shows "1 / 3" not "7 / 9" (cumulative across all rounds).
  const currentRoundItems = skillItems.filter(
    (it) => it.generation === currentGeneration,
  );
  const currentRoundIndex = currentRoundItems.findIndex((it) => it.id === item.id);

  // All answered items for this skill — used by the accordion below.
  const answeredItems = skillItems
    .map((it, idx) => ({ item: it, idx, attempt: attemptsByItemId[it.id] ?? null }))
    .filter((x): x is { item: QuizItem; idx: number; attempt: Attempt } => x.attempt !== null);

  const handleSubmit = async (response: { selected_index: number } | { text: string }) => {
    await submitAttempt.mutateAsync({
      practitioner_id: practitionerId,
      item_id: item.id,
      response,
    });
  };

  const handleNext = () => {
    // Find next unanswered item after the current index.
    const nextUnanswered = skillItems.findIndex(
      (itm, idx) => idx > itemIndex && !attemptsByItemId[itm.id],
    );
    if (nextUnanswered !== -1) {
      setItemIndex(nextUnanswered);
    } else {
      // All remaining items are answered — show message, do NOT navigate.
      setShowAllAnswered(true);
    }
  };

  return (
    <div>
      {/* Header row */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1.25rem",
          flexWrap: "wrap",
          gap: "0.5rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.625rem" }}>
          <h3 style={{ margin: 0 }}>{skillName}</h3>
          {currentGeneration != null && currentGeneration > 1 && (
            <span
              style={{
                fontSize: "0.75rem",
                padding: "0.1rem 0.45rem",
                borderRadius: "999px",
                background: "var(--surface-alt)",
                border: "1px solid var(--border)",
                color: "var(--text-muted)",
                fontVariantNumeric: "tabular-nums",
              }}
            >
              Round {currentGeneration}
            </span>
          )}
        </div>
        <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
          {currentRoundIndex + 1} / {currentRoundItems.length}
        </span>
      </div>

      {/* Active question */}
      {item.item_type === "mcq" ? (
        <MCQItem
          key={item.id}
          item={item}
          attempt={attempt}
          onSubmit={(idx) => handleSubmit({ selected_index: idx })}
          isPending={submitAttempt.isPending}
          certCode={certCode}
        />
      ) : (
        <FreeTextItem
          key={item.id}
          item={item}
          attempt={attempt}
          onSubmit={(text) => handleSubmit({ text })}
          isPending={submitAttempt.isPending}
          certCode={certCode}
        />
      )}

      {/* Next button — only shown when current item is answered and not at the last position */}
      {attempt && itemIndex < skillItems.length - 1 && !showAllAnswered && (
        <button
          className="btn btn-outline"
          style={{ marginTop: "1.25rem" }}
          onClick={handleNext}
        >
          Next question →
        </button>
      )}

      {/* All-remaining-answered message */}
      {showAllAnswered && (
        <p style={{ marginTop: "1.25rem", color: "var(--text-muted)", fontSize: "0.875rem" }}>
          All answered — regenerate path to get new questions.
        </p>
      )}

      {/* Last-item completion message */}
      {attempt && itemIndex === skillItems.length - 1 && !showAllAnswered && (
        <p style={{ marginTop: "1.25rem", color: "var(--text-muted)", fontSize: "0.875rem" }}>
          You've completed all items for this skill.
        </p>
      )}

      {/* Answered questions accordion — below the active question card */}
      <AnsweredAccordion answeredItems={answeredItems} />
    </div>
  );
}

// ── Quiz-status badge glyphs ────────────────────────────────────────────────────

function quizStatusGlyph(status: "pending" | "ready" | "failed") {
  if (status === "ready") return null;   // clean — no badge needed once ready
  if (status === "failed") return "⚠️";
  return "⏳";  // pending
}

// ── Main QuizRunner ────────────────────────────────────────────────────────────

export default function QuizRunner({ practitionerId }: Props) {
  const { data: allSkills } = useSkills();
  const { data: certList } = useCertifications();
  const { data: allAttempts } = usePractitionerAttempts(practitionerId);
  const { session } = useSession();
  const [selectedSkillId, setSelectedSkillId] = useState<string | null>(null);
  const certCode = session?.active_certification_code ?? null;

  const { mutate: retryGeneration, isPending: retryPending } = useRetryQuizGeneration(practitionerId);

  // ── Skill name & cert-membership lookups ──────────────────────────────────
  const skillNameById = useMemo(() => {
    const map = new Map<string, string>();
    allSkills?.forEach((s) => map.set(s.id, s.name));
    return map;
  }, [allSkills]);

  const certSkillIds = useMemo(() => {
    const ids = new Set<string>();
    const code = session?.active_certification_code;
    if (!code || !certList) return ids;
    const cert = certList.find((c) => c.code === code);
    cert?.certification_skills.forEach((cs) => ids.add(cs.skill_id));
    return ids;
  }, [certList, session?.active_certification_code]);

  // ── Paths with polling — poll every 5s while any skill is pending ─────────
  //
  // refetchInterval receives the raw Query object in TanStack v5; we pull
  // `.state.data` (typed as unknown) and cast it ourselves.
  const refetchInterval = useCallback((query: unknown) => {
    const data = (query as { state?: { data?: unknown } })?.state?.data as
      | { items?: { quiz_status?: string }[] }[]
      | undefined;
    // Check every path, every item — we must not assume the active path is [0].
    // If any item in any path is pending we need to keep polling every 5 s.
    const anyPending = data?.some((path) =>
      path.items?.some((it) => it.quiz_status === "pending"),
    );
    return anyPending ? 5000 : (false as const);
  }, []);

  const { data: paths, isLoading: pathsLoading } = useLearningPaths(
    practitionerId,
    refetchInterval,
  );

  // ── Attempt map ───────────────────────────────────────────────────────────
  const attemptsByItemId = useMemo(() => {
    const map: Record<string, Attempt> = {};
    allAttempts?.forEach((a) => {
      if (!map[a.item_id]) map[a.item_id] = a;
    });
    return map;
  }, [allAttempts]);

  // ── pathSkills — cert-first, includes quiz_status ─────────────────────────
  // Must be computed BEFORE early returns so useQueries hook count is stable.
  const pathSkills = useMemo(() => {
    const activePath = paths?.find((p) => p.status === "active") ?? paths?.[0];
    if (!activePath || activePath.items.length === 0) return [];
    const rawPathSkills = activePath.items.reduce<
      { id: string; name: string; isCert: boolean; quizStatus: "pending" | "ready" | "failed" }[]
    >((acc, item) => {
      if (!acc.find((s) => s.id === item.skill_id)) {
        acc.push({
          id: item.skill_id,
          name: skillNameById.get(item.skill_id) ?? `Skill ${item.skill_id.slice(0, 8)}`,
          isCert: certSkillIds.has(item.skill_id),
          quizStatus: item.quiz_status ?? "pending",
        });
      }
      return acc;
    }, []);
    return [
      ...rawPathSkills.filter((s) => s.isCert),
      ...rawPathSkills.filter((s) => !s.isCert),
    ];
  }, [paths, skillNameById, certSkillIds]);

  // ── Prefetch items for all ready skills ───────────────────────────────────
  const skillItemQueries = useQueries({
    queries: pathSkills.map((s) => ({
      queryKey: ["items", "skill", s.id] as const,
      queryFn: () => items.listBySkill(s.id),
      // Only fetch items once questions are ready (avoid 404-ish empty returns for pending skills)
      enabled: s.quizStatus === "ready",
    })),
  });

  // ── Per-skill tab progress ────────────────────────────────────────────────
  const skillProgressById = useMemo(() => {
    const map: Record<string, { answered: number; total: number }> = {};
    pathSkills.forEach((s, i) => {
      const skillItems = (skillItemQueries[i]?.data as QuizItem[] | undefined) ?? [];
      const answered = skillItems.filter((it) => !!attemptsByItemId[it.id]).length;
      map[s.id] = { answered, total: skillItems.length };
    });
    return map;
  }, [pathSkills, skillItemQueries, attemptsByItemId]);

  const anyFailed = pathSkills.some((s) => s.quizStatus === "failed");

  const activePath = paths?.find((p) => p.status === "active") ?? paths?.[0];

  // ── Early returns (after all hooks) ──────────────────────────────────────
  if (pathsLoading) {
    return (
      <div style={{ textAlign: "center", padding: "3rem" }}>
        <span className="spinner" />
      </div>
    );
  }

  if (!activePath || activePath.items.length === 0) {
    return (
      <div className="empty-state">
        <p>No learning path yet. Generate one from the Skill Radar tab first.</p>
      </div>
    );
  }

  const defaultSkillId = (pathSkills.find((s) => s.isCert) ?? pathSkills[0])?.id ?? null;
  const active = selectedSkillId ?? defaultSkillId;

  const certSkills = pathSkills.filter((s) => s.isCert);
  const suppSkills = pathSkills.filter((s) => !s.isCert);
  const hasBothGroups = certSkills.length > 0 && suppSkills.length > 0;

  // ── Skill tab renderer (shared between cert and supp groups) ─────────────
  function SkillTab({
    s,
    isCertStyle,
  }: {
    s: { id: string; name: string; isCert: boolean; quizStatus: "pending" | "ready" | "failed" };
    isCertStyle: boolean;
  }) {
    const prog = skillProgressById[s.id];
    const isActive = active === s.id;
    const glyph = quizStatusGlyph(s.quizStatus);

    // Colour override for failed skills
    const failedStyle =
      s.quizStatus === "failed" && !isActive
        ? { borderColor: "var(--warning)", color: "var(--warning)", opacity: 0.9 }
        : {};

    // Pulse animation class for pending skills
    const pendingClass = s.quizStatus === "pending" && !isActive ? " quiz-tab-pending" : "";

    return (
      <button
        key={s.id}
        className={`btn ${isActive ? "btn-primary" : "btn-outline"}${pendingClass}`}
        onClick={() => setSelectedSkillId(s.id)}
        title={
          s.quizStatus === "pending"
            ? "Questions are being prepared…"
            : s.quizStatus === "failed"
            ? "Question generation failed — click ↻ Retry above to try again"
            : undefined
        }
        style={
          isCertStyle && !isActive
            ? { borderColor: "var(--primary)", color: "var(--primary)", ...failedStyle }
            : failedStyle
        }
      >
        {glyph && <span style={{ marginRight: "0.25rem" }}>{glyph}</span>}
        {s.name}
        {prog && prog.total > 0 && (
          <span
            style={{
              marginLeft: "0.35rem",
              fontSize: "0.7rem",
              color: isActive ? "rgba(255,255,255,0.7)" : "var(--text-muted)",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            ({prog.answered}/{prog.total})
          </span>
        )}
        {isCertStyle && (
          <span
            style={{
              marginLeft: "0.4rem",
              fontSize: "0.6rem",
              padding: "0.1rem 0.35rem",
              borderRadius: "999px",
              background: isActive ? "rgba(255,255,255,0.28)" : "var(--primary)",
              color: "#fff",
              fontWeight: 700,
              letterSpacing: "0.03em",
              verticalAlign: "middle",
            }}
          >
            EXAM
          </span>
        )}
        {!isCertStyle && (
          <span
            style={{
              marginLeft: "0.4rem",
              fontSize: "0.6rem",
              padding: "0.1rem 0.35rem",
              borderRadius: "999px",
              background: isActive ? "rgba(255,255,255,0.18)" : "var(--surface-alt)",
              color: isActive ? "rgba(255,255,255,0.85)" : "var(--text-muted)",
              border: isActive ? "none" : "1px solid var(--border)",
              fontWeight: 600,
              letterSpacing: "0.02em",
              verticalAlign: "middle",
            }}
          >
            SUPP
          </span>
        )}
      </button>
    );
  }

  // ── Active skill pane ─────────────────────────────────────────────────────
  const activeSkill = pathSkills.find((s) => s.id === active);

  return (
    <div>
      <h2>Quiz</h2>
      <p style={{ color: "var(--text-muted)", marginBottom: "1rem", fontSize: "0.875rem" }}>
        Practice questions for your active learning path. Select a skill to begin.
      </p>

      {/* ── Retry banner — shown when any skill failed ── */}
      {anyFailed && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
            marginBottom: "1rem",
            padding: "0.625rem 1rem",
            borderRadius: "var(--radius)",
            border: "1px solid var(--warning)",
            background: "color-mix(in srgb, var(--warning) 8%, var(--surface))",
            fontSize: "0.875rem",
          }}
        >
          <span>⚠️ Some skills couldn't generate questions.</span>
          <button
            className="btn btn-outline"
            style={{ fontSize: "0.8125rem", borderColor: "var(--warning)", color: "var(--warning)" }}
            disabled={retryPending}
            onClick={() => retryGeneration()}
          >
            {retryPending ? <><span className="spinner" style={{ width: "0.75rem", height: "0.75rem" }} /> Retrying…</> : "↻ Retry Failed Skills"}
          </button>
        </div>
      )}

      {/* ── Skill selector ── */}
      <div style={{ marginBottom: "1.5rem" }}>
        {certSkills.length > 0 && (
          <>
            {hasBothGroups && (
              <p
                style={{
                  fontSize: "0.7rem",
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  color: "var(--primary)",
                  margin: "0 0 0.4rem",
                }}
              >
                📋 Exam-critical
              </p>
            )}
            <div
              style={{
                display: "flex",
                gap: "0.5rem",
                flexWrap: "wrap",
                marginBottom: hasBothGroups ? "0.75rem" : "0",
              }}
            >
              {certSkills.map((s) => (
                <SkillTab key={s.id} s={s} isCertStyle={true} />
              ))}
            </div>
          </>
        )}

        {hasBothGroups && (
          <div
            style={{ display: "flex", alignItems: "center", gap: "0.5rem", margin: "0.25rem 0 0.6rem" }}
          >
            <hr style={{ flex: 1, border: "none", borderTop: "1px dashed var(--border)", margin: 0 }} />
            <span
              style={{
                fontSize: "0.65rem",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                color: "var(--text-muted)",
                whiteSpace: "nowrap",
              }}
            >
              💡 Good to know ↓
            </span>
            <hr style={{ flex: 1, border: "none", borderTop: "1px dashed var(--border)", margin: 0 }} />
          </div>
        )}

        {suppSkills.length > 0 && (
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            {suppSkills.map((s) => (
              <SkillTab key={s.id} s={s} isCertStyle={false} />
            ))}
          </div>
        )}
      </div>

      {/* ── Active skill pane ── */}
      {active && (
        <div className="card">
          {activeSkill?.quizStatus === "pending" ? (
            <div style={{ textAlign: "center", padding: "2.5rem 1rem" }}>
              <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>⏳</div>
              <p style={{ fontWeight: 600, margin: "0 0 0.375rem" }}>Questions are baking…</p>
              <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", margin: "0 0 1rem" }}>
                We're preparing questions for <strong>{activeSkill.name}</strong> in the background.
                This tab will light up automatically when they're ready.
              </p>
              <button
                className="btn btn-outline"
                style={{ fontSize: "0.8125rem" }}
                disabled={retryPending}
                onClick={() => retryGeneration()}
              >
                {retryPending ? "Retrying…" : "↻ Stuck? Retry generation"}
              </button>
            </div>
          ) : activeSkill?.quizStatus === "failed" ? (
            <div style={{ textAlign: "center", padding: "2.5rem 1rem" }}>
              <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>⚠️</div>
              <p style={{ fontWeight: 600, margin: "0 0 0.375rem" }}>Generation failed</p>
              <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", margin: "0 0 1rem" }}>
                Couldn't prepare questions for <strong>{activeSkill.name}</strong> — the AI provider
                was unavailable. Use the retry button above to try again.
              </p>
              <button
                className="btn btn-outline"
                style={{ fontSize: "0.8125rem", borderColor: "var(--warning)", color: "var(--warning)" }}
                disabled={retryPending}
                onClick={() => retryGeneration()}
              >
                {retryPending ? "Retrying…" : "↻ Retry now"}
              </button>
            </div>
          ) : (
            /* quiz_status === "ready" — render the quiz */
            <SkillItemQuiz
              key={active}
              practitionerId={practitionerId}
              skillId={active}
              skillName={pathSkills.find((s) => s.id === active)?.name ?? active}
              certCode={certCode}
              attemptsByItemId={attemptsByItemId}
            />
          )}
        </div>
      )}
    </div>
  );
}
