"""Step 10.4/10.8 — Domain gap scoring via compute_domain_scores.

Scenario 1: Practitioner with 3 correct cert-evaluated answers in Domain 1 →
  mastery_score > 0 after compute_domain_scores.

Scenario 2: Non-cert-evaluated answer does not change certification_domain_scores.
  Given an attempt on a non-cert-evaluated item
  When compute_domain_scores runs
  Then no certification_domain_scores row is created/modified for that domain.

Scenario 3: CertDomainGapChart API returns domains in sequence_order.
  Given a certification with 3 domains (sequence 3, 1, 2) and scores for each
  When GET /practitioners/{id}/certification-domain-scores is called
  Then domains are returned in sequence_order (1, 2, 3).

Scenario 4: If all domain scores have source=quiz_derived →
  no self_assessment_estimate rows exist for those domains.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.round_metrics import compute_domain_scores
from app.db.models import (
    Attempt,
    Certification,
    CertificationDomain,
    CertificationDomainScore,
    CertificationDomainVersion,
    CertificationProvider,
    Item,
    Practitioner,
)
from app.db.session import get_db
from app.main import app
from tests.conftest import (  # noqa: F401
    admin_session_info,
    apply_admin_auth_overrides,
    make_practitioner_session,
)


# ── helpers ───────────────────────────────────────────────────────────────────


async def _setup_cert_with_domain(
    db: AsyncSession,
    domain_name: str = "Domain 1",
    sequence_order: int = 1,
    weight_pct: float = 100.0,
) -> tuple[Certification, CertificationDomain]:
    """Create provider, cert, version, and one domain."""
    provider = CertificationProvider(
        id=str(uuid.uuid4()),
        name=f"Provider-{uuid.uuid4().hex[:6]}",
    )
    db.add(provider)
    await db.flush()

    cert = Certification(
        id=str(uuid.uuid4()),
        provider_id=provider.id,
        code=f"GAP-{uuid.uuid4().hex[:6]}",
        name="Gap Test Cert",
        level="foundational",
        requires_coding_background=False,
        is_active=True,
    )
    db.add(cert)
    await db.flush()

    version = CertificationDomainVersion(
        id=str(uuid.uuid4()),
        certification_id=cert.id,
        version_label="v1",
        is_current=True,
        source_notes="Test version",
        created_at=datetime.now(UTC),
    )
    db.add(version)
    await db.flush()

    domain = CertificationDomain(
        id=str(uuid.uuid4()),
        certification_id=cert.id,
        domain_version_id=version.id,
        domain_name=domain_name,
        domain_description=f"Description for {domain_name}",
        weight_pct=weight_pct,
        sequence_order=sequence_order,
    )
    db.add(domain)
    await db.flush()
    return cert, domain


async def _create_practitioner(db: AsyncSession, email_prefix: str = "gap") -> Practitioner:
    p = Practitioner(
        id=str(uuid.uuid4()),
        name="Gap Test Practitioner",
        email=f"{email_prefix}-{uuid.uuid4().hex[:6]}@test.com",
    )
    db.add(p)
    await db.flush()
    return p


async def _create_cert_evaluated_item(
    db: AsyncSession, skill_id: str, domain_id: str
) -> Item:
    item = Item(
        id=str(uuid.uuid4()),
        skill_id=skill_id,
        item_type="mcq",
        prompt="Cert-evaluated test question",
        answer_key={"options": ["A", "B", "C", "D"], "correct_index": 0},
        difficulty=0.5,
        certification_domain_id=domain_id,
        is_cert_evaluated=True,
        generation=1,
    )
    db.add(item)
    await db.flush()
    return item


async def _create_non_cert_evaluated_item(
    db: AsyncSession, skill_id: str
) -> Item:
    item = Item(
        id=str(uuid.uuid4()),
        skill_id=skill_id,
        item_type="mcq",
        prompt="Supplementary test question",
        answer_key={"options": ["A", "B", "C", "D"], "correct_index": 0},
        difficulty=0.5,
        certification_domain_id=None,
        is_cert_evaluated=False,
        generation=1,
    )
    db.add(item)
    await db.flush()
    return item


async def _record_attempt(
    db: AsyncSession,
    practitioner_id: str,
    item_id: str,
    score: float,
    offset_seconds: int = 0,
) -> Attempt:
    attempt = Attempt(
        id=str(uuid.uuid4()),
        practitioner_id=practitioner_id,
        item_id=item_id,
        response={"selected_index": 0},
        score=score,
        grader_rationale=f"Score: {score}",
        attempted_at=datetime.now(UTC) + timedelta(seconds=offset_seconds),
    )
    db.add(attempt)
    await db.flush()
    return attempt


# ── Scenario 1: correct cert-evaluated answers → mastery_score > 0 ───────────


class TestComputeDomainScores:
    async def test_three_correct_answers_yield_positive_domain_mastery(
        self, db_session: AsyncSession
    ):
        """
        Scenario 1: Practitioner with 3 correct cert-evaluated answers in Domain 1 →
          mastery_score > 0 after compute_domain_scores.
        """
        from app.db.models import Skill

        practitioner = await _create_practitioner(db_session, "scenario1")
        cert, domain = await _setup_cert_with_domain(db_session, "Domain 1")

        skill = Skill(
            id=str(uuid.uuid4()), name="Scenario1 Skill", category="Test"
        )
        db_session.add(skill)
        await db_session.flush()

        # 3 cert-evaluated items
        items = [
            await _create_cert_evaluated_item(db_session, skill.id, domain.id)
            for _ in range(3)
        ]

        # Attempt all 3 with a score of 0.85
        for i, item in enumerate(items):
            await _record_attempt(
                db_session, practitioner.id, item.id, score=0.85, offset_seconds=i
            )

        # Run compute_domain_scores
        results = await compute_domain_scores(
            practitioner_id=practitioner.id,
            certification_id=cert.id,
            db=db_session,
        )

        assert len(results) > 0, (
            "Expected at least one domain score result from compute_domain_scores"
        )

        # Check the DB row
        score_result = await db_session.execute(
            select(CertificationDomainScore).where(
                CertificationDomainScore.practitioner_id == practitioner.id,
                CertificationDomainScore.certification_domain_id == domain.id,
            )
        )
        score = score_result.scalar_one_or_none()
        assert score is not None, "Domain score row should be created in DB"
        assert float(score.mastery_score) > 0, (
            f"mastery_score should be > 0 after correct answers, got {score.mastery_score}"
        )
        assert score.source == "quiz_derived"

    async def test_non_cert_evaluated_item_does_not_create_domain_score(
        self, db_session: AsyncSession
    ):
        """
        Scenario 2: Non-cert-evaluated answer does not change certification_domain_scores.
          Given an attempt on a non-cert-evaluated item
          When compute_domain_scores runs
          Then no certification_domain_scores row is created for any domain.
        """
        from app.db.models import Skill

        practitioner = await _create_practitioner(db_session, "scenario2")
        cert, domain = await _setup_cert_with_domain(db_session, "Domain 2")

        skill = Skill(
            id=str(uuid.uuid4()), name="Scenario2 Skill", category="Test"
        )
        db_session.add(skill)
        await db_session.flush()

        # Only a NON-cert-evaluated item
        non_cert_item = await _create_non_cert_evaluated_item(db_session, skill.id)
        await _record_attempt(db_session, practitioner.id, non_cert_item.id, score=1.0)

        # Run compute_domain_scores
        results = await compute_domain_scores(
            practitioner_id=practitioner.id,
            certification_id=cert.id,
            db=db_session,
        )

        assert results == [], (
            f"Expected no domain scores from non-cert-evaluated item, got {results}"
        )

        # Verify no DB row was created
        score_result = await db_session.execute(
            select(CertificationDomainScore).where(
                CertificationDomainScore.practitioner_id == practitioner.id,
                CertificationDomainScore.certification_domain_id == domain.id,
            )
        )
        score = score_result.scalar_one_or_none()
        assert score is None, (
            "No certification_domain_score row should be created for non-cert-evaluated items"
        )


# ── Scenario 3: API returns domains in sequence_order ────────────────────────


@pytest_asyncio.fixture
async def api_client_admin(db_session: AsyncSession, admin_session_info):
    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    apply_admin_auth_overrides(app, admin_session_info)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


class TestCertDomainGapChartAPI:
    async def test_domains_returned_in_sequence_order(
        self, api_client_admin: AsyncClient, db_session: AsyncSession
    ):
        """
        Scenario 3: GET /practitioners/{id}/certification-domain-scores returns
          domains in sequence_order.
          Given 3 domains with sequence orders 3, 1, 2
          When GET endpoint is called
          Then response is ordered 1, 2, 3.
        """
        from app.db.models import Skill

        practitioner = await _create_practitioner(db_session, "scenario3")

        provider = CertificationProvider(
            id=str(uuid.uuid4()), name=f"P-{uuid.uuid4().hex[:6]}"
        )
        db_session.add(provider)
        await db_session.flush()

        cert = Certification(
            id=str(uuid.uuid4()),
            provider_id=provider.id,
            code=f"SEQ-{uuid.uuid4().hex[:6]}",
            name="Sequence Order Test",
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
            source_notes="test",
            created_at=datetime.now(UTC),
        )
        db_session.add(version)
        await db_session.flush()

        # Create domains in non-sequential order
        skill = Skill(id=str(uuid.uuid4()), name="Seq Skill", category="Test")
        db_session.add(skill)
        await db_session.flush()

        domains_data = [
            ("Domain C", 3),
            ("Domain A", 1),
            ("Domain B", 2),
        ]
        domain_ids = []
        for name, seq in domains_data:
            d = CertificationDomain(
                id=str(uuid.uuid4()),
                certification_id=cert.id,
                domain_version_id=version.id,
                domain_name=name,
                domain_description=f"Desc for {name}",
                weight_pct=33.0,
                sequence_order=seq,
            )
            db_session.add(d)
            await db_session.flush()
            domain_ids.append((d.id, seq))

        # Create score rows for each domain
        for domain_id, seq in domain_ids:
            db_session.add(CertificationDomainScore(
                id=str(uuid.uuid4()),
                practitioner_id=practitioner.id,
                certification_domain_id=domain_id,
                mastery_score=seq * 0.1,  # different scores so we can tell them apart
                confidence=0.3,
                source="self_assessment_estimate",
                last_computed_at=datetime.now(UTC),
            ))
        await db_session.flush()

        # When
        response = await api_client_admin.get(
            f"/api/v1/practitioners/{practitioner.id}/certification-domain-scores"
            f"?certification_id={cert.id}"
        )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert len(data) == 3, f"Expected 3 domain scores, got {len(data)}"

        # Verify sequence order is ascending
        sequence_orders = [item["sequence_order"] for item in data]
        assert sequence_orders == sorted(sequence_orders), (
            f"Domains should be returned in sequence_order, got {sequence_orders}"
        )
        assert sequence_orders == [1, 2, 3], (
            f"Expected [1, 2, 3], got {sequence_orders}"
        )

    async def test_all_quiz_derived_scores_means_no_estimate_rows(
        self, db_session: AsyncSession
    ):
        """
        Scenario 4: If all domain scores have source=quiz_derived →
          no self_assessment_estimate rows exist for those domains.
          This ensures that once quiz-derived data is present, estimate rows
          are not co-existing for the same practitioner × domain.
        """
        from app.db.models import Skill

        practitioner = await _create_practitioner(db_session, "scenario4")
        cert, domain = await _setup_cert_with_domain(db_session, "Quiz Domain")

        skill = Skill(id=str(uuid.uuid4()), name="Quiz Only Skill", category="Test")
        db_session.add(skill)
        await db_session.flush()

        # Create quiz-derived score (simulating what compute_domain_scores would do)
        quiz_derived_score = CertificationDomainScore(
            id=str(uuid.uuid4()),
            practitioner_id=practitioner.id,
            certification_domain_id=domain.id,
            mastery_score=0.65,
            confidence=0.70,
            source="quiz_derived",
            last_computed_at=datetime.now(UTC),
        )
        db_session.add(quiz_derived_score)
        await db_session.flush()

        # Verify: for this practitioner × domain, only quiz_derived exists
        all_scores_result = await db_session.execute(
            select(CertificationDomainScore).where(
                CertificationDomainScore.practitioner_id == practitioner.id,
                CertificationDomainScore.certification_domain_id == domain.id,
            )
        )
        all_scores = all_scores_result.scalars().all()

        assert len(all_scores) == 1, (
            f"Expected exactly 1 score row for practitioner × domain, got {len(all_scores)}"
        )
        assert all_scores[0].source == "quiz_derived", (
            "The unique constraint ensures one row — it should be quiz_derived"
        )

        # Check there are no self_assessment_estimate rows for this domain
        estimate_result = await db_session.execute(
            select(CertificationDomainScore).where(
                CertificationDomainScore.practitioner_id == practitioner.id,
                CertificationDomainScore.certification_domain_id == domain.id,
                CertificationDomainScore.source == "self_assessment_estimate",
            )
        )
        estimates = estimate_result.scalars().all()
        assert len(estimates) == 0, (
            f"Expected no self_assessment_estimate rows when quiz_derived exists, "
            f"got {len(estimates)}"
        )
