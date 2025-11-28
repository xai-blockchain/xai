from xai.core.crypto_utils import (
    deterministic_keypair_from_seed,
    sign_message_hex,
    verify_signature_hex,
    derive_public_key_hex,
)
from xai.core.block_header import BlockHeader


def test_deterministic_keypair_from_seed_is_stable():
    seed = b"p2p-deterministic-seed-32bytes----"
    priv1, pub1 = deterministic_keypair_from_seed(seed)
    priv2, pub2 = deterministic_keypair_from_seed(seed)
    assert priv1 == priv2
    assert pub1 == pub2
    # Derived public matches direct result
    assert derive_public_key_hex(priv1) == pub1


def test_signature_roundtrip_and_length():
    seed = b"signature-seed-vector-1234567890abcd"
    priv, pub = deterministic_keypair_from_seed(seed)
    message = b"deterministic test message"
    sig = sign_message_hex(priv, message)
    # Raw signature is 64 bytes -> 128 hex chars
    assert len(sig) == 128
    assert verify_signature_hex(pub, message, sig) is True
    # Tampering fails verification
    tampered = sig[:-2] + ("00" if sig[-2:] != "00" else "ff")
    assert verify_signature_hex(pub, message, tampered) is False


def test_block_header_hash_is_deterministic():
    header = BlockHeader(
        index=10,
        previous_hash="00" * 32,
        merkle_root="11" * 32,
        timestamp=1700000000.0,
        difficulty=4,
        nonce=42,
    )
    expected = header.calculate_hash()
    # Recalculate must match stored hash and deterministic string ordering
    assert header.hash == expected
    header_again = BlockHeader(
        index=10,
        previous_hash="00" * 32,
        merkle_root="11" * 32,
        timestamp=1700000000.0,
        difficulty=4,
        nonce=42,
    )
    assert header_again.hash == expected
