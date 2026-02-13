"""
Tests for TestHarness assertion helper methods.

This module tests the assertion helpers provided by the TestHarness class:
- assert_telegram_message_sent(): Verify Telegram messages were sent correctly
- assert_transaction_executed(): Verify blockchain transactions were executed
- wait_for_async_operation(): Wait for async operations to complete

These helpers are used throughout the test suite to verify bot behavior.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from tests.test_harness import TestHarness


class TestAssertTelegramMessageSent:
    """Tests for assert_telegram_message_sent() helper."""
    
    def test_assert_message_sent_with_text_contains(self, test_harness):
        """Test asserting a message was sent with specific text."""
        # Create mock bot
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        # Simulate sending a message
        mock_bot.send_message(12345, "Welcome to Harvest Bot!")
        
        # Assert message was sent with expected text
        test_harness.assert_telegram_message_sent(
            mock_bot, 12345, text_contains="Welcome"
        )
    
    def test_assert_message_sent_with_call_count(self, test_harness):
        """Test asserting message was sent specific number of times."""
        # Create mock bot
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        # Send multiple messages
        mock_bot.send_message(12345, "Message 1")
        mock_bot.send_message(12345, "Message 2")
        mock_bot.send_message(12345, "Message 3")
        
        # Assert correct call count
        test_harness.assert_telegram_message_sent(
            mock_bot, 12345, call_count=3
        )
    
    def test_assert_message_sent_with_kwargs(self, test_harness):
        """Test asserting message sent using keyword arguments."""
        # Create mock bot
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        # Send message with kwargs
        mock_bot.send_message(chat_id=12345, text="Test message")
        
        # Assert message was sent
        test_harness.assert_telegram_message_sent(
            mock_bot, 12345, text_contains="Test"
        )
    
    def test_assert_message_sent_fails_when_text_not_found(self, test_harness):
        """Test assertion fails when expected text is not in message."""
        # Create mock bot
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        # Send message without expected text
        mock_bot.send_message(12345, "Different message")
        
        # Assert should fail
        with pytest.raises(AssertionError, match="Expected message containing"):
            test_harness.assert_telegram_message_sent(
                mock_bot, 12345, text_contains="Welcome"
            )
    
    def test_assert_message_sent_fails_when_call_count_wrong(self, test_harness):
        """Test assertion fails when call count doesn't match."""
        # Create mock bot
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        # Send one message
        mock_bot.send_message(12345, "Message")
        
        # Assert should fail with wrong count
        with pytest.raises(AssertionError, match="Expected 3 calls"):
            test_harness.assert_telegram_message_sent(
                mock_bot, 12345, call_count=3
            )
    
    def test_assert_message_sent_with_multiple_chats(self, test_harness):
        """Test asserting message sent to specific chat among multiple."""
        # Create mock bot
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        # Send messages to different chats
        mock_bot.send_message(12345, "Message to user 1")
        mock_bot.send_message(67890, "Message to user 2")
        mock_bot.send_message(12345, "Another message to user 1")
        
        # Assert message to specific chat
        test_harness.assert_telegram_message_sent(
            mock_bot, 12345, text_contains="user 1"
        )
    
    def test_assert_message_sent_with_no_calls(self, test_harness):
        """Test assertion with zero expected calls."""
        # Create mock bot
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        # Don't send any messages
        
        # Assert zero calls
        test_harness.assert_telegram_message_sent(
            mock_bot, 12345, call_count=0
        )


