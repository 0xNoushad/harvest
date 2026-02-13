"""
Tests for mock response utilities and fixtures.

This test suite verifies that the mock_rpc_response(), mock_api_response(),
and fixture library work correctly and provide realistic test data.
"""

import pytest
from unittest.mock import MagicMock
from tests.test_harness import TestHarness
from tests.fixtures import (
    HELIUS_FIXTURES,
    JUPITER_FIXTURES,
    MARINADE_FIXTURES,
    GROQ_FIXTURES,
    COINGECKO_FIXTURES,
    TELEGRAM_FIXTURES,
    get_fixture,
    list_fixtures
)


class TestMockRPCResponse:
    """Test mock_rpc_response() functionality."""
    
    def test_basic_rpc_response(self):
        """Test creating a basic RPC response."""
        harness = TestHarness()
        response = harness.mock_rpc_response("getBalance", {"value": 1000000000})
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert response["result"]["value"] == 1000000000
        assert "error" not in response
    
    def test_rpc_error_response(self):
        """Test creating an RPC error response."""
        harness = TestHarness()
        error = {"code": -32602, "message": "Invalid params"}
        response = harness.mock_rpc_response("getBalance", None, error=error)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" not in response
        assert response["error"]["code"] == -32602
        assert response["error"]["message"] == "Invalid params"
    
    def test_rpc_response_with_context(self):
        """Test creating an RPC response with context."""
        harness = TestHarness()
        context = {"slot": 123456, "apiVersion": "1.14.0"}
        response = harness.mock_rpc_response(
            "getAccountInfo",
            {"value": {"lamports": 1000000}},
            context=context
        )
        
        assert response["context"]["slot"] == 123456
        assert response["context"]["apiVersion"] == "1.14.0"


class TestMockAPIResponse:
    """Test mock_api_response() functionality."""
    
    def test_basic_api_response(self):
        """Test creating a basic API response."""
        harness = TestHarness()
        response = harness.mock_api_response(
            "jupiter",
            "/quote",
            {"inAmount": "1000000", "outAmount": "950000"}
        )
        
        assert response.status_code == 200
        assert response.ok is True
        assert response.json()["inAmount"] == "1000000"
        assert response.json()["outAmount"] == "950000"
    
    def test_api_error_response(self):
        """Test creating an API error response."""
        harness = TestHarness()
        response = harness.mock_api_response(
            "groq",
            "/chat/completions",
            {"error": "Rate limit exceeded"},
            status_code=429
        )
        
        assert response.status_code == 429
        assert response.ok is False
        assert response.json()["error"] == "Rate limit exceeded"
    
    def test_api_response_with_headers(self):
        """Test creating an API response with custom headers."""
        harness = TestHarness()
        headers = {"Retry-After": "60", "X-RateLimit-Remaining": "0"}
        response = harness.mock_api_response(
            "groq",
            "/chat/completions",
            {"error": "Rate limit exceeded"},
            status_code=429,
            headers=headers
        )
        
        assert response.headers["Retry-After"] == "60"
        assert response.headers["X-RateLimit-Remaining"] == "0"
    
    def test_api_response_raise_for_status(self):
        """Test that raise_for_status works correctly."""
        harness = TestHarness()
        
        # Success response should not raise
        success_response = harness.mock_api_response(
            "jupiter", "/quote", {"success": True}, status_code=200
        )
        success_response.raise_for_status()  # Should not raise
        
        # Error response should raise
        error_response = harness.mock_api_response(
            "jupiter", "/quote", {"error": "Not found"}, status_code=404
        )
        
        with pytest.raises(Exception):
            error_response.raise_for_status()
    
    def test_api_response_non_json(self):
        """Test creating an API response with non-JSON data."""
        harness = TestHarness()
        response = harness.mock_api_response(
            "service",
            "/endpoint",
            "Plain text response",
            status_code=200
        )
        
        assert response.text == "Plain text response"
        with pytest.raises(ValueError):
            response.json()


class TestHeliusFixtures:
    """Test Helius RPC fixtures."""
    
    def test_get_balance_success_fixture(self):
        """Test get_balance_success fixture."""
        fixture = HELIUS_FIXTURES["get_balance_success"]
        
        assert fixture["jsonrpc"] == "2.0"
        assert fixture["result"]["value"] == 1000000000
        assert "context" in fixture["result"]
    
    def test_get_balance_zero_fixture(self):
        """Test get_balance_zero fixture."""
        fixture = HELIUS_FIXTURES["get_balance_zero"]
        
        assert fixture["result"]["value"] == 0
    
    def test_get_token_accounts_fixture(self):
        """Test get_token_accounts_success fixture."""
        fixture = HELIUS_FIXTURES["get_token_accounts_success"]
        
        assert len(fixture["result"]["value"]) > 0
        account = fixture["result"]["value"][0]
        assert "account" in account
        assert "pubkey" in account
        assert account["account"]["data"]["parsed"]["info"]["tokenAmount"]["uiAmount"] == 1.0
    
    def test_rpc_error_fixtures(self):
        """Test RPC error fixtures."""
        invalid_params = HELIUS_FIXTURES["rpc_error_invalid_params"]
        assert invalid_params["error"]["code"] == -32602
        
        rate_limit = HELIUS_FIXTURES["rpc_error_rate_limit"]
        assert rate_limit["error"]["code"] == 429


