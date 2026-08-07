"""Nudge Category Generator Agent — Step 7.2.

Ingests aggregate KPI data (no PII) and proposes up to 10 actionable nudge
categories, each with machine-readable criteria and a tone hint for the Nudge
Composer.

Model: claude-sonnet-4-5 — needs nuanced judgment about what constitutes
actionable vs. punishing categories; the aggregate-only privacy contract makes
this lower-stakes than individual-facing agents.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import Agent
from app.schemas.nudge_campaign import NudgeCategoryInput, NudgeCategoryOutput


class NudgeCategoryGeneratorAgent(Agent[NudgeCategoryInput, NudgeCategoryOutput]):
    """Generates nudge categories from aggregate practitioner data."""

    name = "nudge_category_generator"
    model = "claude-sonnet-4-5"
    output_model = NudgeCategoryOutput

    def _build_messages(self, input: NudgeCategoryInput) -> list[dict[str, Any]]:
        skill_gap_json = json.dumps(
            [
                g.model_dump() if hasattr(g, "model_dump") else g
                for g in input.skill_gap_summary
            ],
            indent=2,
        )
        return [
            {
                "role": "user",
                "content": (
                    f"## Aggregate KPI snapshot\n\n"
                    f"- Total practitioners: {input.total_practitioners}\n"
                    f"- No quiz activity in 7 days: {input.practitioners_no_quiz_7d}\n"
                    f"- No quiz activity in 14 days: {input.practitioners_no_quiz_14d}\n"
                    f"- No active profile: {input.practitioners_no_profile}\n"
                    f"- Profile exists but no skill ratings: {input.practitioners_profile_unrated}\n"
                    f"- Mastery stalled 14+ days: {input.practitioners_stalled}\n"
                    f"- Near cert-ready (≥80% avg mastery): {input.practitioners_near_cert_ready}\n"
                    f"- Nudges sent in last 7 days: {input.nudges_sent_last_7d}\n\n"
                    f"## Top skill gaps\n\n```json\n{skill_gap_json}\n```\n\n"
                    "Please propose up to 10 actionable nudge categories from this data."
                ),
            }
        ]
