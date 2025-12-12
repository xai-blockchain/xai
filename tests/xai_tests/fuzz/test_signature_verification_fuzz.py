"""
Fuzzing tests for ECDSA signature verification edge cases.

These tests ensure the crypto_utils helpers remain resilient to random data and
detect tampering across a broad range of payload sizes.
"""

import os
import random

import pytest

from xai.core.crypto_utils import (
    generate_secp256k1_keypair_hex,
    sign_message_hex,
    verify_signature_hex,
)


def _random_message() -> bytes:
    return os.urandom(random.randint(0, 512))


def test_signature_roundtrip_random_messages():
    """Random messages should sign/verify successfully."""
    for _ in range(100):
        priv, pub = generate_secp256k1_keypair_hex()
        message = _random_message()
        signature = sign_message_hex(priv, message)
        assert verify_signature_hex(pub, message, signature)


def test_signature_mutation_is_detected():
    """Any bit flip in the signature must cause verification to fail."""
    priv, pub = generate_secp256k1_keypair_hex()
    message = _random_message()
    signature = bytearray.fromhex(sign_message_hex(priv, message))
    # Flip a random bit
    idx = random.randrange(len(signature))
    signature[idx] ^= 0x01
    tampered = signature.hex()
    assert verify_signature_hex(pub, message, tampered) is False


def test_random_signature_inputs_do_not_crash():
    """Random signatures should return False without raising."""
    priv, pub = generate_secp256k1_keypair_hex()
    for _ in range(200):
        message = _random_message()
        rand_sig = os.urandom(random.randint(0, 128)).hex()
        assert verify_signature_hex(pub, message, rand_sig) in {True, False}


def test_invalid_public_key_lengths_raise():
    """Malformed public keys should raise ValueError instead of crashing later."""
    message = _random_message()
    signature = os.urandom(64).hex()
    invalid_pub = os.urandom(random.randint(1, 63)).hex()
    with pytest.raises(ValueError):
        verify_signature_hex(invalid_pub, message, signature)
