"""Messaging utilities for Telegram bot."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def send_message(bot_instance, text: str, **kwargs):
    """
    Send a message to the user.
    
    Args:
        bot_instance: TelegramBot instance
        text: Message text to send
        **kwargs: Additional arguments for send_message
    """
    if not bot_instance._initialized:
        await bot_instance.initialize()
    
    try:
        await bot_instance.application.bot.send_message(
            chat_id=bot_instance.chat_id,
            text=text,
            **kwargs
        )
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
