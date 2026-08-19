/**
 * MockExamPage — full-screen timed mock certification exam.
 *
 * Opened in a new browser tab at /mock-exam/:sessionId.
 * All state comes from the server session — no localStorage.
 */

import { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  useAnswerMockExamQuestion,
  useAbandonMockExam,
  useCompleteMockExam,
  useMockExamSession,
  usePauseMockExam,
  useResumeMockExam,
} from "../hooks";
import { useSession } from "../context/SessionContext";
import type { MockExamQuestion, MockExamSession } from "../api/types";

// ── Timer ─────────────────────────────────────────────────────────────────────

function useExamTimer(initialSeconds: number, running: boolean): number {
  const [elapsed, setElapsed] = useState(initialSeconds);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (running) {
      intervalRef.current = setInterval(() => setElapsed((s) => s + 1), 1000);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [running]);

  useEffect(() => {
    setElapsed(initialSeconds);
  }, [initialSeconds]);

  return elapsed;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

// ── Score screen ──────────────────────────────────────────────────────────────

function ScoreScreen({ session }: { session: MockExamSession }) {
  const scorePct = session.score != null ? Math.round(session.score * 100) : null;
  const passPct = session.exam_passing_score_pct;
  const passed = scorePct != null && scorePct >= passPct;

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--surface)",
        flexDirection: "column",
        gap: "1.5rem",
        padding: "2rem",
        textAlign: "center",
      }}
    >
      <div
        style={{
          fontSize: "5rem",
          fontWeight: 800,
          lineHeight: 1,
          color: passed ? "var(--success)" : "var(--danger)",
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {scorePct != null ? `${scorePct}%` : "—"}
      </div>

      <div
        style={{
          display: "inline-block",
          padding: "0.4rem 1.25rem",
          borderRadius: "999px",
          background: passed
            ? "color-mix(in srgb, var(--success) 14%, var(--surface))"
            : "color-mix(in srgb, var(--danger) 14%, var(--surface))",
          border: `2px solid ${passed ? "var(--success)" : "var(--danger)"}`,
          fontWeight: 700,
          fontSize: "1.125rem",
          color: passed ? "var(--success)" : "var(--danger)",
        }}
      >
        {passed ? "PASS" : "FAIL"}
      </div>

      <p style={{ fontSize: "1rem", color: "var(--text-muted)", margin: 0 }}>
        You answered{" "}
        <strong style={{ color: "var(--text)" }}>
          {session.correct_count ?? "?"}/{session.total_count}
        </strong>{" "}
        correctly
      </p>

      <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", margin: 0 }}>
        Exam saved to your Adoption Trend.
      </p>

      <Link
        to="/"
        style={{
          marginTop: "0.5rem",
          fontSize: "0.9375rem",
          color: "var(--primary)",
          textDecoration: "none",
          fontWeight: 500,
        }}
      >
        ← Return to Mastery Pulse
      </Link>
    </div>
  );
}

// ── Generating screen ─────────────────────────────────────────────────────────

function GeneratingScreen({ session }: { session: MockExamSession }) {
  const ready = session.questions.length;
  const total = session.exam_question_count;
  const pct = total > 0 ? Math.round((ready / total) * 100) : 0;

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        gap: "1.5rem",
        padding: "2rem",
        textAlign: "center",
        background: "var(--surface)",
      }}
    >
      <span className="spinner" style={{ width: 40, height: 40, borderWidth: 4 }} />
      <h2 style={{ margin: 0 }}>Generating Your Exam…</h2>
      <p style={{ color: "var(--text-muted)", margin: 0, fontSize: "0.9375rem" }}>
        {session.certification_name} ({session.certification_code})
      </p>
      <p style={{ color: "var(--text-muted)", margin: 0, fontSize: "0.875rem" }}>
        {ready > 0
          ? `${ready} of ${total} questions ready (${pct}%)`
          : "Starting question generation — this takes about 30–60 s…"}
      </p>
      {ready > 0 && (
        <div
          style={{
            width: "min(320px, 90vw)",
            height: 6,
            borderRadius: 3,
            background: "var(--border)",
          }}
        >
          <div
            style={{
              height: "100%",
              borderRadius: 3,
              width: `${pct}%`,
              background: "var(--primary)",
              transition: "width 0.5s ease",
            }}
          />
        </div>
      )}
    </div>
  );
}

