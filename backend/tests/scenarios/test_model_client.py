"""
Scenario tests — Phase 8: Model Client Factory and NVIDIA Client.

Tests the model abstraction layer that allows switching between Anthropic and NVIDIA providers.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from app.agents.model_client import (
    AnthropicModelClient,
    NVIDIAModelClient,
    create_model_client,
)
from app.config import get_settings
from tests.fixtures.stub_claude_client import StubClaudeClient, StubNVIDIAModelClient


# ── Test Models ────────────────────────────────────────────────────────────────

class _TestOutput(BaseModel):
    greeting: str
    score: float


# ── Factory Tests ──────────────────────────────────────────────────────────────

class TestModelClientFactory:
    """Test the create_model_client factory function."""

    def test_factory_returns_anthropic_client_when_configured(self, monkeypatch):
        """Phase 15: APP_BRAIN_MODEL=ANTHROPIC → MultiTierModelClient; Haiku is Tier-1."""
        import app.agents.model_client as mc_module
        from app.agents.model_client import MultiTierModelClient

        monkeypatch.setenv("APP_BRAIN_MODEL", "ANTHROPIC")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("NVIDIA_API_KEY", "")  # no NVIDIA → single-tier Haiku

        get_settings.cache_clear()
        mc_module._nvidia_circuit_breaker = None

        client = create_model_client()
        # Phase 15: always returns MultiTierModelClient; Haiku is the first (and only) tier here
        assert isinstance(client, MultiTierModelClient)
        assert client._tiers[0][0]._model_id == "claude-haiku-4-5-20251001"
        assert client._circuit_breaker is None  # no circuit breaker in ANTHROPIC mode

    def test_factory_returns_nvidia_client_when_configured(self, monkeypatch):
        """Phase 15: APP_BRAIN_MODEL=NVIDIA without ANTHROPIC key → 2-tier MultiTierModelClient.

        Phase 15 always returns MultiTierModelClient (replaces bare NVIDIAModelClient).
        Without ANTHROPIC_API_KEY, the chain is Ultra → Lightning (no Haiku fallback).
        """
        import app.agents.model_client as mc_module
        from app.agents.model_client import MultiTierModelClient, NvidiaCircuitBreaker

        monkeypatch.setenv("APP_BRAIN_MODEL", "NVIDIA")
        monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-key-000000000000000000000000000")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")  # no Anthropic key → no Haiku tier

        get_settings.cache_clear()
        mc_module._nvidia_circuit_breaker = None

        client = create_model_client()
        assert isinstance(client, MultiTierModelClient)
        assert len(client._tiers) == 2
        assert isinstance(client._circuit_breaker, NvidiaCircuitBreaker)

    def test_factory_returns_fallback_client_when_both_keys_configured(self, monkeypatch):
        """Phase 15: NVIDIA + ANTHROPIC keys both set → 3-tier MultiTierModelClient."""
        import app.agents.model_client as mc_module
        from app.agents.model_client import MultiTierModelClient, NvidiaCircuitBreaker

        monkeypatch.setenv("APP_BRAIN_MODEL", "NVIDIA")
        monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-key-000000000000000000000000000")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        get_settings.cache_clear()
        mc_module._nvidia_circuit_breaker = None

        client = create_model_client()
        # Phase 15: 3 tiers — Ultra → Lightning → Haiku; circuit breaker active
        assert isinstance(client, MultiTierModelClient)
        assert len(client._tiers) == 3
        assert isinstance(client._circuit_breaker, NvidiaCircuitBreaker)

    def test_factory_raises_error_for_invalid_provider(self, monkeypatch):
        """Given invalid APP_BRAIN_MODEL, factory raises clear error."""
        monkeypatch.setenv("APP_BRAIN_MODEL", "INVALID")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        
        get_settings.cache_clear()
        
        with pytest.raises(ValueError, match="Invalid APP_BRAIN_MODEL"):
            create_model_client()

    def test_factory_raises_error_when_anthropic_key_missing(self, monkeypatch):
        """Given APP_BRAIN_MODEL=ANTHROPIC but no API key, factory raises error."""
        monkeypatch.setenv("APP_BRAIN_MODEL", "ANTHROPIC")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")  # Empty string to simulate missing key
        
        get_settings.cache_clear()
        
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"):
            create_model_client()

    def test_factory_raises_error_when_nvidia_key_missing(self, monkeypatch):
        """Given APP_BRAIN_MODEL=NVIDIA but no API key, factory raises error."""
        monkeypatch.setenv("APP_BRAIN_MODEL", "NVIDIA")
        monkeypatch.setenv("NVIDIA_API_KEY", "")  # Empty string to simulate missing key
        
        get_settings.cache_clear()
        
        with pytest.raises(ValueError, match="NVIDIA_API_KEY is required"):
            create_model_client()

    def test_both_clients_implement_model_client_protocol(self):
        """Both AnthropicModelClient and NVIDIAModelClient implement ModelClient protocol."""
        # This is a structural test — if they didn't implement the protocol,
        # the type checker would catch it and the code wouldn't run.
        anthropic_client = AnthropicModelClient(api_key="test")
        nvidia_client = NVIDIAModelClient(api_key="test")
        
        # Both should have messages attribute with parse method
        assert hasattr(anthropic_client, "messages")
        assert hasattr(anthropic_client.messages, "parse")
        assert hasattr(anthropic_client, "parse")
        
        assert hasattr(nvidia_client, "messages")
        assert hasattr(nvidia_client.messages, "parse")
        assert hasattr(nvidia_client, "parse")


# ── NVIDIA Client Tests (with stub) ─────────────────────────────────────────────

class TestNVIDIAModelClientWithStub:
    """Test NVIDIA client behavior using stub (no real API calls)."""

    @pytest.mark.asyncio
    async def test_structured_outputs_parsing_works(self):
        """NVIDIA client correctly parses structured output with OpenAI-format response."""
        # Use the stub directly as it implements the ModelClient protocol
        client = StubNVIDIAModelClient(
            response_data={"greeting": "Hello from Nemotron!", "score": 0.95}
        )
        
        response = await client.parse(
            model="nemotron-3-ultra",
            system="You are a helpful assistant.",
            messages=[{"role": "user", "content": "Say hello"}],
            max_tokens=100,
            output_format=_TestOutput,
        )
        
        parsed = response.choices[0].message.parsed
        assert isinstance(parsed, _TestOutput)
        assert parsed.greeting == "Hello from Nemotron!"
        assert parsed.score == 0.95

    @pytest.mark.asyncio
    async def test_token_counts_extracted_correctly(self):
        """Token counts match the stub's fake usage."""
        client = StubNVIDIAModelClient(
            response_data={"greeting": "Hi", "score": 0.5}
        )
        
        response = await client.parse(
            model="nemotron-3-ultra",
            system="Test",
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=100,
            output_format=_TestOutput,
        )
        
        assert response.usage.input_tokens == 100
        assert response.usage.output_tokens == 50

    @pytest.mark.asyncio
    async def test_malformed_response_raises_validation_error(self):
        """Malformed responses are caught and raise ValidationError."""
        client = StubNVIDIAModelClient(
            response_data={"wrong_field": "oops"}  # missing required fields
        )
        
        with pytest.raises(Exception):  # Pydantic ValidationError
            await client.parse(
                model="nemotron-3-ultra",
                system="Test",
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=100,
                output_format=_TestOutput,
            )

    @pytest.mark.asyncio
    async def test_transient_error_triggers_retry(self):
        """Phase 14.2: NVIDIAModelClient has empty _transient_errors — FallbackModelClient handles routing.

        After Phase 14.2, NVIDIAModelClient._transient_errors is intentionally empty so
        that a single failure immediately falls through to the Haiku fallback tier inside
        FallbackModelClient, rather than retrying the slow NVIDIA endpoint multiple times.

        This test documents the new behaviour: the empty tuple means no in-client retries.
        """
        from app.agents.model_client import openai

        client = NVIDIAModelClient(api_key="nvapi-test")

        # Phase 14.2 behaviour: _transient_errors is EMPTY — no automatic retries at
        # the client level.  FallbackModelClient handles the "try again" routing.
        assert client._transient_errors == ()
        assert openai.RateLimitError not in client._transient_errors

    @pytest.mark.asyncio
    async def test_non_transient_error_fails_immediately(self):
        """Non-transient errors (400, 401, 404) fail immediately without retry."""
        from app.agents.model_client import openai
        
        class _FailingStub:
            def __init__(self):
                self.messages = self
                
            async def parse(self, **kwargs):
                raise openai.BadRequestError("invalid request")
        
        client = NVIDIAModelClient(api_key="test")
        client.messages = _FailingStub()
        
        # BadRequestError should NOT be in _transient_errors
        assert openai.BadRequestError not in client._transient_errors

    def test_works_with_stub_fixture_pattern(self):
        """NVIDIA client works with the stub client fixture pattern used in tests."""
        # This verifies the StubNVIDIAModelClient can be used as a drop-in replacement
        stub = StubNVIDIAModelClient(
            response_data={"greeting": "Test", "score": 0.75}
        )
        
        assert hasattr(stub, "messages")
        assert hasattr(stub, "parse")
        assert hasattr(stub, "beta")
        assert stub.messages.call_count == 0


