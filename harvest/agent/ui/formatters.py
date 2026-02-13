"""
UI Formatters

Comprehensive formatting utilities for numbers, time, and text display.
Implements consistent formatting standards across the bot interface.
"""

from datetime import datetime, timedelta
from typing import Optional, Union
import re


class NumberFormatter:
    """Format numbers with consistent styling."""
    
    @staticmethod
    def format_sol(amount: float, decimals: int = 4) -> str:
        """
        Format SOL amount with appropriate decimal places.
        
        Args:
            amount: SOL amount to format
            decimals: Number of decimal places (default: 4)
        
        Returns:
            Formatted SOL string (e.g., "1.2345 SOL")
        """
        if amount == 0:
            return "0 SOL"
        
        # Use more decimals for very small amounts
        if abs(amount) < 0.0001:
            return f"{amount:.9f} SOL"
        
        return f"{amount:.{decimals}f} SOL"
    
    @staticmethod
    def format_usd(amount: float, decimals: int = 2) -> str:
        """
        Format USD amount with dollar sign and thousand separators.
        
        Args:
            amount: USD amount to format
            decimals: Number of decimal places (default: 2)
        
        Returns:
            Formatted USD string (e.g., "$1,234.56")
        """
        if amount == 0:
            return "$0.00"
        
        # Format with thousand separators
        formatted = f"{amount:,.{decimals}f}"
        return f"${formatted}"
    
    @staticmethod
    def format_percentage(value: float, decimals: int = 1, show_sign: bool = True) -> str:
        """
        Format percentage with optional sign.
        
        Args:
            value: Percentage value (e.g., 5.2 for 5.2%)
            decimals: Number of decimal places (default: 1)
            show_sign: Whether to show + for positive values
        
        Returns:
            Formatted percentage string (e.g., "+5.2%")
        """
        if value == 0:
            return "0%"
        
        sign = "+" if value > 0 and show_sign else ""
        return f"{sign}{value:.{decimals}f}%"
    
    @staticmethod
    def format_large_number(value: float, decimals: int = 1) -> str:
        """
        Format large numbers with abbreviations (K, M, B).
        
        Args:
            value: Number to format
            decimals: Number of decimal places
        
        Returns:
            Formatted string (e.g., "1.2M", "3.4B")
        """
        if abs(value) < 1000:
            return f"{value:.{decimals}f}"
        elif abs(value) < 1_000_000:
            return f"{value/1000:.{decimals}f}K"
        elif abs(value) < 1_000_000_000:
            return f"{value/1_000_000:.{decimals}f}M"
        else:
            return f"{value/1_000_000_000:.{decimals}f}B"
    
    @staticmethod
    def format_token_amount(amount: float, symbol: str, decimals: int = 2) -> str:
        """
        Format token amount with symbol.
        
        Args:
            amount: Token amount
            symbol: Token symbol
            decimals: Number of decimal places
        
        Returns:
            Formatted token string (e.g., "100.50 USDC")
        """
        if amount == 0:
            return f"0 {symbol}"
        
        # Use thousand separators for large amounts
        if amount >= 1000:
            formatted = f"{amount:,.{decimals}f}"
        else:
            formatted = f"{amount:.{decimals}f}"
        
        return f"{formatted} {symbol}"
    
    @staticmethod
    def format_with_separators(value: Union[int, float], decimals: int = 0) -> str:
        """
        Format number with thousand separators.
        
        Args:
            value: Number to format
            decimals: Number of decimal places
        
        Returns:
            Formatted string (e.g., "1,234,567")
        """
        if decimals > 0:
            return f"{value:,.{decimals}f}"
        return f"{int(value):,}"


