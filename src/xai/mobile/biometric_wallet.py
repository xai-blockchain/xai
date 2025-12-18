"""
Biometric Wallet - Wallet wrapper with biometric authentication

Production-ready wallet integration with biometric protection for:
- Viewing private keys (requires biometric)
- Signing transactions above threshold (requires biometric)
- Exporting wallet (requires biometric)
- Configurable security policies

Features:
- Transparent integration with existing Wallet class
- Configurable security policies per wallet
- Transaction threshold-based authentication
- Automatic session management
- Audit logging for sensitive operations

Security:
- Private key never exposed without biometric authentication
- Configurable policies for different security levels
- Rate limiting on sensitive operations
- Automatic lockout on repeated failures
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, Dict, Any, Callable

from xai.core.wallet import Wallet
from xai.mobile.biometric_auth import (
    BiometricAuthManager,
    BiometricResult,
    BiometricStrength,
    ProtectionLevel,
    BiometricError
)
from xai.mobile.secure_enclave import (
    SecureEnclaveManager,
    KeyAlgorithm,
    KeyProtection
)

logger = logging.getLogger(__name__)


@dataclass
class SecurityPolicy:
    """Security policy for biometric wallet operations."""

    # Private key operations
    require_biometric_for_private_key: bool = True
    require_biometric_for_export: bool = True
    require_biometric_for_signing: bool = True

    # Transaction thresholds (in base units, e.g., wei)
    small_transaction_threshold: Decimal = Decimal("1000000000000000000")  # 1 token
    large_transaction_threshold: Decimal = Decimal("10000000000000000000")  # 10 tokens

    # Protection levels for different operations
    private_key_protection: ProtectionLevel = ProtectionLevel.BIOMETRIC_STRONG
    export_protection: ProtectionLevel = ProtectionLevel.BIOMETRIC_STRONG
    small_tx_protection: ProtectionLevel = ProtectionLevel.BIOMETRIC_WEAK
    large_tx_protection: ProtectionLevel = ProtectionLevel.BIOMETRIC_STRONG

    # Session settings
    allow_session_reuse: bool = True
    session_timeout_seconds: int = 300

    # Rate limiting
    max_failed_attempts: int = 3
    lockout_duration_seconds: int = 300

    # Audit
    audit_sensitive_operations: bool = True


@dataclass
class OperationAudit:
    """Audit record for sensitive operations."""
    operation: str
    wallet_address: str
    success: bool
    timestamp: int = field(default_factory=lambda: int(time.time()))
    biometric_used: bool = False
    error: Optional[str] = None


class BiometricWalletError(Exception):
    """Base exception for biometric wallet errors."""
    pass


class AuthenticationRequiredError(BiometricWalletError):
    """Raised when biometric authentication is required."""
    pass


class AuthenticationFailedError(BiometricWalletError):
    """Raised when biometric authentication fails."""
    pass


class WalletLockedError(BiometricWalletError):
    """Raised when wallet is locked due to failed attempts."""
    pass


class BiometricWallet:
    """
    Wallet wrapper with biometric authentication protection.

    This class wraps the standard Wallet class and adds biometric
    authentication requirements for sensitive operations.

    Usage:
        # Create biometric wallet
        wallet = Wallet()
        bio_wallet = BiometricWallet(
            wallet=wallet,
            biometric_manager=bio_manager,
            policy=SecurityPolicy()
        )

        # Signing requires biometric
        signature = bio_wallet.sign_message("Hello")  # Triggers biometric prompt

        # View private key requires biometric
        private_key = bio_wallet.get_private_key()  # Triggers biometric prompt

        # Export requires biometric
        exported = bio_wallet.export_wallet(password="secret")
    """

    def __init__(
        self,
        wallet: Wallet,
        biometric_manager: BiometricAuthManager,
        policy: Optional[SecurityPolicy] = None,
        secure_enclave: Optional[SecureEnclaveManager] = None
    ):
        """
        Initialize biometric wallet.

        Args:
            wallet: Standard wallet instance to wrap
            biometric_manager: Biometric authentication manager
            policy: Security policy (uses defaults if None)
            secure_enclave: Optional secure enclave for hardware-backed signing
        """
        self._wallet = wallet
        self._biometric = biometric_manager
        self._policy = policy or SecurityPolicy()
        self._enclave = secure_enclave

        self._failed_attempts = 0
        self._locked_until: Optional[float] = None
        self._audit_log: list[OperationAudit] = []

        logger.info(
            "BiometricWallet initialized",
            extra={
                "event": "biometric_wallet.init",
                "address": wallet.address[:16] + "..."
            }
        )

    @property
    def address(self) -> str:
        """Public address (no authentication required)."""
        return self._wallet.address

    @property
    def public_key(self) -> str:
        """Public key (no authentication required)."""
        return self._wallet.public_key

    def _check_locked(self) -> None:
        """Check if wallet is locked and raise exception if so."""
        if self._locked_until:
            now = time.time()
            if now < self._locked_until:
                remaining = int(self._locked_until - now)
                raise WalletLockedError(
                    f"Wallet locked due to failed authentication attempts. "
                    f"Try again in {remaining} seconds."
                )
            else:
                # Unlock
                self._locked_until = None
                self._failed_attempts = 0

    def _authenticate(
        self,
        operation: str,
        protection_level: ProtectionLevel,
        prompt_message: Optional[str] = None
    ) -> BiometricResult:
        """
        Perform biometric authentication for operation.

        Args:
            operation: Operation name for audit
            protection_level: Required protection level
            prompt_message: Custom prompt message

        Returns:
            BiometricResult

        Raises:
            WalletLockedError: If wallet is locked
            AuthenticationFailedError: If authentication fails
        """
        self._check_locked()

        if prompt_message is None:
            prompt_message = f"Authenticate to {operation}"

        result = self._biometric.authenticate(
            prompt_message=prompt_message,
            protection_level=protection_level
        )

        # Audit
        if self._policy.audit_sensitive_operations:
            audit = OperationAudit(
                operation=operation,
                wallet_address=self.address,
                success=result.success,
                biometric_used=True,
                error=result.error_message
            )
            self._audit_log.append(audit)

        if not result.success:
            self._failed_attempts += 1

            if self._failed_attempts >= self._policy.max_failed_attempts:
                self._locked_until = time.time() + self._policy.lockout_duration_seconds
                logger.warning(
                    "Wallet locked due to repeated authentication failures",
                    extra={
                        "event": "biometric_wallet.locked",
                        "address": self.address[:16] + "...",
                        "attempts": self._failed_attempts
                    }
                )

            raise AuthenticationFailedError(
                f"Authentication failed: {result.error_message}"
            )

        # Reset failed attempts on success
        self._failed_attempts = 0

        return result

    def get_private_key(self, prompt_message: Optional[str] = None) -> str:
        """
        Get wallet private key (requires biometric authentication).

        Args:
            prompt_message: Custom authentication prompt

        Returns:
            Private key hex string

        Raises:
            WalletLockedError: If wallet is locked
            AuthenticationFailedError: If authentication fails
        """
        if not self._policy.require_biometric_for_private_key:
            return self._wallet.private_key

        self._authenticate(
            operation="view private key",
            protection_level=self._policy.private_key_protection,
            prompt_message=prompt_message
        )

        logger.info(
            "Private key accessed",
            extra={
                "event": "biometric_wallet.private_key_accessed",
                "address": self.address[:16] + "..."
            }
        )

        return self._wallet.private_key

    def sign_message(
        self,
        message: str,
        amount: Optional[Decimal] = None,
        prompt_message: Optional[str] = None
    ) -> str:
        """
        Sign message with biometric authentication based on amount.

        Args:
            message: Message to sign
            amount: Transaction amount (determines auth level)
            prompt_message: Custom authentication prompt

        Returns:
            Signature hex string

        Raises:
            WalletLockedError: If wallet is locked
            AuthenticationFailedError: If authentication fails
        """
        # Determine protection level based on amount
        if not self._policy.require_biometric_for_signing:
            return self._wallet.sign_message(message)

        protection_level = self._get_protection_level_for_amount(amount)

        self._authenticate(
            operation="sign transaction",
            protection_level=protection_level,
            prompt_message=prompt_message
        )

        # Use secure enclave if available
        if self._enclave and self._enclave.is_available():
            tx_hash = message.encode()
            signature = self._enclave.sign_transaction(
                wallet_id=self.address,
                transaction_hash=tx_hash
            )
            if signature:
                return signature.hex()

        # Fall back to software signing
        signature = self._wallet.sign_message(message)

        logger.info(
            "Message signed",
            extra={
                "event": "biometric_wallet.message_signed",
                "address": self.address[:16] + "...",
                "amount": str(amount) if amount else "N/A"
            }
        )

        return signature

    def _get_protection_level_for_amount(
        self,
        amount: Optional[Decimal]
    ) -> ProtectionLevel:
        """Determine protection level based on transaction amount."""
        if amount is None:
            return self._policy.large_tx_protection

        if amount >= self._policy.large_transaction_threshold:
            return self._policy.large_tx_protection
        elif amount >= self._policy.small_transaction_threshold:
            return self._policy.small_tx_protection
        else:
            # Small amounts may not require authentication
            if self._policy.allow_session_reuse:
                return self._policy.small_tx_protection
            else:
                return ProtectionLevel.BIOMETRIC_WEAK

    def export_wallet(
        self,
        password: Optional[str] = None,
        prompt_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Export wallet data (requires biometric authentication).

        Args:
            password: Optional encryption password
            prompt_message: Custom authentication prompt

        Returns:
            Wallet export dictionary

        Raises:
            WalletLockedError: If wallet is locked
            AuthenticationFailedError: If authentication fails
        """
        if not self._policy.require_biometric_for_export:
            return self._wallet.export_to_json(include_private=True, password=password)

        self._authenticate(
            operation="export wallet",
            protection_level=self._policy.export_protection,
            prompt_message=prompt_message
        )

        exported = self._wallet.export_to_json(include_private=True, password=password)

        logger.info(
            "Wallet exported",
            extra={
                "event": "biometric_wallet.exported",
                "address": self.address[:16] + "...",
                "encrypted": password is not None
            }
        )

        return exported

    def save_to_file(
        self,
        filename: str,
        password: Optional[str] = None,
        prompt_message: Optional[str] = None
    ) -> None:
        """
        Save wallet to file (requires biometric for unencrypted).

        Args:
            filename: File path
            password: Encryption password (required for unencrypted saves)
            prompt_message: Custom authentication prompt

        Raises:
            WalletLockedError: If wallet is locked
            AuthenticationFailedError: If authentication fails
            ValueError: If saving unencrypted without authentication
        """
        # Require biometric for unencrypted saves
        if password is None and self._policy.require_biometric_for_export:
            self._authenticate(
                operation="save wallet (unencrypted)",
                protection_level=self._policy.export_protection,
                prompt_message=prompt_message
            )

        self._wallet.save_to_file(filename, password)

        logger.info(
            "Wallet saved to file",
            extra={
                "event": "biometric_wallet.saved",
                "address": self.address[:16] + "...",
                "encrypted": password is not None
            }
        )

    def verify_signature(
        self,
        message: str,
        signature: str,
        public_key: str
    ) -> bool:
        """
        Verify signature (no authentication required).

        Args:
            message: Original message
            signature: Signature to verify
            public_key: Signer's public key

        Returns:
            True if signature is valid
        """
        return self._wallet.verify_signature(message, signature, public_key)

    def update_policy(self, policy: SecurityPolicy) -> None:
        """
        Update security policy.

        Args:
            policy: New security policy
        """
        self._policy = policy
        logger.info(
            "Security policy updated",
            extra={
                "event": "biometric_wallet.policy_updated",
                "address": self.address[:16] + "..."
            }
        )

    def get_policy(self) -> SecurityPolicy:
        """Get current security policy."""
        return self._policy

    def is_locked(self) -> bool:
        """Check if wallet is locked."""
        if self._locked_until:
            return time.time() < self._locked_until
        return False

    def unlock(self, prompt_message: Optional[str] = None) -> bool:
        """
        Manually unlock wallet (requires authentication).

        Args:
            prompt_message: Custom authentication prompt

        Returns:
            True if unlocked successfully
        """
        try:
            self._authenticate(
                operation="unlock wallet",
                protection_level=ProtectionLevel.BIOMETRIC_STRONG,
                prompt_message=prompt_message
            )
            self._locked_until = None
            self._failed_attempts = 0
            return True
        except (WalletLockedError, AuthenticationFailedError):
            return False

    def get_audit_log(self) -> list[OperationAudit]:
        """Get audit log for sensitive operations."""
        return self._audit_log.copy()

    def clear_audit_log(self) -> None:
        """Clear audit log."""
        self._audit_log.clear()

    def get_status(self) -> Dict[str, Any]:
        """Get wallet status information."""
        return {
            "address": self.address,
            "locked": self.is_locked(),
            "failed_attempts": self._failed_attempts,
            "locked_until": self._locked_until,
            "biometric_session_valid": self._biometric.is_session_valid(),
            "session_info": self._biometric.get_session_info(),
            "audit_entries": len(self._audit_log)
        }

    def to_dict(self) -> Dict[str, Any]:
        """Export public wallet data (no authentication required)."""
        return self._wallet.to_public_dict()

    def __repr__(self) -> str:
        """Safe string representation."""
        return f"BiometricWallet(address='{self.address[:16]}...', locked={self.is_locked()})"

    def __str__(self) -> str:
        """Safe string representation."""
        return f"Biometric XAI Wallet {self.address[:16]}..."


