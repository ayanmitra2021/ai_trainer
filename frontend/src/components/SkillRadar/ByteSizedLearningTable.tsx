/**
 * ByteSizedLearningTable — Phase 18.4
 * Displays AI-generated micro-lessons per skill gap above the Learning Journey.
 */

import { useState, useEffect, useCallback } from "react";
import type { ByteSizedLesson, LessonListResponse } from "../../api/types";

interface Props {
  practitionerId: string;
  onOpenLesson: (lesson: ByteSizedLesson) => void;
  /** Increment to force a data refresh (e.g. after modal close updates read time). */
  refreshTrigger?: number;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function fetchLessons(practitionerId: string): Promise<LessonListResponse> {
  const resp = await fetch(`${API_BASE}/api/v1/practitioners/${practitionerId}/byte-sized-lessons`, {
    credentials: "include",
  });
  if (!resp.ok) throw new Error(`Failed to load lessons: ${resp.status}`);
  return resp.json();
}

async function triggerGenerate(practitionerId: string): Promise<void> {
  await fetch(`${API_BASE}/api/v1/practitioners/${practitionerId}/byte-sized-lessons/generate`, {
    method: "POST",
    credentials: "include",
  });
}

function formatTimeSpent(seconds: number | null, estimatedMinutes: number | null): {
  text: string;
  style: "none" | "low" | "good";
} {
  if (seconds === null || seconds === undefined) {
    return { text: "—", style: "none" };
  }
  const threshold = (estimatedMinutes ?? 3) * 60 * 0.5;
  if (seconds < threshold) {
    return { text: "⚡ Read again", style: "low" };
  }
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return { text: m > 0 ? `${m} min ${s} sec` : `${s} sec`, style: "good" };
}

function LessonRow({
  lesson,
  dimmed,
  onOpen,
  onRetry,
}: {
  lesson: ByteSizedLesson;
  dimmed: boolean;
  onOpen: (lesson: ByteSizedLesson) => void;
  onRetry: (lesson: ByteSizedLesson) => void;
}) {
  const isUnread =
    (lesson.total_read_seconds === null || lesson.total_read_seconds === undefined) &&
    lesson.generation_status === "ready";

  const timeSpent = formatTimeSpent(lesson.total_read_seconds ?? null, lesson.estimated_read_minutes ?? null);

  return (
    <tr
      style={{
        opacity: dimmed ? 0.65 : 1,
        borderLeft: isUnread ? "3px solid var(--primary)" : "3px solid transparent",
        animation: isUnread ? "pulse-border 1.5s ease-in-out infinite" : "none",
      }}
    >
      <td style={{ padding: "0.625rem 0.75rem", fontWeight: 500 }}>{lesson.skill_name}</td>
      <td style={{ padding: "0.625rem 0.75rem", textAlign: "center" }}>
        {(lesson.gap_pct * 100).toFixed(0)}%
      </td>
      <td style={{ padding: "0.625rem 0.75rem", textAlign: "center" }}>
        {(lesson.target_pct * 100).toFixed(0)}% mastery
      </td>
      <td style={{ padding: "0.625rem 0.75rem", maxWidth: 280, fontSize: "0.8125rem", color: "var(--text-muted)" }}>
        {lesson.what_missing
          ? lesson.what_missing.length > 80
            ? <span title={lesson.what_missing}>{lesson.what_missing.slice(0, 80)}…</span>
            : lesson.what_missing
          : <span style={{ color: "var(--text-muted)", fontStyle: "italic" }}>—</span>}
      </td>
      <td style={{ padding: "0.625rem 0.75rem", textAlign: "center", fontSize: "0.8125rem" }}>
        {timeSpent.style === "low" ? (
          <span style={{ color: "#b45309", fontWeight: 600 }}>{timeSpent.text}</span>
        ) : timeSpent.style === "good" ? (
          <span style={{ color: "#16a34a" }}>{timeSpent.text}</span>
        ) : (
          <span style={{ color: "var(--text-muted)" }}>{timeSpent.text}</span>
        )}
      </td>
      <td style={{ padding: "0.625rem 0.75rem", textAlign: "center" }}>
        {lesson.generation_status === "pending" && (
          <span style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>⏳ Generating…</span>
        )}
        {lesson.generation_status === "failed" && (
          <span style={{ fontSize: "0.8125rem" }}>
            ⚠️ Failed{" "}
            <button
              style={{ background: "none", border: "none", color: "var(--primary)", cursor: "pointer", fontSize: "0.8125rem", padding: 0, textDecoration: "underline" }}
              onClick={() => onRetry(lesson)}
            >
              Retry
            </button>
          </span>
        )}
        {lesson.generation_status === "ready" && (
          <button
            className="btn btn-outline"
            style={{ fontSize: "0.8125rem", padding: "0.25rem 0.75rem" }}
            onClick={() => onOpen(lesson)}
          >
            Read
          </button>
        )}
      </td>
    </tr>
  );
}

export default function ByteSizedLearningTable({ practitionerId, onOpenLesson, refreshTrigger }: Props) {
  const [data, setData] = useState<LessonListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const result = await fetchLessons(practitionerId);
      setData(result);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [practitionerId]);

