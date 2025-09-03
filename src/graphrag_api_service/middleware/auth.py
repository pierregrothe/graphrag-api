# src/graphrag_api_service/middleware/auth.py
# Authentication middleware
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Authentication middleware for GraphRAG API Service."""

import time
from collections.abc import Callable

from fastapi import FastAPI, Request, Response

from ..logging_config import get_logger

logger = get_logger(__name__)


def setup_auth_middleware(app: FastAPI, security_middleware, performance_middleware) -> None:
    """Set up authentication and performance middleware for the FastAPI application.

    Args:
        app: FastAPI application instance
        security_middleware: Security middleware instance
        performance_middleware: Performance middleware instance
    """
    logger.info("Setting up authentication and performance middleware")

    @app.middleware("http")
    async def performance_security_middleware(request: Request, call_next: Callable) -> Response:
        """Combine performance monitoring and security middleware.

        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in the chain

        Returns:
            Response object with added headers and monitoring
        """
        start_time = time.time()

        try:
            # Apply security checks if middleware is available
            if security_middleware:
                security_result = await security_middleware.process_request(request)
                if security_result.get("blocked"):
                    from fastapi.responses import JSONResponse

                    return JSONResponse(
                        status_code=security_result.get("status_code", 403),
                        content={"error": security_result.get("message", "Access denied")},
                    )

            # Process the request
            response = await call_next(request)

            # Add performance metrics
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)

            # Apply performance monitoring if available
            if performance_middleware:
                await performance_middleware.record_request(
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    process_time=process_time,
                )

            # Apply security headers if available
            if security_middleware:
                security_headers = security_middleware.get_security_headers()
                for header_name, header_value in security_headers.items():
                    response.headers[header_name] = header_value

            return response  # type: ignore[no-any-return]

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(f"Middleware error after {process_time:.3f}s: {e}")

            # Record failed request if middleware is available
            if performance_middleware:
                await performance_middleware.record_request(
                    method=request.method,
                    path=request.url.path,
                    status_code=500,
                    process_time=process_time,
                    error=str(e),
                )

            raise e
