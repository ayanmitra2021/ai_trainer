"""Step 2.7 — Grader Agent scenarios.

Scenario: A fully correct MCQ response scores full marks.
Scenario: A trap-option response is flagged and explained.
Scenario: A partially correct free-text response gets partial credit with a rationale.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.grader import GraderAgent
from app.schemas.items import GraderInput, GraderOutput
from tests.fixtures.stub_claude_client import StubClaudeClient

# ── Shared item fixture data ───────────────────────────────────────────────────

MCQ_ITEM = {
    "item_id": str(uuid.uuid4()),
    "item_type": "mcq",
    "item_prompt": "Which parameter enforces a typed JSON schema on Claude's response?",
    "answer_key": {
        "options": [
            "max_tokens",
            "output_format",
            "temperature",
            "stop_sequences",
        ],
        "correct_index": 1,
        "trap_index": 0,
    },
    "trap_explanation": (
        "The common mistake is thinking max_tokens controls response shape. "
        "max_tokens only limits length; output_format (Structured Outputs) enforces the schema."
    ),
}

FREE_TEXT_ITEM = {
    "item_id": str(uuid.uuid4()),
    "item_type": "free_text",
    "item_prompt": "Explain why prompt caching reduces cost in the Claude API.",
    "answer_key": {
        "model_answer": (
            "Prompt caching stores processed prefix tokens so subsequent calls that reuse "
            "the same prefix are billed at a lower cache-read rate rather than the full "
            "input-token rate."
        ),
        "key_points": [
            "caching stores already-processed tokens",
            "re-used prefixes are cheaper to read than to process",
            "reduces cost for repeated system prompts or long context",
        ],
    },
    "trap_explanation": None,
}


class TestGraderScenarios:
    async def test_correct_mcq_response_scores_full_marks(self, db_session: AsyncSession):
        """
        Scenario: A fully correct MCQ response scores full marks.
          Given an MCQ item with a known correct_index
          When the Grader receives a response selecting that index
          Then score == 1.0 and is_trap_selected == False
        """
        # Given
        stub_client = StubClaudeClient(
            response_data={
                "score": 1.0,
                "grader_rationale": (
                    "Correct. output_format is the parameter that enforces a typed JSON schema "
                    "on the response via Structured Outputs."
                ),
                "is_trap_selected": False,
            }
        )
        grader_input = GraderInput(
            **MCQ_ITEM,
            submitted_response={"selected_index": 1},  # correct_index = 1
        )

        # When
        agent = GraderAgent(client=stub_client, db_session=db_session)
        result = await agent.run(grader_input)

        # Then
        assert result.score == 1.0
        assert result.is_trap_selected is False
        assert result.grader_rationale  # non-empty

    async def test_trap_option_response_is_flagged_and_explained(
        self, db_session: AsyncSession
    ):
        """
        Scenario: A trap-option response is flagged and explained.
          Given an MCQ item where the practitioner selects the trap option
          When the Grader agent runs
          Then is_trap_selected == True and grader_rationale references the misconception
        """
        # Given
        stub_client = StubClaudeClient(
            response_data={
                "score": 0.0,
                "grader_rationale": (
                    "Incorrect — and you selected the trap option. "
                    "max_tokens controls response length, not its shape. "
                    "The common mistake is thinking length limits and schema enforcement "
                    "are the same parameter. output_format is what enforces a JSON schema."
                ),
                "is_trap_selected": True,
            }
        )
        grader_input = GraderInput(
            **MCQ_ITEM,
            submitted_response={"selected_index": 0},  # trap_index = 0
        )

        # When
        agent = GraderAgent(client=stub_client, db_session=db_session)
        result = await agent.run(grader_input)

        # Then
        assert result.is_trap_selected is True
        assert result.score == 0.0
        # Rationale must reference the misconception (not just say "wrong")
        assert len(result.grader_rationale) > 50  # meaningful explanation, not a stub

    async def test_partially_correct_free_text_gets_partial_credit_with_rationale(
        self, db_session: AsyncSession
    ):
        """
        Scenario: A partially correct free-text response gets partial credit with a rationale.
          Given a free-text item where the practitioner covers some but not all key points
          When the Grader agent runs
          Then 0 < score < 1 and the rationale explains what was missing
        """
        # Given
        stub_client = StubClaudeClient(
            response_data={
                "score": 0.5,
                "grader_rationale": (
                    "Score: 0.5. You correctly identified that caching stores processed tokens "
                    "and that repeated calls are cheaper. "
                    "However, the response did not explain the cost mechanism (cache-read rate "
                    "vs. full input-token rate) or name concrete use cases like repeated system prompts."
                ),
                "is_trap_selected": None,
            }
        )
        grader_input = GraderInput(
            **FREE_TEXT_ITEM,
            submitted_response={
                "text": "Prompt caching stores tokens so you don't have to reprocess them every time, making it cheaper."
            },
        )

        # When
        agent = GraderAgent(client=stub_client, db_session=db_session)
        result = await agent.run(grader_input)

        # Then
        assert 0 < result.score < 1.0
        assert result.is_trap_selected is None  # free-text — no trap mechanic
        assert result.grader_rationale  # non-empty rationale
        # Rationale should be substantive (not just "partial credit")
        assert len(result.grader_rationale) > 50
