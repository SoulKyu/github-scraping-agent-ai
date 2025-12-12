"""Tests for configuration loading."""

import json
import tempfile
from pathlib import Path

from src.config import load_config, Config


def test_load_config_from_file():
    """Config loads from JSON file."""
    config_data = {
        "github": {"token": "ghp_test"},
        "llm": {"provider": "openai", "model": "gpt-4o-mini", "api_key": "sk-test"},
        "discord": {"webhook_url": "https://discord.com/api/webhooks/test"},
        "settings": {"max_repos": 100, "readme_max_chars": 500, "batch_size": 10, "cache_days": 30}
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        config_path = Path(f.name)

    try:
        config = load_config(config_path)

        assert config.github_token == "ghp_test"
        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4o-mini"
        assert config.llm_api_key == "sk-test"
        assert config.discord_webhook_url == "https://discord.com/api/webhooks/test"
        assert config.max_repos == 100
        assert config.readme_max_chars == 500
        assert config.batch_size == 10
        assert config.cache_days == 30
    finally:
        config_path.unlink()


def test_load_config_file_not_found():
    """Config raises clear error when file missing."""
    import pytest

    with pytest.raises(FileNotFoundError, match="Config file not found"):
        load_config(Path("/nonexistent/config.json"))


def test_load_config_with_keywords():
    """Config loads keywords list from github section."""
    config_data = {
        "github": {"token": "ghp_test", "keywords": ["kubernetes", "devops", "terraform"]},
        "llm": {"provider": "openai", "model": "gpt-4o-mini", "api_key": "sk-test"},
        "discord": {"webhook_url": "https://discord.com/api/webhooks/test"},
        "settings": {"max_repos": 100, "readme_max_chars": 500, "batch_size": 10, "cache_days": 30}
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        config_path = Path(f.name)

    try:
        config = load_config(config_path)

        assert config.keywords == ["kubernetes", "devops", "terraform"]
    finally:
        config_path.unlink()


def test_load_config_keywords_defaults_to_empty():
    """Config defaults to empty keywords list when not provided."""
    config_data = {
        "github": {"token": "ghp_test"},
        "llm": {"provider": "openai", "model": "gpt-4o-mini", "api_key": "sk-test"},
        "discord": {"webhook_url": "https://discord.com/api/webhooks/test"},
        "settings": {"max_repos": 100, "readme_max_chars": 500, "batch_size": 10, "cache_days": 30}
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        config_path = Path(f.name)

    try:
        config = load_config(config_path)

        assert config.keywords == []
    finally:
        config_path.unlink()
