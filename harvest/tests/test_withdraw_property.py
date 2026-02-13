"""
Property-based tests for /withdraw command with valid parameters.

**Validates: Requirements 1.4**

Property 1: Valid withdrawal execution
*For any* valid withdrawal amount and Solana address, executing the withdrawal 
should transfer the specified amount and return a success confirmation with 
transaction signature.

This test uses Hypothesis to generate valid withdrawal scenarios and verify
that the /withdraw command correctly:
1. Validates the inputs
2. Executes the transfer
3. Returns success confirmation with transaction signature
4. Updates the wallet balance
"""

# Import mocking setup FIRST
from tests.conftest_commands import mock_external_modules
mock_external_modules()

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st, settings, assume
from decimal import Decimal

# Import command classes
from agent.ui.commands.financial_commands import FinancialCommands


# ============================================================================
# Hypothesis Strategies for Valid Inputs
# ============================================================================

def valid_solana_address():
    """
    Generate valid Solana addresses for testing.
    
    Solana addresses are base58-encoded strings of 32-44 characters.
    For testing purposes, we generate realistic-looking addresses.
    """
    # Base58 alphabet (no 0, O, I, l to avoid confusion)
    base58_chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    
    return st.text(
        alphabet=base58_chars,
        min_size=32,
        max_size=44
    )


def valid_withdrawal_amount(min_amount=0.001, max_amount=10.0):
    """
    Generate valid withdrawal amounts for testing.
    
    Args:
        min_amount: Minimum withdrawal amount (default: 0.001 SOL)
        max_amount: Maximum withdrawal amount (default: 10.0 SOL)
    
    Returns:
        Strategy generating valid withdrawal amounts
    """
    return st.floats(
        min_value=min_amount,
        max_value=max_amount,
        allow_nan=False,
        allow_infinity=False
    ).map(lambda x: round(x, 4))  # Round to 4 decimal places like SOL


def valid_wallet_balance(withdrawal_amount):
    """
    Generate valid wallet balances that can cover the withdrawal.
    
    Args:
        withdrawal_amount: The amount to be withdrawn
    
    Returns:
        Strategy generating valid wallet balances
    """
    # Balance must be at least withdrawal amount + 0.01 SOL for fees
    min_balance = withdrawal_amount + 0.01
    max_balance = withdrawal_amount + 100.0
    
    return st.floats(
        min_value=min_balance,
        max_value=max_balance,
        allow_nan=False,
        allow_infinity=False
    ).map(lambda x: round(x, 4))


# ============================================================================
# Property-Based Tests
# ============================================================================

