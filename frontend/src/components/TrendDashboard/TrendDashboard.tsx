/**
 * TrendDashboard — Adoption Trends tab content.
 *
 * Sections (all rendered unconditionally):
 *   1. NudgeInbox          — in-app messages from admins
 *   2. AdoptionTrendChart  — self-assessed baseline vs. weekly quiz performance
 *                            (real-time, no nightly batch required)
 *   3. ProgressTrendChart  — mastery score over time (Skill Profiler synthesis)
 *   4. MockExamHistory     — exam table + recency-weighted confidence gauge
 */

import AdoptionTrendChart from "../AdoptionTrendChart";
import MockExamHistory from "../MockExamHistory/MockExamHistory";
import NudgeInbox from "../NudgeInbox";
import ProgressTrendChart from "../ProgressTrendChart";
import { useSession } from "../../context/SessionContext";

interface Props {
  practitionerId: string;
}

export default function TrendDashboard({ practitionerId }: Props) {
  const { session } = useSession();
  const isEnterprise = session?.plan_tier === "enterprise";

  return (
    <div>
      {/* ── 1. Messages ─────────────────────────────────────────────────── */}
      {isEnterprise ? (
        <NudgeInbox practitionerId={practitionerId} />
      ) : (
        <div
          style={{
            padding: "1.5rem",
            background: "rgba(100,116,139,0.08)",
            border: "1px solid var(--border)",
            borderRadius: 10,
            textAlign: "center",
            color: "var(--text-muted)",
            marginBottom: "1.5rem",
          }}
        >
          🔒 Nudge messages are available on the Enterprise plan. Contact your administrator to upgrade.
        </div>
      )}

      {/* ── 2. Skill calibration (self-assessed vs. quiz performance) ───── */}
      <AdoptionTrendChart practitionerId={practitionerId} />

      {/* ── 3. Mastery score history (Skill Profiler snapshots over time) ── */}
      <ProgressTrendChart practitionerId={practitionerId} />

      {/* ── 4. Mock exam history + confidence score (Phase 19) ──────────── */}
      <MockExamHistory practitionerId={practitionerId} />
    </div>
  );
}
