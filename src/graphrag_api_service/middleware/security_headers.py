# src/graphrag_api_service/middleware/security_headers.py
# Security headers middleware implementation
# Author: Pierre Grothé
# Creation Date: 2025-09-02
# Updated: 2025-09-05 - Enhanced with comprehensive security headers

"""Security headers middleware for enhanced protection."""

import logging
from collections.abc import Callable
from typing import cast

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..security.security_config import get_security_config

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add comprehensive security headers to responses."""

    def __init__(self, app: ASGIApp):
        """Initialize security headers middleware."""
        super().__init__(app)
        self.security_config = get_security_config()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        try:
            if self.security_config.enable_security:
                # Add basic security headers from config
                headers = self.security_config.get_security_headers()
                for header, value in headers.items():
                    response.headers[header] = value

                # Add comprehensive security headers
                self._add_comprehensive_security_headers(response, request)

        except Exception as e:
            logger.error(f"Security headers middleware error: {e}")
            # Don't block response on header addition errors
            try:
                self._add_basic_security_headers(response)
            except Exception as inner_e:
                logger.warning(f"Failed to add basic security headers: {inner_e}")

        return cast(Response, response)

    def _add_comprehensive_security_headers(self, response: Response, request: Request) -> None:
        """Add comprehensive security headers to the response."""

        # HTTP Strict Transport Security (HSTS) for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                self.security_config.headers.strict_transport_security
            )

        # Content Security Policy
        if not response.headers.get("Content-Security-Policy"):
            response.headers["Content-Security-Policy"] = self._get_default_csp()

        # X-Frame-Options (prevent clickjacking)
        if not response.headers.get("X-Frame-Options"):
            response.headers["X-Frame-Options"] = "DENY"

        # X-Content-Type-Options (prevent MIME sniffing)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-XSS-Protection (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy
        if not response.headers.get("Referrer-Policy"):
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy
        if not response.headers.get("Permissions-Policy"):
            response.headers["Permissions-Policy"] = self._get_default_permissions_policy()

        # Cross-Origin policies
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        # Remove potentially sensitive headers
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]
        if "Server" in response.headers:
            del response.headers["Server"]

        # Cache control for sensitive endpoints
        if request.url.path.startswith("/auth/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

    def _add_basic_security_headers(self, response: Response) -> None:
        """Add basic security headers (fallback for error cases)."""
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"

    def _get_default_csp(self) -> str:
        """Get default Content Security Policy."""
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "media-src 'self'; "
            "object-src 'none'; "
            "child-src 'none'; "
            "worker-src 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self'; "
            "manifest-src 'self'"
        )

    def _get_default_permissions_policy(self) -> str:
        """Get default Permissions Policy."""
        return (
            "accelerometer=(), "
            "ambient-light-sensor=(), "
            "autoplay=(), "
            "battery=(), "
            "camera=(), "
            "cross-origin-isolated=(), "
            "display-capture=(), "
            "document-domain=(), "
            "encrypted-media=(), "
            "execution-while-not-rendered=(), "
            "execution-while-out-of-viewport=(), "
            "fullscreen=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "keyboard-map=(), "
            "magnetometer=(), "
            "microphone=(), "
            "midi=(), "
            "navigation-override=(), "
            "payment=(), "
            "picture-in-picture=(), "
            "publickey-credentials-get=(), "
            "screen-wake-lock=(), "
            "sync-xhr=(), "
            "usb=(), "
            "web-share=(), "
            "xr-spatial-tracking=()"
        )


def setup_security_headers(app: ASGIApp) -> ASGIApp:
    """Set up security headers for the application."""
    config = get_security_config()

    if config.enable_security:
        # Note: This function is for documentation purposes
        # Actual middleware should be added to FastAPI app instance
        pass

    return app
