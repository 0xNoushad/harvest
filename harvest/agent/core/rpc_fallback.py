"""
RPC Fallback Manager

Provides automatic fallback between multiple RPC providers to handle:
- Rate limiting
- Downtime
- Free tier exhaustion

Supports: Helius (primary), Public Solana RPC (fallback), QuickNode (optional)
"""

import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import asyncio
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class RPCProvider:
    """RPC provider configuration."""
    name: str
    url: str
    priority: int  # Lower = higher priority
    max_retries: int = 3
    timeout: int = 10
    is_available: bool = True
    failure_count: int = 0


class RPCFallbackManager:
    """
    Manages multiple RPC providers with automatic fallback.
    
    Features:
    - Automatic failover on rate limits or errors
    - Health checking and circuit breaker pattern
    - Load balancing across providers
    - Optional integration with API Key Manager for user-specific routing
    """
    
    def __init__(self, api_key_manager=None):
        """
        Initialize RPC fallback manager with multiple providers.
        
        Args:
            api_key_manager: Optional APIKeyManager for user-specific key routing.
                           If provided, enables user-specific routing when user_id
                           is passed to rpc_call(). Maintains backward compatibility
                           when None.
        """
        self.providers: List[RPCProvider] = []
        self._setup_providers()
        self.current_provider_index = 0
        self.max_failures_before_fallback = 3
        self.api_key_manager = api_key_manager
        
        logger.info(
            f"Initialized RPC fallback with {len(self.providers)} providers"
            f"{' (with API Key Manager)' if api_key_manager else ''}"
        )
    
    def _setup_providers(self):
        """Setup RPC providers in priority order."""
        # Primary: Helius (if API key available)
        helius_key = os.getenv("HELIUS_API_KEY")
        if helius_key:
            self.providers.append(RPCProvider(
                name="Helius",
                url=f"https://rpc.helius.xyz/?api-key={helius_key}",
                priority=1,
                max_retries=3
            ))
        
        # Fallback 1: Public Solana RPC (free, rate limited)
        self.providers.append(RPCProvider(
            name="Solana Public",
            url="https://api.mainnet-beta.solana.com",
            priority=2,
            max_retries=2
        ))
        
        # Fallback 2: QuickNode (if API key available)
        quicknode_url = os.getenv("QUICKNODE_RPC_URL")
        if quicknode_url:
            self.providers.append(RPCProvider(
                name="QuickNode",
                url=quicknode_url,
                priority=1,  # Same priority as Helius
                max_retries=3
            ))
        
        # Fallback 3: Alchemy (if API key available)
        alchemy_key = os.getenv("ALCHEMY_API_KEY")
        if alchemy_key:
            self.providers.append(RPCProvider(
                name="Alchemy",
                url=f"https://solana-mainnet.g.alchemy.com/v2/{alchemy_key}",
                priority=1,
                max_retries=3
            ))
        
        # Sort by priority
        self.providers.sort(key=lambda p: p.priority)
        
        if not self.providers:
            raise ValueError("No RPC providers configured!")
    
    def get_current_provider(self) -> RPCProvider:
        """Get the current active provider."""
        # Find first available provider
        for provider in self.providers:
            if provider.is_available:
                return provider
        
        # If all failed, reset and try again
        logger.warning("All providers failed, resetting availability")
        for provider in self.providers:
            provider.is_available = True
            provider.failure_count = 0
        
        return self.providers[0]
    
    async def rpc_call(
        self,
        method: str,
        params: Optional[List[Any]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Make RPC call with automatic fallback.
        
        When both api_key_manager and user_id are provided, attempts to use
        the user's assigned API key first before falling back to the standard
        provider chain. This enables user-specific key routing while maintaining
        backward compatibility.
        
        Args:
            method: RPC method name
            params: Method parameters
            user_id: Optional user identifier for user-specific key routing.
                    Only used when api_key_manager is configured.
        
        Returns:
            RPC response
        
        Raises:
            Exception: If all providers fail
        """
        if params is None:
            params = []
        
        # Try user-specific key routing if both api_key_manager and user_id provided
        if self.api_key_manager and user_id:
            try:
                result = await self._call_with_user_key(method, params, user_id)
                return result
            except Exception as e:
                # Log the failure and fall through to standard fallback chain
                logger.warning(
                    f"User-specific key routing failed for {user_id}: {e}. "
                    f"Falling back to standard provider chain."
                )
        
        # Standard fallback logic (existing behavior)
        last_error = None
        
        # Try each provider
        for attempt in range(len(self.providers)):
            provider = self.get_current_provider()
            
            try:
                result = await self._call_provider(provider, method, params)
                
                # Success - reset failure count
                provider.failure_count = 0
                return result
            
            except Exception as e:
                last_error = e
                provider.failure_count += 1
                
                logger.warning(
                    f"RPC call failed on {provider.name} "
                    f"(attempt {provider.failure_count}/{provider.max_retries}): {e}"
                )
                
                # Mark as unavailable if too many failures
                if provider.failure_count >= provider.max_retries:
                    provider.is_available = False
                    logger.error(f"Marking {provider.name} as unavailable")
                
                # Try next provider
                continue
        
        # All providers failed
        error_msg = f"All RPC providers failed. Last error: {last_error}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    async def _call_with_user_key(
        self,
        method: str,
        params: List[Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Make RPC call using user's assigned API key.
        
        This method implements user-specific key routing when api_key_manager
        is configured. It checks if the user should use fallback, gets the
        user's RPC URL, and makes the call.
        
        Args:
            method: RPC method name
            params: Method parameters
            user_id: User identifier
        
        Returns:
            RPC response
        
        Raises:
            Exception: If the call fails or key is unavailable
        """
        # Check if user should use fallback (key unavailable or all keys down)
        if self.api_key_manager.should_use_fallback(user_id):
            raise Exception(f"User {user_id}'s assigned key unavailable, using fallback")
        
        # Get user's RPC URL
        rpc_url = self.api_key_manager.get_rpc_url_for_user(user_id)
        
        if not rpc_url:
            raise Exception(f"No RPC URL available for user {user_id}")
        
        # Make the call
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    rpc_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    # Check for rate limiting
                    if response.status == 429:
                        # Get user's key index to mark it unavailable
                        assignment = self.api_key_manager.user_assignments.get(user_id)
                        if assignment:
                            self.api_key_manager.handle_rate_limit_error(assignment.key_index)
                        raise Exception(f"Rate limited on user {user_id}'s assigned key")
                    
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status} from user key")
                    
                    data = await response.json()
                    
                    if "error" in data:
                        error_msg = data["error"].get("message", "Unknown error")
                        raise Exception(f"RPC error from user key: {error_msg}")
                    
                    return data.get("result", {})
        
        except aiohttp.ClientError as e:
            raise Exception(f"Network error calling user key: {e}")
    
    async def _call_provider(
        self,
        provider: RPCProvider,
        method: str,
        params: List[Any]
    ) -> Dict[str, Any]:
        """
        Call a specific RPC provider.
        
        Args:
            provider: Provider to call
            method: RPC method
            params: Method parameters
        
        Returns:
            RPC response
        
        Raises:
            Exception: If call fails
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                provider.url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=provider.timeout)
            ) as response:
                if response.status == 429:
                    raise Exception(f"Rate limited on {provider.name}")
                
                if response.status != 200:
                    raise Exception(f"HTTP {response.status} from {provider.name}")
                
                data = await response.json()
                
                if "error" in data:
                    error_msg = data["error"].get("message", "Unknown error")
                    raise Exception(f"RPC error from {provider.name}: {error_msg}")
                
                return data.get("result", {})
    
    async def get_balance(self, pubkey: str) -> float:
        """Get SOL balance with fallback."""
        result = await self.rpc_call("getBalance", [pubkey])
        lamports = result.get("value", 0)
        return lamports / 1e9
    
    async def get_latest_blockhash(self) -> Dict[str, Any]:
        """Get latest blockhash with fallback."""
        result = await self.rpc_call("getLatestBlockhash")
        return result.get("value", {})
    
    async def send_transaction(self, signed_transaction: str) -> str:
        """Send transaction with fallback."""
        return await self.rpc_call("sendTransaction", [signed_transaction])
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers."""
        return {
            "providers": [
                {
                    "name": p.name,
                    "available": p.is_available,
                    "failures": p.failure_count,
                    "priority": p.priority
                }
                for p in self.providers
            ],
            "current": self.get_current_provider().name
        }
