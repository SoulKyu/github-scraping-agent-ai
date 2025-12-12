"""LLM provider interface and base types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.github import Repository


@dataclass
class EvaluationResult:
    """Result of evaluating a repository."""

    interested: bool
    reason: str


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def evaluate(self, repo: Repository, prompt: str) -> EvaluationResult:
        """Evaluate if a repository matches user interests.

        Args:
            repo: Repository to evaluate
            prompt: User's interests prompt

        Returns:
            EvaluationResult with interested flag and reason
        """
        pass
