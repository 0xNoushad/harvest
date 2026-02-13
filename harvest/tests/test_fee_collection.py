"""
Test suite for fee collection functionality.

This module tests fee collection features including:
- Fee calculation on net profit (Property 21)
- Fee payment flows (Properties 22, 23, 24)
- Overdue fee handling (Properties 25, 26, 27)

Tests validate Requirements 4.1-4.10 from the requirements document.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st, settings, assume
from pathlib import Path
import json
import tempfile

from agent.monitoring.monthly_fees import MonthlyFeeCollector
from agent.trading.performance import PerformanceTracker, TradeRecord
from agent.services.user_manager import UserManager
from tests.test_harness import TestHarness


# ============================================================================
# Test Fixtures
# ============================================================================

def create_test_trade(
    strategy_name: str = "jupiter_swap",
    expected_profit: float = 1.0,
    actual_profit: float = 1.0,
    timestamp: datetime = None,
    was_successful: bool = True
) -> TradeRecord:
    """Helper function to create test TradeRecord objects."""
    return TradeRecord(
        strategy_name=strategy_name,
        expected_profit=expected_profit,
        actual_profit=actual_profit,
        was_successful=was_successful,
        timestamp=timestamp or datetime.now(),
        transaction_hash=f"sig_{strategy_name}",
        error_message=None if was_successful else "Test error",
        gas_fees=0.0001,
        execution_time_ms=1000
    )


@pytest.fixture
def temp_storage():
    """Create a temporary storage file for fee history."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    yield temp_path
    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def mock_user_manager():
    """Create a mock UserManager."""
    manager = MagicMock()
    manager.get_all_users = MagicMock(return_value=["user1", "user2"])
    manager.get_user_wallet = MagicMock()
    return manager


@pytest.fixture
def mock_performance_tracker():
    """Create a mock PerformanceTracker with trade history."""
    tracker = MagicMock()
    tracker.get_recent_trades = MagicMock(return_value=[])
    return tracker


@pytest.fixture
def fee_collector(mock_user_manager, mock_performance_tracker, temp_storage):
    """Create a MonthlyFeeCollector instance for testing."""
    # Use a valid-looking Solana address (44 characters, base58)
    platform_wallet = "11111111111111111111111111111111111111111111"
    collector = MonthlyFeeCollector(
        user_manager=mock_user_manager,
        performance_tracker=mock_performance_tracker,
        platform_wallet=platform_wallet,
        storage_path=temp_storage
    )
    return collector


# ============================================================================
# Subtask 10.1: Fee Calculation Tests (Property 21)
# ============================================================================

