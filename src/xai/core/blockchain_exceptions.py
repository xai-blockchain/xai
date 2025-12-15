"""
Blockchain-specific exception hierarchy for XAI.

Provides typed exceptions for blockchain operations to replace bare Exception
handlers and enable precise error handling, recovery, and diagnostics.
"""

from __future__ import annotations
from typing import Optional, Any, Dict


class BlockchainError(Exception):
    """Base exception for all blockchain-related errors.

    All blockchain exceptions inherit from this base class to enable
    catch-all handling when needed while maintaining type specificity.

    Attributes:
        message: Human-readable error description
        details: Additional context about the error
        recoverable: Whether the operation can be retried
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.recoverable = recoverable


# ==================== Validation Errors ====================


class ValidationError(BlockchainError):
    """Raised when blockchain data fails validation rules.

    Used for block validation, transaction validation, signature verification,
    and other validation failures.
    """
    pass


class InvalidBlockError(ValidationError):
    """Raised when a block fails structural or consensus validation.

    Examples: invalid hash, timestamp, difficulty, nonce, or transaction merkle root.
    """
    pass


class InvalidTransactionError(ValidationError):
    """Raised when a transaction fails validation.

    Examples: invalid signature, insufficient balance, nonce mismatch, double spend.
    """
    pass


class SignatureError(ValidationError):
    """Raised when cryptographic signature verification fails."""
    pass


class NonceError(ValidationError):
    """Raised when transaction nonce is invalid or out of sequence."""
    pass


class InsufficientBalanceError(ValidationError):
    """Raised when account lacks sufficient balance for an operation."""
    pass


# ==================== Consensus Errors ====================


class ConsensusError(BlockchainError):
    """Raised when consensus rules are violated."""
    pass


class ForkDetectedError(ConsensusError):
    """Raised when blockchain fork is detected."""
    pass


class OrphanBlockError(ConsensusError):
    """Raised when a block's parent is not found in the chain."""
    pass


class ChainReorgError(ConsensusError):
    """Raised when chain reorganization fails or encounters issues."""

    def __init__(
        self,
        message: str,
        old_height: Optional[int] = None,
        new_height: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.old_height = old_height
        self.new_height = new_height


# ==================== Storage Errors ====================


class StorageError(BlockchainError):
    """Raised when blockchain storage operations fail."""
    pass


class DatabaseError(StorageError):
    """Raised when database operations fail."""
    pass


class CorruptedDataError(StorageError):
    """Raised when stored blockchain data is corrupted or invalid."""
    recoverable = False  # Data corruption usually requires manual intervention


class StateError(StorageError):
    """Raised when blockchain state is inconsistent or invalid."""
    pass


# ==================== Transaction Pool Errors ====================


class MempoolError(BlockchainError):
    """Raised when mempool operations fail."""
    pass


class DuplicateTransactionError(MempoolError):
    """Raised when attempting to add a transaction that already exists in mempool."""
    pass


class MempoolFullError(MempoolError):
    """Raised when mempool has reached capacity."""
    recoverable = True  # Can retry after mempool clears


# ==================== Network & Synchronization Errors ====================


class NetworkError(BlockchainError):
    """Raised when network operations fail."""
    recoverable = True  # Network errors are often transient


class PeerError(NetworkError):
    """Raised when peer-related operations fail."""
    pass


class SyncError(NetworkError):
    """Raised when blockchain synchronization fails."""
    pass


# ==================== Mining Errors ====================


class MiningError(BlockchainError):
    """Raised when mining operations fail."""
    pass


class InvalidProofOfWorkError(MiningError):
    """Raised when proof-of-work does not meet difficulty target."""
    pass


class MiningRateLimitError(MiningError):
    """Raised when mining rate limit is exceeded."""
    recoverable = True  # Can retry after rate limit window


class MiningAbortedError(MiningError):
    """Raised when mining is aborted due to receiving a peer block at the same height."""
    recoverable = True  # Can retry mining next block


# ==================== Smart Contract & VM Errors ====================


class VMError(BlockchainError):
    """Raised when virtual machine execution fails."""
    pass


class ContractError(VMError):
    """Raised when smart contract execution fails."""
    pass


class OutOfGasError(VMError):
    """Raised when contract execution runs out of gas."""
    pass


class RevertError(VMError):
    """Raised when contract execution reverts."""

    def __init__(
        self,
        message: str,
        reason: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.reason = reason


# ==================== Configuration & Initialization Errors ====================


class ConfigurationError(BlockchainError):
    """Raised when blockchain configuration is invalid."""
    recoverable = False


class InitializationError(BlockchainError):
    """Raised when blockchain initialization fails."""
    recoverable = False


# ==================== Utility Functions ====================


def is_recoverable_error(exc: Exception) -> bool:
    """Check if an exception represents a recoverable error.

    Args:
        exc: The exception to check

    Returns:
        True if the error is recoverable and the operation can be retried
    """
    if isinstance(exc, BlockchainError):
        return exc.recoverable

    # Some standard exceptions are known to be recoverable
    recoverable_types = (
        ConnectionError,
        TimeoutError,
        OSError,  # Includes network errors, file system errors
    )
    return isinstance(exc, recoverable_types)


def get_error_context(exc: Exception) -> Dict[str, Any]:
    """Extract error context from an exception for logging.

    Args:
        exc: The exception to extract context from

    Returns:
        Dictionary containing error type, message, and any additional details
    """
    context = {
        "error_type": type(exc).__name__,
        "error_message": str(exc),
    }

    if isinstance(exc, BlockchainError):
        context["recoverable"] = exc.recoverable
        if exc.details:
            context["details"] = exc.details

    if isinstance(exc, ChainReorgError):
        if exc.old_height is not None:
            context["old_height"] = exc.old_height
        if exc.new_height is not None:
            context["new_height"] = exc.new_height

    if isinstance(exc, RevertError) and exc.reason:
        context["revert_reason"] = exc.reason

    return context
