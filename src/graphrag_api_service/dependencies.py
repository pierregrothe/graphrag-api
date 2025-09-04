# src/graphrag_api_service/dependencies.py
# Dependency injection and service initialization
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Dependency injection and service initialization for GraphRAG API Service."""

import warnings
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from .auth.api_keys import get_api_key_manager
from .auth.jwt_auth import JWTConfig
from .caching.redis_cache import RedisCacheConfig, get_redis_cache, initialize_redis_cache
from .config import settings
from .graph import GraphOperations
from .graphql.subscriptions import get_subscription_manager
from .graphrag_integration import GraphRAGIntegration
from .indexing import IndexingManager
from .logging_config import get_logger
from .monitoring.tracing import TracingConfig, initialize_tracing, shutdown_tracing
from .performance.cache_manager import cleanup_cache_manager, get_cache_manager
from .performance.compression import get_performance_middleware
from .performance.connection_pool import cleanup_connection_pool, get_connection_pool
from .performance.memory_optimizer import get_memory_optimizer
from .performance.monitoring import cleanup_performance_monitor, get_performance_monitor
from .providers import LLMProviderFactory, register_providers
from .security.middleware import get_security_middleware
from .workspace import WorkspaceManager

# Suppress passlib bcrypt warnings
warnings.filterwarnings("ignore", category=UserWarning, module="passlib")

logger = get_logger(__name__)


class ServiceContainer:
    """Container for all application services and dependencies.

    This class manages the lifecycle of all application services and provides
    dependency injection for FastAPI endpoints.

    Attributes
    ----------
    database_manager : SQLiteManager | None
        Database manager instance
    auth_service : AuthService | None
        Authentication service instance
    workspace_manager : WorkspaceManager | None
        Workspace management service instance
    graph_operations : GraphOperations | None
        Graph operations service instance
    cache_manager : CacheManager | None
        Cache manager instance
    performance_monitor : PerformanceMonitor | None
        Performance monitoring service instance
    """

    def __init__(self) -> None:
        from .auth.jwt_auth import AuthenticationService
        from .database.simple_connection import SimpleDatabaseManager
        from .performance.compression import PerformanceMiddleware
        from .security.middleware import SecurityMiddleware
        from .system.operations import SystemOperations

        self.database_manager: SimpleDatabaseManager | None = None
        self.auth_service: AuthenticationService | None = None
        self.workspace_manager: WorkspaceManager | None = None
        self.workspace_cleanup_service: Any | None = None
        self.indexing_manager: IndexingManager | None = None
        self.graphrag_integration: GraphRAGIntegration | None = None
        self.graph_operations: GraphOperations | None = None
        self.system_operations: SystemOperations | None = None
        self.security_middleware: SecurityMiddleware | None = None
        self.performance_middleware: PerformanceMiddleware | None = None
        self.initialized = False
        self._initializing = False

    def ensure_initialized(self) -> None:
        """Ensure the service container is initialized synchronously (for app setup)."""
        if self.initialized or self._initializing:
            return

        self._initializing = True
        try:
            # Initialize core services synchronously for app setup
            from .database.simple_connection import SimpleDatabaseManager
            from .graph.operations import GraphOperations
            from .graphrag_integration import GraphRAGIntegration
            from .indexing.manager import IndexingManager
            from .security.middleware import get_security_middleware
            from .system.operations import SystemOperations
            from .workspace.manager import WorkspaceManager

            # Initialize database manager (using SQLite)
            try:
                self.database_manager = SimpleDatabaseManager(settings)
                logger.info("SQLite database manager initialized successfully")
            except Exception as e:
                logger.warning(
                    f"Database initialization failed, falling back to file-based storage: {e}"
                )
                self.database_manager = None

            # Initialize core services
            self.workspace_manager = WorkspaceManager(settings, self.database_manager)
            self.indexing_manager = IndexingManager(settings)
            self.graph_operations = GraphOperations(settings)

            # Initialize GraphRAG integration with provider
            try:
                from .providers.factory import LLMProviderFactory
                from .providers.registry import register_providers

                # Register providers first
                register_providers()
                provider = LLMProviderFactory.create_provider(settings)
                self.graphrag_integration = GraphRAGIntegration(settings, provider)
                logger.info("GraphRAG integration initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize GraphRAG integration: {e}")
                self.graphrag_integration = None

            self.system_operations = SystemOperations(settings)

            # Initialize middleware
            self.security_middleware = get_security_middleware()
            # Note: Using None for performance_middleware in sync init to avoid API mismatch
            # The auth middleware expects a metrics recorder with record_request method
            self.performance_middleware = None

            self.initialized = True
            logger.info("Core services initialized successfully (synchronous)")
        finally:
            self._initializing = False

    async def initialize(self) -> None:
        """Initialize all services."""
        if self.initialized:
            return

        logger.info(f"Initializing services for {settings.app_name} v{settings.app_version}")

        # Initialize database manager (using SQLite)
        try:
            from .database.simple_connection import get_simple_database_manager

            self.database_manager = get_simple_database_manager(settings)
            if self.database_manager:
                self.database_manager.initialize()
            logger.info("SQLite database manager initialized successfully")
        except Exception as e:
            logger.warning(
                f"Database initialization failed, falling back to file-based storage: {e}"
            )
            self.database_manager = None

        # Initialize core services
        self.workspace_manager = WorkspaceManager(settings, self.database_manager)

        # Initialize workspace cleanup service
        from .workspace.cleanup import get_cleanup_service

        self.workspace_cleanup_service = get_cleanup_service(settings, self.workspace_manager)

        self.indexing_manager = IndexingManager(settings)
        self.graph_operations = GraphOperations(settings)

        # Initialize middleware
        self.security_middleware = get_security_middleware()
        self.performance_middleware = get_performance_middleware()

        # Register LLM providers
        register_providers()
        logger.info("LLM providers registered successfully")

        # Initialize GraphRAG integration with provider
        try:
            provider = LLMProviderFactory.create_provider(settings)
            self.graphrag_integration = GraphRAGIntegration(settings, provider)
            logger.info("GraphRAG integration initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize GraphRAG integration: {e}")
            self.graphrag_integration = None

        # System operations will be handled by individual route handlers
        self.system_operations = None
        logger.info("Core services initialized successfully")

        # Start indexing manager
        await self.indexing_manager.start()
        logger.info("Indexing manager started successfully")

        # Start workspace cleanup service
        if self.workspace_cleanup_service:
            await self.workspace_cleanup_service.start()
            logger.info("Workspace cleanup service started successfully")

        # Initialize advanced features
        await self._initialize_advanced_features()

        # Initialize performance components
        await self._initialize_performance_components()

    async def _initialize_advanced_features(self) -> None:
        """Initialize Phase 11 advanced features."""
        try:
            # Initialize distributed tracing
            if getattr(settings, "tracing_enabled", False):
                tracing_config = TracingConfig(
                    service_name=settings.app_name,
                    service_version=settings.app_version,
                    environment=getattr(settings, "environment", "development"),
                    jaeger_endpoint=getattr(settings, "jaeger_endpoint", None),
                    otlp_endpoint=getattr(settings, "otlp_endpoint", None),
                )
                initialize_tracing(tracing_config)
                logger.info("Distributed tracing initialized")

            # Initialize Redis cache if configured
            if getattr(settings, "redis_enabled", False):
                redis_config = RedisCacheConfig(
                    host=getattr(settings, "redis_host", "localhost"),
                    port=getattr(settings, "redis_port", 6379),
                    password=getattr(settings, "redis_password", None),
                )
                await initialize_redis_cache(redis_config)
                logger.info("Redis distributed cache initialized")

            # Initialize subscription manager
            await get_subscription_manager()
            logger.info("GraphQL subscription manager initialized")

            # Initialize authentication service
            if getattr(settings, "auth_enabled", True):
                jwt_config = JWTConfig(
                    secret_key=getattr(settings, "secret_key", "default-secret-key"),
                    access_token_expire_minutes=getattr(
                        settings, "access_token_expire_minutes", 30
                    ),
                )

                # Use simple authentication service
                if self.database_manager:
                    from .auth.jwt_auth import AuthenticationService as JWTAuthService

                    self.auth_service = JWTAuthService(jwt_config, self.database_manager)
                    if self.auth_service and hasattr(self.auth_service, "rbac"):
                        get_api_key_manager(self.auth_service.rbac)
                    logger.info("Authentication service initialized with database support")
                else:
                    logger.warning("Database manager not available for authentication")

            logger.info("Advanced features initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize advanced features: {e}")
            # Continue without advanced features

    async def _initialize_performance_components(self) -> None:
        """Initialize performance monitoring components."""
        try:
            # Initialize connection pool with database manager
            await get_connection_pool(self.database_manager)
            logger.info("Connection pool initialized successfully")

            # Initialize cache manager
            await get_cache_manager()
            logger.info("Cache manager initialized successfully")

            # Initialize performance monitor
            await get_performance_monitor()
            logger.info("Performance monitoring started successfully")

            # Initialize memory optimizer
            get_memory_optimizer()
            logger.info("Memory optimizer initialized successfully")

            logger.info("All performance components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize performance components: {e}")

    async def _shutdown_database(self) -> None:
        """Shutdown database connections."""
        try:
            if self.database_manager:
                self.database_manager.close()
                logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")

    async def _shutdown_performance_components(self) -> None:
        """Shutdown performance monitoring components."""
        try:
            await cleanup_performance_monitor()
            await cleanup_cache_manager()
            await cleanup_connection_pool()
            logger.info("Performance components shut down successfully")
        except Exception as e:
            logger.error(f"Error shutting down performance components: {e}")

    async def _shutdown_advanced_features(self) -> None:
        """Shutdown advanced features like tracing and caching."""
        try:
            # Shutdown distributed tracing
            shutdown_tracing()

            # Shutdown Redis cache
            redis_cache = await get_redis_cache()
            if redis_cache:
                await redis_cache.disconnect()

            # Shutdown subscription manager
            subscription_manager = await get_subscription_manager()
            if subscription_manager:
                await subscription_manager.stop()

            logger.info("Advanced features shut down successfully")
        except Exception as e:
            logger.error(f"Error shutting down advanced features: {e}")

    async def _shutdown_indexing_manager(self) -> None:
        """Shutdown indexing manager."""
        if self.indexing_manager:
            await self.indexing_manager.stop()
            logger.info("Indexing manager stopped")

    async def _shutdown_workspace_cleanup(self) -> None:
        """Shutdown workspace cleanup service."""
        if self.workspace_cleanup_service:
            await self.workspace_cleanup_service.stop()
            logger.info("Workspace cleanup service stopped")

    async def shutdown(self) -> None:
        """Shutdown all services."""
        logger.info("Shutting down services")

        await self._shutdown_database()
        await self._shutdown_performance_components()
        await self._shutdown_advanced_features()
        await self._shutdown_indexing_manager()
        await self._shutdown_workspace_cleanup()

        logger.info("All services shut down successfully")


# Global service container
service_container = ServiceContainer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    await service_container.initialize()
    yield
    await service_container.shutdown()


def get_service_container() -> ServiceContainer:
    """Get the global service container, ensuring it's initialized."""
    service_container.ensure_initialized()
    return service_container
