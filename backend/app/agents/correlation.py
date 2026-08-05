"""Correlation Agent — Step 3.2.

Compares a practitioner's trained mastery (skill_profile_snapshots) against
usage evidence (aggregated usage_events) to compute adoption gap scores.

Callers persist correlation_snapshots rows to the database.

Model: Opus 5 — highest-stakes reasoning in the whole system. The gap scores
this agent produces drive nudges sent to real practitioners and leadership
rollups. Getting the framing right matters more than cost here.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import Agent
from app.schemas.pulse import CorrelationInput, CorrelationOutput


class CorrelationAgent(Agent[CorrelationInput, CorrelationOutput]):
    """Computes trained-vs-adopted gap scores per practitioner × skill."""

    name = "correlation"
    model = "claude-opus-5"
    output_model = CorrelationOutput

    def _build_messages(self, input: CorrelationInput) -> list[dict[str, Any]]:
        snapshots_json = json.dumps(
            [s.model_dump() for s in input.skill_snapshots], indent=2, default=str
        )
        usage_json = json.dumps(
            [u.model_dump() for u in input.skill_usage_summaries], indent=2, default=str
        )

        return [
            {
                "role": "user",
                "content": (
                    f"## Skill mastery snapshots for practitioner `{input.practitioner_id}`\n\n"
                    f"```json\n{snapshots_json}\n```\n\n"
                    f"## Usage evidence (last {input.lookback_days} days)\n\n"
                    f"```json\n{usage_json}\n```\n\n"
                    "Please compute the trained-vs-adopted correlation for each skill, "
                    "distinguishing training needs from adoption gaps."
                ),
            }
        ]
