# src/graphrag_api_service/graph/operations.py
# Graph operations implementation
# Author: Pierre Grothé
# Creation Date: 2025-08-28

"""Graph operations implementation for knowledge graph analysis and visualization."""

import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from ..config import Settings
from ..logging_config import get_logger

logger = get_logger(__name__)


class GraphOperationsError(Exception):
    """Base exception for graph operations."""

    pass


class GraphOperations:
    """Graph operations for knowledge graph analysis and visualization."""

    def __init__(self, settings: Settings):
        """Initialize graph operations.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.metrics = {"queries": 0, "exports": 0}

    def _load_parquet_file(self, data_path: str, filename: str) -> pd.DataFrame | None:
        """Load a parquet file from the GraphRAG output directory.

        Args:
            data_path: Path to GraphRAG data directory
            filename: Name of the parquet file to load

        Returns:
            DataFrame if file exists and loads successfully, None otherwise
        """
        try:
            file_path = Path(data_path) / "output" / "artifacts" / filename
            if file_path.exists():
                return pd.read_parquet(file_path)
            return None
        except Exception as e:
            logger.warning(f"Failed to load {filename}: {e}")
            return None

    async def query_entities(
        self,
        data_path: str,
        entity_name: str | None = None,
        entity_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Query entities from the knowledge graph.

        Args:
            data_path: Path to GraphRAG data directory
            entity_name: Optional entity name filter
            entity_type: Optional entity type filter
            limit: Maximum number of entities to return
            offset: Offset for pagination

        Returns:
            Dictionary containing entities and metadata

        Raises:
            GraphOperationsError: If entity querying fails
        """
        try:
            # Load entities parquet file
            entities_df = self._load_parquet_file(data_path, "create_final_entities.parquet")
            if entities_df is None:
                raise GraphOperationsError("Entities data not found. Please run indexing first.")

            # Apply filters
            filtered_df = entities_df.copy()

            if entity_name:
                # Case-insensitive partial match
                mask = filtered_df["title"].str.contains(entity_name, case=False, na=False)
                filtered_df = filtered_df[mask]

            if entity_type:
                # Filter by entity type if the column exists
                if "type" in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df["type"] == entity_type]

            total_count = len(filtered_df)

            # Apply pagination
            paginated_df = filtered_df.iloc[offset : offset + limit]

            # Convert to list of dictionaries
            entities = []
            for _, row in paginated_df.iterrows():
                entity = {
                    "id": row.get("id", ""),
                    "title": row.get("title", ""),
                    "type": row.get("type", "unknown"),
                    "description": (
                        row.get("description", "")[:200] + "..."
                        if len(str(row.get("description", ""))) > 200
                        else row.get("description", "")
                    ),
                    "degree": row.get("degree", 0),
                    "community_ids": row.get("community_ids", []),
                    "text_unit_ids": row.get("text_unit_ids", []),
                }
                entities.append(entity)

            self.metrics["queries"] += 1
            return {
                "entities": entities,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
            }

        except Exception as e:
            logger.error(f"Entity querying failed: {e}")
            raise GraphOperationsError(f"Entity querying failed: {e}") from e

    async def query_relationships(
        self,
        data_path: str,
        source_entity: str | None = None,
        target_entity: str | None = None,
        relationship_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Query relationships from the knowledge graph.

        Args:
            data_path: Path to GraphRAG data directory
            source_entity: Optional source entity filter
            target_entity: Optional target entity filter
            relationship_type: Optional relationship type filter
            limit: Maximum number of relationships to return
            offset: Offset for pagination

        Returns:
            Dictionary containing relationships and metadata

        Raises:
            GraphOperationsError: If relationship querying fails
        """
        try:
            # Load relationships parquet file
            relationships_df = self._load_parquet_file(
                data_path, "create_final_relationships.parquet"
            )
            if relationships_df is None:
                raise GraphOperationsError(
                    "Relationships data not found. Please run indexing first."
                )

            # Apply filters
            filtered_df = relationships_df.copy()

            if source_entity:
                # Case-insensitive partial match on source
                mask = filtered_df["source"].str.contains(source_entity, case=False, na=False)
                filtered_df = filtered_df[mask]

            if target_entity:
                # Case-insensitive partial match on target
                mask = filtered_df["target"].str.contains(target_entity, case=False, na=False)
                filtered_df = filtered_df[mask]

            if relationship_type:
                # Filter by relationship type if the column exists
                if "type" in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df["type"] == relationship_type]

            total_count = len(filtered_df)

            # Apply pagination
            paginated_df = filtered_df.iloc[offset : offset + limit]

            # Convert to list of dictionaries
            relationships = []
            for _, row in paginated_df.iterrows():
                relationship = {
                    "id": row.get("id", ""),
                    "source": row.get("source", ""),
                    "target": row.get("target", ""),
                    "type": row.get("type", "unknown"),
                    "description": (
                        row.get("description", "")[:200] + "..."
                        if len(str(row.get("description", ""))) > 200
                        else row.get("description", "")
                    ),
                    "weight": row.get("weight", 0.0),
                    "text_unit_ids": row.get("text_unit_ids", []),
                }
                relationships.append(relationship)

            self.metrics["queries"] += 1
            return {
                "relationships": relationships,
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
            }

        except Exception as e:
            logger.error(f"Relationship querying failed: {e}")
            raise GraphOperationsError(f"Relationship querying failed: {e}") from e

    async def get_entities(self, data_path: str, entity_ids: list[str]) -> list[dict[str, Any]]:
        """Get entities by their IDs.

        Args:
            data_path: Path to GraphRAG data directory
            entity_ids: List of entity IDs to retrieve

        Returns:
            List of entity dictionaries
        """
        try:
            entities_df = self._load_parquet_file(data_path, "create_final_entities.parquet")
            if entities_df is None:
                return []

            # Filter by entity IDs
            filtered_entities = entities_df[entities_df["id"].isin(entity_ids)]

            return [
                {
                    "id": row["id"],
                    "name": row.get("title", ""),
                    "type": row.get("type", ""),
                    "description": row.get("description", ""),
                    "degree": row.get("degree", 0),
                    "community": row.get("community", ""),
                }
                for _, row in filtered_entities.iterrows()
            ]

        except Exception as e:
            logger.error(f"Entity retrieval failed: {e}")
            return []

    async def get_relationships(
        self, data_path: str, relationship_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Get relationships by their IDs.

        Args:
            data_path: Path to GraphRAG data directory
            relationship_ids: List of relationship IDs to retrieve

        Returns:
            List of relationship dictionaries
        """
        try:
            relationships_df = self._load_parquet_file(
                data_path, "create_final_relationships.parquet"
            )
            if relationships_df is None:
                return []

            # Filter by relationship IDs
            filtered_relationships = relationships_df[relationships_df["id"].isin(relationship_ids)]

            return [
                {
                    "id": row["id"],
                    "source": row.get("source", ""),
                    "target": row.get("target", ""),
                    "type": row.get("type", ""),
                    "description": row.get("description", ""),
                    "weight": row.get("weight", 1.0),
                }
                for _, row in filtered_relationships.iterrows()
            ]

        except Exception as e:
            logger.error(f"Relationship retrieval failed: {e}")
            return []

    async def get_communities(
        self, data_path: str, community_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Get communities by their IDs.

        Args:
            data_path: Path to GraphRAG data directory
            community_ids: List of community IDs to retrieve

        Returns:
            List of community dictionaries
        """
        try:
            communities_df = self._load_parquet_file(data_path, "create_final_communities.parquet")
            if communities_df is None:
                return []

            # Filter by community IDs
            filtered_communities = communities_df[communities_df["id"].isin(community_ids)]

            return [
                {
                    "id": row["id"],
                    "title": row.get("title", ""),
                    "level": row.get("level", 0),
                    "size": row.get("size", 0),
                    "description": row.get("full_content", ""),
                }
                for _, row in filtered_communities.iterrows()
            ]

        except Exception as e:
            logger.error(f"Community retrieval failed: {e}")
            return []

    async def query_communities(self, data_path: str, **kwargs) -> dict[str, Any]:
        """Query communities from the knowledge graph.

        Args:
            data_path: Path to GraphRAG data directory
            **kwargs: Additional query parameters

        Returns:
            Dictionary containing communities and metadata
        """
        try:
            communities_df = self._load_parquet_file(data_path, "create_final_communities.parquet")
            if communities_df is None:
                return {"communities": [], "total": 0}

            # Apply any filtering based on kwargs
            limit = kwargs.get("limit", 50)
            offset = kwargs.get("offset", 0)

            # Paginate results
            total = len(communities_df)
            paginated_df = communities_df.iloc[offset : offset + limit]

            communities = [
                {
                    "id": row["id"],
                    "title": row.get("title", ""),
                    "level": row.get("level", 0),
                    "size": row.get("size", 0),
                    "description": row.get("full_content", ""),
                }
                for _, row in paginated_df.iterrows()
            ]

            return {
                "communities": communities,
                "total": total,
                "limit": limit,
                "offset": offset,
            }

        except Exception as e:
            logger.error(f"Community querying failed: {e}")
            raise GraphOperationsError(f"Community querying failed: {e}") from e

    async def get_graph_statistics(self, data_path: str) -> dict[str, Any]:
        """Get comprehensive statistics about the knowledge graph.

        Args:
            data_path: Path to GraphRAG data directory

        Returns:
            Dictionary containing graph statistics

        Raises:
            GraphOperationsError: If statistics calculation fails
        """
        try:
            # Load data files
            entities_df = self._load_parquet_file(data_path, "create_final_entities.parquet")
            relationships_df = self._load_parquet_file(
                data_path, "create_final_relationships.parquet"
            )
            communities_df = self._load_parquet_file(data_path, "create_final_communities.parquet")

            if entities_df is None or relationships_df is None:
                raise GraphOperationsError("Graph data not found. Please run indexing first.")

            # Basic counts
            total_entities = len(entities_df)
            total_relationships = len(relationships_df)
            total_communities = len(communities_df) if communities_df is not None else 0

            # Entity type distribution
            entity_types = {}
            if "type" in entities_df.columns:
                entity_types = entities_df["type"].value_counts().to_dict()
            else:
                entity_types = {"unknown": total_entities}

            # Relationship type distribution
            relationship_types = {}
            if "type" in relationships_df.columns:
                relationship_types = relationships_df["type"].value_counts().to_dict()
            else:
                relationship_types = {"unknown": total_relationships}

            # Community level distribution
            community_levels = {}
            if communities_df is not None and "level" in communities_df.columns:
                community_levels = communities_df["level"].value_counts().to_dict()
                # Convert numpy int keys to strings
                community_levels = {str(k): int(v) for k, v in community_levels.items()}

            # Calculate graph density
            # Density = 2 * edges / (nodes * (nodes - 1))
            graph_density = 0.0
            if total_entities > 1:
                max_edges = total_entities * (total_entities - 1)
                graph_density = (2.0 * total_relationships) / max_edges

            # Estimate connected components (simplified - actual calculation would require graph analysis)
            connected_components = 1 if total_relationships > 0 else total_entities

            return {
                "total_entities": total_entities,
                "total_relationships": total_relationships,
                "total_communities": total_communities,
                "entity_types": entity_types,
                "relationship_types": relationship_types,
                "community_levels": community_levels,
                "graph_density": round(graph_density, 6),
                "connected_components": connected_components,
            }

        except Exception as e:
            logger.error(f"Graph statistics calculation failed: {e}")
            raise GraphOperationsError(f"Graph statistics calculation failed: {e}") from e

    async def generate_visualization(
        self,
        data_path: str,
        entity_limit: int = 100,
        relationship_limit: int = 200,
        community_level: int | None = None,
        layout_algorithm: str = "force_directed",
        include_node_labels: bool = True,
        include_edge_labels: bool = False,
    ) -> dict[str, Any]:
        """Generate graph visualization data.

        Args:
            data_path: Path to GraphRAG data directory
            entity_limit: Maximum number of entities to include
            relationship_limit: Maximum number of relationships to include
            community_level: Optional community level filter
            layout_algorithm: Layout algorithm to use
            include_node_labels: Whether to include node labels
            include_edge_labels: Whether to include edge labels

        Returns:
            Dictionary containing visualization data

        Raises:
            GraphOperationsError: If visualization generation fails
        """
        try:
            # Load data files
            entities_df = self._load_parquet_file(data_path, "create_final_entities.parquet")
            relationships_df = self._load_parquet_file(
                data_path, "create_final_relationships.parquet"
            )
            # Load communities for potential future use in visualization
            self._load_parquet_file(data_path, "create_final_communities.parquet")

            if entities_df is None or relationships_df is None:
                raise GraphOperationsError("Graph data not found. Please run indexing first.")

            # Sample entities (prefer higher degree nodes for better visualization)
            if "degree" in entities_df.columns:
                entities_sample = entities_df.nlargest(entity_limit, "degree")
            else:
                entities_sample = entities_df.head(entity_limit)

            # Get entity IDs for filtering relationships
            entity_ids = set(entities_sample["title"].tolist())

            # Filter relationships to only include those between sampled entities
            rel_mask = (relationships_df["source"].isin(entity_ids)) & (
                relationships_df["target"].isin(entity_ids)
            )
            relationships_sample = relationships_df[rel_mask].head(relationship_limit)

            # Create nodes
            nodes = []
            for _, entity in entities_sample.iterrows():
                node = {
                    "id": entity["title"],
                    "label": entity["title"] if include_node_labels else "",
                    "type": entity.get("type", "unknown"),
                    "size": min(
                        max(entity.get("degree", 1) * 2, 5), 20
                    ),  # Scale node size by degree
                    "community": (
                        entity.get("community_ids", [None])[0]
                        if entity.get("community_ids") is not None
                        and len(entity.get("community_ids", [])) > 0
                        else None
                    ),
                    "description": (
                        str(entity.get("description", ""))[:100] + "..."
                        if len(str(entity.get("description", ""))) > 100
                        else str(entity.get("description", ""))
                    ),
                }
                nodes.append(node)

            # Create edges
            edges = []
            for _, rel in relationships_sample.iterrows():
                edge = {
                    "source": rel["source"],
                    "target": rel["target"],
                    "type": rel.get("type", "unknown"),
                    "weight": rel.get("weight", 1.0),
                    "label": rel.get("description", "") if include_edge_labels else "",
                }
                edges.append(edge)

            # Metadata
            metadata = {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "layout_algorithm": layout_algorithm,
                "entity_limit": entity_limit,
                "relationship_limit": relationship_limit,
                "community_level": community_level,
                "generated_at": datetime.now(UTC).isoformat(),
            }

            return {
                "nodes": nodes,
                "edges": edges,
                "layout": layout_algorithm,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"Graph visualization generation failed: {e}")
            raise GraphOperationsError(f"Graph visualization generation failed: {e}") from e

    async def export_graph(
        self,
        data_path: str,
        format: str = "json",
        include_entities: bool = True,
        include_relationships: bool = True,
        include_communities: bool = True,
        entity_limit: int | None = None,
        relationship_limit: int | None = None,
    ) -> dict[str, Any]:
        """Export graph data in various formats.

        Args:
            data_path: Path to GraphRAG data directory
            format: Export format (json, csv)
            include_entities: Include entities in export
            include_relationships: Include relationships in export
            include_communities: Include communities in export
            entity_limit: Optional limit on entities
            relationship_limit: Optional limit on relationships

        Returns:
            Dictionary containing export information

        Raises:
            GraphOperationsError: If graph export fails
        """
        try:
            export_data = {}

            # Load and include entities
            if include_entities:
                entities_df = self._load_parquet_file(data_path, "create_final_entities.parquet")
                if entities_df is not None:
                    if entity_limit:
                        entities_df = entities_df.head(entity_limit)
                    export_data["entities"] = entities_df.to_dict(orient="records")

            # Load and include relationships
            if include_relationships:
                relationships_df = self._load_parquet_file(
                    data_path, "create_final_relationships.parquet"
                )
                if relationships_df is not None:
                    if relationship_limit:
                        relationships_df = relationships_df.head(relationship_limit)
                    export_data["relationships"] = relationships_df.to_dict(orient="records")

            # Load and include communities
            if include_communities:
                communities_df = self._load_parquet_file(
                    data_path, "create_final_communities.parquet"
                )
                if communities_df is not None:
                    export_data["communities"] = communities_df.to_dict(orient="records")

            # Create temporary file for export
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=f".{format}", delete=False
            ) as temp_file:
                if format.lower() == "json":
                    json.dump(export_data, temp_file, indent=2, default=str)
                elif format.lower() == "csv":
                    # For CSV, export entities and relationships separately
                    if "entities" in export_data:
                        entities_df = pd.DataFrame(export_data["entities"])
                        entities_csv = temp_file.name.replace(".csv", "_entities.csv")
                        entities_df.to_csv(entities_csv, index=False)
                    if "relationships" in export_data:
                        relationships_df = pd.DataFrame(export_data["relationships"])
                        relationships_csv = temp_file.name.replace(".csv", "_relationships.csv")
                        relationships_df.to_csv(relationships_csv, index=False)

                temp_file_path = temp_file.name

            # Get file size
            file_size = Path(temp_file_path).stat().st_size

            # Calculate counts
            entity_count = len(export_data.get("entities", []))
            relationship_count = len(export_data.get("relationships", []))

            # Generate expiration time (24 hours from now)
            expires_at = (datetime.now(UTC) + timedelta(hours=24)).isoformat()

            # For now, return file path as download URL (in production, this would be a proper URL)
            download_url = f"/api/graph/download/{Path(temp_file_path).name}"

            self.metrics["exports"] += 1
            return {
                "download_url": download_url,
                "format": format,
                "file_size": file_size,
                "entity_count": entity_count,
                "relationship_count": relationship_count,
                "expires_at": expires_at,
            }

        except Exception as e:
            logger.error(f"Graph export failed: {e}")
            raise GraphOperationsError(f"Graph export failed: {e}") from e
