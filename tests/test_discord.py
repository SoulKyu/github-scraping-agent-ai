"""Tests for Discord webhook client."""

import httpx
import pytest

from src.discord import DiscordClient, format_repo_embed
from src.github import Repository
from src.llm.base import EvaluationResult


@pytest.fixture
def sample_repo():
    """Sample repository."""
    return Repository(
        full_name="owner/cool-ai-tool",
        url="https://github.com/owner/cool-ai-tool",
        description="An AI-powered CLI tool for productivity",
        stars=150,
        language="Python",
        topics=["ai", "cli", "productivity"],
    )


@pytest.fixture
def sample_result():
    """Sample evaluation result."""
    return EvaluationResult(interested=True, reason="Matches your interest in AI tools")


def test_format_repo_embed(sample_repo, sample_result):
    """format_repo_embed creates Discord embed structure."""
    embed = format_repo_embed(sample_repo, sample_result)

    assert embed["title"] == "owner/cool-ai-tool"
    assert embed["url"] == "https://github.com/owner/cool-ai-tool"
    assert "150" in embed["description"]
    assert "Python" in embed["description"]
    assert "AI-powered CLI tool" in embed["description"]
    assert "ai, cli, productivity" in embed["description"]
    assert "Matches your interest" in embed["description"]


def test_discord_client_send_repos(sample_repo, sample_result):
    """DiscordClient sends repos to webhook."""
    sent_payloads = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        import json
        sent_payloads.append(json.loads(request.content))
        return httpx.Response(204)

    transport = httpx.MockTransport(mock_handler)
    client = DiscordClient(webhook_url="https://discord.com/api/webhooks/test", transport=transport)

    repos_with_results = [(sample_repo, sample_result)]
    client.send_repos(repos_with_results, batch_size=10)

    assert len(sent_payloads) == 1
    assert "embeds" in sent_payloads[0]
    assert len(sent_payloads[0]["embeds"]) == 1


def test_discord_client_batches_repos(sample_repo, sample_result):
    """DiscordClient batches repos into multiple messages."""
    sent_payloads = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        import json
        sent_payloads.append(json.loads(request.content))
        return httpx.Response(204)

    transport = httpx.MockTransport(mock_handler)
    client = DiscordClient(webhook_url="https://discord.com/api/webhooks/test", transport=transport)

    # Create 15 repos to test batching with batch_size=10
    repos_with_results = [(sample_repo, sample_result)] * 15
    client.send_repos(repos_with_results, batch_size=10)

    assert len(sent_payloads) == 2  # 10 + 5
    assert len(sent_payloads[0]["embeds"]) == 10
    assert len(sent_payloads[1]["embeds"]) == 5
