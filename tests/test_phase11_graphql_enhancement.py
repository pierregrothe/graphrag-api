# tests/test_phase11_graphql_enhancement.py
# Tests for Phase 11: Advanced Monitoring & GraphQL Enhancement
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Comprehensive tests for Phase 11 GraphQL enhancements and monitoring systems."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graphrag_api_service.auth.api_keys import APIKeyManager, APIKeyPermissions, APIKeyRequest
from src.graphrag_api_service.auth.jwt_auth import (
    AuthenticationService,
    JWTConfig,
    JWTManager,
    TokenData,
)
from src.graphrag_api_service.caching.redis_cache import (
    GraphRAGRedisCache,
    RedisCacheConfig,
    RedisDistributedCache,
)
from src.graphrag_api_service.graphql.optimization import (
    FieldSelector,
    QueryCache,
    QueryComplexityAnalyzer,
)
from src.graphrag_api_service.graphql.subscriptions import SubscriptionManager
from src.graphrag_api_service.graphql.testing import GraphQLTestCase, GraphQLTestSuiteBuilder
from src.graphrag_api_service.monitoring.prometheus import PrometheusMetrics
from src.graphrag_api_service.monitoring.tracing import (
    GraphQLTracingExtension,
    TracingConfig,
    TracingManager,
)


class TestGraphQLOptimization:
    """Test GraphQL query optimization features."""

    def test_field_selector_initialization(self):
        """Test field selector initialization."""
        field_selector = FieldSelector()
        assert field_selector is not None
        assert "Entity" in field_selector._field_mappings
        assert "Relationship" in field_selector._field_mappings

    def test_field_selector_get_selected_fields(self):
        """Test field selection extraction."""
        field_selector = FieldSelector()

        # Mock GraphQL info
        mock_info = MagicMock()
        mock_info.field_nodes = []

        selected_fields = field_selector.get_selected_fields("Entity", mock_info)
        assert isinstance(selected_fields, set)

    def test_query_complexity_analyzer(self):
        """Test query complexity analysis."""
        analyzer = QueryComplexityAnalyzer(max_complexity=100)
        assert analyzer.max_complexity == 100
        assert analyzer._field_costs["id"] == 1
        assert analyzer._field_costs["entities"] == 20

    def test_query_cache_operations(self):
        """Test query cache operations."""
        cache = QueryCache()

        # Test cache key generation
        cache_key = cache.generate_cache_key("entities", {"limit": 10}, {"id", "title"})
        assert isinstance(cache_key, str)
        assert len(cache_key) == 16  # SHA256 hash truncated to 16 chars

        # Test cache operations
        cache.set(cache_key, {"test": "data"}, ttl=300)
        result = cache.get(cache_key)
        assert result is not None
        assert result["result"]["test"] == "data"


class TestGraphQLTesting:
    """Test GraphQL testing framework."""

    def test_graphql_test_case_creation(self):
        """Test GraphQL test case creation."""
        test_case = GraphQLTestCase(
            name="test_entities",
            query="query { entities { id title } }",
            variables={"limit": 10},
            expected_data={"entities": []},
        )

        assert test_case.name == "test_entities"
        assert "entities" in test_case.query
        assert test_case.variables["limit"] == 10

    def test_test_suite_builder(self):
        """Test GraphQL test suite builder."""
        builder = GraphQLTestSuiteBuilder()
        builder.add_entity_tests()
        builder.add_relationship_tests()

        test_cases = builder.build_comprehensive_suite()
        assert len(test_cases) > 0

        # Check that entity tests were added
        entity_tests = [tc for tc in test_cases if "entity" in tc.name.lower()]
        assert len(entity_tests) > 0


class TestGraphQLSubscriptions:
    """Test GraphQL subscription system."""

    @pytest.mark.asyncio
    async def test_subscription_manager_lifecycle(self):
        """Test subscription manager lifecycle."""
        manager = SubscriptionManager()

        # Test start/stop
        await manager.start()
        assert manager._running is True

        await manager.stop()
        assert manager._running is False

    @pytest.mark.asyncio
    async def test_subscription_publish_subscribe(self):
        """Test publish/subscribe functionality."""
        manager = SubscriptionManager()
        await manager.start()

        # Test publishing
        test_data = {"entity_id": "test-1", "action": "created"}
        await manager.publish("entity_updates", test_data)

        # Test subscriber count
        count = manager.get_subscriber_count("entity_updates")
        assert count == 0  # No active subscribers

        await manager.stop()


