"""Step 2.4 — Skill Profiler Agent scenarios.

Updated for Phase 9.4 (quiz-only mastery engine):
  All events passed to the profiler are now source='quiz_attempt'.
  Self-assessment and certification signals are no longer sent to the agent.

Scenario: New practitioner with a quiz attempt gets an initial profile.
Scenario: Multiple quiz attempts are weighted, with recency and consistency mattering.
Scenario: Re-running is idempotent absent new quiz signals.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.skill_profiler import SkillProfilerAgent
from app.db.models import Practitioner, Skill, SkillProfileEvent, SkillProfileSnapshot
from app.schemas.learning_paths import SkillProfilerInput, SkillProfilerOutput
from tests.fixtures.stub_claude_client import StubClaudeClient


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def practitioner_and_skill(db_session: AsyncSession):
    p = Practitioner(
        id=str(uuid.uuid4()),
        name="Profiler Test",
        email="profiler.test@mastery.example",
    )
    s = Skill(
        id=str(uuid.uuid4()),
        name="Prompt Engineering",
        category="AI Foundations",
    )
    db_session.add(p)
    db_session.add(s)
    await db_session.flush()
    return p, s


def _quiz_event(practitioner_id: str, skill_id: str, strength: float, days_ago: int = 1):
    """Create a quiz_attempt event dict (the only source used post-Phase 9.4)."""
    return {
        "skill_id": skill_id,
        "source": "quiz_attempt",
        "signal_strength": strength,
        "occurred_at": (datetime.now(UTC) - timedelta(days=days_ago)).isoformat(),
        "metadata": None,
    }


class TestSkillProfilerScenarios:
    async def test_new_practitioner_with_quiz_attempt_gets_initial_profile(
        self,
        db_session: AsyncSession,
        practitioner_and_skill,
    ):
        """
        Scenario: New practitioner with a quiz attempt gets an initial profile.
          Given no existing snapshot and one high-scoring quiz attempt
          When the Skill Profiler Agent runs for that practitioner
          Then a skill score is returned with mastery_score > 0
        """
        # Given
        practitioner, skill = practitioner_and_skill
        events = [_quiz_event(practitioner.id, skill.id, 0.85, days_ago=10)]

        stub_client = StubClaudeClient(
            response_data={
                "skill_scores": [
                    {
                        "skill_id": skill.id,
                        "mastery_score": 0.75,
                        "confidence": 0.4,
                        "reasoning": "One strong quiz attempt indicates solid foundational performance.",
                    }
                ],
                "summary": "One skill with moderate mastery from a single quiz attempt.",
            }
        )
        agent_input = SkillProfilerInput(
            practitioner_id=practitioner.id,
            events=events,
        )

        # When
        agent = SkillProfilerAgent(client=stub_client, db_session=db_session)
        result = await agent.run(agent_input)

        # Then
        assert len(result.skill_scores) >= 1
        scores_for_skill = [s for s in result.skill_scores if s.skill_id == skill.id]
        assert len(scores_for_skill) == 1
        assert scores_for_skill[0].mastery_score > 0

    async def test_multiple_quiz_attempts_are_weighted_by_recency_and_consistency(
        self,
        db_session: AsyncSession,
        practitioner_and_skill,
    ):
        """
        Scenario: Multiple quiz attempts are weighted — recent poor performance tempers earlier success.
          Given a high-scoring older quiz attempt and a low-scoring recent one
          When the Skill Profiler Agent runs
          Then the resulting score reflects both — lower than the early high alone
        """
        # Given
        practitioner, skill = practitioner_and_skill
        events = [
            _quiz_event(practitioner.id, skill.id, 0.9, days_ago=30),  # older high score
            _quiz_event(practitioner.id, skill.id, 0.2, days_ago=5),   # recent low score
        ]

        # The stub returns a blended score — not just the early high or the recent low
        blended_score = 0.55
        stub_client = StubClaudeClient(
            response_data={
                "skill_scores": [
                    {
                        "skill_id": skill.id,
                        "mastery_score": blended_score,
                        "confidence": 0.5,
                        "reasoning": (
                            "Earlier quiz scored well; recent quiz shows a gap — "
                            "recency-weighted estimate is lower than the early peak."
                        ),
                    }
                ],
                "summary": "Mixed quiz results: high older score, low recent score for the same skill.",
            }
        )
        agent_input = SkillProfilerInput(
            practitioner_id=practitioner.id,
            events=events,
        )

        # When
        agent = SkillProfilerAgent(client=stub_client, db_session=db_session)
        result = await agent.run(agent_input)

        # Then — score must be between the two extremes (not either signal alone)
        scores_for_skill = [s for s in result.skill_scores if s.skill_id == skill.id]
        assert len(scores_for_skill) == 1
        score = scores_for_skill[0].mastery_score
        # Not the old high alone (0.9), not the recent low alone (0.2)
        assert 0.2 < score < 0.9, (
            f"Expected a blended score between 0.2 and 0.9, got {score}"
        )

    async def test_re_running_without_new_signals_is_idempotent(
        self,
        db_session: AsyncSession,
        practitioner_and_skill,
    ):
        """
        Scenario: Re-running is idempotent absent new signals.
          Given a practitioner already profiled with no new quiz events since
          When the agent runs again with the same events
          Then the output skill scores are the same as the first run
        """
        # Given
        practitioner, skill = practitioner_and_skill
        events = [_quiz_event(practitioner.id, skill.id, 0.6, days_ago=20)]

        fixed_response = {
            "skill_scores": [
                {
                    "skill_id": skill.id,
                    "mastery_score": 0.6,
                    "confidence": 0.4,
                    "reasoning": "Single quiz attempt signal.",
                }
            ],
            "summary": "One skill with moderate confidence from quiz.",
        }

        # When — run twice with the same events and same stub response
        agent1 = SkillProfilerAgent(
            client=StubClaudeClient(response_data=fixed_response),
            db_session=db_session,
        )
        result1 = await agent1.run(
            SkillProfilerInput(practitioner_id=practitioner.id, events=events)
        )

        agent2 = SkillProfilerAgent(
            client=StubClaudeClient(response_data=fixed_response),
            db_session=db_session,
        )
        result2 = await agent2.run(
            SkillProfilerInput(practitioner_id=practitioner.id, events=events)
        )

        # Then — same output both times
        scores1 = {s.skill_id: s.mastery_score for s in result1.skill_scores}
        scores2 = {s.skill_id: s.mastery_score for s in result2.skill_scores}
        assert scores1 == scores2
