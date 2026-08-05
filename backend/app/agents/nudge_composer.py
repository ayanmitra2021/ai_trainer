"""Nudge Composer Agent — Step 3.3.

Drafts an individual, tone-checked nudge for a practitioner who has a
meaningful adoption gap. Nothing auto-sends — status starts at 'drafted' and
requires human approval. Callers persist nudges rows.

Model: Sonnet 5 — tone-sensitive writing; more nuanced than Haiku but
Opus-level reasoning is not required here.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import Agent
from app.schemas.pulse import NudgeComposerInput, NudgeComposerOutput


class NudgeComposerAgent(Agent[NudgeComposerInput, NudgeComposerOutput]):
    """Drafts individual nudges from correlation gap data."""

    name = "nudge_composer"
    model = "claude-sonnet-5"
    output_model = NudgeComposerOutput

    def _build_messages(self, input: NudgeComposerInput) -> list[dict[str, Any]]:
        gaps_json = json.dumps(
            [g.model_dump() for g in input.skill_gaps], indent=2, default=str
        )

        gaps_section = (
            f"## Skill adoption gaps for {input.practitioner_name}\n\n"
            f"```json\n{gaps_json}\n```"
            if input.skill_gaps
            else "## Skill adoption gaps\n\n(No gaps with has_adoption_gap=true — all scores within healthy range.)"
        )

        return [
            {
                "role": "user",
                "content": (
                    f"{gaps_section}\n\n"
                    f"Delivery channel: `{input.channel}`\n\n"
                    "Please draft an appropriate nudge for this practitioner, "
                    "or explain why none is needed."
                ),
            }
        ]
