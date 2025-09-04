# src/graphrag_api_service/performance/memory_optimizer.py
# Memory Usage Optimization for Large Graph Operations
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Memory optimization system for efficient handling of large graph datasets."""

import gc
import logging
import weakref
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any

import pandas as pd
import psutil
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class MemoryConfig(BaseModel):
    """Configuration for memory optimization."""

    max_memory_usage_percent: float = 80.0
    chunk_size: int = 10000
    enable_gc_optimization: bool = True
    enable_dataframe_optimization: bool = True
    memory_warning_threshold: float = 70.0


class MemoryStats(BaseModel):
    """Memory usage statistics."""

    total_memory_mb: float
    used_memory_mb: float
    available_memory_mb: float
    usage_percent: float
    process_memory_mb: float
    gc_collections: dict[str, int]


class DataFrameOptimizer:
    """Optimizer for pandas DataFrame memory usage."""

    @staticmethod
    def optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
        """Optimize DataFrame data types to reduce memory usage.

        Args:
            df: DataFrame to optimize

        Returns:
            Optimized DataFrame
        """
        if df.empty:
            return df

        optimized_df = df.copy()

        for column in optimized_df.columns:
            col_type = optimized_df[column].dtype

            # Optimize numeric columns
            if col_type in ["int64", "int32"]:
                col_min = optimized_df[column].min()
                col_max = optimized_df[column].max()

                if col_min >= -128 and col_max <= 127:
                    optimized_df[column] = optimized_df[column].astype("int8")
                elif col_min >= -32768 and col_max <= 32767:
                    optimized_df[column] = optimized_df[column].astype("int16")
                elif col_min >= -2147483648 and col_max <= 2147483647:
                    optimized_df[column] = optimized_df[column].astype("int32")

            elif col_type == "float64":
                optimized_df[column] = pd.to_numeric(optimized_df[column], downcast="float")

            # Optimize string columns
            elif col_type == "object":
                if optimized_df[column].nunique() / len(optimized_df) < 0.5:
                    optimized_df[column] = optimized_df[column].astype("category")

        return optimized_df

    @staticmethod
    def get_memory_usage(df: pd.DataFrame) -> dict[str, Any]:
        """Get detailed memory usage of DataFrame.

        Args:
            df: DataFrame to analyze

        Returns:
            Memory usage statistics
        """
        memory_usage = df.memory_usage(deep=True)
        total_mb = memory_usage.sum() / (1024 * 1024)

        return {
            "total_mb": total_mb,
            "index_mb": memory_usage.iloc[0] / (1024 * 1024),
            "columns": {
                col: memory_usage.iloc[i + 1] / (1024 * 1024) for i, col in enumerate(df.columns)
            },
        }


class ChunkedProcessor:
    """Process large datasets in chunks to manage memory usage."""

    def __init__(self, chunk_size: int = 10000):
        """Initialize the chunked processor.

        Args:
            chunk_size: Size of each chunk
        """
        self.chunk_size = chunk_size

    def process_dataframe_chunks(
        self, df: pd.DataFrame, processor_func: Callable[[pd.DataFrame], Any], **kwargs: Any
    ) -> list[Any]:
        """Process DataFrame in chunks.

        Args:
            df: DataFrame to process
            processor_func: Function to apply to each chunk
            **kwargs: Additional arguments for processor function

        Returns:
            List of processed results
        """
        results = []
        total_chunks = (len(df) + self.chunk_size - 1) // self.chunk_size

        logger.info("Processing %s rows in %s chunks of %s", len(df), total_chunks, self.chunk_size)

        for i in range(0, len(df), self.chunk_size):
            chunk = df.iloc[i : i + self.chunk_size]
            chunk_result = processor_func(chunk, **kwargs)
            results.append(chunk_result)

            # Force garbage collection after each chunk
            gc.collect()

            if (i // self.chunk_size + 1) % 10 == 0:
                logger.debug("Processed chunk %s/%s", i // self.chunk_size + 1, total_chunks)

        return results

    def aggregate_chunked_results(
        self, results: list[Any], aggregation_func: Callable[[list[Any]], Any] | None = None
    ) -> Any:
        """Aggregate results from chunked processing.

        Args:
            results: List of chunk results
            aggregation_func: Function to aggregate results

        Returns:
            Aggregated result
        """
        if not results:
            return None

        if aggregation_func:
            return aggregation_func(results)

        # Default aggregation for DataFrames
        if isinstance(results[0], pd.DataFrame):
            return pd.concat(results, ignore_index=True)

        # Default aggregation for lists
        if isinstance(results[0], list):
            aggregated = []
            for result in results:
                aggregated.extend(result)
            return aggregated

        return results


class MemoryMonitor:
    """Monitor and manage memory usage."""

    def __init__(self, config: MemoryConfig):
        """Initialize the memory monitor.

        Args:
            config: Memory configuration
        """
        self.config = config
        self._tracked_objects: set[weakref.ref[Any]] = set()

    def get_memory_stats(self) -> MemoryStats:
        """Get current memory statistics.

        Returns:
            Memory usage statistics
        """
        # System memory
        memory = psutil.virtual_memory()

        # Process memory
        process = psutil.Process()
        process_memory = process.memory_info().rss / (1024 * 1024)

        # Garbage collection stats
        gc_stats = {f"gen_{i}": gc.get_count()[i] for i in range(3)}

        return MemoryStats(
            total_memory_mb=memory.total / (1024 * 1024),
            used_memory_mb=memory.used / (1024 * 1024),
            available_memory_mb=memory.available / (1024 * 1024),
            usage_percent=memory.percent,
            process_memory_mb=process_memory,
            gc_collections=gc_stats,
        )

    def check_memory_pressure(self) -> bool:
        """Check if system is under memory pressure.

        Returns:
            True if memory usage is high
        """
        stats = self.get_memory_stats()
        return stats.usage_percent > self.config.max_memory_usage_percent

    def track_object(self, obj: Any) -> None:
        """Track an object for memory monitoring.

        Args:
            obj: Object to track
        """
        self._tracked_objects.add(weakref.ref(obj))

    def cleanup_tracked_objects(self) -> int:
        """Clean up dead references from tracked objects.

        Returns:
            Number of objects cleaned up
        """
        dead_refs = {ref for ref in self._tracked_objects if ref() is None}
        self._tracked_objects -= dead_refs
        return len(dead_refs)

    def get_tracked_objects_count(self) -> int:
        """Get the number of currently tracked objects.

        Returns:
            Number of tracked objects
        """
        return len(self._tracked_objects)

    @contextmanager
    def memory_limit_context(self, max_memory_mb: float) -> Generator[None, None, None]:
        """Context manager to enforce memory limits.

        Args:
            max_memory_mb: Maximum memory usage in MB

        Yields:
            None
        """
        initial_stats = self.get_memory_stats()

        try:
            yield
        finally:
            final_stats = self.get_memory_stats()
            memory_used = final_stats.process_memory_mb - initial_stats.process_memory_mb

            if memory_used > max_memory_mb:
                logger.warning(
                    "Memory limit exceeded: %.1fMB used, limit was %.1fMB",
                    memory_used,
                    max_memory_mb,
                )

                # Force garbage collection
                if self.config.enable_gc_optimization:
                    self.force_garbage_collection()

    def force_garbage_collection(self) -> dict[str, int]:
        """Force garbage collection and return statistics.

        Returns:
            Garbage collection statistics
        """
        # Force collection for all generations
        collected = {}
        for generation in range(3):
            collected[f"gen_{generation}"] = gc.collect(generation)

        logger.debug("Garbage collection completed: %s", collected)
        return collected

    def optimize_memory_usage(self) -> dict[str, Any]:
        """Optimize current memory usage.

        Returns:
            Optimization results
        """
        initial_stats = self.get_memory_stats()

        # Clean up tracked objects
        cleaned_objects = self.cleanup_tracked_objects()

        # Force garbage collection
        gc_results = {}
        if self.config.enable_gc_optimization:
            gc_results = self.force_garbage_collection()

        final_stats = self.get_memory_stats()
        memory_freed = initial_stats.process_memory_mb - final_stats.process_memory_mb

        results = {
            "memory_freed_mb": memory_freed,
            "cleaned_objects": cleaned_objects,
            "gc_collections": gc_results,
            "initial_memory_mb": initial_stats.process_memory_mb,
            "final_memory_mb": final_stats.process_memory_mb,
        }

        logger.info("Memory optimization completed: %.1fMB freed", memory_freed)
        return results


class MemoryOptimizer:
    """Main memory optimization coordinator."""

    def __init__(self, config: MemoryConfig | None = None):
        """Initialize the memory optimizer.

        Args:
            config: Memory optimization configuration
        """
        self.config = config or MemoryConfig()
        self.monitor = MemoryMonitor(self.config)
        self.dataframe_optimizer = DataFrameOptimizer()
        self.chunked_processor = ChunkedProcessor(self.config.chunk_size)

    def optimize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Optimize DataFrame for memory efficiency.

        Args:
            df: DataFrame to optimize

        Returns:
            Optimized DataFrame
        """
        if not self.config.enable_dataframe_optimization:
            return df

        initial_memory = self.dataframe_optimizer.get_memory_usage(df)
        optimized_df = self.dataframe_optimizer.optimize_dtypes(df)
        final_memory = self.dataframe_optimizer.get_memory_usage(optimized_df)

        memory_saved = initial_memory["total_mb"] - final_memory["total_mb"]
        logger.debug("DataFrame optimized: %.2fMB saved", memory_saved)

        return optimized_df

    def process_large_dataset(
        self, df: pd.DataFrame, processor_func: Callable[[pd.DataFrame], Any], **kwargs: Any
    ) -> Any:
        """Process large dataset with memory optimization.

        Args:
            df: Large DataFrame to process
            processor_func: Processing function
            **kwargs: Additional arguments

        Returns:
            Processed result
        """
        # Check if chunking is needed
        memory_stats = self.monitor.get_memory_stats()
        df_memory = self.dataframe_optimizer.get_memory_usage(df)

        if (
            memory_stats.usage_percent > self.config.memory_warning_threshold
            or df_memory["total_mb"] > 100
        ):  # 100MB threshold

            logger.info(
                "Using chunked processing for large dataset (%.1fMB)",
                df_memory["total_mb"],
            )
            results = self.chunked_processor.process_dataframe_chunks(df, processor_func, **kwargs)
            return self.chunked_processor.aggregate_chunked_results(results)
        return processor_func(df, **kwargs)

    async def get_optimization_status(self) -> dict[str, Any]:
        """Get current optimization status.

        Returns:
            Optimization status information
        """
        memory_stats = self.monitor.get_memory_stats()

        return {
            "memory_stats": memory_stats.model_dump(),
            "memory_pressure": self.monitor.check_memory_pressure(),
            "config": self.config.model_dump(),
            "tracked_objects": self.monitor.get_tracked_objects_count(),
        }


# Global memory optimizer instance
# Rationale: Using a global instance for the memory optimizer simplifies access
# throughout the application and ensures a single, consistent state for memory
# management. While 'global' is generally discouraged, it's a common and acceptable pattern
# for managing singletons like this in Python applications.
_memory_optimizer: MemoryOptimizer | None = None


def get_memory_optimizer() -> MemoryOptimizer:
    """Get the global memory optimizer instance.

    Returns:
        Memory optimizer instance
    """
    global _memory_optimizer

    if _memory_optimizer is None:
        _memory_optimizer = MemoryOptimizer()

    return _memory_optimizer
