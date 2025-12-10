"""
SPV proof verification tests for atomic swaps.
"""

import hashlib
from typing import List

from xai.core.aixn_blockchain.atomic_swap_11_coins import CrossChainVerifier


def _build_expected_root(tx_hash: str, siblings: List[str], tx_index: int) -> str:
    current = bytes.fromhex(tx_hash)[::-1]
    position = tx_index
    for sibling in siblings:
        sib_bytes = bytes.fromhex(sibling)[::-1]
        if position & 1:
            concat = sib_bytes + current
        else:
            concat = current + sib_bytes
        current = hashlib.sha256(hashlib.sha256(concat).digest()).digest()
        position >>= 1
    return current[::-1].hex()


def test_spv_proof_success():
    verifier = CrossChainVerifier()
    tx_hash = "aa" * 32
    siblings = ["bb" * 32, "cc" * 32]
    tx_index = 2
    block_header = {"merkle_root": _build_expected_root(tx_hash, siblings, tx_index)}

    ok, msg = verifier.verify_spv_proof("BTC", tx_hash, siblings, block_header, tx_index=tx_index)
    assert ok is True
    assert "successfully" in msg


def test_spv_proof_mismatch():
    verifier = CrossChainVerifier()
    tx_hash = "aa" * 32
    siblings = ["bb" * 32]
    block_header = {"merkle_root": "ff" * 32}
    ok, msg = verifier.verify_spv_proof("BTC", tx_hash, siblings, block_header, tx_index=0)
    assert ok is False
    assert "merkle root mismatch" in msg


def test_verify_transaction_spv_fetches_merkle_and_header(monkeypatch):
    verifier = CrossChainVerifier()
    tx_hash = "aa" * 32
    siblings = ["bb" * 32]
    tx_index = 0
    merkle_root = _build_expected_root(tx_hash, siblings, tx_index)

    def fake_get_json(url, params=None, timeout=None):
        assert "merkle-proof" in url
        return {"merkle": siblings, "pos": tx_index, "block_height": 100}

    header_hex = (
        (1).to_bytes(4, "little")
        + bytes.fromhex("11" * 32)[::-1]
        + bytes.fromhex(merkle_root)[::-1]
        + (1234567890).to_bytes(4, "little")
        + (0x1D00FFFF).to_bytes(4, "little")
        + (0).to_bytes(4, "little")
    ).hex()
    text_responses = ["0000deadbeef", header_hex]

    def fake_get_text(url, params=None, timeout=None):
        return text_responses.pop(0)

    monkeypatch.setattr(verifier, "_http_get_json", fake_get_json)
    monkeypatch.setattr(verifier, "_http_get_text", fake_get_text)

    ok, msg, data = verifier.verify_transaction_spv("BTC", tx_hash)
    assert ok is True
    assert data["merkle_root"] == merkle_root
    assert data["block_hash"] == "0000deadbeef"


def test_verify_transaction_spv_unsupported_coin():
    verifier = CrossChainVerifier()
    ok, msg, data = verifier.verify_transaction_spv("XMR", "aa" * 32)
    assert ok is False
    assert "not supported" in msg.lower()
