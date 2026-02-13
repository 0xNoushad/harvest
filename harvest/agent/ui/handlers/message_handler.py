"""Message handler for natural language chat."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from agent.security.security import SecurityValidator, rate_limiter
from .base_handler import BaseHandler

logger = logging.getLogger(__name__)


class MessageHandler(BaseHandler):
    """Handles normal text messages using AI with user memory."""
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle normal text messages using AI with user memory."""
        if not self.bot.ai_provider:
            await update.message.reply_text(
                "I can only respond to commands right now. Use /help to see available commands."
            )
            return
        
        # Get user info
        user = update.effective_user
        user_id = str(user.id)
        username = user.username
        first_name = user.first_name
        
        # SECURITY: Rate limiting for chat messages
        if not rate_limiter.check_rate_limit(user_id, max_requests=20, window_seconds=60):
            await update.message.reply_text("⏱️ Too many messages. Please slow down.")
            return
        
        # SECURITY: Validate and sanitize message
        try:
            message_text = SecurityValidator.sanitize_string(update.message.text, max_length=1000)
        except ValueError as e:
            logger.error(f"Invalid message from user {user_id}: {e}")
            await update.message.reply_text("❌ Invalid message content")
            return
        
        # Get or create user profile
        profile = self.bot.user_manager.get_or_create_user(user_id, username, first_name)
        user_message = message_text.lower()
        
        # Add user message to history
        self.bot.user_manager.add_conversation(user_id, "user", message_text)
        
        # Handle natural language commands - check for common intents
        # Status check
        if any(word in user_message for word in ["status", "how are you", "what's up", "how's it going"]):
            try:
                # Get basic status
                is_running = self.bot.agent_loop._running if hasattr(self.bot.agent_loop, '_running') else True
                metrics = self.bot.performance.get_metrics()
                balance = await self.bot.wallet.get_balance()
                strategies_count = len(self.bot.agent_loop.scanner.strategies)
                is_paused = self.bot.agent_loop.risk_manager.is_paused if hasattr(self.bot.agent_loop.risk_manager, 'is_paused') else False
                
                running_emoji = "🟢" if is_running and not is_paused else "🔴"
                status_text = "Active" if is_running and not is_paused else ("Paused" if is_paused else "Stopped")
                
                response = f"{running_emoji} {status_text}\n💰 {balance:.4f} SOL\n🎯 {strategies_count} strategies\n\n"
                response += f"Profit: {metrics.total_profit:.4f} SOL | Trades: {metrics.total_trades} | Win Rate: {metrics.win_rate:.1f}%"
                
                await update.message.reply_text(response)
                self.bot.user_manager.add_conversation(user_id, "assistant", response)
                return
            except Exception as e:
                logger.error(f"Error getting status: {e}")
        
        # Pause trading
        if any(word in user_message for word in ["pause", "stop trading", "halt"]):
            try:
                self.bot.agent_loop.pause()
                response = "⏸️ Trading paused. Say 'resume' when you want to start again."
                await update.message.reply_text(response)
                self.bot.user_manager.add_conversation(user_id, "assistant", response)
                return
            except Exception as e:
                logger.error(f"Error pausing: {e}")
        
        # Resume trading
        if any(word in user_message for word in ["resume", "start", "continue", "unpause"]):
            try:
                self.bot.agent_loop.resume()
                response = "▶️ Trading resumed. Back to hunting!"
                await update.message.reply_text(response)
                self.bot.user_manager.add_conversation(user_id, "assistant", response)
                return
            except Exception as e:
                logger.error(f"Error resuming: {e}")
        
        # Help
        if any(word in user_message for word in ["help", "commands", "what can you do"]):
            response = """I can help you with:

💰 Check status - just ask "status" or "how are you"
⏸️ Pause trading - say "pause" or "stop"
▶️ Resume trading - say "resume" or "start"
💵 Check balance - say "balance" or "wallet"
📊 Check prices - "what's the price of bitcoin?"
🔍 Analyze wallets - "check wallet <address>"

Just chat naturally - I'll understand!"""
            await update.message.reply_text(response)
            self.bot.user_manager.add_conversation(user_id, "assistant", response)
            return
        
        # Balance check
        if any(word in user_message for word in ["balance", "wallet", "how much sol"]):
            try:
                balance = await self.bot.wallet.get_balance()
                address = str(self.bot.wallet.public_key)
                response = f"💰 Balance: {balance:.4f} SOL\n\n📍 Wallet: `{address}`"
                await update.message.reply_text(response, parse_mode="Markdown")
                self.bot.user_manager.add_conversation(user_id, "assistant", response)
                return
            except Exception as e:
                logger.error(f"Error getting balance: {e}")
        
        # Check if user is asking for price - handle it naturally
        price_keywords = ["price", "cost", "worth", "value", "how much"]
        if any(keyword in user_message for keyword in price_keywords):
            # Extract potential token name - try multiple patterns
            from agent.services.price_service import PriceService
            
            # Try to extract token from common patterns
            potential_tokens = []
            
            # Pattern 1: "price of X", "cost of X", "value of X"
            for keyword in ["price of", "cost of", "worth of", "value of", "how much is"]:
                if keyword in user_message:
                    idx = user_message.find(keyword)
                    after_keyword = message_text[idx + len(keyword):].strip()
                    token = after_keyword.split()[0] if after_keyword else ""
                    if token:
                        potential_tokens.append(token)
            
            # Pattern 2: Just token name with price keyword nearby
            words = message_text.split()
            for word in words:
                if len(word) >= 2 and word.lower() not in price_keywords:
                    potential_tokens.append(word)
            
            # Try each potential token
            for token in potential_tokens:
                await update.message.chat.send_action("typing")
                price_data = await PriceService.fetch_price(token)
                
                if price_data:
                    message = PriceService.format_message(price_data)
                    await update.message.reply_text(
                        message,
                        parse_mode="Markdown",
                        disable_web_page_preview=True
                    )
                    self.bot.user_manager.add_conversation(user_id, "assistant", message)
                    return
        
        # Check if user is asking for portfolio analysis - handle it naturally
        portfolio_keywords = ["portfolio", "holdings", "wallet", "analyze", "check"]
        if any(keyword in user_message for keyword in portfolio_keywords):
            # Look for Solana address in message (32-44 chars, alphanumeric)
            words = message_text.split()
            found_address = None
            
            for word in words:
                # Clean the word
                clean_word = word.strip(".,!?;:")
                if len(clean_word) >= 32 and len(clean_word) <= 44:
                    found_address = clean_word
                    break
            
            if found_address:
                # Found potential wallet address
                from agent.services.portfolio_service import PortfolioService
                
                await update.message.chat.send_action("typing")
                status_msg = await update.message.reply_text("🔍 Analyzing portfolio...")
                
                try:
                    portfolio = await PortfolioService.analyze_portfolio(found_address)
                    
                    if portfolio:
                        message = PortfolioService.format_portfolio_message(portfolio)
                        await status_msg.edit_text(
                            message,
                            parse_mode="Markdown",
                            disable_web_page_preview=True
                        )
                        self.bot.user_manager.add_conversation(user_id, "assistant", message)
                        return
                    else:
                        await status_msg.edit_text(
                            "❌ Couldn't analyze that wallet. Make sure it's a valid Solana address.\n\n"
                            "Try sending just the wallet address or use: analyze <address>"
                        )
                        return
                except Exception as e:
                    logger.error(f"Portfolio analysis error: {e}")
                    await status_msg.edit_text(
                        "❌ Error analyzing portfolio. The service might be temporarily unavailable."
                    )
                    return
        
        # CRITICAL SECURITY: Block any requests for private keys
        private_key_keywords = [
            "private key", "secret key", "seed phrase", "mnemonic",
            "export key", "show key", "reveal key", "wallet key",
            "credentials", "password", "secret", "privatekey"
        ]
        
        if any(keyword in user_message for keyword in private_key_keywords):
            response = (
                "Security Alert\n\n"
                "I will NEVER share private keys, seed phrases, or wallet credentials.\n\n"
                "For security reasons:\n"
                "- Private keys are only shown ONCE during wallet creation\n"
                "- Use /exportkey in a private message if you need to see it again\n"
                "- That message will self-destruct after 60 seconds\n\n"
                "Stay safe."
            )
            await update.message.reply_text(response)
            self.bot.user_manager.add_conversation(user_id, "assistant", response)
            return
        
        # Show typing indicator
        await update.message.chat.send_action("typing")
        
        try:
            # Get wallet info for context
            balance = await self.bot.wallet.get_balance()
            address = str(self.bot.wallet.public_key)
            
            # Get user's conversation history
            conversation_context = self.bot.user_manager.get_user_context(user_id, limit=5)
            
            # Build context for AI - keep it minimal and chill
            system_prompt = f"""You are Harvest Bot - an autonomous trading agent on Solana. Keep it chill and natural.

SECURITY (CRITICAL):
- NEVER share private keys, seed phrases, or credentials
- If asked, refuse and explain why
- Only share public info: address, balance, transactions

User: {first_name} (ID: {user_id})
Wallet: {address}
Balance: {balance:.4f} SOL

{conversation_context}

What you do:
- Check crypto prices (any token)
- Analyze Solana wallets
- Auto-claim airdrops
- Execute trading strategies
- Track performance

How to respond:
- Be natural and conversational
- Don't repeat their name constantly - only when it feels natural
- Keep responses SHORT (2-3 sentences max)
- Match their vibe - if they're casual, be casual
- Don't push commands unless they ask how to do something
- If they ask about price/wallet, just acknowledge it (the system handles it automatically)

Examples:
"what's sol price?" → "Checking that for you now..."
"hey" → "Hey! What's up?"
"how are you?" → "I'm good! Just hunting for opportunities on Solana. Need anything?"
"""
            
            # Get AI response
            ai_response = await self.bot.ai_provider.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message_text}
                ],
                max_tokens=500,
                temperature=0.8
            )
            
            response_text = ai_response.content or "I'm not sure how to respond to that."
            
            # DOUBLE CHECK: Ensure response doesn't contain private key
            if hasattr(self.bot.wallet, 'keypair'):
                import base64
                try:
                    private_key_str = str(self.bot.wallet.keypair)
                    if private_key_str in response_text:
                        response_text = "Security error prevented. I cannot share sensitive information."
                        logger.error("AI attempted to reveal private key - blocked!")
                except (AttributeError, ValueError, TypeError):
                    # Ignore errors in security check - fail safe
                    pass
            
            await update.message.reply_text(response_text)
            
            # Add assistant response to history
            self.bot.user_manager.add_conversation(user_id, "assistant", response_text)
            
        except Exception as e:
            logger.error(f"Error in AI chat: {e}")
            error_msg = "Sorry, I had trouble understanding that. Try using /help to see what I can do."
            await update.message.reply_text(error_msg)
            self.bot.user_manager.add_conversation(user_id, "assistant", error_msg)