@pytest.mark.asyncio
class TestFeeCalculation:
    """
    Tests for fee calculation on net profit.
    
    **Validates: Property 21, Requirements 4.1, 4.10**
    
    Property 21: For any user profit amount, the calculated platform fee 
    should be exactly 2% of net profit (profit minus transaction costs).
    """
    
    async def test_fee_calculation_on_positive_profit(self, fee_collector, mock_performance_tracker):
        """
        Test fee calculation when user has positive profit.
        
        Fee should be exactly 2% of net profit.
        """
        # Setup: User made 10 SOL profit this month
        trades = [
            create_test_trade(strategy_name="jupiter_swap", actual_profit=5.0, expected_profit=5.0),
            create_test_trade(strategy_name="marinade_stake", actual_profit=5.0, expected_profit=5.0)
        ]
        mock_performance_tracker.get_recent_trades.return_value = trades
        
        # Calculate fee
        fee = fee_collector.calculate_monthly_fee("user1")
        
        # Assert: 2% of 10 SOL = 0.2 SOL
        assert fee == 0.2, f"Expected 0.2 SOL fee, got {fee}"
    
    async def test_fee_calculation_on_zero_profit(self, fee_collector, mock_performance_tracker):
        """
        Test fee calculation when user has zero profit.
        
        No fee should be charged on zero profit.
        """
        # Setup: No trades or break-even trades
        mock_performance_tracker.get_recent_trades.return_value = []
        
        # Calculate fee
        fee = fee_collector.calculate_monthly_fee("user1")
        
        # Assert: No fee on zero profit
        assert fee == 0.0, f"Expected 0.0 SOL fee, got {fee}"
    
    async def test_fee_calculation_on_negative_profit(self, fee_collector, mock_performance_tracker):
        """
        Test fee calculation when user has losses.
        
        No fee should be charged on losses.
        """
        # Setup: User lost 5 SOL this month
        trades = [
            create_test_trade(strategy_name="jupiter_swap", actual_profit=-5.0, expected_profit=2.0)
        ]
        mock_performance_tracker.get_recent_trades.return_value = trades
        
        # Calculate fee
        fee = fee_collector.calculate_monthly_fee("user1")
        
        # Assert: No fee on losses
        assert fee == 0.0, f"Expected 0.0 SOL fee on loss, got {fee}"
    
    async def test_fee_calculation_with_mixed_trades(self, fee_collector, mock_performance_tracker):
        """
        Test fee calculation with both winning and losing trades.
        
        Fee should be 2% of net profit (sum of all trades).
        """
        # Setup: Mixed trades with net profit of 3 SOL
        trades = [
            create_test_trade(strategy_name="jupiter_swap", actual_profit=5.0, expected_profit=5.0),
            create_test_trade(strategy_name="marinade_stake", actual_profit=-2.0, expected_profit=2.0)
        ]
        mock_performance_tracker.get_recent_trades.return_value = trades
        
        # Calculate fee
        fee = fee_collector.calculate_monthly_fee("user1")
        
        # Assert: 2% of 3 SOL net profit = 0.06 SOL
        assert fee == 0.06, f"Expected 0.06 SOL fee, got {fee}"
    
    async def test_fee_rate_is_exactly_2_percent(self, fee_collector):
        """
        Test that the fee rate constant is exactly 2%.
        """
        assert fee_collector.FEE_RATE == 0.02, f"Expected fee rate 0.02, got {fee_collector.FEE_RATE}"
    
    async def test_get_monthly_profit_filters_by_month(self, fee_collector, mock_performance_tracker):
        """
        Test that monthly profit calculation only includes trades from specified month.
        """
        # Setup: Trades from different months
        current_month = datetime.now()
        last_month = current_month - timedelta(days=35)
        
        trades = [
            create_test_trade(strategy_name="jupiter_swap", actual_profit=5.0, expected_profit=5.0, timestamp=current_month),
            create_test_trade(strategy_name="marinade_stake", actual_profit=3.0, expected_profit=3.0, timestamp=last_month)
        ]
        mock_performance_tracker.get_recent_trades.return_value = trades
        
        # Get profit for current month
        profit = fee_collector.get_monthly_profit("user1", current_month)
        
        # Assert: Only current month's trade (5 SOL)
        assert profit == 5.0, f"Expected 5.0 SOL profit, got {profit}"


# ============================================================================
# Property-Based Test for Fee Calculation (Property 21)
# ============================================================================

