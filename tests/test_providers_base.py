# tests/test_providers_base.py
# Unit tests for provider base classes
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Tests for provider base classes and factory."""

from unittest.mock import AsyncMock

import pytest

from src.graphrag_api_service.config import LLMProvider, Settings
from src.graphrag_api_service.providers.base import (
    EmbeddingResponse,
    GraphRAGLLM,
    LLMResponse,
    ProviderHealth,
)
from src.graphrag_api_service.providers.factory import LLMProviderFactory


class MockGraphRAGLLM(GraphRAGLLM):
    """Mock implementation for testing."""

    def _get_provider_name(self) -> str:
        return "mock"

    async def generate_text(
        self, prompt: str, max_tokens: int = 1500, temperature: float = 0.1, **kwargs
    ) -> LLMResponse:
        return LLMResponse(
            content="Mock response", tokens_used=10, model="mock-model", provider="mock"
        )

    async def generate_embeddings(self, texts: list[str], **kwargs) -> list[EmbeddingResponse]:
        return [
            EmbeddingResponse(
                embeddings=[0.1, 0.2, 0.3],
                tokens_used=5,
                model="mock-embed",
                provider="mock",
                dimensions=3,
            )
            for _ in texts
        ]

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            healthy=True, provider="mock", message="Mock provider healthy", latency_ms=10.0
        )


class TestGraphRAGLLM:
    """Test the abstract base class functionality."""

    def test_initialization(self):
        """Test provider initialization with config."""
        config = {"test_key": "test_value", "api_key": "secret"}
        provider = MockGraphRAGLLM(config)

        assert provider.config == config
        assert provider.provider_name == "mock"

    def test_get_configuration_info(self):
        """Test configuration info masking of sensitive data."""
        config = {"base_url": "http://localhost", "api_key": "secret", "token": "secret_token"}
        provider = MockGraphRAGLLM(config)

        info = provider.get_configuration_info()

        assert info["provider"] == "mock"
        assert info["config"]["base_url"] == "http://localhost"
        assert info["config"]["api_key"] == "***"
        assert info["config"]["token"] == "***"

    @pytest.mark.asyncio
    async def test_validate_connection_success(self):
        """Test successful connection validation."""
        provider = MockGraphRAGLLM({})

        is_valid = await provider.validate_connection()

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_connection_failure(self):
        """Test failed connection validation."""
        provider = MockGraphRAGLLM({})
        provider.health_check = AsyncMock(side_effect=Exception("Connection failed"))

        is_valid = await provider.validate_connection()

        assert is_valid is False


class TestLLMProviderFactory:
    """Test the provider factory functionality."""

    def setup_method(self):
        """Setup test environment."""
        # Clear registered providers before each test
        LLMProviderFactory._providers.clear()

    def test_register_provider(self):
        """Test provider registration."""
        LLMProviderFactory.register_provider(LLMProvider.OLLAMA, MockGraphRAGLLM)

        assert LLMProvider.OLLAMA in LLMProviderFactory._providers
        assert LLMProviderFactory._providers[LLMProvider.OLLAMA] == MockGraphRAGLLM

    def test_create_provider_ollama(self):
        """Test creating Ollama provider instance."""
        LLMProviderFactory.register_provider(LLMProvider.OLLAMA, MockGraphRAGLLM)

        settings = Settings(
            llm_provider=LLMProvider.OLLAMA,
            ollama_base_url="http://localhost:11434",
            ollama_llm_model="gemma:4b",
            ollama_embedding_model="nomic-embed-text",
        )

        provider = LLMProviderFactory.create_provider(settings)

        assert isinstance(provider, MockGraphRAGLLM)
        assert provider.config["base_url"] == "http://localhost:11434"
        assert provider.config["llm_model"] == "gemma:4b"
        assert provider.config["embedding_model"] == "nomic-embed-text"

    def test_create_provider_google_gemini(self):
        """Test creating Google Gemini provider instance."""
        LLMProviderFactory.register_provider(LLMProvider.GOOGLE_GEMINI, MockGraphRAGLLM)

        settings = Settings(
            llm_provider=LLMProvider.GOOGLE_GEMINI,
            google_api_key="test_key",
            google_project_id="test_project",
            google_location="us-central1",
            gemini_model="gemini-2.5-flash",
            gemini_embedding_model="text-embedding-004",
        )

        provider = LLMProviderFactory.create_provider(settings)

        assert isinstance(provider, MockGraphRAGLLM)
        assert provider.config["api_key"] == "test_key"
        assert provider.config["project_id"] == "test_project"
        assert provider.config["location"] == "us-central1"
        assert provider.config["llm_model"] == "gemini-2.5-flash"
        assert provider.config["embedding_model"] == "text-embedding-004"

    def test_create_provider_unsupported(self):
        """Test error handling for unsupported provider."""
        settings = Settings(llm_provider=LLMProvider.OLLAMA)

        with pytest.raises(ValueError, match="Unsupported provider type"):
            LLMProviderFactory.create_provider(settings)

    def test_get_supported_providers(self):
        """Test getting list of supported providers."""
        LLMProviderFactory.register_provider(LLMProvider.OLLAMA, MockGraphRAGLLM)
        LLMProviderFactory.register_provider(LLMProvider.GOOGLE_GEMINI, MockGraphRAGLLM)

        supported = LLMProviderFactory.get_supported_providers()

        assert "ollama" in supported
        assert "google_gemini" in supported
        assert len(supported) == 2

    def test_is_provider_supported(self):
        """Test checking if provider is supported."""
        LLMProviderFactory.register_provider(LLMProvider.OLLAMA, MockGraphRAGLLM)

        assert LLMProviderFactory.is_provider_supported(LLMProvider.OLLAMA) is True
        assert LLMProviderFactory.is_provider_supported(LLMProvider.GOOGLE_GEMINI) is False
