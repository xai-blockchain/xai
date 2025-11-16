"""
Simple audit signer using ECDSA (secp256k1) for proving order/event authenticity.
"""

import os
from pathlib import Path
from hashlib import sha256
from typing import Optional

import ecdsa


class AuditSigner:
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.key_path = self.data_dir / "audit_key.pem"
        self._key: Optional[ecdsa.SigningKey] = None
        self._load_or_generate()

    def _load_or_generate(self):
        if self.key_path.exists():
            with open(self.key_path, "rb") as f:
                self._key = ecdsa.SigningKey.from_pem(f.read())
        else:
            self._key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
            with open(self.key_path, "wb") as f:
                f.write(self._key.to_pem())

    def sign(self, payload: str) -> str:
        if not self._key:
            self._load_or_generate()
        digest = sha256(payload.encode()).digest()
        return self._key.sign(digest).hex()

    def public_key(self) -> str:
        if not self._key:
            self._load_or_generate()
        return self._key.get_verifying_key().to_string("compressed").hex()
