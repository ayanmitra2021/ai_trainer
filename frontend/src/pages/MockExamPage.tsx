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
  useCompleteMockExam,
  useMockExamSession,
  usePauseMockExam,
  useResumeMockExam,
} from "../hooks";
import { useSession } from "../context/SessionContext";
import type { MockExamQuestion, MockExamSession } from "../api/types";

// ── Timer ─────────────────────────────────────────────────────────────────────

function useExamTimer(
  initialSeconds: number,
  running: boolean,
): number {
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

  // Sync initial value when session data loads
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

// ── Question view ─────────────────────────────────────────────────────────────

function QuestionView({
  question,
  questionNumber,
  totalQuestions,
  onAnswer,
  isAnswering,
}: {
  question: MockExamQuestion;
  questionNumber: number;
  totalQuestions: number;
  onAnswer: (selectedIndex: number) => void;
  isAnswering: boolean;
}) {
  const [selected, setSelected] = useState<number | null>(null);
  const answered = question.response !== null;

  const optionLabel = (i: number) => String.fromCharCode(65 + i); // A, B, C, D

  const optionStyle = (i: number): React.CSSProperties => {
    if (!answered) {
      return selected === i
        ? { borderColor: "var(--primary)", background: "color-mix(in srgb, var(--primary) 8%, var(--surface))" }
        : {};
    }
    const selectedIdx = question.response!.selected_index;
    const correctIdx = question.correct_index;
    if (i === correctIdx)
      return { borderColor: "var(--success)", background: "color-mix(in srgb, var(--success) 8%, var(--surface))" };
    if (i === selectedIdx && i !== correctIdx)
      return { borderColor: "var(--danger)", background: "color-mix(in srgb, var(--danger) 8%, var(--surface))" };
    return {};
  };

  return (
    <div style={{ maxWidth: 760, margin: "0 auto", padding: "1.5rem 1rem" }}>
      {/* Question header */}
      <div style={{ marginBottom: "1rem" }}>
        <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)", fontWeight: 500 }}>
          Question {questionNumber} of {totalQuestions}
        </span>
        {question.certification_domain_name && (
          <span
            style={{
              marginLeft: "0.75rem",
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
      </div>

      <p style={{ fontSize: "1.0625rem", lineHeight: 1.7, marginBottom: "1.5rem", color: "var(--text)" }}>
        {question.prompt}
      </p>

      {/* Options */}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.625rem", marginBottom: "1.5rem" }}>
        {question.options.map((opt, i) => (
          <label
            key={i}
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: "0.75rem",
              padding: "0.875rem 1rem",
              border: "1.5px solid var(--border)",
              borderRadius: "8px",
              cursor: answered ? "default" : "pointer",
              transition: "all 0.15s",
              ...optionStyle(i),
            }}
          >
            <input
              type="radio"
              name={`q-${question.id}`}
              value={i}
              disabled={answered}
              checked={answered ? question.response!.selected_index === i : selected === i}
              onChange={() => !answered && setSelected(i)}
              style={{ marginTop: "0.2rem", flexShrink: 0 }}
            />
            <span style={{ fontSize: "0.9375rem", lineHeight: 1.55 }}>
              <strong style={{ marginRight: "0.375rem" }}>{optionLabel(i)})</strong>
              {opt}
            </span>
          </label>
        ))}
      </div>

      {/* Submit button */}
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

      {/* Result panel */}
      {answered && (
        <div
          style={{
            padding: "1rem 1.25rem",
            borderRadius: "8px",
            border: `2px solid ${question.score === 1 ? "var(--success)" : question.is_trap_selected ? "var(--warning)" : "var(--danger)"}`,
            background: question.score === 1
              ? "color-mix(in srgb, var(--success) 6%, var(--surface))"
              : question.is_trap_selected
              ? "color-mix(in srgb, var(--warning) 6%, var(--surface))"
              : "color-mix(in srgb, var(--danger) 6%, var(--surface))",
          }}
        >
          <p
            style={{
              fontWeight: 700,
              margin: "0 0 0.375rem",
              color: question.score === 1 ? "var(--success)" : question.is_trap_selected ? "var(--warning)" : "var(--danger)",
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
          {question.trap_explanation && question.is_trap_selected && (
            <p style={{ margin: "0", fontSize: "0.875rem", lineHeight: 1.55, color: "var(--text)" }}>
              {question.trap_explanation}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Overview grid ─────────────────────────────────────────────────────────────

function OverviewGrid({
  questions,
  currentIndex,
  onSelect,
}: {
  questions: MockExamQuestion[];
  currentIndex: number;
  onSelect: (idx: number) => void;
}) {
  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "0.375rem",
        padding: "0.75rem 1rem",
        borderTop: "1px solid var(--border)",
        background: "var(--surface)",
      }}
    >
      {questions.map((q, i) => {
        const isAnswered = q.response !== null;
        const isCorrect = q.score === 1;
        const isCurrent = i === currentIndex;

        let bg = "var(--surface-alt)";
        let border = "1px solid var(--border)";
        if (isAnswered) {
          bg = isCorrect
            ? "color-mix(in srgb, var(--success) 20%, var(--surface))"
            : "color-mix(in srgb, var(--danger) 20%, var(--surface))";
          border = `1px solid ${isCorrect ? "var(--success)" : "var(--danger)"}`;
        }
        if (isCurrent) {
          border = "2px solid var(--primary)";
        }

        return (
          <button
            key={q.id}
            onClick={() => onSelect(i)}
            title={`Q${q.sequence_order}${isAnswered ? (isCorrect ? " ✓" : " ✗") : " (unanswered)"}`}
            style={{
              width: 32,
              height: 32,
              borderRadius: "6px",
              border,
              background: bg,
              fontSize: "0.75rem",
              fontWeight: isCurrent ? 700 : 500,
              color: isCurrent ? "var(--primary)" : "var(--text)",
              cursor: "pointer",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {q.sequence_order}
          </button>
        );
      })}
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

  const [currentIndex, setCurrentIndex] = useState(0);

  const isRunning =
    examSession?.status === "in_progress" && !pauseMutation.isPending;

  // Sort questions by sequence_order for stable display
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
    await answerMutation.mutateAsync({ questionId: q.id, selectedIndex });
    // Auto-advance to next unanswered question
    const nextUnanswered = sortedQuestions.findIndex(
      (sq, idx) => idx > currentIndex && sq.response === null,
    );
    if (nextUnanswered !== -1) setCurrentIndex(nextUnanswered);
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
        minHeight: "100vh",
        background: "var(--surface)",
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

        <span style={{ fontSize: "0.875rem", color: "var(--text-muted)", fontVariantNumeric: "tabular-nums" }}>
          Q {(currentQuestion?.sequence_order ?? 1)}/{examSession.total_count}
        </span>

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
          <button
            className="btn btn-outline"
            disabled={pauseMutation.isPending}
            onClick={handlePause}
          >
            {pauseMutation.isPending ? <><span className="spinner" /></> : "⏸ Pause"}
          </button>
        )}
      </div>

      {/* ── Progress bar ───────────────────────────────────────────────────── */}
      <div style={{ height: 4, background: "var(--border)", flexShrink: 0 }}>
        <div
          style={{
            height: "100%",
            width: `${(answeredCount / Math.max(sortedQuestions.length, 1)) * 100}%`,
            background: "var(--primary)",
            transition: "width 0.3s ease",
          }}
        />
      </div>
      <div
        style={{
          padding: "0.375rem 1.25rem",
          fontSize: "0.75rem",
          color: "var(--text-muted)",
          background: "var(--surface-alt)",
          borderBottom: "1px solid var(--border)",
          flexShrink: 0,
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {answeredCount}/{sortedQuestions.length} answered &nbsp;·&nbsp;{" "}
        {Math.round((answeredCount / Math.max(sortedQuestions.length, 1)) * 100)}% done
      </div>

      {/* ── Question area ──────────────────────────────────────────────────── */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        {currentQuestion ? (
          <QuestionView
            key={currentQuestion.id}
            question={currentQuestion}
            questionNumber={currentQuestion.sequence_order}
            totalQuestions={sortedQuestions.length}
            onAnswer={handleAnswer}
            isAnswering={answerMutation.isPending}
          />
        ) : (
          <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
            Loading questions…
          </div>
        )}

        {/* Prev / Next navigation */}
        {sortedQuestions.length > 1 && currentQuestion && (
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              padding: "0 1rem 1.5rem",
              maxWidth: 760,
              margin: "0 auto",
            }}
          >
            <button
              className="btn btn-outline"
              disabled={currentIndex === 0}
              onClick={() => setCurrentIndex((i) => Math.max(i - 1, 0))}
            >
              ← Previous
            </button>
            <button
              className="btn btn-outline"
              disabled={currentIndex === sortedQuestions.length - 1}
              onClick={() => setCurrentIndex((i) => Math.min(i + 1, sortedQuestions.length - 1))}
            >
              Next →
            </button>
          </div>
        )}
      </div>

      {/* ── Overview grid (question navigator) ────────────────────────────── */}
      <OverviewGrid
        questions={sortedQuestions}
        currentIndex={currentIndex}
        onSelect={setCurrentIndex}
      />
    </div>
  );
}
