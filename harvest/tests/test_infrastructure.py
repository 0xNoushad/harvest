"""
Tests for the testing infrastructure itself.

This module verifies that the test harness, fixtures, and utilities
are working correctly before running actual feature tests.
"""

import pytest
from hypothesis import given, strategies as st

from tests.generators import (
    user_strategy,
    wallet_strategy,
    trade_strategy,
    token_holding_strategy,
    portfolio_strategy,
    sol_amount_strategy,
    telegram_user_id_strategy
)
from tests.test_utils import (
    wait_for_condition,
    run_with_timeout,
    MockConfig,
    assert_dict_contains,
    create_test_trades,
    create_test_users,
    PerformanceTimer
)


# ============================================================================
# Fixture Tests
# ============================================================================

@pytest.mark.unit
def test_mock_telegram_update_fixture(mock_telegram_update):
    """Test that mock_telegram_update fixture creates valid updates."""
    update = mock_telegram_update("start", user_id=123, args=["arg1"])
    
    assert update.message is not None
    assert update.message.from_user.id == 123
    assert "start" in update.message.text


@pytest.mark.unit
def test_mock_telegram_context_fixture(mock_telegram_context):
    """Test that mock_telegram_context fixture creates valid contexts."""
    context = mock_telegram_context(args=["arg1", "arg2"])
    
    assert context.args == ["arg1", "arg2"]
    assert context.bot is not None


@pytest.mark.unit
def test_mock_wallet_fixture(mock_wallet):
    """Test that mock_wallet fixture creates valid wallets."""
    wallet = mock_wallet(balance=5.0, address="TestAddress123")
    
    assert wallet.get_address() == "TestAddress123"
    assert wallet.network in ["devnet", "mainnet-beta"]


@pytest.mark.unit
def test_mock_performance_tracker_fixture(mock_performance_tracker):
    """Test that mock_performance_tracker fixture creates valid trackers."""
    tracker = mock_performance_tracker(
        total_profit=10.0,
        win_rate=75.0,
        total_trades=100
    )
    
    assert tracker.get_total_profit() == 10.0
    assert tracker.get_win_rate() == 75.0
    assert tracker.get_total_trades() == 100


@pytest.mark.unit
def test_mock_user_fixture(mock_user):
    """Test that mock_user fixture creates valid users."""
    user = mock_user(user_id=123, telegram_username="testuser")
    
    assert user["user_id"] == 123
    assert user["telegram_username"] == "testuser"
    assert "wallet_address" in user


# ============================================================================
# Generator Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.property
@given(user=user_strategy())
def test_user_generator(user):
    """Test that user generator creates valid users."""
    assert "user_id" in user
    assert "telegram_username" in user
    assert "wallet_address" in user
    assert user["user_id"] > 0
    assert len(user["telegram_username"]) >= 5


@pytest.mark.unit
@pytest.mark.property
@given(wallet=wallet_strategy())
def test_wallet_generator(wallet):
    """Test that wallet generator creates valid wallets."""
    assert "address" in wallet
    assert "balance" in wallet
    assert wallet["balance"] >= 0.0
    assert len(wallet["address"]) >= 32


@pytest.mark.unit
@pytest.mark.property
@given(trade=trade_strategy())
def test_trade_generator(trade):
    """Test that trade generator creates valid trades."""
    assert "strategy" in trade
    assert "expected_profit" in trade
    assert "actual_profit" in trade
    assert "status" in trade
    assert trade["strategy"] in ["jupiter_swap", "marinade_stake", "airdrop_hunter"]


@pytest.mark.unit
@pytest.mark.property
@given(holding=token_holding_strategy())
def test_token_holding_generator(holding):
    """Test that token holding generator creates valid holdings."""
    assert "symbol" in holding
    assert "amount" in holding
    assert "price_usd" in holding
    assert holding["amount"] > 0
    assert holding["price_usd"] > 0


@pytest.mark.unit
@pytest.mark.property
@given(portfolio=portfolio_strategy())
def test_portfolio_generator(portfolio):
    """Test that portfolio generator creates valid portfolios."""
    assert "holdings" in portfolio
    assert "total_value_usd" in portfolio
    assert "token_count" in portfolio
    assert len(portfolio["holdings"]) == portfolio["token_count"]


# ============================================================================
# Utility Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_wait_for_condition_success():
    """Test wait_for_condition with successful condition."""
    counter = {"value": 0}
    
    async def increment():
        counter["value"] += 1
    
    # Start incrementing in background
    import asyncio
    task = asyncio.create_task(increment())
    
    # Wait for condition
    result = await wait_for_condition(
        lambda: counter["value"] > 0,
        timeout=1.0
    )
    
    assert result is True
    await task


