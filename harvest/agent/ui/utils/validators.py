"""Input validation utilities for Telegram bot."""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class InputValidator:
    """Utilities for validating user inputs."""
    
    @staticmethod
    def validate_wallet_address(address: str) -> str:
        """
        Validate Solana wallet address format.
        
        Args:
            address: Wallet address to validate
            
        Returns:
            Validated address
            
        Raises:
            ValueError: If address is invalid
        """
        if not address:
            raise ValueError("Wallet address cannot be empty")
        
        # Remove whitespace
        address = address.strip()
        
        # Solana addresses are base58 encoded and typically 32-44 characters
        if len(address) < 32 or len(address) > 44:
            raise ValueError("Invalid wallet address length. Must be 32-44 characters.")
        
        # Check if address contains only valid base58 characters
        # Base58 alphabet: 123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz
        base58_pattern = re.compile(r'^[1-9A-HJ-NP-Za-km-z]+$')
        if not base58_pattern.match(address):
            raise ValueError("Invalid wallet address format. Must be base58 encoded.")
        
        return address
    
    @staticmethod
    def validate_amount(amount: float, min_val: float = 0.0, max_val: Optional[float] = None) -> float:
        """
        Validate amount value.
        
        Args:
            amount: Amount to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value (optional)
            
        Returns:
            Validated amount
            
        Raises:
            ValueError: If amount is invalid
        """
        if not isinstance(amount, (int, float)):
            raise ValueError("Amount must be a number")
        
        if amount < min_val:
            raise ValueError(f"Amount must be at least {min_val}")
        
        if max_val is not None and amount > max_val:
            raise ValueError(f"Amount must not exceed {max_val}")
        
        return float(amount)
    
    @staticmethod
    def validate_token_symbol(symbol: str) -> str:
        """
        Validate token symbol format.
        
        Args:
            symbol: Token symbol to validate
            
        Returns:
            Validated symbol
            
        Raises:
            ValueError: If symbol is invalid
        """
        if not symbol:
            raise ValueError("Token symbol cannot be empty")
        
        # Remove whitespace and convert to uppercase
        symbol = symbol.strip().upper()
        
        # Token symbols are typically 2-10 characters, alphanumeric
        if len(symbol) < 2 or len(symbol) > 10:
            raise ValueError("Token symbol must be 2-10 characters")
        
        if not symbol.isalnum():
            raise ValueError("Token symbol must be alphanumeric")
        
        return symbol
    
    @staticmethod
    def validate_user_id(user_id: str) -> str:
        """
        Validate Telegram user ID format.
        
        Args:
            user_id: User ID to validate
            
        Returns:
            Validated user ID
            
        Raises:
            ValueError: If user ID is invalid
        """
        if not user_id:
            raise ValueError("User ID cannot be empty")
        
        # User IDs should be numeric strings
        if not user_id.isdigit():
            raise ValueError("User ID must be numeric")
        
        return user_id
    
    @staticmethod
    def validate_message_text(text: str, max_length: int = 4096) -> str:
        """
        Validate message text length.
        
        Args:
            text: Message text to validate
            max_length: Maximum allowed length (Telegram limit is 4096)
            
        Returns:
            Validated text
            
        Raises:
            ValueError: If text is invalid
        """
        if not text:
            raise ValueError("Message text cannot be empty")
        
        if len(text) > max_length:
            raise ValueError(f"Message text exceeds maximum length of {max_length} characters")
        
        return text
    
    @staticmethod
    def sanitize_string(text: str, max_length: int = 1000) -> str:
        """
        Sanitize user input string.
        
        Args:
            text: Text to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized text
            
        Raises:
            ValueError: If text is invalid
        """
        if not text:
            raise ValueError("Text cannot be empty")
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Check length
        if len(text) > max_length:
            raise ValueError(f"Text exceeds maximum length of {max_length} characters")
        
        # Remove null bytes and other control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
        
        return text
    
    @staticmethod
    def is_valid_command(command: str) -> bool:
        """
        Check if string is a valid command format.
        
        Args:
            command: Command string to check
            
        Returns:
            True if valid command format, False otherwise
        """
        if not command:
            return False
        
        # Commands start with / and contain only alphanumeric and underscore
        command_pattern = re.compile(r'^/[a-zA-Z_][a-zA-Z0-9_]*$')
        return bool(command_pattern.match(command))
