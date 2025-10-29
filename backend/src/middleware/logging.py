"""Structured logging middleware for FastAPI."""
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from src.utils.logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured logging of all HTTP requests."""

    async def dispatch(self, request: Request, call_next):
        """
        Log HTTP request and response with structured data.

        Args:
            request: FastAPI request object
            call_next: Next middleware in chain

        Returns:
            Response object
        """
        # Record start time
        start_time = time.time()

        # Extract request information
        method = request.method
        url = str(request.url)
        client_host = request.client.host if request.client else None

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Log request/response
        logger.info(
            "http_request",
            method=method,
            url=url,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_host=client_host,
        )

        # Add custom header with processing time
        response.headers["X-Process-Time-Ms"] = str(duration_ms)

        return response