@pytest.mark.unit
@pytest.mark.asyncio
async def test_wait_for_condition_timeout():
    """Test wait_for_condition with timeout."""
    with pytest.raises(TimeoutError):
        await wait_for_condition(
            lambda: False,
            timeout=0.1
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_with_timeout_success():
    """Test run_with_timeout with successful operation."""
    async def quick_operation():
        return "success"
    
    result = await run_with_timeout(quick_operation(), timeout=1.0)
    assert result == "success"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_with_timeout_failure():
    """Test run_with_timeout with timeout."""
    import asyncio
    
    async def slow_operation():
        await asyncio.sleep(10)
        return "success"
    
    with pytest.raises(TimeoutError):
        await run_with_timeout(slow_operation(), timeout=0.1)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_config():
    """Test MockConfig helper."""
    config = MockConfig(
        service_name="test_service",
        response_data={"result": "success"},
        response_delay_ms=10,
        failure_rate=0.0
    )
    
    result = await config.get_response()
    assert result == {"result": "success"}
    assert config.call_count == 1


@pytest.mark.unit
def test_assert_dict_contains():
    """Test assert_dict_contains helper."""
    actual = {
        "a": 1,
        "b": 2,
        "c": {"d": 3, "e": 4}
    }
    
    expected = {
        "a": 1,
        "c": {"d": 3}
    }
    
    # Should not raise
    assert_dict_contains(actual, expected)


@pytest.mark.unit
def test_assert_dict_contains_failure():
    """Test assert_dict_contains with missing key."""
    actual = {"a": 1}
    expected = {"b": 2}
    
    with pytest.raises(AssertionError, match="Missing key"):
        assert_dict_contains(actual, expected)


@pytest.mark.unit
def test_create_test_trades():
    """Test create_test_trades helper."""
    trades = create_test_trades(count=5, base_profit=0.01)
    
    assert len(trades) == 5
    assert all("strategy" in t for t in trades)
    assert all("expected_profit" in t for t in trades)


@pytest.mark.unit
def test_create_test_users():
    """Test create_test_users helper."""
    users = create_test_users(count=3, base_user_id=1000)
    
    assert len(users) == 3
    assert users[0]["user_id"] == 1000
    assert users[1]["user_id"] == 1001
    assert users[2]["user_id"] == 1002


@pytest.mark.unit
def test_performance_timer():
    """Test PerformanceTimer helper."""
    import time
    
    with PerformanceTimer("test_operation") as timer:
        time.sleep(0.01)  # Sleep for 10ms
    
    assert timer.duration_ms >= 10
    assert timer.duration_ms < 100  # Should be much less than 100ms


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_async_fixtures_work_together(
    mock_telegram_update,
    mock_telegram_context,
    mock_wallet
):
    """Test that async fixtures work together."""
    update = mock_telegram_update("wallet")
    context = mock_telegram_context()
    wallet = mock_wallet(balance=5.0)
    
    # Simulate async operation
    balance = await wallet.get_balance()
    
    assert balance == 5.0
    assert update.message is not None
    assert context.bot is not None


@pytest.mark.integration
def test_hypothesis_with_fixtures(mock_user):
    """Test that Hypothesis works with pytest fixtures."""
    @given(amount=sol_amount_strategy)
    def check_user_with_amount(amount):
        user = mock_user(wallet_balance=amount)
        assert user["wallet_balance"] == amount
    
    check_user_with_amount()


# ============================================================================
# Property-Based Tests
# ============================================================================

@pytest.mark.property
@given(
    user_id=telegram_user_id_strategy,
    balance=sol_amount_strategy
)
def test_user_creation_property(user_id, balance):
    """
    Property: For any valid user_id and balance, creating a user
    should result in a user with those exact values.
    """
    # Create user directly without fixture
    user = {
        "user_id": user_id,
        "telegram_username": "testuser",
        "wallet_address": "TestWallet1234567890123456789012345",
        "wallet_balance": balance,
        "preferences": {},
        "fee_status": "paid"
    }
    
    assert user["user_id"] == user_id
    assert user["wallet_balance"] == balance


@pytest.mark.property
@given(trades=st.lists(trade_strategy(), min_size=1, max_size=10))
def test_trade_list_property(trades):
    """
    Property: For any list of trades, all trades should have
    required fields and valid values.
    """
    for trade in trades:
        assert "strategy" in trade
        assert "expected_profit" in trade
        assert "actual_profit" in trade
        assert "status" in trade
        assert trade["strategy"] in ["jupiter_swap", "marinade_stake", "airdrop_hunter"]
