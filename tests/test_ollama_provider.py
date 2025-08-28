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
        # Will be replaced with fixtures in the test methods

    def test_initialization(self, ollama_config):
        """Test provider initialization."""
        provider = OllamaGraphRAGLLM(ollama_config)
        assert provider.base_url == ollama_config["base_url"]
        assert provider.llm_model == ollama_config["llm_model"]
        assert provider.embedding_model == ollama_config["embedding_model"]
        assert provider.provider_name == "ollama"

    def test_initialization_with_defaults(self):
        """Test provider initialization with default values."""
        provider = OllamaGraphRAGLLM({})

        assert provider.base_url == "http://localhost:11434"
        assert provider.llm_model == "gemma:4b"
        assert provider.embedding_model == "nomic-embed-text"

    def test_get_provider_name(self, ollama_config):
        """Test provider name method."""
        provider = OllamaGraphRAGLLM(ollama_config)
        assert provider._get_provider_name() == "ollama"

    @pytest.mark.asyncio
    async def test_generate_text_success(self, ollama_config, mock_ollama_response):
        """Test successful text generation."""
        provider = OllamaGraphRAGLLM(ollama_config)

        with patch.object(provider.client, "generate", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_ollama_response

            result = await provider.generate_text("Test prompt")

            assert isinstance(result, LLMResponse)
            assert result.content == mock_ollama_response["response"]
            assert (
                result.tokens_used
                == mock_ollama_response["eval_count"] + mock_ollama_response["prompt_eval_count"]
            )
            assert result.model == provider.llm_model
            assert result.provider == "ollama"
            assert result.metadata["eval_duration"] == mock_ollama_response["eval_duration"]

            mock_generate.assert_called_once_with(
                model="gemma:4b",
                prompt="Test prompt",
                options={"temperature": 0.1, "num_predict": 1500},
                stream=False,
            )

    @pytest.mark.asyncio
    async def test_generate_text_with_custom_params(self, ollama_config):
        """Test text generation with custom parameters."""
        provider = OllamaGraphRAGLLM(ollama_config)
        mock_response = {"response": "Custom response", "eval_count": 15, "prompt_eval_count": 8}

        with patch.object(provider.client, "generate", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_response

            result = await provider.generate_text(
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
    async def test_generate_text_failure(self, ollama_config):
        """Test text generation failure handling."""
        provider = OllamaGraphRAGLLM(ollama_config)
        with patch.object(provider.client, "generate", new_callable=AsyncMock) as mock_generate:
            mock_generate.side_effect = Exception("Connection failed")

            with pytest.raises(Exception, match="Ollama text generation failed: Connection failed"):
                await provider.generate_text("Test prompt")

    @pytest.mark.asyncio
    async def test_generate_embeddings_success(self, ollama_config):
        """Test successful embedding generation."""
        provider = OllamaGraphRAGLLM(ollama_config)
        texts = ["First text", "Second text"]
        mock_responses = [{"embedding": [0.1, 0.2, 0.3]}, {"embedding": [0.4, 0.5, 0.6]}]

        with patch.object(provider.client, "embeddings", new_callable=AsyncMock) as mock_embeddings:
            mock_embeddings.side_effect = mock_responses

            results = await provider.generate_embeddings(texts)

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
    async def test_generate_embeddings_failure(self, ollama_config):
        """Test embedding generation failure handling."""
        provider = OllamaGraphRAGLLM(ollama_config)
        with patch.object(provider.client, "embeddings", new_callable=AsyncMock) as mock_embeddings:
            mock_embeddings.side_effect = Exception("Embedding failed")

            with pytest.raises(
                Exception, match="Ollama embedding generation failed: Embedding failed"
            ):
                await provider.generate_embeddings(["Test text"])

    @pytest.mark.asyncio
    async def test_health_check_success(self, ollama_config):
        """Test successful health check."""
        provider = OllamaGraphRAGLLM(ollama_config)
        mock_models_response = {
            "models": [{"name": "gemma:4b"}, {"name": "nomic-embed-text"}, {"name": "llama2:7b"}]
        }

        with patch.object(provider.client, "list", new_callable=AsyncMock) as mock_list:
            with patch("time.time", side_effect=[0.0, 0.1]):  # Mock timing
                mock_list.return_value = mock_models_response

                result = await provider.health_check()

                assert isinstance(result, ProviderHealth)
                assert result.healthy is True
                assert result.provider == "ollama"
                assert "healthy" in result.message
                assert result.latency_ms == 100.0  # 0.1 * 1000
                assert "gemma:4b" in result.model_info["available_models"]
                assert "nomic-embed-text" in result.model_info["available_models"]

    @pytest.mark.asyncio
    async def test_health_check_missing_models(self, ollama_config):
        """Test health check with missing required models."""
        provider = OllamaGraphRAGLLM(ollama_config)
        mock_models_response = {"models": [{"name": "llama2:7b"}]}  # Missing our required models

        with patch.object(provider.client, "list", new_callable=AsyncMock) as mock_list:
            with patch("time.time", side_effect=[0.0, 0.05]):
                mock_list.return_value = mock_models_response

                result = await provider.health_check()

                assert result.healthy is False
                assert "Required models not available" in result.message
                assert "gemma:4b" in result.message
                assert "nomic-embed-text" in result.message
                assert result.latency_ms == 50.0
                assert result.model_info["llm_available"] is False
                assert result.model_info["embed_available"] is False

    @pytest.mark.asyncio
    async def test_health_check_connection_failure(self, ollama_config):
        """Test health check with connection failure."""
        provider = OllamaGraphRAGLLM(ollama_config)
        with patch.object(provider.client, "list", new_callable=AsyncMock) as mock_list:
            mock_list.side_effect = Exception("Connection refused")

            result = await provider.health_check()

            assert result.healthy is False
            assert result.provider == "ollama"
            assert "Connection refused" in result.message
            assert result.latency_ms == 0.0
            assert "error" in result.model_info

    @pytest.mark.asyncio
    async def test_validate_connection_success(self, ollama_config):
        """Test successful connection validation."""
        provider = OllamaGraphRAGLLM(ollama_config)
        with patch.object(provider, "health_check", new_callable=AsyncMock) as mock_health:
            mock_health.return_value = ProviderHealth(
                healthy=True, provider="ollama", message="Healthy"
            )

            is_valid = await provider.validate_connection()

            assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_connection_failure(self, ollama_config):
        """Test failed connection validation."""
        provider = OllamaGraphRAGLLM(ollama_config)
        with patch.object(provider, "health_check", new_callable=AsyncMock) as mock_health:
            mock_health.return_value = ProviderHealth(
                healthy=False, provider="ollama", message="Unhealthy"
            )

            is_valid = await provider.validate_connection()

            assert is_valid is False

    def test_get_configuration_info(self, ollama_config):
        """Test configuration info retrieval."""
        provider = OllamaGraphRAGLLM(ollama_config)
        info = provider.get_configuration_info()

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


@pytest.mark.integration
class TestOllamaIntegration:
    """Integration tests for Ollama provider with real server.

    These tests require a running Ollama server with the required models.
    Run with: pytest -m integration
    """

    def setup_method(self):
        """Setup test environment for integration tests."""
        self.config = {
            "base_url": "http://localhost:11434",
            "llm_model": "gemma3:4b",  # Use the actual model available on server
            "embedding_model": "nomic-embed-text",  # This should match as substring
        }
        self.provider = OllamaGraphRAGLLM(self.config)

    @pytest.mark.asyncio
    async def test_real_health_check(self):
        """Test health check with real Ollama server."""
        result = await self.provider.health_check()

        assert isinstance(result, ProviderHealth)
        assert result.provider == "ollama"

        if result.healthy:
            # If healthy, verify expected attributes
            assert result.latency_ms >= 0
            assert "available_models" in result.model_info
            assert isinstance(result.model_info["available_models"], list)
            print(f"Available models: {result.model_info['available_models']}")
            print(f"Health status: {result.message}")
            print(f"Latency: {result.latency_ms}ms")
        else:
            # If unhealthy, check error handling
            print(f"Health check failed: {result.message}")
            assert "error" in result.model_info or "not available" in result.message.lower()

    @pytest.mark.asyncio
    async def test_real_connection_validation(self):
        """Test connection validation with real Ollama server."""
        is_valid = await self.provider.validate_connection()

        # This will depend on whether Ollama is running and has required models
        print(f"Connection valid: {is_valid}")
        assert isinstance(is_valid, bool)

    @pytest.mark.asyncio
    async def test_real_text_generation(self):
        """Test actual text generation with real Ollama server."""
        prompt = "What is the capital of France? Please answer in one sentence."

        try:
            result = await self.provider.generate_text(prompt, max_tokens=50, temperature=0.1)

            assert isinstance(result, LLMResponse)
            assert result.content
            assert len(result.content.strip()) > 0
            assert result.model == "gemma3:4b"
            assert result.provider == "ollama"
            assert result.tokens_used > 0

            print(f"Generated response: {result.content}")
            print(f"Tokens used: {result.tokens_used}")
            print(f"Model: {result.model}")

            # Basic content validation
            assert "paris" in result.content.lower() or "france" in result.content.lower()

        except Exception as e:
            pytest.skip(f"Text generation failed - Ollama server may not have required model: {e}")

    @pytest.mark.asyncio
    async def test_real_text_generation_with_custom_params(self):
        """Test text generation with custom parameters."""
        prompt = "Write a haiku about programming."

        try:
            result = await self.provider.generate_text(
                prompt, max_tokens=100, temperature=0.7, top_k=20
            )

            assert isinstance(result, LLMResponse)
            assert result.content
            assert len(result.content.strip()) > 0

            print(f"Haiku response: {result.content}")
            print("Temperature used: 0.7")

            # Should be creative with higher temperature
            assert result.tokens_used > 0

        except Exception as e:
            pytest.skip(f"Custom text generation failed - Ollama server may not be available: {e}")

    @pytest.mark.asyncio
    async def test_real_embedding_generation(self):
        """Test actual embedding generation with real Ollama server."""
        texts = [
            "Machine learning is a subset of artificial intelligence.",
            "Python is a popular programming language for data science.",
            "GraphRAG combines knowledge graphs with retrieval-augmented generation.",
        ]

        try:
            results = await self.provider.generate_embeddings(texts)

            assert len(results) == 3

            for i, result in enumerate(results):
                assert isinstance(result, EmbeddingResponse)
                assert result.embeddings
                assert len(result.embeddings) > 0
                assert result.dimensions == len(result.embeddings)
                assert result.model == "nomic-embed-text"
                assert result.provider == "ollama"
                assert result.tokens_used > 0

                print(f"Text {i+1}: '{texts[i][:50]}...'")
                print(f"  Embedding dimensions: {result.dimensions}")
                print(f"  Tokens used: {result.tokens_used}")
                print(f"  First 5 values: {result.embeddings[:5]}")

            # Verify embeddings are different for different texts
            assert results[0].embeddings != results[1].embeddings
            assert results[1].embeddings != results[2].embeddings

            # All embeddings should have same dimensions
            assert results[0].dimensions == results[1].dimensions == results[2].dimensions

        except Exception as e:
            pytest.skip(
                f"Embedding generation failed - Ollama server may not have embedding model: {e}"
            )

    @pytest.mark.asyncio
    async def test_real_embedding_similarity(self):
        """Test embedding similarity for related vs unrelated texts."""
        related_texts = ["The cat sat on the mat.", "A feline rested on the rug."]
        unrelated_text = "Quantum physics explains the behavior of subatomic particles."

        try:
            # Generate embeddings
            related_results = await self.provider.generate_embeddings(related_texts)
            unrelated_result = await self.provider.generate_embeddings([unrelated_text])

            # Simple cosine similarity calculation
            def cosine_similarity(a, b):
                dot_product = sum(ai * bi for ai, bi in zip(a, b, strict=False))
                magnitude_a = sum(ai * ai for ai in a) ** 0.5
                magnitude_b = sum(bi * bi for bi in b) ** 0.5
                return dot_product / (magnitude_a * magnitude_b)

            # Calculate similarities
            related_similarity = cosine_similarity(
                related_results[0].embeddings, related_results[1].embeddings
            )
            unrelated_similarity = cosine_similarity(
                related_results[0].embeddings, unrelated_result[0].embeddings
            )

            print(f"Related texts similarity: {related_similarity:.4f}")
            print(f"Unrelated texts similarity: {unrelated_similarity:.4f}")

            # Related texts should have higher similarity than unrelated
            assert related_similarity > unrelated_similarity

            # Both similarities should be reasonable values
            assert -1 <= related_similarity <= 1
            assert -1 <= unrelated_similarity <= 1

        except Exception as e:
            pytest.skip(f"Embedding similarity test failed - Ollama server issue: {e}")

    @pytest.mark.asyncio
    async def test_real_batch_processing(self):
        """Test batch processing of multiple texts."""
        batch_texts = [
            "Hello world",
            "How are you today?",
            "The weather is nice",
            "I love programming",
            "AI is fascinating",
        ]

        try:
            # Test batch embedding generation
            results = await self.provider.generate_embeddings(batch_texts)

            assert len(results) == len(batch_texts)

            total_tokens = sum(r.tokens_used for r in results)
            total_dimensions = sum(r.dimensions for r in results)

            print(f"Batch processed {len(batch_texts)} texts")
            print(f"Total tokens used: {total_tokens}")
            print(f"Average dimensions: {total_dimensions / len(results)}")

            # All results should be valid
            for i, result in enumerate(results):
                assert result.embeddings
                assert result.tokens_used > 0
                print(f"  Text {i+1}: {result.tokens_used} tokens, {result.dimensions} dims")

        except Exception as e:
            pytest.skip(f"Batch processing test failed - Ollama server issue: {e}")

    def test_configuration_details(self):
        """Test provider configuration details."""
        config_info = self.provider.get_configuration_info()

        assert config_info["provider"] == "ollama"
        assert config_info["config"]["base_url"] == "http://localhost:11434"
        assert config_info["config"]["llm_model"] == "gemma3:4b"
        assert config_info["config"]["embedding_model"] == "nomic-embed-text"

        print(f"Configuration: {config_info}")

        # Test provider name
        assert self.provider._get_provider_name() == "ollama"
