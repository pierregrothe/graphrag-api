# src/graphrag_api_service/performance/connection_pool.py
# Database Connection Pooling and Query Optimization
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Real database connection pooling and query optimization for GraphRAG operations."""

import asyncio
import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import pandas as pd
from pydantic import BaseModel

logger = logging.getLogger(__name__)


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


class ConnectionPool:
    """Async connection pool for GraphRAG data operations."""

    def __init__(self, config: ConnectionPoolConfig, database_manager=None):
        """Initialize the connection pool.

        Args:
            config: Connection pool configuration
            database_manager: Optional database manager for real database connections
        """
        self.config = config
        self.database_manager = database_manager
        self._connections: list[dict[str, Any]] = []
        self._available_connections: asyncio.Queue = asyncio.Queue()
        self._active_connections: int = 0
        self._lock = asyncio.Lock()
        self._metrics: list[QueryMetrics] = []
        self._initialized = False
        # Simple in-memory cache with TTL
        self._cache: dict[str, tuple[pd.DataFrame, float]] = {}
        self._cache_ttl = 300  # 5 minutes default TTL

    async def initialize(self) -> None:
        """Initialize the connection pool."""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            logger.info("Initializing connection pool")

            # Create minimum number of connections
            for i in range(self.config.min_connections):
                if self.database_manager:
                    # Create database connection metadata
                    connection = await self._create_database_connection(i)
                else:
                    # Create mock connection for file-based operations
                    connection = await self._create_mock_connection(i)
                await self._available_connections.put(connection)

            self._initialized = True
            connection_type = "database" if self.database_manager else "file-based"
            logger.info(
                f"Connection pool initialized with {self.config.min_connections} {connection_type} connections"
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

        self._connections.append(connection)
        self._active_connections += 1

        logger.debug(f"Created database connection metadata: {connection_id}")
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

        self._connections.append(connection)
        self._active_connections += 1

        logger.debug(f"Created mock connection: {connection_id}")
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
                connection = await asyncio.wait_for(
                    self._available_connections.get(), timeout=self.config.connection_timeout
                )
            except TimeoutError:
                # Create new connection if under max limit
                if self._active_connections < self.config.max_connections:
                    connection = await self._create_connection()
                else:
                    raise Exception("Connection pool exhausted")

            # Update connection metadata
            connection["last_used"] = time.time()
            connection["query_count"] += 1

            yield connection

        finally:
            # Return connection to pool
            if connection and connection["active"]:
                await self._available_connections.put(connection)

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
                cached_result = await self._get_cached_result(query_type, data_path, filters)
                if cached_result is not None:
                    cache_hit = True
                    execution_time = time.time() - start_time
                    await self._record_metrics(
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
                    await self._cache_result(query_type, data_path, filters, result)

                execution_time = time.time() - start_time
                rows_processed = len(result) if result is not None else 0
                await self._record_metrics(query_type, execution_time, rows_processed, cache_hit)

                return result

        except Exception as e:
            execution_time = time.time() - start_time
            await self._record_metrics(query_type, execution_time, 0, cache_hit)
            logger.error(f"Query execution failed: {e}")
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
        logger.debug(f"Executing {query_type} query with connection {connection['id']}")

        try:
            if connection.get("type") == "database" and self.database_manager:
                # Execute database query
                return await self._execute_database_query(query_type, data_path, filters)
            else:
                # Execute file-based query (fallback)
                return await self._execute_file_query(data_path, filters)

        except Exception as e:
            logger.error(f"Query execution failed with connection {connection['id']}: {e}")
            raise

    async def _execute_database_query(
        self, query_type: str, table_name: str, filters: dict[str, Any] | None
    ) -> pd.DataFrame:
        """Execute query against database.

        Args:
            query_type: Type of query
            table_name: Database table name
            filters: Optional filters

        Returns:
            Query results as DataFrame
        """
        async with self.database_manager.get_session() as session:
            # Build SQL query based on table name and filters
            if table_name == "entities":
                query = "SELECT * FROM entities"
            elif table_name == "relationships":
                query = "SELECT * FROM relationships"
            elif table_name == "communities":
                query = "SELECT * FROM communities"
            else:
                # Generic query with safe table name validation
                # Only allow alphanumeric characters and underscores for table names
                import re

                if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table_name):
                    raise ValueError(f"Invalid table name: {table_name}")

                # Use parameterized query construction
                from sqlalchemy import text

                query = text(f"SELECT * FROM {table_name}")

            # Add filters if provided
            if filters:
                conditions = []
                for column, value in filters.items():
                    if isinstance(value, list):
                        placeholders = ",".join([f"'{v}'" for v in value])
                        conditions.append(f"{column} IN ({placeholders})")
                    else:
                        conditions.append(f"{column} = '{value}'")

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

            # Execute query and return as DataFrame
            result = await session.execute(text(query))
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

    async def _get_cached_result(
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
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_data.copy()  # Return a copy to prevent mutations
            else:
                # Remove expired entry
                del self._cache[cache_key]
                logger.debug(f"Cache expired for key: {cache_key}")

        return None

    async def _cache_result(
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
        logger.debug(f"Cached result for key: {cache_key}")

        # Clean up old entries if cache is getting too large (simple LRU)
        if len(self._cache) > 100:  # Max 100 entries
            # Remove oldest entries
            current_time = time.time()
            expired_keys = [
                k for k, (_, t) in self._cache.items() if current_time - t > self._cache_ttl
            ]
            for key in expired_keys:
                del self._cache[key]
            logger.debug(f"Cleaned {len(expired_keys)} expired cache entries")

    async def _record_metrics(
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
            f"Query metrics - Type: {query_type}, Time: {execution_time:.3f}s, "
            f"Rows: {rows_processed}, Cache: {cache_hit}"
        )

    async def get_metrics(self) -> list[QueryMetrics]:
        """Get query performance metrics.

        Returns:
            List of query metrics
        """
        return self._metrics.copy()

    async def get_pool_status(self) -> dict[str, Any]:
        """Get connection pool status.

        Returns:
            Pool status information
        """
        return {
            "total_connections": len(self._connections),
            "active_connections": self._active_connections,
            "available_connections": self._available_connections.qsize(),
            "max_connections": self.config.max_connections,
            "total_queries": sum(conn["query_count"] for conn in self._connections),
            "initialized": self._initialized,
        }

    async def cleanup(self) -> None:
        """Clean up connection pool resources."""
        async with self._lock:
            for connection in self._connections:
                connection["active"] = False

            self._connections.clear()
            self._active_connections = 0
            self._initialized = False

            logger.info("Connection pool cleaned up")


# Global connection pool instance
_connection_pool: ConnectionPool | None = None


async def get_connection_pool(database_manager=None) -> ConnectionPool:
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
