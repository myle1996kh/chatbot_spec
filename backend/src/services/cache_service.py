"""Redis caching service with tenant namespace isolation."""
import json
from typing import Any, Optional
from redis import asyncio as aioredis
from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CacheService:
    """Redis caching service with tenant-based namespacing."""

    def __init__(self):
        """Initialize cache service."""
        self._redis_client: Optional[aioredis.Redis] = None

    async def _get_redis(self) -> aioredis.Redis:
        """Get or create Redis client."""
        if not self._redis_client:
            self._redis_client = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis_client

    def _build_key(self, tenant_id: str, key: str) -> str:
        """
        Build cache key with tenant namespace.

        Args:
            tenant_id: Tenant UUID
            key: Cache key

        Returns:
            Namespaced key: agenthub:{tenant_id}:cache:{key}
        """
        return f"agenthub:{tenant_id}:cache:{key}"

    async def get(self, tenant_id: str, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            tenant_id: Tenant UUID
            key: Cache key

        Returns:
            Cached value (deserialized from JSON) or None if not found
        """
        redis = await self._get_redis()
        cache_key = self._build_key(tenant_id, key)

        try:
            value = await redis.get(cache_key)
            if value:
                logger.debug("cache_hit", tenant_id=tenant_id, key=key)
                return json.loads(value)
            else:
                logger.debug("cache_miss", tenant_id=tenant_id, key=key)
                return None
        except Exception as e:
            logger.error("cache_get_error", tenant_id=tenant_id, key=key, error=str(e))
            return None

    async def set(
        self,
        tenant_id: str,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.

        Args:
            tenant_id: Tenant UUID
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (default: settings.CACHE_TTL_SECONDS)

        Returns:
            True if successful, False otherwise
        """
        redis = await self._get_redis()
        cache_key = self._build_key(tenant_id, key)
        ttl = ttl or settings.CACHE_TTL_SECONDS

        try:
            serialized_value = json.dumps(value)
            await redis.setex(cache_key, ttl, serialized_value)
            logger.debug("cache_set", tenant_id=tenant_id, key=key, ttl=ttl)
            return True
        except Exception as e:
            logger.error("cache_set_error", tenant_id=tenant_id, key=key, error=str(e))
            return False

    async def delete(self, tenant_id: str, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            tenant_id: Tenant UUID
            key: Cache key

        Returns:
            True if deleted, False otherwise
        """
        redis = await self._get_redis()
        cache_key = self._build_key(tenant_id, key)

        try:
            deleted = await redis.delete(cache_key)
            logger.debug("cache_delete", tenant_id=tenant_id, key=key, deleted=bool(deleted))
            return bool(deleted)
        except Exception as e:
            logger.error("cache_delete_error", tenant_id=tenant_id, key=key, error=str(e))
            return False

    async def clear_tenant(self, tenant_id: str) -> int:
        """
        Clear all cache entries for a tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Number of keys deleted
        """
        redis = await self._get_redis()
        pattern = self._build_key(tenant_id, "*")

        try:
            keys = await redis.keys(pattern)
            if keys:
                deleted = await redis.delete(*keys)
                logger.info("cache_cleared", tenant_id=tenant_id, keys_deleted=deleted)
                return deleted
            return 0
        except Exception as e:
            logger.error("cache_clear_error", tenant_id=tenant_id, error=str(e))
            return 0

    async def get_agent_config(self, tenant_id: str, agent_id: str) -> Optional[dict]:
        """
        Get agent configuration from cache.

        Args:
            tenant_id: Tenant UUID
            agent_id: Agent UUID

        Returns:
            Agent configuration dict or None
        """
        return await self.get(tenant_id, f"agent:{agent_id}")

    async def set_agent_config(self, tenant_id: str, agent_id: str, config: dict) -> bool:
        """
        Set agent configuration in cache.

        Args:
            tenant_id: Tenant UUID
            agent_id: Agent UUID
            config: Agent configuration dict

        Returns:
            True if successful
        """
        return await self.set(tenant_id, f"agent:{agent_id}", config)

    async def get_tool_config(self, tenant_id: str, tool_id: str) -> Optional[dict]:
        """
        Get tool configuration from cache.

        Args:
            tenant_id: Tenant UUID
            tool_id: Tool UUID

        Returns:
            Tool configuration dict or None
        """
        return await self.get(tenant_id, f"tool:{tool_id}")

    async def set_tool_config(self, tenant_id: str, tool_id: str, config: dict) -> bool:
        """
        Set tool configuration in cache.

        Args:
            tenant_id: Tenant UUID
            tool_id: Tool UUID
            config: Tool configuration dict

        Returns:
            True if successful
        """
        return await self.set(tenant_id, f"tool:{tool_id}", config)

    async def close(self):
        """Close Redis connection."""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None


# Global cache service instance
cache_service = CacheService()
