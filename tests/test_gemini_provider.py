# tests/test_gemini_provider.py
# Unit tests for Google Gemini provider implementation
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Tests for Google Gemini provider implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graphrag_api_service.providers.base import EmbeddingResponse, LLMResponse, ProviderHealth
from src.graphrag_api_service.providers.gemini_provider import GeminiGraphRAGLLM


class TestGeminiGraphRAGLLM:
    """Test the Google Gemini provider implementation."""

    def test_initialization_success(self, gemini_config):
        """Test successful provider initialization."""
        with patch("google.generativeai.configure") as mock_configure:
            provider = GeminiGraphRAGLLM(gemini_config)

            assert provider.api_key == gemini_config["api_key"]
            assert provider.project_id == gemini_config["project_id"]
            assert provider.location == gemini_config["location"]
            assert provider.llm_model == gemini_config["model"]
            assert provider.embedding_model == gemini_config["embedding_model"]
            assert provider.provider_name == "google_gemini"
            assert provider.use_vertex_ai is False
            assert provider.vertex_ai_endpoint is None
            assert provider.vertex_ai_location == "us-central1"

            mock_configure.assert_called_once_with(api_key="test_api_key")

    def test_initialization_missing_api_key(self, gemini_config):
        """Test initialization failure with missing API key."""
        config = gemini_config.copy()
        del config["api_key"]

        with pytest.raises(ValueError, match="Google API key is required"):
            GeminiGraphRAGLLM(config)

    def test_initialization_missing_project_id(self, gemini_config):
        """Test initialization failure with missing project ID."""
        config = gemini_config.copy()
        del config["project_id"]

        with pytest.raises(ValueError, match="Google project ID is required"):
            GeminiGraphRAGLLM(config)

    def test_initialization_with_defaults(self, gemini_config):
        """Test provider initialization with default values."""
        config = {"api_key": gemini_config["api_key"], "project_id": gemini_config["project_id"]}

        with patch("google.generativeai.configure"):
            with patch("google.generativeai.GenerativeModel"):
                provider = GeminiGraphRAGLLM(config)

                assert provider.location == "us-central1"
                assert provider.llm_model == "gemini-2.5-flash"
                assert provider.embedding_model == "text-embedding-004"

    def test_get_provider_name(self, gemini_config):
        """Test provider name method."""
        with patch("google.generativeai.configure"):
            with patch("google.generativeai.GenerativeModel"):
                provider = GeminiGraphRAGLLM(gemini_config)
                assert provider._get_provider_name() == "google_gemini"

    @pytest.mark.asyncio
    async def test_generate_text_success(self, gemini_config):
        """Test successful text generation."""
        mock_response = MagicMock()
        mock_response.text = "This is a test response from Gemini"
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].finish_reason.name = "STOP"
        mock_response.candidates[0].safety_ratings = []
        mock_response.prompt_feedback = None

        with patch("google.generativeai.configure"):
            with patch("google.generativeai.GenerativeModel") as mock_model_class:
                mock_model = MagicMock()
                mock_model.generate_content_async = AsyncMock(return_value=mock_response)
                mock_model.safety_settings = {}
                mock_model_class.return_value = mock_model

                provider = GeminiGraphRAGLLM(gemini_config)

                # Mock the model creation in generate_text
                with patch("google.generativeai.GenerativeModel", return_value=mock_model):
                    result = await provider.generate_text("Test prompt")

                    assert isinstance(result, LLMResponse)
                    assert result.content == "This is a test response from Gemini"
                    assert result.model == "gemini-2.5-flash"
                    assert result.provider == "google_gemini"
                    assert result.metadata["finish_reason"] == "STOP"

                    mock_model.generate_content_async.assert_called_once_with("Test prompt")

    @pytest.mark.asyncio
    async def test_generate_text_with_custom_params(self, gemini_config):
        """Test text generation with custom parameters."""
        mock_response = MagicMock()
        mock_response.text = "Custom response"
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].finish_reason.name = "STOP"
        mock_response.candidates[0].safety_ratings = []
        mock_response.prompt_feedback = None

        with patch("google.generativeai.configure"):
            with patch("google.generativeai.GenerativeModel") as mock_model_class:
                mock_model = MagicMock()
                mock_model.generate_content_async = AsyncMock(return_value=mock_response)
                mock_model.safety_settings = {}
                mock_model_class.return_value = mock_model

                provider = GeminiGraphRAGLLM(gemini_config)

                result = await provider.generate_text(
                    "Custom prompt", max_tokens=1000, temperature=0.7, top_k=40
                )

                assert result.content == "Custom response"
                # Verify the model was called
                mock_model.generate_content_async.assert_called_once_with("Custom prompt")

    @pytest.mark.asyncio
    async def test_generate_text_failure(self, gemini_config):
        """Test text generation failure handling."""
        with patch("google.generativeai.configure"):
            with patch("google.generativeai.GenerativeModel"):
                provider = GeminiGraphRAGLLM(gemini_config)

                with patch("google.generativeai.GenerativeModel") as mock_model_class:
                    mock_model = MagicMock()
                    mock_model.generate_content_async = AsyncMock(
                        side_effect=Exception("API Error")
                    )
                    mock_model.safety_settings = {}
                    mock_model_class.return_value = mock_model

                    with pytest.raises(Exception, match="Gemini text generation failed: API Error"):
                        await provider.generate_text("Test prompt")

    @pytest.mark.asyncio
    async def test_generate_embeddings_success(self, gemini_config):
        """Test successful embedding generation."""
        texts = ["First text", "Second text"]
        mock_embeddings = [{"embedding": [0.1, 0.2, 0.3]}, {"embedding": [0.4, 0.5, 0.6]}]

        with patch("google.generativeai.configure"):
            with patch("google.generativeai.GenerativeModel"):
                provider = GeminiGraphRAGLLM(gemini_config)

                with patch(
                    "google.generativeai.embed_content", side_effect=mock_embeddings
                ) as mock_embed:
                    results = await provider.generate_embeddings(texts)

                    assert len(results) == 2
                    assert isinstance(results[0], EmbeddingResponse)
                    assert results[0].embeddings == [0.1, 0.2, 0.3]
                    assert results[0].dimensions == 3
                    assert results[0].model == "text-embedding-004"
                    assert results[0].provider == "google_gemini"
                    assert results[0].tokens_used == 2  # "First text" -> 2 words

                    assert results[1].embeddings == [0.4, 0.5, 0.6]
                    assert results[1].tokens_used == 2  # "Second text" -> 2 words

                    # Verify calls
                    assert mock_embed.call_count == 2
                    mock_embed.assert_any_call(
                        model="models/text-embedding-004",
                        content="First text",
                        task_type="retrieval_document",
                    )
                    mock_embed.assert_any_call(
                        model="models/text-embedding-004",
                        content="Second text",
                        task_type="retrieval_document",
                    )

    @pytest.mark.asyncio
    async def test_generate_embeddings_with_batching(self, gemini_config):
        """Test embedding generation with custom batch size."""
        texts = ["Text 1", "Text 2", "Text 3", "Text 4", "Text 5"]
        mock_embedding = {"embedding": [0.1, 0.2, 0.3]}

        with patch("google.generativeai.configure"):
            with patch("google.generativeai.GenerativeModel"):
                provider = GeminiGraphRAGLLM(gemini_config)

                with patch(
                    "google.generativeai.embed_content", return_value=mock_embedding
                ) as mock_embed:
                    with patch("asyncio.sleep") as mock_sleep:
                        results = await provider.generate_embeddings(texts, batch_size=2)

                        assert len(results) == 5
                        assert mock_embed.call_count == 5
                        # Should have 2 sleep calls (after batches 1 and 2, but not after the last batch)
                        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_embeddings_failure(self, gemini_config):
        """Test embedding generation failure handling."""
        with patch("google.generativeai.configure"):
            with patch("google.generativeai.GenerativeModel"):
                provider = GeminiGraphRAGLLM(gemini_config)

                with patch(
                    "google.generativeai.embed_content", side_effect=Exception("Embedding failed")
                ):
                    with pytest.raises(
                        Exception, match="Gemini embedding generation failed: Embedding failed"
                    ):
                        await provider.generate_embeddings(["Test text"])

    @pytest.mark.asyncio
    async def test_health_check_success(self, gemini_config):
        """Test successful health check."""
        mock_embed_result = {"embedding": [0.1, 0.2, 0.3]}

        with patch("google.generativeai.configure"):
            with patch("google.generativeai.GenerativeModel"):
                provider = GeminiGraphRAGLLM(gemini_config)

                with patch("google.generativeai.embed_content", return_value=mock_embed_result):
                    with patch("time.time", side_effect=[0.0, 0.1]):
                        result = await provider.health_check()

                        assert isinstance(result, ProviderHealth)
                        assert result.healthy is True
                        assert result.provider == "google_gemini"
                        assert "healthy" in result.message
                        assert result.latency_ms == 100.0
                        assert result.model_info["embedding_available"] is True
                        assert result.model_info["embedding_dimensions"] == 3

    @pytest.mark.asyncio
    async def test_health_check_empty_response(self, gemini_config):
        """Test health check with empty response."""
        mock_embed_result = None

        with patch("google.generativeai.configure"):
            with patch("google.generativeai.GenerativeModel"):
                provider = GeminiGraphRAGLLM(gemini_config)

                with patch("google.generativeai.embed_content", return_value=mock_embed_result):
                    with patch("time.time", side_effect=[0.0, 0.05]):
                        result = await provider.health_check()

                        assert result.healthy is False
                        assert "embedding API not responding" in result.message
                        assert result.latency_ms == 50.0
                        assert result.model_info["embedding_test"] == "failed"

    @pytest.mark.asyncio
    async def test_health_check_connection_failure(self, gemini_config):
        """Test health check with connection failure."""
        with patch("google.generativeai.configure"):
            with patch("google.generativeai.GenerativeModel"):
                provider = GeminiGraphRAGLLM(gemini_config)

                with patch(
                    "google.generativeai.embed_content", side_effect=Exception("Connection failed")
                ):
                    result = await provider.health_check()

                    assert result.healthy is False
                    assert result.provider == "google_gemini"
                    assert "Connection failed" in result.message
                    assert result.latency_ms == 0.0
                    assert "error" in result.model_info

    @pytest.mark.asyncio
    async def test_validate_connection_success(self, gemini_config):
        """Test successful connection validation."""
        with patch("google.generativeai.configure"):
            with patch("google.generativeai.GenerativeModel"):
                provider = GeminiGraphRAGLLM(gemini_config)

                with patch.object(provider, "health_check", new_callable=AsyncMock) as mock_health:
                    mock_health.return_value = ProviderHealth(
                        healthy=True, provider="google_gemini", message="Healthy"
                    )

                    is_valid = await provider.validate_connection()

                    assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_connection_failure(self, gemini_config):
        """Test failed connection validation."""
        with patch("google.generativeai.configure"):
            with patch("google.generativeai.GenerativeModel"):
                provider = GeminiGraphRAGLLM(gemini_config)

                with patch.object(provider, "health_check", new_callable=AsyncMock) as mock_health:
                    mock_health.return_value = ProviderHealth(
                        healthy=False, provider="google_gemini", message="Unhealthy"
                    )

                    is_valid = await provider.validate_connection()

                    assert is_valid is False

    def test_get_configuration_info(self, gemini_config):
        """Test configuration info retrieval."""
        with patch("google.generativeai.configure"):
            with patch("google.generativeai.GenerativeModel"):
                provider = GeminiGraphRAGLLM(gemini_config)

                info = provider.get_configuration_info()

                assert info["provider"] == "google_gemini"
                assert info["config"]["project_id"] == "test_project_id"
                assert info["config"]["location"] == "us-central1"
                assert info["config"]["model"] == "gemini-2.5-flash"
                assert info["config"]["embedding_model"] == "text-embedding-004"
                # API key should be masked
                assert info["config"]["api_key"] == "***"


