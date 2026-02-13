"""Security utilities for Telegram bot."""

import logging
import re
from typing import List

logger = logging.getLogger(__name__)


class SecurityChecker:
    """Security checking utilities for bot operations."""
    
    # Patterns for detecting malicious inputs
    SQL_INJECTION_PATTERNS = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"(\bINSERT\b.*\bINTO\b)",
        r"(\bDELETE\b.*\bFROM\b)",
        r"(\bUPDATE\b.*\bSET\b)",
        r"(--|\#|\/\*)",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"onerror\s*=",
        r"onload\s*=",
        r"onclick\s*=",
        r"<iframe[^>]*>",
        r"<embed[^>]*>",
        r"<object[^>]*>",
    ]
    
    PRIVATE_KEY_KEYWORDS = [
        "private key",
        "secret key",
        "seed phrase",
        "mnemonic",
        "privatekey",
        "secretkey",
        "seedphrase",
    ]
    
    @staticmethod
    def check_sql_injection(text: str) -> bool:
        """
        Check if text contains SQL injection patterns.
        
        Args:
            text: Text to check
            
        Returns:
            True if SQL injection detected, False otherwise
        """
        text_upper = text.upper()
        
        for pattern in SecurityChecker.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_upper, re.IGNORECASE):
                logger.warning(f"SQL injection pattern detected: {pattern}")
                return True
        
        return False
    
    @staticmethod
    def check_xss(text: str) -> bool:
        """
        Check if text contains XSS patterns.
        
        Args:
            text: Text to check
            
        Returns:
            True if XSS detected, False otherwise
        """
        for pattern in SecurityChecker.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"XSS pattern detected: {pattern}")
                return True
        
        return False
    
    @staticmethod
    def check_private_key_request(text: str) -> bool:
        """
        Check if text contains private key related keywords.
        
        Args:
            text: Text to check
            
        Returns:
            True if private key keywords detected, False otherwise
        """
        text_lower = text.lower()
        
        for keyword in SecurityChecker.PRIVATE_KEY_KEYWORDS:
            if keyword in text_lower:
                logger.warning(f"Private key keyword detected: {keyword}")
                return True
        
        return False
    
    @staticmethod
    def sanitize_for_markdown(text: str) -> str:
        """
        Sanitize text for safe Markdown rendering.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text
        """
        # Escape special Markdown characters
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        
        return text
    
    @staticmethod
    def is_rate_limited(user_id: str, max_requests: int, window_seconds: int) -> bool:
        """
        Check if user is rate limited (placeholder - actual implementation in security module).
        
        Args:
            user_id: User ID to check
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            True if rate limited, False otherwise
        """
        # This is a placeholder - actual implementation should use the rate_limiter from security module
        from agent.security.security import rate_limiter
        return not rate_limiter.check_rate_limit(user_id, max_requests, window_seconds)
    
    @staticmethod
    def validate_callback_data(callback_data: str, allowed_prefixes: List[str]) -> bool:
        """
        Validate callback data from inline buttons.
        
        Args:
            callback_data: Callback data to validate
            allowed_prefixes: List of allowed prefixes
            
        Returns:
            True if valid, False otherwise
        """
        if not callback_data:
            return False
        
        # Check if callback data starts with an allowed prefix
        for prefix in allowed_prefixes:
            if callback_data.startswith(prefix):
                return True
        
        logger.warning(f"Invalid callback data prefix: {callback_data}")
        return False
    
    @staticmethod
    def is_private_chat(chat_type: str) -> bool:
        """
        Check if chat is a private chat.
        
        Args:
            chat_type: Chat type from Telegram update
            
        Returns:
            True if private chat, False otherwise
        """
        return chat_type == "private"
    
    @staticmethod
    def mask_sensitive_data(text: str, show_chars: int = 4) -> str:
        """
        Mask sensitive data in text for logging.
        
        Args:
            text: Text containing sensitive data
            show_chars: Number of characters to show at start and end
            
        Returns:
            Masked text
        """
        if len(text) <= show_chars * 2:
            return "*" * len(text)
        
        return f"{text[:show_chars]}{'*' * (len(text) - show_chars * 2)}{text[-show_chars:]}"
