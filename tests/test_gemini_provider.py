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

    def setup_method(self):
        """Setup test environment."""
        self.config = {
            "api_key": "test_api_key",
            "project_id": "test_project",
            "location": "us-central1",
            "llm_model": "gemini-2.5-flash",
            "embedding_model": "text-embedding-004"
        }

    def test_initialization_success(self):
        """Test successful provider initialization."""
        with patch('google.generativeai.configure') as mock_configure:
            with patch('google.generativeai.GenerativeModel') as mock_model:
                provider = GeminiGraphRAGLLM(self.config)

                assert provider.api_key == "test_api_key"
                assert provider.project_id == "test_project"
                assert provider.location == "us-central1"
                assert provider.llm_model == "gemini-2.5-flash"
                assert provider.embedding_model == "text-embedding-004"
                assert provider.provider_name == "google_gemini"

                mock_configure.assert_called_once_with(api_key="test_api_key")
                mock_model.assert_called_once()

    def test_initialization_missing_api_key(self):
        """Test initialization failure with missing API key."""
        config = self.config.copy()
        del config["api_key"]

        with pytest.raises(ValueError, match="Google API key is required"):
            GeminiGraphRAGLLM(config)

    def test_initialization_missing_project_id(self):
        """Test initialization failure with missing project ID."""
        config = self.config.copy()
        del config["project_id"]

        with pytest.raises(ValueError, match="Google project ID is required"):
            GeminiGraphRAGLLM(config)

    def test_initialization_with_defaults(self):
        """Test provider initialization with default values."""
        config = {
            "api_key": "test_key",
            "project_id": "test_project"
        }

        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                provider = GeminiGraphRAGLLM(config)

                assert provider.location == "us-central1"
                assert provider.llm_model == "gemini-2.5-flash"
                assert provider.embedding_model == "text-embedding-004"

    def test_get_provider_name(self):
        """Test provider name method."""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                provider = GeminiGraphRAGLLM(self.config)
                assert provider._get_provider_name() == "google_gemini"

    @pytest.mark.asyncio
    async def test_generate_text_success(self):
        """Test successful text generation."""
        mock_response = MagicMock()
        mock_response.text = "This is a test response from Gemini"
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].finish_reason.name = "STOP"
        mock_response.candidates[0].safety_ratings = []
        mock_response.prompt_feedback = None

        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel') as mock_model_class:
                mock_model = MagicMock()
                mock_model.generate_content_async = AsyncMock(return_value=mock_response)
                mock_model.safety_settings = {}
                mock_model_class.return_value = mock_model

                provider = GeminiGraphRAGLLM(self.config)

                # Mock the model creation in generate_text
                with patch('google.generativeai.GenerativeModel', return_value=mock_model):
                    result = await provider.generate_text("Test prompt")

                    assert isinstance(result, LLMResponse)
                    assert result.content == "This is a test response from Gemini"
                    assert result.model == "gemini-2.5-flash"
                    assert result.provider == "google_gemini"
                    assert result.metadata["finish_reason"] == "STOP"

                    mock_model.generate_content_async.assert_called_once_with("Test prompt")

    @pytest.mark.asyncio
    async def test_generate_text_with_custom_params(self):
        """Test text generation with custom parameters."""
        mock_response = MagicMock()
        mock_response.text = "Custom response"
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].finish_reason.name = "STOP"
        mock_response.candidates[0].safety_ratings = []
        mock_response.prompt_feedback = None

        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel') as mock_model_class:
                mock_model = MagicMock()
                mock_model.generate_content_async = AsyncMock(return_value=mock_response)
                mock_model.safety_settings = {}
                mock_model_class.return_value = mock_model

                provider = GeminiGraphRAGLLM(self.config)

                result = await provider.generate_text(
                    "Custom prompt",
                    max_tokens=1000,
                    temperature=0.7,
                    top_k=40
                )

                assert result.content == "Custom response"
                # Verify the model was called
                mock_model.generate_content_async.assert_called_once_with("Custom prompt")

    @pytest.mark.asyncio
    async def test_generate_text_failure(self):
        """Test text generation failure handling."""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                provider = GeminiGraphRAGLLM(self.config)

                with patch('google.generativeai.GenerativeModel') as mock_model_class:
                    mock_model = MagicMock()
                    mock_model.generate_content_async = AsyncMock(side_effect=Exception("API Error"))
                    mock_model.safety_settings = {}
                    mock_model_class.return_value = mock_model

                    with pytest.raises(Exception, match="Gemini text generation failed: API Error"):
                        await provider.generate_text("Test prompt")

    @pytest.mark.asyncio
    async def test_generate_embeddings_success(self):
        """Test successful embedding generation."""
        texts = ["First text", "Second text"]
        mock_embeddings = [
            {"embedding": [0.1, 0.2, 0.3]},
            {"embedding": [0.4, 0.5, 0.6]}
        ]

        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                provider = GeminiGraphRAGLLM(self.config)

                with patch('google.generativeai.embed_content', side_effect=mock_embeddings) as mock_embed:
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
                        task_type="retrieval_document"
                    )
                    mock_embed.assert_any_call(
                        model="models/text-embedding-004",
                        content="Second text",
                        task_type="retrieval_document"
                    )

    @pytest.mark.asyncio
    async def test_generate_embeddings_with_batching(self):
        """Test embedding generation with custom batch size."""
        texts = ["Text 1", "Text 2", "Text 3", "Text 4", "Text 5"]
        mock_embedding = {"embedding": [0.1, 0.2, 0.3]}

        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                provider = GeminiGraphRAGLLM(self.config)

                with patch('google.generativeai.embed_content', return_value=mock_embedding) as mock_embed:
                    with patch('asyncio.sleep') as mock_sleep:
                        results = await provider.generate_embeddings(texts, batch_size=2)

                        assert len(results) == 5
                        assert mock_embed.call_count == 5
                        # Should have 2 sleep calls (after batches 1 and 2, but not after the last batch)
                        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_embeddings_failure(self):
        """Test embedding generation failure handling."""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                provider = GeminiGraphRAGLLM(self.config)

                with patch('google.generativeai.embed_content', side_effect=Exception("Embedding failed")):
                    with pytest.raises(Exception, match="Gemini embedding generation failed: Embedding failed"):
                        await provider.generate_embeddings(["Test text"])

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        mock_response = MagicMock()
        mock_response.text = "Hello response"

        mock_embed_result = {"embedding": [0.1, 0.2, 0.3]}

        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                provider = GeminiGraphRAGLLM(self.config)

                with patch('google.generativeai.GenerativeModel') as mock_model_class:
                    mock_model = MagicMock()
                    mock_model.generate_content_async = AsyncMock(return_value=mock_response)
                    mock_model_class.return_value = mock_model

                    with patch('google.generativeai.embed_content', return_value=mock_embed_result):
                        with patch('time.time', side_effect=[0.0, 0.1]):
                            result = await provider.health_check()

                            assert isinstance(result, ProviderHealth)
                            assert result.healthy is True
                            assert result.provider == "google_gemini"
                            assert "healthy" in result.message
                            assert result.latency_ms == 100.0
                            assert result.model_info["llm_available"] is True
                            assert result.model_info["embedding_available"] is True

    @pytest.mark.asyncio
    async def test_health_check_empty_response(self):
        """Test health check with empty response."""
        mock_response = MagicMock()
        mock_response.text = None

        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                provider = GeminiGraphRAGLLM(self.config)

                with patch('google.generativeai.GenerativeModel') as mock_model_class:
                    mock_model = MagicMock()
                    mock_model.generate_content_async = AsyncMock(return_value=mock_response)
                    mock_model_class.return_value = mock_model

                    with patch('time.time', side_effect=[0.0, 0.05]):
                        result = await provider.health_check()

                        assert result.healthy is False
                        assert "empty response" in result.message
                        assert result.latency_ms == 50.0
                        assert result.model_info["response_received"] is False

    @pytest.mark.asyncio
    async def test_health_check_connection_failure(self):
        """Test health check with connection failure."""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                provider = GeminiGraphRAGLLM(self.config)

                with patch('google.generativeai.GenerativeModel') as mock_model_class:
                    mock_model = MagicMock()
                    mock_model.generate_content_async = AsyncMock(side_effect=Exception("Connection failed"))
                    mock_model_class.return_value = mock_model

                    result = await provider.health_check()

                    assert result.healthy is False
                    assert result.provider == "google_gemini"
                    assert "Connection failed" in result.message
                    assert result.latency_ms == 0.0
                    assert "error" in result.model_info

    @pytest.mark.asyncio
    async def test_validate_connection_success(self):
        """Test successful connection validation."""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                provider = GeminiGraphRAGLLM(self.config)

                with patch.object(provider, 'health_check', new_callable=AsyncMock) as mock_health:
                    mock_health.return_value = ProviderHealth(
                        healthy=True,
                        provider="google_gemini",
                        message="Healthy"
                    )

                    is_valid = await provider.validate_connection()

                    assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_connection_failure(self):
        """Test failed connection validation."""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                provider = GeminiGraphRAGLLM(self.config)

                with patch.object(provider, 'health_check', new_callable=AsyncMock) as mock_health:
                    mock_health.return_value = ProviderHealth(
                        healthy=False,
                        provider="google_gemini",
                        message="Unhealthy"
                    )

                    is_valid = await provider.validate_connection()

                    assert is_valid is False

    def test_get_configuration_info(self):
        """Test configuration info retrieval."""
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel'):
                provider = GeminiGraphRAGLLM(self.config)

                info = provider.get_configuration_info()

                assert info["provider"] == "google_gemini"
                assert info["config"]["project_id"] == "test_project"
                assert info["config"]["location"] == "us-central1"
                assert info["config"]["llm_model"] == "gemini-2.5-flash"
                assert info["config"]["embedding_model"] == "text-embedding-004"
                # API key should be masked
                assert info["config"]["api_key"] == "***"
