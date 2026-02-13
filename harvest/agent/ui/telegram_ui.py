"""
Telegram UI Components - Professional Interface

Clean, modular UI components for Telegram bot.
"""

from .buttons import Buttons
from .messages import Messages

# Backward compatibility aliases
TelegramUI = Buttons
MessageTemplates = Messages

__all__ = [
    'Buttons',
    'Messages',
    'TelegramUI',
    'MessageTemplates',
]
