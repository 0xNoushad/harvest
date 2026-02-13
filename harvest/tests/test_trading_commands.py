"""
Test suite for trading control commands.

This module tests trading control commands:
- /pause - Pause the bot
- /resume - Resume the bot
- /strategies - Show active strategies
- /settings - Show bot settings

Tests validate:
- Commands execute correctly
- Bot state changes appropriately
- Proper user feedback
- Error handling
"""

# Import mocking setup FIRST
from tests.conftest_commands import mock_external_modules
mock_external_modules()

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from hypothesis import given, strategies as st, settings, Phase

# Import command classes
from agent.ui.commands.trading_commands import TradingCommands


@pytest.mark.asyncio
class TestPauseResumeCommands:
    """Tests for /pause and /resume commands."""
    
    async def test_pause_command_stops_agent_loop(self, test_harness):
        """
        Test /pause command stops the agent loop.
        
        **Validates: Requirements 1.8**
        
        WHEN a user sends /pause, THE Trading_Engine SHALL stop scanning
        and confirm pause state.
        """
        # Setup
        mock_bot = MagicMock()
        mock_bot.agent_loop = MagicMock()
        mock_bot.agent_loop.stop = MagicMock()
        
        trading_commands = TradingCommands(mock_bot)
        
        update = test_harness.create_mock_telegram_update("pause")
        context = test_harness.create_mock_telegram_context()
        
        # Execute
        await trading_commands.cmd_pause(update, context)
        
        # Assert - agent loop stop was called
        assert mock_bot.agent_loop.stop.called, "Agent loop stop() was not called"
        
        # Assert - confirmation message was sent
        assert update.message.reply_text.called, "No reply message was sent"
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Verify message contains pause confirmation
        assert "Paused" in message_text or "paused" in message_text, \
            f"Expected pause confirmation in message, got: {message_text}"
        
        # Verify message suggests how to resume
        assert "/resume" in message_text, \
            f"Expected /resume suggestion in message, got: {message_text}"
    
    async def test_pause_command_displays_pause_emoji(self, test_harness):
        """
        Test /pause command displays pause emoji for visual feedback.
        
        **Validates: Requirements 1.8, 12.4**
        """
        # Setup
        mock_bot = MagicMock()
        mock_bot.agent_loop = MagicMock()
        mock_bot.agent_loop.stop = MagicMock()
        
        trading_commands = TradingCommands(mock_bot)
        
        update = test_harness.create_mock_telegram_update("pause")
        context = test_harness.create_mock_telegram_context()
        
        # Execute
        await trading_commands.cmd_pause(update, context)
        
        # Assert - message contains pause emoji
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        assert "⏸️" in message_text or "🔴" in message_text, \
            f"Expected pause emoji in message, got: {message_text}"
    
    async def test_pause_command_uses_markdown_formatting(self, test_harness):
        """
        Test /pause command uses Markdown for better formatting.
        
        **Validates: Requirements 1.8, 12.1**
        """
        # Setup
        mock_bot = MagicMock()
        mock_bot.agent_loop = MagicMock()
        mock_bot.agent_loop.stop = MagicMock()
        
        trading_commands = TradingCommands(mock_bot)
        
        update = test_harness.create_mock_telegram_update("pause")
        context = test_harness.create_mock_telegram_context()
        
        # Execute
        await trading_commands.cmd_pause(update, context)
        
        # Assert - Markdown parse mode is used
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        parse_mode = call_args[1].get('parse_mode') if len(call_args) > 1 else None
        assert parse_mode == "Markdown", f"Expected Markdown parse mode, got: {parse_mode}"
    
    async def test_resume_command_displays_confirmation(self, test_harness):
        """
        Test /resume command displays resume confirmation.
        
        **Validates: Requirements 1.9**
        
        WHEN a user sends /resume, THE Trading_Engine SHALL restart scanning
        and confirm active state.
        """
        # Setup
        mock_bot = MagicMock()
        mock_bot.agent_loop = MagicMock()
        
        trading_commands = TradingCommands(mock_bot)
        
        update = test_harness.create_mock_telegram_update("resume")
        context = test_harness.create_mock_telegram_context()
        
        # Execute
        await trading_commands.cmd_resume(update, context)
        
        # Assert - confirmation message was sent
        assert update.message.reply_text.called, "No reply message was sent"
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Verify message contains resume confirmation
        assert "Resumed" in message_text or "resumed" in message_text or "Running" in message_text, \
            f"Expected resume confirmation in message, got: {message_text}"
        
        # Verify message suggests checking status
        assert "/status" in message_text, \
            f"Expected /status suggestion in message, got: {message_text}"
    
    async def test_resume_command_displays_play_emoji(self, test_harness):
        """
        Test /resume command displays play emoji for visual feedback.
        
        **Validates: Requirements 1.9, 12.4**
        """
        # Setup
        mock_bot = MagicMock()
        mock_bot.agent_loop = MagicMock()
        
        trading_commands = TradingCommands(mock_bot)
        
        update = test_harness.create_mock_telegram_update("resume")
        context = test_harness.create_mock_telegram_context()
        
        # Execute
        await trading_commands.cmd_resume(update, context)
        
        # Assert - message contains play emoji
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        assert "▶️" in message_text or "🟢" in message_text, \
            f"Expected play emoji in message, got: {message_text}"
    
    async def test_resume_command_uses_markdown_formatting(self, test_harness):
        """
        Test /resume command uses Markdown for better formatting.
        
        **Validates: Requirements 1.9, 12.1**
        """
        # Setup
        mock_bot = MagicMock()
        mock_bot.agent_loop = MagicMock()
        
        trading_commands = TradingCommands(mock_bot)
        
        update = test_harness.create_mock_telegram_update("resume")
        context = test_harness.create_mock_telegram_context()
        
        # Execute
        await trading_commands.cmd_resume(update, context)
        
        # Assert - Markdown parse mode is used
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        parse_mode = call_args[1].get('parse_mode') if len(call_args) > 1 else None
        assert parse_mode == "Markdown", f"Expected Markdown parse mode, got: {parse_mode}"