  useEffect(() => {
    load();
  }, [load]);

  // Poll while any current lesson is pending
  useEffect(() => {
    if (!data) return;
    const hasPending = data.current.some((l) => l.generation_status === "pending");
    if (!hasPending) return;

    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, [data, load]);

  // Re-fetch when the parent signals a refresh (e.g. after a lesson modal closes,
  // so total_read_seconds updates without waiting for the next poll cycle).
  useEffect(() => {
    if (refreshTrigger === undefined || refreshTrigger === 0) return;
    load();
  }, [refreshTrigger, load]);

  const handleRetry = async (_lesson: ByteSizedLesson) => {
    await triggerGenerate(practitionerId);
    setTimeout(load, 1000);
  };

  if (loading) return null;
  if (error) return null; // silently suppress on error (feature degrades gracefully)
  if (!data || (data.current.length === 0 && data.history.length === 0)) return null;

  return (
    <div style={{ marginBottom: "2.5rem" }}>
      <style>{`
        @keyframes pulse-border {
          0%, 100% { border-left-color: rgba(77, 171, 247, 0.4); }
          50% { border-left-color: rgba(77, 171, 247, 1.0); }
        }
      `}</style>

      <div style={{ marginBottom: "0.75rem" }}>
        <h2 style={{ marginBottom: "0.25rem" }}>📖 Byte-Sized Learning</h2>
        <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", margin: 0 }}>
          Targeted micro-reads for your current gaps — regenerated each time you update your path.
        </p>
      </div>

      <div style={{ overflowX: "auto", border: "1px solid var(--border)", borderRadius: "8px" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
          <thead>
            <tr style={{ background: "var(--surface)", borderBottom: "1px solid var(--border)" }}>
              <th style={{ padding: "0.625rem 0.75rem", textAlign: "left", fontWeight: 600, fontSize: "0.8125rem" }}>Skill</th>
              <th style={{ padding: "0.625rem 0.75rem", textAlign: "center", fontWeight: 600, fontSize: "0.8125rem" }}>Current Gap</th>
              <th style={{ padding: "0.625rem 0.75rem", textAlign: "center", fontWeight: 600, fontSize: "0.8125rem" }}>Target</th>
              <th style={{ padding: "0.625rem 0.75rem", textAlign: "left", fontWeight: 600, fontSize: "0.8125rem" }}>What You Might Be Missing</th>
              <th style={{ padding: "0.625rem 0.75rem", textAlign: "center", fontWeight: 600, fontSize: "0.8125rem" }}>Time Spent</th>
              <th style={{ padding: "0.625rem 0.75rem", textAlign: "center", fontWeight: 600, fontSize: "0.8125rem" }}>Read</th>
            </tr>
          </thead>
          <tbody>
            {data.current.map((lesson) => (
              <LessonRow
                key={lesson.id}
                lesson={lesson}
                dimmed={false}
                onOpen={onOpenLesson}
                onRetry={handleRetry}
              />
            ))}

            {data.history.length > 0 && (
              <>
                <tr>
                  <td
                    colSpan={6}
                    style={{
                      padding: "0.5rem 0.75rem",
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      color: "var(--text-muted)",
                      background: "var(--surface)",
                      borderTop: "1px solid var(--border)",
                      borderBottom: "1px solid var(--border)",
                      letterSpacing: "0.05em",
                      textTransform: "uppercase",
                    }}
                  >
                    Previous paths
                  </td>
                </tr>
                {data.history.map((lesson) => (
                  <LessonRow
                    key={lesson.id}
                    lesson={lesson}
                    dimmed
                    onOpen={onOpenLesson}
                    onRetry={handleRetry}
                  />
                ))}
              </>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
