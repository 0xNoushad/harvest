"""Tests for performance tracking functionality."""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime

from agent.trading.performance import PerformanceTracker, TradeRecord, StrategyMetrics


class TestTradeRecord:
    """Tests for TradeRecord data model."""
    
    def test_trade_record_creation(self):
        """Test creating a trade record."""
        record = TradeRecord(
            strategy_name="test_strategy",
            timestamp=datetime.now(),
            expected_profit=0.05,
            actual_profit=0.048,
            transaction_hash="test_tx_hash",
            was_successful=True,
            error_message=None,
            gas_fees=0.002,
            execution_time_ms=1500,
        )
        
        assert record.strategy_name == "test_strategy"
        assert record.expected_profit == 0.05
        assert record.actual_profit == 0.048
        assert record.transaction_hash == "test_tx_hash"
        assert record.was_successful is True
        assert record.gas_fees == 0.002
        assert record.execution_time_ms == 1500
    
    def test_trade_record_to_dict(self):
        """Test converting record to dictionary."""
        timestamp = datetime.now()
        record = TradeRecord(
            strategy_name="test_strategy",
            timestamp=timestamp,
            expected_profit=0.05,
            actual_profit=0.048,
            transaction_hash="test_tx_hash",
            was_successful=True,
            error_message=None,
            gas_fees=0.002,
            execution_time_ms=1500,
        )
        
        data = record.to_dict()
        
        assert data["strategy_name"] == "test_strategy"
        assert data["timestamp"] == timestamp.isoformat()
        assert data["expected_profit"] == 0.05
        assert data["actual_profit"] == 0.048
        assert data["transaction_hash"] == "test_tx_hash"
        assert data["was_successful"] is True
        assert data["gas_fees"] == 0.002
        assert data["execution_time_ms"] == 1500
    
    def test_trade_record_from_dict(self):
        """Test creating record from dictionary."""
        timestamp = datetime.now()
        data = {
            "strategy_name": "test_strategy",
            "timestamp": timestamp.isoformat(),
            "expected_profit": 0.05,
            "actual_profit": 0.048,
            "transaction_hash": "test_tx_hash",
            "was_successful": True,
            "error_message": None,
            "gas_fees": 0.002,
            "execution_time_ms": 1500,
        }
        
        record = TradeRecord.from_dict(data)
        
        assert record.strategy_name == "test_strategy"
        assert record.timestamp == timestamp
        assert record.expected_profit == 0.05
        assert record.actual_profit == 0.048
        assert record.transaction_hash == "test_tx_hash"
        assert record.was_successful is True
        assert record.gas_fees == 0.002
        assert record.execution_time_ms == 1500


