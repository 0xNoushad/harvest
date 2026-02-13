"""
Integration test for complete withdrawal flow.

**Validates: Requirements 1.4, 1.5**

This integration test validates the complete end-to-end withdrawal flow including:
- Command parsing and validation
- Rate limiting checks
- Balance verification
- Transaction execution
- Balance updates
- User notifications
- Error handling

The test covers both successful withdrawals and various error scenarios to ensure
the complete flow works correctly from user input to final confirmation.
"""

# Import mocking setup FIRST
from tests.conftest_commands import mock_external_modules
mock_external_modules()

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from tests.test_harness import TestHarness


@pytest.mark.asyncio
class TestWithdrawIntegration:
    """
    Integration tests for complete /withdraw command flow.
    
    These tests verify the entire withdrawal workflow from command input
    through validation, execution, and user notification.
    """
    
    async def test_complete_withdrawal_flow_success(self):
        """
        Test the complete successful withdrawal flow.
        
        This test validates:
        1. Command is received with valid parameters
        2. Rate limiting allows the request
        3. Input validation passes
        4. Balance check passes
        5. Transaction is executed
        6. Balance is updated
        7. User receives processing message
        8. User receives success confirmation with transaction details
        9. Transaction signature is included
        10. Solscan link is provided
        
        **Validates: Requirement 1.4**
        """
        # Setup test harness
        harness = TestHarness()
        
        # Test parameters
        user_id = 12345
        to_address = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
        amount = 0.5
        initial_balance = 2.0
        expected_new_balance = initial_balance - amount
        expected_signature = "5xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU123456789"
        
        # Mock rate limiter to allow request
        with patch('agent.ui.commands.financial_commands.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = MagicMock(return_value=True)
            
            # Setup mock bot with wallet
            mock_bot = MagicMock()
            mock_bot.wallet = harness.create_mock_wallet(balance=initial_balance)
            
            # Mock wallet methods for the complete flow
            mock_bot.wallet.get_balance = AsyncMock(
                side_effect=[initial_balance, expected_new_balance]
            )
            mock_bot.wallet.send_sol = AsyncMock(return_value=expected_signature)
            
            # Import and create command handler
            from agent.ui.commands.financial_commands import FinancialCommands
            financial_commands = FinancialCommands(mock_bot)
            
            # Create mock Telegram update and context
            update = harness.create_mock_telegram_update(
                "withdraw",
                user_id=user_id,
                args=[to_address, str(amount)]
            )
            context = harness.create_mock_telegram_context(
                args=[to_address, str(amount)]
            )
            
            # Execute the command
            await financial_commands.cmd_withdraw(update, context)
            
            # Verify rate limiter was checked
            mock_rate_limiter.check_rate_limit.assert_called_once()
            
            # Verify balance was checked (at least twice: before and after)
            assert mock_bot.wallet.get_balance.call_count >= 2
            
            # Verify transaction was executed with correct parameters
            mock_bot.wallet.send_sol.assert_called_once()
            call_args = mock_bot.wallet.send_sol.call_args
            assert call_args[0][0] == to_address
            assert abs(call_args[0][1] - amount) < 0.0001
            
            # Verify user received messages
            assert update.message.reply_text.call_count >= 2
            
            # Verify processing message was sent
            first_call = update.message.reply_text.call_args_list[0]
            first_message = first_call[0][0] if first_call[0] else first_call[1].get('text', '')
            assert "⏳" in first_message or "Sending" in first_message
            assert str(amount) in first_message
            assert to_address in first_message
            
            # Verify success message was sent
            last_call = update.message.reply_text.call_args_list[-1]
            last_message = last_call[0][0] if last_call[0] else last_call[1].get('text', '')
            assert "✅" in last_message or "Successful" in last_message
            assert str(amount) in last_message
            assert to_address in last_message
            assert expected_signature in last_message
            assert "solscan.io" in last_message.lower()
            assert f"{expected_new_balance:.4f}" in last_message
    
    async def test_withdrawal_flow_insufficient_balance(self):
        """
        Test withdrawal flow with insufficient balance.
        
        This test validates:
        1. Command is received with valid parameters
        2. Rate limiting allows the request
        3. Input validation passes
        4. Balance check fails (insufficient funds)
        5. Transaction is NOT executed
        6. User receives error message with current balance
        7. Balance is NOT modified
        
        **Validates: Requirement 1.5**
        """
        harness = TestHarness()
        
        # Test parameters - amount exceeds balance
        user_id = 12345
        to_address = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
        amount = 5.0
        current_balance = 1.0  # Less than amount
        
        with patch('agent.ui.commands.financial_commands.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = MagicMock(return_value=True)
            
            # Setup mock bot
            mock_bot = MagicMock()
            mock_bot.wallet = harness.create_mock_wallet(balance=current_balance)
            mock_bot.wallet.get_balance = AsyncMock(return_value=current_balance)
            mock_bot.wallet.send_sol = AsyncMock()
            
            from agent.ui.commands.financial_commands import FinancialCommands
            financial_commands = FinancialCommands(mock_bot)
            
            update = harness.create_mock_telegram_update(
                "withdraw",
                user_id=user_id,
                args=[to_address, str(amount)]
            )
            context = harness.create_mock_telegram_context(
                args=[to_address, str(amount)]
            )
            
            # Execute
            await financial_commands.cmd_withdraw(update, context)
            
            # Verify transaction was NOT executed
            mock_bot.wallet.send_sol.assert_not_called()
            
            # Verify error message was sent
            assert update.message.reply_text.called
            error_call = update.message.reply_text.call_args
            error_message = error_call[0][0] if error_call[0] else error_call[1].get('text', '')
            
            # Verify error message content
            assert "❌" in error_message
            assert "Insufficient" in error_message or "balance" in error_message.lower()
            assert f"{current_balance:.4f}" in error_message
    
    async def test_withdrawal_flow_invalid_address(self):
        """
        Test withdrawal flow with invalid address.
        
        This test validates:
        1. Command is received with invalid address
        2. Rate limiting allows the request
        3. Input validation fails (invalid address format)
        4. Transaction is NOT executed
        5. User receives error message explaining the issue
        6. Balance is NOT checked or modified
        
        **Validates: Requirement 1.5**
        """
        harness = TestHarness()
        
        # Test parameters - invalid address
        user_id = 12345
        invalid_address = "invalid_address_123"
        amount = 0.5
        current_balance = 2.0
        
        with patch('agent.ui.commands.financial_commands.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = MagicMock(return_value=True)
            
            # Setup mock bot
            mock_bot = MagicMock()
            mock_bot.wallet = harness.create_mock_wallet(balance=current_balance)
            mock_bot.wallet.get_balance = AsyncMock(return_value=current_balance)
            mock_bot.wallet.send_sol = AsyncMock()
            
            from agent.ui.commands.financial_commands import FinancialCommands
            financial_commands = FinancialCommands(mock_bot)
            
            update = harness.create_mock_telegram_update(
                "withdraw",
                user_id=user_id,
                args=[invalid_address, str(amount)]
            )
            context = harness.create_mock_telegram_context(
                args=[invalid_address, str(amount)]
            )
            
            # Execute
            await financial_commands.cmd_withdraw(update, context)
            
            # Verify transaction was NOT executed
            mock_bot.wallet.send_sol.assert_not_called()
            
            # Verify error message was sent
            assert update.message.reply_text.called
            error_call = update.message.reply_text.call_args
            error_message = error_call[0][0] if error_call[0] else error_call[1].get('text', '')
            
            # Verify error message content
            assert "❌" in error_message
            assert "Invalid" in error_message or "address" in error_message.lower()
    
    async def test_withdrawal_flow_negative_amount(self):
        """
        Test withdrawal flow with negative amount.
        
        This test validates:
        1. Command is received with negative amount
        2. Rate limiting allows the request
        3. Amount validation fails
        4. Transaction is NOT executed
        5. User receives error message
        
        **Validates: Requirement 1.5**
        """
        harness = TestHarness()
        
        # Test parameters - negative amount
        user_id = 12345
        to_address = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
        amount = -0.5
        current_balance = 2.0
        
        with patch('agent.ui.commands.financial_commands.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = MagicMock(return_value=True)
            
            # Setup mock bot
            mock_bot = MagicMock()
            mock_bot.wallet = harness.create_mock_wallet(balance=current_balance)
            mock_bot.wallet.get_balance = AsyncMock(return_value=current_balance)
            mock_bot.wallet.send_sol = AsyncMock()
            
            from agent.ui.commands.financial_commands import FinancialCommands
            financial_commands = FinancialCommands(mock_bot)
            
            update = harness.create_mock_telegram_update(
                "withdraw",
                user_id=user_id,
                args=[to_address, str(amount)]
            )
            context = harness.create_mock_telegram_context(
                args=[to_address, str(amount)]
            )
            
            # Execute
            await financial_commands.cmd_withdraw(update, context)
            
            # Verify transaction was NOT executed
            mock_bot.wallet.send_sol.assert_not_called()
            
            # Verify error message was sent
            assert update.message.reply_text.called
            error_call = update.message.reply_text.call_args
            error_message = error_call[0][0] if error_call[0] else error_call[1].get('text', '')
            
            # Verify error message content
            assert "❌" in error_message
    
    async def test_withdrawal_flow_insufficient_balance_for_fees(self):
        """
        Test withdrawal flow that would leave insufficient balance for fees.
        
        This test validates:
        1. Command is received with amount that leaves < 0.01 SOL
        2. Rate limiting allows the request
        3. Input validation passes
        4. Fee reserve check fails
        5. Transaction is NOT executed
        6. User receives error message about fee requirement
        
        **Validates: Requirement 1.5**
        """
        harness = TestHarness()
        
        # Test parameters - amount leaves insufficient balance for fees
        user_id = 12345
        to_address = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
        current_balance = 0.5
        amount = 0.495  # Leaves only 0.005 SOL (less than 0.01 minimum)
        
        with patch('agent.ui.commands.financial_commands.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = MagicMock(return_value=True)
            
            # Setup mock bot
            mock_bot = MagicMock()
            mock_bot.wallet = harness.create_mock_wallet(balance=current_balance)
            mock_bot.wallet.get_balance = AsyncMock(return_value=current_balance)
            mock_bot.wallet.send_sol = AsyncMock()
            
            from agent.ui.commands.financial_commands import FinancialCommands
            financial_commands = FinancialCommands(mock_bot)
            
            update = harness.create_mock_telegram_update(
                "withdraw",
                user_id=user_id,
                args=[to_address, str(amount)]
            )
            context = harness.create_mock_telegram_context(
                args=[to_address, str(amount)]
            )
            
            # Execute
            await financial_commands.cmd_withdraw(update, context)
            
            # Verify transaction was NOT executed
            mock_bot.wallet.send_sol.assert_not_called()
            
            # Verify error message was sent
            assert update.message.reply_text.called
            error_call = update.message.reply_text.call_args
            error_message = error_call[0][0] if error_call[0] else error_call[1].get('text', '')
            
            # Verify error message content
            assert "❌" in error_message
            assert "0.01" in error_message or "fee" in error_message.lower()
    
    async def test_withdrawal_flow_rate_limit_exceeded(self):
        """
        Test withdrawal flow when rate limit is exceeded.
        
        This test validates:
        1. Command is received
        2. Rate limiting blocks the request
        3. User receives rate limit error message
        4. No further processing occurs
        5. Transaction is NOT executed
        
        **Validates: Requirement 5.1, 5.2 (Rate limiting)**
        """
        harness = TestHarness()
        
        # Test parameters
        user_id = 12345
        to_address = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
        amount = 0.5
        current_balance = 2.0
        
        # Mock rate limiter to block request
        with patch('agent.ui.commands.financial_commands.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = MagicMock(return_value=False)
            
            # Setup mock bot
            mock_bot = MagicMock()
            mock_bot.wallet = harness.create_mock_wallet(balance=current_balance)
            mock_bot.wallet.get_balance = AsyncMock(return_value=current_balance)
            mock_bot.wallet.send_sol = AsyncMock()
            
            from agent.ui.commands.financial_commands import FinancialCommands
            financial_commands = FinancialCommands(mock_bot)
            
            update = harness.create_mock_telegram_update(
                "withdraw",
                user_id=user_id,
                args=[to_address, str(amount)]
            )
            context = harness.create_mock_telegram_context(
                args=[to_address, str(amount)]
            )
            
            # Execute
            await financial_commands.cmd_withdraw(update, context)
            
            # Verify rate limiter was checked
            mock_rate_limiter.check_rate_limit.assert_called_once()
            
            # Verify transaction was NOT executed
            mock_bot.wallet.send_sol.assert_not_called()
            
            # Verify balance was NOT checked
            mock_bot.wallet.get_balance.assert_not_called()
            
            # Verify rate limit error message was sent
            assert update.message.reply_text.called
            error_call = update.message.reply_text.call_args
            error_message = error_call[0][0] if error_call[0] else error_call[1].get('text', '')
            
            # Verify error message content
            assert "⏱️" in error_message or "Too many" in error_message
            assert "wait" in error_message.lower()
    
    async def test_withdrawal_flow_missing_parameters(self):
        """
        Test withdrawal flow with missing parameters.
        
        This test validates:
        1. Command is received without required parameters
        2. Rate limiting allows the request
        3. Parameter validation fails
        4. User receives usage instructions
        5. Current balance is shown
        6. Transaction is NOT executed
        
        **Validates: Requirement 1.5**
        """
        harness = TestHarness()
        
        # Test parameters - missing arguments
        user_id = 12345
        current_balance = 2.0
        
        with patch('agent.ui.commands.financial_commands.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = MagicMock(return_value=True)
            
            # Setup mock bot
            mock_bot = MagicMock()
            mock_bot.wallet = harness.create_mock_wallet(balance=current_balance)
            mock_bot.wallet.get_balance = AsyncMock(return_value=current_balance)
            mock_bot.wallet.send_sol = AsyncMock()
            
            from agent.ui.commands.financial_commands import FinancialCommands
            financial_commands = FinancialCommands(mock_bot)
            
            # Test with no arguments
            update = harness.create_mock_telegram_update(
                "withdraw",
                user_id=user_id,
                args=[]
            )
            context = harness.create_mock_telegram_context(args=[])
            
            # Execute
            await financial_commands.cmd_withdraw(update, context)
            
            # Verify transaction was NOT executed
            mock_bot.wallet.send_sol.assert_not_called()
            
            # Verify usage message was sent
            assert update.message.reply_text.called
            usage_call = update.message.reply_text.call_args
            usage_message = usage_call[0][0] if usage_call[0] else usage_call[1].get('text', '')
            
            # Verify usage message content
            assert "Usage" in usage_message or "withdraw" in usage_message.lower()
            assert "<address>" in usage_message or "address" in usage_message.lower()
            assert "<amount>" in usage_message or "amount" in usage_message.lower()
            assert f"{current_balance:.4f}" in usage_message
    
    async def test_withdrawal_flow_transaction_failure(self):
        """
        Test withdrawal flow when transaction execution fails.
        
        This test validates:
        1. Command is received with valid parameters
        2. Rate limiting allows the request
        3. Input validation passes
        4. Balance check passes
        5. Transaction execution fails (returns None)
        6. User receives failure message
        7. Balance is checked but not modified
        
        **Validates: Requirement 1.5 (Error handling)**
        """
        harness = TestHarness()
        
        # Test parameters
        user_id = 12345
        to_address = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
        amount = 0.5
        current_balance = 2.0
        
        with patch('agent.ui.commands.financial_commands.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = MagicMock(return_value=True)
            
            # Setup mock bot with transaction failure
            mock_bot = MagicMock()
            mock_bot.wallet = harness.create_mock_wallet(balance=current_balance)
            mock_bot.wallet.get_balance = AsyncMock(return_value=current_balance)
            mock_bot.wallet.send_sol = AsyncMock(return_value=None)  # Transaction fails
            
            from agent.ui.commands.financial_commands import FinancialCommands
            financial_commands = FinancialCommands(mock_bot)
            
            update = harness.create_mock_telegram_update(
                "withdraw",
                user_id=user_id,
                args=[to_address, str(amount)]
            )
            context = harness.create_mock_telegram_context(
                args=[to_address, str(amount)]
            )
            
            # Execute
            await financial_commands.cmd_withdraw(update, context)
            
            # Verify transaction was attempted
            mock_bot.wallet.send_sol.assert_called_once()
            
            # Verify user received messages
            assert update.message.reply_text.call_count >= 2
            
            # Verify failure message was sent
            last_call = update.message.reply_text.call_args_list[-1]
            last_message = last_call[0][0] if last_call[0] else last_call[1].get('text', '')
            
            # Verify failure message content
            assert "❌" in last_message
            assert "failed" in last_message.lower() or "try again" in last_message.lower()
