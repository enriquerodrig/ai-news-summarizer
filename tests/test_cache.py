"""
Unit tests for CacheManager component.

Tests cache functionality including TTL expiration, invalidation,
and concurrent access scenarios.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from app.components.cache import CacheManager, CacheEntry


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""
    
    def test_cache_entry_not_expired(self):
        """Test that a fresh cache entry is not expired."""
        entry = CacheEntry(
            value="test_value",
            created_at=datetime.utcnow(),
            ttl_seconds=60
        )
        assert not entry.is_expired()
    
    def test_cache_entry_expired(self):
        """Test that an old cache entry is expired."""
        entry = CacheEntry(
            value="test_value",
            created_at=datetime.utcnow() - timedelta(seconds=120),
            ttl_seconds=60
        )
        assert entry.is_expired()
    
    def test_cache_entry_exactly_at_ttl(self):
        """Test edge case where entry is past TTL boundary."""
        entry = CacheEntry(
            value="test_value",
            created_at=datetime.utcnow() - timedelta(seconds=61),
            ttl_seconds=60
        )
        # Should be expired (age > ttl_seconds)
        assert entry.is_expired()


class TestCacheManager:
    """Tests for CacheManager class."""
    
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = CacheManager(ttl_minutes=30)
        
        await cache.set("test_key", "test_value")
        result = await cache.get("test_key")
        
        assert result == "test_value"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self):
        """Test getting a key that doesn't exist."""
        cache = CacheManager(ttl_minutes=30)
        
        result = await cache.get("nonexistent")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_set_with_custom_ttl(self):
        """Test setting a value with custom TTL."""
        cache = CacheManager(ttl_minutes=30)
        
        # Set with 2 second TTL
        await cache.set("test_key", "test_value", ttl=2)
        
        # Should exist immediately
        result = await cache.get("test_key")
        assert result == "test_value"
        
        # Wait for expiration
        await asyncio.sleep(2.1)
        
        # Should be expired now
        result = await cache.get("test_key")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_invalidate(self):
        """Test cache invalidation."""
        cache = CacheManager(ttl_minutes=30)
        
        await cache.set("test_key", "test_value")
        await cache.invalidate("test_key")
        
        result = await cache.get("test_key")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_invalidate_nonexistent_key(self):
        """Test invalidating a key that doesn't exist (should not raise error)."""
        cache = CacheManager(ttl_minutes=30)
        
        # Should not raise an exception
        await cache.invalidate("nonexistent")
    
    def test_is_expired_nonexistent_key(self):
        """Test is_expired for nonexistent key."""
        cache = CacheManager(ttl_minutes=30)
        
        assert cache.is_expired("nonexistent")
    
    def test_is_expired_fresh_entry(self):
        """Test is_expired for fresh entry."""
        cache = CacheManager(ttl_minutes=30)
        
        # Manually add entry to cache
        cache._cache["test_key"] = CacheEntry(
            value="test_value",
            created_at=datetime.utcnow(),
            ttl_seconds=1800
        )
        
        assert not cache.is_expired("test_key")
    
    def test_is_expired_old_entry(self):
        """Test is_expired for expired entry."""
        cache = CacheManager(ttl_minutes=30)
        
        # Manually add expired entry
        cache._cache["test_key"] = CacheEntry(
            value="test_value",
            created_at=datetime.utcnow() - timedelta(seconds=2000),
            ttl_seconds=1800
        )
        
        assert cache.is_expired("test_key")
    
    @pytest.mark.asyncio
    async def test_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = CacheManager(ttl_minutes=30)
        
        # Add fresh entry
        await cache.set("fresh_key", "fresh_value")
        
        # Add expired entry manually
        cache._cache["expired_key"] = CacheEntry(
            value="expired_value",
            created_at=datetime.utcnow() - timedelta(seconds=2000),
            ttl_seconds=1800
        )
        
        # Cleanup
        await cache.cleanup_expired()
        
        # Fresh entry should still exist
        assert await cache.get("fresh_key") == "fresh_value"
        
        # Expired entry should be gone
        assert await cache.get("expired_key") is None
    
    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clearing all cache entries."""
        cache = CacheManager(ttl_minutes=30)
        
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        await cache.clear()
        
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert await cache.size() == 0
    
    @pytest.mark.asyncio
    async def test_size(self):
        """Test getting cache size."""
        cache = CacheManager(ttl_minutes=30)
        
        assert await cache.size() == 0
        
        await cache.set("key1", "value1")
        assert await cache.size() == 1
        
        await cache.set("key2", "value2")
        assert await cache.size() == 2
        
        await cache.invalidate("key1")
        assert await cache.size() == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Test thread-safe concurrent access."""
        cache = CacheManager(ttl_minutes=30)
        
        async def set_value(key: str, value: str):
            await cache.set(key, value)
        
        async def get_value(key: str):
            return await cache.get(key)
        
        # Perform concurrent operations
        await asyncio.gather(
            set_value("key1", "value1"),
            set_value("key2", "value2"),
            set_value("key3", "value3"),
        )
        
        results = await asyncio.gather(
            get_value("key1"),
            get_value("key2"),
            get_value("key3"),
        )
        
        assert results == ["value1", "value2", "value3"]
    
    @pytest.mark.asyncio
    async def test_overwrite_existing_key(self):
        """Test overwriting an existing cache entry."""
        cache = CacheManager(ttl_minutes=30)
        
        await cache.set("test_key", "value1")
        await cache.set("test_key", "value2")
        
        result = await cache.get("test_key")
        assert result == "value2"
    
    @pytest.mark.asyncio
    async def test_default_ttl_minutes(self):
        """Test that default TTL is correctly converted to seconds."""
        cache = CacheManager(ttl_minutes=1)
        
        await cache.set("test_key", "test_value")
        
        # Check internal TTL is in seconds
        entry = cache._cache["test_key"]
        assert entry.ttl_seconds == 60
    
    @pytest.mark.asyncio
    async def test_get_removes_expired_entry(self):
        """Test that get() automatically removes expired entries."""
        cache = CacheManager(ttl_minutes=30)
        
        # Manually add expired entry
        cache._cache["expired_key"] = CacheEntry(
            value="expired_value",
            created_at=datetime.utcnow() - timedelta(seconds=2000),
            ttl_seconds=1800
        )
        
        # Get should return None and remove the entry
        result = await cache.get("expired_key")
        assert result is None
        
        # Entry should be removed from cache
        assert "expired_key" not in cache._cache
