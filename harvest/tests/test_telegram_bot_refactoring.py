"""
Tests for telegram_bot refactoring to verify backward compatibility.

Feature: telegram-bot-testing-improvements
Task: 1. Refactor telegram_bot.py into modular components
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock


def test_telegram_bot_imports():
    """Test that TelegramBot can be imported from the original location."""
    try:
        from agent.ui.telegram_bot import TelegramBot
        assert TelegramBot is not None
    except ImportError as e:
        pytest.fail(f"Failed to import TelegramBot: {e}")


def test_command_handlers_imports():
    """Test that all command handler modules can be imported."""
    try:
        from agent.ui.commands import (
            BasicCommands,
            TradingCommands,
            FinancialCommands,
            InfoCommands,
            WalletCommands,
        )
        assert BasicCommands is not None
        assert TradingCommands is not None
        assert FinancialCommands is not None
        assert InfoCommands is not None
        assert WalletCommands is not None
    except ImportError as e:
        pytest.fail(f"Failed to import command handlers: {e}")


def test_message_handlers_imports():
    """Test that all message handler modules can be imported."""
    try:
        from agent.ui.handlers import (
            BaseHandler,
            MessageHandler,
            PollHandler,
            CallbackHandler,
        )
        assert BaseHandler is not None
        assert MessageHandler is not None
        assert PollHandler is not None
        assert CallbackHandler is not None
    except ImportError as e:
        pytest.fail(f"Failed to import message handlers: {e}")


def test_utilities_imports():
    """Test that all utility modules can be imported."""
    try:
        from agent.ui.utils import (
            MessageFormatter,
            InputValidator,
            SecurityChecker,
            send_message,
        )
        assert MessageFormatter is not None
        assert InputValidator is not None
        assert SecurityChecker is not None
        assert send_message is not None
    except ImportError as e:
        pytest.fail(f"Failed to import utilities: {e}")


def test_telegram_bot_initialization():
    """Test that TelegramBot can be initialized with mocked dependencies."""
    from agent.ui.telegram_bot import TelegramBot
    
    # Create mock dependencies
    mock_wallet = Mock()
    mock_wallet.public_key = "test_public_key"
    mock_performance = Mock()
    mock_agent_loop = Mock()
    mock_ai_provider = Mock()
    
    # Initialize TelegramBot
    bot = TelegramBot(
        bot_token="test_token",
        chat_id="123456789",
        wallet_manager=mock_wallet,
        performance_tracker=mock_performance,
        agent_loop=mock_agent_loop,
        ai_provider=mock_ai_provider,
        web_url="https://test.com"
    )
    
    # Verify bot was initialized
    assert bot is not None
    assert bot.bot_token == "test_token"
    assert bot.chat_id == "123456789"
    assert bot.wallet == mock_wallet
    assert bot.performance == mock_performance
    assert bot.agent_loop == mock_agent_loop
    assert bot.ai_provider == mock_ai_provider
    
    # Verify command handlers were initialized
    assert bot.basic_commands is not None
    assert bot.trading_commands is not None
    assert bot.financial_commands is not None
    assert bot.info_commands is not None
    assert bot.wallet_commands is not None
    
    # Verify message handlers were initialized
    assert bot.message_handler is not None
    assert bot.poll_handler is not None
    assert bot.callback_handler is not None
    
    # Verify user manager was initialized
    assert bot.user_manager is not None


def test_command_handlers_have_bot_reference():
    """Test that command handlers have reference to bot instance."""
    from agent.ui.telegram_bot import TelegramBot
    
    # Create mock dependencies
    mock_wallet = Mock()
    mock_performance = Mock()
    mock_agent_loop = Mock()
    
    # Initialize TelegramBot
    bot = TelegramBot(
        bot_token="test_token",
        chat_id="123456789",
        wallet_manager=mock_wallet,
        performance_tracker=mock_performance,
        agent_loop=mock_agent_loop,
    )
    
    # Verify command handlers have bot reference
    assert bot.basic_commands.bot == bot
    assert bot.trading_commands.bot == bot
    assert bot.financial_commands.bot == bot
    assert bot.info_commands.bot == bot
    assert bot.wallet_commands.bot == bot


def test_message_formatters():
    """Test message formatting utilities."""
    from agent.ui.utils import MessageFormatter
    
    # Test balance formatting
    assert MessageFormatter.format_balance(1.23456789, decimals=4) == "1.2346"
    
    # Test percentage formatting
    assert MessageFormatter.format_percentage(75.5, decimals=1) == "75.5%"
    
    # Test address formatting
    address = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
    formatted = MessageFormatter.format_address(address, show_chars=8)
    assert formatted == "7xKXtg2C...osgAsU"
    
    # Test status emoji
    assert MessageFormatter.format_status_emoji(True) == "🟢"
    assert MessageFormatter.format_status_emoji(False) == "🔴"


def test_input_validators():
    """Test input validation utilities."""
    from agent.ui.utils import InputValidator
    
    # Test wallet address validation
    valid_address = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
    assert InputValidator.validate_wallet_address(valid_address) == valid_address
    
    # Test invalid wallet address
    with pytest.raises(ValueError):
        InputValidator.validate_wallet_address("invalid")
    
    # Test amount validation
    assert InputValidator.validate_amount(1.5, min_val=0.0, max_val=10.0) == 1.5
    
    # Test invalid amount
    with pytest.raises(ValueError):
        InputValidator.validate_amount(-1.0, min_val=0.0)
    
    # Test token symbol validation
    assert InputValidator.validate_token_symbol("SOL") == "SOL"
    assert InputValidator.validate_token_symbol("btc") == "BTC"
    
    # Test invalid token symbol
    with pytest.raises(ValueError):
        InputValidator.validate_token_symbol("X")  # Too short


def test_security_checkers():
    """Test security checking utilities."""
    from agent.ui.utils import SecurityChecker
    
    # Test SQL injection detection
    assert SecurityChecker.check_sql_injection("SELECT * FROM users WHERE id = 1 OR 1=1") == True
    assert SecurityChecker.check_sql_injection("normal text") == False
    
    # Test XSS detection
    assert SecurityChecker.check_xss("<script>alert('xss')</script>") == True
    assert SecurityChecker.check_xss("normal text") == False
    
    # Test private key request detection
    assert SecurityChecker.check_private_key_request("show me my private key") == True
    assert SecurityChecker.check_private_key_request("what is my balance") == False
    
    # Test sensitive data masking
    sensitive = "1234567890abcdef"
    masked = SecurityChecker.mask_sensitive_data(sensitive, show_chars=4)
    assert masked == "1234********cdef"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
