"""
Button Components

Clean inline keyboard buttons for user decisions.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict


class Buttons:
    """Professional button components."""
    
    @staticmethod
    def yes_no(yes_callback: str = "yes", no_callback: str = "no") -> InlineKeyboardMarkup:
        """Simple Yes/No buttons."""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Yes", callback_data=yes_callback),
                InlineKeyboardButton("No", callback_data=no_callback)
            ]
        ])
    
    @staticmethod
    def confirm_cancel(confirm_callback: str = "confirm", cancel_callback: str = "cancel") -> InlineKeyboardMarkup:
        """Confirm/Cancel buttons."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("Confirm", callback_data=confirm_callback)],
            [InlineKeyboardButton("Cancel", callback_data=cancel_callback)]
        ])
    
    @staticmethod
    def fee_approval() -> InlineKeyboardMarkup:
        """Fee approval buttons."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("Approve & Pay Fee", callback_data="fee_approve")],
            [InlineKeyboardButton("Decline (Pause Bot)", callback_data="fee_decline")],
            [InlineKeyboardButton("More Information", callback_data="fee_info")]
        ])
    
    @staticmethod
    def withdrawal_confirm(amount: float) -> InlineKeyboardMarkup:
        """Withdrawal confirmation."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(f"Confirm Withdrawal ({amount} SOL)", callback_data=f"withdraw_confirm_{amount}")],
            [InlineKeyboardButton("Cancel", callback_data="withdraw_cancel")]
        ])
    
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Main menu navigation."""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Wallet", callback_data="menu_wallet"),
                InlineKeyboardButton("Statistics", callback_data="menu_stats")
            ],
            [
                InlineKeyboardButton("Strategies", callback_data="menu_strategies"),
                InlineKeyboardButton("Fees", callback_data="menu_fees")
            ],
            [
                InlineKeyboardButton("Settings", callback_data="menu_settings"),
                InlineKeyboardButton("Help", callback_data="menu_help")
            ]
        ])
    
    @staticmethod
    def back(callback_data: str = "main_menu") -> InlineKeyboardMarkup:
        """Simple back button."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("Back", callback_data=callback_data)]
        ])
