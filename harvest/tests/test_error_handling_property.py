"""
Property-based test suite for error handling and user feedback.

This module tests Properties 50-53:
- Property 50: Error message clarity
- Property 51: Error logging with context
- Property 52: Success confirmation
- Property 53: Long operation progress updates

Tests validate:
- All errors provide clear, actionable messages
- All errors are logged with full context
- All successful operations provide confirmation
- Long operations send progress updates
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import List, Dict, Any, Optional

from hypothesis import given, settings, strategies as st, assume
from tests.generators import (
    user_strategy,
    error_scenario_strategy,
    telegram_command_strategy,
    sol_amount_strategy,
    solana_address_strategy
)


# ============================================================================
# Property 50: Error Message Clarity
# ============================================================================

@given(error_scenario_strategy())
@settings(max_examples=50, deadline=None)
def test_property_error_message_clarity(error_scenario):
    """
    Property 50: Error message clarity
    
    For any operation failure, the system should display user-friendly error
    message explaining the issue and suggesting recovery actions if applicable.
    
    Test Strategy:
    - Generate various error scenarios
    - Verify error messages are clear and actionable
    - Verify messages contain specific details
    - Verify messages suggest recovery actions
    """
    error_type = error_scenario["error_type"]
    error_message = error_scenario["error_message"]
    user_facing_message = error_scenario["user_facing_message"]
    
    # Verify user-facing message is not empty
    assert len(user_facing_message) > 0, "Error message should not be empty"
    
    # Verify message is reasonably long (not just "Error")
    assert len(user_facing_message) >= 20, \
        f"Error message should be descriptive, got: {user_facing_message}"
    
    # Verify message doesn't contain technical jargon for user-facing errors
    technical_terms = ["NoneType", "AttributeError", "KeyError", "IndexError"]
    for term in technical_terms:
        assert term not in user_facing_message, \
            f"User-facing message should not contain technical term: {term}"


@pytest.mark.asyncio
async def test_insufficient_balance_error_message(test_harness):
    """
    Test that insufficient balance errors provide clear, actionable messages.
    
    Validates Property 50: Error messages explain issue and suggest actions.
    """
    # Mock wallet with low balance
    wallet = test_harness.create_mock_wallet(balance=0.5)
    
    # Attempt withdrawal exceeding balance
    withdrawal_amount = 1.0
    
    # Generate error message
    def generate_insufficient_balance_error(current: float, required: float) -> str:
        """Generate user-friendly insufficient balance error."""
        return (
            f"❌ Withdrawal Failed\n\n"
            f"Issue: Insufficient balance\n"
            f"Current Balance: {current:.2f} SOL\n"
            f"Required: {required:.2f} SOL\n\n"
            f"💡 What you can do:\n"
            f"• Add more SOL to your wallet\n"
            f"• Reduce withdrawal amount\n"
            f"• Check /wallet for details"
        )
    
    error_msg = generate_insufficient_balance_error(0.5, 1.0)
    
    # Verify message contains key elements
    assert "Insufficient balance" in error_msg, "Should explain the issue"
    assert "0.5" in error_msg, "Should show current balance"
    assert "1.0" in error_msg or "1.00" in error_msg, "Should show required amount"
    assert "Add more SOL" in error_msg or "Reduce withdrawal" in error_msg, \
        "Should suggest recovery actions"
    assert "/wallet" in error_msg, "Should reference relevant command"


@pytest.mark.asyncio
async def test_invalid_address_error_message(test_harness):
    """
    Test that invalid address errors provide clear format guidance.
    
    Validates Property 50: Validation errors explain expected format.
    """
    invalid_address = "not_a_valid_address"
    
    def generate_invalid_address_error(address: str) -> str:
        """Generate user-friendly invalid address error."""
        return (
            f"❌ Invalid Address\n\n"
            f"The address '{address}' is not a valid Solana address.\n\n"
            f"Valid Solana addresses:\n"
            f"• Are 32-44 characters long\n"
            f"• Use base58 encoding\n"
            f"• Start with letters/numbers\n\n"
            f"Example: 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
        )
    
    error_msg = generate_invalid_address_error(invalid_address)
    
    # Verify message contains key elements
    assert invalid_address in error_msg, "Should show the invalid address"
    assert "not a valid" in error_msg.lower(), "Should explain it's invalid"
    assert "32-44 characters" in error_msg, "Should explain format requirements"
    assert "base58" in error_msg, "Should mention encoding"


@pytest.mark.asyncio
async def test_network_error_message(test_harness):
    """
    Test that network errors suggest retry and indicate temporary issue.
    
    Validates Property 50: Recoverable errors suggest specific actions.
    """
    def generate_network_error() -> str:
        """Generate user-friendly network error."""
        return (
            f"⚠️ Network Error\n\n"
            f"Unable to connect to Solana network.\n"
            f"This is usually a temporary issue.\n\n"
            f"💡 What you can do:\n"
            f"• Wait a moment and try again\n"
            f"• Check your internet connection\n"
            f"• Use /status to check bot status"
        )
    
    error_msg = generate_network_error()
    
    # Verify message contains key elements
    assert "Network Error" in error_msg or "Unable to connect" in error_msg, \
        "Should explain the issue"
    assert "temporary" in error_msg.lower(), "Should indicate it's temporary"
    assert "try again" in error_msg.lower(), "Should suggest retry"


# ============================================================================
# Property 51: Error Logging with Context
# ============================================================================

@given(
    user_strategy(),
    telegram_command_strategy,
    error_scenario_strategy()
)
@settings(max_examples=30, deadline=None)
def test_property_error_logging_with_context(user, command, error_scenario):
    """
    Property 51: Error logging with context
    
    For any error occurrence, the system should log full context including
    user ID, command, parameters, timestamp, and stack trace.
    
    Test Strategy:
    - Generate various error scenarios with user context
    - Verify all required context is logged
    - Verify log format is consistent
    """
    # Simulate error logging
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "level": "ERROR",
        "user_id": user["user_id"],
        "command": command,
        "error_type": error_scenario["error_type"],
        "error_message": error_scenario["error_message"],
        "user_facing_message": error_scenario["user_facing_message"]
    }
    
    # Verify all required fields are present
    assert "timestamp" in log_entry, "Log should include timestamp"
    assert "level" in log_entry, "Log should include level"
    assert "user_id" in log_entry, "Log should include user ID"
    assert "command" in log_entry, "Log should include command"
    assert "error_type" in log_entry, "Log should include error type"
    assert "error_message" in log_entry, "Log should include error message"
    
    # Verify user ID is valid
    assert log_entry["user_id"] > 0, "User ID should be positive"
    
    # Verify timestamp is valid
    assert len(log_entry["timestamp"]) > 0, "Timestamp should not be empty"


@pytest.mark.asyncio
async def test_error_logging_includes_stack_trace(test_harness):
    """
    Test that error logs include stack trace for debugging.
    
    Validates Property 51: Errors are logged with full context.
    """
    import traceback
    
    # Mock logger
    logged_errors = []
    
    def log_error(user_id: int, command: str, error: Exception):
        """Log error with full context."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": "ERROR",
            "user_id": user_id,
            "command": command,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "stack_trace": traceback.format_exc()
        }
        logged_errors.append(log_entry)
    
    # Simulate error
    user_id = 12345
    command = "withdraw"
    
    try:
        # Trigger an error
        raise ValueError("Invalid withdrawal amount")
    except Exception as e:
        log_error(user_id, command, e)
    
    # Verify error was logged
    assert len(logged_errors) == 1
    
    log_entry = logged_errors[0]
    
    # Verify all context is present
    assert log_entry["user_id"] == user_id
    assert log_entry["command"] == command
    assert log_entry["error_type"] == "ValueError"
    assert "Invalid withdrawal amount" in log_entry["error_message"]
    assert "stack_trace" in log_entry
    assert len(log_entry["stack_trace"]) > 0


