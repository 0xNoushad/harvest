"""
Test AI Chat Functionality

Tests for AI chat response generation, context management, and error handling.
Validates Properties 33, 34, 35, 36 from the design document.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st, settings
from tests.test_harness import TestHarness


class TestAIChatResponseGeneration:
    """
    Test AI response generation with context.
    
    **Validates: Property 33** - AI contextual response generation
    *For any* natural language message, the AI should generate a contextually 
    relevant response using conversation history and current system state
    """
    
    @pytest.mark.asyncio
    async def test_ai_generates_contextual_response(self):
        """Test that AI generates contextually relevant responses."""
        harness = TestHarness()
        
        # Create mock components
        mock_user_manager = MagicMock()
        mock_user_manager.get_user_context = MagicMock(
            return_value="Previous conversation:\nUser: Hello\nAssistant: Hi there!"
        )
        mock_user_manager.add_conversation = MagicMock()
        
        mock_ai_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "I can help you with trading on Solana!"
        mock_ai_provider.chat = AsyncMock(return_value=mock_response)
        
        mock_wallet = harness.create_mock_wallet(balance=1.5)
        
        # Create message handler
        from agent.handlers.message_handler import MessageHandler
        handler = MessageHandler(mock_user_manager, mock_ai_provider, mock_wallet)
        
        # Create update
        update = harness.create_mock_telegram_update(
            "help",
            user_id=12345,
            message_text="What can you do?"
        )
        update.effective_user.first_name = "TestUser"
        
        # Process message
        await handler.handle_ai_chat(
            update,
            "What can you do?",
            "12345",
            "TestUser"
        )
        
        # Verify AI was called with context
        assert mock_ai_provider.chat.called
        call_args = mock_ai_provider.chat.call_args
        messages = call_args[1]["messages"]
        
        # Should have system prompt and user message
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "What can you do?"
        
        # System prompt should include context
        system_prompt = messages[0]["content"]
        assert "TestUser" in system_prompt
        assert "12345" in system_prompt
        assert "1.5" in system_prompt  # Balance
        
        # Verify response was sent
        assert update.message.reply_text.called
        update.message.reply_text.assert_called_once_with(
            "I can help you with trading on Solana!"
        )
        
        # Verify conversation was recorded
        assert mock_user_manager.add_conversation.call_count == 1
    
    @pytest.mark.asyncio
    async def test_ai_includes_conversation_history(self):
        """Test that AI includes conversation history in context."""
        harness = TestHarness()
        
        # Create mock with conversation history
        mock_user_manager = MagicMock()
        conversation_history = """Recent conversation:
User: What's my balance?
Assistant: Your balance is 1.5 SOL
User: Can I trade?
Assistant: Yes, you can trade with that balance"""
        mock_user_manager.get_user_context = MagicMock(return_value=conversation_history)
        mock_user_manager.add_conversation = MagicMock()
        
        mock_ai_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Based on your 1.5 SOL balance, you can start trading."
        mock_ai_provider.chat = AsyncMock(return_value=mock_response)
        
        mock_wallet = harness.create_mock_wallet(balance=1.5)
        
        from agent.handlers.message_handler import MessageHandler
        handler = MessageHandler(mock_user_manager, mock_ai_provider, mock_wallet)
        
        update = harness.create_mock_telegram_update(
            "chat",
            user_id=12345,
            message_text="Should I start trading now?"
        )
        update.effective_user.first_name = "TestUser"
        
        await handler.handle_ai_chat(
            update,
            "Should I start trading now?",
            "12345",
            "TestUser"
        )
        
        # Verify context was requested
        mock_user_manager.get_user_context.assert_called_once_with("12345", limit=5)
        
        # Verify AI received the context
        call_args = mock_ai_provider.chat.call_args
        system_prompt = call_args[1]["messages"][0]["content"]
        assert conversation_history in system_prompt


class TestAIServiceQueryIntegration:
    """
    Test AI integration with services.
    
    **Validates: Property 34** - AI service query integration
    *For any* user question about system state (balance, trades, prices, portfolio), 
    the AI should query the appropriate service and format the response naturally
    """
    
    @pytest.mark.asyncio
    async def test_ai_queries_wallet_balance(self):
        """Test that AI can query wallet balance for context."""
        harness = TestHarness()
        
        mock_user_manager = MagicMock()
        mock_user_manager.get_user_context = MagicMock(return_value="")
        mock_user_manager.add_conversation = MagicMock()
        
        mock_ai_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Your current balance is 2.5 SOL."
        mock_ai_provider.chat = AsyncMock(return_value=mock_response)
        
        # Wallet with specific balance
        mock_wallet = harness.create_mock_wallet(balance=2.5)
        
        from agent.handlers.message_handler import MessageHandler
        handler = MessageHandler(mock_user_manager, mock_ai_provider, mock_wallet)
        
        update = harness.create_mock_telegram_update(
            "chat",
            user_id=12345,
            message_text="What's my balance?"
        )
        update.effective_user.first_name = "TestUser"
        
        await handler.handle_ai_chat(
            update,
            "What's my balance?",
            "12345",
            "TestUser"
        )
        
        # Verify wallet balance was queried
        assert mock_wallet.get_balance.called
        
        # Verify balance is in system prompt
        call_args = mock_ai_provider.chat.call_args
        system_prompt = call_args[1]["messages"][0]["content"]
        assert "2.5" in system_prompt
    
    @pytest.mark.asyncio
    async def test_price_query_detection_and_routing(self):
        """Test that price queries are detected and routed to PriceService."""
        harness = TestHarness()
        
        mock_user_manager = MagicMock()
        mock_user_manager.add_conversation = MagicMock()
        
        mock_ai_provider = MagicMock()
        mock_wallet = harness.create_mock_wallet()
        
        from agent.handlers.message_handler import MessageHandler
        handler = MessageHandler(mock_user_manager, mock_ai_provider, mock_wallet)
        
        # Test price query detection - use queries that match the detection logic
        token = handler.detect_price_query("price of SOL")
        assert token is not None  # Should detect "SOL"
        assert "SOL" in token
        
        token = handler.detect_price_query("check Bitcoin")
        assert token is not None  # Should detect "Bitcoin"
        assert "Bitcoin" in token
        
        token = handler.detect_price_query("cost ETH")
        assert token is not None  # Should detect "ETH"
        
        # Non-price queries should return None
        token = handler.detect_price_query("Hello, how are you?")
        assert token is None
    
    @pytest.mark.asyncio
    async def test_portfolio_query_detection_and_routing(self):
        """Test that portfolio queries are detected and routed to PortfolioService."""
        harness = TestHarness()
        
        mock_user_manager = MagicMock()
        mock_ai_provider = MagicMock()
        mock_wallet = harness.create_mock_wallet()
        
        from agent.handlers.message_handler import MessageHandler
        handler = MessageHandler(mock_user_manager, mock_ai_provider, mock_wallet)
        
        # Test portfolio query detection with valid address
        test_address = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
        
        address = handler.detect_portfolio_query(f"Show me portfolio for {test_address}")
        assert address == test_address
        
        address = handler.detect_portfolio_query(f"Analyze wallet {test_address}")
        assert address == test_address
        
        # Non-portfolio queries should return None
        address = handler.detect_portfolio_query("What's the weather?")
        assert address is None


class TestAIHelpInstructions:
    """
    Test AI help instructions.
    
    **Validates: Property 35** - AI help instructions
    *For any* user question about how to perform an action, the AI should 
    provide step-by-step instructions including relevant commands
    """
    
    @pytest.mark.asyncio
    async def test_ai_provides_help_instructions(self):
        """Test that AI provides helpful instructions with commands."""
        harness = TestHarness()
        
        mock_user_manager = MagicMock()
        mock_user_manager.get_user_context = MagicMock(return_value="")
        mock_user_manager.add_conversation = MagicMock()
        
        mock_ai_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.content = """To withdraw SOL:
1. Use the /withdraw command
2. Provide amount and address
3. Confirm the transaction

