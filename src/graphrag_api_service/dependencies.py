# src/graphrag_api_service/dependencies.py
# Dependency injection and service initialization
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Dependency injection and service initialization for GraphRAG API Service."""

import warnings
from contextlib import asynccontextmanager

from fastapi import FastAPI

# Suppress passlib bcrypt warnings
warnings.filterwarnings("ignore", category=UserWarning, module="passlib")

from .auth.api_keys import get_api_key_manager
from .auth.database_auth import DatabaseAuthenticationService
from .auth.jwt_auth import JWTConfig
from .caching.redis_cache import RedisCacheConfig, get_redis_cache, initialize_redis_cache
from .config import settings
from .database import get_database_manager
from .graph import GraphOperations
from .graphql.subscriptions import get_subscription_manager
from .graphrag_integration import GraphRAGIntegration
from .indexing import IndexingManager
from .logging_config import get_logger
from .monitoring.prometheus import get_metrics
from .monitoring.tracing import TracingConfig, initialize_tracing, shutdown_tracing
from .performance.cache_manager import cleanup_cache_manager, get_cache_manager
from .performance.compression import get_performance_middleware
from .performance.connection_pool import cleanup_connection_pool, get_connection_pool
from .performance.memory_optimizer import get_memory_optimizer
from .performance.monitoring import cleanup_performance_monitor, get_performance_monitor
from .providers import LLMProviderFactory, register_providers
from .security.middleware import get_security_middleware
from .workspace import WorkspaceManager

logger = get_logger(__name__)


class ServiceContainer:
    """Container for all application services and dependencies."""

    def __init__(self):
        self.database_manager = None
        self.auth_service = None
        self.workspace_manager = None
        self.indexing_manager = None
        self.graphrag_integration = None
        self.graph_operations = None
        self.system_operations = None
        self.security_middleware = None
        self.performance_middleware = None

    async def initialize(self):
        """Initialize all services."""
        logger.info(f"Initializing services for {settings.app_name} v{settings.app_version}")

        # Initialize database manager first
        try:
            from ..deployment.config import DeploymentSettings

            deployment_settings = DeploymentSettings()
            self.database_manager = get_database_manager(deployment_settings)
            await self.database_manager.initialize()
            await self.database_manager.create_tables()
            logger.info("Database manager initialized successfully")
        except Exception as e:
            logger.warning(
                f"Database initialization failed, falling back to file-based storage: {e}"
            )
            self.database_manager = None

        # Initialize core services
        self.workspace_manager = WorkspaceManager(settings, self.database_manager)
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

        # Initialize advanced features
        await self._initialize_advanced_features()

        # Initialize performance components
        await self._initialize_performance_components()

    async def _initialize_advanced_features(self):
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
            subscription_manager = await get_subscription_manager()
            logger.info("GraphQL subscription manager initialized")

            # Initialize authentication service
            if getattr(settings, "auth_enabled", True):
                jwt_config = JWTConfig(
                    secret_key=getattr(settings, "secret_key", "default-secret-key"),
                    access_token_expire_minutes=getattr(
                        settings, "access_token_expire_minutes", 30
                    ),
                )

                # Use database-backed authentication if database is available
                if self.database_manager:
                    self.auth_service = DatabaseAuthenticationService(
                        jwt_config, self.database_manager.async_session_factory
                    )

                    # Create default roles
                    await self.auth_service.create_default_roles()

                    # Initialize API key manager with RBAC
                    api_key_manager = get_api_key_manager(self.auth_service.rbac)
                    logger.info("Database-backed authentication service initialized")

                    # Create default admin user if none exists
                    try:
                        await self.auth_service.create_user(
                            username="admin",
                            email="admin@graphrag.local",
                            password=getattr(settings, "default_admin_password", "admin123"),
                            roles=["admin"],
                        )
                        logger.info("Default admin user created")
                    except Exception as e:
                        logger.debug(f"Admin user already exists or creation failed: {e}")

                else:
                    # Fallback to in-memory authentication
                    from .auth.jwt_auth import AuthenticationService

                    self.auth_service = AuthenticationService(jwt_config)
                    api_key_manager = get_api_key_manager(self.auth_service.rbac)
                    logger.warning("Using in-memory authentication (database not available)")

            logger.info("Advanced features initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize advanced features: {e}")
            # Continue without advanced features

    async def _initialize_performance_components(self):
        """Initialize performance monitoring components."""
        try:
            # Initialize connection pool with database manager
            connection_pool = await get_connection_pool(self.database_manager)
            logger.info("Connection pool initialized successfully")

            # Initialize cache manager
            cache_manager = await get_cache_manager()
            logger.info("Cache manager initialized successfully")

            # Initialize performance monitor
            performance_monitor = await get_performance_monitor()
            logger.info("Performance monitoring started successfully")

            # Initialize memory optimizer
            memory_optimizer = get_memory_optimizer()
            logger.info("Memory optimizer initialized successfully")

            logger.info("All performance components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize performance components: {e}")

    async def shutdown(self):
        """Shutdown all services."""
        logger.info("Shutting down services")

        # Shutdown database connections
        try:
            if self.database_manager:
                await self.database_manager.close()
                logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")

        # Shutdown performance components
        try:
            await cleanup_performance_monitor()
            await cleanup_cache_manager()
            await cleanup_connection_pool()
            logger.info("Performance components shut down successfully")
        except Exception as e:
            logger.error(f"Error shutting down performance components: {e}")

        # Shutdown advanced features
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

        # Shutdown indexing manager
        if self.indexing_manager:
            await self.indexing_manager.stop()
            logger.info("Indexing manager stopped")

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
    """Get the global service container."""
    return service_container
