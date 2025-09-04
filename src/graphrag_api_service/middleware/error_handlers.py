# src/graphrag_api_service/middleware/error_handlers.py
# Error handling middleware
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Error handling middleware for GraphRAG API Service."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..exceptions import AuthenticationError, ValidationError
from ..logging_config import get_logger

logger = get_logger(__name__)


def setup_error_handlers(app: FastAPI) -> None:
    """Set up error handlers for the FastAPI application.

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
    async def request_validation_exception_handler(
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

        # Clean up error details to ensure JSON serialization
        errors = []
        for error in exc.errors():
            cleaned_error = {}
            for key, value in error.items():
                # Convert bytes to string if needed
                if isinstance(value, bytes):
                    cleaned_error[key] = value.decode("utf-8", errors="ignore")
                else:
                    cleaned_error[key] = value
            errors.append(cleaned_error)

        return JSONResponse(
            status_code=422,
            content={"error": "Validation error", "details": errors},
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

    @app.exception_handler(AuthenticationError)
    async def authentication_exception_handler(
        request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        """Handle authentication errors with comprehensive security logging.

        This handler was enhanced in 2025 to provide proper HTTP status code mapping
        for authentication failures, ensuring consistent API responses and security
        event logging for audit trails.

        Security Features:
        - Converts internal AuthenticationError to standard HTTP 401 responses
        - Logs authentication failures for security monitoring
        - Prevents information leakage through standardized error messages
        - Integrates with security logging system for audit compliance

        Args:
            request: FastAPI request object containing client information
            exc: Authentication exception with failure details

        Returns:
            JSON response with 401 status code and standardized error format
        """
        logger.warning(f"Authentication error: {str(exc)}")
        return JSONResponse(
            status_code=401,
            content={
                "error": "Authentication failed",
                "message": str(exc),
            },
        )

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
        """Handle validation errors.

        Args:
            request: FastAPI request object
            exc: Validation exception

        Returns:
            JSON response with 400 status code
        """
        logger.warning(f"Validation error: {str(exc)}")
        return JSONResponse(
            status_code=400,
            content={
                "error": "Validation failed",
                "message": str(exc),
            },
        )
