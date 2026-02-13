"""
Trade execution queue for serializing trade execution across multiple users.

This module provides a queue system to serialize trade execution, avoiding
nonce conflicts when multiple users have approved trades simultaneously.
"""

import asyncio
import logging
from typing import Optional, Callable, Any, Dict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class TradeStatus(Enum):
    """Status of a trade in the queue."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class QueuedTrade:
    """Represents a trade in the execution queue."""
    trade_id: str
    user_id: str
    opportunity: Any  # Opportunity object
    execute_func: Callable  # Async function to execute the trade
    queued_at: datetime
    status: TradeStatus = TradeStatus.PENDING
    result: Optional[Any] = None
    error: Optional[Exception] = None
    executed_at: Optional[datetime] = None


class TradeQueue:
    """
    Queue system for serializing trade execution.
    
    Ensures trades are executed sequentially to avoid nonce conflicts
    when multiple users have approved trades. Maintains FIFO ordering
    and provides status tracking for queued trades.
    """
    
    def __init__(self):
        """Initialize trade execution queue."""
        self._queue: asyncio.Queue = asyncio.Queue()
        self._trades: Dict[str, QueuedTrade] = {}  # trade_id -> QueuedTrade
        self._processing = False
        self._processor_task: Optional[asyncio.Task] = None
        self._trade_counter = 0
        self._lock = asyncio.Lock()
        
        logger.info("TradeQueue initialized")
    
    def _generate_trade_id(self, user_id: str) -> str:
        """
        Generate unique trade ID.
        
        Args:
            user_id: User ID for the trade
            
        Returns:
            Unique trade ID
        """
        self._trade_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{user_id}_{timestamp}_{self._trade_counter}"
    
    async def enqueue(
        self,
        user_id: str,
        opportunity: Any,
        execute_func: Callable
    ) -> str:
        """
        Add a trade to the execution queue.
        
        Args:
            user_id: User ID for the trade
            opportunity: Opportunity object
            execute_func: Async function to execute the trade
            
        Returns:
            Trade ID for tracking
        """
        async with self._lock:
            trade_id = self._generate_trade_id(user_id)
            
            queued_trade = QueuedTrade(
                trade_id=trade_id,
                user_id=user_id,
                opportunity=opportunity,
                execute_func=execute_func,
                queued_at=datetime.now(),
                status=TradeStatus.PENDING
            )
            
            self._trades[trade_id] = queued_trade
            await self._queue.put(queued_trade)
            
            logger.info(
                f"Trade queued: {trade_id} for user {user_id} "
                f"(strategy: {opportunity.strategy_name if hasattr(opportunity, 'strategy_name') else 'unknown'})"
            )
            
            return trade_id
    
    async def start_processing(self):
        """
        Start processing trades from the queue.
        
        Launches a background task that processes trades sequentially.
        """
        if self._processing:
            logger.warning("Trade queue processor already running")
            return
        
        self._processing = True
        self._processor_task = asyncio.create_task(self._process_queue())
        logger.info("Trade queue processor started")
    
    async def stop_processing(self):
        """
        Stop processing trades from the queue.
        
        Waits for current trade to complete before stopping.
        """
        if not self._processing:
            return
        
        self._processing = False
        
        if self._processor_task:
            # Wait for current trade to complete
            try:
                await asyncio.wait_for(self._processor_task, timeout=30.0)
            except asyncio.TimeoutError:
                logger.warning("Trade queue processor did not stop within timeout")
                self._processor_task.cancel()
        
        logger.info("Trade queue processor stopped")
    
    async def _process_queue(self):
        """
        Process trades from the queue sequentially.
        
        Runs continuously while processing is enabled, executing trades
        one at a time in FIFO order.
        """
        logger.info("Trade queue processor running")
        
        while self._processing:
            try:
                # Get next trade from queue (with timeout to allow checking _processing flag)
                try:
                    queued_trade = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    # No trade available, continue loop
                    continue
                
                # Update status to executing
                queued_trade.status = TradeStatus.EXECUTING
                queued_trade.executed_at = datetime.now()
                
                logger.info(
                    f"Executing trade {queued_trade.trade_id} for user {queued_trade.user_id}"
                )
                
                try:
                    # Execute the trade
                    result = await queued_trade.execute_func()
                    
                    # Mark as completed
                    queued_trade.status = TradeStatus.COMPLETED
                    queued_trade.result = result
                    
                    logger.info(
                        f"Trade {queued_trade.trade_id} completed successfully"
                    )
                    
                except Exception as e:
                    # Mark as failed
                    queued_trade.status = TradeStatus.FAILED
                    queued_trade.error = e
                    
                    logger.error(
                        f"Trade {queued_trade.trade_id} failed: {e}",
                        exc_info=True
                    )
                
                finally:
                    # Mark task as done
                    self._queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in trade queue processor: {e}", exc_info=True)
                # Continue processing despite error
                continue
        
        logger.info("Trade queue processor stopped")
    
    def get_trade_status(self, trade_id: str) -> Optional[TradeStatus]:
        """
        Get status of a queued trade.
        
        Args:
            trade_id: Trade ID to check
            
        Returns:
            TradeStatus if trade exists, None otherwise
        """
        if trade_id in self._trades:
            return self._trades[trade_id].status
        return None
    
    def get_trade_result(self, trade_id: str) -> Optional[Any]:
        """
        Get result of a completed trade.
        
        Args:
            trade_id: Trade ID to check
            
        Returns:
            Trade result if completed, None otherwise
        """
        if trade_id in self._trades:
            trade = self._trades[trade_id]
            if trade.status == TradeStatus.COMPLETED:
                return trade.result
        return None
    
    def get_trade_error(self, trade_id: str) -> Optional[Exception]:
        """
        Get error from a failed trade.
        
        Args:
            trade_id: Trade ID to check
            
        Returns:
            Exception if trade failed, None otherwise
        """
        if trade_id in self._trades:
            trade = self._trades[trade_id]
            if trade.status == TradeStatus.FAILED:
                return trade.error
        return None
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics.
        
        Returns:
            Dictionary with queue metrics
        """
        pending_count = sum(
            1 for t in self._trades.values()
            if t.status == TradeStatus.PENDING
        )
        executing_count = sum(
            1 for t in self._trades.values()
            if t.status == TradeStatus.EXECUTING
        )
        completed_count = sum(
            1 for t in self._trades.values()
            if t.status == TradeStatus.COMPLETED
        )
        failed_count = sum(
            1 for t in self._trades.values()
            if t.status == TradeStatus.FAILED
        )
        
        return {
            "queue_size": self._queue.qsize(),
            "total_trades": len(self._trades),
            "pending": pending_count,
            "executing": executing_count,
            "completed": completed_count,
            "failed": failed_count,
            "processing": self._processing
        }
    
    async def wait_for_trade(self, trade_id: str, timeout: float = 60.0) -> bool:
        """
        Wait for a trade to complete.
        
        Args:
            trade_id: Trade ID to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if trade completed, False if timeout or failed
        """
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            if trade_id not in self._trades:
                return False
            
            trade = self._trades[trade_id]
            
            if trade.status == TradeStatus.COMPLETED:
                return True
            elif trade.status == TradeStatus.FAILED:
                return False
            
            # Wait a bit before checking again
            await asyncio.sleep(0.5)
        
        # Timeout
        return False
    
    def clear_completed_trades(self, max_age_seconds: int = 3600):
        """
        Clear completed/failed trades older than max_age.
        
        Args:
            max_age_seconds: Maximum age in seconds (default 1 hour)
        """
        now = datetime.now()
        trades_to_remove = []
        
        for trade_id, trade in self._trades.items():
            if trade.status in [TradeStatus.COMPLETED, TradeStatus.FAILED]:
                age = (now - trade.queued_at).total_seconds()
                if age > max_age_seconds:
                    trades_to_remove.append(trade_id)
        
        for trade_id in trades_to_remove:
            del self._trades[trade_id]
        
        if trades_to_remove:
            logger.info(f"Cleared {len(trades_to_remove)} old trades from queue")
