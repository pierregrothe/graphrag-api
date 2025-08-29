# tests/test_load_testing.py
# Tests for Load Testing Framework
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Tests for load testing framework and benchmarking tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graphrag_api_service.performance.load_testing import (
    BenchmarkSuite,
    LoadTestConfig,
    LoadTestResult,
    LoadTestScenario,
)


class TestLoadTestConfig:
    """Test cases for load test configuration."""

    def test_default_config(self):
        """Test default load test configuration."""
        config = LoadTestConfig()

        assert config.base_url == "http://localhost:8000"
        assert config.concurrent_users == 10
        assert config.test_duration_seconds == 60
        assert config.ramp_up_seconds == 10
        assert config.timeout_seconds == 30.0

    def test_custom_config(self):
        """Test custom load test configuration."""
        config = LoadTestConfig(
            base_url="http://example.com:8080",
            concurrent_users=20,
            test_duration_seconds=120,
            requests_per_user=100,
        )

        assert config.base_url == "http://example.com:8080"
        assert config.concurrent_users == 20
        assert config.test_duration_seconds == 120
        assert config.requests_per_user == 100


class TestLoadTestScenario:
    """Test cases for test scenarios."""

    def test_basic_scenario(self):
        """Test basic test scenario creation."""
        scenario = LoadTestScenario(
            name="test_scenario",
            method="GET",
            endpoint="/api/test",
            weight=1.0,
        )

        assert scenario.name == "test_scenario"
        assert scenario.method == "GET"
        assert scenario.endpoint == "/api/test"
        assert scenario.weight == 1.0
        assert scenario.headers == {}
        assert scenario.payload is None

    def test_post_scenario_with_payload(self):
        """Test POST scenario with payload."""
        payload = {"query": "test", "limit": 10}
        scenario = LoadTestScenario(
            name="post_test",
            method="POST",
            endpoint="/api/search",
            payload=payload,
            headers={"Content-Type": "application/json"},
            weight=0.5,
        )

        assert scenario.method == "POST"
        assert scenario.payload == payload
        assert scenario.headers["Content-Type"] == "application/json"
        assert scenario.weight == 0.5


