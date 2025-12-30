"""
DeadDrop FastAPI Application

Zero-knowledge ephemeral file sharing service.
Server never sees encryption keys or plaintext data.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from api.v1 import upload, download
from services.redis_client import RedisClient
from core.config import settings
from core.logging import setup_logging, get_logger

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


# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,  # No cookies needed (stateless)
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    max_age=3600,  # Cache preflight requests for 1 hour
)


# Dependency injection middleware for Redis
@app.middleware("http")
async def add_dependencies(request: Request, call_next):
    """
    Inject dependencies into request state.
    
    This allows endpoints to access redis_client via request.state.redis
    without passing it as a parameter to every function.
    """
    request.state.redis = redis_client
    response = await call_next(request)
    return response


# Include API routers
app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
app.include_router(download.router, prefix="/api/v1", tags=["download"])


@app.get("/api/v1/health", tags=["health"])
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        JSON with status and version information
    """
    return {
        "status": "healthy",
        "version": settings.app_version,
        "service": settings.app_name
    }


# Global exception handler (prevents information leakage)
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Catch-all exception handler.
    
    Logs the error with full details but returns generic message to client.
    This prevents attackers from learning about internal system architecture.
    
    Interview Talking Point:
        "I log the full exception server-side for debugging, but return a
        generic error to the client. This prevents information leakage while
        maintaining observability for operations teams."
    """
    logger.error(
        "unhandled_exception",
        error=str(exc),
        path=request.url.path,
        method=request.method
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