@pytest.mark.asyncio
class TestFeeCalculationProperty:
    """
    Property-based tests for fee calculation.
    
    **Validates: Property 21**
    """
    
    @given(
        profit=st.floats(min_value=0.01, max_value=1000.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50, deadline=None)
    async def test_fee_is_always_2_percent_of_profit(self, profit):
        """
        Property: For any positive profit, fee should always be exactly 2% of that profit.
        
        **Validates: Property 21**
        """
        # Create fresh instances for each test
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            mock_user_manager = MagicMock()
            mock_performance_tracker = MagicMock()
            
            # Setup: Create trade with given profit
            trades = [
                create_test_trade(strategy_name="test_strategy", actual_profit=profit, expected_profit=profit)
            ]
            mock_performance_tracker.get_recent_trades.return_value = trades
            
            fee_collector = MonthlyFeeCollector(
                user_manager=mock_user_manager,
                performance_tracker=mock_performance_tracker,
                platform_wallet="11111111111111111111111111111111111111111111",
                storage_path=temp_path
            )
            
            # Calculate fee
            fee = fee_collector.calculate_monthly_fee("user1")
            
            # Property: fee = profit * 0.02
            expected_fee = profit * 0.02
            assert abs(fee - expected_fee) < 0.0001, f"Expected {expected_fee} SOL fee, got {fee}"
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    @given(
        loss=st.floats(min_value=-1000.0, max_value=-0.01, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50, deadline=None)
    async def test_no_fee_on_any_loss(self, loss):
        """
        Property: For any loss amount, fee should always be zero.
        
        **Validates: Property 21**
        """
        # Create fresh instances for each test
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            mock_user_manager = MagicMock()
            mock_performance_tracker = MagicMock()
            
            # Setup: Create trade with loss
            trades = [
                create_test_trade(strategy_name="test_strategy", actual_profit=loss, expected_profit=abs(loss))
            ]
            mock_performance_tracker.get_recent_trades.return_value = trades
            
            fee_collector = MonthlyFeeCollector(
                user_manager=mock_user_manager,
                performance_tracker=mock_performance_tracker,
                platform_wallet="11111111111111111111111111111111111111111111",
                storage_path=temp_path
            )
            
            # Calculate fee
            fee = fee_collector.calculate_monthly_fee("user1")
            
            # Property: No fee on losses
            assert fee == 0.0, f"Expected 0.0 SOL fee on loss, got {fee}"
        finally:
            Path(temp_path).unlink(missing_ok=True)



# ============================================================================
# Subtask 10.2: Fee Payment Flow Tests (Properties 22, 23, 24)
# ============================================================================

@pytest.mark.asyncio
class TestFeePaymentFlows:
    """
    Tests for fee payment flows including approval, decline, and execution.
    
    **Validates: Properties 22, 23, 24, Requirements 4.2-4.6**
    """
    
    async def test_request_fee_approval_creates_pending_approval(self, fee_collector, mock_performance_tracker):
        """
        Test that requesting fee approval creates a pending approval record.
        
        **Validates: Property 22, Requirement 4.2**
        """
        # Setup: User has profit
        trades = [
            create_test_trade(
                strategy_name="jupiter_swap",
                expected_profit=10.0,
                actual_profit=10.0,
                timestamp=datetime.now(),
            )
        ]
        mock_performance_tracker.get_recent_trades.return_value = trades
        
        # Request fee approval
        result = fee_collector.request_fee_approval("user1", datetime.now())
        
        # Assert: Pending approval created
        assert result["status"] == "pending"
        assert result["user_id"] == "user1"
        assert result["fee_amount"] == 0.2  # 2% of 10 SOL
        assert result["monthly_profit"] == 10.0
        assert result["fee_rate"] == 0.02
        assert "requested_at" in result
        assert "expires_at" in result
    
    async def test_request_fee_approval_no_fee_when_no_profit(self, fee_collector, mock_performance_tracker):
        """
        Test that no fee is requested when user has no profit.
        
        **Validates: Property 22**
        """
        # Setup: No profit
        mock_performance_tracker.get_recent_trades.return_value = []
        
        # Request fee approval
        result = fee_collector.request_fee_approval("user1", datetime.now())
        
        # Assert: No fee required
        assert result["status"] == "no_fee_required"
    
    async def test_request_fee_approval_has_grace_period(self, fee_collector, mock_performance_tracker):
        """
        Test that fee approval request includes grace period.
        
        **Validates: Property 22**
        """
        # Setup: User has profit
        trades = [
            create_test_trade(
                strategy_name="jupiter_swap",
                expected_profit=5.0,
                actual_profit=5.0,
                timestamp=datetime.now(),
            )
        ]
        mock_performance_tracker.get_recent_trades.return_value = trades
        
        # Request fee approval
        result = fee_collector.request_fee_approval("user1", datetime.now())
        
        # Assert: Grace period is 7 days
        requested_at = datetime.fromisoformat(result["requested_at"])
        expires_at = datetime.fromisoformat(result["expires_at"])
        grace_period = (expires_at - requested_at).days
        
        assert grace_period == 7, f"Expected 7 day grace period, got {grace_period}"
    
    @patch('asyncio.get_event_loop')
    async def test_approve_fee_executes_payment(self, mock_loop, fee_collector, mock_user_manager, mock_performance_tracker):
        """
        Test that approving fee executes the payment transaction.
        
        **Validates: Property 23, Requirements 4.3, 4.5**
        """
        # Setup: Create pending approval
        trades = [
            create_test_trade(
                strategy_name="jupiter_swap",
                expected_profit=10.0,
                actual_profit=10.0,
                timestamp=datetime.now(),
            )
        ]
        mock_performance_tracker.get_recent_trades.return_value = trades
        fee_collector.request_fee_approval("user1", datetime.now())
        
        # Mock wallet
        mock_wallet = MagicMock()
        mock_wallet.send_sol = AsyncMock(return_value="tx_signature_123")
        mock_user_manager.get_user_wallet.return_value = mock_wallet
        
        # Mock event loop
        mock_loop_instance = MagicMock()
        mock_loop_instance.run_until_complete = MagicMock(return_value="tx_signature_123")
        mock_loop.return_value = mock_loop_instance
        
        # Approve fee
        result = fee_collector.approve_fee("user1")
        
        # Assert: Payment executed successfully
        assert result["status"] == "collected"
        assert result["fee_amount"] == 0.2
        assert result["transaction_hash"] == "tx_signature_123"
        assert "collected_at" in result
    
    @patch('asyncio.get_event_loop')
    async def test_approve_fee_marks_user_as_paid(self, mock_loop, fee_collector, mock_user_manager, mock_performance_tracker):
        """
        Test that approving fee marks user as paid and removes pending approval.
        
        **Validates: Property 23, Requirement 4.5**
        """
        # Setup: Create pending approval
        trades = [
            create_test_trade(
                strategy_name="jupiter_swap",
                expected_profit=10.0,
                actual_profit=10.0,
                timestamp=datetime.now(),
            )
        ]
        mock_performance_tracker.get_recent_trades.return_value = trades
        fee_collector.request_fee_approval("user1", datetime.now())
        
        # Mock wallet
        mock_wallet = MagicMock()
        mock_wallet.send_sol = AsyncMock(return_value="tx_signature_123")
        mock_user_manager.get_user_wallet.return_value = mock_wallet
        
        # Mock event loop
        mock_loop_instance = MagicMock()
        mock_loop_instance.run_until_complete = MagicMock(return_value="tx_signature_123")
        mock_loop.return_value = mock_loop_instance
        
        # Approve fee
        fee_collector.approve_fee("user1")
        
        # Assert: User marked as paid
        status = fee_collector.get_user_status("user1")
        assert status["payment_status"]["paid"] == True
        assert status["has_pending_fee"] == False
    
    async def test_approve_fee_fails_when_no_pending_approval(self, fee_collector):
        """
        Test that approving fee fails when there's no pending approval.
        
        **Validates: Property 23**
        """
        # Approve fee without pending approval
        result = fee_collector.approve_fee("user1")
        
        # Assert: Error returned
        assert result["status"] == "error"
        assert "No pending fee approval" in result["message"]
    
    async def test_approve_fee_fails_when_expired(self, fee_collector, mock_performance_tracker):
        """
        Test that approving fee fails when grace period has expired.
        
        **Validates: Property 23**
        """
        # Use a different user to avoid rate limiting from previous tests
        user_id = "user_expired_test"
        
        # Setup: Create pending approval
        trades = [
            create_test_trade(
                strategy_name="jupiter_swap",
                expected_profit=10.0,
                actual_profit=10.0,
                timestamp=datetime.now(),
            )
        ]
        mock_performance_tracker.get_recent_trades.return_value = trades
        fee_collector.request_fee_approval(user_id, datetime.now())
        
        # Manually expire the approval
        approval = fee_collector.fee_history["pending_approvals"][user_id]
        approval["expires_at"] = (datetime.now() - timedelta(days=1)).isoformat()
        
        # Approve fee
        result = fee_collector.approve_fee(user_id)
        
        # Assert: Expired
        assert result["status"] == "expired"
    
    async def test_decline_fee_pauses_bot(self, fee_collector, mock_performance_tracker):
        """
        Test that declining fee pauses the bot for next month.
        
        **Validates: Property 24, Requirement 4.4**
        """
        # Setup: Create pending approval
        trades = [
            create_test_trade(
                strategy_name="jupiter_swap",
                expected_profit=10.0,
                actual_profit=10.0,
                timestamp=datetime.now(),
            )
        ]
        mock_performance_tracker.get_recent_trades.return_value = trades
        fee_collector.request_fee_approval("user1", datetime.now())
        
        # Decline fee
        result = fee_collector.decline_fee("user1")
        
        # Assert: Bot paused
        assert result["status"] == "declined"
        assert "paused_until" in result
        assert "Pay fee to resume" in result["message"]
    
    async def test_decline_fee_keeps_pending_approval(self, fee_collector, mock_performance_tracker):
        """
        Test that declining fee keeps the pending approval (user can pay later).
        
        **Validates: Property 24**
        """
        # Setup: Create pending approval
        trades = [
            create_test_trade(
                strategy_name="jupiter_swap",
                expected_profit=10.0,
                actual_profit=10.0,
                timestamp=datetime.now(),
            )
        ]
        mock_performance_tracker.get_recent_trades.return_value = trades
        fee_collector.request_fee_approval("user1", datetime.now())
        
        # Decline fee
        fee_collector.decline_fee("user1")
        
        # Assert: Pending approval still exists but marked as declined
        assert "user1" in fee_collector.fee_history["pending_approvals"]
        assert fee_collector.fee_history["pending_approvals"]["user1"]["status"] == "declined"
    
    async def test_decline_fee_records_unpaid_amount(self, fee_collector, mock_performance_tracker):
        """
        Test that declining fee records the unpaid fee amount.
        
        **Validates: Property 24**
        """
        # Setup: Create pending approval
        trades = [
            create_test_trade(
                strategy_name="jupiter_swap",
                expected_profit=10.0,
                actual_profit=10.0,
                timestamp=datetime.now(),
            )
        ]
        mock_performance_tracker.get_recent_trades.return_value = trades
        fee_collector.request_fee_approval("user1", datetime.now())
        
        # Decline fee
        fee_collector.decline_fee("user1")
        
        # Assert: Unpaid fee recorded
        payment_status = fee_collector.fee_history["payment_status"]["user1"]
        assert payment_status["unpaid_fee"] == 0.2
        assert payment_status["paid"] == False
        assert payment_status["paused"] == True



# ============================================================================
# Subtask 10.3: Overdue Fee Handling Tests (Properties 25, 26, 27)
# ============================================================================

@pytest.mark.asyncio
class TestOverdueFeeHandling:
    """
    Tests for overdue fee handling.
    
    **Validates: Properties 25, 26, 27, Requirements 4.7-4.9**
    """
    
    async def test_get_user_status_shows_unpaid_fees(self, fee_collector, mock_performance_tracker):
        """
        Test that user status displays unpaid fees.
        
        **Validates: Property 25, Requirement 4.7**
        """
        # Use unique user ID
        user_id = "user_status_unpaid"
        
        # Setup: Create and decline fee
        trades = [
            create_test_trade(
                strategy_name="jupiter_swap",
                expected_profit=10.0,
                actual_profit=10.0,
                timestamp=datetime.now(),
            )
        ]
        mock_performance_tracker.get_recent_trades.return_value = trades
        fee_collector.request_fee_approval(user_id, datetime.now())
        fee_collector.decline_fee(user_id)
        
        # Get user status
        status = fee_collector.get_user_status(user_id)
        
        # Assert: Unpaid fee shown
        assert status["has_pending_fee"] == True
        assert status["pending_fee"]["fee_amount"] == 0.2
        assert status["payment_status"]["unpaid_fee"] == 0.2
    
    async def test_is_user_active_returns_false_when_paused(self, fee_collector, mock_performance_tracker):
        """
        Test that user is marked as inactive when paused for unpaid fees.
        
        **Validates: Property 26, Requirement 4.8**
        """
        # Use unique user ID
        user_id = "user_active_paused"
        
        # Setup: Create and decline fee
        trades = [
            create_test_trade(
                strategy_name="jupiter_swap",
                expected_profit=10.0,
                actual_profit=10.0,
                timestamp=datetime.now(),
            )
        ]
        mock_performance_tracker.get_recent_trades.return_value = trades
        fee_collector.request_fee_approval(user_id, datetime.now())
        fee_collector.decline_fee(user_id)
        
        # Check if user is active
        is_active = fee_collector.is_user_active(user_id)
        
        # Assert: User is not active (paused)
        assert is_active == False
    
    async def test_is_user_active_returns_false_after_pause_expires_with_unpaid_fee(self, fee_collector, mock_performance_tracker):
        """
        Test that user remains inactive even after pause period expires if fee is still unpaid.
        
        **Validates: Property 26, Requirement 4.8**
        """
        # Use unique user ID
        user_id = "user_pause_expired"
        
        # Setup: Create and decline fee
        trades = [
            create_test_trade(
                strategy_name="jupiter_swap",
                expected_profit=10.0,
                actual_profit=10.0,
                timestamp=datetime.now(),
            )
        ]
        mock_performance_tracker.get_recent_trades.return_value = trades
        fee_collector.request_fee_approval(user_id, datetime.now())
        fee_collector.decline_fee(user_id)
        
        # Manually expire the pause period
        payment_status = fee_collector.fee_history["payment_status"][user_id]
        payment_status["paused_until"] = (datetime.now() - timedelta(days=1)).isoformat()
        
        # Check if user is active
        is_active = fee_collector.is_user_active(user_id)
        
        # Assert: User still not active (fee unpaid)
        assert is_active == False
    
    @patch('asyncio.get_event_loop')
    async def test_paying_overdue_fee_resumes_trading(self, mock_loop, fee_collector, mock_user_manager, mock_performance_tracker):
        """
        Test that paying overdue fee resumes trading.
        
        **Validates: Property 27, Requirement 4.9**
        """
        # Use unique user ID to avoid rate limiting
        user_id = "user_overdue_resume"
        
        # Setup: Create and decline fee (making it overdue)
        trades = [
            create_test_trade(
                strategy_name="jupiter_swap",
                expected_profit=10.0,
                actual_profit=10.0,
                timestamp=datetime.now(),
            )
        ]
        mock_performance_tracker.get_recent_trades.return_value = trades
        fee_collector.request_fee_approval(user_id, datetime.now())
        fee_collector.decline_fee(user_id)
        
        # Verify user is paused
        assert fee_collector.is_user_active(user_id) == False
        
        # Mock wallet
        mock_wallet = MagicMock()
        mock_wallet.send_sol = AsyncMock(return_value="tx_signature_123")
        mock_user_manager.get_user_wallet.return_value = mock_wallet
        
        # Mock event loop
        mock_loop_instance = MagicMock()
        mock_loop_instance.run_until_complete = MagicMock(return_value="tx_signature_123")
        mock_loop.return_value = mock_loop_instance
        
        # Pay the overdue fee
        result = fee_collector.approve_fee(user_id)
        
        # Assert: Payment successful and user is active again
        assert result["status"] == "collected"
        assert fee_collector.is_user_active(user_id) == True
    
    @patch('asyncio.get_event_loop')
    async def test_paying_overdue_fee_clears_overdue_status(self, mock_loop, fee_collector, mock_user_manager, mock_performance_tracker):
        """
        Test that paying overdue fee clears the overdue status.
        
        **Validates: Property 27, Requirement 4.9**
        """
        # Use unique user ID
        user_id = "user_overdue_clear"
        
        # Setup: Create and decline fee
        trades = [
            create_test_trade(
                strategy_name="jupiter_swap",
                expected_profit=10.0,
                actual_profit=10.0,
                timestamp=datetime.now(),
            )
        ]
        mock_performance_tracker.get_recent_trades.return_value = trades
        fee_collector.request_fee_approval(user_id, datetime.now())
        fee_collector.decline_fee(user_id)
        
        # Mock wallet
        mock_wallet = MagicMock()
        mock_wallet.send_sol = AsyncMock(return_value="tx_signature_123")
        mock_user_manager.get_user_wallet.return_value = mock_wallet
        
        # Mock event loop
        mock_loop_instance = MagicMock()
        mock_loop_instance.run_until_complete = MagicMock(return_value="tx_signature_123")
        mock_loop.return_value = mock_loop_instance
        
        # Pay the overdue fee
        fee_collector.approve_fee(user_id)
        
        # Assert: Overdue status cleared
        status = fee_collector.get_user_status(user_id)
        assert status["payment_status"]["paid"] == True
        assert status["payment_status"]["paused"] == False
        assert status["has_pending_fee"] == False
    
    async def test_overdue_fee_after_7_days_pauses_trading(self, fee_collector, mock_performance_tracker):
        """
        Test that fee overdue by 7+ days results in paused trading.
        
        **Validates: Property 26, Requirement 4.8**
        
        Note: The grace period is 7 days, so declining immediately starts the pause.
        """
        # Use unique user ID to avoid rate limiting
        user_id = "user_overdue_7days"
        
        # Setup: Create and decline fee
        trades = [
            create_test_trade(
                strategy_name="jupiter_swap",
                expected_profit=10.0,
                actual_profit=10.0,
                timestamp=datetime.now(),
            )
        ]
        mock_performance_tracker.get_recent_trades.return_value = trades
        fee_collector.request_fee_approval(user_id, datetime.now())
        
        # Decline fee (starts 30-day pause)
        result = fee_collector.decline_fee(user_id)
        
        # Assert: Trading paused
        assert result["status"] == "declined"
        assert fee_collector.is_user_active(user_id) == False
        
        # Verify pause duration is approximately 30 days
        paused_until = datetime.fromisoformat(result["paused_until"])
        days_paused = (paused_until - datetime.now()).days
        assert 29 <= days_paused <= 30, f"Expected ~30 day pause, got {days_paused}"


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
class TestFeeCollectionIntegration:
    """
    Integration tests for complete fee collection workflows.
    """
    
    async def test_complete_fee_approval_workflow(self, fee_collector, mock_user_manager, mock_performance_tracker):
        """
        Test complete workflow: request -> approve -> collect.
        """
        # Use unique user ID
        user_id = "user_integration_approve"
        
        # Setup: User has profit
        trades = [
            create_test_trade(
                strategy_name="jupiter_swap",
                expected_profit=10.0,
                actual_profit=10.0,
                timestamp=datetime.now(),
            )
        ]
        mock_performance_tracker.get_recent_trades.return_value = trades
        
        # Step 1: Request fee approval
        request_result = fee_collector.request_fee_approval(user_id, datetime.now())
        assert request_result["status"] == "pending"
        assert request_result["fee_amount"] == 0.2
        
        # Step 2: Mock wallet and approve
        mock_wallet = MagicMock()
        mock_wallet.send_sol = AsyncMock(return_value="tx_signature_123")
        mock_user_manager.get_user_wallet.return_value = mock_wallet
        
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop_instance = MagicMock()
            mock_loop_instance.run_until_complete = MagicMock(return_value="tx_signature_123")
            mock_loop.return_value = mock_loop_instance
            
            approve_result = fee_collector.approve_fee(user_id)
        
        # Step 3: Verify collection
        assert approve_result["status"] == "collected"
        assert approve_result["transaction_hash"] == "tx_signature_123"
        assert fee_collector.is_user_active(user_id) == True
    
    async def test_complete_fee_decline_workflow(self, fee_collector, mock_performance_tracker):
        """
        Test complete workflow: request -> decline -> pause.
        """
        # Use unique user ID
        user_id = "user_integration_decline"
        
        # Setup: User has profit
        trades = [
            create_test_trade(
                strategy_name="jupiter_swap",
                expected_profit=10.0,
                actual_profit=10.0,
                timestamp=datetime.now(),
            )
        ]
        mock_performance_tracker.get_recent_trades.return_value = trades
        
        # Step 1: Request fee approval
        request_result = fee_collector.request_fee_approval(user_id, datetime.now())
        assert request_result["status"] == "pending"
        
        # Step 2: Decline fee
        decline_result = fee_collector.decline_fee(user_id)
        assert decline_result["status"] == "declined"
        
        # Step 3: Verify pause
        assert fee_collector.is_user_active(user_id) == False
        status = fee_collector.get_user_status(user_id)
        assert status["payment_status"]["paused"] == True
    
    async def test_request_all_fees_for_multiple_users(self, fee_collector, mock_user_manager, mock_performance_tracker):
        """
        Test requesting fees from all users at once.
        """
        # Setup: Multiple users with different profit levels
        mock_user_manager.get_all_users.return_value = ["user1", "user2", "user3"]
        
        # User1: Has profit
        # User2: Has profit
        # User3: No profit
        def get_trades_for_user(limit):
            # This is a simplified mock - in reality would filter by user
            return [
                create_test_trade(
                    strategy_name="jupiter_swap",
                    expected_profit=10.0,
                    actual_profit=10.0,
                    timestamp=datetime.now(),
                )
            ]
        
        mock_performance_tracker.get_recent_trades.side_effect = [
            get_trades_for_user(1000),  # user1
            get_trades_for_user(1000),  # user2
            []  # user3 - no trades
        ]
        
        # Request fees from all users
        results = fee_collector.request_all_fees()
        
        # Assert: Requests sent to all users
        assert len(results) == 3
