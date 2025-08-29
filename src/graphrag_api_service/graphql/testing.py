# src/graphrag_api_service/graphql/testing.py
# GraphQL Testing Framework with Query Validation
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""GraphQL testing framework with comprehensive query validation and testing utilities."""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from graphql import build_schema, validate, parse, GraphQLError
from graphql.validation import ValidationRule
from strawberry.schema import Schema

logger = logging.getLogger(__name__)


class GraphQLTestCase:
    """Represents a single GraphQL test case."""

    def __init__(
        self,
        name: str,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        expected_data: Optional[Dict[str, Any]] = None,
        expected_errors: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a GraphQL test case.

        Args:
            name: Test case name
            query: GraphQL query string
            variables: Query variables
            expected_data: Expected response data
            expected_errors: Expected error messages
            context: Test context
        """
        self.name = name
        self.query = query
        self.variables = variables or {}
        self.expected_data = expected_data
        self.expected_errors = expected_errors or []
        self.context = context or {}


class GraphQLValidator:
    """Validates GraphQL queries and schemas."""

    def __init__(self, schema: Schema):
        """Initialize the validator.

        Args:
            schema: GraphQL schema to validate against
        """
        self.schema = schema

    def validate_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> List[GraphQLError]:
        """Validate a GraphQL query.

        Args:
            query: GraphQL query string
            variables: Query variables

        Returns:
            List of validation errors
        """
        try:
            # Parse the query
            document = parse(query)
            
            # Validate against schema
            errors = validate(self.schema._schema, document)
            
            return errors
        except Exception as e:
            return [GraphQLError(str(e))]

    def validate_query_complexity(self, query: str, max_depth: int = 10) -> List[str]:
        """Validate query complexity and depth.

        Args:
            query: GraphQL query string
            max_depth: Maximum allowed query depth

        Returns:
            List of complexity issues
        """
        issues = []
        
        try:
            document = parse(query)
            depth = self._calculate_query_depth(document)
            
            if depth > max_depth:
                issues.append(f"Query depth {depth} exceeds maximum {max_depth}")
                
        except Exception as e:
            issues.append(f"Error analyzing query complexity: {str(e)}")
            
        return issues

    def _calculate_query_depth(self, document) -> int:
        """Calculate the maximum depth of a GraphQL query.

        Args:
            document: Parsed GraphQL document

        Returns:
            Maximum query depth
        """
        max_depth = 0
        
        for definition in document.definitions:
            if hasattr(definition, 'selection_set'):
                depth = self._calculate_selection_depth(definition.selection_set, 1)
                max_depth = max(max_depth, depth)
                
        return max_depth

    def _calculate_selection_depth(self, selection_set, current_depth: int) -> int:
        """Calculate depth of a selection set.

        Args:
            selection_set: GraphQL selection set
            current_depth: Current depth level

        Returns:
            Maximum depth in this selection set
        """
        max_depth = current_depth
        
        if not selection_set or not selection_set.selections:
            return max_depth
            
        for selection in selection_set.selections:
            if hasattr(selection, 'selection_set') and selection.selection_set:
                depth = self._calculate_selection_depth(
                    selection.selection_set, current_depth + 1
                )
                max_depth = max(max_depth, depth)
                
        return max_depth


