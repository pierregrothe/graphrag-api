# src/graphrag_api_service/performance/compression.py
# Response Compression and Pagination System
# Author: Pierre Grothé
# Creation Date: 2025-08-29

"""Response compression and pagination for improved API performance."""

import gzip
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PaginationConfig(BaseModel):
    """Configuration for pagination."""

    default_page_size: int = 50
    max_page_size: int = 1000
    enable_cursor_pagination: bool = True


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = 1
    page_size: int = 50
    cursor: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: str = "asc"


class PaginatedResponse(BaseModel):
    """Paginated response structure."""

    data: List[Any]
    pagination: Dict[str, Any]
    total_count: Optional[int] = None


class CompressionConfig(BaseModel):
    """Configuration for response compression."""

    enabled: bool = True
    min_size_bytes: int = 1024
    compression_level: int = 6
    supported_encodings: List[str] = ["gzip", "deflate"]


class ResponseCompressor:
    """Response compression handler."""

    def __init__(self, config: CompressionConfig):
        """Initialize the response compressor.

        Args:
            config: Compression configuration
        """
        self.config = config

    def should_compress(self, request: Request, content_length: int) -> bool:
        """Determine if response should be compressed.

        Args:
            request: HTTP request
            content_length: Response content length

        Returns:
            True if response should be compressed
        """
        if not self.config.enabled:
            return False

        if content_length < self.config.min_size_bytes:
            return False

        # Check if client accepts compression
        accept_encoding = request.headers.get("accept-encoding", "")
        return any(encoding in accept_encoding for encoding in self.config.supported_encodings)

    def compress_response(self, content: bytes, encoding: str = "gzip") -> Tuple[bytes, str]:
        """Compress response content.

        Args:
            content: Content to compress
            encoding: Compression encoding

        Returns:
            Tuple of (compressed_content, encoding)
        """
        if encoding == "gzip":
            compressed = gzip.compress(content, compresslevel=self.config.compression_level)
            return compressed, "gzip"
        elif encoding == "deflate":
            import zlib
            compressed = zlib.compress(content, level=self.config.compression_level)
            return compressed, "deflate"
        else:
            return content, "identity"

    def get_preferred_encoding(self, request: Request) -> str:
        """Get the preferred compression encoding from request.

        Args:
            request: HTTP request

        Returns:
            Preferred encoding
        """
        accept_encoding = request.headers.get("accept-encoding", "")

        for encoding in self.config.supported_encodings:
            if encoding in accept_encoding:
                return encoding

        return "identity"


