"""Tests for RiskManager - risk controls and position sizing."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from agent.trading.risk_manager import RiskManager, TradeResult
from agent.trading.scanner import Opportunity


class MockWalletManager:
    """Mock wallet manager for testing."""
    
    def __init__(self, balance: float = 10.0):
        self.balance = balance
    
    async def get_balance(self) -> float:
        return self.balance


class TestRiskManager:
    """Tests for RiskManager class."""
    
    def test_risk_manager_initialization(self):
        """Test that RiskManager initializes correctly."""
        wallet_manager = MockWalletManager()
        risk_manager = RiskManager(wallet_manager)
        
        assert risk_manager.max_position_pct == 0.10
        assert risk_manager.max_daily_loss_pct == 0.20
        assert risk_manager.min_balance_sol == 0.1
        assert len(risk_manager.consecutive_losses) == 0
        assert len(risk_manager.strategy_allocations) == 0
    
    def test_risk_manager_custom_parameters(self):
        """Test RiskManager with custom parameters."""
        wallet_manager = MockWalletManager()
        risk_manager = RiskManager(
            wallet_manager,
            max_position_pct=0.15,
            max_daily_loss_pct=0.25,
            min_balance_sol=0.2
        )
        
        assert risk_manager.max_position_pct == 0.15
        assert risk_manager.max_daily_loss_pct == 0.25
        assert risk_manager.min_balance_sol == 0.2
    
    @pytest.mark.asyncio
    async def test_validate_opportunity_success(self):
        """Test validating a valid opportunity."""
        wallet_manager = MockWalletManager(balance=10.0)
        risk_manager = RiskManager(wallet_manager)
        
        opportunity = Opportunity(
            strategy_name="test_strategy",
            action="swap",
            amount=1.0,
            expected_profit=0.1,
            risk_level="medium",
            details={},
            timestamp=datetime.now()
        )
        
        is_valid, reason = await risk_manager.validate_opportunity(opportunity)
        
        assert is_valid is True
        assert "validated" in reason.lower()
    
    @pytest.mark.asyncio
    async def test_validate_opportunity_invalid_risk_level(self):
        """Test validating opportunity with invalid risk level."""
        wallet_manager = MockWalletManager()
        risk_manager = RiskManager(wallet_manager)
        
        opportunity = Opportunity(
            strategy_name="test_strategy",
            action="swap",
            amount=1.0,
            expected_profit=0.1,
            risk_level="invalid",
            details={},
            timestamp=datetime.now()
        )
        
        is_valid, reason = await risk_manager.validate_opportunity(opportunity)
        
        assert is_valid is False
        assert "invalid risk level" in reason.lower()
    
    @pytest.mark.asyncio
    async def test_validate_opportunity_zero_amount(self):
        """Test validating opportunity with zero amount."""
        wallet_manager = MockWalletManager()
        risk_manager = RiskManager(wallet_manager)
        
        opportunity = Opportunity(
            strategy_name="test_strategy",
            action="swap",
            amount=0.0,
            expected_profit=0.1,
            risk_level="medium",
            details={},
            timestamp=datetime.now()
        )
        
        is_valid, reason = await risk_manager.validate_opportunity(opportunity)
        
        assert is_valid is False
        assert "positive" in reason.lower()
    
    def test_calculate_position_size_high_risk(self):
        """Test position sizing for high risk opportunity."""
        wallet_manager = MockWalletManager(balance=10.0)
        risk_manager = RiskManager(wallet_manager)
        
        opportunity = Opportunity(
            strategy_name="test_strategy",
            action="swap",
            amount=5.0,
            expected_profit=0.5,
            risk_level="high",
            details={},
            timestamp=datetime.now()
        )
        
        position_size = risk_manager.calculate_position_size(opportunity, 10.0)
        
        # High risk: 5% of balance
        assert position_size == 0.5
    
    def test_calculate_position_size_medium_risk(self):
        """Test position sizing for medium risk opportunity."""
        wallet_manager = MockWalletManager(balance=10.0)
        risk_manager = RiskManager(wallet_manager)
        
        opportunity = Opportunity(
            strategy_name="test_strategy",
            action="swap",
            amount=5.0,
            expected_profit=0.5,
            risk_level="medium",
            details={},
            timestamp=datetime.now()
        )
        
        position_size = risk_manager.calculate_position_size(opportunity, 10.0)
        
        # Medium risk: 10% of balance
        assert position_size == 1.0
    
    def test_calculate_position_size_low_risk(self):
        """Test position sizing for low risk opportunity."""
        wallet_manager = MockWalletManager(balance=10.0)
        risk_manager = RiskManager(wallet_manager)
        
        opportunity = Opportunity(
            strategy_name="test_strategy",
            action="swap",
            amount=5.0,
            expected_profit=0.5,
            risk_level="low",
            details={},
            timestamp=datetime.now()
        )
        
        position_size = risk_manager.calculate_position_size(opportunity, 10.0)
        
        # Low risk: 20% of balance, but capped at 10% absolute max
        assert position_size == 1.0  # 10% cap applies
    
    def test_calculate_position_size_respects_opportunity_amount(self):
        """Test that position size doesn't exceed opportunity amount."""
        wallet_manager = MockWalletManager(balance=100.0)
        risk_manager = RiskManager(wallet_manager)
        
        opportunity = Opportunity(
            strategy_name="test_strategy",
            action="swap",
            amount=0.5,  # Small opportunity
            expected_profit=0.05,
            risk_level="medium",
            details={},
            timestamp=datetime.now()
        )
        
        position_size = risk_manager.calculate_position_size(opportunity, 100.0)
        
        # Should be capped at opportunity amount
        assert position_size == 0.5
    
    @pytest.mark.asyncio
    async def test_should_pause_trading_minimum_balance(self):
        """Test circuit breaker for minimum balance."""
        wallet_manager = MockWalletManager(balance=0.05)  # Below minimum
        risk_manager = RiskManager(wallet_manager, min_balance_sol=0.1)
        
        should_pause, reason = await risk_manager.should_pause_trading()
        
        assert should_pause is True
        assert "below minimum" in reason.lower()
    
    @pytest.mark.asyncio
    async def test_should_pause_trading_sufficient_balance(self):
        """Test no pause when balance is sufficient."""
        wallet_manager = MockWalletManager(balance=10.0)
        risk_manager = RiskManager(wallet_manager, min_balance_sol=0.1)
        
        should_pause, reason = await risk_manager.should_pause_trading()
        
        assert should_pause is False
    
    @pytest.mark.asyncio
    async def test_should_pause_trading_daily_loss_limit(self):
        """Test circuit breaker for daily loss limit."""
        wallet_manager = MockWalletManager(balance=8.0)
        risk_manager = RiskManager(wallet_manager, max_daily_loss_pct=0.20)
        
        # Initialize daily tracking
        risk_manager.daily_start_balance = 10.0
        risk_manager.daily_start_date = datetime.now().date()
        risk_manager.daily_losses = 2.5  # 25% loss
        
        should_pause, reason = await risk_manager.should_pause_trading()
        
        assert should_pause is True
        assert "daily loss" in reason.lower()
    
    def test_record_trade_result_success(self):
        """Test recording a successful trade."""
        wallet_manager = MockWalletManager()
        risk_manager = RiskManager(wallet_manager)
        
        # Record a loss first
        risk_manager.consecutive_losses["test_strategy"] = 2
        
        # Record success
        risk_manager.record_trade_result("test_strategy", 0.1, True)
        
        # Consecutive losses should be reset
        assert risk_manager.consecutive_losses["test_strategy"] == 0
    
    def test_record_trade_result_failure(self):
        """Test recording a failed trade."""
        wallet_manager = MockWalletManager()
        risk_manager = RiskManager(wallet_manager)
        
        # Record failures
        risk_manager.record_trade_result("test_strategy", -0.1, False)
        risk_manager.record_trade_result("test_strategy", -0.2, False)
        
        # Consecutive losses should increment
        assert risk_manager.consecutive_losses["test_strategy"] == 2
    
    def test_record_trade_result_three_consecutive_losses(self):
        """Test allocation reduction after 3 consecutive losses."""
        wallet_manager = MockWalletManager()
        risk_manager = RiskManager(wallet_manager)
        
        # Record 3 consecutive losses
        risk_manager.record_trade_result("test_strategy", -0.1, False)
        risk_manager.record_trade_result("test_strategy", -0.1, False)
        risk_manager.record_trade_result("test_strategy", -0.1, False)
        
        # Allocation should be reduced to 50%
        assert risk_manager.strategy_allocations["test_strategy"] == 0.5
    
    def test_record_trade_result_daily_loss_tracking(self):
        """Test daily loss tracking."""
        wallet_manager = MockWalletManager()
        risk_manager = RiskManager(wallet_manager)
        
        # Record losses
        risk_manager.record_trade_result("test_strategy", -0.5, False)
        risk_manager.record_trade_result("test_strategy", -0.3, False)
        
        # Daily losses should accumulate
        assert risk_manager.daily_losses == 0.8
    
    def test_record_trade_result_ignores_gains_in_daily_loss(self):
        """Test that gains don't affect daily loss tracking."""
        wallet_manager = MockWalletManager()
        risk_manager = RiskManager(wallet_manager)
        
        # Record loss and gain
        risk_manager.record_trade_result("test_strategy", -0.5, False)
        risk_manager.record_trade_result("test_strategy", 0.3, True)
        
        # Daily losses should only count losses
        assert risk_manager.daily_losses == 0.5
    
    def test_get_strategy_allocation_default(self):
        """Test default allocation for strategy with no history."""
        wallet_manager = MockWalletManager()
        risk_manager = RiskManager(wallet_manager)
        
        allocation = risk_manager.get_strategy_allocation("new_strategy")
        
        # Default allocation is 1.0
        assert allocation == 1.0
    
    def test_get_strategy_allocation_insufficient_history(self):
        """Test allocation with insufficient trade history."""
        wallet_manager = MockWalletManager()
        risk_manager = RiskManager(wallet_manager)
        
        # Add only 5 trades (need 10)
        for i in range(5):
            risk_manager.record_trade_result("test_strategy", 0.1, True)
        
        allocation = risk_manager.get_strategy_allocation("test_strategy")
        
        # Should use default allocation
        assert allocation == 1.0
    
    def test_get_strategy_allocation_winning_strategy(self):
        """Test allocation increase for winning strategy."""
        wallet_manager = MockWalletManager()
        risk_manager = RiskManager(wallet_manager)
        
        # Add 10 profitable trades
        for i in range(10):
            risk_manager.record_trade_result("test_strategy", 0.1, True)
        
        allocation = risk_manager.get_strategy_allocation("test_strategy")
        
        # Should increase allocation (> 0.8)
        assert allocation > 0.8
        assert allocation <= 1.0
    
    def test_get_strategy_allocation_losing_strategy(self):
        """Test allocation decrease for losing strategy."""
        wallet_manager = MockWalletManager()
        risk_manager = RiskManager(wallet_manager)
        
        # Add 10 losing trades
        for i in range(10):
            risk_manager.record_trade_result("test_strategy", -0.1, False)
        
        # Reset consecutive losses to avoid 50% reduction
        risk_manager.consecutive_losses["test_strategy"] = 0
        
        allocation = risk_manager.get_strategy_allocation("test_strategy")
        
        # Should decrease allocation (< 0.8)
        assert allocation >= 0.5
        assert allocation < 0.8
    
    def test_get_consecutive_losses(self):
        """Test getting consecutive loss count."""
        wallet_manager = MockWalletManager()
        risk_manager = RiskManager(wallet_manager)
        
        risk_manager.record_trade_result("test_strategy", -0.1, False)
        risk_manager.record_trade_result("test_strategy", -0.1, False)
        
        count = risk_manager.get_consecutive_losses("test_strategy")
        
        assert count == 2
    
    def test_get_daily_loss_percentage(self):
        """Test getting daily loss percentage."""
        wallet_manager = MockWalletManager()
        risk_manager = RiskManager(wallet_manager)
        
        risk_manager.daily_start_balance = 10.0
        risk_manager.daily_losses = 1.5
        
        loss_pct = risk_manager.get_daily_loss_percentage()
        
        assert loss_pct == 0.15  # 15%
    
    def test_reset_daily_tracking(self):
        """Test manually resetting daily tracking."""
        wallet_manager = MockWalletManager()
        risk_manager = RiskManager(wallet_manager)
        
        risk_manager.daily_start_balance = 10.0
        risk_manager.daily_losses = 2.0
        
        risk_manager.reset_daily_tracking()
        
        assert risk_manager.daily_start_balance is None
        assert risk_manager.daily_losses == 0.0
    
    def test_unpause_trading(self):
        """Test manually unpausing trading."""
        wallet_manager = MockWalletManager()
        risk_manager = RiskManager(wallet_manager)
        
        risk_manager.is_paused = True
        risk_manager.pause_reason = "Test pause"
        
        risk_manager.unpause_trading()
        
        assert risk_manager.is_paused is False
        assert risk_manager.pause_reason is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
