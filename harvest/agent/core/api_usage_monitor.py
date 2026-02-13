"""
API Usage Monitor for tracking API key usage and alerting on thresholds.

This module implements request tracking, threshold checking, and daily reset
functionality for monitoring API usage across multiple Helius API keys.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """System alert for API usage thresholds."""
    level: str  # "info", "warning", "critical"
    component: str
    message: str
    timestamp: datetime
    key_index: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KeyUsage:
    """Usage tracking for a single API key."""
    key_index: int
    requests_today: int = 0
    daily_limit: int = 3300
    last_reset: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    alerts_sent: List[str] = field(default_factory=list)
    
    def utilization_percent(self) -> float:
        """Calculate current utilization as percentage of daily limit."""
        if self.daily_limit == 0:
            return 0.0
        return (self.requests_today / self.daily_limit) * 100.0


class APIUsageMonitor:
    """
    Monitor API usage per key with threshold alerting and daily reset.
    
    Tracks request counts for each API key, emits alerts when usage exceeds
    thresholds (80% warning, 95% critical), and resets counters at midnight UTC.
    - 2.4: Return usage statistics on query
    - 2.5: Reset counters at midnight UTC
    """
    
    def __init__(self, daily_limit: int = 3300, num_keys: int = 3):
        """
        Initialize API Usage Monitor.
        
        Args:
            daily_limit: Maximum requests per day per key (default 3300)
            num_keys: Number of API keys to track (default 3)
        """
        self.daily_limit = daily_limit
        self.num_keys = num_keys
        self.usage: Dict[int, KeyUsage] = {}
        
        # Initialize usage tracking for each key
        for i in range(num_keys):
            self.usage[i] = KeyUsage(
                key_index=i,
                daily_limit=daily_limit
            )
        
        logger.info(
            f"APIUsageMonitor initialized with {num_keys} keys, "
            f"daily limit {daily_limit} requests/key"
        )
    
    def record_request(self, key_index: int) -> None:
        """
        Record a single API request for the specified key.        
        Args:
            key_index: Index of the API key (0-2)
        """
        if key_index not in self.usage:
            logger.error(f"Invalid key_index: {key_index}")
            return
        
        self.usage[key_index].requests_today += 1
        
        # Check thresholds after recording
        alert = self.check_thresholds(key_index)
        if alert:
            self._emit_alert(alert)
    
    def check_thresholds(self, key_index: int) -> Optional[Alert]:
        """
        Check if usage has crossed alert thresholds.
        
        Args:
            key_index: Index of the API key to check
            
        Returns:
            Alert object if threshold crossed, None otherwise
        """
        if key_index not in self.usage:
            return None
        
        usage = self.usage[key_index]
        utilization = usage.utilization_percent()
        
        # Critical threshold: 95%
        if utilization >= 95.0 and "critical" not in usage.alerts_sent:
            usage.alerts_sent.append("critical")
            return Alert(
                level="critical",
                component="api_usage_monitor",
                message=f"API key {key_index} at {utilization:.1f}% usage "
                       f"({usage.requests_today}/{usage.daily_limit} requests)",
                timestamp=datetime.now(timezone.utc),
                key_index=key_index,
                metadata={
                    "requests_today": usage.requests_today,
                    "daily_limit": usage.daily_limit,
                    "utilization_percent": utilization
                }
            )
        
        # Warning threshold: 80%
        if utilization >= 80.0 and "warning" not in usage.alerts_sent:
            usage.alerts_sent.append("warning")
            return Alert(
                level="warning",
                component="api_usage_monitor",
                message=f"API key {key_index} at {utilization:.1f}% usage "
                       f"({usage.requests_today}/{usage.daily_limit} requests)",
                timestamp=datetime.now(timezone.utc),
                key_index=key_index,
                metadata={
                    "requests_today": usage.requests_today,
                    "daily_limit": usage.daily_limit,
                    "utilization_percent": utilization
                }
            )
        
        return None
    
    def get_usage(self, key_index: int) -> Dict[str, Any]:
        """
        Get usage statistics for a specific key.        
        Args:
            key_index: Index of the API key
            
        Returns:
            Dictionary with usage statistics
        """
        if key_index not in self.usage:
            return {
                "error": f"Invalid key_index: {key_index}"
            }
        
        usage = self.usage[key_index]
        return {
            "key_index": usage.key_index,
            "requests_today": usage.requests_today,
            "daily_limit": usage.daily_limit,
            "utilization_percent": usage.utilization_percent(),
            "last_reset": usage.last_reset.isoformat(),
            "alerts_sent": usage.alerts_sent.copy()
        }
    
    def get_all_usage(self) -> Dict[str, Any]:
        """
        Get usage statistics for all keys.        
        Returns:
            Dictionary with all keys' usage statistics
        """
        return {
            "keys": [self.get_usage(i) for i in range(self.num_keys)],
            "total_requests": sum(u.requests_today for u in self.usage.values()),
            "total_limit": self.daily_limit * self.num_keys,
            "overall_utilization": self._calculate_overall_utilization()
        }
    
    def reset_daily_counters(self) -> None:
        """
        Reset all daily request counters to zero.        
        This should be called at midnight UTC by a scheduled task.
        """
        reset_time = datetime.now(timezone.utc)
        
        for key_index in self.usage:
            old_count = self.usage[key_index].requests_today
            self.usage[key_index].requests_today = 0
            self.usage[key_index].last_reset = reset_time
            self.usage[key_index].alerts_sent.clear()
            
            logger.info(
                f"Reset counter for key {key_index}: "
                f"{old_count} requests → 0"
            )
        
        logger.info(f"All daily counters reset at {reset_time.isoformat()}")
    
    def _calculate_overall_utilization(self) -> float:
        """Calculate overall utilization across all keys."""
        total_requests = sum(u.requests_today for u in self.usage.values())
        total_limit = self.daily_limit * self.num_keys
        
        if total_limit == 0:
            return 0.0
        
        return (total_requests / total_limit) * 100.0
    
    def _emit_alert(self, alert: Alert) -> None:
        """
        Emit an alert through logging system.
        
        Args:
            alert: Alert object to emit
        """
        log_func = {
            "info": logger.info,
            "warning": logger.warning,
            "critical": logger.critical
        }.get(alert.level, logger.info)
        
        log_func(
            f"[{alert.component}] {alert.message}",
            extra={"alert_metadata": alert.metadata}
        )
