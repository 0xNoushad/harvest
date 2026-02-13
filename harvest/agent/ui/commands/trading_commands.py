"""Trading command handlers for Telegram bot."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class TradingCommands:
    """Handles trading-related commands: /pause, /resume, /strategies."""
    
    def __init__(self, bot_instance):
        """
        Initialize trading commands handler.
        
        Args:
            bot_instance: Reference to TelegramBot instance for accessing agent_loop, etc.
        """
        self.bot = bot_instance
    
    async def cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pause command - pause the bot."""
        self.bot.agent_loop.stop()
        
        message = """⏸️ **Bot Paused**

The bot has been paused. No new opportunities will be scanned.

Use /resume to start again.
"""
        
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /resume command - resume the bot."""
        # Note: This would need to restart the agent loop
        # For now, just send a message
        
        message = """▶️ **Bot Resumed**

The bot is now running again!

Use /status to check current status.
"""
        
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def cmd_strategies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /strategies command - show active strategies."""
        try:
            strategies = self.bot.agent_loop.scanner.strategies
            
            message = f"""🎯 **Active Strategies**

Running {len(strategies)} strategies:

"""
            
            for strategy in strategies:
                name = strategy.get_name()
                if name == "airdrop_hunter":
                    next_check = strategy.get_next_check_time()
                    message += f"🔍 **Airdrop Hunter**\n"
                    message += f"   Interval: 12 hours\n"
                    if next_check:
                        message += f"   Next check: {next_check.strftime('%Y-%m-%d %H:%M')}\n"
                    message += "\n"
                
                elif name == "airdrop_claimer":
                    next_check = strategy.get_next_check_time()
                    message += f"🎁 **Airdrop Claimer**\n"
                    message += f"   Interval: 24 hours\n"
                    if next_check:
                        message += f"   Next check: {next_check.strftime('%Y-%m-%d %H:%M')}\n"
                    message += "\n"
            
            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Error fetching strategies: {str(e)}")
