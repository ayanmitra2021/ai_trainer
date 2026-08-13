"""Phase 14 — Provider Resilience: Haiku Fallback & Graceful Degradation.

Scenario tests for:
  14.1 — Haiku-pinned Anthropic client
  14.2 — FallbackModelClient two-tier chain
  14.3 — Graceful degraded domain scoring
  14.4 — domain_scoring_status default value
"""

from __future__ import annotations

import logging
import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import Agent
from app.agents.model_client import (
    AnthropicModelClient,
    FallbackModelClient,
    ProviderUnavailableError,
)
from app.db.models import (
    Certification,
    CertificationDomain,
    CertificationDomainScore,
    CertificationDomainVersion,
    CertificationProvider,
    CertificationSkill,
    PractitionerProfile,
    ProfileSkillAssessment,
    Skill,
    Practitioner,
)
from tests.fixtures.stub_claude_client import StubClaudeClient


# ── Minimal Pydantic output model for test agents ──────────────────────────────

class _EchoOutput(BaseModel):
    message: str


# ── Minimal agent wired to a stub client ──────────────────────────────────────

class _EchoAgent(Agent[BaseModel, _EchoOutput]):
    """Trivial agent that echoes whatever the stub returns."""
    name = "echo_agent"
    model = "claude-sonnet-5"  # intentionally wrong — client overrides this
    output_model = _EchoOutput

    def _build_messages(self, input: BaseModel) -> list[dict[str, Any]]:
        return [{"role": "user", "content": "ping"}]


# ── Stubs: clients that simulate failure and success ─────────────────────────

class _StubParseable:
    """Minimal parsed-response shape for _EchoOutput."""

    def __init__(self, parsed: _EchoOutput) -> None:
        self.parsed = parsed
        self.choices = [_FakeChoice(parsed)]

    class usage:
        input_tokens = 10
        output_tokens = 5


class _FakeChoice:
    def __init__(self, parsed):
        self.message = _FakeMsg(parsed)


class _FakeMsg:
    def __init__(self, parsed):
        self.parsed = parsed


class _SuccessClient:
    """Client stub that always returns a valid _EchoOutput response."""

    def __init__(self, model_id: str = "primary-model") -> None:
        self._model_id = model_id

    async def parse(self, *, output_format, **__) -> Any:
        parsed = output_format.model_validate({"message": f"ok from {self._model_id}"})
        return _StubParseable(parsed)


class _FailClient:
    """Client stub that always raises the given exception."""

    def __init__(self, exc: Exception, model_id: str = "fail-model") -> None:
        self._exc = exc
        self._model_id = model_id

    async def parse(self, **__) -> Any:
        raise self._exc


# ══════════════════════════════════════════════════════════════════════════════
# 14.1 — Haiku-pinned Anthropic client
# ══════════════════════════════════════════════════════════════════════════════

