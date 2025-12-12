"""Google Generative AI LLM provider."""

import json

import google.generativeai as genai

from src.github import Repository
from src.llm.base import EvaluationResult, LLMProvider


PROMPT_TEMPLATE = """You are a GitHub project evaluator. Given a user's interests and a project's metadata, decide if this project would interest them.

Respond ONLY with valid JSON in this exact format:
{{"interested": true, "reason": "one sentence explanation"}}

or

{{"interested": false, "reason": "one sentence explanation"}}

User interests:
{prompt}

Project:
- Name: {full_name}
- Description: {description}
- Language: {language}
- Topics: {topics}
- Stars: {stars}
- README excerpt: {readme}"""


class GoogleProvider(LLMProvider):
    """Google Generative AI-based LLM provider."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        """Initialize with API key and model."""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    def evaluate(self, repo: Repository, prompt: str) -> EvaluationResult:
        """Evaluate repository using Google Generative AI."""
        full_prompt = PROMPT_TEMPLATE.format(
            prompt=prompt,
            full_name=repo.full_name,
            description=repo.description,
            language=repo.language,
            topics=', '.join(repo.topics) if repo.topics else 'none',
            stars=repo.stars,
            readme=repo.readme[:500] if repo.readme else 'none',
        )

        content = None
        try:
            response = self.model.generate_content(full_prompt)
            content = response.text

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
