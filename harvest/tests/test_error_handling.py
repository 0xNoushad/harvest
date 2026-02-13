"""Tests for comprehensive error handling in multi-user wallet and trading loop."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from agent.core.multi_user_wallet import MultiUserWalletManager
from agent.core.database import Database
from agent.trading.loop import AgentLoop
from agent.trading.scanner import Opportunity


@pytest.fixture
def mock_database():
    """Create a mock database."""
    db = MagicMock(spec=Database)
    db.get_user_wallet = MagicMock(return_value=None)
    db.get_all_wallets = MagicMock(return_value=[])
    db.register_secure_wallet = MagicMock(return_value=True)
    return db


@pytest.fixture
async def wallet_manager(mock_database, tmp_path):
    """Create a wallet manager for testing."""
    manager = MultiUserWalletManager(
        database=mock_database,
        network="devnet",
        storage_dir=str(tmp_path / "wallets")
    )
    yield manager
    await manager.close_all()


class TestWalletErrorHandling:
    """Test error handling for wallet operations."""
    
    @pytest.mark.asyncio
    async def test_create_wallet_duplicate_error(self, wallet_manager, mock_database):
        """Test that duplicate wallet creation returns user-friendly error."""
        user_id = "test_user_1"
        
        # Create first wallet
        public_key, mnemonic = await wallet_manager.create_wallet(user_id)
        
        # Mock database to return existing wallet
        mock_database.get_user_wallet = MagicMock(return_value={"user_id": user_id, "public_key": public_key})
        
        # Try to create duplicate - should get user-friendly error
        with pytest.raises(ValueError) as exc_info:
            await wallet_manager.create_wallet(user_id)
        
        # Verify error message is user-friendly
        assert "already have a wallet" in str(exc_info.value)
        assert "/exportkey" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_import_wallet_invalid_mnemonic_error(self, wallet_manager):
        """Test that invalid mnemonic returns user-friendly error."""
        user_id = "test_user_2"
        invalid_mnemonic = "invalid mnemonic phrase"
        
        # Try to import with invalid mnemonic
        with pytest.raises(ValueError) as exc_info:
            await wallet_manager.import_wallet(user_id, invalid_mnemonic)
        
        # Verify error message is user-friendly
        assert "Invalid mnemonic" in str(exc_info.value)
        assert "12 or 24 words" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_export_key_no_wallet_error(self, wallet_manager):
        """Test that export key without wallet returns user-friendly error."""
        user_id = "test_user_3"
        
        # Try to export key without wallet
        with pytest.raises(ValueError) as exc_info:
            await wallet_manager.export_key(user_id)
        
        # Verify error message is user-friendly
        assert "don't have a wallet" in str(exc_info.value)
        assert "/createwallet" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_balance_rpc_failure_returns_cached(self, wallet_manager):
        """Test that balance check returns cached value on RPC failure."""
        user_id = "test_user_4"
        
        # Create wallet
        await wallet_manager.create_wallet(user_id)
        
        # Set cached balance
        wallet_manager._balance_cache[user_id] = (1.5, datetime.now())
        
        # Mock wallet.get_balance to raise exception
        with patch.object(wallet_manager, 'get_wallet') as mock_get_wallet:
            mock_wallet = AsyncMock()
            mock_wallet.get_balance = AsyncMock(side_effect=Exception("RPC error"))
            mock_get_wallet.return_value = mock_wallet
            
            # Get balance should return cached value
            balance = await wallet_manager.get_balance(user_id)
            
            # Should return cached balance
            assert balance == 1.5
    
    @pytest.mark.asyncio
    async def test_get_balance_no_cache_returns_zero(self, wallet_manager):
        """Test that balance check returns 0.0 when RPC fails and no cache."""
        user_id = "test_user_5"
        
        # Create wallet
        await wallet_manager.create_wallet(user_id)
        
        # Mock wallet.get_balance to raise exception
        with patch.object(wallet_manager, 'get_wallet') as mock_get_wallet:
            mock_wallet = AsyncMock()
            mock_wallet.get_balance = AsyncMock(side_effect=Exception("RPC error"))
            mock_get_wallet.return_value = mock_wallet
            
            # Get balance should return 0.0 as safe default
            balance = await wallet_manager.get_balance(user_id)
            
            # Should return 0.0
            assert balance == 0.0


class TestAgentLoopErrorHandling:
    """Test error handling for agent loop operations."""
    
    @pytest.mark.asyncio
    async def test_scan_user_balance_error_returns_empty(self):
        """Test that scan_user returns empty list on balance check error."""
        # Create mock components
        mock_wallet = AsyncMock()
        mock_wallet.get_balance = AsyncMock(side_effect=Exception("RPC error"))
        mock_wallet.get_all_user_ids = MagicMock(return_value=["user1"])
        
        mock_scanner = MagicMock()
        mock_provider = MagicMock()
        mock_notifier = AsyncMock()
        mock_user_control = MagicMock()
        mock_risk_manager = MagicMock()
        
        # Create agent loop
        agent_loop = AgentLoop(
            wallet=mock_wallet,
            scanner=mock_scanner,
            provider=mock_provider,
            notifier=mock_notifier,
            user_control=mock_user_control,
            risk_manager=mock_risk_manager,
        )
        
        # Scan user should return empty list on error
        opportunities = await agent_loop.scan_user("user1")
        
        # Should return empty list
        assert opportunities == []
    
    @pytest.mark.asyncio
    async def test_scan_user_no_wallet_returns_empty(self):
        """Test that scan_user returns empty list when user has no wallet."""
        # Create mock components
        mock_wallet = AsyncMock()
        mock_wallet.get_balance = AsyncMock(side_effect=ValueError("No wallet"))
        mock_wallet.get_all_user_ids = MagicMock(return_value=["user1"])
        
        mock_scanner = MagicMock()
        mock_provider = MagicMock()
        mock_notifier = AsyncMock()
        mock_user_control = MagicMock()
        mock_risk_manager = MagicMock()
        
        # Create agent loop
        agent_loop = AgentLoop(
            wallet=mock_wallet,
            scanner=mock_scanner,
            provider=mock_provider,
            notifier=mock_notifier,
            user_control=mock_user_control,
            risk_manager=mock_risk_manager,
        )
        
        # Scan user should return empty list when no wallet
        opportunities = await agent_loop.scan_user("user1")
        
        # Should return empty list
        assert opportunities == []
    
    @pytest.mark.asyncio
    async def test_execute_opportunity_wallet_error_returns_failed_result(self):
        """Test that execute_opportunity returns failed result on wallet error."""
        # Create mock components
        mock_wallet = AsyncMock()
        mock_wallet.get_wallet = AsyncMock(return_value=None)  # No wallet
        
        mock_scanner = MagicMock()
        mock_scanner.strategies = []
        
        mock_provider = MagicMock()
        mock_notifier = AsyncMock()
        mock_user_control = MagicMock()
        mock_risk_manager = MagicMock()
        
        # Create agent loop
        agent_loop = AgentLoop(
            wallet=mock_wallet,
            scanner=mock_scanner,
            provider=mock_provider,
            notifier=mock_notifier,
            user_control=mock_user_control,
            risk_manager=mock_risk_manager,
        )
        
        # Create test opportunity
        opportunity = Opportunity(
            strategy_name="test_strategy",
            action="test_action",
            amount=1.0,
            expected_profit=0.1,
            risk_level="low",
            details={},
            timestamp=datetime.now()
        )
        
        # Execute should return failed result
        result = await agent_loop.execute_opportunity(opportunity, "user1")
        
        # Should return failed result
        assert result.success is False
        assert result.error is not None
        assert "wallet" in result.error.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
