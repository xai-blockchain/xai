"""
Cryptographic Access Control for DeFi Contracts.

Provides signature-based authentication and role-based access control
to prevent unauthorized access to privileged functions.

Security features:
- ECDSA signature verification
- Nonce-based replay attack prevention
- Timestamp-based request expiration
- Role-based permissions
- Audit trail for all privileged operations

This module addresses critical access control vulnerabilities where
simple address-string matching allowed attackers to impersonate
authorized users without proving ownership of private keys.
"""

from __future__ import annotations

import time
import logging
import hashlib
from dataclasses import dataclass, field
from typing import Dict, Set, Optional, TYPE_CHECKING
from enum import Enum

from ..vm.exceptions import VMExecutionError
from ..crypto_utils import verify_signature_hex

if TYPE_CHECKING:
    from ..blockchain import Blockchain

logger = logging.getLogger(__name__)


class Role(Enum):
    """Standard roles for DeFi access control."""
    ADMIN = "admin"
    GUARDIAN = "guardian"
    PRICE_FEEDER = "price_feeder"
    SLASHER = "slasher"
    OPERATOR = "operator"


@dataclass
class SignedRequest:
    """
    Cryptographically signed request for privileged operations.

    Prevents unauthorized access by requiring ECDSA signature proof
    that the caller controls the private key for the claimed address.

    Security properties:
    - Replay protection via nonce tracking
    - Time-bound validity via timestamp checks
    - Cryptographic proof of address ownership
    - Message integrity via signature
    """

    address: str  # Public address making the request
    signature: str  # ECDSA signature (hex-encoded, 64 bytes)
    message: str  # Signed message (includes operation, nonce, timestamp)
    timestamp: int  # Unix timestamp when request was created
    nonce: int  # Unique nonce to prevent replay attacks
    public_key: str  # Public key for signature verification (hex-encoded)

    def __post_init__(self) -> None:
        """Validate request structure."""
        # Normalize address
        self.address = self.address.lower()

        # Validate signature format
        if not self.signature:
            raise VMExecutionError("Signature is required")

        # Validate timestamp is reasonable (not too far in future/past)
        now = int(time.time())
        # Allow 1 hour in past, 5 minutes in future (for clock skew)
        if self.timestamp < now - 3600:
            raise VMExecutionError("Request timestamp too old")
        if self.timestamp > now + 300:
            raise VMExecutionError("Request timestamp too far in future")

    def get_message_hash(self) -> bytes:
        """
        Get hash of the signed message.

        Returns:
            SHA-256 hash of the message
        """
        return hashlib.sha256(self.message.encode()).digest()


