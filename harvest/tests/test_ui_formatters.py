"""
Tests for UI Formatters

Tests the formatting utilities for numbers, time, and text.
"""

import pytest
from datetime import datetime, timedelta
from agent.ui.formatters import (
    NumberFormatter, TimeFormatter, TextFormatter, EmojiFormatter,
    format_sol, format_usd, format_percentage, format_relative_time,
    format_smart_time, truncate_address, add_status_emoji
)


class TestNumberFormatter:
    """Test number formatting."""
    
    def test_format_sol_basic(self):
        """Test basic SOL formatting."""
        assert format_sol(1.2345) == "1.2345 SOL"
        assert format_sol(0) == "0 SOL"
    
    def test_format_sol_small_amounts(self):
        """Test SOL formatting for very small amounts."""
        result = format_sol(0.00001)
        assert "SOL" in result
        assert "0.00001" in result
    
    def test_format_usd_basic(self):
        """Test basic USD formatting."""
        assert format_usd(1234.56) == "$1,234.56"
        assert format_usd(0) == "$0.00"
    
    def test_format_usd_large_amounts(self):
        """Test USD formatting for large amounts."""
        assert format_usd(1234567.89) == "$1,234,567.89"
    
    def test_format_percentage_positive(self):
        """Test percentage formatting for positive values."""
        assert format_percentage(5.2) == "+5.2%"
        assert format_percentage(5.2, show_sign=False) == "5.2%"
    
    def test_format_percentage_negative(self):
        """Test percentage formatting for negative values."""
        assert format_percentage(-3.5) == "-3.5%"
    
    def test_format_percentage_zero(self):
        """Test percentage formatting for zero."""
        assert format_percentage(0) == "0%"
    
    def test_format_large_number_thousands(self):
        """Test large number formatting for thousands."""
        formatter = NumberFormatter()
        assert formatter.format_large_number(1500) == "1.5K"
    
    def test_format_large_number_millions(self):
        """Test large number formatting for millions."""
        formatter = NumberFormatter()
        assert formatter.format_large_number(2500000) == "2.5M"
    
    def test_format_large_number_billions(self):
        """Test large number formatting for billions."""
        formatter = NumberFormatter()
        assert formatter.format_large_number(3500000000) == "3.5B"
    
    def test_format_token_amount(self):
        """Test token amount formatting."""
        formatter = NumberFormatter()
        result = formatter.format_token_amount(100.50, "USDC")
        assert "100.50" in result
        assert "USDC" in result
    
    def test_format_with_separators(self):
        """Test number formatting with thousand separators."""
        formatter = NumberFormatter()
        assert formatter.format_with_separators(1234567) == "1,234,567"
        assert formatter.format_with_separators(1234.56, decimals=2) == "1,234.56"


class TestTimeFormatter:
    """Test time formatting."""
    
    def test_format_relative_recent(self):
        """Test relative time formatting for recent times."""
        now = datetime.now()
        recent = now - timedelta(minutes=5)
        result = format_relative_time(recent)
        assert "5 minute" in result or "just now" in result
    
    def test_format_relative_hours(self):
        """Test relative time formatting for hours ago."""
        now = datetime.now()
        hours_ago = now - timedelta(hours=2)
        result = format_relative_time(hours_ago)
        assert "hour" in result
    
    def test_format_relative_days(self):
        """Test relative time formatting for days ago."""
        now = datetime.now()
        days_ago = now - timedelta(days=3)
        result = format_relative_time(days_ago)
        assert "day" in result
    
    def test_format_relative_future(self):
        """Test relative time formatting for future times."""
        now = datetime.now()
        future = now + timedelta(hours=2)
        result = format_relative_time(future)
        assert "in" in result
    
    def test_format_smart_time_recent(self):
        """Test smart time formatting for recent times."""
        now = datetime.now()
        recent = now - timedelta(minutes=30)
        result = format_smart_time(recent)
        assert "minute" in result or "ago" in result
    
    def test_format_smart_time_today(self):
        """Test smart time formatting for today."""
        now = datetime.now()
        result = format_smart_time(now)
        # Should show time or relative
        assert len(result) > 0
    
    def test_format_duration_seconds(self):
        """Test duration formatting for seconds."""
        formatter = TimeFormatter()
        assert formatter.format_duration(45) == "45s"
    
    def test_format_duration_minutes(self):
        """Test duration formatting for minutes."""
        formatter = TimeFormatter()
        result = formatter.format_duration(150)
        assert "2m" in result
    
    def test_format_duration_hours(self):
        """Test duration formatting for hours."""
        formatter = TimeFormatter()
        result = formatter.format_duration(7200)
        assert "2h" in result
    
    def test_format_timestamp(self):
        """Test timestamp formatting."""
        formatter = TimeFormatter()
        dt = datetime(2024, 1, 15, 10, 30, 45)
        result = formatter.format_timestamp(dt, include_seconds=True)
        assert "2024-01-15" in result
        assert "10:30:45" in result