class PaginationHandler:
    """Pagination handler for API responses."""

    def __init__(self, config: PaginationConfig):
        """Initialize the pagination handler.

        Args:
            config: Pagination configuration
        """
        self.config = config

    def parse_pagination_params(self, request: Request) -> PaginationParams:
        """Parse pagination parameters from request.

        Args:
            request: HTTP request

        Returns:
            Pagination parameters
        """
        query_params = request.query_params

        page = int(query_params.get("page", 1))
        page_size = min(
            int(query_params.get("page_size", self.config.default_page_size)),
            self.config.max_page_size
        )
        cursor = query_params.get("cursor")
        sort_by = query_params.get("sort_by")
        sort_order = query_params.get("sort_order", "asc")

        return PaginationParams(
            page=page,
            page_size=page_size,
            cursor=cursor,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def paginate_data(
        self,
        data: List[Any],
        params: PaginationParams,
        total_count: Optional[int] = None,
    ) -> PaginatedResponse:
        """Paginate data based on parameters.

        Args:
            data: Data to paginate
            params: Pagination parameters
            total_count: Total count of items

        Returns:
            Paginated response
        """
        if total_count is None:
            total_count = len(data)

        # Calculate pagination info
        total_pages = (total_count + params.page_size - 1) // params.page_size
        start_index = (params.page - 1) * params.page_size
        end_index = start_index + params.page_size

        # Extract page data
        page_data = data[start_index:end_index]

        # Build pagination metadata
        pagination = {
            "page": params.page,
            "page_size": params.page_size,
            "total_pages": total_pages,
            "total_count": total_count,
            "has_next": params.page < total_pages,
            "has_previous": params.page > 1,
        }

        if params.page < total_pages:
            pagination["next_page"] = params.page + 1

        if params.page > 1:
            pagination["previous_page"] = params.page - 1

        # Add cursor pagination if enabled
        if self.config.enable_cursor_pagination and page_data:
            pagination["next_cursor"] = self._generate_cursor(page_data[-1])
            if start_index > 0:
                pagination["previous_cursor"] = self._generate_cursor(data[start_index - 1])

        return PaginatedResponse(
            data=page_data,
            pagination=pagination,
            total_count=total_count,
        )

    def _generate_cursor(self, item: Any) -> str:
        """Generate a cursor for an item.

        Args:
            item: Item to generate cursor for

        Returns:
            Base64 encoded cursor
        """
        import base64

        if isinstance(item, dict):
            cursor_data = str(item.get("id", hash(str(item))))
        else:
            cursor_data = str(hash(str(item)))

        return base64.b64encode(cursor_data.encode()).decode()


class PerformanceMiddleware:
    """Middleware for response compression and pagination."""

    def __init__(
        self,
        compression_config: Optional[CompressionConfig] = None,
        pagination_config: Optional[PaginationConfig] = None,
    ):
        """Initialize the performance middleware.

        Args:
            compression_config: Compression configuration
            pagination_config: Pagination configuration
        """
        self.compressor = ResponseCompressor(compression_config or CompressionConfig())
        self.paginator = PaginationHandler(pagination_config or PaginationConfig())

    async def process_response(
        self,
        request: Request,
        response_data: Any,
        auto_paginate: bool = True,
    ) -> Response:
        """Process response with compression and pagination.

        Args:
            request: HTTP request
            response_data: Response data
            auto_paginate: Whether to auto-paginate large responses

        Returns:
            Processed response
        """
        # Handle pagination for list responses
        if auto_paginate and isinstance(response_data, list):
            pagination_params = self.paginator.parse_pagination_params(request)
            paginated_response = self.paginator.paginate_data(response_data, pagination_params)
            response_data = paginated_response.dict()

        # Serialize response
        if isinstance(response_data, dict):
            content = json.dumps(response_data, default=str).encode()
        else:
            content = json.dumps(response_data, default=str).encode()

        # Check if compression should be applied
        if self.compressor.should_compress(request, len(content)):
            encoding = self.compressor.get_preferred_encoding(request)
            compressed_content, actual_encoding = self.compressor.compress_response(content, encoding)

            # Calculate compression ratio
            compression_ratio = len(compressed_content) / len(content)
            logger.debug(
                f"Response compressed: {len(content)} -> {len(compressed_content)} bytes "
                f"(ratio: {compression_ratio:.2f})"
            )

            response = Response(
                content=compressed_content,
                media_type="application/json",
                headers={
                    "Content-Encoding": actual_encoding,
                    "Content-Length": str(len(compressed_content)),
                    "X-Compression-Ratio": f"{compression_ratio:.2f}",
                }
            )
        else:
            response = JSONResponse(content=response_data)

        return response

    def create_paginated_response(
        self,
        data: List[Any],
        request: Request,
        total_count: Optional[int] = None,
    ) -> PaginatedResponse:
        """Create a paginated response.

        Args:
            data: Data to paginate
            request: HTTP request
            total_count: Total count of items

        Returns:
            Paginated response
        """
        pagination_params = self.paginator.parse_pagination_params(request)
        return self.paginator.paginate_data(data, pagination_params, total_count)


# Global performance middleware instance
_performance_middleware: Optional[PerformanceMiddleware] = None


def get_performance_middleware() -> PerformanceMiddleware:
    """Get the global performance middleware instance.

    Returns:
        Performance middleware instance
    """
    global _performance_middleware

    if _performance_middleware is None:
        _performance_middleware = PerformanceMiddleware()

    return _performance_middleware


def compress_json_response(data: Any, request: Request) -> Response:
    """Compress JSON response if appropriate.

    Args:
        data: Response data
        request: HTTP request

    Returns:
        Compressed or regular response
    """
    middleware = get_performance_middleware()
    return asyncio.run(middleware.process_response(request, data, auto_paginate=False))


def paginate_response(data: List[Any], request: Request, total_count: Optional[int] = None) -> Dict[str, Any]:
    """Paginate response data.

    Args:
        data: Data to paginate
        request: HTTP request
        total_count: Total count of items

    Returns:
        Paginated response data
    """
    middleware = get_performance_middleware()
    paginated = middleware.create_paginated_response(data, request, total_count)
    return paginated.dict()