class TestPrometheusMetrics:
    """Test Prometheus metrics collection."""

    def test_prometheus_metrics_initialization(self):
        """Test Prometheus metrics initialization."""
        metrics = PrometheusMetrics()
        assert metrics is not None
        assert metrics.request_count is not None
        assert metrics.graphql_query_count is not None

    def test_record_request_metrics(self):
        """Test recording request metrics."""
        metrics = PrometheusMetrics()

        # Record a request
        metrics.record_request("GET", "/api/entities", 200, 0.5)

        # Verify metrics were recorded
        metric_output = metrics.get_metrics()
        assert "graphrag_requests_total" in metric_output
        assert "graphrag_request_duration_seconds" in metric_output

    def test_record_graphql_metrics(self):
        """Test recording GraphQL metrics."""
        metrics = PrometheusMetrics()

        # Record a GraphQL query
        metrics.record_graphql_query("query", "getEntities", 0.3, 50)

        # Verify metrics were recorded
        metric_output = metrics.get_metrics()
        assert "graphrag_graphql_queries_total" in metric_output
        assert "graphrag_graphql_query_duration_seconds" in metric_output

    def test_cache_metrics(self):
        """Test cache metrics recording."""
        metrics = PrometheusMetrics()

        # Record cache operations
        metrics.record_cache_hit("entities")
        metrics.record_cache_miss("relationships")
        metrics.update_cache_metrics("entities", 1024, 100)

        # Verify metrics
        metric_output = metrics.get_metrics()
        assert "graphrag_cache_hits_total" in metric_output
        assert "graphrag_cache_misses_total" in metric_output


class TestDistributedTracing:
    """Test OpenTelemetry distributed tracing."""

    def test_tracing_config(self):
        """Test tracing configuration."""
        config = TracingConfig(
            service_name="test-service", jaeger_endpoint="http://localhost:14268", sample_rate=0.5
        )

        assert config.service_name == "test-service"
        assert config.sample_rate == 0.5

    def test_tracing_manager_initialization(self):
        """Test tracing manager initialization."""
        config = TracingConfig(service_name="test-service")
        manager = TracingManager(config)

        assert manager.config.service_name == "test-service"
        assert manager.tracer_provider is None  # Not initialized yet

    def test_graphql_tracing_extension(self):
        """Test GraphQL tracing extension."""
        config = TracingConfig(service_name="test-service")
        manager = TracingManager(config)
        extension = GraphQLTracingExtension(manager)

        assert extension.tracing_manager == manager


class TestJWTAuthentication:
    """Test JWT authentication system."""

    def test_jwt_config(self):
        """Test JWT configuration."""
        config = JWTConfig(secret_key="test-secret", access_token_expire_minutes=15)

        assert config.secret_key == "test-secret"
        assert config.access_token_expire_minutes == 15

    def test_jwt_manager_token_creation(self):
        """Test JWT token creation."""
        config = JWTConfig(secret_key="test-secret")
        manager = JWTManager(config)

        token_data = TokenData(
            user_id="user-1",
            username="testuser",
            email="test@example.com",
            roles=["user"],
            permissions=["read:entities"],
            expires_at=datetime.now(UTC),
        )

        # Create access token
        access_token = manager.create_access_token(token_data)
        assert isinstance(access_token, str)
        assert len(access_token) > 0

        # Verify token
        payload = manager.verify_token(access_token)
        assert payload["sub"] == "user-1"
        assert payload["username"] == "testuser"

    def test_password_hashing(self):
        """Test password hashing and verification."""
        config = JWTConfig(secret_key="test-secret")
        manager = JWTManager(config)

        password = "test-password"
        hashed = manager.hash_password(password)

        assert hashed != password
        assert manager.verify_password(password, hashed) is True
        assert manager.verify_password("wrong-password", hashed) is False


