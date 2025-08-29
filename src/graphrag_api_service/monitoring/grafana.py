# src/graphrag_api_service/monitoring/grafana.py
# Grafana Dashboard Configuration for GraphRAG API
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Grafana dashboard configurations and automated dashboard generation."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class GrafanaDashboard:
    """Grafana dashboard configuration generator."""

    def __init__(self, title: str, description: str = ""):
        """Initialize dashboard.

        Args:
            title: Dashboard title
            description: Dashboard description
        """
        self.title = title
        self.description = description
        self.panels: list[dict[str, Any]] = []
        self.panel_id = 1

    def add_panel(self, panel_config: dict[str, Any]) -> None:
        """Add a panel to the dashboard.

        Args:
            panel_config: Panel configuration
        """
        panel_config["id"] = self.panel_id
        self.panels.append(panel_config)
        self.panel_id += 1

    def generate_config(self) -> dict[str, Any]:
        """Generate complete dashboard configuration.

        Returns:
            Dashboard configuration dictionary
        """
        return {
            "dashboard": {
                "id": None,
                "title": self.title,
                "description": self.description,
                "tags": ["graphrag", "api", "monitoring"],
                "timezone": "browser",
                "panels": self.panels,
                "time": {"from": "now-1h", "to": "now"},
                "timepicker": {},
                "templating": {"list": []},
                "annotations": {"list": []},
                "refresh": "30s",
                "schemaVersion": 30,
                "version": 1,
                "links": [],
            },
            "overwrite": True,
        }


class GraphRAGDashboards:
    """Pre-configured Grafana dashboards for GraphRAG API."""

    @staticmethod
    def create_overview_dashboard() -> GrafanaDashboard:
        """Create the main overview dashboard.

        Returns:
            Configured overview dashboard
        """
        dashboard = GrafanaDashboard(
            "GraphRAG API - Overview", "High-level overview of GraphRAG API performance and health"
        )

        # Request rate panel
        dashboard.add_panel(
            {
                "title": "Request Rate",
                "type": "stat",
                "targets": [
                    {"expr": "rate(graphrag_requests_total[5m])", "legendFormat": "Requests/sec"}
                ],
                "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0},
                "fieldConfig": {
                    "defaults": {"color": {"mode": "palette-classic"}, "unit": "reqps"}
                },
            }
        )

        # Response time panel
        dashboard.add_panel(
            {
                "title": "Response Time (P95)",
                "type": "stat",
                "targets": [
                    {
                        "expr": "histogram_quantile(0.95, rate(graphrag_request_duration_seconds_bucket[5m]))",
                        "legendFormat": "P95 Response Time",
                    }
                ],
                "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0},
                "fieldConfig": {"defaults": {"color": {"mode": "palette-classic"}, "unit": "s"}},
            }
        )

        # Error rate panel
        dashboard.add_panel(
            {
                "title": "Error Rate",
                "type": "stat",
                "targets": [
                    {
                        "expr": 'rate(graphrag_requests_total{status=~"4..|5.."}[5m]) / rate(graphrag_requests_total[5m]) * 100',
                        "legendFormat": "Error Rate %",
                    }
                ],
                "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0},
                "fieldConfig": {
                    "defaults": {"color": {"mode": "palette-classic"}, "unit": "percent"}
                },
            }
        )

        # Active connections panel
        dashboard.add_panel(
            {
                "title": "Active Connections",
                "type": "stat",
                "targets": [
                    {
                        "expr": "graphrag_db_connections_active",
                        "legendFormat": "Active DB Connections",
                    }
                ],
                "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0},
                "fieldConfig": {
                    "defaults": {"color": {"mode": "palette-classic"}, "unit": "short"}
                },
            }
        )

        # Request volume over time
        dashboard.add_panel(
            {
                "title": "Request Volume Over Time",
                "type": "graph",
                "targets": [
                    {
                        "expr": "rate(graphrag_requests_total[5m])",
                        "legendFormat": "{{method}} {{endpoint}}",
                    }
                ],
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                "yAxes": [{"label": "Requests/sec", "min": 0}],
            }
        )

        # Response time distribution
        dashboard.add_panel(
            {
                "title": "Response Time Distribution",
                "type": "graph",
                "targets": [
                    {
                        "expr": "histogram_quantile(0.50, rate(graphrag_request_duration_seconds_bucket[5m]))",
                        "legendFormat": "P50",
                    },
                    {
                        "expr": "histogram_quantile(0.95, rate(graphrag_request_duration_seconds_bucket[5m]))",
                        "legendFormat": "P95",
                    },
                    {
                        "expr": "histogram_quantile(0.99, rate(graphrag_request_duration_seconds_bucket[5m]))",
                        "legendFormat": "P99",
                    },
                ],
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                "yAxes": [{"label": "Seconds", "min": 0}],
            }
        )

        return dashboard

    @staticmethod
    def create_graphql_dashboard() -> GrafanaDashboard:
        """Create GraphQL-specific dashboard.

        Returns:
            Configured GraphQL dashboard
        """
        dashboard = GrafanaDashboard(
            "GraphRAG API - GraphQL", "GraphQL query performance and optimization metrics"
        )

        # GraphQL query rate
        dashboard.add_panel(
            {
                "title": "GraphQL Query Rate",
                "type": "graph",
                "targets": [
                    {
                        "expr": "rate(graphrag_graphql_queries_total[5m])",
                        "legendFormat": "{{operation_type}} - {{operation_name}}",
                    }
                ],
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
            }
        )

        # Query complexity distribution
        dashboard.add_panel(
            {
                "title": "Query Complexity Distribution",
                "type": "graph",
                "targets": [
                    {
                        "expr": "histogram_quantile(0.95, rate(graphrag_graphql_query_complexity_bucket[5m]))",
                        "legendFormat": "P95 Complexity",
                    }
                ],
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
            }
        )

        # GraphQL response times
        dashboard.add_panel(
            {
                "title": "GraphQL Response Times",
                "type": "graph",
                "targets": [
                    {
                        "expr": "histogram_quantile(0.95, rate(graphrag_graphql_query_duration_seconds_bucket[5m]))",
                        "legendFormat": "{{operation_type}} P95",
                    }
                ],
                "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8},
            }
        )

        return dashboard

    @staticmethod
    def create_cache_dashboard() -> GrafanaDashboard:
        """Create cache performance dashboard.

        Returns:
            Configured cache dashboard
        """
        dashboard = GrafanaDashboard(
            "GraphRAG API - Cache Performance", "Cache hit rates, sizes, and performance metrics"
        )

        # Cache hit rate
        dashboard.add_panel(
            {
                "title": "Cache Hit Rate",
                "type": "stat",
                "targets": [
                    {
                        "expr": "rate(graphrag_cache_hits_total[5m]) / (rate(graphrag_cache_hits_total[5m]) + rate(graphrag_cache_misses_total[5m])) * 100",
                        "legendFormat": "Hit Rate %",
                    }
                ],
                "gridPos": {"h": 8, "w": 8, "x": 0, "y": 0},
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "palette-classic"},
                        "unit": "percent",
                        "min": 0,
                        "max": 100,
                    }
                },
            }
        )

        # Cache size
        dashboard.add_panel(
            {
                "title": "Cache Size",
                "type": "graph",
                "targets": [
                    {"expr": "graphrag_cache_size_bytes", "legendFormat": "{{cache_type}}"}
                ],
                "gridPos": {"h": 8, "w": 8, "x": 8, "y": 0},
                "yAxes": [{"label": "Bytes", "min": 0}],
            }
        )

        # Cache entries
        dashboard.add_panel(
            {
                "title": "Cache Entries",
                "type": "graph",
                "targets": [
                    {"expr": "graphrag_cache_entries_total", "legendFormat": "{{cache_type}}"}
                ],
                "gridPos": {"h": 8, "w": 8, "x": 16, "y": 0},
            }
        )

        return dashboard

    @staticmethod
    def create_system_dashboard() -> GrafanaDashboard:
        """Create system metrics dashboard.

        Returns:
            Configured system dashboard
        """
        dashboard = GrafanaDashboard(
            "GraphRAG API - System Metrics", "System resource usage and performance"
        )

        # CPU usage
        dashboard.add_panel(
            {
                "title": "CPU Usage",
                "type": "graph",
                "targets": [{"expr": "graphrag_cpu_usage_percent", "legendFormat": "CPU Usage %"}],
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                "yAxes": [{"label": "Percent", "min": 0, "max": 100}],
            }
        )

        # Memory usage
        dashboard.add_panel(
            {
                "title": "Memory Usage",
                "type": "graph",
                "targets": [{"expr": "graphrag_memory_usage_bytes", "legendFormat": "{{type}}"}],
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                "yAxes": [{"label": "Bytes", "min": 0}],
            }
        )

        # Database connections
        dashboard.add_panel(
            {
                "title": "Database Connections",
                "type": "graph",
                "targets": [
                    {"expr": "graphrag_db_connections_active", "legendFormat": "Active"},
                    {"expr": "graphrag_db_connections_idle", "legendFormat": "Idle"},
                ],
                "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8},
            }
        )

        return dashboard