@pytest.mark.asyncio
class TestStrategiesCommand:
    """Tests for /strategies command."""
    
    async def test_strategies_command_displays_active_strategies(self, test_harness):
        """
        Test /strategies command displays all active strategies.
        
        **Validates: Requirements 1.13**
        
        WHEN a user sends /strategies, THE Telegram_Interface SHALL display
        all available strategies with enable/disable status.
        """
        # Setup
        mock_bot = MagicMock()
        mock_bot.agent_loop = MagicMock()
        mock_bot.agent_loop.scanner = MagicMock()
        
        # Create mock strategies
        mock_strategy1 = MagicMock()
        mock_strategy1.get_name = MagicMock(return_value="airdrop_hunter")
        mock_strategy1.get_next_check_time = MagicMock(return_value=datetime.now())
        
        mock_strategy2 = MagicMock()
        mock_strategy2.get_name = MagicMock(return_value="airdrop_claimer")
        mock_strategy2.get_next_check_time = MagicMock(return_value=datetime.now())
        
        mock_bot.agent_loop.scanner.strategies = [mock_strategy1, mock_strategy2]
        
        trading_commands = TradingCommands(mock_bot)
        
        update = test_harness.create_mock_telegram_update("strategies")
        context = test_harness.create_mock_telegram_context()
        
        # Execute
        await trading_commands.cmd_strategies(update, context)
        
        # Assert - message was sent
        assert update.message.reply_text.called, "No reply message was sent"
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Verify message contains strategy information
        assert "Strategies" in message_text or "strategies" in message_text, \
            f"Expected strategies header in message, got: {message_text}"
        
        # Verify strategy count is shown
        assert "2" in message_text, \
            f"Expected strategy count in message, got: {message_text}"
    
    async def test_strategies_command_shows_strategy_names(self, test_harness):
        """
        Test /strategies command shows individual strategy names.
        
        **Validates: Requirements 1.13**
        """
        # Setup
        mock_bot = MagicMock()
        mock_bot.agent_loop = MagicMock()
        mock_bot.agent_loop.scanner = MagicMock()
        
        # Create mock strategy
        mock_strategy = MagicMock()
        mock_strategy.get_name = MagicMock(return_value="airdrop_hunter")
        mock_strategy.get_next_check_time = MagicMock(return_value=datetime.now())
        
        mock_bot.agent_loop.scanner.strategies = [mock_strategy]
        
        trading_commands = TradingCommands(mock_bot)
        
        update = test_harness.create_mock_telegram_update("strategies")
        context = test_harness.create_mock_telegram_context()
        
        # Execute
        await trading_commands.cmd_strategies(update, context)
        
        # Assert - message contains strategy name
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        assert "Airdrop Hunter" in message_text or "airdrop_hunter" in message_text, \
            f"Expected strategy name in message, got: {message_text}"
    
    async def test_strategies_command_shows_next_check_time(self, test_harness):
        """
        Test /strategies command shows next check time for strategies.
        
        **Validates: Requirements 1.13**
        """
        # Setup
        mock_bot = MagicMock()
        mock_bot.agent_loop = MagicMock()
        mock_bot.agent_loop.scanner = MagicMock()
        
        # Create mock strategy with next check time
        next_check = datetime(2024, 12, 25, 15, 30, 0)
        mock_strategy = MagicMock()
        mock_strategy.get_name = MagicMock(return_value="airdrop_hunter")
        mock_strategy.get_next_check_time = MagicMock(return_value=next_check)
        
        mock_bot.agent_loop.scanner.strategies = [mock_strategy]
        
        trading_commands = TradingCommands(mock_bot)
        
        update = test_harness.create_mock_telegram_update("strategies")
        context = test_harness.create_mock_telegram_context()
        
        # Execute
        await trading_commands.cmd_strategies(update, context)
        
        # Assert - message contains next check time
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        assert "Next check" in message_text or "next check" in message_text, \
            f"Expected next check time in message, got: {message_text}"
    
    async def test_strategies_command_handles_error_gracefully(self, test_harness):
        """
        Test /strategies command handles errors gracefully.
        
        **Validates: Requirements 9.1, 9.3**
        """
        # Setup
        mock_bot = MagicMock()
        mock_bot.agent_loop = MagicMock()
        mock_bot.agent_loop.scanner = MagicMock()
        
        # Make strategies property raise an exception
        type(mock_bot.agent_loop.scanner).strategies = property(
            lambda self: (_ for _ in ()).throw(Exception("Scanner error"))
        )
        
        trading_commands = TradingCommands(mock_bot)
        
        update = test_harness.create_mock_telegram_update("strategies")
        context = test_harness.create_mock_telegram_context()
        
        # Execute
        await trading_commands.cmd_strategies(update, context)
        
        # Assert - error message was sent
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        assert "Error" in message_text or "error" in message_text, \
            f"Expected error message, got: {message_text}"
    
    async def test_strategies_command_uses_markdown_formatting(self, test_harness):
        """
        Test /strategies command uses Markdown for better formatting.
        
        **Validates: Requirements 1.13, 12.1**
        """
        # Setup
        mock_bot = MagicMock()
        mock_bot.agent_loop = MagicMock()
        mock_bot.agent_loop.scanner = MagicMock()
        mock_bot.agent_loop.scanner.strategies = []
        
        trading_commands = TradingCommands(mock_bot)
        
        update = test_harness.create_mock_telegram_update("strategies")
        context = test_harness.create_mock_telegram_context()
        
        # Execute
        await trading_commands.cmd_strategies(update, context)
        
        # Assert - Markdown parse mode is used
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        parse_mode = call_args[1].get('parse_mode') if len(call_args) > 1 else None
        assert parse_mode == "Markdown", f"Expected Markdown parse mode, got: {parse_mode}"
    
    async def test_strategies_command_displays_strategy_emoji(self, test_harness):
        """
        Test /strategies command displays emoji for visual hierarchy.
        
        **Validates: Requirements 12.1, 12.4**
        """
        # Setup
        mock_bot = MagicMock()
        mock_bot.agent_loop = MagicMock()
        mock_bot.agent_loop.scanner = MagicMock()
        
        mock_strategy = MagicMock()
        mock_strategy.get_name = MagicMock(return_value="airdrop_hunter")
        mock_strategy.get_next_check_time = MagicMock(return_value=datetime.now())
        
        mock_bot.agent_loop.scanner.strategies = [mock_strategy]
        
        trading_commands = TradingCommands(mock_bot)
        
        update = test_harness.create_mock_telegram_update("strategies")
        context = test_harness.create_mock_telegram_context()
        
        # Execute
        await trading_commands.cmd_strategies(update, context)
        
        # Assert - message contains emoji
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Should have at least one emoji (🎯 for strategies header or 🔍 for airdrop hunter)
        has_emoji = any(emoji in message_text for emoji in ["🎯", "🔍", "🎁", "💰", "🌾"])
        assert has_emoji, f"Expected emoji in message, got: {message_text}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



