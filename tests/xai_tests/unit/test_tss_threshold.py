"""
Unit tests for MockTSS threshold signing.

Coverage targets:
- Key generation thresholds
- Distributed signing success/failure based on collected signatures
- Verification against master public key
"""

import hashlib
import json

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend

from xai.security.tss import MockTSS


def _message_hash():
    payload = {"tx": "1", "amount": 10}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).digest()


def _sign(priv_hex: str, message_hash: bytes) -> str:
    priv = serialization.load_pem_private_key(bytes.fromhex(priv_hex), password=None, backend=default_backend())
    return priv.sign(message_hash, ec.ECDSA(hashes.SHA256())).hex()


def test_generate_keys_threshold_validation():
    tss = MockTSS()
    shares = tss.generate_distributed_keys(num_participants=3, threshold=2)
    assert len(shares) == 3
    assert tss._master_public_key == shares[0]["public_key"]
    with pytest.raises(ValueError):
        tss.generate_distributed_keys(num_participants=1, threshold=2)


def test_distributed_sign_success_and_failure():
    tss = MockTSS()
    shares = tss.generate_distributed_keys(num_participants=3, threshold=2)
    message_hash = _message_hash()

    sigs = []
    for pid, (priv_hex, pub_hex) in tss._participants_keys.items():
        sigs.append((_sign(priv_hex, message_hash), pub_hex))

    combined = tss.distributed_sign(message_hash, sigs[:2], threshold=2)
    assert combined

    # Insufficient valid signatures
    with pytest.raises(ValueError):
        tss.distributed_sign(message_hash, sigs[:1], threshold=2)


def test_verify_threshold_signature():
    tss = MockTSS()
    tss.generate_distributed_keys(num_participants=2, threshold=1)
    message_hash = _message_hash()
    sig = "deadbeef"
    assert tss.verify_threshold_signature(message_hash, sig, tss._master_public_key) is True
    assert tss.verify_threshold_signature(message_hash, "", tss._master_public_key) is False