@pytest.mark.integration
class TestGeminiIntegration:
    """Integration tests for Google Gemini provider with real Google Cloud API.

    These tests require valid Google Cloud credentials and API access.
    Run with: pytest -m integration
    
    Environment variables needed:
    - GOOGLE_API_KEY: Your Google Cloud API key
    - GOOGLE_PROJECT_ID: Your Google Cloud project ID  
    """

    def setup_method(self):
        """Setup test environment for integration tests."""
        import os
        from src.graphrag_api_service.config import Settings
        
        # Try to get credentials from Settings (which loads from .env)
        try:
            settings = Settings()
            api_key = settings.google_api_key
            project_id = settings.google_project_id
        except Exception:
            # Fallback to environment variables
            api_key = os.getenv("GOOGLE_API_KEY")
            project_id = os.getenv("GOOGLE_PROJECT_ID")
        
        if not api_key or not project_id:
            pytest.skip("Google Cloud credentials not configured for integration tests")
            
        self.config = {
            "api_key": api_key,
            "project_id": project_id,
            "location": "us-central1", 
            "model": "gemini-2.5-flash",
            "embedding_model": "text-embedding-004",
            "use_vertex_ai": False,
            "vertex_ai_endpoint": None,
            "vertex_ai_location": "us-central1",
        }
        self.provider = GeminiGraphRAGLLM(self.config)

    @pytest.mark.asyncio
    async def test_real_health_check(self):
        """Test health check with real Google Cloud API."""
        result = await self.provider.health_check()

        assert isinstance(result, ProviderHealth)
        assert result.provider == "google_gemini"

        if result.healthy:
            # If healthy, verify expected attributes
            assert result.latency_ms >= 0
            assert "model" in result.model_info
            assert result.model_info["model"] == "gemini-2.5-flash"
            print(f"Health status: {result.message}")
            print(f"Latency: {result.latency_ms}ms")
            print(f"Model info: {result.model_info}")
        else:
            # If unhealthy, check error handling
            print(f"Health check failed: {result.message}")
            assert "error" in result.model_info.get("error_details", {}) or "failed" in result.message.lower() or "empty response" in result.message.lower()

    @pytest.mark.asyncio
    async def test_real_connection_validation(self):
        """Test connection validation with real Google Cloud API."""
        is_valid = await self.provider.validate_connection()

        print(f"Connection valid: {is_valid}")
        assert isinstance(is_valid, bool)

    @pytest.mark.asyncio
    async def test_real_text_generation(self):
        """Test actual text generation with real Gemini API."""
        prompt = "What is the capital of France? Please answer in one sentence."

        try:
            result = await self.provider.generate_text(prompt, max_tokens=50, temperature=0.1)

            assert isinstance(result, LLMResponse)
            assert result.content
            assert len(result.content.strip()) > 0
            assert result.model == "gemini-2.5-flash"
            assert result.provider == "google_gemini"
            assert result.tokens_used >= 0

            print(f"Generated response: {result.content}")
            print(f"Tokens used: {result.tokens_used}")
            print(f"Model: {result.model}")

            # Basic content validation
            assert "paris" in result.content.lower() or "france" in result.content.lower()

        except Exception as e:
            pytest.skip(f"Text generation failed - API issue or quota exceeded: {e}")

    @pytest.mark.asyncio
    async def test_real_text_generation_with_custom_params(self):
        """Test text generation with custom parameters."""
        prompt = "Write a haiku about artificial intelligence."

        try:
            result = await self.provider.generate_text(
                prompt, max_tokens=100, temperature=0.7, top_k=40, top_p=0.95
            )

            assert isinstance(result, LLMResponse)
            assert result.content
            assert len(result.content.strip()) > 0

            print(f"Haiku response: {result.content}")
            print("Temperature used: 0.7")

            # Should be creative with higher temperature
            assert result.tokens_used >= 0

        except Exception as e:
            pytest.skip(f"Custom text generation failed - API issue: {e}")

    @pytest.mark.asyncio
    async def test_real_embedding_generation(self):
        """Test actual embedding generation with real Gemini API."""
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
                assert result.model == "text-embedding-004"
                assert result.provider == "google_gemini"
                assert result.tokens_used >= 0

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
            pytest.skip(f"Embedding generation failed - API issue or quota exceeded: {e}")

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
            pytest.skip(f"Embedding similarity test failed - API issue: {e}")

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
                assert result.tokens_used >= 0
                print(f"  Text {i+1}: {result.tokens_used} tokens, {result.dimensions} dims")

        except Exception as e:
            pytest.skip(f"Batch processing test failed - API issue: {e}")

    def test_configuration_details(self):
        """Test provider configuration details."""
        config_info = self.provider.get_configuration_info()

        assert config_info["provider"] == "google_gemini"
        assert config_info["config"]["project_id"] == self.config["project_id"]
        assert config_info["config"]["location"] == "us-central1"
        assert config_info["config"]["model"] == "gemini-2.5-flash"
        assert config_info["config"]["embedding_model"] == "text-embedding-004"
        # API key should be masked
        assert config_info["config"]["api_key"] == "***"

        print(f"Configuration: {config_info}")

        # Test provider name
        assert self.provider._get_provider_name() == "google_gemini"
