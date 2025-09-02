# src/graphrag_api_service/database/base.py
# Database base configuration
# Author: Pierre Grothé
# Creation Date: 2025-09-01

"""Database base configuration and utilities."""

from sqlalchemy.orm import declarative_base

# Create the base class for all database models
Base = declarative_base()
