"""Repository cache for deduplication."""

import json
from datetime import date, timedelta
from pathlib import Path


class RepoCache:
    """Cache for tracking seen repositories."""

    def __init__(self, cache_path: Path, cache_days: int = 30):
        """Initialize cache from file."""
        self.cache_path = cache_path
        self.cache_days = cache_days
        self._data: dict[str, str] = {}

        if cache_path.exists():
            try:
                self._data = json.loads(cache_path.read_text())
            except json.JSONDecodeError:
                self._data = {}

    def is_seen(self, full_name: str) -> bool:
        """Check if a repository has been seen."""
        return full_name in self._data

    def mark_seen(self, full_name: str) -> None:
        """Mark a repository as seen today."""
        self._data[full_name] = date.today().isoformat()

    def prune(self) -> None:
        """Remove entries older than cache_days."""
        cutoff = date.today() - timedelta(days=self.cache_days)
        self._data = {
            name: seen_date
            for name, seen_date in self._data.items()
            if date.fromisoformat(seen_date) >= cutoff
        }

    def save(self) -> None:
        """Save cache to file."""
        self.cache_path.write_text(json.dumps(self._data, indent=2))
