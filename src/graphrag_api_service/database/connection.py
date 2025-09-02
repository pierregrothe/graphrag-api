# src/graphrag_api_service/database/connection.py
# Database connection management
# Author: Pierre Grothé
# Creation Date: 2025-09-01

"""Database connection management and session handling."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from ..deployment.config import DeploymentSettings
from .base import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, settings: DeploymentSettings):
        """Initialize database manager.

        Args:
            settings: Deployment settings containing database configuration
        """
        self.settings = settings
        self.async_engine = None
        self.sync_engine = None
        self.async_session_factory = None
        self.sync_session_factory = None

    async def initialize(self):
        """Initialize database connections."""
        try:
            # Create async engine for main operations
            database_url = self.settings.get_database_url()
            async_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

            self.async_engine = create_async_engine(
                async_url,
                pool_size=self.settings.database.pool_size,
                max_overflow=self.settings.database.max_overflow,
                pool_timeout=self.settings.database.pool_timeout,
                echo=self.settings.debug,
            )

            # Create sync engine for migrations
            self.sync_engine = create_engine(
                database_url,
                pool_size=self.settings.database.pool_size,
                max_overflow=self.settings.database.max_overflow,
                pool_timeout=self.settings.database.pool_timeout,
                echo=self.settings.debug,
            )

            # Create session factories
            self.async_session_factory = async_sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            self.sync_session_factory = sessionmaker(
                bind=self.sync_engine,
                expire_on_commit=False,
            )

            logger.info("Database connections initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database connections: {e}")
            raise

    async def create_tables(self):
        """Create all database tables."""
        try:
            async with self.async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session.

        Yields:
            AsyncSession: Database session
        """
        if not self.async_session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    def get_sync_session(self):
        """Get a sync database session for migrations.

        Returns:
            Session: Sync database session
        """
        if not self.sync_session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.sync_session_factory()

    async def close(self):
        """Close database connections."""
        if self.async_engine:
            await self.async_engine.dispose()
        if self.sync_engine:
            self.sync_engine.dispose()
        logger.info("Database connections closed")

    async def health_check(self) -> bool:
        """Check database connectivity.

        Returns:
            True if database is accessible
        """
        try:
            async with self.get_session() as session:
                await session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database manager
_database_manager: DatabaseManager | None = None


def get_database_manager(settings: DeploymentSettings = None) -> DatabaseManager:
    """Get the global database manager.

    Args:
        settings: Optional deployment settings

    Returns:
        DatabaseManager instance
    """
    global _database_manager

    if _database_manager is None:
        if not settings:
            from ..deployment.config import DeploymentSettings

            settings = DeploymentSettings()
        _database_manager = DatabaseManager(settings)

    return _database_manager
