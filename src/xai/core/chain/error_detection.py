from __future__ import annotations

"""
XAI Blockchain - Error Detection and Classification System

Comprehensive error detection and classification:
- Error severity classification
- Corruption detection
- Health monitoring
- Error pattern analysis
"""

import hashlib
import logging
import time
from collections import deque
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from xai.core.constants import MINIMUM_TRANSACTION_AMOUNT

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels for classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RecoveryState(Enum):
    """System recovery states."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    RECOVERING = "recovering"
    CRITICAL = "critical"
    SHUTDOWN = "shutdown"

class ErrorDetector:
    """
    Detects and classifies system errors.

    Provides comprehensive error detection including:
    - Exception classification
    - Error severity assessment
    - Error pattern tracking
    - Historical error analysis
    """

    def __init__(self, blockchain: Any) -> None:
        """
        Initialize error detector.

        Args:
            blockchain: Blockchain instance to monitor
        """
        self.blockchain = blockchain
        self.error_history: deque = deque(maxlen=1000)
        self.error_patterns: dict[str, int] = {}
        self.logger: logging.Logger = logging.getLogger("error_detector")
        self.logger.setLevel(logging.INFO)

    def detect_error(self, exception: Exception, context: str = "") -> ErrorSeverity:
        """
        Classify error severity based on exception type and context.

        Args:
            exception: The exception that occurred
            context: Additional context about where/why the error occurred

        Returns:
            ErrorSeverity level
        """
        error_type = type(exception).__name__
        error_msg = str(exception)

        # Track error occurrence
        self._log_error(error_type, error_msg, context)

        # Classify by exception type
        if error_type in ["KeyboardInterrupt", "SystemExit"]:
            return ErrorSeverity.CRITICAL

        if error_type in ["MemoryError", "OSError", "IOError"]:
            return ErrorSeverity.CRITICAL

        if error_type in ["ValueError", "TypeError", "AttributeError"]:
            # Check if it's affecting core blockchain operations
            if "blockchain" in error_msg.lower() or "transaction" in error_msg.lower():
                return ErrorSeverity.HIGH
            return ErrorSeverity.MEDIUM

        if error_type in ["ConnectionError", "TimeoutError", "NetworkError"]:
            return ErrorSeverity.MEDIUM

        # Default to medium severity
        return ErrorSeverity.MEDIUM

    def detect_error_patterns(self) -> list[dict[str, Any]]:
        """
        Detect recurring error patterns in recent history.

        Returns:
            List of detected patterns with details
        """
        patterns: list[dict[str, Any]] = []

        # Count errors in last 100 entries
        recent_errors: dict[str, int] = {}
        for error in list(self.error_history)[-100:]:
            error_type = error.get("type", "unknown")
            recent_errors[error_type] = recent_errors.get(error_type, 0) + 1

        # Identify patterns (threshold: 5 occurrences)
        for error_type, count in recent_errors.items():
            if count >= 5:
                patterns.append(
                    {
                        "error_type": error_type,
                        "count": count,
                        "severity": "high" if count >= 10 else "medium",
                        "suggestion": self._get_pattern_suggestion(error_type),
                    }
                )

        return patterns

    def get_error_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive error statistics.

        Returns:
            Dictionary with error statistics
        """
        total_errors = len(self.error_history)

        if total_errors == 0:
            return {
                "total_errors": 0,
                "error_rate": 0.0,
                "common_errors": [],
                "severity_distribution": {},
            }

        # Calculate error rate (errors per hour)
        if total_errors > 1:
            time_span = self.error_history[-1]["timestamp"] - self.error_history[0]["timestamp"]
            error_rate = (total_errors / max(time_span, 1)) * 3600
        else:
            error_rate = 0.0

        # Count error types
        error_counts: dict[str, int] = {}
        for error in self.error_history:
            error_type = error.get("type", "unknown")
            error_counts[error_type] = error_counts.get(error_type, 0) + 1

        # Get top 5 common errors
        common_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_errors": total_errors,
            "error_rate": error_rate,
            "common_errors": [{"type": t, "count": c} for t, c in common_errors],
            "recent_patterns": self.detect_error_patterns(),
        }

    def _log_error(self, error_type: str, error_msg: str, context: str) -> None:
        """
        Log error to history.

        Args:
            error_type: Type of error
            error_msg: Error message
            context: Error context
        """
        error_entry = {
            "timestamp": time.time(),
            "type": error_type,
            "message": error_msg,
            "context": context,
        }

        if len(self.error_history) == self.error_history.maxlen:
            removed = self.error_history.popleft()
            if removed["type"] in self.error_patterns:
                self.error_patterns[removed["type"]] -= 1
                if self.error_patterns[removed["type"]] <= 0:
                    del self.error_patterns[removed["type"]]

        self.error_history.append(error_entry)
        self.error_patterns[error_type] = self.error_patterns.get(error_type, 0) + 1

    def _get_pattern_suggestion(self, error_type: str) -> str:
        """
        Get suggestion for recurring error pattern.

        Args:
            error_type: Type of error occurring repeatedly

        Returns:
            Suggestion for resolving the pattern
        """
        suggestions = {
            "ConnectionError": "Check network connectivity and peer availability",
            "TimeoutError": "Increase timeout values or check network latency",
            "ValueError": "Validate input data before processing",
            "TypeError": "Review data type handling and conversions",
            "MemoryError": "Reduce memory usage or increase available memory",
            "IOError": "Check file permissions and disk space",
        }

        return suggestions.get(error_type, "Review error logs and investigate root cause")

