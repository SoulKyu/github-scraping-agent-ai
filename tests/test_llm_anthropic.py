"""Tests for Anthropic LLM provider."""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.github import Repository
from src.llm.anthropic_provider import AnthropicProvider


@pytest.fixture
def sample_repo():
    """Sample repository for testing."""
    return Repository(
        full_name="owner/cool-ai-tool",
        url="https://github.com/owner/cool-ai-tool",
        description="An AI-powered CLI tool",
        stars=150,
        language="Python",
        topics=["ai", "cli"],
        readme="# Cool AI Tool\nThis tool does amazing things.",
    )


def test_anthropic_provider_interested(sample_repo):
    """Anthropic provider returns interested=True for matching project."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"interested": true, "reason": "Matches AI interest"}')]

    with patch("anthropic.Anthropic") as mock_client_class:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_client_class.return_value = mock_client

        provider = AnthropicProvider(api_key="test-key", model="claude-3-haiku-20240307")
        result = provider.evaluate(sample_repo, "I like AI tools")

        assert result.interested is True
        assert "AI" in result.reason


def test_anthropic_provider_not_interested(sample_repo):
    """Anthropic provider returns interested=False for non-matching project."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"interested": false, "reason": "Not relevant"}')]

    with patch("anthropic.Anthropic") as mock_client_class:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_client_class.return_value = mock_client

        provider = AnthropicProvider(api_key="test-key", model="claude-3-haiku-20240307")
        result = provider.evaluate(sample_repo, "I like Rust only")

        assert result.interested is False
