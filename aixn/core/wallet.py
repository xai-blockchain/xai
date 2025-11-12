"""
XAI Wallet - Real cryptocurrency wallet with ECDSA cryptography, encrypted storage, and helpers.
"""

from __future__ import annotations

import hashlib
import json
import os
from base64 import b64decode, b64encode
from pathlib import Path
from typing import Optional, Dict

import ecdsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from config import Config


class Wallet:
    """Real cryptocurrency wallet with public/private key cryptography"""

    def __init__(self, private_key: Optional[str] = None):
        if private_key:
            self.private_key = private_key
            self.public_key = self._derive_public_key(private_key)
        else:
            self.private_key, self.public_key = self._generate_keypair()

        self.address = self._generate_address(self.public_key)
        self.risk_score = 0.0
        self.risk_level = 'clean'
        self.flag_reasons = []

    def _generate_keypair(self) -> tuple[str, str]:
        """Generate new ECDSA keypair"""
        sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
        vk = sk.get_verifying_key()

        private_key = sk.to_string().hex()
        public_key = vk.to_string().hex()

        return private_key, public_key

    def _derive_public_key(self, private_key: str) -> str:
        """Derive public key from private key"""
        sk = ecdsa.SigningKey.from_string(bytes.fromhex(private_key), curve=ecdsa.SECP256k1)
        vk = sk.get_verifying_key()
        return vk.to_string().hex()

    def _generate_address(self, public_key: str) -> str:
        """Generate XAI address from public key"""
        pub_hash = hashlib.sha256(public_key.encode()).hexdigest()
        return f"XAI{pub_hash[:40]}"

    def sign_message(self, message: str) -> str:
        """Sign a message with private key"""
        sk = ecdsa.SigningKey.from_string(bytes.fromhex(self.private_key), curve=ecdsa.SECP256k1)
        signature = sk.sign(message.encode())
        return signature.hex()

    def verify_signature(self, message: str, signature: str, public_key: str) -> bool:
        """Verify a signature"""
        try:
            vk = ecdsa.VerifyingKey.from_string(bytes.fromhex(public_key), curve=ecdsa.SECP256k1)
            return vk.verify(bytes.fromhex(signature), message.encode())
        except Exception:
            return False

    def save_to_file(self, filename: str, password: Optional[str] = None):
        """Save wallet to encrypted file"""
        wallet_data = {
            'private_key': self.private_key,
            'public_key': self.public_key,
            'address': self.address
        }

        if password:
            encrypted_payload = self._encrypt_payload(json.dumps(wallet_data), password)
            stored = {'encrypted': True, 'version': 1, 'payload': encrypted_payload}
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(stored, f)
        else:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(wallet_data, f, indent=2)

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive AES key from password and salt"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=390_000
        )
        return kdf.derive(password.encode())

    def _encrypt_payload(self, data: str, password: str) -> Dict[str, str]:
        """Encrypt JSON payload using AES-GCM"""
        salt = os.urandom(16)
        key = self._derive_key(password, salt)
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data.encode(), None)
        return {
            'salt': b64encode(salt).decode(),
            'nonce': b64encode(nonce).decode(),
            'ciphertext': b64encode(ciphertext).decode()
        }

    def _decrypt_payload(self, payload: Dict[str, str], password: str) -> str:
        """Decrypt payload and return plaintext"""
        salt = b64decode(payload['salt'])
        nonce = b64decode(payload['nonce'])
        ciphertext = b64decode(payload['ciphertext'])
        key = self._derive_key(password, salt)
        aesgcm = AESGCM(key)
        decrypted = aesgcm.decrypt(nonce, ciphertext, None)
        return decrypted.decode()

    @staticmethod
    def _legacy_decrypt(encrypted_hex: str, password: str) -> str:
        """Legacy XOR decryption (for backward compatibility)"""
        key = hashlib.sha256(password.encode()).digest()
        encrypted = bytes.fromhex(encrypted_hex)
        decrypted = bytearray()
        for i, byte in enumerate(encrypted):
            decrypted.append(byte ^ key[i % len(key)])
        return decrypted.decode()

    @staticmethod
    def load_from_file(filename: str, password: Optional[str] = None) -> 'Wallet':
        """Load wallet from file"""
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if data.get('encrypted'):
            if not password:
                raise ValueError("Password required for encrypted wallet")
            payload = data.get('payload')
            if isinstance(payload, dict):
                wallet_json = Wallet()._decrypt_payload(payload, password)
            else:
                wallet_json = Wallet._legacy_decrypt(payload, password)
            wallet_data = json.loads(wallet_json)
        else:
            wallet_data = data

        return Wallet(private_key=wallet_data['private_key'])

    def to_dict(self) -> dict:
        """Export wallet data (WARNING: includes private key!)"""
        return {
            'address': self.address,
            'public_key': self.public_key,
            'private_key': self.private_key
        }

    def to_public_dict(self) -> dict:
        """Export public wallet data only"""
        return {
            'address': self.address,
            'public_key': self.public_key
        }


class WalletManager:
    """Manage multiple wallets"""

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            self.data_dir = Path.home() / '.aixn' / 'wallets'
        else:
            self.data_dir = Path(data_dir)

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.wallets: Dict[str, Wallet] = {}

    def create_wallet(self, name: str, password: Optional[str] = None) -> Wallet:
        """Create new wallet"""
        wallet = Wallet()
        self.wallets[name] = wallet

        filename = self.data_dir / f"{name}.wallet"
        wallet.save_to_file(str(filename), password or Config.WALLET_PASSWORD)

        return wallet

    def load_wallet(self, name: str, password: Optional[str] = None) -> Wallet:
        """Load wallet from file"""
        filename = self.data_dir / f"{name}.wallet"
        if not filename.exists():
            raise FileNotFoundError(f"Wallet '{name}' not found")

        wallet = Wallet.load_from_file(str(filename), password or Config.WALLET_PASSWORD)
        self.wallets[name] = wallet
        return wallet

    def list_wallets(self) -> list:
        """List all wallet files"""
        return [f.stem for f in self.data_dir.glob('*.wallet')]

    def get_wallet(self, name: str) -> Optional[Wallet]:
        """Get loaded wallet"""
        return self.wallets.get(name)


if __name__ == "__main__":
    print("Creating new XAI wallet...")
    wallet = Wallet()
    print("Wallet created.")
