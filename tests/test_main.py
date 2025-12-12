"""Tests for main pipeline."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.main import run_pipeline
from src.github import Repository


@pytest.fixture
def temp_config():
    """Create temporary config file."""
    config_data = {
        "github": {"token": "ghp_test"},
        "llm": {"provider": "openai", "model": "gpt-4o-mini", "api_key": "sk-test"},
        "discord": {"webhook_url": "https://discord.com/api/webhooks/test"},
        "settings": {"max_repos": 10, "readme_max_chars": 100, "batch_size": 5, "cache_days": 30}
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        config_path = Path(f.name)

    try:
        yield config_path
    finally:
        config_path.unlink(missing_ok=True)


@pytest.fixture
def temp_prompt():
    """Create temporary prompt file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("I like AI tools")
        prompt_path = Path(f.name)

    try:
        yield prompt_path
    finally:
        prompt_path.unlink(missing_ok=True)


@pytest.fixture
def temp_cache():
    """Create temporary cache file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{}")
        cache_path = Path(f.name)

    try:
        yield cache_path
    finally:
        cache_path.unlink(missing_ok=True)


def test_run_pipeline_dry_run(temp_config, temp_prompt, temp_cache):
    """Pipeline runs in dry-run mode without sending to Discord."""
    mock_repos = [
        Repository("owner/repo1", "https://github.com/owner/repo1", "AI tool", 100, "Python", ["ai"], False, "readme"),
    ]

    # Create async mock for AsyncGitHubClient
    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)
    mock_async_client.search_repos = AsyncMock(return_value=mock_repos)
    mock_async_client.fetch_readmes = AsyncMock(return_value={"owner/repo1": "readme content"})

    with patch("src.main.AsyncGitHubClient", return_value=mock_async_client):
        with patch("src.main.create_provider") as mock_llm:
            mock_provider = MagicMock()
            mock_provider.evaluate.return_value = MagicMock(interested=True, reason="AI tool")
            mock_llm.return_value = mock_provider

            with patch("src.main.DiscordClient") as mock_discord:
                result = run_pipeline(
                    config_path=temp_config,
                    prompt_path=temp_prompt,
                    cache_path=temp_cache,
                    dry_run=True,
                )

                # Discord should not be called in dry run
                mock_discord.return_value.send_repos.assert_not_called()

                assert result["processed"] == 1
                assert result["matched"] == 1


def test_run_pipeline_excludes_forks(temp_config, temp_prompt, temp_cache):
    """Pipeline excludes forked repositories."""
    # This test verifies that exclude_forks=True is passed to search_repos

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)
    mock_async_client.search_repos = AsyncMock(return_value=[])
    mock_async_client.fetch_readmes = AsyncMock(return_value={})

    with patch("src.main.AsyncGitHubClient", return_value=mock_async_client):
        with patch("src.main.create_provider") as mock_llm:
            mock_provider = MagicMock()
            mock_llm.return_value = mock_provider

            run_pipeline(
                config_path=temp_config,
                prompt_path=temp_prompt,
                cache_path=temp_cache,
                dry_run=True,
            )

            # Verify search_repos was called with exclude_forks=True
            mock_async_client.search_repos.assert_called_once()
            call_kwargs = mock_async_client.search_repos.call_args[1]
            assert call_kwargs.get("exclude_forks") is True
