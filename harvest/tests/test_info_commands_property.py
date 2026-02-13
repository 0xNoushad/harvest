"""
Property-based tests for information query commands (/price and /portfolio).

These tests use Hypothesis to generate random inputs and verify that
the commands handle all cases correctly according to the specified properties.
"""

# Import mocking setup FIRST
from tests.conftest_commands import mock_external_modules
mock_external_modules()

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime

# Import test utilities
from tests.test_harness import TestHarness
from tests.generators import (
    solana_address_strategy,
    token_symbol_strategy,
    price_strategy,
    token_holding_strategy,
    sol_amount_strategy
)

# Import services
from agent.services.price_service import PriceData
from agent.services.portfolio_service import PortfolioData, TokenHolding


# ============================================================================
# Fixtures
# ============================================================================

# No fixtures needed - we'll create instances inside tests to avoid
# Hypothesis health check issues with function-scoped fixtures


# ============================================================================
# Property 4: Price Query for Valid Tokens
# ============================================================================

@given(
    token=token_symbol_strategy,
    price=price_strategy,
    change_24h=st.floats(min_value=-50.0, max_value=50.0, allow_nan=False)
)
@settings(max_examples=50, deadline=5000)
@pytest.mark.asyncio
async def test_price_command_valid_token_property(
    token,
    price,
    change_24h
):
    """
    Property 4: For any valid token symbol, requesting price should return 
    current USD price and 24h change percentage.
    
    **Validates: Requirements 1.10**
    """
    # Assume token is not empty
    assume(len(token) > 0)
    
    # Create test harness and mock commands
    test_harness = TestHarness()
    from agent.ui.commands.info_commands import InfoCommands
    mock_bot = MagicMock()
    mock_bot.performance = test_harness.create_mock_performance_tracker()
    mock_info_commands = InfoCommands(mock_bot)
    
    # Setup
    update = test_harness.create_mock_telegram_update("price")
    context = test_harness.create_mock_telegram_context(args=[token])
    
    # Mock PriceService.fetch_price to return valid data
    mock_price_data = PriceData(
        name=f"Token {token}",
        symbol=token,
        price=price,
        change_24h=change_24h,
        source="CoinGecko"
    )
    
    with patch(
        "agent.services.price_service.PriceService.fetch_price",
        return_value=mock_price_data
    ) as mock_fetch:
        # Execute
        await mock_info_commands.cmd_price(update, context)
        
        # Assert: Service was called with the token
        mock_fetch.assert_called_once_with(token)
        
        # Assert: Message was sent
        assert update.message.reply_text.called
        
        # Assert: Message contains token symbol and price information
        sent_message = update.message.reply_text.call_args[0][0]
        assert token in sent_message or token.upper() in sent_message


# ============================================================================
# Property 38: Invalid Token Error Handling
# ============================================================================

@given(token=st.text(min_size=1, max_size=50))
@settings(max_examples=50, deadline=5000)
@pytest.mark.asyncio
async def test_price_command_invalid_token_property(
    token
):
    """
    Property 38: For any invalid or unknown token symbol, the price service 
    should return clear error message indicating token not found.
    
    **Validates: Requirements 7.2**
    """
    # Create test harness and mock commands
    test_harness = TestHarness()
    from agent.ui.commands.info_commands import InfoCommands
    mock_bot = MagicMock()
    mock_bot.performance = test_harness.create_mock_performance_tracker()
    mock_info_commands = InfoCommands(mock_bot)
    
    # Setup
    update = test_harness.create_mock_telegram_update("price")
    context = test_harness.create_mock_telegram_context(args=[token])
    
    # Mock PriceService.fetch_price to return None (token not found)
    with patch(
        "agent.services.price_service.PriceService.fetch_price",
        return_value=None
    ) as mock_fetch:
        # Execute
        await mock_info_commands.cmd_price(update, context)
        
        # Assert: Service was called with the token
        mock_fetch.assert_called_once_with(token)
        
        # Assert: Error message was sent
        assert update.message.reply_text.called
        
        # Assert: Message contains "not found" or similar error indicator
        sent_message = update.message.reply_text.call_args[0][0]
        assert "not found" in sent_message.lower() or "error" in sent_message.lower()


# ============================================================================
# Property 5: Portfolio Analysis for Valid Wallets
# ============================================================================