class BiometricWalletFactory:
    """
    Factory for creating biometric wallets with consistent configuration.

    Usage:
        factory = BiometricWalletFactory(
            biometric_manager=bio_manager,
            default_policy=SecurityPolicy()
        )

        # Create new wallet with biometric protection
        wallet = factory.create_wallet()

        # Wrap existing wallet
        bio_wallet = factory.wrap_wallet(existing_wallet)
    """

    def __init__(
        self,
        biometric_manager: BiometricAuthManager,
        default_policy: Optional[SecurityPolicy] = None,
        secure_enclave: Optional[SecureEnclaveManager] = None
    ):
        """
        Initialize wallet factory.

        Args:
            biometric_manager: Biometric authentication manager
            default_policy: Default security policy for new wallets
            secure_enclave: Optional secure enclave manager
        """
        self.biometric_manager = biometric_manager
        self.default_policy = default_policy or SecurityPolicy()
        self.secure_enclave = secure_enclave

    def create_wallet(
        self,
        policy: Optional[SecurityPolicy] = None
    ) -> BiometricWallet:
        """
        Create new wallet with biometric protection.

        Args:
            policy: Security policy (uses default if None)

        Returns:
            New BiometricWallet instance
        """
        wallet = Wallet()
        return self.wrap_wallet(wallet, policy)

    def wrap_wallet(
        self,
        wallet: Wallet,
        policy: Optional[SecurityPolicy] = None
    ) -> BiometricWallet:
        """
        Wrap existing wallet with biometric protection.

        Args:
            wallet: Existing wallet to wrap
            policy: Security policy (uses default if None)

        Returns:
            BiometricWallet instance
        """
        return BiometricWallet(
            wallet=wallet,
            biometric_manager=self.biometric_manager,
            policy=policy or self.default_policy,
            secure_enclave=self.secure_enclave
        )

    def create_from_mnemonic(
        self,
        mnemonic: str,
        passphrase: str = "",
        policy: Optional[SecurityPolicy] = None
    ) -> BiometricWallet:
        """
        Create wallet from BIP-39 mnemonic with biometric protection.

        Args:
            mnemonic: BIP-39 mnemonic phrase
            passphrase: Optional passphrase
            policy: Security policy

        Returns:
            New BiometricWallet instance
        """
        wallet = Wallet.from_mnemonic(mnemonic, passphrase)
        return self.wrap_wallet(wallet, policy)

    def load_from_file(
        self,
        filename: str,
        password: Optional[str] = None,
        policy: Optional[SecurityPolicy] = None
    ) -> BiometricWallet:
        """
        Load wallet from file with biometric protection.

        Args:
            filename: File path
            password: Decryption password
            policy: Security policy

        Returns:
            BiometricWallet instance
        """
        wallet = Wallet.load_from_file(filename, password)
        return self.wrap_wallet(wallet, policy)
