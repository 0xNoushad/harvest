"""
Tests for API Key Manager component.

Feature: multi-api-scaling-optimization
"""

import pytest
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.core.multi_api_manager import APIKeyManager, APIKeyConfig, UserAssignment
from agent.core.api_usage_monitor import APIUsageMonitor


class TestAPIKeyManager:
    """Test suite for APIKeyManager class."""
    
    def test_initialization_with_valid_keys(self):
        """Test initialization with 3 valid keys (Requirement 1.1)."""
        keys = ['test_key_1_abcdefghij', 'test_key_2_abcdefghij', 'test_key_3_abcdefghij']
        manager = APIKeyManager(keys)
        
        assert len(manager.keys) == 3
        assert 0 in manager.keys
        assert 1 in manager.keys
        assert 2 in manager.keys
        
        # Verify key configurations
        assert manager.keys[0].index == 0
        assert manager.keys[0].user_range == (1, 200)
        assert manager.keys[1].index == 1
        assert manager.keys[1].user_range == (201, 400)
        assert manager.keys[2].index == 2
        assert manager.keys[2].user_range == (401, 500)
    
    def test_initialization_excludes_invalid_keys(self):
        """Test that invalid keys are excluded (Requirement 1.4)."""
        keys = ['valid_key_1_abcdefghij', '', 'valid_key_3_abcdefghij']
        manager = APIKeyManager(keys)
        
        # Should only load keys at index 0 and 2
        assert len(manager.keys) == 2
        assert 0 in manager.keys
        assert 1 not in manager.keys  # Empty key excluded
        assert 2 in manager.keys
    
    def test_initialization_excludes_short_keys(self):
        """Test that short/invalid keys are excluded (Requirement 1.4)."""
        keys = ['valid_key_1_abcdefghij', 'short', 'valid_key_3_abcdefghij']
        manager = APIKeyManager(keys)
        
        # Should only load keys at index 0 and 2
        assert len(manager.keys) == 2
        assert 0 in manager.keys
        assert 1 not in manager.keys  # Short key excluded
        assert 2 in manager.keys
    
    def test_user_assignment_range_1_to_200(self):
        """Test user assignment for range 1-200 to key 0 (Requirement 1.2)."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        # Test users in range 1-200
        assert manager.assign_user('user_1') == 0
        assert manager.assign_user('user_50') == 0
        assert manager.assign_user('user_100') == 0
        assert manager.assign_user('user_200') == 0
    
    def test_user_assignment_range_201_to_400(self):
        """Test user assignment for range 201-400 to key 1 (Requirement 1.2)."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        # Test users in range 201-400
        assert manager.assign_user('user_201') == 1
        assert manager.assign_user('user_250') == 1
        assert manager.assign_user('user_300') == 1
        assert manager.assign_user('user_400') == 1
    
    def test_user_assignment_range_401_to_500(self):
        """Test user assignment for range 401-500 to key 2 (Requirement 1.2)."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        # Test users in range 401-500
        assert manager.assign_user('user_401') == 2
        assert manager.assign_user('user_450') == 2
        assert manager.assign_user('user_500') == 2
    
    def test_user_number_extraction_from_various_formats(self):
        """Test extraction of user numbers from different ID formats."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        # Test various formats
        assert manager._extract_user_number('user_123') == 123
        assert manager._extract_user_number('alice_456') == 456
        assert manager._extract_user_number('789') == 789
        assert manager._extract_user_number('test_user_999') == 999
        
        # Test fallback for non-numeric IDs
        num = manager._extract_user_number('alice')
        assert 1 <= num <= 500  # Should be in valid range
    
    def test_get_key_for_user_returns_correct_key(self):
        """Test that get_key_for_user returns the assigned key (Requirement 1.3)."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        # Assign users
        manager.assign_user('user_50')
        manager.assign_user('user_250')
        manager.assign_user('user_450')
        
        # Get keys
        key1 = manager.get_key_for_user('user_50')
        key2 = manager.get_key_for_user('user_250')
        key3 = manager.get_key_for_user('user_450')
        
        assert key1 == 'key1_abcdefghij'
        assert key2 == 'key2_abcdefghij'
        assert key3 == 'key3_abcdefghij'
    
    def test_get_key_for_user_auto_assigns(self):
        """Test that get_key_for_user auto-assigns unassigned users."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        # Get key without prior assignment
        key = manager.get_key_for_user('user_100')
        
        assert key is not None
        assert 'user_100' in manager.user_assignments
        assert manager.user_assignments['user_100'].key_index == 0
    
    def test_get_rpc_url_for_user_returns_correct_url(self):
        """Test that get_rpc_url_for_user returns correct URL (Requirement 1.3)."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        url = manager.get_rpc_url_for_user('user_100')
        
        assert url is not None
        assert 'https://mainnet.helius-rpc.com' in url
        assert 'key1_abcdefghij' in url
    
    def test_mark_key_unavailable(self):
        """Test marking a key as unavailable."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        # Mark key 0 unavailable
        manager.mark_key_unavailable(0)
        
        assert manager.keys[0].is_available is False
        assert manager.keys[0].failure_count == 1
        
        # Get key should return None for unavailable key
        key = manager.get_key_for_user('user_100')
        assert key is None
    
    def test_mark_key_available(self):
        """Test marking a key as available."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        # Mark unavailable then available
        manager.mark_key_unavailable(0)
        assert manager.keys[0].is_available is False
        
        manager.mark_key_available(0)
        assert manager.keys[0].is_available is True
        assert manager.keys[0].last_test is not None
    
    def test_get_status_returns_complete_info(self):
        """Test that get_status returns complete information (Requirement 1.5)."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        # Assign some users
        manager.assign_user('user_50')
        manager.assign_user('user_100')
        manager.assign_user('user_250')
        
        status = manager.get_status()
        
        assert status['total_keys'] == 3
        assert status['valid_keys'] == 3
        assert status['available_keys'] == 3
        assert status['total_users'] == 3
        assert 'keys' in status
        assert len(status['keys']) == 3
        assert 'users_by_key' in status
    
    def test_get_status_with_unavailable_keys(self):
        """Test get_status with some keys unavailable."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        # Mark one key unavailable
        manager.mark_key_unavailable(1)
        
        status = manager.get_status()
        
        assert status['available_keys'] == 2
        assert status['keys'][1]['is_available'] is False
    
    def test_get_assignment_returns_user_details(self):
        """Test that get_assignment returns user assignment details."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        manager.assign_user('user_123')
        
        assignment = manager.get_assignment('user_123')
        
        assert assignment is not None
        assert assignment['user_id'] == 'user_123'
        assert assignment['user_number'] == 123
        assert assignment['key_index'] == 0
        assert 'assigned_at' in assignment
    
    def test_get_assignment_returns_none_for_unassigned(self):
        """Test that get_assignment returns None for unassigned users."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        assignment = manager.get_assignment('user_999')
        
        assert assignment is None
    
    def test_integration_with_usage_monitor(self):
        """Test integration with APIUsageMonitor."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        monitor = APIUsageMonitor()
        manager = APIKeyManager(keys, monitor)
        
        # Get key for user (should record request)
        manager.get_key_for_user('user_100')
        
        # Check that request was recorded
        usage = monitor.get_usage(0)
        assert usage['requests_today'] == 1
        
        # Get key again
        manager.get_key_for_user('user_100')
        usage = monitor.get_usage(0)
        assert usage['requests_today'] == 2
    
    def test_multiple_users_same_key(self):
        """Test that multiple users can be assigned to the same key."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        # Assign multiple users to key 0 range
        for i in range(1, 11):
            key_idx = manager.assign_user(f'user_{i}')
            assert key_idx == 0
        
        status = manager.get_status()
        assert status['users_by_key']['0'] == 10


class TestAPIKeyConfig:
    """Test suite for APIKeyConfig data model."""
    
    def test_api_key_config_initialization(self):
        """Test APIKeyConfig initialization."""
        config = APIKeyConfig(
            index=0,
            key='test_key',
            url='https://test.com',
            user_range=(1, 200)
        )
        
        assert config.index == 0
        assert config.key == 'test_key'
        assert config.url == 'https://test.com'
        assert config.user_range == (1, 200)
        assert config.is_available is True
        assert config.failure_count == 0
        assert config.last_test is None


class TestUserAssignment:
    """Test suite for UserAssignment data model."""
    
    def test_user_assignment_initialization(self):
        """Test UserAssignment initialization."""
        assignment = UserAssignment(
            user_id='user_123',
            user_number=123,
            key_index=0
        )
        
        assert assignment.user_id == 'user_123'
        assert assignment.user_number == 123
        assert assignment.key_index == 0
        assert isinstance(assignment.assigned_at, datetime)


class TestFailoverLogic:
    """Test suite for automatic failover logic (Task 3)."""
    
    def test_handle_rate_limit_error_marks_key_unavailable(self):
        """Test that rate limit error marks key unavailable (Requirement 3.1)."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        # Handle rate limit error
        manager.handle_rate_limit_error(0)
        
        assert manager.keys[0].is_available is False
        assert manager.keys[0].failure_count == 1
        assert manager.keys[0].unavailable_since is not None
    
    def test_should_use_fallback_when_key_unavailable(self):
        """Test that should_use_fallback returns True when key unavailable (Requirement 3.2)."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        # Assign user to key 0
        manager.assign_user('user_100')
        
        # Initially should not use fallback
        assert manager.should_use_fallback('user_100') is False
        
        # Mark key unavailable
        manager.mark_key_unavailable(0, reason="rate_limit")
        
        # Now should use fallback
        assert manager.should_use_fallback('user_100') is True
    
    def test_should_use_fallback_when_all_keys_unavailable(self):
        """Test that should_use_fallback returns True when all keys unavailable (Requirement 3.5)."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        # Mark all keys unavailable
        manager.mark_key_unavailable(0)
        manager.mark_key_unavailable(1)
        manager.mark_key_unavailable(2)
        
        # Should use fallback for any user
        assert manager.should_use_fallback('user_100') is True
        assert manager.should_use_fallback('user_300') is True
        assert manager.should_use_fallback('user_500') is True
    
    @pytest.mark.asyncio
    async def test_test_key_availability_success(self):
        """Test that test_key_availability detects available key (Requirement 3.3)."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        # Mock the HTTP request to return success
        import aiohttp
        from unittest.mock import AsyncMock, patch, MagicMock
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await manager.test_key_availability(0)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_test_key_availability_rate_limited(self):
        """Test that test_key_availability detects rate limit (Requirement 3.3)."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        # Mock the HTTP request to return 429
        from unittest.mock import AsyncMock, patch, MagicMock
        
        mock_response = MagicMock()
        mock_response.status = 429
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await manager.test_key_availability(0)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_mark_key_available_after_successful_test(self):
        """Test that key is marked available after successful test (Requirement 3.4)."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        # Mark key unavailable
        manager.mark_key_unavailable(0, reason="rate_limit")
        assert manager.keys[0].is_available is False
        
        # Mark available (simulating successful test)
        manager.mark_key_available(0)
        
        assert manager.keys[0].is_available is True
        assert manager.keys[0].last_test is not None
        assert manager.keys[0].unavailable_since is None
        assert manager.keys[0].recovery_attempts == 0
    
    def test_mark_key_unavailable_with_reason(self):
        """Test that mark_key_unavailable accepts reason parameter."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        manager.mark_key_unavailable(0, reason="rate_limit")
        
        assert manager.keys[0].is_available is False
        assert manager.keys[0].unavailable_since is not None
    
    def test_get_status_includes_unavailable_duration(self):
        """Test that get_status includes unavailable duration."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        # Mark key unavailable
        manager.mark_key_unavailable(0, reason="rate_limit")
        
        status = manager.get_status()
        
        # Check that unavailable key has duration info
        key_0_status = status['keys'][0]
        assert key_0_status['is_available'] is False
        assert 'unavailable_duration_seconds' in key_0_status
        assert 'unavailable_since' in key_0_status
        assert key_0_status['recovery_attempts'] == 0
    
    def test_recovery_attempts_increment(self):
        """Test that recovery attempts are tracked."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        # Mark unavailable
        manager.mark_key_unavailable(0)
        
        # Simulate recovery attempts
        manager.keys[0].recovery_attempts = 1
        manager.keys[0].recovery_attempts = 2
        
        assert manager.keys[0].recovery_attempts == 2
        
        # Mark available should reset
        manager.mark_key_available(0)
        assert manager.keys[0].recovery_attempts == 0
    
    def test_stop_recovery_monitoring(self):
        """Test that recovery monitoring can be stopped."""
        keys = ['key1_abcdefghij', 'key2_abcdefghij', 'key3_abcdefghij']
        manager = APIKeyManager(keys)
        
        # Stop monitoring (should not raise error even if not started)
        manager.stop_recovery_monitoring()
        
        # Verify task is cancelled if it exists
        if manager._recovery_task:
            assert manager._recovery_task.cancelled() or manager._recovery_task.done()
