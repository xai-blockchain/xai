"""Audit signer backed by secp256k1 keys using cryptography."""
from __future__ import annotations

import os
from hashlib import sha256
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


class AuditSigner:
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.key_path = self.data_dir / "audit_key.pem"
        self._key: ec.EllipticCurvePrivateKey | None = None
        self._load_or_generate()

    def _load_or_generate(self):
        if self.key_path.exists():
            with open(self.key_path, "rb") as f:
                self._key = serialization.load_pem_private_key(f.read(), password=None)
        else:
            self._key = ec.generate_private_key(ec.SECP256K1())
            with open(self.key_path, "wb") as f:
                f.write(
                    self._key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                )

    def sign(self, payload: str) -> str:
        if not self._key:
            self._load_or_generate()
        digest = sha256(payload.encode()).digest()
        signature = self._key.sign(digest, ec.ECDSA(hashes.SHA256()))
        return signature.hex()

    def public_key(self) -> str:
        if not self._key:
            self._load_or_generate()
        return self._key.public_key().public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.CompressedPoint,
        ).hex()
