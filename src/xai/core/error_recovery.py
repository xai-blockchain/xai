from __future__ import annotations

"""
XAI Blockchain - Error Recovery and Resilience System

High-level coordinator for comprehensive error handling:
- Graceful shutdown on errors
- Database corruption recovery
- Network partition handling
- Invalid block/transaction handling
- Circuit breaker pattern
- Automatic retry with exponential backoff
- State recovery and rollback
- Health monitoring
- Transaction queue preservation

This module acts as a lightweight coordinator that delegates to specialized modules:
- error_detection: Error detection and classification
- error_handlers: Circuit breakers, retry logic, error handlers
- recovery_strategies: Backup, restoration, and recovery mechanisms
"""

import logging
import threading
from collections import deque
from typing import Any, Callable

# Import specialized modules
from xai.core.error_detection import (
    CorruptionDetector,
    ErrorDetector,
    ErrorSeverity,
    HealthMonitor,
    RecoveryState,
)
from xai.core.error_handlers import (
    CircuitBreaker,
    ErrorHandlerRegistry,
    ErrorLogger,
    RetryStrategy,
)
from xai.core.recovery_strategies import (
    BlockchainBackup,
    CorruptionRecovery,
    GracefulShutdown,
    NetworkPartitionRecovery,
    StateRecovery,
)


