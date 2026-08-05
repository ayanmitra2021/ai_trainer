"""Grader Agent — Step 2.7.

Scores an attempt (MCQ or free-text) with a rationale. Callers persist
attempts to DB.

👤 Review prompts/grader.md (especially partial-credit rubric) before
   trusting at scale. See docs/human-in-the-loop.md.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import Agent
from app.schemas.items import GraderInput, GraderOutput


class GraderAgent(Agent[GraderInput, GraderOutput]):
    """Scores a practitioner's item response and produces a rationale.

    Model selection follows architecture.md:
      - Opus 5 for free-text/rubric grading (highest-judgment step)
      - Haiku 4.5 for MCQ scoring (near-deterministic, high-volume)
    """

    name = "grader"
    output_model = GraderOutput
    # Default model; _build_messages overrides self.model before the API call
    model = "claude-haiku-4-5-20251001"

    def _build_messages(self, input: GraderInput) -> list[dict[str, Any]]:
        # Set the right model before the call is made
        if input.item_type == "free_text":
            self.model = "claude-opus-5"
        else:
            self.model = "claude-haiku-4-5-20251001"

        item_context = {
            "item_id": input.item_id,
            "item_type": input.item_type,
            "prompt": input.item_prompt,
            "answer_key": input.answer_key,
            "trap_explanation": input.trap_explanation,
        }
        context_json = json.dumps(item_context, indent=2)
        response_json = json.dumps(input.submitted_response, indent=2)

        return [
            {
                "role": "user",
                "content": (
                    f"## Item\n\n```json\n{context_json}\n```\n\n"
                    f"## Submitted response\n\n```json\n{response_json}\n```\n\n"
                    "Please grade this response."
                ),
            }
        ]
