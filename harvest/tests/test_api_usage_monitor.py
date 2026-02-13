"""
Tests for API Usage Monitor component.

Feature: multi-api-scaling-optimization
"""

import pytest
from datetime import datetime, timezone
from agent.core.api_usage_monitor import APIUsageMonitor, KeyUsage, Alert


class TestAPIUsageMonitor:
    """Test suite for APIUsageMonitor class."""
    
    def test_initialization(self):
        """Test that monitor initializes with correct defaults."""
        monitor = APIUsageMonitor()
        
        assert monitor.daily_limit == 3300
        assert monitor.num_keys == 3
        assert len(monitor.usage) == 3
        
        for i in range(3):
            assert i in monitor.usage
            assert monitor.usage[i].key_index == i
            assert monitor.usage[i].requests_today == 0
            assert monitor.usage[i].daily_limit == 3300
    
    def test_record_request_increments_counter(self):
        """Test that recording a request increments the counter (Requirement 2.1)."""
        monitor = APIUsageMonitor()
        
        # Record requests for key 0
        monitor.record_request(0)
        assert monitor.usage[0].requests_today == 1
        
        monitor.record_request(0)
        assert monitor.usage[0].requests_today == 2
        
        # Other keys should remain at 0
        assert monitor.usage[1].requests_today == 0
        assert monitor.usage[2].requests_today == 0
    
    def test_warning_alert_at_80_percent(self):
        """Test warning alert at 80% threshold (Requirement 2.2)."""
        monitor = APIUsageMonitor(daily_limit=3300)
        
        # Set to exactly 80% (2640 requests)
        monitor.usage[0].requests_today = 2640
        monitor.usage[0].alerts_sent.clear()
        
        alert = monitor.check_thresholds(0)
        assert alert is not None
        assert alert.level == "warning"
        assert alert.key_index == 0
        assert "80" in alert.message
    
    def test_critical_alert_at_95_percent(self):
        """Test critical alert at 95% threshold (Requirement 2.3)."""
        monitor = APIUsageMonitor(daily_limit=3300)
        
        # Set to 95% and check
        monitor.usage[0].requests_today = 3135
        monitor.usage[0].alerts_sent.clear()
        
        alert = monitor.check_thresholds(0)
        assert alert is not None
        assert alert.level == "critical"
        assert alert.key_index == 0
        assert "95" in alert.message
    
    def test_get_usage_returns_statistics(self):
        """Test that get_usage returns correct statistics (Requirement 2.4)."""
        monitor = APIUsageMonitor()
        
        # Record some requests
        for _ in range(100):
            monitor.record_request(0)
        
        usage = monitor.get_usage(0)
        
        assert usage["key_index"] == 0
        assert usage["requests_today"] == 100
        assert usage["daily_limit"] == 3300
        assert "utilization_percent" in usage
        assert "last_reset" in usage
        assert "alerts_sent" in usage
    
    def test_get_all_usage_returns_all_keys(self):
        """Test that get_all_usage returns statistics for all keys (Requirement 2.4)."""
        monitor = APIUsageMonitor()
        
        # Record requests on different keys
        for _ in range(50):
            monitor.record_request(0)
        for _ in range(75):
            monitor.record_request(1)
        for _ in range(25):
            monitor.record_request(2)
        
        all_usage = monitor.get_all_usage()
        
        assert "keys" in all_usage
        assert len(all_usage["keys"]) == 3
        assert all_usage["total_requests"] == 150
        assert all_usage["total_limit"] == 9900  # 3300 * 3
    
    def test_reset_daily_counters(self):
        """Test that reset clears all counters (Requirement 2.5)."""
        monitor = APIUsageMonitor()
        
        # Record requests on all keys
        for _ in range(100):
            monitor.record_request(0)
        for _ in range(200):
            monitor.record_request(1)
        for _ in range(300):
            monitor.record_request(2)
        
        # Verify counters are set
        assert monitor.usage[0].requests_today == 100
        assert monitor.usage[1].requests_today == 200
        assert monitor.usage[2].requests_today == 300
        
        # Reset counters
        monitor.reset_daily_counters()
        
        # Verify all counters are zero
        assert monitor.usage[0].requests_today == 0
        assert monitor.usage[1].requests_today == 0
        assert monitor.usage[2].requests_today == 0
        
        # Verify alerts are cleared
        assert len(monitor.usage[0].alerts_sent) == 0
        assert len(monitor.usage[1].alerts_sent) == 0
        assert len(monitor.usage[2].alerts_sent) == 0
    
    def test_utilization_percent_calculation(self):
        """Test that utilization percentage is calculated correctly."""
        usage = KeyUsage(key_index=0, requests_today=1650, daily_limit=3300)
        
        assert usage.utilization_percent() == 50.0
    
    def test_alert_only_sent_once_per_threshold(self):
        """Test that alerts are only sent once per threshold level."""
        monitor = APIUsageMonitor(daily_limit=100)
        
        # Set to warning threshold and check
        monitor.usage[0].requests_today = 80
        monitor.usage[0].alerts_sent.clear()
        
        alert1 = monitor.check_thresholds(0)
        assert alert1 is not None
        assert alert1.level == "warning"
        
        # Try to get alert again - should be None since already sent
        alert2 = monitor.check_thresholds(0)
        assert alert2 is None
        
        # Cross critical threshold (95 requests)
        monitor.usage[0].requests_today = 95
        
        alert3 = monitor.check_thresholds(0)
        assert alert3 is not None
        assert alert3.level == "critical"
    
    def test_invalid_key_index_handling(self):
        """Test that invalid key indices are handled gracefully."""
        monitor = APIUsageMonitor()
        
        # Try to record request for invalid key
        monitor.record_request(99)  # Should not crash
        
        # Try to get usage for invalid key
        usage = monitor.get_usage(99)
        assert "error" in usage


class TestKeyUsage:
    """Test suite for KeyUsage data model."""
    
    def test_key_usage_initialization(self):
        """Test KeyUsage initialization with defaults."""
        usage = KeyUsage(key_index=0)
        
        assert usage.key_index == 0
        assert usage.requests_today == 0
        assert usage.daily_limit == 3300
        assert isinstance(usage.last_reset, datetime)
        assert len(usage.alerts_sent) == 0
    
    def test_utilization_percent_zero_limit(self):
        """Test utilization calculation with zero limit."""
        usage = KeyUsage(key_index=0, daily_limit=0)
        
        assert usage.utilization_percent() == 0.0


class TestAlert:
    """Test suite for Alert data model."""
    
    def test_alert_creation(self):
        """Test Alert creation with all fields."""
        alert = Alert(
            level="warning",
            component="test_component",
            message="Test message",
            timestamp=datetime.now(timezone.utc),
            key_index=0,
            metadata={"test": "data"}
        )
        
        assert alert.level == "warning"
        assert alert.component == "test_component"
        assert alert.message == "Test message"
        assert alert.key_index == 0
        assert alert.metadata["test"] == "data"
