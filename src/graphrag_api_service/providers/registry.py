# src/graphrag_api_service/providers/registry.py
# Provider registration for LLM factory
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Provider registration module for automatic factory setup."""

from ..config import LLMProvider
from .factory import LLMProviderFactory
from .gemini_provider import GeminiGraphRAGLLM
from .ollama_provider import OllamaGraphRAGLLM


def register_providers():
    """Register all available providers with the factory.

    This function should be called during application startup to ensure
    all providers are available for use.
    """
    # Register Ollama provider
    LLMProviderFactory.register_provider(LLMProvider.OLLAMA, OllamaGraphRAGLLM)

    # Register Google Gemini provider
    LLMProviderFactory.register_provider(LLMProvider.GOOGLE_GEMINI, GeminiGraphRAGLLM)


def get_registered_providers() -> list[str]:
    """Get list of all registered provider names.

    Returns:
        List of registered provider string identifiers
    """
    return LLMProviderFactory.get_supported_providers()