// ── Failed screen ──────────────────────────────────────────────────────────────

function FailedScreen() {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        gap: "1.25rem",
        padding: "2rem",
        textAlign: "center",
        background: "var(--surface)",
      }}
    >
      <div style={{ fontSize: "3rem" }}>⚠️</div>
      <h2 style={{ margin: 0 }}>Exam Generation Failed</h2>
      <p style={{ color: "var(--text-muted)", margin: 0, fontSize: "0.9375rem", maxWidth: 400 }}>
        Something went wrong while generating your exam questions. Please return
        to Mastery Pulse and try again.
      </p>
      <Link
        to="/"
        style={{
          marginTop: "0.5rem",
          fontSize: "0.9375rem",
          color: "var(--primary)",
          textDecoration: "none",
          fontWeight: 500,
        }}
      >
        ← Return to Mastery Pulse
      </Link>
    </div>
  );
}

// ── Paused screen ─────────────────────────────────────────────────────────────

function PausedScreen({
  session,
  onResume,
  isResuming,
}: {
  session: MockExamSession;
  onResume: () => void;
  isResuming: boolean;
}) {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        gap: "1.5rem",
        padding: "2rem",
        textAlign: "center",
        background: "var(--surface)",
      }}
    >
      <div style={{ fontSize: "3rem" }}>⏸</div>
      <h2 style={{ margin: 0 }}>Exam Paused</h2>
      <p style={{ color: "var(--text-muted)", margin: 0, fontSize: "0.9375rem" }}>
        {session.certification_name} · {session.certification_code}
      </p>
      <button
        className="btn btn-primary btn-3d"
        disabled={isResuming}
        onClick={onResume}
        style={{ fontSize: "1rem", padding: "0.75rem 2rem" }}
      >
        {isResuming ? <><span className="spinner" /> Resuming…</> : "Resume Exam →"}
      </button>
    </div>
  );
}

// ── Left navigation panel ─────────────────────────────────────────────────────