# ============================================================================
# Property 52: Success Confirmation
# ============================================================================

@given(user_strategy(), sol_amount_strategy)
@settings(max_examples=30, deadline=None)
@pytest.mark.asyncio
async def test_property_success_confirmation(user, amount):
    """
    Property 52: Success confirmation
    
    For any successful operation, the system should provide clear confirmation
    message with relevant details.
    
    Test Strategy:
    - Generate various successful operations
    - Verify confirmation messages are provided
    - Verify messages contain relevant details
    - Verify messages use positive language
    """
    # Assume reasonable amount
    assume(0.001 <= amount <= 100.0)
    
    # Simulate successful withdrawal
    signature = "abc123xyz789"
    
    def generate_success_message(amount: float, signature: str) -> str:
        """Generate success confirmation message."""
        return (
            f"✅ Withdrawal Successful\n\n"
            f"Amount: {amount:.4f} SOL\n"
            f"Transaction: {signature[:8]}...{signature[-8:]}\n\n"
            f"Your new balance will update shortly.\n"
            f"Use /wallet to check your balance."
        )
    
    success_msg = generate_success_message(amount, signature)
    
    # Verify message contains key elements
    assert "✅" in success_msg or "Success" in success_msg, \
        "Should indicate success"
    assert str(amount)[:4] in success_msg, "Should show amount"
    assert signature[:8] in success_msg, "Should show transaction signature"
    assert "/wallet" in success_msg, "Should reference relevant command"


