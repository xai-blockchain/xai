"""Utility helpers for secp256k1 key management and signatures."""

from __future__ import annotations

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)

_CURVE = ec.SECP256K1()
_CURVE_ORDER = int("FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141", 16)

def _normalize_private_value(value: int) -> int:
    normalized = value % _CURVE_ORDER
    if normalized == 0:
        normalized = 1
    return normalized

def _private_key_to_hex(private_key: ec.EllipticCurvePrivateKey) -> str:
    return private_key.private_numbers().private_value.to_bytes(32, "big").hex()

def _public_key_to_hex(public_key: ec.EllipticCurvePublicKey) -> str:
    numbers = public_key.public_numbers()
    return (numbers.x.to_bytes(32, "big") + numbers.y.to_bytes(32, "big")).hex()

def load_private_key_from_hex(private_hex: str) -> ec.EllipticCurvePrivateKey:
    return ec.derive_private_key(_normalize_private_value(int(private_hex, 16)), _CURVE)

def load_public_key_from_hex(public_hex: str) -> ec.EllipticCurvePublicKey:
    raw = bytes.fromhex(public_hex)
    if len(raw) != 64:
        raise ValueError("Public key hex must be 64 bytes (uncompressed without prefix).")
    return ec.EllipticCurvePublicKey.from_encoded_point(_CURVE, b"\x04" + raw)

def generate_secp256k1_keypair_hex() -> tuple[str, str]:
    private_key = ec.generate_private_key(_CURVE)
    public_key = private_key.public_key()
    return _private_key_to_hex(private_key), _public_key_to_hex(public_key)

def derive_public_key_hex(private_hex: str) -> str:
    private_key = load_private_key_from_hex(private_hex)
    return _public_key_to_hex(private_key.public_key())

def deterministic_keypair_from_seed(seed: bytes) -> tuple[str, str]:
    if len(seed) < 32:
        seed = seed.ljust(32, b"\x00")
    private_value = _normalize_private_value(int.from_bytes(seed[:32], "big"))
    private_key = ec.derive_private_key(private_value, _CURVE)
    return _private_key_to_hex(private_key), _public_key_to_hex(private_key.public_key())

def _validate_signature_range(r: int, s: int) -> None:
    """
    Ensure signature components fall within the curve order.

    Raises:
        ValueError: If either component is out of range.
    """
    if not (1 <= r < _CURVE_ORDER):
        raise ValueError("Signature r component out of range.")
    if not (1 <= s < _CURVE_ORDER):
        raise ValueError("Signature s component out of range.")

def canonicalize_signature_components(r: int, s: int) -> tuple[int, int]:
    """
    Normalize signature components to canonical low-S form.

    Args:
        r: Signature r component
        s: Signature s component

    Returns:
        Tuple of canonical (r, s)
    """
    _validate_signature_range(r, s)
    if s > _CURVE_ORDER // 2:
        s = _CURVE_ORDER - s
    return r, s

def is_canonical_signature(r: int, s: int) -> bool:
    """
    Check whether signature components are already canonical.

    Args:
        r: Signature r component
        s: Signature s component

    Returns:
        True if components fall within range and have low-S form.
    """
    try:
        _validate_signature_range(r, s)
    except ValueError:
        return False
    return s <= _CURVE_ORDER // 2

def sign_message_hex(private_hex: str, message: bytes) -> str:
    private_key = load_private_key_from_hex(private_hex)
    der_signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der_signature)
    r, s = canonicalize_signature_components(r, s)
    return (r.to_bytes(32, "big") + s.to_bytes(32, "big")).hex()

def verify_signature_hex(public_hex: str, message: bytes, signature_hex: str) -> bool:
    public_key = load_public_key_from_hex(public_hex)
    try:
        raw_signature = bytes.fromhex(signature_hex)
        if len(raw_signature) != 64:
            return False
        r = int.from_bytes(raw_signature[:32], "big")
        s = int.from_bytes(raw_signature[32:], "big")
        if not is_canonical_signature(r, s):
            return False
        der_signature = encode_dss_signature(r, s)
        public_key.verify(der_signature, message, ec.ECDSA(hashes.SHA256()))
        return True
    except InvalidSignature:
        return False

def compressed_public_key_from_private(private_hex: str) -> str:
    private_key = load_private_key_from_hex(private_hex)
    compressed = private_key.public_key().public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.CompressedPoint,
    )
    return compressed.hex()
