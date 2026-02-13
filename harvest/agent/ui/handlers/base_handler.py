"""Base handler class for common functionality."""

import logging

logger = logging.getLogger(__name__)


class BaseHandler:
    """Base class for all handlers with common functionality."""
    
    def __init__(self, bot_instance):
        """
        Initialize base handler.
        
        Args:
            bot_instance: Reference to TelegramBot instance
        """
        self.bot = bot_instance
        self.logger = logger
    
    def get_user_id(self, update):
        """Extract user ID from update."""
        if update.effective_user:
            return str(update.effective_user.id)
        return None
    
    def get_username(self, update):
        """Extract username from update."""
        if update.effective_user:
            return update.effective_user.username
        return None
    
    def get_first_name(self, update):
        """Extract first name from update."""
        if update.effective_user:
            return update.effective_user.first_name
        return None
    
    async def send_error_message(self, update, error_text):
        """Send a formatted error message."""
        try:
            await update.message.reply_text(f"❌ {error_text}")
        except Exception as e:
            self.logger.error(f"Failed to send error message: {e}")
    
    async def send_success_message(self, update, success_text):
        """Send a formatted success message."""
        try:
            await update.message.reply_text(f"✅ {success_text}")
        except Exception as e:
            self.logger.error(f"Failed to send success message: {e}")
