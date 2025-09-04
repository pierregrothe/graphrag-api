# src/graphrag_api_service/graphql/schema.py
# GraphQL schema definition
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""GraphQL schema combining queries and mutations."""

from typing import Any

import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.subscriptions import GRAPHQL_TRANSPORT_WS_PROTOCOL, GRAPHQL_WS_PROTOCOL

from .dataloaders import create_dataloaders
from .mutations import Mutation
from .queries import Query
from .subscriptions import Subscription

# Create the GraphQL schema with subscriptions
schema = strawberry.Schema(query=Query, mutation=Mutation, subscription=Subscription)


def create_graphql_router(
    graph_operations: Any = None,
    workspace_manager: Any = None,
    system_operations: Any = None,
    graphrag_integration: Any = None,
    indexing_manager: Any = None,
) -> GraphQLRouter[dict[str, Any], None]:
    """Create a GraphQL router with context.

    Args:
        graph_operations: Graph operations instance
        workspace_manager: Workspace manager instance
        system_operations: System operations instance
        graphrag_integration: GraphRAG integration instance
        indexing_manager: Indexing manager instance

    Returns:
        GraphQL router
    """

    def get_context() -> dict[str, Any]:
        """Get context for GraphQL resolvers."""
        # Create DataLoaders for this request
        dataloaders = {}
        if graph_operations:
            dataloaders = create_dataloaders(graph_operations)

        return {
            "graph_operations": graph_operations,
            "workspace_manager": workspace_manager,
            "system_operations": system_operations,
            "graphrag_integration": graphrag_integration,
            "indexing_manager": indexing_manager,
            "dataloaders": dataloaders,
        }

    # Create the main GraphQL router with subscription support
    graphql_router = GraphQLRouter(
        schema,
        context_getter=get_context,
        graphql_ide="graphiql",  # Enable GraphiQL playground
        subscription_protocols=[
            GRAPHQL_TRANSPORT_WS_PROTOCOL,
            GRAPHQL_WS_PROTOCOL,
        ],
    )

    # Return the GraphQL router directly
    return graphql_router
