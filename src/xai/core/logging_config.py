"""
XAI Blockchain - Structured Logging Configuration

Configures structured JSON logging for production deployment:
- JSON format for easy parsing and aggregation
- Log rotation to prevent disk space issues
- Multiple handlers for different output destinations
- Integration with ELK/Loki/Datadog

Usage:
    from xai.core.logging_config import setup_logging

    logger = setup_logging(
        name="xai.blockchain",
        log_file="/var/log/xai/blockchain.json",
        level="INFO"
    )

    logger.info("Block validated", height=100, transactions=50)
"""

import logging
import logging.handlers
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Enhanced JSON formatter with additional context fields.

    Adds timestamp, environment, and other metadata to all log records.
    """

    def __init__(
        self,
        fmt: str = "%(timestamp)s %(level)s %(name)s %(message)s",
        timestamp: bool = True,
        environment: Optional[str] = None,
        service_name: str = "xai",
    ):
        """
        Initialize custom JSON formatter.

        Args:
            fmt: Log format string
            timestamp: Whether to add timestamps
            environment: Environment name (dev, staging, prod)
            service_name: Service name for context
        """
        super().__init__(fmt=fmt)
        self.timestamp = timestamp
        self.environment = environment or "production"
        self.service_name = service_name

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)

        # Add timestamp if not present
        if self.timestamp and "timestamp" not in log_record:
            log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Add environment context
        log_record["environment"] = self.environment
        log_record["service"] = self.service_name

        # Add log level if not present
        if "level" not in log_record:
            log_record["level"] = record.levelname.lower()

        # Add additional context from record
        if hasattr(record, "extra_fields"):
            log_record.update(record.extra_fields)

        # Add source location
        log_record["source"] = {
            "function": record.funcName,
            "module": record.module,
            "line": record.lineno,
        }


def setup_logging(
    name: str = "xai",
    log_file: Optional[str] = None,
    level: str = "INFO",
    environment: str = "production",
    enable_console: bool = True,
    enable_file: bool = True,
    max_bytes: int = 100 * 1024 * 1024,  # 100MB
    backup_count: int = 10,
) -> logging.Logger:
    """
    Setup structured JSON logging for production.

    Args:
        name: Logger name (typically module name)
        log_file: Path to JSON log file (optional)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        environment: Environment identifier (dev, staging, prod)
        enable_console: Whether to log to console
        enable_file: Whether to log to file
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep

    Returns:
        Configured logger instance

    Example:
        logger = setup_logging(
            name="xai.blockchain",
            log_file="/var/log/xai/blockchain.json",
            level="INFO"
        )
        logger.info("Starting blockchain", network="mainnet")
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers to avoid duplicates
    logger.handlers = []

    # Custom JSON formatter
    formatter = CustomJsonFormatter(
        fmt="%(timestamp)s %(level)s %(name)s %(message)s",
        timestamp=True,
        environment=environment,
        service_name=name.split(".")[0],
    )

    # Console handler (JSON format)
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler with rotation (JSON format)
    if enable_file and log_file:
        try:
            # Create log directory if it doesn't exist
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # Rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                filename=log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
            )
            file_handler.setLevel(getattr(logging, level.upper()))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Could not create file handler for {log_file}: {e}")

    return logger


