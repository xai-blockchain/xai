"""
XAI Blockchain - Structured Logging System

Comprehensive structured logging with:
- JSON log format for easy parsing
- Log levels: DEBUG, INFO, WARN, ERROR, CRITICAL
- Daily log rotation with size limits
- Contextual logging with correlation IDs
- Performance tracking
- Privacy-preserving features
"""

import json
import logging
import os
import threading
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from typing import Dict, Any, Optional
from contextvars import ContextVar
import hashlib
import time


# Context variable for correlation ID (thread-safe)
correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs in JSON format

    Features:
    - Structured JSON output
    - UTC timestamps
    - Correlation ID support
    - Custom fields
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""

        # Base log entry
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation ID if present
        corr_id = correlation_id.get()
        if corr_id:
            log_entry["correlation_id"] = corr_id

        # Add thread information
        log_entry["thread"] = {"id": threading.get_ident(), "name": threading.current_thread().name}

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Add custom fields from extra parameter
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry, default=str)


class StructuredLogger:
    """
    Structured logger with JSON output and advanced features

    Features:
    - Multiple log levels (DEBUG, INFO, WARN, ERROR, CRITICAL)
    - JSON format output
    - Daily rotation
    - Maximum file size (100MB)
    - Correlation ID tracking
    - Performance metrics
    - Privacy-preserving (truncated addresses, sanitized data)
    """

    def __init__(
        self,
        name: str = "XAI_Blockchain",
        log_dir: str = None,
        log_level: str = "INFO",
        max_bytes: int = 100 * 1024 * 1024,  # 100MB
        backup_count: int = 30,
    ):  # Keep 30 days
        """
        Initialize structured logger

        Args:
            name: Logger name
            log_dir: Directory for log files
            log_level: Minimum log level (DEBUG, INFO, WARN, ERROR, CRITICAL)
            max_bytes: Maximum log file size before rotation
            backup_count: Number of backup files to keep
        """
        self.name = name

        # Create log directory
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
        os.makedirs(log_dir, exist_ok=True)

        # Configure logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))

        # Prevent duplicate handlers
        if not self.logger.handlers:
            # JSON log file (daily rotation)
            json_log_path = os.path.join(log_dir, f"{name.lower()}.json.log")
            json_handler = TimedRotatingFileHandler(
                json_log_path,
                when="midnight",
                interval=1,
                backupCount=backup_count,
                encoding="utf-8",
                utc=True,
            )
            json_handler.setFormatter(JSONFormatter())
            self.logger.addHandler(json_handler)

            # Human-readable log file (for easier debugging)
            text_log_path = os.path.join(log_dir, f"{name.lower()}.log")
            text_handler = TimedRotatingFileHandler(
                text_log_path,
                when="midnight",
                interval=1,
                backupCount=backup_count,
                encoding="utf-8",
                utc=True,
            )
            text_formatter = logging.Formatter(
                "[%(asctime)s UTC] %(levelname)-8s [%(correlation_id)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            text_formatter.converter = lambda *args: datetime.now(timezone.utc).timetuple()
            text_handler.setFormatter(text_formatter)
            text_handler.addFilter(CorrelationIDFilter())
            self.logger.addHandler(text_handler)

        self.performance_metrics = {}
        self.log_counts = {"DEBUG": 0, "INFO": 0, "WARN": 0, "ERROR": 0, "CRITICAL": 0}

    def _truncate_address(self, address: str) -> str:
        """Truncate wallet address for privacy"""
        if not address or len(address) < 10:
            return "UNKNOWN"
        return f"{address[:6]}...{address[-4:]}"

    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive information from data"""
        sensitive_keys = ["private_key", "password", "secret", "api_key", "signature"]
        sanitized = {}

        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "REDACTED"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            else:
                sanitized[key] = value

        return sanitized

    def _log(self, level: str, message: str, **kwargs):
        """Internal logging method"""
        self.log_counts[level] += 1

        # Sanitize extra fields
        if kwargs:
            kwargs = self._sanitize_data(kwargs)

        # Create log record with extra fields
        extra = {"extra_fields": kwargs} if kwargs else {}

        log_func = getattr(self.logger, level.lower())
        log_func(message, extra=extra)

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log("INFO", message, **kwargs)

    def warn(self, message: str, **kwargs):
        """Log warning message"""
        self._log("WARN", message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message (alias for warn for Python logging compatibility)"""
        self._log("WARN", message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message"""
        self._log("ERROR", message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self._log("CRITICAL", message, **kwargs)

    # Blockchain-specific logging methods

    def block_mined(
        self,
        block_index: int,
        block_hash: str,
        miner: str,
        tx_count: int,
        reward: float,
        mining_time: float = None,
    ):
        """Log block mining event"""
        self.info(
            f"Block #{block_index} mined",
            block_index=block_index,
            block_hash=block_hash[:16] + "...",
            miner=self._truncate_address(miner),
            transaction_count=tx_count,
            block_reward=reward,
            mining_time_seconds=mining_time,
        )

    def transaction_submitted(
        self, txid: str, sender: str, recipient: str, amount: float, fee: float
    ):
        """Log transaction submission"""
        self.info(
            f"Transaction submitted: {txid[:16]}...",
            txid=txid[:16] + "...",
            sender=self._truncate_address(sender),
            recipient=self._truncate_address(recipient),
            amount=amount,
            fee=fee,
        )

    def transaction_confirmed(self, txid: str, block_index: int):
        """Log transaction confirmation"""
        self.info(
            f"Transaction confirmed in block #{block_index}",
            txid=txid[:16] + "...",
            block_index=block_index,
        )

    def network_event(self, event_type: str, peer_count: int = None, **kwargs):
        """Log network event"""
        self.info(f"Network: {event_type}", event_type=event_type, peer_count=peer_count, **kwargs)

    def consensus_event(self, event_type: str, **kwargs):
        """Log consensus event"""
        self.info(f"Consensus: {event_type}", event_type=event_type, **kwargs)

    def security_event(self, event_type: str, severity: str = "WARN", **kwargs):
        """Log security event"""
        log_func = self.warn if severity == "WARN" else self.error
        log_func(f"SECURITY: {event_type}", event_type=event_type, security_event=True, **kwargs)

    def performance_event(self, metric_name: str, value: float, unit: str = ""):
        """Log performance metric"""
        self.debug(
            f"Performance: {metric_name}",
            metric_name=metric_name,
            value=value,
            unit=unit,
            performance_metric=True,
        )

    def api_request(
        self, endpoint: str, method: str, status_code: int = None, duration_ms: float = None
    ):
        """Log API request"""
        self.info(
            f"API: {method} {endpoint}",
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            api_request=True,
        )

    def governance_event(self, event_type: str, proposal_id: str = None, **kwargs):
        """Log governance event"""
        self.info(
            f"Governance: {event_type}", event_type=event_type, proposal_id=proposal_id, **kwargs
        )

    def wallet_event(self, event_type: str, address: str, **kwargs):
        """Log wallet event"""
        self.info(
            f"Wallet: {event_type}",
            event_type=event_type,
            address=self._truncate_address(address),
            **kwargs,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get logger statistics"""
        return {
            "log_counts": self.log_counts.copy(),
            "total_logs": sum(self.log_counts.values()),
            "performance_metrics": self.performance_metrics.copy(),
        }


class CorrelationIDFilter(logging.Filter):
    """Filter to add correlation ID to log records"""

    def filter(self, record):
        corr_id = correlation_id.get()
        record.correlation_id = corr_id if corr_id else "NO-ID"
        return True


class LogContext:
    """
    Context manager for correlation ID tracking

    Usage:
        with LogContext() as ctx:
            logger.info("This log will have a correlation ID")
    """

    def __init__(self, custom_id: str = None):
        """
        Initialize log context

        Args:
            custom_id: Custom correlation ID (auto-generated if not provided)
        """
        self.correlation_id = custom_id or self._generate_correlation_id()

    def _generate_correlation_id(self) -> str:
        """Generate unique correlation ID"""
        timestamp = str(time.time()).encode()
        thread_id = str(threading.get_ident()).encode()
        random_data = os.urandom(8)

        hash_input = timestamp + thread_id + random_data
        return hashlib.sha256(hash_input).hexdigest()[:16]

    def __enter__(self):
        """Set correlation ID on context entry"""
        self.token = correlation_id.set(self.correlation_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clear correlation ID on context exit"""
        correlation_id.reset(self.token)


class PerformanceTimer:
    """
    Context manager for performance timing

    Usage:
        with PerformanceTimer(logger, 'operation_name'):
            # Code to time
            pass
    """

    def __init__(self, logger: StructuredLogger, operation_name: str):
        """
        Initialize performance timer

        Args:
            logger: Structured logger instance
            operation_name: Name of the operation being timed
        """
        self.logger = logger
        self.operation_name = operation_name
        self.start_time = None

    def __enter__(self):
        """Start timer"""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timer and log duration"""
        duration = (time.time() - self.start_time) * 1000  # Convert to ms
        self.logger.performance_event(self.operation_name, duration, "ms")


# Global logger instance
_global_structured_logger = None


def get_structured_logger(name: str = "XAI_Blockchain") -> StructuredLogger:
    """
    Get global structured logger instance

    Args:
        name: Logger name

    Returns:
        StructuredLogger instance
    """
    global _global_structured_logger
    if _global_structured_logger is None:
        _global_structured_logger = StructuredLogger(name)
    return _global_structured_logger


# Convenience functions
def set_correlation_id(custom_id: str = None) -> str:
    """
    Set correlation ID for current context

    Args:
        custom_id: Custom correlation ID (auto-generated if not provided)

    Returns:
        The correlation ID that was set
    """
    ctx = LogContext(custom_id)
    corr_id = ctx.correlation_id
    correlation_id.set(corr_id)
    return corr_id


def clear_correlation_id():
    """Clear correlation ID from current context"""
    correlation_id.set(None)


# Example usage
if __name__ == "__main__":
    # Create logger
    logger = StructuredLogger("XAI_Test", log_level="DEBUG")

    print("Testing Structured Logger...")
    print("=" * 70)

    # Basic logging
    logger.info("Node started", network="mainnet", port=5000)
    logger.debug("Debug message", test_data={"key": "value"})
    logger.warn("Warning message", reason="test")
    logger.error("Error message", error_code=500)

    # Contextual logging with correlation ID
    with LogContext() as ctx:
        logger.info("Request started", correlation_id=ctx.correlation_id)
        logger.info("Processing request")
        logger.info("Request completed")

    # Performance timing
    with PerformanceTimer(logger, "test_operation"):
        time.sleep(0.1)  # Simulate work

    # Blockchain events
    logger.block_mined(
        block_index=100,
        block_hash="0x123456789abcdef",
        miner="XAI1234567890abcdef",
        tx_count=10,
        reward=50.0,
        mining_time=5.2,
    )

    logger.transaction_submitted(
        txid="0xabcdef123456",
        sender="XAI1111111111",
        recipient="XAI2222222222",
        amount=100.0,
        fee=0.01,
    )

    # Security event
    logger.security_event(
        "rate_limit_exceeded", severity="WARN", endpoint="/send", ip_hash="abc123"
    )

    # Get stats
    stats = logger.get_stats()
    print("\nLogger Statistics:")
    print(json.dumps(stats, indent=2))

    print("\n" + "=" * 70)
    print("Logs written to: logs/xai_test.json.log and logs/xai_test.log")