class TimeFormatter:
    """Format time and dates with consistent styling."""
    
    @staticmethod
    def format_relative(dt: datetime) -> str:
        """
        Format datetime as relative time (e.g., "5 minutes ago").
        
        Args:
            dt: Datetime to format
        
        Returns:
            Relative time string
        """
        now = datetime.now()
        
        # Handle future times
        if dt > now:
            diff = dt - now
            return TimeFormatter._format_future(diff)
        
        # Handle past times
        diff = now - dt
        return TimeFormatter._format_past(diff)
    
    @staticmethod
    def _format_past(diff: timedelta) -> str:
        """Format past time difference."""
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
        elif seconds < 2592000:
            weeks = int(seconds / 604800)
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        else:
            months = int(seconds / 2592000)
            return f"{months} month{'s' if months != 1 else ''} ago"
    
    @staticmethod
    def _format_future(diff: timedelta) -> str:
        """Format future time difference."""
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return "in a few seconds"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"in {minutes} minute{'s' if minutes != 1 else ''}"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"in {hours} hour{'s' if hours != 1 else ''}"
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f"in {days} day{'s' if days != 1 else ''}"
        else:
            weeks = int(seconds / 604800)
            return f"in {weeks} week{'s' if weeks != 1 else ''}"
    
    @staticmethod
    def format_smart(dt: datetime) -> str:
        """
        Format datetime intelligently based on how recent it is.
        
        - Recent: Relative time (5 minutes ago)
        - Today: Time only (10:30 AM)
        - This week: Day and time (Mon 10:30 AM)
        - Older: Full date (Jan 15, 2024)
        
        Args:
            dt: Datetime to format
        
        Returns:
            Formatted datetime string
        """
        now = datetime.now()
        diff = now - dt
        
        # Recent (< 1 hour): relative time
        if diff.total_seconds() < 3600:
            return TimeFormatter.format_relative(dt)
        
        # Today: time only
        if dt.date() == now.date():
            return dt.strftime("%I:%M %p")
        
        # This week: day and time
        if diff.days < 7:
            return dt.strftime("%a %I:%M %p")
        
        # This year: month and day
        if dt.year == now.year:
            return dt.strftime("%b %d")
        
        # Older: full date
        return dt.strftime("%b %d, %Y")
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """
        Format duration in seconds to human-readable string.
        
        Args:
            seconds: Duration in seconds
        
        Returns:
            Formatted duration (e.g., "2h 30m", "45s")
        """
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            if secs > 0:
                return f"{minutes}m {secs}s"
            return f"{minutes}m"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            if minutes > 0:
                return f"{hours}h {minutes}m"
            return f"{hours}h"
        else:
            days = int(seconds / 86400)
            hours = int((seconds % 86400) / 3600)
            if hours > 0:
                return f"{days}d {hours}h"
            return f"{days}d"
    
    @staticmethod
    def format_timestamp(dt: datetime, include_seconds: bool = False) -> str:
        """
        Format datetime as timestamp.
        
        Args:
            dt: Datetime to format
            include_seconds: Whether to include seconds
        
        Returns:
            Formatted timestamp (e.g., "2024-01-15 10:30:45")
        """
        if include_seconds:
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M")


class TextFormatter:
    """Format text with consistent styling."""
    
    @staticmethod
    def truncate_address(address: str, start_chars: int = 8, end_chars: int = 8) -> str:
        """
        Truncate Solana address for display.
        
        Args:
            address: Full Solana address
            start_chars: Number of characters to show at start
            end_chars: Number of characters to show at end
        
        Returns:
            Truncated address (e.g., "ABC12345...XYZ98765")
        """
        if len(address) <= start_chars + end_chars:
            return address
        
        return f"{address[:start_chars]}...{address[-end_chars:]}"
    
    @staticmethod
    def truncate_hash(tx_hash: str, chars: int = 8) -> str:
        """
        Truncate transaction hash for display.
        
        Args:
            tx_hash: Full transaction hash
            chars: Number of characters to show at start
        
        Returns:
            Truncated hash (e.g., "ABC12345...")
        """
        if len(tx_hash) <= chars:
            return tx_hash
        
        return f"{tx_hash[:chars]}..."
    
    @staticmethod
    def format_list(items: list, bullet: str = "•") -> str:
        """
        Format list with bullet points.
        
        Args:
            items: List of items to format
            bullet: Bullet character to use
        
        Returns:
            Formatted list string
        """
        if not items:
            return ""
        
        return "\n".join(f"{bullet} {item}" for item in items)
    
    @staticmethod
    def format_numbered_list(items: list) -> str:
        """
        Format list with numbers.
        
        Args:
            items: List of items to format
        
        Returns:
            Formatted numbered list string
        """
        if not items:
            return ""
        
        return "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))
    
    @staticmethod
    def format_key_value(data: dict, separator: str = ": ", indent: str = "") -> str:
        """
        Format dictionary as key-value pairs.
        
        Args:
            data: Dictionary to format
            separator: Separator between key and value
            indent: Indentation for each line
        
        Returns:
            Formatted key-value string
        """
        if not data:
            return ""
        
        lines = []
        for key, value in data.items():
            # Format key (capitalize and replace underscores)
            formatted_key = key.replace("_", " ").title()
            lines.append(f"{indent}{formatted_key}{separator}{value}")
        
        return "\n".join(lines)
    
    @staticmethod
    def add_emoji_status(text: str, status: str) -> str:
        """
        Add status emoji to text.
        
        Args:
            text: Text to add emoji to
            status: Status type (active, paused, error, warning, success, info)
        
        Returns:
            Text with emoji prefix
        """
        emoji_map = {
            "active": "🟢",
            "paused": "🔴",
            "error": "❌",
            "warning": "🟡",
            "success": "✅",
            "info": "ℹ️",
            "pending": "⏳",
            "retry": "🔄",
        }
        
        emoji = emoji_map.get(status.lower(), "")
        return f"{emoji} {text}" if emoji else text
    
    @staticmethod
    def format_progress_bar(current: int, total: int, width: int = 10) -> str:
        """
        Format progress bar.
        
        Args:
            current: Current progress value
            total: Total value
            width: Width of progress bar in characters
        
        Returns:
            Progress bar string (e.g., "████████░░ 80%")
        """
        if total == 0:
            return "░" * width + " 0%"
        
        percentage = min(100, int((current / total) * 100))
        filled = int((current / total) * width)
        empty = width - filled
        
        bar = "█" * filled + "░" * empty
        return f"{bar} {percentage}%"
    
    @staticmethod
    def sanitize_markdown(text: str) -> str:
        """
        Escape Telegram markdown special characters.
        
        Args:
            text: Text to sanitize
        
        Returns:
            Sanitized text safe for Telegram markdown
        """
        # Escape special markdown characters
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        for char in special_chars:
            text = text.replace(char, f"\\{char}")
        
        return text
    
    @staticmethod
    def format_code_block(text: str, language: str = "") -> str:
        """
        Format text as code block.
        
        Args:
            text: Text to format
            language: Programming language for syntax highlighting
        
        Returns:
            Formatted code block
        """
        return f"```{language}\n{text}\n```"
    
    @staticmethod
    def format_inline_code(text: str) -> str:
        """
        Format text as inline code.
        
        Args:
            text: Text to format
        
        Returns:
            Formatted inline code
        """
        return f"`{text}`"


