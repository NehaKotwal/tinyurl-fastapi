"""
URL service containing business logic for URL shortening.
Coordinates between repository, cache, and encoder.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from src.models.url import URLModel, URLCreate, URLUpdate, URLResponse, URLStats, ShortenResponse
from src.repository.url_repository import URLRepository
from src.services.encoder import ShortCodeGenerator
from src.services.cache_service import URLCacheManager
from src.utils.validators import sanitize_url, validate_custom_alias
from src.utils.exceptions import (
    URLNotFoundException,
    URLExpiredException,
    CustomAliasAlreadyExistsException,
    InvalidCustomAliasException
)
from src.config import settings


class URLService:
    """
    Service layer for URL shortening operations.
    Orchestrates repository, cache, and encoder.
    """

    def __init__(
        self,
        repository: URLRepository,
        cache_manager: Optional[URLCacheManager] = None,
        short_code_generator: Optional[ShortCodeGenerator] = None
    ):
        """
        Initialize URL service.

        Args:
            repository: URL repository instance
            cache_manager: Cache manager instance (optional)
            short_code_generator: Short code generator (optional)
        """
        self.repository = repository
        self.cache_manager = cache_manager
        self.short_code_generator = short_code_generator or ShortCodeGenerator(
            min_length=settings.short_code_length
        )

    def shorten_url(self, url_data: URLCreate) -> ShortenResponse:
        """
        Create shortened URL.

        Args:
            url_data: URL creation data

        Returns:
            ShortenResponse with short URL details

        Raises:
            CustomAliasAlreadyExistsException: If custom alias exists
            InvalidCustomAliasException: If custom alias is invalid
        """
        # Sanitize URL
        original_url = sanitize_url(url_data.original_url)

        # Validate custom alias if provided
        if url_data.custom_alias:
            is_valid, error_msg = validate_custom_alias(
                url_data.custom_alias,
                settings.custom_alias_min_length,
                settings.custom_alias_max_length
            )
            if not is_valid:
                raise InvalidCustomAliasException(error_msg)

        # Create URL entry in database
        url_entry = self.repository.create(
            original_url=original_url,
            custom_alias=url_data.custom_alias,
            expires_at=url_data.expires_at,
            user_id=url_data.user_id
        )

        # Generate short code from ID
        short_code = self.short_code_generator.generate_from_id(url_entry.id)

        # Update the entry with short code
        url_entry = self.repository.update_short_code(url_entry.id, short_code)

        # Build short URL
        short_url = f"{settings.base_url}/{short_code}"

        return ShortenResponse(
            short_code=short_code,
            short_url=short_url,
            original_url=original_url,
            custom_alias=url_data.custom_alias,
            created_at=url_entry.created_at,
            expires_at=url_entry.expires_at
        )

    def get_original_url(self, short_code: str) -> str:
        """
        Get original URL from short code and track access.

        Args:
            short_code: Short code or custom alias

        Returns:
            Original URL

        Raises:
            URLNotFoundException: If URL not found
            URLExpiredException: If URL has expired
        """
        # Check cache first
        if self.cache_manager and settings.cache_enabled:
            cached_url = self.cache_manager.get_url(short_code)
            if cached_url:
                # Still need to increment counter in DB
                try:
                    self.repository.increment_click_count(short_code)
                except Exception:
                    pass  # Don't fail redirect on counter update
                return cached_url

        # Try to get by short code
        url_entry = self.repository.get_by_short_code(short_code)

        # If not found, try custom alias
        if not url_entry:
            url_entry = self.repository.get_by_custom_alias(short_code)

        if not url_entry:
            raise URLNotFoundException(f"Short URL '{short_code}' not found")

        # Check if expired
        if url_entry.expires_at and url_entry.expires_at < datetime.now(timezone.utc):
            raise URLExpiredException(f"Short URL '{short_code}' has expired")

        # Increment click count and update last accessed
        url_entry = self.repository.increment_click_count(short_code)

        # Cache the URL if it's popular
        if self.cache_manager and settings.cache_enabled:
            self.cache_manager.cache_url(
                short_code=short_code,
                original_url=url_entry.original_url,
                click_count=url_entry.click_count,
                ttl=settings.cache_ttl
            )

        return url_entry.original_url

    def get_url_stats(self, short_code: str) -> URLStats:
        """
        Get statistics for a shortened URL.

        Args:
            short_code: Short code or custom alias

        Returns:
            URLStats with statistics

        Raises:
            URLNotFoundException: If URL not found
        """
        # Try to get by short code
        url_entry = self.repository.get_by_short_code(short_code)

        # If not found, try custom alias
        if not url_entry:
            url_entry = self.repository.get_by_custom_alias(short_code)

        if not url_entry:
            raise URLNotFoundException(f"Short URL '{short_code}' not found")

        is_expired = False
        if url_entry.expires_at and url_entry.expires_at < datetime.now(timezone.utc):
            is_expired = True

        return URLStats(
            short_code=url_entry.short_code,
            original_url=url_entry.original_url,
            created_at=url_entry.created_at,
            click_count=url_entry.click_count,
            last_accessed_at=url_entry.last_accessed_at,
            expires_at=url_entry.expires_at,
            is_expired=is_expired
        )

    def list_urls(
        self,
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[str] = None
    ) -> List[URLResponse]:
        """
        List all shortened URLs.

        Args:
            limit: Maximum number of URLs to return
            offset: Number of URLs to skip
            user_id: Optional user ID filter

        Returns:
            List of URLResponse
        """
        url_entries = self.repository.list_all(limit=limit, offset=offset, user_id=user_id)

        responses = []
        for entry in url_entries:
            short_url = f"{settings.base_url}/{entry.short_code}"
            responses.append(URLResponse(
                id=entry.id,
                short_code=entry.short_code,
                original_url=entry.original_url,
                custom_alias=entry.custom_alias,
                created_at=entry.created_at,
                expires_at=entry.expires_at,
                click_count=entry.click_count,
                last_accessed_at=entry.last_accessed_at,
                short_url=short_url
            ))

        return responses

    def update_url(self, short_code: str, url_update: URLUpdate) -> URLResponse:
        """
        Update a shortened URL.

        Args:
            short_code: Short code or custom alias
            url_update: Update data

        Returns:
            Updated URLResponse

        Raises:
            URLNotFoundException: If URL not found
        """
        # Sanitize URL if provided
        original_url = None
        if url_update.original_url:
            original_url = sanitize_url(url_update.original_url)

        # Update in database
        url_entry = self.repository.update(
            short_code=short_code,
            original_url=original_url,
            expires_at=url_update.expires_at
        )

        # Invalidate cache
        if self.cache_manager and settings.cache_enabled:
            self.cache_manager.invalidate_url(short_code)

        short_url = f"{settings.base_url}/{url_entry.short_code}"
        return URLResponse(
            id=url_entry.id,
            short_code=url_entry.short_code,
            original_url=url_entry.original_url,
            custom_alias=url_entry.custom_alias,
            created_at=url_entry.created_at,
            expires_at=url_entry.expires_at,
            click_count=url_entry.click_count,
            last_accessed_at=url_entry.last_accessed_at,
            short_url=short_url
        )

    def delete_url(self, short_code: str) -> bool:
        """
        Delete a shortened URL.

        Args:
            short_code: Short code or custom alias

        Returns:
            True if deleted, False if not found
        """
        deleted = self.repository.delete(short_code)

        # Invalidate cache
        if deleted and self.cache_manager and settings.cache_enabled:
            self.cache_manager.invalidate_url(short_code)

        return deleted

    def get_stats_summary(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get summary statistics.

        Args:
            user_id: Optional user ID filter

        Returns:
            Dictionary with summary stats
        """
        total_urls = self.repository.count_all(user_id=user_id)

        stats = {
            'total_urls': total_urls,
            'base_url': settings.base_url
        }

        # Add cache stats if enabled
        if self.cache_manager and settings.cache_enabled:
            stats['cache'] = self.cache_manager.get_cache_stats()

        return stats
