# src/graphrag_api_service/providers/ollama_provider.py
# Ollama LLM provider implementation for GraphRAG API Service
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Ollama provider implementation for local LLM inference."""

import time
from typing import Any

from ollama import AsyncClient

from .base import EmbeddingResponse, GraphRAGLLM, LLMResponse, ProviderHealth


class OllamaGraphRAGLLM(GraphRAGLLM):
    """Ollama provider implementation for local LLM inference.

    This provider integrates with Ollama for privacy-focused local deployment
    using Gemma3:4b for text generation and nomic-embed-text for embeddings.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize Ollama provider with configuration.

        Args:
            config: Configuration containing base_url, llm_model, embedding_model
        """
        super().__init__(config)
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.llm_model = config.get("llm_model", "gemma:4b")
        self.embedding_model = config.get("embedding_model", "nomic-embed-text")

        # Initialize async client
        self.client = AsyncClient(host=self.base_url)

    def _get_provider_name(self) -> str:
        """Get the provider name identifier.

        Returns:
            String identifier for the provider
        """
        return "ollama"

    async def generate_text(
        self, prompt: str, max_tokens: int = 1500, temperature: float = 0.1, **kwargs: Any
    ) -> LLMResponse:
        """Generate text response using Ollama LLM.

        Args:
            prompt: Input prompt for text generation
            max_tokens: Maximum tokens to generate
            temperature: Generation temperature (0.0-1.0)
            **kwargs: Additional Ollama-specific parameters

        Returns:
            LLMResponse containing generated text and metadata

        Raises:
            Exception: If generation fails or Ollama is unavailable
        """
        try:
            # Prepare generation options
            options = {"temperature": temperature, "num_predict": max_tokens, **kwargs}

            # Make the API call
            response = await self.client.generate(
                model=self.llm_model, prompt=prompt, options=options, stream=False
            )

            # Extract response data
            content = response.get("response", "")
            tokens_used = response.get("eval_count", 0) + response.get("prompt_eval_count", 0)

            return LLMResponse(
                content=content,
                tokens_used=tokens_used,
                model=self.llm_model,
                provider=self.provider_name,
                metadata={
                    "eval_duration": response.get("eval_duration", 0),
                    "prompt_eval_duration": response.get("prompt_eval_duration", 0),
                    "total_duration": response.get("total_duration", 0),
                },
            )

        except Exception as e:
            raise Exception(f"Ollama text generation failed: {str(e)}") from e

    async def generate_embeddings(self, texts: list[str], **kwargs: Any) -> list[EmbeddingResponse]:
        """Generate embeddings using Ollama embedding model.

        Args:
            texts: List of texts to embed
            **kwargs: Additional Ollama-specific parameters

        Returns:
            List of EmbeddingResponse objects with embeddings

        Raises:
            Exception: If embedding generation fails
        """
        try:
            embeddings = []

            for text in texts:
                response = await self.client.embeddings(
                    model=self.embedding_model, prompt=text, **kwargs
                )

                embedding_vector = response.get("embedding", [])

                embeddings.append(
                    EmbeddingResponse(
                        embeddings=embedding_vector,
                        tokens_used=len(text.split()),  # Rough estimate
                        model=self.embedding_model,
                        provider=self.provider_name,
                        dimensions=len(embedding_vector),
                    )
                )

            return embeddings

        except Exception as e:
            raise Exception(f"Ollama embedding generation failed: {str(e)}") from e

    async def health_check(self) -> ProviderHealth:
        """Check the health of the Ollama connection.

        Returns:
            ProviderHealth object with status and details
        """
        try:
            start_time = time.time()

            # Test connection with a simple list models call
            models = await self.client.list()

            latency_ms = (time.time() - start_time) * 1000

            # Check if our required models are available
            # Handle the ListResponse object from Ollama client
            if hasattr(models, "models"):
                available_models = [
                    model.model for model in models.models if model.model is not None
                ]
            else:
                # Fallback for dictionary response
                available_models = [model.get("name", "") for model in models.get("models", [])]
            llm_available = any(self.llm_model in model for model in available_models if model)
            embed_available = any(
                self.embedding_model in model for model in available_models if model
            )

            if not llm_available or not embed_available:
                missing_models = []
                if not llm_available:
                    missing_models.append(self.llm_model)
                if not embed_available:
                    missing_models.append(self.embedding_model)

                return ProviderHealth(
                    healthy=False,
                    provider=self.provider_name,
                    message=f"Required models not available: {', '.join(missing_models)}",
                    latency_ms=latency_ms,
                    model_info={
                        "available_models": available_models,
                        "required_llm": self.llm_model,
                        "required_embedding": self.embedding_model,
                        "llm_available": llm_available,
                        "embed_available": embed_available,
                    },
                )

            return ProviderHealth(
                healthy=True,
                provider=self.provider_name,
                message="Ollama connection healthy, required models available",
                latency_ms=latency_ms,
                model_info={
                    "available_models": available_models,
                    "llm_model": self.llm_model,
                    "embedding_model": self.embedding_model,
                    "base_url": self.base_url,
                },
            )

        except Exception as e:
            return ProviderHealth(
                healthy=False,
                provider=self.provider_name,
                message=f"Ollama connection failed: {str(e)}",
                latency_ms=0.0,
                model_info={
                    "base_url": self.base_url,
                    "error": str(e),
                },
            )

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the current Ollama model configuration.

        Returns:
            Dictionary containing model information
        """
        # Extract model info from model name
        model_parts = self.llm_model.split(":")
        model_name = model_parts[0]
        model_version = model_parts[1] if len(model_parts) > 1 else "latest"

        # Estimate max tokens based on common Ollama models
        max_tokens_map = {
            "gemma": 8192,
            "llama": 4096,
            "mistral": 8192,
            "codellama": 16384,
            "phi": 2048,
        }

        max_tokens = 4096  # Default
        for model_prefix, tokens in max_tokens_map.items():
            if model_name.startswith(model_prefix):
                max_tokens = tokens
                break

        return {
            "name": self.llm_model,
            "version": model_version,
            "max_tokens": max_tokens,
            "provider": self.provider_name,
            "embedding_model": self.embedding_model,
            "embedding_dimensions": 768,  # nomic-embed-text dimensions
            "supports_streaming": True,
            "supports_function_calling": False,  # Most Ollama models don't support function calling
            "context_window": max_tokens * 2,  # Estimate context window
            "base_url": self.base_url,
            "model_family": model_name,
        }
