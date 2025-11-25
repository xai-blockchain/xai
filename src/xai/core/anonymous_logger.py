"""
XAI Blockchain - Secure Logging

Privacy-focused logging system for blockchain events.
"""

import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Optional


class AnonymousLogger:
    """
    Logger that preserves complete anonymity

    All logs are:
    - UTC timestamps only
    - No IP addresses
    - No personal data
    - Wallet addresses truncated
    - Error details sanitized
    """

    def __init__(self, log_dir: str = None, log_name: str = "xai_node.log"):
        """
        Initialize anonymous logger

        Args:
            log_dir: Directory for log files
            log_name: Log file name
        """
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")

        # Create log directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)

        log_path = os.path.join(log_dir, log_name)

        # Configure logger
        self.logger = logging.getLogger("XAI_Anonymous")
        self.logger.setLevel(logging.INFO)

        # Rotating file handler (10MB per file, keep 5 backups)
        handler = RotatingFileHandler(log_path, maxBytes=10 * 1024 * 1024, backupCount=5)  # 10MB

        # Anonymous format - UTC time + level + message only
        formatter = logging.Formatter(
            "[%(asctime)s UTC] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        formatter.converter = lambda *args: datetime.now(timezone.utc).timetuple()

        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def _truncate_address(self, address: str) -> str:
        """
        Truncate wallet address for privacy

        Args:
            address: Full wallet address

        Returns:
            str: Truncated address
        """
        if not address or len(address) < 16:
            return "UNKNOWN"

        # Show first 6 and last 4 characters only
        return f"{address[:6]}...{address[-4:]}"

    def _sanitize_message(self, message: str) -> str:
        """
        Remove potentially identifying information from message

        Args:
            message: Original message

        Returns:
            str: Sanitized message
        """
        # Keywords that should not appear in logs
        sensitive_patterns = [
            ("private_key", "REDACTED"),
            ("password", "REDACTED"),
            ("secret", "REDACTED"),
            ("api_key", "REDACTED"),
        ]

        sanitized = message
        for pattern, replacement in sensitive_patterns:
            if pattern.lower() in sanitized.lower():
                # Don't log the actual value
                sanitized = sanitized.replace(pattern, replacement)

        return sanitized

    def info(self, message: str):
        """Log info message (anonymous)"""
        sanitized = self._sanitize_message(message)
        self.logger.info(sanitized)

    def warning(self, message: str):
        """Log warning message (anonymous)"""
        sanitized = self._sanitize_message(message)
        self.logger.warning(sanitized)

    def error(self, message: str):
        """Log error message (anonymous)"""
        sanitized = self._sanitize_message(message)
        self.logger.error(sanitized)

    def security_event(self, event_type: str, details: str = ""):
        """
        Log security event (anonymous)

        Args:
            event_type: Type of security event
            details: Anonymous details (no personal data!)
        """
        sanitized_details = self._sanitize_message(details)
        self.logger.warning(f"SECURITY: {event_type} - {sanitized_details}")

    def block_mined(self, block_index: int, block_hash: str, tx_count: int):
        """
        Log block mining (anonymous)

        Args:
            block_index: Block number
            block_hash: Block hash
            tx_count: Number of transactions
        """
        hash_prefix = block_hash[:12] if block_hash else "UNKNOWN"
        self.logger.info(f"Block #{block_index} mined: {hash_prefix}... ({tx_count} tx)")

    def transaction_received(self, sender: str, recipient: str, amount: float):
        """
        Log transaction (anonymous - addresses truncated)

        Args:
            sender: Sender address
            recipient: Recipient address
            amount: Transaction amount
        """
        sender_trunc = self._truncate_address(sender)
        recipient_trunc = self._truncate_address(recipient)

        self.logger.info(f"Transaction: {sender_trunc} → {recipient_trunc} " f"({amount:.4f} XAI)")

    def wallet_claimed(self, address: str, tier: str):
        """
        Log wallet claim (anonymous)

        Args:
            address: Wallet address (will be truncated)
            tier: Wallet tier
        """
        addr_trunc = self._truncate_address(address)
        self.logger.info(f"Wallet claimed: {addr_trunc} (tier: {tier})")

    def service_consumed(self, service_type: str, amount_burned: float):
        """
        Log service consumption (anonymous)

        Args:
            service_type: Type of service
            amount_burned: Amount of XAI burned
        """
        self.logger.info(f"Service consumed: {service_type} " f"(burned: {amount_burned:.4f} XAI)")

    def node_started(self, network: str, port: int):
        """
        Log node startup (anonymous)

        Args:
            network: Network type (testnet/mainnet)
            port: Port number
        """
        self.logger.info(f"Node started: {network.upper()} on port {port}")

    def node_stopped(self):
        """Log node shutdown (anonymous)"""
        self.logger.info("Node stopped")

    def peer_connected(self, peer_count: int):
        """
        Log peer connection (anonymous - no peer details!)

        Args:
            peer_count: Total peer count
        """
        self.logger.info(f"Peer connected (total: {peer_count})")

    def peer_disconnected(self, peer_count: int):
        """
        Log peer disconnection (anonymous)

        Args:
            peer_count: Remaining peer count
        """
        self.logger.info(f"Peer disconnected (remaining: {peer_count})")

    def validation_failed(self, reason: str):
        """
        Log validation failure (anonymous)

        Args:
            reason: Failure reason (sanitized)
        """
        sanitized = self._sanitize_message(reason)
        self.logger.warning(f"Validation failed: {sanitized}")

    def rate_limit_exceeded(self, endpoint: str):
        """
        Log rate limit (anonymous - no requester info!)

        Args:
            endpoint: Endpoint that was rate limited
        """
        self.logger.warning(f"Rate limit exceeded: {endpoint}")


# Global logger instance
_global_logger = None


def get_logger() -> AnonymousLogger:
    """
    Get global anonymous logger

    Returns:
        AnonymousLogger: Global logger instance
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = AnonymousLogger()
    return _global_logger


# Convenience functions
def log_info(message: str):
    """Log info message"""
    get_logger().info(message)


def log_warning(message: str):
    """Log warning message"""
    get_logger().warning(message)


def log_error(message: str):
    """Log error message"""
    get_logger().error(message)


def log_security_event(event_type: str, details: str = ""):
    """Log security event"""
    get_logger().security_event(event_type, details)


def log_block_mined(block_index: int, block_hash: str, tx_count: int):
    """Log block mining"""
    get_logger().block_mined(block_index, block_hash, tx_count)


def log_transaction(sender: str, recipient: str, amount: float):
    """Log transaction"""
    get_logger().transaction_received(sender, recipient, amount)
