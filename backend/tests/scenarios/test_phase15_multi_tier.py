"""Phase 15 — Multi-Tier Provider Resilience.

Scenario tests for:
  15.1 — AllProvidersUnavailableError carries full error list
  15.2 — MultiTierModelClient three-tier chain (success and failure paths)
  15.3 — NvidiaCircuitBreaker state machine
  15.4 — Circuit breaker integrates with MultiTierModelClient (trips/skips/resets)
  15.5 — ANTHROPIC mode reversed chain (Haiku → Ultra → Lightning, no breaker)
  15.6 — create_model_client() factory creates MultiTierModelClient (config paths)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import BaseModel

from app.agents.model_client import (
    AllProvidersUnavailableError,
    FallbackModelClient,
    MultiTierModelClient,
    NvidiaCircuitBreaker,
    ProviderUnavailableError,
)


# ── Shared stubs ──────────────────────────────────────────────────────────────

class _EchoOutput(BaseModel):
    message: str


class _StubParseable:
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
    """Stub that always returns a valid _EchoOutput response."""

    def __init__(self, model_id: str = "ok-model") -> None:
        self._model_id = model_id
        self.call_count = 0

    async def parse(self, *, output_format, **__) -> Any:
        self.call_count += 1
        parsed = output_format.model_validate({"message": f"ok from {self._model_id}"})
        return _StubParseable(parsed)


class _FailClient:
    """Stub that always raises the given exception."""

    def __init__(self, exc: Exception, model_id: str = "fail-model") -> None:
        self._exc = exc
        self._model_id = model_id
        self.call_count = 0

    async def parse(self, **__) -> Any:
        self.call_count += 1
        raise self._exc


# ── Helper ────────────────────────────────────────────────────────────────────

_PARSE_KWARGS = dict(
    model="ignored",
    system="sys",
    messages=[{"role": "user", "content": "ping"}],
    max_tokens=100,
    output_format=_EchoOutput,
)


# ══════════════════════════════════════════════════════════════════════════════
# 15.1 — AllProvidersUnavailableError
# ══════════════════════════════════════════════════════════════════════════════

class TestAllProvidersUnavailableError:
    """Step 15.1 scenario tests."""

    def test_carries_list_of_errors(self):
        """
        Scenario: AllProvidersUnavailableError stores every tier's exception.
          Given  three exceptions (one per tier)
          When   AllProvidersUnavailableError is constructed
          Then   .errors contains all three, in order
                 str(exc) includes their repr
        """
        e1 = RuntimeError("tier1 failed")
        e2 = TimeoutError("tier2 timed out")
        e3 = ConnectionError("tier3 connection refused")
        err = AllProvidersUnavailableError([e1, e2, e3])

        assert err.errors == [e1, e2, e3]
        assert "tier1 failed" in str(err)
        assert "tier2 timed out" in str(err)
        assert "tier3 connection refused" in str(err)

    def test_single_error(self):
        """
        Scenario: A single-tier failure wraps cleanly.
          Given  one exception
          When   AllProvidersUnavailableError is constructed
          Then   .errors has length 1
        """
        e = ValueError("only tier failed")
        err = AllProvidersUnavailableError([e])
        assert len(err.errors) == 1
        assert err.errors[0] is e

    def test_is_runtime_error(self):
        """AllProvidersUnavailableError is a RuntimeError subclass."""
        err = AllProvidersUnavailableError([RuntimeError("x")])
        assert isinstance(err, RuntimeError)

    def test_provider_unavailable_error_unchanged(self):
        """
        Scenario: ProviderUnavailableError (Phase 14) still works independently.
          Given  primary_error and fallback_error
          When   ProviderUnavailableError is constructed
          Then   both attributes are set, str includes their repr
        """
        primary = RuntimeError("nvidia down")
        fallback = ValueError("haiku 429")
        err = ProviderUnavailableError(primary_error=primary, fallback_error=fallback)
        assert err.primary_error is primary
        assert err.fallback_error is fallback
        assert "nvidia down" in str(err)
        assert "haiku 429" in str(err)


# ══════════════════════════════════════════════════════════════════════════════
# 15.2 — MultiTierModelClient chain
# ══════════════════════════════════════════════════════════════════════════════

class TestMultiTierModelClient:
    """Step 15.2 scenario tests: three-tier chain behaviour."""

    async def test_tier1_success_never_calls_lower_tiers(self):
        """
        Scenario: Tier-1 succeeds — tiers 2 and 3 are never invoked.
          Given  Tier-1 succeeds; Tiers 2 & 3 would fail if called
          When   .parse() is called
          Then   result comes from Tier-1 (_last_model_used = 'ultra')
                 Tiers 2 & 3 call_count == 0
        """
        t1 = _SuccessClient("ultra")
        t2 = _FailClient(RuntimeError("should not be called"), "lightning")
        t3 = _FailClient(RuntimeError("should not be called"), "haiku")

        client = MultiTierModelClient(
            tiers=[(t1, 5.0), (t2, 5.0), (t3, 5.0)],
        )
        await client.parse(**_PARSE_KWARGS)

        assert client._last_model_used == "ultra"
        assert t1.call_count == 1
        assert t2.call_count == 0
        assert t3.call_count == 0

    async def test_tier1_fails_tier2_succeeds(self, caplog):
        """
        Scenario: Tier-1 fails → Tier-2 answers.
          Given  Tier-1 raises RuntimeError; Tier-2 succeeds
          When   .parse() is called
          Then   result comes from Tier-2
                 _last_model_used == 'lightning'
                 WARNING logged naming Tier-1 failure
                 Tier-3 never called
        """
        t1 = _FailClient(RuntimeError("ultra timeout"), "ultra")
        t2 = _SuccessClient("lightning")
        t3 = _FailClient(RuntimeError("should not be called"), "haiku")

        client = MultiTierModelClient(
            tiers=[(t1, 5.0), (t2, 5.0), (t3, 5.0)],
        )
        with caplog.at_level(logging.WARNING):
            await client.parse(**_PARSE_KWARGS)

        assert client._last_model_used == "lightning"
        assert t1.call_count == 1
        assert t2.call_count == 1
        assert t3.call_count == 0
        assert any("ultra" in r.message for r in caplog.records)

    async def test_tiers_1_and_2_fail_tier3_succeeds(self, caplog):
        """
        Scenario: Tiers 1 & 2 fail → Tier-3 (Haiku) answers.
          Given  Tiers 1 & 2 raise errors; Tier-3 succeeds
          When   .parse() is called
          Then   _last_model_used == 'haiku'
                 two WARNING log lines (one per failed tier)
        """
        t1 = _FailClient(RuntimeError("ultra down"), "ultra")
        t2 = _FailClient(RuntimeError("lightning down"), "lightning")
        t3 = _SuccessClient("haiku")

        client = MultiTierModelClient(
            tiers=[(t1, 5.0), (t2, 5.0), (t3, 5.0)],
        )
        with caplog.at_level(logging.WARNING):
            await client.parse(**_PARSE_KWARGS)

        assert client._last_model_used == "haiku"
        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warnings) >= 2

    async def test_all_tiers_fail_raises_all_providers_unavailable(self):
        """
        Scenario: Every tier fails → AllProvidersUnavailableError.
          Given  all three tiers raise distinct exceptions
          When   .parse() is called
          Then   AllProvidersUnavailableError is raised
                 .errors contains all three exceptions in order
        """
        e1 = RuntimeError("ultra failed")
        e2 = RuntimeError("lightning failed")
        e3 = RuntimeError("haiku failed")

        t1 = _FailClient(e1, "ultra")
        t2 = _FailClient(e2, "lightning")
        t3 = _FailClient(e3, "haiku")

        client = MultiTierModelClient(
            tiers=[(t1, 5.0), (t2, 5.0), (t3, 5.0)],
        )
        with pytest.raises(AllProvidersUnavailableError) as exc_info:
            await client.parse(**_PARSE_KWARGS)

        err = exc_info.value
        assert len(err.errors) == 3
        assert err.errors[0] is e1
        assert err.errors[1] is e2
        assert err.errors[2] is e3

    async def test_last_model_used_none_before_call(self):
        """
        Scenario: _last_model_used is None before first call.
          Given  a freshly constructed MultiTierModelClient
          When   _last_model_used is read before .parse()
          Then   it is None
        """
        t1 = _SuccessClient("ultra")
        client = MultiTierModelClient(tiers=[(t1, 5.0)])
        assert client._last_model_used is None

    async def test_primary_property_returns_first_tier_client(self):
        """
        Scenario: _primary returns the Tier-1 client for Agent.effective_model.
          Given  a MultiTierModelClient with three tiers
          When   ._primary is read
          Then   it is the first tier's client
        """
        t1 = _SuccessClient("ultra")
        t2 = _SuccessClient("lightning")
        t3 = _SuccessClient("haiku")
        client = MultiTierModelClient(tiers=[(t1, 5.0), (t2, 5.0), (t3, 5.0)])
        assert client._primary is t1

    async def test_asyncio_timeout_fires_and_next_tier_used(self):
        """
        Scenario: asyncio.wait_for fires when a tier is slow → next tier used.
          Given  Tier-1 sleeps 1 s; asyncio timeout is 0.05 s; Tier-2 succeeds
          When   .parse() is called
          Then   _last_model_used == 'lightning' (Tier-2 responded)
        """
        class _SlowClient:
            _model_id = "ultra"
            async def parse(self, **__):
                await asyncio.sleep(1.0)
                return _StubParseable(_EchoOutput(message="too late"))

        t1 = _SlowClient()
        t2 = _SuccessClient("lightning")

        client = MultiTierModelClient(tiers=[(t1, 0.05), (t2, 5.0)])
        await client.parse(**_PARSE_KWARGS)
        assert client._last_model_used == "lightning"


# ══════════════════════════════════════════════════════════════════════════════
# 15.3 — NvidiaCircuitBreaker state machine
# ══════════════════════════════════════════════════════════════════════════════

class TestNvidiaCircuitBreaker:
    """Step 15.3 scenario tests."""

    def test_starts_closed(self):
        """
        Scenario: A new circuit breaker starts CLOSED.
          Given  NvidiaCircuitBreaker()
          When   .is_open is read
          Then   it is False; consecutive_failures == 0
        """
        cb = NvidiaCircuitBreaker(threshold=5, cooldown_seconds=120)
        assert cb.is_open is False
        assert cb.consecutive_failures == 0

    def test_trips_after_threshold_failures(self, caplog):
        """
        Scenario: Breaker trips (OPEN) after exactly threshold failures.
          Given  threshold=3
          When   record_nvidia_both_failed() is called 3 times
          Then   is_open becomes True
                 open_until is approximately now + 120 s
                 WARNING logged mentioning "circuit breaker tripped"
        """
        cb = NvidiaCircuitBreaker(threshold=3, cooldown_seconds=120)
        with caplog.at_level(logging.WARNING):
            cb.record_nvidia_both_failed()
            assert cb.is_open is False
            cb.record_nvidia_both_failed()
            assert cb.is_open is False
            cb.record_nvidia_both_failed()
        assert cb.is_open is True
        assert cb.open_until is not None
        expected_until = datetime.now(UTC) + timedelta(seconds=120)
        delta = abs((cb.open_until - expected_until).total_seconds())
        assert delta < 2.0  # within 2 seconds of expected
        assert any("circuit breaker tripped" in r.message for r in caplog.records)

    def test_below_threshold_stays_closed(self):
        """
        Scenario: Fewer failures than threshold — breaker stays CLOSED.
          Given  threshold=5
          When   record_nvidia_both_failed() is called 4 times
          Then   is_open is still False
        """
        cb = NvidiaCircuitBreaker(threshold=5, cooldown_seconds=120)
        for _ in range(4):
            cb.record_nvidia_both_failed()
        assert cb.is_open is False

    def test_partial_success_resets_counter(self):
        """
        Scenario: A NVIDIA partial success resets the failure counter.
          Given  threshold=5; 4 failures already recorded
          When   record_nvidia_partial_success() is called
          Then   consecutive_failures == 0
                 2 more failures do NOT trip the breaker (total would only be 2)
        """
        cb = NvidiaCircuitBreaker(threshold=5, cooldown_seconds=120)
        for _ in range(4):
            cb.record_nvidia_both_failed()
        cb.record_nvidia_partial_success()
        assert cb.consecutive_failures == 0
        # 2 more failures — should not trip (below threshold)
        cb.record_nvidia_both_failed()
        cb.record_nvidia_both_failed()
        assert cb.is_open is False

    def test_resets_after_cooldown_expires(self, caplog):
        """
        Scenario: Breaker resets (CLOSED) when cooldown_until has passed.
          Given  breaker is OPEN with open_until in the past
          When   is_open is called
          Then   it returns False and consecutive_failures is reset to 0
                 INFO logged mentioning "circuit breaker reset"
        """
        cb = NvidiaCircuitBreaker(threshold=1, cooldown_seconds=120)
        cb.record_nvidia_both_failed()  # trips immediately (threshold=1)
        assert cb.is_open is True

        # Manually backdate the expiry to the past
        cb.open_until = datetime.now(UTC) - timedelta(seconds=1)
        with caplog.at_level(logging.INFO):
            result = cb.is_open
        assert result is False
        assert cb.consecutive_failures == 0
        assert cb.open_until is None
        assert any("circuit breaker reset" in r.message for r in caplog.records)

    def test_still_open_within_cooldown(self):
        """
        Scenario: is_open remains True during active cooldown.
          Given  breaker is OPEN with open_until in the future
          When   is_open is called
          Then   returns True; open_until unchanged
        """
        cb = NvidiaCircuitBreaker(threshold=1, cooldown_seconds=120)
        cb.record_nvidia_both_failed()
        original_until = cb.open_until
        assert cb.is_open is True
        assert cb.open_until == original_until  # not reset yet


# ══════════════════════════════════════════════════════════════════════════════
# 15.4 — Circuit breaker integration with MultiTierModelClient
# ══════════════════════════════════════════════════════════════════════════════

class TestCircuitBreakerIntegration:
    """Step 15.4 scenario tests: breaker + MultiTierModelClient."""

    async def test_open_breaker_skips_nvidia_tiers(self):
        """
        Scenario: When the breaker is OPEN, NVIDIA tiers are skipped.
          Given  circuit breaker is OPEN (open_until in future)
                 MultiTierModelClient with 2 NVIDIA tiers + 1 Haiku tier
          When   .parse() is called
          Then   NVIDIA tiers are never called
                 Haiku tier is called and responds
                 _last_model_used == 'haiku'
        """
        cb = NvidiaCircuitBreaker(threshold=1, cooldown_seconds=120)
        cb.record_nvidia_both_failed()  # trips immediately
        assert cb.is_open is True

        t1 = _FailClient(RuntimeError("should not be called"), "ultra")
        t2 = _FailClient(RuntimeError("should not be called"), "lightning")
        t3 = _SuccessClient("haiku")

        client = MultiTierModelClient(
            tiers=[(t1, 5.0), (t2, 5.0), (t3, 5.0)],
            circuit_breaker=cb,
            nvidia_tier_count=2,
        )
        await client.parse(**_PARSE_KWARGS)

        assert client._last_model_used == "haiku"
        assert t1.call_count == 0
        assert t2.call_count == 0
        assert t3.call_count == 1

    async def test_breaker_trips_after_threshold_consecutive_all_fail(self):
        """
        Scenario: Breaker trips after threshold consecutive all-NVIDIA-fail calls.
          Given  threshold=2; both NVIDIA tiers fail; Haiku succeeds
          When   .parse() is called 3 times (all NVIDIA tiers fail each time)
          Then   on the 3rd call the breaker is OPEN
        """
        cb = NvidiaCircuitBreaker(threshold=2, cooldown_seconds=120)
        e_ultra = RuntimeError("ultra down")
        e_lightning = RuntimeError("lightning down")

        t1 = _FailClient(e_ultra, "ultra")
        t2 = _FailClient(e_lightning, "lightning")
        t3 = _SuccessClient("haiku")

        client = MultiTierModelClient(
            tiers=[(t1, 5.0), (t2, 5.0), (t3, 5.0)],
            circuit_breaker=cb,
            nvidia_tier_count=2,
        )

        # Call 1: both NVIDIA fail, Haiku succeeds → consecutive_failures = 1
        await client.parse(**_PARSE_KWARGS)
        assert cb.consecutive_failures == 1
        assert cb.is_open is False

        # Reset call counts for clarity
        t1.call_count = 0
        t2.call_count = 0
        t3.call_count = 0

        # Call 2: both NVIDIA fail again → consecutive_failures = 2 → breaker trips
        await client.parse(**_PARSE_KWARGS)
        assert cb.is_open is True

    async def test_partial_nvidia_success_resets_breaker_counter(self):
        """
        Scenario: If Tier-1 fails but Tier-2 succeeds, the failure counter resets.
          Given  threshold=5; Tier-1 fails; Tier-2 succeeds (partial NVIDIA success)
          When   .parse() is called
          Then   consecutive_failures stays 0 (not incremented)
        """
        cb = NvidiaCircuitBreaker(threshold=5, cooldown_seconds=120)
        cb.consecutive_failures = 4  # pre-load near threshold

        t1 = _FailClient(RuntimeError("ultra fail"), "ultra")
        t2 = _SuccessClient("lightning")  # partial NVIDIA success

        client = MultiTierModelClient(
            tiers=[(t1, 5.0), (t2, 5.0)],
            circuit_breaker=cb,
            nvidia_tier_count=2,
        )
        await client.parse(**_PARSE_KWARGS)
        assert client._last_model_used == "lightning"
        # Counter should have been reset to 0 (partial success)
        assert cb.consecutive_failures == 0
        assert cb.is_open is False

    async def test_no_circuit_breaker_in_anthropic_mode(self):
        """
        Scenario: MultiTierModelClient without circuit_breaker — no breaker logic.
          Given  no circuit_breaker is passed
                 all tiers fail
          When   .parse() is called
          Then   AllProvidersUnavailableError raised (no breaker state changes)
        """
        t1 = _FailClient(RuntimeError("haiku fail"), "haiku")
        t2 = _FailClient(RuntimeError("ultra fail"), "ultra")
        t3 = _FailClient(RuntimeError("lightning fail"), "lightning")

        client = MultiTierModelClient(
            tiers=[(t1, 5.0), (t2, 5.0), (t3, 5.0)],
            circuit_breaker=None,
        )
        with pytest.raises(AllProvidersUnavailableError) as exc_info:
            await client.parse(**_PARSE_KWARGS)
        assert len(exc_info.value.errors) == 3


# ══════════════════════════════════════════════════════════════════════════════
# 15.5 — ANTHROPIC mode reversed chain (Haiku → Ultra → Lightning)
# ══════════════════════════════════════════════════════════════════════════════

class TestAnthropicModeChain:
    """Step 15.5 scenario tests: ANTHROPIC-primary mode ordering."""

    async def test_haiku_first_in_anthropic_mode(self):
        """
        Scenario: In ANTHROPIC mode, Haiku is tried first.
          Given  a MultiTierModelClient modelling ANTHROPIC mode order
                 (Haiku, Ultra, Lightning) with no circuit breaker
          When   .parse() succeeds on Tier-1
          Then   _last_model_used == 'claude-haiku-4-5-20251001'
        """
        haiku = _SuccessClient("claude-haiku-4-5-20251001")
        ultra = _FailClient(RuntimeError("should not be called"), "ultra")
        lightning = _FailClient(RuntimeError("should not be called"), "lightning")

        client = MultiTierModelClient(
            tiers=[(haiku, 10.0), (ultra, 20.0), (lightning, 20.0)],
            circuit_breaker=None,
        )
        await client.parse(**_PARSE_KWARGS)
        assert client._last_model_used == "claude-haiku-4-5-20251001"
        assert ultra.call_count == 0
        assert lightning.call_count == 0

    async def test_haiku_fails_ultra_answers(self):
        """
        Scenario: Haiku fails → Ultra answers.
          Given  ANTHROPIC mode order (Haiku → Ultra → Lightning)
                 Haiku raises an error; Ultra succeeds
          When   .parse() is called
          Then   _last_model_used == 'ultra'
                 Lightning never called
        """
        haiku = _FailClient(RuntimeError("haiku 429"), "claude-haiku-4-5-20251001")
        ultra = _SuccessClient("ultra")
        lightning = _FailClient(RuntimeError("should not be called"), "lightning")

        client = MultiTierModelClient(
            tiers=[(haiku, 10.0), (ultra, 20.0), (lightning, 20.0)],
            circuit_breaker=None,
        )
        await client.parse(**_PARSE_KWARGS)
        assert client._last_model_used == "ultra"
        assert lightning.call_count == 0

    async def test_anthropic_mode_all_fail(self):
        """
        Scenario: All three tiers fail in ANTHROPIC mode → AllProvidersUnavailableError.
          Given  ANTHROPIC mode order; all three tiers fail
          When   .parse() is called
          Then   AllProvidersUnavailableError raised with 3 errors
        """
        haiku = _FailClient(RuntimeError("haiku down"), "haiku")
        ultra = _FailClient(RuntimeError("ultra down"), "ultra")
        lightning = _FailClient(RuntimeError("lightning down"), "lightning")

        client = MultiTierModelClient(
            tiers=[(haiku, 10.0), (ultra, 20.0), (lightning, 20.0)],
            circuit_breaker=None,
        )
        with pytest.raises(AllProvidersUnavailableError) as exc_info:
            await client.parse(**_PARSE_KWARGS)
        assert len(exc_info.value.errors) == 3


# ══════════════════════════════════════════════════════════════════════════════
# 15.6 — create_model_client() factory
# ══════════════════════════════════════════════════════════════════════════════

class TestCreateModelClientFactory:
    """Step 15.6 scenario tests: factory creates correct MultiTierModelClient."""

    def _make_settings(self, **overrides):
        """Return a SimpleNamespace mimicking Settings for factory tests."""
        import types
        defaults = dict(
            app_brain_model="NVIDIA",
            anthropic_api_key="test-anthropic-key",
            app_anthropic_model_id="claude-haiku-4-5-20251001",
            nvidia_api_key="nvapi-test-key",
            nvidia_base_url="https://integrate.api.nvidia.com/v1",
            nvidia_model_id_primary="nvidia/nemotron-3-ultra-550b-a55b",
            nvidia_model_id_secondary="nvidia/nemotron-3.5-lightning-30b-a3b",
            nvidia_tier1_timeout_secs=10,
            nvidia_tier2_timeout_secs=20,
            anthropic_tier_timeout_secs=20,
            nvidia_circuit_breaker_threshold=5,
            nvidia_circuit_breaker_cooldown_secs=120,
        )
        defaults.update(overrides)
        return types.SimpleNamespace(**defaults)

    def test_nvidia_mode_returns_multi_tier_with_circuit_breaker(self):
        """
        Scenario: NVIDIA mode → MultiTierModelClient with 3 tiers and circuit breaker.
          Given  APP_BRAIN_MODEL=NVIDIA with both API keys present
          When   create_model_client() is called
          Then   returns MultiTierModelClient
                 _circuit_breaker is a NvidiaCircuitBreaker
                 has 3 tiers (ultra, lightning, haiku)
        """
        from app.agents.model_client import create_model_client
        import app.agents.model_client as mc_module

        fake_settings = self._make_settings(app_brain_model="NVIDIA")
        # Reset global breaker so test is deterministic
        mc_module._nvidia_circuit_breaker = None

        with patch("app.config.get_settings", return_value=fake_settings):
            client = create_model_client()

        assert isinstance(client, MultiTierModelClient)
        assert client._circuit_breaker is not None
        assert isinstance(client._circuit_breaker, NvidiaCircuitBreaker)
        assert len(client._tiers) == 3
        # Tier order: ultra → lightning → haiku
        assert client._tiers[0][0]._model_id == "nvidia/nemotron-3-ultra-550b-a55b"
        assert client._tiers[1][0]._model_id == "nvidia/nemotron-3.5-lightning-30b-a3b"
        assert client._tiers[2][0]._model_id == "claude-haiku-4-5-20251001"

    def test_nvidia_mode_without_anthropic_key_two_tiers(self):
        """
        Scenario: NVIDIA mode without ANTHROPIC_API_KEY → two-tier chain (no Haiku).
          Given  APP_BRAIN_MODEL=NVIDIA; no anthropic_api_key
          When   create_model_client() is called
          Then   returns MultiTierModelClient with 2 tiers (ultra, lightning)
        """
        from app.agents.model_client import create_model_client
        import app.agents.model_client as mc_module

        fake_settings = self._make_settings(
            app_brain_model="NVIDIA",
            anthropic_api_key="",
        )
        mc_module._nvidia_circuit_breaker = None

        with patch("app.config.get_settings", return_value=fake_settings):
            client = create_model_client()

        assert isinstance(client, MultiTierModelClient)
        assert len(client._tiers) == 2
        assert client._tiers[0][0]._model_id == "nvidia/nemotron-3-ultra-550b-a55b"
        assert client._tiers[1][0]._model_id == "nvidia/nemotron-3.5-lightning-30b-a3b"

    def test_anthropic_mode_returns_multi_tier_haiku_first(self):
        """
        Scenario: ANTHROPIC mode → MultiTierModelClient; Haiku is Tier-1.
          Given  APP_BRAIN_MODEL=ANTHROPIC with both keys present
          When   create_model_client() is called
          Then   returns MultiTierModelClient; no circuit breaker
                 Tier-1 is Haiku; Tier-2 is Ultra; Tier-3 is Lightning
        """
        from app.agents.model_client import create_model_client, AnthropicModelClient, NVIDIAModelClient

        fake_settings = self._make_settings(app_brain_model="ANTHROPIC")

        with patch("app.config.get_settings", return_value=fake_settings):
            client = create_model_client()

        assert isinstance(client, MultiTierModelClient)
        assert client._circuit_breaker is None
        assert len(client._tiers) == 3
        t1_client, t1_timeout = client._tiers[0]
        t2_client, t2_timeout = client._tiers[1]
        t3_client, t3_timeout = client._tiers[2]
        # Tier order: haiku → ultra → lightning
        assert isinstance(t1_client, AnthropicModelClient)
        assert t1_client._model_id == "claude-haiku-4-5-20251001"
        assert isinstance(t2_client, NVIDIAModelClient)
        assert t2_client._model_id == "nvidia/nemotron-3-ultra-550b-a55b"
        assert isinstance(t3_client, NVIDIAModelClient)
        assert t3_client._model_id == "nvidia/nemotron-3.5-lightning-30b-a3b"

    def test_anthropic_mode_without_nvidia_key_single_tier(self):
        """
        Scenario: ANTHROPIC mode without NVIDIA key → single-tier Haiku only.
          Given  APP_BRAIN_MODEL=ANTHROPIC; no nvidia_api_key
          When   create_model_client() is called
          Then   returns MultiTierModelClient with 1 tier (haiku)
        """
        from app.agents.model_client import create_model_client

        fake_settings = self._make_settings(
            app_brain_model="ANTHROPIC",
            nvidia_api_key="",
        )

        with patch("app.config.get_settings", return_value=fake_settings):
            client = create_model_client()

        assert isinstance(client, MultiTierModelClient)
        assert len(client._tiers) == 1
        assert client._tiers[0][0]._model_id == "claude-haiku-4-5-20251001"

    def test_invalid_brain_model_raises_value_error(self):
        """
        Scenario: Unknown APP_BRAIN_MODEL → ValueError.
          Given  APP_BRAIN_MODEL='GEMINI'
          When   create_model_client() is called
          Then   ValueError is raised mentioning valid values
        """
        from app.agents.model_client import create_model_client

        fake_settings = self._make_settings(app_brain_model="GEMINI")

        with patch("app.config.get_settings", return_value=fake_settings):
            with pytest.raises(ValueError, match="ANTHROPIC.*NVIDIA"):
                create_model_client()

    def test_nvidia_mode_missing_api_key_raises(self):
        """
        Scenario: NVIDIA mode without key → ValueError.
          Given  APP_BRAIN_MODEL=NVIDIA; nvidia_api_key is empty
          When   create_model_client() is called
          Then   ValueError raised mentioning NVIDIA_API_KEY
        """
        from app.agents.model_client import create_model_client
        import app.agents.model_client as mc_module

        fake_settings = self._make_settings(
            app_brain_model="NVIDIA",
            nvidia_api_key="",
        )
        mc_module._nvidia_circuit_breaker = None

        with patch("app.config.get_settings", return_value=fake_settings):
            with pytest.raises(ValueError, match="NVIDIA_API_KEY"):
                create_model_client()

    def test_nvidia_tier_timeouts_match_config(self):
        """
        Scenario: Tier timeouts come from settings, not hard-coded values.
          Given  NVIDIA_TIER1_TIMEOUT_SECS=7; NVIDIA_TIER2_TIMEOUT_SECS=15
          When   create_model_client() is called in NVIDIA mode
          Then   Tier-1 timeout is 7.0; Tier-2 timeout is 15.0
        """
        from app.agents.model_client import create_model_client
        import app.agents.model_client as mc_module

        fake_settings = self._make_settings(
            app_brain_model="NVIDIA",
            nvidia_tier1_timeout_secs=7,
            nvidia_tier2_timeout_secs=15,
            anthropic_tier_timeout_secs=25,
        )
        mc_module._nvidia_circuit_breaker = None

        with patch("app.config.get_settings", return_value=fake_settings):
            client = create_model_client()

        assert isinstance(client, MultiTierModelClient)
        assert client._tiers[0][1] == 7.0
        assert client._tiers[1][1] == 15.0
        assert client._tiers[2][1] == 25.0

    def test_haiku_model_id_comes_from_config(self):
        """
        Scenario: Anthropic model ID comes from APP_ANTHROPIC_MODEL_ID setting.
          Given  APP_ANTHROPIC_MODEL_ID='claude-haiku-4-5-20251001' (the only allowed value)
          When   create_model_client() is called
          Then   Haiku tier uses exactly that model ID in all modes
        """
        from app.agents.model_client import create_model_client
        import app.agents.model_client as mc_module

        for mode in ("NVIDIA", "ANTHROPIC"):
            mc_module._nvidia_circuit_breaker = None
            fake_settings = self._make_settings(
                app_brain_model=mode,
                app_anthropic_model_id="claude-haiku-4-5-20251001",
            )
            with patch("app.config.get_settings", return_value=fake_settings):
                client = create_model_client()

            assert isinstance(client, MultiTierModelClient)
            # Find the Haiku tier (AnthropicModelClient)
            from app.agents.model_client import AnthropicModelClient
            haiku_tiers = [
                (c, t) for c, t in client._tiers if isinstance(c, AnthropicModelClient)
            ]
            assert len(haiku_tiers) == 1
            assert haiku_tiers[0][0]._model_id == "claude-haiku-4-5-20251001"
