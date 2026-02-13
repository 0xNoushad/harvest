"""Poll handler for user feedback polls."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from .base_handler import BaseHandler

logger = logging.getLogger(__name__)


class PollHandler(BaseHandler):
    """Handles poll answers from users."""
    
    async def handle_poll_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle poll answers."""
        answer = update.poll_answer
        user = answer.user
        selected = answer.option_ids
        
        logger.info(f"Poll answer from {user.username}: {selected}")
        
        # Store feedback (you can save to database here)
        # For now just log it
