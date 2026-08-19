/**
 * LessonModal — Phase 18.5
 * Full lesson content, circular timer, read-session tracking, and Read Aloud (Phase 18.6).
 *
 * The list API returns LessonSummary (no content_md / external_links).
 * This modal fetches the full detail on mount so it always has the real content.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import type { ByteSizedLesson } from "../../api/types";
import { useSpeechSynthesis } from "../../hooks/useSpeechSynthesis";
import { markdownToPlain } from "../../utils/markdownToPlain";

interface Props {
  lesson: ByteSizedLesson;
  practitionerId: string;
  onClose: () => void;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

const SPEEDS = [0.75, 1, 1.25, 1.5, 2] as const;
type Speed = (typeof SPEEDS)[number];

function CircularTimer({
  elapsed,
  totalSeconds,
}: {
  elapsed: number;
  totalSeconds: number;
}) {
  const RADIUS = 28;
  const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
  const progress = Math.min(elapsed / totalSeconds, 1);
  const offset = CIRCUMFERENCE * (1 - progress);
  const done = progress >= 1;

  const minutes = Math.floor(elapsed / 60);
  const secs = elapsed % 60;
  const label = `${minutes}:${String(secs).padStart(2, "0")}`;

  return (
    <svg width={72} height={72} viewBox="0 0 72 72">
      <circle cx={36} cy={36} r={RADIUS} fill="none" stroke="var(--border)" strokeWidth={5} />
      <circle
        cx={36}
        cy={36}
        r={RADIUS}
        fill="none"
        stroke={done ? "#16a34a" : "var(--primary)"}
        strokeWidth={5}
        strokeDasharray={CIRCUMFERENCE}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform="rotate(-90 36 36)"
        style={{ transition: "stroke-dashoffset 1s linear, stroke 0.3s" }}
      />
      <text
        x={36}
        y={40}
        textAnchor="middle"
        fontSize={12}
        fontWeight={600}
        fill={done ? "#16a34a" : "var(--text)"}
      >
        {label}
      </text>
    </svg>
  );
}

function renderMarkdown(md: string): string {
  // Very simple Markdown → HTML for the modal
  return md
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1>$1</h1>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, "<code>$1</code>")
    .replace(/^---$/gm, "<hr/>")
    .replace(/^- (.+)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`)
    .replace(/^\d+\. (.+)$/gm, "<li>$1</li>")
    .replace(/\n\n/g, "</p><p>")
    .replace(/^(?!<[hlupc])/gm, "")
    .trim();
}

const TYPE_ICONS: Record<string, string> = {
  blog: "📝",
  docs: "📖",
  video: "🎥",
};

export default function LessonModal({ lesson, practitionerId, onClose }: Props) {
  const [elapsed, setElapsed] = useState(0);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [speed, setSpeed] = useState<Speed>(1);

  // Full lesson detail (content_md + external_links) fetched on mount —
  // the list API only returns LessonSummary which omits these fields.
  const [fullLesson, setFullLesson] = useState<ByteSizedLesson | null>(
    lesson.content_md != null ? lesson : null
  );
  const [contentLoading, setContentLoading] = useState(lesson.content_md == null);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const { speak, stop, isPlaying } = useSpeechSynthesis();

  const totalSeconds = (lesson.estimated_read_minutes ?? 3) * 60;

  // ── Fetch full lesson detail (has content_md & external_links) ─────────────
  useEffect(() => {
    if (lesson.content_md != null) return; // already have full detail
    fetch(
      `${API_BASE}/api/v1/practitioners/${practitionerId}/byte-sized-lessons/${lesson.id}`,
      { credentials: "include" }
    )
      .then((r) => r.ok ? r.json() : Promise.reject(r.status))
      .then((data: ByteSizedLesson) => {
        setFullLesson(data);
        setContentLoading(false);
      })
      .catch(() => setContentLoading(false));
  }, [lesson.id, lesson.content_md, practitionerId]);

  // ── Open read session on mount ─────────────────────────────────────────────
  useEffect(() => {
    fetch(
      `${API_BASE}/api/v1/practitioners/${practitionerId}/byte-sized-lessons/${lesson.id}/read-sessions`,
      { method: "POST", credentials: "include" }
    )
      .then((r) => r.json())
      .then((data) => setSessionId(data.session_id))
      .catch(() => {});
  }, [lesson.id, practitionerId]);

  // ── Timer ──────────────────────────────────────────────────────────────────
  useEffect(() => {
    intervalRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  // ── Close with duration recording ──────────────────────────────────────────
  const handleClose = useCallback(() => {
    stop();
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (sessionId) {
      fetch(
        `${API_BASE}/api/v1/practitioners/${practitionerId}/byte-sized-lessons/${lesson.id}/read-sessions/${sessionId}`,
        {
          method: "PATCH",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ duration_seconds: elapsed }),
        }
      ).catch(() => {});
    }
    onClose();
  }, [sessionId, elapsed, lesson.id, practitionerId, onClose, stop]);

  // ── Escape key ─────────────────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") handleClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [handleClose]);

  const displayLesson = fullLesson ?? lesson;
  const contentMd = displayLesson.content_md ?? null;
  const externalLinks = displayLesson.external_links ?? null;

  const handleReadAloud = () => {
    if (isPlaying) {
      stop();
    } else {
      const plain = markdownToPlain(contentMd ?? "");
      speak(plain, speed);
    }
  };

  const handleSpeedChange = (newSpeed: Speed) => {
    setSpeed(newSpeed);
    if (isPlaying && contentMd) {
      stop();
      const plain = markdownToPlain(contentMd);
      setTimeout(() => speak(plain, newSpeed), 50);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.6)",
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "1rem",
      }}
      onClick={(e) => { if (e.target === e.currentTarget) handleClose(); }}
    >
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "12px",
          width: "min(680px, 100%)",
          maxHeight: "90vh",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 25px 50px rgba(0,0,0,0.4)",
        }}
      >
        {/* ── Header ── */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "1rem",
            padding: "1rem 1.25rem",
            borderBottom: "1px solid var(--border)",
            flexShrink: 0,
          }}
        >
          <h3 style={{ flex: 1, margin: 0, fontSize: "1rem", fontWeight: 700 }}>
            {lesson.skill_name}
          </h3>

          <CircularTimer elapsed={elapsed} totalSeconds={totalSeconds} />

          {/* Read Aloud controls — only shown when content is loaded */}
          {contentMd && typeof window !== "undefined" && "speechSynthesis" in window && (
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexShrink: 0 }}>
              <button
                style={{
                  background: isPlaying ? "var(--primary)" : "var(--surface)",
                  color: isPlaying ? "#fff" : "var(--text)",
                  border: "1px solid var(--border)",
                  borderRadius: "6px",
                  padding: "0.375rem 0.75rem",
                  cursor: "pointer",
                  fontSize: "0.8125rem",
                  whiteSpace: "nowrap",
                }}
                onClick={handleReadAloud}
              >
                {isPlaying ? "⏹ Stop" : "🔊 Read Aloud"}
              </button>
              <select
                value={speed}
                onChange={(e) => handleSpeedChange(Number(e.target.value) as Speed)}
                style={{
                  background: "var(--surface)",
                  color: "var(--text)",
                  border: "1px solid var(--border)",
                  borderRadius: "6px",
                  padding: "0.375rem 0.5rem",
                  fontSize: "0.8125rem",
                  cursor: "pointer",
                }}
              >
                {SPEEDS.map((s) => (
                  <option key={s} value={s}>{s}×</option>
                ))}
              </select>
            </div>
          )}

          <button
            onClick={handleClose}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              fontSize: "1.25rem",
              color: "var(--text-muted)",
              lineHeight: 1,
              padding: "0.25rem",
              flexShrink: 0,
            }}
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {/* ── Body ── */}
        <div
          style={{
            flex: 1,
            overflow: "auto",
            padding: "1.25rem",
            lineHeight: 1.7,
            fontSize: "0.9375rem",
          }}
        >
          {contentLoading ? (
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", color: "var(--text-muted)", padding: "2rem 0" }}>
              <span className="spinner" />
              <span>Loading lesson content…</span>
            </div>
          ) : contentMd ? (
            <div dangerouslySetInnerHTML={{ __html: renderMarkdown(contentMd) }} />
          ) : (
            <p style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
              Content could not be loaded. Please close and try again.
            </p>
          )}
        </div>

        {/* ── Footer — external links ── */}
        {externalLinks && externalLinks.length > 0 && (
          <div
            style={{
              borderTop: "1px solid var(--border)",
              padding: "1rem 1.25rem",
              flexShrink: 0,
            }}
          >
            <p style={{ fontWeight: 600, marginBottom: "0.5rem", fontSize: "0.875rem" }}>
              📚 Want to learn more?
            </p>
            <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: "0.375rem" }}>
              {externalLinks.map((link: { title: string; url: string; type: string }, idx: number) => (
                <li key={idx}>
                  <a
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: "var(--primary)", fontSize: "0.875rem", textDecoration: "none" }}
                  >
                    {TYPE_ICONS[link.type] ?? "🔗"} {link.title}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
