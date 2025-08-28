# src/graphrag_api_service/providers/gemini_provider.py
# Google Gemini LLM provider implementation for GraphRAG API Service
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Google Gemini provider implementation for cloud-based LLM inference."""

import asyncio
import time
from typing import Any

import google.generativeai as genai
from google.generativeai import GenerationConfig
from google.generativeai.types import HarmBlockThreshold, HarmCategory

from .base import EmbeddingResponse, GraphRAGLLM, LLMResponse, ProviderHealth


class GeminiGraphRAGLLM(GraphRAGLLM):
    """Google Gemini provider implementation for cloud-based LLM inference.

    This provider integrates with Google's Gemini models via the generativeai
    library for high-performance cloud-based text generation and embeddings.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize Gemini provider with configuration.

        Args:
            config: Configuration containing api_key, project_id, models, etc.
        """
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.project_id = config.get("project_id")
        self.location = config.get("location", "us-central1")
        self.llm_model = config.get("llm_model", "gemini-2.5-flash")
        self.embedding_model = config.get("embedding_model", "text-embedding-004")

        if not self.api_key:
            raise ValueError("Google API key is required for Gemini provider")
        if not self.project_id:
            raise ValueError("Google project ID is required for Gemini provider")

        # Configure the generative AI client
        genai.configure(api_key=self.api_key)

        # Initialize the model
        self.model = genai.GenerativeModel(
            model_name=self.llm_model,
            generation_config=GenerationConfig(
                temperature=0.1,
                max_output_tokens=1500,
            ),
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
        )

    def _get_provider_name(self) -> str:
        """Get the provider name identifier.

        Returns:
            String identifier for the provider
        """
        return "google_gemini"

    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 1500,
        temperature: float = 0.1,
        **kwargs: Any
    ) -> LLMResponse:
        """Generate text response using Gemini LLM.

        Args:
            prompt: Input prompt for text generation
            max_tokens: Maximum tokens to generate
            temperature: Generation temperature (0.0-1.0)
            **kwargs: Additional Gemini-specific parameters

        Returns:
            LLMResponse containing generated text and metadata

        Raises:
            Exception: If generation fails or Gemini API is unavailable
        """
        try:
            # Update generation config for this request
            generation_config = GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                **kwargs
            )

            # Create a new model instance with updated config
            model = genai.GenerativeModel(
                model_name=self.llm_model,
                generation_config=generation_config,
                safety_settings=self.model.safety_settings
            )

            # Generate content asynchronously
            response = await model.generate_content_async(prompt)

            # Extract response data
            content = response.text if response.text else ""

            # Estimate token usage (Gemini doesn't provide exact counts in free tier)
            estimated_tokens = len(prompt.split()) + len(content.split())

            return LLMResponse(
                content=content,
                tokens_used=estimated_tokens,
                model=self.llm_model,
                provider=self.provider_name,
                metadata={
                    "finish_reason": response.candidates[0].finish_reason.name if response.candidates else "UNKNOWN",
                    "safety_ratings": [
                        {
                            "category": rating.category.name,
                            "probability": rating.probability.name
                        }
                        for rating in response.candidates[0].safety_ratings
                    ] if response.candidates else [],
                    "prompt_feedback": {
                        "block_reason": response.prompt_feedback.block_reason.name if response.prompt_feedback.block_reason else None,
                        "safety_ratings": [
                            {
                                "category": rating.category.name,
                                "probability": rating.probability.name
                            }
                            for rating in response.prompt_feedback.safety_ratings
                        ] if response.prompt_feedback.safety_ratings else []
                    } if response.prompt_feedback else {}
                }
            )

        except Exception as e:
            raise Exception(f"Gemini text generation failed: {str(e)}") from e

    async def generate_embeddings(
        self,
        texts: list[str],
        **kwargs: Any
    ) -> list[EmbeddingResponse]:
        """Generate embeddings using Gemini embedding model.

        Args:
            texts: List of texts to embed
            **kwargs: Additional Gemini-specific parameters

        Returns:
            List of EmbeddingResponse objects with embeddings

        Raises:
            Exception: If embedding generation fails
        """
        try:
            embeddings = []

            # Process texts in batches to avoid rate limits
            batch_size = kwargs.get("batch_size", 10)

            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]

                # Generate embeddings for batch
                batch_embeddings = []
                for text in batch:
                    # Use the embedding model
                    result = genai.embed_content(
                        model=f"models/{self.embedding_model}",
                        content=text,
                        task_type="retrieval_document"
                    )

                    embedding_vector = result["embedding"]

                    batch_embeddings.append(EmbeddingResponse(
                        embeddings=embedding_vector,
                        tokens_used=len(text.split()),  # Rough estimate
                        model=self.embedding_model,
                        provider=self.provider_name,
                        dimensions=len(embedding_vector)
                    ))

                embeddings.extend(batch_embeddings)

                # Add small delay between batches to respect rate limits
                if i + batch_size < len(texts):
                    await asyncio.sleep(0.1)

            return embeddings

        except Exception as e:
            raise Exception(f"Gemini embedding generation failed: {str(e)}") from e

    async def health_check(self) -> ProviderHealth:
        """Check the health of the Gemini connection.

        Returns:
            ProviderHealth object with status and details
        """
        try:
            start_time = time.time()

            # Test connection with a simple generation call
            test_model = genai.GenerativeModel(
                model_name=self.llm_model,
                generation_config=GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=10,
                )
            )

            response = await test_model.generate_content_async("Hello")

            latency_ms = (time.time() - start_time) * 1000

            # Check if response is valid
            if not response or not response.text:
                return ProviderHealth(
                    healthy=False,
                    provider=self.provider_name,
                    message="Gemini API returned empty response",
                    latency_ms=latency_ms,
                    model_info={
                        "api_key_configured": bool(self.api_key),
                        "project_id": self.project_id,
                        "llm_model": self.llm_model,
                        "embedding_model": self.embedding_model,
                        "location": self.location,
                        "response_received": False
                    }
                )

            # Test embedding model availability
            try:
                embed_result = genai.embed_content(
                    model=f"models/{self.embedding_model}",
                    content="test",
                    task_type="retrieval_document"
                )
                embedding_available = bool(embed_result.get("embedding"))
            except Exception:
                embedding_available = False

            return ProviderHealth(
                healthy=True,
                provider=self.provider_name,
                message="Gemini connection healthy, models responding",
                latency_ms=latency_ms,
                model_info={
                    "api_key_configured": bool(self.api_key),
                    "project_id": self.project_id,
                    "llm_model": self.llm_model,
                    "embedding_model": self.embedding_model,
                    "location": self.location,
                    "llm_available": True,
                    "embedding_available": embedding_available,
                    "response_length": len(response.text) if response.text else 0
                }
            )

        except Exception as e:
            return ProviderHealth(
                healthy=False,
                provider=self.provider_name,
                message=f"Gemini connection failed: {str(e)}",
                latency_ms=0.0,
                model_info={
                    "api_key_configured": bool(self.api_key),
                    "project_id": self.project_id,
                    "llm_model": self.llm_model,
                    "embedding_model": self.embedding_model,
                    "location": self.location,
                    "error": str(e),
                }
            )
