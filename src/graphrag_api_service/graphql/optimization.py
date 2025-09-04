# src/graphrag_api_service/graphql/optimization.py
# GraphQL Query Optimization and Field Selection
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""GraphQL query optimization with field selection and performance enhancements."""

import logging
from typing import Any

from strawberry.types import Info

from graphql import (
    FieldNode,
    FragmentSpreadNode,
    InlineFragmentNode,
    SelectionNode,
    SelectionSetNode,
)

logger = logging.getLogger(__name__)


class FieldSelector:
    """Optimizes database queries based on GraphQL field selection."""

    def __init__(self) -> None:
        """Initialize the field selector."""
        self._field_mappings = {
            # Entity field mappings
            "Entity": {
                "id": "id",
                "title": "title",
                "type": "type",
                "description": "description",
                "degree": "degree",
                "community_ids": "community_ids",
                "text_unit_ids": "text_unit_ids",
            },
            # Relationship field mappings
            "Relationship": {
                "id": "id",
                "source": "source",
                "target": "target",
                "type": "type",
                "description": "description",
                "weight": "weight",
                "text_unit_ids": "text_unit_ids",
            },
            # Community field mappings
            "Community": {
                "id": "id",
                "level": "level",
                "title": "title",
                "entity_ids": "entity_ids",
                "relationship_ids": "relationship_ids",
            },
        }

    def get_selected_fields(self, type_name: str, info: Info) -> set[str]:
        """Get the fields selected in the GraphQL query.

        Args:
            type_name: Type name to get fields for
            info: GraphQL resolver info

        Returns:
            Set of selected field names
        """
        if not info.selected_fields:
            return set()

        selected_fields = set()

        for field in info.selected_fields:
            # Strawberry's selected_fields are SelectedField objects
            # They have a 'name' attribute that is a string
            try:
                field_name = getattr(field, "name", None)
                if field_name:
                    selected_fields.add(field_name)
            except (AttributeError, TypeError):
                pass

            # Handle nested selections if available
            try:
                selections = getattr(field, "selections", [])
                for selection in selections:
                    selection_name = getattr(selection, "name", None)
                    if selection_name:
                        selected_fields.add(selection_name)
            except (AttributeError, TypeError):
                pass

        return selected_fields

    def _extract_fields_from_selection_set(
        self, selection_set: SelectionSetNode, type_name: str
    ) -> set[str]:
        """Extract field names from a GraphQL selection set.

        Args:
            selection_set: GraphQL selection set
            type_name: Type name for field mapping

        Returns:
            Set of field names
        """
        fields = set()

        for selection in selection_set.selections:
            if isinstance(selection, FieldNode):
                field_name = selection.name.value

                # Map GraphQL field to database field
                if type_name in self._field_mappings:
                    db_field = self._field_mappings[type_name].get(field_name, field_name)
                    fields.add(db_field)
                else:
                    fields.add(field_name)

        return fields

    def optimize_entity_query(self, base_query: dict[str, Any], info: Info) -> dict[str, Any]:
        """Optimize entity query based on selected fields.

        Args:
            base_query: Base query parameters
            info: GraphQL resolver info

        Returns:
            Optimized query parameters
        """
        selected_fields = self.get_selected_fields("Entity", info)

        if not selected_fields:
            return base_query

        # Add field selection to query
        optimized_query = base_query.copy()
        optimized_query["fields"] = list(selected_fields)

        # Optimize based on specific field requirements
        if "degree" in selected_fields:
            optimized_query["include_degree"] = True

        if "community_ids" in selected_fields:
            optimized_query["include_communities"] = True

        logger.debug(f"Optimized entity query with fields: {selected_fields}")
        return optimized_query

    def optimize_relationship_query(self, base_query: dict[str, Any], info: Info) -> dict[str, Any]:
        """Optimize relationship query based on selected fields.

        Args:
            base_query: Base query parameters
            info: GraphQL resolver info

        Returns:
            Optimized query parameters
        """
        selected_fields = self.get_selected_fields("Relationship", info)

        if not selected_fields:
            return base_query

        # Add field selection to query
        optimized_query = base_query.copy()
        optimized_query["fields"] = list(selected_fields)

        # Optimize based on specific field requirements
        if "weight" in selected_fields:
            optimized_query["include_weights"] = True

        logger.debug(f"Optimized relationship query with fields: {selected_fields}")
        return optimized_query


class QueryComplexityAnalyzer:
    """Analyzes and limits GraphQL query complexity."""

    def __init__(self, max_complexity: int = 1000):
        """Initialize the complexity analyzer.

        Args:
            max_complexity: Maximum allowed query complexity
        """
        self.max_complexity = max_complexity
        self._field_costs = {
            # Basic fields
            "id": 1,
            "title": 1,
            "type": 1,
            "description": 2,
            # Computed fields
            "degree": 5,
            "community_ids": 10,
            "text_unit_ids": 5,
            # Relationship fields
            "source": 1,
            "target": 1,
            "weight": 3,
            # Complex operations
            "entities": 20,
            "relationships": 20,
            "communities": 30,
        }

    def analyze_complexity(self, info: Info) -> int:
        """Analyze the complexity of a GraphQL query.

        Args:
            info: GraphQL resolver info

        Returns:
            Query complexity score
        """
        if not info.selected_fields:
            return 0

        total_complexity = 0

        for _ in info.selected_fields:
            # Calculate complexity for each field - use simplified approach
            total_complexity += 1  # Basic complexity per field

        return total_complexity

    def _calculate_field_complexity(
        self,
        field: SelectionNode | FieldNode | InlineFragmentNode | FragmentSpreadNode,
        depth: int = 0,
    ) -> int:
        """Calculate complexity for a single field.

        Args:
            field: GraphQL field selection node
            depth: Current nesting depth

        Returns:
            Field complexity score
        """
        if isinstance(field, FieldNode) and hasattr(field, "name"):
            field_name = field.name.value
        else:
            field_name = "unknown"
        base_cost = self._field_costs.get(field_name, 1)

        # Apply depth penalty
        depth_penalty = depth * 2
        field_cost = base_cost + depth_penalty

        # Calculate nested field costs
        if (
            isinstance(field, FieldNode | InlineFragmentNode)
            and hasattr(field, "selection_set")
            and field.selection_set
        ):
            for nested_selection in field.selection_set.selections:
                if isinstance(
                    nested_selection, FieldNode | InlineFragmentNode | FragmentSpreadNode
                ):
                    field_cost += self._calculate_field_complexity(nested_selection, depth + 1)
        # FragmentSpreadNode doesn't have selection_set, it references a fragment definition

        return field_cost

    def validate_complexity(self, info: Info) -> None:
        """Validate that query complexity is within limits.

        Args:
            info: GraphQL resolver info

        Raises:
            Exception: If query complexity exceeds limits
        """
        complexity = self.analyze_complexity(info)

        if complexity > self.max_complexity:
            raise Exception(
                f"Query complexity {complexity} exceeds maximum allowed {self.max_complexity}"
            )

        logger.debug(f"Query complexity: {complexity}")


class QueryCache:
    """Caches GraphQL query results based on field selection."""

    def __init__(self) -> None:
        """Initialize the query cache."""
        self._cache: dict[str, Any] = {}

    def generate_cache_key(self, query_type: str, params: dict[str, Any], fields: set[str]) -> str:
        """Generate a cache key for a query.

        Args:
            query_type: Type of query
            params: Query parameters
            fields: Selected fields

        Returns:
            Cache key string
        """
        import hashlib
        import json

        cache_data = {
            "query_type": query_type,
            "params": params,
            "fields": sorted(fields),
        }

        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_string.encode()).hexdigest()[:16]

    def get(self, cache_key: str) -> Any | None:
        """Get cached result.

        Args:
            cache_key: Cache key

        Returns:
            Cached result if available
        """
        return self._cache.get(cache_key)

    def set(self, cache_key: str, result: Any, ttl: int = 300) -> None:
        """Set cached result.

        Args:
            cache_key: Cache key
            result: Result to cache
            ttl: Time to live in seconds
        """
        import time

        self._cache[cache_key] = {
            "result": result,
            "expires_at": time.time() + ttl,
        }

    def is_expired(self, cache_key: str) -> bool:
        """Check if cached result is expired.

        Args:
            cache_key: Cache key

        Returns:
            True if expired
        """
        import time

        cached_item = self._cache.get(cache_key)
        if not cached_item:
            return True

        return bool(time.time() > cached_item["expires_at"])

    def cleanup_expired(self) -> None:
        """Remove expired cache entries."""
        import time

        current_time = time.time()
        expired_keys = [
            key for key, item in self._cache.items() if current_time > item["expires_at"]
        ]

        for key in expired_keys:
            del self._cache[key]


# Global instances
_field_selector: FieldSelector | None = None
_complexity_analyzer: QueryComplexityAnalyzer | None = None
_query_cache: QueryCache | None = None


def get_field_selector() -> FieldSelector:
    """Get the global field selector instance.

    Returns:
        Field selector instance
    """
    global _field_selector

    if _field_selector is None:
        _field_selector = FieldSelector()

    return _field_selector


def get_complexity_analyzer() -> QueryComplexityAnalyzer:
    """Get the global complexity analyzer instance.

    Returns:
        Complexity analyzer instance
    """
    global _complexity_analyzer

    if _complexity_analyzer is None:
        _complexity_analyzer = QueryComplexityAnalyzer()

    return _complexity_analyzer


def get_query_cache() -> QueryCache:
    """Get the global query cache instance.

    Returns:
        Query cache instance
    """
    global _query_cache

    if _query_cache is None:
        _query_cache = QueryCache()

    return _query_cache
