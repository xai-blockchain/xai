"""
XAI Blockchain - Error Handlers and Circuit Breaker System

Specialized error handling mechanisms:
- Circuit breaker pattern
- Retry strategies with exponential backoff
- Specific handlers for different error types
- Handler registration and dispatch
- Error logging and reporting
"""

import time
import logging
from typing import Callable, Optional, Tuple, Any, Dict, List
from enum import Enum
from collections import deque


class CircuitState(Enum):
    """Circuit breaker states for failure management."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents cascading failures by breaking the circuit when
    a service is experiencing issues. Automatically tests recovery
    after a timeout period.
    """

    def __init__(
        self, failure_threshold: int = 5, timeout: int = 60, success_threshold: int = 2
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting recovery
            success_threshold: Successes needed to close circuit from half-open
        """
        self.failure_threshold: int = failure_threshold
        self.timeout: int = timeout
        self.success_threshold: int = success_threshold

        self.failure_count: int = 0
        self.success_count: int = 0
        self.last_failure_time: Optional[float] = None
        self.state: CircuitState = CircuitState.CLOSED

        self.logger: logging.Logger = logging.getLogger("circuit_breaker")
        self.logger.setLevel(logging.INFO)

    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Tuple[bool, Any, Optional[str]]:
        """
        Execute function through circuit breaker.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Tuple of (success, result, error_message)
        """
        if self.state == CircuitState.OPEN:
            # Check if timeout has elapsed
            if self.last_failure_time and time.time() - self.last_failure_time >= self.timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                self.logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                return False, None, "Circuit breaker is OPEN"

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return True, result, None
        except Exception as e:
            self._on_failure()
            return False, None, str(e)

    def _on_success(self) -> None:
        """Handle successful call."""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.success_count = 0
                self.logger.info("Circuit breaker CLOSED - service recovered")

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.success_count = 0
            self.logger.warning("Circuit breaker OPEN - recovery failed")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.error(f"Circuit breaker OPEN - {self.failure_count} failures")

    def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.logger.info("Circuit breaker manually reset")

    def get_state(self) -> Dict[str, Any]:
        """
        Get current circuit breaker state.

        Returns:
            Dictionary with state information
        """
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
        }


class RetryStrategy:
    """
    Retry logic with exponential backoff and jitter.

    Automatically retries failed operations with increasing
    delays between attempts to prevent overwhelming the system.
    Includes jitter to prevent thundering herd problem.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ) -> None:
        """
        Initialize retry strategy.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential backoff calculation
            jitter: Add random jitter to prevent thundering herd
        """
        self.max_retries: int = max_retries
        self.base_delay: float = base_delay
        self.max_delay: float = max_delay
        self.exponential_base: float = exponential_base
        self.jitter: bool = jitter

        self.logger: logging.Logger = logging.getLogger("retry_strategy")
        self.logger.setLevel(logging.INFO)

    def execute(self, func: Callable, *args: Any, **kwargs: Any) -> Tuple[bool, Any, Optional[str]]:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Tuple of (success, result, error_message)
        """
        last_error: Optional[str] = None

        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    self.logger.info(f"Operation succeeded on attempt {attempt + 1}")
                return True, result, None
            except Exception as e:
                last_error = str(e)
                self.logger.warning(f"Attempt {attempt + 1} failed: {last_error}")

                if attempt < self.max_retries:
                    # Calculate delay with exponential backoff
                    delay = min(self.base_delay * (self.exponential_base**attempt), self.max_delay)

                    # Add jitter to prevent thundering herd
                    if self.jitter:
                        import random
                        delay = delay * (0.5 + random.random())

                    self.logger.info(f"Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)

        return False, None, f"Failed after {self.max_retries + 1} attempts: {last_error}"


class ErrorHandler:
    """
    Base class for specific error handlers.

    Provides a framework for implementing specialized handlers
    for different types of errors (network, validation, storage, etc.)
    """

    def __init__(self, name: str) -> None:
        """
        Initialize error handler.

        Args:
            name: Handler name for logging
        """
        self.name: str = name
        self.handled_count: int = 0
        self.logger: logging.Logger = logging.getLogger(f"handler.{name}")
        self.logger.setLevel(logging.INFO)

    def can_handle(self, error: Exception, context: str) -> bool:
        """
        Check if this handler can handle the error.

        Args:
            error: The exception that occurred
            context: Error context

        Returns:
            True if handler can handle this error
        """
        raise NotImplementedError("Subclasses must implement can_handle()")

    def handle(self, error: Exception, context: str, blockchain: Any) -> Tuple[bool, Optional[str]]:
        """
        Handle the error.

        Args:
            error: The exception to handle
            context: Error context
            blockchain: Blockchain instance

        Returns:
            Tuple of (handled_successfully, error_message)
        """
        raise NotImplementedError("Subclasses must implement handle()")


class NetworkErrorHandler(ErrorHandler):
    """Handler for network-related errors."""

    def __init__(self) -> None:
        """Initialize network error handler."""
        super().__init__("network")
        self.retry_strategy = RetryStrategy(max_retries=3, base_delay=2.0)

    def can_handle(self, error: Exception, context: str) -> bool:
        """Check if error is network-related."""
        error_type = type(error).__name__
        return error_type in ["ConnectionError", "TimeoutError", "NetworkError", "OSError"]

    def handle(self, error: Exception, context: str, blockchain: Any) -> Tuple[bool, Optional[str]]:
        """
        Handle network error.

        Args:
            error: The network exception
            context: Error context
            blockchain: Blockchain instance

        Returns:
            Tuple of (handled, error_message)
        """
        self.logger.warning(f"Handling network error: {error}")
        self.handled_count += 1

        # Network errors are usually temporary - log and continue
        return True, f"Network error handled: {str(error)}"


class ValidationErrorHandler(ErrorHandler):
    """Handler for validation-related errors."""

    def __init__(self) -> None:
        """Initialize validation error handler."""
        super().__init__("validation")

    def can_handle(self, error: Exception, context: str) -> bool:
        """Check if error is validation-related."""
        error_type = type(error).__name__
        return error_type in ["ValueError", "ValidationError"] or "invalid" in str(error).lower()

    def handle(self, error: Exception, context: str, blockchain: Any) -> Tuple[bool, Optional[str]]:
        """
        Handle validation error.

        Args:
            error: The validation exception
            context: Error context
            blockchain: Blockchain instance

        Returns:
            Tuple of (handled, error_message)
        """
        self.logger.warning(f"Handling validation error in {context}: {error}")
        self.handled_count += 1

        # Validation errors typically require rejecting the input
        return True, f"Validation error - input rejected: {str(error)}"


class StorageErrorHandler(ErrorHandler):
    """Handler for storage/database-related errors."""

    def __init__(self) -> None:
        """Initialize storage error handler."""
        super().__init__("storage")
        self.retry_strategy = RetryStrategy(max_retries=2, base_delay=1.0)

    def can_handle(self, error: Exception, context: str) -> bool:
        """Check if error is storage-related."""
        error_type = type(error).__name__
        return error_type in ["IOError", "OSError", "PermissionError", "FileNotFoundError"]

    def handle(self, error: Exception, context: str, blockchain: Any) -> Tuple[bool, Optional[str]]:
        """
        Handle storage error.

        Args:
            error: The storage exception
            context: Error context
            blockchain: Blockchain instance

        Returns:
            Tuple of (handled, error_message)
        """
        self.logger.error(f"Handling storage error in {context}: {error}")
        self.handled_count += 1

        # Storage errors are critical - may require recovery
        return False, f"Storage error - recovery may be needed: {str(error)}"


class ErrorHandlerRegistry:
    """
    Registry and dispatcher for error handlers.

    Manages multiple error handlers and routes errors to
    the appropriate handler based on error type.
    """

    def __init__(self) -> None:
        """Initialize error handler registry."""
        self.handlers: List[ErrorHandler] = []
        self.fallback_handler: Optional[ErrorHandler] = None
        self.logger: logging.Logger = logging.getLogger("error_handler_registry")
        self.logger.setLevel(logging.INFO)

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register default error handlers."""
        self.register_handler(NetworkErrorHandler())
        self.register_handler(ValidationErrorHandler())
        self.register_handler(StorageErrorHandler())

    def register_handler(self, handler: ErrorHandler) -> None:
        """
        Register an error handler.

        Args:
            handler: ErrorHandler instance to register
        """
        self.handlers.append(handler)
        self.logger.info(f"Registered handler: {handler.name}")

    def set_fallback_handler(self, handler: ErrorHandler) -> None:
        """
        Set fallback handler for unhandled errors.

        Args:
            handler: ErrorHandler to use as fallback
        """
        self.fallback_handler = handler
        self.logger.info(f"Set fallback handler: {handler.name}")

    def handle_error(
        self, error: Exception, context: str, blockchain: Any
    ) -> Tuple[bool, Optional[str]]:
        """
        Handle error by dispatching to appropriate handler.

        Args:
            error: The exception to handle
            context: Error context
            blockchain: Blockchain instance

        Returns:
            Tuple of (handled_successfully, error_message)
        """
        # Find appropriate handler
        for handler in self.handlers:
            if handler.can_handle(error, context):
                self.logger.info(f"Dispatching to handler: {handler.name}")
                return handler.handle(error, context, blockchain)

        # Use fallback handler if available
        if self.fallback_handler:
            self.logger.info("Using fallback handler")
            return self.fallback_handler.handle(error, context, blockchain)

        # No handler found
        self.logger.error(f"No handler found for error: {type(error).__name__}")
        return False, f"Unhandled error: {str(error)}"

    def get_handler_statistics(self) -> Dict[str, Any]:
        """
        Get statistics for all registered handlers.

        Returns:
            Dictionary with handler statistics
        """
        return {
            "total_handlers": len(self.handlers),
            "handlers": [
                {"name": handler.name, "handled_count": handler.handled_count}
                for handler in self.handlers
            ],
        }


