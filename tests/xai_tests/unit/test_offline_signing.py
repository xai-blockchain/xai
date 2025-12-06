"""
Unit tests for offline signing helpers.
"""

import pytest

from xai.wallet.offline_signing import sign_offline, signing_preview, verify_offline_signature


def test_offline_sign_and_verify_roundtrip():
    tx = {
        "recipient": "XAI" + "b" * 40,
        "amount": 12.34,
        "fee": 0.01,
        "nonce": 7,
        "tx_type": "normal",
        "metadata": {"note": "test"},
        "timestamp": 1_700_000_000.0,
    }
    # Use a random-looking private key for test (hex string length 64)
    private_key_hex = "1" * 64
    from hashlib import sha256
    from xai.core.crypto_utils import derive_public_key_hex

    pub_key = derive_public_key_hex(private_key_hex)
    sender = "XAI" + sha256(bytes.fromhex(pub_key)).hexdigest()[:40]
    tx["sender"] = sender

    _, tx_hash, _ = signing_preview(tx)
    ack_prefix = tx_hash[:12]
    signed = sign_offline(tx, private_key_hex, acknowledged_digest=ack_prefix)

    assert "signature" in signed and "public_key" in signed
    assert signed["txid"] == tx_hash
    # Verify signature against canonical payload
    assert verify_offline_signature(signed) is True


def test_sign_offline_requires_acknowledgement():
    tx = {
        "sender": "XAI" + "c" * 40,
        "recipient": "XAI" + "d" * 40,
        "amount": 1.0,
        "fee": 0.0,
        "nonce": 1,
        "tx_type": "normal",
        "timestamp": 1_700_000_100.0,
    }
    private_key_hex = "2" * 64
    with pytest.raises(ValueError):
        sign_offline(tx, private_key_hex, acknowledged_digest="")  # too short
