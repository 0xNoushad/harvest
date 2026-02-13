"""Performance tracking for Harvest - records trades and calculates metrics."""

import json
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """
    Record of a single trade execution.
    
    Attributes:
        strategy_name: Name of the strategy that executed the trade
        timestamp: When the trade was executed
        expected_profit: Expected profit before execution (in SOL)
        actual_profit: Actual profit after execution (in SOL)
        transaction_hash: Transaction hash on Solana
        was_successful: Whether the trade completed successfully
        error_message: Error message if trade failed
        gas_fees: Gas fees paid for the transaction (in SOL)
        execution_time_ms: Time taken to execute the transaction (milliseconds)
        user_id: User ID who executed the trade (optional for backward compatibility)
    
    """
    strategy_name: str
    timestamp: datetime
    expected_profit: float
    actual_profit: float
    transaction_hash: str
    was_successful: bool
    error_message: Optional[str]
    gas_fees: float
    execution_time_ms: int
    user_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "strategy_name": self.strategy_name,
            "timestamp": self.timestamp.isoformat(),
            "expected_profit": self.expected_profit,
            "actual_profit": self.actual_profit,
            "transaction_hash": self.transaction_hash,
            "was_successful": self.was_successful,
            "error_message": self.error_message,
            "gas_fees": self.gas_fees,
            "execution_time_ms": self.execution_time_ms,
            "user_id": self.user_id,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TradeRecord":
        """Create from dictionary."""
        return cls(
            strategy_name=data["strategy_name"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            expected_profit=data["expected_profit"],
            actual_profit=data["actual_profit"],
            transaction_hash=data["transaction_hash"],
            was_successful=data["was_successful"],
            error_message=data.get("error_message"),
            gas_fees=data["gas_fees"],
            execution_time_ms=data["execution_time_ms"],
            user_id=data.get("user_id"),
        )


@dataclass
class StrategyMetrics:
    """
    Performance metrics for a strategy.
    
    Attributes:
        strategy_name: Name of the strategy
        total_trades: Total number of trades executed
        successful_trades: Number of successful trades
        total_profit: Total profit across all trades (in SOL)
        average_profit: Average profit per trade (in SOL)
        win_rate: Percentage of successful trades (0-100)
        total_gas_fees: Total gas fees paid (in SOL)
        last_updated: When metrics were last calculated
    
    """
    strategy_name: str
    total_trades: int
    successful_trades: int
    total_profit: float
    average_profit: float
    win_rate: float
    total_gas_fees: float
    last_updated: datetime


class PerformanceTracker:
    """
    Tracks and persists trading performance.
    
    Features:
    - Records all completed trades with expected vs actual profit
    - Calculates per-strategy metrics (win rate, total profit, average profit)
    - Persists data to disk for historical tracking
    - Provides performance reports and analytics
    
    """
    
    def __init__(self, storage_path: str = ".kiro/trading_history.json"):
        """
        Initialize performance tracker.
        
        Args:
            storage_path: Path to JSON file for persisting performance data
        
        """
        self.storage_path = Path(storage_path)
        self.trades: List[TradeRecord] = []
        
        # Track trade count for periodic metrics logging
        self._last_metrics_log_count = 0
        self._metrics_log_interval = 100  # Log every 100 trades
        
        # Create storage directory if it doesn't exist
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing data
        self.load_from_disk()
        
        logger.info(f"PerformanceTracker initialized with {len(self.trades)} historical trades")
    
    def record_trade(self, trade: TradeRecord, user_id: Optional[str] = None):
        """
        Record a completed trade.
        
        Args:
            trade: TradeRecord to add to history
            user_id: User ID who executed the trade (optional for backward compatibility)
        
        """
        self.trades.append(trade)
        
        # Persist to storage after each trade
        self.persist_to_disk()
        
        logger.info(
            f"Recorded trade: {trade.strategy_name} - "
            f"Expected: {trade.expected_profit:.4f} SOL, "
            f"Actual: {trade.actual_profit:.4f} SOL - "
            f"TX: {trade.transaction_hash[:8]}..."
        )
        
        if len(self.trades) - self._last_metrics_log_count >= self._metrics_log_interval:
            self._log_performance_metrics()
            self._last_metrics_log_count = len(self.trades)
    
    def _log_performance_metrics(self):
        """
        Log comprehensive performance metrics.
        
        Logs:
        - Total trades and win rate
        - Total profit across all strategies
        - Profit breakdown by strategy
        
        """
        if not self.trades:
            return
        
        # Calculate overall metrics
        total_trades = len(self.trades)
        successful_trades = sum(1 for t in self.trades if t.was_successful)
        win_rate = (successful_trades / total_trades) * 100 if total_trades > 0 else 0.0
        total_profit = sum(t.actual_profit for t in self.trades)
        total_gas_fees = sum(t.gas_fees for t in self.trades)
        
        # Get profit by strategy
        all_metrics = self.get_all_metrics()
        profit_by_strategy = {
            name: metrics.total_profit
            for name, metrics in all_metrics.items()
        }
        
        # Log comprehensive metrics
        logger.info("=" * 80)
        logger.info(f"PERFORMANCE METRICS (after {total_trades} trades)")
        logger.info("=" * 80)
        logger.info(f"Total Trades: {total_trades}")
        logger.info(f"Successful Trades: {successful_trades}")
        logger.info(f"Win Rate: {win_rate:.2f}%")
        logger.info(f"Total Profit: {total_profit:.4f} SOL")
        logger.info(f"Total Gas Fees: {total_gas_fees:.4f} SOL")
        logger.info(f"Net Profit: {total_profit - total_gas_fees:.4f} SOL")
        logger.info("")
        logger.info("Profit by Strategy:")
        for strategy_name, profit in sorted(profit_by_strategy.items(), key=lambda x: x[1], reverse=True):
            metrics = all_metrics[strategy_name]
            logger.info(
                f"  {strategy_name}: {profit:.4f} SOL "
                f"({metrics.total_trades} trades, {metrics.win_rate:.1f}% win rate)"
            )
        logger.info("=" * 80)
        
        # Also log as structured data for parsing
        logger.info(
            "Performance metrics summary",
            extra={
                'extra_context': {
                    'total_trades': total_trades,
                    'successful_trades': successful_trades,
                    'win_rate': f"{win_rate:.2f}",
                    'total_profit': total_profit,
                    'total_gas_fees': total_gas_fees,
                    'net_profit': total_profit - total_gas_fees,
                    'profit_by_strategy': {k: f"{v:.4f}" for k, v in profit_by_strategy.items()},
                }
            }
        )
    
    def get_recent_trades(self, count: int = 10, user_id: Optional[str] = None) -> List[TradeRecord]:
        """
        Get most recent trades.
        
        Args:
            count: Maximum number of trades to return
            user_id: Optional user ID to filter trades for specific user
        
        Returns:
            List of recent TradeRecords
        
        """
        # Filter trades by user_id if provided
        filtered_trades = self.trades
        if user_id is not None:
            filtered_trades = [t for t in self.trades if t.user_id == user_id]
        
        return sorted(filtered_trades, key=lambda t: t.timestamp, reverse=True)[:count]
    
    def get_strategy_metrics(self, strategy_name: str, user_id: Optional[str] = None) -> StrategyMetrics:
        """
        Get performance metrics for a specific strategy.
        
        Args:
            strategy_name: Name of the strategy
            user_id: Optional user ID to filter metrics for specific user
        
        Returns:
            StrategyMetrics with computed metrics
        
        """
        # Filter trades by strategy and optionally by user_id
        strategy_trades = [t for t in self.trades if t.strategy_name == strategy_name]
        if user_id is not None:
            strategy_trades = [t for t in strategy_trades if t.user_id == user_id]
        
        if not strategy_trades:
            return StrategyMetrics(
                strategy_name=strategy_name,
                total_trades=0,
                successful_trades=0,
                total_profit=0.0,
                average_profit=0.0,
                win_rate=0.0,
                total_gas_fees=0.0,
                last_updated=datetime.now(),
            )
        
        total_trades = len(strategy_trades)
        successful_trades = sum(1 for t in strategy_trades if t.was_successful)
        total_profit = sum(t.actual_profit for t in strategy_trades)
        average_profit = total_profit / total_trades
        win_rate = (successful_trades / total_trades) * 100
        total_gas_fees = sum(t.gas_fees for t in strategy_trades)
        
        return StrategyMetrics(
            strategy_name=strategy_name,
            total_trades=total_trades,
            successful_trades=successful_trades,
            total_profit=total_profit,
            average_profit=average_profit,
            win_rate=win_rate,
            total_gas_fees=total_gas_fees,
            last_updated=datetime.now(),
        )
    
    def get_all_metrics(self, user_id: Optional[str] = None) -> Dict[str, StrategyMetrics]:
        """
        Get metrics for all strategies.
        
        Args:
            user_id: Optional user ID to filter metrics for specific user
        
        Returns:
            Dictionary mapping strategy name to StrategyMetrics
        
        """
        # Filter trades by user_id if provided
        filtered_trades = self.trades
        if user_id is not None:
            filtered_trades = [t for t in self.trades if t.user_id == user_id]
        
        strategy_names = set(t.strategy_name for t in filtered_trades)
        return {
            name: self.get_strategy_metrics(name, user_id=user_id)
            for name in strategy_names
        }
    
    def get_metrics(self, user_id: Optional[str] = None) -> 'OverallMetrics':
        """
        Get overall performance metrics across all strategies.
        
        Args:
            user_id: Optional user ID to filter metrics for specific user
        
        Returns:
            OverallMetrics object with aggregated data
        
        """
        from dataclasses import dataclass
        
        @dataclass
        class OverallMetrics:
            total_trades: int
            successful_trades: int
            win_rate: float
            total_profit: float
            total_gas_fees: float
            net_profit: float
            profit_by_strategy: Dict[str, float]
            performance_fee_collected: float = 0.0
        
        # Filter trades by user_id if provided
        filtered_trades = self.trades
        if user_id is not None:
            filtered_trades = [t for t in self.trades if t.user_id == user_id]
        
        if not filtered_trades:
            return OverallMetrics(
                total_trades=0,
                successful_trades=0,
                win_rate=0.0,
                total_profit=0.0,
                total_gas_fees=0.0,
                net_profit=0.0,
                profit_by_strategy={},
            )
        
        total_trades = len(filtered_trades)
        successful_trades = sum(1 for t in filtered_trades if t.was_successful)
        win_rate = (successful_trades / total_trades) * 100
        total_profit = sum(t.actual_profit for t in filtered_trades)
        total_gas_fees = sum(t.gas_fees for t in filtered_trades)
        net_profit = total_profit - total_gas_fees
        
        # Calculate profit by strategy for filtered trades
        strategy_profits = {}
        for trade in filtered_trades:
            if trade.strategy_name not in strategy_profits:
                strategy_profits[trade.strategy_name] = 0.0
            strategy_profits[trade.strategy_name] += trade.actual_profit
        
        return OverallMetrics(
            total_trades=total_trades,
            successful_trades=successful_trades,
            win_rate=win_rate,
            total_profit=total_profit,
            total_gas_fees=total_gas_fees,
            net_profit=net_profit,
            profit_by_strategy=strategy_profits,
        )
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """
        Get anonymized leaderboard of top performers.
        
        Args:
            limit: Number of top users to return (default 10)
        
        Returns:
            List of {rank, profit, win_rate} without user IDs
        
        """
        # Group trades by user_id and calculate metrics
        user_metrics = {}
        for trade in self.trades:
            if trade.user_id is None:
                continue  # Skip trades without user_id
            
            if trade.user_id not in user_metrics:
                user_metrics[trade.user_id] = {
                    'total_profit': 0.0,
                    'total_trades': 0,
                    'successful_trades': 0,
                }
            
            user_metrics[trade.user_id]['total_profit'] += trade.actual_profit
            user_metrics[trade.user_id]['total_trades'] += 1
            if trade.was_successful:
                user_metrics[trade.user_id]['successful_trades'] += 1
        
        # Calculate win rate for each user
        leaderboard_data = []
        for user_id, metrics in user_metrics.items():
            win_rate = (metrics['successful_trades'] / metrics['total_trades'] * 100) if metrics['total_trades'] > 0 else 0.0
            leaderboard_data.append({
                'profit': metrics['total_profit'],
                'win_rate': win_rate,
            })
        
        # Sort by profit descending
        leaderboard_data.sort(key=lambda x: x['profit'], reverse=True)
        
        # Add rank and limit results
        leaderboard = []
        for rank, entry in enumerate(leaderboard_data[:limit], start=1):
            leaderboard.append({
                'rank': rank,
                'profit': entry['profit'],
                'win_rate': entry['win_rate'],
            })
        
        return leaderboard
    
    def calculate_roi(self, initial_balance: float) -> float:
        """
        Calculate overall return on investment.
        
        Args:
            initial_balance: Initial balance in SOL
        
        Returns:
            ROI as percentage
        
        """
        if initial_balance <= 0:
            return 0.0
        
        total_profit = sum(t.actual_profit for t in self.trades)
        current_balance = initial_balance + total_profit
        
        roi = ((current_balance - initial_balance) / initial_balance) * 100
        return roi
    
    def persist_to_disk(self):
        """
        Save trade history to disk.
        
        """
        try:
            data = {
                "trades": [trade.to_dict() for trade in self.trades],
                "last_updated": datetime.now().isoformat(),
            }
            
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved {len(self.trades)} trades to {self.storage_path}")
            
        except Exception as e:
            logger.error(f"Error saving performance data: {e}", exc_info=True)
    
    def load_from_disk(self):
        """
        Load trade history from disk.
        
        """
        if not self.storage_path.exists():
            logger.info("No existing performance data found")
            return
        
        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
            
            self.trades = [
                TradeRecord.from_dict(trade_data)
                for trade_data in data.get("trades", [])
            ]
            
            logger.info(f"Loaded {len(self.trades)} trades from {self.storage_path}")
            
        except Exception as e:
            logger.error(f"Error loading performance data: {e}", exc_info=True)
            self.trades = []
    
    def generate_report(
        self,
        initial_balance: float,
        unrealized_profit: float = 0.0
    ) -> Dict[str, any]:
        """
        Generate comprehensive performance report.
        
        Args:
            initial_balance: Initial balance in SOL
            unrealized_profit: Unrealized profit from open positions (in SOL)
        
        Returns:
            Dictionary with performance report data
        
        """
        if not self.trades:
            return {
                "total_trades": 0,
                "successful_trades": 0,
                "win_rate": 0.0,
                "total_profit": 0.0,
                "realized_profit": 0.0,
                "unrealized_profit": 0.0,
                "total_gas_fees": 0.0,
                "roi": 0.0,
                "profit_by_strategy": {},
                "generated_at": datetime.now().isoformat(),
            }
        
        # Calculate overall metrics
        total_trades = len(self.trades)
        successful_trades = sum(1 for t in self.trades if t.was_successful)
        win_rate = (successful_trades / total_trades) * 100
        realized_profit = sum(t.actual_profit for t in self.trades)
        total_gas_fees = sum(t.gas_fees for t in self.trades)
        total_profit = realized_profit + unrealized_profit
        roi = self.calculate_roi(initial_balance)
        
        # Calculate profit by strategy
        all_metrics = self.get_all_metrics()
        profit_by_strategy = {
            name: metrics.total_profit
            for name, metrics in all_metrics.items()
        }
        
        # Calculate time periods
        if self.trades:
            first_trade = min(self.trades, key=lambda t: t.timestamp)
            last_trade = max(self.trades, key=lambda t: t.timestamp)
            trading_period_days = (last_trade.timestamp - first_trade.timestamp).days
        else:
            trading_period_days = 0
        
        return {
            "total_trades": total_trades,
            "successful_trades": successful_trades,
            "win_rate": win_rate,
            "total_profit": total_profit,
            "realized_profit": realized_profit,
            "unrealized_profit": unrealized_profit,
            "total_gas_fees": total_gas_fees,
            "roi": roi,
            "profit_by_strategy": profit_by_strategy,
            "trading_period_days": trading_period_days,
            "generated_at": datetime.now().isoformat(),
        }
    
    def clear_history(self):
        """Clear all performance history (use with caution)."""
        self.trades = []
        self.persist_to_disk()
        logger.warning("Performance history cleared")
    
    def export_to_csv(self, output_path: str):
        """
        Export performance data to CSV file.
        
        Args:
            output_path: Path to output CSV file
        """
        import csv
        
        try:
            with open(output_path, "w", newline="") as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow([
                    "Strategy",
                    "Timestamp",
                    "Expected Profit",
                    "Actual Profit",
                    "Was Successful",
                    "Gas Fees",
                    "Execution Time (ms)",
                    "Transaction Hash",
                    "Error Message",
                ])
                
                # Write trades
                for trade in self.trades:
                    writer.writerow([
                        trade.strategy_name,
                        trade.timestamp.isoformat(),
                        trade.expected_profit,
                        trade.actual_profit,
                        trade.was_successful,
                        trade.gas_fees,
                        trade.execution_time_ms,
                        trade.transaction_hash,
                        trade.error_message or "",
                    ])
            
            logger.info(f"Exported {len(self.trades)} trades to {output_path}")
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}", exc_info=True)
