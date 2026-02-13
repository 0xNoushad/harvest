"""
Message Templates

Pre-formatted message templates for common scenarios.
"""

from telegram import InlineKeyboardMarkup
from typing import Tuple
from datetime import datetime
from .buttons import Buttons
from .formatters import (
    format_sol, format_usd, truncate_address,
    TimeFormatter, EmojiFormatter
)


class Messages:
    """Professional message templates."""
    
    @staticmethod
    def fee_approval(
        month: str,
        profit: float,
        fee: float,
        expires_at: str
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """Fee approval request message."""
        message = f"""{EmojiFormatter.MONEY} **Monthly Performance Fee**

**Month:** {month}
**Your Profit:** {format_sol(profit)}
**Performance Fee (2%):** {format_sol(fee)}

**Expires:** {expires_at}

Approve payment to continue using Harvest next month.

**What happens if you:**
• **Approve:** Fee is paid, bot continues running
• **Decline:** Bot pauses for 30 days

Choose an option below:"""
        
        return message, Buttons.fee_approval()
    
    @staticmethod
    def withdrawal_confirmation(
        amount: float,
        address: str,
        balance: float
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """Withdrawal confirmation message."""
        truncated_addr = truncate_address(address)
        remaining = balance - amount
        
        message = f"""{EmojiFormatter.ALERT} **Confirm Withdrawal**

**Amount:** {format_sol(amount)}
**To Address:** `{truncated_addr}`
**Current Balance:** {format_sol(balance)}
**Remaining:** {format_sol(remaining)}

**WARNING:** This action cannot be undone.

Confirm to proceed:"""
        
        return message, Buttons.withdrawal_confirm(amount)
    
    @staticmethod
    def pause_confirmation() -> Tuple[str, InlineKeyboardMarkup]:
        """Bot pause confirmation."""
        message = f"""{EmojiFormatter.WARNING} **Pause Bot?**

This will stop all trading activities until you resume.

**What gets paused:**
• All strategy execution
• Trade scanning
• Opportunity alerts

**What continues:**
• Your wallet remains secure
• Performance tracking
• Fee notifications

Are you sure?"""
        
        return message, Buttons.yes_no("bot_pause_confirm", "bot_pause_cancel")
