# tests/test_ollama_provider.py
# Unit tests for Ollama provider implementation
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Tests for Ollama provider implementation."""

from unittest.mock import AsyncMock, patch

import pytest

from src.graphrag_api_service.providers.base import EmbeddingResponse, LLMResponse, ProviderHealth
from src.graphrag_api_service.providers.ollama_provider import OllamaGraphRAGLLM


class TestOllamaGraphRAGLLM:
    """Test the Ollama provider implementation."""

    def setup_method(self):
        """Setup test environment."""
        self.config = {
            "base_url": "http://localhost:11434",
            "llm_model": "gemma:4b",
            "embedding_model": "nomic-embed-text",
        }
        self.provider = OllamaGraphRAGLLM(self.config)

    def test_initialization(self):
        """Test provider initialization."""
        assert self.provider.base_url == "http://localhost:11434"
        assert self.provider.llm_model == "gemma:4b"
        assert self.provider.embedding_model == "nomic-embed-text"
        assert self.provider.provider_name == "ollama"

    def test_initialization_with_defaults(self):
        """Test provider initialization with default values."""
        provider = OllamaGraphRAGLLM({})

        assert provider.base_url == "http://localhost:11434"
        assert provider.llm_model == "gemma:4b"
        assert provider.embedding_model == "nomic-embed-text"

    def test_get_provider_name(self):
        """Test provider name method."""
        assert self.provider._get_provider_name() == "ollama"

    @pytest.mark.asyncio
    async def test_generate_text_success(self):
        """Test successful text generation."""
        mock_response = {
            "response": "This is a test response",
            "eval_count": 20,
            "prompt_eval_count": 10,
            "eval_duration": 1000000,
            "prompt_eval_duration": 500000,
            "total_duration": 1500000,
        }

        with patch.object(
            self.provider.client, "generate", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = mock_response

            result = await self.provider.generate_text("Test prompt")

            assert isinstance(result, LLMResponse)
            assert result.content == "This is a test response"
            assert result.tokens_used == 30
            assert result.model == "gemma:4b"
            assert result.provider == "ollama"
            assert result.metadata["eval_duration"] == 1000000

            mock_generate.assert_called_once_with(
                model="gemma:4b",
                prompt="Test prompt",
                options={"temperature": 0.1, "num_predict": 1500},
                stream=False,
            )

    @pytest.mark.asyncio
    async def test_generate_text_with_custom_params(self):
        """Test text generation with custom parameters."""
        mock_response = {"response": "Custom response", "eval_count": 15, "prompt_eval_count": 8}

        with patch.object(
            self.provider.client, "generate", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = mock_response

            result = await self.provider.generate_text(
                "Custom prompt", max_tokens=1000, temperature=0.7, top_k=40
            )

            assert result.content == "Custom response"
            assert result.tokens_used == 23

            mock_generate.assert_called_once_with(
                model="gemma:4b",
                prompt="Custom prompt",
                options={"temperature": 0.7, "num_predict": 1000, "top_k": 40},
                stream=False,
            )

    @pytest.mark.asyncio
    async def test_generate_text_failure(self):
        """Test text generation failure handling."""
        with patch.object(
            self.provider.client, "generate", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.side_effect = Exception("Connection failed")

            with pytest.raises(Exception, match="Ollama text generation failed: Connection failed"):
                await self.provider.generate_text("Test prompt")

    @pytest.mark.asyncio
    async def test_generate_embeddings_success(self):
        """Test successful embedding generation."""
        texts = ["First text", "Second text"]
        mock_responses = [{"embedding": [0.1, 0.2, 0.3]}, {"embedding": [0.4, 0.5, 0.6]}]

        with patch.object(
            self.provider.client, "embeddings", new_callable=AsyncMock
        ) as mock_embeddings:
            mock_embeddings.side_effect = mock_responses

            results = await self.provider.generate_embeddings(texts)

            assert len(results) == 2
            assert isinstance(results[0], EmbeddingResponse)
            assert results[0].embeddings == [0.1, 0.2, 0.3]
            assert results[0].dimensions == 3
            assert results[0].model == "nomic-embed-text"
            assert results[0].provider == "ollama"
            assert results[0].tokens_used == 2  # "First text" -> 2 words

            assert results[1].embeddings == [0.4, 0.5, 0.6]
            assert results[1].tokens_used == 2  # "Second text" -> 2 words

            # Verify calls
            assert mock_embeddings.call_count == 2
            mock_embeddings.assert_any_call(model="nomic-embed-text", prompt="First text")
            mock_embeddings.assert_any_call(model="nomic-embed-text", prompt="Second text")

    @pytest.mark.asyncio
    async def test_generate_embeddings_failure(self):
        """Test embedding generation failure handling."""
        with patch.object(
            self.provider.client, "embeddings", new_callable=AsyncMock
        ) as mock_embeddings:
            mock_embeddings.side_effect = Exception("Embedding failed")

            with pytest.raises(
                Exception, match="Ollama embedding generation failed: Embedding failed"
            ):
                await self.provider.generate_embeddings(["Test text"])

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        mock_models_response = {
            "models": [{"name": "gemma:4b"}, {"name": "nomic-embed-text"}, {"name": "llama2:7b"}]
        }

        with patch.object(self.provider.client, "list", new_callable=AsyncMock) as mock_list:
            with patch("time.time", side_effect=[0.0, 0.1]):  # Mock timing
                mock_list.return_value = mock_models_response

                result = await self.provider.health_check()

                assert isinstance(result, ProviderHealth)
                assert result.healthy is True
                assert result.provider == "ollama"
                assert "healthy" in result.message
                assert result.latency_ms == 100.0  # 0.1 * 1000
                assert "gemma:4b" in result.model_info["available_models"]
                assert "nomic-embed-text" in result.model_info["available_models"]

    @pytest.mark.asyncio
    async def test_health_check_missing_models(self):
        """Test health check with missing required models."""
        mock_models_response = {"models": [{"name": "llama2:7b"}]}  # Missing our required models

        with patch.object(self.provider.client, "list", new_callable=AsyncMock) as mock_list:
            with patch("time.time", side_effect=[0.0, 0.05]):
                mock_list.return_value = mock_models_response

                result = await self.provider.health_check()

                assert result.healthy is False
                assert "Required models not available" in result.message
                assert "gemma:4b" in result.message
                assert "nomic-embed-text" in result.message
                assert result.latency_ms == 50.0
                assert result.model_info["llm_available"] is False
                assert result.model_info["embed_available"] is False

    @pytest.mark.asyncio
    async def test_health_check_connection_failure(self):
        """Test health check with connection failure."""
        with patch.object(self.provider.client, "list", new_callable=AsyncMock) as mock_list:
            mock_list.side_effect = Exception("Connection refused")

            result = await self.provider.health_check()

            assert result.healthy is False
            assert result.provider == "ollama"
            assert "Connection refused" in result.message
            assert result.latency_ms == 0.0
            assert "error" in result.model_info

    @pytest.mark.asyncio
    async def test_validate_connection_success(self):
        """Test successful connection validation."""
        with patch.object(self.provider, "health_check", new_callable=AsyncMock) as mock_health:
            mock_health.return_value = ProviderHealth(
                healthy=True, provider="ollama", message="Healthy"
            )

            is_valid = await self.provider.validate_connection()

            assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_connection_failure(self):
        """Test failed connection validation."""
        with patch.object(self.provider, "health_check", new_callable=AsyncMock) as mock_health:
            mock_health.return_value = ProviderHealth(
                healthy=False, provider="ollama", message="Unhealthy"
            )

            is_valid = await self.provider.validate_connection()

            assert is_valid is False

    def test_get_configuration_info(self):
        """Test configuration info retrieval."""
        info = self.provider.get_configuration_info()

        assert info["provider"] == "ollama"
        assert info["config"]["base_url"] == "http://localhost:11434"
        assert info["config"]["llm_model"] == "gemma:4b"
        assert info["config"]["embedding_model"] == "nomic-embed-text"

        # Test with API key masking (though Ollama doesn't use API keys)
        provider_with_key = OllamaGraphRAGLLM(
            {"base_url": "http://localhost:11434", "api_key": "secret"}
        )
        info = provider_with_key.get_configuration_info()
        assert info["config"]["api_key"] == "***"
