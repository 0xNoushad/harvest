"""Wallet command handlers for Telegram bot."""

import logging
import asyncio
import base64
import base58
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class WalletCommands:
    """Handles wallet commands: /newwallet, /exportkey, /connect."""
    
    def __init__(self, bot_instance):
        """
        Initialize wallet commands handler.
        
        Args:
            bot_instance: Reference to TelegramBot instance for accessing wallet, etc.
        """
        self.bot = bot_instance
    
    async def cmd_newwallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /newwallet command - create a new wallet (with confirmation)."""
        message = """⚠️  **Create New Wallet**

This will DELETE your current wallet and create a new one.

**WARNING:**
• Your current wallet will be permanently deleted
• You will lose access to funds if you haven't backed up your private key
• This action CANNOT be undone

To proceed, run:
`python harvest/setup_secure_wallet.py`

Then choose option 2 to delete and create new wallet.

**Make sure you've backed up your current private key first!**
Use /exportkey to see it one more time.
"""
        
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def cmd_exportkey(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /exportkey command - show private key (DM only for security)."""
        # Check if this is a private chat
        if update.message.chat.type != "private":
            await update.message.reply_text(
                "🚫 For security, this command only works in private messages (DM).\n"
                "Send me a direct message and try again."
            )
            return
        
        from agent.wallet_setup import WalletSetup
        
        try:
            # Get the private key from the wallet
            if hasattr(self.bot.wallet, 'keypair'):
                private_key = base58.b58encode(bytes(self.bot.wallet.keypair)).decode('utf-8')
            else:
                await update.message.reply_text("❌ No wallet keypair available")
                return
            
            message = f"""🔑 **Your Private Key**

⚠️  **CRITICAL SECURITY WARNING**

This is your wallet's private key. Anyone with this key has FULL ACCESS to your funds.

**Private Key:**
`{private_key}`

**Security Instructions:**
1. 📝 Save this in a secure password manager
2. 🚫 NEVER share it with anyone
3. 🚫 NEVER post it online
4. 🗑️  Delete this message after saving

**This message will self-destruct in 60 seconds for your security.**
"""
            
            # Send the message
            sent_message = await update.message.reply_text(message, parse_mode="Markdown")
            
            # Delete after 60 seconds
            await asyncio.sleep(60)
            try:
                await sent_message.delete()
                await update.message.delete()
            except Exception:
                # Message might already be deleted or bot lacks permissions
                pass
                
        except Exception as e:
            await update.message.reply_text(f"❌ Error exporting key: {str(e)}")