class TestPerformanceTracker:
    """Tests for PerformanceTracker."""
    
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
    
    def test_tracker_initialization(self, tracker):
        """Test tracker initialization."""
        assert tracker.trades == []
    
    def test_record_trade(self, tracker):
        """Test recording a trade (Requirement 5.1, 10.2)."""
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
        )
        
        tracker.record_trade(trade)
        
        assert len(tracker.trades) == 1
        assert tracker.trades[0].strategy_name == "test_strategy"
        assert tracker.trades[0].actual_profit == 0.048
    
    def test_get_recent_trades(self, tracker):
        """Test getting recent trades (Requirement 5.1, 10.2)."""
        # Record trades
        for i in range(5):
            trade = TradeRecord(
                strategy_name=f"strategy{i}",
                timestamp=datetime.now(),
                expected_profit=0.05,
                actual_profit=0.048,
                transaction_hash=f"tx{i}",
                was_successful=True,
                error_message=None,
                gas_fees=0.002,
                execution_time_ms=1500,
            )
            tracker.record_trade(trade)
        
        recent = tracker.get_recent_trades(count=3)
        
        assert len(recent) == 3
        # Should be in reverse chronological order
        assert recent[0].transaction_hash == "tx4"
        assert recent[1].transaction_hash == "tx3"
        assert recent[2].transaction_hash == "tx2"
    
    def test_get_strategy_metrics(self, tracker):
        """Test getting metrics for specific strategy (Requirement 5.2)."""
        # Record trades for strategy1
        for i in range(3):
            trade = TradeRecord(
                strategy_name="strategy1",
                timestamp=datetime.now(),
                expected_profit=0.05,
                actual_profit=0.01 if i < 2 else -0.005,  # 2 wins, 1 loss
                transaction_hash=f"tx{i}",
                was_successful=i < 2,
                error_message=None if i < 2 else "Failed",
                gas_fees=0.002,
                execution_time_ms=1500,
            )
            tracker.record_trade(trade)
        
        # Record trade for strategy2
        trade = TradeRecord(
            strategy_name="strategy2",
            timestamp=datetime.now(),
            expected_profit=0.05,
            actual_profit=0.015,
            transaction_hash="tx3",
            was_successful=True,
            error_message=None,
            gas_fees=0.002,
            execution_time_ms=1500,
        )
        tracker.record_trade(trade)
        
        metrics = tracker.get_strategy_metrics("strategy1")
        
        assert metrics.strategy_name == "strategy1"
        assert metrics.total_trades == 3
        assert metrics.successful_trades == 2
        assert metrics.total_profit == pytest.approx(0.015, rel=0.01)  # 0.01 + 0.01 - 0.005
        assert metrics.average_profit == pytest.approx(0.005, rel=0.01)  # 0.015 / 3
        assert metrics.win_rate == pytest.approx(66.67, rel=0.01)  # 2 out of 3
        assert metrics.total_gas_fees == pytest.approx(0.006, rel=0.01)  # 0.002 * 3
    
    def test_get_strategy_metrics_nonexistent(self, tracker):
        """Test getting metrics for strategy with no trades."""
        metrics = tracker.get_strategy_metrics("nonexistent")
        
        assert metrics.strategy_name == "nonexistent"
        assert metrics.total_trades == 0
        assert metrics.successful_trades == 0
        assert metrics.total_profit == 0.0
        assert metrics.average_profit == 0.0
        assert metrics.win_rate == 0.0
        assert metrics.total_gas_fees == 0.0
    
    def test_get_all_metrics(self, tracker):
        """Test getting metrics for all strategies (Requirement 5.2)."""
        # Record trades for multiple strategies
        for strategy_num in range(2):
            for i in range(2):
                trade = TradeRecord(
                    strategy_name=f"strategy{strategy_num}",
                    timestamp=datetime.now(),
                    expected_profit=0.05,
                    actual_profit=0.01,
                    transaction_hash=f"tx{strategy_num}_{i}",
                    was_successful=True,
                    error_message=None,
                    gas_fees=0.002,
                    execution_time_ms=1500,
                )
                tracker.record_trade(trade)
        
        all_metrics = tracker.get_all_metrics()
        
        assert len(all_metrics) == 2
        assert "strategy0" in all_metrics
        assert "strategy1" in all_metrics
        assert all_metrics["strategy0"].total_trades == 2
        assert all_metrics["strategy1"].total_trades == 2
    
    def test_calculate_roi(self, tracker):
        """Test calculating ROI (Requirement 10.5)."""
        initial_balance = 1.0  # 1 SOL
        
        # Record trades with profits
        for i in range(3):
            trade = TradeRecord(
                strategy_name="strategy1",
                timestamp=datetime.now(),
                expected_profit=0.05,
                actual_profit=0.02,  # 0.02 SOL profit each
                transaction_hash=f"tx{i}",
                was_successful=True,
                error_message=None,
                gas_fees=0.002,
                execution_time_ms=1500,
            )
            tracker.record_trade(trade)
        
        roi = tracker.calculate_roi(initial_balance)
        
        # Total profit = 0.06 SOL, ROI = (1.06 - 1.0) / 1.0 * 100 = 6%
        assert roi == pytest.approx(6.0, rel=0.01)
    
    def test_calculate_roi_zero_balance(self, tracker):
        """Test ROI calculation with zero initial balance."""
        roi = tracker.calculate_roi(0.0)
        assert roi == 0.0
    
    def test_persistence_save_and_load(self, temp_storage):
        """Test saving and loading from storage (Requirement 5.5)."""
        # Create tracker and record trades
        tracker1 = PerformanceTracker(storage_path=temp_storage)
        trade1 = TradeRecord(
            strategy_name="strategy1",
            timestamp=datetime.now(),
            expected_profit=0.05,
            actual_profit=0.048,
            transaction_hash="tx1",
            was_successful=True,
            error_message=None,
            gas_fees=0.002,
            execution_time_ms=1500,
        )
        trade2 = TradeRecord(
            strategy_name="strategy2",
            timestamp=datetime.now(),
            expected_profit=0.03,
            actual_profit=0.028,
            transaction_hash="tx2",
            was_successful=True,
            error_message=None,
            gas_fees=0.002,
            execution_time_ms=1200,
        )
        tracker1.record_trade(trade1)
        tracker1.record_trade(trade2)
        
        # Create new tracker instance to test loading
        tracker2 = PerformanceTracker(storage_path=temp_storage)
        
        assert len(tracker2.trades) == 2
        assert tracker2.trades[0].strategy_name == "strategy1"
        assert tracker2.trades[1].strategy_name == "strategy2"
        assert sum(t.actual_profit for t in tracker2.trades) == pytest.approx(0.076, rel=0.01)
    
    def test_persistence_file_format(self, temp_storage):
        """Test that storage file is valid JSON."""
        tracker = PerformanceTracker(storage_path=temp_storage)
        trade = TradeRecord(
            strategy_name="strategy1",
            timestamp=datetime.now(),
            expected_profit=0.05,
            actual_profit=0.048,
            transaction_hash="tx1",
            was_successful=True,
            error_message=None,
            gas_fees=0.002,
            execution_time_ms=1500,
        )
        tracker.record_trade(trade)
        
        # Read and parse JSON file
        with open(temp_storage, 'r') as f:
            data = json.load(f)
        
        assert "trades" in data
        assert "last_updated" in data
        assert len(data["trades"]) == 1
        assert data["trades"][0]["strategy_name"] == "strategy1"
    
    def test_generate_report(self, tracker):
        """Test generating performance report (Requirement 5.6, 10.3, 10.6)."""
        initial_balance = 1.0  # 1 SOL
        
        # Record trades
        for i in range(3):
            trade = TradeRecord(
                strategy_name=f"strategy{i % 2}",  # Alternate between 2 strategies
                timestamp=datetime.now(),
                expected_profit=0.05,
                actual_profit=0.02 if i < 2 else -0.01,  # 2 wins, 1 loss
                transaction_hash=f"tx{i}",
                was_successful=i < 2,
                error_message=None if i < 2 else "Failed",
                gas_fees=0.002,
                execution_time_ms=1500,
            )
            tracker.record_trade(trade)
        
        report = tracker.generate_report(initial_balance, unrealized_profit=0.01)
        
        assert report["total_trades"] == 3
        assert report["successful_trades"] == 2
        assert report["win_rate"] == pytest.approx(66.67, rel=0.01)
        assert report["realized_profit"] == pytest.approx(0.03, rel=0.01)  # 0.02 + 0.02 - 0.01
        assert report["unrealized_profit"] == 0.01
        assert report["total_profit"] == pytest.approx(0.04, rel=0.01)  # 0.03 + 0.01
        assert report["total_gas_fees"] == pytest.approx(0.006, rel=0.01)  # 0.002 * 3
        assert report["roi"] == pytest.approx(3.0, rel=0.01)  # (1.03 - 1.0) / 1.0 * 100
        assert "profit_by_strategy" in report
        assert "generated_at" in report
    
    def test_generate_report_empty(self, tracker):
        """Test generating report with no trades."""
        report = tracker.generate_report(1.0, unrealized_profit=0.0)
        
        assert report["total_trades"] == 0
        assert report["successful_trades"] == 0
        assert report["win_rate"] == 0.0
        assert report["total_profit"] == 0.0
        assert report["realized_profit"] == 0.0
        assert report["unrealized_profit"] == 0.0
        assert report["total_gas_fees"] == 0.0
        assert report["roi"] == 0.0
        assert report["profit_by_strategy"] == {}
    
    def test_clear_history(self, tracker):
        """Test clearing performance history."""
        trade = TradeRecord(
            strategy_name="strategy1",
            timestamp=datetime.now(),
            expected_profit=0.05,
            actual_profit=0.048,
            transaction_hash="tx1",
            was_successful=True,
            error_message=None,
            gas_fees=0.002,
            execution_time_ms=1500,
        )
        tracker.record_trade(trade)
        
        tracker.clear_history()
        
        assert len(tracker.trades) == 0
    
    def test_export_to_csv(self, tracker, tmp_path):
        """Test exporting to CSV."""
        trade = TradeRecord(
            strategy_name="strategy1",
            timestamp=datetime.now(),
            expected_profit=0.05,
            actual_profit=0.048,
            transaction_hash="tx1",
            was_successful=True,
            error_message=None,
            gas_fees=0.002,
            execution_time_ms=1500,
        )
        tracker.record_trade(trade)
        
        csv_path = tmp_path / "test_export.csv"
        tracker.export_to_csv(str(csv_path))
        
        # Verify CSV file exists and has content
        assert csv_path.exists()
        content = csv_path.read_text()
        assert "Strategy,Timestamp,Expected Profit,Actual Profit" in content
        assert "strategy1" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestPerformanceRecord:
    """Tests for PerformanceRecord data model."""
    
    def test_performance_record_creation(self):
        """Test creating a performance record."""
        record = PerformanceRecord(
            strategy_name="test_strategy",
            timestamp=datetime.now(),
            action="test_action",
            amount=100.0,
            profit=10.0,
            transaction_hash="test_tx_hash",
        )
        
        assert record.strategy_name == "test_strategy"
        assert record.action == "test_action"
        assert record.amount == 100.0
        assert record.profit == 10.0
        assert record.transaction_hash == "test_tx_hash"
    
    def test_performance_record_to_dict(self):
        """Test converting record to dictionary."""
        timestamp = datetime.now()
        record = PerformanceRecord(
            strategy_name="test_strategy",
            timestamp=timestamp,
            action="test_action",
            amount=100.0,
            profit=10.0,
            transaction_hash="test_tx_hash",
        )
        
        data = record.to_dict()
        
        assert data["strategy_name"] == "test_strategy"
        assert data["timestamp"] == timestamp.isoformat()
        assert data["action"] == "test_action"
        assert data["amount"] == 100.0
        assert data["profit"] == 10.0
        assert data["transaction_hash"] == "test_tx_hash"
    
    def test_performance_record_from_dict(self):
        """Test creating record from dictionary."""
        timestamp = datetime.now()
        data = {
            "strategy_name": "test_strategy",
            "timestamp": timestamp.isoformat(),
            "action": "test_action",
            "amount": 100.0,
            "profit": 10.0,
            "transaction_hash": "test_tx_hash",
        }
        
        record = PerformanceRecord.from_dict(data)
        
        assert record.strategy_name == "test_strategy"
        assert record.timestamp == timestamp
        assert record.action == "test_action"
        assert record.amount == 100.0
        assert record.profit == 10.0
        assert record.transaction_hash == "test_tx_hash"


