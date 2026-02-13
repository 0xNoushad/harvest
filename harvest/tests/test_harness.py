"""
TestHarness class for Harvest bot testing.

This module provides a unified TestHarness class that consolidates all mock
factories and test utilities into a single, easy-to-use interface. It implements
the TestHarness design from the testing infrastructure specification.

The TestHarness provides:
- Mock factories for Telegram objects (updates, contexts, callbacks)
- Mock factories for wallet and blockchain objects
- Mock factories for trading and performance tracking
- Mock factories for services (price, portfolio, AI chat)
- Test user creation utilities
- Assertion helpers for common verification patterns
- Async operation utilities

Usage:
    harness = TestHarness()
    update = harness.create_mock_telegram_update("start", user_id=12345)
    wallet = harness.create_mock_wallet(balance=1.5)
    user = harness.create_test_user(user_id=12345, wallet_balance=1.5)
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

# Import fixtures for easy access
try:
    from .fixtures import (
        HELIUS_FIXTURES,
        JUPITER_FIXTURES,
        MARINADE_FIXTURES,
        GROQ_FIXTURES,
        COINGECKO_FIXTURES,
        TELEGRAM_FIXTURES,
        AIRDROP_FIXTURES,
        PORTFOLIO_FIXTURES,
        ERROR_FIXTURES,
        get_fixture,
        list_fixtures
    )
except ImportError:
    # Fixtures not available, will use basic mocks
    HELIUS_FIXTURES = {}
    JUPITER_FIXTURES = {}
    MARINADE_FIXTURES = {}
    GROQ_FIXTURES = {}
    COINGECKO_FIXTURES = {}
    TELEGRAM_FIXTURES = {}
    AIRDROP_FIXTURES = {}
    PORTFOLIO_FIXTURES = {}
    ERROR_FIXTURES = {}
    
    def get_fixture(service: str, fixture_name: str) -> Dict[str, Any]:
        return {}
    
    def list_fixtures(service: Optional[str] = None) -> Dict[str, list]:
        return {}


class TestHarness:
    """
    Unified test harness providing mock factories and utilities.
    
    This class consolidates all test fixtures and utilities into a single
    interface for easy test setup and execution.
    """
    
    def __init__(self):
        """Initialize the test harness."""
        self._mock_call_counts = {}
    
    # ========================================================================
    # Telegram Mock Factories
    # ========================================================================
    
    def create_mock_telegram_update(
        self,
        command: str,
        user_id: int = 12345,
        chat_id: Optional[int] = None,
        args: Optional[List[str]] = None,
        message_text: Optional[str] = None
    ):
        """
        Create a mock Telegram Update object for command testing.
        
        Args:
            command: Command name (without leading slash)
            user_id: Telegram user ID
            chat_id: Chat ID (defaults to user_id)
            args: Command arguments
            message_text: Full message text (auto-generated if not provided)
            
        Returns:
            Mock Update object with all required attributes
            
        Example:
            update = harness.create_mock_telegram_update("start", user_id=12345)
            update = harness.create_mock_telegram_update("withdraw", args=["1.0", "ABC..."])
        """
        if chat_id is None:
            chat_id = user_id
        
        if message_text is None:
            args_str = ' '.join(args) if args else ''
            message_text = f"/{command} {args_str}".strip()
        
        update = MagicMock()
        update.message = MagicMock()
        update.message.from_user = MagicMock()
        update.message.from_user.id = user_id
        update.message.chat_id = chat_id
        update.message.text = message_text
        update.message.reply_text = AsyncMock()
        update.message.chat = MagicMock()
        update.message.chat.send_action = AsyncMock()
        
        update.effective_chat = MagicMock()
        update.effective_chat.id = chat_id
        
        update.effective_user = MagicMock()
        update.effective_user.id = user_id
        update.effective_user.username = f"user{user_id}"
        
        return update
    
    def create_mock_telegram_context(
        self,
        args: Optional[List[str]] = None,
        bot_data: Optional[Dict] = None,
        user_data: Optional[Dict] = None
    ):
        """
        Create a mock Telegram Context object.
        
        Args:
            args: Command arguments
            bot_data: Bot-level data dictionary
            user_data: User-level data dictionary
            
        Returns:
            Mock Context object with bot and data attributes
            
        Example:
            context = harness.create_mock_telegram_context(args=["1.0", "ABC..."])
        """
        context = MagicMock()
        context.args = args or []
        context.bot_data = bot_data or {}
        context.user_data = user_data or {}
        
        context.bot = MagicMock()
        context.bot.send_message = AsyncMock()
        context.bot.edit_message_text = AsyncMock()
        context.bot.delete_message = AsyncMock()
        
        return context
    
    def create_mock_telegram_callback_query(
        self,
        data: str,
        user_id: int = 12345,
        chat_id: Optional[int] = None
    ):
        """
        Create a mock Telegram CallbackQuery object.
        
        Args:
            data: Callback data string
            user_id: Telegram user ID
            chat_id: Chat ID (defaults to user_id)
            
        Returns:
            Mock CallbackQuery object
            
        Example:
            query = harness.create_mock_telegram_callback_query("approve_fee")
        """
        if chat_id is None:
            chat_id = user_id
        
        query = MagicMock()
        query.data = data
        query.from_user = MagicMock()
        query.from_user.id = user_id
        query.message = MagicMock()
        query.message.chat_id = chat_id
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        
        return query
    
    # ========================================================================
    # Wallet Mock Factories
    # ========================================================================
    
    def create_mock_wallet(
        self,
        balance: float = 1.0,
        address: str = "TestWallet1234567890123456789012345",
        network: str = "devnet"
    ):
        """
        Create a mock WalletManager object for wallet testing.
        
        Args:
            balance: Wallet balance in SOL
            address: Wallet address (Solana public key)
            network: Network name (devnet, mainnet-beta)
            
        Returns:
            Mock WalletManager with common methods
            
        Example:
            wallet = harness.create_mock_wallet(balance=1.5, network="devnet")
            balance = await wallet.get_balance()  # Returns 1.5
        """
        wallet = MagicMock()
        wallet.get_balance = AsyncMock(return_value=balance)
        wallet.get_address = MagicMock(return_value=address)
        wallet.network = network
        wallet.withdraw = AsyncMock(return_value="mock_signature_123")
        wallet.send_transaction = AsyncMock(return_value="mock_signature_123")
        wallet.get_recent_transactions = AsyncMock(return_value=[])
        wallet.generate_keypair = MagicMock()
        wallet.export_private_key = MagicMock(return_value="mock_private_key")
        
        return wallet
    
    def create_mock_keypair(
        self,
        public_key: str = "TestPublicKey1234567890123456789012"
    ):
        """
        Create a mock Solana Keypair object.
        
        Args:
            public_key: Public key string
            
        Returns:
            Mock Keypair object
            
        Example:
            keypair = harness.create_mock_keypair()
        """
        keypair = MagicMock()
        keypair.pubkey = MagicMock()
        keypair.pubkey.__str__ = MagicMock(return_value=public_key)
        keypair.secret = b"mock_secret_key_bytes"
        
        return keypair
    
    # ========================================================================
    # Performance Tracker Mock Factories
    # ========================================================================
    
    def create_mock_performance_tracker(
        self,
        total_profit: float = 0.0,
        win_rate: float = 0.0,
        total_trades: int = 0,
        winning_trades: int = 0,
        trades: Optional[List[Dict]] = None
    ):
        """
        Create a mock PerformanceTracker object for stats testing.
        
        Args:
            total_profit: Total profit in SOL
            win_rate: Win rate percentage (0-100)
            total_trades: Total number of trades
            winning_trades: Number of winning trades
            trades: List of trade dictionaries
            
        Returns:
            Mock PerformanceTracker with stats methods
            
        Example:
            tracker = harness.create_mock_performance_tracker(
                total_profit=0.5,
                win_rate=68.5,
                total_trades=100,
                winning_trades=68
            )
        """
        tracker = MagicMock()
        tracker.get_total_profit = MagicMock(return_value=total_profit)
        tracker.get_win_rate = MagicMock(return_value=win_rate)
        tracker.get_total_trades = MagicMock(return_value=total_trades)
        tracker.get_winning_trades = MagicMock(return_value=winning_trades)
        tracker.get_losing_trades = MagicMock(return_value=total_trades - winning_trades)
        tracker.get_trades = MagicMock(return_value=trades or [])
        tracker.record_trade = MagicMock()
        tracker.get_strategy_performance = MagicMock(return_value={})
        tracker.get_recent_trades = MagicMock(return_value=trades or [])
        
        # Add get_metrics method for multi-user support
        tracker.get_metrics = MagicMock(return_value=MagicMock(
            total_profit=total_profit,
            total_trades=total_trades,
            successful_trades=winning_trades,
            win_rate=win_rate,
            total_gas_fees=0.0,
            net_profit=total_profit,
            profit_by_strategy={},
            performance_fee_collected=0.0
        ))
        
        return tracker
    
    def create_mock_risk_manager(
        self,
        is_paused: bool = False,
        risk_level: str = "medium",
        position_size: float = 0.1
    ):
        """
        Create a mock RiskManager object.
        
        Args:
            is_paused: Whether trading is paused
            risk_level: Risk level (high, medium, low)
            position_size: Default position size
            
        Returns:
            Mock RiskManager
            
        Example:
            risk_mgr = harness.create_mock_risk_manager(risk_level="low")
        """
        risk_manager = MagicMock()
        risk_manager.is_paused = MagicMock(return_value=is_paused)
        risk_manager.get_risk_level = MagicMock(return_value=risk_level)
        risk_manager.calculate_position_size = MagicMock(return_value=position_size)
        risk_manager.check_circuit_breaker = MagicMock(return_value=False)
        risk_manager.pause_trading = MagicMock()
        risk_manager.resume_trading = MagicMock()
        risk_manager.record_loss = MagicMock()
        risk_manager.record_win = MagicMock()
        
        return risk_manager
    
    # ========================================================================
    # User Mock Factories
    # ========================================================================
    
    def create_test_user(
        self,
        user_id: int = 12345,
        telegram_username: str = "testuser",
        wallet_address: str = "TestWallet1234567890123456789012345",
        wallet_balance: float = 1.0,
        preferences: Optional[Dict[str, Any]] = None,
        fee_status: str = "paid"
    ) -> Dict[str, Any]:
        """
        Create a test User object for multi-user testing.
        
        Args:
            user_id: Telegram user ID
            telegram_username: Telegram username
            wallet_address: Solana wallet address
            wallet_balance: Wallet balance in SOL
            preferences: User preferences dictionary
            fee_status: Fee payment status (paid, pending, overdue)
            
        Returns:
            User dictionary with all required fields
            
        Example:
            user = harness.create_test_user(
                user_id=12345,
                wallet_balance=1.5,
                fee_status="paid"
            )
        """
        return {
            "user_id": user_id,
            "telegram_username": telegram_username,
            "wallet_address": wallet_address,
            "wallet_balance": wallet_balance,
            "preferences": preferences or {},
            "fee_status": fee_status,
            "created_at": datetime.now(),
            "last_active": datetime.now(),
            "total_profit": 0.0,
            "total_trades": 0,
            "active_strategies": []
        }
    
    def create_test_trade(
        self,
        strategy: str = "jupiter_swap",
        expected_profit: float = 0.01,
        actual_profit: Optional[float] = None,
        status: str = "completed",
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Create a test Trade object.
        
        Args:
            strategy: Strategy name
            expected_profit: Expected profit in SOL
            actual_profit: Actual profit in SOL (defaults to expected_profit)
            status: Trade status (pending, executing, completed, failed)
            timestamp: Trade timestamp
            
        Returns:
            Trade dictionary
            
        Example:
            trade = harness.create_test_trade(
                strategy="jupiter_swap",
                expected_profit=0.01,
                actual_profit=0.009
            )
        """
        return {
            "strategy": strategy,
            "expected_profit": expected_profit,
            "actual_profit": actual_profit if actual_profit is not None else expected_profit,
            "status": status,
            "timestamp": timestamp or datetime.now(),
            "signature": "mock_signature_123",
            "execution_time_ms": 1000
        }
    
    # ========================================================================
    # Service Mock Factories
    # ========================================================================
    
    def create_mock_price_service(
        self,
        default_price: float = 100.0,
        cache_enabled: bool = True
    ):
        """
        Create a mock PriceService object.
        
        Args:
            default_price: Default price to return
            cache_enabled: Whether caching is enabled
            
        Returns:
            Mock PriceService
            
        Example:
            price_svc = harness.create_mock_price_service(default_price=150.0)
        """
        service = MagicMock()
        service.get_price = AsyncMock(return_value={
            "price": default_price,
            "change_24h": 5.0,
            "market_cap": 1000000000,
            "symbol": "SOL"
        })
        service.cache_enabled = cache_enabled
        service.get_cached_price = MagicMock(return_value=None)
        service.set_cached_price = MagicMock()
        
        return service
    
    def create_mock_portfolio_service(
        self,
        holdings: Optional[List[Dict]] = None,
        total_value: float = 1000.0
    ):
        """
        Create a mock PortfolioService object.
        
        Args:
            holdings: List of token holdings
            total_value: Total portfolio value in USD
            
        Returns:
            Mock PortfolioService
            
        Example:
            portfolio_svc = harness.create_mock_portfolio_service(
                holdings=[{"symbol": "SOL", "amount": 10.0}]
            )
        """
        service = MagicMock()
        service.get_portfolio = AsyncMock(return_value=holdings or [])
        service.calculate_total_value = AsyncMock(return_value=total_value)
        service.get_token_holdings = AsyncMock(return_value=holdings or [])
        
        return service
    
    def create_mock_ai_chat(
        self,
        default_response: str = "This is a test response"
    ):
        """
        Create a mock AI Chat object.
        
        Args:
            default_response: Default response text
            
        Returns:
            Mock AI Chat
            
        Example:
            ai_chat = harness.create_mock_ai_chat(
                default_response="Hello! How can I help?"
            )
        """
        chat = MagicMock()
        chat.generate_response = AsyncMock(return_value=default_response)
        chat.add_to_context = MagicMock()
        chat.clear_context = MagicMock()
        chat.get_context = MagicMock(return_value=[])
        
        return chat
    
    # ========================================================================
    # RPC and API Mock Utilities
    # ========================================================================
    
    def mock_rpc_response(
        self,
        method: str,
        response: Any,
        error: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a mock RPC response for blockchain mocking.
        
        This method creates properly formatted JSON-RPC 2.0 responses for
        Solana RPC and Helius RPC calls. Supports both success and error responses.
        
        Args:
            method: RPC method name (e.g., "getBalance", "getAccountInfo")
            response: Response data (result field)
            error: Optional error object with code and message
            context: Optional context data (slot, etc.)
            
        Returns:
            RPC response dictionary in JSON-RPC 2.0 format
            
        Examples:
            # Success response
            rpc_resp = harness.mock_rpc_response(
                "getBalance", 
                {"value": 1000000000, "context": {"slot": 123456}}
            )
            
            # Error response
            rpc_resp = harness.mock_rpc_response(
                "getBalance",
                None,
                error={"code": -32602, "message": "Invalid params"}
            )
            
            # With context
            rpc_resp = harness.mock_rpc_response(
                "getAccountInfo",
                {"value": {"data": "...", "lamports": 1000000}},
                context={"slot": 123456, "apiVersion": "1.14.0"}
            )
        """
        base_response = {
            "jsonrpc": "2.0",
            "id": 1,
        }
        
        if error:
            base_response["error"] = error
        else:
            base_response["result"] = response
            
        if context:
            base_response["context"] = context
            
        return base_response
    
    def mock_api_response(
        self,
        service: str,
        endpoint: str,
        response: Any,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        delay_ms: int = 0
    ):
        """
        Create a mock API response for external API mocking.
        
        This method creates mock HTTP response objects for external services
        like Jupiter, Groq, CoinGecko, etc. Supports custom headers, status
        codes, and simulated delays.
        
        Args:
            service: Service name (jupiter, groq, coingecko, helius)
            endpoint: API endpoint path
            response: Response data (will be JSON serialized)
            status_code: HTTP status code (default: 200)
            headers: Optional response headers
            delay_ms: Simulated response delay in milliseconds
            
        Returns:
            Mock response object with json(), text, status_code, etc.
            
        Examples:
            # Jupiter quote response
            api_resp = harness.mock_api_response(
                "jupiter", 
                "/quote",
                {"inAmount": "1000000", "outAmount": "950000"},
                status_code=200
            )
            
            # Groq API error
            api_resp = harness.mock_api_response(
                "groq",
                "/chat/completions",
                {"error": "Rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": "60"}
            )
            
            # Slow API response
            api_resp = harness.mock_api_response(
                "coingecko",
                "/simple/price",
                {"solana": {"usd": 100.0}},
                delay_ms=2000
            )
        """
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.ok = status_code < 400
        mock_resp.headers = headers or {}
        
        # Add service and endpoint metadata
        mock_resp._service = service
        mock_resp._endpoint = endpoint
        mock_resp._delay_ms = delay_ms
        
        # JSON response
        if isinstance(response, (dict, list)):
            mock_resp.json = MagicMock(return_value=response)
            mock_resp.text = str(response)
        else:
            mock_resp.text = str(response)
            mock_resp.json = MagicMock(side_effect=ValueError("Not JSON"))
        
        # Add raise_for_status method
        def raise_for_status():
            if not mock_resp.ok:
                # Use a generic exception instead of requests.HTTPError
                raise Exception(f"{status_code} Error: {response}")
        
        mock_resp.raise_for_status = raise_for_status
        
        return mock_resp
    
    # ========================================================================
    # Assertion Helpers
    # ========================================================================
    
    def assert_telegram_message_sent(
        self,
        mock_bot,
        chat_id: int,
        text_contains: Optional[str] = None,
        call_count: Optional[int] = None
    ):
        """
        Assert that a Telegram message was sent.
        
        Args:
            mock_bot: Mock bot object
            chat_id: Expected chat ID
            text_contains: Text that should be in the message
            call_count: Expected number of calls
            
        Raises:
            AssertionError: If assertion fails
            
        Example:
            harness.assert_telegram_message_sent(
                bot, 12345, text_contains="Welcome"
            )
        """
        if call_count is not None:
            assert mock_bot.send_message.call_count == call_count, \
                f"Expected {call_count} calls, got {mock_bot.send_message.call_count}"
        
        if text_contains:
            calls = mock_bot.send_message.call_args_list
            found = False
            for call in calls:
                args, kwargs = call
                if chat_id in args or kwargs.get("chat_id") == chat_id:
                    message_text = args[1] if len(args) > 1 else kwargs.get("text", "")
                    if text_contains in str(message_text):
                        found = True
                        break
            assert found, f"Expected message containing '{text_contains}' not found in {len(calls)} calls"
    
    def assert_transaction_executed(
        self,
        mock_wallet,
        signature: Optional[str] = None,
        method_name: str = "withdraw"
    ):
        """
        Assert that a blockchain transaction was executed.
        
        Args:
            mock_wallet: Mock wallet object
            signature: Expected transaction signature
            method_name: Method name to check (withdraw, send_transaction)
            
        Raises:
            AssertionError: If assertion fails
            
        Example:
            harness.assert_transaction_executed(wallet, signature="abc123")
        """
        method = getattr(mock_wallet, method_name, None)
        assert method is not None, f"Method {method_name} not found on wallet"
        assert method.called, f"Method {method_name} was not called"
        
        if signature:
            # Check if the method returned the expected signature
            if hasattr(method, 'return_value'):
                # For AsyncMock, check the return value
                import asyncio
                return_val = method.return_value
                if asyncio.iscoroutine(return_val):
                    # Can't await here, so just check the mock's return_value attribute
                    pass
                elif return_val == signature:
                    return
            
            # Also check call args
            calls = method.call_args_list
            found = any(signature in str(call) for call in calls)
            
            # If not found in args, check if return value matches
            if not found and hasattr(method, 'return_value'):
                found = signature == str(method.return_value)
            
            assert found, f"Transaction with signature '{signature}' not found"
    
    async def wait_for_async_operation(
        self,
        condition_func,
        timeout: float = 5.0,
        interval: float = 0.1
    ) -> bool:
        """
        Wait for an async condition to become true.
        
        Args:
            condition_func: Function that returns True when condition is met
            timeout: Maximum time to wait in seconds
            interval: Time between checks in seconds
            
        Returns:
            True if condition was met
            
        Raises:
            TimeoutError: If timeout is reached
            
        Example:
            await harness.wait_for_async_operation(
                lambda: mock_wallet.get_balance.called,
                timeout=2.0
            )
        """
        import asyncio
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            if condition_func():
                return True
            await asyncio.sleep(interval)
        
        raise TimeoutError(f"Condition not met within {timeout} seconds")
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def get_fixture(self, service: str, fixture_name: str) -> Dict[str, Any]:
        """
        Get a pre-defined fixture for a service.
        
        This is a convenience wrapper around the fixtures module that provides
        realistic mock data for all external services.
        
        Args:
            service: Service name (helius, jupiter, marinade, groq, coingecko, telegram)
            fixture_name: Fixture name
            
        Returns:
            Fixture dictionary
            
        Example:
            balance = harness.get_fixture("helius", "get_balance_success")
            quote = harness.get_fixture("jupiter", "quote_success")
        """
        return get_fixture(service, fixture_name)
    
    def list_fixtures(self, service: Optional[str] = None) -> Dict[str, list]:
        """
        List all available fixtures.
        
        Args:
            service: Optional service name to filter by
            
        Returns:
            Dictionary mapping service names to lists of fixture names
            
        Example:
            all_fixtures = harness.list_fixtures()
            helius_fixtures = harness.list_fixtures("helius")
        """
        return list_fixtures(service)
    
    def mock_helius_rpc(
        self,
        method: str,
        fixture_name: Optional[str] = None,
        custom_response: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Create a mock Helius RPC response using fixtures.
        
        Args:
            method: RPC method name
            fixture_name: Name of fixture to use (e.g., "get_balance_success")
            custom_response: Custom response data (overrides fixture)
            
        Returns:
            Mock RPC response
            
        Example:
            # Use fixture
            response = harness.mock_helius_rpc("getBalance", "get_balance_success")
            
            # Use custom response
            response = harness.mock_helius_rpc("getBalance", custom_response={"value": 2000000000})
        """
        if custom_response is not None:
            return self.mock_rpc_response(method, custom_response)
        
        if fixture_name:
            fixture = get_fixture("helius", fixture_name)
            return fixture
        
        # Default to success response
        return self.mock_rpc_response(method, {"value": 1000000000})
    
    def mock_jupiter_api(
        self,
        endpoint: str,
        fixture_name: Optional[str] = None,
        custom_response: Optional[Any] = None,
        status_code: int = 200
    ):
        """
        Create a mock Jupiter API response using fixtures.
        
        Args:
            endpoint: API endpoint (e.g., "/quote", "/swap")
            fixture_name: Name of fixture to use
            custom_response: Custom response data (overrides fixture)
            status_code: HTTP status code
            
        Returns:
            Mock API response
            
        Example:
            # Use fixture
            response = harness.mock_jupiter_api("/quote", "quote_success")
            
            # Use custom response
            response = harness.mock_jupiter_api("/quote", custom_response={"outAmount": "100000"})
        """
        if custom_response is not None:
            return self.mock_api_response("jupiter", endpoint, custom_response, status_code)
        
        if fixture_name:
            fixture = get_fixture("jupiter", fixture_name)
            return self.mock_api_response("jupiter", endpoint, fixture, status_code)
        
        # Default to success response
        return self.mock_api_response("jupiter", endpoint, {"success": True}, status_code)
    
    def mock_groq_api(
        self,
        fixture_name: Optional[str] = None,
        custom_response: Optional[Any] = None,
        status_code: int = 200
    ):
        """
        Create a mock Groq API response using fixtures.
        
        Args:
            fixture_name: Name of fixture to use
            custom_response: Custom response data (overrides fixture)
            status_code: HTTP status code
            
        Returns:
            Mock API response
            
        Example:
            # Use fixture
            response = harness.mock_groq_api("chat_completion_success")
            
            # Use custom response
            response = harness.mock_groq_api(
                custom_response={"choices": [{"message": {"content": "Hello!"}}]}
            )
        """
        if custom_response is not None:
            return self.mock_api_response("groq", "/chat/completions", custom_response, status_code)
        
        if fixture_name:
            fixture = get_fixture("groq", fixture_name)
            return self.mock_api_response("groq", "/chat/completions", fixture, status_code)
        
        # Default to success response
        default_response = {
            "choices": [{"message": {"content": "Test response"}}]
        }
        return self.mock_api_response("groq", "/chat/completions", default_response, status_code)
    
    def mock_coingecko_api(
        self,
        fixture_name: Optional[str] = None,
        custom_response: Optional[Any] = None,
        status_code: int = 200
    ):
        """
        Create a mock CoinGecko API response using fixtures.
        
        Args:
            fixture_name: Name of fixture to use
            custom_response: Custom response data (overrides fixture)
            status_code: HTTP status code
            
        Returns:
            Mock API response
            
        Example:
            # Use fixture
            response = harness.mock_coingecko_api("simple_price_success")
            
            # Use custom response
            response = harness.mock_coingecko_api(
                custom_response={"solana": {"usd": 150.0}}
            )
        """
        if custom_response is not None:
            return self.mock_api_response("coingecko", "/simple/price", custom_response, status_code)
        
        if fixture_name:
            fixture = get_fixture("coingecko", fixture_name)
            return self.mock_api_response("coingecko", "/simple/price", fixture, status_code)
        
        # Default to success response
        default_response = {"solana": {"usd": 127.50}}
        return self.mock_api_response("coingecko", "/simple/price", default_response, status_code)
    
    def reset_mocks(self, *mocks):
        """
        Reset call counts and side effects on mock objects.
        
        Args:
            *mocks: Mock objects to reset
            
        Example:
            harness.reset_mocks(mock_wallet, mock_bot)
        """
        for mock in mocks:
            if hasattr(mock, 'reset_mock'):
                mock.reset_mock()
    
    def get_call_count(self, mock_obj, method_name: str) -> int:
        """
        Get the call count for a specific method on a mock.
        
        Args:
            mock_obj: Mock object
            method_name: Method name
            
        Returns:
            Number of times the method was called
            
        Example:
            count = harness.get_call_count(mock_wallet, "get_balance")
        """
        method = getattr(mock_obj, method_name, None)
        if method is None:
            return 0
        return method.call_count if hasattr(method, 'call_count') else 0
