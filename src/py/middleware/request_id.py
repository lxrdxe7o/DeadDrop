"""
Request ID middleware for distributed tracing.

Adds a unique request ID to each request and makes it available
throughout the request lifecycle for logging and debugging.
"""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add unique request IDs to all requests.

    Features:
    - Generates UUIDs for request tracking
    - Adds X-Request-ID header to responses
    - Makes request ID available in request.state
    - Supports client-provided request IDs
    """

    def __init__(self, app, header_name: str = "X-Request-ID"):
        """
        Initialize middleware.

        Args:
            app: FastAPI application
            header_name: Header name for request ID
        """
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Process request and add request ID.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response with X-Request-ID header
        """
        # Use client-provided request ID if available, otherwise generate new one
        request_id = request.headers.get(self.header_name)
        if not request_id:
            request_id = str(uuid.uuid4())

        # Make request ID available throughout request lifecycle
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response headers for client-side tracking
        response.headers[self.header_name] = request_id

        return response
