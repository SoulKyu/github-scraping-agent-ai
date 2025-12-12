"""LLM provider factory."""

from src.llm.base import LLMProvider
from src.llm.openai_provider import OpenAIProvider
from src.llm.anthropic_provider import AnthropicProvider
from src.llm.google_provider import GoogleProvider


def create_provider(provider_name: str, model: str, api_key: str) -> LLMProvider:
    """Create an LLM provider by name.

    Args:
        provider_name: One of "openai", "anthropic", "google"
        model: Model name to use
        api_key: API key for the provider

    Returns:
        Configured LLM provider

    Raises:
        ValueError: If provider_name is unknown
    """
    providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "google": GoogleProvider,
    }

    if provider_name not in providers:
        raise ValueError(f"Unknown provider: {provider_name}. Available: {list(providers.keys())}")

    return providers[provider_name](api_key=api_key, model=model)
