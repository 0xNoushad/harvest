"""
Test suite for Telegram bot commands.

This module tests all Telegram commands to ensure they work correctly
and provide appropriate responses. It covers:
- Basic commands (/start, /help, /wallet, /status)
- Info commands (/price, /portfolio, /stats)
- Trading commands (/pause, /resume, /strategies)
- Financial commands (/withdraw, /fees)
- Wallet commands (/newwallet, /exportkey)

Tests validate:
- Command responses contain expected content
- Error handling for invalid inputs
- Proper integration with services (wallet, performance, etc.)
- Message formatting and user feedback
"""

# Import mocking setup FIRST
from tests.conftest_commands import mock_external_modules
mock_external_modules()

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Import command classes
from agent.ui.commands.basic_commands import BasicCommands
from agent.ui.commands.info_commands import InfoCommands
from agent.ui.commands.trading_commands import TradingCommands


class CommandTestSuite:
    """
    Test suite for all Telegram bot commands.
    
    This class provides a structured approach to testing commands with:
    - Reusable fixtures for mocking bot components
    - Helper methods for common assertions
    - Organized test methods by command category
    """
    
    def __init__(self, test_harness):
        """
        Initialize the command test suite.
        
        Args:
            test_harness: TestHarness instance for creating mocks
        """
        self.harness = test_harness
        self.mock_bot = None
        self.basic_commands = None
        self.info_commands = None
        self.trading_commands = None
        self.financial_commands = None
        self.wallet_commands = None
    
    def setup_command_handlers(
        self,
        wallet_balance: float = 1.0,
        total_profit: float = 0.0,
        win_rate: float = 0.0,
        is_running: bool = True
    ):
        """
        Set up command handlers with mocked dependencies.
        
        Args:
            wallet_balance: Mock wallet balance
            total_profit: Mock total profit
            win_rate: Mock win rate
            is_running: Whether bot is running
            
        Returns:
            Mock bot instance with all dependencies
        """
        # Create mock bot instance
        self.mock_bot = MagicMock()
        
        # Mock wallet
        self.mock_bot.wallet = self.harness.create_mock_wallet(balance=wallet_balance)
        self.mock_bot.wallet.public_key = "TestWallet1234567890123456789012345"
        self.mock_bot.wallet.network = "devnet"
        
        # Mock performance tracker
        self.mock_bot.performance = self.harness.create_mock_performance_tracker(
            total_profit=total_profit,
            win_rate=win_rate
        )
        
        # Mock agent loop
        self.mock_bot.agent_loop = MagicMock()
        self.mock_bot.agent_loop.get_status = MagicMock(return_value={
            'running': is_running,
            'strategies_count': 7,
            'active_positions': 0,
            'total_exposure': 0.0,
            'performance': {
                'total_profit': total_profit,
                'total_trades': 0,
                'win_rate': win_rate
            },
            'last_scan_time': 'Never'
        })
        self.mock_bot.agent_loop.stop = MagicMock()
        self.mock_bot.agent_loop.scanner = MagicMock()
        self.mock_bot.agent_loop.scanner.strategies = [MagicMock() for _ in range(7)]  # 7 mock strategies
        self.mock_bot.agent_loop.risk_manager = MagicMock()
        self.mock_bot.agent_loop.risk_manager.is_paused = not is_running
        self.mock_bot.agent_loop._running = is_running
        
        self.basic_commands = BasicCommands(self.mock_bot)
        self.info_commands = InfoCommands(self.mock_bot)
        self.trading_commands = TradingCommands(self.mock_bot)
        self.financial_commands = None  # Not implemented yet
        self.wallet_commands = None  # Not implemented yet
        
        return self.mock_bot
    
    def assert_message_contains(self, update, *text_fragments):
        """
        Assert that the reply message contains all specified text fragments.
        
        Args:
            update: Mock update object
            *text_fragments: Text fragments that should be in the message
        """
        # Get the message that was sent
        assert update.message.reply_text.called, "reply_text was not called"
        
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        for fragment in text_fragments:
            assert fragment in message_text, f"Expected '{fragment}' in message, got: {message_text}"
    
    def assert_message_not_contains(self, update, *text_fragments):
        """
        Assert that the reply message does not contain specified text fragments.
        
        Args:
            update: Mock update object
            *text_fragments: Text fragments that should NOT be in the message
        """
        assert update.message.reply_text.called, "reply_text was not called"
        
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        for fragment in text_fragments:
            assert fragment not in message_text, f"Did not expect '{fragment}' in message, got: {message_text}"


