# tests/test_postman_runner.py
# Python test runner for Postman collections
# Author: Pierre Grothé
# Creation Date: 2025-09-01

"""Execute Postman collections using Python for automated API testing."""

import json
import time
from pathlib import Path

import httpx
import pytest


class PostmanCollectionRunner:
    """Run Postman collections programmatically."""

    def __init__(self, base_url: str = "http://localhost:8001"):
        """Initialize the Postman collection runner.

        Args:
            base_url: Base URL for API requests
        """
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url, timeout=30.0)
        self.environment = {}
        self.test_results = []

    def load_collection(self, collection_path: str) -> dict:
        """Load a Postman collection from file.

        Args:
            collection_path: Path to the collection JSON file

        Returns:
            Collection data
        """
        with open(collection_path) as f:
            return json.load(f)

    def replace_variables(self, text: str) -> str:
        """Replace Postman variables in text.

        Args:
            text: Text containing variables

        Returns:
            Text with variables replaced
        """
        # Replace environment variables
        for _key, value in self.environment.items():
            text = text.replace("{{key}}", str(value))

        # Replace base_url
        text = text.replace("{{base_url}}", self.base_url)

        # Replace timestamp
        text = text.replace("{{$timestamp}}", str(int(time.time() * 1000)))

        return text

    def execute_request(self, request_item: dict) -> httpx.Response:
        """Execute a single Postman request.

        Args:
            request_item: Postman request item

        Returns:
            HTTP response
        """
        request = request_item.get("request", {})

        # Get method and URL
        method = request.get("method", "GET")
        url_data = request.get("url", {})

        # Build URL
        if isinstance(url_data, str):
            url = self.replace_variables(url_data)
        else:
            # Handle structured URL
            path = "/".join(url_data.get("path", []))
            url = f"/{path}" if path else "/"

            # Add query parameters
            if "query" in url_data:
                params = {q["key"]: q["value"] for q in url_data["query"]}
                param_str = "&".join(f"{k}={v}" for k, v in params.items())
                url = f"{url}?{param_str}"

        # Get headers
        headers = {}
        for header in request.get("header", []):
            headers[header["key"]] = header["value"]

        # Get body
        body = None
        body_data = request.get("body", {})
        if body_data.get("mode") == "raw":
            body = self.replace_variables(body_data.get("raw", ""))
        elif body_data.get("mode") == "graphql":
            graphql = body_data.get("graphql", {})
            body = json.dumps(
                {
                    "query": graphql.get("query", ""),
                    "variables": (
                        json.loads(graphql.get("variables", "{}"))
                        if graphql.get("variables")
                        else None
                    ),
                }
            )
            headers["Content-Type"] = "application/json"

        # Execute request
        response = self.client.request(method=method, url=url, headers=headers, content=body)

        return response

    def run_tests(self, item: dict, response: httpx.Response) -> list[dict]:
        """Run tests for a request.

        Args:
            item: Postman request item
            response: HTTP response

        Returns:
            Test results
        """
        results = []

        # Get test scripts
        events = item.get("event", [])
        for event in events:
            if event.get("listen") == "test":
                script = event.get("script", {})
                exec_lines = script.get("exec", [])

                # Simple test execution (basic checks)
                for line in exec_lines:
                    if "pm.test" in line and "Status code is 200" in line:
                        passed = response.status_code == 200
                        results.append(
                            {
                                "name": "Status code is 200",
                                "passed": passed,
                                "actual": response.status_code,
                            }
                        )
                    elif "pm.test" in line and "Status code is 200 or 500" in line:
                        passed = response.status_code in [200, 500]
                        results.append(
                            {
                                "name": "Status code is 200 or 500",
                                "passed": passed,
                                "actual": response.status_code,
                            }
                        )

        return results

    def run_collection(self, collection_path: str) -> dict:
        """Run an entire Postman collection.

        Args:
            collection_path: Path to the collection JSON file

        Returns:
            Test results summary
        """
        collection = self.load_collection(collection_path)
        collection_name = collection["info"]["name"]

        total_requests = 0
        total_passed = 0
        total_failed = 0
        failures = []

        print(f"\nRunning collection: {collection_name}")
        print("=" * 60)

        def run_items(items, folder_name=""):
            nonlocal total_requests, total_passed, total_failed

            for item in items:
                if "item" in item:
                    # It's a folder
                    folder = item["name"]
                    print(f"\n{folder}:")
                    run_items(item["item"], folder)
                else:
                    # It's a request
                    name = item.get("name", "Unnamed")
                    print(f"  - {name}: ", end="")

                    try:
                        response = self.execute_request(item)
                        tests = self.run_tests(item, response)

                        total_requests += 1

                        if not tests:
                            # No tests defined, check status code
                            if response.status_code < 400:
                                print("PASS")
                                total_passed += 1
                            else:
                                print(f"FAIL (status: {response.status_code})")
                                total_failed += 1
                                failures.append(
                                    {
                                        "folder": folder_name,
                                        "request": name,
                                        "error": f"Status code: {response.status_code}",
                                    }
                                )
                        else:
                            # Run defined tests
                            all_passed = all(t["passed"] for t in tests)
                            if all_passed:
                                print("PASS")
                                total_passed += 1
                            else:
                                print("FAIL")
                                total_failed += 1
                                failed_tests = [t for t in tests if not t["passed"]]
                                failures.append(
                                    {
                                        "folder": folder_name,
                                        "request": name,
                                        "failed_tests": failed_tests,
                                    }
                                )

                    except Exception as e:
                        print(f"ERROR: {e}")
                        total_failed += 1
                        failures.append({"folder": folder_name, "request": name, "error": str(e)})

        run_items(collection.get("item", []))

        # Print summary
        print("\n" + "=" * 60)
        print(f"Total requests: {total_requests}")
        print(f"Passed: {total_passed}")
        print(f"Failed: {total_failed}")

        if failures:
            print("\nFailures:")
            for failure in failures:
                print(
                    f"  - {failure['folder']}/{failure['request']}: {failure.get('error', 'Test failures')}"
                )

        return {
            "collection": collection_name,
            "total": total_requests,
            "passed": total_passed,
            "failed": total_failed,
            "failures": failures,
        }


