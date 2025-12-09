"""
SPV proof verification tests for atomic swaps.
"""

from xai.core.aixn_blockchain.atomic_swap_11_coins import CrossChainVerifier


def test_spv_proof_success():
    verifier = CrossChainVerifier()
    tx_hash = "aa" * 32
    # simple two-branch merkle: hash(hash(tx + b1) + b2) == expected root
    b1 = "bb" * 32
    b2 = "cc" * 32
    current = tx_hash
    import hashlib

    combined1 = current + b1
    h1 = hashlib.sha256(hashlib.sha256(combined1.encode()).digest()).hexdigest()
    combined2 = h1 + b2
    merkle_root = hashlib.sha256(hashlib.sha256(combined2.encode()).digest()).hexdigest()
    block_header = {"merkle_root": merkle_root}

    ok, msg = verifier.verify_spv_proof("BTC", tx_hash, [b1, b2], block_header)
    assert ok is True
    assert "successfully" in msg


def test_spv_proof_mismatch():
    verifier = CrossChainVerifier()
    tx_hash = "aa" * 32
    b1 = "bb" * 32
    block_header = {"merkle_root": "ff" * 32}
    ok, msg = verifier.verify_spv_proof("BTC", tx_hash, [b1], block_header)
    assert ok is False
    assert "merkle root mismatch" in msg