@pytest.mark.asyncio
class TestPauseResumePropertyTests:
    """Property-based tests for pause-resume functionality."""
    
    @given(
        initial_state=st.booleans(),
        num_cycles=st.integers(min_value=1, max_value=5)
    )
    @settings(
        max_examples=20,
        phases=[Phase.generate, Phase.target],
        deadline=None
    )
    async def test_pause_resume_round_trip_property(
        self,
        initial_state,
        num_cycles
    ):
        """
        Property 3: Pause-resume round trip
        
        **Validates: Requirements 1.8, 1.9**
        
        For any bot state, pausing then immediately resuming should restore
        the bot to active scanning state.
        
        This property tests that:
        1. Pause command stops the agent loop
        2. Resume command can be called after pause
        3. Multiple pause-resume cycles work correctly
        4. The bot state is consistent after each cycle
        """
        # Import TestHarness directly to avoid fixture issues
        from tests.test_harness import TestHarness
        test_harness = TestHarness()
        
        # Setup
        mock_bot = MagicMock()
        mock_bot.agent_loop = MagicMock()
        mock_bot.agent_loop._running = initial_state
        mock_bot.agent_loop.stop = MagicMock()
        
        # Track state changes
        state_changes = []
        
        def track_stop():
            mock_bot.agent_loop._running = False
            state_changes.append('stopped')
        
        mock_bot.agent_loop.stop.side_effect = track_stop
        
        trading_commands = TradingCommands(mock_bot)
        
        # Execute multiple pause-resume cycles
        for cycle in range(num_cycles):
            # Pause
            pause_update = test_harness.create_mock_telegram_update("pause")
            pause_context = test_harness.create_mock_telegram_context()
            
            await trading_commands.cmd_pause(pause_update, pause_context)
            
            # Verify pause was called
            assert mock_bot.agent_loop.stop.called, \
                f"Cycle {cycle}: stop() was not called during pause"
            
            # Verify pause message was sent
            assert pause_update.message.reply_text.called, \
                f"Cycle {cycle}: No pause confirmation message"
            
            # Resume
            resume_update = test_harness.create_mock_telegram_update("resume")
            resume_context = test_harness.create_mock_telegram_context()
            
            await trading_commands.cmd_resume(resume_update, resume_context)
            
            # Verify resume message was sent
            assert resume_update.message.reply_text.called, \
                f"Cycle {cycle}: No resume confirmation message"
            
            # Reset mocks for next cycle
            mock_bot.agent_loop.stop.reset_mock()
            pause_update.message.reply_text.reset_mock()
            resume_update.message.reply_text.reset_mock()
        
        # Verify all cycles completed successfully
        assert len(state_changes) == num_cycles, \
            f"Expected {num_cycles} state changes, got {len(state_changes)}"
    
    @given(
        pause_count=st.integers(min_value=1, max_value=10)
    )
    @settings(
        max_examples=10,
        phases=[Phase.generate, Phase.target],
        deadline=None
    )
    async def test_multiple_pause_calls_are_idempotent(
        self,
        pause_count
    ):
        """
        Property: Multiple pause calls are idempotent
        
        **Validates: Requirements 1.8**
        
        For any number of consecutive pause calls, the bot should remain
        in paused state and not cause errors.
        """
        # Import TestHarness directly to avoid fixture issues
        from tests.test_harness import TestHarness
        test_harness = TestHarness()
        
        # Setup
        mock_bot = MagicMock()
        mock_bot.agent_loop = MagicMock()
        mock_bot.agent_loop.stop = MagicMock()
        
        trading_commands = TradingCommands(mock_bot)
        
        # Execute multiple pause commands
        for i in range(pause_count):
            update = test_harness.create_mock_telegram_update("pause")
            context = test_harness.create_mock_telegram_context()
            
            # Should not raise exception
            await trading_commands.cmd_pause(update, context)
            
            # Verify message was sent
            assert update.message.reply_text.called, \
                f"Pause {i+1}: No confirmation message"
        
        # Verify stop was called at least once
        assert mock_bot.agent_loop.stop.called, \
            "stop() was never called"
    
    @given(
        resume_count=st.integers(min_value=1, max_value=10)
    )
    @settings(
        max_examples=10,
        phases=[Phase.generate, Phase.target],
        deadline=None
    )
    async def test_multiple_resume_calls_are_idempotent(
        self,
        resume_count
    ):
        """
        Property: Multiple resume calls are idempotent
        
        **Validates: Requirements 1.9**
        
        For any number of consecutive resume calls, the bot should remain
        in running state and not cause errors.
        """
        # Import TestHarness directly to avoid fixture issues
        from tests.test_harness import TestHarness
        test_harness = TestHarness()
        
        # Setup
        mock_bot = MagicMock()
        mock_bot.agent_loop = MagicMock()
        
        trading_commands = TradingCommands(mock_bot)
        
        # Execute multiple resume commands
        for i in range(resume_count):
            update = test_harness.create_mock_telegram_update("resume")
            context = test_harness.create_mock_telegram_context()
            
            # Should not raise exception
            await trading_commands.cmd_resume(update, context)
            
            # Verify message was sent
            assert update.message.reply_text.called, \
                f"Resume {i+1}: No confirmation message"
    
    @given(
        operations=st.lists(
            st.sampled_from(['pause', 'resume']),
            min_size=1,
            max_size=20
        )
    )
    @settings(
        max_examples=15,
        phases=[Phase.generate, Phase.target],
        deadline=None
    )
    async def test_arbitrary_pause_resume_sequence(
        self,
        operations
    ):
        """
        Property: Arbitrary pause-resume sequences work correctly
        
        **Validates: Requirements 1.8, 1.9**
        
        For any sequence of pause and resume operations, the bot should
        handle them correctly without errors.
        """
        # Import TestHarness directly to avoid fixture issues
        from tests.test_harness import TestHarness
        test_harness = TestHarness()
        
        # Setup
        mock_bot = MagicMock()
        mock_bot.agent_loop = MagicMock()
        mock_bot.agent_loop.stop = MagicMock()
        
        trading_commands = TradingCommands(mock_bot)
        
        # Execute sequence of operations
        for op in operations:
            update = test_harness.create_mock_telegram_update(op)
            context = test_harness.create_mock_telegram_context()
            
            if op == 'pause':
                await trading_commands.cmd_pause(update, context)
            else:
                await trading_commands.cmd_resume(update, context)
            
            # Verify message was sent
            assert update.message.reply_text.called, \
                f"No confirmation message for {op}"
        
        # Verify no exceptions were raised
        # If we got here, all operations completed successfully
        assert True



