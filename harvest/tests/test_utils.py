"""
Test utilities and helper functions.

This module provides utility functions for common testing operations,
including async helpers, mock configuration, and assertion utilities.
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta


# ============================================================================
# Async Test Helpers
# ============================================================================

async def wait_for_condition(
    condition_func: Callable[[], bool],
    timeout: float = 5.0,
    interval: float = 0.1,
    error_message: str = "Condition not met within timeout"
) -> bool:
    """
    Wait for a condition to become true.
    
    Args:
        condition_func: Function that returns True when condition is met
        timeout: Maximum time to wait in seconds
        interval: Time between checks in seconds
        error_message: Error message if timeout is reached
        
    Returns:
        True if condition was met, raises TimeoutError otherwise
    """
    start_time = asyncio.get_event_loop().time()
    
    while asyncio.get_event_loop().time() - start_time < timeout:
        if condition_func():
            return True
        await asyncio.sleep(interval)
    
    raise TimeoutError(error_message)


async def run_with_timeout(
    coro,
    timeout: float = 5.0,
    error_message: str = "Operation timed out"
):
    """
    Run a coroutine with a timeout.
    
    Args:
        coro: Coroutine to run
        timeout: Maximum time to wait in seconds
        error_message: Error message if timeout is reached
        
    Returns:
        Result of the coroutine
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(error_message)


# ============================================================================
# Mock Configuration Helpers
# ============================================================================

class MockConfig:
    """Configuration for mock objects with failure simulation."""
    
    def __init__(
        self,
        service_name: str,
        endpoint: str = "",
        response_data: Any = None,
        response_delay_ms: int = 0,
        failure_rate: float = 0.0,
        error_type: Optional[type] = None
    ):
        """
        Initialize mock configuration.
        
        Args:
            service_name: Name of the service being mocked
            endpoint: API endpoint being mocked
            response_data: Data to return on success
            response_delay_ms: Delay before returning response
            failure_rate: Probability of failure (0.0 to 1.0)
            error_type: Type of exception to raise on failure
        """
        self.service_name = service_name
        self.endpoint = endpoint
        self.response_data = response_data
        self.response_delay_ms = response_delay_ms
        self.failure_rate = failure_rate
        self.error_type = error_type or Exception
        self._call_count = 0
    
    def should_fail(self) -> bool:
        """Determine if this call should fail based on failure rate."""
        import random
        return random.random() < self.failure_rate
    
    async def get_response(self) -> Any:
        """
        Get the mock response, simulating delay and potential failure.
        
        Returns:
            Response data if successful
            
        Raises:
            Configured error type if failure occurs
        """
        self._call_count += 1
        
        # Simulate delay
        if self.response_delay_ms > 0:
            await asyncio.sleep(self.response_delay_ms / 1000.0)
        
        # Simulate failure
        if self.should_fail():
            raise self.error_type(f"Mock failure for {self.service_name}")
        
        return self.response_data
    
    @property
    def call_count(self) -> int:
        """Get the number of times this mock was called."""
        return self._call_count


# ============================================================================
# Assertion Helpers
# ============================================================================

def assert_dict_contains(actual: Dict, expected: Dict, path: str = ""):
    """
    Assert that actual dict contains all keys and values from expected dict.
    
    Args:
        actual: Actual dictionary
        expected: Expected dictionary (subset)
        path: Current path for error messages
    """
    for key, expected_value in expected.items():
        current_path = f"{path}.{key}" if path else key
        
        assert key in actual, f"Missing key: {current_path}"
        
        actual_value = actual[key]
        
        if isinstance(expected_value, dict):
            assert isinstance(actual_value, dict), \
                f"Expected dict at {current_path}, got {type(actual_value)}"
            assert_dict_contains(actual_value, expected_value, current_path)
        else:
            assert actual_value == expected_value, \
                f"Value mismatch at {current_path}: expected {expected_value}, got {actual_value}"


def assert_called_with_partial(mock_obj, **expected_kwargs):
    """
    Assert that a mock was called with at least the specified kwargs.
    
    Args:
        mock_obj: Mock object to check
        **expected_kwargs: Expected keyword arguments (subset)
    """
    assert mock_obj.called, "Mock was not called"
    
    # Get the last call's kwargs
    last_call = mock_obj.call_args
    if last_call is None:
        raise AssertionError("Mock was not called")
    
    _, actual_kwargs = last_call
    
    for key, expected_value in expected_kwargs.items():
        assert key in actual_kwargs, f"Missing kwarg: {key}"
        assert actual_kwargs[key] == expected_value, \
            f"Kwarg mismatch for {key}: expected {expected_value}, got {actual_kwargs[key]}"


def assert_list_contains_item(items: List[Dict], **expected_fields):
    """
    Assert that a list contains at least one item matching the expected fields.
    
    Args:
        items: List of dictionaries
        **expected_fields: Fields that must match in at least one item
    """
    for item in items:
        if all(item.get(k) == v for k, v in expected_fields.items()):
            return
    
    raise AssertionError(
        f"No item found matching {expected_fields} in list of {len(items)} items"
    )


# ============================================================================
# Test Data Helpers
# ============================================================================