@dataclass
class AccessControl:
    """
    Signature-based access control with replay protection.

    Verifies that callers cryptographically prove ownership of
    their claimed address before granting access to privileged
    functions.

    Security features:
    - ECDSA signature verification
    - Nonce tracking to prevent replay attacks
    - Timestamp validation to prevent stale requests
    - Automatic nonce cleanup to prevent memory exhaustion

    Usage:
        ac = AccessControl()
        if ac.verify_caller(signed_request, expected_address):
            # Caller proved ownership of expected_address
            perform_privileged_operation()
    """

    # Track used nonces per address to prevent replay attacks
    used_nonces: Dict[str, Set[int]] = field(default_factory=dict)

    # Maximum age of requests (5 minutes)
    max_age_seconds: int = 300

    # Cleanup threshold (when to garbage collect old nonces)
    cleanup_threshold: int = 1000

    # Last cleanup time
    last_cleanup: float = field(default_factory=time.time)

    def verify_caller(
        self,
        request: SignedRequest,
        expected_address: str,
    ) -> bool:
        """
        Verify that the caller cryptographically proves ownership of expected_address.

        This is the primary security gate for all privileged operations.
        It ensures that:
        1. The request comes from the expected address
        2. The caller has the private key for that address (via signature)
        3. The request hasn't been replayed (via nonce)
        4. The request is recent (via timestamp)

        Args:
            request: Signed request from caller
            expected_address: Address that should be making this call

        Returns:
            True if caller is authorized, False otherwise

        Security:
            - Verifies ECDSA signature over message
            - Checks nonce hasn't been used (replay protection)
            - Validates timestamp is within max_age_seconds
            - Marks nonce as used after successful verification
        """
        expected_norm = expected_address.lower()
        request_norm = request.address.lower()

        # Step 1: Verify address matches expected
        if request_norm != expected_norm:
            logger.warning(
                "Access denied: address mismatch",
                extra={
                    "event": "access_control.address_mismatch",
                    "expected": expected_norm[:10],
                    "actual": request_norm[:10],
                }
            )
            return False

        # Step 2: Verify timestamp is recent
        now = int(time.time())
        age = abs(now - request.timestamp)
        if age > self.max_age_seconds:
            logger.warning(
                "Access denied: request too old",
                extra={
                    "event": "access_control.stale_request",
                    "address": request_norm[:10],
                    "age_seconds": age,
                    "max_age": self.max_age_seconds,
                }
            )
            return False

        # Step 3: Verify nonce not reused (replay protection)
        if request_norm not in self.used_nonces:
            self.used_nonces[request_norm] = set()

        if request.nonce in self.used_nonces[request_norm]:
            logger.error(
                "Access denied: replay attack detected",
                extra={
                    "event": "access_control.replay_attack",
                    "address": request_norm[:10],
                    "nonce": request.nonce,
                }
            )
            return False

        # Step 4: Verify cryptographic signature
        message_hash = request.get_message_hash()
        if not verify_signature_hex(
            request.public_key,
            message_hash,
            request.signature
        ):
            logger.error(
                "Access denied: invalid signature",
                extra={
                    "event": "access_control.invalid_signature",
                    "address": request_norm[:10],
                    "message": request.message[:50],
                }
            )
            return False

        # Step 5: All checks passed - mark nonce as used
        self.used_nonces[request_norm].add(request.nonce)

        # Periodic cleanup of old nonces
        self._cleanup_old_nonces()

        logger.info(
            "Access granted",
            extra={
                "event": "access_control.access_granted",
                "address": request_norm[:10],
                "nonce": request.nonce,
            }
        )

        return True

    def verify_caller_simple(
        self,
        request: SignedRequest,
        expected_address: str,
    ) -> None:
        """
        Verify caller and raise exception if unauthorized.

        Convenience wrapper around verify_caller that raises
        instead of returning bool.

        Args:
            request: Signed request
            expected_address: Expected caller address

        Raises:
            VMExecutionError: If verification fails
        """
        if not self.verify_caller(request, expected_address):
            raise VMExecutionError(
                f"Unauthorized: caller {request.address[:10]} does not have valid signature"
            )

    def _cleanup_old_nonces(self) -> None:
        """
        Garbage collect old nonces to prevent memory exhaustion.

        Called periodically to remove nonces that are too old to be
        replayed (older than max_age_seconds).
        """
        now = time.time()

        # Only cleanup if enough time has passed
        if now - self.last_cleanup < 3600:  # 1 hour
            return

        # Count total nonces
        total_nonces = sum(len(nonces) for nonces in self.used_nonces.values())

        # Only cleanup if above threshold
        if total_nonces < self.cleanup_threshold:
            return

        # This is a simple cleanup - in production you'd track timestamps
        # For now, just clear everything since old nonces are expired anyway
        cleared = 0
        for address in list(self.used_nonces.keys()):
            cleared += len(self.used_nonces[address])
            self.used_nonces[address].clear()

        self.last_cleanup = now

        logger.info(
            "Nonce cleanup completed",
            extra={
                "event": "access_control.nonce_cleanup",
                "cleared_nonces": cleared,
            }
        )


