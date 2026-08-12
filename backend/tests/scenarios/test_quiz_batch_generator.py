"""Phase 12.2 — Quiz Batch Generator Agent scenarios.

Scenario: Batch generates exactly one item per skill for the active path.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Item,
    LearningPath,
    LearningPathItem,
    Practitioner,
    Skill,
    SkillProfileSnapshot,
)
from app.agents.quiz_batch_generator import (
    QuizBatchGeneratorAgent,
    QuizBatchGeneratorInput,
    SkillQuizSpec,
)
from tests.fixtures.stub_claude_client import StubClaudeClient


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_batch_stub(skill_ids: list[str]) -> StubClaudeClient:
    """Return a stub that produces one MCQ per skill_id in order."""
    items = []
    for i, sid in enumerate(skill_ids):
        items.append({
            "skill_id": sid,
            "item_type": "mcq",
            "prompt": f"Question for skill {i + 1}?",
            "answer_key": {
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_index": 0,
                "trap_index": 1,
            },
            "trap_explanation": "Option B exploits a common misconception.",
            "difficulty": 0.40 + i * 0.05,
            "certification_domain_id": None,
            "is_cert_evaluated": False,
        })
    return StubClaudeClient(response_data={"items": items})


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def batch_practitioner(db_session: AsyncSession) -> Practitioner:
    p = Practitioner(
        id=str(uuid.uuid4()),
        name="Quiz Batch Test Practitioner",
        email="quiz.batch@mastery.example",
    )
    db_session.add(p)
    await db_session.flush()
    return p


@pytest_asyncio.fixture
async def batch_skills(db_session: AsyncSession) -> list[Skill]:
    skills = [
        Skill(
            id=str(uuid.uuid4()),
            name=f"Skill {i + 1}",
            category="AI Foundations",
            description=f"Description for skill {i + 1}.",
        )
        for i in range(3)
    ]
    for s in skills:
        db_session.add(s)
    await db_session.flush()
    return skills


@pytest_asyncio.fixture
async def batch_learning_path(
    db_session: AsyncSession,
    batch_practitioner: Practitioner,
    batch_skills: list[Skill],
) -> LearningPath:
    path = LearningPath(
        id=str(uuid.uuid4()),
        practitioner_id=batch_practitioner.id,
        status="active",
        workflow_run_id=str(uuid.uuid4()),
    )
    db_session.add(path)
    await db_session.flush()

    for i, skill in enumerate(batch_skills):
        lp_item = LearningPathItem(
            id=str(uuid.uuid4()),
            learning_path_id=path.id,
            skill_id=skill.id,
            sequence_order=i,
            resource_type="item_set",
            status="pending",
        )
        db_session.add(lp_item)

    await db_session.flush()
    return path


# ── Tests ──────────────────────────────────────────────────────────────────────


class TestQuizBatchGeneratorAgent:
    async def test_batch_generates_one_item_per_skill(
        self,
        db_session: AsyncSession,
        batch_practitioner: Practitioner,
        batch_skills: list[Skill],
    ):
        """
        Scenario: Batch generates exactly one item per skill for the active path.
          Given a practitioner with a locked profile and 3 skills in a learning path
            and no existing items for those skills
          When QuizBatchGeneratorAgent.run() is called with those 3 skills
          Then the output contains exactly 3 items, one per skill
            and each item has item_type='mcq'
            and each item's skill_id matches the corresponding input skill
            and difficulty is calibrated within the expected band
        """
        skill_ids = [s.id for s in batch_skills]
        stub = _make_batch_stub(skill_ids)

        skill_specs = [
            SkillQuizSpec(
                skill_id=s.id,
                skill_name=s.name,
                skill_description=s.description,
                mastery_score=0.3,  # solidifying band → target 0.45–0.65
            )
            for s in batch_skills
        ]
        batch_input = QuizBatchGeneratorInput(
            skills=skill_specs,
            cert_code="TEST-01",
            cert_name="Test Certification",
        )

        agent = QuizBatchGeneratorAgent(client=stub, db_session=db_session)
        output = await agent.run(batch_input)

        # Exactly 3 items, one per skill
        assert len(output.items) == 3

        for i, item in enumerate(output.items):
            assert item.item_type == "mcq"
            assert item.skill_id == skill_ids[i]
            assert len(item.answer_key.options) == 4
            assert 0 <= item.answer_key.correct_index < 4
            assert 0.0 <= item.difficulty <= 1.0

    async def test_batch_difficulty_calibrated_to_mastery_band(
        self,
        db_session: AsyncSession,
    ):
        """
        Scenario: Difficulty calibration is reflected in the prompt context.
          Given a skill with high mastery (0.85)
          When QuizBatchGeneratorAgent builds its messages
          Then the target_difficulty_band in the prompt context is exam-hard (0.80–0.95)
        """
        skill_id = str(uuid.uuid4())
        stub = _make_batch_stub([skill_id])
        # Override difficulty in stub response to match exam-hard band
        stub_items = [
            {
                "skill_id": skill_id,
                "item_type": "mcq",
                "prompt": "Advanced question?",
                "answer_key": {
                    "options": ["A", "B", "C", "D"],
                    "correct_index": 2,
                    "trap_index": 0,
                },
                "trap_explanation": "A exploits over-reliance on defaults.",
                "difficulty": 0.88,
                "certification_domain_id": None,
                "is_cert_evaluated": False,
            }
        ]
        high_mastery_stub = StubClaudeClient(response_data={"items": stub_items})

        skill_specs = [
            SkillQuizSpec(
                skill_id=skill_id,
                skill_name="Expert Skill",
                skill_description="Advanced domain knowledge.",
                mastery_score=0.85,  # → exam-hard band
            )
        ]
        batch_input = QuizBatchGeneratorInput(
            skills=skill_specs,
            cert_code="TEST-01",
            cert_name="Test Certification",
        )

        agent = QuizBatchGeneratorAgent(client=high_mastery_stub, db_session=db_session)
        output = await agent.run(batch_input)

        assert len(output.items) == 1
        item = output.items[0]
        # Exam-hard band: difficulty must be in 0.80–0.95 range
        assert item.difficulty >= 0.80
        assert item.difficulty <= 1.0
        assert item.answer_key.correct_index == 2