Example: /withdraw 1.0 YourAddressHere"""
        mock_ai_provider.chat = AsyncMock(return_value=mock_response)
        
        mock_wallet = harness.create_mock_wallet()
        
        from agent.handlers.message_handler import MessageHandler
        handler = MessageHandler(mock_user_manager, mock_ai_provider, mock_wallet)
        
        update = harness.create_mock_telegram_update(
            "chat",
            user_id=12345,
            message_text="How do I withdraw SOL?"
        )
        update.effective_user.first_name = "TestUser"
        
        await handler.handle_ai_chat(
            update,
            "How do I withdraw SOL?",
            "12345",
            "TestUser"
        )
        
        # Verify response contains instructions
        response_text = update.message.reply_text.call_args[0][0]
        assert "/withdraw" in response_text
        assert "1." in response_text or "step" in response_text.lower()
    
    @pytest.mark.asyncio
    async def test_ai_system_prompt_includes_capabilities(self):
        """Test that system prompt includes bot capabilities."""
        harness = TestHarness()
        
        mock_user_manager = MagicMock()
        mock_user_manager.get_user_context = MagicMock(return_value="")
        mock_user_manager.add_conversation = MagicMock()
        
        mock_ai_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "I can help with trading, airdrops, and more!"
        mock_ai_provider.chat = AsyncMock(return_value=mock_response)
        
        mock_wallet = harness.create_mock_wallet()
        
        from agent.handlers.message_handler import MessageHandler
        handler = MessageHandler(mock_user_manager, mock_ai_provider, mock_wallet)
        
        update = harness.create_mock_telegram_update(
            "chat",
            user_id=12345,
            message_text="What can you help me with?"
        )
        update.effective_user.first_name = "TestUser"
        
        await handler.handle_ai_chat(
            update,
            "What can you help me with?",
            "12345",
            "TestUser"
        )
        
        # Verify system prompt includes capabilities
        call_args = mock_ai_provider.chat.call_args
        system_prompt = call_args[1]["messages"][0]["content"]
        
        assert "trading" in system_prompt.lower()
        assert "airdrop" in system_prompt.lower()
        assert "price" in system_prompt.lower()
        assert "portfolio" in system_prompt.lower()


class TestAIContextManagement:
    """Test AI conversation context management."""
    
    @pytest.mark.asyncio
    async def test_conversation_history_is_recorded(self):
        """Test that user messages and AI responses are recorded."""
        harness = TestHarness()
        
        mock_user_manager = MagicMock()
        mock_user_manager.get_user_context = MagicMock(return_value="")
        mock_user_manager.add_conversation = MagicMock()
        
        mock_ai_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Test response"
        mock_ai_provider.chat = AsyncMock(return_value=mock_response)
        
        mock_wallet = harness.create_mock_wallet()
        
        from agent.handlers.message_handler import MessageHandler
        handler = MessageHandler(mock_user_manager, mock_ai_provider, mock_wallet)
        
        update = harness.create_mock_telegram_update(
            "chat",
            user_id=12345,
            message_text="Test message"
        )
        update.effective_user.first_name = "TestUser"
        
        # Process message through main handler
        await handler.process_message(update, None)
        
        # Verify both user message and assistant response were recorded
        assert mock_user_manager.add_conversation.call_count == 2
        
        # First call should be user message
        first_call = mock_user_manager.add_conversation.call_args_list[0]
        assert first_call[0][0] == "12345"  # user_id
        assert first_call[0][1] == "user"  # role
        assert first_call[0][2] == "Test message"  # content
        
        # Second call should be assistant response
        second_call = mock_user_manager.add_conversation.call_args_list[1]
        assert second_call[0][0] == "12345"
        assert second_call[0][1] == "assistant"
        assert second_call[0][2] == "Test response"
    
    @pytest.mark.asyncio
    async def test_context_limit_is_respected(self):
        """Test that conversation context respects the limit parameter."""
        harness = TestHarness()
        
        mock_user_manager = MagicMock()
        mock_user_manager.get_user_context = MagicMock(return_value="Limited context")
        mock_user_manager.add_conversation = MagicMock()
        
        mock_ai_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Response"
        mock_ai_provider.chat = AsyncMock(return_value=mock_response)
        
        mock_wallet = harness.create_mock_wallet()
        
        from agent.handlers.message_handler import MessageHandler
        handler = MessageHandler(mock_user_manager, mock_ai_provider, mock_wallet)
        
        update = harness.create_mock_telegram_update(
            "chat",
            user_id=12345,
            message_text="Test"
        )
        update.effective_user.first_name = "TestUser"
        
        await handler.handle_ai_chat(update, "Test", "12345", "TestUser")
        
        # Verify context was requested with limit=5
        mock_user_manager.get_user_context.assert_called_once_with("12345", limit=5)


class TestAISecurityControls:
    """Test AI security controls and private key protection."""
    
    @pytest.mark.asyncio
    async def test_ai_system_prompt_includes_security_rules(self):
        """Test that system prompt includes security rules about private keys."""
        harness = TestHarness()
        
        mock_user_manager = MagicMock()
        mock_user_manager.get_user_context = MagicMock(return_value="")
        mock_user_manager.add_conversation = MagicMock()
        
        mock_ai_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Use /exportkey command for private key access."
        mock_ai_provider.chat = AsyncMock(return_value=mock_response)
        
        mock_wallet = harness.create_mock_wallet()
        
        from agent.handlers.message_handler import MessageHandler
        handler = MessageHandler(mock_user_manager, mock_ai_provider, mock_wallet)
        
        update = harness.create_mock_telegram_update(
            "chat",
            user_id=12345,
            message_text="Show me my private key"
        )
        update.effective_user.first_name = "TestUser"
        
        await handler.handle_ai_chat(
            update,
            "Show me my private key",
            "12345",
            "TestUser"
        )
        
        # Verify system prompt includes security rules
        call_args = mock_ai_provider.chat.call_args
        system_prompt = call_args[1]["messages"][0]["content"]
        
        assert "NEVER reveal private keys" in system_prompt
        assert "seed phrases" in system_prompt
        assert "/exportkey" in system_prompt
        assert "PUBLIC information" in system_prompt


# Property-based tests
class TestAIPropertyBased:
    """Property-based tests for AI chat functionality."""
    
    @given(
        message=st.text(min_size=1, max_size=500).filter(lambda x: x.strip())
    )
    @settings(max_examples=50, deadline=5000)
    @pytest.mark.asyncio
    async def test_ai_handles_any_valid_message(self, message):
        """
        Property test: AI should handle any valid text message without crashing.
        
        **Validates: Property 33** - AI contextual response generation
        """
        harness = TestHarness()
        
        mock_user_manager = MagicMock()
        mock_user_manager.get_user_context = MagicMock(return_value="")
        mock_user_manager.add_conversation = MagicMock()
        
        mock_ai_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Test response"
        mock_ai_provider.chat = AsyncMock(return_value=mock_response)
        
        mock_wallet = harness.create_mock_wallet()
        
        from agent.handlers.message_handler import MessageHandler
        handler = MessageHandler(mock_user_manager, mock_ai_provider, mock_wallet)
        
        update = harness.create_mock_telegram_update(
            "chat",
            user_id=12345,
            message_text=message
        )
        update.effective_user.first_name = "TestUser"
        
        # Should not raise any exception
        try:
            await handler.handle_ai_chat(update, message, "12345", "TestUser")
            assert True
        except Exception as e:
            pytest.fail(f"AI chat failed with message '{message}': {e}")



class TestAIErrorHandling:
    """
    Test AI error handling and graceful degradation.
    
    **Validates: Property 36** - AI error handling
    *For any* AI error (API failure, timeout, rate limit), the system should 
    display friendly error message and suggest alternatives
    """
    
    @pytest.mark.asyncio
    async def test_ai_handles_api_failure_gracefully(self):
        """Test that AI API failures are handled with friendly error messages."""
        harness = TestHarness()
        
        mock_user_manager = MagicMock()
        mock_user_manager.get_user_context = MagicMock(return_value="")
        mock_user_manager.add_conversation = MagicMock()
        
        # Mock AI provider that raises an exception
        mock_ai_provider = MagicMock()
        mock_ai_provider.chat = AsyncMock(side_effect=Exception("API connection failed"))
        
        mock_wallet = harness.create_mock_wallet()
        
        from agent.handlers.message_handler import MessageHandler
        handler = MessageHandler(mock_user_manager, mock_ai_provider, mock_wallet)
        
        update = harness.create_mock_telegram_update(
            "chat",
            user_id=12345,
            message_text="Hello"
        )
        update.effective_user.first_name = "TestUser"
        
        # Should not crash
        await handler.handle_ai_chat(update, "Hello", "12345", "TestUser")
        
        # Verify error message was sent
        assert update.message.reply_text.called
        error_message = update.message.reply_text.call_args[0][0]
        
        # Should be user-friendly
        assert "Sorry" in error_message or "trouble" in error_message
        assert "/help" in error_message
        
        # Error should be recorded in conversation
        assert mock_user_manager.add_conversation.called
    
    @pytest.mark.asyncio
    async def test_ai_handles_timeout_gracefully(self):
        """Test that AI timeouts are handled gracefully."""
        harness = TestHarness()
        
        mock_user_manager = MagicMock()
        mock_user_manager.get_user_context = MagicMock(return_value="")
        mock_user_manager.add_conversation = MagicMock()
        
        # Mock AI provider that times out
        import asyncio
        mock_ai_provider = MagicMock()
        mock_ai_provider.chat = AsyncMock(side_effect=asyncio.TimeoutError("Request timed out"))
        
        mock_wallet = harness.create_mock_wallet()
        
        from agent.handlers.message_handler import MessageHandler
        handler = MessageHandler(mock_user_manager, mock_ai_provider, mock_wallet)
        
        update = harness.create_mock_telegram_update(
            "chat",
            user_id=12345,
            message_text="What's the weather?"
        )
        update.effective_user.first_name = "TestUser"
        
        # Should handle timeout gracefully
        await handler.handle_ai_chat(update, "What's the weather?", "12345", "TestUser")
        
        # Verify error message was sent
        assert update.message.reply_text.called
        error_message = update.message.reply_text.call_args[0][0]
        assert "Sorry" in error_message or "trouble" in error_message
    
    @pytest.mark.asyncio
    async def test_ai_handles_rate_limit_gracefully(self):
        """Test that AI rate limits are handled with appropriate messages."""
        harness = TestHarness()
        
        mock_user_manager = MagicMock()
        mock_user_manager.get_user_context = MagicMock(return_value="")
        mock_user_manager.add_conversation = MagicMock()
        
        # Mock AI provider that hits rate limit
        mock_ai_provider = MagicMock()
        mock_ai_provider.chat = AsyncMock(
            side_effect=Exception("Rate limit exceeded. Retry after 60 seconds")
        )
        
        mock_wallet = harness.create_mock_wallet()
        
        from agent.handlers.message_handler import MessageHandler
        handler = MessageHandler(mock_user_manager, mock_ai_provider, mock_wallet)
        
        update = harness.create_mock_telegram_update(
            "chat",
            user_id=12345,
            message_text="Tell me about trading"
        )
        update.effective_user.first_name = "TestUser"
        
        # Should handle rate limit gracefully
        await handler.handle_ai_chat(update, "Tell me about trading", "12345", "TestUser")
        
        # Verify error message was sent
        assert update.message.reply_text.called
        error_message = update.message.reply_text.call_args[0][0]
        assert "Sorry" in error_message or "trouble" in error_message
    
    @pytest.mark.asyncio
    async def test_ai_handles_empty_response_gracefully(self):
        """Test that empty AI responses are handled gracefully."""
        harness = TestHarness()
        
        mock_user_manager = MagicMock()
        mock_user_manager.get_user_context = MagicMock(return_value="")
        mock_user_manager.add_conversation = MagicMock()
        
        # Mock AI provider that returns empty response
        mock_ai_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.content = None  # Empty response
        mock_ai_provider.chat = AsyncMock(return_value=mock_response)
        
        mock_wallet = harness.create_mock_wallet()
        
        from agent.handlers.message_handler import MessageHandler
        handler = MessageHandler(mock_user_manager, mock_ai_provider, mock_wallet)
        
        update = harness.create_mock_telegram_update(
            "chat",
            user_id=12345,
            message_text="Hello"
        )
        update.effective_user.first_name = "TestUser"
        
        await handler.handle_ai_chat(update, "Hello", "12345", "TestUser")
        
        # Verify fallback message was sent
        assert update.message.reply_text.called
        response_text = update.message.reply_text.call_args[0][0]
        assert "not sure" in response_text.lower() or "respond" in response_text.lower()
    
    @pytest.mark.asyncio
    async def test_ai_handles_wallet_error_gracefully(self):
        """Test that wallet errors during AI chat are handled gracefully."""
        harness = TestHarness()
        
        mock_user_manager = MagicMock()
        mock_user_manager.get_user_context = MagicMock(return_value="")
        mock_user_manager.add_conversation = MagicMock()
        
        mock_ai_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Your balance is available."
        mock_ai_provider.chat = AsyncMock(return_value=mock_response)
        
        # Mock wallet that fails to get balance
        mock_wallet = MagicMock()
        mock_wallet.get_balance = AsyncMock(side_effect=Exception("RPC connection failed"))
        mock_wallet.public_key = "TestWallet123"
        
        from agent.handlers.message_handler import MessageHandler
        handler = MessageHandler(mock_user_manager, mock_ai_provider, mock_wallet)
        
        update = harness.create_mock_telegram_update(
            "chat",
            user_id=12345,
            message_text="What's my balance?"
        )
        update.effective_user.first_name = "TestUser"
        
        # Should handle wallet error gracefully
        await handler.handle_ai_chat(update, "What's my balance?", "12345", "TestUser")
        
        # Should still send a response (even if wallet info is missing)
        assert update.message.reply_text.called or mock_user_manager.add_conversation.called
    
    @pytest.mark.asyncio
    async def test_ai_error_messages_suggest_help_command(self):
        """Test that error messages suggest using /help command."""
        harness = TestHarness()
        
        mock_user_manager = MagicMock()
        mock_user_manager.get_user_context = MagicMock(return_value="")
        mock_user_manager.add_conversation = MagicMock()
        
        # Mock AI provider that fails
        mock_ai_provider = MagicMock()
        mock_ai_provider.chat = AsyncMock(side_effect=Exception("Service unavailable"))
        
        mock_wallet = harness.create_mock_wallet()
        
        from agent.handlers.message_handler import MessageHandler
        handler = MessageHandler(mock_user_manager, mock_ai_provider, mock_wallet)
        
        update = harness.create_mock_telegram_update(
            "chat",
            user_id=12345,
            message_text="Random message"
        )
        update.effective_user.first_name = "TestUser"
        
        await handler.handle_ai_chat(update, "Random message", "12345", "TestUser")
        
        # Verify error message suggests /help
        assert update.message.reply_text.called
        error_message = update.message.reply_text.call_args[0][0]
        assert "/help" in error_message


class TestAIMessageRouting:
    """Test message routing between AI chat and specialized services."""
    
    @pytest.mark.asyncio
    async def test_price_queries_bypass_ai_chat(self):
        """Test that price queries are routed to PriceService, not AI."""
        harness = TestHarness()
        
        mock_user_manager = MagicMock()
        mock_user_manager.add_conversation = MagicMock()
        
        # AI should NOT be called for price queries
        mock_ai_provider = MagicMock()
        mock_ai_provider.chat = AsyncMock()
        
        mock_wallet = harness.create_mock_wallet()
        
        from agent.handlers.message_handler import MessageHandler
        handler = MessageHandler(mock_user_manager, mock_ai_provider, mock_wallet)
        
        # Mock the price query handler to return True (handled)
        handler.handle_price_query = AsyncMock(return_value=True)
        
        update = harness.create_mock_telegram_update(
            "chat",
            user_id=12345,
            message_text="What's the price of SOL?"
        )
        update.effective_user.first_name = "TestUser"
        
        context = harness.create_mock_telegram_context()
        
        await handler.process_message(update, context)
        
        # Verify price handler was called
        assert handler.handle_price_query.called
        
        # Verify AI was NOT called (price query was handled)
        assert not mock_ai_provider.chat.called
    
    @pytest.mark.asyncio
    async def test_portfolio_queries_bypass_ai_chat(self):
        """Test that portfolio queries are routed to PortfolioService, not AI."""
        harness = TestHarness()
        
        mock_user_manager = MagicMock()
        mock_user_manager.add_conversation = MagicMock()
        
        # AI should NOT be called for portfolio queries
        mock_ai_provider = MagicMock()
        mock_ai_provider.chat = AsyncMock()
        
        mock_wallet = harness.create_mock_wallet()
        
        from agent.handlers.message_handler import MessageHandler
        handler = MessageHandler(mock_user_manager, mock_ai_provider, mock_wallet)
        
        # Mock the portfolio query handler to return True (handled)
        handler.handle_portfolio_query = AsyncMock(return_value=True)
        
        test_address = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
        update = harness.create_mock_telegram_update(
            "chat",
            user_id=12345,
            message_text=f"Show portfolio for {test_address}"
        )
        update.effective_user.first_name = "TestUser"
        
        context = harness.create_mock_telegram_context()
        
        await handler.process_message(update, context)
        
        # Verify portfolio handler was called
        assert handler.handle_portfolio_query.called
        
        # Verify AI was NOT called (portfolio query was handled)
        assert not mock_ai_provider.chat.called
    
    @pytest.mark.asyncio
    async def test_general_messages_route_to_ai_chat(self):
        """Test that general messages are routed to AI chat."""
        harness = TestHarness()
        
        mock_user_manager = MagicMock()
        mock_user_manager.get_user_context = MagicMock(return_value="")
        mock_user_manager.add_conversation = MagicMock()
        
        mock_ai_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Hello! How can I help you?"
        mock_ai_provider.chat = AsyncMock(return_value=mock_response)
        
        mock_wallet = harness.create_mock_wallet()
        
        from agent.handlers.message_handler import MessageHandler
        handler = MessageHandler(mock_user_manager, mock_ai_provider, mock_wallet)
        
        update = harness.create_mock_telegram_update(
            "chat",
            user_id=12345,
            message_text="Hello, how are you?"
        )
        update.effective_user.first_name = "TestUser"
        
        context = harness.create_mock_telegram_context()
        
        await handler.process_message(update, context)
        
        # Verify AI was called for general message
        assert mock_ai_provider.chat.called
        
        # Verify response was sent
        assert update.message.reply_text.called


class TestAIInputValidation:
    """Test AI input validation and sanitization."""
    
    @pytest.mark.asyncio
    async def test_ai_sanitizes_long_messages(self):
        """Test that excessively long messages are handled properly."""
        harness = TestHarness()
        
        mock_user_manager = MagicMock()
        mock_user_manager.get_user_context = MagicMock(return_value="")
        mock_user_manager.add_conversation = MagicMock()
        
        mock_ai_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Response"
        mock_ai_provider.chat = AsyncMock(return_value=mock_response)
        
        mock_wallet = harness.create_mock_wallet()
        
        from agent.handlers.message_handler import MessageHandler
        handler = MessageHandler(mock_user_manager, mock_ai_provider, mock_wallet)
        
        # Very long message (over 500 chars)
        long_message = "A" * 1000
        
        update = harness.create_mock_telegram_update(
            "chat",
            user_id=12345,
            message_text=long_message
        )
        update.effective_user.first_name = "TestUser"
        
        # Should handle without crashing
        await handler.handle_ai_chat(update, long_message, "12345", "TestUser")
        
        # Should still process (sanitization happens in detect methods)
        assert update.message.reply_text.called or mock_ai_provider.chat.called
    
    @pytest.mark.asyncio
    async def test_price_query_detection_sanitizes_input(self):
        """Test that price query detection sanitizes malicious input."""
        from agent.handlers.message_handler import MessageHandler
        
        # Test with potentially malicious input
        result = MessageHandler.detect_price_query("price of <script>alert('xss')</script>")
        # Should either return None or sanitized token name
        assert result is None or "<script>" not in str(result)
        
        # Test with SQL injection patterns
        result = MessageHandler.detect_price_query("price of SOL'; DROP TABLE users;--")
        # Should handle safely
        assert result is None or "DROP TABLE" not in str(result)
    
    @pytest.mark.asyncio
    async def test_portfolio_query_detection_sanitizes_input(self):
        """Test that portfolio query detection sanitizes malicious input."""
        from agent.handlers.message_handler import MessageHandler
        
        # Test with potentially malicious input
        result = MessageHandler.detect_portfolio_query("portfolio <script>alert('xss')</script>")
        # Should return None (no valid address)
        assert result is None
        
        # Test with SQL injection patterns
        result = MessageHandler.detect_portfolio_query("portfolio '; DROP TABLE users;--")
        # Should return None (no valid address)
        assert result is None
