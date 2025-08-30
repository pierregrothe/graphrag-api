# src/graphrag_api_service/performance/load_testing.py
# Load Testing Framework and Benchmarking Tools
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Load testing framework for performance benchmarking and stress testing."""

import asyncio
import logging
import statistics
import time
from typing import Any

import aiohttp
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class LoadTestConfig(BaseModel):
    """Configuration for load testing."""

    base_url: str = "http://localhost:8000"
    concurrent_users: int = 10
    test_duration_seconds: int = 60
    ramp_up_seconds: int = 10
    requests_per_user: int | None = None
    timeout_seconds: float = 30.0


class LoadTestScenario(BaseModel):
    """Test scenario definition."""

    name: str
    method: str
    endpoint: str
    headers: dict[str, str] = {}
    payload: dict[str, Any] | None = None
    weight: float = 1.0  # Relative frequency of this scenario


class LoadTestResult(BaseModel):
    """Load test result statistics."""

    scenario_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    min_response_time: float
    max_response_time: float
    p50_response_time: float
    p90_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    error_rate: float
    errors: dict[str, int]


class BenchmarkSuite:
    """Comprehensive benchmark suite for GraphRAG API."""

    def __init__(self, config: LoadTestConfig):
        """Initialize the benchmark suite.

        Args:
            config: Load test configuration
        """
        self.config = config
        self.scenarios = self._create_default_scenarios()

    def _create_default_scenarios(self) -> list[LoadTestScenario]:
        """Create default test scenarios.

        Returns:
            List of test scenarios
        """
        return [
            # Basic API endpoints
            LoadTestScenario(name="health_check", method="GET", endpoint="/health", weight=0.1),
            LoadTestScenario(
                name="get_entities", method="GET", endpoint="/api/entities", weight=0.3
            ),
            LoadTestScenario(
                name="get_relationships", method="GET", endpoint="/api/relationships", weight=0.3
            ),
            LoadTestScenario(
                name="search_entities",
                method="POST",
                endpoint="/api/entities/search",
                payload={"query": "test entity", "limit": 10},
                weight=0.2,
            ),
            # Advanced features
            LoadTestScenario(
                name="multi_hop_query",
                method="POST",
                endpoint="/api/graph/query/multi-hop",
                payload={
                    "start_entities": ["entity1"],
                    "end_entities": ["entity2"],
                    "max_hops": 3,
                    "scoring_algorithm": "pagerank",
                },
                weight=0.05,
            ),
            LoadTestScenario(
                name="community_detection",
                method="POST",
                endpoint="/api/graph/analytics/communities",
                payload={"algorithm": "louvain", "resolution": 1.0},
                weight=0.05,
            ),
        ]

    def add_scenario(self, scenario: LoadTestScenario) -> None:
        """Add a custom test scenario.

        Args:
            scenario: Test scenario to add
        """
        self.scenarios.append(scenario)

    async def run_load_test(self) -> dict[str, LoadTestResult]:
        """Run the complete load test suite.

        Returns:
            Dictionary of test results by scenario name
        """
        logger.info(
            f"Starting load test with {self.config.concurrent_users} users for {self.config.test_duration_seconds}s"
        )

        # Create user tasks
        tasks = []
        for user_id in range(self.config.concurrent_users):
            # Stagger user start times for ramp-up
            start_delay = (user_id / self.config.concurrent_users) * self.config.ramp_up_seconds
            task = asyncio.create_task(self._simulate_user(user_id, start_delay))
            tasks.append(task)

        # Wait for all users to complete
        user_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and keep only successful results
        valid_results = [
            result for result in user_results 
            if not isinstance(result, BaseException)
        ]

        # Aggregate results by scenario
        scenario_results = {}
        for scenario in self.scenarios:
            scenario_results[scenario.name] = self._aggregate_scenario_results(
                scenario.name, valid_results
            )

        logger.info("Load test completed")
        return scenario_results

    async def _simulate_user(self, user_id: int, start_delay: float) -> list[dict[str, Any]]:
        """Simulate a single user's behavior.

        Args:
            user_id: User identifier
            start_delay: Delay before starting requests

        Returns:
            List of request results
        """
        await asyncio.sleep(start_delay)

        results = []
        start_time = time.time()
        request_count = 0

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        ) as session:
            while True:
                # Check if test duration exceeded
                if time.time() - start_time > self.config.test_duration_seconds:
                    break

                # Check if request limit reached
                if self.config.requests_per_user and request_count >= self.config.requests_per_user:
                    break

                # Select scenario based on weights
                scenario = self._select_weighted_scenario()
                result = await self._execute_request(session, scenario, user_id)
                results.append(result)
                request_count += 1

                # Small delay between requests
                await asyncio.sleep(0.1)

        logger.debug(f"User {user_id} completed {request_count} requests")
        return results

    def _select_weighted_scenario(self) -> LoadTestScenario:
        """Select a scenario based on weights.

        Returns:
            Selected test scenario
        """
        import random

        total_weight = sum(scenario.weight for scenario in self.scenarios)
        random_value = random.uniform(0, total_weight)

        cumulative_weight = 0
        for scenario in self.scenarios:
            cumulative_weight += scenario.weight
            if random_value <= cumulative_weight:
                return scenario

        return self.scenarios[-1]  # Fallback

    async def _execute_request(
        self, session: aiohttp.ClientSession, scenario: LoadTestScenario, user_id: int
    ) -> dict[str, Any]:
        """Execute a single request.

        Args:
            session: HTTP session
            scenario: Test scenario
            user_id: User identifier

        Returns:
            Request result
        """
        url = f"{self.config.base_url}{scenario.endpoint}"
        start_time = time.time()

        try:
            if scenario.method.upper() == "GET":
                async with session.get(url, headers=scenario.headers) as response:
                    await response.text()
                    status_code = response.status
            else:
                async with session.request(
                    scenario.method.upper(), url, json=scenario.payload, headers=scenario.headers
                ) as response:
                    await response.text()
                    status_code = response.status

            response_time = time.time() - start_time
            success = 200 <= status_code < 400

            return {
                "scenario": scenario.name,
                "user_id": user_id,
                "success": success,
                "status_code": status_code,
                "response_time": response_time,
                "error": None,
                "timestamp": start_time,
            }

        except Exception as e:
            response_time = time.time() - start_time
            return {
                "scenario": scenario.name,
                "user_id": user_id,
                "success": False,
                "status_code": 0,
                "response_time": response_time,
                "error": str(e),
                "timestamp": start_time,
            }

    def _aggregate_scenario_results(
        self, scenario_name: str, user_results: list[list[dict[str, Any]]]
    ) -> LoadTestResult:
        """Aggregate results for a specific scenario.

        Args:
            scenario_name: Name of the scenario
            user_results: Results from all users

        Returns:
            Aggregated load test result
        """
        # Flatten and filter results for this scenario
        scenario_requests = []
        for user_result in user_results:
            if isinstance(user_result, list):
                scenario_requests.extend(
                    [req for req in user_result if req.get("scenario") == scenario_name]
                )

        if not scenario_requests:
            return LoadTestResult(
                scenario_name=scenario_name,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                average_response_time=0.0,
                min_response_time=0.0,
                max_response_time=0.0,
                p50_response_time=0.0,
                p90_response_time=0.0,
                p95_response_time=0.0,
                p99_response_time=0.0,
                requests_per_second=0.0,
                error_rate=0.0,
                errors={},
            )

        # Calculate statistics
        total_requests = len(scenario_requests)
        successful_requests = sum(1 for req in scenario_requests if req["success"])
        failed_requests = total_requests - successful_requests

        response_times = [req["response_time"] for req in scenario_requests]
        response_times.sort()

        # Calculate percentiles
        def percentile(data: list[float], p: float) -> float:
            if not data:
                return 0.0
            index = int(len(data) * p / 100)
            return data[min(index, len(data) - 1)]

        # Calculate requests per second
        if scenario_requests:
            start_time = min(req["timestamp"] for req in scenario_requests)
            end_time = max(req["timestamp"] + req["response_time"] for req in scenario_requests)
            duration = max(end_time - start_time, 1.0)
            requests_per_second = total_requests / duration
        else:
            requests_per_second = 0.0

        # Count errors
        errors = {}
        for req in scenario_requests:
            if not req["success"]:
                error_key = req.get("error", f"HTTP_{req['status_code']}")
                errors[error_key] = errors.get(error_key, 0) + 1

        return LoadTestResult(
            scenario_name=scenario_name,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            average_response_time=statistics.mean(response_times) if response_times else 0.0,
            min_response_time=min(response_times) if response_times else 0.0,
            max_response_time=max(response_times) if response_times else 0.0,
            p50_response_time=percentile(response_times, 50),
            p90_response_time=percentile(response_times, 90),
            p95_response_time=percentile(response_times, 95),
            p99_response_time=percentile(response_times, 99),
            requests_per_second=requests_per_second,
            error_rate=failed_requests / total_requests if total_requests > 0 else 0.0,
            errors=errors,
        )

    def generate_report(self, results: dict[str, LoadTestResult]) -> str:
        """Generate a human-readable test report.

        Args:
            results: Test results by scenario

        Returns:
            Formatted test report
        """
        report = []
        report.append("=" * 80)
        report.append("GRAPHRAG API LOAD TEST REPORT")
        report.append("=" * 80)
        report.append("Configuration:")
        report.append(f"  Concurrent Users: {self.config.concurrent_users}")
        report.append(f"  Test Duration: {self.config.test_duration_seconds}s")
        report.append(f"  Ramp-up Time: {self.config.ramp_up_seconds}s")
        report.append("")

        for scenario_name, result in results.items():
            report.append(f"Scenario: {scenario_name}")
            report.append("-" * 40)
            report.append(f"  Total Requests: {result.total_requests}")
            report.append(f"  Successful: {result.successful_requests}")
            report.append(f"  Failed: {result.failed_requests}")
            report.append(f"  Success Rate: {(1 - result.error_rate) * 100:.1f}%")
            report.append(f"  Requests/sec: {result.requests_per_second:.2f}")
            report.append("")
            report.append("  Response Times (ms):")
            report.append(f"    Average: {result.average_response_time * 1000:.1f}")
            report.append(f"    Min: {result.min_response_time * 1000:.1f}")
            report.append(f"    Max: {result.max_response_time * 1000:.1f}")
            report.append(f"    P50: {result.p50_response_time * 1000:.1f}")
            report.append(f"    P90: {result.p90_response_time * 1000:.1f}")
            report.append(f"    P95: {result.p95_response_time * 1000:.1f}")
            report.append(f"    P99: {result.p99_response_time * 1000:.1f}")

            if result.errors:
                report.append("  Errors:")
                for error, count in result.errors.items():
                    report.append(f"    {error}: {count}")

            report.append("")

        return "\n".join(report)
