"""
Tests for the TestHarness class.

This module verifies that the TestHarness provides all required mock
factories and utilities as specified in the design document.
"""

import pytest
from tests.test_harness import TestHarness


class TestTestHarness:
    """Test suite for TestHarness functionality."""
    
    def test_harness_initialization(self):
        """Test that TestHarness can be initialized."""
        harness = TestHarness()
        assert harness is not None
        assert hasattr(harness, '_mock_call_counts')
    
    # ========================================================================
    # Telegram Mock Factory Tests
    # ========================================================================
    
    def test_create_mock_telegram_update(self):
        """Test creating mock Telegram Update objects."""
        harness = TestHarness()
        
        # Test basic update creation
        update = harness.create_mock_telegram_update("start", user_id=12345)
        assert update is not None
        assert update.message.from_user.id == 12345
        assert update.message.chat_id == 12345
        assert "/start" in update.message.text
        
        # Test with args
        update = harness.create_mock_telegram_update(
            "withdraw",
            user_id=67890,
            args=["1.0", "ABC123"]
        )
        assert update.message.from_user.id == 67890
        assert "1.0" in update.message.text
        assert "ABC123" in update.message.text
    
    def test_create_mock_telegram_context(self):
        """Test creating mock Telegram Context objects."""
        harness = TestHarness()
        
        context = harness.create_mock_telegram_context(args=["arg1", "arg2"])
        assert context is not None
        assert context.args == ["arg1", "arg2"]
        assert hasattr(context.bot, 'send_message')
        assert hasattr(context, 'bot_data')
        assert hasattr(context, 'user_data')
    
    def test_create_mock_telegram_callback_query(self):
        """Test creating mock Telegram CallbackQuery objects."""
        harness = TestHarness()
        
        query = harness.create_mock_telegram_callback_query(
            "approve_fee",
            user_id=12345
        )
        assert query is not None
        assert query.data == "approve_fee"
        assert query.from_user.id == 12345
        assert hasattr(query, 'answer')
    
    # ========================================================================
    # Wallet Mock Factory Tests
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_create_mock_wallet(self):
        """Test creating mock WalletManager objects."""
        harness = TestHarness()
        
        wallet = harness.create_mock_wallet(
            balance=1.5,
            address="TestAddress123",
            network="devnet"
        )
        assert wallet is not None
        assert await wallet.get_balance() == 1.5
        assert wallet.get_address() == "TestAddress123"
        assert wallet.network == "devnet"
        
        # Test withdraw method
        signature = await wallet.withdraw()
        assert signature == "mock_signature_123"
    
    def test_create_mock_keypair(self):
        """Test creating mock Keypair objects."""
        harness = TestHarness()
        
        keypair = harness.create_mock_keypair(public_key="TestPubKey123")
        assert keypair is not None
        assert str(keypair.pubkey) == "TestPubKey123"
    
    # ========================================================================
    # Performance Tracker Mock Factory Tests
    # ========================================================================
    
    def test_create_mock_performance_tracker(self):
        """Test creating mock PerformanceTracker objects."""
        harness = TestHarness()
        
        tracker = harness.create_mock_performance_tracker(
            total_profit=0.5,
            win_rate=68.5,
            total_trades=100,
            winning_trades=68
        )
        assert tracker is not None
        assert tracker.get_total_profit() == 0.5
        assert tracker.get_win_rate() == 68.5
        assert tracker.get_total_trades() == 100
        assert tracker.get_winning_trades() == 68
    
    def test_create_mock_risk_manager(self):
        """Test creating mock RiskManager objects."""
        harness = TestHarness()
        
        risk_mgr = harness.create_mock_risk_manager(
            is_paused=False,
            risk_level="medium",
            position_size=0.1
        )
        assert risk_mgr is not None
        assert risk_mgr.is_paused() is False
        assert risk_mgr.get_risk_level() == "medium"
        assert risk_mgr.calculate_position_size() == 0.1
    
    # ========================================================================
    # User Mock Factory Tests
    # ========================================================================
    
    def test_create_test_user(self):
        """Test creating test User objects."""
        harness = TestHarness()
        
        user = harness.create_test_user(
            user_id=12345,
            telegram_username="testuser",
            wallet_balance=1.5,
            fee_status="paid"
        )
        assert user is not None
        assert user["user_id"] == 12345
        assert user["telegram_username"] == "testuser"
        assert user["wallet_balance"] == 1.5
        assert user["fee_status"] == "paid"
        assert "created_at" in user
        assert "preferences" in user
    
    def test_create_test_trade(self):
        """Test creating test Trade objects."""
        harness = TestHarness()
        
        trade = harness.create_test_trade(
            strategy="jupiter_swap",
            expected_profit=0.01,
            actual_profit=0.009,
            status="completed"
        )
        assert trade is not None
        assert trade["strategy"] == "jupiter_swap"
        assert trade["expected_profit"] == 0.01
        assert trade["actual_profit"] == 0.009
        assert trade["status"] == "completed"
        assert "timestamp" in trade
    
    # ========================================================================
    # Service Mock Factory Tests
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_create_mock_price_service(self):
        """Test creating mock PriceService objects."""
        harness = TestHarness()
        
        price_svc = harness.create_mock_price_service(default_price=150.0)
        assert price_svc is not None
        
        price_data = await price_svc.get_price()
        assert price_data["price"] == 150.0
        assert "change_24h" in price_data
    
    @pytest.mark.asyncio
    async def test_create_mock_portfolio_service(self):
        """Test creating mock PortfolioService objects."""
        harness = TestHarness()
        
        holdings = [{"symbol": "SOL", "amount": 10.0}]
        portfolio_svc = harness.create_mock_portfolio_service(
            holdings=holdings,
            total_value=1500.0
        )
        assert portfolio_svc is not None
        
        result = await portfolio_svc.get_portfolio()
        assert result == holdings
        
        total = await portfolio_svc.calculate_total_value()
        assert total == 1500.0
    
    @pytest.mark.asyncio
    async def test_create_mock_ai_chat(self):
        """Test creating mock AI Chat objects."""
        harness = TestHarness()
        
        ai_chat = harness.create_mock_ai_chat(
            default_response="Hello, how can I help?"
        )
        assert ai_chat is not None
        
        response = await ai_chat.generate_response()
        assert response == "Hello, how can I help?"
    
    # ========================================================================
    # RPC and API Mock Utility Tests
    # ========================================================================
    
    def test_mock_rpc_response(self):
        """Test creating mock RPC responses."""
        harness = TestHarness()
        
        rpc_resp = harness.mock_rpc_response("getBalance", 1000000000)
        assert rpc_resp is not None
        assert rpc_resp["result"] == 1000000000
        assert rpc_resp["jsonrpc"] == "2.0"
        assert rpc_resp["id"] == 1
    
    def test_mock_api_response(self):
        """Test creating mock API responses."""
        harness = TestHarness()
        
        api_resp = harness.mock_api_response(
            "jupiter",
            "/quote",
            {"price": 100.0},
            status_code=200
        )
        assert api_resp is not None
        assert api_resp.status_code == 200
        assert api_resp.json() == {"price": 100.0}
        assert api_resp.ok is True
    
    # ========================================================================
    # Assertion Helper Tests
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_assert_telegram_message_sent(self):
        """Test Telegram message assertion helper."""
        harness = TestHarness()
        
        # Create mock bot and send a message
        context = harness.create_mock_telegram_context()
        await context.bot.send_message(12345, "Welcome to the bot!")
        
        # Assert message was sent
        harness.assert_telegram_message_sent(
            context.bot,
            12345,
            text_contains="Welcome"
        )
        
        # Test call count assertion
        harness.assert_telegram_message_sent(
            context.bot,
            12345,
            call_count=1
        )
    
    @pytest.mark.asyncio
    async def test_assert_transaction_executed(self):
        """Test transaction execution assertion helper."""
        harness = TestHarness()
        
        wallet = harness.create_mock_wallet()
        signature = await wallet.withdraw()
        
        # Assert transaction was executed
        harness.assert_transaction_executed(wallet)
        
        # For signature checking, we verify the return value matches
        assert signature == "mock_signature_123"
    
    @pytest.mark.asyncio
    async def test_wait_for_async_operation(self):
        """Test async operation waiting helper."""
        harness = TestHarness()
        
        wallet = harness.create_mock_wallet()
        
        # Trigger an async operation
        await wallet.get_balance()
        
        # Wait for the operation to complete
        result = await harness.wait_for_async_operation(
            lambda: wallet.get_balance.called,
            timeout=1.0
        )
        assert result is True
    
    # ========================================================================
    # Utility Method Tests
    # ========================================================================
    
    @pytest.mark.asyncio
    async def test_reset_mocks(self):
        """Test mock reset utility."""
        harness = TestHarness()
        
        wallet = harness.create_mock_wallet()
        await wallet.get_balance()
        
        assert wallet.get_balance.call_count == 1
        
        harness.reset_mocks(wallet)
        assert wallet.get_balance.call_count == 0
    
    @pytest.mark.asyncio
    async def test_get_call_count(self):
        """Test call count utility."""
        harness = TestHarness()
        
        wallet = harness.create_mock_wallet()
        
        # Initially no calls
        count = harness.get_call_count(wallet, "get_balance")
        assert count == 0
        
        # After calling
        await wallet.get_balance()
        count = harness.get_call_count(wallet, "get_balance")
        assert count == 1