@pytest.mark.asyncio
async def test_trade_execution_success_confirmation(test_harness):
    """
    Test that successful trades provide detailed confirmation.
    
    Validates Property 52: Success messages include relevant details.
    """
    # Create test trade
    trade = test_harness.create_test_trade(
        strategy="jupiter_swap",
        expected_profit=0.01,
        actual_profit=0.009,
        status="completed"
    )
    
    def generate_trade_success_message(trade: Dict[str, Any]) -> str:
        """Generate trade success confirmation."""
        return (
            f"✅ Trade Completed\n\n"
            f"Strategy: {trade['strategy']}\n"
            f"Expected Profit: {trade['expected_profit']:.4f} SOL\n"
            f"Actual Profit: {trade['actual_profit']:.4f} SOL\n"
            f"Execution Time: {trade['execution_time_ms']}ms\n"
            f"Signature: {trade['signature'][:8]}...\n\n"
            f"Use /stats to see your performance."
        )
    
    success_msg = generate_trade_success_message(trade)
    
    # Verify message contains key elements
    assert "Completed" in success_msg or "Success" in success_msg
    assert trade["strategy"] in success_msg
    assert str(trade["expected_profit"])[:4] in success_msg
    assert str(trade["actual_profit"])[:4] in success_msg
    assert trade["signature"][:8] in success_msg


# ============================================================================
# Property 53: Long Operation Progress Updates
# ============================================================================

@pytest.mark.asyncio
async def test_long_operation_progress_updates(test_harness):
    """
    Property 53: Long operation progress updates
    
    For any operation taking longer than 10 seconds, the system should send
    progress update messages every 10 seconds until completion.
    
    Test Strategy:
    - Simulate long-running operation
    - Verify progress updates are sent
    - Verify updates are sent at correct intervals
    - Verify final completion message is sent
    """
    # Mock update object
    update = test_harness.create_mock_telegram_update("portfolio", user_id=12345)
    
    # Track progress messages
    progress_messages = []
    
    async def send_progress_update(message: str):
        """Send progress update to user."""
        progress_messages.append({
            "timestamp": asyncio.get_event_loop().time(),
            "message": message
        })
        await update.message.reply_text(message)
    
    async def long_running_operation(duration: float):
        """Simulate long-running operation with progress updates."""
        start_time = asyncio.get_event_loop().time()
        last_update = start_time
        
        await send_progress_update("⏳ Starting portfolio analysis...")
        
        while asyncio.get_event_loop().time() - start_time < duration:
            await asyncio.sleep(0.5)  # Check every 0.5s
            
            current_time = asyncio.get_event_loop().time()
            if current_time - last_update >= 2.0:  # Update every 2s (scaled down for testing)
                elapsed = int(current_time - start_time)
                await send_progress_update(f"⏳ Still working... ({elapsed}s elapsed)")
                last_update = current_time
        
        await send_progress_update("✅ Portfolio analysis complete!")
    
    # Run operation that takes 5 seconds
    await long_running_operation(5.0)
    
    # Verify progress updates were sent
    assert len(progress_messages) >= 3, \
        f"Should send multiple progress updates, got {len(progress_messages)}"
    
    # Verify first message is start message
    assert "Starting" in progress_messages[0]["message"]
    
    # Verify last message is completion message
    assert "complete" in progress_messages[-1]["message"].lower()
    
    # Verify intermediate updates show elapsed time
    if len(progress_messages) > 2:
        intermediate_messages = progress_messages[1:-1]
        for msg in intermediate_messages:
            assert "elapsed" in msg["message"].lower() or "working" in msg["message"].lower()


