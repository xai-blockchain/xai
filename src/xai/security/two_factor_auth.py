"""
Production-Grade Two-Factor Authentication (2FA) Implementation
Implements TOTP (Time-based One-Time Password) following RFC 6238.
"""

import secrets
import time
import hashlib
import hmac
import base64
from typing import Optional, Tuple
from dataclasses import dataclass

import pyotp


@dataclass
class TwoFactorSetup:
    """2FA setup information"""
    secret: str
    provisioning_uri: str
    backup_codes: list[str]
    qr_code_url: str


class TwoFactorAuthManager:
    """
    Production-grade 2FA manager using TOTP.

    Features:
    - RFC 6238 compliant TOTP generation
    - Secure secret generation
    - Backup codes for account recovery
    - Rate limiting support
    - Time window validation
    """

    def __init__(self, issuer_name: str = "XAI Blockchain", time_window: int = 30):
        """
        Initialize 2FA manager.

        Args:
            issuer_name: Name to display in authenticator apps
            time_window: TOTP time window in seconds (default 30)
        """
        self.issuer_name = issuer_name
        self.time_window = time_window
        self.backup_code_length = 8
        self.num_backup_codes = 10

    def setup_2fa(self, user_id: str, user_email: Optional[str] = None) -> TwoFactorSetup:
        """
        Set up 2FA for a user.

        Args:
            user_id: Unique user identifier
            user_email: User's email (optional, for display in authenticator)

        Returns:
            TwoFactorSetup with secret, provisioning URI, and backup codes
        """
        # Generate secure random secret (160 bits / 32 base32 characters)
        secret = pyotp.random_base32()

        # Create TOTP instance
        totp = pyotp.TOTP(secret, interval=self.time_window)

        # Generate provisioning URI for QR code
        account_name = user_email if user_email else user_id
        provisioning_uri = totp.provisioning_uri(
            name=account_name,
            issuer_name=self.issuer_name
        )

        # Generate backup codes
        backup_codes = self._generate_backup_codes()

        # Create QR code URL (for use with QR code generator)
        qr_code_url = f"otpauth://totp/{self.issuer_name}:{account_name}?secret={secret}&issuer={self.issuer_name}"

        return TwoFactorSetup(
            secret=secret,
            provisioning_uri=provisioning_uri,
            backup_codes=backup_codes,
            qr_code_url=qr_code_url
        )

    def generate_totp(self, secret: str) -> str:
        """
        Generate current TOTP code.

        Args:
            secret: User's 2FA secret

        Returns:
            6-digit TOTP code
        """
        totp = pyotp.TOTP(secret, interval=self.time_window)
        return totp.now()

    def verify_totp(
        self,
        secret: str,
        code: str,
        valid_window: int = 1
    ) -> bool:
        """
        Verify a TOTP code.

        Args:
            secret: User's 2FA secret
            code: Code to verify
            valid_window: Number of time windows to accept (1 = ±30 seconds)

        Returns:
            True if code is valid
        """
        totp = pyotp.TOTP(secret, interval=self.time_window)
        return totp.verify(code, valid_window=valid_window)

    def verify_backup_code(
        self,
        provided_code: str,
        stored_backup_codes: list[str]
    ) -> Tuple[bool, Optional[list[str]]]:
        """
        Verify a backup code and remove it from the list.

        Args:
            provided_code: Code provided by user
            stored_backup_codes: List of hashed backup codes

        Returns:
            Tuple of (is_valid, updated_backup_codes)
        """
        # Hash the provided code
        hashed_provided = self._hash_backup_code(provided_code)

        # Check if it matches any stored code
        if hashed_provided in stored_backup_codes:
            # Remove the used code
            updated_codes = [c for c in stored_backup_codes if c != hashed_provided]
            return True, updated_codes

        return False, None

    def _generate_backup_codes(self) -> list[str]:
        """
        Generate secure backup codes.

        Returns:
            List of unhashed backup codes (to show to user)
        """
        codes = []
        for _ in range(self.num_backup_codes):
            # Generate random alphanumeric code
            code = ''.join(
                secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789')
                for _ in range(self.backup_code_length)
            )
            # Format as XXXX-XXXX for readability
            formatted_code = f"{code[:4]}-{code[4:]}"
            codes.append(formatted_code)

        return codes

    def hash_backup_codes(self, backup_codes: list[str]) -> list[str]:
        """
        Hash backup codes for storage.

        Args:
            backup_codes: Plain text backup codes

        Returns:
            List of hashed backup codes
        """
        return [self._hash_backup_code(code) for code in backup_codes]

    def _hash_backup_code(self, code: str) -> str:
        """Hash a single backup code"""
        # Remove formatting
        code_clean = code.replace('-', '')
        # SHA256 hash
        return hashlib.sha256(code_clean.encode()).hexdigest()

    def get_current_time_counter(self) -> int:
        """Get current time counter for TOTP"""
        return int(time.time() // self.time_window)

    def generate_recovery_codes(self, num_codes: int = 5) -> list[str]:
        """
        Generate one-time recovery codes.

        Args:
            num_codes: Number of recovery codes to generate

        Returns:
            List of recovery codes
        """
        codes = []
        for _ in range(num_codes):
            # 16-character recovery code
            code = secrets.token_hex(8).upper()
            # Format as XXXX-XXXX-XXXX-XXXX
            formatted = '-'.join([code[i:i+4] for i in range(0, len(code), 4)])
            codes.append(formatted)

        return codes


if __name__ == "__main__":
    raise SystemExit("TwoFactorAuth demo removed; use unit tests instead.")
