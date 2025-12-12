"""OpenAI LLM provider."""

import json

import openai

from src.github import Repository
from src.llm.base import EvaluationResult, LLMProvider


SYSTEM_PROMPT = """You are a GitHub project evaluator. Given a user's interests and a project's metadata, decide if this project would interest them.

Respond ONLY with valid JSON in this exact format:
{"interested": true, "reason": "one sentence explanation"}

or

{"interested": false, "reason": "one sentence explanation"}"""


class OpenAIProvider(LLMProvider):
    """OpenAI-based LLM provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """Initialize with API key and model."""
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def evaluate(self, repo: Repository, prompt: str) -> EvaluationResult:
        """Evaluate repository using OpenAI."""
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
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.1,
                max_tokens=150,
            )

            content = response.choices[0].message.content

            # Try to extract JSON from response (handle markdown code blocks)
            if content:
                # Strip markdown code blocks if present
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
