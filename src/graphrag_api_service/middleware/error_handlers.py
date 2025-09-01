# src/graphrag_api_service/middleware/error_handlers.py
# Error handling middleware
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Error handling middleware for GraphRAG API Service."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..logging_config import get_logger

logger = get_logger(__name__)


def setup_error_handlers(app: FastAPI) -> None:
    """Setup error handlers for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    logger.info("Setting up error handlers")

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Handle HTTP exceptions.

        Args:
            request: FastAPI request object
            exc: HTTP exception

        Returns:
            JSON response with error details
        """
        logger.error(f"HTTP error {exc.status_code}: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "status_code": exc.status_code},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle request validation errors.

        Args:
            request: FastAPI request object
            exc: Validation error

        Returns:
            JSON response with validation error details
        """
        logger.error(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={"error": "Validation error", "details": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle general exceptions.

        Args:
            request: FastAPI request object
            exc: General exception

        Returns:
            JSON response with error details
        """
        logger.exception(f"Unhandled exception: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred. Please try again later.",
            },
        )
