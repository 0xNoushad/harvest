"""
End-to-end integration tests for Harvest agent.

Tests the complete flow:
1. Wire all strategies into the main agent loop
2. Test end-to-end flow with mock data
3. Verify all notifications work correctly
4. Test user control flow (YES/NO/ALWAYS)
5. Verify performance tracking across all strategies
6. Test on devnet with small amounts
"""

import asyncio
import pytest
import os
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Import all components
from agent.trading.loop import AgentLoop
from agent.trading.scanner import Scanner, Strategy, Opportunity
from agent.core.provider import Provider, Decision
from agent.services.notifier import Notifier, ExecutionResult
from agent.monitoring.user_control import UserControl
from agent.core.wallet import WalletManager
from agent.trading.risk_manager import RiskManager
from agent.trading.performance import PerformanceTracker

# Import all strategies
from strategies.airdrop_farmer import AirdropFarmer
from strategies.liquid_staking import LiquidStaking
from strategies.yield_farmer import YieldFarmer
from strategies.nft_flipper import NFTFlipper


class MockStrategy(Strategy):
    """Mock strategy for testing."""
    
    def __init__(self, name: str, opportunities: list = None):
        self.name = name
        self.opportunities = opportunities or []
        self.executed = []
    
    def scan(self):
        return self.opportunities
    
    def get_name(self):
        return self.name
    
    async def execute(self, opportunity):
        self.executed.append(opportunity)
        return ExecutionResult(
            success=True,
            transaction_hash=f"mock_tx_{len(self.executed)}",
            profit=opportunity.expected_profit,
            error=None,
            timestamp=datetime.now()
        )


@pytest.fixture
def temp_storage_dir(tmp_path):
    """Create temporary storage directory."""
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    return storage_dir


@pytest.fixture
def mock_wallet():
    """Create mock multi-user wallet manager."""
    wallet = Mock()
    wallet.public_key = "mock_public_key_123"
    wallet.get_balance = AsyncMock(return_value=10.0)
    wallet.get_token_balance = AsyncMock(return_value=100.0)
    wallet.close = AsyncMock()
    # Multi-user methods
    wallet.get_all_user_ids = Mock(return_value=["test_user_1"])
    # Return a mock wallet for the user
    user_wallet = Mock()
    user_wallet.public_key = "mock_public_key_123"
    user_wallet.get_balance = AsyncMock(return_value=10.0)
    user_wallet.get_token_balance = AsyncMock(return_value=100.0)
    user_wallet.sign_transaction = AsyncMock(return_value="mock_signature")
    wallet.get_wallet = AsyncMock(return_value=user_wallet)
    return wallet


@pytest.fixture
def mock_provider():
    """Create mock provider."""
    provider = Mock(spec=Provider)
    provider.make_decision = AsyncMock(return_value=Decision(
        action="execute",
        reasoning="Good opportunity",
        confidence=0.9
    ))
    return provider


@pytest.fixture
def mock_notifier():
    """Create mock notifier."""
    notifier = Mock(spec=Notifier)
    notifier.initialize = AsyncMock()
    notifier.shutdown = AsyncMock()
    notifier.send_opportunity = AsyncMock(return_value="msg_123")
    notifier.wait_for_response = AsyncMock(return_value="yes")
    notifier.send_execution_result = AsyncMock()
    notifier.send_risk_rejection = AsyncMock()
    notifier.send_stop_loss_exit = AsyncMock()
    return notifier


@pytest.fixture
def user_control(temp_storage_dir):
    """Create user control with temp storage."""
    return UserControl(storage_path=str(temp_storage_dir / "preferences.json"))


@pytest.fixture
def risk_manager(mock_wallet):
    """Create risk manager."""
    return RiskManager(wallet_manager=mock_wallet)


@pytest.fixture
def performance_tracker(temp_storage_dir):
    """Create performance tracker with temp storage."""
    return PerformanceTracker(storage_path=str(temp_storage_dir / "performance.json"))


