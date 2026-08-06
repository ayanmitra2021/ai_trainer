"""Step 2.6 — Item-Writer Agent scenarios.

Scenario: A generated MCQ item has exactly one correct option and a non-empty trap explanation.
Scenario: Recalibration responds to a low accuracy rate.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.item_writer import ItemWriterAgent
from app.schemas.items import ItemWriterInput, ItemWriterOutput
from tests.fixtures.stub_claude_client import StubClaudeClient


class TestItemWriterScenarios:
    async def test_generated_mcq_has_one_correct_option_and_trap_explanation(
        self, db_session: AsyncSession
    ):
        """
        Scenario: A generated MCQ item has exactly one correct option and a non-empty trap explanation.
          Given a request for an MCQ item on a specific skill
          When the Item-Writer Agent runs
          Then the returned item has item_type='mcq'
            and answer_key.correct_index is a valid index into options
            and trap_explanation is non-null and non-empty
        """
        # Given
        skill_id = str(uuid.uuid4())
        stub_client = StubClaudeClient(
            response_data={
                "item_type": "mcq",
                "prompt": (
                    "Which of the following best describes the purpose of Structured Outputs "
                    "in the Claude API?"
                ),
                "answer_key": {
                    "options": [
                        "They allow Claude to stream its response token-by-token.",
                        "They enforce a typed JSON schema on Claude's response, eliminating manual parsing.",
                        "They increase Claude's context window for longer conversations.",
                        "They enable Claude to call external tools automatically.",
                    ],
                    "correct_index": 1,
                    "trap_index": 3,
                },
                "trap_explanation": (
                    "The common mistake here is confusing Structured Outputs with tool use. "
                    "Tool use is what lets Claude call external functions; Structured Outputs "
                    "is specifically about enforcing the shape of Claude's final answer using a JSON schema."
                ),
                "difficulty": 0.4,
                "rationale": "Intermediate difficulty — tests distinction between two commonly-confused features.",
            }
        )
        agent_input = ItemWriterInput(
            skill_id=skill_id,
            skill_name="Structured Outputs",
            skill_description="Using JSON schemas to enforce typed responses.",
            item_type="mcq",
            target_difficulty=0.4,
        )

        # When
        agent = ItemWriterAgent(client=stub_client, db_session=db_session)
        result = await agent.run(agent_input)

        # Then
        assert result.item_type == "mcq"
        # answer_key is now a typed MCQAnswerKey (not a raw dict)
        assert isinstance(result.answer_key.correct_index, int)
        assert 0 <= result.answer_key.correct_index < len(result.answer_key.options)
        # Trap explanation is non-null and non-empty
        assert result.trap_explanation is not None
        assert len(result.trap_explanation.strip()) > 0

    async def test_recalibration_responds_to_low_accuracy_rate(
        self, db_session: AsyncSession
    ):
        """
        Scenario: Recalibration responds to a low accuracy rate.
          Given an item whose calibration_stats show near-zero accuracy across attempts
          When recalibration runs (low_accuracy_hint=True)
          Then the returned difficulty rating changes (decreases)
        """
        # Given
        skill_id = str(uuid.uuid4())
        original_difficulty = 0.85  # was too hard

        # Stub simulates a recalibrated, easier item
        stub_client = StubClaudeClient(
            response_data={
                "item_type": "mcq",
                "prompt": "What does the 'system' parameter in the Claude API messages call do?",
                "answer_key": {
                    "options": [
                        "It sets the temperature of Claude's responses.",
                        "It provides Claude with a persistent role or context for the conversation.",
                        "It limits the number of tokens Claude can generate.",
                        "It specifies which Claude model version to use.",
                    ],
                    "correct_index": 1,
                    "trap_index": 3,
                },
                "trap_explanation": (
                    "Model selection is done via the 'model' parameter, not 'system'. "
                    "The system parameter provides Claude with a persistent role or context "
                    "that frames the entire conversation."
                ),
                "difficulty": 0.3,  # recalibrated down from 0.85
                "rationale": "Lowered difficulty due to near-zero accuracy on previous version.",
            }
        )
        agent_input = ItemWriterInput(
            skill_id=skill_id,
            skill_name="Claude API",
            skill_description="Working with the Anthropic Claude API.",
            item_type="mcq",
            target_difficulty=0.3,  # recalibration target
            existing_items_count=50,
            low_accuracy_hint=True,
        )

        # When
        agent = ItemWriterAgent(client=stub_client, db_session=db_session)
        result = await agent.run(agent_input)

        # Then — difficulty has changed (decreased) from the original
        assert result.difficulty < original_difficulty, (
            f"Expected recalibrated difficulty < {original_difficulty}, "
            f"got {result.difficulty}"
        )
