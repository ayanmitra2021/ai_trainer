/** QuizRunner — interactive quiz with trap-reveal mechanic. */

import { useMemo, useState } from "react";
import { useItemsBySkill, useCertifications, useLearningPaths, usePractitionerAttempts, useSkills, useSubmitAttempt } from "../../hooks";
import { useSession } from "../../context/SessionContext";
import type { Attempt, Item, MCQAnswerKey } from "../../api/types";

interface Props {
  practitionerId: string;
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
      <p
        style={{
          fontWeight: 700,
          margin: "0 0 0.5rem",
          color: "var(--warning)",
          fontSize: "0.875rem",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
        }}
      >
        ⚠ Common misconception spotted
      </p>
      <p style={{ margin: "0 0 0.75rem", fontSize: "0.9375rem", lineHeight: 1.6 }}>
        {trapExplanation}
      </p>
      <p style={{ margin: 0, fontSize: "0.875rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
        {graderRationale}
      </p>
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
      <p
        style={{
          fontWeight: 700,
          margin: "0 0 0.5rem",
          color: "var(--success)",
          fontSize: "0.875rem",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
        }}
      >
        ✓ Correct
      </p>
      <p style={{ margin: 0, fontSize: "0.875rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
        {graderRationale}
      </p>
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
      <p
        style={{
          fontWeight: 700,
          margin: "0 0 0.5rem",
          color: "var(--primary)",
          fontSize: "0.875rem",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
        }}
      >
        Partial credit — {(score * 100).toFixed(0)}%
      </p>
      <p style={{ margin: 0, fontSize: "0.875rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
        {graderRationale}
      </p>
    </div>
  );
}

// ── MCQ item ──────────────────────────────────────────────────────────────────

function MCQItem({
  item,
  attempt,
  onSubmit,
  isPending,
}: {
  item: Item;
  attempt: Attempt | null;
  onSubmit: (selectedIndex: number) => void;
  isPending: boolean;
}) {
  const [selected, setSelected] = useState<number | null>(null);
  const key = item.answer_key as MCQAnswerKey;

  // Guard: answer_key may be empty ({}) on items written before the schema fix.
  // Hooks must all be called before this early return to satisfy Rules of Hooks.
  if (!key?.options || key.options.length === 0) {
    return (
      <div className="empty-state">
        Answer options unavailable for this item. Regenerate your learning path
        to replace it with a fresh question.
      </div>
    );
  }

  const optionStyle = (i: number): React.CSSProperties => {
    if (!attempt) {
      return {};
    }
    const isCorrect = i === key.correct_index;
    const isSelected = i === (attempt.response as { selected_index: number }).selected_index;
    if (isCorrect) return { borderColor: "var(--success)", background: "color-mix(in srgb, var(--success) 8%, var(--surface))" };
    if (isSelected && !isCorrect) return { borderColor: "var(--danger)", background: "color-mix(in srgb, var(--danger) 8%, var(--surface))" };
    return {};
  };

  return (
    <div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
          marginBottom: "1rem",
        }}
      >
        <span className="badge badge-blue">{item.item_type.toUpperCase()}</span>
        <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
          Difficulty {(item.difficulty * 100).toFixed(0)}%
        </span>
      </div>
      <p style={{ fontSize: "1rem", lineHeight: 1.65, marginBottom: "1.25rem" }}>
        {item.prompt}
      </p>
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
            <PartialCreditPanel
              score={attempt.score}
              graderRationale={attempt.grader_rationale}
            />
          )}
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
}: {
  item: Item;
  attempt: Attempt | null;
  onSubmit: (text: string) => void;
  isPending: boolean;
}) {
  const [text, setText] = useState("");

  return (
    <div>
      <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1rem" }}>
        <span className="badge badge-gray">{item.item_type.replace("_", " ").toUpperCase()}</span>
        <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
          Difficulty {(item.difficulty * 100).toFixed(0)}%
        </span>
      </div>
      <p style={{ fontSize: "1rem", lineHeight: 1.65, marginBottom: "1.25rem" }}>
        {item.prompt}
      </p>
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
        attempt.score === 1 ? (
          <CorrectAnswerPanel graderRationale={attempt.grader_rationale} />
        ) : (
          <PartialCreditPanel score={attempt.score} graderRationale={attempt.grader_rationale} />
        )
      )}
    </div>
  );
}

// ── Main QuizRunner ────────────────────────────────────────────────────────────

