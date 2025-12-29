"""
Structured Error Response Module

Provides standardized error response formats for the XAI API:
- Consistent error structure across all endpoints
- Error code definitions
- Error serialization and validation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """Standard error codes for API responses."""

    # Authentication/Authorization (1xxx)
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_API_KEY = "INVALID_API_KEY"
    EXPIRED_API_KEY = "EXPIRED_API_KEY"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"

    # Validation (2xxx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    MISSING_PARAMETER = "MISSING_PARAMETER"
    INVALID_ADDRESS = "INVALID_ADDRESS"
    INVALID_HASH = "INVALID_HASH"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    INVALID_AMOUNT = "INVALID_AMOUNT"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"

    # Resource (3xxx)
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    TRANSACTION_NOT_FOUND = "TRANSACTION_NOT_FOUND"
    BLOCK_NOT_FOUND = "BLOCK_NOT_FOUND"
    PROPOSAL_NOT_FOUND = "PROPOSAL_NOT_FOUND"
    CONTRACT_NOT_FOUND = "CONTRACT_NOT_FOUND"
    WEBHOOK_NOT_FOUND = "WEBHOOK_NOT_FOUND"

    # Transaction (4xxx)
    TRANSACTION_REJECTED = "TRANSACTION_REJECTED"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    INSUFFICIENT_FEE = "INSUFFICIENT_FEE"
    NONCE_TOO_LOW = "NONCE_TOO_LOW"
    NONCE_TOO_HIGH = "NONCE_TOO_HIGH"
    DUPLICATE_TRANSACTION = "DUPLICATE_TRANSACTION"
    SPEND_LIMIT_EXCEEDED = "SPEND_LIMIT_EXCEEDED"

    # Rate Limiting (5xxx)
    RATE_LIMITED = "RATE_LIMITED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"

    # Service (6xxx)
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    SERVICE_PAUSED = "SERVICE_PAUSED"
    TIMEOUT = "TIMEOUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    BLOCKCHAIN_UNAVAILABLE = "BLOCKCHAIN_UNAVAILABLE"
    P2P_UNAVAILABLE = "P2P_UNAVAILABLE"

    # Governance (7xxx)
    VOTING_CLOSED = "VOTING_CLOSED"
    ALREADY_VOTED = "ALREADY_VOTED"
    PROPOSAL_EXPIRED = "PROPOSAL_EXPIRED"
    INVALID_VOTE = "INVALID_VOTE"

    # Batch Operations (8xxx)
    BATCH_TOO_LARGE = "BATCH_TOO_LARGE"
    PARTIAL_FAILURE = "PARTIAL_FAILURE"
    IMPORT_FAILED = "IMPORT_FAILED"

    # Contract (9xxx)
    CONTRACT_EXECUTION_FAILED = "CONTRACT_EXECUTION_FAILED"
    CONTRACT_REVERTED = "CONTRACT_REVERTED"
    OUT_OF_GAS = "OUT_OF_GAS"
    INVALID_OPCODE = "INVALID_OPCODE"


# HTTP status code mapping for error codes
ERROR_STATUS_MAP: dict[ErrorCode, int] = {
    # 400 Bad Request
    ErrorCode.VALIDATION_ERROR: 400,
    ErrorCode.INVALID_PARAMETER: 400,
    ErrorCode.MISSING_PARAMETER: 400,
    ErrorCode.INVALID_ADDRESS: 400,
    ErrorCode.INVALID_HASH: 400,
    ErrorCode.INVALID_SIGNATURE: 400,
    ErrorCode.INVALID_AMOUNT: 400,
    ErrorCode.INVALID_PAYLOAD: 400,
    ErrorCode.TRANSACTION_REJECTED: 400,
    ErrorCode.NONCE_TOO_LOW: 400,
    ErrorCode.NONCE_TOO_HIGH: 400,
    ErrorCode.DUPLICATE_TRANSACTION: 400,
    ErrorCode.INVALID_VOTE: 400,
    ErrorCode.BATCH_TOO_LARGE: 400,
    ErrorCode.IMPORT_FAILED: 400,
    # 401 Unauthorized
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.INVALID_API_KEY: 401,
    ErrorCode.EXPIRED_API_KEY: 401,
    # 403 Forbidden
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.INSUFFICIENT_PERMISSIONS: 403,
    ErrorCode.INSUFFICIENT_BALANCE: 403,
    ErrorCode.INSUFFICIENT_FEE: 403,
    ErrorCode.SPEND_LIMIT_EXCEEDED: 403,
    ErrorCode.VOTING_CLOSED: 403,
    ErrorCode.ALREADY_VOTED: 403,
    ErrorCode.PROPOSAL_EXPIRED: 403,
    # 404 Not Found
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.TRANSACTION_NOT_FOUND: 404,
    ErrorCode.BLOCK_NOT_FOUND: 404,
    ErrorCode.PROPOSAL_NOT_FOUND: 404,
    ErrorCode.CONTRACT_NOT_FOUND: 404,
    ErrorCode.WEBHOOK_NOT_FOUND: 404,
    # 409 Conflict
    ErrorCode.ALREADY_EXISTS: 409,
    # 429 Too Many Requests
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.QUOTA_EXCEEDED: 429,
    # 500 Internal Server Error
    ErrorCode.INTERNAL_ERROR: 500,
    ErrorCode.CONTRACT_EXECUTION_FAILED: 500,
    ErrorCode.CONTRACT_REVERTED: 500,
    ErrorCode.OUT_OF_GAS: 500,
    ErrorCode.INVALID_OPCODE: 500,
    ErrorCode.PARTIAL_FAILURE: 500,
    # 503 Service Unavailable
    ErrorCode.SERVICE_UNAVAILABLE: 503,
    ErrorCode.SERVICE_PAUSED: 503,
    ErrorCode.BLOCKCHAIN_UNAVAILABLE: 503,
    ErrorCode.P2P_UNAVAILABLE: 503,
    # 504 Gateway Timeout
    ErrorCode.TIMEOUT: 504,
}


@dataclass
class ErrorDetail:
    """Additional error details."""

    field: str | None = None
    reason: str | None = None
    value: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {}
        if self.field:
            result["field"] = self.field
        if self.reason:
            result["reason"] = self.reason
        if self.value is not None:
            result["value"] = self.value
        return result


@dataclass
class APIError:
    """
    Structured API error response.

    Format:
    {
        "error": {
            "code": "ERROR_CODE",
            "message": "Human readable message",
            "details": {...}  // Optional additional context
        }
    }
    """

    code: ErrorCode | str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to API response format."""
        error_body: dict[str, Any] = {
            "code": self.code.value if isinstance(self.code, ErrorCode) else self.code,
            "message": self.message,
        }

        if self.details:
            error_body["details"] = self.details

        if self.request_id:
            error_body["request_id"] = self.request_id

        return {"error": error_body}

    @property
    def status_code(self) -> int:
        """Get appropriate HTTP status code for this error."""
        if isinstance(self.code, ErrorCode):
            return ERROR_STATUS_MAP.get(self.code, 500)
        return 500

    def to_response(self) -> tuple[dict[str, Any], int]:
        """Return as Flask response tuple (body, status_code)."""
        return self.to_dict(), self.status_code


