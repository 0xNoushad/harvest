"""
Tests for RPC Fallback Manager integration with API Key Manager.

Feature: multi-api-scaling-optimization
Task: 11.1 - Write unit test for backward compatibility
"""

import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Add harvest directory to path for direct imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import directly from modules to avoid __init__.py dependencies
from agent.core.rpc_fallback import RPCFallbackManager
from agent.core.multi_api_manager import APIKeyManager


class TestRPCFallbackBackwardCompatibility:
    """Test backward compatibility of RPC Fallback Manager."""
    
    def test_initialization_without_api_key_manager(self):
        """
        Test that RPC Fallback Manager works without API Key Manager.        """
        # Should initialize successfully without api_key_manager
        manager = RPCFallbackManager()
        
        assert manager.api_key_manager is None
        assert len(manager.providers) > 0
        assert manager.max_failures_before_fallback == 3
    
    def test_initialization_with_api_key_manager(self):
        """
        Test that RPC Fallback Manager accepts API Key Manager.        """
        keys = ['test_key_1_abcdefghij', 'test_key_2_abcdefghij', 'test_key_3_abcdefghij']
        api_key_manager = APIKeyManager(keys)
        
        manager = RPCFallbackManager(api_key_manager=api_key_manager)
        
        assert manager.api_key_manager is not None
        assert manager.api_key_manager == api_key_manager
        assert len(manager.providers) > 0
    
    @pytest.mark.asyncio
    async def test_rpc_call_without_user_id_parameter(self):
        """
        Test that RPC Fallback Manager works without user_id parameter.        """
        manager = RPCFallbackManager()
        
        # Mock the _call_provider method to simulate successful call
        mock_result = {"blockhash": "test_hash", "lastValidBlockHeight": 12345}
        manager._call_provider = AsyncMock(return_value=mock_result)
        
        # Call without user_id (backward compatible)
        result = await manager.rpc_call("getLatestBlockhash")
        
        assert result == mock_result
        manager._call_provider.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rpc_call_with_user_id_but_no_api_key_manager(self):
        """
        Test that providing user_id without api_key_manager uses standard fallback.        """
        manager = RPCFallbackManager()
        
        # Mock the _call_provider method
        mock_result = {"blockhash": "test_hash", "lastValidBlockHeight": 12345}
        manager._call_provider = AsyncMock(return_value=mock_result)
        
        # Call with user_id but no api_key_manager - should use standard fallback
        result = await manager.rpc_call("getLatestBlockhash", user_id="user_123")
        
        assert result == mock_result
        # Should use standard provider chain, not user-specific routing
        manager._call_provider.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rpc_call_with_both_api_key_manager_and_user_id(self):
        """
        Test that providing both api_key_manager and user_id enables user-specific routing.        """
        keys = ['test_key_1_abcdefghij', 'test_key_2_abcdefghij', 'test_key_3_abcdefghij']
        api_key_manager = APIKeyManager(keys)
        manager = RPCFallbackManager(api_key_manager=api_key_manager)
        
        # Mock the _call_with_user_key method
        mock_result = {"blockhash": "test_hash", "lastValidBlockHeight": 12345}
        manager._call_with_user_key = AsyncMock(return_value=mock_result)
        
        # Call with both api_key_manager and user_id
        result = await manager.rpc_call("getLatestBlockhash", user_id="user_123")
        
        assert result == mock_result
        # Should use user-specific routing
        manager._call_with_user_key.assert_called_once_with(
            "getLatestBlockhash", [], "user_123"
        )
    
    @pytest.mark.asyncio
    async def test_fallback_to_standard_chain_on_user_key_failure(self):
        """
        Test that failures in user-specific routing fall back to standard chain.        """
        keys = ['test_key_1_abcdefghij', 'test_key_2_abcdefghij', 'test_key_3_abcdefghij']
        api_key_manager = APIKeyManager(keys)
        manager = RPCFallbackManager(api_key_manager=api_key_manager)
        
        # Mock _call_with_user_key to fail
        manager._call_with_user_key = AsyncMock(
            side_effect=Exception("User key unavailable")
        )
        
        # Mock _call_provider to succeed
        mock_result = {"blockhash": "test_hash", "lastValidBlockHeight": 12345}
        manager._call_provider = AsyncMock(return_value=mock_result)
        
        # Call should fall back to standard chain
        result = await manager.rpc_call("getLatestBlockhash", user_id="user_123")
        
        assert result == mock_result
        # Should have tried user key first, then fallen back
        manager._call_with_user_key.assert_called_once()
        manager._call_provider.assert_called()


class TestRPCFallbackUserSpecificRouting:
    """Test user-specific key routing functionality."""
    
    @pytest.mark.asyncio
    async def test_user_specific_routing_uses_assigned_key(self):
        """
        Test that user-specific routing uses the user's assigned key.        """
        keys = ['test_key_1_abcdefghij', 'test_key_2_abcdefghij', 'test_key_3_abcdefghij']
        api_key_manager = APIKeyManager(keys)
        manager = RPCFallbackManager(api_key_manager=api_key_manager)
        
        # Assign user to key 0 (user_id with number 1-200)
        user_id = "user_50"
        api_key_manager.assign_user(user_id)
        
        # Mock the _call_with_user_key method directly
        with patch.object(manager, '_call_with_user_key', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"result": {"test": "data"}}
            
            # Make call with user_id
            result = await manager.rpc_call("getLatestBlockhash", user_id=user_id)
            
            # Verify the method was called with correct user_id
            assert mock_call.called
            call_args = mock_call.call_args
            assert call_args[0][2] == user_id  # Third arg is user_id
            assert result == {"result": {"test": "data"}}
    
    @pytest.mark.asyncio
    async def test_rate_limit_marks_key_unavailable(self):
        """
        Test that HTTP 429 marks the user's key as unavailable.        """
        keys = ['test_key_1_abcdefghij', 'test_key_2_abcdefghij', 'test_key_3_abcdefghij']
        api_key_manager = APIKeyManager(keys)
        manager = RPCFallbackManager(api_key_manager=api_key_manager)
        
        user_id = "user_50"
        api_key_manager.assign_user(user_id)
        
        # Verify key is initially available
        assert api_key_manager.keys[0].is_available
        
        # Mock _call_with_user_key to raise rate limit error
        async def mock_rate_limit(*args, **kwargs):
            # Simulate rate limit detection and marking key unavailable
            api_key_manager.handle_rate_limit_error(0)
            raise Exception("Rate limited on user user_50's assigned key")
        
        with patch.object(manager, '_call_with_user_key', side_effect=mock_rate_limit):
            # Mock _call_provider to succeed (for fallback)
            manager._call_provider = AsyncMock(return_value={"result": "fallback"})
            
            # Make call - should detect rate limit and fall back
            result = await manager.rpc_call("getLatestBlockhash", user_id=user_id)
            
            # Verify key was marked unavailable
            assert not api_key_manager.keys[0].is_available
            assert api_key_manager.keys[0].failure_count > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
