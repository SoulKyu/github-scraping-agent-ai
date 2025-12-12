"""Tests for prompt loading."""

import tempfile
from pathlib import Path

from src.prompt import load_prompt


def test_load_prompt_from_file():
    """Prompt loads from markdown file."""
    prompt_content = """I'm interested in:
- AI/ML tools
- Python libraries

I'm NOT interested in:
- Crypto projects
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(prompt_content)
        prompt_path = Path(f.name)

    try:
        prompt = load_prompt(prompt_path)
        assert "AI/ML tools" in prompt
        assert "Crypto projects" in prompt
    finally:
        prompt_path.unlink()


def test_load_prompt_file_not_found():
    """Prompt raises clear error when file missing."""
    import pytest

    with pytest.raises(FileNotFoundError, match="Prompt file not found"):
        load_prompt(Path("/nonexistent/prompt.md"))
