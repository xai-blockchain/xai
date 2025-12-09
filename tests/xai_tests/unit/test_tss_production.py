"""
Unit tests for ProductionTSS and ShamirSecretSharing (production variant).

Coverage targets:
- Secret splitting/reconstruction and share validation
- Distributed key generation parameter validation
- Threshold signing success/failure and verification
"""

import hashlib
import json

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend

from xai.security.tss_production import (
    ProductionTSS,
    ShamirSecretSharing,
    SecretShare,
    TSSKeyShare,
)


def _message_hash():
    payload = {"tx": "1", "amount": 5}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).digest()


def test_split_and_reconstruct_secret():
    secret = 123456
    shares = ShamirSecretSharing.split_secret(secret, threshold=2, num_shares=3)
    assert len(shares) == 3
    reconstructed = ShamirSecretSharing.reconstruct_secret(shares[:2])
    assert reconstructed == secret
    with pytest.raises(ValueError):
        ShamirSecretSharing.split_secret(secret, threshold=4, num_shares=3)


def test_verify_share_consistency():
    shares = ShamirSecretSharing.split_secret(42, threshold=2, num_shares=3)
    assert ShamirSecretSharing.verify_share(shares[0], [shares[1]], shares) is True


def _sign(priv_hex: str, msg_hash: bytes) -> str:
    priv = serialization.load_pem_private_key(bytes.fromhex(priv_hex), password=None, backend=default_backend())
    return priv.sign(msg_hash, ec.ECDSA(hashes.SHA256())).hex()


def test_production_tss_generate_and_sign(monkeypatch):
    tss = ProductionTSS()
    shares, master_pub = tss.generate_distributed_keys(num_participants=3, threshold=2)
    assert len(shares) == 3
    message = b"hello"
    monkeypatch.setattr("xai.security.tss_production.secrets.randbelow", lambda *args, **kwargs: 5)

    # Create partial signatures using first two shares
    partials = []
    for share in shares[:2]:
        r_s = tss.create_partial_signature(share, message)
        partials.append((share.share_index, share, r_s))

    combined = tss.combine_partial_signatures(partials, threshold=2)
    assert combined
    assert tss.verify_threshold_signature(master_pub, message, combined) is True

    with pytest.raises(ValueError):
        tss.generate_distributed_keys(num_participants=1, threshold=2)
    with pytest.raises(ValueError):
        tss.combine_partial_signatures(partials[:1], threshold=2)


def test_combine_partial_signatures_rejects_inconsistent_r():
    tss = ProductionTSS()
    share = TSSKeyShare(
        participant_id="p1",
        share_index=1,
        private_share=1,
        public_key=b"pub",
        verification_point=b"ver",
    )
    partials = [
        (1, share, (1, 2)),
        (2, share, (2, 3)),  # different r
    ]
    with pytest.raises(ValueError):
        tss.combine_partial_signatures(partials, threshold=2)