class TestTextFormatter:
    """Test text formatting."""
    
    def test_truncate_address_basic(self):
        """Test basic address truncation."""
        address = "ABC123456789XYZ987654321"
        result = truncate_address(address)
        assert result.startswith("ABC12345")
        assert result.endswith("87654321")
        assert "..." in result
    
    def test_truncate_address_short(self):
        """Test truncation of short addresses."""
        address = "SHORT"
        result = truncate_address(address)
        assert result == address
    
    def test_truncate_hash(self):
        """Test hash truncation."""
        formatter = TextFormatter()
        tx_hash = "ABC123456789XYZ987654321"
        result = formatter.truncate_hash(tx_hash)
        assert result.startswith("ABC12345")
        assert result.endswith("...")
    
    def test_format_list(self):
        """Test list formatting."""
        formatter = TextFormatter()
        items = ["Item 1", "Item 2", "Item 3"]
        result = formatter.format_list(items)
        assert "•" in result
        assert "Item 1" in result
        assert "Item 2" in result
    
    def test_format_numbered_list(self):
        """Test numbered list formatting."""
        formatter = TextFormatter()
        items = ["First", "Second", "Third"]
        result = formatter.format_numbered_list(items)
        assert "1." in result
        assert "2." in result
        assert "3." in result
    
    def test_format_key_value(self):
        """Test key-value formatting."""
        formatter = TextFormatter()
        data = {"user_name": "Alice", "balance": "1.5 SOL"}
        result = formatter.format_key_value(data)
        assert "User Name" in result
        assert "Alice" in result
    
    def test_add_emoji_status_active(self):
        """Test adding status emoji for active status."""
        result = add_status_emoji("Bot Running", "active")
        assert "🟢" in result
        assert "Bot Running" in result
    
    def test_add_emoji_status_error(self):
        """Test adding status emoji for error status."""
        result = add_status_emoji("Failed", "error")
        assert "❌" in result
    
    def test_format_progress_bar(self):
        """Test progress bar formatting."""
        formatter = TextFormatter()
        result = formatter.format_progress_bar(80, 100, width=10)
        assert "█" in result
        assert "80%" in result
    
    def test_format_code_block(self):
        """Test code block formatting."""
        formatter = TextFormatter()
        result = formatter.format_code_block("print('hello')", "python")
        assert "```python" in result
        assert "print('hello')" in result
    
    def test_format_inline_code(self):
        """Test inline code formatting."""
        formatter = TextFormatter()
        result = formatter.format_inline_code("variable")
        assert result == "`variable`"


class TestEmojiFormatter:
    """Test emoji formatting."""
    
    def test_get_trend_emoji_positive(self):
        """Test trend emoji for positive values."""
        assert EmojiFormatter.get_trend_emoji(5.2) == EmojiFormatter.UP
    
    def test_get_trend_emoji_negative(self):
        """Test trend emoji for negative values."""
        assert EmojiFormatter.get_trend_emoji(-3.5) == EmojiFormatter.DOWN
    
    def test_get_trend_emoji_zero(self):
        """Test trend emoji for zero."""
        assert EmojiFormatter.get_trend_emoji(0) == EmojiFormatter.NEUTRAL
    
    def test_get_status_emoji_active(self):
        """Test status emoji for active status."""
        assert EmojiFormatter.get_status_emoji("active") == EmojiFormatter.ACTIVE
    
    def test_get_status_emoji_paused(self):
        """Test status emoji for paused status."""
        assert EmojiFormatter.get_status_emoji("paused") == EmojiFormatter.PAUSED
    
    def test_get_status_emoji_error(self):
        """Test status emoji for error status."""
        assert EmojiFormatter.get_status_emoji("error") == EmojiFormatter.ERROR


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_format_sol_convenience(self):
        """Test format_sol convenience function."""
        result = format_sol(1.5)
        assert "1.5" in result
        assert "SOL" in result
    
    def test_format_usd_convenience(self):
        """Test format_usd convenience function."""
        result = format_usd(100.50)
        assert "$100.50" in result
    
    def test_format_percentage_convenience(self):
        """Test format_percentage convenience function."""
        result = format_percentage(5.2)
        assert "+5.2%" in result
    
    def test_truncate_address_convenience(self):
        """Test truncate_address convenience function."""
        address = "ABC123456789XYZ987654321"
        result = truncate_address(address)
        assert "..." in result
    
    def test_add_status_emoji_convenience(self):
        """Test add_status_emoji convenience function."""
        result = add_status_emoji("Test", "success")
        assert "✅" in result
