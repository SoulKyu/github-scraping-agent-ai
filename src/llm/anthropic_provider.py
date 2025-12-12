"""Anthropic LLM provider."""

import json

import anthropic

from src.github import Repository
from src.llm.base import EvaluationResult, LLMProvider


SYSTEM_PROMPT = """You are a GitHub project evaluator. Given a user's interests and a project's metadata, decide if this project would interest them.

Respond ONLY with valid JSON in this exact format:
{"interested": true, "reason": "one sentence explanation"}

or

{"interested": false, "reason": "one sentence explanation"}"""


class AnthropicProvider(LLMProvider):
    """Anthropic-based LLM provider."""

    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        """Initialize with API key and model."""
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def evaluate(self, repo: Repository, prompt: str) -> EvaluationResult:
        """Evaluate repository using Anthropic."""
        user_message = f"""User interests:
{prompt}

Project:
- Name: {repo.full_name}
- Description: {repo.description}
- Language: {repo.language}
- Topics: {', '.join(repo.topics) if repo.topics else 'none'}
- Stars: {repo.stars}
- README excerpt: {repo.readme[:500] if repo.readme else 'none'}"""

        content = None
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=150,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )

            content = response.content[0].text

            # Try to extract JSON from response (handle markdown code blocks)
            if content:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)

            return EvaluationResult(
                interested=data.get("interested", False),
                reason=data.get("reason", "No reason provided"),
            )
        except json.JSONDecodeError:
            raw = content[:200] if content else "empty response"
            return EvaluationResult(interested=False, reason=f"Failed to parse LLM response: {raw}")
        except Exception as e:
            return EvaluationResult(interested=False, reason=f"Error: {str(e)}")