@pytest.mark.asyncio
class TestWithdrawValidParametersProperty:
    """
    Property-based tests for /withdraw command with valid parameters.
    
    These tests verify Property 1: Valid withdrawal execution
    """
    
    @given(
        address=valid_solana_address(),
        amount=valid_withdrawal_amount(min_amount=0.001, max_amount=5.0)
    )
    @settings(max_examples=50, deadline=None)
    async def test_withdraw_valid_parameters_executes_transfer(
        self,
        address,
        amount
    ):
        """
        Property 1: Valid withdrawal execution
        
        For any valid withdrawal amount and Solana address, executing the 
        withdrawal should transfer the specified amount and return a success 
        confirmation with transaction signature.
        
        This test verifies:
        1. The command accepts valid inputs
        2. The wallet.send_sol method is called with correct parameters
        3. A success message is returned
        4. The transaction signature is included in the response
        """
        # Import test harness inside the test
        from tests.test_harness import TestHarness
        test_harness = TestHarness()
        
        # Mock the rate limiter to allow all requests
        with patch('agent.ui.commands.financial_commands.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = MagicMock(return_value=True)
            
            # Ensure we have sufficient balance
            wallet_balance = amount + 0.1  # Add buffer for fees
            
            # Setup mock bot with sufficient balance
            mock_bot = MagicMock()
            mock_bot.wallet = test_harness.create_mock_wallet(balance=wallet_balance)
            
            # Mock successful transaction
            expected_signature = f"mock_tx_sig_{hash(address)}"
            mock_bot.wallet.send_sol = AsyncMock(return_value=expected_signature)
            
            # After withdrawal, balance should be reduced
            new_balance = wallet_balance - amount
            mock_bot.wallet.get_balance = AsyncMock(side_effect=[wallet_balance, new_balance])
            
            # Create command handler
            financial_commands = FinancialCommands(mock_bot)
            
            # Create mock update and context
            update = test_harness.create_mock_telegram_update(
                "withdraw",
                args=[address, str(amount)]
            )
            context = test_harness.create_mock_telegram_context(
                args=[address, str(amount)]
            )
            
            # Execute command
            await financial_commands.cmd_withdraw(update, context)
            
            # Verify wallet.send_sol was called with correct parameters
            mock_bot.wallet.send_sol.assert_called_once()
            call_args = mock_bot.wallet.send_sol.call_args
            
            # Check that the address and amount were passed correctly
            assert call_args[0][0] == address or call_args[1].get('to') == address
            called_amount = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get('amount')
            assert abs(called_amount - amount) < 0.0001  # Allow for floating point precision
            
            # Verify success message was sent
            assert update.message.reply_text.called
            
            # Get all messages sent
            call_count = update.message.reply_text.call_count
            assert call_count >= 2  # At least "Sending..." and "Successful!" messages
            
            # Check the final success message
            final_call = update.message.reply_text.call_args_list[-1]
            final_message = final_call[0][0] if final_call[0] else final_call[1].get('text', '')
            
            # Verify success indicators in message
            assert "✅" in final_message or "Successful" in final_message
            assert str(amount) in final_message
            assert address in final_message
            assert expected_signature in final_message
    
    @given(
        address=valid_solana_address(),
        amount=valid_withdrawal_amount(min_amount=0.001, max_amount=5.0)
    )
    @settings(max_examples=50, deadline=None)
    async def test_withdraw_valid_parameters_returns_transaction_signature(
        self,
        address,
        amount
    ):
        """
        Property 1: Valid withdrawal execution - Transaction signature verification
        
        For any valid withdrawal, the response should include a transaction 
        signature that can be used to verify the transaction on-chain.
        
        This test specifically verifies that:
        1. A transaction signature is returned
        2. The signature is included in the success message
        3. A Solscan link is provided for verification
        """
        # Import test harness inside the test
        from tests.test_harness import TestHarness
        test_harness = TestHarness()
        
        # Mock the rate limiter to allow all requests
        with patch('agent.ui.commands.financial_commands.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = MagicMock(return_value=True)
            
            # Setup
            wallet_balance = amount + 0.1
            mock_bot = MagicMock()
            mock_bot.wallet = test_harness.create_mock_wallet(balance=wallet_balance)
            
            # Generate a realistic-looking transaction signature
            expected_signature = f"5{'x' * 87}"  # Solana tx signatures are ~88 chars
            mock_bot.wallet.send_sol = AsyncMock(return_value=expected_signature)
            mock_bot.wallet.get_balance = AsyncMock(side_effect=[wallet_balance, wallet_balance - amount])
            
            financial_commands = FinancialCommands(mock_bot)
            
            update = test_harness.create_mock_telegram_update(
                "withdraw",
                args=[address, str(amount)]
            )
            context = test_harness.create_mock_telegram_context(
                args=[address, str(amount)]
            )
            
            # Execute
            await financial_commands.cmd_withdraw(update, context)
            
            # Verify transaction signature is in the response
            final_call = update.message.reply_text.call_args_list[-1]
            final_message = final_call[0][0] if final_call[0] else final_call[1].get('text', '')
            
            # Check for transaction signature
            assert expected_signature in final_message
            
            # Check for Solscan link
            assert "solscan.io" in final_message.lower()
            assert expected_signature in final_message
    
    @given(
        address=valid_solana_address(),
        amount=valid_withdrawal_amount(min_amount=0.001, max_amount=5.0)
    )
    @settings(max_examples=50, deadline=None)
    async def test_withdraw_valid_parameters_updates_balance(
        self,
        address,
        amount
    ):
        """
        Property 1: Valid withdrawal execution - Balance update verification
        
        For any valid withdrawal, the wallet balance should be updated to 
        reflect the withdrawn amount.
        
        This test verifies that:
        1. The balance is checked before withdrawal
        2. The balance is checked after withdrawal
        3. The new balance is displayed in the success message
        4. The balance change matches the withdrawal amount
        """
        # Import test harness inside the test
        from tests.test_harness import TestHarness
        test_harness = TestHarness()
        
        # Mock the rate limiter to allow all requests
        with patch('agent.ui.commands.financial_commands.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = MagicMock(return_value=True)
            
            # Setup
            initial_balance = amount + 0.5  # Ensure sufficient balance
            expected_new_balance = initial_balance - amount
            
            mock_bot = MagicMock()
            mock_bot.wallet = test_harness.create_mock_wallet(balance=initial_balance)
            
            # Mock balance checks: first call returns initial, second returns new balance
            mock_bot.wallet.get_balance = AsyncMock(
                side_effect=[initial_balance, expected_new_balance]
            )
            
            expected_signature = f"mock_tx_{hash(address)}"
            mock_bot.wallet.send_sol = AsyncMock(return_value=expected_signature)
            
            financial_commands = FinancialCommands(mock_bot)
            
            update = test_harness.create_mock_telegram_update(
                "withdraw",
                args=[address, str(amount)]
            )
            context = test_harness.create_mock_telegram_context(
                args=[address, str(amount)]
            )
            
            # Execute
            await financial_commands.cmd_withdraw(update, context)
            
            # Verify get_balance was called at least twice
            assert mock_bot.wallet.get_balance.call_count >= 2
            
            # Verify new balance is in the success message
            final_call = update.message.reply_text.call_args_list[-1]
            final_message = final_call[0][0] if final_call[0] else final_call[1].get('text', '')
            
            # Check that new balance is displayed
            assert "New Balance" in final_message or "Balance" in final_message
            # The new balance should be in the message (allowing for formatting)
            assert f"{expected_new_balance:.4f}" in final_message or \
                   f"{expected_new_balance:.2f}" in final_message
    
    @given(
        address=valid_solana_address(),
        amount=valid_withdrawal_amount(min_amount=0.001, max_amount=5.0)
    )
    @settings(max_examples=50, deadline=None)
    async def test_withdraw_valid_parameters_sends_confirmation_message(
        self,
        address,
        amount
    ):
        """
        Property 1: Valid withdrawal execution - Confirmation message verification
        
        For any valid withdrawal, the user should receive:
        1. A "processing" message while the transaction is being sent
        2. A success confirmation message with all relevant details
        
        This test verifies the user experience and message flow.
        """
        # Import test harness inside the test
        from tests.test_harness import TestHarness
        test_harness = TestHarness()
        
        # Mock the rate limiter to allow all requests
        with patch('agent.ui.commands.financial_commands.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = MagicMock(return_value=True)
            
            # Setup
            wallet_balance = amount + 0.2
            mock_bot = MagicMock()
            mock_bot.wallet = test_harness.create_mock_wallet(balance=wallet_balance)
            
            expected_signature = f"tx_sig_{hash(address)}"
            mock_bot.wallet.send_sol = AsyncMock(return_value=expected_signature)
            mock_bot.wallet.get_balance = AsyncMock(
                side_effect=[wallet_balance, wallet_balance - amount]
            )
            
            financial_commands = FinancialCommands(mock_bot)
            
            update = test_harness.create_mock_telegram_update(
                "withdraw",
                args=[address, str(amount)]
            )
            context = test_harness.create_mock_telegram_context(
                args=[address, str(amount)]
            )
            
            # Execute
            await financial_commands.cmd_withdraw(update, context)
            
            # Verify multiple messages were sent
            assert update.message.reply_text.call_count >= 2
            
            # Check processing message (first message)
            first_call = update.message.reply_text.call_args_list[0]
            first_message = first_call[0][0] if first_call[0] else first_call[1].get('text', '')
            assert "Sending" in first_message or "⏳" in first_message
            
            # Check success message (last message)
            last_call = update.message.reply_text.call_args_list[-1]
            last_message = last_call[0][0] if last_call[0] else last_call[1].get('text', '')
            
            # Verify all required information is in the success message
            assert "✅" in last_message or "Successful" in last_message
            assert str(amount) in last_message  # Amount
            assert address in last_message  # Destination address
            assert expected_signature in last_message  # Transaction signature
            assert "solscan.io" in last_message.lower()  # Explorer link


# ============================================================================
# Property 2: Invalid withdrawal rejection
# ============================================================================

"""
Property 2: Invalid withdrawal rejection

**Validates: Requirements 1.5**

*For any* invalid withdrawal parameters (negative amount, invalid address, 
insufficient balance), the system should reject the withdrawal with a specific 
error message explaining the issue.

This test suite uses Hypothesis to generate various invalid withdrawal scenarios 
and verify that the /withdraw command correctly:
1. Detects the invalid input
2. Rejects the withdrawal
3. Returns a clear error message explaining the issue
4. Does NOT execute any transfer
5. Does NOT modify the wallet balance
"""


# ============================================================================
# Hypothesis Strategies for Invalid Inputs
# ============================================================================

def invalid_solana_address():
    """
    Generate invalid Solana addresses for testing.
    
    Invalid addresses include:
    - Too short (< 32 chars)
    - Too long (> 44 chars)
    - Invalid characters (not base58: 0, O, I, l)
    - Special characters
    - Empty strings
    """
    return st.one_of(
        # Too short
        st.text(alphabet="123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz", 
                min_size=1, max_size=31),
        # Too long
        st.text(alphabet="123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz", 
                min_size=45, max_size=100),
        # Invalid characters - contains 0, O, I, or l (not in base58)
        st.text(alphabet="0", min_size=32, max_size=44),
        st.text(alphabet="O", min_size=32, max_size=44),
        st.text(alphabet="I", min_size=32, max_size=44),
        st.text(alphabet="l", min_size=32, max_size=44),
        # Mixed valid and invalid characters
        st.text(alphabet="123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz0OIl", 
                min_size=32, max_size=44).filter(lambda x: any(c in x for c in "0OIl")),
        # Special characters
        st.text(alphabet="!@#$%^&*()", min_size=32, max_size=44),
        # Mixed alphanumeric with special chars
        st.text(alphabet="123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz!@#$%", 
                min_size=32, max_size=44).filter(lambda x: any(c in x for c in "!@#$%")),
        # Empty or whitespace
        st.just(""),
        st.just("   "),
        st.just("invalid_address"),
    )


def negative_or_zero_amount():
    """
    Generate negative or zero amounts for testing.
    
    Returns:
        Strategy generating invalid amounts (negative or zero)
    """
    return st.one_of(
        # Negative amounts
        st.floats(min_value=-1000.0, max_value=-0.001, allow_nan=False, allow_infinity=False),
        # Zero
        st.just(0.0),
        # Very small negative
        st.floats(min_value=-0.001, max_value=-0.0000001, allow_nan=False, allow_infinity=False),
    )


def excessive_amount(balance):
    """
    Generate amounts that exceed the wallet balance.
    
    Args:
        balance: Current wallet balance
    
    Returns:
        Strategy generating amounts greater than balance
    """
    return st.floats(
        min_value=balance + 0.001,
        max_value=balance + 1000.0,
        allow_nan=False,
        allow_infinity=False
    ).map(lambda x: round(x, 4))


def amount_leaving_insufficient_balance(balance):
    """
    Generate amounts that would leave insufficient balance for fees.
    
    The minimum balance required is 0.01 SOL for fees.
    
    Args:
        balance: Current wallet balance
    
    Returns:
        Strategy generating amounts that leave < 0.01 SOL
    """
    min_balance = 0.01
    if balance <= min_balance:
        # If balance is already too low, any amount is invalid
        return st.floats(min_value=0.001, max_value=balance, 
                        allow_nan=False, allow_infinity=False)
    
    # Generate amounts that leave less than min_balance
    return st.floats(
        min_value=balance - min_balance + 0.001,
        max_value=balance,
        allow_nan=False,
        allow_infinity=False
    ).map(lambda x: round(x, 4))


# ============================================================================
# Property-Based Tests for Invalid Parameters
# ============================================================================

@pytest.mark.asyncio
class TestWithdrawInvalidParametersProperty:
    """
    Property-based tests for /withdraw command with invalid parameters.
    
    These tests verify Property 2: Invalid withdrawal rejection
    """
    
    @given(
        address=invalid_solana_address(),
        amount=valid_withdrawal_amount(min_amount=0.001, max_amount=5.0)
    )
    @settings(max_examples=50, deadline=None)
    async def test_withdraw_invalid_address_rejected(
        self,
        address,
        amount
    ):
        """
        Property 2: Invalid withdrawal rejection - Invalid address
        
        For any invalid Solana address, the system should reject the withdrawal
        with a clear error message explaining the address format issue.
        
        This test verifies:
        1. Invalid addresses are detected
        2. The withdrawal is rejected
        3. An error message is returned
        4. No transfer is executed
        5. The wallet balance is not modified
        """
        # Import test harness inside the test
        from tests.test_harness import TestHarness
        test_harness = TestHarness()
        
        # Mock the rate limiter to allow all requests
        with patch('agent.ui.commands.financial_commands.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = MagicMock(return_value=True)
            
            # Setup
            wallet_balance = amount + 1.0  # Ensure sufficient balance
            mock_bot = MagicMock()
            mock_bot.wallet = test_harness.create_mock_wallet(balance=wallet_balance)
            
            # Mock send_sol - should NOT be called
            mock_bot.wallet.send_sol = AsyncMock()
            mock_bot.wallet.get_balance = AsyncMock(return_value=wallet_balance)
            
            financial_commands = FinancialCommands(mock_bot)
            
            update = test_harness.create_mock_telegram_update(
                "withdraw",
                args=[address, str(amount)]
            )
            context = test_harness.create_mock_telegram_context(
                args=[address, str(amount)]
            )
            
            # Execute
            await financial_commands.cmd_withdraw(update, context)
            
            # Verify send_sol was NOT called
            mock_bot.wallet.send_sol.assert_not_called()
            
            # Verify error message was sent
            assert update.message.reply_text.called
            
            # Get the error message
            call_args = update.message.reply_text.call_args
            error_message = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
            
            # Verify error indicators
            assert "❌" in error_message or "Invalid" in error_message or "Error" in error_message
            
            # Verify the message explains the issue
            assert "address" in error_message.lower() or "invalid" in error_message.lower()
    
    @given(
        address=valid_solana_address(),
        amount=negative_or_zero_amount()
    )
    @settings(max_examples=50, deadline=None)
    async def test_withdraw_negative_or_zero_amount_rejected(
        self,
        address,
        amount
    ):
        """
        Property 2: Invalid withdrawal rejection - Negative or zero amount
        
        For any negative or zero amount, the system should reject the withdrawal
        with a clear error message explaining the amount issue.
        
        This test verifies:
        1. Negative and zero amounts are detected
        2. The withdrawal is rejected
        3. An error message is returned
        4. No transfer is executed
        """
        # Import test harness inside the test
        from tests.test_harness import TestHarness
        test_harness = TestHarness()
        
        # Mock the rate limiter to allow all requests
        with patch('agent.ui.commands.financial_commands.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = MagicMock(return_value=True)
            
            # Setup
            wallet_balance = 10.0  # Sufficient balance
            mock_bot = MagicMock()
            mock_bot.wallet = test_harness.create_mock_wallet(balance=wallet_balance)
            
            # Mock send_sol - should NOT be called
            mock_bot.wallet.send_sol = AsyncMock()
            mock_bot.wallet.get_balance = AsyncMock(return_value=wallet_balance)
            
            financial_commands = FinancialCommands(mock_bot)
            
            update = test_harness.create_mock_telegram_update(
                "withdraw",
                args=[address, str(amount)]
            )
            context = test_harness.create_mock_telegram_context(
                args=[address, str(amount)]
            )
            
            # Execute
            await financial_commands.cmd_withdraw(update, context)
            
            # Verify send_sol was NOT called
            mock_bot.wallet.send_sol.assert_not_called()
            
            # Verify error message was sent
            assert update.message.reply_text.called
            
            # Get the error message
            call_args = update.message.reply_text.call_args
            error_message = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
            
            # Verify error indicators
            assert "❌" in error_message
            
            # Verify the message explains the issue (amount must be positive)
            assert "amount" in error_message.lower() or "greater than" in error_message.lower()
    
    @given(
        address=valid_solana_address(),
        balance=st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50, deadline=None)
    async def test_withdraw_insufficient_balance_rejected(
        self,
        address,
        balance
    ):
        """
        Property 2: Invalid withdrawal rejection - Insufficient balance
        
        For any withdrawal amount that exceeds the wallet balance, the system 
        should reject the withdrawal with a clear error message showing the 
        current balance and required amount.
        
        This test verifies:
        1. Insufficient balance is detected
        2. The withdrawal is rejected
        3. An error message shows current balance
        4. No transfer is executed
        """
        # Import test harness inside the test
        from tests.test_harness import TestHarness
        test_harness = TestHarness()
        
        # Generate an amount that exceeds balance
        amount = balance + 0.5
        
        # Mock the rate limiter to allow all requests
        with patch('agent.ui.commands.financial_commands.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = MagicMock(return_value=True)
            
            # Setup
            mock_bot = MagicMock()
            mock_bot.wallet = test_harness.create_mock_wallet(balance=balance)
            
            # Mock send_sol - should NOT be called
            mock_bot.wallet.send_sol = AsyncMock()
            mock_bot.wallet.get_balance = AsyncMock(return_value=balance)
            
            financial_commands = FinancialCommands(mock_bot)
            
            update = test_harness.create_mock_telegram_update(
                "withdraw",
                args=[address, str(amount)]
            )
            context = test_harness.create_mock_telegram_context(
                args=[address, str(amount)]
            )
            
            # Execute
            await financial_commands.cmd_withdraw(update, context)
            
            # Verify send_sol was NOT called
            mock_bot.wallet.send_sol.assert_not_called()
            
            # Verify error message was sent
            assert update.message.reply_text.called
            
            # Get the error message
            call_args = update.message.reply_text.call_args
            error_message = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
            
            # Verify error indicators
            assert "❌" in error_message
            
            # Verify the message explains insufficient balance
            assert "Insufficient" in error_message or "balance" in error_message.lower()
            
            # Verify current balance is shown
            assert str(balance)[:4] in error_message or f"{balance:.4f}" in error_message
    
    @given(
        address=valid_solana_address(),
        balance=st.floats(min_value=0.05, max_value=10.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50, deadline=None)
    async def test_withdraw_insufficient_balance_for_fees_rejected(
        self,
        address,
        balance
    ):
        """
        Property 2: Invalid withdrawal rejection - Insufficient balance for fees
        
        For any withdrawal amount that would leave less than 0.01 SOL for fees,
        the system should reject the withdrawal with a clear error message 
        explaining the minimum balance requirement.
        
        This test verifies:
        1. Minimum balance requirement is enforced
        2. The withdrawal is rejected
        3. An error message explains the fee requirement
        4. No transfer is executed
        """
        # Import test harness inside the test
        from tests.test_harness import TestHarness
        test_harness = TestHarness()
        
        # Generate an amount that leaves insufficient balance for fees
        min_balance = 0.01
        amount = balance - (min_balance / 2)  # Leaves less than min_balance
        
        # Skip if amount would be negative or zero
        assume(amount > 0)
        
        # Mock the rate limiter to allow all requests
        with patch('agent.ui.commands.financial_commands.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = MagicMock(return_value=True)
            
            # Setup
            mock_bot = MagicMock()
            mock_bot.wallet = test_harness.create_mock_wallet(balance=balance)
            
            # Mock send_sol - should NOT be called
            mock_bot.wallet.send_sol = AsyncMock()
            mock_bot.wallet.get_balance = AsyncMock(return_value=balance)
            
            financial_commands = FinancialCommands(mock_bot)
            
            update = test_harness.create_mock_telegram_update(
                "withdraw",
                args=[address, str(amount)]
            )
            context = test_harness.create_mock_telegram_context(
                args=[address, str(amount)]
            )
            
            # Execute
            await financial_commands.cmd_withdraw(update, context)
            
            # Verify send_sol was NOT called
            mock_bot.wallet.send_sol.assert_not_called()
            
            # Verify error message was sent
            assert update.message.reply_text.called
            
            # Get the error message
            call_args = update.message.reply_text.call_args
            error_message = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
            
            # Verify error indicators
            assert "❌" in error_message
            
            # Verify the message explains the fee requirement
            assert ("fee" in error_message.lower() or 
                    "keep" in error_message.lower() or 
                    "minimum" in error_message.lower())
            
            # Verify minimum balance amount is mentioned
            assert "0.01" in error_message
    
    @given(
        address=valid_solana_address()
    )
    @settings(max_examples=30, deadline=None)
    async def test_withdraw_missing_parameters_shows_usage(
        self,
        address
    ):
        """
        Property 2: Invalid withdrawal rejection - Missing parameters
        
        When the /withdraw command is called without sufficient parameters,
        the system should show usage instructions with examples.
        
        This test verifies:
        1. Missing parameters are detected
        2. Usage instructions are shown
        3. Current balance is displayed
        4. No transfer is executed
        """
        # Import test harness inside the test
        from tests.test_harness import TestHarness
        test_harness = TestHarness()
        
        # Mock the rate limiter to allow all requests
        with patch('agent.ui.commands.financial_commands.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = MagicMock(return_value=True)
            
            # Setup
            wallet_balance = 5.0
            mock_bot = MagicMock()
            mock_bot.wallet = test_harness.create_mock_wallet(balance=wallet_balance)
            
            # Mock send_sol - should NOT be called
            mock_bot.wallet.send_sol = AsyncMock()
            mock_bot.wallet.get_balance = AsyncMock(return_value=wallet_balance)
            
            financial_commands = FinancialCommands(mock_bot)
            
            # Test with no arguments
            update = test_harness.create_mock_telegram_update("withdraw", args=[])
            context = test_harness.create_mock_telegram_context(args=[])
            
            # Execute
            await financial_commands.cmd_withdraw(update, context)
            
            # Verify send_sol was NOT called
            mock_bot.wallet.send_sol.assert_not_called()
            
            # Verify usage message was sent
            assert update.message.reply_text.called
            
            # Get the message
            call_args = update.message.reply_text.call_args
            message = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
            
            # Verify usage instructions
            assert "Usage" in message or "withdraw" in message.lower()
            assert "address" in message.lower() and "amount" in message.lower()
            
            # Verify current balance is shown
            assert str(wallet_balance) in message or f"{wallet_balance:.4f}" in message
    
    @given(
        address=valid_solana_address(),
        amount=valid_withdrawal_amount(min_amount=0.001, max_amount=5.0)
    )
    @settings(max_examples=30, deadline=None)
    async def test_withdraw_invalid_parameters_no_balance_change(
        self,
        address,
        amount
    ):
        """
        Property 2: Invalid withdrawal rejection - No balance change
        
        For any invalid withdrawal (invalid address, negative amount, etc.),
        the wallet balance should remain unchanged.
        
        This test verifies that rejected withdrawals do not modify state.
        """
        # Import test harness inside the test
        from tests.test_harness import TestHarness
        test_harness = TestHarness()
        
        # Use an invalid address (too short)
        invalid_address = "short"
        
        # Mock the rate limiter to allow all requests
        with patch('agent.ui.commands.financial_commands.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = MagicMock(return_value=True)
            
            # Setup
            initial_balance = amount + 1.0
            mock_bot = MagicMock()
            mock_bot.wallet = test_harness.create_mock_wallet(balance=initial_balance)
            
            # Track balance calls
            balance_calls = []
            async def track_balance():
                balance_calls.append(initial_balance)
                return initial_balance
            
            mock_bot.wallet.get_balance = AsyncMock(side_effect=track_balance)
            mock_bot.wallet.send_sol = AsyncMock()
            
            financial_commands = FinancialCommands(mock_bot)
            
            update = test_harness.create_mock_telegram_update(
                "withdraw",
                args=[invalid_address, str(amount)]
            )
            context = test_harness.create_mock_telegram_context(
                args=[invalid_address, str(amount)]
            )
            
            # Execute
            await financial_commands.cmd_withdraw(update, context)
            
            # Verify send_sol was NOT called
            mock_bot.wallet.send_sol.assert_not_called()
            
            # Verify balance was checked (for usage message) but not modified
            # The balance should only be checked once for the usage message
            assert len(balance_calls) <= 1
            
            # All balance checks should return the same value
            if balance_calls:
                assert all(b == initial_balance for b in balance_calls)
    
    @given(
        address=valid_solana_address(),
        amount=valid_withdrawal_amount(min_amount=0.001, max_amount=5.0)
    )
    @settings(max_examples=30, deadline=None)
    async def test_withdraw_rate_limit_exceeded_rejected(
        self,
        address,
        amount
    ):
        """
        Property 2: Invalid withdrawal rejection - Rate limit exceeded
        
        When a user exceeds the rate limit for withdrawal commands, the system
        should reject the request with a clear cooldown message.
        
        This test verifies:
        1. Rate limiting is enforced
        2. The withdrawal is rejected
        3. A cooldown message is shown
        4. No transfer is executed
        """
        # Import test harness inside the test
        from tests.test_harness import TestHarness
        test_harness = TestHarness()
        
        # Mock the rate limiter to DENY requests
        with patch('agent.ui.commands.financial_commands.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = MagicMock(return_value=False)
            
            # Setup
            wallet_balance = amount + 1.0
            mock_bot = MagicMock()
            mock_bot.wallet = test_harness.create_mock_wallet(balance=wallet_balance)
            
            # Mock send_sol - should NOT be called
            mock_bot.wallet.send_sol = AsyncMock()
            mock_bot.wallet.get_balance = AsyncMock(return_value=wallet_balance)
            
            financial_commands = FinancialCommands(mock_bot)
            
            update = test_harness.create_mock_telegram_update(
                "withdraw",
                args=[address, str(amount)]
            )
            context = test_harness.create_mock_telegram_context(
                args=[address, str(amount)]
            )
            
            # Execute
            await financial_commands.cmd_withdraw(update, context)
            
            # Verify send_sol was NOT called
            mock_bot.wallet.send_sol.assert_not_called()
            
            # Verify rate limit message was sent
            assert update.message.reply_text.called
            
            # Get the message
            call_args = update.message.reply_text.call_args
            message = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
            
            # Verify rate limit indicators
            assert "⏱️" in message or "Too many" in message or "wait" in message.lower()