class TestPerformanceTracker:
    """Tests for PerformanceTracker."""
    
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
    
    def test_tracker_initialization(self, tracker):
        """Test tracker initialization."""
        assert tracker.trades == []
        assert tracker.PERFORMANCE_FEE_RATE == 0.02
    
    def test_record_trade(self, tracker):
        """Test recording a trade (Requirement 13.1)."""
        record = tracker.record_trade(
            strategy_name="test_strategy",
            action="test_action",
            amount=100.0,
            profit=10.0,
            transaction_hash="test_tx_hash",
        )
        
        assert len(tracker.trades) == 1
        assert record.strategy_name == "test_strategy"
        assert record.profit == 10.0
    
    def test_get_total_profit(self, tracker):
        """Test calculating total profit (Requirement 13.2)."""
        # Record multiple trades
        tracker.record_trade("strategy1", "action1", 100.0, 10.0, "tx1")
        tracker.record_trade("strategy2", "action2", 200.0, 20.0, "tx2")
        tracker.record_trade("strategy3", "action3", 50.0, -5.0, "tx3")
        
        total_profit = tracker.get_total_profit()
        
        assert total_profit == 25.0  # 10 + 20 - 5
    
    def test_calculate_performance_fee(self, tracker):
        """Test calculating 2% performance fee (Requirement 13.3)."""
        # Test with positive profit
        fee = tracker.calculate_performance_fee(100.0)
        assert fee == 2.0  # 2% of 100
        
        # Test with negative profit (no fee on losses)
        fee = tracker.calculate_performance_fee(-50.0)
        assert fee == 0.0
        
        # Test with zero profit
        fee = tracker.calculate_performance_fee(0.0)
        assert fee == 0.0
    
    def test_calculate_performance_fee_on_total(self, tracker):
        """Test calculating fee on total profit."""
        tracker.record_trade("strategy1", "action1", 100.0, 50.0, "tx1")
        tracker.record_trade("strategy2", "action2", 200.0, 30.0, "tx2")
        
        fee = tracker.calculate_performance_fee()
        
        assert fee == 1.6  # 2% of 80
    
    def test_get_metrics(self, tracker):
        """Test getting performance metrics (Requirement 13.4)."""
        # Record trades with different outcomes
        tracker.record_trade("strategy1", "action1", 100.0, 10.0, "tx1")
        tracker.record_trade("strategy2", "action2", 200.0, 20.0, "tx2")
        tracker.record_trade("strategy1", "action3", 50.0, -5.0, "tx3")
        tracker.record_trade("strategy3", "action4", 150.0, 15.0, "tx4")
        
        metrics = tracker.get_metrics()
        
        assert metrics.total_profit == 40.0  # 10 + 20 - 5 + 15
        assert metrics.total_trades == 4
        assert metrics.win_rate == 75.0  # 3 out of 4 trades profitable
        assert metrics.profit_by_strategy["strategy1"] == 5.0  # 10 - 5
        assert metrics.profit_by_strategy["strategy2"] == 20.0
        assert metrics.profit_by_strategy["strategy3"] == 15.0
        assert metrics.performance_fee_collected == 0.8  # 2% of 40
    
    def test_get_metrics_empty(self, tracker):
        """Test getting metrics with no trades."""
        metrics = tracker.get_metrics()
        
        assert metrics.total_profit == 0.0
        assert metrics.total_trades == 0
        assert metrics.win_rate == 0.0
        assert metrics.profit_by_strategy == {}
        assert metrics.performance_fee_collected == 0.0
    
    def test_get_strategy_metrics(self, tracker):
        """Test getting metrics for specific strategy."""
        tracker.record_trade("strategy1", "action1", 100.0, 10.0, "tx1")
        tracker.record_trade("strategy1", "action2", 200.0, 20.0, "tx2")
        tracker.record_trade("strategy1", "action3", 50.0, -5.0, "tx3")
        tracker.record_trade("strategy2", "action4", 150.0, 15.0, "tx4")
        
        metrics = tracker.get_strategy_metrics("strategy1")
        
        assert metrics["total_trades"] == 3
        assert metrics["total_profit"] == 25.0  # 10 + 20 - 5
        assert metrics["win_rate"] == pytest.approx(66.67, rel=0.01)  # 2 out of 3
        assert metrics["avg_profit"] == pytest.approx(8.33, rel=0.01)  # 25 / 3
    
    def test_get_strategy_metrics_nonexistent(self, tracker):
        """Test getting metrics for strategy with no trades."""
        metrics = tracker.get_strategy_metrics("nonexistent")
        
        assert metrics["total_trades"] == 0
        assert metrics["total_profit"] == 0.0
        assert metrics["win_rate"] == 0.0
        assert metrics["avg_profit"] == 0.0
    
    def test_get_recent_trades(self, tracker):
        """Test getting recent trades."""
        # Record trades
        for i in range(5):
            tracker.record_trade(f"strategy{i}", f"action{i}", 100.0, 10.0, f"tx{i}")
        
        recent = tracker.get_recent_trades(limit=3)
        
        assert len(recent) == 3
        # Should be in reverse chronological order
        assert recent[0].transaction_hash == "tx4"
        assert recent[1].transaction_hash == "tx3"
        assert recent[2].transaction_hash == "tx2"
    
    def test_persistence_save_and_load(self, temp_storage):
        """Test saving and loading from storage (Requirement 13.5)."""
        # Create tracker and record trades
        tracker1 = PerformanceTracker(storage_path=temp_storage)
        tracker1.record_trade("strategy1", "action1", 100.0, 10.0, "tx1")
        tracker1.record_trade("strategy2", "action2", 200.0, 20.0, "tx2")
        
        # Create new tracker instance to test loading
        tracker2 = PerformanceTracker(storage_path=temp_storage)
        
        assert len(tracker2.trades) == 2
        assert tracker2.trades[0].strategy_name == "strategy1"
        assert tracker2.trades[1].strategy_name == "strategy2"
        assert tracker2.get_total_profit() == 30.0
    
    def test_persistence_file_format(self, temp_storage):
        """Test that storage file is valid JSON."""
        tracker = PerformanceTracker(storage_path=temp_storage)
        tracker.record_trade("strategy1", "action1", 100.0, 10.0, "tx1")
        
        # Read and parse JSON file
        with open(temp_storage, 'r') as f:
            data = json.load(f)
        
        assert "trades" in data
        assert "last_updated" in data
        assert len(data["trades"]) == 1
        assert data["trades"][0]["strategy_name"] == "strategy1"
    
    def test_clear_history(self, tracker):
        """Test clearing performance history."""
        tracker.record_trade("strategy1", "action1", 100.0, 10.0, "tx1")
        tracker.record_trade("strategy2", "action2", 200.0, 20.0, "tx2")
        
        tracker.clear_history()
        
        assert len(tracker.trades) == 0
        assert tracker.get_total_profit() == 0.0
    
    def test_export_to_csv(self, tracker, tmp_path):
        """Test exporting to CSV."""
        tracker.record_trade("strategy1", "action1", 100.0, 10.0, "tx1")
        tracker.record_trade("strategy2", "action2", 200.0, 20.0, "tx2")
        
        csv_path = tmp_path / "test_export.csv"
        tracker.export_to_csv(str(csv_path))
        
        # Verify CSV file exists and has content
        assert csv_path.exists()
        content = csv_path.read_text()
        assert "Strategy,Timestamp,Action,Amount,Profit,Transaction Hash" in content
        assert "strategy1" in content
        assert "strategy2" in content
    
    def test_win_rate_calculation(self, tracker):
        """Test win rate calculation with various scenarios."""
        # All winning trades
        tracker.clear_history()
        tracker.record_trade("s1", "a1", 100.0, 10.0, "tx1")
        tracker.record_trade("s2", "a2", 100.0, 20.0, "tx2")
        assert tracker.get_metrics().win_rate == 100.0
        
        # All losing trades
        tracker.clear_history()
        tracker.record_trade("s1", "a1", 100.0, -10.0, "tx1")
        tracker.record_trade("s2", "a2", 100.0, -20.0, "tx2")
        assert tracker.get_metrics().win_rate == 0.0
        
        # Mixed trades
        tracker.clear_history()
        tracker.record_trade("s1", "a1", 100.0, 10.0, "tx1")
        tracker.record_trade("s2", "a2", 100.0, -5.0, "tx2")
        tracker.record_trade("s3", "a3", 100.0, 15.0, "tx3")
        assert tracker.get_metrics().win_rate == pytest.approx(66.67, rel=0.01)
    
    def test_profit_by_strategy_aggregation(self, tracker):
        """Test profit aggregation by strategy."""
        tracker.record_trade("strategy1", "action1", 100.0, 10.0, "tx1")
        tracker.record_trade("strategy1", "action2", 200.0, 20.0, "tx2")
        tracker.record_trade("strategy2", "action3", 50.0, -5.0, "tx3")
        tracker.record_trade("strategy1", "action4", 150.0, 15.0, "tx4")
        tracker.record_trade("strategy2", "action5", 100.0, 10.0, "tx5")
        
        metrics = tracker.get_metrics()
        
        assert metrics.profit_by_strategy["strategy1"] == 45.0  # 10 + 20 + 15
        assert metrics.profit_by_strategy["strategy2"] == 5.0   # -5 + 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
