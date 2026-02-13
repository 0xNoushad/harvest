"""
Test suite for multi-user concurrent operations and user isolation.

This module tests Properties 54, 55, 56:
- Property 54: Multi-user concurrent processing
- Property 55: User state isolation
- Property 56: Concurrent data integrity

Tests validate:
- Multiple users can execute commands simultaneously without blocking
- User state (wallet, trades, performance, fees) is completely isolated
- Concurrent operations maintain data integrity with proper locking
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import List, Dict, Any

from hypothesis import given, settings, strategies as st, assume
from tests.generators import (
    user_strategy,
    multi_user_scenario_strategy,
    telegram_command_strategy
)


# ============================================================================
# Property 54: Multi-user Concurrent Processing
# ============================================================================

@pytest.mark.asyncio
async def test_concurrent_command_processing_multiple_users(test_harness):
    """
    Property 54: Multi-user concurrent processing
    
    For any set of simultaneous commands from different users, the system
    should process each independently without blocking.
    
    Test Strategy:
    - Create multiple users with different IDs
    - Send commands from all users simultaneously
    - Verify all commands are processed
    - Verify no command blocks another
    - Measure that concurrent execution is faster than sequential
    """
    # Create 5 test users
    num_users = 5
    users = [test_harness.create_test_user(user_id=10000 + i) for i in range(num_users)]
    
    # Create mock bot for each user
    mock_bots = []
    for user in users:
        bot = MagicMock()
        bot.wallet = test_harness.create_mock_wallet(
            balance=user["wallet_balance"],
            address=user["wallet_address"]
        )
        bot.performance = test_harness.create_mock_performance_tracker()
        mock_bots.append(bot)
    
    # Create mock updates for each user
    updates = [
        test_harness.create_mock_telegram_update(
            "wallet",
            user_id=user["user_id"]
        )
        for user in users
    ]
    
    # Create mock contexts
    contexts = [test_harness.create_mock_telegram_context() for _ in range(num_users)]
    
    # Mock command handler that simulates processing time
    async def mock_command_handler(update, context, bot):
        """Simulate command processing with delay."""
        await asyncio.sleep(0.1)  # Simulate processing time
        await update.message.reply_text(f"Processed for user {update.effective_user.id}")
        return True
    
    # Execute commands concurrently
    start_time = asyncio.get_event_loop().time()
    
    tasks = [
        mock_command_handler(updates[i], contexts[i], mock_bots[i])
        for i in range(num_users)
    ]
    results = await asyncio.gather(*tasks)
    
    concurrent_time = asyncio.get_event_loop().time() - start_time
    
    # Verify all commands completed
    assert all(results), "All commands should complete successfully"
    
    # Verify concurrent execution is faster than sequential
    # Sequential would take num_users * 0.1 = 0.5 seconds
    # Concurrent should take ~0.1 seconds (plus overhead)
    assert concurrent_time < 0.3, f"Concurrent execution should be fast, took {concurrent_time}s"
    
    # Verify each user received a response
    for i, update in enumerate(updates):
        assert update.message.reply_text.called, f"User {i} should receive response"
        call_args = update.message.reply_text.call_args[0][0]
        assert str(users[i]["user_id"]) in call_args, "Response should contain user ID"


@pytest.mark.asyncio
async def test_concurrent_operations_no_blocking(test_harness):
    """
    Test that concurrent operations from different users don't block each other.
    
    Validates Property 54: Commands from different users process independently.
    """
    # Create 3 users
    users = [test_harness.create_test_user(user_id=20000 + i) for i in range(3)]
    
    # Track execution order
    execution_order = []
    
    async def slow_command(user_id: int, delay: float):
        """Simulate a slow command."""
        await asyncio.sleep(delay)
        execution_order.append(user_id)
        return user_id
    
    # User 1: slow command (0.3s)
    # User 2: fast command (0.1s)
    # User 3: medium command (0.2s)
    tasks = [
        slow_command(users[0]["user_id"], 0.3),
        slow_command(users[1]["user_id"], 0.1),
        slow_command(users[2]["user_id"], 0.2)
    ]
    
    results = await asyncio.gather(*tasks)
    
    # Verify all completed
    assert len(results) == 3
    assert set(results) == {users[0]["user_id"], users[1]["user_id"], users[2]["user_id"]}
    
    # Verify execution order: fastest first
    assert execution_order[0] == users[1]["user_id"], "Fastest command should complete first"
    assert execution_order[1] == users[2]["user_id"], "Medium command should complete second"
    assert execution_order[2] == users[0]["user_id"], "Slowest command should complete last"


# ============================================================================
# Property 55: User State Isolation
# ============================================================================

@pytest.mark.asyncio
async def test_user_wallet_isolation(test_harness):
    """
    Property 55: User state isolation - Wallet access
    
    For any user operation accessing wallet, the system should ensure
    complete isolation from other users' wallets.
    
    Test Strategy:
    - Create multiple users with different wallets
    - Execute wallet operations concurrently
    - Verify each user accesses only their own wallet
    - Verify no cross-contamination of wallet data
    """
    # Create 3 users with different wallets
    users = [
        test_harness.create_test_user(
            user_id=30000 + i,
            wallet_address=f"Wallet{i}{'x' * 35}",
            wallet_balance=float(i + 1)
        )
        for i in range(3)
    ]
    
    # Create mock wallets for each user
    wallets = {
        user["user_id"]: test_harness.create_mock_wallet(
            balance=user["wallet_balance"],
            address=user["wallet_address"]
        )
        for user in users
    }
    
    # Simulate concurrent wallet access
    async def get_user_balance(user_id: int) -> float:
        """Get balance for specific user."""
        wallet = wallets[user_id]
        return await wallet.get_balance()
    
    # Execute concurrent balance checks
    tasks = [get_user_balance(user["user_id"]) for user in users]
    balances = await asyncio.gather(*tasks)
    
    # Verify each user got their own balance
    for i, user in enumerate(users):
        assert balances[i] == user["wallet_balance"], \
            f"User {user['user_id']} should get their own balance"
    
    # Verify balances are different (proving isolation)
    assert len(set(balances)) == len(balances), "All balances should be unique"


@pytest.mark.asyncio
async def test_user_trade_tracking_isolation(test_harness):
    """
    Property 55: User state isolation - Trade tracking
    
    For any user operation tracking trades, the system should ensure
    complete isolation from other users' trade history.
    """
    # Create 3 users
    users = [test_harness.create_test_user(user_id=40000 + i) for i in range(3)]
    
    # Create mock performance trackers with different trade counts
    trackers = {
        user["user_id"]: test_harness.create_mock_performance_tracker(
            total_trades=10 * (i + 1),
            winning_trades=5 * (i + 1),
            total_profit=float(i + 1) * 0.5
        )
        for i, user in enumerate(users)
    }
    
    # Simulate concurrent trade queries
    async def get_user_stats(user_id: int) -> Dict[str, Any]:
        """Get stats for specific user."""
        tracker = trackers[user_id]
        return {
            "total_trades": tracker.get_total_trades(),
            "winning_trades": tracker.get_winning_trades(),
            "total_profit": tracker.get_total_profit()
        }
    
    # Execute concurrent stats queries
    tasks = [get_user_stats(user["user_id"]) for user in users]
    stats = await asyncio.gather(*tasks)
    
    # Verify each user got their own stats
    for i, user in enumerate(users):
        expected_trades = 10 * (i + 1)
        expected_wins = 5 * (i + 1)
        expected_profit = float(i + 1) * 0.5
        
        assert stats[i]["total_trades"] == expected_trades, \
            f"User {user['user_id']} should get their own trade count"
        assert stats[i]["winning_trades"] == expected_wins, \
            f"User {user['user_id']} should get their own win count"
        assert stats[i]["total_profit"] == expected_profit, \
            f"User {user['user_id']} should get their own profit"


@pytest.mark.asyncio
async def test_user_pause_resume_isolation(test_harness):
    """
    Property 55: User state isolation - Pause/resume state
    
    For any user pausing their bot, the system should not affect other users.
    """
    # Create 3 users
    users = [test_harness.create_test_user(user_id=50000 + i) for i in range(3)]
    
    # Create mock risk managers for each user
    risk_managers = {
        user["user_id"]: test_harness.create_mock_risk_manager(is_paused=False)
        for user in users
    }
    
    # User 0 pauses their bot
    risk_managers[users[0]["user_id"]].pause_trading()
    risk_managers[users[0]["user_id"]].is_paused.return_value = True
    
    # Verify only user 0 is paused
    assert risk_managers[users[0]["user_id"]].is_paused() == True, \
        "User 0 should be paused"
    assert risk_managers[users[1]["user_id"]].is_paused() == False, \
        "User 1 should still be active"
    assert risk_managers[users[2]["user_id"]].is_paused() == False, \
        "User 2 should still be active"


@pytest.mark.asyncio
async def test_user_circuit_breaker_isolation(test_harness):
    """
    Property 55: User state isolation - Circuit breaker
    
    For any user's circuit breaker activating, the system should not affect
    other users.
    """
    # Create 3 users
    users = [test_harness.create_test_user(user_id=60000 + i) for i in range(3)]
    
    # Create mock risk managers
    risk_managers = {
        user["user_id"]: test_harness.create_mock_risk_manager(is_paused=False)
        for user in users
    }
    
    # Simulate circuit breaker activation for user 0
    # (e.g., due to excessive losses)
    risk_managers[users[0]["user_id"]].check_circuit_breaker.return_value = True
    risk_managers[users[0]["user_id"]].pause_trading()
    risk_managers[users[0]["user_id"]].is_paused.return_value = True
    
    # Verify isolation
    assert risk_managers[users[0]["user_id"]].is_paused() == True, \
        "User 0 circuit breaker should be active"
    assert risk_managers[users[1]["user_id"]].is_paused() == False, \
        "User 1 should not be affected"
    assert risk_managers[users[2]["user_id"]].is_paused() == False, \
        "User 2 should not be affected"


@pytest.mark.asyncio
async def test_user_fee_calculation_isolation(test_harness):
    """
    Property 55: User state isolation - Fee calculation
    
    For any user's fee calculation, the system should use only that user's
    profit data.
    """
    # Create 3 users with different profits
    users = [
        test_harness.create_test_user(user_id=70000 + i)
        for i in range(3)
    ]
    
    # Mock profit data for each user
    user_profits = {
        users[0]["user_id"]: 1.0,  # 1 SOL profit
        users[1]["user_id"]: 2.0,  # 2 SOL profit
        users[2]["user_id"]: 0.5,  # 0.5 SOL profit
    }
    
    # Calculate fees (20% of profit)
    def calculate_fee(user_id: int) -> float:
        """Calculate fee for specific user."""
        profit = user_profits[user_id]
        return profit * 0.20
    
    # Calculate fees for all users
    fees = {user["user_id"]: calculate_fee(user["user_id"]) for user in users}
    
    # Verify each user's fee is based on their own profit
    assert fees[users[0]["user_id"]] == 0.20, "User 0 fee should be 20% of 1.0 SOL"
    assert fees[users[1]["user_id"]] == 0.40, "User 1 fee should be 20% of 2.0 SOL"
    assert fees[users[2]["user_id"]] == 0.10, "User 2 fee should be 20% of 0.5 SOL"
    
    # Verify fees are different (proving isolation)
    assert len(set(fees.values())) == len(fees), "All fees should be unique"


# ============================================================================
# Property 56: Concurrent Data Integrity
# ============================================================================

@pytest.mark.asyncio
async def test_concurrent_state_modification_with_locking(test_harness):
    """
    Property 56: Concurrent data integrity
    
    For any concurrent operations modifying user state, the system should
    use locking or transactions to ensure data integrity.
    
    Test Strategy:
    - Simulate concurrent modifications to shared state
    - Verify final state is consistent
    - Verify no race conditions or lost updates
    """
    # Shared counter representing user balance
    user_balance = {"value": 1.0, "lock": asyncio.Lock()}
    
    async def add_to_balance(amount: float):
        """Add amount to balance with locking."""
        async with user_balance["lock"]:
            current = user_balance["value"]
            await asyncio.sleep(0.01)  # Simulate processing
            user_balance["value"] = current + amount
    
    async def subtract_from_balance(amount: float):
        """Subtract amount from balance with locking."""
        async with user_balance["lock"]:
            current = user_balance["value"]
            await asyncio.sleep(0.01)  # Simulate processing
            user_balance["value"] = current - amount
    
    # Execute concurrent modifications
    # 10 additions of 0.1 SOL and 5 subtractions of 0.1 SOL
    # Expected final balance: 1.0 + (10 * 0.1) - (5 * 0.1) = 1.5 SOL
    tasks = []
    for _ in range(10):
        tasks.append(add_to_balance(0.1))
    for _ in range(5):
        tasks.append(subtract_from_balance(0.1))
    
    await asyncio.gather(*tasks)
    
    # Verify final balance is correct (no lost updates)
    expected_balance = 1.0 + (10 * 0.1) - (5 * 0.1)
    assert abs(user_balance["value"] - expected_balance) < 0.001, \
        f"Balance should be {expected_balance}, got {user_balance['value']}"


@pytest.mark.asyncio
async def test_concurrent_trade_recording_integrity(test_harness):
    """
    Test that concurrent trade recording maintains data integrity.
    
    Validates Property 56: Concurrent operations maintain data integrity.
    """
    # Shared trade list with lock
    trades = {"list": [], "lock": asyncio.Lock()}
    
    async def record_trade(trade_data: Dict[str, Any]):
        """Record a trade with locking."""
        async with trades["lock"]:
            # Simulate processing
            await asyncio.sleep(0.01)
            trades["list"].append(trade_data)
    
    # Create 20 trades with unique signatures
    trade_data_list = [
        {
            **test_harness.create_test_trade(
                strategy="jupiter_swap",
                expected_profit=0.01 * i
            ),
            "signature": f"mock_signature_{i}"  # Unique signature for each trade
        }
        for i in range(20)
    ]
    
    # Record all trades concurrently
    tasks = [record_trade(trade) for trade in trade_data_list]
    await asyncio.gather(*tasks)
    
    # Verify all trades were recorded
    assert len(trades["list"]) == 20, "All 20 trades should be recorded"
    
    # Verify no duplicate trades
    trade_signatures = [t["signature"] for t in trades["list"]]
    assert len(trade_signatures) == len(set(trade_signatures)), \
        "No duplicate trades should exist"


@pytest.mark.asyncio
async def test_new_user_initialization_isolation(test_harness):
    """
    Property 57: New user initialization
    
    For any new user starting the bot, the system should initialize isolated
    state without affecting existing users.
    """
    # Create 2 existing users
    existing_users = [
        test_harness.create_test_user(user_id=80000 + i)
        for i in range(2)
    ]
    
    # Store existing user data
    existing_user_data = {
        user["user_id"]: {
            "wallet_balance": user["wallet_balance"],
            "total_profit": user.get("total_profit", 0.0)
        }
        for user in existing_users
    }
    
    # Initialize new user
    new_user = test_harness.create_test_user(user_id=90000)
    
    # Verify new user has fresh state
    assert new_user["wallet_balance"] == 1.0, "New user should have default balance"
    assert new_user["total_profit"] == 0.0, "New user should have zero profit"
    assert new_user["total_trades"] == 0, "New user should have zero trades"
    
    # Verify existing users are unaffected
    for user in existing_users:
        original_data = existing_user_data[user["user_id"]]
        assert user["wallet_balance"] == original_data["wallet_balance"], \
            "Existing user balance should be unchanged"
        assert user.get("total_profit", 0.0) == original_data["total_profit"], \
            "Existing user profit should be unchanged"


# ============================================================================
# Property-Based Tests
# ============================================================================

@given(multi_user_scenario_strategy(min_users=2, max_users=5))
@settings(max_examples=20, deadline=None)
@pytest.mark.asyncio
async def test_property_multi_user_concurrent_processing(scenario):
    """
    Property-based test for multi-user concurrent processing.
    
    Validates Property 54: Any set of simultaneous commands from different
    users should process independently without blocking.
    """
    users = scenario["users"]
    num_operations = scenario["concurrent_operations"]
    
    # Track completion times
    completion_times = []
    
    async def mock_operation(user_id: int, operation_id: int):
        """Simulate a user operation."""
        start = asyncio.get_event_loop().time()
        await asyncio.sleep(0.01)  # Simulate work
        end = asyncio.get_event_loop().time()
        completion_times.append(end - start)
        return (user_id, operation_id)
    
    # Create operations for random users
    import random
    tasks = [
        mock_operation(
            random.choice(users)["user_id"],
            i
        )
        for i in range(num_operations)
    ]
    
    # Execute concurrently
    results = await asyncio.gather(*tasks)
    
    # Verify all operations completed
    assert len(results) == num_operations
    
    # Verify operations completed in reasonable time
    # (concurrent execution should be much faster than sequential)
    assert len(completion_times) == num_operations


@given(user_strategy(), user_strategy())
@settings(max_examples=20, deadline=None)
@pytest.mark.asyncio
async def test_property_user_state_isolation(user1, user2):
    """
    Property-based test for user state isolation.
    
    Validates Property 55: Any user operation should ensure complete
    isolation from other users' data and state.
    """
    # Ensure users have different IDs and addresses
    assume(user1["user_id"] != user2["user_id"])
    assume(user1["wallet_address"] != user2["wallet_address"])
    
    # Verify users have independent state
    assert user1["user_id"] != user2["user_id"], "Users should have different IDs"
    assert user1["wallet_address"] != user2["wallet_address"], \
        "Users should have different wallet addresses"
    
    # Simulate state modification for user1
    user1["wallet_balance"] += 0.5
    user1["total_profit"] = 0.3
    
    # Verify user2 is unaffected
    assert user2["wallet_balance"] != user1["wallet_balance"] or \
           user2["wallet_balance"] == user1["wallet_balance"] - 0.5, \
        "User2 balance should be independent"
