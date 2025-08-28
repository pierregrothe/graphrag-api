# src/graphrag_api_service/providers/base.py
# Abstract base class for GraphRAG LLM providers
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Abstract base class for GraphRAG LLM provider implementations."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class LLMResponse(BaseModel):
    """Response model for LLM operations."""

    content: str
    tokens_used: int = 0
    model: str = ""
    provider: str = ""
    metadata: dict[str, Any] = {}


class EmbeddingResponse(BaseModel):
    """Response model for embedding operations."""

    embeddings: list[float]
    tokens_used: int = 0
    model: str = ""
    provider: str = ""
    dimensions: int = 0


class ProviderHealth(BaseModel):
    """Health status model for provider connections."""

    healthy: bool
    provider: str
    message: str = ""
    latency_ms: float = 0.0
    model_info: dict[str, Any] = {}


class GraphRAGLLM(ABC):
    """Abstract base class for GraphRAG LLM provider implementations.

    This class defines the interface that all LLM providers must implement
    to work with the GraphRAG API service. It provides methods for text
    generation, embeddings, and health checking.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the LLM provider with configuration.

        Args:
            config: Provider-specific configuration dictionary
        """
        self.config = config
        self.provider_name = self._get_provider_name()

    @abstractmethod
    def _get_provider_name(self) -> str:
        """Get the provider name identifier.

        Returns:
            String identifier for the provider
        """

    @abstractmethod
    async def generate_text(
        self, prompt: str, max_tokens: int = 1500, temperature: float = 0.1, **kwargs: Any
    ) -> LLMResponse:
        """Generate text response from the LLM.

        Args:
            prompt: Input prompt for text generation
            max_tokens: Maximum tokens to generate
            temperature: Generation temperature (0.0-1.0)
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse containing generated text and metadata

        Raises:
            Exception: If generation fails
        """

    @abstractmethod
    async def generate_embeddings(self, texts: list[str], **kwargs: Any) -> list[EmbeddingResponse]:
        """Generate embeddings for input texts.

        Args:
            texts: List of texts to embed
            **kwargs: Additional provider-specific parameters

        Returns:
            List of EmbeddingResponse objects with embeddings

        Raises:
            Exception: If embedding generation fails
        """

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Check the health of the provider connection.

        Returns:
            ProviderHealth object with status and details
        """

    async def validate_connection(self) -> bool:
        """Validate that the provider connection is working.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            health = await self.health_check()
            return health.healthy
        except Exception:
            return False

    def get_configuration_info(self) -> dict[str, Any]:
        """Get current provider configuration information.

        Returns:
            Dictionary with provider configuration details
        """
        return {
            "provider": self.provider_name,
            "config": {
                k: "***" if "key" in k.lower() or "token" in k.lower() else v
                for k, v in self.config.items()
            },
        }
