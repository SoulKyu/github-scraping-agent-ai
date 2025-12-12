"""Tests for LLM provider factory."""

import pytest

from src.llm.factory import create_provider
from src.llm.openai_provider import OpenAIProvider
from src.llm.anthropic_provider import AnthropicProvider
from src.llm.google_provider import GoogleProvider


def test_create_openai_provider():
    """Factory creates OpenAI provider."""
    with pytest.MonkeyPatch().context() as mp:
        mp.setenv("OPENAI_API_KEY", "")  # Prevent real client init
        provider = create_provider("openai", "gpt-4o-mini", "test-key")
        assert isinstance(provider, OpenAIProvider)


def test_create_anthropic_provider():
    """Factory creates Anthropic provider."""
    provider = create_provider("anthropic", "claude-3-haiku-20240307", "test-key")
    assert isinstance(provider, AnthropicProvider)


def test_create_google_provider():
    """Factory creates Google provider."""
    from unittest.mock import patch
    with patch("google.generativeai.configure"):
        with patch("google.generativeai.GenerativeModel"):
            provider = create_provider("google", "gemini-1.5-flash", "test-key")
            assert isinstance(provider, GoogleProvider)


def test_create_unknown_provider():
    """Factory raises error for unknown provider."""
    with pytest.raises(ValueError, match="Unknown provider"):
        create_provider("unknown", "model", "key")
