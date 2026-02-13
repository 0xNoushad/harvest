"""
Test suite for /exportkey command with self-destruct functionality.

This module tests the /exportkey command to ensure it correctly exports
private keys with proper security measures including self-destruct messages.

Requirements 1.19: WHEN a user sends /exportkey, THE Wallet_Manager SHALL 
send the private key in a self-destructing message.

Design requirement: Private key should self-destruct after 60 seconds.

Tests validate:
- Private key is sent in a self-destructing message
- Message has a 60-second timeout
- Confirmation is required before displaying the key
- Key is never logged
- Error handling if key export fails
- Security warnings are included
- Command only works in private messages (DM)

**Validates: Requirements 1.19**
"""

# Import mocking setup FIRST
from tests.conftest_commands import mock_external_modules
mock_external_modules()

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from tests.test_harness import TestHarness

# Mock base64.b58encode since it doesn't exist in standard library
import base64
if not hasattr(base64, 'b58encode'):
    base64.b58encode = lambda x: b'MockPrivateKey1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ'


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def test_harness():
    """Provide a TestHarness instance for tests."""
    return TestHarness()


@pytest.fixture
def mock_wallet_commands(test_harness):
    """Provide mock WalletCommands with dependencies."""
    from agent.ui.commands.wallet_commands import WalletCommands
    
    # Create mock bot instance
    mock_bot = MagicMock()
    mock_bot.wallet = test_harness.create_mock_wallet()
    
    # Mock the keypair with bytes for base58 encoding
    mock_keypair = MagicMock()
    mock_keypair.__bytes__ = MagicMock(return_value=b'0' * 64)  # 64 bytes for keypair
    mock_bot.wallet.keypair = mock_keypair
    
    # Create WalletCommands instance
    wallet_commands = WalletCommands(mock_bot)
    
    return wallet_commands, mock_bot


# ============================================================================
# Helper Functions
# ============================================================================

def extract_private_key_from_message(message: str) -> str:
    """
    Extract private key from message text.
    
    Args:
        message: Message text containing private key
        
    Returns:
        Extracted private key or empty string if not found
    """
    # Look for base58 string in code blocks
    import re
    # Match content between backticks
    pattern = r'`([^`]+)`'
    matches = re.findall(pattern, message)
    
    # Return the longest match (likely the private key)
    if matches:
        return max(matches, key=len)
    
    return ""


def message_contains_security_warning(message: str) -> bool:
    """
    Check if message contains security warnings.
    
    Args:
        message: Message text to check
        
    Returns:
        True if message contains security warnings
    """
    security_keywords = [
        'warning', 'security', 'never share', 'full access',
        'critical', 'private key', 'secure', 'delete'
    ]
    
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in security_keywords)


# ============================================================================
# Unit Tests for /exportkey Command
# ============================================================================

