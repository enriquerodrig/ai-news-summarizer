"""
Cache management component with TTL support.

This module provides an in-memory cache with time-to-live (TTL) functionality,
automatic expiration checking, and thread-safe operations for concurrent access.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """Cache entry with TTL tracking."""
    value: Any
    created_at: datetime
    ttl_seconds: int
    
    def is_expired(self) -> bool:
        """Check if entry has exceeded TTL."""
        age = (datetime.utcnow() - self.created_at).total_seconds()
        return age > self.ttl_seconds


class CacheManager:
    """
    In-memory cache manager with TTL support and thread-safe operations.
    
    Provides methods for storing, retrieving, and invalidating cached values
    with automatic expiration checking. Uses asyncio locks for thread safety.
    """
    
    def __init__(self, ttl_minutes: int = 30):
        """
        Initialize cache with TTL configuration.
        
        Args:
            ttl_minutes: Default time-to-live in minutes for cached entries
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._default_ttl_seconds = ttl_minutes * 60
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve cached value if not expired.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            Cached value if exists and not expired, None otherwise
        """
        async with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if entry.is_expired():
                # Remove expired entry
                del self._cache[key]
                return None
            
            return entry.value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Store value with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL in seconds (uses default if not provided)
        """
        async with self._lock:
            ttl_seconds = ttl if ttl is not None else self._default_ttl_seconds
            entry = CacheEntry(
                value=value,
                created_at=datetime.utcnow(),
                ttl_seconds=ttl_seconds
            )
            self._cache[key] = entry
    
    async def invalidate(self, key: str):
        """
        Remove cached value.
        
        Args:
            key: Cache key to remove
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def is_expired(self, key: str) -> bool:
        """
        Check if cached value has expired (synchronous check).
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key doesn't exist or is expired, False otherwise
        """
        if key not in self._cache:
            return True
        
        return self._cache[key].is_expired()
    
    async def cleanup_expired(self):
        """
        Remove all expired entries from cache.
        
        This method can be called periodically to free memory.
        """
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
    
    async def clear(self):
        """Clear all cached entries."""
        async with self._lock:
            self._cache.clear()
    
    async def size(self) -> int:
        """
        Get the number of entries in cache.
        
        Returns:
            Number of cached entries (including expired ones)
        """
        async with self._lock:
            return len(self._cache)
