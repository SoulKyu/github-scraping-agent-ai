"""Tests for LLM provider interface."""

from src.llm.base import EvaluationResult


def test_evaluation_result_interested():
    """EvaluationResult stores interested=True with reason."""
    result = EvaluationResult(interested=True, reason="Matches AI interest")

    assert result.interested is True
    assert result.reason == "Matches AI interest"


def test_evaluation_result_not_interested():
    """EvaluationResult stores interested=False with reason."""
    result = EvaluationResult(interested=False, reason="Crypto project")

    assert result.interested is False
    assert result.reason == "Crypto project"