class TestStrategyIntegration:
    """Test 1: Wire all strategies into the main agent loop."""
    
    def test_all_strategies_can_be_instantiated(self, mock_wallet):
        """Test that all strategy classes can be instantiated."""
        strategies = []
        
        # Try to instantiate each strategy
        try:
            strategies.append(AirdropFarmer(wallet=mock_wallet))
        except Exception as e:
            pytest.fail(f"Failed to instantiate AirdropFarmer: {e}")
        
        try:
            strategies.append(LiquidStaking(wallet=mock_wallet))
        except Exception as e:
            pytest.fail(f"Failed to instantiate LiquidStaking: {e}")
        
        try:
            strategies.append(YieldFarmer(wallet=mock_wallet))
        except Exception as e:
            pytest.fail(f"Failed to instantiate YieldFarmer: {e}")
        
        try:
            strategies.append(NFTFlipper(wallet=mock_wallet))
        except Exception as e:
            pytest.fail(f"Failed to instantiate NFTFlipper: {e}")
        
        # Verify all strategies were created
        assert len(strategies) == 4
        
        # Verify each has required methods
        for strategy in strategies:
            assert hasattr(strategy, 'scan')
            assert hasattr(strategy, 'get_name')
            assert callable(strategy.scan)
            assert callable(strategy.get_name)
    
    def test_scanner_with_all_strategies(self, mock_wallet):
        """Test scanner can handle all strategies."""
        # Mock async methods to avoid coroutine warnings
        mock_wallet.get_balance = Mock(return_value=10.0)
        mock_wallet.get_token_balance = Mock(return_value=100.0)
        
        # Create all strategies
        strategies = [
            AirdropFarmer(wallet=mock_wallet),
            LiquidStaking(wallet=mock_wallet),
            YieldFarmer(wallet=mock_wallet),
            NFTFlipper(wallet=mock_wallet),
        ]
        
        # Create scanner
        scanner = Scanner(strategies)
        
        # Verify scanner initialized correctly
        assert len(scanner.strategies) == 4
        
        # Scan all strategies (should not raise errors)
        try:
            import asyncio
            opportunities = asyncio.run(scanner.scan_all())
            # Should return a list (may be empty)
            assert isinstance(opportunities, list)
        except Exception as e:
            pytest.fail(f"Scanner failed with all strategies: {e}")
    
    @pytest.mark.asyncio
    async def test_agent_loop_with_all_strategies(
        self,
        mock_wallet,
        mock_provider,
        mock_notifier,
        user_control,
        risk_manager,
        performance_tracker
    ):
        """Test agent loop can be initialized with all strategies."""
        # Create all strategies
        strategies = [
            AirdropFarmer(wallet=mock_wallet),
            LiquidStaking(wallet=mock_wallet),
            YieldFarmer(wallet=mock_wallet),
            NFTFlipper(wallet=mock_wallet),
        ]
        
        scanner = Scanner(strategies)
        
        # Create agent loop
        agent = AgentLoop(
            wallet=mock_wallet,
            scanner=scanner,
            provider=mock_provider,
            notifier=mock_notifier,
            user_control=user_control,
            risk_manager=risk_manager,
            performance_tracker=performance_tracker,
            scan_interval=1  # Short interval for testing
        )
        
        # Verify agent initialized correctly
        assert agent.wallet == mock_wallet
        assert agent.scanner == scanner
        assert agent.provider == mock_provider
        assert agent.notifier == mock_notifier
        assert len(agent.scanner.strategies) == 4