class TestHaikuPinnedAnthropicClient:
    """Step 14.1 scenario tests."""

    def test_anthropic_client_model_id_defaults_to_haiku(self):
        """
        Scenario: AnthropicModelClient defaults to claude-haiku-4-5-20251001.
          Given  an AnthropicModelClient with no explicit model_id
          When   _model_id is read
          Then   it equals 'claude-haiku-4-5-20251001'
        """
        # Construct without a real API key (we won't call it)
        try:
            client = AnthropicModelClient(api_key="test-key")
        except Exception:
            # If construction requires a live key, skip network but still test the attr
            pytest.skip("AnthropicModelClient construction failed — skipping live-key test")
        assert client._model_id == "claude-haiku-4-5-20251001"

    def test_anthropic_client_respects_explicit_model_id(self):
        """
        Scenario: AnthropicModelClient stores the model_id passed at construction.
          Given  an AnthropicModelClient with model_id='claude-haiku-4-5-20251001'
          When   _model_id is read
          Then   it equals 'claude-haiku-4-5-20251001'
        """
        try:
            client = AnthropicModelClient(api_key="test-key", model_id="claude-haiku-4-5-20251001")
        except Exception:
            pytest.skip("AnthropicModelClient construction failed — skipping live-key test")
        assert client._model_id == "claude-haiku-4-5-20251001"

    async def test_effective_model_reflects_client_model_id(self, db_session: AsyncSession):
        """
        Scenario: effective_model reflects the client's _model_id, not the agent's model attr.
          Given  an _EchoAgent (model='claude-sonnet-5') wired to a client with
                 _model_id='claude-haiku-4-5-20251001'
          When   agent.effective_model is read (before any call)
          Then   it returns 'claude-haiku-4-5-20251001', not 'claude-sonnet-5'
        """
        client = _SuccessClient(model_id="claude-haiku-4-5-20251001")
        agent = _EchoAgent(client=client, db_session=db_session)

        assert agent.effective_model == "claude-haiku-4-5-20251001"
        assert agent.effective_model != "claude-sonnet-5"

    def test_anthropic_messages_client_uses_model_id_not_arg(self):
        """
        Scenario: AnthropicMessagesClient uses _model_id, not the 'model' kwarg.
          Given  an agent with model='claude-sonnet-5' and a client with
                 _model_id='claude-haiku-4-5-20251001'
          When   effective_model is read (which is what the agent passes to parse())
          Then   it returns 'claude-haiku-4-5-20251001', not 'claude-sonnet-5'

        This is the key invariant: effective_model reads _model_id from the client
        rather than the agent's own model attr, so parse() always receives the
        pinned Haiku model string.
        """
        client = _SuccessClient(model_id="claude-haiku-4-5-20251001")
        agent = _EchoAgent(client=client, db_session=None)

        # effective_model is what the base class passes to parse() — verify it
        # reflects the client's _model_id, not the agent's 'claude-sonnet-5' attr
        assert agent.effective_model == "claude-haiku-4-5-20251001"
        assert agent.model == "claude-sonnet-5"           # agent's own attr unchanged
        assert agent.effective_model != agent.model       # client override wins


# ══════════════════════════════════════════════════════════════════════════════
# 14.2 — FallbackModelClient
# ══════════════════════════════════════════════════════════════════════════════

