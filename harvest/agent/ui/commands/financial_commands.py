"""Financial command handlers for Telegram bot."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from agent.security.security import SecurityValidator, rate_limiter

logger = logging.getLogger(__name__)


class FinancialCommands:
    """Handles financial commands: /withdraw, /fees, /approve_fee, /decline_fee."""
    
    def __init__(self, bot_instance):
        """
        Initialize financial commands handler.
        
        Args:
            bot_instance: Reference to TelegramBot instance for accessing wallet, agent_loop, etc.
        """
        self.bot = bot_instance
    
    async def cmd_withdraw(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /withdraw command - send SOL to user's wallet."""
        try:
            # SECURITY: Rate limiting
            user_id = str(update.effective_user.id)
            if not rate_limiter.check_rate_limit(user_id, max_requests=5, window_seconds=60):
                await update.message.reply_text("⏱️ Too many requests. Please wait a minute.")
                return
            
            # Check if user provided address and amount
            if not context.args or len(context.args) < 2:
                message = """💸 **Withdraw SOL**

**Usage:**
`/withdraw <address> <amount>`

**Example:**
`/withdraw 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU 0.5`

This will send 0.5 SOL to your wallet.

**Current Balance:**
"""
                balance = await self.bot.wallet.get_balance()
                message += f"{balance:.4f} SOL"
                
                await update.message.reply_text(
                    message,
                    parse_mode="Markdown"
                )
                return
            
            # SECURITY: Validate inputs
            try:
                to_address = SecurityValidator.validate_wallet_address(context.args[0])
                amount = SecurityValidator.validate_amount(float(context.args[1]), min_val=0.001, max_val=1000.0)
            except ValueError as e:
                await update.message.reply_text(f"❌ Invalid input: {str(e)}")
                return
            
            # Validate amount
            balance = await self.bot.wallet.get_balance()
            if amount <= 0:
                await update.message.reply_text("❌ Amount must be greater than 0")
                return
            
            if amount > balance:
                await update.message.reply_text(
                    f"❌ Insufficient balance. You have {balance:.4f} SOL"
                )
                return
            
            # Keep minimum balance for fees
            min_balance = 0.01
            if balance - amount < min_balance:
                await update.message.reply_text(
                    f"❌ Must keep at least {min_balance} SOL for transaction fees"
                )
                return
            
            # Send confirmation message
            await update.message.reply_text(
                f"⏳ Sending {amount} SOL to `{to_address}`...",
                parse_mode="Markdown"
            )
            
            # Execute transfer
            tx_signature = await self.bot.wallet.send_sol(to_address, amount)
            
            if tx_signature:
                new_balance = await self.bot.wallet.get_balance()
                message = f"""✅ **Withdrawal Successful!**

**Amount:** {amount} SOL
**To:** `{to_address}`
**New Balance:** {new_balance:.4f} SOL

**Transaction:**
https://solscan.io/tx/{tx_signature}
"""
                await update.message.reply_text(
                    message,
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text("❌ Transaction failed. Please try again.")
                
        except ValueError:
            await update.message.reply_text("❌ Invalid amount. Please use a number (e.g., 0.5)")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def cmd_fees(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /fees command - show fee status and history."""
        try:
            # SECURITY: Rate limiting
            user_id = str(update.effective_user.id)
            if not rate_limiter.check_rate_limit(user_id, max_requests=10, window_seconds=60):
                await update.message.reply_text("⏱️ Too many requests. Please wait a minute.")
                return
            
            # SECURITY: Validate user ID
            try:
                user_id = SecurityValidator.validate_user_id(user_id)
            except ValueError as e:
                logger.error(f"Invalid user ID: {e}")
                await update.message.reply_text("❌ Invalid user ID")
                return
            
            # Get fee collector from agent loop
            if not hasattr(self.bot.agent_loop, 'fee_collector'):
                await update.message.reply_text(
                    "💰 **Monthly Fees**\n\n"
                    "Fee collection system not initialized yet.\n"
                    "Check back soon!",
                    parse_mode="Markdown"
                )
                return
            
            fee_collector = self.bot.agent_loop.fee_collector
            
            # Get user status
            status = fee_collector.get_user_status(user_id)
            
            # Build message
            message = "💰 **Your Monthly Fees**\n\n"
            
            # Active status
            if status["is_active"]:
                message += "✅ **Status:** Active\n\n"
            else:
                message += "⏸️ **Status:** Paused (payment required)\n\n"
            
            # Pending fee
            if status["has_pending_fee"]:
                pending = status["pending_fee"]
                message += f"📋 **Pending Fee Approval**\n"
                message += f"Month: {pending['month']}\n"
                message += f"Your Profit: {pending['monthly_profit']:.4f} SOL\n"
                message += f"Fee (2%): {pending['fee_amount']:.4f} SOL\n"
                message += f"Expires: {pending['expires_at'][:10]}\n\n"
                message += "Use /approve_fee to approve\n"
                message += "Use /decline_fee to decline\n\n"
            
            # Fee history
            history = fee_collector.get_user_fee_history(user_id)
            if history:
                message += f"📊 **Fee History** (Last 5)\n\n"
                for fee in history[-5:]:
                    status_emoji = "✅" if fee["status"] == "collected" else "⏭️"
                    message += f"{status_emoji} {fee['month']}: {fee['fee_amount']:.4f} SOL\n"
            else:
                message += "📊 **Fee History:** No fees yet\n"
            
            message += f"\n💡 **How it works:**\n"
            message += f"• We charge 2% on monthly profits only\n"
            message += f"• No profit = no fee\n"
            message += f"• You approve each payment\n"
            message += f"• Fair and transparent\n"
            
            await update.message.reply_text(message, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in /fees command: {e}")
            await update.message.reply_text(f"❌ Error fetching fee info: {str(e)}")
    
    async def cmd_approve_fee(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /approve_fee command - approve pending fee payment."""
        try:
            # SECURITY: Rate limiting (strict for financial operations)
            user_id = str(update.effective_user.id)
            if not rate_limiter.check_rate_limit(user_id, max_requests=3, window_seconds=60):
                await update.message.reply_text("⏱️ Too many requests. Please wait a minute.")
                return
            
            # SECURITY: Validate user ID
            try:
                user_id = SecurityValidator.validate_user_id(user_id)
            except ValueError as e:
                logger.error(f"Invalid user ID: {e}")
                await update.message.reply_text("❌ Invalid user ID")
                return
            
            # Get fee collector
            if not hasattr(self.bot.agent_loop, 'fee_collector'):
                await update.message.reply_text("❌ Fee collection system not initialized")
                return
            
            fee_collector = self.bot.agent_loop.fee_collector
            
            # Approve fee
            result = fee_collector.approve_fee(user_id)
            
            if result["status"] == "collected":
                message = f"""✅ **Fee Payment Approved!**

Month: {result['month']}
Your Profit: {result['monthly_profit']:.4f} SOL
Fee Paid: {result['fee_amount']:.4f} SOL

Thank you! Your bot will continue running.

Transaction: `{result['transaction_hash']}`
"""
                await update.message.reply_text(message, parse_mode="Markdown")
            
            elif result["status"] == "error":
                await update.message.reply_text(f"❌ {result['message']}")
            
            elif result["status"] == "expired":
                await update.message.reply_text(
                    "⏰ **Approval Expired**\n\n"
                    "The approval period has expired.\n"
                    "Contact support if you'd like to resume service.",
                    parse_mode="Markdown"
                )
            
            elif result["status"] == "failed":
                await update.message.reply_text(
                    f"❌ **Payment Failed**\n\n"
                    f"Error: {result.get('error', 'Unknown error')}\n\n"
                    f"Please try again or contact support.",
                    parse_mode="Markdown"
                )
            
        except Exception as e:
            logger.error(f"Error in /approve_fee command: {e}")
            await update.message.reply_text(f"❌ Error approving fee: {str(e)}")
    
    async def cmd_decline_fee(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /decline_fee command - decline pending fee payment."""
        try:
            # SECURITY: Rate limiting
            user_id = str(update.effective_user.id)
            if not rate_limiter.check_rate_limit(user_id, max_requests=3, window_seconds=60):
                await update.message.reply_text("⏱️ Too many requests. Please wait a minute.")
                return
            
            # SECURITY: Validate user ID
            try:
                user_id = SecurityValidator.validate_user_id(user_id)
            except ValueError as e:
                logger.error(f"Invalid user ID: {e}")
                await update.message.reply_text("❌ Invalid user ID")
                return
            
            # Get fee collector
            if not hasattr(self.bot.agent_loop, 'fee_collector'):
                await update.message.reply_text("❌ Fee collection system not initialized")
                return
            
            fee_collector = self.bot.agent_loop.fee_collector
            
            # Decline fee
            result = fee_collector.decline_fee(user_id)
            
            if result["status"] == "declined":
                message = f"""⏸️ **Fee Payment Declined**

Your bot has been paused until: {result['paused_until'][:10]}

You can resume service anytime by:
1. Using /approve_fee to pay the fee
2. Or waiting until next month

{result['message']}
"""
                await update.message.reply_text(message, parse_mode="Markdown")
            
            elif result["status"] == "error":
                await update.message.reply_text(f"❌ {result['message']}")
            
        except Exception as e:
            logger.error(f"Error in /decline_fee command: {e}")
            await update.message.reply_text(f"❌ Error declining fee: {str(e)}")