class TestAPIKeyManagement:
    """Test API key management system."""

    @pytest.mark.asyncio
    async def test_api_key_creation(self):
        """Test API key creation."""
        manager = APIKeyManager()

        request = APIKeyRequest(
            name="test-key", permissions=[APIKeyPermissions.READ_ENTITIES], rate_limit=100
        )

        response = await manager.create_api_key("user-1", request)

        assert response.name == "test-key"
        assert len(response.key) > 0
        assert response.prefix.startswith("grag_")
        assert APIKeyPermissions.READ_ENTITIES in response.permissions

    @pytest.mark.asyncio
    async def test_api_key_validation(self):
        """Test API key validation."""
        manager = APIKeyManager()

        # Create a key
        request = APIKeyRequest(name="test-key", permissions=[APIKeyPermissions.READ_ENTITIES])
        response = await manager.create_api_key("user-1", request)

        # Validate the key
        api_key = await manager.validate_api_key(response.key)
        assert api_key is not None
        assert api_key.name == "test-key"
        assert api_key.user_id == "user-1"

    @pytest.mark.asyncio
    async def test_api_key_rate_limiting(self):
        """Test API key rate limiting."""
        manager = APIKeyManager()

        # Create a key with low rate limit
        request = APIKeyRequest(
            name="rate-limited-key",
            permissions=[APIKeyPermissions.READ_ENTITIES],
            rate_limit=1,  # Only 1 request per hour
        )
        response = await manager.create_api_key("user-1", request)

        # First validation should succeed
        api_key1 = await manager.validate_api_key(response.key)
        assert api_key1 is not None

        # Second validation should fail due to rate limit
        api_key2 = await manager.validate_api_key(response.key)
        assert api_key2 is None


class TestRedisCache:
    """Test Redis distributed caching."""

    def test_redis_cache_config(self):
        """Test Redis cache configuration."""
        config = RedisCacheConfig(host="localhost", port=6379, default_ttl=3600)

        assert config.host == "localhost"
        assert config.port == 6379
        assert config.default_ttl == 3600

    @pytest.mark.asyncio
    async def test_redis_cache_operations(self):
        """Test Redis cache operations (mocked)."""
        config = RedisCacheConfig()
        cache = RedisDistributedCache(config)

        # Mock Redis client
        with patch("redis.asyncio.Redis") as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            mock_client.get.return_value = None
            mock_client.setex.return_value = True

            cache.redis_client = mock_client
            cache._connected = True

            # Test cache operations
            result = await cache.get("test", "key1")
            assert result is None

            success = await cache.set("test", "key1", {"data": "value"})
            assert success is True

    def test_graphrag_redis_cache(self):
        """Test GraphRAG-specific Redis cache."""
        config = RedisCacheConfig()
        redis_cache = RedisDistributedCache(config)
        graphrag_cache = GraphRAGRedisCache(redis_cache)

        assert graphrag_cache.redis_cache == redis_cache
        assert "entities" in graphrag_cache.namespaces
        assert "relationships" in graphrag_cache.namespaces


class TestIntegration:
    """Test integration between different Phase 11 components."""

    def test_metrics_and_tracing_integration(self):
        """Test integration between metrics and tracing."""
        # Initialize metrics
        metrics = PrometheusMetrics()

        # Initialize tracing
        tracing_config = TracingConfig(service_name="test-service")
        tracing_manager = TracingManager(tracing_config)

        # Test that both can coexist
        assert metrics is not None
        assert tracing_manager is not None

    @pytest.mark.asyncio
    async def test_auth_and_caching_integration(self):
        """Test integration between authentication and caching."""
        # Initialize JWT auth
        jwt_config = JWTConfig(secret_key="test-secret")
        # Create a mock database manager for testing
        from unittest.mock import MagicMock

        mock_db_manager = MagicMock()
        auth_service = AuthenticationService(jwt_config, mock_db_manager)

        # Initialize API key manager
        api_key_manager = APIKeyManager()

        # Initialize cache
        cache_config = RedisCacheConfig()
        redis_cache = RedisDistributedCache(cache_config)

        # Test that all components can be initialized together
        assert auth_service is not None
        assert api_key_manager is not None
        assert redis_cache is not None


if __name__ == "__main__":
    pytest.main([__file__])
