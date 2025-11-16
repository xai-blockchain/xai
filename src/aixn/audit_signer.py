"""Stubbed audit signer for tests."""

from typing import Any


class AuditSigner:
    """Stub implementation of audit signing functionality for testing."""

    def __init__(self, trade_dir: str) -> None:
        """
        Initialize the audit signer.

        Args:
            trade_dir: Directory path for trade data
        """
        self.trade_dir = trade_dir

    def public_key(self) -> str:
        """
        Get the public key for verification.

        Returns:
            Stub public key string
        """
        return "AUDIT_PUBLIC_KEY"

    def sign(self, data: Any) -> str:
        """
        Sign data with the audit private key.

        Args:
            data: Data to be signed

        Returns:
            Signature string
        """
        return "signed"
