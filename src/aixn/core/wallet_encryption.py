"""
XAI Blockchain - Secure Wallet Encryption

AES-256 encryption for wallet private keys with PBKDF2 key derivation.
"""

import os
import json
import hashlib
import base64
from typing import Dict, Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet, InvalidToken


class WalletEncryption:
    """
    Secure wallet encryption using AES-256

    Private keys are encrypted with user password.
    Uses PBKDF2 for secure key derivation.
    """

    # Security parameters
    PBKDF2_ITERATIONS = 600000  # OWASP recommendation (2023)
    SALT_SIZE = 32  # 256 bits
    KEY_SIZE = 32  # 256 bits for AES-256

    @staticmethod
    def _derive_key(password: str, salt: bytes) -> bytes:
        """
        Derive encryption key from password using PBKDF2

        Args:
            password: User password
            salt: Random salt

        Returns:
            bytes: Derived encryption key
        """
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=WalletEncryption.KEY_SIZE,
            salt=salt,
            iterations=WalletEncryption.PBKDF2_ITERATIONS,
            backend=default_backend(),
        )

        key = kdf.derive(password.encode("utf-8"))
        return base64.urlsafe_b64encode(key)

    @staticmethod
    def encrypt_wallet(wallet_data: dict, password: str) -> dict:
        """
        Encrypt wallet private key with password

        Args:
            wallet_data: Wallet data with 'private_key' field
            password: User password

        Returns:
            dict: Encrypted wallet data
        """
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

        if "private_key" not in wallet_data:
            raise ValueError("Wallet data must contain 'private_key'")

        # Generate random salt
        salt = os.urandom(WalletEncryption.SALT_SIZE)

        # Derive encryption key from password
        encryption_key = WalletEncryption._derive_key(password, salt)

        # Encrypt private key
        fernet = Fernet(encryption_key)
        encrypted_pk = fernet.encrypt(wallet_data["private_key"].encode("utf-8"))

        # Return encrypted wallet (ANONYMOUS - no password stored!)
        encrypted_wallet = {
            "address": wallet_data["address"],
            "public_key": wallet_data["public_key"],
            "encrypted_private_key": base64.b64encode(encrypted_pk).decode("utf-8"),
            "salt": base64.b64encode(salt).decode("utf-8"),
            "encryption_version": "1.0",
            "encrypted": True,
            "note": "Password required to access private key",
        }

        # Include optional fields
        for key in ["initial_balance", "time_capsule_eligible", "tier"]:
            if key in wallet_data:
                encrypted_wallet[key] = wallet_data[key]

        return encrypted_wallet

    @staticmethod
    def decrypt_wallet(encrypted_wallet: dict, password: str) -> dict:
        """
        Decrypt wallet private key with password

        Args:
            encrypted_wallet: Encrypted wallet data
            password: User password

        Returns:
            dict: Decrypted wallet data

        Raises:
            ValueError: If password is incorrect or wallet is not encrypted
        """
        if not encrypted_wallet.get("encrypted"):
            raise ValueError("Wallet is not encrypted")

        if "encrypted_private_key" not in encrypted_wallet:
            raise ValueError("Missing encrypted private key")

        if "salt" not in encrypted_wallet:
            raise ValueError("Missing encryption salt")

        # Decode salt and encrypted private key
        salt = base64.b64decode(encrypted_wallet["salt"])
        encrypted_pk = base64.b64decode(encrypted_wallet["encrypted_private_key"])

        # Derive decryption key from password
        decryption_key = WalletEncryption._derive_key(password, salt)

        # Decrypt private key
        try:
            fernet = Fernet(decryption_key)
            decrypted_pk = fernet.decrypt(encrypted_pk).decode("utf-8")
        except InvalidToken:
            raise ValueError("Incorrect password")

        # Return decrypted wallet
        decrypted_wallet = {
            "address": encrypted_wallet["address"],
            "public_key": encrypted_wallet["public_key"],
            "private_key": decrypted_pk,
            "encrypted": False,
        }

        # Include optional fields
        for key in ["initial_balance", "time_capsule_eligible", "tier"]:
            if key in encrypted_wallet:
                decrypted_wallet[key] = encrypted_wallet[key]

        return decrypted_wallet

    @staticmethod
    def change_password(encrypted_wallet: dict, old_password: str, new_password: str) -> dict:
        """
        Change wallet encryption password

        Args:
            encrypted_wallet: Encrypted wallet
            old_password: Current password
            new_password: New password

        Returns:
            dict: Wallet encrypted with new password
        """
        # Decrypt with old password
        decrypted = WalletEncryption.decrypt_wallet(encrypted_wallet, old_password)

        # Re-encrypt with new password
        return WalletEncryption.encrypt_wallet(decrypted, new_password)

    @staticmethod
    def is_encrypted(wallet_data: dict) -> bool:
        """
        Check if wallet is encrypted

        Args:
            wallet_data: Wallet data

        Returns:
            bool: True if encrypted
        """
        return wallet_data.get("encrypted", False)


def save_encrypted_wallet(wallet_data: dict, password: str, filename: str):
    """
    Encrypt and save wallet to file

    Args:
        wallet_data: Wallet data
        password: Encryption password
        filename: File path
    """
    encrypted = WalletEncryption.encrypt_wallet(wallet_data, password)

    with open(filename, "w") as f:
        json.dump(encrypted, f, indent=2)


def load_encrypted_wallet(filename: str, password: str) -> dict:
    """
    Load and decrypt wallet from file

    Args:
        filename: File path
        password: Decryption password

    Returns:
        dict: Decrypted wallet data
    """
    with open(filename, "r") as f:
        encrypted = json.load(f)

    return WalletEncryption.decrypt_wallet(encrypted, password)


def verify_password(encrypted_wallet: dict, password: str) -> bool:
    """
    Verify if password is correct for encrypted wallet

    Args:
        encrypted_wallet: Encrypted wallet
        password: Password to verify

    Returns:
        bool: True if password is correct
    """
    try:
        WalletEncryption.decrypt_wallet(encrypted_wallet, password)
        return True
    except (ValueError, InvalidToken):
        return False