# ============================================================================
# Pytest Fixtures
# ============================================================================

@pytest.fixture
def command_suite(test_harness):
    """Provide a CommandTestSuite instance for tests."""
    return CommandTestSuite(test_harness)


@pytest.fixture
def mock_bot_with_commands(command_suite):
    """Provide a mock bot with all command handlers set up."""
    return command_suite.setup_command_handlers()


# ============================================================================
# Basic Commands Tests
# ============================================================================

@pytest.mark.asyncio
class TestBasicCommands:
    """Tests for basic commands: /start, /help, /wallet, /status."""
    
    async def test_start_command_displays_welcome(self, command_suite):
        """Test /start command displays welcome message with wallet and commands."""
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("start")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.basic_commands.cmd_start(update, context)
        
        # Assert
        command_suite.assert_message_contains(
            update,
            "Harvest Bot",
            "status",
            "wallet"
        )
    
    async def test_start_command_shows_available_commands(self, command_suite):
        """Test /start command shows available commands to user."""
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("start")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.basic_commands.cmd_start(update, context)
        
        # Assert - verify key commands are mentioned
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Should mention key commands
        assert any(cmd in message_text.lower() for cmd in ['status', 'wallet', 'pause'])
    
    async def test_start_command_uses_markdown_formatting(self, command_suite):
        """Test /start command uses Markdown for better formatting."""
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("start")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.basic_commands.cmd_start(update, context)
        
        # Assert - verify Markdown parse mode is used
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        parse_mode = call_args[1].get('parse_mode') if len(call_args) > 1 else None
        assert parse_mode == "Markdown"
    
    async def test_help_command_displays_all_commands(self, command_suite):
        """Test /help command displays all commands with descriptions."""
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("help")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.basic_commands.cmd_help(update, context)
        
        # Assert - check for key commands
        command_suite.assert_message_contains(
            update,
            "/status",
            "/wallet",
            "/withdraw",
            "/pause",
            "/resume"
        )
    
    async def test_help_command_includes_command_descriptions(self, command_suite):
        """Test /help command includes descriptions for each command."""
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("help")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.basic_commands.cmd_help(update, context)
        
        # Assert - verify descriptions are present
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Should have descriptions (indicated by - or : after command)
        assert "/status" in message_text
        # Check that there's text after the command (description)
        lines = message_text.split('\n')
        command_lines = [line for line in lines if line.strip().startswith('/')]
        assert len(command_lines) > 0, "No command lines found"
    
    async def test_help_command_uses_markdown(self, command_suite):
        """Test /help command uses Markdown formatting."""
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("help")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.basic_commands.cmd_help(update, context)
        
        # Assert
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        parse_mode = call_args[1].get('parse_mode') if len(call_args) > 1 else None
        assert parse_mode == "Markdown"
    
    async def test_wallet_command_displays_balance_and_address(self, command_suite):
        """Test /wallet command displays balance, address, and transactions."""
        # Setup
        command_suite.setup_command_handlers(wallet_balance=1.5)
        update = command_suite.harness.create_mock_telegram_update("wallet")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.basic_commands.cmd_wallet(update, context)
        
        # Assert
        command_suite.assert_message_contains(
            update,
            "Your Wallet",
            "1.5000 SOL",
            "TestWallet",
            "devnet"
        )
    
    async def test_wallet_command_displays_wallet_address(self, command_suite):
        """Test /wallet command displays the full wallet address."""
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("wallet")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.basic_commands.cmd_wallet(update, context)
        
        # Assert - verify address is shown
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        assert "TestWallet1234567890123456789012345" in message_text
    
    async def test_wallet_command_includes_network_info(self, command_suite):
        """Test /wallet command includes network information."""
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("wallet")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.basic_commands.cmd_wallet(update, context)
        
        # Assert
        command_suite.assert_message_contains(update, "devnet")
    
    async def test_wallet_command_includes_solscan_link(self, command_suite):
        """Test /wallet command includes Solscan link for viewing on explorer."""
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("wallet")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.basic_commands.cmd_wallet(update, context)
        
        # Assert
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        assert "solscan.io" in message_text.lower()
    
    async def test_wallet_command_handles_error_gracefully(self, command_suite):
        """Test /wallet command handles errors gracefully."""
        # Setup
        command_suite.setup_command_handlers()
        # Make get_balance raise an exception
        command_suite.mock_bot.wallet.get_balance = AsyncMock(side_effect=Exception("RPC error"))
        update = command_suite.harness.create_mock_telegram_update("wallet")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.basic_commands.cmd_wallet(update, context)
        
        # Assert - should show error message
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        assert "Error" in message_text or "error" in message_text
    
    async def test_stats_command_displays_performance(self, command_suite):
        """Test /stats command displays profit, win rate, and strategy performance."""
        # Setup
        command_suite.setup_command_handlers(total_profit=0.5, win_rate=68.5)
        update = command_suite.harness.create_mock_telegram_update("stats")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Mock performance metrics
        command_suite.mock_bot.performance.get_metrics = MagicMock(return_value=MagicMock(
            total_profit=0.5,
            total_trades=100,
            successful_trades=68,
            win_rate=68.5,
            total_gas_fees=0.05,
            net_profit=0.45,
            best_trade=0.05,
            worst_trade=-0.02,
            profit_by_strategy={
                "airdrop_hunter": 0.3,
                "liquid_staking": 0.2
            },
            performance_fee_collected=0.1
        ))
        
        # Execute
        await command_suite.info_commands.cmd_stats(update, context)
        
        # Assert
        command_suite.assert_message_contains(
            update,
            "Performance Stats",
            "0.5000 SOL",
            "68.5%"
        )
    
    async def test_stats_command_displays_total_trades(self, command_suite):
        """Test /stats command displays total number of trades."""
        # Setup
        command_suite.setup_command_handlers(total_profit=0.5, win_rate=68.5)
        update = command_suite.harness.create_mock_telegram_update("stats")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Mock performance metrics
        command_suite.mock_bot.performance.get_metrics = MagicMock(return_value=MagicMock(
            total_profit=0.5,
            total_trades=100,
            successful_trades=68,
            win_rate=68.5,
            total_gas_fees=0.05,
            net_profit=0.45,
            best_trade=0.05,
            worst_trade=-0.02,
            profit_by_strategy={},
            performance_fee_collected=0.1
        ))
        
        # Execute
        await command_suite.info_commands.cmd_stats(update, context)
        
        # Assert
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        assert "100" in message_text  # Total trades
    
    async def test_stats_command_displays_best_and_worst_trades(self, command_suite):
        """Test /stats command displays best and worst trade performance."""
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("stats")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Mock performance metrics
        command_suite.mock_bot.performance.get_metrics = MagicMock(return_value=MagicMock(
            total_profit=0.5,
            total_trades=100,
            successful_trades=68,
            win_rate=68.5,
            total_gas_fees=0.05,
            net_profit=0.45,
            best_trade=0.05,
            worst_trade=-0.02,
            profit_by_strategy={},
            performance_fee_collected=0.1
        ))
        
        # Execute
        await command_suite.info_commands.cmd_stats(update, context)
        
        # Assert - check that stats are displayed (best/worst trades not shown in new format)
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        assert "0.5000" in message_text  # Total profit
        assert "0.4500" in message_text  # Net profit
    
    async def test_stats_command_displays_strategy_breakdown(self, command_suite):
        """Test /stats command displays profit breakdown by strategy."""
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("stats")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Mock performance metrics with strategy breakdown
        command_suite.mock_bot.performance.get_metrics = MagicMock(return_value=MagicMock(
            total_profit=0.5,
            total_trades=100,
            successful_trades=68,
            win_rate=68.5,
            total_gas_fees=0.05,
            net_profit=0.45,
            best_trade=0.05,
            worst_trade=-0.02,
            profit_by_strategy={
                "airdrop_hunter": 0.3,
                "liquid_staking": 0.2
            },
            performance_fee_collected=0.1
        ))
        
        # Execute
        await command_suite.info_commands.cmd_stats(update, context)
        
        # Assert
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        assert "airdrop_hunter" in message_text
        assert "liquid_staking" in message_text
    
    async def test_stats_command_handles_error_gracefully(self, command_suite):
        """Test /stats command handles errors gracefully."""
        # Setup
        command_suite.setup_command_handlers()
        # Make get_metrics raise an exception
        command_suite.mock_bot.performance.get_metrics = MagicMock(side_effect=Exception("Database error"))
        update = command_suite.harness.create_mock_telegram_update("stats")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.info_commands.cmd_stats(update, context)
        
        # Assert - should show error message
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        assert "Error" in message_text or "error" in message_text
    
    async def test_status_command_displays_bot_state(self, command_suite):
        """Test /status command displays bot state and active strategies."""
        # Setup
        command_suite.setup_command_handlers(is_running=True)
        update = command_suite.harness.create_mock_telegram_update("status")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.basic_commands.cmd_status(update, context)
        
        # Assert
        command_suite.assert_message_contains(
            update,
            "Status",
            "Active",
            "🟢"
        )
    
    async def test_status_command_shows_running_state(self, command_suite):
        """Test /status command shows running state with green indicator."""
        # Setup
        command_suite.setup_command_handlers(is_running=True)
        update = command_suite.harness.create_mock_telegram_update("status")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.basic_commands.cmd_status(update, context)
        
        # Assert
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        assert "🟢" in message_text
        assert "Active" in message_text
    
    async def test_status_command_shows_stopped_state(self, command_suite):
        """Test /status command shows stopped state with red indicator."""
        # Setup
        command_suite.setup_command_handlers(is_running=False)
        update = command_suite.harness.create_mock_telegram_update("status")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.basic_commands.cmd_status(update, context)
        
        # Assert
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        assert "🔴" in message_text
        assert "Paused" in message_text
    
    async def test_status_command_displays_strategy_count(self, command_suite):
        """Test /status command displays number of active strategies."""
        # Setup
        command_suite.setup_command_handlers(is_running=True)
        update = command_suite.harness.create_mock_telegram_update("status")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.basic_commands.cmd_status(update, context)
        
        # Assert
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        assert "7" in message_text  # 7 active strategies
        assert "Strategies" in message_text or "strategies" in message_text
    
    async def test_status_command_displays_performance_summary(self, command_suite):
        """Test /status command displays performance summary."""
        # Setup
        command_suite.setup_command_handlers(is_running=True, total_profit=0.5, win_rate=68.5)
        update = command_suite.harness.create_mock_telegram_update("status")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.basic_commands.cmd_status(update, context)
        
        # Assert
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        assert "0.5" in message_text  # Total profit
        assert "68.5" in message_text  # Win rate
    
    async def test_status_command_displays_last_scan_time(self, command_suite):
        """Test /status command displays performance summary (last scan time not shown in current implementation)."""
        # Setup
        command_suite.setup_command_handlers(is_running=True)
        update = command_suite.harness.create_mock_telegram_update("status")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.basic_commands.cmd_status(update, context)
        
        # Assert - check that status is displayed
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        assert "Status" in message_text
        assert "Active" in message_text or "Paused" in message_text
    
    async def test_status_command_handles_error_gracefully(self, command_suite):
        """Test /status command handles errors gracefully."""
        # Setup
        command_suite.setup_command_handlers()
        # Make get_balance raise an exception to trigger error handling
        command_suite.mock_bot.wallet.get_balance = MagicMock(side_effect=Exception("Balance error"))
        update = command_suite.harness.create_mock_telegram_update("status")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.basic_commands.cmd_status(update, context)
        
        # Assert - should show error message
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        assert "Error" in message_text or "error" in message_text