function LeftNavPanel({
  questions,
  currentIndex,
  onSelect,
  flaggedIds,
}: {
  questions: MockExamQuestion[];
  currentIndex: number;
  onSelect: (idx: number) => void;
  flaggedIds: Set<string>;
}) {
  return (
    <div
      style={{
        width: 210,
        flexShrink: 0,
        borderRight: "1px solid var(--border)",
        overflowY: "auto",
        padding: "0.875rem 0.75rem",
        background: "var(--surface)",
      }}
    >
      <p
        style={{
          fontSize: "0.6875rem",
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.07em",
          color: "var(--text-muted)",
          margin: "0 0 0.625rem 0.125rem",
        }}
      >
        Questions
      </p>

      {/* Legend */}
      <div
        style={{
          display: "flex",
          gap: "0.5rem",
          marginBottom: "0.75rem",
          flexWrap: "wrap",
        }}
      >
        {[
          { color: "var(--success)", label: "Correct" },
          { color: "var(--danger)", label: "Wrong" },
          { color: "var(--border)", label: "Unanswered" },
        ].map(({ color, label }) => (
          <span
            key={label}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.25rem",
              fontSize: "0.625rem",
              color: "var(--text-muted)",
            }}
          >
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: 2,
                background: color === "var(--border)" ? "transparent" : color,
                border: `1.5px solid ${color}`,
                flexShrink: 0,
              }}
            />
            {label}
          </span>
        ))}
      </div>

      {/* 5-per-row grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(5, 1fr)",
          gap: "0.3125rem",
        }}
      >
        {questions.map((q, i) => {
          const isAnswered = q.response !== null;
          const isCorrect = q.score === 1;
          const isCurrent = i === currentIndex;
          const isFlagged = flaggedIds.has(q.id);

          let bg = "transparent";
          let borderColor = "var(--border)";
          let textColor = "var(--text-muted)";

          if (isAnswered) {
            bg = isCorrect
              ? "color-mix(in srgb, var(--success) 18%, var(--surface))"
              : "color-mix(in srgb, var(--danger) 18%, var(--surface))";
            borderColor = isCorrect ? "var(--success)" : "var(--danger)";
            textColor = isCorrect ? "var(--success)" : "var(--danger)";
          }

          return (
            <button
              key={q.id}
              onClick={() => onSelect(i)}
              title={`Q${q.sequence_order}${isFlagged ? " 🚩 Flagged" : ""}${isAnswered ? (isCorrect ? " ✓" : " ✗") : " (unanswered)"}`}
              style={{
                position: "relative",
                width: "100%",
                aspectRatio: "1",
                borderRadius: "5px",
                border: isCurrent
                  ? `2px solid var(--primary)`
                  : `1.5px solid ${borderColor}`,
                background: isCurrent
                  ? "color-mix(in srgb, var(--primary) 12%, var(--surface))"
                  : bg,
                fontSize: "0.6875rem",
                fontWeight: isCurrent ? 700 : 500,
                color: isCurrent ? "var(--primary)" : textColor,
                cursor: "pointer",
                fontVariantNumeric: "tabular-nums",
                padding: 0,
                lineHeight: 1,
              }}
            >
              {q.sequence_order}
              {isFlagged && (
                <span
                  style={{
                    position: "absolute",
                    top: 1,
                    right: 2,
                    fontSize: "0.5rem",
                    lineHeight: 1,
                    pointerEvents: "none",
                  }}
                >
                  🚩
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ── Question view ─────────────────────────────────────────────────────────────

function QuestionView({
  question,
  questionNumber,
  totalQuestions,
  onAnswer,
  isAnswering,
  isFlagged,
  onToggleFlag,
  onNext,
  onPrev,
  isFirst,
  isLast,
}: {
  question: MockExamQuestion;
  questionNumber: number;
  totalQuestions: number;
  onAnswer: (selectedIndex: number) => void;
  isAnswering: boolean;
  isFlagged: boolean;
  onToggleFlag: () => void;
  onNext: () => void;
  onPrev: () => void;
  isFirst: boolean;
  isLast: boolean;
}) {
  const [selected, setSelected] = useState<number | null>(null);
  const [eliminated, setEliminated] = useState<Set<number>>(new Set());

  // Reset local state whenever the question changes
  useEffect(() => {
    setSelected(null);
    setEliminated(new Set());
  }, [question.id]);

  const answered = question.response !== null;
  const optionLabel = (i: number) => String.fromCharCode(65 + i); // A, B, C, D

  const toggleEliminate = (i: number, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setEliminated((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  };

  const optionStyle = (i: number): React.CSSProperties => {
    if (!answered) {
      const isElim = eliminated.has(i);
      return {
        opacity: isElim ? 0.4 : 1,
        ...(selected === i
          ? { borderColor: "var(--primary)", background: "color-mix(in srgb, var(--primary) 8%, var(--surface))" }
          : {}),
      };
    }
    const selectedIdx = question.response!.selected_index;
    const correctIdx = question.correct_index!;
    if (i === correctIdx)
      return { borderColor: "var(--success)", background: "color-mix(in srgb, var(--success) 8%, var(--surface))" };
    if (i === selectedIdx && i !== correctIdx)
      return { borderColor: "var(--danger)", background: "color-mix(in srgb, var(--danger) 8%, var(--surface))" };
    return {};
  };

  const isWrong = answered && question.score !== 1;

  return (
    <div style={{ maxWidth: 760, margin: "0 auto", padding: "1.5rem 1.25rem 2rem" }}>
      {/* Question header */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: "0.625rem",
          marginBottom: "1rem",
          flexWrap: "wrap",
        }}
      >
        <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)", fontWeight: 500, marginRight: "auto" }}>
          Question {questionNumber} of {totalQuestions}
        </span>

        {question.certification_domain_name && (
          <span
            style={{
              fontSize: "0.75rem",
              padding: "0.2rem 0.6rem",
              borderRadius: "999px",
              background: "var(--surface-alt)",
              border: "1px solid var(--border)",
              color: "var(--text-muted)",
            }}
          >
            {question.certification_domain_name}
          </span>
        )}

        {/* Flag button */}
        <button
          onClick={onToggleFlag}
          title={isFlagged ? "Remove flag" : "Flag for review"}
          style={{
            background: isFlagged
              ? "color-mix(in srgb, var(--warning, #f59e0b) 15%, var(--surface))"
              : "transparent",
            border: `1.5px solid ${isFlagged ? "var(--warning, #f59e0b)" : "var(--border)"}`,
            borderRadius: "6px",
            cursor: "pointer",
            padding: "0.2rem 0.5rem",
            fontSize: "0.875rem",
            lineHeight: 1,
            color: isFlagged ? "var(--warning, #f59e0b)" : "var(--text-muted)",
            transition: "all 0.15s",
          }}
        >
          🚩
        </button>
      </div>

      {/* Question text */}
      <p
        style={{
          fontSize: "1.0625rem",
          lineHeight: 1.75,
          marginBottom: "1.5rem",
          color: "var(--text)",
          whiteSpace: "pre-wrap",
        }}
      >
        {question.prompt}
      </p>

      {/* Eliminate hint — only shown before answering */}
      {!answered && (
        <p
          style={{
            fontSize: "0.75rem",
            color: "var(--text-muted)",
            marginBottom: "0.625rem",
            margin: "0 0 0.625rem",
          }}
        >
          Tip: click <strong>✕</strong> beside an option to eliminate it.
        </p>
      )}

      {/* Options */}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.625rem", marginBottom: "1.5rem" }}>
        {question.options.map((opt, i) => {
          const isElim = !answered && eliminated.has(i);
          return (
            <label
              key={i}
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "0.5rem",
                padding: "0.875rem 0.875rem 0.875rem 0.75rem",
                border: "1.5px solid var(--border)",
                borderRadius: "8px",
                cursor: answered ? "default" : "pointer",
                transition: "all 0.15s",
                ...optionStyle(i),
              }}
            >
              {/* Eliminate toggle */}
              {!answered && (
                <button
                  type="button"
                  onClick={(e) => toggleEliminate(i, e)}
                  title={isElim ? "Un-eliminate" : "Eliminate this option"}
                  style={{
                    flexShrink: 0,
                    width: 22,
                    height: 22,
                    marginTop: "0.05rem",
                    border: `1px solid ${isElim ? "var(--danger)" : "var(--border)"}`,
                    borderRadius: "4px",
                    background: isElim
                      ? "color-mix(in srgb, var(--danger) 12%, var(--surface))"
                      : "var(--surface-alt)",
                    color: isElim ? "var(--danger)" : "var(--text-muted)",
                    cursor: "pointer",
                    fontSize: "0.625rem",
                    fontWeight: 700,
                    lineHeight: 1,
                    padding: 0,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    transition: "all 0.12s",
                  }}
                >
                  ✕
                </button>
              )}

              <input
                type="radio"
                name={`q-${question.id}`}
                value={i}
                disabled={answered}
                checked={answered ? question.response!.selected_index === i : selected === i}
                onChange={() => !answered && setSelected(i)}
                style={{ marginTop: "0.25rem", flexShrink: 0 }}
              />

              <span
                style={{
                  fontSize: "0.9375rem",
                  lineHeight: 1.55,
                  textDecoration: isElim ? "line-through" : "none",
                  transition: "text-decoration 0.1s",
                }}
              >
                <strong style={{ marginRight: "0.375rem" }}>{optionLabel(i)})</strong>
                {opt}
              </span>
            </label>
          );
        })}
      </div>

      {/* Submit button — only when not yet answered */}
      {!answered && (
        <button
          className="btn btn-primary"
          disabled={selected === null || isAnswering}
          onClick={() => selected !== null && onAnswer(selected)}
          style={{ fontSize: "0.9375rem" }}
        >
          {isAnswering ? <><span className="spinner" /> Submitting…</> : "Submit Answer"}
        </button>
      )}

      {/* Result panel — shown after answering */}
      {answered && (
        <div
          style={{
            padding: "1rem 1.25rem",
            borderRadius: "8px",
            border: `2px solid ${question.score === 1 ? "var(--success)" : question.is_trap_selected ? "var(--warning, #f59e0b)" : "var(--danger)"}`,
            background: question.score === 1
              ? "color-mix(in srgb, var(--success) 6%, var(--surface))"
              : question.is_trap_selected
              ? "color-mix(in srgb, var(--warning, #f59e0b) 6%, var(--surface))"
              : "color-mix(in srgb, var(--danger) 6%, var(--surface))",
            marginBottom: "1.25rem",
          }}
        >
          <p
            style={{
              fontWeight: 700,
              margin: "0 0 0.375rem",
              color: question.score === 1
                ? "var(--success)"
                : question.is_trap_selected
                ? "var(--warning, #f59e0b)"
                : "var(--danger)",
              fontSize: "0.875rem",
              textTransform: "uppercase",
              letterSpacing: "0.04em",
            }}
          >
            {question.score === 1
              ? "✓ Correct"
              : question.is_trap_selected
              ? "⚠ Common misconception"
              : "✗ Incorrect"}
          </p>

          {/* Trap explanation — when the trap option was chosen */}
          {question.trap_explanation && question.is_trap_selected && (
            <p style={{ margin: "0 0 0.5rem", fontSize: "0.875rem", lineHeight: 1.6, color: "var(--text)" }}>
              {question.trap_explanation}
            </p>
          )}

          {/* Explanation — shown for any wrong answer.
               Prefers `explanation` (generated); falls back to trap_explanation when
               the trap was NOT selected (so the user still gets some rationale);
               falls back to a generic message if neither is present. */}
          {isWrong && (() => {
            const trapWasSelected = question.is_trap_selected;
            // Use `explanation` if present; otherwise use trap_explanation only when
            // trap was NOT chosen (already shown above when trap was chosen).
            const text = question.explanation
              ?? (!trapWasSelected ? question.trap_explanation : null)
              ?? "Review the official documentation for this topic to reinforce the correct approach.";

            // Determine whether to show a divider above (when trap panel already visible)
            const hasTrapPanel = !!(trapWasSelected && question.trap_explanation);

            return (
              <div
                style={{
                  marginTop: hasTrapPanel ? "0.625rem" : 0,
                  paddingTop: hasTrapPanel ? "0.625rem" : 0,
                  borderTop: hasTrapPanel
                    ? "1px solid color-mix(in srgb, var(--border) 60%, transparent)"
                    : "none",
                }}
              >
                <p
                  style={{
                    margin: "0 0 0.25rem",
                    fontSize: "0.8125rem",
                    fontWeight: 600,
                    color: "var(--text-muted)",
                    textTransform: "uppercase",
                    letterSpacing: "0.04em",
                  }}
                >
                  Why the correct answer is right:
                </p>
                <p style={{ margin: 0, fontSize: "0.875rem", lineHeight: 1.6, color: "var(--text)" }}>
                  {text}
                </p>
              </div>
            );
          })()}
        </div>
      )}

      {/* Prev / Next navigation */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "0.75rem",
          marginTop: answered ? 0 : "1rem",
        }}
      >
        <button
          className="btn btn-outline"
          disabled={isFirst}
          onClick={onPrev}
        >
          ← Previous
        </button>
        <button
          className="btn btn-outline"
          disabled={isLast}
          onClick={onNext}
        >
          Next →
        </button>
      </div>
    </div>
  );
}

