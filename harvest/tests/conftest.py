"""
Pytest configuration and shared fixtures for Harvest testing.

This module provides reusable fixtures, mock factories, and utilities
for all test suites. It implements the TestHarness design from the
testing infrastructure specification.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from datetime import datetime, timedelta

import pytest
from hypothesis import settings, Verbosity

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import TestHarness
from tests.test_harness import TestHarness


# ============================================================================
# Hypothesis Configuration
# ============================================================================

# Configure Hypothesis for property-based testing
settings.register_profile("default", max_examples=100, deadline=None)
settings.register_profile("ci", max_examples=1000, deadline=None)
settings.register_profile("dev", max_examples=20, verbosity=Verbosity.verbose)
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))


# ============================================================================
# Pytest Configuration
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# TestHarness Fixture
# ============================================================================

@pytest.fixture
def test_harness():
    """
    Provide a TestHarness instance for tests.
    
    The TestHarness consolidates all mock factories and utilities into a
    single, easy-to-use interface.
    
    Example:
        def test_command(test_harness):
            update = test_harness.create_mock_telegram_update("start")
            wallet = test_harness.create_mock_wallet(balance=1.5)
    """
    return TestHarness()


# ============================================================================
# Mock Telegram Objects
# ============================================================================

@pytest.fixture
def mock_telegram_update():
    """Factory for creating mock Telegram Update objects."""
    def _create_update(
        command: str,
        user_id: int = 12345,
        chat_id: int = 12345,
        args: Optional[List[str]] = None,
        message_text: Optional[str] = None
    ):
        """Create a mock Telegram Update object."""
        update = MagicMock()
        update.message = MagicMock()
        update.message.from_user = MagicMock()
        update.message.from_user.id = user_id
        update.message.chat_id = chat_id
        update.message.text = message_text or f"/{command} {' '.join(args or [])}"
        update.effective_chat = MagicMock()
        update.effective_chat.id = chat_id
        update.effective_user = MagicMock()
        update.effective_user.id = user_id
        return update
    
    return _create_update


@pytest.fixture
def mock_telegram_context():
    """Factory for creating mock Telegram Context objects."""
    def _create_context(args: Optional[List[str]] = None):
        """Create a mock Telegram Context object."""
        context = MagicMock()
        context.args = args or []
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        return context
    
    return _create_context


@pytest.fixture
def mock_telegram_callback_query():
    """Factory for creating mock Telegram CallbackQuery objects."""
    def _create_callback(
        data: str,
        user_id: int = 12345,
        chat_id: int = 12345
    ):
        """Create a mock Telegram CallbackQuery object."""
        query = MagicMock()
        query.data = data
        query.from_user = MagicMock()
        query.from_user.id = user_id
        query.message = MagicMock()
        query.message.chat_id = chat_id
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        return query
    
    return _create_callback


# ============================================================================
# Mock Wallet Objects
# ============================================================================

@pytest.fixture
def mock_wallet():
    """Factory for creating mock WalletManager objects."""
    def _create_wallet(
        balance: float = 1.0,
        address: str = "TestWallet1234567890123456789012345",
        network: str = "devnet"
    ):
        """Create a mock WalletManager object."""
        wallet = MagicMock()
        wallet.get_balance = AsyncMock(return_value=balance)
        wallet.get_address = MagicMock(return_value=address)
        wallet.network = network
        wallet.withdraw = AsyncMock(return_value="mock_signature_123")
        wallet.get_recent_transactions = AsyncMock(return_value=[])
        return wallet
    
    return _create_wallet


@pytest.fixture
def mock_keypair():
    """Factory for creating mock Solana Keypair objects."""
    def _create_keypair(
        public_key: str = "TestPublicKey1234567890123456789012"
    ):
        """Create a mock Keypair object."""
        keypair = MagicMock()
        keypair.pubkey = MagicMock()
        keypair.pubkey.__str__ = MagicMock(return_value=public_key)
        return keypair
    
    return _create_keypair


# ============================================================================
# Mock Trading Objects
# ============================================================================

@pytest.fixture
def mock_performance_tracker():
    """Factory for creating mock PerformanceTracker objects."""
    def _create_tracker(
        total_profit: float = 0.0,
        win_rate: float = 0.0,
        total_trades: int = 0,
        winning_trades: int = 0
    ):
        """Create a mock PerformanceTracker object."""
        tracker = MagicMock()
        tracker.get_total_profit = MagicMock(return_value=total_profit)
        tracker.get_win_rate = MagicMock(return_value=win_rate)
        tracker.get_total_trades = MagicMock(return_value=total_trades)
        tracker.get_winning_trades = MagicMock(return_value=winning_trades)
        tracker.record_trade = MagicMock()
        return tracker
    
    return _create_tracker


@pytest.fixture
def mock_risk_manager():
    """Factory for creating mock RiskManager objects."""
    def _create_risk_manager(
        is_paused: bool = False,
        risk_level: str = "medium"
    ):
        """Create a mock RiskManager object."""
        risk_manager = MagicMock()
        risk_manager.is_paused = MagicMock(return_value=is_paused)
        risk_manager.get_risk_level = MagicMock(return_value=risk_level)
        risk_manager.calculate_position_size = MagicMock(return_value=0.1)
        risk_manager.check_circuit_breaker = MagicMock(return_value=False)
        risk_manager.pause_trading = MagicMock()
        risk_manager.resume_trading = MagicMock()
        return risk_manager
    
    return _create_risk_manager


@pytest.fixture
def mock_trade():
    """Factory for creating mock Trade objects."""
    def _create_trade(
        strategy: str = "jupiter_swap",
        expected_profit: float = 0.01,
        actual_profit: Optional[float] = None,
        status: str = "pending",
        timestamp: Optional[datetime] = None
    ):
        """Create a mock Trade object."""
        trade = {
            "strategy": strategy,
            "expected_profit": expected_profit,
            "actual_profit": actual_profit or expected_profit,
            "status": status,
            "timestamp": timestamp or datetime.now(),
            "signature": "mock_signature_123"
        }
        return trade
    
    return _create_trade


# ============================================================================
# Mock User Objects
# ============================================================================

@pytest.fixture
def mock_user():
    """Factory for creating test User objects."""
    def _create_user(
        user_id: int = 12345,
        telegram_username: str = "testuser",
        wallet_address: str = "TestWallet1234567890123456789012345",
        wallet_balance: float = 1.0,
        preferences: Optional[Dict[str, Any]] = None,
        fee_status: str = "paid"
    ):
        """Create a test User object."""
        user = {
            "user_id": user_id,
            "telegram_username": telegram_username,
            "wallet_address": wallet_address,
            "wallet_balance": wallet_balance,
            "preferences": preferences or {},
            "fee_status": fee_status,
            "created_at": datetime.now(),
            "last_active": datetime.now()
        }
        return user
    
    return _create_user


# ============================================================================
# Mock Service Objects
# ============================================================================

@pytest.fixture
def mock_price_service():
    """Factory for creating mock PriceService objects."""
    def _create_price_service(
        default_price: float = 100.0,
        cache_enabled: bool = True
    ):
        """Create a mock PriceService object."""
        service = MagicMock()
        service.get_price = AsyncMock(return_value={
            "price": default_price,
            "change_24h": 5.0,
            "market_cap": 1000000000
        })
        service.cache_enabled = cache_enabled
        return service
    
    return _create_price_service


@pytest.fixture
def mock_portfolio_service():
    """Factory for creating mock PortfolioService objects."""
    def _create_portfolio_service(
        holdings: Optional[List[Dict]] = None
    ):
        """Create a mock PortfolioService object."""
        service = MagicMock()
        service.get_portfolio = AsyncMock(return_value=holdings or [])
        service.calculate_total_value = AsyncMock(return_value=1000.0)
        return service
    
    return _create_portfolio_service


@pytest.fixture
def mock_ai_chat():
    """Factory for creating mock AI Chat objects."""
    def _create_ai_chat(
        default_response: str = "This is a test response"
    ):
        """Create a mock AI Chat object."""
        chat = MagicMock()
        chat.generate_response = AsyncMock(return_value=default_response)
        chat.add_to_context = MagicMock()
        return chat
    
    return _create_ai_chat


# ============================================================================
# Mock RPC and API Responses
# ============================================================================

@pytest.fixture
def mock_rpc_response():
    """Factory for mocking RPC responses."""
    def _mock_response(method: str, response: Any):
        """Mock an RPC response for a specific method."""
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "result": response
        }
    
    return _mock_response


@pytest.fixture
def mock_api_response():
    """Factory for mocking external API responses."""
    def _mock_response(
        service: str,
        endpoint: str,
        response: Any,
        status_code: int = 200
    ):
        """Mock an API response for a specific service and endpoint."""
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.json = MagicMock(return_value=response)
        mock_resp.text = str(response)
        return mock_resp
    
    return _mock_response


# ============================================================================
# Assertion Helpers
# ============================================================================

@pytest.fixture
def assert_telegram_message_sent():
    """Helper for asserting Telegram messages were sent."""
    def _assert_sent(
        mock_bot,
        chat_id: int,
        text_contains: Optional[str] = None,
        call_count: Optional[int] = None
    ):
        """Assert that a Telegram message was sent."""
        if call_count is not None:
            assert mock_bot.send_message.call_count == call_count
        
        if text_contains:
            calls = mock_bot.send_message.call_args_list
            found = False
            for call in calls:
                args, kwargs = call
                if chat_id in args or kwargs.get("chat_id") == chat_id:
                    message_text = args[1] if len(args) > 1 else kwargs.get("text", "")
                    if text_contains in message_text:
                        found = True
                        break
            assert found, f"Expected message containing '{text_contains}' not found"
    
    return _assert_sent


@pytest.fixture
def assert_transaction_executed():
    """Helper for asserting blockchain transactions were executed."""
    def _assert_executed(
        mock_wallet,
        signature: Optional[str] = None
    ):
        """Assert that a transaction was executed."""
        assert mock_wallet.withdraw.called or hasattr(mock_wallet, 'send_transaction')
        
        if signature:
            # Check if the signature matches
            calls = mock_wallet.withdraw.call_args_list
            found = any(signature in str(call) for call in calls)
            assert found, f"Transaction with signature '{signature}' not found"
    
    return _assert_executed


@pytest.fixture
def wait_for_async():
    """Helper for waiting for async operations."""
    async def _wait(
        condition_func,
        timeout: float = 5.0,
        interval: float = 0.1
    ):
        """Wait for an async condition to become true."""
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            if await condition_func():
                return True
            await asyncio.sleep(interval)
        return False
    
    return _wait


# ============================================================================
# Test Database Fixtures
# ============================================================================

@pytest.fixture
def test_database():
    """Create a test database for integration tests."""
    # This would set up an in-memory SQLite database
    # or a test PostgreSQL database
    db = MagicMock()
    db.execute = AsyncMock()
    db.fetch_one = AsyncMock()
    db.fetch_all = AsyncMock()
    return db


# ============================================================================
# Environment Configuration
# ============================================================================

@pytest.fixture(autouse=True)
def test_environment():
    """Set up test environment variables."""
    test_env = {
        "ENVIRONMENT": "test",
        "TELEGRAM_BOT_TOKEN": "test_token_123",
        "HELIUS_API_KEY": "test_helius_key",
        "GROQ_API_KEY": "test_groq_key",
        "PRICE_CACHE_TTL": "60",
        "STRATEGY_CACHE_TTL": "30",
        "RPC_BATCH_SIZE": "10"
    }
    
    with patch.dict(os.environ, test_env, clear=False):
        yield


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Clean up after each test."""
    yield
    # Cleanup code here if needed
    pass
