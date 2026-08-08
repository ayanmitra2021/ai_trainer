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
    model = "claude-haiku-4-5-20251001"

    def _build_messages(self, input: GraderInput) -> list[dict[str, Any]]:
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

    def _model_for_input(self, input: GraderInput) -> str:
        """Return the appropriate model for this input without mutating self.model."""
        if input.item_type == "free_text":
            return "claude-opus-5"
        return "claude-haiku-4-5-20251001"

    async def _call_claude(
        self, input: GraderInput
    ) -> tuple[GraderOutput, int | None, int | None]:
        """Override to use per-request model selection without race conditions."""
        system = self._load_prompt()
        messages = self._build_messages(input)
        model = self._model_for_input(input)

        response = await self._client.messages.parse(
            model=model,
            system=system,
            messages=messages,
            max_tokens=self.max_tokens,
            output_format=self.output_model,
        )

        raw = self._extract_parsed(response)
        if raw is None:
            raise ValueError(
                f"Agent '{self.name}': no parsed output found in response. "
                f"Content types: {[getattr(b, 'type', '?') for b in getattr(response, 'content', [])]}"
            )

        if not isinstance(raw, self.output_model):
            try:
                validated = self.output_model.model_validate(
                    raw if isinstance(raw, dict) else raw.model_dump()
                )
            except Exception:
                raise
        else:
            validated = raw

        try:
            tokens_in: int | None = response.usage.input_tokens
            tokens_out: int | None = response.usage.output_tokens
        except AttributeError:
            tokens_in = tokens_out = None

        return validated, tokens_in, tokens_out