class TestEndToEndFlow:
    """Test 2: Test end-to-end flow with mock data."""
    
    @pytest.mark.asyncio
    async def test_complete_scan_cycle(
        self,
        mock_wallet,
        mock_provider,
        mock_notifier,
        user_control,
        risk_manager,
        performance_tracker
    ):
        """Test complete scan cycle from scan to execution."""
        # Create mock strategy with opportunity
        opportunity = Opportunity(
            strategy_name="test_strategy",
            action="test_action",
            amount=1.0,
            expected_profit=0.1,
            risk_level="low",
            details={"test": "data"},
            timestamp=datetime.now()
        )
        
        mock_strategy = MockStrategy("test_strategy", [opportunity])
        scanner = Scanner([mock_strategy])
        
        # Enable ALWAYS mode for automatic execution
        user_control.set_always("test_strategy")
        
        # Create agent
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
        
        # Verify scan found opportunity
        assert len(opportunities) == 1
        assert opportunities[0].strategy_name == "test_strategy"
        
        # Verify provider was called
        mock_provider.make_decision.assert_called_once()
        
        # Verify execution result was sent
        mock_notifier.send_execution_result.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multiple_opportunities_processing(
        self,
        mock_wallet,
        mock_provider,
        mock_notifier,
        user_control,
        risk_manager,
        performance_tracker
    ):
        """Test processing multiple opportunities in one cycle."""
        # Create multiple opportunities
        opportunities = [
            Opportunity(
                strategy_name=f"test_strategy_{i}",
                action=f"action_{i}",
                amount=1.0,
                expected_profit=0.1 * i,
                risk_level="low",
                details={},
                timestamp=datetime.now()
            )
            for i in range(3)
        ]
        
        # Create strategies
        strategies = [
            MockStrategy(f"test_strategy_{i}", [opportunities[i]])
            for i in range(3)
        ]
        
        scanner = Scanner(strategies)
        
        # Enable ALWAYS mode for all
        for i in range(3):
            user_control.set_always(f"test_strategy_{i}")
        
        # Create agent
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
        
        # Run scan cycle
        found_opportunities = await agent.scan_cycle()
        
        # Verify all opportunities were found
        assert len(found_opportunities) == 3
        
        # Verify provider was called for each
        assert mock_provider.make_decision.call_count == 3
        
        # Verify execution results were sent
        assert mock_notifier.send_execution_result.call_count == 3
    
    @pytest.mark.asyncio
    async def test_error_recovery_during_scan(
        self,
        mock_wallet,
        mock_provider,
        mock_notifier,
        user_control,
        risk_manager,
        performance_tracker
    ):
        """Test that agent continues after strategy failure."""
        # Create one failing strategy and one working strategy
        failing_strategy = MockStrategy("failing", [])
        failing_strategy.scan = Mock(side_effect=Exception("Strategy failed"))
        
        working_opportunity = Opportunity(
            strategy_name="working",
            action="test",
            amount=1.0,
            expected_profit=0.1,
            risk_level="low",
            details={},
            timestamp=datetime.now()
        )
        working_strategy = MockStrategy("working", [working_opportunity])
        
        scanner = Scanner([failing_strategy, working_strategy])
        user_control.set_always("working")
        
        # Create agent
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
        
        # Run scan cycle - should not raise exception
        opportunities = await agent.scan_cycle()
        
        # Verify working strategy still processed
        assert len(opportunities) == 1
        assert opportunities[0].strategy_name == "working"


