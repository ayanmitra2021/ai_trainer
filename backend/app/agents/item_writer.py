"""Item-Writer Agent — Step 2.6.

Generates and calibrates practice items, including the trap-reveal mechanic.
Callers persist items to DB.

👤 Review prompts/item_writer.md before trusting generated items at scale.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import Agent
from app.schemas.items import ItemWriterInput, ItemWriterOutput


class ItemWriterAgent(Agent[ItemWriterInput, ItemWriterOutput]):
    """Generates calibrated practice items with trap options and reveal explanations."""

    name = "item_writer"
    # Escalate to Opus 5 for high-difficulty items per architecture.md guidance
    model = "claude-sonnet-5"
    output_model = ItemWriterOutput

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def _maybe_escalate_model(self, target_difficulty: float) -> None:
        """Use Opus 5 for expert-level items where pedagogical judgment matters most."""
        if target_difficulty >= 0.8:
            self.model = "claude-opus-5"
        else:
            self.model = "claude-sonnet-5"

    def _build_messages(self, input: ItemWriterInput) -> list[dict[str, Any]]:
        self._maybe_escalate_model(input.target_difficulty)

        context = {
            "skill_id": input.skill_id,
            "skill_name": input.skill_name,
            "skill_description": input.skill_description,
            "item_type": input.item_type,
            "target_difficulty": input.target_difficulty,
            "existing_items_count": input.existing_items_count,
            "low_accuracy_hint": input.low_accuracy_hint,
        }
        context_json = json.dumps(context, indent=2)

        return [
            {
                "role": "user",
                "content": (
                    f"## Item generation request\n\n```json\n{context_json}\n```\n\n"
                    "Please generate a practice item for this skill."
                ),
            }
        ]