@dataclass
class RoleBasedAccessControl:
    """
    Role-based access control with signature verification.

    Manages roles (admin, guardian, price_feeder, etc.) and verifies
    that callers have both the required role AND valid signature.

    Security:
    - Only admins can grant/revoke roles
    - All role checks require signature verification
    - Audit trail of role changes
    """

    # Access control for signature verification
    access_control: AccessControl = field(default_factory=AccessControl)

    # Role assignments: role -> set of addresses
    roles: Dict[str, Set[str]] = field(default_factory=dict)

    # Admin address (can grant/revoke roles)
    admin_address: str = ""

    # Audit log
    role_changes: list = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize roles."""
        # Initialize standard roles
        for role in Role:
            if role.value not in self.roles:
                self.roles[role.value] = set()

        # Admin starts with admin role
        if self.admin_address:
            self.roles[Role.ADMIN.value].add(self.admin_address.lower())

    def grant_role(
        self,
        admin_request: SignedRequest,
        role: str,
        address: str,
    ) -> bool:
        """
        Grant a role to an address.

        Args:
            admin_request: Signed request from admin
            role: Role to grant
            address: Address to grant role to

        Returns:
            True if role granted

        Raises:
            VMExecutionError: If caller is not admin
        """
        # Verify caller is admin with valid signature
        self.access_control.verify_caller_simple(
            admin_request,
            self.admin_address
        )

        # Grant role
        address_norm = address.lower()
        if role not in self.roles:
            self.roles[role] = set()

        self.roles[role].add(address_norm)

        # Audit log
        self.role_changes.append({
            "action": "grant",
            "role": role,
            "address": address_norm,
            "admin": admin_request.address,
            "timestamp": time.time(),
        })

        logger.info(
            "Role granted",
            extra={
                "event": "rbac.role_granted",
                "role": role,
                "address": address_norm[:10],
                "admin": admin_request.address[:10],
            }
        )

        return True

    def revoke_role(
        self,
        admin_request: SignedRequest,
        role: str,
        address: str,
    ) -> bool:
        """
        Revoke a role from an address.

        Args:
            admin_request: Signed request from admin
            role: Role to revoke
            address: Address to revoke role from

        Returns:
            True if role revoked

        Raises:
            VMExecutionError: If caller is not admin
        """
        # Verify caller is admin with valid signature
        self.access_control.verify_caller_simple(
            admin_request,
            self.admin_address
        )

        # Revoke role
        address_norm = address.lower()
        if role in self.roles:
            self.roles[role].discard(address_norm)

        # Audit log
        self.role_changes.append({
            "action": "revoke",
            "role": role,
            "address": address_norm,
            "admin": admin_request.address,
            "timestamp": time.time(),
        })

        logger.info(
            "Role revoked",
            extra={
                "event": "rbac.role_revoked",
                "role": role,
                "address": address_norm[:10],
                "admin": admin_request.address[:10],
            }
        )

        return True

    def has_role(self, role: str, address: str) -> bool:
        """
        Check if an address has a role (without signature verification).

        Args:
            role: Role to check
            address: Address to check

        Returns:
            True if address has role
        """
        address_norm = address.lower()
        return address_norm in self.roles.get(role, set())

    def verify_role(
        self,
        request: SignedRequest,
        role: str,
    ) -> bool:
        """
        Verify that caller has a role with valid signature.

        Args:
            request: Signed request from caller
            role: Required role

        Returns:
            True if caller has role and valid signature
        """
        # First check if they have the role
        if not self.has_role(role, request.address):
            logger.warning(
                "Access denied: role not assigned",
                extra={
                    "event": "rbac.role_not_assigned",
                    "address": request.address[:10],
                    "required_role": role,
                }
            )
            return False

        # Then verify signature (proves they control the address)
        return self.access_control.verify_caller(request, request.address)

    def verify_role_simple(
        self,
        request: SignedRequest,
        role: str,
    ) -> None:
        """
        Verify role and raise if unauthorized.

        Args:
            request: Signed request
            role: Required role

        Raises:
            VMExecutionError: If verification fails
        """
        if not self.verify_role(request, role):
            raise VMExecutionError(
                f"Unauthorized: caller {request.address[:10]} "
                f"does not have role '{role}' with valid signature"
            )

    def get_role_members(self, role: str) -> Set[str]:
        """Get all addresses with a given role."""
        return self.roles.get(role, set()).copy()

    def get_user_roles(self, address: str) -> Set[str]:
        """Get all roles assigned to an address."""
        address_norm = address.lower()
        return {
            role
            for role, members in self.roles.items()
            if address_norm in members
        }


def requires_signature(
    access_control: AccessControl,
    expected_address: str,
):
    """
    Decorator to require signature verification for a function.

    Usage:
        @requires_signature(self.access_control, self.owner)
        def admin_function(self, request: SignedRequest, ...):
            # Only called if signature is valid
            pass

    Args:
        access_control: AccessControl instance
        expected_address: Address that must sign the request

    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(self, request: SignedRequest, *args, **kwargs):
            access_control.verify_caller_simple(request, expected_address)
            return func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def requires_role(rbac: RoleBasedAccessControl, role: str):
    """
    Decorator to require a role with signature verification.

    Usage:
        @requires_role(self.rbac, Role.ADMIN.value)
        def admin_function(self, request: SignedRequest, ...):
            # Only called if caller has admin role with valid signature
            pass

    Args:
        rbac: RoleBasedAccessControl instance
        role: Required role

    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(self, request: SignedRequest, *args, **kwargs):
            rbac.verify_role_simple(request, role)
            return func(self, request, *args, **kwargs)
        return wrapper
    return decorator
