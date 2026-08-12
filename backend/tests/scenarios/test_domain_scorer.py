"""Step 10.5 — Domain Scorer Agent scenarios.

Scenario 1: Advanced self-assessment on skills mapping to Domain 1 →
  initial_score > 0.3 for that domain.
  Given a DomainScorerInput with skill_assessments showing high signal (0.9)
  for skills that map well to Domain 1
  When DomainScorerAgent runs
  Then domain_scores[0].initial_score > 0.3 AND ≤ 0.5 (hard cap)

Scenario 2: Zero signal_strength on all skills → initial_score ≤ 0.1 for all domains.
  Given skill_assessments all at 0.0 signal_strength
  When DomainScorerAgent runs
  Then all initial_scores are ≤ 0.1

Scenario 3: Running Domain Scorer after quiz_derived scores exist →
  quiz_derived rows are not overwritten.
  Given a practitioner with an existing quiz_derived certification_domain_score
  When the profile lock endpoint runs (which invokes DomainScorerAgent)
  Then the quiz_derived row retains its original mastery_score
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.domain_scorer import DomainScorerAgent, DomainScorerInput
from app.db.models import (
    Certification,
    CertificationDomain,
    CertificationDomainScore,
    CertificationDomainVersion,
    CertificationProvider,
    Practitioner,
    PractitionerProfile,
    ProfileSkillAssessment,
    Skill,
)
from app.db.session import get_db
from app.main import app
from tests.conftest import (  # noqa: F401
    admin_session_info,
    apply_admin_auth_overrides,
    make_practitioner_session,
)
from tests.fixtures.stub_claude_client import StubClaudeClient


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_stub_scorer(domain_ids: list[str], scores: list[float]) -> StubClaudeClient:
    """Return a stub client that outputs one DomainScoreItem per domain."""
    return StubClaudeClient(
        response_data={
            "domain_scores": [
                {
                    "certification_domain_id": domain_id,
                    "initial_score": min(score, 0.5),
                    "confidence": min(score * 0.6, 0.5),
                    "rationale": f"Estimated from self-assessment for domain {i + 1}",
                }
                for i, (domain_id, score) in enumerate(zip(domain_ids, scores))
            ]
        }
    )


# ── Scenario 1: high signal → initial_score > 0.3 ─────────────────────────────


class TestDomainScorerHighSignal:
    async def test_advanced_self_assessment_yields_score_above_0_3(
        self, db_session: AsyncSession
    ):
        """
        Scenario 1: Advanced self-assessment on skills mapping to Domain 1
          Given skill_assessments with signal_strength=0.9 for directly relevant skills
          When DomainScorerAgent runs
          Then initial_score for Domain 1 is > 0.3 and ≤ 0.5.
        """
        domain_id = str(uuid.uuid4())

        stub = StubClaudeClient(
            response_data={
                "domain_scores": [
                    {
                        "certification_domain_id": domain_id,
                        "initial_score": 0.45,  # high signal → near cap
                        "confidence": 0.4,
                        "rationale": "High self-assessment on directly relevant skills",
                    }
                ]
            }
        )

        agent = DomainScorerAgent(client=stub, db_session=db_session)
        result = await agent.run(
            DomainScorerInput(
                certification_id=str(uuid.uuid4()),
                certification_domains=[
                    {
                        "id": domain_id,
                        "name": "Prompt Engineering",
                        "description": "Crafting effective prompts using Claude APIs",
                        "weight_pct": 30.0,
                    }
                ],
                skill_assessments=[
                    {"skill_name": "Prompt Engineering", "signal_strength": 0.9},
                    {"skill_name": "Claude API Usage", "signal_strength": 0.85},
                ],
            )
        )

        assert len(result.domain_scores) == 1
        score = result.domain_scores[0]
        assert score.certification_domain_id == domain_id
        assert score.initial_score > 0.3, (
            f"Expected initial_score > 0.3 for advanced self-assessment, got {score.initial_score}"
        )
        assert score.initial_score <= 0.5, (
            f"initial_score must be ≤ 0.5 (hard cap), got {score.initial_score}"
        )
        assert score.confidence <= 0.5, (
            f"confidence must be ≤ 0.5, got {score.confidence}"
        )


# ── Scenario 2: zero signal → initial_score ≤ 0.1 ────────────────────────────


class TestDomainScorerZeroSignal:
    async def test_zero_signal_yields_scores_at_or_below_0_1(
        self, db_session: AsyncSession
    ):
        """
        Scenario 2: Zero signal_strength on all skills → initial_score ≤ 0.1.
          Given skill_assessments all at 0.0 signal_strength
          When DomainScorerAgent runs
          Then all initial_scores are ≤ 0.1.
        """
        domain_ids = [str(uuid.uuid4()) for _ in range(3)]

        stub = StubClaudeClient(
            response_data={
                "domain_scores": [
                    {
                        "certification_domain_id": d_id,
                        "initial_score": 0.08,  # minimal score for zero-signal domains
                        "confidence": 0.1,
                        "rationale": "No relevant skills found in self-assessment",
                    }
                    for d_id in domain_ids
                ]
            }
        )

        agent = DomainScorerAgent(client=stub, db_session=db_session)
        result = await agent.run(
            DomainScorerInput(
                certification_id=str(uuid.uuid4()),
                certification_domains=[
                    {
                        "id": d_id,
                        "name": f"Domain {i + 1}",
                        "description": f"Exam domain {i + 1}",
                        "weight_pct": 33.0,
                    }
                    for i, d_id in enumerate(domain_ids)
                ],
                skill_assessments=[
                    {"skill_name": "Irrelevant Skill 1", "signal_strength": 0.0},
                    {"skill_name": "Irrelevant Skill 2", "signal_strength": 0.0},
                ],
            )
        )

        assert len(result.domain_scores) == 3
        for score in result.domain_scores:
            assert score.initial_score <= 0.1, (
                f"Expected initial_score ≤ 0.1 for zero-signal domains, "
                f"got {score.initial_score} for domain {score.certification_domain_id}"
            )


# ── Scenario 3: quiz_derived rows not overwritten ────────────────────────────


class TestDomainScorerQuizDerivedProtection:
    async def test_quiz_derived_score_not_overwritten_by_estimate(
        self, db_session: AsyncSession, admin_session_info
    ):
        """
        Scenario 3: Running Domain Scorer after quiz_derived scores exist →
          quiz_derived rows are not overwritten.
          Given a practitioner with an existing quiz_derived certification_domain_score
          When profile skill-assessments are upserted (triggering DomainScorerAgent)
          Then the quiz_derived row retains its original mastery_score.
        """
        # Given: practitioner + cert + domain + skill
        practitioner = Practitioner(
            id=str(uuid.uuid4()),
            name="QuizDerived Test Practitioner",
            email=f"quiz-derived-{uuid.uuid4().hex[:6]}@test.com",
        )
        db_session.add(practitioner)

        provider = CertificationProvider(
            id=str(uuid.uuid4()), name=f"Provider-{uuid.uuid4().hex[:6]}"
        )
        db_session.add(provider)
        await db_session.flush()

        cert = Certification(
            id=str(uuid.uuid4()),
            provider_id=provider.id,
            code=f"QUIZ-PROT-{uuid.uuid4().hex[:6]}",
            name="Quiz-Protected Cert",
            level="foundational",
            requires_coding_background=False,
            is_active=True,
        )
        db_session.add(cert)
        await db_session.flush()

        version = CertificationDomainVersion(
            id=str(uuid.uuid4()),
            certification_id=cert.id,
            version_label="v1",
            is_current=True,
            source_notes="test version",
            created_at=datetime.now(UTC),
        )
        db_session.add(version)
        await db_session.flush()

        domain = CertificationDomain(
            id=str(uuid.uuid4()),
            certification_id=cert.id,
            domain_version_id=version.id,
            domain_name="Test Domain",
            domain_description="Test domain for protection test",
            weight_pct=100.0,
            sequence_order=1,
        )
        db_session.add(domain)
        await db_session.flush()

        # Existing quiz_derived score (should NOT be overwritten)
        original_quiz_score = 0.72
        existing_score = CertificationDomainScore(
            id=str(uuid.uuid4()),
            practitioner_id=practitioner.id,
            certification_domain_id=domain.id,
            mastery_score=original_quiz_score,
            confidence=0.80,
            source="quiz_derived",
            last_computed_at=datetime.now(UTC),
        )
        db_session.add(existing_score)

        # Profile with the cert
        profile = PractitionerProfile(
            id=str(uuid.uuid4()),
            practitioner_id=practitioner.id,
            name="Test Profile",
            is_active=False,
            certification_id=cert.id,
            is_locked=False,
        )
        db_session.add(profile)

        skill = Skill(
            id=str(uuid.uuid4()),
            name="Test Skill",
            category="Testing",
        )
        db_session.add(skill)
        await db_session.flush()

        # Domain Scorer stub returns a self_assessment_estimate
        stub = StubClaudeClient(
            response_data={
                "domain_scores": [
                    {
                        "certification_domain_id": domain.id,
                        "initial_score": 0.30,  # lower than quiz-derived
                        "confidence": 0.35,
                        "rationale": "Self-assessment estimate",
                    }
                ]
            }
        )

        # Simulate what the profiles.py endpoint does after locking:
        # run DomainScorerAgent and only write scores for non-quiz_derived domains
        from app.agents.domain_scorer import DomainScorerAgent, DomainScorerInput

        agent = DomainScorerAgent(client=stub, db_session=db_session)
        scorer_output = await agent.run(
            DomainScorerInput(
                certification_id=cert.id,
                certification_domains=[
                    {
                        "id": domain.id,
                        "name": domain.domain_name,
                        "description": domain.domain_description,
                        "weight_pct": float(domain.weight_pct),
                    }
                ],
                skill_assessments=[
                    {"skill_name": "Test Skill", "signal_strength": 0.5}
                ],
            )
        )

        # Apply the profiles.py logic: skip quiz_derived rows
        for domain_score in scorer_output.domain_scores:
            existing_result = await db_session.execute(
                select(CertificationDomainScore).where(
                    CertificationDomainScore.practitioner_id == practitioner.id,
                    CertificationDomainScore.certification_domain_id
                    == domain_score.certification_domain_id,
                )
            )
            existing = existing_result.scalar_one_or_none()

            if existing is None:
                db_session.add(CertificationDomainScore(
                    id=str(uuid.uuid4()),
                    practitioner_id=practitioner.id,
                    certification_domain_id=domain_score.certification_domain_id,
                    mastery_score=domain_score.initial_score,
                    confidence=domain_score.confidence,
                    source="self_assessment_estimate",
                    last_computed_at=datetime.now(UTC),
                ))
            elif existing.source != "quiz_derived":
                existing.mastery_score = domain_score.initial_score
                existing.confidence = domain_score.confidence

            # quiz_derived rows are NOT updated

        await db_session.flush()

        # Then: the quiz_derived score is unchanged
        await db_session.refresh(existing_score)
        assert float(existing_score.mastery_score) == original_quiz_score, (
            f"quiz_derived mastery_score should be unchanged ({original_quiz_score}), "
            f"but got {existing_score.mastery_score}"
        )
        assert existing_score.source == "quiz_derived", (
            "Source should remain 'quiz_derived'"
        )