def create_test_trades(
    count: int,
    base_profit: float = 0.01,
    strategy: str = "jupiter_swap"
) -> List[Dict]:
    """
    Create a list of test trades.
    
    Args:
        count: Number of trades to create
        base_profit: Base profit amount
        strategy: Strategy name
        
    Returns:
        List of trade dictionaries
    """
    trades = []
    for i in range(count):
        trades.append({
            "strategy": strategy,
            "expected_profit": base_profit * (i + 1),
            "actual_profit": base_profit * (i + 1) * 0.95,  # 5% slippage
            "status": "completed",
            "timestamp": datetime.now() - timedelta(hours=i),
            "signature": f"test_signature_{i}",
            "execution_time_ms": 1000 + i * 100
        })
    return trades


def create_test_users(
    count: int,
    base_user_id: int = 10000
) -> List[Dict]:
    """
    Create a list of test users.
    
    Args:
        count: Number of users to create
        base_user_id: Starting user ID
        
    Returns:
        List of user dictionaries
    """
    users = []
    for i in range(count):
        users.append({
            "user_id": base_user_id + i,
            "telegram_username": f"testuser{i}",
            "wallet_address": f"TestWallet{i:032d}",
            "wallet_balance": 1.0 + i * 0.1,
            "preferences": {},
            "fee_status": "paid",
            "created_at": datetime.now() - timedelta(days=i),
            "last_active": datetime.now()
        })
    return users


# ============================================================================
# Mock Service Builders
# ============================================================================

def build_mock_telegram_bot(
    send_message_response: Any = None,
    send_message_side_effect: Optional[Exception] = None
) -> MagicMock:
    """
    Build a mock Telegram bot with configurable behavior.
    
    Args:
        send_message_response: Response to return from send_message
        send_message_side_effect: Exception to raise from send_message
        
    Returns:
        Mock Telegram bot
    """
    bot = MagicMock()
    
    if send_message_side_effect:
        bot.send_message = AsyncMock(side_effect=send_message_side_effect)
    else:
        bot.send_message = AsyncMock(return_value=send_message_response)
    
    bot.edit_message_text = AsyncMock()
    bot.delete_message = AsyncMock()
    bot.answer_callback_query = AsyncMock()
    
    return bot


def build_mock_database(
    query_results: Optional[Dict[str, Any]] = None
) -> MagicMock:
    """
    Build a mock database with configurable query results.
    
    Args:
        query_results: Dictionary mapping query patterns to results
        
    Returns:
        Mock database
    """
    db = MagicMock()
    
    if query_results:
        def execute_side_effect(query, *args, **kwargs):
            for pattern, result in query_results.items():
                if pattern in query:
                    return result
            return None
        
        db.execute = AsyncMock(side_effect=execute_side_effect)
    else:
        db.execute = AsyncMock()
    
    db.fetch_one = AsyncMock()
    db.fetch_all = AsyncMock(return_value=[])
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    
    return db


# ============================================================================
# Performance Testing Helpers
# ============================================================================

class PerformanceTimer:
    """Context manager for measuring execution time."""
    
    def __init__(self, name: str = "Operation"):
        """
        Initialize performance timer.
        
        Args:
            name: Name of the operation being timed
        """
        self.name = name
        self.start_time = None
        self.end_time = None
        self.duration_ms = None
    
    def __enter__(self):
        """Start the timer."""
        import time
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the timer and calculate duration."""
        import time
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000
    
    def assert_under_threshold(self, threshold_ms: float):
        """
        Assert that the operation completed under the threshold.
        
        Args:
            threshold_ms: Maximum allowed duration in milliseconds
        """
        assert self.duration_ms is not None, "Timer was not used"
        assert self.duration_ms < threshold_ms, \
            f"{self.name} took {self.duration_ms:.2f}ms, expected < {threshold_ms}ms"


async def measure_async_performance(
    coro,
    name: str = "Operation"
) -> tuple[Any, float]:
    """
    Measure the performance of an async operation.
    
    Args:
        coro: Coroutine to measure
        name: Name of the operation
        
    Returns:
        Tuple of (result, duration_ms)
    """
    start_time = asyncio.get_event_loop().time()
    result = await coro
    end_time = asyncio.get_event_loop().time()
    duration_ms = (end_time - start_time) * 1000
    
    return result, duration_ms


# ============================================================================
# Concurrent Testing Helpers
# ============================================================================

async def run_concurrent_operations(
    operations: List[Callable],
    max_concurrent: int = 10
) -> List[Any]:
    """
    Run multiple operations concurrently with a concurrency limit.
    
    Args:
        operations: List of async callables to run
        max_concurrent: Maximum number of concurrent operations
        
    Returns:
        List of results in the same order as operations
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def run_with_semaphore(op):
        async with semaphore:
            return await op()
    
    tasks = [run_with_semaphore(op) for op in operations]
    return await asyncio.gather(*tasks)


# ============================================================================
# Cleanup Helpers
# ============================================================================

class TestCleanup:
    """Context manager for test cleanup operations."""
    
    def __init__(self):
        """Initialize cleanup manager."""
        self.cleanup_funcs = []
    
    def add(self, func: Callable, *args, **kwargs):
        """
        Add a cleanup function to be called on exit.
        
        Args:
            func: Cleanup function
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
        """
        self.cleanup_funcs.append((func, args, kwargs))
    
    def __enter__(self):
        """Enter context."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and run cleanup functions."""
        for func, args, kwargs in reversed(self.cleanup_funcs):
            try:
                if asyncio.iscoroutinefunction(func):
                    asyncio.get_event_loop().run_until_complete(
                        func(*args, **kwargs)
                    )
                else:
                    func(*args, **kwargs)
            except Exception as e:
                # Log but don't raise cleanup errors
                print(f"Cleanup error: {e}")
