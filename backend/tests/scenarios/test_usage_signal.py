"""Step 3.1 — Usage-Signal Agent scenarios.

Scenario: A mapped session produces a usage_event linked to the right skill.
Scenario: An unmapped session still produces a record, just without a skill_id.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.usage_signal import UsageSignalAgent
from app.schemas.pulse import RawSignal, UsageSignalInput, UsageSignalOutput
from tests.fixtures.stub_claude_client import StubClaudeClient


def _make_signal(
    signal_type: str = "claude_code_session",
    skill_id: str | None = "prompt_engineering",
    confidence: str | None = "high",
    description: str = "Worked on prompt templates",
    days_ago: int = 3,
) -> RawSignal:
    return RawSignal(
        signal_type=signal_type,
        raw_ref=f"{signal_type}:{uuid.uuid4()}",
        occurred_at=(datetime.now(UTC) - timedelta(days=days_ago)).isoformat(),
        skill_id=skill_id,
        skill_confidence=confidence,
        description=description,
    )


KNOWN_SKILLS = [
    {"skill_id": "prompt_engineering", "name": "Prompt Engineering", "category": "AI Foundations"},
    {"skill_id": "agent_building", "name": "Agent Building", "category": "Advanced AI"},
]


class TestUsageSignalScenarios:
    async def test_mapped_session_produces_event_with_skill_id(
        self, db_session: AsyncSession
    ):
        """
        Scenario: A mapped session produces a usage_event linked to the right skill.
          Given a fixture session with a high-confidence skill mapping for 'prompt_engineering'
          When the Usage-Signal Agent runs
          Then the normalized output includes an event with skill_id='prompt_engineering'
        """
        # Given
        practitioner_id = str(uuid.uuid4())
        mapped_signal = _make_signal(
            signal_type="claude_code_session",
            skill_id="prompt_engineering",
            confidence="high",
            description="Worked on few-shot prompt templates for classification.",
        )

        stub_client = StubClaudeClient(
            response_data={
                "normalized_events": [
                    {
                        "signal_type": "claude_code_session",
                        "skill_id": "prompt_engineering",
                        "raw_ref": mapped_signal.raw_ref,
                        "occurred_at": mapped_signal.occurred_at,
                        "mapping_reasoning": "High-confidence mapping from source project_type field.",
                    }
                ],
                "unmapped_count": 0,
                "summary": "1 event, 1 mapped to prompt_engineering.",
            }
        )

        agent_input = UsageSignalInput(
            practitioner_id=practitioner_id,
            raw_signals=[mapped_signal],
            known_skills=KNOWN_SKILLS,
        )

        # When
        agent = UsageSignalAgent(client=stub_client, db_session=db_session)
        result = await agent.run(agent_input)

        # Then
        assert len(result.normalized_events) == 1
        event = result.normalized_events[0]
        assert event.skill_id == "prompt_engineering"
        assert event.signal_type == "claude_code_session"
        assert event.raw_ref == mapped_signal.raw_ref

    async def test_unmapped_session_produces_record_without_skill_id(
        self, db_session: AsyncSession
    ):
        """
        Scenario: An unmapped session still produces a record, just without a skill_id.
          Given a fixture session with no clear skill signal (ambiguous description)
          When the Usage-Signal Agent runs
          Then the output includes the event with skill_id=None
          And the event is NOT discarded
        """
        # Given
        practitioner_id = str(uuid.uuid4())
        ambiguous_signal = _make_signal(
            signal_type="claude_code_session",
            skill_id=None,
            confidence=None,
            description="Various admin tasks and code review.",
        )

        stub_client = StubClaudeClient(
            response_data={
                "normalized_events": [
                    {
                        "signal_type": "claude_code_session",
                        "skill_id": None,
                        "raw_ref": ambiguous_signal.raw_ref,
                        "occurred_at": ambiguous_signal.occurred_at,
                        "mapping_reasoning": "Source returned null — description too generic to resolve.",
                    }
                ],
                "unmapped_count": 1,
                "summary": "1 event, 0 mapped (1 ambiguous).",
            }
        )

        agent_input = UsageSignalInput(
            practitioner_id=practitioner_id,
            raw_signals=[ambiguous_signal],
            known_skills=KNOWN_SKILLS,
        )

        # When
        agent = UsageSignalAgent(client=stub_client, db_session=db_session)
        result = await agent.run(agent_input)

        # Then — event is returned, not discarded
        assert len(result.normalized_events) == 1
        event = result.normalized_events[0]
        assert event.skill_id is None
        assert result.unmapped_count == 1
        # And the raw_ref is preserved exactly
        assert event.raw_ref == ambiguous_signal.raw_ref
