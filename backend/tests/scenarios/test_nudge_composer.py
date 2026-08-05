"""Step 3.3 — Nudge Composer Agent scenarios.

Scenario: A meaningful gap produces a drafted (not sent) nudge with status 'drafted'.
Scenario: A near-zero gap produces no nudge at all.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.nudge_composer import NudgeComposerAgent
from app.schemas.pulse import NudgeComposerInput, SkillGapContext
from tests.fixtures.stub_claude_client import StubClaudeClient


class TestNudgeComposerScenarios:
    async def test_meaningful_gap_produces_drafted_nudge(
        self, db_session: AsyncSession
    ):
        """
        Scenario: A meaningful gap produces a drafted (not sent) nudge.
          Given a practitioner with one skill where trained_score=0.8 and adoption_score=0.05
          When the Nudge Composer Agent runs
          Then should_compose is True
          And the nudge_type and content are populated
          And the content is addressed in second person
        """
        # Given
        practitioner_id = str(uuid.uuid4())
        skill_gap = SkillGapContext(
            skill_name="Prompt Engineering",
            trained_score=0.80,
            adoption_score=0.05,
            gap_score=0.75,
        )

        stub_client = StubClaudeClient(
            response_data={
                "should_compose": True,
                "nudge_type": "gap_alert",
                "content": (
                    "You've built strong foundations in Prompt Engineering — "
                    "it looks like you haven't had many recent chances to apply it in projects. "
                    "Would a small side experiment or pairing session using prompt templates be useful?"
                ),
                "reasoning": (
                    "Gap score 0.75 on a high-mastery skill (0.80) warrants a gap_alert. "
                    "Tone kept encouraging and opportunity-framed."
                ),
            }
        )

        agent_input = NudgeComposerInput(
            practitioner_id=practitioner_id,
            practitioner_name="Alex Rivera",
            skill_gaps=[skill_gap],
            channel="in_app",
        )

        # When
        agent = NudgeComposerAgent(client=stub_client, db_session=db_session)
        result = await agent.run(agent_input)

        # Then
        assert result.should_compose is True
        assert result.nudge_type is not None
        assert result.content is not None
        assert len(result.content) > 0
        # Content should be second-person ("You" not "The practitioner")
        assert result.content.lower().startswith("you"), (
            "Nudge content should be addressed in second person ('You...')"
        )

    async def test_near_zero_gap_produces_no_nudge(
        self, db_session: AsyncSession
    ):
        """
        Scenario: A near-zero gap produces no nudge at all.
          Given a practitioner with no adoption gaps (all gap_scores below threshold)
          When the Nudge Composer Agent runs
          Then should_compose is False
          And nudge_type and content are None
        """
        # Given — no gaps passed (empty skill_gaps list)
        practitioner_id = str(uuid.uuid4())

        stub_client = StubClaudeClient(
            response_data={
                "should_compose": False,
                "nudge_type": None,
                "content": None,
                "reasoning": (
                    "No skills with has_adoption_gap=True — practitioner is applying skills at a healthy rate."
                ),
            }
        )

        agent_input = NudgeComposerInput(
            practitioner_id=practitioner_id,
            practitioner_name="Sam Chen",
            skill_gaps=[],  # empty — no meaningful gaps
            channel="in_app",
        )

        # When
        agent = NudgeComposerAgent(client=stub_client, db_session=db_session)
        result = await agent.run(agent_input)

        # Then — no nudge produced
        assert result.should_compose is False
        assert result.nudge_type is None
        assert result.content is None
        assert result.reasoning  # reasoning must still explain the decision