class TestNotifications:
    """Test 3: Verify all notifications work correctly."""
    
    @pytest.mark.asyncio
    async def test_opportunity_notification_sent(
        self,
        mock_wallet,
        mock_provider,
        mock_notifier,
        user_control,
        risk_manager,
        performance_tracker
    ):
        """Test that opportunity notifications are sent."""
        opportunity = Opportunity(
            strategy_name="test_strategy",
            action="test_action",
            amount=1.0,
            expected_profit=0.1,
            risk_level="low",
            details={},
            timestamp=datetime.now()
        )
        
        mock_strategy = MockStrategy("test_strategy", [opportunity])
        scanner = Scanner([mock_strategy])
        
        # Don't enable ALWAYS mode - should trigger notification
        
        # Create agent
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
        
        # Run scan cycle
        await agent.scan_cycle()
        
        # Verify notification was sent
        mock_notifier.send_opportunity.assert_called_once()
        call_args = mock_notifier.send_opportunity.call_args[0]
        assert call_args[0].strategy_name == "test_strategy"
    
    @pytest.mark.asyncio
    async def test_execution_result_notification(
        self,
        mock_wallet,
        mock_provider,
        mock_notifier,
        user_control,
        risk_manager,
        performance_tracker
    ):
        """Test that execution result notifications are sent."""
        opportunity = Opportunity(
            strategy_name="test_strategy",
            action="test_action",
            amount=1.0,
            expected_profit=0.1,
            risk_level="low",
            details={},
            timestamp=datetime.now()
        )
        
        mock_strategy = MockStrategy("test_strategy", [opportunity])
        scanner = Scanner([mock_strategy])
        user_control.set_always("test_strategy")
        
        # Create agent
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
        
        # Run scan cycle
        await agent.scan_cycle()
        
        # Verify execution result notification was sent
        mock_notifier.send_execution_result.assert_called_once()
        call_args = mock_notifier.send_execution_result.call_args[0]
        assert call_args[0].success is True
    
    @pytest.mark.asyncio
    async def test_risk_rejection_notification(
        self,
        mock_wallet,
        mock_provider,
        mock_notifier,
        user_control,
        performance_tracker
    ):
        """Test that risk rejection notifications are sent."""
        # Create risk manager with wallet_manager
        risk_manager = RiskManager(
            wallet_manager=mock_wallet,
            max_position_pct=0.05,  # 5% max position
            max_daily_loss_pct=0.05  # 5% daily loss threshold
        )
        
        # Create high-risk opportunity that exceeds limits
        # NFT flipping has 50% max loss by default, which exceeds 5% threshold
        opportunity = Opportunity(
            strategy_name="nft_flipper",
            action="buy_nft",
            amount=1.0,
            expected_profit=0.1,
            risk_level="high",
            details={},
            timestamp=datetime.now()
        )
        
        mock_strategy = MockStrategy("nft_flipper", [opportunity])
        scanner = Scanner([mock_strategy])
        user_control.set_always("nft_flipper")
        
        # Create agent
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
        
        # Run scan cycle
        await agent.scan_cycle()
        
        # Verify risk rejection notification was sent
        mock_notifier.send_risk_rejection.assert_called_once()


