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


import base64
from cryptography.fernet import Fernet


class Wallet:
    """Real cryptocurrency wallet with public/private key cryptography"""

    def __init__(self, private_key: Optional[str] = None, hardware_wallet: Optional[HardwareWallet] = None) -> None:
        self.hardware_wallet = hardware_wallet or (get_default_hardware_wallet() if HARDWARE_WALLET_ENABLED else None)

        if self.hardware_wallet:
            self.private_key = ""
            self.public_key = ""
            self.address = self.hardware_wallet.get_address()
        elif private_key:
            # Load existing wallet
            self.private_key = private_key
            self.public_key = self._derive_public_key(private_key)
            self.address = self._generate_address(self.public_key)
        else:
            # Generate new wallet
            self.private_key, self.public_key = self._generate_keypair()
            self.address = self._generate_address(self.public_key)

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
        of the public key.

        Args:
            public_key: The public key as a hex string.

        Returns:
            The generated XAI address string.
        """
        # XAI addresses: XAI + first 40 chars of public key hash
        pub_hash = hashlib.sha256(public_key.encode()).hexdigest()
        return f"XAI{pub_hash[:40]}"

    def sign_message(self, message: str) -> str:
        """
        Signs a message using the wallet's private key.

        Args:
            message: The message string to be signed.

        Returns:
            The signature as a hex string.
        """
        if self.hardware_wallet:
            signature = self.hardware_wallet.sign_transaction(message.encode())
            return signature.hex()

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
            print(f"An unexpected error occurred during signature verification: {exc}")
            return False

    def save_to_file(self, filename: str, password: Optional[str] = None) -> None:
        """Save wallet to encrypted file"""
        wallet_data = {
            "private_key": self.private_key,
            "public_key": self.public_key,
            "address": self.address,
        }

        if password:
            payload = self._encrypt_payload(json.dumps(wallet_data), password)
            with open(filename, "w") as f:
                json.dump({"encrypted": True, "payload": payload}, f)
        else:
            with open(filename, "w") as f:
                json.dump(wallet_data, f, indent=2)

    def _encrypt(self, data: str, password: str) -> str:
        """Encrypt data using Fernet symmetric encryption"""
        key = base64.urlsafe_b64encode(hashlib.sha256(password.encode()).digest())
        f = Fernet(key)
        encrypted_data = f.encrypt(data.encode())
        return encrypted_data.decode()

    def _decrypt(self, encrypted_data: str, password: str) -> str:
        """Decrypt data using Fernet symmetric encryption"""
        key = base64.urlsafe_b64encode(hashlib.sha256(password.encode()).digest())
        f = Fernet(key)
        decrypted_data = f.decrypt(encrypted_data.encode())
        return decrypted_data.decode()

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
        """Load wallet from file"""
        with open(filename, "r") as f:
            data = json.load(f)

        if data.get("encrypted"):
            if not password:
                raise ValueError("Password required for encrypted wallet")
            # Support both new payload format and old data format
            if "payload" in data:
                wallet_json = Wallet._decrypt_payload_static(data["payload"], password)
            else:
                wallet_json = Wallet._decrypt_static(data["data"], password)
            wallet_data = json.loads(wallet_json)
        else:
            wallet_data = data

        return Wallet(private_key=wallet_data["private_key"])

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


# Example usage
if __name__ == "__main__":
    # Create new wallet
    print("Creating new AXN wallet...")
    wallet = Wallet()

    print(f"\n✅ Wallet Created!")
    print(f"Address: {wallet.address}")
    print(f"Public Key: {wallet.public_key[:32]}...")
    print(f"Private Key: {wallet.private_key[:32]}... (KEEP SECRET!)")

    # Test signing
    message = "Hello AXN!"
    signature = wallet.sign_message(message)
    print(f"\nMessage: {message}")
    print(f"Signature: {signature[:64]}...")

    # Verify
    is_valid = wallet.verify_signature(message, signature, wallet.public_key)
    print(f"Signature Valid: {is_valid}")

    # Save wallet
    wallet.save_to_file("test_wallet.json")
    print(f"\n💾 Wallet saved to test_wallet.json")
