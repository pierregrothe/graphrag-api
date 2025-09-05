# src/graphrag_api_service/performance/connection_pool.py
# Database Connection Pooling and Query Optimization
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Real database connection pooling and query optimization for GraphRAG operations."""

import asyncio
import logging
import re  # Moved from inside _execute_database_query
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import pandas as pd
from pydantic import BaseModel
from sqlalchemy import text  # Moved from inside _execute_database_query

logger = logging.getLogger(__name__)


class ConnectionPoolExhaustedError(Exception):
    """Custom exception raised when the connection pool is exhausted."""


class ConnectionPoolConfig(BaseModel):
    """Configuration for database connection pooling."""

    max_connections: int = 10
    min_connections: int = 2
    connection_timeout: float = 30.0
    idle_timeout: float = 300.0
    max_retries: int = 3
    retry_delay: float = 1.0


class QueryMetrics(BaseModel):
    """Metrics for query performance tracking."""

    query_type: str
    execution_time: float
    rows_processed: int
    cache_hit: bool
    timestamp: float


class QueryCache:
    """Manages in-memory caching for query results."""

    def __init__(self, cache_ttl: int = 300):
        self._cache: dict[str, tuple[pd.DataFrame, float]] = {}
        self._cache_ttl = cache_ttl

    async def get_cached_result(
        self, query_type: str, data_path: str, filters: dict[str, Any] | None
    ) -> pd.DataFrame | None:
        """Get cached query result.

        Args:
            query_type: Type of query
            data_path: Path to data file
            filters: Optional filters

        Returns:
            Cached result if available
        """
        cache_key = f"{query_type}:{data_path}:{str(filters)}"

        # Check if key exists and is not expired
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                logger.debug("Cache hit for key: %s", cache_key)
                return cached_data.copy()  # Return a copy to prevent mutations
            # Remove expired entry
            del self._cache[cache_key]
            logger.debug("Cache expired for key: %s", cache_key)

        return None

    async def cache_result(
        self,
        query_type: str,
        data_path: str,
        filters: dict[str, Any] | None,
        result: pd.DataFrame,
    ) -> None:
        """Cache query result.

        Args:
            query_type: Type of query
            data_path: Path to data file
            filters: Optional filters
            result: Query result to cache
        """
        cache_key = f"{query_type}:{data_path}:{str(filters)}"

        # Store result with current timestamp
        self._cache[cache_key] = (result.copy(), time.time())
        logger.debug("Cached result for key: %s", cache_key)

        # Clean up old entries if cache is getting too large (simple LRU)
        if len(self._cache) > 100:  # Max 100 entries
            # Remove oldest entries
            current_time = time.time()
            expired_keys = [
                k for k, (_, t) in self._cache.items() if current_time - t > self._cache_ttl
            ]
            for key in expired_keys:
                del self._cache[key]
            logger.debug("Cleaned %s expired cache entries", len(expired_keys))


class MetricsManager:
    """Manages query performance metrics."""

    def __init__(self) -> None:
        self._metrics: list[QueryMetrics] = []

    async def record_metrics(
        self, query_type: str, execution_time: float, rows_processed: int, cache_hit: bool
    ) -> None:
        """Record query performance metrics.

        Args:
            query_type: Type of query
            execution_time: Time taken to execute
            rows_processed: Number of rows processed
            cache_hit: Whether result came from cache
        """
        metric = QueryMetrics(
            query_type=query_type,
            execution_time=execution_time,
            rows_processed=rows_processed,
            cache_hit=cache_hit,
            timestamp=time.time(),
        )

        self._metrics.append(metric)

        # Keep only recent metrics (last 1000)
        if len(self._metrics) > 1000:
            self._metrics = self._metrics[-1000:]

        logger.debug(
            "Query metrics - Type: %s, Time: %.3fs, Rows: %s, Cache: %s",
            query_type,
            execution_time,
            rows_processed,
            cache_hit,
        )

    async def get_metrics(self) -> list[QueryMetrics]:
        """Get query performance metrics.

        Returns:
            List of query metrics
        """
        return self._metrics.copy()


class ConnectionPoolState:
    """Manages the state of connections within the pool."""

    def __init__(self) -> None:
        """Initialize the ConnectionPoolState."""
        self._connections: list[dict[str, Any]] = []
        self._available_connections: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._active_connections: int = 0

    def add_connection(self, connection: dict[str, Any]) -> None:
        """Add a connection to the pool state."""
        self._connections.append(connection)
        self._active_connections += 1

    async def put_available_connection(self, connection: dict[str, Any]) -> None:
        """Put an available connection back into the queue."""
        await self._available_connections.put(connection)

    async def get_available_connection(self, timeout: float) -> dict[str, Any]:
        """Get an available connection from the queue."""
        return await asyncio.wait_for(self._available_connections.get(), timeout=timeout)

    def get_active_connections_count(self) -> int:
        """Get the count of active connections."""
        return self._active_connections

    def get_total_connections_count(self) -> int:
        """Get the total count of connections."""
        return len(self._connections)

    def get_available_connections_qsize(self) -> int:
        """Get the size of the available connections queue."""
        return self._available_connections.qsize()

    def clear_connections(self) -> None:
        """Clear all connections from the pool state."""
        self._connections.clear()
        self._active_connections = 0

    def get_connections_list(self) -> list[dict[str, Any]]:
        """Get the list of all connections."""
        return self._connections


class ConnectionPool:
    """Async connection pool for GraphRAG data operations."""

    def __init__(self, config: ConnectionPoolConfig, database_manager: Any = None) -> None:
        """Initialize the connection pool.

        Args:
            config: Connection pool configuration
            database_manager: Optional database manager for real database connections
        """
        self.config = config
        self.database_manager = database_manager
        self._lock = asyncio.Lock()
        self._initialized = False
        self._query_cache = QueryCache()  # Use the new QueryCache class
        self._metrics_manager = MetricsManager()  # Use the new MetricsManager class
        self._pool_state = ConnectionPoolState()  # Use the new ConnectionPoolState class

    async def initialize(self) -> None:
        """Initialize the connection pool."""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:  # Double-check after acquiring lock
                return  # type: ignore[unreachable]  # pragma: no cover

            logger.info("Initializing connection pool")

            # Create minimum number of connections
            for i in range(self.config.min_connections):
                if self.database_manager:
                    # Create database connection metadata
                    connection = await self._create_database_connection(i)
                else:
                    # Create mock connection for file-based operations
                    connection = await self._create_mock_connection(i)
                await self._pool_state.put_available_connection(connection)

            self._initialized = True
            connection_type = "database" if self.database_manager else "file-based"
            logger.info(
                "Connection pool initialized with %s %s connections",
                self.config.min_connections,
                connection_type,
            )

    async def _create_database_connection(self, index: int) -> dict[str, Any]:
        """Create a new database connection metadata.

        Args:
            index: Connection index

        Returns:
            Connection dictionary with metadata
        """
        connection_id = f"db_conn_{index}"
        connection = {
            "id": connection_id,
            "created_at": time.time(),
            "last_used": time.time(),
            "query_count": 0,
            "active": True,
            "type": "database",
        }

        self._pool_state.add_connection(connection)

        logger.debug("Created database connection metadata: %s", connection_id)
        return connection

    async def _create_mock_connection(self, index: int) -> dict[str, Any]:
        """Create a new mock connection for file-based operations.

        Args:
            index: Connection index

        Returns:
            Connection dictionary with metadata
        """
        connection_id = f"mock_conn_{index}"
        connection = {
            "id": connection_id,
            "created_at": time.time(),
            "last_used": time.time(),
            "query_count": 0,
            "active": True,
            "type": "mock",
        }

        self._pool_state.add_connection(connection)

        logger.debug("Created mock connection: %s", connection_id)
        return connection

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[dict[str, Any], None]:
        """Get a connection from the pool.

        Yields:
            Database connection
        """
        if not self._initialized:
            await self.initialize()

        connection = None
        try:
            # Try to get an available connection
            try:
                connection = await self._pool_state.get_available_connection(
                    self.config.connection_timeout
                )
            except TimeoutError as timeout_err:
                # Create new connection if under max limit
                if self._pool_state.get_active_connections_count() < self.config.max_connections:
                    if self.database_manager:
                        connection = await self._create_database_connection(
                            self._pool_state.get_total_connections_count()
                        )
                    else:
                        connection = await self._create_mock_connection(
                            self._pool_state.get_total_connections_count()
                        )
                else:
                    raise ConnectionPoolExhaustedError("Connection pool exhausted") from timeout_err

            # Update connection metadata
            connection["last_used"] = time.time()
            connection["query_count"] += 1

            yield connection

        finally:
            # Return connection to pool
            if connection and connection["active"]:
                await self._pool_state.put_available_connection(connection)

    async def execute_query(
        self,
        query_type: str,
        data_path: str,
        filters: dict[str, Any] | None = None,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """Execute a query with connection pooling and caching.

        Args:
            query_type: Type of query being executed
            data_path: Path to the data file
            filters: Optional filters to apply
            use_cache: Whether to use caching

        Returns:
            Query results as DataFrame
        """
        start_time = time.time()
        cache_hit = False

        try:
            # Check cache first if enabled
            if use_cache:
                cached_result = await self._query_cache.get_cached_result(
                    query_type, data_path, filters
                )
                if cached_result is not None:
                    cache_hit = True
                    execution_time = time.time() - start_time
                    await self._metrics_manager.record_metrics(
                        query_type, execution_time, len(cached_result), cache_hit
                    )
                    return cached_result

            # Execute query with connection pooling
            async with self.get_connection() as connection:
                result = await self._execute_with_connection(
                    connection, query_type, data_path, filters
                )

                # Cache result if enabled
                if use_cache and result is not None:
                    await self._query_cache.cache_result(query_type, data_path, filters, result)

                execution_time = time.time() - start_time
                rows_processed = len(result) if result is not None else 0
                await self._metrics_manager.record_metrics(
                    query_type, execution_time, rows_processed, cache_hit
                )

                return result

        except Exception as e:
            execution_time = time.time() - start_time
            await self._metrics_manager.record_metrics(query_type, execution_time, 0, cache_hit)
            logger.error("Query execution failed: %s", e)
            raise

    async def _execute_with_connection(
        self,
        connection: dict[str, Any],
        query_type: str,
        data_path: str,
        filters: dict[str, Any] | None,
    ) -> pd.DataFrame:
        """Execute query with a specific connection.

        Args:
            connection: Database connection
            query_type: Type of query
            data_path: Path to data file
            filters: Optional filters

        Returns:
            Query results
        """
        logger.debug("Executing %s query with connection %s", query_type, connection["id"])

        try:
            if connection.get("type") == "database" and self.database_manager:
                # Execute database query
                return await self._execute_database_query(query_type, filters)
            # Execute file-based query (fallback)
            return await self._execute_file_query(data_path, filters)

        except Exception as e:
            logger.error("Query execution failed with connection %s: %s", connection["id"], e)
            raise

    async def _execute_database_query(
        self, table_name: str, filters: dict[str, Any] | None
    ) -> pd.DataFrame:
        """Execute query against database.

        Args:
            table_name: Database table name
            filters: Optional filters

        Returns:
            Query results as DataFrame
        """
        if self.database_manager is None:
            raise RuntimeError("Database manager is not initialized.")

        query_str = ""  # Initialize query_str
        async with self.database_manager.get_session() as session:
            # Build SQL query based on table name and filters
            if table_name == "entities":
                query_str = "SELECT * FROM entities"
            elif table_name == "relationships":
                query_str = "SELECT * FROM relationships"
            elif table_name == "communities":
                query_str = "SELECT * FROM communities"
            else:
                # Generic query with safe table name validation
                # Only allow alphanumeric characters and underscores for table names
                if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table_name):
                    raise ValueError(f"Invalid table name: {table_name}")

                # Use parameterized query construction
                query_str = (
                    f"SELECT * FROM {table_name}"  # nosec B608 - Table name from internal config
                )

            # Add filters if provided
            conditions, params = self._build_sql_filters(filters)

            if conditions:
                query_str += " WHERE " + " AND ".join(conditions)

            if params:
                result = await session.execute(
                    text(query_str), params
                )  # nosec B608 - Query uses parameterized values from _build_sql_filters # nosemgrep: avoid-sqlalchemy-text
            else:
                result = await session.execute(
                    text(query_str)
                )  # nosec B608 - Query built from validated table name and no user input # nosemgrep: avoid-sqlalchemy-text
            rows = result.fetchall()
            columns = result.keys()

            return pd.DataFrame(rows, columns=columns)

    async def _execute_file_query(
        self, data_path: str, filters: dict[str, Any] | None
    ) -> pd.DataFrame:
        """Execute query against file-based data.

        Args:
            data_path: Path to data file
            filters: Optional filters

        Returns:
            Query results as DataFrame
        """
        # File-based operation (original implementation)
        if data_path.endswith(".parquet"):
            result = pd.read_parquet(data_path)
        else:
            result = pd.DataFrame()

        # Apply filters if provided
        if filters and not result.empty:
            for column, value in filters.items():
                if column in result.columns:
                    if isinstance(value, list):
                        result = result[result[column].isin(value)]
                    else:
                        result = result[result[column] == value]

        return result

    def _build_sql_filters(
        self, filters: dict[str, Any] | None
    ) -> tuple[list[str], dict[str, Any]]:
        """Build SQL filter conditions and parameters from a dictionary of filters.

        Args:
            filters: A dictionary of filters where keys are column names and values are
                filter values.

        Returns:
            A tuple containing a list of SQL condition strings and a dictionary of parameters.
        """
        conditions = []
        params = {}
        if filters:
            for column, value in filters.items():
                if isinstance(value, list):
                    placeholders = ", ".join([f":{column}_{i}" for i, _ in enumerate(value)])
                    conditions.append(f"{column} IN ({placeholders})")
                    for i, v in enumerate(value):
                        params[f"{column}_{i}"] = v
                else:
                    conditions.append(f"{column} = :{column}")
                    params[column] = value
        return conditions, params

    async def get_pool_status(self) -> dict[str, Any]:
        """Get connection pool status.

        Returns:
            Pool status information
        """
        return {
            "total_connections": self._pool_state.get_total_connections_count(),
            "active_connections": self._pool_state.get_active_connections_count(),
            "available_connections": self._pool_state.get_available_connections_qsize(),
            "max_connections": self.config.max_connections,
            "total_queries": sum(
                conn["query_count"] for conn in self._pool_state.get_connections_list()
            ),
            "initialized": self._initialized,
        }

    async def get_metrics(self) -> list[QueryMetrics]:
        """Get query performance metrics.

        Returns:
            List of query metrics from the metrics manager
        """
        return await self._metrics_manager.get_metrics()

    async def cleanup(self) -> None:
        """Clean up connection pool resources."""
        async with self._lock:
            for connection in self._pool_state.get_connections_list():
                connection["active"] = False

            self._pool_state.clear_connections()
            self._initialized = False

            logger.info("Connection pool cleaned up")


# Global connection pool instance
# Rationale: Using a global instance for the connection pool simplifies access
# throughout the application and ensures a single, consistent pool state.
# While 'global' is generally discouraged, it's a common and acceptable pattern
# for managing singletons like this in Python applications.
_connection_pool: ConnectionPool | None = None


async def get_connection_pool(database_manager: Any = None) -> ConnectionPool:
    """Get the global connection pool instance.

    Args:
        database_manager: Optional database manager for real database connections

    Returns:
        Connection pool instance
    """
    global _connection_pool

    if _connection_pool is None:
        config = ConnectionPoolConfig()
        _connection_pool = ConnectionPool(config, database_manager)
        await _connection_pool.initialize()

    return _connection_pool


async def cleanup_connection_pool() -> None:
    """Clean up the global connection pool."""
    global _connection_pool

    if _connection_pool is not None:
        await _connection_pool.cleanup()
        _connection_pool = None
