"""
Main FastAPI application for URL Shortener service.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import logging
from pathlib import Path

from src.config import settings
from src.api.routes import router, set_url_service
from src.api.middleware import RateLimitMiddleware
from src.repository.url_repository import URLRepository, DatabaseConnection
from src.services.url_service import URLService
from src.services.cache_service import get_cache_manager
from src.services.encoder import ShortCodeGenerator

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI application
    """
    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="A scalable URL shortener service with analytics, caching, and rate limiting.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_allowed_origins_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add rate limiting middleware
    app.add_middleware(
        RateLimitMiddleware,
        enabled=settings.rate_limit_enabled,
        requests=settings.rate_limit_requests,
        window=settings.rate_limit_window
    )

    # Initialize database
    logger.info(f"Connecting to database: {settings.database_url}")
    db_connection = DatabaseConnection(settings.database_url)

    # Initialize repository
    repository = URLRepository(db_connection)

    # Initialize cache manager
    cache_manager = None
    if settings.cache_enabled:
        logger.info("Cache enabled")
        cache_manager = get_cache_manager(
            max_size=settings.cache_max_size,
            ttl=settings.cache_ttl,
            popular_threshold=settings.cache_popular_threshold
        )

    # Initialize short code generator
    short_code_generator = ShortCodeGenerator(min_length=settings.short_code_length)

    # Initialize URL service
    url_service = URLService(
        repository=repository,
        cache_manager=cache_manager,
        short_code_generator=short_code_generator
    )

    # Set service in routes
    set_url_service(url_service)

    # Include routes
    app.include_router(router)

    # Mount static files
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        logger.info(f"Static files mounted from: {static_dir}")

    # Add root redirect to UI
    @app.get("/")
    async def root():
        """Redirect to web UI."""
        return RedirectResponse(url="/static/index.html")

    # Add exception handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """Global exception handler."""
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

    logger.info("Application startup complete")

    return app


# Create app instance
app = create_app()


@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Base URL: {settings.base_url}")
    logger.info(f"Rate limiting: {'enabled' if settings.rate_limit_enabled else 'disabled'}")
    logger.info(f"Caching: {'enabled' if settings.cache_enabled else 'disabled'}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info("Shutting down application")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
