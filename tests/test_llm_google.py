"""Tests for Google LLM provider."""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.github import Repository
from src.llm.google_provider import GoogleProvider


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


def test_google_provider_interested(sample_repo):
    """Google provider returns interested=True for matching project."""
    with patch("google.generativeai.configure"):
        with patch("google.generativeai.GenerativeModel") as mock_model_class:
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = '{"interested": true, "reason": "Matches AI interest"}'
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model

            provider = GoogleProvider(api_key="test-key", model="gemini-1.5-flash")
            result = provider.evaluate(sample_repo, "I like AI tools")

            assert result.interested is True
            assert "AI" in result.reason


def test_google_provider_not_interested(sample_repo):
    """Google provider returns interested=False for non-matching project."""
    with patch("google.generativeai.configure"):
        with patch("google.generativeai.GenerativeModel") as mock_model_class:
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = '{"interested": false, "reason": "Not relevant"}'
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model

            provider = GoogleProvider(api_key="test-key", model="gemini-1.5-flash")
            result = provider.evaluate(sample_repo, "I like Rust only")

            assert result.interested is False
