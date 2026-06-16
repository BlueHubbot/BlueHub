"""
BlueHub Cache Module
=====================
Redis-based caching with structured key patterns,
serialization, and TTL management.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import timedelta
from typing import Any, TypeVar

import redis.asyncio as aioredis

from core.config import settings

T = TypeVar("T")


def build_cache_key(prefix: str, *parts: str | int, **kwargs: str | int) -> str:
    """
    Build a structured cache key with namespace.

    Examples:
        >>> build_cache_key("user", 1)
        'bluehub:user:1'
        >>> build_cache_key("vpn", "config", "user:1")
        'bluehub:vpn:config:user:1'
    """
    key_parts = ["bluehub", prefix]
    key_parts.extend(str(p) for p in parts)
    if kwargs:
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
    return ":".join(key_parts)


class CacheService:
    """
    Redis-backed cache service with serialization support.
    Provides high-level get/set/delete with structured keys.
    """

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url or str(settings.REDIS_URL)
        self._client: aioredis.Redis | None = None
        self._default_ttl: int = 300  # 5 minutes

    @property
    def client(self) -> aioredis.Redis:
        """Get or create the Redis client."""
        if self._client is None:
            self._client = aioredis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=settings.REDIS_POOL_SIZE,
            )
        return self._client

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def ping(self) -> bool:
        """Check if Redis is reachable."""
        try:
            return await self.client.ping()
        except Exception:
            return False

    # --- Basic Operations ---

    async def get(self, key: str, default: T | None = None) -> Any | T | None:
        """
        Get a value from cache.

        Args:
            key: Cache key
            default: Default value if key not found

        Returns:
            Deserialized value or default.
        """
        value = await self.client.get(key)
        if value is None:
            return default
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | timedelta | None = None,
    ) -> bool:
        """
        Set a value in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time-to-live in seconds or timedelta

        Returns:
            True if successful.
        """
        if isinstance(ttl, timedelta):
            ttl = int(ttl.total_seconds())
        ttl = ttl or self._default_ttl

        serialized = json.dumps(value, default=str)
        return await self.client.setex(key, ttl, serialized)

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        return bool(await self.client.delete(key))

    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        return await self.client.exists(key) > 0

    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL on an existing key."""
        return await self.client.expire(key, ttl)

    async def ttl(self, key: str) -> int:
        """Get remaining TTL of a key in seconds."""
        return await self.client.ttl(key)

    # --- Pattern Operations ---

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Redis glob pattern (e.g., "bluehub:user:*")

        Returns:
            Number of deleted keys.
        """
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = await self.client.scan(
                cursor=cursor, match=pattern, count=100
            )
            if keys:
                deleted += await self.client.delete(*keys)
            if cursor == 0:
                break
        return deleted

    # --- Caching Decorator ---

    def cached(
        self,
        key_prefix: str,
        ttl: int | timedelta | None = None,
        key_builder: Callable[..., str] | None = None,
    ):
        """
        Decorator that caches function return values.

        Args:
            key_prefix: Prefix for cache key
            ttl: Cache TTL
            key_builder: Optional function to build cache key from args

        Example:
            @cache_service.cached("user", ttl=60)
            async def get_user(user_id: int):
                return await fetch_user_from_db(user_id)
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    parts = [str(a) for a in args] + [
                        f"{k}:{v}" for k, v in sorted(kwargs.items())
                    ]
                    cache_key = build_cache_key(key_prefix, *parts)

                cached_value = await self.get(cache_key)
                if cached_value is not None:
                    return cached_value

                result = await func(*args, **kwargs)
                await self.set(cache_key, result, ttl=ttl)
                return result

            return wrapper

        return decorator

    # --- Counter Operations ---

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter."""
        return await self.client.incrby(key, amount)

    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement a counter."""
        return await self.client.decrby(key, amount)

    # --- Set Operations ---

    async def sadd(self, key: str, *members: Any) -> int:
        """Add members to a set."""
        return await self.client.sadd(key, *members)

    async def smembers(self, key: str) -> set[str]:
        """Get all members of a set."""
        return await self.client.smembers(key)

    async def srem(self, key: str, *members: Any) -> int:
        """Remove members from a set."""
        return await self.client.srem(key, *members)


# Global cache service instance
cache_service = CacheService()

__all__ = [
    "CacheService",
    "build_cache_key",
    "cache_service",
]
