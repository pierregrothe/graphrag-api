# tests/test_provider.py
# Unified provider test for GraphRAG API Service
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Unified provider test for validating configured provider and implementation patterns."""

import asyncio
import time
from typing import Any, Dict

import pytest

from src.graphrag_api_service.config import Settings, LLMProvider
from src.graphrag_api_service.providers.factory import LLMProviderFactory
from src.graphrag_api_service.providers.registry import register_providers
from src.graphrag_api_service.providers.base import GraphRAGLLM


class TestProviderValidation:
    """Test suite for provider validation and implementation patterns."""
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_providers(self):
        """Setup providers for all tests in this class."""
        register_providers()
    
    @pytest.fixture
    def settings(self) -> Settings:
        """Provide settings loaded from .env file."""
        return Settings()
    
    @pytest.fixture
    def provider(self, settings: Settings) -> GraphRAGLLM:
        """Create provider instance from factory."""
        factory = LLMProviderFactory()
        return factory.create_provider(settings)
    
    def test_configuration_validation(self, settings: Settings):
        """Test configuration validation and completeness.
        
        Args:
            settings: Application settings from fixture
        """
        # Test basic configuration
        assert settings.app_name, "App name not configured"
        assert settings.port > 0, "Invalid port configuration"
        assert settings.llm_provider in LLMProvider, "Invalid LLM provider"
        
        # Test provider-specific configuration
        if settings.llm_provider == LLMProvider.OLLAMA:
            assert settings.ollama_base_url, "Ollama base URL not configured"
            assert settings.ollama_llm_model, "Ollama LLM model not configured"
            assert settings.ollama_embedding_model, "Ollama embedding model not configured"
            
        elif settings.llm_provider == LLMProvider.GOOGLE_GEMINI:
            assert settings.google_api_key, "Google API key not configured"
            assert settings.google_project_id, "Google Project ID not configured"
            assert settings.gemini_model, "Gemini model not configured"
    
    def test_provider_creation(self, provider: GraphRAGLLM, settings: Settings):
        """Test provider instantiation and factory pattern.
        
        Args:
            provider: Provider instance from fixture
            settings: Application settings from fixture
        """
        assert provider is not None, "Provider creation returned None"
        assert isinstance(provider, GraphRAGLLM), "Provider not implementing GraphRAGLLM interface"
        
        # Test provider properties
        provider_name = provider._get_provider_name()
        assert provider_name, "Provider name not set"
        
        # Test provider name consistency
        expected_names = {
            LLMProvider.OLLAMA: "ollama",
            LLMProvider.GOOGLE_GEMINI: "google_gemini"
        }
        expected = expected_names.get(settings.llm_provider)
        assert provider_name == expected, f"Provider name mismatch: {provider_name} != {expected}"
    
    def test_implementation_patterns(self, provider: GraphRAGLLM, settings: Settings):
        """Test implementation patterns without LLM access.
        
        Args:
            provider: Provider instance from fixture
            settings: Application settings from fixture
        """
        # Test abstract method implementation
        methods = ['generate_text', 'generate_embeddings', 'health_check', '_get_provider_name']
        for method in methods:
            assert hasattr(provider, method), f"Missing required method: {method}"
            assert callable(getattr(provider, method)), f"Method not callable: {method}"
        
        # Test configuration building
        config = LLMProviderFactory._build_provider_config(settings)
        assert isinstance(config, dict), "Config building failed"
        assert len(config) > 0, "Empty configuration"
        
        # Test provider-specific config keys
        if settings.llm_provider == LLMProvider.OLLAMA:
            required_keys = {"base_url", "llm_model", "embedding_model"}
            assert required_keys.issubset(config.keys()), f"Missing Ollama config keys: {required_keys - config.keys()}"
            
        elif settings.llm_provider == LLMProvider.GOOGLE_GEMINI:
            required_keys = {"api_key", "project_id", "llm_model", "embedding_model"}
            assert required_keys.issubset(config.keys()), f"Missing Gemini config keys: {required_keys - config.keys()}"
        
        # Test enum values
        assert settings.llm_provider.value in ["ollama", "google_gemini"], "Invalid enum value"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_health_check(self, provider: GraphRAGLLM):
        """Test provider health check functionality.
        
        Args:
            provider: Provider instance from fixture
        """
        start_time = time.time()
        health = await provider.health_check()
        latency_ms = (time.time() - start_time) * 1000
        
        # Health check should succeed
        if not health.healthy:
            pytest.skip(f"Provider unavailable: {health.message}")
        
        assert health.healthy, f"Health check failed: {health.message}"
        assert health.latency_ms >= 0, "Invalid latency measurement"
        assert latency_ms > 0, "Health check completed too quickly"
        
        # Print health check details for debugging
        print(f"\nHealth Check Results:")
        print(f"  Provider: {health.provider}")
        print(f"  Status: {'HEALTHY' if health.healthy else 'UNHEALTHY'}")
        print(f"  Message: {health.message}")
        print(f"  Latency: {health.latency_ms:.1f}ms")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_text_generation(self, provider: GraphRAGLLM):
        """Test provider text generation functionality.
        
        Args:
            provider: Provider instance from fixture
        """
        # Simple math prompt to avoid safety filters
        response = await provider.generate_text(
            prompt="What is 2+2? Answer with just the number.",
            max_tokens=10,
            temperature=0.1
        )
        
        assert response.content, "Text generation returned empty response"
        assert response.content.strip(), "Text generation returned whitespace-only response"
        assert response.tokens_used > 0, "Text generation reported zero tokens used"
        assert response.model, "Text generation missing model information"
        assert response.provider, "Text generation missing provider information"
        
        # Print generation details for debugging
        print(f"\nText Generation Results:")
        print(f"  Content: '{response.content.strip()[:100]}...'")
        print(f"  Tokens Used: {response.tokens_used}")
        print(f"  Model: {response.model}")
        print(f"  Provider: {response.provider}")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_embedding_generation(self, provider: GraphRAGLLM):
        """Test provider embedding generation functionality.
        
        Args:
            provider: Provider instance from fixture
        """
        test_texts = ["test document", "another test"]
        embeddings = await provider.generate_embeddings(test_texts)
        
        assert len(embeddings) == len(test_texts), "Wrong number of embeddings returned"
        
        for i, embedding in enumerate(embeddings):
            assert len(embedding.embeddings) > 0, f"Embedding {i} is empty"
            assert embedding.dimensions > 0, f"Embedding {i} has zero dimensions"
            assert embedding.tokens_used > 0, f"Embedding {i} reported zero tokens"
            assert embedding.model, f"Embedding {i} missing model information"
            assert embedding.provider, f"Embedding {i} missing provider information"
        
        # Test embedding consistency (same dimensions)
        first_dims = embeddings[0].dimensions
        for i, embedding in enumerate(embeddings[1:], 1):
            assert embedding.dimensions == first_dims, f"Embedding {i} dimension mismatch"
        
        # Print embedding details for debugging
        print(f"\nEmbedding Generation Results:")
        print(f"  Texts Processed: {len(embeddings)}")
        print(f"  Embedding Dimensions: {embeddings[0].dimensions}")
        print(f"  Model: {embeddings[0].model}")
        print(f"  Provider: {embeddings[0].provider}")
        print(f"  Total Tokens: {sum(e.tokens_used for e in embeddings)}")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_embedding_consistency(self, provider: GraphRAGLLM):
        """Test embedding generation consistency.
        
        Args:
            provider: Provider instance from fixture
        """
        test_text = "consistent embedding test"
        
        # Generate embeddings twice
        embeddings1 = await provider.generate_embeddings([test_text])
        embeddings2 = await provider.generate_embeddings([test_text])
        
        assert len(embeddings1) == 1, "First embedding generation failed"
        assert len(embeddings2) == 1, "Second embedding generation failed"
        
        emb1 = embeddings1[0]
        emb2 = embeddings2[0]
        
        assert len(emb1.embeddings) == len(emb2.embeddings), "Embedding dimension mismatch"
        
        # Calculate cosine similarity for consistency check
        import numpy as np
        
        vec1 = np.array(emb1.embeddings)
        vec2 = np.array(emb2.embeddings)
        
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        
        # Embeddings should be highly consistent (>0.95 similarity)
        assert similarity > 0.95, f"Embedding consistency low: {similarity:.3f}"
        
        print(f"\nEmbedding Consistency Results:")
        print(f"  Cosine Similarity: {similarity:.6f}")
        print(f"  Consistency Status: {'HIGH' if similarity > 0.99 else 'MODERATE' if similarity > 0.95 else 'LOW'}")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_comprehensive_workflow(self, provider: GraphRAGLLM):
        """Test complete provider workflow end-to-end.
        
        Args:
            provider: Provider instance from fixture
        """
        start_time = time.time()
        
        # Step 1: Health check
        health = await provider.health_check()
        if not health.healthy:
            pytest.skip(f"Provider unavailable: {health.message}")
        
        health_time = time.time()
        
        # Step 2: Text generation
        response = await provider.generate_text(
            prompt="Explain AI in one sentence.",
            max_tokens=50,
            temperature=0.1
        )
        
        text_time = time.time()
        
        # Step 3: Embedding generation
        embeddings = await provider.generate_embeddings([response.content[:100]])
        
        embed_time = time.time()
        
        # Validate workflow results
        assert health.healthy, "Health check failed in workflow"
        assert response.content, "Text generation failed in workflow"
        assert len(embeddings) == 1, "Embedding generation failed in workflow"
        
        # Print comprehensive workflow results
        total_time = (embed_time - start_time) * 1000
        health_duration = (health_time - start_time) * 1000
        text_duration = (text_time - health_time) * 1000
        embed_duration = (embed_time - text_time) * 1000
        
        print(f"\nComprehensive Workflow Results:")
        print(f"  Total Duration: {total_time:.1f}ms")
        print(f"  Health Check: {health_duration:.1f}ms")
        print(f"  Text Generation: {text_duration:.1f}ms")
        print(f"  Embedding Generation: {embed_duration:.1f}ms")
        print(f"  Provider: {provider._get_provider_name()}")
        print(f"  Text Length: {len(response.content)} chars")
        print(f"  Embedding Dims: {embeddings[0].dimensions}")
        
        # Workflow should complete reasonably quickly
        assert total_time < 30000, f"Workflow too slow: {total_time:.1f}ms"


# Standalone execution support (for backwards compatibility)
async def main():
    """Main function for standalone execution."""
    print("Running provider validation tests...")
    
    # Import pytest and run tests programmatically
    import subprocess
    import sys
    
    # Run pytest on this file
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        __file__, 
        "-v", 
        "-s",  # Show print statements
        "--tb=short"  # Shorter traceback format
    ], cwd="D:/dev/GraphRAG")
    
    return result.returncode == 0


if __name__ == "__main__":
    asyncio.run(main())