"""Optional Redis: per-client rate limiting + response caching.

Both features degrade gracefully to no-ops when REDIS_URL is unset, so the API
runs without Redis in dev/CI and gains rate limiting + caching in deployment.
"""

from __future__ import annotations

from typing import Any, cast

import redis.asyncio as aioredis

from app.config import settings


class RedisCache:
    def __init__(self, url: str | None = None) -> None:
        self._url = url if url is not None else settings.redis_url
        self.client: aioredis.Redis | None = None

    @property
    def enabled(self) -> bool:
        return bool(self._url)

    async def connect(self) -> None:
        if self.enabled:
            self.client = aioredis.from_url(self._url, decode_responses=True)

    async def close(self) -> None:
        if self.client is not None:
            await self.client.aclose()

    async def hit_rate_limit(self, key: str, limit: int, window_s: int = 60) -> bool:
        """Fixed-window counter. Returns True if the caller is over the limit."""
        if self.client is None:
            return False
        count = await self.client.incr(key)
        if count == 1:
            await self.client.expire(key, window_s)
        return count > limit

    async def get(self, key: str) -> str | None:
        if self.client is None:
            return None
        # decode_responses=True → str, but the stub widens to bytes|str|None.
        return cast("str | None", await self.client.get(key))

    async def set(self, key: str, value: str, ttl_s: int) -> None:
        if self.client is not None:
            await self.client.set(key, value, ex=ttl_s)


cache = RedisCache()


async def enforce_rate_limit(client_id: str) -> bool:
    """True if the request should be rejected (429)."""
    return await cache.hit_rate_limit(
        f"ratelimit:{client_id}", settings.rate_limit_per_min, window_s=60
    )


async def cached_json(key: str) -> Any | None:
    import json

    raw = await cache.get(key)
    return json.loads(raw) if raw else None


async def store_json(key: str, value: Any) -> None:
    import json

    await cache.set(key, json.dumps(value), ttl_s=settings.cache_ttl_seconds)
