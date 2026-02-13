"""
Shared caching components for multi-user optimization.

This module provides shared caching for price data and strategy results
to reduce API calls across multiple users.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List, Callable
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class CachedData:
    """Represents a cached data entry with TTL."""
    data: Any
    timestamp: float
    ttl: int
    
    def is_expired(self) -> bool:
        """Check if cached data has expired."""
        return time.time() - self.timestamp > self.ttl


@dataclass
class CacheStats:
    """Statistics for cache performance tracking."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    api_calls_saved: int = 0
    
    def hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.cache_hits / self.total_requests) * 100


class SharedPriceCache:
    """
    Global price cache shared across all users.
    
    Caches cryptocurrency prices with configurable TTL to reduce
    redundant API calls. Expected to reduce price API calls by 99%+
    for 500 concurrent users.
    """
    
    def __init__(self, ttl: int = 60):
        """
        Initialize shared price cache.
        
        Args:
            ttl: Time-to-live for cached prices in seconds (default 60)
        """
        self.cache: Dict[str, CachedData] = {}
        self.ttl = ttl
        self.stats = CacheStats()
        self._lock = asyncio.Lock()
        logger.info(f"SharedPriceCache initialized with TTL={ttl}s")
    
    async def get_price(self, token: str) -> Optional[float]:
        """
        Get price for a single token.
        
        Returns cached price if available and not expired, otherwise
        returns None (caller should fetch and cache).
        
        Args:
            token: Token symbol (e.g., "SOL", "USDC")
            
        Returns:
            Cached price if available, None otherwise
        """
        async with self._lock:
            self.stats.total_requests += 1
            
            if token in self.cache:
                cached = self.cache[token]
                if not cached.is_expired():
                    self.stats.cache_hits += 1
                    self.stats.api_calls_saved += 1
                    logger.debug(f"Cache HIT for {token}: {cached.data}")
                    return cached.data
                else:
                    # Expired entry
                    logger.debug(f"Cache EXPIRED for {token}")
                    del self.cache[token]
            
            self.stats.cache_misses += 1
            logger.debug(f"Cache MISS for {token}")
            return None
    
    async def get_prices(self, tokens: List[str]) -> Dict[str, float]:
        """
        Get prices for multiple tokens.
        
        Returns cached prices for tokens that are available and not expired.
        Tokens not in cache or expired will not be included in result.
        
        Args:
            tokens: List of token symbols
            
        Returns:
            Dictionary mapping token symbols to prices (only cached tokens)
        """
        result = {}
        
        for token in tokens:
            price = await self.get_price(token)
            if price is not None:
                result[token] = price
        
        return result

    
    async def set_price(self, token: str, price: float) -> None:
        """
        Cache a price for a token.
        
        Args:
            token: Token symbol
            price: Price value to cache
        """
        async with self._lock:
            self.cache[token] = CachedData(
                data=price,
                timestamp=time.time(),
                ttl=self.ttl
            )
            logger.debug(f"Cached price for {token}: {price}")
    
    async def set_prices(self, prices: Dict[str, float]) -> None:
        """
        Cache prices for multiple tokens.
        
        Args:
            prices: Dictionary mapping token symbols to prices
        """
        for token, price in prices.items():
            await self.set_price(token, price)
    
    async def refresh_prices(self, tokens: List[str], fetch_func: Callable) -> Dict[str, float]:
        """
        Refresh prices for tokens by fetching from API.
        
        This is a convenience method that fetches prices and caches them.
        
        Args:
            tokens: List of token symbols to refresh
            fetch_func: Async function that fetches prices, should return Dict[str, float]
            
        Returns:
            Dictionary mapping token symbols to fresh prices
        """
        try:
            prices = await fetch_func(tokens)
            await self.set_prices(prices)
            logger.info(f"Refreshed prices for {len(prices)} tokens")
            return prices
        except Exception as e:
            logger.error(f"Failed to refresh prices: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary containing cache performance metrics
        """
        return {
            "total_requests": self.stats.total_requests,
            "cache_hits": self.stats.cache_hits,
            "cache_misses": self.stats.cache_misses,
            "hit_rate_percent": self.stats.hit_rate(),
            "api_calls_saved": self.stats.api_calls_saved,
            "cached_tokens": len(self.cache),
            "ttl_seconds": self.ttl
        }
    
    def clear(self) -> None:
        """Clear all cached data."""
        self.cache.clear()
        logger.info("Cache cleared")
    
    def evict_expired(self) -> int:
        """
        Remove expired entries from cache.
        
        Returns:
            Number of entries evicted
        """
        expired_keys = [
            token for token, cached in self.cache.items()
            if cached.is_expired()
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.debug(f"Evicted {len(expired_keys)} expired entries")
        
        return len(expired_keys)


class StrategyCache:
    """
    Cache for strategy analysis results shared across users.
    
    Caches strategy execution results with configurable TTL to reduce
    redundant computations. Multiple users running the same strategy
    can share results within the TTL window.
    """
    
    def __init__(self, ttl: int = 30):
        """
        Initialize strategy cache.
        
        Args:
            ttl: Time-to-live for cached results in seconds (default 30)
        """
        self.cache: Dict[str, CachedData] = {}
        self.ttl = ttl
        self.stats: Dict[str, CacheStats] = {}
        self._lock = asyncio.Lock()
        logger.info(f"StrategyCache initialized with TTL={ttl}s")
    
    def _generate_cache_key(self, strategy_name: str, context: Dict[str, Any]) -> str:
        """
        Generate cache key from strategy name and context.
        
        Includes relevant context that affects strategy results while
        excluding user-specific data to enable sharing across users.
        
        Args:
            strategy_name: Name of the strategy
            context: Context dictionary with market data
            
        Returns:
            Cache key string
        """
        import json
        import hashlib
        
        # Extract only relevant context (exclude user-specific data)
        relevant_context = {}
        
        # Include market conditions if present
        if "market_conditions" in context:
            relevant_context["market_conditions"] = context["market_conditions"]
        
        # Include price data if present
        if "price_data" in context:
            relevant_context["price_data"] = context["price_data"]
        
        # Include any other non-user-specific data
        for key in ["timestamp", "network", "protocol_data"]:
            if key in context:
                relevant_context[key] = context[key]
        
        # Create deterministic hash of context
        context_str = json.dumps(relevant_context, sort_keys=True)
        context_hash = hashlib.md5(context_str.encode()).hexdigest()[:8]
        
        return f"{strategy_name}:{context_hash}"
    
    async def get_strategy_result(
        self,
        strategy_name: str,
        context: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Get cached strategy result if available.
        
        Returns cached result if available and not expired, otherwise
        returns None (caller should execute strategy and cache).
        
        Args:
            strategy_name: Name of the strategy
            context: Context dictionary for cache key generation
            
        Returns:
            Cached result if available, None otherwise
        """
        cache_key = self._generate_cache_key(strategy_name, context)
        
        async with self._lock:
            # Initialize stats for this strategy if needed
            if strategy_name not in self.stats:
                self.stats[strategy_name] = CacheStats()
            
            self.stats[strategy_name].total_requests += 1
            
            if cache_key in self.cache:
                cached = self.cache[cache_key]
                if not cached.is_expired():
                    self.stats[strategy_name].cache_hits += 1
                    self.stats[strategy_name].api_calls_saved += 1
                    logger.debug(f"Strategy cache HIT for {strategy_name}")
                    return cached.data
                else:
                    # Expired entry
                    logger.debug(f"Strategy cache EXPIRED for {strategy_name}")
                    del self.cache[cache_key]
            
            self.stats[strategy_name].cache_misses += 1
            logger.debug(f"Strategy cache MISS for {strategy_name}")
            return None
    
    async def set_strategy_result(
        self,
        strategy_name: str,
        context: Dict[str, Any],
        result: Any
    ) -> None:
        """
        Cache a strategy result.
        
        Args:
            strategy_name: Name of the strategy
            context: Context dictionary for cache key generation
            result: Strategy result to cache
        """
        cache_key = self._generate_cache_key(strategy_name, context)
        
        async with self._lock:
            self.cache[cache_key] = CachedData(
                data=result,
                timestamp=time.time(),
                ttl=self.ttl
            )
            logger.debug(f"Cached result for strategy {strategy_name}")
    
    async def execute_and_cache(
        self,
        strategy_name: str,
        strategy_func: Callable,
        context: Dict[str, Any]
    ) -> Any:
        """
        Execute strategy and cache result, or return cached result.
        
        This is a convenience method that checks cache first, and if
        not found, executes the strategy function and caches the result.
        
        Args:
            strategy_name: Name of the strategy
            strategy_func: Async function that executes the strategy
            context: Context dictionary for the strategy
            
        Returns:
            Strategy result (cached or freshly computed)
        """
        # Check cache first
        cached_result = await self.get_strategy_result(strategy_name, context)
        if cached_result is not None:
            return cached_result
        
        # Execute strategy
        try:
            result = await strategy_func(context)
            await self.set_strategy_result(strategy_name, context, result)
            logger.info(f"Executed and cached strategy {strategy_name}")
            return result
        except Exception as e:
            logger.error(f"Failed to execute strategy {strategy_name}: {e}")
            raise
    
    def get_stats(self, strategy_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Args:
            strategy_name: Optional strategy name to get stats for specific strategy.
                          If None, returns stats for all strategies.
        
        Returns:
            Dictionary containing cache performance metrics
        """
        if strategy_name:
            # Return stats for specific strategy
            if strategy_name not in self.stats:
                return {
                    "strategy": strategy_name,
                    "total_requests": 0,
                    "cache_hits": 0,
                    "cache_misses": 0,
                    "hit_rate_percent": 0.0,
                    "api_calls_saved": 0
                }
            
            stats = self.stats[strategy_name]
            return {
                "strategy": strategy_name,
                "total_requests": stats.total_requests,
                "cache_hits": stats.cache_hits,
                "cache_misses": stats.cache_misses,
                "hit_rate_percent": stats.hit_rate(),
                "api_calls_saved": stats.api_calls_saved
            }
        else:
            # Return aggregated stats for all strategies
            total_stats = {
                "total_requests": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "api_calls_saved": 0,
                "strategies": {}
            }
            
            for name, stats in self.stats.items():
                total_stats["total_requests"] += stats.total_requests
                total_stats["cache_hits"] += stats.cache_hits
                total_stats["cache_misses"] += stats.cache_misses
                total_stats["api_calls_saved"] += stats.api_calls_saved
                
                total_stats["strategies"][name] = {
                    "total_requests": stats.total_requests,
                    "cache_hits": stats.cache_hits,
                    "cache_misses": stats.cache_misses,
                    "hit_rate_percent": stats.hit_rate(),
                    "api_calls_saved": stats.api_calls_saved
                }
            
            # Calculate overall hit rate
            if total_stats["total_requests"] > 0:
                total_stats["hit_rate_percent"] = (
                    total_stats["cache_hits"] / total_stats["total_requests"]
                ) * 100
            else:
                total_stats["hit_rate_percent"] = 0.0
            
            total_stats["cached_entries"] = len(self.cache)
            total_stats["ttl_seconds"] = self.ttl
            
            return total_stats
    
    def clear(self, strategy_name: Optional[str] = None) -> None:
        """
        Clear cached data.
        
        Args:
            strategy_name: Optional strategy name to clear only that strategy's cache.
                          If None, clears all cached data.
        """
        if strategy_name:
            # Clear only entries for specific strategy
            keys_to_remove = [
                key for key in self.cache.keys()
                if key.startswith(f"{strategy_name}:")
            ]
            for key in keys_to_remove:
                del self.cache[key]
            logger.info(f"Cleared cache for strategy {strategy_name}")
        else:
            # Clear all
            self.cache.clear()
            logger.info("Strategy cache cleared")
    
    def evict_expired(self) -> int:
        """
        Remove expired entries from cache.
        
        Returns:
            Number of entries evicted
        """
        expired_keys = [
            key for key, cached in self.cache.items()
            if cached.is_expired()
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.debug(f"Evicted {len(expired_keys)} expired strategy cache entries")
        
        return len(expired_keys)
