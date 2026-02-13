"""
Logging configuration for Harvest agent.

Implements structured logging with:
- Multiple log levels (ERROR, WARNING, INFO, DEBUG)
- Daily log rotation
- 30-day retention
- Compression for files older than 7 days
- Activity logging to persistent storage
- Error logging with context

"""

import sys
import gzip
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from logging.handlers import TimedRotatingFileHandler


class CompressingTimedRotatingFileHandler(TimedRotatingFileHandler):
    """
    Custom handler that compresses rotated log files older than 7 days.
    
    Extends TimedRotatingFileHandler to add automatic compression
    of old log files using gzip.
    """
    
    def __init__(self, *args, compress_after_days: int = 7, **kwargs):
        """
        Initialize handler with compression settings.
        
        Args:
            compress_after_days: Number of days after which to compress logs
            *args, **kwargs: Passed to TimedRotatingFileHandler
        """
        super().__init__(*args, **kwargs)
        self.compress_after_days = compress_after_days
    
    def doRollover(self):
        """
        Override doRollover to add compression of old files.
        
        After rotating the log file, checks for files older than
        compress_after_days and compresses them with gzip.
        """
        # Perform standard rotation
        super().doRollover()
        
        # Compress old log files
        self._compress_old_logs()
    
    def _compress_old_logs(self):
        """
        Compress log files older than compress_after_days.
        
        Finds all uncompressed log files in the log directory that are
        older than the threshold and compresses them with gzip.
        """
        if not self.baseFilename:
            return
        
        log_dir = Path(self.baseFilename).parent
        log_basename = Path(self.baseFilename).name
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=self.compress_after_days)
        
        # Find all log files matching the pattern
        for log_file in log_dir.glob(f"{log_basename}.*"):
            # Skip already compressed files
            if log_file.suffix == '.gz':
                continue
            
            # Check file age
            try:
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                
                if file_mtime < cutoff_date:
                    # Compress the file
                    self._compress_file(log_file)
            except Exception as e:
                # Log error but don't fail
                print(f"Error compressing {log_file}: {e}", file=sys.stderr)
    
    def _compress_file(self, file_path: Path):
        """
        Compress a single file with gzip.
        
        Args:
            file_path: Path to file to compress
        """
        compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
        
        try:
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove original file after successful compression
            file_path.unlink()
            
            print(f"Compressed log file: {file_path} -> {compressed_path}", file=sys.stderr)
        except Exception as e:
            print(f"Failed to compress {file_path}: {e}", file=sys.stderr)
            # Clean up partial compressed file if it exists
            if compressed_path.exists():
                compressed_path.unlink()


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that adds structured context to log messages.
    
    Formats log messages with consistent structure including:
    - Timestamp
    - Log level
    - Component name
    - Message
    - Additional context (if provided)
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with structured context.
        
        Args:
            record: LogRecord to format
        
        Returns:
            Formatted log message string
        """
        # Add component name from logger name
        component = record.name.split('.')[-1] if '.' in record.name else record.name
        record.component = component
        
        # Format exception info if present
        if record.exc_info:
            record.exc_text = self.formatException(record.exc_info)
        
        # Build structured message
        formatted = super().format(record)
        
        # Add extra context if present
        if hasattr(record, 'extra_context'):
            context_str = ' | '.join(f"{k}={v}" for k, v in record.extra_context.items())
            formatted += f" | {context_str}"
        
        return formatted


def setup_logging(
    log_dir: str = "logs",
    log_level: str = "INFO",
    console_level: str = "INFO",
    enable_compression: bool = True,
    compress_after_days: int = 7,
    retention_days: int = 30,
) -> logging.Logger:
    """
    Set up logging configuration for Harvest agent.
    
    Creates a comprehensive logging setup with:
    - Console output for immediate feedback
    - Daily rotating file logs
    - Automatic compression of old logs
    - 30-day retention policy
    - Structured log format
    
    Args:
        log_dir: Directory for log files
        log_level: File logging level (DEBUG, INFO, WARNING, ERROR)
        console_level: Console logging level
        enable_compression: Whether to compress old log files
        compress_after_days: Days after which to compress logs
        retention_days: Days to retain log files
    
    Returns:
        Configured root logger
    
    """
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all levels
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = StructuredFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(component)-15s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, console_level.upper()))
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation and compression
    log_file = log_path / "harvest.log"
    
    if enable_compression:
        file_handler = CompressingTimedRotatingFileHandler(
            filename=str(log_file),
            when='midnight',
            interval=1,
            backupCount=retention_days,
            compress_after_days=compress_after_days,
            encoding='utf-8',
        )
    else:
        file_handler = TimedRotatingFileHandler(
            filename=str(log_file),
            when='midnight',
            interval=1,
            backupCount=retention_days,
            encoding='utf-8',
        )
    
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_handler.setFormatter(detailed_formatter)
    file_handler.suffix = "%Y-%m-%d"  # Date suffix for rotated files
    root_logger.addHandler(file_handler)
    
    # Error log file (ERROR and CRITICAL only)
    error_log_file = log_path / "harvest_errors.log"
    error_handler = TimedRotatingFileHandler(
        filename=str(error_log_file),
        when='midnight',
        interval=1,
        backupCount=retention_days,
        encoding='utf-8',
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    error_handler.suffix = "%Y-%m-%d"
    root_logger.addHandler(error_handler)
    
    # Activity log file (INFO and above)
    activity_log_file = log_path / "harvest_activity.log"
    activity_handler = TimedRotatingFileHandler(
        filename=str(activity_log_file),
        when='midnight',
        interval=1,
        backupCount=retention_days,
        encoding='utf-8',
    )
    activity_handler.setLevel(logging.INFO)
    activity_handler.setFormatter(detailed_formatter)
    activity_handler.suffix = "%Y-%m-%d"
    root_logger.addHandler(activity_handler)
    
    # Log startup message
    root_logger.info("=" * 80)
    root_logger.info("Harvest Agent Logging Initialized")
    root_logger.info(f"Log directory: {log_path.absolute()}")
    root_logger.info(f"Log level: {log_level}")
    root_logger.info(f"Console level: {console_level}")
    root_logger.info(f"Compression: {'enabled' if enable_compression else 'disabled'} (after {compress_after_days} days)")
    root_logger.info(f"Retention: {retention_days} days")
    root_logger.info("=" * 80)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific component.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context
):
    """
    Log a message with additional context.
    
    Args:
        logger: Logger instance
        level: Log level (logging.INFO, logging.ERROR, etc.)
        message: Log message
        **context: Additional context key-value pairs
    """
    extra = {'extra_context': context} if context else {}
    logger.log(level, message, extra=extra)


class ActivityLogger:
    """
    Specialized logger for tracking agent activities.
    
    Logs all agent activities to a persistent storage file
    with structured format for easy parsing and analysis.
    """
    
    def __init__(self, log_dir: str = "logs"):
        """
        Initialize activity logger.
        
        Args:
            log_dir: Directory for activity logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger('harvest.activity')
    
    def log_scan_cycle(self, opportunities_found: int, duration: float):
        """
        Log a scan cycle completion.
        
        Args:
            opportunities_found: Number of opportunities found
            duration: Scan duration in seconds
        """
        log_with_context(
            self.logger,
            logging.INFO,
            f"Scan cycle completed",
            opportunities_found=opportunities_found,
            duration_seconds=f"{duration:.2f}",
        )
    
    def log_opportunity_evaluation(
        self,
        strategy_name: str,
        action: str,
        decision: str,
        confidence: float
    ):
        """
        Log opportunity evaluation.
        
        Args:
            strategy_name: Name of strategy
            action: Action type
            decision: Decision made (execute, notify, skip)
            confidence: Confidence level
        """
        log_with_context(
            self.logger,
            logging.INFO,
            f"Opportunity evaluated: {strategy_name} - {action}",
            strategy=strategy_name,
            action=action,
            decision=decision,
            confidence=f"{confidence:.2f}",
        )
    
    def log_execution(
        self,
        strategy_name: str,
        action: str,
        success: bool,
        transaction_hash: Optional[str] = None,
        profit: Optional[float] = None,
        error: Optional[str] = None
    ):
        """
        Log opportunity execution.
        
        Args:
            strategy_name: Name of strategy
            action: Action type
            success: Whether execution succeeded
            transaction_hash: Transaction hash if successful
            profit: Profit amount if successful
            error: Error message if failed
        """
        context = {
            'strategy': strategy_name,
            'action': action,
            'success': success,
        }
        
        if transaction_hash:
            context['tx_hash'] = transaction_hash
        if profit is not None:
            context['profit'] = f"{profit:.4f}"
        if error:
            context['error'] = error
        
        level = logging.INFO if success else logging.ERROR
        message = f"Execution {'succeeded' if success else 'failed'}: {strategy_name} - {action}"
        
        log_with_context(self.logger, level, message, **context)
    
    def log_user_response(
        self,
        strategy_name: str,
        response: str
    ):
        """
        Log user response to notification.
        
        Args:
            strategy_name: Name of strategy
            response: User response (yes, no, always)
        """
        log_with_context(
            self.logger,
            logging.INFO,
            f"User response: {response}",
            strategy=strategy_name,
            response=response,
        )
    
    def log_risk_rejection(
        self,
        strategy_name: str,
        reason: str
    ):
        """
        Log opportunity rejected by risk manager.
        
        Args:
            strategy_name: Name of strategy
            reason: Rejection reason
        """
        log_with_context(
            self.logger,
            logging.WARNING,
            f"Opportunity rejected by risk manager",
            strategy=strategy_name,
            reason=reason,
        )
    
    def log_stop_loss_exit(
        self,
        position_id: str,
        strategy_name: str,
        loss_amount: float,
        reason: str
    ):
        """
        Log stop-loss position exit.
        
        Args:
            position_id: Position identifier
            strategy_name: Name of strategy
            loss_amount: Loss amount
            reason: Exit reason
        """
        log_with_context(
            self.logger,
            logging.WARNING,
            f"Stop-loss triggered",
            position_id=position_id,
            strategy=strategy_name,
            loss=f"{loss_amount:.4f}",
            reason=reason,
        )
    
    def log_error(
        self,
        component: str,
        error_type: str,
        error_message: str,
        **context
    ):
        """
        Log an error with context.
        
        Args:
            component: Component where error occurred
            error_type: Type of error
            error_message: Error message
            **context: Additional context
        """
        context.update({
            'component': component,
            'error_type': error_type,
        })
        
        log_with_context(
            self.logger,
            logging.ERROR,
            error_message,
            **context
        )


# Global activity logger instance
_activity_logger: Optional[ActivityLogger] = None


def get_activity_logger(log_dir: str = "logs") -> ActivityLogger:
    """
    Get the global activity logger instance.
    
    Args:
        log_dir: Directory for activity logs
    
    Returns:
        ActivityLogger instance
    """
    global _activity_logger
    if _activity_logger is None:
        _activity_logger = ActivityLogger(log_dir)
    return _activity_logger
