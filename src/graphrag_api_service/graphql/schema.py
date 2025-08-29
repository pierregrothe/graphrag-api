# src/graphrag_api_service/graphql/schema.py
# GraphQL schema definition
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""GraphQL schema combining queries and mutations."""

import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.subscriptions import GRAPHQL_TRANSPORT_WS_PROTOCOL, GRAPHQL_WS_PROTOCOL

from .mutations import Mutation
from .queries import Query
from .subscriptions import Subscription

# Create the GraphQL schema with subscriptions
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription
)


def create_graphql_router(
    graph_operations=None,
    workspace_manager=None,
    system_operations=None,
    graphrag_integration=None,
    indexing_manager=None,
) -> GraphQLRouter:
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

    async def get_context():
        """Get context for GraphQL resolvers."""
        return {
            "graph_operations": graph_operations,
            "workspace_manager": workspace_manager,
            "system_operations": system_operations,
            "graphrag_integration": graphrag_integration,
            "indexing_manager": indexing_manager,
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
