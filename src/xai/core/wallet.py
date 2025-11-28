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
from cryptography.fernet import Fernet
import hmac


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
        """Save wallet to encrypted file with HMAC integrity protection (TASK 57)"""
        wallet_data = {
            "private_key": self.private_key,
            "public_key": self.public_key,
            "address": self.address,
        }

        if password:
            payload = self._encrypt_payload(json.dumps(wallet_data), password)
            file_data = {"encrypted": True, "payload": payload}
        else:
            file_data = wallet_data

        # Add HMAC-SHA256 signature for integrity (TASK 57)
        file_json = json.dumps(file_data, sort_keys=True)
        hmac_key = hashlib.sha256(self.private_key.encode()).digest()
        signature = hmac.new(hmac_key, file_json.encode(), hashlib.sha256).hexdigest()

        final_data = {
            "data": file_data,
            "hmac_signature": signature,
            "version": "1.0"
        }

        with open(filename, "w") as f:
            json.dump(final_data, f, indent=2)

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
        """Load wallet from file with HMAC integrity verification (TASK 57)"""
        with open(filename, "r") as f:
            file_data = json.load(f)

        # Check if new format with HMAC signature (TASK 57)
        if "hmac_signature" in file_data:
            stored_signature = file_data["hmac_signature"]
            data = file_data["data"]

            # We'll verify HMAC after we load the wallet
            # Store signature for later verification
            needs_hmac_verification = True
            hmac_signature = stored_signature
            file_json = json.dumps(data, sort_keys=True)
        else:
            # Old format without HMAC
            data = file_data
            needs_hmac_verification = False

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

        wallet = Wallet(private_key=wallet_data["private_key"])

        # Verify HMAC if present (TASK 57)
        if needs_hmac_verification:
            hmac_key = hashlib.sha256(wallet.private_key.encode()).digest()
            expected_signature = hmac.new(hmac_key, file_json.encode(), hashlib.sha256).hexdigest()

            if expected_signature != hmac_signature:
                raise ValueError("Wallet file integrity check failed: HMAC mismatch (file may be tampered)")

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
        Encode bytes to base58.

        Args:
            data: Bytes to encode

        Returns:
            Base58 string
        """
        alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        num = int.from_bytes(data, 'big')

        if num == 0:
            return alphabet[0]

        result = ""
        while num > 0:
            num, remainder = divmod(num, 58)
            result = alphabet[remainder] + result

        # Add leading zeros
        for byte in data:
            if byte == 0:
                result = alphabet[0] + result
            else:
                break

        return result

    @staticmethod
    def _base58_decode(string: str) -> bytes:
        """
        Decode base58 string to bytes.

        Args:
            string: Base58 string

        Returns:
            Decoded bytes

        Raises:
            ValueError: If string contains invalid characters
        """
        alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        num = 0

        for char in string:
            if char not in alphabet:
                raise ValueError(f"Invalid base58 character: {char}")
            num = num * 58 + alphabet.index(char)

        # Convert to bytes
        result = num.to_bytes((num.bit_length() + 7) // 8, 'big')

        # Add leading zero bytes
        for char in string:
            if char == alphabet[0]:
                result = b'\x00' + result
            else:
                break

        return result


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
