"""
Unit tests for cache service.
"""
import pytest
import time
from src.services.cache_service import LRUCache, URLCacheManager


class TestLRUCache:
    """Test LRU cache implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = LRUCache(max_size=3, default_ttl=2)

    def test_set_and_get(self):
        """Test basic set and get operations."""
        self.cache.set('key1', 'value1')
        result = self.cache.get('key1')
        assert result == 'value1'

    def test_get_nonexistent_key(self):
        """Test getting non-existent key."""
        result = self.cache.get('nonexistent')
        assert result is None

    def test_cache_expiration(self):
        """Test TTL expiration."""
        self.cache.set('key1', 'value1', ttl=1)
        assert self.cache.get('key1') == 'value1'

        time.sleep(1.1)
        result = self.cache.get('key1')
        assert result is None

    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        self.cache.set('key1', 'value1')
        self.cache.set('key2', 'value2')
        self.cache.set('key3', 'value3')

        # Access key1 to make it recently used
        self.cache.get('key1')

        # Add new key, should evict key2 (least recently used)
        self.cache.set('key4', 'value4')

        assert self.cache.get('key1') == 'value1'
        assert self.cache.get('key2') is None  # Evicted
        assert self.cache.get('key3') == 'value3'
        assert self.cache.get('key4') == 'value4'

    def test_update_existing_key(self):
        """Test updating existing key."""
        self.cache.set('key1', 'value1')
        self.cache.set('key1', 'value2')
        result = self.cache.get('key1')
        assert result == 'value2'

    def test_delete(self):
        """Test deleting a key."""
        self.cache.set('key1', 'value1')
        self.cache.delete('key1')
        result = self.cache.get('key1')
        assert result is None

    def test_clear(self):
        """Test clearing cache."""
        self.cache.set('key1', 'value1')
        self.cache.set('key2', 'value2')
        self.cache.clear()

        assert self.cache.get('key1') is None
        assert self.cache.get('key2') is None
        assert self.cache.size() == 0

    def test_cleanup_expired(self):
        """Test cleaning up expired entries."""
        self.cache.set('key1', 'value1', ttl=1)
        self.cache.set('key2', 'value2', ttl=10)

        time.sleep(1.1)
        self.cache.cleanup_expired()

        assert self.cache.get('key1') is None
        assert self.cache.get('key2') == 'value2'

    def test_cache_stats(self):
        """Test cache statistics."""
        self.cache.set('key1', 'value1')
        self.cache.get('key1')  # Hit
        self.cache.get('key2')  # Miss

        stats = self.cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['size'] == 1
        assert stats['max_size'] == 3
        assert stats['total_requests'] == 2

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        self.cache.set('key1', 'value1')

        # 2 hits, 1 miss = 66.67% hit rate
        self.cache.get('key1')
        self.cache.get('key1')
        self.cache.get('key2')

        stats = self.cache.get_stats()
        assert stats['hit_rate'] == pytest.approx(66.67, rel=0.01)


class TestURLCacheManager:
    """Test URL cache manager."""

    def setup_method(self):
        """Set up test fixtures."""
        # Clear singleton instance
        URLCacheManager._instance = None
        self.manager = URLCacheManager(max_size=10, ttl=60, popular_threshold=5)

    def test_singleton_pattern(self):
        """Test that cache manager is a singleton."""
        manager1 = URLCacheManager()
        manager2 = URLCacheManager()
        assert manager1 is manager2

    def test_cache_url_below_threshold(self):
        """Test that URLs below popularity threshold are not cached."""
        self.manager.cache_url('abc123', 'https://example.com', click_count=3)
        result = self.manager.get_url('abc123')
        assert result is None

    def test_cache_url_above_threshold(self):
        """Test that popular URLs are cached."""
        self.manager.cache_url('abc123', 'https://example.com', click_count=10)
        result = self.manager.get_url('abc123')
        assert result == 'https://example.com'

    def test_invalidate_url(self):
        """Test invalidating cached URL."""
        self.manager.cache_url('abc123', 'https://example.com', click_count=10)
        self.manager.invalidate_url('abc123')
        result = self.manager.get_url('abc123')
        assert result is None

    def test_clear_cache(self):
        """Test clearing all cached URLs."""
        self.manager.cache_url('abc123', 'https://example.com', click_count=10)
        self.manager.cache_url('def456', 'https://example2.com', click_count=10)
        self.manager.clear_cache()

        assert self.manager.get_url('abc123') is None
        assert self.manager.get_url('def456') is None

    def test_get_cache_stats(self):
        """Test getting cache statistics."""
        self.manager.cache_url('abc123', 'https://example.com', click_count=10)
        self.manager.get_url('abc123')

        stats = self.manager.get_cache_stats()
        assert 'hits' in stats
        assert 'misses' in stats
        assert 'size' in stats
        assert 'hit_rate' in stats

    def test_custom_ttl(self):
        """Test caching with custom TTL."""
        self.manager.cache_url('abc123', 'https://example.com', click_count=10, ttl=1)
        assert self.manager.get_url('abc123') == 'https://example.com'

        time.sleep(1.1)
        result = self.manager.get_url('abc123')
        assert result is None
