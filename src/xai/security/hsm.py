from __future__ import annotations

"""
Production-Grade Hardware Security Module (HSM) Implementation
Provides secure key generation, storage, rotation, audit logging, and multi-signature support.
"""

import hashlib
import json
import logging
import os
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Security-specific exceptions
class HSMError(Exception):
    """Base exception for HSM operations"""
    pass

class HSMKeyGenerationError(HSMError):
    """Raised when key generation fails"""
    pass

class HSMSigningError(HSMError):
    """Raised when signing operation fails"""
    pass

class HSMKeyRotationError(HSMError):
    """Raised when key rotation fails"""
    pass

class HSMStorageError(HSMError):
    """Raised when storage operations fail"""
    pass

class HSMCryptographicError(HSMError):
    """Raised when cryptographic operations fail"""
    pass

class KeyType(Enum):
    """Supported cryptographic key types"""
    SECP256K1 = "secp256k1"
    SECP256R1 = "secp256r1"
    ED25519 = "ed25519"
    RSA_2048 = "rsa_2048"
    RSA_4096 = "rsa_4096"

class KeyPurpose(Enum):
    """Purpose classification for keys"""
    SIGNING = "signing"
    ENCRYPTION = "encryption"
    MULTISIG = "multisig"
    COLD_STORAGE = "cold_storage"
    HOT_WALLET = "hot_wallet"

@dataclass
class AuditLogEntry:
    """Audit log entry for HSM operations"""
    timestamp: str
    operation: str
    key_id: str
    user_id: str
    success: bool
    details: dict[str, Any]

    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class KeyMetadata:
    """Metadata for stored keys"""
    key_id: str
    key_type: KeyType
    purpose: KeyPurpose
    created_at: str
    last_used: str
    rotation_date: str | None
    is_active: bool
    multisig_threshold: int | None
    multisig_total: int | None
    public_key_pem: str