class TestJupiterFixtures:
    """Test Jupiter API fixtures."""
    
    def test_quote_success_fixture(self):
        """Test quote_success fixture."""
        fixture = JUPITER_FIXTURES["quote_success"]
        
        assert fixture["inputMint"] == "So11111111111111111111111111111111111111112"
        assert fixture["inAmount"] == "1000000000"
        assert fixture["outAmount"] == "100000000"
        assert len(fixture["routePlan"]) > 0
    
    def test_swap_success_fixture(self):
        """Test swap_success fixture."""
        fixture = JUPITER_FIXTURES["swap_success"]
        
        assert "swapTransaction" in fixture
        assert "lastValidBlockHeight" in fixture
    
    def test_tokens_list_fixture(self):
        """Test tokens_list fixture."""
        fixture = JUPITER_FIXTURES["tokens_list"]
        
        assert len(fixture["tokens"]) >= 2
        sol_token = fixture["tokens"][0]
        assert sol_token["symbol"] == "SOL"
        assert sol_token["decimals"] == 9


class TestGroqFixtures:
    """Test Groq API fixtures."""
    
    def test_chat_completion_success_fixture(self):
        """Test chat_completion_success fixture."""
        fixture = GROQ_FIXTURES["chat_completion_success"]
        
        assert fixture["object"] == "chat.completion"
        assert len(fixture["choices"]) > 0
        assert fixture["choices"][0]["message"]["role"] == "assistant"
        assert "usage" in fixture
    
    def test_chat_completion_error_fixtures(self):
        """Test chat completion error fixtures."""
        rate_limit = GROQ_FIXTURES["chat_completion_error_rate_limit"]
        assert rate_limit["error"]["type"] == "rate_limit_error"
        
        context_length = GROQ_FIXTURES["chat_completion_error_context_length"]
        assert context_length["error"]["type"] == "invalid_request_error"


class TestCoinGeckoFixtures:
    """Test CoinGecko API fixtures."""
    
    def test_simple_price_success_fixture(self):
        """Test simple_price_success fixture."""
        fixture = COINGECKO_FIXTURES["simple_price_success"]
        
        assert "solana" in fixture
        assert fixture["solana"]["usd"] == 127.50
        assert "usd_24h_change" in fixture["solana"]
    
    def test_simple_price_multiple_fixture(self):
        """Test simple_price_multiple fixture."""
        fixture = COINGECKO_FIXTURES["simple_price_multiple"]
        
        assert "solana" in fixture
        assert "usd-coin" in fixture
        assert "bonk" in fixture


class TestTelegramFixtures:
    """Test Telegram API fixtures."""
    
    def test_send_message_success_fixture(self):
        """Test send_message_success fixture."""
        fixture = TELEGRAM_FIXTURES["send_message_success"]
        
        assert fixture["ok"] is True
        assert "result" in fixture
        assert fixture["result"]["message_id"] == 123
    
    def test_send_message_error_fixtures(self):
        """Test send message error fixtures."""
        blocked = TELEGRAM_FIXTURES["send_message_error_blocked"]
        assert blocked["ok"] is False
        assert blocked["error_code"] == 403


class TestFixtureHelpers:
    """Test fixture helper functions."""
    
    def test_get_fixture(self):
        """Test get_fixture() function."""
        balance = get_fixture("helius", "get_balance_success")
        assert balance["result"]["value"] == 1000000000
        
        quote = get_fixture("jupiter", "quote_success")
        assert quote["inAmount"] == "1000000000"
    
    def test_get_fixture_invalid_service(self):
        """Test get_fixture() with invalid service."""
        with pytest.raises(KeyError):
            get_fixture("invalid_service", "some_fixture")
    
    def test_get_fixture_invalid_name(self):
        """Test get_fixture() with invalid fixture name."""
        with pytest.raises(KeyError):
            get_fixture("helius", "invalid_fixture")
    
    def test_list_fixtures_all(self):
        """Test list_fixtures() for all services."""
        fixtures = list_fixtures()
        
        assert "helius" in fixtures
        assert "jupiter" in fixtures
        assert "groq" in fixtures
        assert len(fixtures["helius"]) > 0
    
    def test_list_fixtures_specific_service(self):
        """Test list_fixtures() for specific service."""
        fixtures = list_fixtures("helius")
        
        assert "helius" in fixtures
        assert "get_balance_success" in fixtures["helius"]
        assert "get_balance_zero" in fixtures["helius"]


