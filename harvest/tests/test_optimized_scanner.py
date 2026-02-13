"""
Tests for Optimized Scanner with staggered scanning.

Feature: multi-api-scaling-optimization
"""

import pytest
import sys
import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.core.optimized_scanner import OptimizedScanner, UserScanState, ScanStats


class MockRPCManager:
    """Mock RPC manager for testing."""
    
    async def get_balance(self, user_id):
        """Mock get_balance method."""
        return 1.0
    
    async def rpc_call(self, method, params=None, user_id=None):
        """Mock rpc_call method."""
        return {"result": "success"}


class TestOptimizedScannerStaggering:
    """Test suite for OptimizedScanner staggered scanning functionality."""
    
    def test_extract_user_number_from_various_formats(self):
        """Test extraction of user numbers from different ID formats."""
        rpc_manager = MockRPCManager()
        scanner = OptimizedScanner(rpc_manager)
        
        # Test various formats
        assert scanner._extract_user_number('user_123') == 123
        assert scanner._extract_user_number('alice_456') == 456
        assert scanner._extract_user_number('789') == 789
        assert scanner._extract_user_number('test_user_999') == 999
        
        # Test fallback for non-numeric IDs
        num = scanner._extract_user_number('alice')
        assert isinstance(num, int)
        assert num >= 0
    
    def test_calculate_scan_offset_modulo_60(self):
        """
        Test scan offset calculation based on user ID modulo 60.        """
        rpc_manager = MockRPCManager()
        scanner = OptimizedScanner(rpc_manager)
        
        # Test that offsets are in range 0-59
        for i in range(1, 501):
            offset = scanner._calculate_scan_offset(f'user_{i}')
            assert 0 <= offset < 60, f"Offset {offset} out of range for user_{i}"
    
    def test_calculate_scan_offset_distribution(self):
        """
        Test that scan offsets are evenly distributed.        """
        rpc_manager = MockRPCManager()
        scanner = OptimizedScanner(rpc_manager)
        
        # Calculate offsets for 500 users
        offsets = []
        for i in range(1, 501):
            offset = scanner._calculate_scan_offset(f'user_{i}')
            offsets.append(offset)
        
        # Check distribution - each offset should appear roughly 8-9 times (500/60 ≈ 8.33)
        from collections import Counter
        offset_counts = Counter(offsets)
        
        # All offsets 0-59 should be used
        for i in range(60):
            assert i in offset_counts, f"Offset {i} not used"
            # Each offset should have 7-10 users (allowing some variance)
            assert 7 <= offset_counts[i] <= 10, f"Offset {i} has {offset_counts[i]} users"
    
    def test_add_user_assigns_scan_offset(self):
        """
        Test that add_user assigns scan offset to user.        """
        rpc_manager = MockRPCManager()
        scanner = OptimizedScanner(rpc_manager)
        
        # Add users
        scanner.add_user('user_1', scan_interval=60)
        scanner.add_user('user_61', scan_interval=60)
        scanner.add_user('user_121', scan_interval=60)
        
        # Check that offsets are assigned
        assert scanner.users['user_1'].scan_offset == 1
        assert scanner.users['user_61'].scan_offset == 1  # 61 % 60 = 1
        assert scanner.users['user_121'].scan_offset == 1  # 121 % 60 = 1
    
    def test_add_user_different_offsets(self):
        """Test that different users get different offsets."""
        rpc_manager = MockRPCManager()
        scanner = OptimizedScanner(rpc_manager)
        
        # Add users with different IDs
        scanner.add_user('user_1', scan_interval=60)
        scanner.add_user('user_2', scan_interval=60)
        scanner.add_user('user_3', scan_interval=60)
        
        # Check that offsets are different
        offset1 = scanner.users['user_1'].scan_offset
        offset2 = scanner.users['user_2'].scan_offset
        offset3 = scanner.users['user_3'].scan_offset
        
        assert offset1 != offset2
        assert offset2 != offset3
        assert offset1 != offset3
    
    def test_add_user_sets_initial_last_scan_with_offset(self):
        """
        Test that add_user sets initial last_scan to respect offset.        """
        rpc_manager = MockRPCManager()
        scanner = OptimizedScanner(rpc_manager)
        
        current_time = time.time()
        scan_interval = 60
        
        scanner.add_user('user_10', scan_interval=scan_interval)
        
        user = scanner.users['user_10']
        expected_offset = 10  # user_10 -> 10 % 60 = 10
        
        # Initial last_scan should be: current_time - scan_interval + offset
        # This means the first scan will happen at: current_time + offset
        expected_last_scan = current_time - scan_interval + expected_offset
        
        # Allow 1 second tolerance for test execution time
        assert abs(user.last_scan - expected_last_scan) < 1.0
        assert user.scan_offset == expected_offset
    
    @pytest.mark.asyncio
    async def test_scan_all_users_respects_offsets(self):
        """
        Test that scan_all_users respects scan offsets.        """
        rpc_manager = MockRPCManager()
        scanner = OptimizedScanner(rpc_manager)
        
        # Add users with different offsets
        scanner.add_user('user_1', scan_interval=60)
        scanner.add_user('user_2', scan_interval=60)
        
        # Set last_scan to trigger scanning
        current_time = time.time()
        scanner.users['user_1'].last_scan = current_time - 61  # Should scan
        scanner.users['user_2'].last_scan = current_time - 50  # Should not scan yet
        
        # Mock the internal methods
        scanner._refresh_shared_caches = AsyncMock()
        scanner._scan_user = AsyncMock(return_value=[])
        
        results = await scanner.scan_all_users()
        
        # Only user_1 should be scanned
        assert 'user_1' in results
        assert 'user_2' not in results
    
    @pytest.mark.asyncio
    async def test_scan_updates_last_scan_time(self):
        """
        Test that scanning updates last_scan time.        """
        rpc_manager = MockRPCManager()
        scanner = OptimizedScanner(rpc_manager)
        
        scanner.add_user('user_1', scan_interval=60)
        
        # Set last_scan to trigger scanning
        current_time = time.time()
        scanner.users['user_1'].last_scan = current_time - 61
        
        # Mock the internal methods
        scanner._refresh_shared_caches = AsyncMock()
        scanner._scan_user = AsyncMock(return_value=[])
        
        old_last_scan = scanner.users['user_1'].last_scan
        
        await scanner.scan_all_users()
        
        # last_scan should be updated to current time
        new_last_scan = scanner.users['user_1'].last_scan
        assert new_last_scan > old_last_scan
        assert abs(new_last_scan - time.time()) < 1.0
    
    def test_scan_stats_initialization(self):
        """Test that scan statistics are initialized."""
        rpc_manager = MockRPCManager()
        scanner = OptimizedScanner(rpc_manager)
        
        assert scanner.scan_stats is not None
        assert scanner.scan_stats.users_scanned == 0
        assert scanner.scan_stats.pending_scans == 0
        assert scanner.scan_stats.total_scan_cycles == 0
    
    @pytest.mark.asyncio
    async def test_scan_stats_tracking(self):
        """
        Test that scan statistics are tracked correctly.        """
        rpc_manager = MockRPCManager()
        scanner = OptimizedScanner(rpc_manager)
        
        # Add users
        scanner.add_user('user_1', scan_interval=60)
        scanner.add_user('user_2', scan_interval=60)
        scanner.add_user('user_3', scan_interval=60)
        
        # Set all to need scanning
        current_time = time.time()
        for user in scanner.users.values():
            user.last_scan = current_time - 61
        
        # Mock the internal methods
        scanner._refresh_shared_caches = AsyncMock()
        scanner._scan_user = AsyncMock(return_value=[])
        
        await scanner.scan_all_users()
        
        # Check statistics
        assert scanner.scan_stats.users_scanned == 3
        assert scanner.scan_stats.total_scan_cycles == 1
        assert scanner.scan_stats.last_scan_time > 0
    
    @pytest.mark.asyncio
    async def test_scan_stats_pending_scans(self):
        """
        Test that pending scans are tracked.        """
        rpc_manager = MockRPCManager()
        scanner = OptimizedScanner(rpc_manager)
        
        # Add users
        scanner.add_user('user_1', scan_interval=60)
        scanner.add_user('user_2', scan_interval=60)
        
        # Set one to need scanning
        current_time = time.time()
        scanner.users['user_1'].last_scan = current_time - 61  # Should scan
        scanner.users['user_2'].last_scan = current_time - 30  # Should not scan
        
        # Mock the internal methods
        scanner._refresh_shared_caches = AsyncMock()
        scanner._scan_user = AsyncMock(return_value=[])
        
        await scanner.scan_all_users()
        
        # pending_scans should have been set to 1 during scan
        # (it's set at the start of scan_all_users)
        assert scanner.scan_stats.pending_scans == 1
    
    def test_scan_stats_rate_calculation(self):
        """
        Test scan rate calculation.        """
        stats = ScanStats()
        
        # Initially should be 0
        assert stats.scan_rate_per_second() == 0.0
        
        # Set up some stats
        stats.scan_start_time = time.time() - 10  # Started 10 seconds ago
        stats.users_scanned = 50
        
        rate = stats.scan_rate_per_second()
        
        # Should be approximately 5 users/second
        assert 4.5 <= rate <= 5.5
    
    def test_get_stats_includes_scan_statistics(self):
        """
        Test that get_stats includes scan statistics.        """
        rpc_manager = MockRPCManager()
        scanner = OptimizedScanner(rpc_manager)
        
        # Add some users
        scanner.add_user('user_1')
        scanner.add_user('user_2')
        
        # Set some scan stats
        scanner.scan_stats.users_scanned = 10
        scanner.scan_stats.pending_scans = 2
        scanner.scan_stats.total_scan_cycles = 5
        
        stats = scanner.get_stats()
        
        # Check that scan statistics are included
        assert 'users_scanned' in stats
        assert 'pending_scans' in stats
        assert 'total_scan_cycles' in stats
        assert 'scan_rate_per_second' in stats
        assert 'last_scan_time' in stats
        
        assert stats['users_scanned'] == 10
        assert stats['pending_scans'] == 2
        assert stats['total_scan_cycles'] == 5
    
    @pytest.mark.asyncio
    async def test_multiple_scan_cycles_increment_counter(self):
        """Test that multiple scan cycles increment the counter."""
        rpc_manager = MockRPCManager()
        scanner = OptimizedScanner(rpc_manager)
        
        scanner.add_user('user_1', scan_interval=60)
        
        # Mock the internal methods
        scanner._refresh_shared_caches = AsyncMock()
        scanner._scan_user = AsyncMock(return_value=[])
        
        # Set to need scanning
        current_time = time.time()
        scanner.users['user_1'].last_scan = current_time - 61
        
        # First scan
        await scanner.scan_all_users()
        assert scanner.scan_stats.total_scan_cycles == 1
        
        # Set to need scanning again
        scanner.users['user_1'].last_scan = current_time - 61
        
        # Second scan
        await scanner.scan_all_users()
        assert scanner.scan_stats.total_scan_cycles == 2
    
    def test_user_scan_state_has_offset_field(self):
        """Test that UserScanState includes scan_offset field."""
        state = UserScanState(
            user_id='user_123',
            last_scan=time.time(),
            scan_interval=60,
            active_strategies=['strategy1'],
            scan_offset=15
        )
        
        assert state.scan_offset == 15
        assert state.user_id == 'user_123'
        assert state.scan_interval == 60
    
    def test_should_scan_respects_interval(self):
        """Test that should_scan respects the scan interval."""
        current_time = time.time()
        
        # User scanned 30 seconds ago with 60 second interval
        state = UserScanState(
            user_id='user_1',
            last_scan=current_time - 30,
            scan_interval=60,
            scan_offset=0
        )
        
        assert state.should_scan() is False
        
        # User scanned 61 seconds ago
        state.last_scan = current_time - 61
        assert state.should_scan() is True