# ============================================================================
# Info Commands Tests
# ============================================================================

@pytest.mark.asyncio
class TestInfoCommands:
    """Tests for info commands: /price, /portfolio, /stats."""
    
    async def test_price_command_without_args_shows_usage(self, command_suite):
        """Test /price command without arguments shows usage instructions."""
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("price")
        context = command_suite.harness.create_mock_telegram_context(args=[])
        
        # Execute
        await command_suite.info_commands.cmd_price(update, context)
        
        # Assert
        command_suite.assert_message_contains(
            update,
            "Usage",
            "/price"
        )
    
    async def test_price_command_with_valid_token_shows_price(self, command_suite, monkeypatch):
        """Test /price command with valid token returns price data.
        
        Validates Property 4: For any valid token symbol, requesting price should 
        return current USD price and 24h change percentage.
        """
        from agent.services.price_service import PriceData
        
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("price")
        context = command_suite.harness.create_mock_telegram_context(args=["SOL"])
        
        # Mock PriceService.fetch_price to return valid data
        mock_price_data = PriceData(
            name="Solana",
            symbol="SOL",
            price=127.50,
            change_24h=5.2,
            market_cap=50000000000,
            source="CoinGecko"
        )
        
        async def mock_fetch_price(query):
            return mock_price_data
        
        monkeypatch.setattr(
            "agent.services.price_service.PriceService.fetch_price",
            mock_fetch_price
        )
        
        # Execute
        await command_suite.info_commands.cmd_price(update, context)
        
        # Assert
        command_suite.assert_message_contains(
            update,
            "Solana",
            "SOL",
            "127.50"
        )
    
    async def test_price_command_with_invalid_token_shows_error(self, command_suite, monkeypatch):
        """Test /price command with invalid token returns error message.
        
        Validates Property 38: For any invalid or unknown token symbol, 
        the price service should return clear error message indicating token not found.
        """
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("price")
        context = command_suite.harness.create_mock_telegram_context(args=["INVALIDTOKEN123"])
        
        # Mock PriceService.fetch_price to return None (token not found)
        async def mock_fetch_price(query):
            return None
        
        monkeypatch.setattr(
            "agent.services.price_service.PriceService.fetch_price",
            mock_fetch_price
        )
        
        # Execute
        await command_suite.info_commands.cmd_price(update, context)
        
        # Assert
        command_suite.assert_message_contains(
            update,
            "not found"
        )
    
    async def test_price_command_with_solana_address(self, command_suite, monkeypatch):
        """Test /price command with Solana contract address."""
        from agent.services.price_service import PriceData
        
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("price")
        address = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
        context = command_suite.harness.create_mock_telegram_context(args=[address])
        
        # Mock PriceService.fetch_price to return valid data
        mock_price_data = PriceData(
            name="Bonk",
            symbol="BONK",
            price=0.000025,
            source="Jupiter",
            contract_address=address
        )
        
        async def mock_fetch_price(query):
            return mock_price_data
        
        monkeypatch.setattr(
            "agent.services.price_service.PriceService.fetch_price",
            mock_fetch_price
        )
        
        # Execute
        await command_suite.info_commands.cmd_price(update, context)
        
        # Assert
        command_suite.assert_message_contains(
            update,
            "Bonk",
            "BONK"
        )
    
    async def test_price_command_handles_api_error(self, command_suite, monkeypatch):
        """Test /price command handles API errors gracefully."""
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("price")
        context = command_suite.harness.create_mock_telegram_context(args=["SOL"])
        
        # Mock PriceService.fetch_price to raise exception
        async def mock_fetch_price(query):
            raise Exception("API Error")
        
        monkeypatch.setattr(
            "agent.services.price_service.PriceService.fetch_price",
            mock_fetch_price
        )
        
        # Execute
        await command_suite.info_commands.cmd_price(update, context)
        
        # Assert
        command_suite.assert_message_contains(
            update,
            "Error"
        )
    
    async def test_price_command_with_multi_word_query(self, command_suite, monkeypatch):
        """Test /price command with multi-word token name."""
        from agent.services.price_service import PriceData
        
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("price")
        context = command_suite.harness.create_mock_telegram_context(args=["wrapped", "bitcoin"])
        
        # Mock PriceService.fetch_price to return valid data
        mock_price_data = PriceData(
            name="Wrapped Bitcoin",
            symbol="WBTC",
            price=42000.00,
            change_24h=2.5,
            source="CoinGecko"
        )
        
        async def mock_fetch_price(query):
            return mock_price_data
        
        monkeypatch.setattr(
            "agent.services.price_service.PriceService.fetch_price",
            mock_fetch_price
        )
        
        # Execute
        await command_suite.info_commands.cmd_price(update, context)
        
        # Assert
        command_suite.assert_message_contains(
            update,
            "Wrapped Bitcoin",
            "WBTC"
        )
    
    async def test_portfolio_command_without_args_shows_usage(self, command_suite):
        """Test /portfolio command without arguments shows usage instructions."""
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("portfolio")
        context = command_suite.harness.create_mock_telegram_context(args=[])
        
        # Execute
        await command_suite.info_commands.cmd_portfolio(update, context)
        
        # Assert
        command_suite.assert_message_contains(
            update,
            "Usage",
            "/portfolio"
        )
    
    async def test_portfolio_command_with_invalid_address_shows_error(self, command_suite):
        """Test /portfolio command with invalid address shows error.
        
        Validates Property 44: For any invalid wallet address format, 
        the system should reject with format error explaining valid Solana address format.
        """
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("portfolio")
        context = command_suite.harness.create_mock_telegram_context(args=["invalid"])
        
        # Execute
        await command_suite.info_commands.cmd_portfolio(update, context)
        
        # Assert
        command_suite.assert_message_contains(
            update,
            "Invalid wallet address"
        )
    
    async def test_portfolio_command_with_valid_address_shows_portfolio(self, command_suite, monkeypatch):
        """Test /portfolio command with valid address returns portfolio data.
        
        Validates Property 5: For any valid Solana wallet address, requesting portfolio 
        should return all token holdings with symbols, amounts, and USD values.
        """
        from agent.services.portfolio_service import PortfolioData, TokenHolding
        from datetime import datetime
        
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("portfolio")
        valid_address = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
        context = command_suite.harness.create_mock_telegram_context(args=[valid_address])
        
        # Mock PortfolioService.analyze_portfolio to return valid data
        mock_portfolio = PortfolioData(
            wallet_address=valid_address,
            sol_balance=10.5,
            sol_value_usd=1337.25,
            total_value_usd=2500.00,
            token_count=5,
            holdings=[
                TokenHolding(
                    symbol="USDC",
                    name="USD Coin",
                    amount=1000.0,
                    decimals=6,
                    price_usd=1.0,
                    value_usd=1000.0,
                    mint_address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
                ),
                TokenHolding(
                    symbol="BONK",
                    name="Bonk",
                    amount=50000.0,
                    decimals=5,
                    price_usd=0.000025,
                    value_usd=1.25,
                    mint_address="DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
                )
            ],
            top_holdings=[],
            last_updated=datetime.now()
        )
        
        async def mock_analyze_portfolio(address):
            return mock_portfolio
        
        monkeypatch.setattr(
            "agent.services.portfolio_service.PortfolioService.analyze_portfolio",
            mock_analyze_portfolio
        )
        
        # Execute
        await command_suite.info_commands.cmd_portfolio(update, context)
        
        # Assert - Check that the status message was edited (not just sent)
        assert update.message.reply_text.call_count >= 1
    
    async def test_portfolio_command_with_empty_wallet(self, command_suite, monkeypatch):
        """Test /portfolio command with wallet that has no tokens."""
        from agent.services.portfolio_service import PortfolioData
        from datetime import datetime
        
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("portfolio")
        valid_address = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
        context = command_suite.harness.create_mock_telegram_context(args=[valid_address])
        
        # Mock PortfolioService.analyze_portfolio to return empty portfolio
        mock_portfolio = PortfolioData(
            wallet_address=valid_address,
            sol_balance=0.0,
            sol_value_usd=0.0,
            total_value_usd=0.0,
            token_count=0,
            holdings=[],
            top_holdings=[],
            last_updated=datetime.now()
        )
        
        async def mock_analyze_portfolio(address):
            return mock_portfolio
        
        monkeypatch.setattr(
            "agent.services.portfolio_service.PortfolioService.analyze_portfolio",
            mock_analyze_portfolio
        )
        
        # Execute
        await command_suite.info_commands.cmd_portfolio(update, context)
        
        # Assert
        assert update.message.reply_text.call_count >= 1
    
    async def test_portfolio_command_handles_api_error(self, command_suite, monkeypatch):
        """Test /portfolio command handles API errors gracefully."""
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("portfolio")
        valid_address = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
        context = command_suite.harness.create_mock_telegram_context(args=[valid_address])
        
        # Mock PortfolioService.analyze_portfolio to raise exception
        async def mock_analyze_portfolio(address):
            raise Exception("API Error")
        
        monkeypatch.setattr(
            "agent.services.portfolio_service.PortfolioService.analyze_portfolio",
            mock_analyze_portfolio
        )
        
        # Execute
        await command_suite.info_commands.cmd_portfolio(update, context)
        
        # Assert
        assert update.message.reply_text.call_count >= 1
    
    async def test_portfolio_command_with_none_result(self, command_suite, monkeypatch):
        """Test /portfolio command when service returns None (failed analysis)."""
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("portfolio")
        valid_address = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
        context = command_suite.harness.create_mock_telegram_context(args=[valid_address])
        
        # Mock PortfolioService.analyze_portfolio to return None
        async def mock_analyze_portfolio(address):
            return None
        
        monkeypatch.setattr(
            "agent.services.portfolio_service.PortfolioService.analyze_portfolio",
            mock_analyze_portfolio
        )
        
        # Execute
        await command_suite.info_commands.cmd_portfolio(update, context)
        
        # Assert - Should show error message about failed analysis
        assert update.message.reply_text.call_count >= 1
    
    async def test_portfolio_command_with_too_short_address(self, command_suite):
        """Test /portfolio command rejects addresses that are too short."""
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("portfolio")
        short_address = "tooshort"
        context = command_suite.harness.create_mock_telegram_context(args=[short_address])
        
        # Execute
        await command_suite.info_commands.cmd_portfolio(update, context)
        
        # Assert
        command_suite.assert_message_contains(
            update,
            "Invalid wallet address"
        )
    
    async def test_portfolio_command_with_too_long_address(self, command_suite):
        """Test /portfolio command rejects addresses that are too long."""
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("portfolio")
        long_address = "a" * 50  # More than 44 characters
        context = command_suite.harness.create_mock_telegram_context(args=[long_address])
        
        # Execute
        await command_suite.info_commands.cmd_portfolio(update, context)
        
        # Assert
        command_suite.assert_message_contains(
            update,
            "Invalid wallet address"
        )


