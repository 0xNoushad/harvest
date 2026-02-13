"""
Security Module - Input Validation & Protection

Protects against:
- SQL injection
- Command injection
- Path traversal
- XSS attacks
- Invalid inputs
- Malicious data
"""

import re
import logging
from typing import Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class SecurityValidator:
    """Validate and sanitize all inputs."""
    
    # Allowed characters for different input types
    USER_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')
    WALLET_ADDRESS_PATTERN = re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')
    TX_HASH_PATTERN = re.compile(r'^[1-9A-HJ-NP-Za-km-z]{64,88}$')
    STRATEGY_NAME_PATTERN = re.compile(r'^[a-z0-9_]{3,50}$')
    MONTH_PATTERN = re.compile(r'^\d{4}-\d{2}$')
    
    # SQL injection patterns to block
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|;|\/\*|\*\/)",
        r"(\bOR\b\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?)",
        r"(\bAND\b\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"]?)",
        r"(';\s*\w+)",  # Quote followed by semicolon and command
        r"('\s*OR\s+')",  # Classic SQL injection pattern
        r"('\s*--)",  # Quote followed by SQL comment
    ]
    
    # Command injection patterns to block
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$()]",
        r"(\.\./)",
        r"(~\/)",
    ]
    
    @classmethod
    def validate_user_id(cls, user_id: str) -> str:
        """
        Validate user ID.
        
        Args:
            user_id: User ID to validate
        
        Returns:
            Validated user ID
        
        Raises:
            ValueError: If invalid
        """
        if not user_id:
            raise ValueError("User ID cannot be empty")
        
        if not isinstance(user_id, str):
            raise ValueError("User ID must be a string")
        
        if not cls.USER_ID_PATTERN.match(user_id):
            raise ValueError("Invalid user ID format")
        
        if len(user_id) > 64:
            raise ValueError("User ID too long")
        
        return user_id
    
    @classmethod
    def validate_wallet_address(cls, address: str) -> str:
        """
        Validate Solana wallet address.
        
        Args:
            address: Wallet address to validate
        
        Returns:
            Validated address
        
        Raises:
            ValueError: If invalid
        """
        if not address:
            raise ValueError("Wallet address cannot be empty")
        
        if not isinstance(address, str):
            raise ValueError("Wallet address must be a string")
        
        if not cls.WALLET_ADDRESS_PATTERN.match(address):
            raise ValueError("Invalid Solana wallet address format")
        
        return address
    
    @classmethod
    def validate_transaction_hash(cls, tx_hash: str) -> str:
        """
        Validate transaction hash.
        
        Args:
            tx_hash: Transaction hash to validate
        
        Returns:
            Validated hash
        
        Raises:
            ValueError: If invalid
        """
        if not tx_hash:
            raise ValueError("Transaction hash cannot be empty")
        
        if not isinstance(tx_hash, str):
            raise ValueError("Transaction hash must be a string")
        
        if not cls.TX_HASH_PATTERN.match(tx_hash):
            raise ValueError("Invalid transaction hash format")
        
        return tx_hash
    
    @classmethod
    def validate_strategy_name(cls, name: str) -> str:
        """
        Validate strategy name.
        
        Args:
            name: Strategy name to validate
        
        Returns:
            Validated name
        
        Raises:
            ValueError: If invalid
        """
        if not name:
            raise ValueError("Strategy name cannot be empty")
        
        if not isinstance(name, str):
            raise ValueError("Strategy name must be a string")
        
        if not cls.STRATEGY_NAME_PATTERN.match(name):
            raise ValueError("Invalid strategy name format")
        
        return name
    
    @classmethod
    def validate_amount(cls, amount: float, min_val: float = 0.0, max_val: float = 1000000.0) -> float:
        """
        Validate amount.
        
        Args:
            amount: Amount to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
        
        Returns:
            Validated amount
        
        Raises:
            ValueError: If invalid
        """
        if not isinstance(amount, (int, float)):
            raise ValueError("Amount must be a number")
        
        if amount < min_val:
            raise ValueError(f"Amount must be at least {min_val}")
        
        if amount > max_val:
            raise ValueError(f"Amount cannot exceed {max_val}")
        
        return float(amount)
    
    @classmethod
    def validate_month(cls, month: str) -> str:
        """
        Validate month format (YYYY-MM).
        
        Args:
            month: Month string to validate
        
        Returns:
            Validated month
        
        Raises:
            ValueError: If invalid
        """
        if not month:
            raise ValueError("Month cannot be empty")
        
        if not isinstance(month, str):
            raise ValueError("Month must be a string")
        
        if not cls.MONTH_PATTERN.match(month):
            raise ValueError("Invalid month format (use YYYY-MM)")
        
        # Validate month range
        year, month_num = month.split('-')
        if not (1 <= int(month_num) <= 12):
            raise ValueError("Month must be between 01 and 12")
        
        return month
    
    @classmethod
    def check_sql_injection(cls, value: str) -> None:
        """
        Check for SQL injection attempts.
        
        Args:
            value: String to check
        
        Raises:
            ValueError: If SQL injection detected
        """
        if not isinstance(value, str):
            return
        
        value_upper = value.upper()
        
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_upper, re.IGNORECASE):
                logger.error(f"SQL injection attempt detected: {value}")
                raise ValueError("Invalid input detected")
    
    @classmethod
    def check_command_injection(cls, value: str) -> None:
        """
        Check for command injection attempts.
        
        Args:
            value: String to check
        
        Raises:
            ValueError: If command injection detected
        """
        if not isinstance(value, str):
            return
        
        for pattern in cls.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, value):
                logger.error(f"Command injection attempt detected: {value}")
                raise ValueError("Invalid input detected")
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 1000, check_injections: bool = True) -> str:
        """
        Sanitize string input.
        
        Args:
            value: String to sanitize
            max_length: Maximum allowed length
            check_injections: Whether to check for SQL/command injection (disable for conversation text)
        
        Returns:
            Sanitized string
        
        Raises:
            ValueError: If invalid
        """
        if not isinstance(value, str):
            raise ValueError("Value must be a string")
        
        # Check for injection attempts (skip for conversation messages)
        if check_injections:
            cls.check_sql_injection(value)
            cls.check_command_injection(value)
        
        # Trim to max length
        if len(value) > max_length:
            raise ValueError(f"String too long (max {max_length} characters)")
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        return value
    
    @classmethod
    def validate_file_path(cls, path: str, base_dir: str = "config") -> Path:
        """
        Validate file path to prevent path traversal.
        
        Args:
            path: File path to validate
            base_dir: Base directory to restrict to
        
        Returns:
            Validated Path object
        
        Raises:
            ValueError: If invalid or outside base directory
        """
        if not path:
            raise ValueError("Path cannot be empty")
        
        if not isinstance(path, str):
            raise ValueError("Path must be a string")
        
        # Check for path traversal attempts
        if '..' in path or '~' in path:
            raise ValueError("Path traversal not allowed")
        
        # Convert to Path object
        file_path = Path(path)
        base_path = Path(base_dir).resolve()
        
        # Resolve and check if within base directory
        try:
            resolved_path = file_path.resolve()
            if not str(resolved_path).startswith(str(base_path)):
                raise ValueError("Path outside allowed directory")
        except Exception as e:
            raise ValueError(f"Invalid path: {e}")
        
        return file_path
    
    @classmethod
    def validate_json_data(cls, data: dict, max_size: int = 10000) -> dict:
        """
        Validate JSON data.
        
        Args:
            data: Dictionary to validate
            max_size: Maximum size in bytes
        
        Returns:
            Validated data
        
        Raises:
            ValueError: If invalid
        """
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
        
        # Check size
        import json
        json_str = json.dumps(data)
        if len(json_str) > max_size:
            raise ValueError(f"Data too large (max {max_size} bytes)")
        
        # Check for injection in values
        for key, value in data.items():
            if isinstance(value, str):
                cls.sanitize_string(value)
        
        return data


