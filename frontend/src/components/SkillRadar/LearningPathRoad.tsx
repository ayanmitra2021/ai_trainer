/**
 * LearningPathRoad — graphical "road map" for a learning path.
 *
 * Items are laid out in a serpentine (snaking) grid — left→right on row 0,
 * right→left on row 1, and so on — connected by smooth cubic-bezier U-turns.
 * Each milestone shows: step number, skill name, resource type, and target week.
 *
 * Phase 6.8: replaces the plain text list with a graphical journey map.
 */

import { useSkills } from "../../hooks";
import type { LearningPath } from "../../api/types";

interface Props {
  path: LearningPath;
}

// ── Layout constants ──────────────────────────────────────────────────────────
const ITEMS_PER_ROW = 4;
const CELL_W = 175;       // px per column
const CELL_H = 152;       // px per row
const PADDING_X = 88;     // left/right margin (must ≥ TURN_BULGE + DOT_R + ~10)
const PADDING_Y = 56;     // top margin (room for START label)
const DOT_R = 24;         // milestone circle radius
const TURN_BULGE = 54;    // how far the U-turn bezier curves outward
const ROAD_W = 46;        // road stroke width

// ── Metadata maps ─────────────────────────────────────────────────────────────
const RESOURCE_LABELS: Record<string, string> = {
  item_set: "Quiz Set",
  scenario_lab: "Scenario Lab",
  external_reading: "Reading",
};

const STATUS_COLORS: Record<string, string> = {
  done: "#10b981",
  in_progress: "#3b82f6",
  pending: "#94a3b8",
};

function resLabel(type: string): string {
  return RESOURCE_LABELS[type] ?? type;
}

function dotColor(status: string): string {
  return STATUS_COLORS[status] ?? "#94a3b8";
}

// ── Component ──────────────────────────────────────────────────────────────────
export default function LearningPathRoad({ path }: Props) {
  const { data: skillsData } = useSkills();
  const skillMap = new Map((skillsData ?? []).map((s) => [s.id, s.name]));

  const sorted = [...path.items].sort((a, b) => a.sequence_order - b.sequence_order);
  if (sorted.length === 0) return null;

  const numRows = Math.ceil(sorted.length / ITEMS_PER_ROW);
  const SVG_W = PADDING_X * 2 + ITEMS_PER_ROW * CELL_W;
  const SVG_H = PADDING_Y + numRows * CELL_H + 72; // extra for labels of last row

  // ── Milestone positions ────────────────────────────────────────────────────
  const milestones = sorted.map((item, idx) => {
    const row = Math.floor(idx / ITEMS_PER_ROW);
    const posInRow = idx % ITEMS_PER_ROW;
    const isRTL = row % 2 === 1;
    const col = isRTL ? ITEMS_PER_ROW - 1 - posInRow : posInRow;

    const x = PADDING_X + col * CELL_W + CELL_W / 2;
    const y = PADDING_Y + row * CELL_H + DOT_R + 8;

    return { item, x, y, row, idx };
  });

  // ── Serpentine road path ───────────────────────────────────────────────────
  // Within a row: straight lines. At row boundaries: cubic-bezier U-turns.
  const pathD = milestones.reduce<string>((acc, m, i) => {
    if (i === 0) return `M ${m.x.toFixed(1)} ${m.y.toFixed(1)}`;
    const prev = milestones[i - 1];
    if (m.row !== prev.row) {
      // U-turn curves outward on the right (even rows) or left (odd rows)
      const bulge = prev.row % 2 === 0 ? TURN_BULGE : -TURN_BULGE;
      return (
        `${acc} C ${(prev.x + bulge).toFixed(1)} ${prev.y.toFixed(1)} ` +
        `${(m.x + bulge).toFixed(1)} ${m.y.toFixed(1)} ` +
        `${m.x.toFixed(1)} ${m.y.toFixed(1)}`
      );
    }
    return `${acc} L ${m.x.toFixed(1)} ${m.y.toFixed(1)}`;
  }, "");

  const first = milestones[0];
  const last = milestones[milestones.length - 1];

  return (
    <div style={{ overflowX: "auto", marginTop: "0.5rem" }}>
      <svg
        width={SVG_W}
        height={SVG_H}
        viewBox={`0 0 ${SVG_W} ${SVG_H}`}
        style={{ display: "block" }}
        role="img"
        aria-label="Learning path road map"
      >
        {/* ── Road surface ───────────────────────────────────────────────── */}
        <path
          d={pathD}
          fill="none"
          stroke="var(--border)"
          strokeWidth={ROAD_W}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Centre dashes (white/surface) */}
        <path
          d={pathD}
          fill="none"
          stroke="var(--surface)"
          strokeWidth={2.5}
          strokeLinecap="round"
          strokeDasharray="13 13"
        />

        {/* ── START / FINISH labels ──────────────────────────────────────── */}
        <text
          x={first.x}
          y={first.y - DOT_R - 14}
          textAnchor="middle"
          fontSize={11}
          fill="var(--text-muted)"
        >
          🚀 Start
        </text>
        <text
          x={last.x}
          y={last.y + DOT_R + 54}   // below the last milestone's labels
          textAnchor="middle"
          fontSize={11}
          fill="var(--text-muted)"
        >
          🎯 Finish
        </text>

        {/* ── Milestones ────────────────────────────────────────────────── */}
        {milestones.map(({ item, x, y, idx }) => {
          const color = dotColor(item.status);
          const isDone = item.status === "done";
          const isActive = item.status === "in_progress";
          const rawName = skillMap.get(item.skill_id) ?? "Skill";
          const name = rawName.length > 17 ? rawName.slice(0, 16) + "…" : rawName;
          const labelY = y + DOT_R + 10;

          return (
            <g key={item.id}>
              {/* Native SVG tooltip shows rationale on hover */}
              {item.rationale && <title>{item.rationale}</title>}

              {/* Pulsing ring for the active milestone */}
              {isActive && (
                <circle
                  cx={x}
                  cy={y}
                  r={DOT_R + 9}
                  fill="none"
                  stroke={color}
                  strokeWidth={2}
                  opacity={0.3}
                />
              )}

              {/* White halo cuts the milestone out of the road */}
              <circle cx={x} cy={y} r={DOT_R + 5} fill="var(--surface)" />

              {/* Milestone circle */}
              <circle
                cx={x}
                cy={y}
                r={DOT_R}
                fill={isDone || isActive ? color : "var(--surface)"}
                stroke={color}
                strokeWidth={2.5}
              />

              {/* Step number or checkmark */}
              <text
                x={x}
                y={y}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={isDone ? 15 : 12}
                fontWeight="700"
                fill={isDone || isActive ? "white" : color}
              >
                {isDone ? "✓" : idx + 1}
              </text>

              {/* Skill name */}
              <text
                x={x}
                y={labelY}
                textAnchor="middle"
                dominantBaseline="hanging"
                fontSize={11}
                fontWeight="600"
                fill="var(--text)"
              >
                {name}
              </text>

              {/* Resource type */}
              <text
                x={x}
                y={labelY + 17}
                textAnchor="middle"
                dominantBaseline="hanging"
                fontSize={9}
                fontWeight="500"
                fill={color}
              >
                {resLabel(item.resource_type).toUpperCase()}
              </text>

              {/* Week label */}
              <text
                x={x}
                y={labelY + 31}
                textAnchor="middle"
                dominantBaseline="hanging"
                fontSize={10}
                fill="var(--text-muted)"
              >
                Week {idx + 1}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