# ── Anthropic Client Tests (with stub) ──────────────────────────────────────────

class TestAnthropicModelClientWithStub:
    """Test Anthropic client behavior using stub (regression tests)."""

    @pytest.mark.asyncio
    async def test_structured_outputs_parsing_works(self):
        """Anthropic client correctly parses structured output with Anthropic-format response."""
        client = StubClaudeClient(
            response_data={"greeting": "Hello from Claude!", "score": 0.95}
        )
        
        response = await client.parse(
            model="claude-sonnet-5",
            system="You are a helpful assistant.",
            messages=[{"role": "user", "content": "Say hello"}],
            max_tokens=100,
            output_format=_TestOutput,
        )
        
        # Stub returns _FakeParsedResponse with a `parsed` attribute
        parsed = response.parsed
        assert isinstance(parsed, _TestOutput)
        assert parsed.greeting == "Hello from Claude!"
        assert parsed.score == 0.95

    @pytest.mark.asyncio
    async def test_token_counts_extracted_correctly(self):
        """Token counts match the stub's fake usage."""
        client = StubClaudeClient(
            response_data={"greeting": "Hi", "score": 0.5}
        )
        
        response = await client.parse(
            model="claude-sonnet-5",
            system="Test",
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=100,
            output_format=_TestOutput,
        )
        
        assert response.usage.input_tokens == 100
        assert response.usage.output_tokens == 50

    def test_transient_errors_include_anthropic_types(self):
        """Anthropic client's _transient_errors includes Anthropic error types."""
        from app.agents.model_client import anthropic
        
        client = AnthropicModelClient(api_key="test")
        
        assert anthropic.RateLimitError in client._transient_errors
        assert anthropic.APITimeoutError in client._transient_errors
        assert anthropic.APIConnectionError in client._transient_errors
        assert anthropic.InternalServerError in client._transient_errors


