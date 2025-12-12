"""Configuration loading and validation."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Application configuration."""

    github_token: str
    llm_provider: str
    llm_model: str
    llm_api_key: str
    discord_webhook_url: str
    max_repos: int
    readme_max_chars: int
    batch_size: int
    cache_days: int
    keywords: list[str]


def load_config(config_path: Path) -> Config:
    """Load configuration from JSON file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        data = json.load(f)

    return Config(
        github_token=data["github"]["token"],
        llm_provider=data["llm"]["provider"],
        llm_model=data["llm"]["model"],
        llm_api_key=data["llm"]["api_key"],
        discord_webhook_url=data["discord"]["webhook_url"],
        max_repos=data["settings"]["max_repos"],
        readme_max_chars=data["settings"]["readme_max_chars"],
        batch_size=data["settings"]["batch_size"],
        cache_days=data["settings"]["cache_days"],
        keywords=data["github"].get("keywords", []),
    )
