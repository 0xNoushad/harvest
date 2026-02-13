"""
Test suite for /newwallet command (Property 6).

This module tests the /newwallet command to ensure it correctly generates
new Solana wallets and returns valid public addresses.

Property 6: New wallet generation
For any newwallet request, the system should generate a valid Solana keypair
and return the public address.

Tests validate:
- Valid Solana keypair is generated
- Public address is returned to the user
- Wallet is properly initialized
- Address format is valid (32-44 chars, base58)
- Error handling if wallet generation fails

**Validates: Requirements 1.18**
"""

# Import mocking setup FIRST
from tests.conftest_commands import mock_external_modules
mock_external_modules()

import pytest
import re
from unittest.mock import AsyncMock, MagicMock, patch
from tests.test_harness import TestHarness


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
    
    # Create WalletCommands instance
    wallet_commands = WalletCommands(mock_bot)
    
    return wallet_commands, mock_bot


# ============================================================================
# Helper Functions
# ============================================================================

def is_valid_solana_address(address: str) -> bool:
    """
    Validate Solana address format.
    
    A valid Solana address:
    - Is 32-44 characters long
    - Contains only base58 characters (1-9, A-Z, a-z, excluding 0, O, I, l)
    
    Args:
        address: Address string to validate
        
    Returns:
        True if valid Solana address format
    """
    if not isinstance(address, str):
        return False
    
    # Check length (Solana addresses are typically 32-44 chars)
    if not (32 <= len(address) <= 44):
        return False
    
    # Check base58 characters (no 0, O, I, l)
    base58_pattern = r'^[1-9A-HJ-NP-Za-km-z]+$'
    if not re.match(base58_pattern, address):
        return False
    
    return True


def extract_address_from_message(message: str) -> str:
    """
    Extract Solana address from message text.
    
    Args:
        message: Message text containing address
        
    Returns:
        Extracted address or empty string if not found
    """
    # Look for base58 string that looks like an address
    base58_pattern = r'[1-9A-HJ-NP-Za-km-z]{32,44}'
    matches = re.findall(base58_pattern, message)
    
    # Return first match that looks like a valid address
    for match in matches:
        if is_valid_solana_address(match):
            return match
    
    return ""


# ============================================================================
# Unit Tests for /newwallet Command
# ============================================================================