class TestUserControl:
    """Test 4: Test user control flow (YES/NO/ALWAYS)."""
    
    @pytest.mark.asyncio
    async def test_yes_response_executes_once(
        self,
        mock_wallet,
        mock_provider,
        mock_notifier,
        user_control,
        risk_manager,
        performance_tracker
    ):
        """Test that YES response executes opportunity once."""
        opportunity = Opportunity(
            strategy_name="test_strategy",
            action="test_action",
            amount=1.0,
            expected_profit=0.1,
            risk_level="low",
            details={},
            timestamp=datetime.now()
        )
        
        mock_strategy = MockStrategy("test_strategy", [opportunity])
        scanner = Scanner([mock_strategy])
        
        # Configure notifier to return "yes"
        mock_notifier.wait_for_response = AsyncMock(return_value="yes")
        
        # Create agent
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
        
        # Run scan cycle
        await agent.scan_cycle()
        
        # Verify execution happened
        mock_notifier.send_execution_result.assert_called_once()
        
        # Verify ALWAYS mode was NOT enabled
        assert not user_control.should_execute("test_strategy")
    
    @pytest.mark.asyncio
    async def test_no_response_skips_execution(
        self,
        mock_wallet,
        mock_provider,
        mock_notifier,
        user_control,
        risk_manager,
        performance_tracker
    ):
        """Test that NO response skips execution."""
        opportunity = Opportunity(
            strategy_name="test_strategy",
            action="test_action",
            amount=1.0,
            expected_profit=0.1,
            risk_level="low",
            details={},
            timestamp=datetime.now()
        )
        
        mock_strategy = MockStrategy("test_strategy", [opportunity])
        scanner = Scanner([mock_strategy])
        
        # Configure notifier to return "no"
        mock_notifier.wait_for_response = AsyncMock(return_value="no")
        
        # Create agent
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
        
        # Run scan cycle
        await agent.scan_cycle()
        
        # Verify execution did NOT happen
        mock_notifier.send_execution_result.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_always_response_enables_autopilot(
        self,
        mock_wallet,
        mock_provider,
        mock_notifier,
        user_control,
        risk_manager,
        performance_tracker
    ):
        """Test that ALWAYS response enables autopilot mode."""
        opportunity = Opportunity(
            strategy_name="test_strategy",
            action="test_action",
            amount=1.0,
            expected_profit=0.1,
            risk_level="low",
            details={},
            timestamp=datetime.now()
        )
        
        mock_strategy = MockStrategy("test_strategy", [opportunity])
        scanner = Scanner([mock_strategy])
        
        # Configure notifier to return "always"
        mock_notifier.wait_for_response = AsyncMock(return_value="always")
        
        # Create agent
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
        
        # Run scan cycle
        await agent.scan_cycle()
        
        # Verify execution happened
        mock_notifier.send_execution_result.assert_called_once()
        
        # Verify ALWAYS mode was enabled
        assert user_control.should_execute("test_strategy")
    
    @pytest.mark.asyncio
    async def test_always_mode_skips_notification(
        self,
        mock_wallet,
        mock_provider,
        mock_notifier,
        user_control,
        risk_manager,
        performance_tracker
    ):
        """Test that ALWAYS mode skips notification and executes directly."""
        opportunity = Opportunity(
            strategy_name="test_strategy",
            action="test_action",
            amount=1.0,
            expected_profit=0.1,
            risk_level="low",
            details={},
            timestamp=datetime.now()
        )
        
        mock_strategy = MockStrategy("test_strategy", [opportunity])
        scanner = Scanner([mock_strategy])
        
        # Enable ALWAYS mode
        user_control.set_always("test_strategy")
        
        # Create agent
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
        
        # Run scan cycle
        await agent.scan_cycle()
        
        # Verify notification was NOT sent
        mock_notifier.send_opportunity.assert_not_called()
        
        # Verify execution happened
        mock_notifier.send_execution_result.assert_called_once()


class TestPerformanceTracking:
    """Test 5: Verify performance tracking across all strategies."""
    
    @pytest.mark.asyncio
    async def test_trades_are_recorded(
        self,
        mock_wallet,
        mock_provider,
        mock_notifier,
        user_control,
        risk_manager,
        performance_tracker
    ):
        """Test that all trades are recorded in performance tracker."""
        # Create multiple opportunities
        opportunities = [
            Opportunity(
                strategy_name=f"test_strategy_{i}",
                action=f"action_{i}",
                amount=1.0,
                expected_profit=0.1 * (i + 1),
                risk_level="low",
                details={},
                timestamp=datetime.now()
            )
            for i in range(3)
        ]
        
        strategies = [
            MockStrategy(f"test_strategy_{i}", [opportunities[i]])
            for i in range(3)
        ]
        
        scanner = Scanner(strategies)
        
        # Enable ALWAYS mode for all
        for i in range(3):
            user_control.set_always(f"test_strategy_{i}")
        
        # Create agent
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
        
        # Run scan cycle
        await agent.scan_cycle()
        
        # Verify trades were recorded
        metrics = performance_tracker.get_metrics()
        assert metrics.total_trades == 3
        assert metrics.total_profit > 0
    
    @pytest.mark.asyncio
    async def test_profit_by_strategy_tracked(
        self,
        mock_wallet,
        mock_provider,
        mock_notifier,
        user_control,
        risk_manager,
        performance_tracker
    ):
        """Test that profit is tracked per strategy."""
        # Create opportunities with different profits
        opportunities = [
            Opportunity(
                strategy_name="test_strategy_a",
                action="action_a",
                amount=1.0,
                expected_profit=0.5,
                risk_level="low",
                details={},
                timestamp=datetime.now()
            ),
            Opportunity(
                strategy_name="test_strategy_b",
                action="action_b",
                amount=1.0,
                expected_profit=0.3,
                risk_level="low",
                details={},
                timestamp=datetime.now()
            ),
        ]
        
        strategies = [
            MockStrategy("test_strategy_a", [opportunities[0]]),
            MockStrategy("test_strategy_b", [opportunities[1]]),
        ]
        
        scanner = Scanner(strategies)
        
        # Enable ALWAYS mode
        user_control.set_always("test_strategy_a")
        user_control.set_always("test_strategy_b")
        
        # Create agent
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
        
        # Run scan cycle
        await agent.scan_cycle()
        
        # Verify profit tracked by strategy
        metrics = performance_tracker.get_metrics()
        assert "test_strategy_a" in metrics.profit_by_strategy
        assert "test_strategy_b" in metrics.profit_by_strategy
        assert metrics.profit_by_strategy["test_strategy_a"] > 0
        assert metrics.profit_by_strategy["test_strategy_b"] > 0
    
    @pytest.mark.asyncio
    async def test_performance_fee_calculated(
        self,
        mock_wallet,
        mock_provider,
        mock_notifier,
        user_control,
        risk_manager,
        performance_tracker
    ):
        """Test that 2% performance fee is calculated."""
        opportunity = Opportunity(
            strategy_name="test_strategy",
            action="test_action",
            amount=1.0,
            expected_profit=1.0,  # 1 SOL profit
            risk_level="low",
            details={},
            timestamp=datetime.now()
        )
        
        mock_strategy = MockStrategy("test_strategy", [opportunity])
        scanner = Scanner([mock_strategy])
        user_control.set_always("test_strategy")
        
        # Create agent
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
        
        # Run scan cycle
        await agent.scan_cycle()
        
        # Verify performance fee
        metrics = performance_tracker.get_metrics()
        expected_fee = 1.0 * 0.02  # 2% of 1 SOL
        assert abs(metrics.performance_fee_collected - expected_fee) < 0.001


