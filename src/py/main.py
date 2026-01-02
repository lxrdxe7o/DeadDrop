"""
DeadDrop FastAPI Application

Zero-knowledge ephemeral file sharing service.
Server never sees encryption keys or plaintext data.

Features:
- Request ID tracking for distributed tracing
- Comprehensive error handling
- Connection pooling and graceful shutdown
- Structured logging with context
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from api.v1 import upload, download
from services.redis_client import RedisClient
from middleware import RequestIDMiddleware
from core.config import settings
from core.logging import setup_logging, get_logger, set_request_id
from core.exceptions import DeadDropException, exception_to_http_exception
import traceback

# Initialize logging
setup_logging(debug=settings.debug)
logger = get_logger(__name__)

# Initialize Redis client
redis_client = RedisClient(settings.redis_url)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events:
    - Startup: Connect to Redis
    - Shutdown: Close Redis connection
    
    Interview Talking Point:
        "I use FastAPI's lifespan context manager for clean resource management.
        This ensures Redis connections are properly closed even if the app crashes."
    """
    # Startup
    await redis_client.connect()
    logger.info(
        "application_startup",
        app_name=settings.app_name,
        version=settings.app_version,
        redis_url=settings.redis_url
    )
    yield
    # Shutdown
    await redis_client.disconnect()
    logger.info("application_shutdown")


# Create FastAPI application
app = FastAPI(
    title="DeadDrop API",
    description="Zero-knowledge ephemeral file sharing with client-side encryption",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)


# Request ID middleware (must be first to track all requests)
app.add_middleware(RequestIDMiddleware)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,  # No cookies needed (stateless)
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],  # Allow client to read request ID
    max_age=3600,  # Cache preflight requests for 1 hour
)


# Dependency injection middleware for Redis and request context
@app.middleware("http")
async def add_dependencies(request: Request, call_next):
    """
    Inject dependencies and context into request state.

    This allows endpoints to access:
    - redis_client via request.state.redis
    - request_id via request.state.request_id (set by RequestIDMiddleware)

    Also sets the request ID in logging context for automatic inclusion
    in all log entries during this request.
    """
    # Set request ID in logging context
    if hasattr(request.state, "request_id"):
        set_request_id(request.state.request_id)

    # Inject Redis client
    request.state.redis = redis_client

    response = await call_next(request)
    return response


# Include API routers
app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
app.include_router(download.router, prefix="/api/v1", tags=["download"])


@app.get("/api/v1/health", tags=["health"])
async def health_check(request: Request):
    """
    Health check endpoint for monitoring and load balancers.

    Checks:
    - Application is running (implicit)
    - Redis connection is healthy

    Returns:
        JSON with status, version, and dependency health
    """
    # Check Redis health
    redis_healthy = await redis_client.health_check()

    # Overall health is healthy only if all dependencies are healthy
    overall_status = "healthy" if redis_healthy else "degraded"

    return {
        "status": overall_status,
        "version": settings.app_version,
        "service": settings.app_name,
        "dependencies": {
            "redis": "healthy" if redis_healthy else "unhealthy"
        }
    }


# Custom exception handler for DeadDrop exceptions
@app.exception_handler(DeadDropException)
async def deaddrop_exception_handler(request: Request, exc: DeadDropException):
    """
    Handler for custom DeadDrop exceptions.

    Converts custom exceptions to appropriate HTTP responses while
    logging full details for debugging.
    """
    logger.warning(
        "deaddrop_exception",
        exception_type=exc.__class__.__name__,
        message=exc.message,
        details=exc.details,
        path=request.url.path,
        method=request.method
    )

    # Convert to HTTPException and return
    http_exc = exception_to_http_exception(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail,
        headers=http_exc.headers
    )


# Validation error handler for better error messages
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handler for request validation errors.

    Provides detailed validation error messages to help clients
    fix their requests.
    """
    logger.warning(
        "validation_error",
        errors=exc.errors(),
        path=request.url.path,
        method=request.method
    )

    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "details": exc.errors()
        }
    )


# Global exception handler (prevents information leakage)
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Catch-all exception handler for unexpected errors.

    Logs the error with full details including stack trace but returns
    generic message to client. This prevents information leakage while
    maintaining observability for operations teams.
    """
    # Log full exception with stack trace
    logger.error(
        "unhandled_exception",
        error=str(exc),
        exception_type=exc.__class__.__name__,
        path=request.url.path,
        method=request.method,
        traceback=traceback.format_exc()
    )

    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
