from __future__ import annotations

"""
XAI SDK Exception classes

Provides comprehensive error handling for SDK operations.
"""

from typing import Any


class XAIError(Exception):
    """Base exception class for all XAI SDK errors."""

    def __init__(
        self,
        message: str,
        code: int | None = None,
        error_details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize XAI Error.

        Args:
            message: Error message
            code: Error code
            error_details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.error_details = error_details or {}

    def __str__(self) -> str:
        """Return string representation of error."""
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message

class AuthenticationError(XAIError):
    """Raised when authentication fails."""

    pass

class AuthorizationError(XAIError):
    """Raised when user lacks required permissions."""

    pass

class ValidationError(XAIError):
    """Raised when input validation fails."""

    pass

class RateLimitError(XAIError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: int | None = None,
        code: int | None = None,
    ) -> None:
        """
        Initialize Rate Limit Error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retry
            code: HTTP status code
        """
        super().__init__(message, code)
        self.retry_after = retry_after

class NetworkError(XAIError):
    """Raised when network connectivity issue occurs."""

    pass

class TimeoutError(XAIError):
    """Raised when request times out."""

    pass

class NotFoundError(XAIError):
    """Raised when requested resource is not found."""

    pass

class ConflictError(XAIError):
    """Raised when resource conflict occurs."""

    pass

class InternalServerError(XAIError):
    """Raised when server encounters an error."""

    pass

class ServiceUnavailableError(XAIError):
    """Raised when service is temporarily unavailable."""

    pass

class TransactionError(XAIError):
    """Raised when transaction operation fails."""

    pass

class WalletError(XAIError):
    """Raised when wallet operation fails."""

    pass

class MiningError(XAIError):
    """Raised when mining operation fails."""

    pass

class GovernanceError(XAIError):
    """Raised when governance operation fails."""

    pass


class APIError(XAIError):
    """Raised when API operation fails."""

    pass
