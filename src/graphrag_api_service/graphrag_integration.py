# src/graphrag_api_service/graphrag_integration.py
# GraphRAG Core Integration Module
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""GraphRAG core integration module for query and indexing operations."""

import asyncio
import subprocess  # nosec B404 - Required for GraphRAG CLI integration, input is controlled
import sys
from pathlib import Path
from typing import Any

from .config import Settings
from .logging_config import get_logger
from .providers.base import GraphRAGLLM

logger = get_logger(__name__)


class GraphRAGError(Exception):
    """Base exception for GraphRAG operations."""

    pass


class GraphRAGIntegration:
    """Core GraphRAG integration class for query and indexing operations."""

    def __init__(self, settings: Settings, provider: GraphRAGLLM):
        """Initialize GraphRAG integration.

        Args:
            settings: Application settings
            provider: LLM provider instance
        """
        self.settings = settings
        self.provider = provider

    async def query_global(
        self,
        query: str,
        data_path: str,
        community_level: int = 2,
        max_tokens: int = 1500,
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        """Perform global search using GraphRAG CLI.

        Args:
            query: Search query
            data_path: Path to GraphRAG data directory
            community_level: Community level for search
            max_tokens: Maximum tokens in response
            workspace_id: Optional workspace ID

        Returns:
            Dictionary containing search results and metadata

        Raises:
            GraphRAGError: If global search fails
        """
        logger.info(f"Performing GraphRAG global search: {query[:100]}...")

        try:
            # Use GraphRAG CLI for global search
            cmd = [
                sys.executable,
                "-m",
                "graphrag.cli.query",
                "--root",
                data_path,
                "--method",
                "global",
                "--community_level",
                str(community_level),
                "--response_type",
                "multiple paragraphs",
                query,
            ]

            # Run command in thread to avoid blocking
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                cwd=data_path,
                timeout=120,  # 2 minute timeout
            )

            if result.returncode != 0:
                error_msg = result.stderr or "GraphRAG global search failed"
                logger.error(f"Global search failed: {error_msg}")
                raise GraphRAGError(f"Global search failed: {error_msg}")

            # Parse result
            answer = result.stdout.strip() if result.stdout else "No results found"
            tokens_used = len(answer.split()) if answer else 0

            logger.info(f"Global search completed successfully, {tokens_used} tokens used")

            return {
                "answer": answer,
                "sources": ["graphrag_global_search"],  # Simplified for now
                "community_level": community_level,
                "tokens_used": tokens_used,
                "search_type": "global",
            }

        except subprocess.TimeoutExpired:
            logger.error("Global search timed out")
            raise GraphRAGError("Global search timed out") from None
        except Exception as e:
            logger.error(f"Global search failed: {e}")
            raise GraphRAGError(f"Global search failed: {e}") from e

    async def query_local(
        self,
        query: str,
        data_path: str,
        max_tokens: int = 1500,
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        """Perform local search using GraphRAG CLI.

        Args:
            query: Search query
            data_path: Path to GraphRAG data directory
            max_tokens: Maximum tokens in response
            workspace_id: Optional workspace ID

        Returns:
            Dictionary containing search results and metadata

        Raises:
            GraphRAGError: If local search fails
        """
        logger.info(f"Performing GraphRAG local search: {query[:100]}...")

        try:
            # Use GraphRAG CLI for local search
            cmd = [
                sys.executable,
                "-m",
                "graphrag.cli.query",
                "--root",
                data_path,
                "--method",
                "local",
                "--response_type",
                "multiple paragraphs",
                query,
            ]

            # Run command in thread to avoid blocking
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                cwd=data_path,
                timeout=120,  # 2 minute timeout
            )

            if result.returncode != 0:
                error_msg = result.stderr or "GraphRAG local search failed"
                logger.error(f"Local search failed: {error_msg}")
                raise GraphRAGError(f"Local search failed: {error_msg}")

            # Parse result
            answer = result.stdout.strip() if result.stdout else "No results found"
            tokens_used = len(answer.split()) if answer else 0

            logger.info(f"Local search completed successfully, {tokens_used} tokens used")

            return {
                "answer": answer,
                "sources": ["graphrag_local_search"],  # Simplified for now
                "community_level": 0,  # Local search doesn't use community levels
                "tokens_used": tokens_used,
                "search_type": "local",
            }

        except subprocess.TimeoutExpired:
            logger.error("Local search timed out")
            raise GraphRAGError("Local search timed out") from None
        except Exception as e:
            logger.error(f"Local search failed: {e}")
            raise GraphRAGError(f"Local search failed: {e}") from e

    def _validate_data_directory(self, data_path: str) -> tuple[Path, int]:
        """Validate data directory and count input files."""
        data_dir = Path(data_path)
        if not data_dir.exists():
            raise GraphRAGError(f"Data directory does not exist: {data_path}")

        input_files = list(data_dir.glob("**/*.txt")) + list(data_dir.glob("**/*.md"))
        files_count = len(input_files)
        logger.info(f"Found {files_count} files to process")

        return data_dir, files_count

    def _build_indexing_command(
        self, data_dir: Path, config_path: str | None, force_reindex: bool
    ) -> list[str]:
        """Build the GraphRAG indexing command."""
        cmd = [sys.executable, "-m", "graphrag.cli.index", "--root", str(data_dir)]

        if config_path:
            cmd.extend(["--config", config_path])

        if not force_reindex:
            cmd.append("--resume")

        return cmd

    async def _run_indexing_process(self, cmd: list[str], data_dir: Path) -> None:
        """Run the GraphRAG indexing process."""
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            cwd=str(data_dir),
            timeout=1800,  # 30 minute timeout for indexing
        )

        if result.returncode != 0:
            error_msg = result.stderr or "GraphRAG indexing failed"
            logger.error(f"Indexing failed: {error_msg}")
            raise GraphRAGError(f"Indexing failed: {error_msg}")

    def _analyze_indexing_results(self, output_dir: Path) -> tuple[int, int]:
        """Analyze indexing results and count entities/relationships."""
        artifacts_dir = output_dir / "artifacts"
        entities_count = 0
        relationships_count = 0

        try:
            entities_file = artifacts_dir / "create_final_entities.parquet"
            relationships_file = artifacts_dir / "create_final_relationships.parquet"

            if entities_file.exists():
                import pandas as pd

                entities_df = pd.read_parquet(entities_file)
                entities_count = len(entities_df)

            if relationships_file.exists():
                import pandas as pd

                relationships_df = pd.read_parquet(relationships_file)
                relationships_count = len(relationships_df)

        except ImportError:
            logger.warning("Pandas not available for result analysis")
        except Exception as e:
            logger.warning(f"Failed to analyze results: {e}")

        return entities_count, relationships_count

    async def index_data(
        self,
        data_path: str,
        config_path: str | None = None,
        force_reindex: bool = False,
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        """Index data using GraphRAG CLI.

        Args:
            data_path: Path to data directory to index
            config_path: Optional path to GraphRAG configuration file
            force_reindex: Whether to force reindexing
            workspace_id: Optional workspace ID

        Returns:
            Dictionary containing indexing results and statistics

        Raises:
            GraphRAGError: If indexing fails
        """
        logger.info(f"Starting GraphRAG indexing for: {data_path}")

        try:
            # Validate and prepare
            data_dir, files_count = self._validate_data_directory(data_path)
            output_dir = data_dir / "output"
            output_dir.mkdir(exist_ok=True)

            # Build and run indexing command
            cmd = self._build_indexing_command(data_dir, config_path, force_reindex)
            await self._run_indexing_process(cmd, data_dir)

            # Analyze results
            entities_count, relationships_count = self._analyze_indexing_results(output_dir)

            logger.info(
                f"Indexing completed: {files_count} files, {entities_count} entities, "
                f"{relationships_count} relationships"
            )

            return {
                "status": "completed",
                "message": f"Successfully indexed {files_count} files",
                "files_processed": files_count,
                "entities_extracted": entities_count,
                "relationships_extracted": relationships_count,
                "output_directory": str(output_dir),
            }

        except subprocess.TimeoutExpired:
            logger.error("Indexing timed out")
            raise GraphRAGError("Indexing operation timed out") from None
        except Exception as e:
            logger.error(f"GraphRAG indexing failed: {e}")
            raise GraphRAGError(f"Indexing failed: {e}") from e

    async def get_index_status(self, data_path: str) -> dict[str, Any]:
        """Get indexing status for a data directory.

        Args:
            data_path: Path to data directory

        Returns:
            Dictionary containing index status information
        """
        try:
            data_dir = Path(data_path)
            output_dir = data_dir / "output"
            artifacts_dir = output_dir / "artifacts"

            # Check if indexing has been performed
            indexed = artifacts_dir.exists() and any(artifacts_dir.glob("*.parquet"))

            # Get file counts
            input_files = list(data_dir.glob("**/*.txt")) + list(data_dir.glob("**/*.md"))
            files_count = len(input_files)

            status_info = {
                "indexed": indexed,
                "input_files": files_count,
                "output_directory": str(output_dir) if output_dir.exists() else None,
                "artifacts_directory": str(artifacts_dir) if artifacts_dir.exists() else None,
            }

            if indexed:
                # Get artifact file information
                parquet_files = list(artifacts_dir.glob("*.parquet"))
                status_info["artifact_files"] = len(parquet_files)
                status_info["last_modified"] = (
                    int(max(f.stat().st_mtime for f in parquet_files)) if parquet_files else None
                )

            return status_info

        except Exception as e:
            logger.error(f"Failed to get index status: {e}")
            return {"indexed": False, "error": str(e)}