class HardwareSecurityModule:
    """
    Production-grade HSM implementation with:
    - Secure key generation using cryptographically secure random
    - Encrypted key storage with AES-GCM
    - Key rotation with configurable schedules
    - Comprehensive audit logging
    - Multi-signature support with M-of-N threshold
    """

    def __init__(
        self,
        storage_path: str = "./hsm_storage",
        master_password: str | None = None,
        auto_rotate_days: int = 90
    ):
        """
        Initialize HSM with secure storage.

        Args:
            storage_path: Path to encrypted key storage
            master_password: Master password for key encryption (required for production)
            auto_rotate_days: Days before automatic key rotation is required
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.keys_file = self.storage_path / "encrypted_keys.dat"
        self.metadata_file = self.storage_path / "key_metadata.json"
        self.audit_log_file = self.storage_path / "audit_log.jsonl"
        self.salt_file = self.storage_path / "hsm_salt.bin"

        self.auto_rotate_days = auto_rotate_days
        self.logger = logging.getLogger(__name__)

        # Load or generate unique salt for this HSM instance
        self._hsm_salt = self._load_or_generate_salt()

        # Derive encryption key from master password
        if master_password:
            self.encryption_key = self._derive_encryption_key(master_password, self._hsm_salt)
        else:
            # For testing only - generate random key
            self.logger.warning("No master password provided - using random encryption key")
            self.encryption_key = AESGCM.generate_key(bit_length=256)

        self.aesgcm = AESGCM(self.encryption_key)

        # Load existing keys and metadata
        self.key_metadata: dict[str, KeyMetadata] = self._load_metadata()
        self.encrypted_keys: dict[str, bytes] = self._load_encrypted_keys()

    def _load_or_generate_salt(self) -> bytes:
        """
        Load existing HSM salt or generate a new random one.

        Each HSM instance has a unique 32-byte salt stored persistently.
        This prevents rainbow table attacks and ensures different HSM
        instances with the same password derive different encryption keys.

        Returns:
            32-byte salt unique to this HSM instance
        """
        if self.salt_file.exists():
            salt = self.salt_file.read_bytes()
            if len(salt) == 32:
                self.logger.info("Loaded existing HSM salt")
                return salt
            else:
                self.logger.warning(
                    "Invalid salt file size, regenerating",
                    extra={"event": "hsm.salt_regenerated", "old_size": len(salt)}
                )

        # Generate new cryptographically secure random salt
        salt = secrets.token_bytes(32)

        # Persist salt with restrictive permissions
        self.salt_file.write_bytes(salt)
        try:
            self.salt_file.chmod(0o600)  # Owner read/write only
        except (OSError, PermissionError):
            self.logger.warning("Could not set restrictive permissions on salt file")

        self.logger.info(
            "Generated new HSM salt",
            extra={"event": "hsm.salt_generated"}
        )
        return salt

    def _derive_encryption_key(self, password: str, salt: bytes | None = None) -> bytes:
        """
        Derive encryption key from master password using PBKDF2.

        Uses the HSM instance's unique salt to prevent rainbow table attacks.

        Args:
            password: Master password for key derivation
            salt: Optional salt override (uses instance salt if not provided)

        Returns:
            32-byte derived encryption key
        """
        if salt is None:
            salt = self._hsm_salt

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,  # OWASP 2023 recommendation
            backend=default_backend()
        )
        return kdf.derive(password.encode())

    def _audit_log(
        self,
        operation: str,
        key_id: str,
        user_id: str,
        success: bool,
        details: dict[str, Any]
    ) -> None:
        """Write audit log entry"""
        entry = AuditLogEntry(
            timestamp=datetime.utcnow().isoformat(),
            operation=operation,
            key_id=key_id,
            user_id=user_id,
            success=success,
            details=details
        )

        with open(self.audit_log_file, "a") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

    def generate_key(
        self,
        key_type: KeyType,
        purpose: KeyPurpose,
        user_id: str = "system",
        multisig_config: tuple[int, int] | None = None
    ) -> str:
        """
        Generate a new cryptographic key pair.

        Args:
            key_type: Type of key to generate
            purpose: Purpose of the key
            user_id: ID of user requesting key generation
            multisig_config: (M, N) for M-of-N multisig, if applicable

        Returns:
            key_id: Unique identifier for the generated key
        """
        try:
            # Generate key pair based on type
            if key_type == KeyType.SECP256K1:
                private_key = ec.generate_private_key(ec.SECP256K1(), default_backend())
            elif key_type == KeyType.SECP256R1:
                private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
            elif key_type == KeyType.ED25519:
                private_key = ed25519.Ed25519PrivateKey.generate()
            elif key_type == KeyType.RSA_2048:
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                    backend=default_backend()
                )
            elif key_type == KeyType.RSA_4096:
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=4096,
                    backend=default_backend()
                )
            else:
                raise ValueError(f"Unsupported key type: {key_type}")

            # Generate unique key ID
            key_id = self._generate_key_id()

            # Serialize private key
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )

            # Encrypt and store private key
            self._encrypt_and_store_key(key_id, private_pem)

            # Get public key
            public_key = private_key.public_key()
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode()

            # Store metadata
            metadata = KeyMetadata(
                key_id=key_id,
                key_type=key_type,
                purpose=purpose,
                created_at=datetime.utcnow().isoformat(),
                last_used=datetime.utcnow().isoformat(),
                rotation_date=(datetime.utcnow() + timedelta(days=self.auto_rotate_days)).isoformat(),
                is_active=True,
                multisig_threshold=multisig_config[0] if multisig_config else None,
                multisig_total=multisig_config[1] if multisig_config else None,
                public_key_pem=public_pem
            )

            self.key_metadata[key_id] = metadata
            self._save_metadata()

            self._audit_log(
                operation="generate_key",
                key_id=key_id,
                user_id=user_id,
                success=True,
                details={
                    "key_type": key_type.value,
                    "purpose": purpose.value,
                    "multisig": multisig_config
                }
            )

            return key_id

        except (ValueError, TypeError) as e:
            self._audit_log(
                operation="generate_key",
                key_id="N/A",
                user_id=user_id,
                success=False,
                details={"error": str(e), "error_type": "validation"}
            )
            raise HSMKeyGenerationError(f"Invalid key parameters: {e}") from e
        except OSError as e:
            self.logger.error(
                "OSError occurred",
                extra={
                    "error_type": "OSError",
                    "error": str(e)
                }
            )
            self._audit_log(
                operation="generate_key",
                key_id="N/A",
                user_id=user_id,
                success=False,
                details={"error": str(e), "error_type": "storage"}
            )
            raise HSMStorageError(f"Failed to store key: {e}") from e
        except (RuntimeError, MemoryError, OverflowError) as e:
            self._audit_log(
                operation="generate_key",
                key_id="N/A",
                user_id=user_id,
                success=False,
                details={"error": str(e), "error_type": "cryptographic"}
            )
            self.logger.error(
                "Key generation failed",
                exc_info=True,
                extra={"event": "hsm.key_generation_failed", "user_id": user_id, "error_type": type(e).__name__}
            )
            raise HSMCryptographicError(f"Key generation failed: {e}") from e

    def sign(self, key_id: str, message: bytes, user_id: str = "system") -> bytes:
        """
        Sign a message using the specified key.

        Args:
            key_id: ID of key to use for signing
            message: Message bytes to sign
            user_id: ID of user requesting signature

        Returns:
            Signature bytes
        """
        try:
            # Load private key
            private_key = self._load_private_key(key_id)

            # Get metadata
            metadata = self.key_metadata.get(key_id)
            if not metadata:
                raise ValueError(f"Key {key_id} not found")

            if not metadata.is_active:
                raise ValueError(f"Key {key_id} is not active")

            # Check if rotation needed
            if metadata.rotation_date:
                rotation_date = datetime.fromisoformat(metadata.rotation_date)
                if datetime.utcnow() > rotation_date:
                    self.logger.warning(f"Key {key_id} requires rotation")

            # Sign based on key type
            if isinstance(private_key, ec.EllipticCurvePrivateKey):
                signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
            elif isinstance(private_key, ed25519.Ed25519PrivateKey):
                signature = private_key.sign(message)
            elif isinstance(private_key, rsa.RSAPrivateKey):
                from cryptography.hazmat.primitives.asymmetric import padding
                signature = private_key.sign(
                    message,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
            else:
                raise ValueError("Unsupported key type for signing")

            # Update last used timestamp
            metadata.last_used = datetime.utcnow().isoformat()
            self._save_metadata()

            self._audit_log(
                operation="sign",
                key_id=key_id,
                user_id=user_id,
                success=True,
                details={"message_hash": hashlib.sha256(message).hexdigest()[:16]}
            )

            return signature

        except ValueError as e:
            self.logger.debug(
                "ValueError in sign",
                extra={
                    "error_type": "ValueError",
                    "error": str(e),
                    "function": "sign"
                }
            )
            self._audit_log(
                operation="sign",
                key_id=key_id,
                user_id=user_id,
                success=False,
                details={"error": str(e), "error_type": "validation"}
            )
            raise HSMSigningError(f"Invalid signing parameters: {e}") from e
        except InvalidSignature as e:
            self.logger.error(
                "InvalidSignature in sign",
                extra={
                    "error_type": "InvalidSignature",
                    "error": str(e),
                    "function": "sign"
                }
            )
            self._audit_log(
                operation="sign",
                key_id=key_id,
                user_id=user_id,
                success=False,
                details={"error": str(e), "error_type": "signature"}
            )
            raise HSMCryptographicError(f"Signature operation failed: {e}") from e
        except OSError as e:
            self.logger.error(
                "OSError in sign",
                extra={
                    "error_type": "OSError",
                    "error": str(e),
                    "function": "sign"
                }
            )
            self._audit_log(
                operation="sign",
                key_id=key_id,
                user_id=user_id,
                success=False,
                details={"error": str(e), "error_type": "storage"}
            )
            raise HSMStorageError(f"Failed to access key storage: {e}") from e
        except (RuntimeError, MemoryError, OverflowError, AttributeError) as e:
            self._audit_log(
                operation="sign",
                key_id=key_id,
                user_id=user_id,
                success=False,
                details={"error": str(e), "error_type": "cryptographic"}
            )
            self.logger.error(
                "Signing operation failed",
                exc_info=True,
                extra={"event": "hsm.signing_failed", "key_id": key_id[:16], "user_id": user_id, "error_type": type(e).__name__}
            )
            raise HSMSigningError(f"Signing operation failed: {e}") from e

    def verify_signature(self, key_id: str, message: bytes, signature: bytes) -> bool:
        """
        Verify a signature against the stored public key.

        Args:
            key_id: Key identifier
            message: Message bytes
            signature: Signature bytes

        Returns:
            True if signature valid, False otherwise
        """
        if key_id not in self.key_metadata or key_id not in self.encrypted_keys:
            raise ValueError("Key not found.")

        public_pem = self.key_metadata[key_id].public_key_pem.encode()
        public_key = serialization.load_pem_public_key(public_pem, backend=default_backend())
        try:
            if isinstance(public_key, ec.EllipticCurvePublicKey):
                public_key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
            elif hasattr(public_key, "verify"):  # RSA/Ed25519
                public_key.verify(signature, message)
            else:  # pragma: no cover - defensive fallback
                raise ValueError("Unsupported public key type for verification")
            return True
        except InvalidSignature:
            return False
    def rotate_key(self, old_key_id: str, user_id: str = "system") -> str:
        """
        Rotate a key by generating a new one and deactivating the old.

        Args:
            old_key_id: ID of key to rotate
            user_id: ID of user requesting rotation

        Returns:
            new_key_id: ID of newly generated key
        """
        try:
            old_metadata = self.key_metadata.get(old_key_id)
            if not old_metadata:
                raise ValueError(f"Key {old_key_id} not found")

            # Generate new key with same parameters
            multisig_config = None
            if old_metadata.multisig_threshold and old_metadata.multisig_total:
                multisig_config = (old_metadata.multisig_threshold, old_metadata.multisig_total)

            new_key_id = self.generate_key(
                key_type=old_metadata.key_type,
                purpose=old_metadata.purpose,
                user_id=user_id,
                multisig_config=multisig_config
            )

            # Deactivate old key
            old_metadata.is_active = False
            self._save_metadata()

            self._audit_log(
                operation="rotate_key",
                key_id=old_key_id,
                user_id=user_id,
                success=True,
                details={"new_key_id": new_key_id}
            )

            return new_key_id

        except ValueError as e:
            self.logger.debug(
                "ValueError in rotate_key",
                extra={
                    "error_type": "ValueError",
                    "error": str(e),
                    "function": "rotate_key"
                }
            )
            self._audit_log(
                operation="rotate_key",
                key_id=old_key_id,
                user_id=user_id,
                success=False,
                details={"error": str(e), "error_type": "validation"}
            )
            raise HSMKeyRotationError(f"Invalid key rotation parameters: {e}") from e
        except HSMKeyGenerationError as e:
            self.logger.error(
                "HSMKeyGenerationError in rotate_key",
                extra={
                    "error_type": "HSMKeyGenerationError",
                    "error": str(e),
                    "function": "rotate_key"
                }
            )
            self._audit_log(
                operation="rotate_key",
                key_id=old_key_id,
                user_id=user_id,
                success=False,
                details={"error": str(e), "error_type": "key_generation"}
            )
            raise HSMKeyRotationError(f"Key rotation failed during key generation: {e}") from e
        except OSError as e:
            self.logger.error(
                "OSError in rotate_key",
                extra={
                    "error_type": "OSError",
                    "error": str(e),
                    "function": "rotate_key"
                }
            )
            self._audit_log(
                operation="rotate_key",
                key_id=old_key_id,
                user_id=user_id,
                success=False,
                details={"error": str(e), "error_type": "storage"}
            )
            raise HSMStorageError(f"Failed to persist key rotation: {e}") from e
        except (RuntimeError, MemoryError, AttributeError) as e:
            self._audit_log(
                operation="rotate_key",
                key_id=old_key_id,
                user_id=user_id,
                success=False,
                details={"error": str(e), "error_type": "unknown"}
            )
            self.logger.error(
                "Key rotation failed",
                exc_info=True,
                extra={"event": "hsm.key_rotation_failed", "old_key_id": old_key_id[:16], "user_id": user_id, "error_type": type(e).__name__}
            )
            raise HSMKeyRotationError(f"Key rotation failed: {e}") from e

    def get_public_key(self, key_id: str) -> str:
        """Get public key PEM for a given key ID"""
        metadata = self.key_metadata.get(key_id)
        if not metadata:
            raise ValueError(f"Key {key_id} not found")
        return metadata.public_key_pem

    def list_keys(self, active_only: bool = True) -> list[Dict]:
        """List all keys with metadata"""
        keys = []
        for metadata in self.key_metadata.values():
            if active_only and not metadata.is_active:
                continue
            keys.append({
                "key_id": metadata.key_id,
                "key_type": metadata.key_type.value,
                "purpose": metadata.purpose.value,
                "created_at": metadata.created_at,
                "is_active": metadata.is_active,
                "requires_rotation": self._requires_rotation(metadata)
            })
        return keys

    def multisig_sign(
        self,
        key_ids: list[str],
        message: bytes,
        user_id: str = "system"
    ) -> list[tuple[str, bytes]]:
        """
        Create multiple signatures for multisig transaction.

        Args:
            key_ids: List of key IDs to sign with
            message: Message to sign
            user_id: User requesting signatures

        Returns:
            List of (key_id, signature) tuples
        """
        signatures = []
        for key_id in key_ids:
            signature = self.sign(key_id, message, user_id)
            signatures.append((key_id, signature))

        return signatures

    def verify_multisig(
        self,
        signatures: list[tuple[str, bytes]],
        message: bytes,
        threshold: int
    ) -> bool:
        """
        Verify that enough valid signatures exist for multisig.

        Args:
            signatures: List of (key_id, signature) tuples
            message: Original message
            threshold: Minimum required valid signatures

        Returns:
            True if threshold met with valid signatures
        """
        valid_count = 0

        for key_id, signature in signatures:
            try:
                metadata = self.key_metadata.get(key_id)
                if not metadata:
                    continue

                # Load public key and verify
                public_pem = metadata.public_key_pem.encode()
                public_key = serialization.load_pem_public_key(public_pem, default_backend())

                if isinstance(public_key, ec.EllipticCurvePublicKey):
                    public_key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
                    valid_count += 1
                elif isinstance(public_key, ed25519.Ed25519PublicKey):
                    public_key.verify(signature, message)
                    valid_count += 1
                elif isinstance(public_key, rsa.RSAPublicKey):
                    from cryptography.hazmat.primitives.asymmetric import padding
                    public_key.verify(
                        signature,
                        message,
                        padding.PSS(
                            mgf=padding.MGF1(hashes.SHA256()),
                            salt_length=padding.PSS.MAX_LENGTH
                        ),
                        hashes.SHA256()
                    )
                    valid_count += 1

            except InvalidSignature:
                continue
            except (ValueError, TypeError) as e:
                logging.debug(
                    "Invalid signature parameters for key %s: %s",
                    key_id,
                    e,
                    extra={"event": "hsm.multisig_verify_invalid_params", "key_id": key_id[:16]}
                )
                continue
            except OSError as e:
                logging.warning(
                    "Storage error during signature verification for key %s: %s",
                    key_id,
                    e,
                    extra={"event": "hsm.multisig_verify_storage_error", "key_id": key_id[:16]}
                )
                continue
            except (RuntimeError, MemoryError, AttributeError, KeyError) as e:
                logging.error(
                    "Signature verification failed for key %s: %s",
                    key_id,
                    e,
                    exc_info=True,
                    extra={"event": "hsm.multisig_verify_failed", "key_id": key_id[:16], "error_type": type(e).__name__}
                )
                continue

        return valid_count >= threshold

    def get_audit_logs(self, limit: int = 100) -> list[Dict]:
        """Retrieve recent audit log entries"""
        logs = []
        if not self.audit_log_file.exists():
            return logs

        with open(self.audit_log_file, "r") as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                logs.append(json.loads(line.strip()))

        return logs

    # Private helper methods

    def _generate_key_id(self) -> str:
        """Generate unique key ID"""
        return f"hsm_key_{secrets.token_hex(16)}"

    def _encrypt_and_store_key(self, key_id: str, private_pem: bytes) -> None:
        """Encrypt private key and store securely"""
        nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
        ciphertext = self.aesgcm.encrypt(nonce, private_pem, None)

        # Store as: nonce (12 bytes) + ciphertext
        encrypted_data = nonce + ciphertext
        self.encrypted_keys[key_id] = encrypted_data
        self._save_encrypted_keys()

    def _load_private_key(self, key_id: str):
        """Load and decrypt private key"""
        encrypted_data = self.encrypted_keys.get(key_id)
        if not encrypted_data:
            raise ValueError(f"Key {key_id} not found in storage")

        # Extract nonce and ciphertext
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]

        # Decrypt
        private_pem = self.aesgcm.decrypt(nonce, ciphertext, None)

        # Load private key
        return serialization.load_pem_private_key(
            private_pem,
            password=None,
            backend=default_backend()
        )

    def _requires_rotation(self, metadata: KeyMetadata) -> bool:
        """Check if key requires rotation"""
        if not metadata.rotation_date:
            return False
        rotation_date = datetime.fromisoformat(metadata.rotation_date)
        return datetime.utcnow() > rotation_date

    def _save_metadata(self) -> None:
        """Save key metadata to disk"""
        data = {}
        for key_id, metadata in self.key_metadata.items():
            data[key_id] = {
                "key_id": metadata.key_id,
                "key_type": metadata.key_type.value,
                "purpose": metadata.purpose.value,
                "created_at": metadata.created_at,
                "last_used": metadata.last_used,
                "rotation_date": metadata.rotation_date,
                "is_active": metadata.is_active,
                "multisig_threshold": metadata.multisig_threshold,
                "multisig_total": metadata.multisig_total,
                "public_key_pem": metadata.public_key_pem
            }

        with open(self.metadata_file, "w") as f:
            json.dump(data, f, indent=2)

    def _load_metadata(self) -> dict[str, KeyMetadata]:
        """Load key metadata from disk"""
        if not self.metadata_file.exists():
            return {}

        with open(self.metadata_file, "r") as f:
            data = json.load(f)

        metadata = {}
        for key_id, item in data.items():
            metadata[key_id] = KeyMetadata(
                key_id=item["key_id"],
                key_type=KeyType(item["key_type"]),
                purpose=KeyPurpose(item["purpose"]),
                created_at=item["created_at"],
                last_used=item["last_used"],
                rotation_date=item.get("rotation_date"),
                is_active=item["is_active"],
                multisig_threshold=item.get("multisig_threshold"),
                multisig_total=item.get("multisig_total"),
                public_key_pem=item["public_key_pem"]
            )

        return metadata

    def _save_encrypted_keys(self) -> None:
        """Save encrypted keys to disk"""
        # Serialize as binary file
        with open(self.keys_file, "wb") as f:
            # Write count
            f.write(len(self.encrypted_keys).to_bytes(4, 'big'))

            for key_id, encrypted_data in self.encrypted_keys.items():
                # Write key_id length and key_id
                key_id_bytes = key_id.encode()
                f.write(len(key_id_bytes).to_bytes(2, 'big'))
                f.write(key_id_bytes)

                # Write encrypted data length and data
                f.write(len(encrypted_data).to_bytes(4, 'big'))
                f.write(encrypted_data)

    def _load_encrypted_keys(self) -> dict[str, bytes]:
        """Load encrypted keys from disk"""
        if not self.keys_file.exists():
            return {}

        encrypted_keys = {}
        with open(self.keys_file, "rb") as f:
            # Read count
            count = int.from_bytes(f.read(4), 'big')

            for _ in range(count):
                # Read key_id
                key_id_len = int.from_bytes(f.read(2), 'big')
                key_id = f.read(key_id_len).decode()

                # Read encrypted data
                data_len = int.from_bytes(f.read(4), 'big')
                encrypted_data = f.read(data_len)

                encrypted_keys[key_id] = encrypted_data

        return encrypted_keys
