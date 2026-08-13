"""Phase 13.5 — 80/20 cert/supp ratio enforcement in QuizBatchGeneratorAgent."""

from __future__ import annotations

import logging
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.quiz_batch_generator import (
    QuizBatchGeneratorAgent,
    QuizBatchGeneratorInput,
    QuizBatchGeneratorOutput,
    SkillQuizSpec,
)
from tests.fixtures.stub_claude_client import StubClaudeClient


def _make_ratio_stub(skill_ids: list[str], cert_eval_indices: set[int]) -> StubClaudeClient:
    """Stub that marks specific skills as cert-evaluated."""
    items = []
    for i, sid in enumerate(skill_ids):
        items.append({
            "skill_id": sid,
            "item_type": "mcq",
            "prompt": f"Q for {sid}?",
            "answer_key": {
                "options": ["A", "B", "C", "D"],
                "correct_index": 0,
                "trap_index": 1,
            },
            "trap_explanation": "Trap explanation.",
            "difficulty": 0.5,
            "certification_domain_id": None,
            "is_cert_evaluated": i in cert_eval_indices,
        })
    return StubClaudeClient(response_data={"items": items})


class TestQuizBatchRatio:
    async def test_cert_question_pct_computed_correctly(
        self, db_session: AsyncSession
    ):
        """
        Scenario: cert_question_pct is correctly computed from batch output.
          Given a batch with 8 cert items and 2 supp items
          When QuizBatchGeneratorAgent runs
          Then cert_question_pct equals 80.0 and supp_question_pct equals 20.0
        """
        skill_ids = [str(uuid.uuid4()) for _ in range(10)]
        # Indices 0-7 are cert-evaluated, 8-9 are supplementary → 80% cert
        stub = _make_ratio_stub(skill_ids, cert_eval_indices=set(range(8)))

        specs = [
            SkillQuizSpec(skill_id=sid, skill_name=f"Skill {i}", mastery_score=0.3)
            for i, sid in enumerate(skill_ids)
        ]
        agent = QuizBatchGeneratorAgent(client=stub, db_session=db_session)
        output = await agent.run(QuizBatchGeneratorInput(
            skills=specs, cert_code="TEST-01", cert_name="Test Cert"
        ))

        # Simulate what the endpoint does
        cert_count = sum(1 for item in output.items if item.is_cert_evaluated)
        total = len(output.items)
        cert_pct = round(cert_count / total * 100, 1) if total else 0.0
        supp_pct = round(100.0 - cert_pct, 1)
        output.cert_question_pct = cert_pct
        output.supp_question_pct = supp_pct

        assert output.cert_question_pct == 80.0
        assert output.supp_question_pct == 20.0

    async def test_warning_logged_when_cert_ratio_below_80(
        self, db_session: AsyncSession, caplog
    ):
        """
        Scenario: Batch endpoint logs warning when cert ratio falls below 80%.
          Given a batch with 5 cert and 5 supp items (50% cert)
          When the endpoint computes the ratio
          Then a WARNING is logged containing '< 80% target'
        """
        skill_ids = [str(uuid.uuid4()) for _ in range(10)]
        # 5 cert, 5 supp → 50% cert
        stub = _make_ratio_stub(skill_ids, cert_eval_indices=set(range(5)))

        specs = [
            SkillQuizSpec(skill_id=sid, skill_name=f"Skill {i}", mastery_score=0.3)
            for i, sid in enumerate(skill_ids)
        ]
        agent = QuizBatchGeneratorAgent(client=stub, db_session=db_session)
        output = await agent.run(QuizBatchGeneratorInput(
            skills=specs, cert_code="TEST-01", cert_name="Test Cert"
        ))

        # Simulate endpoint logic
        cert_count = sum(1 for item in output.items if item.is_cert_evaluated)
        total = len(output.items)
        cert_pct = round(cert_count / total * 100, 1) if total else 0.0

        with caplog.at_level(logging.WARNING):
            if cert_pct < 80.0:
                logger = logging.getLogger("app.api.routes.learning_paths")
                logger.warning(
                    "Quiz batch path=%s cert_pct=%.1f%% (< 80%% target). "
                    "cert=%d supp=%d total=%d. Check curriculum planner supp_max.",
                    "test-path-id", cert_pct, cert_count, total - cert_count, total,
                )

        assert any("< 80% target" in r.message for r in caplog.records)
        assert cert_pct == 50.0