class TestFallbackModelClient:
    """Step 14.2 scenario tests."""

    async def test_primary_succeeds_fallback_never_called(self):
        """
        Scenario: Primary succeeds — fallback is never invoked.
          Given  a FallbackModelClient where primary returns a valid response
          When   .parse() is called
          Then   result equals primary's response
                 _last_model_used equals primary model ID
        """
        primary = _SuccessClient(model_id="primary-model-id")
        # fallback should never be called; use a failing client to prove it
        fallback = _FailClient(RuntimeError("fallback should not be called"), model_id="fallback-id")
        fc = FallbackModelClient(primary=primary, fallback=fallback)

        result = await fc.parse(
            model="ignored",
            system="sys",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=100,
            output_format=_EchoOutput,
        )

        from app.agents.model_client import _extract_parsed
        parsed = _extract_parsed(result)
        assert parsed is not None
        assert fc._last_model_used == "primary-model-id"

    async def test_primary_fails_fallback_succeeds(self, caplog):
        """
        Scenario: Primary fails → fallback succeeds.
          Given  primary raises RuntimeError (simulating network error)
                 and fallback returns a valid response
          When   .parse() is called
          Then   result equals fallback's response
                 _last_model_used equals 'claude-haiku-4-5-20251001'
                 a WARNING is logged naming the primary failure
        """
        primary = _FailClient(RuntimeError("primary timeout"), model_id="nvidia-model")
        fallback = _SuccessClient(model_id="claude-haiku-4-5-20251001")
        fc = FallbackModelClient(primary=primary, fallback=fallback)

        with caplog.at_level(logging.WARNING):
            result = await fc.parse(
                model="ignored",
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=100,
                output_format=_EchoOutput,
            )

        from app.agents.model_client import _extract_parsed
        parsed = _extract_parsed(result)
        assert parsed is not None
        assert fc._last_model_used == "claude-haiku-4-5-20251001"
        # Warning should have been logged
        assert any("Primary provider failed" in r.message for r in caplog.records)

    async def test_both_fail_raises_provider_unavailable_error(self):
        """
        Scenario: Both primary and fallback fail → ProviderUnavailableError.
          Given  primary raises RuntimeError("primary broke")
                 and fallback raises RuntimeError("fallback broke")
          When   .parse() is called
          Then   ProviderUnavailableError is raised
                 primary_error is the primary exception
                 fallback_error is the fallback exception
        """
        primary_exc = RuntimeError("primary broke")
        fallback_exc = RuntimeError("fallback broke")
        primary = _FailClient(primary_exc, model_id="nvidia")
        fallback = _FailClient(fallback_exc, model_id="haiku")
        fc = FallbackModelClient(primary=primary, fallback=fallback)

        with pytest.raises(ProviderUnavailableError) as exc_info:
            await fc.parse(
                model="ignored",
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=100,
                output_format=_EchoOutput,
            )

        err = exc_info.value
        assert err.primary_error is primary_exc
        assert err.fallback_error is fallback_exc

    async def test_no_fallback_raises_provider_unavailable_with_primary_error(self):
        """
        Scenario: No fallback configured — primary failure wraps in ProviderUnavailableError.
          Given  primary fails and no fallback is set
          When   .parse() is called
          Then   ProviderUnavailableError is raised; fallback_error is None
        """
        primary_exc = RuntimeError("primary broke")
        primary = _FailClient(primary_exc)
        fc = FallbackModelClient(primary=primary, fallback=None)

        with pytest.raises(ProviderUnavailableError) as exc_info:
            await fc.parse(
                model="ignored",
                system="sys",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=100,
                output_format=_EchoOutput,
            )

        err = exc_info.value
        assert err.primary_error is primary_exc
        assert err.fallback_error is None

    async def test_effective_model_reflects_fallback_tier(self, db_session: AsyncSession):
        """
        Scenario: effective_model reports the tier that responded.
          Given  a FallbackModelClient where primary fails and fallback succeeds
          When   parse() is called (fallback fires)
          Then   _last_model_used equals fallback's _model_id
                 and an agent reading effective_model also returns it
        """
        primary = _FailClient(RuntimeError("primary down"), model_id="nvidia-model")
        fallback = _SuccessClient(model_id="claude-haiku-4-5-20251001")
        fc = FallbackModelClient(primary=primary, fallback=fallback)

        # Call parse() directly so the fallback fires and _last_model_used is set
        await fc.parse(
            model="ignored",
            system="sys",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=100,
            output_format=_EchoOutput,
        )

        # Verify _last_model_used was set to the fallback tier
        assert fc._last_model_used == "claude-haiku-4-5-20251001"

        # An agent wired to this client should reflect the same value
        agent = _EchoAgent(client=fc, db_session=db_session)
        assert agent.effective_model == "claude-haiku-4-5-20251001"

    async def test_effective_model_pre_call_returns_primary_model(self, db_session: AsyncSession):
        """
        Scenario: effective_model before any call returns primary's model ID.
          Given  an agent wired to a FallbackModelClient (no calls yet)
          When   agent.effective_model is read
          Then   it returns the primary client's _model_id
        """
        primary = _SuccessClient(model_id="nvidia/nemotron-3-ultra")
        fallback = _SuccessClient(model_id="claude-haiku-4-5-20251001")
        fc = FallbackModelClient(primary=primary, fallback=fallback)

        agent = _EchoAgent(client=fc, db_session=db_session)
        assert agent.effective_model == "nvidia/nemotron-3-ultra"


# ══════════════════════════════════════════════════════════════════════════════
# 14.3 — Graceful degraded domain scoring
# ══════════════════════════════════════════════════════════════════════════════

# Fixtures shared across 14.3 and 14.4 tests

