"""Step 2.5 — Curriculum Planner Agent scenarios.

Scenario: A practitioner with one weak skill gets a path prioritising it.
Scenario: A practitioner with an active certification goal gets cert-weighted path.
Scenario: A fully-mastered practitioner gets an empty or maintenance-only path, not an error.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.curriculum_planner import CurriculumPlannerAgent
from app.schemas.learning_paths import (
    CertGoalContext,
    CurriculumPlannerInput,
    SkillScoreContext,
)
from tests.fixtures.stub_claude_client import StubClaudeClient


class TestCurriculumPlannerScenarios:
    async def test_weak_skill_is_placed_first_in_path(self, db_session: AsyncSession):
        """
        Scenario: A practitioner with one weak skill gets a path prioritising it.
          Given skill scores where one skill is significantly weaker than others
          When the Curriculum Planner Agent runs
          Then the resulting path_items sequence places the weak skill first
        """
        # Given
        weak_skill_id = str(uuid.uuid4())
        strong_skill_id = str(uuid.uuid4())
        skill_scores = [
            SkillScoreContext(
                skill_id=weak_skill_id,
                skill_name="Weak Skill",
                mastery_score=0.1,
                confidence=0.8,
            ),
            SkillScoreContext(
                skill_id=strong_skill_id,
                skill_name="Strong Skill",
                mastery_score=0.85,
                confidence=0.9,
            ),
        ]
        stub_client = StubClaudeClient(
            response_data={
                "path_items": [
                    {
                        "skill_id": weak_skill_id,
                        "resource_type": "item_set",
                        "rationale": "Large mastery gap — prioritised first.",
                    },
                ],
                "summary": "One significant gap found; strong skill not included.",
            }
        )
        agent_input = CurriculumPlannerInput(
            practitioner_id=str(uuid.uuid4()),
            skill_scores=skill_scores,
            certification_goal=None,
        )

        # When
        agent = CurriculumPlannerAgent(client=stub_client, db_session=db_session)
        result = await agent.run(agent_input)

        # Then
        assert len(result.path_items) >= 1
        assert result.path_items[0].skill_id == weak_skill_id

    async def test_active_cert_goal_weights_path_toward_cert_skills(
        self, db_session: AsyncSession
    ):
        """
        Scenario: A practitioner with an active certification goal gets cert-weighted path.
          Given a practitioner_certification_goals row with status 'selected'
            and that certification's certification_skills weights
          When the Curriculum Planner Agent runs
          Then the path prioritises cert skills over equally-weak non-cert skills
        """
        # Given
        cert_skill_id = str(uuid.uuid4())
        non_cert_skill_id = str(uuid.uuid4())
        # Both equally weak, but cert_skill is in the certification
        skill_scores = [
            SkillScoreContext(
                skill_id=cert_skill_id,
                skill_name="Cert-relevant Skill",
                mastery_score=0.3,
                confidence=0.7,
            ),
            SkillScoreContext(
                skill_id=non_cert_skill_id,
                skill_name="Non-cert Skill",
                mastery_score=0.3,
                confidence=0.7,
            ),
        ]
        cert_goal = CertGoalContext(
            certification_code="CCDV-F",
            certification_name="Claude Certified Developer – Foundations",
            status="selected",
            skill_weights={cert_skill_id: 0.9},  # only cert_skill_id is in the cert
        )
        stub_client = StubClaudeClient(
            response_data={
                "path_items": [
                    {
                        "skill_id": cert_skill_id,
                        "resource_type": "item_set",
                        "rationale": "High cert weight + mastery gap — prioritised first.",
                    },
                    {
                        "skill_id": non_cert_skill_id,
                        "resource_type": "item_set",
                        "rationale": "Equal mastery gap but outside cert scope — secondary.",
                    },
                ],
                "summary": "Cert-weighted path: cert skills come first.",
            }
        )
        agent_input = CurriculumPlannerInput(
            practitioner_id=str(uuid.uuid4()),
            skill_scores=skill_scores,
            certification_goal=cert_goal,
        )

        # When
        agent = CurriculumPlannerAgent(client=stub_client, db_session=db_session)
        result = await agent.run(agent_input)

        # Then
        assert len(result.path_items) >= 1
        # Cert skill must appear before non-cert skill
        path_skill_ids = [item.skill_id for item in result.path_items]
        assert cert_skill_id in path_skill_ids
        cert_idx = path_skill_ids.index(cert_skill_id)
        if non_cert_skill_id in path_skill_ids:
            non_cert_idx = path_skill_ids.index(non_cert_skill_id)
            assert cert_idx < non_cert_idx

    async def test_fully_mastered_practitioner_gets_maintenance_path_not_error(
        self, db_session: AsyncSession
    ):
        """
        Scenario: A fully-mastered practitioner gets an empty or maintenance-only path, not an error.
          Given a practitioner with all skills at mastery >= 0.9
          When the Curriculum Planner Agent runs
          Then the agent returns successfully (no exception)
          And the path is either empty or contains only maintenance items
        """
        # Given
        skill_ids = [str(uuid.uuid4()) for _ in range(3)]
        skill_scores = [
            SkillScoreContext(
                skill_id=sid,
                skill_name=f"Mastered Skill {i}",
                mastery_score=0.95,
                confidence=0.9,
            )
            for i, sid in enumerate(skill_ids)
        ]
        # Stub returns a short maintenance path
        stub_client = StubClaudeClient(
            response_data={
                "path_items": [
                    {
                        "skill_id": skill_ids[0],
                        "resource_type": "scenario_lab",
                        "rationale": "Refresher item to maintain mastery.",
                    }
                ],
                "summary": "All skills well-mastered; one light refresher included.",
            }
        )
        agent_input = CurriculumPlannerInput(
            practitioner_id=str(uuid.uuid4()),
            skill_scores=skill_scores,
        )

        # When — must not raise
        agent = CurriculumPlannerAgent(client=stub_client, db_session=db_session)
        result = await agent.run(agent_input)

        # Then — completed without exception; path is short or empty
        assert result is not None
        assert len(result.path_items) <= len(skill_scores)  # not more items than skills