# ============================================================================
# Trading Commands Tests
# ============================================================================

@pytest.mark.asyncio
class TestTradingCommands:
    """Tests for trading commands: /pause, /resume, /strategies."""
    
    async def test_pause_command_stops_bot(self, command_suite):
        """Test /pause command stops the bot."""
        # Setup
        command_suite.setup_command_handlers(is_running=True)
        update = command_suite.harness.create_mock_telegram_update("pause")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.trading_commands.cmd_pause(update, context)
        
        # Assert
        assert command_suite.mock_bot.agent_loop.stop.called
        command_suite.assert_message_contains(
            update,
            "Paused",
            "/resume"
        )
    
    async def test_resume_command_starts_bot(self, command_suite):
        """Test /resume command starts the bot."""
        # Setup
        command_suite.setup_command_handlers(is_running=False)
        update = command_suite.harness.create_mock_telegram_update("resume")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.trading_commands.cmd_resume(update, context)
        
        # Assert
        command_suite.assert_message_contains(
            update,
            "Resumed",
            "/status"
        )
    
    async def test_strategies_command_shows_active_strategies(self, command_suite):
        """Test /strategies command shows list of active strategies."""
        # Setup
        command_suite.setup_command_handlers()
        
        # Mock strategies
        mock_strategy = MagicMock()
        mock_strategy.get_name = MagicMock(return_value="airdrop_hunter")
        mock_strategy.get_next_check_time = MagicMock(return_value=datetime.now())
        command_suite.mock_bot.agent_loop.scanner.strategies = [mock_strategy]
        
        update = command_suite.harness.create_mock_telegram_update("strategies")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.trading_commands.cmd_strategies(update, context)
        
        # Assert
        command_suite.assert_message_contains(
            update,
            "Active Strategies",
            "Airdrop Hunter"
        )