class ErrorLogger:
    """
    Specialized error logging with categorization and analysis.

    Provides structured error logging with severity levels,
    context tracking, and historical analysis.
    """

    def __init__(self, max_entries: int = 1000) -> None:
        """
        Initialize error logger.

        Args:
            max_entries: Maximum number of log entries to retain
        """
        self.error_log: deque = deque(maxlen=max_entries)
        self.logger: logging.Logger = logging.getLogger("error_logger")
        self.logger.setLevel(logging.INFO)

    def log_error(
        self,
        error: Exception,
        context: str,
        severity: str = "medium",
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an error with full context.

        Args:
            error: The exception that occurred
            context: Error context
            severity: Error severity level
            additional_info: Optional additional information
        """
        entry = {
            "timestamp": time.time(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "severity": severity,
            "additional_info": additional_info or {},
        }

        self.error_log.append(entry)

        # Log to standard logger
        log_msg = f"[{severity.upper()}] {context}: {type(error).__name__} - {str(error)}"
        if severity == "critical":
            self.logger.error(log_msg)
        elif severity == "high":
            self.logger.error(log_msg)
        else:
            self.logger.warning(log_msg)

    def get_recent_errors(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get most recent errors.

        Args:
            count: Number of recent errors to return

        Returns:
            List of recent error entries
        """
        return list(self.error_log)[-count:]

    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get summary of logged errors.

        Returns:
            Dictionary with error summary statistics
        """
        if not self.error_log:
            return {"total_errors": 0, "by_severity": {}, "by_type": {}}

        by_severity: Dict[str, int] = {}
        by_type: Dict[str, int] = {}

        for entry in self.error_log:
            severity = entry["severity"]
            error_type = entry["error_type"]

            by_severity[severity] = by_severity.get(severity, 0) + 1
            by_type[error_type] = by_type.get(error_type, 0) + 1

        return {
            "total_errors": len(self.error_log),
            "by_severity": by_severity,
            "by_type": by_type,
            "recent_errors": self.get_recent_errors(5),
        }