class CorruptionDetector:
    """
    Detect and analyze blockchain data corruption.

    Performs comprehensive integrity checks on:
    - Block hash integrity
    - Chain continuity
    - UTXO consistency
    - Supply validation
    - Transaction validity
    """

    def __init__(self) -> None:
        """Initialize corruption detector with check registry."""
        self.corruption_checks: dict[str, Any] = {
            "hash_integrity": self._check_hash_integrity,
            "chain_continuity": self._check_chain_continuity,
            "utxo_consistency": self._check_utxo_consistency,
            "supply_validation": self._check_supply_validation,
            "transaction_validity": self._check_transaction_validity,
        }
        self.logger: logging.Logger = logging.getLogger("corruption_detector")
        self.logger.setLevel(logging.INFO)

    def detect_corruption(self, blockchain: Any) -> tuple[bool, list[str]]:
        """
        Run all corruption checks on blockchain.

        Args:
            blockchain: Blockchain instance to check

        Returns:
            Tuple of (is_corrupted, list of issues found)
        """
        issues: list[str] = []

        for check_name, check_func in self.corruption_checks.items():
            try:
                is_valid, errors = check_func(blockchain)
                if not is_valid:
                    issues.extend([f"[{check_name}] {err}" for err in errors])
            except (ValueError, TypeError, RuntimeError) as e:
                issues.append(f"[{check_name}] Check failed: {str(e)}")
                self.logger.error(
                    "Corruption check %s failed: %s",
                    check_name,
                    e,
                    extra={"event": "corruption_check_failed", "check": check_name},
                )

        return len(issues) > 0, issues

    def _check_hash_integrity(self, blockchain: Any) -> tuple[bool, list[str]]:
        """
        Check block hash integrity.

        Args:
            blockchain: Blockchain instance

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors: list[str] = []

        for i, block in enumerate(blockchain.chain):
            # Verify hash matches content
            calculated_hash = block.calculate_hash()
            if block.hash != calculated_hash:
                errors.append(
                    f"Block {i} hash mismatch: {block.hash[:16]}... != {calculated_hash[:16]}..."
                )

        return len(errors) == 0, errors

    def _check_chain_continuity(self, blockchain: Any) -> tuple[bool, list[str]]:
        """
        Check blockchain continuity.

        Args:
            blockchain: Blockchain instance

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors: list[str] = []

        for i in range(1, len(blockchain.chain)):
            current = blockchain.chain[i]
            previous = blockchain.chain[i - 1]

            if current.previous_hash != previous.hash:
                errors.append(f"Block {i} broken chain: previous_hash mismatch")

            if current.index != previous.index + 1:
                errors.append(f"Block {i} index discontinuity")

        return len(errors) == 0, errors

    def _check_utxo_consistency(self, blockchain: Any) -> tuple[bool, list[str]]:
        """
        Check UTXO set consistency by rebuilding and comparing.

        Args:
            blockchain: Blockchain instance

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors: list[str] = []

        try:
            rebuilt_utxo: dict[str, list[dict[str, Any]]] = {}

            for block in blockchain.chain:
                for tx in block.transactions:
                    # Add outputs
                    if tx.recipient not in rebuilt_utxo:
                        rebuilt_utxo[tx.recipient] = []

                    rebuilt_utxo[tx.recipient].append(
                        {"txid": tx.txid, "amount": tx.amount, "spent": False}
                    )

                    # Mark inputs as spent (simplified)
                    if tx.sender != "COINBASE" and tx.sender in rebuilt_utxo:
                        spent_amount = tx.amount + tx.fee
                        remaining = spent_amount

                        for utxo in rebuilt_utxo[tx.sender]:
                            if not utxo["spent"] and remaining > 0:
                                if utxo["amount"] <= remaining:
                                    utxo["spent"] = True
                                    remaining -= utxo["amount"]
                                else:
                                    utxo["amount"] -= remaining
                                    remaining = 0

            # Compare balances
            for address in rebuilt_utxo:
                rebuilt_balance = sum(u["amount"] for u in rebuilt_utxo[address] if not u["spent"])
                current_balance = blockchain.get_balance(address)

                if abs(rebuilt_balance - current_balance) > MINIMUM_TRANSACTION_AMOUNT:
                    errors.append(
                        f"UTXO mismatch for {address[:10]}...: "
                        f"rebuilt={rebuilt_balance}, current={current_balance}"
                    )

        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            logger.error(
                "Exception in _check_utxo_consistency",
                extra={
                    "error_type": "Exception",
                    "error": str(e),
                    "function": "_check_utxo_consistency"
                }
            )
            errors.append(f"UTXO check failed: {str(e)}")

        return len(errors) == 0, errors

    def _check_supply_validation(self, blockchain: Any) -> tuple[bool, list[str]]:
        """
        Check total supply doesn't exceed maximum cap.

        Args:
            blockchain: Blockchain instance

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors: list[str] = []

        try:
            total_supply = Decimal(0)
            for address, utxos in blockchain.utxo_set.items():
                for utxo in utxos:
                    if not utxo["spent"]:
                        total_supply += Decimal(str(utxo["amount"]))

            max_supply = getattr(blockchain, "max_supply", 121000000)

            if float(total_supply) > max_supply:
                errors.append(f"Supply cap exceeded: {float(total_supply)} > {max_supply}")

        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            logger.error(
                "Exception in _check_supply_validation",
                extra={
                    "error_type": "Exception",
                    "error": str(e),
                    "function": "_check_supply_validation"
                }
            )
            errors.append(f"Supply validation failed: {str(e)}")

        return len(errors) == 0, errors

    def _check_transaction_validity(self, blockchain: Any) -> tuple[bool, list[str]]:
        """
        Check transaction validity across all blocks.

        Args:
            blockchain: Blockchain instance

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors: list[str] = []

        for i, block in enumerate(blockchain.chain):
            for j, tx in enumerate(block.transactions):
                # Check basic transaction properties
                if tx.amount < 0:
                    errors.append(f"Block {i}, tx {j}: Negative amount")

                if tx.fee < 0:
                    errors.append(f"Block {i}, tx {j}: Negative fee")

                # Verify signature (skip coinbase)
                if tx.sender != "COINBASE":
                    try:
                        if not tx.verify_signature():
                            errors.append(f"Block {i}, tx {j}: Invalid signature")
                    except Exception as e:
                        # Catch signature verification errors
                        from xai.core.transaction import (
                            InvalidSignatureError,
                            MissingSignatureError,
                            SignatureCryptoError,
                            SignatureVerificationError,
                        )
                        if isinstance(e, (SignatureVerificationError, MissingSignatureError, InvalidSignatureError, SignatureCryptoError)):
                            errors.append(f"Block {i}, tx {j}: Signature verification failed: {e}")
                        else:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(
                                "Unexpected signature verification error in error detection",
                                extra={
                                    "error_type": type(e).__name__,
                                    "error": str(e),
                                    "block": i,
                                    "tx": j
                                },
                                exc_info=True
                            )
                            errors.append(f"Block {i}, tx {j}: Unexpected signature verification error: {type(e).__name__}: {e}")

        return len(errors) == 0, errors

class HealthMonitor:
    """
    Monitor blockchain health and performance metrics.

    Tracks:
    - Block production rate
    - Transaction processing
    - Network connectivity
    - Error rates
    - Overall system health score
    """

    def __init__(self) -> None:
        """Initialize health monitor with default metrics."""
        self.metrics: dict[str, Any] = {
            "last_block_time": time.time(),
            "blocks_mined": 0,
            "transactions_processed": 0,
            "errors_encountered": 0,
            "network_peers": 0,
            "mempool_size": 0,
            "sync_status": "synced",
        }

        self.health_history: deque = deque(maxlen=100)
        self.logger: logging.Logger = logging.getLogger("health_monitor")
        self.logger.setLevel(logging.INFO)

    def update_metrics(self, blockchain: Any, node: Any | None = None) -> None:
        """
        Update health metrics from blockchain and node state.

        Args:
            blockchain: Blockchain instance
            node: Optional node instance for network metrics
        """
        self.metrics["last_block_time"] = blockchain.get_latest_block().timestamp
        self.metrics["blocks_mined"] = len(blockchain.chain)
        self.metrics["mempool_size"] = len(blockchain.pending_transactions)

        if node:
            self.metrics["network_peers"] = len(node.peers) if hasattr(node, "peers") else 0

        # Calculate and record health score
        health_score = self._calculate_health_score(blockchain)

        self.health_history.append(
            {"timestamp": time.time(), "score": health_score, "metrics": dict(self.metrics)}
        )

    def _calculate_health_score(self, blockchain: Any) -> float:
        """
        Calculate overall health score (0-100).

        Args:
            blockchain: Blockchain instance

        Returns:
            Health score between 0 and 100
        """
        score = 100.0

        # Penalize if last block is old
        time_since_last_block = time.time() - self.metrics["last_block_time"]
        if time_since_last_block > 600:  # 10 minutes
            score -= min(30, time_since_last_block / 60)

        # Penalize if mempool is very full
        if self.metrics["mempool_size"] > 10000:
            score -= min(20, (self.metrics["mempool_size"] - 10000) / 500)

        # Penalize if no peers
        if self.metrics["network_peers"] == 0:
            score -= 25

        # Penalize for errors
        if self.metrics["errors_encountered"] > 10:
            score -= min(25, self.metrics["errors_encountered"])

        return max(0, score)

    def get_health_status(self) -> dict[str, Any]:
        """
        Get current health status with score and classification.

        Returns:
            Dictionary with health status information
        """
        if not self.health_history:
            return {"status": "unknown", "score": 0, "metrics": self.metrics}

        current = self.health_history[-1]
        score = current["score"]

        # Classify health status
        if score >= 80:
            status = "healthy"
        elif score >= 60:
            status = "degraded"
        elif score >= 40:
            status = "warning"
        else:
            status = "critical"

        return {
            "status": status,
            "score": score,
            "metrics": current["metrics"],
            "timestamp": current["timestamp"],
        }

    def get_health_trend(self) -> str:
        """
        Analyze health trend over recent history.

        Returns:
            Trend description: "improving", "declining", or "stable"
        """
        if len(self.health_history) < 10:
            return "stable"

        recent = list(self.health_history)[-10:]
        first_half_avg = sum(h["score"] for h in recent[:5]) / 5
        second_half_avg = sum(h["score"] for h in recent[5:]) / 5

        diff = second_half_avg - first_half_avg

        if diff > 5:
            return "improving"
        elif diff < -5:
            return "declining"
        else:
            return "stable"
