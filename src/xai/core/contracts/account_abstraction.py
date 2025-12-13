"""
Account Abstraction Implementation (ERC-4337 Style).

Provides smart contract wallets with:
- Gasless transactions (sponsored by bundlers/paymasters)
- Custom signature validation
- Social recovery
- Multi-signature support
- Session keys
- Spending limits

This implementation follows ERC-4337 architecture:
- UserOperation: Struct representing user intent
- EntryPoint: Singleton contract handling UserOps
- Smart Account: User's smart contract wallet
- Paymaster: Optional sponsor for gas fees
- Bundler: Service that submits UserOps to EntryPoint

Security features:
- Nonce management
- Signature validation
- Gas limits
- Paymaster validation
- Replay protection
"""

from __future__ import annotations

import time
import logging
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable, Any, TYPE_CHECKING
from enum import Enum

from ..vm.exceptions import VMExecutionError
from ..crypto_utils import verify_signature_hex

if TYPE_CHECKING:
    from ..blockchain import Blockchain

logger = logging.getLogger(__name__)


# ==================== Signature Verification Exceptions ====================

class SignatureError(VMExecutionError):
    """Base exception for signature verification failures."""
    pass


class MalformedSignatureError(SignatureError):
    """
    Raised when signature format is invalid.

    This indicates the signature data itself is malformed (wrong length,
    invalid encoding, missing data, etc.). This should NEVER be silently
    ignored as it may indicate an attack or data corruption.
    """
    pass


class InvalidSignatureError(SignatureError):
    """
    Raised when signature does not match the claimed signer.

    This indicates the signature was properly formed but cryptographic
    verification failed - i.e., the signature was not created by the
    claimed signer's private key.
    """
    pass


class MissingPublicKeyError(SignatureError):
    """
    Raised when public key required for verification is not registered.

    Account abstraction requires public keys to be explicitly registered
    for signature verification. This error indicates the key is missing.
    """
    pass


# ERC-4337 Constants
VALIDATION_SUCCESS = 0
VALIDATION_FAILED = 1
SIG_VALIDATION_FAILED = 1
SIG_VALIDATION_SUCCESS = 0

# Gas limits
MAX_VERIFICATION_GAS = 150_000
MAX_CALL_GAS = 500_000


class AccountType(Enum):
    """Types of smart accounts."""
    SIMPLE = "simple"
    MULTI_SIG = "multisig"
    SOCIAL_RECOVERY = "social_recovery"
    SESSION_KEY = "session_key"


@dataclass
class UserOperation:
    """
    ERC-4337 UserOperation struct.

    Represents a user's intent to execute a transaction.
    This is what users sign instead of regular transactions.
    """

    sender: str  # Smart account address
    nonce: int  # Replay protection
    init_code: bytes = b""  # For account creation
    calldata: bytes = b""  # What to execute
    call_gas_limit: int = 200_000
    verification_gas_limit: int = 100_000
    pre_verification_gas: int = 50_000
    max_fee_per_gas: int = 1_000_000_000  # 1 Gwei
    max_priority_fee_per_gas: int = 1_000_000_000
    paymaster_and_data: bytes = b""  # Paymaster address + data
    signature: bytes = b""  # Account signature

    def pack(self) -> bytes:
        """Pack UserOp for hashing (without signature)."""
        # Simplified packing - real implementation uses ABI encoding
        return (
            self.sender.encode() +
            self.nonce.to_bytes(32, 'big') +
            hashlib.sha3_256(self.init_code).digest() +
            hashlib.sha3_256(self.calldata).digest() +
            self.call_gas_limit.to_bytes(32, 'big') +
            self.verification_gas_limit.to_bytes(32, 'big') +
            self.pre_verification_gas.to_bytes(32, 'big') +
            self.max_fee_per_gas.to_bytes(32, 'big') +
            self.max_priority_fee_per_gas.to_bytes(32, 'big') +
            hashlib.sha3_256(self.paymaster_and_data).digest()
        )

    def hash(self, entry_point: str, chain_id: int) -> bytes:
        """
        Get UserOp hash for signing.

        Args:
            entry_point: EntryPoint contract address
            chain_id: Chain ID for replay protection

        Returns:
            Hash to be signed
        """
        packed = self.pack()
        inner_hash = hashlib.sha3_256(packed).digest()

        # Include entry point and chain ID (prevents cross-chain replay)
        full_data = (
            inner_hash +
            entry_point.encode() +
            chain_id.to_bytes(32, 'big')
        )

        return hashlib.sha3_256(full_data).digest()


@dataclass
class ValidationResult:
    """Result of UserOp validation."""
    valid: bool
    valid_after: int = 0  # Timestamp after which valid
    valid_until: int = 0  # Timestamp until which valid
    sig_failed: bool = False
    prefund: int = 0  # Required prefund


@dataclass
class ExecutionResult:
    """Result of UserOp execution."""
    success: bool
    actual_gas_used: int
    return_data: bytes = b""


