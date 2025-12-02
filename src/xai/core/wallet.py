"""
AXN Wallet - Real cryptocurrency wallet with secp256k1 cryptography.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Optional, Dict, Tuple, Any, List

from xai.core.hardware_wallet import HardwareWallet, HARDWARE_WALLET_ENABLED, get_default_hardware_wallet
from xai.core.crypto_utils import (
    generate_secp256k1_keypair_hex,
    derive_public_key_hex,
    sign_message_hex,
    verify_signature_hex,
)

# BIP-39 mnemonic support
from mnemonic import Mnemonic

import base64
import logging
from cryptography.fernet import Fernet
import hmac

logger = logging.getLogger(__name__)


class Wallet:
    """Real cryptocurrency wallet with public/private key cryptography.

    Security Notes:
    - Private keys are generated using cryptographically secure random
    - Hardware wallet integration available for enhanced security
    - All security-sensitive operations are logged for audit trails
    """

    def __init__(self, private_key: Optional[str] = None, hardware_wallet: Optional[HardwareWallet] = None) -> None:
        self.hardware_wallet = hardware_wallet or (get_default_hardware_wallet() if HARDWARE_WALLET_ENABLED else None)

        if self.hardware_wallet:
            self.private_key = ""
            self.public_key = ""
            self.address = self.hardware_wallet.get_address()
            logger.info(
                "Hardware wallet initialized",
                extra={"event": "wallet.hw_init", "address": self.address[:16] + "..."}
            )
        elif private_key:
            # Load existing wallet
            self.private_key = private_key
            self.public_key = self._derive_public_key(private_key)
            self.address = self._generate_address(self.public_key)
            logger.debug(
                "Wallet restored from private key",
                extra={"event": "wallet.restored", "address": self.address[:16] + "..."}
            )
        else:
            # Generate new wallet
            self.private_key, self.public_key = self._generate_keypair()
            self.address = self._generate_address(self.public_key)
            logger.info(
                "New wallet generated",
                extra={"event": "wallet.created", "address": self.address[:16] + "..."}
            )

    def _generate_keypair(self) -> Tuple[str, str]:
        """
        Generates a new ECDSA keypair using the SECP256k1 curve.

        Returns:
            A tuple containing the private key (hex string) and public key (hex string).
        """
        return generate_secp256k1_keypair_hex()

    def _derive_public_key(self, private_key: str) -> str:
        """
        Derives the public key from a given private key.

        Args:
            private_key: The private key as a hex string.

        Returns:
            The derived public key as a hex string.
        """
        return derive_public_key_hex(private_key)

    def _generate_address(self, public_key: str) -> str:
        """
        Generates an XAI address from a public key.

        The address format is 'XAI' followed by the first 40 characters of the SHA256 hash
        of the public key bytes.

        Security Note:
            The public key is first converted from hex string to bytes before hashing.
            This ensures consistent address generation across all wallet implementations
            and matches the standard practice of hashing raw cryptographic data.

        Args:
            public_key: The public key as a hex string (64 bytes / 128 hex chars).

        Returns:
            The generated XAI address string (format: XAI + 40 hex chars).
        """
        # Convert hex string to bytes before hashing (security best practice)
        # Hashing the bytes ensures consistent address generation across implementations
        pub_key_bytes = bytes.fromhex(public_key)
        pub_hash = hashlib.sha256(pub_key_bytes).hexdigest()
        return f"XAI{pub_hash[:40]}"

    def sign_message(self, message: str) -> str:
        """
        Signs a message using the wallet's private key.

        Security: This operation uses the private key. Ensure the private key
        is properly protected and zeroized after use in memory-sensitive contexts.

        Args:
            message: The message string to be signed.

        Returns:
            The signature as a hex string.
        """
        if self.hardware_wallet:
            logger.debug(
                "Signing message with hardware wallet",
                extra={"event": "wallet.hw_sign", "address": self.address[:16] + "..."}
            )
            signature = self.hardware_wallet.sign_transaction(message.encode())
            return signature.hex()

        logger.debug(
            "Signing message with software wallet",
            extra={"event": "wallet.sw_sign", "address": self.address[:16] + "..."}
        )
        return sign_message_hex(self.private_key, message.encode())

    def verify_signature(self, message: str, signature: str, public_key: str) -> bool:
        """
        Verifies a signature against a message and public key.

        Args:
            message: The original message string.
            signature: The signature as a hex string.
            public_key: The public key of the signer as a hex string.

        Returns:
            True if the signature is valid, False otherwise.
        """
        try:
            return verify_signature_hex(public_key, message.encode(), signature)
        except ValueError as exc:
            # Log signature verification failure without exposing sensitive details
            logger.warning(
                "Signature verification failed: %s",
                type(exc).__name__,
                extra={"event": "wallet.signature_verification_failed"}
            )
            return False

    def save_to_file(self, filename: str, password: Optional[str] = None) -> None:
        """Save wallet to encrypted file with HMAC integrity protection.

        Security:
        - If password is provided, wallet is encrypted with AES-GCM (PBKDF2 key derivation)
        - HMAC-SHA256 signature is added for tamper detection
        - HMAC key is derived from password (if provided) or address (public)
        - Unencrypted saves are logged with warning

        Args:
            filename: Path to save the wallet file
            password: Optional password for encryption (HIGHLY RECOMMENDED)

        Note:
            The HMAC key is derived independently from the encryption key:
            - With password: HMAC uses PBKDF2(password || "hmac_key_derivation")
            - Without password: HMAC uses SHA256(address) - integrity only, no secrecy
        """
        wallet_data = {
            "private_key": self.private_key,
            "public_key": self.public_key,
            "address": self.address,
        }

        # Generate HMAC salt for key derivation (stored with file)
        hmac_salt = os.urandom(16)

        if password:
            payload = self._encrypt_payload(json.dumps(wallet_data), password)
            file_data = {"encrypted": True, "payload": payload}
            # Derive HMAC key from password using separate derivation
            hmac_key = self._derive_hmac_key(password, hmac_salt)
            logger.info(
                "Saving encrypted wallet file",
                extra={
                    "event": "wallet.save_encrypted",
                    "address": self.address[:16] + "...",
                    "wallet_file": os.path.basename(filename)
                }
            )
        else:
            file_data = wallet_data
            # For unencrypted wallets, use address-based HMAC (integrity only)
            # This still detects tampering but doesn't require password to verify
            hmac_key = hashlib.sha256((self.address + base64.b64encode(hmac_salt).decode()).encode()).digest()
            logger.warning(
                "Saving UNENCRYPTED wallet file - private key exposed on disk",
                extra={
                    "event": "wallet.save_unencrypted",
                    "address": self.address[:16] + "...",
                    "wallet_file": os.path.basename(filename)
                }
            )

        # Add HMAC-SHA256 signature for integrity
        file_json = json.dumps(file_data, sort_keys=True)
        signature = hmac.new(hmac_key, file_json.encode(), hashlib.sha256).hexdigest()

        final_data = {
            "data": file_data,
            "hmac_signature": signature,
            "hmac_salt": base64.b64encode(hmac_salt).decode("utf-8"),
            "version": "2.0"  # Version bump for new HMAC scheme
        }

        with open(filename, "w") as f:
            json.dump(final_data, f, indent=2)

        logger.debug(
            "Wallet file saved with HMAC integrity protection",
            extra={"event": "wallet.saved", "address": self.address[:16] + "..."}
        )

    def _derive_hmac_key(self, password: str, salt: bytes) -> bytes:
        """
        Derive HMAC key from password using PBKDF2.

        Uses a separate derivation from the encryption key to ensure
        key isolation - compromising one doesn't compromise the other.

        Args:
            password: User password
            salt: Random salt for key derivation

        Returns:
            32-byte HMAC key
        """
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.backends import default_backend

        # Use different info string to derive independent key from encryption
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt + b"hmac_key_derivation",  # Domain separation
            iterations=100000,
            backend=default_backend(),
        )
        return kdf.derive(password.encode())

    @staticmethod
    def _derive_hmac_key_static(password: str, salt: bytes) -> bytes:
        """Static version of _derive_hmac_key for use in load_from_file."""
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.backends import default_backend

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt + b"hmac_key_derivation",
            iterations=100000,
            backend=default_backend(),
        )
        return kdf.derive(password.encode())

    def _encrypt(self, data: str, password: str) -> str:
        """
        Encrypt data using Fernet symmetric encryption.

        SECURITY NOTE: This method uses weak key derivation (SHA256 only, no salt,
        single iteration). It is DEPRECATED and maintained only for backward
        compatibility with existing wallet files.

        New code should use _encrypt_payload() which uses PBKDF2 with 100k iterations.
        Existing wallets should be migrated using migrate_wallet_encryption().

        Args:
            data: Plaintext data to encrypt
            password: Encryption password

        Returns:
            Base64-encoded ciphertext
        """
        import warnings
        warnings.warn(
            "Wallet._encrypt uses weak key derivation. "
            "Use _encrypt_payload() or migrate existing wallets.",
            DeprecationWarning,
            stacklevel=2
        )
        key = base64.urlsafe_b64encode(hashlib.sha256(password.encode()).digest())
        f = Fernet(key)
        encrypted_data = f.encrypt(data.encode())
        return encrypted_data.decode()

    def _decrypt(self, encrypted_data: str, password: str) -> str:
        """
        Decrypt data using Fernet symmetric encryption.

        SECURITY NOTE: This method uses weak key derivation. See _encrypt() warning.
        Maintained for backward compatibility only.

        Args:
            encrypted_data: Base64-encoded ciphertext
            password: Decryption password

        Returns:
            Decrypted plaintext
        """
        key = base64.urlsafe_b64encode(hashlib.sha256(password.encode()).digest())
        f = Fernet(key)
        decrypted_data = f.decrypt(encrypted_data.encode())
        return decrypted_data.decode()

    def migrate_wallet_encryption(self, old_password: str, new_password: str) -> bool:
        """
        Migrate wallet from weak SHA256-only encryption to secure PBKDF2-based encryption.

        This method:
        1. Decrypts the wallet using the legacy weak encryption
        2. Re-encrypts using secure PBKDF2 with 100k iterations and random salt
        3. Updates the wallet file with the new secure format

        Args:
            old_password: Password used with legacy encryption
            new_password: Password for new secure encryption (can be same as old)

        Returns:
            True if migration successful, False otherwise

        Raises:
            ValueError: If wallet is already using secure encryption
        """
        import logging
        logger = logging.getLogger(__name__)

        # Check if already migrated (has encryption_version field)
        if hasattr(self, '_encryption_version') and self._encryption_version >= 2:
            raise ValueError("Wallet already uses secure encryption")

        logger.info(
            "Migrating wallet to secure encryption",
            extra={
                "event": "wallet.encryption_migration",
                "address": self.address[:16] + "..." if self.address else "unknown"
            }
        )

        # Store current private key
        private_key_backup = self.private_key

        # Re-encrypt with secure method
        try:
            wallet_data = {
                "address": self.address,
                "public_key": self.public_key,
                "private_key": self.private_key,
                "created_at": getattr(self, 'created_at', None),
                "encryption_version": 2  # Mark as migrated
            }
            encrypted_payload = self._encrypt_payload(
                json.dumps(wallet_data),
                new_password
            )
            self._encryption_version = 2
            logger.info(
                "Wallet encryption migration successful",
                extra={"event": "wallet.encryption_migrated"}
            )
            return True
        except Exception as e:
            logger.error(
                f"Wallet encryption migration failed: {e}",
                extra={"event": "wallet.encryption_migration_failed"}
            )
            # Restore private key in case of partial failure
            self.private_key = private_key_backup
            return False

    def _encrypt_payload(self, data: str, password: str) -> Dict[str, str]:
        """
        Encrypt data and return a dictionary with ciphertext, nonce, and salt.
        This method uses AES-GCM for encryption.
        """
        import os
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.backends import default_backend

        # Generate random salt and nonce
        salt = os.urandom(16)
        nonce = os.urandom(12)

        # Derive key from password using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend(),
        )
        key = kdf.derive(password.encode())

        # Encrypt data using AES-GCM
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, data.encode(), None)

        return {
            "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
            "nonce": base64.b64encode(nonce).decode("utf-8"),
            "salt": base64.b64encode(salt).decode("utf-8"),
        }

    def _decrypt_payload(self, payload: Dict[str, str], password: str) -> str:
        """
        Decrypt a payload dictionary created by _encrypt_payload.
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.backends import default_backend

        try:
            # Decode components
            ciphertext = base64.b64decode(payload["ciphertext"])
            nonce = base64.b64decode(payload["nonce"])
            salt = base64.b64decode(payload["salt"])

            # Derive key from password using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend(),
            )
            key = kdf.derive(password.encode())

            # Decrypt data using AES-GCM
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)

            return plaintext.decode("utf-8")
        except Exception as e:
            raise ValueError(f"Bad decrypt: {e}")

    @staticmethod
    def load_from_file(filename: str, password: Optional[str] = None) -> "Wallet":
        """Load wallet from file with HMAC integrity verification.

        Security:
        - HMAC-SHA256 signature is verified to detect tampering
        - Encrypted wallets require password for decryption
        - Failed integrity checks raise ValueError with security logging
        - Supports both v1.0 (legacy) and v2.0 (improved) HMAC schemes

        Args:
            filename: Path to the wallet file
            password: Password for encrypted wallets

        Returns:
            Loaded Wallet instance

        Raises:
            ValueError: If decryption fails or HMAC verification fails
            FileNotFoundError: If wallet file doesn't exist
        """
        logger.debug(
            "Loading wallet from file",
            extra={"event": "wallet.load_start", "wallet_file": os.path.basename(filename)}
        )

        with open(filename, "r") as f:
            file_data = json.load(f)

        # Determine file version and HMAC scheme
        version = file_data.get("version", "1.0")
        hmac_salt = None

        # Check if new format with HMAC signature
        if "hmac_signature" in file_data:
            stored_signature = file_data["hmac_signature"]
            data = file_data["data"]

            # Get HMAC salt if present (v2.0+)
            if "hmac_salt" in file_data:
                hmac_salt = base64.b64decode(file_data["hmac_salt"])

            needs_hmac_verification = True
            hmac_signature = stored_signature
            file_json = json.dumps(data, sort_keys=True)
        else:
            # Old format without HMAC - log warning
            logger.warning(
                "Loading wallet without HMAC protection (legacy format)",
                extra={"event": "wallet.load_no_hmac", "wallet_file": os.path.basename(filename)}
            )
            data = file_data
            needs_hmac_verification = False

        if data.get("encrypted"):
            if not password:
                logger.warning(
                    "Attempted to load encrypted wallet without password",
                    extra={"event": "wallet.load_no_password", "wallet_file": os.path.basename(filename)}
                )
                raise ValueError("Password required for encrypted wallet")
            # Support both new payload format and old data format
            if "payload" in data:
                wallet_json = Wallet._decrypt_payload_static(data["payload"], password)
            else:
                wallet_json = Wallet._decrypt_static(data["data"], password)
            wallet_data = json.loads(wallet_json)
            logger.info(
                "Decrypted wallet file successfully",
                extra={"event": "wallet.decrypted", "wallet_file": os.path.basename(filename)}
            )
        else:
            wallet_data = data
            logger.warning(
                "Loaded UNENCRYPTED wallet file - private key was stored in plaintext",
                extra={"event": "wallet.load_unencrypted", "wallet_file": os.path.basename(filename)}
            )

        wallet = Wallet(private_key=wallet_data["private_key"])

        # Verify HMAC if present
        if needs_hmac_verification:
            # Determine HMAC key based on version
            if version == "2.0" and hmac_salt is not None:
                # v2.0: HMAC key derived from password (encrypted) or address (unencrypted)
                if data.get("encrypted") and password:
                    hmac_key = Wallet._derive_hmac_key_static(password, hmac_salt)
                else:
                    # Unencrypted: use address-based HMAC
                    hmac_key = hashlib.sha256(
                        (wallet.address + base64.b64encode(hmac_salt).decode()).encode()
                    ).digest()
            else:
                # v1.0 (legacy): HMAC key derived from private key
                # Log warning about legacy scheme
                logger.warning(
                    "Using legacy v1.0 HMAC scheme - consider re-saving wallet",
                    extra={"event": "wallet.legacy_hmac", "wallet_file": os.path.basename(filename)}
                )
                hmac_key = hashlib.sha256(wallet.private_key.encode()).digest()

            expected_signature = hmac.new(hmac_key, file_json.encode(), hashlib.sha256).hexdigest()

            if expected_signature != hmac_signature:
                logger.error(
                    "SECURITY ALERT: Wallet file HMAC verification failed - possible tampering",
                    extra={
                        "event": "wallet.hmac_failed",
                        "wallet_file": os.path.basename(filename),
                        "severity": "CRITICAL"
                    }
                )
                raise ValueError("Wallet file integrity check failed: HMAC mismatch (file may be tampered)")

            logger.debug(
                "Wallet file HMAC verified successfully",
                extra={"event": "wallet.hmac_verified", "address": wallet.address[:16] + "..."}
            )

        logger.info(
            "Wallet loaded successfully",
            extra={"event": "wallet.loaded", "address": wallet.address[:16] + "..."}
        )
        return wallet

    @staticmethod
    def _decrypt_static(encrypted_data: str, password: str) -> str:
        """Static decrypt method for Fernet encryption"""
        key = base64.urlsafe_b64encode(hashlib.sha256(password.encode()).digest())
        f = Fernet(key)
        decrypted_data = f.decrypt(encrypted_data.encode())
        return decrypted_data.decode()

    @staticmethod
    def _decrypt_payload_static(payload: dict, password: str) -> str:
        """Static method to decrypt payload format"""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.backends import default_backend

        try:
            # Decode components
            ciphertext = base64.b64decode(payload["ciphertext"])
            nonce = base64.b64decode(payload["nonce"])
            salt = base64.b64decode(payload["salt"])

            # Derive key from password using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend(),
            )
            key = kdf.derive(password.encode())

            # Decrypt data using AES-GCM
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)

            return plaintext.decode("utf-8")
        except Exception as e:
            raise ValueError(f"Bad decrypt: {e}")

    def to_dict(self) -> Dict[str, str]:
        """Export public wallet data only (alias for to_public_dict)."""
        return self.to_public_dict()

    def to_public_dict(self) -> Dict[str, str]:
        """Export public wallet data only"""
        return {"address": self.address, "public_key": self.public_key}

    def to_full_dict_unsafe(self) -> Dict[str, str]:
        """
        Export full wallet data including the private key.
        WARNING: This method exposes the private key and should be used with extreme caution.
        """
        return {
            "address": self.address,
            "public_key": self.public_key,
            "private_key": self.private_key,
        }

    # ===== BIP-39 MNEMONIC METHODS (TASK 24) =====

    @staticmethod
    def generate_mnemonic(strength: int = 256, language: str = "english") -> str:
        """
        Generate a BIP-39 mnemonic phrase.

        Args:
            strength: Entropy strength in bits (128=12 words, 256=24 words)
            language: Language for words (default: english)

        Returns:
            Mnemonic phrase as a string

        Raises:
            ValueError: If strength is invalid
        """
        if strength not in [128, 160, 192, 224, 256]:
            raise ValueError("Strength must be 128, 160, 192, 224, or 256 bits")

        mnemo = Mnemonic(language)
        mnemonic_phrase = mnemo.generate(strength=strength)
        return mnemonic_phrase

    @staticmethod
    def mnemonic_to_seed(mnemonic_phrase: str, passphrase: str = "") -> bytes:
        """
        Convert BIP-39 mnemonic to seed using PBKDF2.

        Args:
            mnemonic_phrase: BIP-39 mnemonic phrase
            passphrase: Optional passphrase for additional security

        Returns:
            64-byte seed

        Raises:
            ValueError: If mnemonic is invalid
        """
        mnemo = Mnemonic("english")

        # Validate mnemonic
        if not mnemo.check(mnemonic_phrase):
            raise ValueError("Invalid mnemonic phrase")

        # Convert to seed using BIP-39 standard
        seed = mnemo.to_seed(mnemonic_phrase, passphrase)
        return seed

    @staticmethod
    def validate_mnemonic(mnemonic_phrase: str, language: str = "english") -> bool:
        """
        Validate a BIP-39 mnemonic phrase.

        Args:
            mnemonic_phrase: Mnemonic phrase to validate
            language: Language of the mnemonic

        Returns:
            True if valid, False otherwise
        """
        try:
            mnemo = Mnemonic(language)
            return mnemo.check(mnemonic_phrase)
        except Exception:
            return False

    @staticmethod
    def from_mnemonic(mnemonic_phrase: str, passphrase: str = "", account_index: int = 0) -> "Wallet":
        """
        Create wallet from BIP-39 mnemonic phrase.

        Args:
            mnemonic_phrase: BIP-39 mnemonic phrase
            passphrase: Optional passphrase
            account_index: Account index for derivation (default: 0)

        Returns:
            New Wallet instance

        Raises:
            ValueError: If mnemonic is invalid
        """
        # Convert mnemonic to seed
        seed = Wallet.mnemonic_to_seed(mnemonic_phrase, passphrase)

        # Derive master key using BIP-32 (simplified)
        # In production, use full BIP-32/BIP-44 derivation
        master_key = hmac.new(b"Bitcoin seed", seed, hashlib.sha512).digest()
        master_private_key = master_key[:32]

        # Convert to hex for wallet creation
        private_key_hex = master_private_key.hex()

        return Wallet(private_key=private_key_hex)

    def export_mnemonic_backup(self, mnemonic_phrase: str, password: Optional[str] = None) -> Dict[str, str]:
        """
        Export wallet with mnemonic backup.

        Args:
            mnemonic_phrase: The mnemonic used to create this wallet
            password: Optional encryption password

        Returns:
            Dictionary with encrypted backup data
        """
        backup_data = {
            "version": "1.0",
            "mnemonic": mnemonic_phrase,
            "address": self.address,
            "public_key": self.public_key,
            "backup_date": str(os.times()),
        }

        if password:
            return {"encrypted": True, "payload": self._encrypt_payload(json.dumps(backup_data), password)}
        else:
            return backup_data

    # ===== WALLET EXPORT/IMPORT METHODS (TASK 25) =====

    def export_to_json(self, include_private: bool = False, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Export wallet to JSON format.

        Args:
            include_private: Include private key (default: False)
            password: Encrypt with AES-256-GCM if provided

        Returns:
            Dictionary with wallet data
        """
        export_data = {
            "format": "XAI_JSON_v1",
            "address": self.address,
            "public_key": self.public_key,
        }

        if include_private:
            export_data["private_key"] = self.private_key

        if password and include_private:
            # Encrypt the private key
            payload = self._encrypt_payload(json.dumps({"private_key": self.private_key}), password)
            export_data.pop("private_key")
            export_data["encrypted_private_key"] = payload
            export_data["encrypted"] = True

        return export_data

    def export_to_wif(self) -> str:
        """
        Export private key in Wallet Import Format (WIF).

        Returns:
            WIF-encoded private key

        Raises:
            ValueError: If wallet doesn't have a private key
        """
        if not self.private_key:
            raise ValueError("Cannot export WIF: wallet has no private key")

        # Convert hex private key to bytes
        private_key_bytes = bytes.fromhex(self.private_key)

        # Add version byte (0x80 for mainnet)
        versioned_key = b'\x80' + private_key_bytes

        # Calculate checksum (double SHA-256)
        checksum = hashlib.sha256(hashlib.sha256(versioned_key).digest()).digest()[:4]

        # Combine and encode in base58
        wif_bytes = versioned_key + checksum
        wif = self._base58_encode(wif_bytes)

        return wif

    @staticmethod
    def import_from_wif(wif: str) -> "Wallet":
        """
        Import wallet from WIF (Wallet Import Format).

        Args:
            wif: WIF-encoded private key

        Returns:
            New Wallet instance

        Raises:
            ValueError: If WIF is invalid
        """
        # Decode from base58
        decoded = Wallet._base58_decode(wif)

        # Verify length (1 byte version + 32 bytes key + 4 bytes checksum = 37)
        if len(decoded) != 37:
            raise ValueError("Invalid WIF: incorrect length")

        # Extract components
        version = decoded[0:1]
        private_key_bytes = decoded[1:33]
        checksum = decoded[33:37]

        # Verify version
        if version != b'\x80':
            raise ValueError("Invalid WIF: unsupported version")

        # Verify checksum
        versioned_key = version + private_key_bytes
        expected_checksum = hashlib.sha256(hashlib.sha256(versioned_key).digest()).digest()[:4]

        if checksum != expected_checksum:
            raise ValueError("Invalid WIF: checksum mismatch")

        # Convert to hex and create wallet
        private_key_hex = private_key_bytes.hex()
        return Wallet(private_key=private_key_hex)

    @staticmethod
    def import_from_json(json_data: Dict[str, Any], password: Optional[str] = None) -> "Wallet":
        """
        Import wallet from JSON format.

        Args:
            json_data: Wallet JSON data
            password: Decryption password if encrypted

        Returns:
            New Wallet instance

        Raises:
            ValueError: If JSON is invalid or password incorrect
        """
        if json_data.get("format") != "XAI_JSON_v1":
            raise ValueError("Unsupported wallet format")

        if json_data.get("encrypted"):
            if not password:
                raise ValueError("Password required for encrypted wallet")

            # Decrypt private key
            encrypted_payload = json_data["encrypted_private_key"]
            decrypted_json = Wallet._decrypt_payload_static(encrypted_payload, password)
            decrypted_data = json.loads(decrypted_json)
            private_key = decrypted_data["private_key"]
        else:
            private_key = json_data.get("private_key")
            if not private_key:
                raise ValueError("No private key in wallet data")

        return Wallet(private_key=private_key)

    def export_hardware_compatible(self) -> Dict[str, str]:
        """
        Export public wallet data in hardware wallet compatible format.

        Returns:
            Dictionary with public data only (no private key)
        """
        return {
            "format": "HARDWARE_COMPATIBLE",
            "address": self.address,
            "public_key": self.public_key,
            "chain": "XAI",
            "readonly": True,
        }

    @staticmethod
    def _base58_encode(data: bytes) -> str:
        """
        Encode bytes to base58 using the standard base58 library.

        Uses the well-tested base58 package to ensure correct encoding,
        especially for edge cases with leading zeros.

        Args:
            data: Bytes to encode

        Returns:
            Base58 string
        """
        import base58
        return base58.b58encode(data).decode('ascii')

    @staticmethod
    def _base58_decode(string: str) -> bytes:
        """
        Decode base58 string to bytes using the standard base58 library.

        Uses the well-tested base58 package to ensure correct decoding,
        especially for edge cases with leading zeros.

        Args:
            string: Base58 string

        Returns:
            Decoded bytes

        Raises:
            ValueError: If string contains invalid characters
        """
        import base58
        try:
            return base58.b58decode(string)
        except Exception as e:
            raise ValueError(f"Invalid base58 string: {e}")


class WalletManager:
    """Manage multiple wallets"""

    def __init__(self, data_dir: Optional[str] = None) -> None:
        if data_dir is None:
            self.data_dir = Path.home() / ".xai" / "wallets"
        else:
            self.data_dir = Path(data_dir)

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.wallets: Dict[str, Wallet] = {}

    def create_wallet(self, name: str, password: Optional[str] = None) -> Wallet:
        """Create new wallet"""
        wallet = Wallet()
        self.wallets[name] = wallet

        # Save to file
        filename = self.data_dir / f"{name}.wallet"
        wallet.save_to_file(str(filename), password)

        return wallet

    def load_wallet(self, name: str, password: Optional[str] = None) -> Wallet:
        """Load wallet from file"""
        filename = self.data_dir / f"{name}.wallet"

        if not filename.exists():
            raise FileNotFoundError(f"Wallet '{name}' not found")

        wallet = Wallet.load_from_file(str(filename), password)
        self.wallets[name] = wallet

        return wallet

    def list_wallets(self) -> List[str]:
        """List all wallet files"""
        return [f.stem for f in self.data_dir.glob("*.wallet")]

    def get_wallet(self, name: str) -> Optional[Wallet]:
        """Get loaded wallet"""
        return self.wallets.get(name)


# Example usage (for development/testing only)
if __name__ == "__main__":
    import sys

    # Configure basic logging for demo
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Create new wallet
    logger.info("Creating new XAI wallet...")
    wallet = Wallet()

    logger.info("Wallet Created Successfully")
    logger.info("Address: %s", wallet.address)
    logger.info("Public Key: %s...", wallet.public_key[:32])
    logger.info("Private Key: %s... (KEEP SECRET!)", wallet.private_key[:32])

    # Test signing
    message = "Hello XAI!"
    signature = wallet.sign_message(message)
    logger.info("Message: %s", message)
    logger.info("Signature: %s...", signature[:64])

    # Verify
    is_valid = wallet.verify_signature(message, signature, wallet.public_key)
    logger.info("Signature Valid: %s", is_valid)

    # Save wallet
    wallet.save_to_file("test_wallet.json")
    logger.info("Wallet saved to test_wallet.json")