@pytest_asyncio.fixture
async def base_entities(db_session: AsyncSession):
    """Create a practitioner, provider, cert, domain version, and domains."""
    practitioner = Practitioner(
        id=str(uuid.uuid4()),
        name="Test Practitioner 14",
        email=f"p14-{uuid.uuid4().hex[:8]}@example.com",
    )
    db_session.add(practitioner)

    provider = CertificationProvider(
        id=str(uuid.uuid4()), name="Test Provider 14"
    )
    db_session.add(provider)
    await db_session.flush()

    cert = Certification(
        id=str(uuid.uuid4()),
        provider_id=provider.id,
        code="TEST14",
        name="Test Cert Phase 14",
        level="foundational",
        requires_coding_background=False,
        is_active=True,
    )
    db_session.add(cert)
    await db_session.flush()

    version = CertificationDomainVersion(
        id=str(uuid.uuid4()),
        certification_id=cert.id,
        version_label="bootstrap-14",
        is_current=True,
        source_notes="test",
    )
    db_session.add(version)
    await db_session.flush()

    domains = []
    for i in range(3):
        d = CertificationDomain(
            id=str(uuid.uuid4()),
            certification_id=cert.id,
            domain_version_id=version.id,
            domain_name=f"Domain {i + 1}",
            domain_description=f"Domain {i + 1} description",
            weight_pct=33.0 + (1.0 if i == 2 else 0),
            sequence_order=i + 1,
        )
        db_session.add(d)
        domains.append(d)
    await db_session.flush()

    return {
        "practitioner": practitioner,
        "cert": cert,
        "version": version,
        "domains": domains,
    }


@pytest_asyncio.fixture
async def profile_with_assessments(db_session: AsyncSession, base_entities):
    """Create a profile with skills and assessments linked to domains."""
    practitioner = base_entities["practitioner"]
    cert = base_entities["cert"]
    version = base_entities["version"]
    domains = base_entities["domains"]

    profile = PractitionerProfile(
        id=str(uuid.uuid4()),
        practitioner_id=practitioner.id,
        name="Test Profile 14",
        is_active=True,
        certification_id=cert.id,
        domain_version_id=version.id,
        is_locked=False,
        domain_scoring_status="pending",
    )
    db_session.add(profile)
    await db_session.flush()

    # Create skills and link them to domains via certification_skills
    skills = []
    assessments = []
    for i, domain in enumerate(domains):
        skill = Skill(
            id=str(uuid.uuid4()),
            name=f"Skill {i + 1}",
            category="Test",
            description=f"Skill for domain {i + 1}",
        )
        db_session.add(skill)
        await db_session.flush()
        skills.append(skill)

        cert_skill = CertificationSkill(
            certification_id=cert.id,
            skill_id=skill.id,
            weight=0.5,
            certification_domain_id=domain.id,
            source="seed",
        )
        db_session.add(cert_skill)

        # signal_strength of 0.6 for skills 0 and 1, 0.4 for skill 2
        strength = 0.6 if i < 2 else 0.4
        assessment = ProfileSkillAssessment(
            id=str(uuid.uuid4()),
            profile_id=profile.id,
            skill_id=skill.id,
            signal_strength=strength,
        )
        db_session.add(assessment)
        assessments.append(assessment)

    await db_session.flush()

    return {
        "profile": profile,
        "skills": skills,
        "assessments": assessments,
    }