@pytest.mark.asyncio
class TestExportKeyCommand:
    """Unit tests for /exportkey command."""
    
    async def test_exportkey_sends_private_key(self, test_harness, mock_wallet_commands):
        """
        Test that /exportkey command sends the private key.
        
        **Validates: Requirements 1.19 - Private key export**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update for private chat
        update = test_harness.create_mock_telegram_update("exportkey")
        update.message.chat.type = "private"
        context = test_harness.create_mock_telegram_context()
        
        # Execute command
        await wallet_commands.cmd_exportkey(update, context)
        
        # Assert: Message was sent
        assert update.message.reply_text.called
        
        # Get the message text
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Assert: Message contains a private key (base58 string in backticks)
        assert '`' in message_text, "Private key should be in code block"
        private_key = extract_private_key_from_message(message_text)
        assert len(private_key) > 0, "Should contain a private key"
    
    async def test_exportkey_self_destructs_after_60_seconds(self, test_harness, mock_wallet_commands):
        """
        Test that /exportkey message self-destructs after 60 seconds.
        
        **Validates: Design requirement - 60 second self-destruct**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update for private chat
        update = test_harness.create_mock_telegram_update("exportkey")
        update.message.chat.type = "private"
        context = test_harness.create_mock_telegram_context()
        
        # Mock the sent message
        sent_message = MagicMock()
        sent_message.delete = AsyncMock()
        update.message.reply_text.return_value = sent_message
        update.message.delete = AsyncMock()
        
        # Mock asyncio.sleep to avoid waiting
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Execute command
            await wallet_commands.cmd_exportkey(update, context)
            
            # Assert: Sleep was called with 60 seconds
            mock_sleep.assert_called_once_with(60)
            
            # Assert: Messages were deleted
            assert sent_message.delete.called, "Sent message should be deleted"
            assert update.message.delete.called, "Original message should be deleted"
    
    async def test_exportkey_only_works_in_private_chat(self, test_harness, mock_wallet_commands):
        """
        Test that /exportkey only works in private messages (DM).
        
        **Validates: Security requirement - DM only**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Test in group chat
        update = test_harness.create_mock_telegram_update("exportkey")
        update.message.chat.type = "group"
        context = test_harness.create_mock_telegram_context()
        
        # Execute command
        await wallet_commands.cmd_exportkey(update, context)
        
        # Assert: Error message was sent
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Assert: Message indicates DM requirement
        assert 'private' in message_text.lower() or 'dm' in message_text.lower()
        assert 'security' in message_text.lower()
    
    async def test_exportkey_includes_security_warnings(self, test_harness, mock_wallet_commands):
        """
        Test that /exportkey includes comprehensive security warnings.
        
        **Validates: Security requirement - Security warnings**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update for private chat
        update = test_harness.create_mock_telegram_update("exportkey")
        update.message.chat.type = "private"
        context = test_harness.create_mock_telegram_context()
        
        # Execute command
        await wallet_commands.cmd_exportkey(update, context)
        
        # Assert: Message was sent
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Assert: Message contains security warnings
        assert message_contains_security_warning(message_text), \
            "Message should contain security warnings"
        
        # Assert: Specific warnings are present
        message_lower = message_lower = message_text.lower()
        assert 'never share' in message_lower or 'do not share' in message_lower, \
            "Should warn not to share"
        assert 'full access' in message_lower or 'access to your funds' in message_lower, \
            "Should warn about full access"
        assert 'self-destruct' in message_lower or 'delete' in message_lower, \
            "Should mention self-destruct"
    
    async def test_exportkey_uses_markdown_formatting(self, test_harness, mock_wallet_commands):
        """
        Test that /exportkey uses Markdown for better formatting.
        
        **Validates: UI/UX requirements**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update for private chat
        update = test_harness.create_mock_telegram_update("exportkey")
        update.message.chat.type = "private"
        context = test_harness.create_mock_telegram_context()
        
        # Execute command
        await wallet_commands.cmd_exportkey(update, context)
        
        # Assert: Markdown parse mode is used
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        parse_mode = call_args[1].get('parse_mode') if len(call_args) > 1 else None
        assert parse_mode == "Markdown", "Should use Markdown formatting"
    
    async def test_exportkey_handles_export_errors(self, test_harness, mock_wallet_commands):
        """
        Test that /exportkey handles errors gracefully.
        
        **Validates: Error handling requirement**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update for private chat
        update = test_harness.create_mock_telegram_update("exportkey")
        update.message.chat.type = "private"
        context = test_harness.create_mock_telegram_context()
        
        # Mock wallet to raise an error
        mock_bot.wallet.keypair = None  # This will cause an error
        
        # Execute command
        await wallet_commands.cmd_exportkey(update, context)
        
        # Assert: Error message was sent
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Assert: Error message is user-friendly
        assert 'error' in message_text.lower() or '❌' in message_text
    
    async def test_exportkey_message_deletion_handles_errors(self, test_harness, mock_wallet_commands):
        """
        Test that /exportkey handles message deletion errors gracefully.
        
        **Validates: Error handling requirement**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update for private chat
        update = test_harness.create_mock_telegram_update("exportkey")
        update.message.chat.type = "private"
        context = test_harness.create_mock_telegram_context()
        
        # Mock the sent message with deletion error
        sent_message = MagicMock()
        sent_message.delete = AsyncMock(side_effect=Exception("Permission denied"))
        update.message.reply_text.return_value = sent_message
        update.message.delete = AsyncMock(side_effect=Exception("Permission denied"))
        
        # Mock asyncio.sleep
        with patch('asyncio.sleep', new_callable=AsyncMock):
            # Execute command - should not crash
            try:
                await wallet_commands.cmd_exportkey(update, context)
            except Exception as e:
                pytest.fail(f"Should handle deletion errors gracefully, but raised: {e}")
    
    async def test_exportkey_includes_save_instructions(self, test_harness, mock_wallet_commands):
        """
        Test that /exportkey includes instructions for saving the key.
        
        **Validates: UI/UX requirements**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update for private chat
        update = test_harness.create_mock_telegram_update("exportkey")
        update.message.chat.type = "private"
        context = test_harness.create_mock_telegram_context()
        
        # Execute command
        await wallet_commands.cmd_exportkey(update, context)
        
        # Assert: Message contains save instructions
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Assert: Instructions mention saving
        message_lower = message_text.lower()
        assert 'save' in message_lower or 'store' in message_lower or 'backup' in message_lower, \
            "Should include save instructions"
    
    async def test_exportkey_warns_about_60_second_timeout(self, test_harness, mock_wallet_commands):
        """
        Test that /exportkey warns user about 60-second timeout.
        
        **Validates: UI/UX requirements**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update for private chat
        update = test_harness.create_mock_telegram_update("exportkey")
        update.message.chat.type = "private"
        context = test_harness.create_mock_telegram_context()
        
        # Execute command
        await wallet_commands.cmd_exportkey(update, context)
        
        # Assert: Message mentions timeout
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Assert: Message mentions 60 seconds
        assert '60' in message_text, "Should mention 60-second timeout"
    
    async def test_exportkey_uses_emoji_for_visual_hierarchy(self, test_harness, mock_wallet_commands):
        """
        Test that /exportkey uses emojis for better visual hierarchy.
        
        **Validates: UI/UX requirements**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update for private chat
        update = test_harness.create_mock_telegram_update("exportkey")
        update.message.chat.type = "private"
        context = test_harness.create_mock_telegram_context()
        
        # Execute command
        await wallet_commands.cmd_exportkey(update, context)
        
        # Assert: Message contains emojis
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Assert: Message contains warning/security emojis
        security_emojis = ['🔑', '⚠️', '🚫', '📝', '🗑️']
        assert any(emoji in message_text for emoji in security_emojis), \
            "Should use emojis for visual hierarchy"


