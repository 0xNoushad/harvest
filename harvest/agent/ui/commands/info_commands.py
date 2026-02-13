"""Information command handlers for Telegram bot."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class InfoCommands:
    """Handles information commands: /price, /portfolio, /stats."""
    
    def __init__(self, bot_instance):
        """
        Initialize info commands handler.
        
        Args:
            bot_instance: Reference to TelegramBot instance for accessing performance, etc.
        """
        self.bot = bot_instance
    
    async def cmd_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /price command - check ANY crypto price by name or address."""
        from agent.services.price_service import PriceService
        
        # Get token from command args
        if not context.args:
            await update.message.reply_text(
                "**Check Crypto Prices**\n\n"
                "Usage: `/price <token or address>`\n\n"
                "Examples:\n"
                "• `/price SOL`\n"
                "• `/price bitcoin`\n"
                "• `/price ethereum`\n"
                "• `/price DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263`\n\n"
                "Works with ANY cryptocurrency!",
                parse_mode="Markdown"
            )
            return
        
        query = " ".join(context.args)
        
        # Show typing indicator
        await update.message.chat.send_action("typing")
        
        try:
            # Fetch price data
            price_data = await PriceService.fetch_price(query)
            
            if not price_data:
                await update.message.reply_text(
                    f"Token '{query}' not found.\n\n"
                    f"Try using:\n"
                    f"• Full token name (e.g., 'bitcoin')\n"
                    f"• Token symbol (e.g., 'BTC')\n"
                    f"• Solana contract address"
                )
                return
            
            # Format and send message
            message = PriceService.format_message(price_data)
            
            await update.message.reply_text(
                message,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            
        except Exception as e:
            logger.error(f"Error in price command: {e}")
            await update.message.reply_text(
                f"Error fetching price data. Please try again."
            )
    
    async def cmd_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /portfolio command - analyze any Solana wallet portfolio."""
        from agent.services.portfolio_service import PortfolioService
        
        # Get wallet address from command args
        if not context.args:
            await update.message.reply_text(
                "**Analyze Wallet Portfolio**\n\n"
                "Usage: `/portfolio <wallet_address>`\n\n"
                "Example:\n"
                "`/portfolio 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU`\n\n"
                "Shows:\n"
                "• Total portfolio value\n"
                "• SOL balance\n"
                "• All token holdings with prices\n"
                "• Top holdings breakdown",
                parse_mode="Markdown"
            )
            return
        
        wallet_address = context.args[0].strip()
        
        # Validate wallet address format
        if len(wallet_address) < 32 or len(wallet_address) > 44:
            await update.message.reply_text(
                "Invalid wallet address format.\n\n"
                "Solana addresses are 32-44 characters long."
            )
            return
        
        # Show typing indicator
        await update.message.chat.send_action("typing")
        
        # Send initial message
        status_msg = await update.message.reply_text(
            "Analyzing portfolio...\n"
            "This may take a few seconds."
        )
        
        try:
            # Analyze portfolio
            portfolio = await PortfolioService.analyze_portfolio(wallet_address)
            
            if not portfolio:
                await status_msg.edit_text(
                    "Failed to analyze portfolio.\n\n"
                    "Possible reasons:\n"
                    "• Invalid wallet address\n"
                    "• Network error\n"
                    "• RPC timeout\n\n"
                    "Please try again."
                )
                return
            
            # Format and send detailed message
            message = PortfolioService.format_portfolio_message(portfolio)
            
            await status_msg.edit_text(
                message,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            
        except Exception as e:
            logger.error(f"Error in portfolio command: {e}")
            await status_msg.edit_text(
                "Error analyzing portfolio. Please try again."
            )
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command - show performance stats."""
        try:
            # Get user_id from message
            user_id = str(update.effective_user.id)
            
            # Get per-user metrics
            metrics = self.bot.performance.get_metrics(user_id=user_id)
            
            # Check if user has any trades
            if metrics.total_trades == 0:
                await update.message.reply_text(
                    "📊 **Your Performance Stats**\n\n"
                    "No trades yet! Start trading to see your performance metrics.\n\n"
                    "Use /balance to check your wallet balance.",
                    parse_mode="Markdown"
                )
                return
            
            message = f"""📊 **Your Performance Stats**

**Total Profit:** {metrics.total_profit:.4f} SOL
**Net Profit:** {metrics.net_profit:.4f} SOL
**Total Trades:** {metrics.total_trades}
**Successful Trades:** {metrics.successful_trades}
**Win Rate:** {metrics.win_rate:.1f}%
**Total Gas Fees:** {metrics.total_gas_fees:.4f} SOL

**Profit by Strategy:**
"""
            
            if metrics.profit_by_strategy:
                for strategy, profit in metrics.profit_by_strategy.items():
                    message += f"• {strategy}: {profit:.4f} SOL\n"
            else:
                message += "No strategy data available\n"
            
            if hasattr(metrics, 'performance_fee_collected') and metrics.performance_fee_collected > 0:
                message += f"\n**Performance Fee Collected:** {metrics.performance_fee_collected:.4f} SOL"
            
            await update.message.reply_text(
                message,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error in cmd_stats: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Error fetching stats: {str(e)}")
    
    async def cmd_bounty(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /bounty command - show active bounties."""
        message = """🎯 **Active Bounties**

**Coming Soon!**

We're building a bounty hunter that will:
• Scan for on-chain bounties
• Find bug bounties
• Track hackathon prizes
• Monitor protocol incentives

Stay tuned! 🚀
"""
        
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def cmd_airdrops(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /airdrops command - show recent airdrop discoveries."""
        try:
            # Get airdrop hunter from scanner
            hunter = None
            for strategy in self.bot.agent_loop.scanner.strategies:
                if strategy.get_name() == "airdrop_hunter":
                    hunter = strategy
                    break
            
            if not hunter:
                await update.message.reply_text("❌ Airdrop hunter not found")
                return
            
            discoveries = hunter.get_discoveries(days=7)
            
            if not discoveries:
                message = """🔍 **Recent Airdrop Discoveries**

No airdrops discovered in the last 7 days.

The bot scans every 12 hours, so check back soon!
"""
            else:
                message = f"""🎁 **Recent Airdrop Discoveries**

Found {len(discoveries)} airdrops in the last 7 days:

"""
                for disc in discoveries[-10:]:  # Show last 10
                    message += f"• **{disc['protocol']}** ({disc['token']})\n"
                    message += f"  Source: {disc['source']}\n"
                    if disc.get('claim_url'):
                        message += f"  [Claim Here]({disc['claim_url']})\n"
                    message += "\n"
            
            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Error fetching airdrops: {str(e)}")
    
    async def cmd_claims(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /claims command - show claim history."""
        try:
            # Get airdrop claimer from scanner
            claimer = None
            for strategy in self.bot.agent_loop.scanner.strategies:
                if strategy.get_name() == "airdrop_claimer":
                    claimer = strategy
                    break
            
            if not claimer:
                await update.message.reply_text("❌ Airdrop claimer not found")
                return
            
            claims = claimer.get_claim_history()
            total_claimed = claimer.get_total_claimed()
            
            if not claims:
                message = """✅ **Claim History**

No claims yet.

The bot checks eligibility every 24 hours and auto-claims when available!
"""
            else:
                message = f"""✅ **Claim History**

**Total Claimed:** {total_claimed:.2f} tokens

**Recent Claims:**

"""
                for claim in claims[-10:]:  # Show last 10
                    status = "✅" if claim['success'] else "❌"
                    message += f"{status} **{claim['protocol']}**\n"
                    message += f"   {claim['amount']:.2f} {claim['token']}\n"
                    if claim.get('claim_tx_hash'):
                        message += f"   [View TX](https://solscan.io/tx/{claim['claim_tx_hash']})\n"
                    message += "\n"
            
            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Error fetching claims: {str(e)}")
    
    async def cmd_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /settings command - configure bot settings."""
        message = """⚙️ **Bot Settings**

Current settings:
• Risk limits: Active
• Auto-claim: Enabled
• Notifications: All enabled

To modify settings, use these commands:
/pause - Pause the bot
/resume - Resume the bot
/status - Check bot status

More settings coming soon!
"""
        
        await update.message.reply_text(
            message,
            parse_mode="Markdown"
        )
    
    async def cmd_poll(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /poll command - send user feedback poll."""
        questions = [
            {
                "question": "How satisfied are you with Harvest Bot?",
                "options": ["😍 Love it!", "👍 Good", "😐 Okay", "👎 Not great", "😡 Terrible"]
            },
            {
                "question": "Which feature do you use most?",
                "options": ["🔍 Airdrop Hunter", "🎁 Auto Claimer", "📊 Stats", "💰 Wallet", "🎯 Bounties"]
            },
            {
                "question": "What should we build next?",
                "options": ["🤖 More strategies", "📈 Better analytics", "⚡ Faster scanning", "🔔 More notifications", "🎮 Gamification"]
            }
        ]
        
        # Send first poll
        poll = questions[0]
        await update.message.reply_poll(
            question=poll["question"],
            options=poll["options"],
            is_anonymous=False,
            allows_multiple_answers=False
        )
        
        await update.message.reply_text(
            "📊 Thanks for your feedback! Your input helps us improve Harvest Bot.",
            parse_mode="Markdown"
        )
    
    async def cmd_connect(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /connect command - get wallet connection link."""
        message = f"""🔗 **Connect Your Wallet**

To connect your wallet, visit the web dashboard.

Supported wallets:
• Phantom
• Solflare
• Backpack
• Ledger

Your private key never leaves your device!

Use /wallet to see your current wallet info.
"""
        
        await update.message.reply_text(
            message,
            parse_mode="Markdown"
        )
    
    async def cmd_leaderboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /leaderboard command - show anonymized rankings."""
        try:
            # Get leaderboard data
            leaderboard = self.bot.performance.get_leaderboard(limit=10)
            
            if not leaderboard:
                await update.message.reply_text(
                    "🏆 **Leaderboard**\n\n"
                    "No trading data yet! Be the first to start trading.\n\n"
                    "Use /stats to see your performance.",
                    parse_mode="Markdown"
                )
                return
            
            message = "🏆 **Top Traders Leaderboard**\n\n"
            
            # Add medal emojis for top 3
            medals = {1: "🥇", 2: "🥈", 3: "🥉"}
            
            for entry in leaderboard:
                rank = entry['rank']
                profit = entry['profit']
                win_rate = entry['win_rate']
                
                # Add medal for top 3
                rank_display = medals.get(rank, f"{rank}.")
                
                message += f"{rank_display} **Profit:** {profit:.4f} SOL | **Win Rate:** {win_rate:.1f}%\n"
            
            message += "\n_Rankings are anonymized for privacy_"
            
            await update.message.reply_text(
                message,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error in cmd_leaderboard: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Error fetching leaderboard: {str(e)}")