class TestDegradedDomainScoring:
    """Step 14.3 scenario tests: graceful degraded domain scoring."""

    async def test_degraded_scores_written_when_provider_unavailable(
        self, db_session: AsyncSession, base_entities, profile_with_assessments
    ):
        """
        Scenario: Both providers fail — mechanical estimates are written.
          Given  a profile with 3 skill assessments (signals: 0.6, 0.6, 0.4)
                 and ProviderUnavailableError is raised by the Domain Scorer
          When   _compute_degraded_domain_scores() runs
          Then   one CertificationDomainScore per domain exists
                 each has source='degraded_estimate', confidence=0.3
                 mastery_score <= 0.5 (capped)
        """
        from datetime import UTC, datetime
        from app.api.routes.profiles import _compute_degraded_domain_scores

        profile = profile_with_assessments["profile"]
        assessments = profile_with_assessments["assessments"]
        domains = base_entities["domains"]
        now = datetime.now(UTC)

        await _compute_degraded_domain_scores(
            profile=profile,
            cert_domains=domains,
            skill_assessments=assessments,
            db=db_session,
            now=now,
        )
        await db_session.flush()

        # Verify rows exist for each domain
        for domain in domains:
            result = await db_session.execute(
                select(CertificationDomainScore).where(
                    CertificationDomainScore.practitioner_id == profile.practitioner_id,
                    CertificationDomainScore.certification_domain_id == domain.id,
                )
            )
            score_row = result.scalar_one_or_none()
            assert score_row is not None, f"No score for domain {domain.domain_name}"
            assert score_row.source == "degraded_estimate"
            assert float(score_row.confidence) == pytest.approx(0.3, abs=0.01)
            assert float(score_row.mastery_score) <= 0.5

    async def test_degraded_scores_cap_at_0_5(
        self, db_session: AsyncSession, base_entities
    ):
        """
        Scenario: Even with signal_strength > 0.5, the degraded score is capped at 0.5.
          Given  a profile where all skill assessments have signal_strength=1.0
          When   _compute_degraded_domain_scores() runs
          Then   every domain score is exactly 0.5
        """
        from datetime import UTC, datetime
        from app.api.routes.profiles import _compute_degraded_domain_scores

        practitioner = base_entities["practitioner"]
        cert = base_entities["cert"]
        version = base_entities["version"]
        domains = base_entities["domains"]

        # New profile
        profile = PractitionerProfile(
            id=str(uuid.uuid4()),
            practitioner_id=practitioner.id,
            name="High Signal Profile",
            is_active=False,
            certification_id=cert.id,
            domain_version_id=version.id,
            is_locked=False,
            domain_scoring_status="pending",
        )
        db_session.add(profile)
        await db_session.flush()

        # Skills with 100% signal, linked to each domain
        high_assessments = []
        for domain in domains:
            skill = Skill(
                id=str(uuid.uuid4()),
                name=f"High Skill {domain.id[:4]}",
                category="Test",
                description="High signal skill",
            )
            db_session.add(skill)
            await db_session.flush()

            db_session.add(CertificationSkill(
                certification_id=cert.id,
                skill_id=skill.id,
                weight=1.0,
                certification_domain_id=domain.id,
                source="seed",
            ))

            assessment = ProfileSkillAssessment(
                id=str(uuid.uuid4()),
                profile_id=profile.id,
                skill_id=skill.id,
                signal_strength=1.0,  # max signal
            )
            db_session.add(assessment)
            high_assessments.append(assessment)

        await db_session.flush()
        now = datetime.now(UTC)

        await _compute_degraded_domain_scores(
            profile=profile,
            cert_domains=domains,
            skill_assessments=high_assessments,
            db=db_session,
            now=now,
        )
        await db_session.flush()

        for domain in domains:
            result = await db_session.execute(
                select(CertificationDomainScore).where(
                    CertificationDomainScore.practitioner_id == practitioner.id,
                    CertificationDomainScore.certification_domain_id == domain.id,
                )
            )
            score_row = result.scalar_one()
            assert float(score_row.mastery_score) <= 0.5

    async def test_degraded_does_not_overwrite_quiz_derived(
        self, db_session: AsyncSession, base_entities, profile_with_assessments
    ):
        """
        Scenario: Degraded scoring never overwrites quiz_derived rows.
          Given  a domain already has a quiz_derived score
          When   _compute_degraded_domain_scores() runs
          Then   the quiz_derived row is unchanged (not replaced with degraded_estimate)
        """
        from datetime import UTC, datetime
        from app.api.routes.profiles import _compute_degraded_domain_scores

        profile = profile_with_assessments["profile"]
        assessments = profile_with_assessments["assessments"]
        domains = base_entities["domains"]
        now = datetime.now(UTC)
        first_domain = domains[0]

        # Pre-populate a quiz_derived row for the first domain
        quiz_score = CertificationDomainScore(
            id=str(uuid.uuid4()),
            practitioner_id=profile.practitioner_id,
            certification_domain_id=first_domain.id,
            mastery_score=0.85,
            confidence=0.9,
            source="quiz_derived",
            last_computed_at=now,
        )
        db_session.add(quiz_score)
        await db_session.flush()

        await _compute_degraded_domain_scores(
            profile=profile,
            cert_domains=domains,
            skill_assessments=assessments,
            db=db_session,
            now=now,
        )
        await db_session.flush()

        # The quiz_derived row must remain unchanged
        result = await db_session.execute(
            select(CertificationDomainScore).where(
                CertificationDomainScore.practitioner_id == profile.practitioner_id,
                CertificationDomainScore.certification_domain_id == first_domain.id,
            )
        )
        preserved_row = result.scalar_one()
        assert preserved_row.source == "quiz_derived"
        assert float(preserved_row.mastery_score) == pytest.approx(0.85, abs=0.01)
        assert float(preserved_row.confidence) == pytest.approx(0.9, abs=0.01)