class ErrorRecoveryManager:
    """
    Main error recovery and resilience manager.

    Coordinates all recovery mechanisms and provides high-level
    error handling for the blockchain by delegating to specialized modules.
    """

    def __init__(
        self, blockchain: Any, node: Any | None = None, config: Dict | None = None
    ) -> None:
        """
        Initialize error recovery manager.

        Args:
            blockchain: Blockchain instance to protect
            node: Optional node instance
            config: Optional configuration dictionary
        """
        self.blockchain = blockchain
        self.node = node
        self.config: Dict = config or {}

        # Recovery state
        self.state: RecoveryState = RecoveryState.HEALTHY
        self.recovery_in_progress: bool = False

        # Initialize detection components
        self.error_detector: ErrorDetector = ErrorDetector(blockchain)
        self.corruption_detector: CorruptionDetector = CorruptionDetector()
        self.health_monitor: HealthMonitor = HealthMonitor()

        # Initialize handler components
        self.circuit_breakers: dict[str, CircuitBreaker] = {
            "mining": CircuitBreaker(failure_threshold=5, timeout=60),
            "validation": CircuitBreaker(failure_threshold=3, timeout=30),
            "network": CircuitBreaker(failure_threshold=10, timeout=120),
            "storage": CircuitBreaker(failure_threshold=2, timeout=30),
        }
        self.retry_strategy: RetryStrategy = RetryStrategy(max_retries=3, base_delay=1.0)
        self.error_handler_registry: ErrorHandlerRegistry = ErrorHandlerRegistry()
        self.error_logger: ErrorLogger = ErrorLogger()

        # Initialize recovery components
        self.backup_manager: BlockchainBackup = BlockchainBackup()
        self.state_recovery: StateRecovery = StateRecovery()
        self.corruption_recovery: CorruptionRecovery = CorruptionRecovery(self.backup_manager)
        self.network_recovery: NetworkPartitionRecovery = NetworkPartitionRecovery()
        self.graceful_shutdown_manager: GracefulShutdown = GracefulShutdown(self.backup_manager)

        # Tracking
        self.error_log: deque = deque(maxlen=1000)
        self.recovery_log: deque = deque(maxlen=100)

        # Setup logging
        self.logger: logging.Logger = logging.getLogger("error_recovery")
        self.logger.setLevel(logging.INFO)

        # Start health monitoring
        self.monitoring_active: bool = True
        self.monitor_thread: threading.Thread = threading.Thread(
            target=self._monitor_health, daemon=True
        )
        self.monitor_thread.start()

    def wrap_operation(
        self, operation: str, func: Callable, *args: Any, **kwargs: Any
    ) -> tuple[bool, Any, str | None]:
        """
        Wrap critical operation with circuit breaker and error handling.

        Args:
            operation: Operation name (mining, validation, network, storage)
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Tuple of (success, result, error_message)
        """
        circuit_breaker = self.circuit_breakers.get(operation)

        if circuit_breaker:
            success, result, error = circuit_breaker.call(func, *args, **kwargs)
            if not success:
                self.error_logger.log_error(
                    Exception(error or "Unknown error"), operation, "medium"
                )
            return success, result, error
        else:
            try:
                result = func(*args, **kwargs)
                return True, result, None
            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                self.error_logger.log_error(e, operation, "medium")
                self.logger.error(f"Error in {operation}", extra={"error_type": type(e).__name__})
                return False, None, str(e)

    def handle_corruption(self, force_rollback: bool = False) -> tuple[bool, str | None]:
        """
        Handle blockchain corruption using corruption recovery strategy.

        Args:
            force_rollback: Force rollback without corruption checks

        Returns:
            Tuple of (success, error_message)
        """
        self.logger.warning("Checking for blockchain corruption...")

        # Detect corruption
        is_corrupted, issues = self.corruption_detector.detect_corruption(self.blockchain)

        if not is_corrupted and not force_rollback:
            self.logger.info("No corruption detected")
            return True, None

        # Corruption detected - attempt recovery
        self.state = RecoveryState.RECOVERING
        self.recovery_in_progress = True

        success, error = self.corruption_recovery.recover_from_corruption(self.blockchain, issues)

        if success:
            self.state = RecoveryState.HEALTHY
            self._log_recovery("corruption_recovery", "success", "Recovered from corruption")
        else:
            self.state = RecoveryState.CRITICAL
            self._log_recovery("corruption_recovery", "failed", error or "Unknown error")

        self.recovery_in_progress = False
        return success, error

    def handle_network_partition(self) -> tuple[bool, str | None]:
        """
        Handle network partition using network recovery strategy.

        Returns:
            Tuple of (success, error_message)
        """
        self.logger.warning("Handling network partition...")

        if not self.node:
            return False, "No node instance available"

        # Attempt reconnection
        success, error = self.network_recovery.attempt_reconnection(self.node)

        if success:
            self._log_recovery("network_partition", "success", "Reconnected to network")
            return True, None

        # Enter degraded mode
        self.state = RecoveryState.DEGRADED
        success, error = self.network_recovery.enter_degraded_mode(self.node)
        self._log_recovery("network_partition", "degraded", "Operating in offline mode")

        return True, "Operating in degraded mode"

    def graceful_shutdown(self, reason: str = "manual") -> tuple[bool, str | None]:
        """
        Perform graceful shutdown with backup and transaction preservation.

        Args:
            reason: Shutdown reason

        Returns:
            Tuple of (success, error_message)
        """
        self.state = RecoveryState.SHUTDOWN
        self.monitoring_active = False

        return self.graceful_shutdown_manager.shutdown(self.blockchain, self.node, reason)

    def create_checkpoint(self, name: str | None = None) -> str:
        """
        Create blockchain checkpoint/backup.

        Args:
            name: Optional checkpoint name

        Returns:
            Path to created checkpoint
        """
        return self.backup_manager.create_backup(self.blockchain, name)

    def get_recovery_status(self) -> dict[str, Any]:
        """
        Get comprehensive recovery system status.

        Returns:
            Dictionary with status information
        """
        health_status = self.health_monitor.get_health_status()

        return {
            "state": self.state.value,
            "recovery_in_progress": self.recovery_in_progress,
            "health": health_status,
            "circuit_breakers": {
                name: breaker.state.value for name, breaker in self.circuit_breakers.items()
            },
            "recent_errors": self.error_logger.get_recent_errors(10),
            "recent_recoveries": list(self.recovery_log)[-10:],
            "backups_available": len(self.backup_manager.list_backups()),
            "error_statistics": self.error_detector.get_error_statistics(),
        }

    def _monitor_health(self) -> None:
        """Background health monitoring thread."""
        import time

        while self.monitoring_active:
            try:
                self.health_monitor.update_metrics(self.blockchain, self.node)

                health = self.health_monitor.get_health_status()
                if health["score"] < 40 and self.state == RecoveryState.HEALTHY:
                    self.logger.warning(f"Health degraded: score={health['score']}")
                    self.state = RecoveryState.DEGRADED

                # Auto-backup hourly
                if int(time.time()) % 3600 == 0:
                    self.backup_manager.create_backup(self.blockchain, f"auto_{int(time.time())}")
                    self.backup_manager.cleanup_old_backups(keep_count=24)

            except (OSError, IOError, ValueError, TypeError, RuntimeError) as e:
                self.logger.error(f"Health monitoring error: {e}", extra={"error_type": type(e).__name__})

            time.sleep(60)

    def _log_recovery(self, recovery_type: str, status: str, details: str) -> None:
        """
        Log recovery action.

        Args:
            recovery_type: Type of recovery performed
            status: Recovery status
            details: Recovery details
        """
        import time

        recovery_entry = {
            "timestamp": time.time(),
            "type": recovery_type,
            "status": status,
            "details": details,
        }

        self.recovery_log.append(recovery_entry)
        self.logger.info(f"Recovery [{recovery_type}]: {status} - {details}")

# Convenience functions for backward compatibility

def create_recovery_manager(
    blockchain: Any, node: Any | None = None, config: Dict | None = None
) -> ErrorRecoveryManager:
    """
    Create and initialize error recovery manager.

    Args:
        blockchain: Blockchain instance
        node: Optional node instance
        config: Optional configuration

    Returns:
        ErrorRecoveryManager instance
    """
    return ErrorRecoveryManager(blockchain, node, config)