class EmojiFormatter:
    """Emoji constants for consistent usage."""
    
    # Status indicators
    ACTIVE = "🟢"
    PAUSED = "🔴"
    WARNING = "🟡"
    INFO = "⚪"
    
    # Action indicators
    SUCCESS = "✅"
    ERROR = "❌"
    PENDING = "⏳"
    RETRY = "🔄"
    
    # Category emojis
    MONEY = "💰"
    STATS = "📊"
    SETTINGS = "⚙️"
    SECURITY = "🔒"
    COMMANDS = "📱"
    AI = "🤖"
    STRATEGIES = "🎯"
    WALLET = "👛"
    CHART = "📈"
    ALERT = "⚠️"
    INFO_ICON = "ℹ️"
    ROCKET = "🚀"
    FIRE = "🔥"
    TROPHY = "🏆"
    
    # Trend indicators
    UP = "↑"
    DOWN = "↓"
    NEUTRAL = "→"
    
    @staticmethod
    def get_trend_emoji(value: float) -> str:
        """
        Get trend emoji based on value.
        
        Args:
            value: Value to check (positive = up, negative = down)
        
        Returns:
            Trend emoji
        """
        if value > 0:
            return EmojiFormatter.UP
        elif value < 0:
            return EmojiFormatter.DOWN
        return EmojiFormatter.NEUTRAL
    
    @staticmethod
    def get_status_emoji(status: str) -> str:
        """
        Get status emoji.
        
        Args:
            status: Status string
        
        Returns:
            Status emoji
        """
        status_map = {
            "active": EmojiFormatter.ACTIVE,
            "running": EmojiFormatter.ACTIVE,
            "paused": EmojiFormatter.PAUSED,
            "stopped": EmojiFormatter.PAUSED,
            "warning": EmojiFormatter.WARNING,
            "error": EmojiFormatter.ERROR,
            "success": EmojiFormatter.SUCCESS,
            "pending": EmojiFormatter.PENDING,
            "info": EmojiFormatter.INFO,
        }
        
        return status_map.get(status.lower(), EmojiFormatter.INFO)


# Convenience functions for common formatting tasks
def format_sol(amount: float, decimals: int = 4) -> str:
    """Format SOL amount."""
    return NumberFormatter.format_sol(amount, decimals)


def format_usd(amount: float, decimals: int = 2) -> str:
    """Format USD amount."""
    return NumberFormatter.format_usd(amount, decimals)


def format_percentage(value: float, decimals: int = 1, show_sign: bool = True) -> str:
    """Format percentage."""
    return NumberFormatter.format_percentage(value, decimals, show_sign)


def format_relative_time(dt: datetime) -> str:
    """Format relative time."""
    return TimeFormatter.format_relative(dt)


def format_smart_time(dt: datetime) -> str:
    """Format time intelligently."""
    return TimeFormatter.format_smart(dt)


def truncate_address(address: str, start_chars: int = 8, end_chars: int = 8) -> str:
    """Truncate Solana address."""
    return TextFormatter.truncate_address(address, start_chars, end_chars)


def add_status_emoji(text: str, status: str) -> str:
    """Add status emoji to text."""
    return TextFormatter.add_emoji_status(text, status)