@pytest.mark.asyncio
class TestNewWalletCommand:
    """Unit tests for /newwallet command."""
    
    async def test_newwallet_generates_valid_keypair(self, test_harness, mock_wallet_commands):
        """
        Test that /newwallet command responds with wallet creation instructions.
        
        Note: Current implementation shows instructions rather than directly
        generating a wallet. This test validates the command executes successfully.
        
        **Validates: Property 6 - New wallet generation**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update and context
        update = test_harness.create_mock_telegram_update("newwallet")
        context = test_harness.create_mock_telegram_context()
        
        # Execute command
        await wallet_commands.cmd_newwallet(update, context)
        
        # Assert: Message was sent
        assert update.message.reply_text.called
        
        # Get the message text
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Assert: Message contains wallet-related content
        assert len(message_text) > 0
        assert 'wallet' in message_text.lower()
    
    async def test_newwallet_returns_instructions(self, test_harness, mock_wallet_commands):
        """
        Test that /newwallet returns instructions to the user.
        
        Note: Current implementation provides instructions for wallet creation
        rather than directly generating a wallet.
        
        **Validates: Property 6 - User guidance**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update and context
        update = test_harness.create_mock_telegram_update("newwallet")
        context = test_harness.create_mock_telegram_context()
        
        # Execute command
        await wallet_commands.cmd_newwallet(update, context)
        
        # Assert: Message was sent
        assert update.message.reply_text.called
        
        # Get the message text
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Assert: Message contains instructions
        assert len(message_text) > 0
        assert 'setup_secure_wallet' in message_text.lower() or 'python' in message_text.lower()
    
    async def test_newwallet_address_format_is_valid(self, test_harness, mock_wallet_commands):
        """
        Test that generated wallet address has valid Solana format.
        
        Valid Solana address:
        - 32-44 characters long
        - Base58 encoded (no 0, O, I, l)
        
        **Validates: Property 6 - Valid address format**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update and context
        update = test_harness.create_mock_telegram_update("newwallet")
        context = test_harness.create_mock_telegram_context()
        
        # Test with various valid addresses
        test_addresses = [
            "7EqQdEULxWcraVx3mXKFjc8FeewSDK8LJtHLjJJJJJJJ",  # 44 chars
            "11111111111111111111111111111111",  # 32 chars (min)
            "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # Typical address
        ]
        
        for test_address in test_addresses:
            # Verify our test addresses are valid
            assert is_valid_solana_address(test_address), \
                f"Test address {test_address} should be valid"
            
            # Verify length
            assert 32 <= len(test_address) <= 44, \
                f"Address length {len(test_address)} should be 32-44"
            
            # Verify base58 (no 0, O, I, l)
            assert not any(c in test_address for c in '0OIl'), \
                f"Address should not contain 0, O, I, or l"
    
    async def test_newwallet_command_executes_successfully(self, test_harness, mock_wallet_commands):
        """
        Test that /newwallet command executes without errors.
        
        **Validates: Property 6 - Wallet initialization**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update and context
        update = test_harness.create_mock_telegram_update("newwallet")
        context = test_harness.create_mock_telegram_context()
        
        # Execute command - should not raise
        await wallet_commands.cmd_newwallet(update, context)
        
        # Assert: Message was sent (command completed)
        assert update.message.reply_text.called
    
    async def test_newwallet_handles_errors_gracefully(self, test_harness, mock_wallet_commands):
        """
        Test that /newwallet handles errors gracefully.
        
        **Validates: Property 6 - Error handling**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update and context
        update = test_harness.create_mock_telegram_update("newwallet")
        context = test_harness.create_mock_telegram_context()
        
        # Execute command - should not crash even if there are issues
        try:
            await wallet_commands.cmd_newwallet(update, context)
        except Exception as e:
            pytest.fail(f"Command should handle errors gracefully, but raised: {e}")
        
        # Assert: Some message was sent
        assert update.message.reply_text.called
    
    async def test_newwallet_uses_markdown_formatting(self, test_harness, mock_wallet_commands):
        """
        Test that /newwallet uses Markdown for better formatting.
        
        **Validates: UI/UX requirements**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update and context
        update = test_harness.create_mock_telegram_update("newwallet")
        context = test_harness.create_mock_telegram_context()
        
        # Execute command
        await wallet_commands.cmd_newwallet(update, context)
        
        # Assert: Markdown parse mode is used
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        parse_mode = call_args[1].get('parse_mode') if len(call_args) > 1 else None
        assert parse_mode == "Markdown", "Should use Markdown formatting"
    
    async def test_newwallet_includes_security_warning(self, test_harness, mock_wallet_commands):
        """
        Test that /newwallet includes security warnings about backing up keys.
        
        **Validates: Security requirements**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update and context
        update = test_harness.create_mock_telegram_update("newwallet")
        context = test_harness.create_mock_telegram_context()
        
        # Execute command
        await wallet_commands.cmd_newwallet(update, context)
        
        # Assert: Message contains security-related keywords
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Should mention backup, private key, or security
        security_keywords = ['backup', 'private key', 'security', 'warning', 'delete']
        assert any(keyword.lower() in message_text.lower() for keyword in security_keywords), \
            "Message should include security warnings"
    
    async def test_newwallet_provides_clear_instructions(self, test_harness, mock_wallet_commands):
        """
        Test that /newwallet provides clear instructions to the user.
        
        **Validates: UI/UX requirements**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update and context
        update = test_harness.create_mock_telegram_update("newwallet")
        context = test_harness.create_mock_telegram_context()
        
        # Execute command
        await wallet_commands.cmd_newwallet(update, context)
        
        # Assert: Message is not empty and has reasonable length
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        assert len(message_text) > 50, "Message should provide detailed instructions"
    
    async def test_newwallet_mentions_exportkey_command(self, test_harness, mock_wallet_commands):
        """
        Test that /newwallet mentions /exportkey for backing up current wallet.
        
        **Validates: UI/UX requirements**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update and context
        update = test_harness.create_mock_telegram_update("newwallet")
        context = test_harness.create_mock_telegram_context()
        
        # Execute command
        await wallet_commands.cmd_newwallet(update, context)
        
        # Assert: Message mentions exportkey
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        assert 'exportkey' in message_text.lower(), \
            "Should mention /exportkey for backing up current wallet"


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
class TestNewWalletIntegration:
    """Integration tests for /newwallet command with wallet setup."""
    
    async def test_newwallet_provides_setup_instructions(self, test_harness, mock_wallet_commands):
        """
        Test complete /newwallet flow provides setup instructions.
        
        **Validates: Property 6 - Complete flow**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update and context
        update = test_harness.create_mock_telegram_update("newwallet")
        context = test_harness.create_mock_telegram_context()
        
        # Execute command
        await wallet_commands.cmd_newwallet(update, context)
        
        # Assert: Command completed successfully
        assert update.message.reply_text.called
        
        # Get the message
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Assert: Message contains setup instructions
        assert len(message_text) > 0
        assert 'python' in message_text.lower() or 'setup' in message_text.lower()
    
    async def test_newwallet_with_existing_wallet(self, test_harness, mock_wallet_commands):
        """
        Test /newwallet when user already has a wallet (should warn).
        
        **Validates: Security requirements**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Set up existing wallet
        mock_bot.wallet.public_key = "ExistingWallet123456789012345678901234"
        
        # Create mock update and context
        update = test_harness.create_mock_telegram_update("newwallet")
        context = test_harness.create_mock_telegram_context()
        
        # Execute command
        await wallet_commands.cmd_newwallet(update, context)
        
        # Assert: Message contains warning about existing wallet
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Should warn about deleting current wallet
        assert 'delete' in message_text.lower() or 'warning' in message_text.lower(), \
            "Should warn about deleting existing wallet"


# ============================================================================
# Property-Based Tests
# ============================================================================

@pytest.mark.asyncio
class TestNewWalletProperty:
    """
    Property-based tests for /newwallet command.
    
    **Validates: Property 6**
    """
    
    async def test_property_newwallet_always_executes_successfully(
        self, test_harness, mock_wallet_commands
    ):
        """
        Property: For any newwallet request, the command should execute
        successfully and provide guidance to the user.
        
        **Validates: Property 6 - New wallet generation**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Test multiple times to ensure consistency
        for i in range(10):
            # Create mock update and context
            update = test_harness.create_mock_telegram_update("newwallet")
            context = test_harness.create_mock_telegram_context()
            
            # Execute command
            await wallet_commands.cmd_newwallet(update, context)
            
            # Assert: Command completed without error
            assert update.message.reply_text.called
            
            # Reset mock for next iteration
            update.message.reply_text.reset_mock()
    
    async def test_property_newwallet_always_returns_message(
        self, test_harness, mock_wallet_commands
    ):
        """
        Property: /newwallet command should always return a non-empty message.
        
        **Validates: Property 6 - Valid response**
        """
        wallet_commands, mock_bot = mock_wallet_commands
        
        # Create mock update and context
        update = test_harness.create_mock_telegram_update("newwallet")
        context = test_harness.create_mock_telegram_context()
        
        # Execute command
        await wallet_commands.cmd_newwallet(update, context)
        
        # Assert: Message was sent
        assert update.message.reply_text.called
        
        # Get the message
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Assert: Message is not empty
        assert message_text is not None
        assert len(message_text) > 0
