"""Tests for per-user performance tracking functionality."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from agent.trading.performance import PerformanceTracker, TradeRecord


class TestPerUserPerformanceTracking:
    """Tests for per-user performance tracking (Task 5)."""
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        yield temp_path
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)
    
    @pytest.fixture
    def tracker(self, temp_storage):
        """Create tracker with temporary storage."""
        return PerformanceTracker(storage_path=temp_storage)
    
    def test_record_trade_with_user_id(self, tracker):
        """Test recording a trade with user_id (Subtask 5.1)."""
        trade = TradeRecord(
            strategy_name="test_strategy",
            timestamp=datetime.now(),
            expected_profit=0.05,
            actual_profit=0.048,
            transaction_hash="test_tx_hash",
            was_successful=True,
            error_message=None,
            gas_fees=0.002,
            execution_time_ms=1500,
            user_id="user123",
        )
        
        tracker.record_trade(trade, user_id="user123")
        
        assert len(tracker.trades) == 1
        assert tracker.trades[0].user_id == "user123"
        assert tracker.trades[0].actual_profit == 0.048
    
    def test_get_metrics_filtered_by_user(self, tracker):
        """Test getting metrics filtered by user_id (Subtask 5.3)."""
        # Record trades for user1
        for i in range(3):
            trade = TradeRecord(
                strategy_name="strategy1",
                timestamp=datetime.now(),
                expected_profit=0.05,
                actual_profit=0.01,
                transaction_hash=f"tx_user1_{i}",
                was_successful=True,
                error_message=None,
                gas_fees=0.002,
                execution_time_ms=1500,
                user_id="user1",
            )
            tracker.record_trade(trade)
        
        # Record trades for user2
        for i in range(2):
            trade = TradeRecord(
                strategy_name="strategy1",
                timestamp=datetime.now(),
                expected_profit=0.05,
                actual_profit=0.02,
                transaction_hash=f"tx_user2_{i}",
                was_successful=True,
                error_message=None,
                gas_fees=0.002,
                execution_time_ms=1500,
                user_id="user2",
            )
            tracker.record_trade(trade)
        
        # Get metrics for user1
        user1_metrics = tracker.get_metrics(user_id="user1")
        assert user1_metrics.total_trades == 3
        assert user1_metrics.total_profit == pytest.approx(0.03, rel=0.01)
        
        # Get metrics for user2
        user2_metrics = tracker.get_metrics(user_id="user2")
        assert user2_metrics.total_trades == 2
        assert user2_metrics.total_profit == pytest.approx(0.04, rel=0.01)
        
        # Get overall metrics (all users)
        all_metrics = tracker.get_metrics()
        assert all_metrics.total_trades == 5
        assert all_metrics.total_profit == pytest.approx(0.07, rel=0.01)
    
    def test_get_strategy_metrics_filtered_by_user(self, tracker):
        """Test getting strategy metrics filtered by user_id (Subtask 5.3)."""
        # Record trades for user1 with strategy1
        for i in range(2):
            trade = TradeRecord(
                strategy_name="strategy1",
                timestamp=datetime.now(),
                expected_profit=0.05,
                actual_profit=0.01,
                transaction_hash=f"tx_user1_s1_{i}",
                was_successful=True,
                error_message=None,
                gas_fees=0.002,
                execution_time_ms=1500,
                user_id="user1",
            )
            tracker.record_trade(trade)
        
        # Record trades for user2 with strategy1
        trade = TradeRecord(
            strategy_name="strategy1",
            timestamp=datetime.now(),
            expected_profit=0.05,
            actual_profit=0.03,
            transaction_hash="tx_user2_s1",
            was_successful=True,
            error_message=None,
            gas_fees=0.002,
            execution_time_ms=1500,
            user_id="user2",
        )
        tracker.record_trade(trade)
        
        # Get strategy metrics for user1
        user1_strategy_metrics = tracker.get_strategy_metrics("strategy1", user_id="user1")
        assert user1_strategy_metrics.total_trades == 2
        assert user1_strategy_metrics.total_profit == pytest.approx(0.02, rel=0.01)
        
        # Get strategy metrics for user2
        user2_strategy_metrics = tracker.get_strategy_metrics("strategy1", user_id="user2")
        assert user2_strategy_metrics.total_trades == 1
        assert user2_strategy_metrics.total_profit == pytest.approx(0.03, rel=0.01)
    
    def test_get_leaderboard(self, tracker):
        """Test getting anonymized leaderboard (Subtask 5.6)."""
        # Record trades for multiple users
        users_data = [
            ("user1", 0.05, 3, 3),  # user_id, profit_per_trade, num_trades, successful_trades
            ("user2", 0.03, 2, 2),
            ("user3", 0.08, 4, 3),
            ("user4", 0.02, 1, 1),
        ]
        
        for user_id, profit_per_trade, num_trades, successful_trades in users_data:
            for i in range(num_trades):
                trade = TradeRecord(
                    strategy_name="strategy1",
                    timestamp=datetime.now(),
                    expected_profit=0.05,
                    actual_profit=profit_per_trade,
                    transaction_hash=f"tx_{user_id}_{i}",
                    was_successful=i < successful_trades,
                    error_message=None if i < successful_trades else "Failed",
                    gas_fees=0.002,
                    execution_time_ms=1500,
                    user_id=user_id,
                )
                tracker.record_trade(trade)
        
        # Get leaderboard
        leaderboard = tracker.get_leaderboard(limit=10)
        
        # Verify leaderboard structure
        assert len(leaderboard) == 4
        assert all('rank' in entry for entry in leaderboard)
        assert all('profit' in entry for entry in leaderboard)
        assert all('win_rate' in entry for entry in leaderboard)
        
        # Verify no user IDs in leaderboard (anonymized)
        assert all('user_id' not in entry for entry in leaderboard)
        
        # Verify ranking order (by profit descending)
        assert leaderboard[0]['rank'] == 1
        assert leaderboard[0]['profit'] == pytest.approx(0.32, rel=0.01)  # user3: 0.08 * 4
        assert leaderboard[1]['rank'] == 2
        assert leaderboard[1]['profit'] == pytest.approx(0.15, rel=0.01)  # user1: 0.05 * 3
        assert leaderboard[2]['rank'] == 3
        assert leaderboard[2]['profit'] == pytest.approx(0.06, rel=0.01)  # user2: 0.03 * 2
        assert leaderboard[3]['rank'] == 4
        assert leaderboard[3]['profit'] == pytest.approx(0.02, rel=0.01)  # user4: 0.02 * 1
    
    def test_get_leaderboard_with_limit(self, tracker):
        """Test leaderboard respects limit parameter."""
        # Record trades for 5 users
        for user_num in range(5):
            trade = TradeRecord(
                strategy_name="strategy1",
                timestamp=datetime.now(),
                expected_profit=0.05,
                actual_profit=0.01 * (user_num + 1),
                transaction_hash=f"tx_user{user_num}",
                was_successful=True,
                error_message=None,
                gas_fees=0.002,
                execution_time_ms=1500,
                user_id=f"user{user_num}",
            )
            tracker.record_trade(trade)
        
        # Get top 3
        leaderboard = tracker.get_leaderboard(limit=3)
        
        assert len(leaderboard) == 3
        assert leaderboard[0]['rank'] == 1
        assert leaderboard[1]['rank'] == 2
        assert leaderboard[2]['rank'] == 3
    
    def test_get_recent_trades_filtered_by_user(self, tracker):
        """Test getting recent trades filtered by user_id."""
        # Record trades for user1
        for i in range(3):
            trade = TradeRecord(
                strategy_name="strategy1",
                timestamp=datetime.now(),
                expected_profit=0.05,
                actual_profit=0.01,
                transaction_hash=f"tx_user1_{i}",
                was_successful=True,
                error_message=None,
                gas_fees=0.002,
                execution_time_ms=1500,
                user_id="user1",
            )
            tracker.record_trade(trade)
        
        # Record trades for user2
        for i in range(2):
            trade = TradeRecord(
                strategy_name="strategy1",
                timestamp=datetime.now(),
                expected_profit=0.05,
                actual_profit=0.02,
                transaction_hash=f"tx_user2_{i}",
                was_successful=True,
                error_message=None,
                gas_fees=0.002,
                execution_time_ms=1500,
                user_id="user2",
            )
            tracker.record_trade(trade)
        
        # Get recent trades for user1
        user1_trades = tracker.get_recent_trades(count=10, user_id="user1")
        assert len(user1_trades) == 3
        assert all(t.user_id == "user1" for t in user1_trades)
        
        # Get recent trades for user2
        user2_trades = tracker.get_recent_trades(count=10, user_id="user2")
        assert len(user2_trades) == 2
        assert all(t.user_id == "user2" for t in user2_trades)
        
        # Get all recent trades
        all_trades = tracker.get_recent_trades(count=10)
        assert len(all_trades) == 5
    
    def test_user_data_isolation(self, tracker):
        """Test that user data is properly isolated (Requirement 5.2, 5.4, 7.5)."""
        # Record trades for user1
        trade1 = TradeRecord(
            strategy_name="strategy1",
            timestamp=datetime.now(),
            expected_profit=0.05,
            actual_profit=0.01,
            transaction_hash="tx_user1",
            was_successful=True,
            error_message=None,
            gas_fees=0.002,
            execution_time_ms=1500,
            user_id="user1",
        )
        tracker.record_trade(trade1)
        
        # Record trades for user2
        trade2 = TradeRecord(
            strategy_name="strategy1",
            timestamp=datetime.now(),
            expected_profit=0.05,
            actual_profit=0.02,
            transaction_hash="tx_user2",
            was_successful=True,
            error_message=None,
            gas_fees=0.002,
            execution_time_ms=1500,
            user_id="user2",
        )
        tracker.record_trade(trade2)
        
        # Verify user1 metrics don't include user2 data
        user1_metrics = tracker.get_metrics(user_id="user1")
        assert user1_metrics.total_profit == pytest.approx(0.01, rel=0.01)
        assert user1_metrics.total_trades == 1
        
        # Verify user2 metrics don't include user1 data
        user2_metrics = tracker.get_metrics(user_id="user2")
        assert user2_metrics.total_profit == pytest.approx(0.02, rel=0.01)
        assert user2_metrics.total_trades == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