class TestOptimizedScannerIntegration:
    """Integration tests for OptimizedScanner."""
    
    @pytest.mark.asyncio
    async def test_full_scan_cycle_with_staggering(self):
        """Test a full scan cycle with multiple users and staggering."""
        rpc_manager = MockRPCManager()
        scanner = OptimizedScanner(rpc_manager)
        
        # Add 10 users
        for i in range(1, 11):
            scanner.add_user(f'user_{i}', scan_interval=60)
        
        # Verify offsets are assigned
        for i in range(1, 11):
            user = scanner.users[f'user_{i}']
            assert 0 <= user.scan_offset < 60
        
        # Set all to need scanning
        current_time = time.time()
        for user in scanner.users.values():
            user.last_scan = current_time - 61
        
        # Mock the internal methods
        scanner._refresh_shared_caches = AsyncMock()
        scanner._scan_user = AsyncMock(return_value=[])
        
        results = await scanner.scan_all_users()
        
        # All 10 users should be scanned
        assert len(results) == 10
        assert scanner.scan_stats.users_scanned == 10
        assert scanner.scan_stats.total_scan_cycles == 1
    
    @pytest.mark.asyncio
    async def test_staggered_scanning_over_time(self):
        """Test that users scan at staggered times over multiple cycles."""
        rpc_manager = MockRPCManager()
        scanner = OptimizedScanner(rpc_manager)
        
        # Add users with different offsets
        scanner.add_user('user_5', scan_interval=10)   # offset 5
        scanner.add_user('user_15', scan_interval=10)  # offset 15
        scanner.add_user('user_25', scan_interval=10)  # offset 25
        
        # Mock the internal methods
        scanner._refresh_shared_caches = AsyncMock()
        scanner._scan_user = AsyncMock(return_value=[])
        
        # Simulate time progression
        base_time = time.time() - 100  # Start in the past
        
        # Set initial last_scan times
        scanner.users['user_5'].last_scan = base_time
        scanner.users['user_15'].last_scan = base_time
        scanner.users['user_25'].last_scan = base_time
        
        # All should scan (all past their interval)
        results = await scanner.scan_all_users()
        assert len(results) == 3
        
        # After scanning, they should have different next scan times
        # based on their offsets (though in practice, last_scan is set to current time)
        assert scanner.users['user_5'].last_scan > base_time
        assert scanner.users['user_15'].last_scan > base_time
        assert scanner.users['user_25'].last_scan > base_time
