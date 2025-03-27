"""
Main application module.
"""
import logging
import logging.config
import time  # Import time
from fastapi import FastAPI

from .api_routes import router
from .config import settings, CacheType  # Import CacheType
from .wikipedia_client import WikipediaClient
from .caching_service import CachingService
from .parser import WikipediaParser
from .security import setup_security

# Configure logging
logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": settings.LOG_FORMAT
        }
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "formatter": "default",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "wikipedia_mcp.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
    },
    "loggers": {
        "": {
            "handlers": ["default", "file"],
            "level": settings.LOG_LEVEL
        }
    }
})

# Setup logging
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Wikipedia MCP API",
    description="API for parsing and caching Wikipedia articles",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# Setup security middleware (includes CORS)
setup_security(app)

# Include API routes
app.include_router(router, prefix="/api/v1")

# Health check endpoint
@app.get("/ping")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application state and singletons on startup."""
    logger.info("Starting Wikipedia MCP API")

    # Create and store singleton instances in app.state
    # Note: Renamed RATE_LIMIT to WIKIPEDIA_RATE_LIMIT in config (will update config next)
    app.state.wikipedia_client = WikipediaClient(rate_limit_delay=settings.WIKIPEDIA_RATE_LIMIT)
    app.state.cache_service = CachingService(
        cache_type=settings.CACHE_TYPE,
        ttl=settings.CACHE_TTL,
        maxsize=settings.CACHE_MAXSIZE,
        cache_dir=settings.CACHE_DIR
    )
    app.state.parser = WikipediaParser()

    logger.info(f"Cache: {settings.CACHE_TYPE.value} (TTL: {settings.CACHE_TTL}s, Max Size: {settings.CACHE_MAXSIZE})")
    logger.info(f"Wikipedia Rate Limit: {settings.WIKIPEDIA_RATE_LIMIT}s between requests")
    # Note: Added API_RATE_LIMIT and API_RATE_LIMIT_WINDOW to config (will update config next)
    logger.info(f"API Rate Limit: {settings.API_RATE_LIMIT} requests per {settings.API_RATE_LIMIT_WINDOW}s")

    # Initialize API stats
    app.state.api_stats = {
        "requests": 0,
        "errors": 0,
        "start_time": time.time() # Use time.time()
    }
    logger.info("Application startup complete.")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup application state on shutdown."""
    logger.info("Shutting down Wikipedia MCP API")
    # Access cache_service from app.state
    cache_service: CachingService = getattr(app.state, 'cache_service', None)
    if cache_service:
        if settings.CACHE_TYPE == CacheType.PERSIST:
            # Ideally, make _save_cache async or run in executor
            logger.info("Saving persistent cache...")
            cache_service._save_cache() # Use internal method for now
            logger.info("Persistent cache saved.")
        elif settings.CACHE_TYPE == CacheType.DISK:
            logger.info("Closing disk cache...")
            cache_service.cache.close() # Ensure disk cache is closed
            logger.info("Disk cache closed.")
    logger.info("Application shutdown complete.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD
    )
