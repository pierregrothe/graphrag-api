# src/graphrag_api_service/monitoring/tracing.py
# OpenTelemetry Distributed Tracing for GraphRAG API
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""OpenTelemetry distributed tracing integration for request flow analysis."""

import logging
import os
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Import instrumentation packages conditionally
try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
except ImportError:
    FastAPIInstrumentor = None

try:
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
except ImportError:
    HTTPXClientInstrumentor = None

try:
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
except ImportError:
    LoggingInstrumentor = None

try:
    from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
except ImportError:
    Psycopg2Instrumentor = None

try:
    from opentelemetry.instrumentation.redis import RedisInstrumentor
except ImportError:
    RedisInstrumentor = None

try:
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
except ImportError:
    RequestsInstrumentor = None

try:
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
except ImportError:
    SQLAlchemyInstrumentor = None
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv.resource import ResourceAttributes

logger = logging.getLogger(__name__)


class TracingConfig:
    """Configuration for distributed tracing."""

    def __init__(
        self,
        service_name: str = "graphrag-api",
        service_version: str = "1.0.0",
        environment: str = "production",
        jaeger_endpoint: str | None = None,
        otlp_endpoint: str | None = None,
        sample_rate: float = 1.0,
        enable_console_export: bool = False,
    ):
        """Initialize tracing configuration.

        Args:
            service_name: Name of the service
            service_version: Version of the service
            environment: Environment (dev, staging, prod)
            jaeger_endpoint: Jaeger collector endpoint
            otlp_endpoint: OTLP collector endpoint
            sample_rate: Sampling rate (0.0 to 1.0)
            enable_console_export: Enable console span export for debugging
        """
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment
        self.jaeger_endpoint = jaeger_endpoint or os.getenv("JAEGER_ENDPOINT")
        self.otlp_endpoint = otlp_endpoint or os.getenv("OTLP_ENDPOINT")
        self.sample_rate = sample_rate
        self.enable_console_export = enable_console_export


class TracingManager:
    """Manages OpenTelemetry tracing setup and instrumentation."""

    def __init__(self, config: TracingConfig):
        """Initialize the tracing manager.

        Args:
            config: Tracing configuration
        """
        self.config = config
        self.tracer_provider: TracerProvider | None = None
        self.tracer: trace.Tracer | None = None

    def setup_tracing(self) -> None:
        """Set up OpenTelemetry tracing."""
        try:
            # Create resource
            resource = Resource.create(
                {
                    ResourceAttributes.SERVICE_NAME: self.config.service_name,
                    ResourceAttributes.SERVICE_VERSION: self.config.service_version,
                    ResourceAttributes.DEPLOYMENT_ENVIRONMENT: self.config.environment,
                }
            )

            # Create tracer provider
            self.tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(self.tracer_provider)

            # Set up exporters
            self._setup_exporters()

            # Set up propagators
            set_global_textmap(B3MultiFormat())

            # Get tracer
            self.tracer = trace.get_tracer(__name__)

            # Instrument libraries
            self._setup_instrumentation()

            logger.info(f"Tracing initialized for service: {self.config.service_name}")

        except Exception as e:
            logger.error(f"Failed to initialize tracing: {e}")

    def _setup_exporters(self) -> None:
        """Set up trace exporters."""
        if not self.tracer_provider:
            return

        # Jaeger exporter
        if self.config.jaeger_endpoint:
            try:
                jaeger_exporter = JaegerExporter(
                    agent_host_name=self.config.jaeger_endpoint.split("://")[1].split(":")[0],
                    agent_port=int(self.config.jaeger_endpoint.split(":")[-1]),
                )
                self.tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
                logger.info(f"Jaeger exporter configured: {self.config.jaeger_endpoint}")
            except Exception as e:
                logger.error(f"Failed to configure Jaeger exporter: {e}")

        # OTLP exporter
        if self.config.otlp_endpoint:
            try:
                otlp_exporter = OTLPSpanExporter(endpoint=self.config.otlp_endpoint)
                self.tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
                logger.info(f"OTLP exporter configured: {self.config.otlp_endpoint}")
            except Exception as e:
                logger.error(f"Failed to configure OTLP exporter: {e}")

        # Console exporter for debugging
        if self.config.enable_console_export:
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter

            console_exporter = ConsoleSpanExporter()
            self.tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
            logger.info("Console exporter configured")

    def _setup_instrumentation(self) -> None:
        """Set up automatic instrumentation for common libraries."""
        try:
            # FastAPI instrumentation
            if FastAPIInstrumentor:
                FastAPIInstrumentor.instrument()
                logger.debug("FastAPI instrumentation enabled")

            # HTTP client instrumentation
            if HTTPXClientInstrumentor:
                HTTPXClientInstrumentor().instrument()
                logger.debug("HTTPX instrumentation enabled")

            if RequestsInstrumentor:
                RequestsInstrumentor().instrument()
                logger.debug("Requests instrumentation enabled")

            # Database instrumentation
            if Psycopg2Instrumentor:
                try:
                    Psycopg2Instrumentor().instrument()
                    logger.debug("Psycopg2 instrumentation enabled")
                except Exception as e:
                    logger.warning(f"Psycopg2 instrumentation failed: {e}")

            if SQLAlchemyInstrumentor:
                try:
                    SQLAlchemyInstrumentor().instrument()
                    logger.debug("SQLAlchemy instrumentation enabled")
                except Exception as e:
                    logger.warning(f"SQLAlchemy instrumentation failed: {e}")

            # Redis instrumentation
            if RedisInstrumentor:
                try:
                    RedisInstrumentor().instrument()
                    logger.debug("Redis instrumentation enabled")
                except Exception as e:
                    logger.warning(f"Redis instrumentation failed: {e}")

            # Logging instrumentation
            if LoggingInstrumentor:
                LoggingInstrumentor().instrument()
                logger.debug("Logging instrumentation enabled")

        except Exception as e:
            logger.error(f"Failed to set up instrumentation: {e}")

    def create_span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
        kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    ) -> trace.Span:
        """Create a new span.

        Args:
            name: Span name
            attributes: Span attributes
            kind: Span kind

        Returns:
            Created span
        """
        if not self.tracer:
            # Return a no-op span if tracing is not initialized
            return trace.NonRecordingSpan(trace.SpanContext(0, 0, False))

        span = self.tracer.start_span(name, kind=kind)

        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)

        return span

    def add_span_attributes(self, span: trace.Span, attributes: dict[str, Any]) -> None:
        """Add attributes to an existing span.

        Args:
            span: Target span
            attributes: Attributes to add
        """
        for key, value in attributes.items():
            span.set_attribute(key, value)

    def record_exception(self, span: trace.Span, exception: Exception) -> None:
        """Record an exception in a span.

        Args:
            span: Target span
            exception: Exception to record
        """
        span.record_exception(exception)
        span.set_status(trace.Status(trace.StatusCode.ERROR, str(exception)))

    def shutdown(self) -> None:
        """Shutdown tracing and flush remaining spans."""
        if self.tracer_provider:
            self.tracer_provider.shutdown()
            logger.info("Tracing shutdown completed")


class GraphQLTracingExtension:
    """GraphQL-specific tracing extension."""

    def __init__(self, tracing_manager: TracingManager):
        """Initialize GraphQL tracing extension.

        Args:
            tracing_manager: Tracing manager instance
        """
        self.tracing_manager = tracing_manager

    def trace_graphql_operation(
        self,
        operation_type: str,
        operation_name: str,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> trace.Span:
        """Create a span for GraphQL operation.

        Args:
            operation_type: Type of operation (query, mutation, subscription)
            operation_name: Name of the operation
            query: GraphQL query string
            variables: Query variables

        Returns:
            Created span
        """
        span_name = f"graphql.{operation_type}"
        if operation_name:
            span_name += f".{operation_name}"

        attributes = {
            "graphql.operation.type": operation_type,
            "graphql.operation.name": operation_name or "anonymous",
            "graphql.document": query[:1000],  # Truncate long queries
        }

        if variables:
            # Only include non-sensitive variables
            safe_variables = {
                k: v
                for k, v in variables.items()
                if not any(
                    sensitive in k.lower() for sensitive in ["password", "token", "secret", "key"]
                )
            }
            attributes["graphql.variables"] = str(safe_variables)[:500]

        return self.tracing_manager.create_span(
            span_name, attributes=attributes, kind=trace.SpanKind.SERVER
        )

    def trace_resolver(self, field_name: str, parent_type: str) -> trace.Span:
        """Create a span for GraphQL resolver.

        Args:
            field_name: Name of the field being resolved
            parent_type: Parent type name

        Returns:
            Created span
        """
        span_name = f"graphql.resolve.{parent_type}.{field_name}"

        attributes = {
            "graphql.field.name": field_name,
            "graphql.field.parent_type": parent_type,
        }

        return self.tracing_manager.create_span(
            span_name, attributes=attributes, kind=trace.SpanKind.INTERNAL
        )


# Global tracing manager
_tracing_manager: TracingManager | None = None


def get_tracing_manager() -> TracingManager | None:
    """Get the global tracing manager.

    Returns:
        TracingManager instance or None if not initialized
    """
    return _tracing_manager


def initialize_tracing(config: TracingConfig | None = None) -> TracingManager:
    """Initialize distributed tracing.

    Args:
        config: Optional tracing configuration

    Returns:
        TracingManager instance
    """
    global _tracing_manager

    if config is None:
        config = TracingConfig()

    _tracing_manager = TracingManager(config)
    _tracing_manager.setup_tracing()

    return _tracing_manager


def shutdown_tracing() -> None:
    """Shutdown distributed tracing."""
    global _tracing_manager

    if _tracing_manager:
        _tracing_manager.shutdown()
        _tracing_manager = None
