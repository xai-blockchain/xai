#!/usr/bin/env python3
"""
Microbenchmarks for crypto-heavy paths: signature verification and block serialization.
"""
import timeit
from xai.core.crypto_utils import generate_secp256k1_keypair_hex, sign_message_hex, verify_signature_hex
from xai.core.block_header import BlockHeader


def bench_verify_signatures(iterations: int = 1000) -> float:
    priv, pub = generate_secp256k1_keypair_hex()
    message = b"benchmark-message"
    sig = sign_message_hex(priv, message)
    timer = timeit.Timer(lambda: verify_signature_hex(pub, message, sig))
    return timer.timeit(number=iterations) / iterations


def bench_block_header_serialize(iterations: int = 1000) -> float:
    header = BlockHeader(
        index=1,
        previous_hash="0" * 64,
        timestamp=1704067200.0,
        merkle_root="f" * 64,
        difficulty=4,
        nonce=12345,
        miner_pubkey="02" + "a" * 64,
    )
    timer = timeit.Timer(lambda: header.to_dict())
    return timer.timeit(number=iterations) / iterations


if __name__ == "__main__":
    sig_ms = bench_verify_signatures() * 1000
    ser_ms = bench_block_header_serialize() * 1000
    print(f"Signature verify avg: {sig_ms:.4f} ms")
    print(f"Block header serialize avg: {ser_ms:.4f} ms")
