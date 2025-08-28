# src/graphrag_api_service/config.py
# Configuration management for GraphRAG API Service
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Configuration settings for the GraphRAG API service."""

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables."""

    # API Settings
    app_name: str = "GraphRAG API Service"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000

    # GraphRAG Settings
    graphrag_config_path: str | None = None
    graphrag_data_path: str | None = None

    # Logging Settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Global settings instance
settings = Settings()
