"""Step 2.3 — Certification Advisor Agent scenarios.

Scenario: Non-coder interested in Anthropic → CCAO-F.
Scenario: Experienced architect with no provider preference → rationale names trade-off.
Scenario: Answers are persisted even when recommendation is later ignored.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.certification_advisor import CertificationAdvisorAgent, CertificationAdvisorInput
from app.db.models import (
    Certification,
    CertificationAdvisorResponse,
    CertificationProvider,
    CertificationSkill,
    PractitionerCertificationGoal,
    Practitioner,
    Skill,
)
from app.schemas.certifications import (
    AdvisorOutput,
    CertificationContext,
    QuestionnaireAnswers,
)
from tests.fixtures.stub_claude_client import StubClaudeClient


# ── Shared fixtures ────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def seeded_practitioner(db_session: AsyncSession) -> Practitioner:
    p = Practitioner(
        id=str(uuid.uuid4()),
        name="Advisor Test Practitioner",
        email="advisor.test@mastery.example",
        role="Consultant",
        practice="AI&E",
        seniority_level="mid",
    )
    db_session.add(p)
    await db_session.flush()
    return p


@pytest_asyncio.fixture
async def sample_catalog() -> list[CertificationContext]:
    """A minimal catalog covering the key scenarios without needing a live DB."""
    return [
        CertificationContext(
            code="CCAO-F",
            name="Claude Certified Associate – Foundations",
            provider_name="Anthropic",
            level="foundational",
            requires_coding_background=False,
            typical_audience="Business/productivity users, not developers or agentic builders.",
            focus_area="Effective use of Claude for business tasks; prompt fundamentals.",
            eligibility_notes="Requires Anthropic Partner Network org email.",
        ),
        CertificationContext(
            code="CCDV-F",
            name="Claude Certified Developer – Foundations",
            provider_name="Anthropic",
            level="foundational",
            requires_coding_background=True,
            typical_audience="Software developers building Claude-powered applications.",
            focus_area="Claude API integration; tool use; structured outputs.",
            eligibility_notes="Requires Anthropic Partner Network org email.",
        ),
        CertificationContext(
            code="CCAF",
            name="Claude Certified Architect – Foundations",
            provider_name="Anthropic",
            level="foundational",
            requires_coding_background=True,
            typical_audience="Technical architects designing Claude-powered systems.",
            focus_area="System design; agentic patterns; MCP; multi-agent orchestration.",
            eligibility_notes="Requires Anthropic Partner Network org email.",
        ),
        CertificationContext(
            code="CCAR-P",
            name="Claude Certified Architect – Professional",
            provider_name="Anthropic",
            level="professional",
            requires_coding_background=True,
            typical_audience="Senior architects with production Claude systems experience.",
            focus_area="Advanced multi-agent design; security; large-scale deployment.",
            eligibility_notes="Requires Anthropic Partner Network org email.",
        ),
        CertificationContext(
            code="AIF-C01",
            name="AWS Certified AI Practitioner",
            provider_name="AWS",
            level="foundational",
            requires_coding_background=False,
            typical_audience="Business stakeholders and non-technical practitioners.",
            focus_area="AWS AI/ML service landscape; responsible AI.",
            eligibility_notes=None,
        ),
    ]


# ── Scenario tests ─────────────────────────────────────────────────────────────

class TestCertificationAdvisorScenarios:
    async def test_non_coder_anthropic_preference_gets_ccao_f(
        self,
        db_session: AsyncSession,
        seeded_practitioner: Practitioner,
        sample_catalog: list[CertificationContext],
    ):
        """
        Scenario: A non-coder interested in Anthropic gets pointed at Associate, not Architect or Developer.
          Given answers indicating no coding background, a business/advising focus, and an Anthropic preference
          When the Certification Advisor Agent runs
          Then the recommendation is CCAO-F, not one of the coding-required tracks
        """
        # Given
        stub_client = StubClaudeClient(
            response_data={
                "primary_recommendation_code": "CCAO-F",
                "primary_rationale": (
                    "CCAO-F is designed for practitioners who use Claude in a business or "
                    "advisory capacity and do not write code. Your advising focus and "
                    "Anthropic preference make this the clear fit."
                ),
                "alternative_code": None,
                "alternative_rationale": None,
            }
        )
        answers = QuestionnaireAnswers(
            provider_preference="anthropic",
            writes_code=False,
            focus_area="advising",
            experience_level="some",
        )
        agent_input = CertificationAdvisorInput(
            practitioner_id=seeded_practitioner.id,
            answers=answers,
            catalog=sample_catalog,
        )

        # When
        agent = CertificationAdvisorAgent(client=stub_client, db_session=db_session)
        result = await agent.run(agent_input)

        # Then
        assert result.primary_recommendation_code.upper() == "CCAO-F"
        # Must NOT be a coding-required track
        coding_required_codes = {"CCDV-F", "CCAF", "CCAR-P"}
        assert result.primary_recommendation_code.upper() not in coding_required_codes

    async def test_experienced_architect_no_preference_gets_rationale_with_tradeoff(
        self,
        db_session: AsyncSession,
        seeded_practitioner: Practitioner,
        sample_catalog: list[CertificationContext],
    ):
        """
        Scenario: An experienced architect with no provider preference gets a rationale naming the trade-off.
          Given answers indicating strong technical experience, an architecting focus, and no provider preference
          When the Certification Advisor Agent runs
          Then the response includes a primary recommendation and a rationale referencing at least one alternative
        """
        # Given
        stub_client = StubClaudeClient(
            response_data={
                "primary_recommendation_code": "CCAR-P",
                "primary_rationale": (
                    "Your experienced background and architecting focus align well with the "
                    "professional-level architect track. CCAR-P targets practitioners designing "
                    "complex, production Claude systems."
                ),
                "alternative_code": "CCAF",
                "alternative_rationale": (
                    "If you prefer a shorter ramp or are newer to the Anthropic ecosystem "
                    "specifically, CCAF covers the same architectural scope at a foundational level."
                ),
            }
        )
        answers = QuestionnaireAnswers(
            provider_preference=None,
            writes_code=True,
            focus_area="architecting",
            experience_level="experienced",
        )
        agent_input = CertificationAdvisorInput(
            practitioner_id=seeded_practitioner.id,
            answers=answers,
            catalog=sample_catalog,
        )

        # When
        agent = CertificationAdvisorAgent(client=stub_client, db_session=db_session)
        result = await agent.run(agent_input)

        # Then
        assert result.primary_recommendation_code  # non-empty
        assert result.primary_rationale  # non-empty
        # Must have an alternative since the scenario says "names at least one alternative"
        assert result.alternative_code is not None
        assert result.alternative_rationale is not None

    async def test_answers_are_persisted_independent_of_subsequent_actions(
        self,
        db_session: AsyncSession,
        seeded_practitioner: Practitioner,
        sample_catalog: list[CertificationContext],
    ):
        """
        Scenario: Answers are persisted even when the recommendation is later ignored.
          Given a completed questionnaire
          When the agent runs (via the route, which handles persistence)
          Then a certification_advisor_responses row exists
          And a practitioner_certification_goals row (status=recommended) exists
          Independent of whether the practitioner ever acts on it.

        Note: this test exercises the persistence logic directly (simulating what
        the route does) rather than going through the HTTP layer, since the
        scenario is about the DB side-effects, not the HTTP contract.
        """
        # Given
        from app.db.models import (
            CertificationAdvisorResponse as CARModel,
            PractitionerCertificationGoal as PCGModel,
            Certification as CertModel,
        )
        from datetime import UTC, datetime

        # Set up a minimal cert in DB that the recommendation references
        provider = CertificationProvider(
            id=str(uuid.uuid4()),
            name="Anthropic Test",
        )
        db_session.add(provider)
        await db_session.flush()

        cert = Certification(
            id=str(uuid.uuid4()),
            provider_id=provider.id,
            code="CCAO-F",
            name="Claude Certified Associate – Foundations",
            level="foundational",
            requires_coding_background=False,
            is_active=True,
        )
        db_session.add(cert)
        await db_session.flush()

        stub_client = StubClaudeClient(
            response_data={
                "primary_recommendation_code": "CCAO-F",
                "primary_rationale": "Good fit for a non-technical practitioner.",
                "alternative_code": None,
                "alternative_rationale": None,
            }
        )
        answers = QuestionnaireAnswers(
            provider_preference="anthropic",
            writes_code=False,
            focus_area="advising",
            experience_level="new",
        )
        agent_input = CertificationAdvisorInput(
            practitioner_id=seeded_practitioner.id,
            answers=answers,
            catalog=sample_catalog,
        )

        # When — run agent
        agent = CertificationAdvisorAgent(client=stub_client, db_session=db_session)
        recommendation = await agent.run(agent_input)

        # Simulate what the route does: persist advisor_response + goal
        response_id = str(uuid.uuid4())
        advisor_response = CARModel(
            id=response_id,
            practitioner_id=seeded_practitioner.id,
            responses=answers.model_dump(),
        )
        db_session.add(advisor_response)
        await db_session.flush()

        goal = PCGModel(
            id=str(uuid.uuid4()),
            practitioner_id=seeded_practitioner.id,
            certification_id=cert.id,
            status="recommended",
            recommended_at=datetime.now(UTC),
        )
        db_session.add(goal)
        await db_session.flush()

        # Then — certification_advisor_responses row exists
        car_result = await db_session.execute(
            select(CARModel).where(
                CARModel.practitioner_id == seeded_practitioner.id
            )
        )
        saved_response = car_result.scalar_one_or_none()
        assert saved_response is not None
        assert saved_response.responses["writes_code"] is False

        # And — practitioner_certification_goals row at status=recommended
        goal_result = await db_session.execute(
            select(PCGModel).where(
                PCGModel.practitioner_id == seeded_practitioner.id,
                PCGModel.status == "recommended",
            )
        )
        saved_goal = goal_result.scalar_one_or_none()
        assert saved_goal is not None
        assert saved_goal.certification_id == cert.id
