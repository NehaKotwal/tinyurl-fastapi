"""
API routes for URL shortener service.
Simplified version with core functionality only.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import RedirectResponse

from src.models.url import URLCreate, URLResponse, URLStats, ShortenResponse
from src.services.url_service import URLService
from src.utils.exceptions import (
    URLNotFoundException,
    URLExpiredException,
    CustomAliasAlreadyExistsException,
    InvalidURLException,
    InvalidCustomAliasException,
    DatabaseException
)


# Create router
router = APIRouter()

# Service instance (will be set by main app)
url_service: Optional[URLService] = None


def set_url_service(service: URLService):
    """Set the URL service instance."""
    global url_service
    url_service = service


def get_url_service() -> URLService:
    """Get URL service instance."""
    if url_service is None:
        raise RuntimeError("URL service not initialized")
    return url_service


@router.get(
    "/health",
    summary="Health check",
    tags=["System"]
)
async def health_check():
    """Check if the service is running."""
    return {
        "status": "healthy",
        "service": "URL Shortener",
        "version": "1.0.0"
    }


@router.post(
    "/api/shorten",
    response_model=ShortenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Shorten a URL",
    tags=["URL Operations"]
)
async def shorten_url(url_data: URLCreate):
    """
    Create a shortened URL.

    - **original_url**: The long URL to shorten
    - **custom_alias**: Optional custom alias (4-20 characters)
    - **expires_at**: Optional expiration date
    """
    try:
        service = get_url_service()
        result = service.shorten_url(url_data)
        return result

    except CustomAliasAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except (InvalidCustomAliasException, InvalidURLException) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DatabaseException:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )


@router.get(
    "/api/urls",
    response_model=List[URLResponse],
    summary="List all URLs",
    tags=["URL Operations"]
)
async def list_urls(
    limit: int = Query(100, ge=1, le=1000, description="Maximum URLs to return"),
    offset: int = Query(0, ge=0, description="Number of URLs to skip")
):
    """Get a list of all shortened URLs with pagination."""
    try:
        service = get_url_service()
        urls = service.list_urls(limit=limit, offset=offset)
        return urls

    except DatabaseException:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )


@router.get(
    "/api/urls/{short_code}/stats",
    response_model=URLStats,
    summary="Get URL statistics",
    tags=["Analytics"]
)
async def get_url_stats(short_code: str):
    """
    Get statistics for a shortened URL.

    Returns click count, creation date, and last accessed time.
    """
    try:
        service = get_url_service()
        stats = service.get_url_stats(short_code)
        return stats

    except URLNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except DatabaseException:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )


@router.get(
    "/{short_code}",
    summary="Redirect to original URL",
    tags=["URL Operations"],
    response_class=RedirectResponse
)
async def redirect_to_url(short_code: str):
    """
    Redirect to the original URL using short code or custom alias.

    Also increments the click counter for analytics.
    """
    try:
        service = get_url_service()
        original_url = service.get_original_url(short_code)
        return RedirectResponse(
            url=original_url,
            status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )

    except URLNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except URLExpiredException as e:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=str(e)
        )
    except DatabaseException:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