// ── MockExamPage ──────────────────────────────────────────────────────────────

export default function MockExamPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { session: authSession } = useSession();
  const practitionerId = authSession?.practitioner_id ?? "";

  const {
    data: examSession,
    isLoading,
    isError,
    error,
  } = useMockExamSession(practitionerId, sessionId ?? "");

  const pauseMutation = usePauseMockExam(practitionerId, sessionId ?? "");
  const resumeMutation = useResumeMockExam(practitionerId, sessionId ?? "");
  const answerMutation = useAnswerMockExamQuestion(practitionerId, sessionId ?? "");
  const completeMutation = useCompleteMockExam(practitionerId, sessionId ?? "");
  const abandonMutation = useAbandonMockExam(practitionerId, sessionId ?? "");

  const [showAbandonDialog, setShowAbandonDialog] = useState(false);
  const [abandonReason, setAbandonReason] = useState("");

  const [currentIndex, setCurrentIndex] = useState(0);
  const [flaggedIds, setFlaggedIds] = useState<Set<string>>(new Set());

  const isRunning =
    examSession?.status === "in_progress" && !pauseMutation.isPending;

  const sortedQuestions: MockExamQuestion[] = examSession
    ? [...examSession.questions].sort((a, b) => a.sequence_order - b.sequence_order)
    : [];

  const elapsed = useExamTimer(examSession?.time_elapsed_seconds ?? 0, isRunning);

  const durationSeconds = (examSession?.exam_duration_minutes ?? 0) * 60;
  const isOverTime = elapsed > durationSeconds && durationSeconds > 0;

  const allAnswered =
    sortedQuestions.length > 0 && sortedQuestions.every((q) => q.response !== null);

  const answeredCount = sortedQuestions.filter((q) => q.response !== null).length;

  const handleAnswer = async (selectedIndex: number) => {
    const q = sortedQuestions[currentIndex];
    if (!q || q.response !== null) return;
    // Submit but do NOT auto-advance — let the user read the feedback and press Next
    await answerMutation.mutateAsync({ questionId: q.id, selectedIndex });
  };

  const handlePause = async () => {
    await pauseMutation.mutateAsync();
  };

  const handleResume = async () => {
    await resumeMutation.mutateAsync();
  };

  const handleComplete = async () => {
    await completeMutation.mutateAsync();
  };

  const toggleFlag = (id: string) => {
    setFlaggedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const goNext = () =>
    setCurrentIndex((i) => Math.min(i + 1, sortedQuestions.length - 1));
  const goPrev = () => setCurrentIndex((i) => Math.max(i - 1, 0));

  // ── Loading / error states ─────────────────────────────────────────────────

  if (!practitionerId) {
    return (
      <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
        Please log in to view this exam session.
      </div>
    );
  }

  if (isLoading) {
    return (
      <div style={{ padding: "3rem", textAlign: "center" }}>
        <span className="spinner" />
      </div>
    );
  }

  if (isError) {
    const status = (error as { status?: number }).status;
    return (
      <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
        <p style={{ fontSize: "1.125rem", marginBottom: "0.5rem" }}>
          {status === 404
            ? "Session not found. You may have already completed this exam."
            : "Could not load exam session. Please try again."}
        </p>
        <Link to="/" style={{ color: "var(--primary)", textDecoration: "none" }}>
          ← Return to Mastery Pulse
        </Link>
      </div>
    );
  }

  if (!examSession) return null;

  // ── Generating ────────────────────────────────────────────────────────────

  if (examSession.status === "generating") {
    return <GeneratingScreen session={examSession} />;
  }

  // ── Failed ────────────────────────────────────────────────────────────────

  if (examSession.status === "failed") {
    return <FailedScreen />;
  }

  // ── Completed ──────────────────────────────────────────────────────────────

  if (examSession.status === "completed" || completeMutation.isSuccess) {
    const finalSession = completeMutation.data ?? examSession;
    return <ScoreScreen session={finalSession} />;
  }

  // ── Paused ─────────────────────────────────────────────────────────────────

  if (examSession.status === "paused" && !resumeMutation.isPending) {
    return (
      <PausedScreen
        session={examSession}
        onResume={handleResume}
        isResuming={resumeMutation.isPending}
      />
    );
  }

  // ── In progress ────────────────────────────────────────────────────────────

  const currentQuestion = sortedQuestions[currentIndex] ?? sortedQuestions[0];

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        background: "var(--surface)",
        overflow: "hidden",
      }}
    >
      {/* ── Header bar ─────────────────────────────────────────────────────── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "1rem",
          padding: "0 1.25rem",
          height: 56,
          borderBottom: "1px solid var(--border)",
          background: "var(--surface)",
          boxShadow: "var(--shadow)",
          flexShrink: 0,
          flexWrap: "wrap",
        }}
      >
        <span style={{ fontWeight: 700, fontSize: "0.9375rem", color: "var(--text)", marginRight: "auto" }}>
          {examSession.certification_code} Mock Exam
        </span>

        {/* Answered progress */}
        <span
          style={{
            fontSize: "0.8125rem",
            color: "var(--text-muted)",
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {answeredCount}/{sortedQuestions.length} answered
        </span>

        {/* Timer */}
        <span
          style={{
            fontSize: "0.9375rem",
            fontWeight: 600,
            fontVariantNumeric: "tabular-nums",
            color: isOverTime ? "var(--danger)" : "var(--text)",
            minWidth: "3.5rem",
          }}
          title={isOverTime ? "Over time limit" : "Elapsed time"}
        >
          ⏱ {formatTime(elapsed)}
        </span>

        {allAnswered ? (
          <button
            className="btn btn-primary"
            disabled={completeMutation.isPending}
            onClick={handleComplete}
          >
            {completeMutation.isPending ? (
              <><span className="spinner" /> Finishing…</>
            ) : (
              "Complete Exam"
            )}
          </button>
        ) : (
          <>
            <button
              className="btn btn-outline"
              disabled={pauseMutation.isPending}
              onClick={handlePause}
            >
              {pauseMutation.isPending ? <><span className="spinner" /></> : "⏸ Pause"}
            </button>
            <button
              className="btn btn-outline"
              style={{ color: "var(--danger)", borderColor: "var(--danger)" }}
              onClick={() => setShowAbandonDialog(true)}
            >
              Abandon
            </button>
          </>
        )}
      </div>

      {/* ── Progress bar ───────────────────────────────────────────────────── */}
      <div style={{ height: 3, background: "var(--border)", flexShrink: 0 }}>
        <div
          style={{
            height: "100%",
            width: `${(answeredCount / Math.max(sortedQuestions.length, 1)) * 100}%`,
            background: "var(--primary)",
            transition: "width 0.3s ease",
          }}
        />
      </div>

      {/* ── Body: left nav + question area ─────────────────────────────────── */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>

        {/* Left navigation panel */}
        <LeftNavPanel
          questions={sortedQuestions}
          currentIndex={currentIndex}
          onSelect={setCurrentIndex}
          flaggedIds={flaggedIds}
        />

        {/* Question scroll area */}
        <div style={{ flex: 1, overflowY: "auto" }}>
          {currentQuestion ? (
            <QuestionView
              key={currentQuestion.id}
              question={currentQuestion}
              questionNumber={currentQuestion.sequence_order}
              totalQuestions={sortedQuestions.length}
              onAnswer={handleAnswer}
              isAnswering={answerMutation.isPending}
              isFlagged={flaggedIds.has(currentQuestion.id)}
              onToggleFlag={() => toggleFlag(currentQuestion.id)}
              onNext={goNext}
              onPrev={goPrev}
              isFirst={currentIndex === 0}
              isLast={currentIndex === sortedQuestions.length - 1}
            />
          ) : (
            <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
              Loading questions…
            </div>
          )}
        </div>
      </div>

      {/* ── Abandon dialog ─────────────────────────────────────────────────── */}
      {showAbandonDialog && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.55)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: "1rem",
          }}
          onClick={(e) => e.target === e.currentTarget && setShowAbandonDialog(false)}
        >
          <div
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "12px",
              padding: "1.75rem",
              maxWidth: 440,
              width: "100%",
              boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
            }}
          >
            <h3 style={{ margin: "0 0 0.5rem", fontSize: "1.0625rem" }}>Abandon this exam?</h3>
            <p style={{ margin: "0 0 1.25rem", fontSize: "0.875rem", color: "var(--text-muted)", lineHeight: 1.6 }}>
              Your progress will be saved. Unanswered questions from this exam may be reused in your next attempt, and any questions you got wrong will be offered again for remediation.
            </p>
            <label style={{ display: "block", marginBottom: "1rem" }}>
              <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text)", display: "block", marginBottom: "0.375rem" }}>
                Reason for abandoning <span style={{ color: "var(--danger)" }}>*</span>
              </span>
              <textarea
                value={abandonReason}
                onChange={(e) => setAbandonReason(e.target.value)}
                placeholder="e.g. Running out of time, need to prepare more, unexpected interruption…"
                rows={3}
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  padding: "0.625rem 0.75rem",
                  borderRadius: "6px",
                  border: "1.5px solid var(--border)",
                  background: "var(--surface-alt)",
                  color: "var(--text)",
                  fontSize: "0.875rem",
                  resize: "vertical",
                  fontFamily: "inherit",
                }}
              />
            </label>
            <div style={{ display: "flex", gap: "0.75rem", justifyContent: "flex-end" }}>
              <button
                className="btn btn-outline"
                onClick={() => { setShowAbandonDialog(false); setAbandonReason(""); }}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary"
                style={{ background: "var(--danger)", borderColor: "var(--danger)" }}
                disabled={!abandonReason.trim() || abandonMutation.isPending}
                onClick={async () => {
                  await abandonMutation.mutateAsync(abandonReason.trim());
                  setShowAbandonDialog(false);
                  setAbandonReason("");
                  // Navigate back since the session is now abandoned
                  window.location.href = "/";
                }}
              >
                {abandonMutation.isPending ? <><span className="spinner" /> Abandoning…</> : "Yes, Abandon Exam"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