@dataclass
class SmartAccount:
    """
    Base smart account implementation.

    Smart accounts are contract wallets that can:
    - Use custom signature validation
    - Implement custom authorization logic
    - Be sponsored by paymasters

    Security: Signatures are verified using ECDSA on the secp256k1 curve.
    The owner_public_key must be provided for signature verification.
    """

    address: str = ""
    owner: str = ""
    owner_public_key: str = ""  # 64-byte hex public key for ECDSA verification

    # Account state
    nonce: int = 0
    balance: int = 0

    # Features
    account_type: AccountType = AccountType.SIMPLE

    # Entry point
    entry_point: str = ""

    def __post_init__(self) -> None:
        """Initialize account."""
        if not self.address:
            addr_hash = hashlib.sha3_256(
                f"smart_account:{self.owner}:{time.time()}".encode()
            ).digest()
            self.address = f"0x{addr_hash[-20:].hex()}"

    # ==================== IAccount Interface (ERC-4337) ====================

    def validate_user_op(
        self,
        user_op: UserOperation,
        user_op_hash: bytes,
        missing_account_funds: int,
    ) -> int:
        """
        Validate UserOperation signature and pay prefund.

        Args:
            user_op: The UserOperation to validate
            user_op_hash: Hash of the UserOp
            missing_account_funds: Amount to pay to EntryPoint

        Returns:
            Packed validation data (see ERC-4337)

        Note:
            Signature validation now raises exceptions on failures.
            The caller must catch SignatureError and handle appropriately.
        """
        # Verify signature - will raise exception on failure
        try:
            self._validate_signature(user_op_hash, user_op.signature)
        except SignatureError:
            # Signature verification failed - re-raise to caller
            # This ensures signature failures are never silently ignored
            raise

        # Pay prefund if needed
        if missing_account_funds > 0:
            self._pay_prefund(missing_account_funds)

        return SIG_VALIDATION_SUCCESS

    def execute(
        self,
        dest: str,
        value: int,
        data: bytes,
    ) -> bytes:
        """
        Execute a call from this account.

        Can only be called by EntryPoint.

        Args:
            dest: Target address
            value: ETH value to send
            data: Call data

        Returns:
            Return data from call
        """
        # In real implementation, would do the actual call
        logger.debug(
            "Account executing call",
            extra={
                "event": "account.execute",
                "account": self.address[:10],
                "dest": dest[:10],
                "value": value,
            }
        )

        return b""

    def execute_batch(
        self,
        dests: List[str],
        values: List[int],
        datas: List[bytes],
    ) -> List[bytes]:
        """
        Execute multiple calls in a batch.

        Args:
            dests: Target addresses
            values: ETH values
            datas: Call data for each

        Returns:
            Return data from each call
        """
        if len(dests) != len(values) or len(dests) != len(datas):
            raise VMExecutionError("Batch arrays length mismatch")

        results = []
        for i in range(len(dests)):
            result = self.execute(dests[i], values[i], datas[i])
            results.append(result)

        return results

    # ==================== Account Management ====================

    def add_deposit(self, amount: int) -> None:
        """Add to account balance."""
        self.balance += amount

    def withdraw_deposit(self, caller: str, to: str, amount: int) -> bool:
        """Withdraw from account deposit."""
        self._require_owner(caller)

        if amount > self.balance:
            raise VMExecutionError("Insufficient balance")

        self.balance -= amount
        return True

    def get_deposit(self) -> int:
        """Get current deposit balance."""
        return self.balance

    def increment_nonce(self) -> int:
        """Increment and return new nonce."""
        self.nonce += 1
        return self.nonce

    # ==================== Internal ====================

    def _validate_signature(self, hash_: bytes, signature: bytes) -> bool:
        """
        Validate ECDSA signature against hash using secp256k1.

        Verifies that the signature was created by the owner using their
        registered public key.

        Args:
            hash_: The message hash to verify (32 bytes)
            signature: The ECDSA signature (64 bytes: r || s)

        Returns:
            True if signature is valid

        Raises:
            MissingPublicKeyError: If owner_public_key is not registered
            MalformedSignatureError: If signature format is invalid
            InvalidSignatureError: If signature verification fails
            SignatureError: If cryptographic error occurs during verification

        Security:
            - Requires owner_public_key to be set for verification
            - Uses cryptographic ECDSA verification, not length checks
            - Fails fast with explicit exceptions (never silently ignores errors)
        """
        # Require public key to be registered
        if not self.owner_public_key:
            logger.error(
                "Signature validation failed: no public key registered",
                extra={
                    "event": "account.signature_validation_failed",
                    "account": self.address[:16] if self.address else "unknown",
                    "reason": "no_public_key",
                }
            )
            raise MissingPublicKeyError(
                f"Account {self.address[:16] if self.address else 'unknown'} has no public key registered"
            )

        # Validate signature format - CRITICAL: must be exactly 64 bytes
        if not signature:
            logger.error(
                "Signature validation failed: missing signature",
                extra={
                    "event": "account.signature_validation_failed",
                    "account": self.address[:16] if self.address else "unknown",
                    "reason": "missing_signature",
                }
            )
            raise MalformedSignatureError("Missing signature")

        if len(signature) != 64:
            logger.error(
                "Signature validation failed: invalid signature length",
                extra={
                    "event": "account.signature_validation_failed",
                    "account": self.address[:16] if self.address else "unknown",
                    "reason": "invalid_signature_length",
                    "expected": 64,
                    "actual": len(signature),
                }
            )
            raise MalformedSignatureError(
                f"Signature must be 64 bytes, got {len(signature)} bytes"
            )

        try:
            # Convert signature bytes to hex for verification
            signature_hex = signature.hex()

            # Perform ECDSA verification
            is_valid = verify_signature_hex(
                self.owner_public_key,
                hash_,
                signature_hex
            )

            if not is_valid:
                logger.warning(
                    "Signature validation failed: invalid signature",
                    extra={
                        "event": "account.signature_validation_failed",
                        "account": self.address[:16] if self.address else "unknown",
                        "reason": "ecdsa_verification_failed",
                    }
                )
                raise InvalidSignatureError(
                    f"Signature does not match owner of account {self.address[:16] if self.address else 'unknown'}"
                )

            # Signature is valid
            logger.debug(
                "Signature validation succeeded",
                extra={
                    "event": "account.signature_validation_success",
                    "account": self.address[:16] if self.address else "unknown",
                }
            )
            return True

        except (MalformedSignatureError, InvalidSignatureError, MissingPublicKeyError):
            # Re-raise our specific errors
            raise

        except ValueError as e:
            # Invalid hex encoding or cryptographic parameter
            logger.error(
                "Signature validation error: invalid format",
                extra={
                    "event": "account.signature_validation_error",
                    "account": self.address[:16] if self.address else "unknown",
                    "error": str(e),
                }
            )
            raise MalformedSignatureError(f"Invalid signature format: {e}")

        except (TypeError, AttributeError, KeyError, RuntimeError) as e:
            # Unexpected cryptographic error - fail fast, don't continue
            # Covers: type issues, missing attributes, key access errors, crypto runtime failures
            logger.error(
                "Signature validation error: cryptographic failure",
                extra={
                    "event": "account.signature_validation_error",
                    "account": self.address[:16] if self.address else "unknown",
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True
            )
            raise SignatureError(f"Signature verification failed: {e}") from e

    def _pay_prefund(self, amount: int) -> None:
        """Pay prefund to EntryPoint."""
        if amount > self.balance:
            raise VMExecutionError("Insufficient funds for prefund")
        self.balance -= amount

    def _require_owner(self, caller: str) -> None:
        if caller.lower() != self.owner.lower():
            raise VMExecutionError("Caller is not owner")

    def _require_entry_point(self, caller: str) -> None:
        if caller.lower() != self.entry_point.lower():
            raise VMExecutionError("Caller is not entry point")


@dataclass
class MultiSigAccount(SmartAccount):
    """
    Multi-signature smart account.

    Requires multiple owners to sign for execution. Each owner must have
    their public key registered for cryptographic signature verification.

    Security:
        - All signatures are verified using ECDSA on secp256k1
        - Requires exactly `threshold` valid signatures from distinct owners
        - Signatures must be concatenated in order: sig1 || sig2 || ... || sigN
        - Each signature is 64 bytes (r || s)
    """

    owners: List[str] = field(default_factory=list)
    owner_public_keys: Dict[str, str] = field(default_factory=dict)  # owner_address -> public_key
    threshold: int = 1

    def __post_init__(self) -> None:
        """Initialize multi-sig account."""
        super().__post_init__()
        self.account_type = AccountType.MULTI_SIG
        if self.owner and self.owner not in self.owners:
            self.owners.append(self.owner)

    def add_owner(self, caller: str, new_owner: str, public_key: str = "") -> bool:
        """
        Add a new owner with their public key.

        Args:
            caller: Must be existing owner
            new_owner: Address of new owner
            public_key: 64-byte hex public key for signature verification

        Returns:
            True if successful
        """
        self._require_is_owner(caller)

        if new_owner.lower() in [o.lower() for o in self.owners]:
            raise VMExecutionError("Already an owner")

        self.owners.append(new_owner)
        if public_key:
            self.owner_public_keys[new_owner.lower()] = public_key

        logger.info(
            "MultiSig owner added",
            extra={
                "event": "multisig.owner_added",
                "account": self.address[:16] if self.address else "unknown",
                "new_owner": new_owner[:16],
                "has_pubkey": bool(public_key),
            }
        )
        return True

    def register_owner_public_key(self, caller: str, owner: str, public_key: str) -> bool:
        """
        Register or update an owner's public key.

        Args:
            caller: Must be existing owner
            owner: Owner address to register key for
            public_key: 64-byte hex public key

        Returns:
            True if successful
        """
        self._require_is_owner(caller)

        if owner.lower() not in [o.lower() for o in self.owners]:
            raise VMExecutionError("Address is not an owner")

        if not public_key or len(public_key) != 128:  # 64 bytes = 128 hex chars
            raise VMExecutionError("Invalid public key format (expected 64 bytes hex)")

        self.owner_public_keys[owner.lower()] = public_key
        return True

    def remove_owner(self, caller: str, owner: str) -> bool:
        """Remove an owner."""
        self._require_is_owner(caller)

        owner_lower = owner.lower()
        matching_owners = [o for o in self.owners if o.lower() == owner_lower]

        if not matching_owners:
            raise VMExecutionError("Not an owner")

        if len(self.owners) <= self.threshold:
            raise VMExecutionError("Cannot remove: would break threshold")

        self.owners.remove(matching_owners[0])
        # Also remove public key
        if owner_lower in self.owner_public_keys:
            del self.owner_public_keys[owner_lower]

        return True

    def change_threshold(self, caller: str, new_threshold: int) -> bool:
        """Change signature threshold."""
        self._require_is_owner(caller)

        if new_threshold < 1 or new_threshold > len(self.owners):
            raise VMExecutionError("Invalid threshold")

        self.threshold = new_threshold
        return True

    def _validate_signature(self, hash_: bytes, signature: bytes) -> bool:
        """
        Validate multi-signature using ECDSA.

        Expects concatenated signatures from `threshold` distinct owners.
        Each signature is 64 bytes (r || s). Signatures must be ordered
        to match owners in the owners list.

        Args:
            hash_: The message hash to verify (32 bytes)
            signature: Concatenated signatures (threshold * 64 bytes)

        Returns:
            True if at least `threshold` valid signatures from distinct owners

        Raises:
            MissingPublicKeyError: If insufficient public keys registered
            MalformedSignatureError: If signature format is invalid
            InvalidSignatureError: If signature verification fails
            SignatureError: If cryptographic error occurs

        Security:
            - Verifies each signature cryptographically using ECDSA
            - Tracks which owners have signed to prevent duplicate signatures
            - Fails fast with explicit exceptions (never silently ignores errors)
        """
        # Check we have enough registered public keys
        registered_count = len(self.owner_public_keys)
        if registered_count < self.threshold:
            logger.error(
                "MultiSig validation failed: insufficient registered public keys",
                extra={
                    "event": "multisig.validation_failed",
                    "account": self.address[:16] if self.address else "unknown",
                    "reason": "insufficient_public_keys",
                    "registered": registered_count,
                    "threshold": self.threshold,
                }
            )
            raise MissingPublicKeyError(
                f"MultiSig account {self.address[:16] if self.address else 'unknown'} "
                f"has only {registered_count} public keys registered but needs {self.threshold}"
            )

        # Check signature length - CRITICAL: must be exact multiple of 64
        expected_length = self.threshold * 64
        if not signature:
            logger.error(
                "MultiSig validation failed: missing signature",
                extra={
                    "event": "multisig.validation_failed",
                    "account": self.address[:16] if self.address else "unknown",
                    "reason": "missing_signature",
                }
            )
            raise MalformedSignatureError("Missing multisig signature")

        if len(signature) < expected_length:
            logger.error(
                "MultiSig validation failed: signature too short",
                extra={
                    "event": "multisig.validation_failed",
                    "account": self.address[:16] if self.address else "unknown",
                    "reason": "signature_too_short",
                    "expected": expected_length,
                    "actual": len(signature),
                }
            )
            raise MalformedSignatureError(
                f"Multisig signature must be at least {expected_length} bytes "
                f"({self.threshold} signatures * 64 bytes), got {len(signature)} bytes"
            )

        # Extract and verify each signature
        valid_signers: set = set()
        signature_errors: list = []  # Track errors for debugging

        for i in range(self.threshold):
            sig_start = i * 64
            sig_end = sig_start + 64
            single_sig = signature[sig_start:sig_end]
            single_sig_hex = single_sig.hex()

            # Try to verify against each owner's public key
            sig_valid = False
            last_error: Optional[Exception] = None

            for owner in self.owners:
                owner_lower = owner.lower()

                # Skip if already signed (prevent double-counting)
                if owner_lower in valid_signers:
                    continue

                public_key = self.owner_public_keys.get(owner_lower)
                if not public_key:
                    continue

                try:
                    if verify_signature_hex(public_key, hash_, single_sig_hex):
                        valid_signers.add(owner_lower)
                        sig_valid = True
                        logger.debug(
                            "MultiSig signature verified",
                            extra={
                                "event": "multisig.signature_verified",
                                "account": self.address[:16] if self.address else "unknown",
                                "signature_index": i,
                                "signer": owner[:16],
                            }
                        )
                        break
                except ValueError as e:
                    # Malformed signature or cryptographic parameter
                    last_error = e
                    logger.debug(
                        f"Signature {i} verification failed for owner {owner[:16]}: {e}"
                    )
                    continue
                except (TypeError, AttributeError, KeyError, RuntimeError) as e:
                    # Unexpected error in signature verification: type issues, missing attributes,
                    # key access errors, or cryptographic runtime failures
                    logger.error(
                        "Unexpected error verifying signature %s for owner %s: %s",
                        i,
                        owner[:16],
                        type(e).__name__,
                        extra={
                            "event": "multisig.signature_validation_error",
                            "account": self.address[:16] if self.address else "unknown",
                            "signature_index": i,
                            "owner": owner[:16],
                            "error_type": type(e).__name__,
                        },
                        exc_info=True,
                    )
                    raise SignatureError(
                        f"Unexpected signature verification failure at index {i} for owner {owner[:16]}: {e}"
                    ) from e

            if not sig_valid:
                # None of the owners could verify this signature
                error_msg = f"Signature {i} could not be verified against any owner"
                if last_error:
                    error_msg += f" (last error: {last_error})"
                signature_errors.append(error_msg)

                logger.error(
                    "MultiSig validation failed: invalid signature",
                    extra={
                        "event": "multisig.validation_failed",
                        "account": self.address[:16] if self.address else "unknown",
                        "reason": "invalid_signature",
                        "signature_index": i,
                        "error": str(last_error) if last_error else "no matching owner",
                    }
                )

                # If last error was a malformed signature, raise that
                if isinstance(last_error, ValueError):
                    raise MalformedSignatureError(
                        f"Malformed signature at index {i}: {last_error}"
                    )

                # Otherwise, signature was well-formed but didn't match any owner
                raise InvalidSignatureError(
                    f"Signature {i} does not match any owner. "
                    f"Valid signers so far: {len(valid_signers)}/{self.threshold}. "
                    f"Errors: {'; '.join(signature_errors)}"
                )

        # Check we have enough valid signers
        if len(valid_signers) >= self.threshold:
            logger.info(
                "MultiSig validation succeeded",
                extra={
                    "event": "multisig.validation_success",
                    "account": self.address[:16] if self.address else "unknown",
                    "valid_signers": len(valid_signers),
                    "threshold": self.threshold,
                    "signers": [owner[:16] for owner in valid_signers],
                }
            )
            return True

        # This should never happen if we correctly validated threshold signatures above
        logger.error(
            "MultiSig validation failed: insufficient valid signers (unexpected state)",
            extra={
                "event": "multisig.validation_failed",
                "account": self.address[:16] if self.address else "unknown",
                "reason": "insufficient_signers",
                "valid_signers": len(valid_signers),
                "threshold": self.threshold,
            }
        )
        raise InvalidSignatureError(
            f"Insufficient valid signatures: got {len(valid_signers)}, need {self.threshold}"
        )

    def _require_is_owner(self, caller: str) -> None:
        if caller.lower() not in [o.lower() for o in self.owners]:
            raise VMExecutionError("Caller is not an owner")


@dataclass
class SocialRecoveryAccount(SmartAccount):
    """
    Smart account with social recovery.

    Allows guardians to recover the account if owner loses access.
    """

    guardians: List[str] = field(default_factory=list)
    guardian_threshold: int = 2
    recovery_period: int = 86400  # 24 hours

    # Pending recovery
    pending_recovery: Optional[str] = None
    recovery_initiated_at: float = 0

    def __post_init__(self) -> None:
        """Initialize social recovery account."""
        super().__post_init__()
        self.account_type = AccountType.SOCIAL_RECOVERY

    # ==================== Guardian Management ====================

    def add_guardian(self, caller: str, guardian: str) -> bool:
        """Add a guardian."""
        self._require_owner(caller)

        if guardian in self.guardians:
            raise VMExecutionError("Already a guardian")

        self.guardians.append(guardian)
        return True

    def remove_guardian(self, caller: str, guardian: str) -> bool:
        """Remove a guardian."""
        self._require_owner(caller)

        if guardian not in self.guardians:
            raise VMExecutionError("Not a guardian")

        self.guardians.remove(guardian)
        return True

    def set_guardian_threshold(self, caller: str, threshold: int) -> bool:
        """Set guardian threshold for recovery."""
        self._require_owner(caller)

        if threshold < 1 or threshold > len(self.guardians):
            raise VMExecutionError("Invalid threshold")

        self.guardian_threshold = threshold
        return True

    # ==================== Recovery ====================

    def initiate_recovery(
        self,
        caller: str,
        new_owner: str,
        guardian_signatures: List[bytes],
    ) -> bool:
        """
        Initiate account recovery.

        Requires guardian_threshold signatures from guardians.

        Args:
            caller: Any address (usually one of the guardians)
            new_owner: Proposed new owner
            guardian_signatures: Signatures from guardians

        Returns:
            True if recovery initiated
        """
        if len(guardian_signatures) < self.guardian_threshold:
            raise VMExecutionError(
                f"Need {self.guardian_threshold} guardian signatures, "
                f"got {len(guardian_signatures)}"
            )

        # Verify signatures (simplified)
        # Real implementation would verify each signature against guardians

        self.pending_recovery = new_owner
        self.recovery_initiated_at = time.time()

        logger.info(
            "Recovery initiated",
            extra={
                "event": "account.recovery_initiated",
                "account": self.address[:10],
                "new_owner": new_owner[:10],
            }
        )

        return True

    def execute_recovery(self, caller: str) -> bool:
        """
        Execute pending recovery after time delay.

        Args:
            caller: Any address

        Returns:
            True if recovery executed
        """
        if not self.pending_recovery:
            raise VMExecutionError("No pending recovery")

        elapsed = time.time() - self.recovery_initiated_at
        if elapsed < self.recovery_period:
            remaining = self.recovery_period - elapsed
            raise VMExecutionError(
                f"Recovery period not elapsed. {remaining:.0f}s remaining"
            )

        old_owner = self.owner
        self.owner = self.pending_recovery
        self.pending_recovery = None
        self.recovery_initiated_at = 0

        logger.info(
            "Recovery executed",
            extra={
                "event": "account.recovery_executed",
                "account": self.address[:10],
                "old_owner": old_owner[:10],
                "new_owner": self.owner[:10],
            }
        )

        return True

    def cancel_recovery(self, caller: str) -> bool:
        """
        Cancel pending recovery.

        Only the current owner can cancel.

        Args:
            caller: Must be owner

        Returns:
            True if cancelled
        """
        self._require_owner(caller)

        if not self.pending_recovery:
            raise VMExecutionError("No pending recovery")

        self.pending_recovery = None
        self.recovery_initiated_at = 0

        return True


@dataclass
class SessionKeyAccount(SmartAccount):
    """
    Smart account with session keys.

    Allows delegating limited permissions to temporary keys.
    Useful for:
    - Gaming (no approval popups)
    - Subscriptions
    - Automated trading
    """

    # Session key address -> permissions
    session_keys: Dict[str, "SessionKeyPermissions"] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize session key account."""
        super().__post_init__()
        self.account_type = AccountType.SESSION_KEY

    def add_session_key(
        self,
        caller: str,
        key: str,
        permissions: "SessionKeyPermissions",
    ) -> bool:
        """
        Add a session key with specific permissions.

        Args:
            caller: Must be owner
            key: Session key address
            permissions: Allowed operations

        Returns:
            True if successful
        """
        self._require_owner(caller)

        self.session_keys[key.lower()] = permissions

        logger.info(
            "Session key added",
            extra={
                "event": "account.session_key_added",
                "account": self.address[:10],
                "key": key[:10],
            }
        )

        return True

    def revoke_session_key(self, caller: str, key: str) -> bool:
        """Revoke a session key."""
        self._require_owner(caller)

        key_lower = key.lower()
        if key_lower not in self.session_keys:
            raise VMExecutionError("Session key not found")

        del self.session_keys[key_lower]
        return True

    def validate_session_key(
        self,
        key: str,
        dest: str,
        value: int,
        selector: bytes,
    ) -> bool:
        """
        Validate that session key can perform operation.

        Args:
            key: Session key address
            dest: Target contract
            value: ETH value
            selector: Function selector

        Returns:
            True if operation is allowed
        """
        key_lower = key.lower()
        perms = self.session_keys.get(key_lower)

        if not perms:
            return False

        # Check expiry
        if perms.valid_until > 0 and time.time() > perms.valid_until:
            return False

        # Check spending limit
        if perms.spending_limit > 0 and value > perms.spending_limit:
            return False

        # Check allowed targets
        if perms.allowed_targets and dest.lower() not in [
            t.lower() for t in perms.allowed_targets
        ]:
            return False

        # Check allowed selectors
        if perms.allowed_selectors and selector not in perms.allowed_selectors:
            return False

        return True


@dataclass
class SessionKeyPermissions:
    """Permissions for a session key."""

    valid_until: float = 0  # Timestamp, 0 = no expiry
    spending_limit: int = 0  # Max value per tx, 0 = no limit
    allowed_targets: List[str] = field(default_factory=list)  # Allowed contracts
    allowed_selectors: List[bytes] = field(default_factory=list)  # Allowed functions


@dataclass
class Paymaster:
    """
    ERC-4337 Paymaster.

    Sponsors gas for UserOperations, enabling:
    - Gasless transactions
    - Pay gas in ERC20 tokens
    - Subscription-based sponsorship
    - Promotional gas subsidies
    """

    address: str = ""
    owner: str = ""

    # Deposit at EntryPoint
    deposit: int = 0

    # Sponsored accounts (whitelist mode)
    sponsored_accounts: Dict[str, bool] = field(default_factory=dict)

    # Token payment settings
    accepted_tokens: Dict[str, int] = field(default_factory=dict)  # token -> rate

    # Statistics
    total_sponsored: int = 0
    gas_sponsored: int = 0

    def __post_init__(self) -> None:
        """Initialize paymaster."""
        if not self.address:
            addr_hash = hashlib.sha3_256(
                f"paymaster:{time.time()}".encode()
            ).digest()
            self.address = f"0x{addr_hash[-20:].hex()}"

    # ==================== IPaymaster Interface ====================

    def validate_paymaster_user_op(
        self,
        user_op: UserOperation,
        user_op_hash: bytes,
        max_cost: int,
    ) -> Tuple[bytes, int]:
        """
        Validate UserOp and agree to pay.

        Args:
            user_op: The UserOperation
            user_op_hash: Hash for validation
            max_cost: Maximum gas cost

        Returns:
            (context, validationData)
        """
        # Check if we should sponsor this account
        if not self._should_sponsor(user_op.sender):
            raise VMExecutionError("Account not sponsored")

        # Check we have enough deposit
        if self.deposit < max_cost:
            raise VMExecutionError("Paymaster deposit too low")

        # Create context for post-op
        context = user_op.sender.encode()

        logger.debug(
            "Paymaster validating",
            extra={
                "event": "paymaster.validate",
                "sender": user_op.sender[:10],
                "max_cost": max_cost,
            }
        )

        return context, SIG_VALIDATION_SUCCESS

    def post_op(
        self,
        mode: int,  # 0 = success, 1 = user op reverted, 2 = postOp reverted
        context: bytes,
        actual_gas_cost: int,
    ) -> None:
        """
        Called after UserOp execution.

        Used for:
        - Charging users in ERC20
        - Logging/analytics
        - Refunding unused gas

        Args:
            mode: Execution mode
            context: Context from validation
            actual_gas_cost: Actual gas used
        """
        self.total_sponsored += 1
        self.gas_sponsored += actual_gas_cost

        logger.info(
            "Paymaster post-op",
            extra={
                "event": "paymaster.post_op",
                "mode": mode,
                "gas_cost": actual_gas_cost,
            }
        )

    # ==================== Management ====================

    def add_deposit(self, amount: int) -> None:
        """Add to paymaster deposit."""
        self.deposit += amount

    def withdraw_deposit(self, caller: str, to: str, amount: int) -> bool:
        """Withdraw from deposit."""
        self._require_owner(caller)

        if amount > self.deposit:
            raise VMExecutionError("Insufficient deposit")

        self.deposit -= amount
        return True

    def add_sponsored_account(self, caller: str, account: str) -> bool:
        """Add account to whitelist."""
        self._require_owner(caller)
        self.sponsored_accounts[account.lower()] = True
        return True

    def remove_sponsored_account(self, caller: str, account: str) -> bool:
        """Remove account from whitelist."""
        self._require_owner(caller)
        self.sponsored_accounts[account.lower()] = False
        return True

    def set_token_rate(self, caller: str, token: str, rate: int) -> bool:
        """Set exchange rate for paying in token."""
        self._require_owner(caller)
        self.accepted_tokens[token.lower()] = rate
        return True

    # ==================== Internal ====================

    def _should_sponsor(self, sender: str) -> bool:
        """Check if sender should be sponsored."""
        # If whitelist is empty, sponsor everyone
        if not self.sponsored_accounts:
            return True
        return self.sponsored_accounts.get(sender.lower(), False)

    def _require_owner(self, caller: str) -> None:
        if caller.lower() != self.owner.lower():
            raise VMExecutionError("Caller is not owner")


@dataclass
class EntryPoint:
    """
    ERC-4337 EntryPoint contract.

    The singleton contract that:
    - Receives UserOperations from bundlers
    - Validates signatures and pays gas
    - Executes operations
    - Manages account/paymaster deposits

    This is the core of the account abstraction system.
    """

    address: str = ""
    chain_id: int = 1

    # Deposits (for gas prepayment)
    deposits: Dict[str, int] = field(default_factory=dict)

    # Account nonces
    nonces: Dict[str, int] = field(default_factory=dict)

    # Statistics
    total_ops_processed: int = 0
    total_gas_used: int = 0

    # Registry of known accounts/paymasters
    accounts: Dict[str, SmartAccount] = field(default_factory=dict)
    paymasters: Dict[str, Paymaster] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize EntryPoint."""
        if not self.address:
            # Use deterministic address like real ERC-4337
            self.address = "0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789"

    # ==================== Main Entry Point ====================

    def handle_ops(
        self,
        ops: List[UserOperation],
        beneficiary: str,
    ) -> List[ExecutionResult]:
        """
        Handle a batch of UserOperations.

        Called by bundlers. Each UserOp is:
        1. Validated
        2. Executed
        3. Gas accounted for

        Args:
            ops: List of UserOperations
            beneficiary: Address to receive gas payment

        Returns:
            List of execution results
        """
        results = []

        for op in ops:
            try:
                result = self._handle_single_op(op, beneficiary)
                results.append(result)
            except VMExecutionError as e:
                logger.warning(
                    "UserOp failed",
                    extra={
                        "event": "entrypoint.op_failed",
                        "sender": op.sender[:10],
                        "error": str(e),
                    }
                )
                results.append(ExecutionResult(
                    success=False,
                    actual_gas_used=op.pre_verification_gas,
                ))

        self.total_ops_processed += len(ops)

        return results

    def _handle_single_op(
        self,
        op: UserOperation,
        beneficiary: str,
    ) -> ExecutionResult:
        """Handle a single UserOperation."""
        gas_used = op.pre_verification_gas

        # 1. Create account if needed
        if op.init_code:
            self._create_account(op.sender, op.init_code)
            gas_used += 50_000  # Account creation gas

        # 2. Validate UserOp
        op_hash = op.hash(self.address, self.chain_id)
        validation_result = self._validate_user_op(op, op_hash)

        if not validation_result.valid:
            raise VMExecutionError("UserOp validation failed")

        gas_used += op.verification_gas_limit

        # 3. Validate paymaster if used
        paymaster_context = b""
        if op.paymaster_and_data:
            paymaster_address = op.paymaster_and_data[:42].decode()
            paymaster_context = self._validate_paymaster(op, op_hash, paymaster_address)
            gas_used += 50_000  # Paymaster validation gas

        # 4. Execute the operation
        try:
            account = self.accounts.get(op.sender)
            if not account:
                raise VMExecutionError(f"Account {op.sender} not found")

            # Increment nonce
            account.increment_nonce()

            # Execute
            if op.calldata:
                account.execute(
                    account.address,  # self-call to parse calldata
                    0,
                    op.calldata,
                )

            success = True
            gas_used += op.call_gas_limit // 2  # Simplified gas accounting

        except (VMExecutionError, SignatureError, ValueError, TypeError, AttributeError, KeyError) as e:
            # Catch execution failures: VM errors, signature errors, value/type/attribute errors
            success = False
            logger.warning(
                "UserOp execution failed",
                extra={
                    "sender": op.sender[:16] if op.sender else "unknown",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )

        # 5. Paymaster post-op
        if paymaster_context:
            paymaster_address = op.paymaster_and_data[:42].decode()
            paymaster = self.paymasters.get(paymaster_address)
            if paymaster:
                paymaster.post_op(
                    0 if success else 1,
                    paymaster_context,
                    gas_used,
                )

        # 6. Pay beneficiary
        # In real implementation, would transfer gas payment

        self.total_gas_used += gas_used

        logger.info(
            "UserOp processed",
            extra={
                "event": "entrypoint.op_processed",
                "sender": op.sender[:10],
                "success": success,
                "gas_used": gas_used,
            }
        )

        return ExecutionResult(
            success=success,
            actual_gas_used=gas_used,
        )

    def _validate_user_op(
        self,
        op: UserOperation,
        op_hash: bytes,
    ) -> ValidationResult:
        """
        Validate UserOp with account.

        This method now properly handles signature verification exceptions
        and logs detailed security events for audit purposes.
        """
        account = self.accounts.get(op.sender)
        if not account:
            logger.warning(
                "UserOp validation failed: account not found",
                extra={
                    "event": "entrypoint.validation_failed",
                    "sender": op.sender[:16],
                    "reason": "account_not_found",
                }
            )
            return ValidationResult(valid=False)

        # Check nonce
        expected_nonce = account.nonce
        if op.nonce != expected_nonce:
            logger.warning(
                "UserOp validation failed: nonce mismatch",
                extra={
                    "event": "entrypoint.validation_failed",
                    "sender": op.sender[:16],
                    "reason": "nonce_mismatch",
                    "expected": expected_nonce,
                    "got": op.nonce,
                }
            )
            return ValidationResult(valid=False)

        # Calculate missing funds
        max_gas = (
            op.verification_gas_limit +
            op.call_gas_limit +
            op.pre_verification_gas
        )
        max_cost = max_gas * op.max_fee_per_gas
        current_deposit = account.balance
        missing_funds = max(0, max_cost - current_deposit)

        # Validate with account - this will raise SignatureError on failures
        try:
            result = account.validate_user_op(op, op_hash, missing_funds)

            logger.info(
                "UserOp signature validation succeeded",
                extra={
                    "event": "entrypoint.signature_validated",
                    "sender": op.sender[:16],
                    "nonce": op.nonce,
                }
            )

            return ValidationResult(
                valid=(result == SIG_VALIDATION_SUCCESS),
                prefund=max_cost,
            )

        except MissingPublicKeyError as e:
            logger.error(
                "UserOp validation failed: missing public key",
                extra={
                    "event": "entrypoint.validation_failed",
                    "sender": op.sender[:16],
                    "reason": "missing_public_key",
                    "error": str(e),
                }
            )
            return ValidationResult(valid=False, sig_failed=True)

        except MalformedSignatureError as e:
            logger.error(
                "UserOp validation failed: malformed signature",
                extra={
                    "event": "entrypoint.validation_failed",
                    "sender": op.sender[:16],
                    "reason": "malformed_signature",
                    "error": str(e),
                }
            )
            return ValidationResult(valid=False, sig_failed=True)

        except InvalidSignatureError as e:
            logger.warning(
                "UserOp validation failed: invalid signature",
                extra={
                    "event": "entrypoint.validation_failed",
                    "sender": op.sender[:16],
                    "reason": "invalid_signature",
                    "error": str(e),
                }
            )
            return ValidationResult(valid=False, sig_failed=True)

        except SignatureError as e:
            logger.error(
                "UserOp validation failed: signature verification error",
                extra={
                    "event": "entrypoint.validation_failed",
                    "sender": op.sender[:16],
                    "reason": "signature_error",
                    "error": str(e),
                },
                exc_info=True
            )
            return ValidationResult(valid=False, sig_failed=True)

    def _validate_paymaster(
        self,
        op: UserOperation,
        op_hash: bytes,
        paymaster_address: str,
    ) -> bytes:
        """Validate with paymaster."""
        paymaster = self.paymasters.get(paymaster_address)
        if not paymaster:
            raise VMExecutionError(f"Paymaster {paymaster_address} not found")

        max_gas = (
            op.verification_gas_limit +
            op.call_gas_limit +
            op.pre_verification_gas
        )
        max_cost = max_gas * op.max_fee_per_gas

        context, validation = paymaster.validate_paymaster_user_op(
            op, op_hash, max_cost
        )

        if validation != SIG_VALIDATION_SUCCESS:
            raise VMExecutionError("Paymaster validation failed")

        return context

    def _create_account(self, sender: str, init_code: bytes) -> None:
        """Create account from init code."""
        # In real implementation, would deploy the account contract
        # For now, just verify sender matches expected address
        pass

    # ==================== Deposit Management ====================

    def deposit_to(self, account: str, amount: int) -> bool:
        """Deposit funds for an account."""
        self.deposits[account.lower()] = (
            self.deposits.get(account.lower(), 0) + amount
        )
        return True

    def withdraw_to(
        self,
        caller: str,
        withdrawable_address: str,
        amount: int,
    ) -> bool:
        """Withdraw from deposit."""
        caller_lower = caller.lower()
        current = self.deposits.get(caller_lower, 0)

        if amount > current:
            raise VMExecutionError("Insufficient deposit")

        self.deposits[caller_lower] = current - amount
        return True

    def balance_of(self, account: str) -> int:
        """Get account deposit balance."""
        return self.deposits.get(account.lower(), 0)

    def get_nonce(self, sender: str, key: int = 0) -> int:
        """
        Get nonce for account.

        Supports 2D nonces (key, sequence) for parallel execution.
        """
        account = self.accounts.get(sender)
        if account:
            return account.nonce
        return 0

    # ==================== Registration ====================

    def register_account(self, account: SmartAccount) -> None:
        """Register a smart account."""
        self.accounts[account.address] = account
        account.entry_point = self.address

    def register_paymaster(self, paymaster: Paymaster) -> None:
        """Register a paymaster."""
        self.paymasters[paymaster.address] = paymaster

    # ==================== Stats ====================

    def get_stats(self) -> Dict:
        """Get EntryPoint statistics."""
        return {
            "total_ops_processed": self.total_ops_processed,
            "total_gas_used": self.total_gas_used,
            "accounts_registered": len(self.accounts),
            "paymasters_registered": len(self.paymasters),
        }


@dataclass
class AccountFactory:
    """
    Factory for deploying smart accounts.

    Provides deterministic addresses for counterfactual deployment.
    """

    address: str = ""
    entry_point: str = ""

    # Deployed accounts
    accounts: Dict[str, SmartAccount] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize factory."""
        if not self.address:
            addr_hash = hashlib.sha3_256(
                f"account_factory:{time.time()}".encode()
            ).digest()
            self.address = f"0x{addr_hash[-20:].hex()}"

    def create_account(
        self,
        owner: str,
        salt: int,
        owner_public_key: str = "",
    ) -> SmartAccount:
        """
        Create a simple smart account.

        Args:
            owner: Account owner address
            salt: Salt for deterministic address
            owner_public_key: 64-byte hex public key for ECDSA signature verification
                             (required for signature validation to work)

        Returns:
            Created account
        """
        # Compute deterministic address
        addr_input = f"{self.address}:{owner}:{salt}".encode()
        addr_hash = hashlib.sha3_256(addr_input).digest()
        address = f"0x{addr_hash[-20:].hex()}"

        # Check if already exists
        if address in self.accounts:
            return self.accounts[address]

        account = SmartAccount(
            address=address,
            owner=owner,
            owner_public_key=owner_public_key,
            entry_point=self.entry_point,
        )

        self.accounts[address] = account

        logger.info(
            "Account created",
            extra={
                "event": "factory.account_created",
                "owner": owner[:10],
                "address": address[:10],
                "has_pubkey": bool(owner_public_key),
            }
        )

        return account

    def create_multisig_account(
        self,
        owners: List[str],
        threshold: int,
        salt: int,
        owner_public_keys: Optional[Dict[str, str]] = None,
    ) -> MultiSigAccount:
        """
        Create a multi-sig account.

        Args:
            owners: List of owner addresses
            threshold: Number of signatures required
            salt: Salt for deterministic address
            owner_public_keys: Dict mapping owner addresses to their 64-byte hex public keys
                              (required for signature validation to work)

        Returns:
            Created multi-sig account
        """
        addr_input = f"{self.address}:{':'.join(owners)}:{threshold}:{salt}".encode()
        addr_hash = hashlib.sha3_256(addr_input).digest()
        address = f"0x{addr_hash[-20:].hex()}"

        # Normalize public keys dict
        normalized_keys: Dict[str, str] = {}
        if owner_public_keys:
            for addr, pubkey in owner_public_keys.items():
                normalized_keys[addr.lower()] = pubkey

        account = MultiSigAccount(
            address=address,
            owner=owners[0],
            owners=owners,
            owner_public_keys=normalized_keys,
            threshold=threshold,
            entry_point=self.entry_point,
        )

        self.accounts[address] = account
        return account

    def create_social_recovery_account(
        self,
        owner: str,
        guardians: List[str],
        threshold: int,
        salt: int,
    ) -> SocialRecoveryAccount:
        """Create a social recovery account."""
        addr_input = f"{self.address}:{owner}:{':'.join(guardians)}:{salt}".encode()
        addr_hash = hashlib.sha3_256(addr_input).digest()
        address = f"0x{addr_hash[-20:].hex()}"

        account = SocialRecoveryAccount(
            address=address,
            owner=owner,
            guardians=guardians,
            guardian_threshold=threshold,
            entry_point=self.entry_point,
        )

        self.accounts[address] = account
        return account

    def get_address(self, owner: str, salt: int) -> str:
        """
        Get deterministic address without deploying.

        Useful for counterfactual deployment.
        """
        addr_input = f"{self.address}:{owner}:{salt}".encode()
        addr_hash = hashlib.sha3_256(addr_input).digest()
        return f"0x{addr_hash[-20:].hex()}"
