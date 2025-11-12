"""
AXN Wallet - Real cryptocurrency wallet with ECDSA cryptography
"""

import ecdsa
import hashlib
import json
import os
from pathlib import Path
from typing import Optional, Dict


class Wallet:
    """Real cryptocurrency wallet with public/private key cryptography"""

    def __init__(self, private_key: Optional[str] = None):
        if private_key:
            # Load existing wallet
            self.private_key = private_key
            self.public_key = self._derive_public_key(private_key)
        else:
            # Generate new wallet
            self.private_key, self.public_key = self._generate_keypair()

        self.address = self._generate_address(self.public_key)

    def _generate_keypair(self) -> tuple:
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
        """Generate AXN address from public key"""
        # AXN addresses: AXN + first 40 chars of public key hash
        pub_hash = hashlib.sha256(public_key.encode()).hexdigest()
        return f"AXN{pub_hash[:40]}"

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
        except:
            return False

    def save_to_file(self, filename: str, password: Optional[str] = None):
        """Save wallet to encrypted file"""
        wallet_data = {
            'private_key': self.private_key,
            'public_key': self.public_key,
            'address': self.address
        }

        if password:
            # Simple encryption (in production, use proper key derivation)
            encrypted_data = self._encrypt(json.dumps(wallet_data), password)
            with open(filename, 'w') as f:
                json.dump({'encrypted': True, 'data': encrypted_data}, f)
        else:
            with open(filename, 'w') as f:
                json.dump(wallet_data, f, indent=2)

    def _encrypt(self, data: str, password: str) -> str:
        """Simple XOR encryption (use proper encryption in production)"""
        key = hashlib.sha256(password.encode()).digest()
        encrypted = bytearray()

        for i, char in enumerate(data.encode()):
            encrypted.append(char ^ key[i % len(key)])

        return encrypted.hex()

    def _decrypt(self, encrypted_hex: str, password: str) -> str:
        """Decrypt data"""
        key = hashlib.sha256(password.encode()).digest()
        encrypted = bytes.fromhex(encrypted_hex)
        decrypted = bytearray()

        for i, byte in enumerate(encrypted):
            decrypted.append(byte ^ key[i % len(key)])

        return decrypted.decode()

    @staticmethod
    def load_from_file(filename: str, password: Optional[str] = None) -> 'Wallet':
        """Load wallet from file"""
        with open(filename, 'r') as f:
            data = json.load(f)

        if data.get('encrypted'):
            if not password:
                raise ValueError("Password required for encrypted wallet")
            wallet_json = Wallet._decrypt_static(data['data'], password)
            wallet_data = json.loads(wallet_json)
        else:
            wallet_data = data

        return Wallet(private_key=wallet_data['private_key'])

    @staticmethod
    def _decrypt_static(encrypted_hex: str, password: str) -> str:
        """Static decrypt method"""
        key = hashlib.sha256(password.encode()).digest()
        encrypted = bytes.fromhex(encrypted_hex)
        decrypted = bytearray()

        for i, byte in enumerate(encrypted):
            decrypted.append(byte ^ key[i % len(key)])

        return decrypted.decode()

    def to_dict(self) -> dict:
        """Export wallet data (WARNING: includes private key!)"""
        return {
            'address': self.address,
            'public_key': self.public_key,
            'private_key': self.private_key  # NEVER share this!
        }

    def to_public_dict(self) -> dict:
        """Export public wallet data only"""
        return {
            'address': self.address,
            'public_key': self.public_key
        }


class WalletManager:
    """Manage multiple wallets"""

    def __init__(self, data_dir: str = None):
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

    def list_wallets(self) -> list:
        """List all wallet files"""
        return [f.stem for f in self.data_dir.glob('*.wallet')]

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
