"""
Risk Management Module for Harvest Agent

Implements risk controls including:
- Risk-based position sizing (5% high, 10% medium, 20% low)
- Circuit breakers for balance and loss limits
- Consecutive loss tracking and allocation reduction
- Daily loss tracking with 20% threshold
- Adaptive strategy allocation based on performance

"""

import logging
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import deque

from .scanner import Opportunity

logger = logging.getLogger(__name__)


@dataclass
class TradeResult:
    """
    Represents the result of a completed trade.
    
    Attributes:
        strategy_name: Name of the strategy
        profit: Actual profit/loss in SOL
        was_successful: Whether the trade was profitable
        timestamp: When the trade completed
    """
    strategy_name: str
    profit: float
    was_successful: bool
    timestamp: datetime


class RiskManager:
    """
    Manages trading risk and enforces position sizing limits.
    
    Features:
    - Risk-based position sizing (5% high, 10% medium, 20% low risk)
    - Circuit breakers for minimum balance and daily losses
    - Consecutive loss tracking with allocation reduction
    - Adaptive strategy allocation based on performance
    
    """
    
    def __init__(
        self,
        wallet_manager,
        max_position_pct: float = 0.10,
        max_daily_loss_pct: float = 0.20,
        min_balance_sol: float = 0.1
    ):
        """
        Initialize risk manager.
        
        Args:
            wallet_manager: Wallet manager for balance queries
            max_position_pct: Maximum % of balance per trade (default 10%)
            max_daily_loss_pct: Maximum daily loss % before circuit breaker (default 20%)
            min_balance_sol: Minimum SOL balance to maintain (default 0.1)
        
        """
        self.wallet_manager = wallet_manager
        self.max_position_pct = max_position_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.min_balance_sol = min_balance_sol
        
        # Track consecutive losses by strategy
        self.consecutive_losses: Dict[str, int] = {}
        
        # Track strategy allocations (multiplier from 0.0 to 1.0)
        self.strategy_allocations: Dict[str, float] = {}
        
        # Track daily losses
        self.daily_start_balance: Optional[float] = None
        self.daily_start_date: Optional[datetime] = None
        self.daily_losses: float = 0.0
        
        # Track recent trades for performance analysis (last 10 per strategy)
        self.recent_trades: Dict[str, deque] = {}
        
        # Pause state
        self.is_paused: bool = False
        self.pause_reason: Optional[str] = None
        self.pause_until: Optional[datetime] = None
        
        logger.info(
            f"RiskManager initialized: max_position={max_position_pct*100}%, "
            f"max_daily_loss={max_daily_loss_pct*100}%, min_balance={min_balance_sol} SOL"
        )
    
    
    async def validate_opportunity(self, opportunity: Opportunity) -> Tuple[bool, str]:
        """
        Validate opportunity against risk limits.
        
        Checks:
        - Circuit breakers (balance, daily loss, pause state)
        - Position sizing limits
        
        Args:
            opportunity: Opportunity to evaluate
        
        Returns:
            (is_valid, rejection_reason)
        
        """
        # Check if trading is paused
        should_pause, pause_reason = await self.should_pause_trading()
        if should_pause:
            return False, pause_reason
        
        # Validate opportunity has required fields
        if not hasattr(opportunity, 'risk_level') or opportunity.risk_level not in ['low', 'medium', 'high']:
            return False, f"Invalid risk level: {getattr(opportunity, 'risk_level', 'missing')}"
        
        if opportunity.amount <= 0:
            return False, "Trade amount must be positive"
        
        logger.info(
            f"Validated opportunity for {opportunity.strategy_name}: "
            f"risk={opportunity.risk_level}, amount={opportunity.amount}"
        )
        
        return True, "Opportunity validated"
    
    def calculate_position_size(
        self,
        opportunity: Opportunity,
        current_balance: float
    ) -> float:
        """
        Calculate appropriate position size based on risk level.
        
        Position sizing rules:
        - High risk: max 5% of balance
        - Medium risk: max 10% of balance
        - Low risk: max 20% of balance
        - Absolute maximum: 10% of balance (enforced across all risk levels)
        
        Also applies strategy allocation multiplier based on recent performance.
        
        Args:
            opportunity: Opportunity to size
            current_balance: Current wallet balance in SOL
        
        Returns:
            Position size in SOL
        
        """
        # Determine base position size based on risk level
        risk_level = opportunity.risk_level.lower()
        
        if risk_level == 'high':
            base_pct = 0.05  # 5%
        elif risk_level == 'medium':
            base_pct = 0.10  # 10%
        elif risk_level == 'low':
            base_pct = 0.20  # 20%
        else:
            logger.warning(f"Unknown risk level: {risk_level}, using medium (10%)")
            base_pct = 0.10
        
        # Apply absolute maximum of 10%
        base_pct = min(base_pct, self.max_position_pct)
        
        # Calculate base position size
        base_position = current_balance * base_pct
        
        # Apply strategy allocation multiplier
        strategy_name = opportunity.strategy_name
        allocation_multiplier = self.get_strategy_allocation(strategy_name)
        
        # Final position size
        position_size = base_position * allocation_multiplier
        
        # Ensure position size doesn't exceed requested amount
        position_size = min(position_size, opportunity.amount)
        
        logger.info(
            f"Calculated position size for {strategy_name}: "
            f"{position_size:.4f} SOL (balance={current_balance:.4f}, "
            f"risk={risk_level}, base_pct={base_pct*100}%, "
            f"allocation={allocation_multiplier:.2f})"
        )
        
        return position_size
    
    
    async def should_pause_trading(self) -> Tuple[bool, str]:
        """
        Check if trading should be paused due to risk limits.
        
        Checks:
        - Minimum balance circuit breaker (< 0.1 SOL)
        - Daily loss circuit breaker (> 20% loss)
        - Manual pause state
        
        Returns:
            (should_pause, reason)
        
        """
        # Check if manually paused
        if self.is_paused:
            # Check if pause period has expired
            if self.pause_until and datetime.now() >= self.pause_until:
                self.is_paused = False
                self.pause_until = None
                self.pause_reason = None
                logger.info("Trading pause period expired, resuming trading")
            else:
                return True, self.pause_reason or "Trading is paused"
        
        # Check minimum balance circuit breaker
        try:
            current_balance = await self.wallet_manager.get_balance()
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return True, "Unable to check balance"
        
        if current_balance < self.min_balance_sol:
            reason = f"Balance ({current_balance:.4f} SOL) below minimum ({self.min_balance_sol} SOL)"
            logger.warning(f"Circuit breaker: {reason}")
            
            logger.warning(
                f"CIRCUIT BREAKER ACTIVATED - Minimum balance threshold",
                extra={
                    'extra_context': {
                        'circuit_breaker_type': 'minimum_balance',
                        'current_balance': current_balance,
                        'minimum_balance': self.min_balance_sol,
                        'deficit': self.min_balance_sol - current_balance,
                    }
                }
            )
            
            return True, reason
        
        # Initialize daily tracking if needed
        today = datetime.now().date()
        if self.daily_start_date is None or self.daily_start_date != today:
            self.daily_start_balance = current_balance
            self.daily_start_date = today
            self.daily_losses = 0.0
            logger.info(f"Reset daily tracking: start_balance={current_balance:.4f} SOL")
        
        # Check daily loss circuit breaker
        if self.daily_start_balance and self.daily_start_balance > 0:
            daily_loss_pct = self.daily_losses / self.daily_start_balance
            
            if daily_loss_pct > self.max_daily_loss_pct:
                reason = (
                    f"Daily loss ({daily_loss_pct*100:.2f}%) exceeds "
                    f"threshold ({self.max_daily_loss_pct*100}%)"
                )
                logger.warning(f"Circuit breaker: {reason}")
                
                logger.warning(
                    f"CIRCUIT BREAKER ACTIVATED - Daily loss threshold",
                    extra={
                        'extra_context': {
                            'circuit_breaker_type': 'daily_loss',
                            'daily_loss_pct': f"{daily_loss_pct*100:.2f}",
                            'daily_loss_amount': self.daily_losses,
                            'daily_start_balance': self.daily_start_balance,
                            'threshold_pct': f"{self.max_daily_loss_pct*100}",
                            'pause_duration_hours': 24,
                        }
                    }
                )
                
                # Pause for 24 hours
                self.is_paused = True
                self.pause_reason = reason
                self.pause_until = datetime.now() + timedelta(hours=24)
                
                return True, reason
        
        return False, "No circuit breakers triggered"
    
    def record_trade_result(
        self,
        strategy_name: str,
        profit: float,
        was_successful: bool
    ):
        """
        Record trade result for risk tracking.
        
        Updates:
        - Consecutive loss counter
        - Daily loss tracking
        - Recent trade history for performance analysis
        
        Args:
            strategy_name: Name of the strategy
            profit: Actual profit/loss in SOL
            was_successful: Whether the trade was profitable
        
        """
        trade_result = TradeResult(
            strategy_name=strategy_name,
            profit=profit,
            was_successful=was_successful,
            timestamp=datetime.now()
        )
        
        # Update consecutive losses
        if was_successful:
            # Reset consecutive losses on success
            self.consecutive_losses[strategy_name] = 0
            logger.info(f"Strategy {strategy_name} successful, reset consecutive losses")
        else:
            # Increment consecutive losses
            self.consecutive_losses[strategy_name] = self.consecutive_losses.get(strategy_name, 0) + 1
            consecutive = self.consecutive_losses[strategy_name]
            logger.warning(f"Strategy {strategy_name} failed, consecutive losses: {consecutive}")
            
            # Apply 50% allocation reduction after 3 consecutive losses
            if consecutive >= 3:
                current_allocation = self.strategy_allocations.get(strategy_name, 1.0)
                new_allocation = current_allocation * 0.5
                self.strategy_allocations[strategy_name] = new_allocation
                logger.warning(
                    f"Strategy {strategy_name} hit 3 consecutive losses, "
                    f"reducing allocation from {current_allocation:.2f} to {new_allocation:.2f}"
                )
                
                logger.warning(
                    f"ALLOCATION REDUCTION - Consecutive losses threshold",
                    extra={
                        'extra_context': {
                            'strategy': strategy_name,
                            'consecutive_losses': consecutive,
                            'previous_allocation': current_allocation,
                            'new_allocation': new_allocation,
                            'reduction_pct': 50,
                        }
                    }
                )
        
        # Update daily losses (only track losses, not gains)
        if profit < 0:
            self.daily_losses += abs(profit)
            logger.info(f"Daily losses updated: {self.daily_losses:.4f} SOL")
        
        # Update recent trades for performance analysis
        if strategy_name not in self.recent_trades:
            self.recent_trades[strategy_name] = deque(maxlen=10)
        
        self.recent_trades[strategy_name].append(trade_result)
        
        logger.info(
            f"Recorded trade result for {strategy_name}: "
            f"profit={profit:.4f} SOL, success={was_successful}"
        )
    
    def get_strategy_allocation(self, strategy_name: str) -> float:
        """
        Get current allocation multiplier for strategy (0.0 to 1.0).
        
        Analyzes recent performance (last 10 trades) and adjusts allocation:
        - Positive total profit: Increase allocation (up to 1.0)
        - Negative total profit: Decrease allocation (down to 0.5)
        - No trade history: Default to 1.0
        
        Args:
            strategy_name: Name of the strategy
        
        Returns:
            Allocation multiplier based on recent performance (0.5 to 1.0)
        
        """
        # Check if we have a manually set allocation (e.g., from consecutive losses)
        if strategy_name in self.strategy_allocations:
            allocation = self.strategy_allocations[strategy_name]
            logger.debug(f"Using existing allocation for {strategy_name}: {allocation:.2f}")
            return max(0.5, min(1.0, allocation))  # Clamp between 0.5 and 1.0
        
        # Check if we have enough trade history (need at least 10 trades)
        if strategy_name not in self.recent_trades or len(self.recent_trades[strategy_name]) < 10:
            logger.debug(f"Insufficient trade history for {strategy_name}, using default allocation 1.0")
            return 1.0
        
        # Calculate total profit over last 10 trades
        recent = self.recent_trades[strategy_name]
        total_profit = sum(trade.profit for trade in recent)
        
        # Adjust allocation based on performance
        if total_profit > 0:
            # Winning strategy: increase allocation
            # Scale increase based on profit magnitude (up to 1.0)
            allocation = min(1.0, 0.8 + (total_profit * 0.1))
            logger.info(
                f"Strategy {strategy_name} profitable over last 10 trades "
                f"(profit={total_profit:.4f}), allocation={allocation:.2f}"
            )
        else:
            # Losing strategy: decrease allocation
            # Scale decrease based on loss magnitude (down to 0.5)
            allocation = max(0.5, 0.8 + (total_profit * 0.1))
            logger.warning(
                f"Strategy {strategy_name} unprofitable over last 10 trades "
                f"(profit={total_profit:.4f}), allocation={allocation:.2f}"
            )
        
        # Store the calculated allocation
        self.strategy_allocations[strategy_name] = allocation
        
        return allocation
    
    def get_consecutive_losses(self, strategy_name: str) -> int:
        """
        Get consecutive loss count for a strategy.
        
        Args:
            strategy_name: Name of the strategy
        
        Returns:
            Number of consecutive losses
        """
        return self.consecutive_losses.get(strategy_name, 0)
    
    def get_daily_loss_percentage(self) -> float:
        """
        Get current daily loss as percentage of starting balance.
        
        Returns:
            Daily loss percentage (0.0 to 1.0)
        """
        if self.daily_start_balance and self.daily_start_balance > 0:
            return self.daily_losses / self.daily_start_balance
        return 0.0
    
    def reset_daily_tracking(self):
        """
        Manually reset daily loss tracking.
        
        Useful for testing or manual intervention.
        """
        self.daily_start_balance = None
        self.daily_start_date = None
        self.daily_losses = 0.0
        logger.info("Daily tracking manually reset")
    
    def unpause_trading(self):
        """
        Manually unpause trading.
        
        Clears pause state and allows trading to resume.
        """
        self.is_paused = False
        self.pause_until = None
        self.pause_reason = None
        logger.info("Trading manually unpaused")

    def get_active_positions(self) -> list:
        """
        Get list of active positions.
        
        Returns:
            List of active positions (empty for now, can be extended)
        """
        # TODO: Implement position tracking if needed
        return []
    
    def get_total_exposure(self) -> float:
        """
        Get total exposure across all positions.
        
        Returns:
            Total exposure in SOL
        """
        # TODO: Implement exposure tracking if needed
        return 0.0
    
    def get_total_max_loss(self) -> float:
        """
        Get total maximum loss across all positions.
        
        Returns:
            Total max loss in SOL
        """
        # TODO: Implement max loss tracking if needed
        return 0.0