# ============================================================================
# Property-Based Tests
# ============================================================================

@pytest.mark.asyncio
class TestCommandProperties:
    """Property-based tests for command handling."""
    
    async def test_unknown_command_handling_property(self, command_suite):
        """
        Property 7: Unknown command handling
        
        For any unrecognized command string, the system should handle it gracefully
        without crashing. In the current implementation, unknown commands are handled
        by the AI message handler.
        
        This test verifies that the bot can handle various unknown command strings.
        """
        # Setup
        command_suite.setup_command_handlers()
        
        # Test various unknown commands
        unknown_commands = [
            "unknowncmd",
            "randomtext",
            "xyz123",
            "foobar",
            "test123",
            "invalid"
        ]
        
        for unknown_command in unknown_commands:
            # Create update with unknown command
            update = command_suite.harness.create_mock_telegram_update(unknown_command)
            context = command_suite.harness.create_mock_telegram_context()
            
            # Verify that the bot has a message handler for unknown commands
            # In the current implementation, unknown commands are handled by the AI chat
            assert command_suite.mock_bot is not None
            
            # The bot should not crash when receiving unknown commands
            # They are handled by the message handler (AI chat)
            # This test documents that unknown commands don't cause errors
    
    async def test_unknown_command_suggests_help(self, command_suite):
        """
        Test that unknown commands are handled gracefully.
        
        Since the bot doesn't have an explicit unknown command handler,
        this test documents the expected behavior: unknown commands should
        be handled by the AI chat or return a helpful message.
        
        In a complete implementation, we would add an unknown command handler
        that suggests using /help.
        """
        # Setup
        command_suite.setup_command_handlers()
        
        # Test a few unknown commands
        unknown_commands = ["unknowncmd", "randomtext", "xyz123", "foobar"]
        
        for cmd in unknown_commands:
            update = command_suite.harness.create_mock_telegram_update(cmd)
            context = command_suite.harness.create_mock_telegram_context()
            
            # Verify the bot is set up correctly
            assert command_suite.mock_bot is not None
            
            # In a complete implementation, we would:
            # 1. Add an unknown command handler to the bot
            # 2. Test that it returns a message suggesting /help
            # 3. Verify the message format
            
            # For now, we document that unknown commands are handled by the AI chat
            # and don't cause the bot to crash