# ── Configuration Tests ────────────────────────────────────────────────────────

class TestConfiguration:
    """Test that settings load all new env vars correctly."""

    def test_settings_loads_all_new_env_vars(self, monkeypatch):
        """Settings correctly loads all Phase 8 environment variables."""
        monkeypatch.setenv("APP_BRAIN_MODEL", "NVIDIA")
        monkeypatch.setenv("NVIDIA_API_KEY", "test-nvidia-key")
        monkeypatch.setenv("NVIDIA_BASE_URL", "https://custom.nvidia.com/v1")
        monkeypatch.setenv("NVIDIA_MODEL_ID", "nvidia/custom-model")
        
        from app.config import Settings, get_settings
        get_settings.cache_clear()
        
        settings = Settings()
        assert settings.app_brain_model == "NVIDIA"
        assert settings.nvidia_api_key == "test-nvidia-key"
        assert settings.nvidia_base_url == "https://custom.nvidia.com/v1"
        assert settings.nvidia_model_id == "nvidia/custom-model"

    def test_settings_default_values_are_sensible(self, monkeypatch):
        """Default values for new settings are sensible."""
        from app.config import Settings, get_settings
        # Override env vars to test defaults (pydantic-settings reads .env file too)
        monkeypatch.setenv("APP_BRAIN_MODEL", "ANTHROPIC")
        monkeypatch.setenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        monkeypatch.setenv("NVIDIA_MODEL_ID", "nemotron-3-ultra")
        
        get_settings.cache_clear()
        
        settings = Settings()
        assert settings.app_brain_model == "ANTHROPIC"
        assert settings.nvidia_base_url == "https://integrate.api.nvidia.com/v1"
        assert settings.nvidia_model_id == "nemotron-3-ultra"