# src/graphrag_api_service/middleware/auth.py
# Authentication middleware
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Authentication middleware for GraphRAG API Service."""

import time
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response

from ..logging_config import get_logger

logger = get_logger(__name__)


def setup_auth_middleware(
    app: FastAPI, security_middleware: Any, performance_middleware: Any
) -> None:
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
                try:
                    await security_middleware.process_request(request)
                except HTTPException as security_error:
                    # Security middleware raises HTTPException for blocked requests
                    from fastapi.responses import JSONResponse

                    return JSONResponse(
                        status_code=security_error.status_code,
                        content={"error": security_error.detail},
                        headers=getattr(security_error, "headers", None),
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
                security_middleware.add_security_headers(response)

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