class GrafanaManager:
    """Manages Grafana dashboard deployment and updates."""

    def __init__(self, grafana_url: str, api_key: str):
        """Initialize Grafana manager.

        Args:
            grafana_url: Grafana instance URL
            api_key: Grafana API key
        """
        self.grafana_url = grafana_url.rstrip("/")
        self.api_key = api_key

    async def deploy_dashboard(self, dashboard: GrafanaDashboard) -> bool:
        """Deploy a dashboard to Grafana.

        Args:
            dashboard: Dashboard to deploy

        Returns:
            True if successful
        """
        try:
            import httpx

            config = dashboard.generate_config()

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.grafana_url}/api/dashboards/db", json=config, headers=headers
                )

                if response.status_code == 200:
                    logger.info(f"Successfully deployed dashboard: {dashboard.title}")
                    return True
                else:
                    logger.error(f"Failed to deploy dashboard: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Error deploying dashboard: {e}")
            return False

    async def deploy_all_dashboards(self) -> dict[str, bool]:
        """Deploy all GraphRAG dashboards.

        Returns:
            Dictionary of dashboard names and deployment status
        """
        dashboards = {
            "overview": GraphRAGDashboards.create_overview_dashboard(),
            "graphql": GraphRAGDashboards.create_graphql_dashboard(),
            "cache": GraphRAGDashboards.create_cache_dashboard(),
            "system": GraphRAGDashboards.create_system_dashboard(),
        }

        results = {}
        for name, dashboard in dashboards.items():
            results[name] = await self.deploy_dashboard(dashboard)

        return results