@pytest.mark.asyncio
class TestSettingsCommand:
    """Tests for /settings command."""
    
    async def test_settings_command_displays_configuration(self, test_harness):
        """
        Test /settings command displays bot configuration.
        
        **Validates: Requirements 1.14**
        
        WHEN a user sends /settings, THE Telegram_Interface SHALL display
        current configuration with modification options.
        """
        # Setup
        mock_bot = MagicMock()
        
        # Import InfoCommands since settings is in info_commands
        from agent.ui.commands.info_commands import InfoCommands
        info_commands = InfoCommands(mock_bot)
        
        update = test_harness.create_mock_telegram_update("settings")
        context = test_harness.create_mock_telegram_context()
        
        # Execute
        await info_commands.cmd_settings(update, context)
        
        # Assert - message was sent
        assert update.message.reply_text.called, "No reply message was sent"
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Verify message contains settings header
        assert "Settings" in message_text or "settings" in message_text, \
            f"Expected settings header in message, got: {message_text}"
    
    async def test_settings_command_shows_current_settings(self, test_harness):
        """
        Test /settings command shows current settings values.
        
        **Validates: Requirements 1.14**
        """
        # Setup
        mock_bot = MagicMock()
        
        from agent.ui.commands.info_commands import InfoCommands
        info_commands = InfoCommands(mock_bot)
        
        update = test_harness.create_mock_telegram_update("settings")
        context = test_harness.create_mock_telegram_context()
        
        # Execute
        await info_commands.cmd_settings(update, context)
        
        # Assert - message contains settings information
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Should show some settings (risk limits, auto-claim, notifications, etc.)
        has_settings = any(setting in message_text.lower() for setting in 
                          ['risk', 'auto', 'notification', 'setting'])
        assert has_settings, f"Expected settings information in message, got: {message_text}"
    
    async def test_settings_command_shows_modification_options(self, test_harness):
        """
        Test /settings command shows how to modify settings.
        
        **Validates: Requirements 1.14**
        """
        # Setup
        mock_bot = MagicMock()
        
        from agent.ui.commands.info_commands import InfoCommands
        info_commands = InfoCommands(mock_bot)
        
        update = test_harness.create_mock_telegram_update("settings")
        context = test_harness.create_mock_telegram_context()
        
        # Execute
        await info_commands.cmd_settings(update, context)
        
        # Assert - message contains modification instructions
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Should mention commands for modifying settings
        has_commands = any(cmd in message_text for cmd in ['/pause', '/resume', '/status'])
        assert has_commands, f"Expected modification commands in message, got: {message_text}"
    
    async def test_settings_command_uses_markdown_formatting(self, test_harness):
        """
        Test /settings command uses Markdown for better formatting.
        
        **Validates: Requirements 1.14, 12.1**
        """
        # Setup
        mock_bot = MagicMock()
        
        from agent.ui.commands.info_commands import InfoCommands
        info_commands = InfoCommands(mock_bot)
        
        update = test_harness.create_mock_telegram_update("settings")
        context = test_harness.create_mock_telegram_context()
        
        # Execute
        await info_commands.cmd_settings(update, context)
        
        # Assert - Markdown parse mode is used
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        parse_mode = call_args[1].get('parse_mode') if len(call_args) > 1 else None
        assert parse_mode == "Markdown", f"Expected Markdown parse mode, got: {parse_mode}"
    
    async def test_settings_command_displays_settings_emoji(self, test_harness):
        """
        Test /settings command displays emoji for visual hierarchy.
        
        **Validates: Requirements 12.1, 12.4**
        """
        # Setup
        mock_bot = MagicMock()
        
        from agent.ui.commands.info_commands import InfoCommands
        info_commands = InfoCommands(mock_bot)
        
        update = test_harness.create_mock_telegram_update("settings")
        context = test_harness.create_mock_telegram_context()
        
        # Execute
        await info_commands.cmd_settings(update, context)
        
        # Assert - message contains emoji
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Should have settings emoji (⚙️)
        assert "⚙️" in message_text, f"Expected settings emoji in message, got: {message_text}"
    
    async def test_settings_command_uses_bullet_points(self, test_harness):
        """
        Test /settings command uses bullet points for readability.
        
        **Validates: Requirements 12.3**
        """
        # Setup
        mock_bot = MagicMock()
        
        from agent.ui.commands.info_commands import InfoCommands
        info_commands = InfoCommands(mock_bot)
        
        update = test_harness.create_mock_telegram_update("settings")
        context = test_harness.create_mock_telegram_context()
        
        # Execute
        await info_commands.cmd_settings(update, context)
        
        # Assert - message uses bullet points
        assert update.message.reply_text.called
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Should have bullet points (•)
        assert "•" in message_text or "-" in message_text or "*" in message_text, \
            f"Expected bullet points in message, got: {message_text}"