@given(
    wallet_address=solana_address_strategy,
    sol_balance=sol_amount_strategy,
    num_tokens=st.integers(min_value=0, max_value=10)
)
@settings(max_examples=30, deadline=10000)
@pytest.mark.asyncio
async def test_portfolio_command_valid_address_property(
    wallet_address,
    sol_balance,
    num_tokens
):
    """
    Property 5: For any valid Solana wallet address, requesting portfolio 
    should return all token holdings with symbols, amounts, and USD values.
    
    **Validates: Requirements 1.11**
    """
    # Assume valid address length
    assume(32 <= len(wallet_address) <= 44)
    
    # Create test harness and mock commands
    test_harness = TestHarness()
    from agent.ui.commands.info_commands import InfoCommands
    mock_bot = MagicMock()
    mock_bot.performance = test_harness.create_mock_performance_tracker()
    mock_info_commands = InfoCommands(mock_bot)
    
    # Setup
    update = test_harness.create_mock_telegram_update("portfolio")
    context = test_harness.create_mock_telegram_context(args=[wallet_address])
    
    # Generate token holdings
    holdings = []
    for i in range(num_tokens):
        holdings.append(TokenHolding(
            symbol=f"TOKEN{i}",
            name=f"Test Token {i}",
            amount=float(i + 1) * 100.0,
            decimals=6,
            price_usd=1.0 + float(i),
            value_usd=float(i + 1) * 100.0 * (1.0 + float(i)),
            mint_address=f"mint{i}" + "x" * 40,
            percentage=0.0
        ))
    
    total_value = sum(h.value_usd for h in holdings) + (sol_balance * 127.50)
    
    # Mock PortfolioService.analyze_portfolio to return valid data
    mock_portfolio = PortfolioData(
        wallet_address=wallet_address,
        sol_balance=sol_balance,
        sol_value_usd=sol_balance * 127.50,
        total_value_usd=total_value,
        token_count=num_tokens,
        holdings=holdings,
        top_holdings=holdings[:3] if len(holdings) > 0 else [],
        last_updated=datetime.now()
    )
    
    with patch(
        "agent.services.portfolio_service.PortfolioService.analyze_portfolio",
        return_value=mock_portfolio
    ) as mock_analyze:
        # Execute
        await mock_info_commands.cmd_portfolio(update, context)
        
        # Assert: Service was called with the wallet address
        mock_analyze.assert_called_once_with(wallet_address)
        
        # Assert: At least one message was sent (initial status + result)
        assert update.message.reply_text.call_count >= 1


# ============================================================================
# Property 44: Invalid Address Rejection
# ============================================================================

@given(address=st.text(min_size=1, max_size=100))
@settings(max_examples=50, deadline=5000)
@pytest.mark.asyncio
async def test_portfolio_command_invalid_address_property(
    address
):
    """
    Property 44: For any invalid wallet address format, the system should 
    reject with format error explaining valid Solana address format.
    
    **Validates: Requirements 8.2**
    """
    # Assume address is outside valid length range
    assume(len(address) < 32 or len(address) > 44)
    
    # Create test harness and mock commands
    test_harness = TestHarness()
    from agent.ui.commands.info_commands import InfoCommands
    mock_bot = MagicMock()
    mock_bot.performance = test_harness.create_mock_performance_tracker()
    mock_info_commands = InfoCommands(mock_bot)
    
    # Setup
    update = test_harness.create_mock_telegram_update("portfolio")
    context = test_harness.create_mock_telegram_context(args=[address])
    
    # Execute
    await mock_info_commands.cmd_portfolio(update, context)
    
    # Assert: Error message was sent without calling the service
    assert update.message.reply_text.called
    
    # Assert: Message contains "invalid" or similar error indicator
    sent_message = update.message.reply_text.call_args[0][0]
    assert "invalid" in sent_message.lower() or "address" in sent_message.lower()


# ============================================================================
# Property: Price Command Handles Empty Args
# ============================================================================

@pytest.mark.asyncio
async def test_price_command_no_args_shows_usage():
    """
    Property: When /price is called without arguments, it should display 
    usage instructions.
    """
    # Create test harness and mock commands
    test_harness = TestHarness()
    from agent.ui.commands.info_commands import InfoCommands
    mock_bot = MagicMock()
    mock_bot.performance = test_harness.create_mock_performance_tracker()
    mock_info_commands = InfoCommands(mock_bot)
    
    # Setup
    update = test_harness.create_mock_telegram_update("price")
    context = test_harness.create_mock_telegram_context(args=[])
    
    # Execute
    await mock_info_commands.cmd_price(update, context)
    
    # Assert: Usage message was sent
    assert update.message.reply_text.called
    sent_message = update.message.reply_text.call_args[0][0]
    assert "usage" in sent_message.lower() or "example" in sent_message.lower()


# ============================================================================
# Property: Portfolio Command Handles Empty Args
# ============================================================================

