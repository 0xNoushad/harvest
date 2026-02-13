"""Callback handler for inline button interactions."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from .base_handler import BaseHandler

logger = logging.getLogger(__name__)


class CallbackHandler(BaseHandler):
    """Handles inline button callbacks."""
    
    async def handle_button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks."""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        # Route to appropriate handler based on callback data
        if callback_data.startswith("fee_"):
            await self._handle_fee_callback(query, callback_data)
        elif callback_data.startswith("bot_"):
            await self._handle_bot_control_callback(query, callback_data)
        elif callback_data.startswith("menu_"):
            await self._handle_menu_callback(query, callback_data)
        else:
            await query.edit_message_text("Action not implemented yet.")
    
    async def _handle_fee_callback(self, query, callback_data: str):
        """Handle fee-related button callbacks."""
        if callback_data == "fee_approve":
            # Trigger fee approval
            user_id = str(query.from_user.id)
            if hasattr(self.bot.agent_loop, 'fee_collector'):
                result = self.bot.agent_loop.fee_collector.approve_fee(user_id)
                if result["status"] == "collected":
                    await query.edit_message_text(
                        f"Fee payment approved! {result['fee_amount']:.4f} SOL paid.",
                        parse_mode="Markdown"
                    )
                else:
                    await query.edit_message_text(f"Error: {result.get('message', 'Unknown error')}")
        
        elif callback_data == "fee_decline":
            user_id = str(query.from_user.id)
            if hasattr(self.bot.agent_loop, 'fee_collector'):
                result = self.bot.agent_loop.fee_collector.decline_fee(user_id)
                await query.edit_message_text(
                    f"Fee declined. Bot paused until {result.get('paused_until', 'next month')}",
                    parse_mode="Markdown"
                )
        
        elif callback_data == "fee_info":
            await query.edit_message_text(
                "**Monthly Fee System**\n\n"
                "We charge 2% on monthly profits only.\n"
                "No profit = no fee.\n\n"
                "Use /fees to see your fee history.",
                parse_mode="Markdown"
            )
    
    async def _handle_bot_control_callback(self, query, callback_data: str):
        """Handle bot control button callbacks."""
        if callback_data == "bot_pause":
            self.bot.agent_loop.stop()
            await query.edit_message_text("Bot paused. Use /resume to start again.")
        
        elif callback_data == "bot_resume":
            await query.edit_message_text("Bot resumed! Use /status to check.")
    
    async def _handle_menu_callback(self, query, callback_data: str):
        """Handle menu navigation button callbacks."""
        if callback_data == "menu_wallet":
            await query.message.reply_text("Use /wallet to see wallet info.")
        elif callback_data == "menu_stats":
            await query.message.reply_text("Use /stats to see performance.")
        elif callback_data == "menu_fees":
            await query.message.reply_text("Use /fees to see fee info.")
        else:
            await query.edit_message_text("Menu option not implemented yet.")
