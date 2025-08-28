# src/graphrag_api_service/config.py
# Configuration management for GraphRAG API Service
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Configuration settings for the GraphRAG API service."""

from enum import Enum

from pydantic import ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OLLAMA = "ollama"
    GOOGLE_GEMINI = "google_gemini"


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables."""

    # API Settings
    app_name: str = "GraphRAG API Service"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8001  # Changed from 8000 to avoid common Docker conflicts

    # GraphRAG Settings
    graphrag_config_path: str | None = None
    graphrag_data_path: str | None = None

    # LLM Provider Configuration
    llm_provider: LLMProvider = Field(
        default=LLMProvider.OLLAMA,
        description="LLM provider to use (ollama or google_gemini)",
    )

    # Ollama Configuration (Local)
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama server base URL",
    )
    ollama_llm_model: str = Field(
        default="gemma:4b",
        description="Ollama LLM model name",
    )
    ollama_embedding_model: str = Field(
        default="nomic-embed-text",
        description="Ollama embedding model name",
    )

    # Google Gemini Configuration (Cloud)
    google_api_key: str | None = Field(
        default=None,
        description="Google Cloud API key for Gemini",
    )
    google_project_id: str | None = Field(
        default=None,
        description="Google Cloud project ID",
    )
    google_location: str = Field(
        default="us-central1",
        description="Google Cloud location",
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model version",
    )
    gemini_embedding_model: str = Field(
        default="text-embedding-004",
        description="Gemini embedding model",
    )

    # Logging Settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("google_api_key")
    @classmethod
    def validate_google_api_key(cls, v, info):
        """Validate Google API key when using Google Gemini provider."""
        if info.data.get("llm_provider") == LLMProvider.GOOGLE_GEMINI and not v:
            raise ValueError("google_api_key is required when using google_gemini provider")
        return v

    @field_validator("google_project_id")
    @classmethod
    def validate_google_project_id(cls, v, info):
        """Validate Google project ID when using Google Gemini provider."""
        if info.data.get("llm_provider") == LLMProvider.GOOGLE_GEMINI and not v:
            raise ValueError("google_project_id is required when using google_gemini provider")
        return v

    def is_ollama_provider(self) -> bool:
        """Check if Ollama provider is configured."""
        return self.llm_provider == LLMProvider.OLLAMA

    def is_google_gemini_provider(self) -> bool:
        """Check if Google Gemini provider is configured."""
        return self.llm_provider == LLMProvider.GOOGLE_GEMINI

    def get_provider_info(self) -> dict[str, str | None]:
        """Get current provider configuration info."""
        if self.is_ollama_provider():
            return {
                "provider": "ollama",
                "base_url": self.ollama_base_url,
                "llm_model": self.ollama_llm_model,
                "embedding_model": self.ollama_embedding_model,
            }
        elif self.is_google_gemini_provider():
            return {
                "provider": "google_gemini",
                "project_id": self.google_project_id,
                "location": self.google_location,
                "llm_model": self.gemini_model,
                "embedding_model": self.gemini_embedding_model,
            }
        return {"provider": "unknown"}


# Global settings instance
settings = Settings()