class TestTestHarnessIntegration:
    """Integration tests for TestHarness with multiple components."""
    
    @pytest.mark.asyncio
    async def test_full_command_flow(self):
        """Test a complete command flow using TestHarness."""
        harness = TestHarness()
        
        # Create all necessary mocks
        update = harness.create_mock_telegram_update("wallet", user_id=12345)
        context = harness.create_mock_telegram_context()
        wallet = harness.create_mock_wallet(balance=1.5)
        
        # Simulate command execution
        balance = await wallet.get_balance()
        await context.bot.send_message(
            update.message.chat_id,
            f"Your balance is {balance} SOL"
        )
        
        # Verify the flow
        assert wallet.get_balance.called
        harness.assert_telegram_message_sent(
            context.bot,
            12345,
            text_contains="1.5 SOL"
        )
    
    @pytest.mark.asyncio
    async def test_multi_user_scenario(self):
        """Test multi-user scenario using TestHarness."""
        harness = TestHarness()
        
        # Create multiple users
        user1 = harness.create_test_user(user_id=1, wallet_balance=1.0)
        user2 = harness.create_test_user(user_id=2, wallet_balance=2.0)
        user3 = harness.create_test_user(user_id=3, wallet_balance=3.0)
        
        users = [user1, user2, user3]
        
        # Verify isolation
        assert user1["user_id"] != user2["user_id"]
        assert user1["wallet_balance"] != user2["wallet_balance"]
        assert len(users) == 3
    
    def test_performance_tracking_scenario(self):
        """Test performance tracking scenario using TestHarness."""
        harness = TestHarness()
        
        # Create trades
        trades = [
            harness.create_test_trade(expected_profit=0.01, actual_profit=0.009),
            harness.create_test_trade(expected_profit=0.02, actual_profit=0.018),
            harness.create_test_trade(expected_profit=0.01, actual_profit=-0.005),
        ]
        
        # Create tracker with trades
        tracker = harness.create_mock_performance_tracker(
            total_profit=0.022,
            win_rate=66.67,
            total_trades=3,
            winning_trades=2,
            trades=trades
        )
        
        # Verify tracker
        assert tracker.get_total_trades() == 3
        assert tracker.get_winning_trades() == 2
        assert tracker.get_win_rate() == 66.67
