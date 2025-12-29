import binascii

import pytest

from xai.core.security.crypto_utils import (
    _CURVE_ORDER,  # pylint: disable=protected-access
    canonicalize_signature_components,
    generate_secp256k1_keypair_hex,
    is_canonical_signature,
    sign_message_hex,
    verify_signature_hex,
)


def test_signatures_enforced_low_s_and_range():
    private_hex, public_hex = generate_secp256k1_keypair_hex()
    message = b"range-check"

    sig_hex = sign_message_hex(private_hex, message)
    raw = bytes.fromhex(sig_hex)
    r = int.from_bytes(raw[:32], "big")
    s = int.from_bytes(raw[32:], "big")

    assert 1 <= r < _CURVE_ORDER
    assert 1 <= s <= _CURVE_ORDER // 2  # low-S normalization applied
    assert is_canonical_signature(r, s) is True
    assert verify_signature_hex(public_hex, message, sig_hex) is True


@pytest.mark.parametrize(
    "r_bytes,s_bytes",
    [
        (b"\x00" * 32, b"\x01" * 32),  # r = 0
        (b"\x01" * 32, b"\x00" * 32),  # s = 0
        (b"\xff" * 32, b"\xff" * 32),  # r,s >= order
    ],
)
def test_verify_rejects_out_of_range_components(r_bytes: bytes, s_bytes: bytes):
    _, public_hex = generate_secp256k1_keypair_hex()
    message = b"reject-out-of-range"
    sig_hex = binascii.hexlify(r_bytes + s_bytes).decode()
    assert verify_signature_hex(public_hex, message, sig_hex) is False


def test_verify_rejects_high_s_malleability():
    private_hex, public_hex = generate_secp256k1_keypair_hex()
    message = b"high-s-blocked"
    sig_hex = sign_message_hex(private_hex, message)
    raw = bytearray.fromhex(sig_hex)
    r = raw[:32]
    # Force high-S by setting s to order - 1
    s_high = (_CURVE_ORDER - 1).to_bytes(32, "big")
    forged = binascii.hexlify(r + s_high).decode()
    assert is_canonical_signature(int.from_bytes(r, "big"), int.from_bytes(s_high, "big")) is False
    assert verify_signature_hex(public_hex, message, forged) is False


def test_canonicalize_signature_components_enforces_low_s():
    private_hex, _ = generate_secp256k1_keypair_hex()
    message = b"normalize"
    sig_hex = sign_message_hex(private_hex, message)
    raw = bytes.fromhex(sig_hex)
    r = int.from_bytes(raw[:32], "big")
    s = int.from_bytes(raw[32:], "big")

    canon_r, canon_s = canonicalize_signature_components(r, s)
    assert canon_r == r
    assert canon_s == s

    # Force high-S and ensure canonicalization adjusts
    s_high = _CURVE_ORDER - s
    canon_r2, canon_s2 = canonicalize_signature_components(r, s_high)
    assert canon_r2 == r
    assert canon_s2 == s
