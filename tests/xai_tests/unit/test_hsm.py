"""
Unit tests for HardwareSecurityModule (HSM) key lifecycle.

Coverage targets:
- Key generation for supported types
- Signing/verification and audit logging metadata
- Encryption key derivation and metadata persistence
"""

from pathlib import Path

import pytest

from xai.security.hsm import HardwareSecurityModule, KeyType, KeyPurpose, HSMSigningError


def _hsm(tmp_path: Path) -> HardwareSecurityModule:
    return HardwareSecurityModule(storage_path=str(tmp_path / "hsm"), master_password="secret")


def test_generate_key_and_metadata_persist(tmp_path):
    hsm = _hsm(tmp_path)
    key_id = hsm.generate_key(KeyType.SECP256K1, KeyPurpose.SIGNING, user_id="tester")
    assert key_id in hsm.key_metadata
    meta = hsm.key_metadata[key_id]
    assert meta.key_type == KeyType.SECP256K1
    assert meta.purpose == KeyPurpose.SIGNING
    # Reload to ensure persistence
    hsm2 = _hsm(tmp_path)
    assert key_id in hsm2.key_metadata


def test_sign_and_verify_round_trip(tmp_path):
    hsm = _hsm(tmp_path)
    key_id = hsm.generate_key(KeyType.ED25519, KeyPurpose.SIGNING)
    message = b"hello"
    signature = hsm.sign(key_id, message)
    assert hsm.verify_signature(key_id, message, signature) is True
    with pytest.raises(HSMSigningError):
        hsm.sign("unknown", message)
    with pytest.raises(ValueError):
        hsm.verify_signature("unknown", message, signature)


def test_encryption_key_derivation_changes_with_password(tmp_path):
    hsm1 = HardwareSecurityModule(storage_path=str(tmp_path / "h1"), master_password="a")
    hsm2 = HardwareSecurityModule(storage_path=str(tmp_path / "h2"), master_password="b")
    assert hsm1.encryption_key != hsm2.encryption_key
