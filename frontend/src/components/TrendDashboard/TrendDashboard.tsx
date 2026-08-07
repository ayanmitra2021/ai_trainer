/**
 * TrendDashboard — Adoption Trends tab content.
 *
 * Sections (all rendered unconditionally):
 *   1. NudgeInbox          — in-app messages from admins
 *   2. AdoptionTrendChart  — self-assessed baseline vs. weekly quiz performance
 *                            (real-time, no nightly batch required)
 *   3. ProgressTrendChart  — mastery score over time (Skill Profiler synthesis)
 */

import AdoptionTrendChart from "../AdoptionTrendChart";
import NudgeInbox from "../NudgeInbox";
import ProgressTrendChart from "../ProgressTrendChart";

interface Props {
  practitionerId: string;
}

export default function TrendDashboard({ practitionerId }: Props) {
  return (
    <div>
      {/* ── 1. Messages ─────────────────────────────────────────────────── */}
      <NudgeInbox practitionerId={practitionerId} />

      {/* ── 2. Skill calibration (self-assessed vs. quiz performance) ───── */}
      <AdoptionTrendChart practitionerId={practitionerId} />

      {/* ── 3. Mastery score history (Skill Profiler snapshots over time) ── */}
      <ProgressTrendChart practitionerId={practitionerId} />
    </div>
  );
}