function SkillItemQuiz({
  practitionerId,
  skillId,
  skillName,
}: {
  practitionerId: string;
  skillId: string;
  skillName: string;
}) {
  const { data: skillItems, isLoading: itemsLoading } = useItemsBySkill(skillId);
  const { data: allAttempts, isLoading: attemptsLoading } = usePractitionerAttempts(practitionerId);
  const submitAttempt = useSubmitAttempt(practitionerId);
  const [itemIndex, setItemIndex] = useState(0);

  // Build item_id → most recent attempt from the server-persisted list.
  // This survives navigation and page refreshes — no local state needed.
  const attemptsByItemId = useMemo(() => {
    const map: Record<string, Attempt> = {};
    allAttempts?.forEach((a) => {
      // Keep only the most recent per item (list is newest-first from server)
      if (!map[a.item_id]) map[a.item_id] = a;
    });
    return map;
  }, [allAttempts]);

  if (itemsLoading || attemptsLoading)
    return <div style={{ textAlign: "center", padding: "2rem" }}><span className="spinner" /></div>;

  if (!skillItems || skillItems.length === 0)
    return (
      <div className="empty-state">
        No items yet for <strong>{skillName}</strong>. Generate a learning path
        first to have the Item-Writer create practice questions.
      </div>
    );

  const item = skillItems[itemIndex];
  const attempt = attemptsByItemId[item.id] ?? null;

  const handleSubmit = async (response: { selected_index: number } | { text: string }) => {
    await submitAttempt.mutateAsync({
      practitioner_id: practitionerId,
      item_id: item.id,
      response,
    });
    // No local state update needed — useSubmitAttempt updates the query cache directly
  };

  return (
    <div>
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
        <h3 style={{ margin: 0 }}>{skillName}</h3>
        <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
          {itemIndex + 1} / {skillItems.length}
        </span>
      </div>

      {item.item_type === "mcq" ? (
        <MCQItem
          key={item.id}
          item={item}
          attempt={attempt}
          onSubmit={(idx) => handleSubmit({ selected_index: idx })}
          isPending={submitAttempt.isPending}
        />
      ) : (
        <FreeTextItem
          key={item.id}
          item={item}
          attempt={attempt}
          onSubmit={(text) => handleSubmit({ text })}
          isPending={submitAttempt.isPending}
        />
      )}

      {attempt && itemIndex < skillItems.length - 1 && (
        <button
          className="btn btn-outline"
          style={{ marginTop: "1.25rem" }}
          onClick={() => {
            // Find the next unanswered item after the current index
            const nextUnanswered = skillItems.findIndex(
              (itm, idx) => idx > itemIndex && !attemptsByItemId[itm.id]
            );
            if (nextUnanswered !== -1) {
              setItemIndex(nextUnanswered);
            } else {
              // All remaining items answered — advance to next item regardless
              setItemIndex((i) => Math.min(i + 1, skillItems.length - 1));
            }
          }}
        >
          Next question →
        </button>
      )}

      {attempt && itemIndex === skillItems.length - 1 && (
        <p style={{ marginTop: "1.25rem", color: "var(--text-muted)", fontSize: "0.875rem" }}>
          You've completed all items for this skill.
        </p>
      )}
    </div>
  );
}

export default function QuizRunner({ practitionerId }: Props) {
  const { data: paths, isLoading: pathsLoading } = useLearningPaths(practitionerId);
  const { data: allSkills } = useSkills();
  const { data: certList } = useCertifications();
  const { session } = useSession();
  const [selectedSkillId, setSelectedSkillId] = useState<string | null>(null);

  // Build a fast id→name lookup from the global skill list.
  const skillNameById = useMemo(() => {
    const map = new Map<string, string>();
    allSkills?.forEach((s) => map.set(s.id, s.name));
    return map;
  }, [allSkills]);

  // Determine cert skill IDs from the active certification code in session
  const certSkillIds = useMemo(() => {
    const ids = new Set<string>();
    const certCode = session?.active_certification_code;
    if (!certCode || !certList) return ids;
    const cert = certList.find((c) => c.code === certCode);
    cert?.certification_skills.forEach((cs) => ids.add(cs.skill_id));
    return ids;
  }, [certList, session?.active_certification_code]);

  if (pathsLoading) {
    return (
      <div style={{ textAlign: "center", padding: "3rem" }}>
        <span className="spinner" />
      </div>
    );
  }

  const activePath = paths?.find((p) => p.status === "active") ?? paths?.[0];

  if (!activePath || activePath.items.length === 0) {
    return (
      <div className="empty-state">
        <p>No learning path yet. Generate one from the Skill Radar tab first.</p>
      </div>
    );
  }

  // Deduplicate skills from path items (show each skill once).
  // Cert-relevant skills appear first (isCert: true), then others.
  const rawPathSkills = activePath.items.reduce<{ id: string; name: string; isCert: boolean }[]>(
    (acc, item) => {
      if (!acc.find((s) => s.id === item.skill_id)) {
        acc.push({
          id: item.skill_id,
          name: skillNameById.get(item.skill_id) ?? `Skill ${item.skill_id.slice(0, 8)}`,
          isCert: certSkillIds.has(item.skill_id),
        });
      }
      return acc;
    },
    [],
  );

  // Sort: cert skills first, then others
  const pathSkills = [
    ...rawPathSkills.filter((s) => s.isCert),
    ...rawPathSkills.filter((s) => !s.isCert),
  ];

  // Default to first cert-relevant skill; fall back to first skill overall
  const defaultSkillId = (pathSkills.find((s) => s.isCert) ?? pathSkills[0])?.id ?? null;
  const active = selectedSkillId ?? defaultSkillId;

  return (
    <div>
      <h2>Quiz</h2>
      <p style={{ color: "var(--text-muted)", marginBottom: "1.25rem", fontSize: "0.875rem" }}>
        Practice questions for your active learning path. Select a skill to begin.
      </p>

      {/* Skill selector */}
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginBottom: "1.5rem" }}>
        {pathSkills.map((s) => (
          <button
            key={s.id}
            className={`btn ${active === s.id ? "btn-primary" : "btn-outline"}`}
            onClick={() => setSelectedSkillId(s.id)}
          >
            {s.name}
            {s.isCert && (
              <span
                style={{
                  marginLeft: "0.375rem",
                  fontSize: "0.65rem",
                  padding: "0.1rem 0.3rem",
                  borderRadius: "999px",
                  background: active === s.id ? "rgba(255,255,255,0.3)" : "var(--primary)",
                  color: active === s.id ? "#fff" : "#fff",
                  verticalAlign: "middle",
                }}
              >
                cert
              </span>
            )}
          </button>
        ))}
      </div>

      {active && (
        <div className="card">
          {/* key={active} ensures itemIndex resets to 0 when the user
              switches to a different skill — without it, the index from
              the previous skill carries over into the new skill's item list. */}
          <SkillItemQuiz
            key={active}
            practitionerId={practitionerId}
            skillId={active}
            skillName={pathSkills.find((s) => s.id === active)?.name ?? active}
          />
        </div>
      )}
    </div>
  );
}