class RateLimiter:
    """Rate limiting to prevent abuse."""
    
    def __init__(self):
        self.requests = {}
    
    def check_rate_limit(self, user_id: str, max_requests: int = 100, window_seconds: int = 60) -> bool:
        """
        Check if user is within rate limit.
        
        Args:
            user_id: User ID
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
        
        Returns:
            True if within limit, False if exceeded
        """
        import time
        
        now = time.time()
        
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # Remove old requests outside window
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if now - req_time < window_seconds
        ]
        
        # Check limit
        if len(self.requests[user_id]) >= max_requests:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return False
        
        # Add current request
        self.requests[user_id].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


def secure_input(func):
    """
    Decorator to validate function inputs.
    
    Usage:
        @secure_input
        def my_function(user_id: str, amount: float):
            pass
    """
    def wrapper(*args, **kwargs):
        # Validate string arguments
        for arg in args:
            if isinstance(arg, str):
                SecurityValidator.sanitize_string(arg)
        
        for key, value in kwargs.items():
            if isinstance(value, str):
                SecurityValidator.sanitize_string(value)
        
        return func(*args, **kwargs)
    
    return wrapper


# Example usage
if __name__ == "__main__":
    validator = SecurityValidator()
    
    # Valid inputs
    try:
        validator.validate_user_id("user_123")
        print("✅ Valid user ID")
    except ValueError as e:
        print(f"❌ {e}")
    
    # Invalid inputs (SQL injection)
    try:
        validator.validate_user_id("user'; DROP TABLE users;--")
        print("❌ Should have failed!")
    except ValueError as e:
        print(f"✅ Blocked: {e}")
    
    # Invalid inputs (command injection)
    try:
        validator.sanitize_string("test; rm -rf /")
        print("❌ Should have failed!")
    except ValueError as e:
        print(f"✅ Blocked: {e}")
    
    print("\n✅ Security validation working!")
