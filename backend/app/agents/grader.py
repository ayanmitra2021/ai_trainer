"""Grader Agent — Step 2.7.

Scores an attempt (MCQ or free-text) with a rationale. Callers persist
attempts to DB.

👤 Review prompts/grader.md (especially partial-credit rubric) before
   trusting at scale. See docs/human-in-the-loop.md.
"""

from __future__ import annotations

import json
import pydantic
from typing import Any

from app.agents.base import Agent
from app.agents.model_client import _extract_parsed
from app.schemas.items import GraderInput, GraderOutput


class GraderAgent(Agent[GraderInput, GraderOutput]):
    """Scores a practitioner's item response and produces a rationale.

    Model selection follows architecture.md:
      - Opus 5 for free-text/rubric grading (highest-judgment step)
      - Haiku 4.5 for MCQ scoring (near-deterministic, high-volume)

    When APP_BRAIN_MODEL=NVIDIA the client ignores the passed model string
    and always uses the configured NVIDIA model — so the Anthropic model
    differentiation is a no-op in that mode, which is acceptable.
    """

    name = "grader"
    output_model = GraderOutput
    # Default model (used by base class if _call_model is not overridden;
    # kept for observability / agent_runs.model_used logging).
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
        """Select the appropriate model based on item type.

        Free-text grading needs Opus 5's rubric-reasoning depth.
        MCQ scoring is near-deterministic and Haiku 4.5 handles it well.
        """
        if input.item_type == "free_text":
            return "claude-opus-5"
        return "claude-haiku-4-5-20251001"

    async def _call_model(
        self, input: GraderInput
    ) -> tuple[GraderOutput, int | None, int | None]:
        """Override base _call_model to apply per-item-type model selection.

        The base Agent.run() calls this method. We select the right Claude model
        based on item type before delegating to the client.
        When APP_BRAIN_MODEL=NVIDIA the client ignores the model string anyway.
        """
        system = self._load_prompt()
        messages = self._build_messages(input)
        model = self._model_for_input(input)

        response = await self._client.parse(
            model=model,
            system=system,
            messages=messages,
            max_tokens=self.max_tokens,
            output_format=self.output_model,
        )

        raw = _extract_parsed(response)
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
            except pydantic.ValidationError:
                raise
        else:
            validated = raw

        try:
            tokens_in: int | None = response.usage.input_tokens
            tokens_out: int | None = response.usage.output_tokens
        except AttributeError:
            tokens_in = tokens_out = None

        return validated, tokens_in, tokens_out
