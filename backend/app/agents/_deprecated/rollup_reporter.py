"""Rollup Reporter Agent — Step 3.4.

Produces aggregate, privacy-safe leadership rollups from anonymized correlation
data. Callers persist rollups rows.

Model: Sonnet 5 — narrative synthesis over pre-computed numbers.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import Agent
from app.schemas.pulse import RollupReporterInput, RollupReporterOutput

# ── Privacy policy ────────────────────────────────────────────────────────────
# Minimum cohort size before any aggregate metrics are produced.
# Below this threshold, metrics and narrative are withheld entirely — this is a
# structural privacy commitment, not a display preference. Small cohorts allow
# leaders to reverse-engineer individual scores from aggregates.
MINIMUM_COHORT_SIZE: int = 5


class RollupReporterAgent(Agent[RollupReporterInput, RollupReporterOutput]):
    """Produces privacy-safe leadership rollups from anonymized correlation data."""

    name = "rollup_reporter"
    model = "claude-sonnet-5"
    output_model = RollupReporterOutput

    def _build_messages(self, input: RollupReporterInput) -> list[dict[str, Any]]:
        summaries_json = json.dumps(
            [s.model_dump() for s in input.practitioner_summaries], indent=2, default=str
        )

        return [
            {
                "role": "user",
                "content": (
                    f"## Rollup request\n\n"
                    f"- Scope: `{input.scope}` / `{input.scope_ref}`\n"
                    f"- Period: {input.period_start} → {input.period_end}\n"
                    f"- Practitioner count: {input.practitioner_count}\n"
                    f"- Minimum cohort size: {input.min_cohort_size}\n\n"
                    f"## Anonymized practitioner summaries\n\n"
                    f"```json\n{summaries_json}\n```\n\n"
                    "Please produce the rollup report. Apply the privacy gate first."
                ),
            }
        ]
