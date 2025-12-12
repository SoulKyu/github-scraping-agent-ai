"""Tests for OpenAI LLM provider."""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.github import Repository
from src.llm.openai_provider import OpenAIProvider


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


def test_openai_provider_interested(sample_repo):
    """OpenAI provider returns interested=True for matching project."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"interested": true, "reason": "Matches AI interest"}'))
    ]

    with patch("openai.OpenAI") as mock_client_class:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_client_class.return_value = mock_client

        provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")
        result = provider.evaluate(sample_repo, "I like AI tools")

        assert result.interested is True
        assert "AI" in result.reason


def test_openai_provider_not_interested(sample_repo):
    """OpenAI provider returns interested=False for non-matching project."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"interested": false, "reason": "Not relevant"}'))
    ]

    with patch("openai.OpenAI") as mock_client_class:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_client_class.return_value = mock_client

        provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")
        result = provider.evaluate(sample_repo, "I like Rust only")

        assert result.interested is False


def test_openai_provider_handles_invalid_json(sample_repo):
    """OpenAI provider handles invalid JSON gracefully."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="not valid json"))
    ]

    with patch("openai.OpenAI") as mock_client_class:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_client_class.return_value = mock_client

        provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")
        result = provider.evaluate(sample_repo, "I like AI tools")

        # Should return not interested on parse failure
        assert result.interested is False
        assert "parse" in result.reason.lower() or "error" in result.reason.lower()
