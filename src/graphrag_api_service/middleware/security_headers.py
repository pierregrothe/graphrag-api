# src/graphrag_api_service/middleware/security_headers.py
# Security headers middleware implementation
# Author: Pierre Grothé
# Creation Date: 2025-09-02

"""Security headers middleware for enhanced protection."""

from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..security.security_config import get_security_config


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to responses."""

    def __init__(self, app: ASGIApp):
        """Initialize security headers middleware."""
        super().__init__(app)
        self.security_config = get_security_config()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        if self.security_config.enable_security:
            # Add security headers
            headers = self.security_config.get_security_headers()
            for header, value in headers.items():
                response.headers[header] = value

            # Add additional security headers based on request
            if request.url.scheme == "https":
                response.headers["Strict-Transport-Security"] = (
                    self.security_config.headers.strict_transport_security
                )

        return response  # type: ignore[no-any-return]


def setup_security_headers(app: ASGIApp) -> ASGIApp:
    """Set up security headers for the application."""
    config = get_security_config()

    if config.enable_security:
        # Note: This function is for documentation purposes
        # Actual middleware should be added to FastAPI app instance
        pass

    return app