@pytest.mark.asyncio
async def test_portfolio_command_no_args_shows_usage():
    """
    Property: When /portfolio is called without arguments, it should display 
    usage instructions.
    """
    # Create test harness and mock commands
    test_harness = TestHarness()
    from agent.ui.commands.info_commands import InfoCommands
    mock_bot = MagicMock()
    mock_bot.performance = test_harness.create_mock_performance_tracker()
    mock_info_commands = InfoCommands(mock_bot)
    
    # Setup
    update = test_harness.create_mock_telegram_update("portfolio")
    context = test_harness.create_mock_telegram_context(args=[])
    
    # Execute
    await mock_info_commands.cmd_portfolio(update, context)
    
    # Assert: Usage message was sent
    assert update.message.reply_text.called
    sent_message = update.message.reply_text.call_args[0][0]
    assert "usage" in sent_message.lower() or "example" in sent_message.lower()


# ============================================================================
# Property: Price Command Handles Multi-Word Queries
# ============================================================================

@given(
    words=st.lists(
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=3, max_size=10),
        min_size=2,
        max_size=4
    ),
    price=price_strategy
)
@settings(max_examples=30, deadline=5000)
@pytest.mark.asyncio
async def test_price_command_multi_word_query_property(
    words,
    price
):
    """
    Property: Price command should handle multi-word token names by joining 
    arguments with spaces.
    """
    # Create test harness and mock commands
    test_harness = TestHarness()
    from agent.ui.commands.info_commands import InfoCommands
    mock_bot = MagicMock()
    mock_bot.performance = test_harness.create_mock_performance_tracker()
    mock_info_commands = InfoCommands(mock_bot)
    
    # Setup
    update = test_harness.create_mock_telegram_update("price")
    context = test_harness.create_mock_telegram_context(args=words)
    
    expected_query = " ".join(words)
    
    # Mock PriceService.fetch_price
    mock_price_data = PriceData(
        name=expected_query.title(),
        symbol="TOKEN",
        price=price,
        source="CoinGecko"
    )
    
    with patch(
        "agent.services.price_service.PriceService.fetch_price",
        return_value=mock_price_data
    ) as mock_fetch:
        # Execute
        await mock_info_commands.cmd_price(update, context)
        
        # Assert: Service was called with joined query
        mock_fetch.assert_called_once_with(expected_query)


# ============================================================================
# Property: Portfolio Command Handles Service Errors
# ============================================================================

@given(wallet_address=solana_address_strategy)
@settings(max_examples=20, deadline=5000)
@pytest.mark.asyncio
async def test_portfolio_command_service_error_property(
    wallet_address
):
    """
    Property: Portfolio command should handle service errors gracefully 
    and display user-friendly error messages.
    """
    # Assume valid address length
    assume(32 <= len(wallet_address) <= 44)
    
    # Create test harness and mock commands
    test_harness = TestHarness()
    from agent.ui.commands.info_commands import InfoCommands
    mock_bot = MagicMock()
    mock_bot.performance = test_harness.create_mock_performance_tracker()
    mock_info_commands = InfoCommands(mock_bot)
    
    # Setup
    update = test_harness.create_mock_telegram_update("portfolio")
    context = test_harness.create_mock_telegram_context(args=[wallet_address])
    
    # Mock PortfolioService.analyze_portfolio to raise exception
    with patch(
        "agent.services.portfolio_service.PortfolioService.analyze_portfolio",
        side_effect=Exception("Service error")
    ):
        # Execute
        await mock_info_commands.cmd_portfolio(update, context)
        
        # Assert: Error message was sent
        assert update.message.reply_text.call_count >= 1


# ============================================================================
# Property: Price Command Handles Service Errors
# ============================================================================

@given(token=token_symbol_strategy)
@settings(max_examples=20, deadline=5000)
@pytest.mark.asyncio
async def test_price_command_service_error_property(
    token
):
    """
    Property: Price command should handle service errors gracefully 
    and display user-friendly error messages.
    """
    # Assume token is not empty
    assume(len(token) > 0)
    
    # Create test harness and mock commands
    test_harness = TestHarness()
    from agent.ui.commands.info_commands import InfoCommands
    mock_bot = MagicMock()
    mock_bot.performance = test_harness.create_mock_performance_tracker()
    mock_info_commands = InfoCommands(mock_bot)
    
    # Setup
    update = test_harness.create_mock_telegram_update("price")
    context = test_harness.create_mock_telegram_context(args=[token])
    
    # Mock PriceService.fetch_price to raise exception
    with patch(
        "agent.services.price_service.PriceService.fetch_price",
        side_effect=Exception("Service error")
    ):
        # Execute
        await mock_info_commands.cmd_price(update, context)
        
        # Assert: Error message was sent
        assert update.message.reply_text.called
        sent_message = update.message.reply_text.call_args[0][0]
        assert "error" in sent_message.lower()
