"""Message formatting utilities for Telegram bot."""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class MessageFormatter:
    """Utilities for formatting Telegram messages."""
    
    @staticmethod
    def format_balance(balance: float, decimals: int = 4) -> str:
        """
        Format balance with appropriate decimal places.
        
        Args:
            balance: Balance amount
            decimals: Number of decimal places
            
        Returns:
            Formatted balance string
        """
        return f"{balance:.{decimals}f}"
    
    @staticmethod
    def format_percentage(value: float, decimals: int = 1) -> str:
        """
        Format percentage value.
        
        Args:
            value: Percentage value
            decimals: Number of decimal places
            
        Returns:
            Formatted percentage string
        """
        return f"{value:.{decimals}f}%"
    
    @staticmethod
    def format_address(address: str, show_chars: int = 8) -> str:
        """
        Format wallet address for display (shortened).
        
        Args:
            address: Full wallet address
            show_chars: Number of characters to show at start and end
            
        Returns:
            Formatted address string
        """
        if len(address) <= show_chars * 2:
            return address
        return f"{address[:show_chars]}...{address[-show_chars:]}"
    
    @staticmethod
    def format_transaction_link(tx_signature: str, network: str = "mainnet") -> str:
        """
        Format transaction link for Solscan.
        
        Args:
            tx_signature: Transaction signature
            network: Network name (mainnet, devnet, testnet)
            
        Returns:
            Formatted Solscan link
        """
        if network == "mainnet":
            return f"https://solscan.io/tx/{tx_signature}"
        else:
            return f"https://solscan.io/tx/{tx_signature}?cluster={network}"
    
    @staticmethod
    def format_wallet_link(address: str, network: str = "mainnet") -> str:
        """
        Format wallet link for Solscan.
        
        Args:
            address: Wallet address
            network: Network name (mainnet, devnet, testnet)
            
        Returns:
            Formatted Solscan link
        """
        if network == "mainnet":
            return f"https://solscan.io/account/{address}"
        else:
            return f"https://solscan.io/account/{address}?cluster={network}"
    
    @staticmethod
    def format_status_emoji(is_active: bool) -> str:
        """
        Get status emoji based on active state.
        
        Args:
            is_active: Whether the status is active
            
        Returns:
            Status emoji
        """
        return "🟢" if is_active else "🔴"
    
    @staticmethod
    def format_list(items: List[str], bullet: str = "•") -> str:
        """
        Format list of items with bullets.
        
        Args:
            items: List of items
            bullet: Bullet character
            
        Returns:
            Formatted list string
        """
        return "\n".join([f"{bullet} {item}" for item in items])
    
    @staticmethod
    def format_key_value(key: str, value: str, separator: str = ": ") -> str:
        """
        Format key-value pair.
        
        Args:
            key: Key name
            value: Value
            separator: Separator between key and value
            
        Returns:
            Formatted key-value string
        """
        return f"{key}{separator}{value}"
    
    @staticmethod
    def format_section(title: str, content: str) -> str:
        """
        Format a message section with title.
        
        Args:
            title: Section title
            content: Section content
            
        Returns:
            Formatted section string
        """
        return f"**{title}**\n\n{content}\n"
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """
        Truncate text to maximum length.
        
        Args:
            text: Text to truncate
            max_length: Maximum length
            suffix: Suffix to add if truncated
            
        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
