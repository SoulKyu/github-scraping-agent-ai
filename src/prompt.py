"""Prompt file loading."""

from pathlib import Path


def load_prompt(prompt_path: Path) -> str:
    """Load user interests prompt from markdown file."""
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    return prompt_path.read_text().strip()