class GraphQLTestRunner:
    """Runs GraphQL test suites and validates results."""

    def __init__(self, schema: Schema):
        """Initialize the test runner.

        Args:
            schema: GraphQL schema to test against
        """
        self.schema = schema
        self.validator = GraphQLValidator(schema)

    async def run_test_case(self, test_case: GraphQLTestCase) -> Dict[str, Any]:
        """Run a single test case.

        Args:
            test_case: Test case to run

        Returns:
            Test result with status and details
        """
        result = {
            "name": test_case.name,
            "status": "passed",
            "errors": [],
            "warnings": [],
            "execution_time": 0.0,
        }

        try:
            import time
            start_time = time.time()

            # Validate query syntax
            validation_errors = self.validator.validate_query(
                test_case.query, test_case.variables
            )
            
            if validation_errors:
                result["status"] = "failed"
                result["errors"].extend([str(error) for error in validation_errors])
                return result

            # Check query complexity
            complexity_issues = self.validator.validate_query_complexity(test_case.query)
            if complexity_issues:
                result["warnings"].extend(complexity_issues)

            # Execute query
            response = await self.schema.execute(
                test_case.query,
                variable_values=test_case.variables,
                context_value=test_case.context,
            )

            result["execution_time"] = time.time() - start_time

            # Validate response
            if response.errors:
                if test_case.expected_errors:
                    # Check if errors match expected
                    error_messages = [str(error) for error in response.errors]
                    for expected_error in test_case.expected_errors:
                        if not any(expected_error in msg for msg in error_messages):
                            result["status"] = "failed"
                            result["errors"].append(f"Expected error not found: {expected_error}")
                else:
                    result["status"] = "failed"
                    result["errors"].extend([str(error) for error in response.errors])

            # Validate data
            if test_case.expected_data and response.data:
                if not self._compare_data(response.data, test_case.expected_data):
                    result["status"] = "failed"
                    result["errors"].append("Response data does not match expected data")

        except Exception as e:
            result["status"] = "failed"
            result["errors"].append(f"Test execution failed: {str(e)}")

        return result

    def _compare_data(self, actual: Any, expected: Any) -> bool:
        """Compare actual and expected data.

        Args:
            actual: Actual response data
            expected: Expected response data

        Returns:
            True if data matches
        """
        if type(actual) != type(expected):
            return False

        if isinstance(actual, dict):
            for key, value in expected.items():
                if key not in actual:
                    return False
                if not self._compare_data(actual[key], value):
                    return False
            return True

        elif isinstance(actual, list):
            if len(actual) != len(expected):
                return False
            for i, item in enumerate(expected):
                if not self._compare_data(actual[i], item):
                    return False
            return True

        else:
            return actual == expected

    async def run_test_suite(self, test_cases: List[GraphQLTestCase]) -> Dict[str, Any]:
        """Run a complete test suite.

        Args:
            test_cases: List of test cases to run

        Returns:
            Test suite results
        """
        results = {
            "total_tests": len(test_cases),
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "total_time": 0.0,
            "test_results": [],
        }

        import time
        start_time = time.time()

        for test_case in test_cases:
            test_result = await self.run_test_case(test_case)
            results["test_results"].append(test_result)

            if test_result["status"] == "passed":
                results["passed"] += 1
            else:
                results["failed"] += 1

            if test_result["warnings"]:
                results["warnings"] += len(test_result["warnings"])

        results["total_time"] = time.time() - start_time

        return results


class GraphQLTestSuiteBuilder:
    """Builds comprehensive test suites for GraphQL APIs."""

    def __init__(self):
        """Initialize the test suite builder."""
        self.test_cases: List[GraphQLTestCase] = []

    def add_entity_tests(self) -> None:
        """Add entity-related test cases."""
        # Basic entity query
        self.test_cases.append(GraphQLTestCase(
            name="entity_basic_query",
            query="""
                query GetEntities($limit: Int) {
                    entities(limit: $limit) {
                        id
                        title
                        type
                    }
                }
            """,
            variables={"limit": 10},
        ))

        # Entity with relationships
        self.test_cases.append(GraphQLTestCase(
            name="entity_with_relationships",
            query="""
                query GetEntityWithRelationships($entityId: String!) {
                    entity(id: $entityId) {
                        id
                        title
                        relationships {
                            id
                            source
                            target
                            type
                        }
                    }
                }
            """,
            variables={"entityId": "test-entity-1"},
        ))

    def add_relationship_tests(self) -> None:
        """Add relationship-related test cases."""
        self.test_cases.append(GraphQLTestCase(
            name="relationship_basic_query",
            query="""
                query GetRelationships($limit: Int) {
                    relationships(limit: $limit) {
                        id
                        source
                        target
                        type
                        weight
                    }
                }
            """,
            variables={"limit": 10},
        ))

    def add_community_tests(self) -> None:
        """Add community-related test cases."""
        self.test_cases.append(GraphQLTestCase(
            name="community_basic_query",
            query="""
                query GetCommunities($limit: Int) {
                    communities(limit: $limit) {
                        id
                        level
                        title
                        entityIds
                    }
                }
            """,
            variables={"limit": 10},
        ))

    def add_mutation_tests(self) -> None:
        """Add mutation test cases."""
        self.test_cases.append(GraphQLTestCase(
            name="create_workspace_mutation",
            query="""
                mutation CreateWorkspace($name: String!, $description: String) {
                    createWorkspace(name: $name, description: $description) {
                        id
                        name
                        description
                        status
                    }
                }
            """,
            variables={"name": "test-workspace", "description": "Test workspace"},
        ))

    def add_subscription_tests(self) -> None:
        """Add subscription test cases."""
        self.test_cases.append(GraphQLTestCase(
            name="indexing_updates_subscription",
            query="""
                subscription IndexingUpdates {
                    indexingUpdates {
                        workspaceId
                        status
                        progress
                        message
                    }
                }
            """,
        ))

    def build_comprehensive_suite(self) -> List[GraphQLTestCase]:
        """Build a comprehensive test suite.

        Returns:
            List of test cases
        """
        self.add_entity_tests()
        self.add_relationship_tests()
        self.add_community_tests()
        self.add_mutation_tests()
        self.add_subscription_tests()

        return self.test_cases