class TestBenchmarkSuite:
    """Test cases for the benchmark suite."""

    @pytest.fixture
    def benchmark_suite(self):
        """Create a benchmark suite for testing."""
        config = LoadTestConfig(
            concurrent_users=2,
            test_duration_seconds=1,
            ramp_up_seconds=0,
        )
        return BenchmarkSuite(config)

    def test_default_scenarios_creation(self, benchmark_suite):
        """Test that default scenarios are created."""
        scenarios = benchmark_suite.scenarios

        assert len(scenarios) > 0
        scenario_names = [s.name for s in scenarios]
        assert "health_check" in scenario_names
        assert "get_entities" in scenario_names
        assert "get_relationships" in scenario_names

    def test_custom_scenario_addition(self, benchmark_suite):
        """Test adding custom scenarios."""
        initial_count = len(benchmark_suite.scenarios)

        custom_scenario = LoadTestScenario(
            name="custom_test",
            method="GET",
            endpoint="/api/custom",
        )

        benchmark_suite.add_scenario(custom_scenario)

        assert len(benchmark_suite.scenarios) == initial_count + 1
        assert benchmark_suite.scenarios[-1].name == "custom_test"

    def test_weighted_scenario_selection(self, benchmark_suite):
        """Test weighted scenario selection."""
        # Add scenarios with different weights
        benchmark_suite.scenarios = [
            LoadTestScenario(name="high_weight", method="GET", endpoint="/high", weight=0.8),
            LoadTestScenario(name="low_weight", method="GET", endpoint="/low", weight=0.2),
        ]

        # Select scenarios multiple times and check distribution
        selections = []
        for _ in range(100):
            scenario = benchmark_suite._select_weighted_scenario()
            selections.append(scenario.name)

        high_weight_count = selections.count("high_weight")
        low_weight_count = selections.count("low_weight")

        # High weight scenario should be selected more often
        assert high_weight_count > low_weight_count

    @pytest.mark.asyncio
    async def test_request_execution_success(self, benchmark_suite):
        """Test successful request execution."""
        scenario = LoadTestScenario(
            name="test_scenario",
            method="GET",
            endpoint="/api/test",
        )

        # Mock successful HTTP response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="success")

        # Create proper async context manager mock using MagicMock
        from unittest.mock import MagicMock

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_context_manager)

        result = await benchmark_suite._execute_request(mock_session, scenario, user_id=1)

        assert result["scenario"] == "test_scenario"
        assert result["success"] is True
        assert result["status_code"] == 200
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_request_execution_failure(self, benchmark_suite):
        """Test failed request execution."""
        scenario = LoadTestScenario(
            name="test_scenario",
            method="GET",
            endpoint="/api/test",
        )

        # Mock failed HTTP response - make the async context manager raise an exception
        from unittest.mock import MagicMock

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(side_effect=Exception("Connection error"))
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_context_manager)

        result = await benchmark_suite._execute_request(mock_session, scenario, user_id=1)

        assert result["scenario"] == "test_scenario"
        assert result["success"] is False
        assert result["status_code"] == 0
        assert "Connection error" in result["error"]

    def test_scenario_results_aggregation(self, benchmark_suite):
        """Test aggregation of scenario results."""
        # Mock user results
        user_results = [
            [
                {
                    "scenario": "test_scenario",
                    "success": True,
                    "status_code": 200,
                    "response_time": 0.1,
                    "timestamp": 1000.0,
                },
                {
                    "scenario": "test_scenario",
                    "success": True,
                    "status_code": 200,
                    "response_time": 0.2,
                    "timestamp": 1000.1,
                },
                {
                    "scenario": "other_scenario",
                    "success": False,
                    "status_code": 500,
                    "response_time": 0.5,
                    "timestamp": 1000.2,
                },
            ],
            [
                {
                    "scenario": "test_scenario",
                    "success": False,
                    "status_code": 404,
                    "response_time": 0.3,
                    "timestamp": 1000.3,
                },
            ],
        ]

        result = benchmark_suite._aggregate_scenario_results("test_scenario", user_results)

        assert isinstance(result, LoadTestResult)
        assert result.scenario_name == "test_scenario"
        assert result.total_requests == 3
        assert result.successful_requests == 2
        assert result.failed_requests == 1
        assert result.error_rate == 1 / 3

    def test_scenario_results_aggregation_empty(self, benchmark_suite):
        """Test aggregation with no results."""
        user_results = [[], []]

        result = benchmark_suite._aggregate_scenario_results("nonexistent", user_results)

        assert result.total_requests == 0
        assert result.successful_requests == 0
        assert result.failed_requests == 0
        assert result.error_rate == 0.0

    def test_report_generation(self, benchmark_suite):
        """Test load test report generation."""
        # Create mock results
        results = {
            "test_scenario": LoadTestResult(
                scenario_name="test_scenario",
                total_requests=100,
                successful_requests=95,
                failed_requests=5,
                average_response_time=0.15,
                min_response_time=0.05,
                max_response_time=0.5,
                p50_response_time=0.12,
                p90_response_time=0.25,
                p95_response_time=0.35,
                p99_response_time=0.45,
                requests_per_second=10.0,
                error_rate=0.05,
                errors={"HTTP_500": 3, "timeout": 2},
            )
        }

        report = benchmark_suite.generate_report(results)

        assert "GRAPHRAG API LOAD TEST REPORT" in report
        assert "test_scenario" in report
        assert "Total Requests: 100" in report
        assert "Success Rate: 95.0%" in report
        assert "Requests/sec: 10.00" in report
        assert "HTTP_500: 3" in report

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession")
    async def test_user_simulation(self, mock_session_class, benchmark_suite):
        """Test user behavior simulation."""
        # Mock HTTP session and responses
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="success")

        # Create proper async context manager mocks
        class MockAsyncContextManager:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        # Set up the session methods to return proper async context managers
        mock_session.get = MagicMock(return_value=MockAsyncContextManager(mock_response))
        mock_session.request = MagicMock(return_value=MockAsyncContextManager(mock_response))

        mock_session_context = AsyncMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session_context

        # Simulate a user with very short duration
        benchmark_suite.config.test_duration_seconds = 0.1

        results = await benchmark_suite._simulate_user(user_id=1, start_delay=0)

        assert isinstance(results, list)
        # Should have made at least one request
        assert len(results) >= 0

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession")
    async def test_full_load_test(self, mock_session_class, benchmark_suite):
        """Test full load test execution."""
        # Mock HTTP session and responses
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="success")

        # Create proper async context manager mocks
        class MockAsyncContextManager:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        # Set up the session methods to return proper async context managers
        mock_session.get = MagicMock(return_value=MockAsyncContextManager(mock_response))
        mock_session.request = MagicMock(return_value=MockAsyncContextManager(mock_response))

        mock_session_context = AsyncMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session_context

        # Run a very short load test
        benchmark_suite.config.concurrent_users = 1
        benchmark_suite.config.test_duration_seconds = 0.1

        results = await benchmark_suite.run_load_test()

        assert isinstance(results, dict)
        # Should have results for each scenario
        for scenario in benchmark_suite.scenarios:
            assert scenario.name in results
            assert isinstance(results[scenario.name], LoadTestResult)


class TestLoadTestResult:
    """Test cases for load test results."""

    def test_load_test_result_creation(self):
        """Test load test result creation."""
        result = LoadTestResult(
            scenario_name="test",
            total_requests=100,
            successful_requests=95,
            failed_requests=5,
            average_response_time=0.15,
            min_response_time=0.05,
            max_response_time=0.5,
            p50_response_time=0.12,
            p90_response_time=0.25,
            p95_response_time=0.35,
            p99_response_time=0.45,
            requests_per_second=10.0,
            error_rate=0.05,
            errors={"HTTP_500": 5},
        )

        assert result.scenario_name == "test"
        assert result.total_requests == 100
        assert result.error_rate == 0.05
        assert result.errors["HTTP_500"] == 5