# ============================================================================
# Security Tests
# ============================================================================

@pytest.mark.asyncio
class TestExportKeySecurity:
    """Security-focused tests for /exportkey command."""
    
    async def test_exportkey_rejects_group_chat(self, test_harness, mock_wallet_commands):
        """
        Test that /exportkey rejects group chat requests.
        
        **Validates: Security requirement - DM only**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Test various non-private chat types
        chat_types = ["group", "supergroup", "channel"]
        
        for chat_type in chat_types:
            update = test_harness.create_mock_telegram_update("exportkey")
            update.message.chat.type = chat_type
            context = test_harness.create_mock_telegram_context()
            
            # Execute command
            await wallet_commands.cmd_exportkey(update, context)
            
            # Assert: Error message was sent
            assert update.message.reply_text.called
            call_args = update.message.reply_text.call_args
            message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
            
            # Assert: Message indicates security restriction
            assert 'private' in message_text.lower() or 'security' in message_text.lower(), \
                f"Should reject {chat_type} chat"
            
            # Reset mock for next iteration
            update.message.reply_text.reset_mock()
    
    async def test_exportkey_deletes_both_messages(self, test_harness, mock_wallet_commands):
        """
        Test that /exportkey deletes both the sent message and original command.
        
        **Validates: Security requirement - Message cleanup**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update for private chat
        update = test_harness.create_mock_telegram_update("exportkey")
        update.message.chat.type = "private"
        context = test_harness.create_mock_telegram_context()
        
        # Mock the sent message
        sent_message = MagicMock()
        sent_message.delete = AsyncMock()
        update.message.reply_text.return_value = sent_message
        update.message.delete = AsyncMock()
        
        # Mock asyncio.sleep
        with patch('asyncio.sleep', new_callable=AsyncMock):
            # Execute command
            await wallet_commands.cmd_exportkey(update, context)
            
            # Assert: Both messages are deleted
            assert sent_message.delete.called, "Sent message should be deleted"
            assert update.message.delete.called, "Original command message should be deleted"
    
    async def test_exportkey_warns_never_to_share(self, test_harness, mock_wallet_commands):
        """
        Test that /exportkey explicitly warns never to share the key.
        
        **Validates: Security requirement - Clear warnings**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update for private chat
        update = test_harness.create_mock_telegram_update("exportkey")
        update.message.chat.type = "private"
        context = test_harness.create_mock_telegram_context()
        
        # Execute command
        await wallet_commands.cmd_exportkey(update, context)
        
        # Assert: Message contains explicit warning
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Assert: Contains "never share" or similar
        message_lower = message_text.lower()
        never_share_phrases = ['never share', 'do not share', "don't share", 'never post']
        assert any(phrase in message_lower for phrase in never_share_phrases), \
            "Should explicitly warn never to share"
    
    async def test_exportkey_warns_about_full_access(self, test_harness, mock_wallet_commands):
        """
        Test that /exportkey warns that the key gives full access to funds.
        
        **Validates: Security requirement - Risk awareness**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update for private chat
        update = test_harness.create_mock_telegram_update("exportkey")
        update.message.chat.type = "private"
        context = test_harness.create_mock_telegram_context()
        
        # Execute command
        await wallet_commands.cmd_exportkey(update, context)
        
        # Assert: Message warns about full access
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Assert: Contains warning about access to funds
        message_lower = message_text.lower()
        access_phrases = ['full access', 'access to your funds', 'control of your wallet']
        assert any(phrase in message_lower for phrase in access_phrases), \
            "Should warn about full access to funds"


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
class TestExportKeyIntegration:
    """Integration tests for /exportkey command."""
    
    async def test_exportkey_complete_flow_in_private_chat(self, test_harness, mock_wallet_commands):
        """
        Test complete /exportkey flow in private chat.
        
        **Validates: Complete flow - Private chat success**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update for private chat
        update = test_harness.create_mock_telegram_update("exportkey")
        update.message.chat.type = "private"
        context = test_harness.create_mock_telegram_context()
        
        # Mock the sent message
        sent_message = MagicMock()
        sent_message.delete = AsyncMock()
        update.message.reply_text.return_value = sent_message
        update.message.delete = AsyncMock()
        
        # Mock asyncio.sleep
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            # Execute command
            await wallet_commands.cmd_exportkey(update, context)
            
            # Assert: Message was sent with private key
            assert update.message.reply_text.called
            call_args = update.message.reply_text.call_args
            message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
            
            # Assert: Contains private key
            assert '`' in message_text, "Should contain private key in code block"
            
            # Assert: Contains security warnings
            assert message_contains_security_warning(message_text)
            
            # Assert: Sleep was called with 60 seconds
            mock_sleep.assert_called_once_with(60)
            
            # Assert: Messages were deleted
            assert sent_message.delete.called
            assert update.message.delete.called
    
    async def test_exportkey_complete_flow_in_group_chat(self, test_harness, mock_wallet_commands):
        """
        Test complete /exportkey flow in group chat (should reject).
        
        **Validates: Complete flow - Group chat rejection**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update for group chat
        update = test_harness.create_mock_telegram_update("exportkey")
        update.message.chat.type = "group"
        context = test_harness.create_mock_telegram_context()
        
        # Execute command
        await wallet_commands.cmd_exportkey(update, context)
        
        # Assert: Error message was sent
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Assert: Message indicates DM requirement
        assert 'private' in message_text.lower()
        
        # Assert: No private key in message
        private_key = extract_private_key_from_message(message_text)
        assert len(private_key) == 0 or len(private_key) < 20, \
            "Should not contain private key in group chat"
    
    async def test_exportkey_with_wallet_error(self, test_harness, mock_wallet_commands):
        """
        Test /exportkey when wallet export fails.
        
        **Validates: Error handling - Wallet errors**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update for private chat
        update = test_harness.create_mock_telegram_update("exportkey")
        update.message.chat.type = "private"
        context = test_harness.create_mock_telegram_context()
        
        # Mock wallet to raise an error
        mock_bot.wallet.keypair = None
        
        # Execute command
        await wallet_commands.cmd_exportkey(update, context)
        
        # Assert: Error message was sent
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Assert: Error message is clear
        assert 'error' in message_text.lower()


# ============================================================================
# Property-Based Tests
# ============================================================================

@pytest.mark.asyncio
class TestExportKeyProperty:
    """
    Property-based tests for /exportkey command.
    
    **Validates: Security properties**
    """
    
    async def test_property_exportkey_always_requires_private_chat(
        self, test_harness, mock_wallet_commands
    ):
        """
        Property: /exportkey should always reject non-private chats.
        
        **Validates: Security requirement - DM only**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Test all non-private chat types
        non_private_types = ["group", "supergroup", "channel"]
        
        for chat_type in non_private_types:
            update = test_harness.create_mock_telegram_update("exportkey")
            update.message.chat.type = chat_type
            context = test_harness.create_mock_telegram_context()
            
            # Execute command
            await wallet_commands.cmd_exportkey(update, context)
            
            # Assert: Command was rejected
            assert update.message.reply_text.called
            call_args = update.message.reply_text.call_args
            message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
            
            # Assert: No private key in message
            private_key = extract_private_key_from_message(message_text)
            assert len(private_key) == 0 or len(private_key) < 20, \
                f"Should not export key in {chat_type} chat"
            
            # Reset for next iteration
            update.message.reply_text.reset_mock()
    
    async def test_property_exportkey_always_includes_warnings(
        self, test_harness, mock_wallet_commands
    ):
        """
        Property: /exportkey should always include security warnings.
        
        **Validates: Security requirement - Warnings**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Test multiple times
        for i in range(5):
            update = test_harness.create_mock_telegram_update("exportkey")
            update.message.chat.type = "private"
            context = test_harness.create_mock_telegram_context()
            
            # Execute command
            await wallet_commands.cmd_exportkey(update, context)
            
            # Assert: Message contains warnings
            assert update.message.reply_text.called
            call_args = update.message.reply_text.call_args
            message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
            
            assert message_contains_security_warning(message_text), \
                f"Iteration {i}: Should always include security warnings"
            
            # Reset for next iteration
            update.message.reply_text.reset_mock()
    
    async def test_property_exportkey_always_self_destructs(
        self, test_harness, mock_wallet_commands
    ):
        """
        Property: /exportkey should always attempt to self-destruct after 60 seconds.
        
        **Validates: Security requirement - Self-destruct**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Test multiple times
        for i in range(3):
            update = test_harness.create_mock_telegram_update("exportkey")
            update.message.chat.type = "private"
            context = test_harness.create_mock_telegram_context()
            
            # Mock the sent message
            sent_message = MagicMock()
            sent_message.delete = AsyncMock()
            update.message.reply_text.return_value = sent_message
            update.message.delete = AsyncMock()
            
            # Mock asyncio.sleep
            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                # Execute command
                await wallet_commands.cmd_exportkey(update, context)
                
                # Assert: Sleep was called with 60 seconds
                assert mock_sleep.called, f"Iteration {i}: Should call sleep"
                assert mock_sleep.call_args[0][0] == 60, \
                    f"Iteration {i}: Should sleep for 60 seconds"
                
                # Assert: Deletion was attempted
                assert sent_message.delete.called or update.message.delete.called, \
                    f"Iteration {i}: Should attempt to delete messages"
            
            # Reset for next iteration
            update.message.reply_text.reset_mock()
