"""
Unit tests for offline signing helpers.
"""

from xai.wallet.offline_signing import serialize_transaction_payload, sign_offline, verify_offline_signature


def test_offline_sign_and_verify_roundtrip():
    tx = {
        "sender": "XAI" + "a" * 40,
        "recipient": "XAI" + "b" * 40,
        "amount": 12.34,
        "fee": 0.01,
        "nonce": 7,
        "tx_type": "normal",
        "metadata": {"note": "test"},
    }
    # Use a random-looking private key for test (hex string length 64)
    private_key_hex = "1" * 64
    signed = sign_offline(tx, private_key_hex)
    assert "signature" in signed and "public_key" in signed
    # Verify signature against serialized payload
    assert verify_offline_signature(signed) is True

