# src/graphrag_api_service/providers/factory.py
# Factory for creating LLM provider instances
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Factory pattern implementation for LLM provider creation."""


from ..config import LLMProvider, Settings
from .base import GraphRAGLLM


class LLMProviderFactory:
    """Factory class for creating LLM provider instances.

    This factory uses the configuration settings to determine which
    provider to instantiate and provides a unified interface for
    creating provider instances.
    """

    _providers: dict[LLMProvider, type[GraphRAGLLM]] = {}

    @classmethod
    def register_provider(
        cls, provider_type: LLMProvider, provider_class: type[GraphRAGLLM]
    ) -> None:
        """Register a provider class for a specific provider type.

        Args:
            provider_type: The LLMProvider enum value
            provider_class: The GraphRAGLLM implementation class
        """
        cls._providers[provider_type] = provider_class

    @classmethod
    def create_provider(cls, settings: Settings) -> GraphRAGLLM:
        """Create a provider instance based on settings.

        Args:
            settings: Application settings containing provider configuration

        Returns:
            Configured GraphRAGLLM instance

        Raises:
            ValueError: If provider type is not supported
            ImportError: If provider dependencies are missing
        """
        provider_type = settings.llm_provider

        if provider_type not in cls._providers:
            raise ValueError(f"Unsupported provider type: {provider_type}")

        provider_class = cls._providers[provider_type]
        provider_config = cls._build_provider_config(settings)

        try:
            return provider_class(provider_config)
        except ImportError as e:
            raise ImportError(
                f"Failed to import dependencies for {provider_type}. "
                f"Please ensure required packages are installed: {e}"
            ) from e

    @classmethod
    def _build_provider_config(cls, settings: Settings) -> dict[str, str | None]:
        """Build provider-specific configuration from settings.

        Args:
            settings: Application settings

        Returns:
            Configuration dictionary for the provider
        """
        if settings.llm_provider == LLMProvider.OLLAMA:
            return {
                "base_url": settings.ollama_base_url,
                "llm_model": settings.ollama_llm_model,
                "embedding_model": settings.ollama_embedding_model,
            }
        elif settings.llm_provider == LLMProvider.GOOGLE_GEMINI:
            return {
                "api_key": settings.google_api_key,
                "project_id": settings.google_project_id,
                "location": settings.google_location,
                "use_vertex_ai": settings.google_cloud_use_vertex_ai,
                "vertex_ai_endpoint": settings.vertex_ai_endpoint,
                "vertex_ai_location": settings.vertex_ai_location,
                "llm_model": settings.gemini_model,
                "embedding_model": settings.gemini_embedding_model,
            }
        else:
            return {}

    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """Get list of supported provider names.

        Returns:
            List of supported provider string identifiers
        """
        return [provider.value for provider in cls._providers.keys()]

    @classmethod
    def is_provider_supported(cls, provider_type: LLMProvider) -> bool:
        """Check if a provider type is supported.

        Args:
            provider_type: The provider type to check

        Returns:
            True if provider is supported, False otherwise
        """
        return provider_type in cls._providers
