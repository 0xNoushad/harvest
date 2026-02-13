"""Basic command handlers for Telegram bot."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class BasicCommands:
    """Handles basic bot commands: /start, /help, /wallet, /status."""
    
    def __init__(self, bot_instance):
        """
        Initialize basic commands handler.
        
        Args:
            bot_instance: Reference to TelegramBot instance for accessing wallet, performance, etc.
        """
        self.bot = bot_instance
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command - welcome message with wallet setup."""
        from agent.wallet_setup import WalletSetup
        
        setup = WalletSetup()
        
        # Check if wallet exists
        if not setup.wallet_exists():
            message = """🌾 **Welcome to Harvest Bot!**

🔐 **First Time Setup Required**

You need a Solana wallet to start trading.

**Option 1: Create New Wallet (Recommended)**
Run: `python harvest/setup_secure_wallet.py`

This will:
✅ Generate a secure Solana wallet
✅ Give you your private key to save
✅ Encrypt and store it locally

**Option 2: Use Existing Wallet**
Add your private key to `.env`:
`WALLET_PRIVATE_KEY=your_key_here`

After setup, use /status to start! 🚀"""
        else:
            message = """🌾 **Harvest Bot**

Autonomous money hunter on Solana.

Running 7 strategies 24/7:
• Airdrops • NFT Flips • Yield Farming
• Staking • Arbitrage • Bounties

Use /status to see profit.
Use /wallet to check balance.
Use /pause to stop trading.

Let's make money. 🚀"""
        
        await update.message.reply_text(
            message,
            parse_mode="Markdown"
        )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command - show all commands."""
        message = """🌾 **Harvest Bot**

/status - Profit & bot status
/wallet - Check balance
/withdraw - Send SOL to your wallet
/fees - View monthly fees
/pause - Stop trading
/resume - Start trading

That's it. I make you money. 💰"""
        
        await update.message.reply_text(
            message,
            parse_mode="Markdown"
        )
    
    async def cmd_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /wallet command - show wallet info and management options."""
        try:
            balance = await self.bot.wallet.get_balance()
            address = str(self.bot.wallet.public_key)
            
            message = f"""💰 **Your Wallet**

**Address:**
`{address}`

**Balance:**
{balance:.4f} SOL

**Network:** {self.bot.wallet.network}

View on Solscan: https://solscan.io/account/{address}

**Commands:**
/withdraw - Send SOL to another address
/newwallet - Create a new wallet (deletes current)
/exportkey - Show your private key (DM only)
"""
            
            await update.message.reply_text(
                message,
                parse_mode="Markdown"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error fetching wallet info: {str(e)}")
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command - show bot status."""
        try:
            # Get basic status
            is_running = self.bot.agent_loop._running if hasattr(self.bot.agent_loop, '_running') else True
            
            # Get performance metrics
            metrics = self.bot.performance.get_metrics()
            
            # Get wallet balance
            balance = await self.bot.wallet.get_balance()
            
            # Get strategies count
            strategies_count = len(self.bot.agent_loop.scanner.strategies)
            
            # Check if paused
            is_paused = self.bot.agent_loop.risk_manager.is_paused if hasattr(self.bot.agent_loop.risk_manager, 'is_paused') else False
            
            running_emoji = "🟢" if is_running and not is_paused else "🔴"
            status_text = "Active" if is_running and not is_paused else ("Paused" if is_paused else "Stopped")
            
            message = f"""📊 Status

{running_emoji} {status_text}
💰 Balance: {balance:.4f} SOL
🎯 Strategies: {strategies_count} active

Performance:
• Profit: {metrics.total_profit:.4f} SOL
• Trades: {metrics.total_trades}
• Win Rate: {metrics.win_rate:.1f}%
"""
            
            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
