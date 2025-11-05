"""
Cache service with LRU eviction and TTL.
Implements Singleton pattern for cache manager.
"""
import time
from typing import Optional, Dict, Any
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock


@dataclass
class CacheEntry:
    """Cache entry with value and expiration time."""

    value: Any
    expires_at: float
    access_count: int = 0

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.time() > self.expires_at

    def increment_access(self):
        """Increment access counter."""
        self.access_count += 1


class LRUCache:
    """
    LRU (Least Recently Used) Cache with TTL support.
    Thread-safe implementation using locks.
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of entries
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                return None

            # Check if expired
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.increment_access()
            self._hits += 1

            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        with self._lock:
            ttl = ttl if ttl is not None else self.default_ttl
            expires_at = time.time() + ttl

            # Update existing entry
            if key in self._cache:
                self._cache[key] = CacheEntry(value, expires_at)
                self._cache.move_to_end(key)
                return

            # Add new entry
            self._cache[key] = CacheEntry(value, expires_at)

            # Evict LRU if at capacity
            if len(self._cache) > self.max_size:
                self._evict_lru()

    def delete(self, key: str):
        """
        Delete entry from cache.

        Args:
            key: Cache key
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def _evict_lru(self):
        """Evict least recently used entry."""
        if self._cache:
            # Remove first item (least recently used)
            self._cache.popitem(last=False)

    def cleanup_expired(self):
        """Remove all expired entries."""
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.expires_at < current_time
            ]
            for key in expired_keys:
                del self._cache[key]

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': round(hit_rate, 2),
                'total_requests': total_requests
            }

    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)


class URLCacheManager:
    """
    Cache manager specifically for URL shortener.
    Implements Singleton pattern.
    """

    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton pattern implementation."""
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, max_size: int = 1000, ttl: int = 3600, popular_threshold: int = 10):
        """
        Initialize URL cache manager.

        Args:
            max_size: Maximum cache size
            ttl: Time-to-live in seconds
            popular_threshold: Click count threshold for caching
        """
        # Avoid re-initialization
        if hasattr(self, '_initialized'):
            return

        self._cache = LRUCache(max_size=max_size, default_ttl=ttl)
        self._popular_threshold = popular_threshold
        self._initialized = True

    def get_url(self, short_code: str) -> Optional[str]:
        """
        Get original URL from cache.

        Args:
            short_code: Short code

        Returns:
            Original URL or None
        """
        return self._cache.get(short_code)

    def cache_url(self, short_code: str, original_url: str, click_count: int = 0, ttl: Optional[int] = None):
        """
        Cache URL if it meets popularity threshold.

        Args:
            short_code: Short code
            original_url: Original URL
            click_count: Number of clicks
            ttl: Time-to-live (optional)
        """
        # Only cache popular URLs
        if click_count >= self._popular_threshold:
            self._cache.set(short_code, original_url, ttl)

    def invalidate_url(self, short_code: str):
        """
        Invalidate cached URL.

        Args:
            short_code: Short code to invalidate
        """
        self._cache.delete(short_code)

    def clear_cache(self):
        """Clear all cached URLs."""
        self._cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self._cache.get_stats()

    def cleanup_expired(self):
        """Remove expired entries from cache."""
        self._cache.cleanup_expired()


# Global cache manager instance
_cache_manager: Optional[URLCacheManager] = None


def get_cache_manager(max_size: int = 1000, ttl: int = 3600, popular_threshold: int = 10) -> URLCacheManager:
    """
    Get or create cache manager instance (Singleton).

    Args:
        max_size: Maximum cache size
        ttl: Time-to-live in seconds
        popular_threshold: Click count threshold

    Returns:
        URLCacheManager instance
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = URLCacheManager(
            max_size=max_size,
            ttl=ttl,
            popular_threshold=popular_threshold
        )
    return _cache_manager
