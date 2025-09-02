# tests/unit/test_providers.py
# Unit tests for LLM providers module
# Author: Pierre Grothé
# Creation Date: 2025-09-02

"""
Module: LLM Providers
Tests: Provider factory, Ollama provider, Gemini provider, base abstractions
Coverage: Provider creation, validation, text generation, embeddings
Dependencies: None (mocked external calls)
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graphrag_api_service.config import Settings
from src.graphrag_api_service.providers.base import GraphRAGLLM
from src.graphrag_api_service.providers.factory import LLMProviderFactory


class TestLLMProviderFactory:
    """Test LLM provider factory functionality."""

    def test_create_ollama_provider_returns_correct_type(self):
        """Test creating Ollama provider returns correct type."""
        from src.graphrag_api_service.providers.registry import register_providers
        
        # Register providers first
        register_providers()
        
        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama"}):
            settings = Settings()
            provider = LLMProviderFactory.create_provider(settings)
            
            assert provider is not None
            assert isinstance(provider, GraphRAGLLM)
            assert provider.__class__.__name__ == "OllamaProvider"

    def test_create_gemini_provider_returns_correct_type(self):
        """Test creating Gemini provider returns correct type."""
        from src.graphrag_api_service.providers.registry import register_providers
        
        # Register providers first
        register_providers()
        
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "google_gemini",
                "GOOGLE_API_KEY": "test_key",
                "GOOGLE_PROJECT_ID": "test_project",
            },
        ):
            settings = Settings()
            provider = LLMProviderFactory.create_provider(settings)
            
            assert provider is not None
            assert isinstance(provider, GraphRAGLLM)
            assert provider.__class__.__name__ == "GeminiProvider"

    def test_create_invalid_provider_raises_error(self):
        """Test creating invalid provider raises error."""
        settings = MagicMock()
        settings.llm_provider.value = "invalid_provider"
        
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            LLMProviderFactory.create_provider(settings)


class TestOllamaProvider:
    """Test Ollama provider functionality."""

    @pytest.fixture
    def ollama_provider(self):
        """Create an Ollama provider instance for testing."""
        from src.graphrag_api_service.providers.ollama_provider import OllamaProvider
        
        settings = Settings()
        return OllamaProvider(settings)

    @pytest.mark.asyncio
    async def test_validate_connection_success(self, ollama_provider):
        """Test successful connection validation."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.return_value = AsyncMock(
                status_code=200,
                json=AsyncMock(return_value={"status": "ok"}),
            )
            
            result = await ollama_provider.validate_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_connection_failure(self, ollama_provider):
        """Test failed connection validation."""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = Exception("Connection failed")
            
            result = await ollama_provider.validate_connection()
            assert result is False

    @pytest.mark.asyncio
    async def test_generate_text_returns_response(self, ollama_provider):
        """Test text generation returns response."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=AsyncMock(return_value={"response": "Generated text"}),
            )
            
            result = await ollama_provider.generate_text("Test prompt")
            assert result == "Generated text"

    @pytest.mark.asyncio
    async def test_generate_embeddings_returns_vectors(self, ollama_provider):
        """Test embedding generation returns vectors."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=AsyncMock(return_value={"embedding": [0.1, 0.2, 0.3]}),
            )
            
            result = await ollama_provider.generate_embeddings(["Test text"])
            assert len(result) == 1
            assert len(result[0]) == 3


class TestGeminiProvider:
    """Test Google Gemini provider functionality."""

    @pytest.fixture
    def gemini_provider(self):
        """Create a Gemini provider instance for testing."""
        from src.graphrag_api_service.providers.gemini_provider import GeminiProvider
        
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "google_gemini",
                "GOOGLE_API_KEY": "test_key",
                "GOOGLE_PROJECT_ID": "test_project",
            },
        ):
            settings = Settings()
            return GeminiProvider(settings)

    @pytest.mark.asyncio
    async def test_validate_connection_with_api_key(self, gemini_provider):
        """Test connection validation with API key."""
        with patch.object(gemini_provider, "_validate_with_api_key") as mock_validate:
            mock_validate.return_value = True
            
            result = await gemini_provider.validate_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_generate_text_with_gemini_model(self, gemini_provider):
        """Test text generation with Gemini model."""
        with patch.object(gemini_provider.model, "generate_content_async") as mock_generate:
            mock_response = MagicMock()
            mock_response.text = "Generated response"
            mock_generate.return_value = mock_response
            
            result = await gemini_provider.generate_text("Test prompt")
            assert result == "Generated response"

    def test_get_model_info_returns_correct_data(self, gemini_provider):
        """Test getting model info returns correct data."""
        info = gemini_provider.get_model_info()
        
        assert "name" in info
        assert "version" in info
        assert "max_tokens" in info
        assert info["name"] == "gemini-2.5-flash"