"""
Unit tests for TransactionExecutor

Tests transaction execution, signing, confirmation, retry logic,
priority fee optimization, and error handling.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from agent.trading.transaction_executor import (
    TransactionExecutor,
    ExecutionResult,
    ErrorHandler
)


class TestErrorHandler:
    """Test ErrorHandler class."""
    
    def test_is_retryable_timeout(self):
        """Test that timeout errors are retryable."""
        error = Exception("Connection timeout")
        assert ErrorHandler.is_retryable(error) is True
    
    def test_is_retryable_network(self):
        """Test that network errors are retryable."""
        error = Exception("Network error occurred")
        assert ErrorHandler.is_retryable(error) is True
    
    def test_is_retryable_rate_limit(self):
        """Test that rate limit errors are retryable."""
        error = Exception("Rate limit exceeded (429)")
        assert ErrorHandler.is_retryable(error) is True
    
    def test_is_not_retryable_insufficient_balance(self):
        """Test that insufficient balance errors are not retryable."""
        error = Exception("Insufficient balance")
        assert ErrorHandler.is_retryable(error) is False
    
    def test_is_not_retryable_invalid_signature(self):
        """Test that invalid signature errors are not retryable."""
        error = Exception("Invalid signature")
        assert ErrorHandler.is_retryable(error) is False
    
    def test_is_critical_wallet_error(self):
        """Test that wallet errors are critical."""
        error = Exception("Wallet access failed")
        assert ErrorHandler.is_critical(error) is True
    
    def test_is_critical_keypair_error(self):
        """Test that keypair errors are critical."""
        error = Exception("Keypair verification failed")
        assert ErrorHandler.is_critical(error) is True
    
    def test_is_not_critical_network_error(self):
        """Test that network errors are not critical."""
        error = Exception("Network timeout")
        assert ErrorHandler.is_critical(error) is False
    
    def test_get_retry_delay_exponential(self):
        """Test exponential backoff calculation."""
        assert ErrorHandler.get_retry_delay(0) == 1
        assert ErrorHandler.get_retry_delay(1) == 2
        assert ErrorHandler.get_retry_delay(2) == 4
        assert ErrorHandler.get_retry_delay(3) == 8
    
    def test_get_retry_delay_capped(self):
        """Test that retry delay is capped at 60 seconds."""
        assert ErrorHandler.get_retry_delay(10) == 60
        assert ErrorHandler.get_retry_delay(100) == 60
    
    def test_handle_error_retryable(self):
        """Test handling retryable errors."""
        error = Exception("Network timeout")
        should_retry, should_shutdown = ErrorHandler.handle_error(error, "test", 0)
        assert should_retry is True
        assert should_shutdown is False
    
    def test_handle_error_non_retryable(self):
        """Test handling non-retryable errors."""
        error = Exception("Insufficient balance")
        should_retry, should_shutdown = ErrorHandler.handle_error(error, "test", 0)
        assert should_retry is False
        assert should_shutdown is False
    
    def test_handle_error_critical(self):
        """Test handling critical errors."""
        error = Exception("Wallet access failed")
        should_retry, should_shutdown = ErrorHandler.handle_error(error, "test", 0)
        assert should_retry is False
        assert should_shutdown is True


class TestTransactionExecutor:
    """Test TransactionExecutor class."""
    
    @pytest.fixture
    def mock_rpc_client(self):
        """Create mock RPC client."""
        client = AsyncMock()
        
        # Mock get_latest_blockhash
        blockhash_response = Mock()
        blockhash_response.value.blockhash = "mock_blockhash_123"
        client.get_latest_blockhash.return_value = blockhash_response
        
        # Mock send_transaction
        tx_response = Mock()
        tx_response.value = "test_signature_123"
        client.send_transaction.return_value = tx_response
        
        # Mock get_signature_statuses (confirmed)
        status_response = Mock()
        status_obj = Mock()
        status_obj.confirmation_status = "confirmed"
        status_obj.err = None
        status_response.value = [status_obj]
        client.get_signature_statuses.return_value = status_response
        
        # Mock get_recent_prioritization_fees
        fee_obj = Mock()
        fee_obj.prioritization_fee = 5000
        client.get_recent_prioritization_fees.return_value = [fee_obj]
        
        return client
    
    @pytest.fixture
    def mock_wallet_manager(self):
        """Create mock wallet manager."""
        wallet = Mock()
        wallet.get_balance = AsyncMock(return_value=1.0)
        
        # Mock sign_transaction
        def sign_tx(tx):
            tx.recent_blockhash = "mock_blockhash_123"
            return tx
        
        wallet.sign_transaction = Mock(side_effect=sign_tx)
        
        return wallet
    
    @pytest.fixture
    def executor(self, mock_rpc_client, mock_wallet_manager):
        """Create TransactionExecutor instance."""
        return TransactionExecutor(
            rpc_client=mock_rpc_client,
            wallet_manager=mock_wallet_manager,
            max_retries=3,
            confirmation_timeout=60
        )
    
    @pytest.fixture
    def mock_transaction(self):
        """Create mock transaction."""
        tx = Mock()
        tx.recent_blockhash = None
        tx.serialize = Mock(return_value=b"mock_tx_bytes")
        return tx
    
    @pytest.mark.asyncio
    async def test_execute_transaction_success(
        self,
        executor,
        mock_transaction,
        mock_wallet_manager
    ):
        """Test successful transaction execution."""
        # Update balance after transaction
        mock_wallet_manager.get_balance.side_effect = [1.0, 1.05]
        
        result = await executor.execute_transaction(
            mock_transaction,
            "test_strategy",
            expected_profit=0.05
        )
        
        assert result.success is True
        assert result.transaction_hash == "test_signature_123"
        assert result.strategy_name == "test_strategy"
        assert result.retry_count == 0
        assert result.profit == 0.05
    
    @pytest.mark.asyncio
    async def test_execute_transaction_with_retry(
        self,
        executor,
        mock_transaction,
        mock_rpc_client,
        mock_wallet_manager
    ):
        """Test transaction execution with retry on timeout."""
        # First attempt times out, second succeeds
        mock_rpc_client.get_signature_statuses.side_effect = [
            Mock(value=[None]),  # First check - not found
            Mock(value=[None]),  # Still not found
            Mock(value=[Mock(confirmation_status="confirmed", err=None)])  # Confirmed
        ]
        
        mock_wallet_manager.get_balance.side_effect = [1.0, 1.05]
        
        result = await executor.execute_transaction(
            mock_transaction,
            "test_strategy",
            expected_profit=0.05
        )
        
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_execute_transaction_max_retries_exceeded(
        self,
        executor,
        mock_transaction,
        mock_rpc_client,
        mock_wallet_manager
    ):
        """Test transaction failure after max retries."""
        # All attempts fail
        mock_rpc_client.send_transaction.side_effect = Exception("Network timeout")
        mock_wallet_manager.get_balance.return_value = 1.0
        
        result = await executor.execute_transaction(
            mock_transaction,
            "test_strategy",
            expected_profit=0.05
        )
        
        assert result.success is False
        assert result.transaction_hash is None
        assert result.error is not None
        assert "timeout" in result.error.lower()
        assert result.retry_count == 3
    
    @pytest.mark.asyncio
    async def test_sign_transaction(self, executor, mock_transaction):
        """Test transaction signing."""
        signed_tx = await executor._sign_transaction(mock_transaction)
        
        assert signed_tx is not None
        assert signed_tx.recent_blockhash is not None
    
    @pytest.mark.asyncio
    async def test_submit_transaction(
        self,
        executor,
        mock_transaction,
        mock_rpc_client
    ):
        """Test transaction submission."""
        signature = await executor._submit_transaction(mock_transaction)
        
        assert signature == "test_signature_123"
        assert mock_rpc_client.send_transaction.called
    
    @pytest.mark.asyncio
    async def test_wait_for_confirmation_success(
        self,
        executor,
        mock_rpc_client
    ):
        """Test waiting for confirmation - success case."""
        confirmed = await executor._wait_for_confirmation("test_sig", 60)
        
        assert confirmed is True
    
    @pytest.mark.asyncio
    async def test_wait_for_confirmation_timeout(
        self,
        executor,
        mock_rpc_client
    ):
        """Test waiting for confirmation - timeout case."""
        # Always return None (not confirmed)
        mock_rpc_client.get_signature_statuses.return_value = Mock(value=[None])
        
        confirmed = await executor._wait_for_confirmation("test_sig", 1)
        
        assert confirmed is False
    
    @pytest.mark.asyncio
    async def test_handle_blockhash_expiration(
        self,
        executor,
        mock_transaction,
        mock_rpc_client
    ):
        """Test blockhash refresh."""
        new_tx = await executor._handle_blockhash_expiration(mock_transaction)
        
        assert new_tx.recent_blockhash is not None
        assert mock_rpc_client.get_latest_blockhash.called
    
    @pytest.mark.asyncio
    async def test_set_priority_fee(self, executor, mock_rpc_client):
        """Test priority fee setting."""
        await executor._set_priority_fee(0)
        
        assert executor.current_priority_fee >= executor.base_priority_fee
    
    @pytest.mark.asyncio
    async def test_set_priority_fee_with_retry(self, executor, mock_rpc_client):
        """Test priority fee increases on retry."""
        await executor._set_priority_fee(0)
        base_fee = executor.current_priority_fee
        
        await executor._set_priority_fee(1)
        retry_fee = executor.current_priority_fee
        
        assert retry_fee > base_fee
    
    @pytest.mark.asyncio
    async def test_get_priority_fee_recommendation(
        self,
        executor,
        mock_rpc_client
    ):
        """Test priority fee recommendation query."""
        fee = await executor._get_priority_fee_recommendation()
        
        assert fee >= executor.base_priority_fee
    
    @pytest.mark.asyncio
    async def test_is_network_congested_false(self, executor, mock_rpc_client):
        """Test network congestion detection - not congested."""
        # Low fee = not congested
        fee_obj = Mock()
        fee_obj.prioritization_fee = 5000  # 0.000005 SOL
        mock_rpc_client.get_recent_prioritization_fees.return_value = [fee_obj]
        
        is_congested = await executor._is_network_congested()
        
        assert is_congested is False
    
    @pytest.mark.asyncio
    async def test_is_network_congested_true(self, executor, mock_rpc_client):
        """Test network congestion detection - congested."""
        # High fee = congested
        fee_obj = Mock()
        fee_obj.prioritization_fee = 2_000_000_000  # 0.002 SOL
        mock_rpc_client.get_recent_prioritization_fees.return_value = [fee_obj]
        
        is_congested = await executor._is_network_congested()
        
        assert is_congested is True
    
    @pytest.mark.asyncio
    async def test_execute_transaction_non_retryable_error(
        self,
        executor,
        mock_transaction,
        mock_rpc_client,
        mock_wallet_manager
    ):
        """Test that non-retryable errors don't trigger retries."""
        # Insufficient balance error
        mock_rpc_client.send_transaction.side_effect = Exception("Insufficient balance")
        mock_wallet_manager.get_balance.return_value = 1.0
        
        result = await executor.execute_transaction(
            mock_transaction,
            "test_strategy",
            expected_profit=0.05
        )
        
        assert result.success is False
        assert result.retry_count == 1  # Only one attempt, no retries
    
    @pytest.mark.asyncio
    async def test_execute_transaction_with_rpc_fallback(
        self,
        mock_rpc_client,
        mock_wallet_manager,
        mock_transaction
    ):
        """Test transaction execution with RPC fallback."""
        # Create mock fallback manager
        mock_fallback = Mock()
        mock_fallback.rpc_call = AsyncMock(return_value="fallback_signature")
        mock_fallback.get_current_provider = Mock(return_value=Mock(name="Fallback"))
        
        executor = TransactionExecutor(
            rpc_client=mock_rpc_client,
            wallet_manager=mock_wallet_manager,
            rpc_fallback_manager=mock_fallback
        )
        
        mock_wallet_manager.get_balance.side_effect = [1.0, 1.05]
        
        result = await executor.execute_transaction(
            mock_transaction,
            "test_strategy",
            expected_profit=0.05,
            user_id="test_user"
        )
        
        # Should use fallback manager for submission
        assert mock_fallback.rpc_call.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