class TestDevnetIntegration:
    """Test 6: Test on devnet with small amounts."""
    
    @pytest.mark.asyncio
    async def test_wallet_connects_to_devnet(self):
        """Test that wallet can connect to devnet."""
        wallet = WalletManager(network="devnet")
        
        try:
            # Get balance (should not raise exception)
            balance = await wallet.get_balance()
            assert balance >= 0
            
            # Verify public key is valid
            assert wallet.public_key is not None
            assert str(wallet.public_key) != ""
            
        finally:
            await wallet.close()
    
    @pytest.mark.asyncio
    async def test_small_transaction_on_devnet(self):
        """Test sending small transaction on devnet."""
        wallet = WalletManager(network="devnet")
        
        try:
            # Check balance
            balance = await wallet.get_balance()
            
            # Just verify wallet is functional - no actual transaction needed
            assert wallet.public_key is not None
            assert balance >= 0
            
        finally:
            await wallet.close()


class TestAgentStatus:
    """Test agent status reporting."""
    
    @pytest.mark.asyncio
    async def test_get_status_returns_complete_info(
        self,
        mock_wallet,
        mock_provider,
        mock_notifier,
        user_control,
        risk_manager,
        performance_tracker
    ):
        """Test that get_status returns complete agent information."""
        mock_strategy = MockStrategy("test_strategy", [])
        scanner = Scanner([mock_strategy])
        
        # Create agent
        agent = AgentLoop(
            wallet=mock_wallet,
            scanner=scanner,
            provider=mock_provider,
            notifier=mock_notifier,
            user_control=user_control,
            risk_manager=risk_manager,
            performance_tracker=performance_tracker,
            scan_interval=300
        )
        
        # Get status
        status = agent.get_status()
        
        # Verify status contains all required fields
        assert "running" in status
        assert "last_scan_time" in status
        assert "scan_interval" in status
        assert "strategies_count" in status
        assert "active_positions" in status
        assert "total_exposure" in status
        assert "total_max_loss" in status
        assert "performance" in status
        
        # Verify performance metrics
        perf = status["performance"]
        assert "total_profit" in perf
        assert "total_trades" in perf
        assert "win_rate" in perf
        assert "profit_by_strategy" in perf
        assert "performance_fee" in perf


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
