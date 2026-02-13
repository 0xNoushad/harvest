"""
Tests for SharedPriceCache component.

Feature: multi-api-scaling-optimization
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch
from agent.core.shared_cache import (
    SharedPriceCache,
    CachedData,
    CacheStats
)


class TestCachedData:
    """Tests for CachedData model."""
    
    def test_cached_data_not_expired(self):
        """Test that fresh cached data is not expired."""
        data = CachedData(
            data=100.5,
            timestamp=time.time(),
            ttl=60
        )
        assert not data.is_expired()
    
    def test_cached_data_expired(self):
        """Test that old cached data is expired."""
        data = CachedData(
            data=100.5,
            timestamp=time.time() - 120,  # 2 minutes ago
            ttl=60  # 60 second TTL
        )
        assert data.is_expired()


class TestCacheStats:
    """Tests for CacheStats model."""
    
    def test_hit_rate_zero_requests(self):
        """Test hit rate is 0% with no requests."""
        stats = CacheStats()
        assert stats.hit_rate() == 0.0
    
    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        stats = CacheStats(
            total_requests=100,
            cache_hits=80,
            cache_misses=20
        )
        assert stats.hit_rate() == 80.0
    
    def test_hit_rate_perfect(self):
        """Test 100% hit rate."""
        stats = CacheStats(
            total_requests=50,
            cache_hits=50,
            cache_misses=0
        )
        assert stats.hit_rate() == 100.0


class TestSharedPriceCache:
    """Tests for SharedPriceCache."""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test cache initializes with correct defaults."""
        cache = SharedPriceCache()
        assert cache.ttl == 60
        assert cache.stats.total_requests == 0
        assert len(cache.cache) == 0
    
    @pytest.mark.asyncio
    async def test_initialization_custom_ttl(self):
        """Test cache initializes with custom TTL."""
        cache = SharedPriceCache(ttl=120)
        assert cache.ttl == 120
    
    @pytest.mark.asyncio
    async def test_cache_miss_on_empty(self):
        """Test cache miss when token not in cache."""
        cache = SharedPriceCache()
        price = await cache.get_price("SOL")
        
        assert price is None
        assert cache.stats.total_requests == 1
        assert cache.stats.cache_misses == 1
        assert cache.stats.cache_hits == 0
    
    @pytest.mark.asyncio
    async def test_set_and_get_price(self):
        """Test setting and getting a price."""
        cache = SharedPriceCache()
        
        # Set price
        await cache.set_price("SOL", 150.5)
        
        # Get price
        price = await cache.get_price("SOL")
        
        assert price == 150.5
        assert cache.stats.cache_hits == 1
        assert cache.stats.api_calls_saved == 1
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """Test that expired cache entries return None."""
        cache = SharedPriceCache(ttl=1)  # 1 second TTL
        
        # Set price
        await cache.set_price("SOL", 150.5)
        
        # Get immediately - should hit
        price1 = await cache.get_price("SOL")
        assert price1 == 150.5
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Get after expiration - should miss
        price2 = await cache.get_price("SOL")
        assert price2 is None
        assert cache.stats.cache_misses == 1

    
    @pytest.mark.asyncio
    async def test_get_prices_multiple(self):
        """Test getting multiple prices at once."""
        cache = SharedPriceCache()
        
        # Set multiple prices
        await cache.set_price("SOL", 150.5)
        await cache.set_price("USDC", 1.0)
        await cache.set_price("BTC", 45000.0)
        
        # Get multiple prices
        prices = await cache.get_prices(["SOL", "USDC", "BTC"])
        
        assert prices == {
            "SOL": 150.5,
            "USDC": 1.0,
            "BTC": 45000.0
        }
    
    @pytest.mark.asyncio
    async def test_get_prices_partial_cache(self):
        """Test getting prices when only some are cached."""
        cache = SharedPriceCache()
        
        # Set only some prices
        await cache.set_price("SOL", 150.5)
        await cache.set_price("USDC", 1.0)
        
        # Request more tokens than cached
        prices = await cache.get_prices(["SOL", "USDC", "BTC"])
        
        # Should only return cached tokens
        assert prices == {
            "SOL": 150.5,
            "USDC": 1.0
        }
        assert "BTC" not in prices
    
    @pytest.mark.asyncio
    async def test_set_prices_bulk(self):
        """Test setting multiple prices at once."""
        cache = SharedPriceCache()
        
        prices_to_set = {
            "SOL": 150.5,
            "USDC": 1.0,
            "BTC": 45000.0
        }
        
        await cache.set_prices(prices_to_set)
        
        # Verify all were cached
        for token, expected_price in prices_to_set.items():
            price = await cache.get_price(token)
            assert price == expected_price
    
    @pytest.mark.asyncio
    async def test_refresh_prices(self):
        """Test refreshing prices with fetch function."""
        cache = SharedPriceCache()
        
        # Mock fetch function
        async def mock_fetch(tokens):
            return {
                "SOL": 150.5,
                "USDC": 1.0
            }
        
        # Refresh prices
        prices = await cache.refresh_prices(["SOL", "USDC"], mock_fetch)
        
        assert prices == {"SOL": 150.5, "USDC": 1.0}
        
        # Verify cached
        cached_price = await cache.get_price("SOL")
        assert cached_price == 150.5
    
    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting cache statistics."""
        cache = SharedPriceCache(ttl=60)
        
        # Perform some operations
        await cache.set_price("SOL", 150.5)
        await cache.get_price("SOL")  # Hit
        await cache.get_price("BTC")  # Miss
        
        stats = cache.get_stats()
        
        assert stats["total_requests"] == 2
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1
        assert stats["hit_rate_percent"] == 50.0
        assert stats["api_calls_saved"] == 1
        assert stats["cached_tokens"] == 1
        assert stats["ttl_seconds"] == 60
    
    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """Test clearing all cached data."""
        cache = SharedPriceCache()
        
        # Add some data
        await cache.set_price("SOL", 150.5)
        await cache.set_price("USDC", 1.0)
        
        assert len(cache.cache) == 2
        
        # Clear cache
        cache.clear()
        
        assert len(cache.cache) == 0
    
    @pytest.mark.asyncio
    async def test_evict_expired(self):
        """Test evicting expired entries."""
        cache = SharedPriceCache(ttl=1)
        
        # Add some data
        await cache.set_price("SOL", 150.5)
        await cache.set_price("USDC", 1.0)
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Add fresh data
        await cache.set_price("BTC", 45000.0)
        
        # Evict expired
        evicted = cache.evict_expired()
        
        assert evicted == 2  # SOL and USDC expired
        assert len(cache.cache) == 1  # Only BTC remains
        assert "BTC" in cache.cache
    
    @pytest.mark.asyncio
    async def test_cache_sharing_across_requests(self):
        """Test that cached data is shared across multiple requests."""
        cache = SharedPriceCache()
        
        # First request sets the price
        await cache.set_price("SOL", 150.5)
        
        # Multiple subsequent requests should get cached value
        price1 = await cache.get_price("SOL")
        price2 = await cache.get_price("SOL")
        price3 = await cache.get_price("SOL")
        
        assert price1 == price2 == price3 == 150.5
        assert cache.stats.cache_hits == 3
        assert cache.stats.api_calls_saved == 3



class TestStrategyCache:
    """Tests for StrategyCache."""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test strategy cache initializes with correct defaults."""
        from agent.core.shared_cache import StrategyCache
        
        cache = StrategyCache()
        assert cache.ttl == 30
        assert len(cache.cache) == 0
        assert len(cache.stats) == 0
    
    @pytest.mark.asyncio
    async def test_initialization_custom_ttl(self):
        """Test strategy cache initializes with custom TTL."""
        from agent.core.shared_cache import StrategyCache
        
        cache = StrategyCache(ttl=60)
        assert cache.ttl == 60
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self):
        """Test cache key generation excludes user-specific data."""
        from agent.core.shared_cache import StrategyCache
        
        cache = StrategyCache()
        
        # Same strategy and market conditions should generate same key
        context1 = {
            "user_id": "user_1",
            "wallet_address": "wallet_1",
            "market_conditions": {"volatility": "high"},
            "price_data": {"SOL": 150.5}
        }
        
        context2 = {
            "user_id": "user_2",
            "wallet_address": "wallet_2",
            "market_conditions": {"volatility": "high"},
            "price_data": {"SOL": 150.5}
        }
        
        key1 = cache._generate_cache_key("yield_farmer", context1)
        key2 = cache._generate_cache_key("yield_farmer", context2)
        
        # Keys should be identical (user-specific data excluded)
        assert key1 == key2
    
    @pytest.mark.asyncio
    async def test_cache_key_different_contexts(self):
        """Test cache key generation differs for different contexts."""
        from agent.core.shared_cache import StrategyCache
        
        cache = StrategyCache()
        
        context1 = {
            "market_conditions": {"volatility": "high"},
            "price_data": {"SOL": 150.5}
        }
        
        context2 = {
            "market_conditions": {"volatility": "low"},
            "price_data": {"SOL": 150.5}
        }
        
        key1 = cache._generate_cache_key("yield_farmer", context1)
        key2 = cache._generate_cache_key("yield_farmer", context2)
        
        # Keys should be different (different market conditions)
        assert key1 != key2
    
    @pytest.mark.asyncio
    async def test_cache_miss_on_empty(self):
        """Test cache miss when strategy result not in cache."""
        from agent.core.shared_cache import StrategyCache
        
        cache = StrategyCache()
        context = {"market_conditions": {"volatility": "high"}}
        
        result = await cache.get_strategy_result("yield_farmer", context)
        
        assert result is None
        assert cache.stats["yield_farmer"].total_requests == 1
        assert cache.stats["yield_farmer"].cache_misses == 1
        assert cache.stats["yield_farmer"].cache_hits == 0
    
    @pytest.mark.asyncio
    async def test_set_and_get_strategy_result(self):
        """Test setting and getting a strategy result."""
        from agent.core.shared_cache import StrategyCache
        
        cache = StrategyCache()
        context = {"market_conditions": {"volatility": "high"}}
        strategy_result = {"opportunities": [{"pool": "SOL-USDC", "apy": 15.5}]}
        
        # Set result
        await cache.set_strategy_result("yield_farmer", context, strategy_result)
        
        # Get result
        result = await cache.get_strategy_result("yield_farmer", context)
        
        assert result == strategy_result
        assert cache.stats["yield_farmer"].cache_hits == 1
        assert cache.stats["yield_farmer"].api_calls_saved == 1
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """Test that expired cache entries return None."""
        from agent.core.shared_cache import StrategyCache
        
        cache = StrategyCache(ttl=1)  # 1 second TTL
        context = {"market_conditions": {"volatility": "high"}}
        strategy_result = {"opportunities": []}
        
        # Set result
        await cache.set_strategy_result("yield_farmer", context, strategy_result)
        
        # Get immediately - should hit
        result1 = await cache.get_strategy_result("yield_farmer", context)
        assert result1 == strategy_result
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Get after expiration - should miss
        result2 = await cache.get_strategy_result("yield_farmer", context)
        assert result2 is None
        assert cache.stats["yield_farmer"].cache_misses == 1
    
    @pytest.mark.asyncio
    async def test_execute_and_cache(self):
        """Test execute_and_cache method."""
        from agent.core.shared_cache import StrategyCache
        
        cache = StrategyCache()
        context = {"market_conditions": {"volatility": "high"}}
        expected_result = {"opportunities": [{"pool": "SOL-USDC", "apy": 15.5}]}
        
        # Mock strategy function
        async def mock_strategy(ctx):
            return expected_result
        
        # First call - should execute and cache
        result1 = await cache.execute_and_cache("yield_farmer", mock_strategy, context)
        assert result1 == expected_result
        
        # Second call - should return cached result
        result2 = await cache.execute_and_cache("yield_farmer", mock_strategy, context)
        assert result2 == expected_result
        
        # Verify cache was used
        assert cache.stats["yield_farmer"].cache_hits == 1
        assert cache.stats["yield_farmer"].cache_misses == 1
    
    @pytest.mark.asyncio
    async def test_get_stats_specific_strategy(self):
        """Test getting stats for a specific strategy."""
        from agent.core.shared_cache import StrategyCache
        
        cache = StrategyCache()
        context = {"market_conditions": {"volatility": "high"}}
        
        # Perform some operations
        await cache.set_strategy_result("yield_farmer", context, {"opportunities": []})
        await cache.get_strategy_result("yield_farmer", context)  # Hit
        await cache.get_strategy_result("yield_farmer", {"market_conditions": {"volatility": "low"}})  # Miss
        
        stats = cache.get_stats("yield_farmer")
        
        assert stats["strategy"] == "yield_farmer"
        assert stats["total_requests"] == 2
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1
        assert stats["hit_rate_percent"] == 50.0
        assert stats["api_calls_saved"] == 1
    
    @pytest.mark.asyncio
    async def test_get_stats_all_strategies(self):
        """Test getting aggregated stats for all strategies."""
        from agent.core.shared_cache import StrategyCache
        
        cache = StrategyCache()
        context = {"market_conditions": {"volatility": "high"}}
        
        # Perform operations on multiple strategies
        await cache.set_strategy_result("yield_farmer", context, {"opportunities": []})
        await cache.get_strategy_result("yield_farmer", context)  # Hit
        
        await cache.set_strategy_result("airdrop_hunter", context, {"airdrops": []})
        await cache.get_strategy_result("airdrop_hunter", context)  # Hit
        
        stats = cache.get_stats()
        
        assert stats["total_requests"] == 2
        assert stats["cache_hits"] == 2
        assert stats["cache_misses"] == 0
        assert stats["hit_rate_percent"] == 100.0
        assert stats["api_calls_saved"] == 2
        assert "yield_farmer" in stats["strategies"]
        assert "airdrop_hunter" in stats["strategies"]
    
    @pytest.mark.asyncio
    async def test_get_stats_nonexistent_strategy(self):
        """Test getting stats for a strategy that hasn't been used."""
        from agent.core.shared_cache import StrategyCache
        
        cache = StrategyCache()
        
        stats = cache.get_stats("nonexistent_strategy")
        
        assert stats["strategy"] == "nonexistent_strategy"
        assert stats["total_requests"] == 0
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["hit_rate_percent"] == 0.0
    
    @pytest.mark.asyncio
    async def test_clear_all_cache(self):
        """Test clearing all cached data."""
        from agent.core.shared_cache import StrategyCache
        
        cache = StrategyCache()
        context = {"market_conditions": {"volatility": "high"}}
        
        # Add some data
        await cache.set_strategy_result("yield_farmer", context, {"opportunities": []})
        await cache.set_strategy_result("airdrop_hunter", context, {"airdrops": []})
        
        assert len(cache.cache) == 2
        
        # Clear cache
        cache.clear()
        
        assert len(cache.cache) == 0
    
    @pytest.mark.asyncio
    async def test_clear_specific_strategy(self):
        """Test clearing cache for a specific strategy."""
        from agent.core.shared_cache import StrategyCache
        
        cache = StrategyCache()
        context = {"market_conditions": {"volatility": "high"}}
        
        # Add data for multiple strategies
        await cache.set_strategy_result("yield_farmer", context, {"opportunities": []})
        await cache.set_strategy_result("airdrop_hunter", context, {"airdrops": []})
        
        assert len(cache.cache) == 2
        
        # Clear only yield_farmer
        cache.clear("yield_farmer")
        
        # Should have 1 entry left (airdrop_hunter)
        assert len(cache.cache) == 1
        
        # Verify yield_farmer is gone
        result = await cache.get_strategy_result("yield_farmer", context)
        assert result is None
        
        # Verify airdrop_hunter still cached
        result = await cache.get_strategy_result("airdrop_hunter", context)
        assert result == {"airdrops": []}
    
    @pytest.mark.asyncio
    async def test_evict_expired(self):
        """Test evicting expired entries."""
        from agent.core.shared_cache import StrategyCache
        
        cache = StrategyCache(ttl=1)
        context = {"market_conditions": {"volatility": "high"}}
        
        # Add some data
        await cache.set_strategy_result("yield_farmer", context, {"opportunities": []})
        await cache.set_strategy_result("airdrop_hunter", context, {"airdrops": []})
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Add fresh data
        await cache.set_strategy_result("nft_flipper", context, {"nfts": []})
        
        # Evict expired
        evicted = cache.evict_expired()
        
        assert evicted == 2  # yield_farmer and airdrop_hunter expired
        assert len(cache.cache) == 1  # Only nft_flipper remains
    
    @pytest.mark.asyncio
    async def test_cache_sharing_across_users(self):
        """Test that strategy results are shared across multiple users."""
        from agent.core.shared_cache import StrategyCache
        
        cache = StrategyCache()
        
        # User 1 context
        context1 = {
            "user_id": "user_1",
            "wallet_address": "wallet_1",
            "market_conditions": {"volatility": "high"},
            "price_data": {"SOL": 150.5}
        }
        
        # User 2 context (different user, same market conditions)
        context2 = {
            "user_id": "user_2",
            "wallet_address": "wallet_2",
            "market_conditions": {"volatility": "high"},
            "price_data": {"SOL": 150.5}
        }
        
        strategy_result = {"opportunities": [{"pool": "SOL-USDC", "apy": 15.5}]}
        
        # User 1 sets result
        await cache.set_strategy_result("yield_farmer", context1, strategy_result)
        
        # User 2 should get cached result
        result = await cache.get_strategy_result("yield_farmer", context2)
        
        assert result == strategy_result
        assert cache.stats["yield_farmer"].cache_hits == 1
        assert cache.stats["yield_farmer"].api_calls_saved == 1
    
    @pytest.mark.asyncio
    async def test_per_strategy_statistics(self):
        """Test that statistics are tracked per strategy."""
        from agent.core.shared_cache import StrategyCache
        
        cache = StrategyCache()
        context = {"market_conditions": {"volatility": "high"}}
        
        # Operations on yield_farmer
        await cache.set_strategy_result("yield_farmer", context, {"opportunities": []})
        await cache.get_strategy_result("yield_farmer", context)  # Hit
        await cache.get_strategy_result("yield_farmer", context)  # Hit
        
        # Operations on airdrop_hunter
        await cache.set_strategy_result("airdrop_hunter", context, {"airdrops": []})
        await cache.get_strategy_result("airdrop_hunter", context)  # Hit
        
        # Check yield_farmer stats
        yf_stats = cache.get_stats("yield_farmer")
        assert yf_stats["total_requests"] == 2
        assert yf_stats["cache_hits"] == 2
        
        # Check airdrop_hunter stats
        ah_stats = cache.get_stats("airdrop_hunter")
        assert ah_stats["total_requests"] == 1
        assert ah_stats["cache_hits"] == 1