def get_logger(
    name: str,
    log_file: Optional[str] = None,
    level: str = "INFO",
) -> logging.Logger:
    """
    Get or create a logger with standard configuration.

    Args:
        name: Logger name
        log_file: Optional log file path
        level: Logging level

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        return setup_logging(name=name, log_file=log_file, level=level)

    return logger


# ==================== LOGGING CONFIGURATION PRESETS ====================

def setup_blockchain_logging(environment: str = "production") -> logging.Logger:
    """Setup logging for blockchain operations."""
    return setup_logging(
        name="xai.blockchain",
        log_file=f"/var/log/xai/blockchain-{environment}.json",
        level="INFO",
        environment=environment,
    )


def setup_api_logging(environment: str = "production") -> logging.Logger:
    """Setup logging for API operations."""
    return setup_logging(
        name="xai.api",
        log_file=f"/var/log/xai/api-{environment}.json",
        level="INFO",
        environment=environment,
    )


def setup_network_logging(environment: str = "production") -> logging.Logger:
    """Setup logging for network operations."""
    return setup_logging(
        name="xai.network",
        log_file=f"/var/log/xai/network-{environment}.json",
        level="DEBUG",
        environment=environment,
    )


def setup_mining_logging(environment: str = "production") -> logging.Logger:
    """Setup logging for mining operations."""
    return setup_logging(
        name="xai.mining",
        log_file=f"/var/log/xai/mining-{environment}.json",
        level="INFO",
        environment=environment,
    )


# ==================== LOG AGGREGATION CONFIGURATIONS ====================

class LogAggregationConfig:
    """Configurations for common log aggregation platforms."""

    @staticmethod
    def elk_config() -> Dict[str, Any]:
        """
        Configuration for ELK Stack (Elasticsearch, Logstash, Kibana).

        Returns:
            Configuration dict for Filebeat
        """
        return {
            "filebeat.inputs": [
                {
                    "type": "log",
                    "enabled": True,
                    "paths": ["/var/log/xai/*.json"],
                    "json.message_key": "message",
                    "json.keys_under_root": True,
                    "tags": ["xai"],
                }
            ],
            "output.elasticsearch": {
                "hosts": ["elasticsearch:9200"],
                "index": "xai-%{+yyyy.MM.dd}",
                "pipeline": "xai-ingest",
            },
        }

    @staticmethod
    def loki_config() -> Dict[str, Any]:
        """
        Configuration for Grafana Loki.

        Returns:
            Configuration dict for Promtail
        """
        return {
            "scrape_configs": [
                {
                    "job_name": "xai-logs",
                    "static_configs": [
                        {
                            "targets": ["localhost"],
                            "labels": {
                                "job": "xai",
                                "__path__": "/var/log/xai/*.json",
                            },
                        }
                    ],
                    "pipeline_stages": [
                        {
                            "json": {
                                "expressions": {
                                    "level": "level",
                                    "timestamp": "timestamp",
                                    "service": "service",
                                }
                            }
                        },
                        {
                            "labels": {
                                "level": "",
                                "service": "",
                            }
                        },
                    ],
                }
            ]
        }

    @staticmethod
    def datadog_config() -> Dict[str, Any]:
        """
        Configuration for Datadog logging.

        Returns:
            Configuration dict for agent
        """
        return {
            "logs": {
                "enabled": True,
                "config_provider": {
                    "poll_interval": 10,
                },
            },
            "log_config": [
                {
                    "service": "xai-blockchain",
                    "source": "xai",
                    "path": "/var/log/xai/blockchain.json",
                    "type": "json",
                    "tags": ["env:production", "blockchain:xai"],
                }
            ],
        }


# ==================== USAGE EXAMPLES ====================

if __name__ == "__main__":
    import tempfile
    from pathlib import Path

    # Security fix: Use environment variable or secure default instead of hardcoded /tmp
    log_dir = os.getenv("XAI_LOG_DIR", os.path.join(Path.home(), ".xai", "logs"))
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    # Example 1: Basic setup
    logger = setup_logging(
        name="xai.test",
        log_file=os.path.join(log_dir, "xai-test.json"),
        level="INFO",
    )

    logger.info("Test message", component="blockchain", action="started")
    logger.warning("Test warning", error_code=1001)
    logger.error("Test error", traceback="sample traceback")

    # Example 2: Using preset configuration
    blockchain_logger = setup_blockchain_logging(environment="development")
    blockchain_logger.info("Block mined", height=100, time=2.5)

    # Example 3: Get logger for module
    api_logger = get_logger("xai.api", log_file=os.path.join(log_dir, "api.json"))
    api_logger.info("API request", endpoint="/blocks", method="GET", status=200)

    print(f"\nLogs written to {log_dir}/xai-test.json and {log_dir}/api.json")
    print("\nView logs with:")
    print(f"  cat {log_dir}/xai-test.json | jq .")
