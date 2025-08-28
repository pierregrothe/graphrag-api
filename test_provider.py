# test_provider.py
# Single provider test script for GraphRAG API Service
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Single test script for validating the configured provider and implementation patterns."""

import asyncio
import sys
import time
from pathlib import Path
from typing import Any, Dict

# Add src to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from graphrag_api_service.config import Settings, LLMProvider
from graphrag_api_service.providers.factory import LLMProviderFactory
from graphrag_api_service.providers.registry import register_providers
from graphrag_api_service.providers.base import GraphRAGLLM


class ProviderTestSuite:
    """Test suite for provider validation and implementation patterns."""
    
    def __init__(self):
        """Initialize the test suite."""
        # Register providers
        register_providers()
        
        # Load settings from .env
        self.settings = Settings()
        self.provider = None
        self.test_results = {
            "config_validation": False,
            "provider_creation": False,
            "implementation_patterns": False,
            "llm_connectivity": False,
            "overall_success": False
        }
    
    def print_header(self):
        """Print test header."""
        print("=" * 60)
        print("GraphRAG API Service - Provider Test Suite")
        print("=" * 60)
        print(f"Configured Provider: {self.settings.llm_provider.value}")
        print(f"Debug Mode: {self.settings.debug}")
        print(f"Log Level: {self.settings.log_level}")
        print("-" * 60)
    
    def test_configuration_validation(self) -> bool:
        """Test configuration validation and completeness.
        
        Returns:
            True if configuration is valid
        """
        print("1. Testing Configuration Validation...")
        
        try:
            # Test basic configuration
            assert self.settings.app_name, "App name not configured"
            assert self.settings.port > 0, "Invalid port configuration"
            assert self.settings.llm_provider in LLMProvider, "Invalid LLM provider"
            
            # Test provider-specific configuration
            if self.settings.llm_provider == LLMProvider.OLLAMA:
                assert self.settings.ollama_base_url, "Ollama base URL not configured"
                assert self.settings.ollama_llm_model, "Ollama LLM model not configured"
                assert self.settings.ollama_embedding_model, "Ollama embedding model not configured"
                print(f"   [OK] Ollama configuration: {self.settings.ollama_base_url}")
                print(f"   [OK] LLM Model: {self.settings.ollama_llm_model}")
                print(f"   [OK] Embedding Model: {self.settings.ollama_embedding_model}")
                
            elif self.settings.llm_provider == LLMProvider.GOOGLE_GEMINI:
                assert self.settings.google_api_key, "Google API key not configured"
                assert self.settings.google_project_id, "Google Project ID not configured"
                assert self.settings.gemini_model, "Gemini model not configured"
                print(f"   [OK] Google Project ID: {self.settings.google_project_id}")
                print(f"   [OK] LLM Model: {self.settings.gemini_model}")
                print(f"   [OK] Embedding Model: {self.settings.gemini_embedding_model}")
                print(f"   [OK] Location: {self.settings.google_location}")
                print(f"   [OK] Vertex AI: {self.settings.google_cloud_use_vertex_ai}")
            
            print("   [OK] Configuration validation PASSED")
            return True
            
        except Exception as e:
            print(f"   [FAIL] Configuration validation FAILED: {e}")
            return False
    
    def test_provider_creation(self) -> bool:
        """Test provider instantiation and factory pattern.
        
        Returns:
            True if provider creation succeeds
        """
        print("2. Testing Provider Creation...")
        
        try:
            # Test factory pattern
            factory = LLMProviderFactory()
            self.provider = factory.create_provider(self.settings)
            
            assert self.provider is not None, "Provider creation returned None"
            assert isinstance(self.provider, GraphRAGLLM), "Provider not implementing GraphRAGLLM interface"
            
            # Test provider properties
            provider_name = self.provider._get_provider_name()
            assert provider_name, "Provider name not set"
            
            print(f"   [OK] Provider created: {provider_name}")
            print(f"   [OK] Interface compliance: GraphRAGLLM")
            print("   [OK] Provider creation PASSED")
            return True
            
        except Exception as e:
            print(f"   [FAIL] Provider creation FAILED: {e}")
            return False
    
    def test_implementation_patterns(self) -> bool:
        """Test implementation patterns without LLM access.
        
        Returns:
            True if implementation patterns are correct
        """
        print("3. Testing Implementation Patterns...")
        
        try:
            if not self.provider:
                print("   [FAIL] No provider available for testing")
                return False
            
            # Test abstract method implementation
            methods = ['generate_text', 'generate_embeddings', 'health_check', '_get_provider_name']
            for method in methods:
                assert hasattr(self.provider, method), f"Missing required method: {method}"
                assert callable(getattr(self.provider, method)), f"Method not callable: {method}"
            
            print("   [OK] All required methods implemented")
            
            # Test provider name consistency
            provider_name = self.provider._get_provider_name()
            expected_names = {
                LLMProvider.OLLAMA: "ollama",
                LLMProvider.GOOGLE_GEMINI: "google_gemini"
            }
            expected = expected_names.get(self.settings.llm_provider)
            assert provider_name == expected, f"Provider name mismatch: {provider_name} != {expected}"
            
            print(f"   [OK] Provider name consistency: {provider_name}")
            
            # Test configuration building
            config = LLMProviderFactory._build_provider_config(self.settings)
            assert isinstance(config, dict), "Config building failed"
            assert len(config) > 0, "Empty configuration"
            
            # Test provider-specific config keys
            if self.settings.llm_provider == LLMProvider.OLLAMA:
                required_keys = {"base_url", "llm_model", "embedding_model"}
                assert required_keys.issubset(config.keys()), f"Missing Ollama config keys: {required_keys - config.keys()}"
                
            elif self.settings.llm_provider == LLMProvider.GOOGLE_GEMINI:
                required_keys = {"api_key", "project_id", "llm_model", "embedding_model"}
                assert required_keys.issubset(config.keys()), f"Missing Gemini config keys: {required_keys - config.keys()}"
            
            print(f"   [OK] Configuration keys validated: {len(config)} parameters")
            
            # Test enum values
            assert self.settings.llm_provider.value in ["ollama", "google_gemini"], "Invalid enum value"
            
            print("   [OK] Implementation patterns PASSED")
            return True
            
        except Exception as e:
            print(f"   [FAIL] Implementation patterns FAILED: {e}")
            return False
    
    async def test_llm_connectivity(self) -> bool:
        """Test LLM connectivity and basic functionality.
        
        Returns:
            True if LLM tests pass
        """
        print("4. Testing LLM Connectivity...")
        
        if not self.provider:
            print("   [FAIL] No provider available for testing")
            return False
        
        try:
            start_time = time.time()
            
            # Test health check
            print("   -> Testing health check...")
            health = await self.provider.health_check()
            
            if not health.healthy:
                print(f"   [WARN] Health check failed: {health.message}")
                return False
            
            print(f"   [OK] Health check passed ({health.latency_ms:.1f}ms)")
            
            # Test simple text generation
            print("   -> Testing text generation...")
            response = await self.provider.generate_text(
                prompt="What is 2+2? Answer with just the number.",
                max_tokens=10,
                temperature=0.1
            )
            
            if not response.content or not response.content.strip():
                print("   [WARN] Text generation returned empty response")
                return False
            
            print(f"   [OK] Text generation: '{response.content.strip()[:50]}...'")
            print(f"   [OK] Tokens used: {response.tokens_used}")
            
            # Test embedding generation
            print("   -> Testing embedding generation...")
            embeddings = await self.provider.generate_embeddings(["test"])
            
            if not embeddings or len(embeddings) != 1:
                print("   [WARN] Embedding generation failed")
                return False
            
            embedding = embeddings[0]
            if not embedding.embeddings or len(embedding.embeddings) == 0:
                print("   [WARN] Empty embedding vector")
                return False
            
            print(f"   [OK] Embedding generated: {embedding.dimensions} dimensions")
            
            total_time = (time.time() - start_time) * 1000
            print(f"   [OK] LLM connectivity PASSED ({total_time:.1f}ms total)")
            return True
            
        except Exception as e:
            print(f"   [FAIL] LLM connectivity FAILED: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all tests and print results."""
        self.print_header()
        
        # Run tests in sequence
        self.test_results["config_validation"] = self.test_configuration_validation()
        self.test_results["provider_creation"] = self.test_provider_creation()
        self.test_results["implementation_patterns"] = self.test_implementation_patterns()
        self.test_results["llm_connectivity"] = await self.test_llm_connectivity()
        
        # Calculate overall result
        self.test_results["overall_success"] = all([
            self.test_results["config_validation"],
            self.test_results["provider_creation"],
            self.test_results["implementation_patterns"],
            self.test_results["llm_connectivity"]
        ])
        
        # Print summary
        print("-" * 60)
        print("TEST SUMMARY:")
        print("-" * 60)
        
        for test_name, passed in self.test_results.items():
            if test_name == "overall_success":
                continue
            status = "PASS" if passed else "FAIL"
            symbol = "[OK]" if passed else "[FAIL]"
            print(f"{symbol} {test_name.replace('_', ' ').title()}: {status}")
        
        print("-" * 60)
        overall_status = "SUCCESS" if self.test_results["overall_success"] else "FAILURE"
        print(f"OVERALL RESULT: {overall_status}")
        print("=" * 60)
        
        return self.test_results["overall_success"]


async def main():
    """Main function."""
    try:
        suite = ProviderTestSuite()
        success = await suite.run_all_tests()
        
        # Return appropriate exit code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())