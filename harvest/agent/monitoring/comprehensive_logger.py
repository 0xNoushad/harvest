"""
Comprehensive Logging and Monitoring

Implements Property 66: Comprehensive logging for all significant events.
Logs operations, errors, trades, API calls, rate limits, circuit breakers,
fee collection, user interactions, and system metrics.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class EventType(Enum):
    """Types of events to log."""
    OPERATION = "operation"
    ERROR = "error"
    TRADE = "trade"
    API_CALL = "api_call"
    RATE_LIMIT = "rate_limit"
    CIRCUIT_BREAKER = "circuit_breaker"
    FEE_COLLECTION = "fee_collection"
    USER_INTERACTION = "user_interaction"
    SYSTEM_METRIC = "system_metric"
    SECURITY = "security"


class LogLevel(Enum):
    """Log levels."""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class ComprehensiveLogger:
    """
    Comprehensive logger for all significant events.
    
    Implements structured logging with full context for:
    - Operations (commands, trades, withdrawals)
    - Errors (with stack traces and context)
    - Trades (execution, profit, strategy)
    - API calls (service, endpoint, response time)
    - Rate limits (service, user, cooldown)
    - Circuit breakers (trigger, reason, affected users)
    - Fee collection (amount, user, transaction)
    - User interactions (command, parameters, timestamp)
    - System metrics (memory, CPU, active users)
    """
    
    def __init__(self, component: str):
        """
        Initialize comprehensive logger.
        
        Args:
            component: Component name (e.g., "trading", "telegram", "risk")
        """
        self.component = component
        self.logger = logging.getLogger(f"harvest.{component}")
    
    def _log_with_context(
        self,
        level: LogLevel,
        event_type: EventType,
        message: str,
        **context
    ):
        """
        Log message with structured context.
        
        Args:
            level: Log level
            event_type: Type of event
            message: Log message
            **context: Additional context key-value pairs
        """
        # Add standard context
        context.update({
            "component": self.component,
            "event_type": event_type.value,
            "timestamp": datetime.now().isoformat(),
        })
        
        # Create extra dict for logging
        extra = {"extra_context": context}
        
        self.logger.log(level.value, message, extra=extra)
    
    # Operation Logging
    
    def log_operation_start(
        self,
        operation: str,
        user_id: Optional[int] = None,
        **params
    ):
        """
        Log operation start.
        
        Args:
            operation: Operation name
            user_id: User ID if applicable
            **params: Operation parameters
        """
        context = {"operation": operation, "status": "started"}
        if user_id:
            context["user_id"] = user_id
        context.update(params)
        
        self._log_with_context(
            LogLevel.INFO,
            EventType.OPERATION,
            f"Operation started: {operation}",
            **context
        )
    
    def log_operation_complete(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        user_id: Optional[int] = None,
        **result
    ):
        """
        Log operation completion.
        
        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            success: Whether operation succeeded
            user_id: User ID if applicable
            **result: Operation result data
        """
        context = {
            "operation": operation,
            "status": "completed" if success else "failed",
            "duration_ms": f"{duration_ms:.2f}",
        }
        if user_id:
            context["user_id"] = user_id
        context.update(result)
        
        level = LogLevel.INFO if success else LogLevel.ERROR
        
        self._log_with_context(
            level,
            EventType.OPERATION,
            f"Operation {'completed' if success else 'failed'}: {operation}",
            **context
        )
    
    # Error Logging
    
    def log_error(
        self,
        error_type: str,
        error_message: str,
        user_id: Optional[int] = None,
        stack_trace: Optional[str] = None,
        **context
    ):
        """
        Log error with full context.
        
        Args:
            error_type: Type of error
            error_message: Error message
            user_id: User ID if applicable
            stack_trace: Stack trace if available
            **context: Additional error context
        """
        error_context = {
            "error_type": error_type,
            "error_message": error_message,
        }
        if user_id:
            error_context["user_id"] = user_id
        if stack_trace:
            error_context["stack_trace"] = stack_trace
        error_context.update(context)
        
        self._log_with_context(
            LogLevel.ERROR,
            EventType.ERROR,
            f"Error occurred: {error_type} - {error_message}",
            **error_context
        )
    
    # Trade Logging
    
    def log_trade_execution(
        self,
        strategy: str,
        action: str,
        expected_profit: float,
        actual_profit: Optional[float] = None,
        execution_time_ms: Optional[float] = None,
        transaction_hash: Optional[str] = None,
        success: bool = True,
        user_id: Optional[int] = None,
        **details
    ):
        """
        Log trade execution.
        
        Args:
            strategy: Strategy name
            action: Action type
            expected_profit: Expected profit in SOL
            actual_profit: Actual profit in SOL (if completed)
            execution_time_ms: Execution time in milliseconds
            transaction_hash: Transaction hash if successful
            success: Whether trade succeeded
            user_id: User ID
            **details: Additional trade details
        """
        context = {
            "strategy": strategy,
            "action": action,
            "expected_profit": f"{expected_profit:.4f}",
            "success": success,
        }
        if user_id:
            context["user_id"] = user_id
        if actual_profit is not None:
            context["actual_profit"] = f"{actual_profit:.4f}"
        if execution_time_ms is not None:
            context["execution_time_ms"] = f"{execution_time_ms:.2f}"
        if transaction_hash:
            context["transaction_hash"] = transaction_hash
        context.update(details)
        
        level = LogLevel.INFO if success else LogLevel.ERROR
        
        self._log_with_context(
            level,
            EventType.TRADE,
            f"Trade {'executed' if success else 'failed'}: {strategy} - {action}",
            **context
        )
    
    # API Call Logging
    
    def log_api_call(
        self,
        service: str,
        endpoint: str,
        method: str = "GET",
        response_time_ms: Optional[float] = None,
        status_code: Optional[int] = None,
        success: bool = True,
        error: Optional[str] = None,
        **params
    ):
        """
        Log API call.
        
        Args:
            service: Service name (e.g., "groq", "helius", "jupiter")
            endpoint: API endpoint
            method: HTTP method
            response_time_ms: Response time in milliseconds
            status_code: HTTP status code
            success: Whether call succeeded
            error: Error message if failed
            **params: Request parameters
        """
        context = {
            "service": service,
            "endpoint": endpoint,
            "method": method,
            "success": success,
        }
        if response_time_ms is not None:
            context["response_time_ms"] = f"{response_time_ms:.2f}"
        if status_code is not None:
            context["status_code"] = status_code
        if error:
            context["error"] = error
        context.update(params)
        
        level = LogLevel.INFO if success else LogLevel.WARNING
        
        self._log_with_context(
            level,
            EventType.API_CALL,
            f"API call to {service}/{endpoint}: {'success' if success else 'failed'}",
            **context
        )
    
    # Rate Limit Logging
    
    def log_rate_limit_hit(
        self,
        service: str,
        user_id: Optional[int] = None,
        limit_type: str = "requests",
        cooldown_seconds: Optional[float] = None,
        **context
    ):
        """
        Log rate limit hit.
        
        Args:
            service: Service that hit rate limit
            user_id: User ID if user-specific
            limit_type: Type of limit (requests, withdrawals, etc.)
            cooldown_seconds: Cooldown period in seconds
            **context: Additional context
        """
        limit_context = {
            "service": service,
            "limit_type": limit_type,
        }
        if user_id:
            limit_context["user_id"] = user_id
        if cooldown_seconds is not None:
            limit_context["cooldown_seconds"] = f"{cooldown_seconds:.2f}"
        limit_context.update(context)
        
        self._log_with_context(
            LogLevel.WARNING,
            EventType.RATE_LIMIT,
            f"Rate limit hit: {service} - {limit_type}",
            **limit_context
        )
    
    # Circuit Breaker Logging
    
    def log_circuit_breaker_activation(
        self,
        trigger_reason: str,
        affected_users: Optional[list] = None,
        resume_time: Optional[datetime] = None,
        **context
    ):
        """
        Log circuit breaker activation.
        
        Args:
            trigger_reason: Reason for activation
            affected_users: List of affected user IDs
            resume_time: When trading will resume
            **context: Additional context
        """
        cb_context = {
            "trigger_reason": trigger_reason,
            "status": "activated",
        }
        if affected_users:
            cb_context["affected_users"] = len(affected_users)
            cb_context["user_ids"] = affected_users
        if resume_time:
            cb_context["resume_time"] = resume_time.isoformat()
        cb_context.update(context)
        
        self._log_with_context(
            LogLevel.WARNING,
            EventType.CIRCUIT_BREAKER,
            f"Circuit breaker activated: {trigger_reason}",
            **cb_context
        )
    
    def log_circuit_breaker_deactivation(
        self,
        reason: str,
        affected_users: Optional[list] = None,
        **context
    ):
        """
        Log circuit breaker deactivation.
        
        Args:
            reason: Reason for deactivation
            affected_users: List of affected user IDs
            **context: Additional context
        """
        cb_context = {
            "reason": reason,
            "status": "deactivated",
        }
        if affected_users:
            cb_context["affected_users"] = len(affected_users)
        cb_context.update(context)
        
        self._log_with_context(
            LogLevel.INFO,
            EventType.CIRCUIT_BREAKER,
            f"Circuit breaker deactivated: {reason}",
            **cb_context
        )
    
    # Fee Collection Logging
    
    def log_fee_collection(
        self,
        user_id: int,
        amount: float,
        transaction_hash: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None,
        **context
    ):
        """
        Log fee collection.
        
        Args:
            user_id: User ID
            amount: Fee amount in SOL
            transaction_hash: Transaction hash if successful
            success: Whether collection succeeded
            error: Error message if failed
            **context: Additional context
        """
        fee_context = {
            "user_id": user_id,
            "amount": f"{amount:.4f}",
            "success": success,
        }
        if transaction_hash:
            fee_context["transaction_hash"] = transaction_hash
        if error:
            fee_context["error"] = error
        fee_context.update(context)
        
        level = LogLevel.INFO if success else LogLevel.ERROR
        
        self._log_with_context(
            level,
            EventType.FEE_COLLECTION,
            f"Fee collection {'succeeded' if success else 'failed'}: {amount:.4f} SOL from user {user_id}",
            **fee_context
        )
    
    # User Interaction Logging
    
    def log_user_command(
        self,
        user_id: int,
        command: str,
        parameters: Optional[Dict[str, Any]] = None,
        success: bool = True,
        **context
    ):
        """
        Log user command.
        
        Args:
            user_id: User ID
            command: Command name
            parameters: Command parameters
            success: Whether command succeeded
            **context: Additional context
        """
        cmd_context = {
            "user_id": user_id,
            "command": command,
            "success": success,
        }
        if parameters:
            cmd_context["parameters"] = parameters
        cmd_context.update(context)
        
        self._log_with_context(
            LogLevel.INFO,
            EventType.USER_INTERACTION,
            f"User command: {command} from user {user_id}",
            **cmd_context
        )
    
    # System Metrics Logging
    
    def log_system_metrics(
        self,
        memory_usage_mb: float,
        cpu_usage_percent: float,
        active_users: int,
        **metrics
    ):
        """
        Log system metrics.
        
        Args:
            memory_usage_mb: Memory usage in MB
            cpu_usage_percent: CPU usage percentage
            active_users: Number of active users
            **metrics: Additional metrics
        """
        metrics_context = {
            "memory_usage_mb": f"{memory_usage_mb:.2f}",
            "cpu_usage_percent": f"{cpu_usage_percent:.2f}",
            "active_users": active_users,
        }
        metrics_context.update(metrics)
        
        self._log_with_context(
            LogLevel.INFO,
            EventType.SYSTEM_METRIC,
            f"System metrics: {memory_usage_mb:.2f}MB memory, {cpu_usage_percent:.2f}% CPU, {active_users} users",
            **metrics_context
        )
    
    # Security Logging
    
    def log_security_event(
        self,
        event_type: str,
        user_id: Optional[int] = None,
        severity: str = "warning",
        **context
    ):
        """
        Log security event.
        
        Args:
            event_type: Type of security event
            user_id: User ID if applicable
            severity: Severity level (info, warning, critical)
            **context: Additional context
        """
        sec_context = {
            "event_type": event_type,
            "severity": severity,
        }
        if user_id:
            sec_context["user_id"] = user_id
        sec_context.update(context)
        
        level_map = {
            "info": LogLevel.INFO,
            "warning": LogLevel.WARNING,
            "critical": LogLevel.CRITICAL,
        }
        level = level_map.get(severity.lower(), LogLevel.WARNING)
        
        self._log_with_context(
            level,
            EventType.SECURITY,
            f"Security event: {event_type}",
            **sec_context
        )


# Global logger instances cache
_loggers: Dict[str, ComprehensiveLogger] = {}


def get_comprehensive_logger(component: str) -> ComprehensiveLogger:
    """
    Get or create a comprehensive logger for a component.
    
    Args:
        component: Component name
    
    Returns:
        ComprehensiveLogger instance
    """
    if component not in _loggers:
        _loggers[component] = ComprehensiveLogger(component)
    return _loggers[component]
