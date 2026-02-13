"""
Distributed Redis cache for sharing data across workers.

Replaces in-memory caches with Redis for multi-worker support.
"""

import json
import logging
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisCache:
    """
    Distributed cache using Redis.
    
    Replaces SharedPriceCache and StrategyCache with distributed versions
    that work across multiple worker processes.
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        default_ttl: int = 60
    ):
        """
        Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds
        """
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.client: Optional[redis.Redis] = None
        
        logger.info(f"RedisCache initialized with TTL: {default_ttl}s")
    
    async def connect(self):
        """Connect to Redis."""
        try:
            self.client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.client:
            await self.client.close()
            logger.info("Disconnected from Redis")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None
        """
        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error getting key {key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (uses default if None)
        """
        try:
            ttl = ttl or self.default_ttl
            await self.client.setex(
                key,
                ttl,
                json.dumps(value)
            )
        except Exception as e:
            logger.error(f"Error setting key {key}: {e}")
    
    async def delete(self, key: str):
        """Delete key from cache."""
        try:
            await self.client.delete(key)
        except Exception as e:
            logger.error(f"Error deleting key {key}: {e}")
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Error checking key {key}: {e}")
            return False
    
    # Price cache methods
    async def get_price(self, token: str) -> Optional[float]:
        """Get cached token price."""
        return await self.get(f"price:{token}")
    
    async def set_price(self, token: str, price: float, ttl: int = 60):
        """Cache token price."""
        await self.set(f"price:{token}", price, ttl)
    
    # Strategy cache methods
    async def get_strategy_data(
        self,
        strategy_name: str,
        data_key: str
    ) -> Optional[Any]:
        """Get cached strategy data."""
        return await self.get(f"strategy:{strategy_name}:{data_key}")
    
    async def set_strategy_data(
        self,
        strategy_name: str,
        data_key: str,
        data: Any,
        ttl: int = 30
    ):
        """Cache strategy data."""
        await self.set(f"strategy:{strategy_name}:{data_key}", data, ttl)
    
    # Rate limiting methods
    async def increment_api_usage(
        self,
        api_key_id: str,
        amount: int = 1
    ) -> int:
        """
        Increment API usage counter.
        
        Args:
            api_key_id: API key identifier
            amount: Amount to increment
        
        Returns:
            New usage count
        """
        try:
            key = f"api_usage:{api_key_id}:{datetime.now().strftime('%Y-%m-%d')}"
            
            # Increment counter
            count = await self.client.incr(key, amount)
            
            # Set expiry to end of day if new key
            if count == amount:
                await self.client.expireat(
                    key,
                    datetime.now().replace(hour=23, minute=59, second=59)
                )
            
            return count
        except Exception as e:
            logger.error(f"Error incrementing API usage: {e}")
            return 0
    
    async def get_api_usage(self, api_key_id: str) -> int:
        """Get current API usage count."""
        try:
            key = f"api_usage:{api_key_id}:{datetime.now().strftime('%Y-%m-%d')}"
            count = await self.client.get(key)
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Error getting API usage: {e}")
            return 0
    
    # Distributed lock methods
    async def acquire_lock(
        self,
        lock_name: str,
        timeout: int = 10
    ) -> bool:
        """
        Acquire distributed lock.
        
        Args:
            lock_name: Lock identifier
            timeout: Lock timeout in seconds
        
        Returns:
            True if lock acquired
        """
        try:
            key = f"lock:{lock_name}"
            acquired = await self.client.set(
                key,
                "locked",
                nx=True,
                ex=timeout
            )
            return acquired is not None
        except Exception as e:
            logger.error(f"Error acquiring lock {lock_name}: {e}")
            return False
    
    async def release_lock(self, lock_name: str):
        """Release distributed lock."""
        try:
            key = f"lock:{lock_name}"
            await self.client.delete(key)
        except Exception as e:
            logger.error(f"Error releasing lock {lock_name}: {e}")
    
    # User assignment methods
    async def assign_user_to_worker(
        self,
        user_id: str,
        worker_id: str
    ):
        """Assign user to worker."""
        await self.set(f"user_assignment:{user_id}", worker_id, ttl=86400)
    
    async def get_user_worker(self, user_id: str) -> Optional[str]:
        """Get worker assigned to user."""
        return await self.get(f"user_assignment:{user_id}")
    
    # Health check methods
    async def set_worker_heartbeat(self, worker_id: str):
        """Update worker heartbeat."""
        await self.set(
            f"worker_heartbeat:{worker_id}",
            datetime.now().isoformat(),
            ttl=60
        )
    
    async def get_active_workers(self) -> list:
        """Get list of active workers."""
        try:
            keys = await self.client.keys("worker_heartbeat:*")
            return [key.split(":")[-1] for key in keys]
        except Exception as e:
            logger.error(f"Error getting active workers: {e}")
            return []


class RedisPriceCache:
    """
    Drop-in replacement for SharedPriceCache using Redis.
    
    Maintains same interface for backward compatibility.
    """
    
    def __init__(self, redis_cache: RedisCache, ttl: int = 60):
        self.redis = redis_cache
        self.ttl = ttl
    
    async def get_price(self, token: str) -> Optional[float]:
        """Get cached price."""
        return await self.redis.get_price(token)
    
    async def set_price(self, token: str, price: float):
        """Cache price."""
        await self.redis.set_price(token, price, self.ttl)
    
    async def invalidate(self, token: str):
        """Invalidate cached price."""
        await self.redis.delete(f"price:{token}")


class RedisStrategyCache:
    """
    Drop-in replacement for StrategyCache using Redis.
    
    Maintains same interface for backward compatibility.
    """
    
    def __init__(self, redis_cache: RedisCache, ttl: int = 30):
        self.redis = redis_cache
        self.ttl = ttl
    
    async def get(self, strategy_name: str, key: str) -> Optional[Any]:
        """Get cached strategy data."""
        return await self.redis.get_strategy_data(strategy_name, key)
    
    async def set(self, strategy_name: str, key: str, value: Any):
        """Cache strategy data."""
        await self.redis.set_strategy_data(strategy_name, key, value, self.ttl)
    
    async def invalidate(self, strategy_name: str, key: str):
        """Invalidate cached data."""
        await self.redis.delete(f"strategy:{strategy_name}:{key}")


if __name__ == "__main__":
    import asyncio
    
    async def test_redis_cache():
        """Test Redis cache functionality."""
        print("\n🧪 Testing Redis Cache\n")
        print("=" * 60)
        
        cache = RedisCache(redis_url="redis://localhost:6379", default_ttl=60)
        
        try:
            await cache.connect()
            print("✅ Connected to Redis")
            
            # Test basic operations
            await cache.set("test_key", {"value": 123})
            value = await cache.get("test_key")
            print(f"✅ Basic set/get: {value}")
            
            # Test price cache
            await cache.set_price("SOL", 150.50)
            price = await cache.get_price("SOL")
            print(f"✅ Price cache: SOL = ${price}")
            
            # Test API usage
            count = await cache.increment_api_usage("key1")
            print(f"✅ API usage tracking: {count}")
            
            # Test distributed lock
            locked = await cache.acquire_lock("test_lock")
            print(f"✅ Distributed lock: {locked}")
            await cache.release_lock("test_lock")
            
            # Test worker heartbeat
            await cache.set_worker_heartbeat("worker_1")
            workers = await cache.get_active_workers()
            print(f"✅ Active workers: {workers}")
            
            await cache.disconnect()
            print("✅ Disconnected from Redis")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    asyncio.run(test_redis_cache())