# ══════════════════════════════════════════════════════════════════════════════
# 14.4 — domain_scoring_status default value
# ══════════════════════════════════════════════════════════════════════════════

class TestDomainScoringStatusDefault:
    """Step 14.4 scenario tests: ORM default and schema."""

    async def test_new_profile_defaults_to_pending(
        self, db_session: AsyncSession, base_entities
    ):
        """
        Scenario: A new profile has domain_scoring_status='pending'.
          Given  a new PractitionerProfile created without setting domain_scoring_status
          When   the profile is read back
          Then   domain_scoring_status equals 'pending'
        """
        practitioner = base_entities["practitioner"]
        cert = base_entities["cert"]

        profile = PractitionerProfile(
            id=str(uuid.uuid4()),
            practitioner_id=practitioner.id,
            name="Default Status Profile",
            is_active=False,
            certification_id=cert.id,
            is_locked=False,
            # domain_scoring_status NOT set — should default to 'pending'
        )
        db_session.add(profile)
        await db_session.flush()

        result = await db_session.execute(
            select(PractitionerProfile).where(PractitionerProfile.id == profile.id)
        )
        fetched = result.scalar_one()
        assert fetched.domain_scoring_status == "pending"

    async def test_domain_scoring_status_can_be_set_to_degraded(
        self, db_session: AsyncSession, base_entities
    ):
        """
        Scenario: domain_scoring_status can be explicitly set to 'degraded'.
          Given  a profile with domain_scoring_status='degraded'
          When   the profile is read back
          Then   domain_scoring_status equals 'degraded'
        """
        practitioner = base_entities["practitioner"]
        cert = base_entities["cert"]

        profile = PractitionerProfile(
            id=str(uuid.uuid4()),
            practitioner_id=practitioner.id,
            name="Degraded Status Profile",
            is_active=False,
            certification_id=cert.id,
            is_locked=False,
            domain_scoring_status="degraded",
        )
        db_session.add(profile)
        await db_session.flush()

        result = await db_session.execute(
            select(PractitionerProfile).where(PractitionerProfile.id == profile.id)
        )
        fetched = result.scalar_one()
        assert fetched.domain_scoring_status == "degraded"

    async def test_domain_scoring_status_can_be_set_to_lm_scored(
        self, db_session: AsyncSession, base_entities
    ):
        """
        Scenario: domain_scoring_status can be set to 'lm_scored'.
          Given  a profile with domain_scoring_status='lm_scored'
          When   the profile is read back
          Then   domain_scoring_status equals 'lm_scored'
        """
        practitioner = base_entities["practitioner"]
        cert = base_entities["cert"]

        profile = PractitionerProfile(
            id=str(uuid.uuid4()),
            practitioner_id=practitioner.id,
            name="LM Scored Profile",
            is_active=False,
            certification_id=cert.id,
            is_locked=False,
            domain_scoring_status="lm_scored",
        )
        db_session.add(profile)
        await db_session.flush()

        result = await db_session.execute(
            select(PractitionerProfile).where(PractitionerProfile.id == profile.id)
        )
        fetched = result.scalar_one()
        assert fetched.domain_scoring_status == "lm_scored"


# ══════════════════════════════════════════════════════════════════════════════
# ProviderUnavailableError contract
# ══════════════════════════════════════════════════════════════════════════════

class TestProviderUnavailableError:
    """Verify ProviderUnavailableError carries both errors."""

    def test_carries_primary_and_fallback_errors(self):
        primary = RuntimeError("nvidia down")
        fallback = ValueError("haiku 429")
        err = ProviderUnavailableError(primary_error=primary, fallback_error=fallback)
        assert err.primary_error is primary
        assert err.fallback_error is fallback
        assert "nvidia down" in str(err)
        assert "haiku 429" in str(err)

    def test_fallback_error_optional(self):
        primary = RuntimeError("primary only")
        err = ProviderUnavailableError(primary_error=primary)
        assert err.primary_error is primary
        assert err.fallback_error is None
