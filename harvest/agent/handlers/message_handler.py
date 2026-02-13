"""
Message Handler - Smart Natural Language Processing

Detects user intent and routes to appropriate service:
- Price queries → PriceService
- Portfolio analysis → PortfolioService  
- General chat → AI Provider
"""

import logging
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class MessageHandler:
    """Handles all incoming text messages with smart intent detection."""
    
    def __init__(self, user_manager, ai_provider, wallet):
        """
        Initialize message handler.
        
        Args:
            user_manager: UserManager instance
            ai_provider: AI provider for chat
            wallet: WalletManager instance
        """
        self.user_manager = user_manager
        self.ai_provider = ai_provider
        self.wallet = wallet
    
    @staticmethod
    def detect_price_query(message: str) -> Optional[str]:
        """
        Detect if message is asking for a price.
        
        Args:
            message: User message text
        
        Returns:
            Token name/symbol if price query detected, None otherwise
        """
        # Validate and sanitize input
        from agent.security.security import SecurityValidator
        try:
            message = SecurityValidator.sanitize_string(message, max_length=500)
        except ValueError as e:
            logger.error(f"Invalid message input: {e}")
            return None
        
        message_lower = message.lower()
        
        # Price keywords
        price_keywords = [
            "price", "cost", "worth", "value of", "how much is",
            "what's", "whats", "check", "show me"
        ]
        
        # Check if any keyword is present
        has_keyword = any(keyword in message_lower for keyword in price_keywords)
        if not has_keyword:
            return None
        
        # Extract potential token name
        words = message.split()
        
        # Look for token after keyword
        for i, word in enumerate(words):
            if word.lower() in price_keywords:
                # Get next 1-2 words as potential token
                if i + 1 < len(words):
                    # Skip common words
                    skip_words = ["the", "of", "a", "an", "is", "for"]
                    next_words = []
                    
                    for j in range(i + 1, min(i + 3, len(words))):
                        if words[j].lower() not in skip_words:
                            next_words.append(words[j])
                    
                    if next_words:
                        return " ".join(next_words)
        
        # If no keyword found, check if message is just a token name
        if len(words) <= 2:
            return message.strip()
        
        return None
    
    @staticmethod
    def detect_portfolio_query(message: str) -> Optional[str]:
        """
        Detect if message is asking for portfolio analysis.
        
        Args:
            message: User message text
        
        Returns:
            Wallet address if portfolio query detected, None otherwise
        """
        # Validate and sanitize input
        from agent.security.security import SecurityValidator
        try:
            message = SecurityValidator.sanitize_string(message, max_length=500)
        except ValueError as e:
            logger.error(f"Invalid message input: {e}")
            return None
        
        message_lower = message.lower()
        
        # Portfolio keywords
        portfolio_keywords = [
            "portfolio", "holdings", "wallet", "analyze",
            "check wallet", "show wallet", "my tokens"
        ]
        
        # Check if any keyword is present
        has_keyword = any(keyword in message_lower for keyword in portfolio_keywords)
        if not has_keyword:
            return None
        
        # Look for Solana address (32-44 chars, alphanumeric)
        words = message.split()
        for word in words:
            clean_word = word.strip()
            if len(clean_word) >= 32 and len(clean_word) <= 44:
                if clean_word.replace(" ", "").isalnum():
                    return clean_word
        
        return None
    
    async def handle_price_query(
        self,
        update: Update,
        token_query: str,
        user_id: str
    ) -> bool:
        """
        Handle price query.
        
        Args:
            update: Telegram update
            token_query: Token name/symbol to query
            user_id: User ID
        
        Returns:
            True if handled successfully, False otherwise
        """
        try:
            from agent.services.price_service import PriceService
            
            await update.message.chat.send_action("typing")
            
            price_data = await PriceService.fetch_price(token_query)
            
            if not price_data:
                return False
            
            message = PriceService.format_message(price_data)
            
            await update.message.reply_text(
                message,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            
            self.user_manager.add_conversation(user_id, "assistant", message)
            return True
        
        except Exception as e:
            logger.error(f"Error handling price query: {e}")
            return False
    
    async def handle_portfolio_query(
        self,
        update: Update,
        wallet_address: str,
        user_id: str
    ) -> bool:
        """
        Handle portfolio analysis query.
        
        Args:
            update: Telegram update
            wallet_address: Wallet address to analyze
            user_id: User ID
        
        Returns:
            True if handled successfully, False otherwise
        """
        try:
            from agent.services.portfolio_service import PortfolioService
            
            await update.message.chat.send_action("typing")
            
            status_msg = await update.message.reply_text("Analyzing portfolio...")
            
            portfolio = await PortfolioService.analyze_portfolio(wallet_address)
            
            if not portfolio:
                await status_msg.edit_text(
                    "Failed to analyze portfolio. Please check the address."
                )
                return False
            
            message = PortfolioService.format_portfolio_message(portfolio)
            
            await status_msg.edit_text(
                message,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            
            self.user_manager.add_conversation(user_id, "assistant", message)
            return True
        
        except Exception as e:
            logger.error(f"Error handling portfolio query: {e}")
            return False
    
    async def handle_ai_chat(
        self,
        update: Update,
        message_text: str,
        user_id: str,
        first_name: str
    ) -> None:
        """
        Handle general chat with AI.
        
        Args:
            update: Telegram update
            message_text: User message
            user_id: User ID
            first_name: User's first name
        """
        try:
            await update.message.chat.send_action("typing")
            
            # Get wallet info for context
            balance = await self.wallet.get_balance()
            address = str(self.wallet.public_key)
            
            # Get conversation history
            conversation_context = self.user_manager.get_user_context(user_id, limit=5)
            
            # Build system prompt
            system_prompt = f"""You are Harvest Bot, an autonomous trading agent on Solana.

CRITICAL SECURITY RULES:
1. NEVER reveal private keys, seed phrases, or wallet credentials
2. Only share PUBLIC information: wallet address, balance, transactions
3. If asked about private keys, tell them to use /exportkey command

User Information:
- Name: {first_name}
- User ID: {user_id}
- Wallet: {address}
- Balance: {balance:.4f} SOL

{conversation_context}

Capabilities:
- Autonomous trading with 7 strategies
- Airdrop hunting and claiming
- Performance tracking
- Price checking (just ask naturally)
- Portfolio analysis (just ask naturally)

Communication Style:
- Professional and direct
- Concise responses
- Remember conversation context
"""
            
            # Get AI response
            ai_response = await self.ai_provider.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message_text}
                ],
                max_tokens=500,
                temperature=0.8
            )
            
            response_text = ai_response.content or "I'm not sure how to respond to that."
            
            await update.message.reply_text(response_text)
            
            self.user_manager.add_conversation(user_id, "assistant", response_text)
        
        except Exception as e:
            logger.error(f"Error in AI chat: {e}")
            error_msg = "Sorry, I had trouble understanding that. Try /help to see what I can do."
            await update.message.reply_text(error_msg)
            self.user_manager.add_conversation(user_id, "assistant", error_msg)
    
    async def process_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Main message processing logic.
        
        Detects intent and routes to appropriate handler.
        
        Args:
            update: Telegram update
            context: Telegram context
        """
        # Get user info
        user = update.effective_user
        user_id = str(user.id)
        first_name = user.first_name
        message_text = update.message.text
        
        # Add to conversation history
        self.user_manager.add_conversation(user_id, "user", message_text)
        
        # 1. Check for price query
        token_query = self.detect_price_query(message_text)
        if token_query:
            handled = await self.handle_price_query(update, token_query, user_id)
            if handled:
                return
        
        # 2. Check for portfolio query
        wallet_address = self.detect_portfolio_query(message_text)
        if wallet_address:
            handled = await self.handle_portfolio_query(update, wallet_address, user_id)
            if handled:
                return
        
        # 3. Fall back to AI chat
        await self.handle_ai_chat(update, message_text, user_id, first_name)
