"""Discord webhook client."""

import httpx

from src.github import Repository
from src.llm.base import EvaluationResult


def format_repo_embed(repo: Repository, result: EvaluationResult) -> dict:
    """Format a repository as a Discord embed."""
    topics_str = ", ".join(repo.topics) if repo.topics else "none"

    description = f"⭐ {repo.stars} stars | 🗂️ {repo.language or 'Unknown'}\n\n"
    description += f"{repo.description}\n\n" if repo.description else ""
    description += f"**Topics:** {topics_str}\n\n"
    description += f"💡 *{result.reason}*"

    return {
        "title": repo.full_name,
        "url": repo.url,
        "description": description,
        "color": 0x238636,  # GitHub green
    }


class DiscordClient:
    """Client for Discord webhooks."""

    def __init__(self, webhook_url: str, transport: httpx.BaseTransport | None = None):
        """Initialize with webhook URL."""
        self.webhook_url = webhook_url
        self._client = httpx.Client(transport=transport, timeout=30.0)

    def send_repos(
        self,
        repos_with_results: list[tuple[Repository, EvaluationResult]],
        batch_size: int = 10,
    ) -> None:
        """Send repositories to Discord in batches."""
        for i in range(0, len(repos_with_results), batch_size):
            batch = repos_with_results[i:i + batch_size]
            embeds = [format_repo_embed(repo, result) for repo, result in batch]

            payload = {"embeds": embeds}

            response = self._client.post(self.webhook_url, json=payload)
            response.raise_for_status()

    def send_summary(self, total_found: int, total_processed: int) -> None:
        """Send a summary message."""
        payload = {
            "content": f"🔍 **GitHub Discovery Report**\nProcessed {total_processed} repos, found {total_found} interesting projects."
        }
        response = self._client.post(self.webhook_url, json=payload)
        response.raise_for_status()

    def close(self):
        """Close the HTTP client."""
        self._client.close()