class TestAssertTransactionExecuted:
    """Tests for assert_transaction_executed() helper."""
    
    def test_assert_transaction_executed_default_method(self, test_harness):
        """Test asserting transaction was executed using default method."""
        # Create mock wallet
        mock_wallet = MagicMock()
        mock_wallet.withdraw = AsyncMock(return_value="signature_123")
        
        # Execute transaction
        mock_wallet.withdraw(1.0, "TestAddress123")
        
        # Assert transaction was executed
        test_harness.assert_transaction_executed(mock_wallet)
    
    def test_assert_transaction_executed_with_signature(self, test_harness):
        """Test asserting transaction with specific signature."""
        # Create mock wallet
        mock_wallet = MagicMock()
        mock_wallet.withdraw = AsyncMock(return_value="signature_abc123")
        
        # Execute transaction
        result = mock_wallet.withdraw(1.0, "TestAddress123")
        
        # Assert transaction with signature
        test_harness.assert_transaction_executed(
            mock_wallet, signature="signature_abc123"
        )
    
    def test_assert_transaction_executed_custom_method(self, test_harness):
        """Test asserting transaction using custom method name."""
        # Create mock wallet
        mock_wallet = MagicMock()
        mock_wallet.send_transaction = AsyncMock(return_value="tx_signature")
        
        # Execute transaction
        mock_wallet.send_transaction("transaction_data")
        
        # Assert transaction with custom method
        test_harness.assert_transaction_executed(
            mock_wallet, method_name="send_transaction"
        )
    
    def test_assert_transaction_executed_fails_when_not_called(self, test_harness):
        """Test assertion fails when transaction method not called."""
        # Create mock wallet
        mock_wallet = MagicMock()
        mock_wallet.withdraw = AsyncMock()
        
        # Don't execute transaction
        
        # Assert should fail
        with pytest.raises(AssertionError, match="was not called"):
            test_harness.assert_transaction_executed(mock_wallet)
    
    def test_assert_transaction_executed_fails_with_wrong_signature(self, test_harness):
        """Test assertion fails when signature doesn't match."""
        # Create mock wallet
        mock_wallet = MagicMock()
        mock_wallet.withdraw = AsyncMock(return_value="signature_123")
        
        # Execute transaction
        mock_wallet.withdraw(1.0, "TestAddress123")
        
        # Assert should fail with wrong signature
        with pytest.raises(AssertionError, match="not found"):
            test_harness.assert_transaction_executed(
                mock_wallet, signature="wrong_signature"
            )
    
    def test_assert_transaction_executed_fails_with_missing_method(self, test_harness):
        """Test assertion fails when method doesn't exist."""
        # Create mock wallet without the method
        mock_wallet = MagicMock(spec=[])
        
        # Assert should fail
        with pytest.raises(AssertionError, match="not found on wallet"):
            test_harness.assert_transaction_executed(
                mock_wallet, method_name="nonexistent_method"
            )
    
    def test_assert_transaction_executed_with_multiple_calls(self, test_harness):
        """Test asserting transaction when method called multiple times."""
        # Create mock wallet
        mock_wallet = MagicMock()
        mock_wallet.withdraw = AsyncMock(return_value="signature_123")
        
        # Execute multiple transactions
        mock_wallet.withdraw(0.5, "Address1")
        mock_wallet.withdraw(1.0, "Address2")
        mock_wallet.withdraw(1.5, "Address3")
        
        # Assert transaction was executed (should pass with any call)
        test_harness.assert_transaction_executed(mock_wallet)