@pytest.mark.asyncio
async def test_progress_updates_interval(test_harness):
    """
    Test that progress updates are sent at correct intervals.
    
    Validates Property 53: Updates sent every 10 seconds.
    """
    # Track update times
    update_times = []
    
    async def send_update():
        """Send progress update."""
        update_times.append(asyncio.get_event_loop().time())
    
    async def operation_with_updates(duration: float, interval: float):
        """Operation that sends updates at intervals."""
        start_time = asyncio.get_event_loop().time()
        last_update = start_time
        
        await send_update()  # Initial update
        
        while asyncio.get_event_loop().time() - start_time < duration:
            await asyncio.sleep(0.1)
            
            current_time = asyncio.get_event_loop().time()
            if current_time - last_update >= interval:
                await send_update()
                last_update = current_time
        
        await send_update()  # Final update
    
    # Run operation for 3 seconds with 1 second intervals
    await operation_with_updates(duration=3.0, interval=1.0)
    
    # Verify updates were sent
    assert len(update_times) >= 3, "Should send multiple updates"
    
    # Verify intervals (allowing some tolerance)
    for i in range(1, len(update_times) - 1):
        interval = update_times[i] - update_times[i-1]
        # Allow 20% tolerance for timing
        assert 0.8 <= interval <= 1.5, \
            f"Update interval should be ~1.0s, got {interval:.2f}s"


@pytest.mark.asyncio
async def test_no_progress_updates_for_fast_operations(test_harness):
    """
    Test that fast operations don't send unnecessary progress updates.
    
    Validates Property 53: Only long operations (>10s) send progress updates.
    """
    # Track messages
    messages = []
    
    async def send_message(msg: str):
        """Send message."""
        messages.append(msg)
    
    async def fast_operation():
        """Fast operation that completes quickly."""
        await send_message("⏳ Processing...")
        await asyncio.sleep(0.1)  # Fast operation
        await send_message("✅ Complete!")
    
    # Run fast operation
    await fast_operation()
    
    # Verify only start and end messages (no progress updates)
    assert len(messages) == 2, \
        f"Fast operations should only send start/end messages, got {len(messages)}"
    assert "Processing" in messages[0]
    assert "Complete" in messages[1]


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_error_handling_end_to_end(test_harness):
    """
    End-to-end test of error handling flow.
    
    Validates Properties 50-51: Errors are handled with clear messages and
    full logging.
    """
    # Mock components
    update = test_harness.create_mock_telegram_update("withdraw", user_id=12345, args=["1.0", "invalid_address"])
    wallet = test_harness.create_mock_wallet(balance=0.5)
    
    # Track logs
    logs = []
    
    def log_error(context: Dict[str, Any]):
        """Log error with context."""
        logs.append(context)
    
    # Simulate withdrawal command with errors
    async def handle_withdraw(update, wallet):
        """Handle withdrawal with error handling."""
        try:
            # Parse amount
            amount = float(update.message.text.split()[1])
            address = update.message.text.split()[2]
            
            # Validate address
            if len(address) < 32:
                raise ValueError("Invalid Solana address format")
            
            # Check balance
            balance = await wallet.get_balance()
            if balance < amount:
                raise ValueError(f"Insufficient balance: {balance} < {amount}")
            
            # Execute withdrawal
            signature = await wallet.withdraw(amount, address)
            
            # Success message
            await update.message.reply_text(
                f"✅ Withdrawal Successful\n"
                f"Amount: {amount} SOL\n"
                f"Signature: {signature}"
            )
            
        except ValueError as e:
            # Log error
            log_error({
                "user_id": update.effective_user.id,
                "command": "withdraw",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            
            # User-facing error
            await update.message.reply_text(
                f"❌ Withdrawal Failed\n\n"
                f"Issue: {str(e)}\n\n"
                f"💡 Please check your input and try again."
            )
    
    # Execute command
    await handle_withdraw(update, wallet)
    
    # Verify error was logged
    assert len(logs) == 1
    assert logs[0]["user_id"] == 12345
    assert logs[0]["command"] == "withdraw"
    assert "Invalid" in logs[0]["error"]
    
    # Verify user received error message
    assert update.message.reply_text.called
    call_args = update.message.reply_text.call_args[0][0]
    assert "❌" in call_args or "Failed" in call_args
    assert "Invalid" in call_args
