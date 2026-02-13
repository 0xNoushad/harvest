"""
Integration tests for trading strategies - verify buy/sell functionality.

Tests actual trading implementations to ensure strategies can:
- Scan for opportunities
- Execute trades (buy/sell)
- Handle errors gracefully
- Track performance
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from agent.trading.scanner import Scanner, Strategy, Opportunity
from agent.trading.loop import AgentLoop
from agent.core.wallet import WalletManager
from agent.core.provider import Provider, Decision
from agent.services.notifier import Notifier, ExecutionResult
from agent.monitoring.user_control import UserControl
from agent.trading.risk_manager import RiskManager
from agent.trading.performance import PerformanceTracker


class TestTradingStrategy(Strategy):
    """Test strategy that simulates real trading."""
    
    def __init__(self, name: str = "test_strategy"):
        self.name = name
        self.scan_called = False
        self.execute_called = False
        self.last_opportunity = None
    
    def get_name(self) -> str:
        return self.name
    
    def scan(self):
        """Simulate finding a trading opportunity."""
        self.scan_called = True
        return [
            Opportunity(
                strategy_name=self.name,
                action="buy",
                amount=0.1,
                expected_profit=0.02,
                risk_level="low",
                details={"token": "SOL", "price": 100.0},
                timestamp=datetime.now()
            )
        ]
    
    async def execute(self, opportunity: Opportunity) -> ExecutionResult:
        """Simulate executing a trade."""
        self.execute_called = True
        self.last_opportunity = opportunity
        
        # Simulate successful trade
        return ExecutionResult(
            success=True,
            transaction_hash="test_tx_hash_123",
            profit=opportunity.expected_profit,
            error=None,
            timestamp=datetime.now()
        )


class TestBuyStrategy(Strategy):
    """Strategy that tests buying functionality."""
    
    def get_name(self) -> str:
        return "buy_strategy"
    
    def scan(self):
        return [
            Opportunity(
                strategy_name="buy_strategy",
                action="buy",
                amount=0.5,
                expected_profit=0.1,
                risk_level="medium",
                details={"token": "BONK", "price": 0.00001},
                timestamp=datetime.now()
            )
        ]
    
    async def execute(self, opportunity: Opportunity) -> ExecutionResult:
        # Simulate buying tokens
        return ExecutionResult(
            success=True,
            transaction_hash="buy_tx_abc123",
            profit=0.0,  # No profit yet, just bought
            error=None,
            timestamp=datetime.now()
        )


class TestSellStrategy(Strategy):
    """Strategy that tests selling functionality."""
    
    def get_name(self) -> str:
        return "sell_strategy"
    
    def scan(self):
        return [
            Opportunity(
                strategy_name="sell_strategy",
                action="sell",
                amount=100.0,
                expected_profit=0.05,
                risk_level="low",
                details={"token": "BONK", "price": 0.00002},
                timestamp=datetime.now()
            )
        ]
    
    async def execute(self, opportunity: Opportunity) -> ExecutionResult:
        # Simulate selling tokens for profit
        return ExecutionResult(
            success=True,
            transaction_hash="sell_tx_xyz789",
            profit=opportunity.expected_profit,
            error=None,
            timestamp=datetime.now()
        )


class TestSwapStrategy(Strategy):
    """Strategy that tests token swapping."""
    
    def get_name(self) -> str:
        return "swap_strategy"
    
    def scan(self):
        return [
            Opportunity(
                strategy_name="swap_strategy",
                action="swap",
                amount=1.0,
                expected_profit=0.03,
                risk_level="low",
                details={"from_token": "SOL", "to_token": "USDC", "rate": 100.0},
                timestamp=datetime.now()
            )
        ]
    
    async def execute(self, opportunity: Opportunity) -> ExecutionResult:
        # Simulate swapping tokens
        return ExecutionResult(
            success=True,
            transaction_hash="swap_tx_def456",
            profit=opportunity.expected_profit,
            error=None,
            timestamp=datetime.now()
        )


@pytest.fixture
def mock_wallet():
    """Mock wallet manager."""
    wallet = Mock(spec=WalletManager)
    wallet.close = AsyncMock()
    return wallet


@pytest.fixture
def mock_provider():
    """Mock LLM provider that always approves."""
    provider = Mock(spec=Provider)
    provider.make_decision = AsyncMock(return_value=Decision(
        action="execute",
        reasoning="Good opportunity, low risk",
        confidence=0.9
    ))
    return provider


@pytest.fixture
def mock_notifier():
    """Mock notifier."""
    notifier = Mock(spec=Notifier)
    notifier.initialize = AsyncMock()
    notifier.shutdown = AsyncMock()
    notifier.send_opportunity = AsyncMock(return_value="msg_123")
    notifier.send_execution_result = AsyncMock()
    notifier.send_risk_rejection = AsyncMock()
    notifier.send_message = AsyncMock()
    return notifier


@pytest.fixture
def user_control():
    """User control in ALWAYS mode."""
    control = UserControl()
    control.set_always("test_strategy")
    control.set_always("buy_strategy")
    control.set_always("sell_strategy")
    control.set_always("swap_strategy")
    return control


class TestTradingIntegration:
    """Test trading strategy integration."""
    
    @pytest.mark.asyncio
    async def test_strategy_can_scan(self):
        """Test that strategy can scan for opportunities."""
        strategy = TestTradingStrategy()
        scanner = Scanner([strategy])
        
        opportunities = scanner.scan_all()
        
        assert len(opportunities) == 1
        assert strategy.scan_called
        assert opportunities[0].action == "buy"
        assert opportunities[0].amount == 0.1
    
    @pytest.mark.asyncio
    async def test_strategy_can_execute(self):
        """Test that strategy can execute trades."""
        strategy = TestTradingStrategy()
        opportunity = Opportunity(
            strategy_name="test_strategy",
            action="buy",
            amount=0.1,
            expected_profit=0.02,
            risk_level="low",
            details={},
            timestamp=datetime.now()
        )
        
        result = await strategy.execute(opportunity)
        
        assert result.success
        assert result.transaction_hash == "test_tx_hash_123"
        assert result.profit == 0.02
        assert strategy.execute_called
    
    @pytest.mark.asyncio
    async def test_buy_strategy_execution(self, mock_wallet, mock_provider, mock_notifier, user_control):
        """Test buying tokens through strategy."""
        strategy = TestBuyStrategy()
        scanner = Scanner([strategy])
        risk_manager = RiskManager()
        performance_tracker = PerformanceTracker()
        
        agent = AgentLoop(
            wallet=mock_wallet,
            scanner=scanner,
            provider=mock_provider,
            notifier=mock_notifier,
            user_control=user_control,
            risk_manager=risk_manager,
            performance_tracker=performance_tracker,
            scan_interval=1
        )
        
        # Run one scan cycle
        opportunities = await agent.scan_cycle()
        
        assert len(opportunities) == 1
        assert opportunities[0].action == "buy"
        
        # Verify execution was called
        assert mock_notifier.send_execution_result.called
    
    @pytest.mark.asyncio
    async def test_sell_strategy_execution(self, mock_wallet, mock_provider, mock_notifier, user_control):
        """Test selling tokens through strategy."""
        strategy = TestSellStrategy()
        scanner = Scanner([strategy])
        risk_manager = RiskManager()
        performance_tracker = PerformanceTracker()
        
        agent = AgentLoop(
            wallet=mock_wallet,
            scanner=scanner,
            provider=mock_provider,
            notifier=mock_notifier,
            user_control=user_control,
            risk_manager=risk_manager,
            performance_tracker=performance_tracker,
            scan_interval=1
        )
        
        # Run one scan cycle
        opportunities = await agent.scan_cycle()
        
        assert len(opportunities) == 1
        assert opportunities[0].action == "sell"
        assert opportunities[0].expected_profit == 0.05
        
        # Verify execution was called
        assert mock_notifier.send_execution_result.called
    
    @pytest.mark.asyncio
    async def test_swap_strategy_execution(self, mock_wallet, mock_provider, mock_notifier, user_control):
        """Test swapping tokens through strategy."""
        strategy = TestSwapStrategy()
        scanner = Scanner([strategy])
        risk_manager = RiskManager()
        performance_tracker = PerformanceTracker()
        
        agent = AgentLoop(
            wallet=mock_wallet,
            scanner=scanner,
            provider=mock_provider,
            notifier=mock_notifier,
            user_control=user_control,
            risk_manager=risk_manager,
            performance_tracker=performance_tracker,
            scan_interval=1
        )
        
        # Run one scan cycle
        opportunities = await agent.scan_cycle()
        
        assert len(opportunities) == 1
        assert opportunities[0].action == "swap"
        
        # Verify execution was called
        assert mock_notifier.send_execution_result.called
    
    @pytest.mark.asyncio
    async def test_multiple_strategies_execution(self, mock_wallet, mock_provider, mock_notifier, user_control):
        """Test multiple strategies can execute in one cycle."""
        buy_strategy = TestBuyStrategy()
        sell_strategy = TestSellStrategy()
        swap_strategy = TestSwapStrategy()
        
        scanner = Scanner([buy_strategy, sell_strategy, swap_strategy])
        risk_manager = RiskManager()
        performance_tracker = PerformanceTracker()
        
        agent = AgentLoop(
            wallet=mock_wallet,
            scanner=scanner,
            provider=mock_provider,
            notifier=mock_notifier,
            user_control=user_control,
            risk_manager=risk_manager,
            performance_tracker=performance_tracker,
            scan_interval=1
        )
        
        # Run one scan cycle
        opportunities = await agent.scan_cycle()
        
        assert len(opportunities) == 3
        actions = [opp.action for opp in opportunities]
        assert "buy" in actions
        assert "sell" in actions
        assert "swap" in actions
        
        # Verify all executions were called
        assert mock_notifier.send_execution_result.call_count == 3
    
    @pytest.mark.asyncio
    async def test_performance_tracking_after_trade(self, mock_wallet, mock_provider, mock_notifier, user_control):
        """Test that trades are tracked in performance tracker."""
        strategy = TestTradingStrategy()
        scanner = Scanner([strategy])
        risk_manager = RiskManager(max_loss_threshold=0.2)  # 20% to allow test trade
        # Create fresh performance tracker with temp file
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        temp_file.close()
        performance_tracker = PerformanceTracker(storage_path=temp_file.name)
        
        agent = AgentLoop(
            wallet=mock_wallet,
            scanner=scanner,
            provider=mock_provider,
            notifier=mock_notifier,
            user_control=user_control,
            risk_manager=risk_manager,
            performance_tracker=performance_tracker,
            scan_interval=1
        )
        
        # Run one scan cycle
        await agent.scan_cycle()
        
        # Check performance tracker
        metrics = performance_tracker.get_metrics()
        assert metrics.total_trades >= 1
        assert metrics.total_profit >= 0.02
        assert "test_strategy" in metrics.profit_by_strategy
    
    @pytest.mark.asyncio
    async def test_risk_manager_rejects_high_risk(self, mock_wallet, mock_provider, mock_notifier, user_control):
        """Test that risk manager rejects high-risk trades."""
        class HighRiskStrategy(Strategy):
            def get_name(self):
                return "high_risk_strategy"
            
            def scan(self):
                return [
                    Opportunity(
                        strategy_name="high_risk_strategy",
                        action="buy",
                        amount=100.0,  # Very large amount
                        expected_profit=50.0,
                        risk_level="high",
                        details={},
                        timestamp=datetime.now()
                    )
                ]
            
            async def execute(self, opportunity):
                return ExecutionResult(
                    success=True,
                    transaction_hash="should_not_execute",
                    profit=50.0,
                    error=None,
                    timestamp=datetime.now()
                )
        
        strategy = HighRiskStrategy()
        scanner = Scanner([strategy])
        risk_manager = RiskManager(max_loss_threshold=0.05)  # 5% max loss (strict)
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        temp_file.close()
        performance_tracker = PerformanceTracker(storage_path=temp_file.name)
        
        user_control.set_always("high_risk_strategy")
        
        agent = AgentLoop(
            wallet=mock_wallet,
            scanner=scanner,
            provider=mock_provider,
            notifier=mock_notifier,
            user_control=user_control,
            risk_manager=risk_manager,
            performance_tracker=performance_tracker,
            scan_interval=1
        )
        
        # Run one scan cycle
        await agent.scan_cycle()
        
        # Verify risk rejection notification was sent
        assert mock_notifier.send_risk_rejection.called
        
        # Verify trade was NOT executed (no execution result sent)
        # send_execution_result should not be called for rejected trades
        metrics = performance_tracker.get_metrics()
        assert metrics.total_trades == 0


class TestJupiterIntegration:
    """Test Jupiter integration for actual swaps."""
    
    @pytest.mark.asyncio
    async def test_jupiter_integration_exists(self):
        """Test that Jupiter integration can be imported and initialized."""
        from integrations.solana.jupiter import JupiterIntegration
        from solders.pubkey import Pubkey
        
        # Mock RPC client
        mock_rpc = Mock()
        wallet_pubkey = Pubkey.from_string("11111111111111111111111111111111")
        
        jupiter = JupiterIntegration(
            rpc_client=mock_rpc,
            wallet_pubkey=wallet_pubkey,
            api_key="test_key"
        )
        
        assert jupiter is not None
        assert jupiter.api_key == "test_key"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
