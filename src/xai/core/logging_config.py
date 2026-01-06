"""
XAI Blockchain - Production Logging Configuration
Comprehensive error logging with structured output for monitoring and debugging.
"""

import logging
import logging.handlers
import os
import sys
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Log directory - uses XAI_LOG_DIR env var, falls back to data dir relative path
LOG_DIR = Path(os.getenv("XAI_LOG_DIR", os.path.join(os.getenv("XAI_DATA_DIR", "/home/ubuntu/xai"), "logs")))
LOG_DIR.mkdir(parents=True, exist_ok=True)

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging compatible with log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info) if record.exc_info[0] else None,
            }

        # Add extra fields
        if hasattr(record, "event"):
            log_data["event"] = record.event
        if hasattr(record, "extra_data"):
            log_data["data"] = record.extra_data

        # Add any other extra attributes
        standard_attrs = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName', 'levelname',
            'levelno', 'lineno', 'module', 'msecs', 'pathname', 'process',
            'processName', 'relativeCreated', 'stack_info', 'exc_info', 'exc_text',
            'thread', 'threadName', 'message', 'event', 'extra_data', 'taskName'
        }
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith('_'):
                try:
                    json.dumps(value)  # Check if serializable
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)

        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """Colored console formatter for development/debugging."""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

        # Base message
        msg = f"{color}{timestamp} [{record.levelname:8}] {record.name}: {record.getMessage()}{self.RESET}"

        # Add event tag if present
        if hasattr(record, 'event'):
            msg = f"{color}{timestamp} [{record.levelname:8}] [{record.event}] {record.name}: {record.getMessage()}{self.RESET}"

        # Add exception traceback
        if record.exc_info:
            msg += f"\n{self.RESET}{self.formatException(record.exc_info)}"

        return msg


def setup_logging(
    level: str = "INFO",
    json_logs: bool = True,
    console_logs: bool = True,
    log_file: str = "xai-node.log",
    error_file: str = "xai-errors.log",
    max_bytes: int = 50 * 1024 * 1024,  # 50MB
    backup_count: int = 10,
) -> logging.Logger:
    """
    Configure comprehensive logging for XAI node.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Enable JSON structured logs to file
        console_logs: Enable colored console output
        log_file: Main log file name
        error_file: Error-only log file name
        max_bytes: Max size per log file before rotation
        backup_count: Number of backup files to keep

    Returns:
        Root logger configured for XAI
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler with colors
    if console_logs:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(ConsoleFormatter())
        root_logger.addHandler(console_handler)

    # Main log file (JSON format, rotating)
    if json_logs:
        main_log_path = LOG_DIR / log_file
        main_handler = logging.handlers.RotatingFileHandler(
            main_log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8',
        )
        main_handler.setLevel(logging.DEBUG)
        main_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(main_handler)

    # Error-only log file (for quick error scanning)
    error_log_path = LOG_DIR / error_file
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8',
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(error_handler)

    # Create specialized loggers
    loggers_config = {
        "xai.core": logging.DEBUG,
        "xai.core.node": logging.DEBUG,
        "xai.core.blockchain": logging.DEBUG,
        "xai.core.p2p": logging.DEBUG,
        "xai.core.consensus": logging.DEBUG,
        "xai.core.mining": logging.DEBUG,
        "xai.core.security": logging.INFO,
        "xai.network": logging.DEBUG,
        "xai.api": logging.INFO,
        "werkzeug": logging.WARNING,
        "urllib3": logging.WARNING,
        "asyncio": logging.WARNING,
    }

    for logger_name, logger_level in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(logger_level)

    root_logger.info(
        "XAI logging initialized",
        extra={
            "event": "logging.init",
            "log_dir": str(LOG_DIR),
            "level": level,
            "json_logs": json_logs,
            "console_logs": console_logs,
        }
    )

    return root_logger


def log_exception(logger: logging.Logger, message: str, exc: Exception, **extra) -> None:
    """
    Log an exception with full context.

    Args:
        logger: Logger instance
        message: Description of what was happening when error occurred
        exc: The exception that was raised
        **extra: Additional context to include in log
    """
    logger.error(
        f"{message}: {type(exc).__name__}: {exc}",
        exc_info=True,
        extra={
            "event": "error.exception",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            **extra,
        }
    )


def log_p2p_event(logger: logging.Logger, event: str, peer: str = None, **data) -> None:
    """Log P2P network events with consistent structure."""
    logger.info(
        f"P2P: {event}" + (f" peer={peer}" if peer else ""),
        extra={"event": f"p2p.{event}", "peer": peer, **data}
    )


def log_mining_event(logger: logging.Logger, event: str, block_height: int = None, **data) -> None:
    """Log mining events with consistent structure."""
    logger.info(
        f"Mining: {event}" + (f" height={block_height}" if block_height else ""),
        extra={"event": f"mining.{event}", "block_height": block_height, **data}
    )


def log_consensus_event(logger: logging.Logger, event: str, **data) -> None:
    """Log consensus events with consistent structure."""
    logger.info(
        f"Consensus: {event}",
        extra={"event": f"consensus.{event}", **data}
    )


def log_api_request(logger: logging.Logger, method: str, path: str, status: int, duration_ms: float, **data) -> None:
    """Log API requests with timing."""
    level = logging.WARNING if status >= 400 else logging.DEBUG
    logger.log(
        level,
        f"API {method} {path} -> {status} ({duration_ms:.1f}ms)",
        extra={
            "event": "api.request",
            "method": method,
            "path": path,
            "status": status,
            "duration_ms": duration_ms,
            **data,
        }
    )
