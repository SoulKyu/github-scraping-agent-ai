"""Tests for repository cache."""

import json
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pytest

from src.cache import RepoCache


def test_cache_is_seen_empty():
    """Cache reports repos as not seen when empty."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        cache_path = Path(f.name)

    try:
        cache = RepoCache(cache_path)
        assert cache.is_seen("owner/repo") is False
    finally:
        cache_path.unlink(missing_ok=True)


def test_cache_mark_seen():
    """Cache marks repos as seen."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        cache_path = Path(f.name)

    try:
        cache = RepoCache(cache_path)
        cache.mark_seen("owner/repo")
        cache.save()

        # Reload and check
        cache2 = RepoCache(cache_path)
        assert cache2.is_seen("owner/repo") is True
        assert cache2.is_seen("other/repo") is False
    finally:
        cache_path.unlink(missing_ok=True)


def test_cache_prune_old_entries():
    """Cache prunes entries older than cache_days."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        cache_path = Path(f.name)

    try:
        # Pre-populate with old entry
        old_date = (date.today() - timedelta(days=40)).isoformat()
        recent_date = (date.today() - timedelta(days=5)).isoformat()

        cache_path.write_text(json.dumps({
            "old/repo": old_date,
            "recent/repo": recent_date,
        }))

        cache = RepoCache(cache_path, cache_days=30)
        cache.prune()
        cache.save()

        # Reload and check
        cache2 = RepoCache(cache_path)
        assert cache2.is_seen("old/repo") is False
        assert cache2.is_seen("recent/repo") is True
    finally:
        cache_path.unlink(missing_ok=True)