def error_response(
    code: ErrorCode | str,
    message: str,
    details: dict[str, Any] | None = None,
    status: int | None = None,
    request_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """
    Create a structured error response.

    Args:
        code: Error code (from ErrorCode enum or string)
        message: Human-readable error message
        details: Additional error context
        status: Override HTTP status code (optional)
        request_id: Request ID for tracing

    Returns:
        Tuple of (response_dict, status_code) for Flask
    """
    error = APIError(
        code=code,
        message=message,
        details=details or {},
        request_id=request_id,
    )

    response_status = status if status is not None else error.status_code
    return error.to_dict(), response_status


def validation_error(
    message: str,
    field: str | None = None,
    value: Any = None,
) -> tuple[dict[str, Any], int]:
    """Create a validation error response."""
    details: dict[str, Any] = {}
    if field:
        details["field"] = field
    if value is not None:
        details["invalid_value"] = value

    return error_response(
        code=ErrorCode.VALIDATION_ERROR,
        message=message,
        details=details,
    )


def not_found_error(
    resource_type: str,
    resource_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Create a not found error response."""
    message = f"{resource_type} not found"
    if resource_id:
        message = f"{resource_type} '{resource_id}' not found"

    return error_response(
        code=ErrorCode.NOT_FOUND,
        message=message,
        details={"resource_type": resource_type, "resource_id": resource_id},
    )


def unauthorized_error(
    message: str = "Authentication required",
    details: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], int]:
    """Create an unauthorized error response."""
    return error_response(
        code=ErrorCode.UNAUTHORIZED,
        message=message,
        details=details,
    )


def rate_limit_error(
    limit: int,
    window_seconds: int,
    retry_after: int | None = None,
) -> tuple[dict[str, Any], int]:
    """Create a rate limit error response."""
    details = {
        "limit": limit,
        "window_seconds": window_seconds,
    }
    if retry_after:
        details["retry_after"] = retry_after

    return error_response(
        code=ErrorCode.RATE_LIMITED,
        message=f"Rate limit exceeded. Maximum {limit} requests per {window_seconds} seconds.",
        details=details,
    )


def internal_error(
    message: str = "An internal error occurred",
    request_id: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Create an internal error response."""
    return error_response(
        code=ErrorCode.INTERNAL_ERROR,
        message=message,
        request_id=request_id,
    )


def service_unavailable_error(
    service: str,
    reason: str | None = None,
) -> tuple[dict[str, Any], int]:
    """Create a service unavailable error response."""
    message = f"Service {service} is currently unavailable"
    if reason:
        message = f"{message}: {reason}"

    return error_response(
        code=ErrorCode.SERVICE_UNAVAILABLE,
        message=message,
        details={"service": service},
    )


# Convenience aliases for common error patterns
class ErrorResponses:
    """Factory methods for common error responses."""

    @staticmethod
    def invalid_address(address: str) -> tuple[dict[str, Any], int]:
        """Invalid blockchain address error."""
        return error_response(
            code=ErrorCode.INVALID_ADDRESS,
            message="Invalid blockchain address format",
            details={"address": address[:20] + "..." if len(address) > 20 else address},
        )

    @staticmethod
    def invalid_signature() -> tuple[dict[str, Any], int]:
        """Invalid transaction signature error."""
        return error_response(
            code=ErrorCode.INVALID_SIGNATURE,
            message="Transaction signature verification failed",
        )

    @staticmethod
    def insufficient_balance(
        required: float,
        available: float,
    ) -> tuple[dict[str, Any], int]:
        """Insufficient balance error."""
        return error_response(
            code=ErrorCode.INSUFFICIENT_BALANCE,
            message="Insufficient balance for transaction",
            details={
                "required": required,
                "available": available,
                "shortfall": required - available,
            },
        )

    @staticmethod
    def transaction_rejected(reason: str) -> tuple[dict[str, Any], int]:
        """Transaction rejected error."""
        return error_response(
            code=ErrorCode.TRANSACTION_REJECTED,
            message=f"Transaction rejected: {reason}",
            details={"reason": reason},
        )

    @staticmethod
    def proposal_not_found(proposal_id: str) -> tuple[dict[str, Any], int]:
        """Governance proposal not found error."""
        return error_response(
            code=ErrorCode.PROPOSAL_NOT_FOUND,
            message=f"Governance proposal '{proposal_id}' not found",
            details={"proposal_id": proposal_id},
        )

    @staticmethod
    def voting_closed(proposal_id: str) -> tuple[dict[str, Any], int]:
        """Voting closed error."""
        return error_response(
            code=ErrorCode.VOTING_CLOSED,
            message="Voting has closed for this proposal",
            details={"proposal_id": proposal_id},
        )

    @staticmethod
    def batch_too_large(
        max_size: int,
        provided: int,
    ) -> tuple[dict[str, Any], int]:
        """Batch size exceeded error."""
        return error_response(
            code=ErrorCode.BATCH_TOO_LARGE,
            message=f"Batch size {provided} exceeds maximum of {max_size}",
            details={"max_size": max_size, "provided": provided},
        )