class TestWaitForAsyncOperation:
    """Tests for wait_for_async_operation() helper."""
    
    @pytest.mark.asyncio
    async def test_wait_for_condition_becomes_true(self, test_harness):
        """Test waiting for a condition that becomes true."""
        # Create a flag that will be set to True
        flag = {"value": False}
        
        # Function to set flag after delay
        async def set_flag_later():
            await asyncio.sleep(0.1)
            flag["value"] = True
        
        # Start the async task
        asyncio.create_task(set_flag_later())
        
        # Wait for condition
        result = await test_harness.wait_for_async_operation(
            lambda: flag["value"],
            timeout=1.0,
            interval=0.05
        )
        
        assert result is True
        assert flag["value"] is True
    
    @pytest.mark.asyncio
    async def test_wait_for_condition_already_true(self, test_harness):
        """Test waiting for a condition that's already true."""
        # Condition is already true
        result = await test_harness.wait_for_async_operation(
            lambda: True,
            timeout=1.0
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_wait_for_condition_timeout(self, test_harness):
        """Test timeout when condition never becomes true."""
        # Condition never becomes true
        with pytest.raises(TimeoutError, match="Condition not met within"):
            await test_harness.wait_for_async_operation(
                lambda: False,
                timeout=0.2,
                interval=0.05
            )
    
    @pytest.mark.asyncio
    async def test_wait_for_mock_method_called(self, test_harness):
        """Test waiting for a mock method to be called."""
        # Create mock
        mock_obj = MagicMock()
        mock_obj.some_method = AsyncMock()
        
        # Function to call method after delay
        async def call_method_later():
            await asyncio.sleep(0.1)
            await mock_obj.some_method()
        
        # Start the async task
        asyncio.create_task(call_method_later())
        
        # Wait for method to be called
        result = await test_harness.wait_for_async_operation(
            lambda: mock_obj.some_method.called,
            timeout=1.0,
            interval=0.05
        )
        
        assert result is True
        assert mock_obj.some_method.called
    
    @pytest.mark.asyncio
    async def test_wait_for_value_change(self, test_harness):
        """Test waiting for a value to change."""
        # Create object with changing value
        obj = {"count": 0}
        
        # Function to increment count
        async def increment_later():
            await asyncio.sleep(0.1)
            obj["count"] = 5
        
        # Start the async task
        asyncio.create_task(increment_later())
        
        # Wait for count to reach 5
        result = await test_harness.wait_for_async_operation(
            lambda: obj["count"] == 5,
            timeout=1.0,
            interval=0.05
        )
        
        assert result is True
        assert obj["count"] == 5
    
    @pytest.mark.asyncio
    async def test_wait_for_custom_interval(self, test_harness):
        """Test waiting with custom check interval."""
        # Track number of checks
        checks = {"count": 0}
        
        def condition():
            checks["count"] += 1
            return checks["count"] >= 3
        
        # Wait with custom interval
        result = await test_harness.wait_for_async_operation(
            condition,
            timeout=1.0,
            interval=0.05
        )
        
        assert result is True
        assert checks["count"] >= 3
    
    @pytest.mark.asyncio
    async def test_wait_for_with_exception_in_condition(self, test_harness):
        """Test handling exception in condition function."""
        # Condition that raises exception
        def bad_condition():
            raise ValueError("Test error")
        
        # Should propagate the exception
        with pytest.raises(ValueError, match="Test error"):
            await test_harness.wait_for_async_operation(
                bad_condition,
                timeout=0.2
            )


class TestAssertionHelpersIntegration:
    """Integration tests combining multiple assertion helpers."""
    
    @pytest.mark.asyncio
    async def test_telegram_and_transaction_assertions(self, test_harness):
        """Test using both Telegram and transaction assertions together."""
        # Create mocks
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        mock_wallet = MagicMock()
        mock_wallet.withdraw = AsyncMock(return_value="tx_signature_123")
        
        # Simulate bot workflow
        await mock_wallet.withdraw(1.0, "TestAddress")
        await mock_bot.send_message(12345, "Withdrawal successful: tx_signature_123")
        
        # Assert both operations
        test_harness.assert_transaction_executed(
            mock_wallet, signature="tx_signature_123"
        )
        test_harness.assert_telegram_message_sent(
            mock_bot, 12345, text_contains="Withdrawal successful"
        )
    
    @pytest.mark.asyncio
    async def test_wait_then_assert_message(self, test_harness):
        """Test waiting for operation then asserting message sent."""
        # Create mock bot
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        # Function to send message after delay
        async def send_message_later():
            await asyncio.sleep(0.1)
            await mock_bot.send_message(12345, "Delayed message")
        
        # Start async task
        asyncio.create_task(send_message_later())
        
        # Wait for message to be sent
        await test_harness.wait_for_async_operation(
            lambda: mock_bot.send_message.called,
            timeout=1.0
        )
        
        # Assert message was sent
        test_harness.assert_telegram_message_sent(
            mock_bot, 12345, text_contains="Delayed"
        )
    
    @pytest.mark.asyncio
    async def test_wait_for_transaction_then_verify(self, test_harness):
        """Test waiting for transaction then verifying it."""
        # Create mock wallet
        mock_wallet = MagicMock()
        mock_wallet.withdraw = AsyncMock(return_value="async_tx_sig")
        
        # Function to execute transaction after delay
        async def execute_transaction_later():
            await asyncio.sleep(0.1)
            await mock_wallet.withdraw(2.0, "TestAddress")
        
        # Start async task
        asyncio.create_task(execute_transaction_later())
        
        # Wait for transaction
        await test_harness.wait_for_async_operation(
            lambda: mock_wallet.withdraw.called,
            timeout=1.0
        )
        
        # Assert transaction was executed
        test_harness.assert_transaction_executed(mock_wallet)


class TestAssertionHelpersEdgeCases:
    """Edge case tests for assertion helpers."""
    
    def test_assert_message_with_empty_text(self, test_harness):
        """Test asserting message with empty text."""
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        # Send empty message
        mock_bot.send_message(12345, "")
        
        # Should handle empty text
        test_harness.assert_telegram_message_sent(
            mock_bot, 12345, text_contains=""
        )
    
    def test_assert_message_with_special_characters(self, test_harness):
        """Test asserting message with special characters."""
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        # Send message with special characters
        mock_bot.send_message(12345, "Balance: $127.50 (↑5.2%)")
        
        # Should handle special characters
        test_harness.assert_telegram_message_sent(
            mock_bot, 12345, text_contains="$127.50"
        )
    
    def test_assert_transaction_with_none_signature(self, test_harness):
        """Test asserting transaction when signature is None."""
        mock_wallet = MagicMock()
        mock_wallet.withdraw = AsyncMock(return_value=None)
        
        # Execute transaction that returns None
        mock_wallet.withdraw(1.0, "TestAddress")
        
        # Should still assert transaction was called
        test_harness.assert_transaction_executed(mock_wallet)
    
    @pytest.mark.asyncio
    async def test_wait_for_with_zero_timeout(self, test_harness):
        """Test waiting with very short timeout."""
        # Should timeout immediately if condition is false
        with pytest.raises(TimeoutError):
            await test_harness.wait_for_async_operation(
                lambda: False,
                timeout=0.01,
                interval=0.001
            )
    
    def test_assert_message_with_unicode(self, test_harness):
        """Test asserting message with Unicode characters."""
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        # Send message with Unicode
        mock_bot.send_message(12345, "🎉 Success! 你好 مرحبا")
        
        # Should handle Unicode
        test_harness.assert_telegram_message_sent(
            mock_bot, 12345, text_contains="🎉"
        )