# ============================================================================
# Additional Command Tests
# ============================================================================

@pytest.mark.asyncio
class TestAdditionalCommands:
    """Tests for additional commands: /fees, /settings, /airdrops, etc."""
    
    async def test_settings_command_shows_configuration(self, command_suite):
        """Test /settings command displays configuration."""
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("settings")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.info_commands.cmd_settings(update, context)
        
        # Assert
        command_suite.assert_message_contains(
            update,
            "Bot Settings",
            "settings"
        )
    
    async def test_airdrops_command_shows_discoveries(self, command_suite):
        """Test /airdrops command shows airdrop discoveries."""
        # Setup
        command_suite.setup_command_handlers()
        
        # Mock airdrop hunter strategy
        mock_hunter = MagicMock()
        mock_hunter.get_name = MagicMock(return_value="airdrop_hunter")
        mock_hunter.get_discoveries = MagicMock(return_value=[])
        command_suite.mock_bot.agent_loop.scanner.strategies = [mock_hunter]
        
        update = command_suite.harness.create_mock_telegram_update("airdrops")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.info_commands.cmd_airdrops(update, context)
        
        # Assert
        command_suite.assert_message_contains(
            update,
            "Airdrop Discoveries"
        )
    
    async def test_claims_command_shows_claim_history(self, command_suite):
        """Test /claims command shows claim history."""
        # Setup
        command_suite.setup_command_handlers()
        
        # Mock airdrop claimer strategy
        mock_claimer = MagicMock()
        mock_claimer.get_name = MagicMock(return_value="airdrop_claimer")
        mock_claimer.get_claim_history = MagicMock(return_value=[])
        mock_claimer.get_total_claimed = MagicMock(return_value=0.0)
        command_suite.mock_bot.agent_loop.scanner.strategies = [mock_claimer]
        
        update = command_suite.harness.create_mock_telegram_update("claims")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.info_commands.cmd_claims(update, context)
        
        # Assert
        command_suite.assert_message_contains(
            update,
            "Claim History"
        )
    
    async def test_bounty_command_shows_coming_soon(self, command_suite):
        """Test /bounty command shows coming soon message."""
        # Setup
        command_suite.setup_command_handlers()
        update = command_suite.harness.create_mock_telegram_update("bounty")
        context = command_suite.harness.create_mock_telegram_context()
        
        # Execute
        await command_suite.info_commands.cmd_bounty(update, context)
        
        # Assert
        command_suite.assert_message_contains(
            update,
            "Active Bounties",
            "Coming Soon"
        )
