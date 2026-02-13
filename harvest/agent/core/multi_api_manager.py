"""
API Key Manager for distributing users across multiple Helius API keys.

This module implements user-to-key assignment, request routing, and automatic
failover for managing multiple Helius API keys to scale beyond single-key limits.
"""

import logging
import re
import asyncio
import aiohttp
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any

try:
    from .api_usage_monitor import APIUsageMonitor
except ImportError:
    from api_usage_monitor import APIUsageMonitor

logger = logging.getLogger(__name__)


@dataclass
class APIKeyConfig:
    """Configuration for a single API key."""
    index: int  # 0, 1, or 2
    key: str
    url: str
    user_range: Tuple[int, int]  # e.g., (1, 200)
    is_available: bool = True
    failure_count: int = 0
    last_test: Optional[datetime] = None
    unavailable_since: Optional[datetime] = None  # Track when key became unavailable
    recovery_attempts: int = 0  # Track recovery attempt count


@dataclass
class UserAssignment:
    """Maps user to API key."""
    user_id: str
    user_number: int  # Extracted from user_id
    key_index: int  # 0, 1, or 2
    assigned_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class APIKeyManager:
    """
    Manage multiple Helius API keys with user distribution and failover.
    
    Distributes users across 3 API keys based on user ID ranges:
    - Users 1-200 → Key 0
    - Users 201-400 → Key 1
    - Users 401-500 → Key 2
    
    Integrates with APIUsageMonitor for request tracking and provides
    automatic failover when keys hit rate limits.
    """
    
    # Recovery configuration
    RECOVERY_WAIT_MINUTES = 5
    RECOVERY_CHECK_INTERVAL_SECONDS = 30
    
    def __init__(
        self,
        keys: List[str],
        usage_monitor: Optional[APIUsageMonitor] = None,
        base_url: str = "https://mainnet.helius-rpc.com",
        rpc_fallback_manager: Optional[Any] = None
    ):
        """
        Initialize API Key Manager.        
        Args:
            keys: List of Helius API keys (up to 3)
            usage_monitor: Optional APIUsageMonitor instance
            base_url: Base URL for Helius RPC endpoints
            rpc_fallback_manager: Optional RPCFallbackManager for failover routing
        """
        self.base_url = base_url
        self.usage_monitor = usage_monitor or APIUsageMonitor()
        self.rpc_fallback_manager = rpc_fallback_manager
        self.keys: Dict[int, APIKeyConfig] = {}
        self.user_assignments: Dict[str, UserAssignment] = {}
        self._recovery_task: Optional[asyncio.Task] = None
        
        # User range definitions for 3 keys
        self.user_ranges = [
            (1, 200),    # Key 0
            (201, 400),  # Key 1
            (401, 500),  # Key 2
        ]
        
        # Load and validate keys
        self._load_keys(keys)
        
        # Start recovery monitoring task
        self._start_recovery_monitoring()
        
        logger.info(
            f"APIKeyManager initialized with {len(self.keys)} valid keys "
            f"out of {len(keys)} provided"
        )
    
    def _load_keys(self, keys: List[str]) -> None:
        """
        Load and validate API keys.        
        Args:
            keys: List of API keys to load
        """
        for index, key in enumerate(keys[:3]):  # Max 3 keys
            if not key or not isinstance(key, str) or len(key.strip()) == 0:
                logger.error(
                    f"Invalid or missing API key at index {index}: "
                    f"excluding from rotation pool"
                )
                continue
            
            # Validate key format (basic check)
            key = key.strip()
            if len(key) < 10:  # Helius keys are longer
                logger.error(
                    f"API key at index {index} appears invalid (too short): "
                    f"excluding from rotation pool"
                )
                continue
            
            # Create key configuration
            user_range = self.user_ranges[index] if index < len(self.user_ranges) else (0, 0)
            self.keys[index] = APIKeyConfig(
                index=index,
                key=key,
                url=f"{self.base_url}/?api-key={key}",
                user_range=user_range,
                is_available=True
            )
            
            logger.info(
                f"Loaded API key {index} for user range {user_range[0]}-{user_range[1]}"
            )
    
    def assign_user(self, user_id: str) -> int:
        """
        Assign a user to an API key based on user ID.        
        Args:
            user_id: User identifier (e.g., "user_123", "alice_456")
            
        Returns:
            Key index (0-2) assigned to the user
        """
        # Extract numeric ID from user_id
        user_number = self._extract_user_number(user_id)
        
        # Determine key index based on user number
        key_index = self._calculate_key_index(user_number)
        
        # Store assignment
        self.user_assignments[user_id] = UserAssignment(
            user_id=user_id,
            user_number=user_number,
            key_index=key_index
        )
        
        logger.debug(
            f"Assigned user {user_id} (number {user_number}) to key {key_index}"
        )
        
        return key_index
    
    def _extract_user_number(self, user_id: str) -> int:
        """
        Extract numeric portion from user ID.
        
        Args:
            user_id: User identifier (e.g., "user_123", "alice_456")
            
        Returns:
            Numeric user ID, or hash-based number if no digits found
        """
        # Try to extract numbers from user_id
        numbers = re.findall(r'\d+', user_id)
        
        if numbers:
            # Use the first number found
            return int(numbers[0])
        else:
            # Fallback: use hash of user_id modulo 500 + 1
            return (hash(user_id) % 500) + 1
    
    def _calculate_key_index(self, user_number: int) -> int:
        """
        Calculate key index based on user number.        
        Args:
            user_number: Numeric user ID
            
        Returns:
            Key index (0-2)
        """
        if user_number <= 200:
            return 0
        elif user_number <= 400:
            return 1
        else:
            return 2
    
    def get_key_for_user(self, user_id: str) -> Optional[str]:
        """
        Get the API key assigned to a user.        
        Args:
            user_id: User identifier
            
        Returns:
            API key string, or None if user not assigned or key unavailable
        """
        # Check if user already assigned
        if user_id not in self.user_assignments:
            # Auto-assign user
            self.assign_user(user_id)
        
        assignment = self.user_assignments[user_id]
        key_index = assignment.key_index
        
        # Check if key exists and is available
        if key_index not in self.keys:
            logger.warning(
                f"Key {key_index} not available for user {user_id}, "
                f"no valid key in rotation pool"
            )
            return None
        
        key_config = self.keys[key_index]
        
        if not key_config.is_available:
            logger.warning(
                f"Key {key_index} marked unavailable for user {user_id}"
            )
            return None
        
        # Record request in usage monitor
        if self.usage_monitor:
            self.usage_monitor.record_request(key_index)
        
        return key_config.key
    
    def get_rpc_url_for_user(self, user_id: str) -> Optional[str]:
        """
        Get the RPC URL for a user's assigned key.        
        Args:
            user_id: User identifier
            
        Returns:
            Full RPC URL with API key, or None if unavailable
        """
        # Check if user already assigned
        if user_id not in self.user_assignments:
            # Auto-assign user
            self.assign_user(user_id)
        
        assignment = self.user_assignments[user_id]
        key_index = assignment.key_index
        
        # Check if key exists and is available
        if key_index not in self.keys:
            logger.warning(
                f"Key {key_index} not available for user {user_id}"
            )
            return None
        
        key_config = self.keys[key_index]
        
        if not key_config.is_available:
            logger.warning(
                f"Key {key_index} marked unavailable for user {user_id}"
            )
            return None
        
        # Record request in usage monitor
        if self.usage_monitor:
            self.usage_monitor.record_request(key_index)
        
        return key_config.url
    
    def mark_key_unavailable(self, key_index: int, reason: str = "unknown") -> None:
        """
        Mark an API key as temporarily unavailable.        
        Used when a key hits rate limits or experiences errors.
        
        Args:
            key_index: Index of the key to mark unavailable
            reason: Reason for marking unavailable (e.g., "rate_limit", "error")
        """
        if key_index not in self.keys:
            logger.warning(f"Cannot mark non-existent key {key_index} unavailable")
            return
        
        self.keys[key_index].is_available = False
        self.keys[key_index].failure_count += 1
        self.keys[key_index].unavailable_since = datetime.now(timezone.utc)
        
        logger.warning(
            f"Marked API key {key_index} as unavailable due to {reason} "
            f"(failure count: {self.keys[key_index].failure_count})"
        )
    
    def mark_key_available(self, key_index: int) -> None:
        """
        Mark an API key as available.        
        Used after successful recovery from rate limits or errors.
        
        Args:
            key_index: Index of the key to mark available
        """
        if key_index not in self.keys:
            logger.warning(f"Cannot mark non-existent key {key_index} available")
            return
        
        self.keys[key_index].is_available = True
        self.keys[key_index].last_test = datetime.now(timezone.utc)
        self.keys[key_index].unavailable_since = None
        self.keys[key_index].recovery_attempts = 0
        
        logger.info(f"Marked API key {key_index} as available after successful recovery")
    
    def handle_rate_limit_error(self, key_index: int) -> None:
        """
        Handle rate limit error (HTTP 429) for a specific key.        
        Args:
            key_index: Index of the key that hit rate limit
        """
        logger.error(f"Rate limit error (HTTP 429) detected for key {key_index}")
        self.mark_key_unavailable(key_index, reason="rate_limit")
    
    def should_use_fallback(self, user_id: str) -> bool:
        """
        Determine if request should use fallback manager.        
        Args:
            user_id: User identifier
            
        Returns:
            True if should use fallback, False otherwise
        """
        # Check if user already assigned
        if user_id not in self.user_assignments:
            self.assign_user(user_id)
        
        assignment = self.user_assignments[user_id]
        key_index = assignment.key_index
        
        # Check if assigned key is unavailable
        if key_index not in self.keys or not self.keys[key_index].is_available:
            return True
        
        # Check if all keys are unavailable
        available_keys = sum(1 for k in self.keys.values() if k.is_available)
        if available_keys == 0:
            logger.warning("All API keys unavailable, using fallback for all requests")
            return True
        
        return False
    
    async def test_key_availability(self, key_index: int) -> bool:
        """
        Test if a key is available by making a test RPC request.        
        Args:
            key_index: Index of the key to test
            
        Returns:
            True if key is available, False otherwise
        """
        if key_index not in self.keys:
            return False
        
        key_config = self.keys[key_index]
        
        try:
            # Make a lightweight test request (getHealth)
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getHealth"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    key_config.url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 429:
                        # Still rate limited
                        logger.debug(f"Key {key_index} still rate limited during test")
                        return False
                    
                    if response.status == 200:
                        # Key is available
                        logger.info(f"Key {key_index} test successful, marking available")
                        return True
                    
                    # Other error
                    logger.warning(
                        f"Key {key_index} test returned HTTP {response.status}"
                    )
                    return False
        
        except Exception as e:
            logger.warning(f"Key {key_index} test failed: {e}")
            return False
    
    def _start_recovery_monitoring(self) -> None:
        """
        Start background task to monitor and recover unavailable keys.        """
        # Only start if not already running and if there's an event loop
        try:
            loop = asyncio.get_running_loop()
            if self._recovery_task is None or self._recovery_task.done():
                self._recovery_task = asyncio.create_task(self._recovery_monitor_loop())
                logger.info("Started key recovery monitoring task")
        except RuntimeError:
            # No event loop running - recovery monitoring will need to be started manually
            logger.debug("No event loop available, recovery monitoring not started")
    
    async def _recovery_monitor_loop(self) -> None:
        """
        Background loop to check and recover unavailable keys.        """
        while True:
            try:
                await asyncio.sleep(self.RECOVERY_CHECK_INTERVAL_SECONDS)
                
                now = datetime.now(timezone.utc)
                recovery_threshold = timedelta(minutes=self.RECOVERY_WAIT_MINUTES)
                
                for key_index, key_config in self.keys.items():
                    # Skip available keys
                    if key_config.is_available:
                        continue
                    
                    # Check if enough time has passed since unavailable
                    if key_config.unavailable_since is None:
                        continue
                    
                    time_unavailable = now - key_config.unavailable_since
                    
                    if time_unavailable >= recovery_threshold:
                        logger.info(
                            f"Attempting recovery for key {key_index} "
                            f"(unavailable for {time_unavailable.total_seconds():.0f}s)"
                        )
                        
                        key_config.recovery_attempts += 1
                        
                        # Test key availability
                        is_available = await self.test_key_availability(key_index)
                        
                        if is_available:
                            # Mark as available
                            self.mark_key_available(key_index)
                            logger.info(
                                f"Successfully recovered key {key_index} "
                                f"after {key_config.recovery_attempts} attempts"
                            )
                        else:
                            # Reset timer for next attempt
                            key_config.unavailable_since = now
                            logger.debug(
                                f"Key {key_index} recovery attempt {key_config.recovery_attempts} failed, "
                                f"will retry in {self.RECOVERY_WAIT_MINUTES} minutes"
                            )
            
            except Exception as e:
                logger.error(f"Error in recovery monitor loop: {e}")
                # Continue monitoring despite errors
                continue
    
    def stop_recovery_monitoring(self) -> None:
        """Stop the recovery monitoring task."""
        if self._recovery_task and not self._recovery_task.done():
            self._recovery_task.cancel()
            logger.info("Stopped key recovery monitoring task")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get status of all API keys and user assignments.        
        Returns:
            Dictionary with key status and user assignments
        """
        # Group users by key
        users_by_key: Dict[int, List[str]] = {0: [], 1: [], 2: []}
        for user_id, assignment in self.user_assignments.items():
            if assignment.key_index in users_by_key:
                users_by_key[assignment.key_index].append(user_id)
        
        # Build status for each key
        key_statuses = []
        for index in range(3):
            if index in self.keys:
                key_config = self.keys[index]
                status = {
                    "index": index,
                    "is_available": key_config.is_available,
                    "user_range": key_config.user_range,
                    "assigned_users": len(users_by_key.get(index, [])),
                    "failure_count": key_config.failure_count,
                    "last_test": key_config.last_test.isoformat() if key_config.last_test else None,
                    "recovery_attempts": key_config.recovery_attempts
                }
                
                # Add unavailable duration if applicable
                if not key_config.is_available and key_config.unavailable_since:
                    duration = datetime.now(timezone.utc) - key_config.unavailable_since
                    status["unavailable_duration_seconds"] = int(duration.total_seconds())
                    status["unavailable_since"] = key_config.unavailable_since.isoformat()
                
                key_statuses.append(status)
            else:
                key_statuses.append({
                    "index": index,
                    "is_available": False,
                    "user_range": self.user_ranges[index] if index < len(self.user_ranges) else (0, 0),
                    "assigned_users": 0,
                    "failure_count": 0,
                    "last_test": None,
                    "recovery_attempts": 0,
                    "error": "Key not loaded or invalid"
                })
        
        return {
            "total_keys": 3,
            "valid_keys": len(self.keys),
            "available_keys": sum(1 for k in self.keys.values() if k.is_available),
            "total_users": len(self.user_assignments),
            "keys": key_statuses,
            "users_by_key": {
                str(k): len(v) for k, v in users_by_key.items()
            }
        }
    
    def get_assignment(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get assignment details for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with assignment details, or None if not assigned
        """
        if user_id not in self.user_assignments:
            return None
        
        assignment = self.user_assignments[user_id]
        return {
            "user_id": assignment.user_id,
            "user_number": assignment.user_number,
            "key_index": assignment.key_index,
            "assigned_at": assignment.assigned_at.isoformat()
        }