class TestTestHarnessFixtureMethods:
    """Test TestHarness convenience methods for fixtures."""
    
    def test_harness_get_fixture(self):
        """Test harness.get_fixture() method."""
        harness = TestHarness()
        balance = harness.get_fixture("helius", "get_balance_success")
        
        assert balance["result"]["value"] == 1000000000
    
    def test_harness_list_fixtures(self):
        """Test harness.list_fixtures() method."""
        harness = TestHarness()
        fixtures = harness.list_fixtures("jupiter")
        
        assert "jupiter" in fixtures
        assert len(fixtures["jupiter"]) > 0
    
    def test_mock_helius_rpc_with_fixture(self):
        """Test mock_helius_rpc() with fixture."""
        harness = TestHarness()
        response = harness.mock_helius_rpc("getBalance", "get_balance_success")
        
        assert response["result"]["value"] == 1000000000
    
    def test_mock_helius_rpc_with_custom_response(self):
        """Test mock_helius_rpc() with custom response."""
        harness = TestHarness()
        response = harness.mock_helius_rpc(
            "getBalance",
            custom_response={"value": 2000000000}
        )
        
        assert response["result"]["value"] == 2000000000
    
    def test_mock_jupiter_api_with_fixture(self):
        """Test mock_jupiter_api() with fixture."""
        harness = TestHarness()
        response = harness.mock_jupiter_api("/quote", "quote_success")
        
        assert response.json()["inAmount"] == "1000000000"
    
    def test_mock_jupiter_api_with_custom_response(self):
        """Test mock_jupiter_api() with custom response."""
        harness = TestHarness()
        response = harness.mock_jupiter_api(
            "/quote",
            custom_response={"outAmount": "999999"}
        )
        
        assert response.json()["outAmount"] == "999999"
    
    def test_mock_groq_api_with_fixture(self):
        """Test mock_groq_api() with fixture."""
        harness = TestHarness()
        response = harness.mock_groq_api("chat_completion_success")
        
        assert response.json()["object"] == "chat.completion"
    
    def test_mock_coingecko_api_with_fixture(self):
        """Test mock_coingecko_api() with fixture."""
        harness = TestHarness()
        response = harness.mock_coingecko_api("simple_price_success")
        
        assert response.json()["solana"]["usd"] == 127.50


class TestIntegrationScenarios:
    """Test realistic integration scenarios using fixtures."""
    
    def test_wallet_balance_check_scenario(self):
        """Test a complete wallet balance check scenario."""
        harness = TestHarness()
        
        # Mock RPC call to get balance
        rpc_response = harness.mock_helius_rpc("getBalance", "get_balance_success")
        balance_lamports = rpc_response["result"]["value"]
        balance_sol = balance_lamports / 1_000_000_000
        
        assert balance_sol == 1.0
    
    def test_jupiter_swap_scenario(self):
        """Test a complete Jupiter swap scenario."""
        harness = TestHarness()
        
        # Get quote
        quote_response = harness.mock_jupiter_api("/quote", "quote_success")
        quote = quote_response.json()
        
        assert quote["inAmount"] == "1000000000"
        assert quote["outAmount"] == "100000000"
        
        # Execute swap
        swap_response = harness.mock_jupiter_api("/swap", "swap_success")
        swap = swap_response.json()
        
        assert "swapTransaction" in swap
    
    def test_ai_chat_scenario(self):
        """Test a complete AI chat scenario."""
        harness = TestHarness()
        
        # Get AI response
        api_response = harness.mock_groq_api("chat_completion_success")
        completion = api_response.json()
        
        message = completion["choices"][0]["message"]["content"]
        assert len(message) > 0
        assert "balance" in message.lower()
    
    def test_price_check_scenario(self):
        """Test a complete price check scenario."""
        harness = TestHarness()
        
        # Get price from CoinGecko
        api_response = harness.mock_coingecko_api("simple_price_success")
        prices = api_response.json()
        
        sol_price = prices["solana"]["usd"]
        sol_change = prices["solana"]["usd_24h_change"]
        
        assert sol_price == 127.50
        assert sol_change == 5.2
    
    def test_error_handling_scenario(self):
        """Test error handling with error fixtures."""
        harness = TestHarness()
        
        # Test RPC rate limit error
        rpc_error = harness.mock_helius_rpc("getBalance", "rpc_error_rate_limit")
        assert rpc_error["error"]["code"] == 429
        
        # Test API rate limit error
        api_error = harness.mock_groq_api("chat_completion_error_rate_limit")
        assert api_error.json()["error"]["type"] == "rate_limit_error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
