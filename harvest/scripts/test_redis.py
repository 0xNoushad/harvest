#!/usr/bin/env python3
"""
Test Redis Cloud connection and functionality.

Usage:
    python scripts/test_redis.py
    
Or with custom URL:
    python scripts/test_redis.py --redis-url redis://...
"""

import asyncio
import sys
import os
import argparse
from datetime import datetime


async def test_redis_connection(redis_url: str):
    """Test Redis connection and basic operations."""
    
    print("🔴 Testing Redis Cloud Connection")
    print("=" * 60)
    print(f"URL: {redis_url[:30]}...")
    print()
    
    try:
        # Import redis
        try:
            import redis.asyncio as redis
        except ImportError:
            print("❌ redis package not installed")
            print("   Install: pip install redis")
            return False
        
        # Connect
        print("1️⃣  Connecting to Redis...")
        client = await redis.from_url(redis_url, decode_responses=True)
        
        # Ping
        print("2️⃣  Testing connection (PING)...")
        pong = await client.ping()
        if pong:
            print("   ✅ PONG received")
        else:
            print("   ❌ No response")
            return False
        
        # Set value
        print("3️⃣  Testing SET operation...")
        await client.set("test_key", "hello_from_harvest")
        print("   ✅ Value set")
        
        # Get value
        print("4️⃣  Testing GET operation...")
        value = await client.get("test_key")
        if value == "hello_from_harvest":
            print(f"   ✅ Value retrieved: {value}")
        else:
            print(f"   ❌ Wrong value: {value}")
            return False
        
        # Set with TTL
        print("5️⃣  Testing TTL (expiration)...")
        await client.setex("test_ttl", 60, "expires_in_60s")
        ttl = await client.ttl("test_ttl")
        print(f"   ✅ TTL set: {ttl}s")
        
        # Increment
        print("6️⃣  Testing INCR operation...")
        await client.set("test_counter", 0)
        count = await client.incr("test_counter")
        print(f"   ✅ Counter incremented: {count}")
        
        # Hash operations
        print("7️⃣  Testing HASH operations...")
        await client.hset("test_hash", "field1", "value1")
        await client.hset("test_hash", "field2", "value2")
        hash_value = await client.hget("test_hash", "field1")
        print(f"   ✅ Hash value: {hash_value}")
        
        # Get info
        print("8️⃣  Getting Redis info...")
        info = await client.info("memory")
        used_memory = info.get("used_memory_human", "unknown")
        max_memory = info.get("maxmemory_human", "unknown")
        print(f"   Memory used: {used_memory}")
        print(f"   Memory limit: {max_memory}")
        
        # Get key count
        print("9️⃣  Counting keys...")
        dbsize = await client.dbsize()
        print(f"   Total keys: {dbsize}")
        
        # Clean up test keys
        print("🔟 Cleaning up test keys...")
        await client.delete("test_key", "test_ttl", "test_counter", "test_hash")
        print("   ✅ Test keys deleted")
        
        # Close connection
        await client.close()
        
        print()
        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        print()
        print("Your Redis is ready to use! 🚀")
        print()
        print("Next steps:")
        print("1. Add REDIS_URL to Railway environment variables")
        print("2. Deploy your app")
        print("3. Check logs for 'Connected to Redis'")
        print()
        
        return True
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ Test failed!")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        print("Troubleshooting:")
        print("1. Check Redis URL is correct")
        print("2. Check password is correct (no spaces)")
        print("3. Check Redis is accessible from your network")
        print("4. Try connecting with redis-cli first")
        print()
        return False


async def test_harvest_redis_cache(redis_url: str):
    """Test Harvest's Redis cache implementation."""
    
    print()
    print("🌾 Testing Harvest Redis Cache")
    print("=" * 60)
    
    try:
        # Import Harvest's Redis cache
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from agent.distributed.redis_cache import RedisCache
        
        # Create cache
        print("1️⃣  Creating RedisCache...")
        cache = RedisCache(redis_url, default_ttl=60)
        await cache.connect()
        print("   ✅ Connected")
        
        # Test price cache
        print("2️⃣  Testing price cache...")
        await cache.set_price("SOL", 150.50, ttl=60)
        price = await cache.get_price("SOL")
        if price == 150.50:
            print(f"   ✅ Price cached: SOL = ${price}")
        else:
            print(f"   ❌ Wrong price: {price}")
            return False
        
        # Test strategy cache
        print("3️⃣  Testing strategy cache...")
        await cache.set_strategy_data("jupiter_swap", "apy", 12.5, ttl=30)
        apy = await cache.get_strategy_data("jupiter_swap", "apy")
        if apy == 12.5:
            print(f"   ✅ Strategy data cached: APY = {apy}%")
        else:
            print(f"   ❌ Wrong APY: {apy}")
            return False
        
        # Test API usage tracking
        print("4️⃣  Testing API usage tracking...")
        count = await cache.increment_api_usage("test_key", 1)
        print(f"   ✅ API usage tracked: {count} calls")
        
        # Test distributed lock
        print("5️⃣  Testing distributed lock...")
        locked = await cache.acquire_lock("test_lock", timeout=10)
        if locked:
            print("   ✅ Lock acquired")
            await cache.release_lock("test_lock")
            print("   ✅ Lock released")
        else:
            print("   ❌ Failed to acquire lock")
            return False
        
        # Test worker heartbeat
        print("6️⃣  Testing worker heartbeat...")
        await cache.set_worker_heartbeat("test_worker")
        workers = await cache.get_active_workers()
        if "test_worker" in workers:
            print(f"   ✅ Worker heartbeat: {workers}")
        else:
            print(f"   ❌ Worker not found: {workers}")
            return False
        
        # Clean up
        print("7️⃣  Cleaning up...")
        await cache.delete("price:SOL")
        await cache.delete("strategy:jupiter_swap:apy")
        await cache.disconnect()
        print("   ✅ Cleaned up")
        
        print()
        print("=" * 60)
        print("✅ Harvest Redis cache works perfectly!")
        print("=" * 60)
        print()
        
        return True
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ Harvest cache test failed!")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        return False


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test Redis Cloud connection")
    parser.add_argument(
        '--redis-url',
        default=os.getenv('REDIS_URL'),
        help='Redis URL (default: from REDIS_URL env var)'
    )
    parser.add_argument(
        '--skip-harvest',
        action='store_true',
        help='Skip Harvest-specific tests'
    )
    
    args = parser.parse_args()
    
    if not args.redis_url:
        print("❌ Error: REDIS_URL not set")
        print()
        print("Usage:")
        print("  export REDIS_URL='redis://default:PASSWORD@HOST:PORT'")
        print("  python scripts/test_redis.py")
        print()
        print("Or:")
        print("  python scripts/test_redis.py --redis-url 'redis://...'")
        print()
        sys.exit(1)
    
    # Test basic connection
    success = await test_redis_connection(args.redis_url)
    
    if not success:
        sys.exit(1)
    
    # Test Harvest cache
    if not args.skip_harvest:
        success = await test_harvest_redis_cache(args.redis_url)
        if not success:
            sys.exit(1)
    
    print("🎉 All tests passed! Redis is ready for production.")


if __name__ == "__main__":
    asyncio.run(main())