class TestPostmanCollections:
    """Test suite for running Postman collections."""

    @pytest.fixture
    def runner(self):
        """Create a Postman collection runner."""
        return PostmanCollectionRunner()

    def test_rest_api_collection(self, runner):
        """Test REST API collection."""
        collection_path = Path(__file__).parent / "postman" / "graphrag_api_collection.json"

        if not collection_path.exists():
            pytest.skip("REST API collection not found")

        results = runner.run_collection(str(collection_path))

        # Assert that most tests pass
        assert results["failed"] / results["total"] < 0.2  # Less than 20% failure rate

    def test_graphql_collection(self, runner):
        """Test GraphQL collection."""
        collection_path = Path(__file__).parent / "postman" / "graphql_collection.json"

        if not collection_path.exists():
            pytest.skip("GraphQL collection not found")

        results = runner.run_collection(str(collection_path))

        # Assert that most tests pass
        assert results["failed"] / results["total"] < 0.2  # Less than 20% failure rate

    @pytest.mark.integration
    def test_health_endpoints(self, runner):
        """Test health endpoints specifically."""
        # Create a minimal collection for health checks
        health_collection = {
            "info": {"name": "Health Check Collection"},
            "item": [
                {"name": "Root Endpoint", "request": {"method": "GET", "url": "/"}},
                {"name": "Health Endpoint", "request": {"method": "GET", "url": "/api/health"}},
                {"name": "Info Endpoint", "request": {"method": "GET", "url": "/api/info"}},
            ],
        }

        # Test each endpoint
        for item in health_collection["item"]:
            response = runner.execute_request(item)
            assert response.status_code == 200

    @pytest.mark.integration
    def test_workspace_crud_operations(self, runner):
        """Test workspace CRUD operations."""
        workspace_id = None

        # Create workspace
        create_request = {
            "request": {
                "method": "POST",
                "url": "/api/workspaces",
                "header": [{"key": "Content-Type", "value": "application/json"}],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps(
                        {
                            "name": f"test-workspace-{int(time.time())}",
                            "description": "Test workspace",
                            "data_path": "./test_data",
                        }
                    ),
                },
            }
        }

        response = runner.execute_request(create_request)
        assert response.status_code == 200
        workspace_id = response.json()["id"]

        # Get workspace
        get_request = {"request": {"method": "GET", "url": f"/api/workspaces/{workspace_id}"}}

        response = runner.execute_request(get_request)
        assert response.status_code == 200

        # Update workspace
        update_request = {
            "request": {
                "method": "PUT",
                "url": f"/api/workspaces/{workspace_id}",
                "header": [{"key": "Content-Type", "value": "application/json"}],
                "body": {"mode": "raw", "raw": json.dumps({"description": "Updated description"})},
            }
        }

        response = runner.execute_request(update_request)
        assert response.status_code == 200

        # Delete workspace
        delete_request = {"request": {"method": "DELETE", "url": f"/api/workspaces/{workspace_id}"}}

        response = runner.execute_request(delete_request)
        assert response.status_code == 200


def main():
    """Run Postman collections from command line."""
    runner = PostmanCollectionRunner()

    # Run REST API collection
    rest_collection = Path(__file__).parent / "postman" / "graphrag_api_collection.json"
    if rest_collection.exists():
        print("\n" + "=" * 60)
        print("REST API COLLECTION")
        print("=" * 60)
        runner.run_collection(str(rest_collection))

    # Run GraphQL collection
    graphql_collection = Path(__file__).parent / "postman" / "graphql_collection.json"
    if graphql_collection.exists():
        print("\n" + "=" * 60)
        print("GRAPHQL COLLECTION")
        print("=" * 60)
        runner.run_collection(str(graphql_collection))


if __name__ == "__main__":
    main()
