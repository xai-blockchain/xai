"""
Fuzzing tests for BlockHeader serialization/deserialization.

These tests ensure block header parsing remains resilient to random input
and maintain key invariants like hash linkage and deterministic canonical JSON.
"""

import json
import os
import random
import string

import pytest

from xai.core.block_header import BlockHeader, canonical_json


def _random_hash() -> str:
    alphabet = string.hexdigits.lower()
    return "".join(random.choice(alphabet) for _ in range(64))


def _random_header_dict() -> dict:
    return {
        "index": random.randint(0, 10_000_000),
        "previous_hash": _random_hash(),
        "merkle_root": _random_hash(),
        "timestamp": random.uniform(1, 2_000_000_000),
        "difficulty": max(1, random.randint(1, 1_000_000)),
        "nonce": random.randint(0, 2**64 - 1),
        "version": random.randint(1, 3),
        "signature": None,
        "miner_pubkey": None,
    }


def test_block_header_roundtrip_random_inputs():
    """Random header dicts should roundtrip via to_dict/from_dict."""
    random.seed(os.urandom(16))
    for _ in range(100):
        payload = _random_header_dict()
        header = BlockHeader(
            index=payload["index"],
            previous_hash=payload["previous_hash"],
            merkle_root=payload["merkle_root"],
            timestamp=payload["timestamp"],
            difficulty=payload["difficulty"],
            nonce=payload["nonce"],
            signature=payload["signature"],
            miner_pubkey=payload["miner_pubkey"],
            version=payload["version"],
        )
        roundtrip = BlockHeader(
            index=header.index,
            previous_hash=header.previous_hash,
            merkle_root=header.merkle_root,
            timestamp=header.timestamp,
            difficulty=header.difficulty,
            nonce=header.nonce,
            signature=header.signature,
            miner_pubkey=header.miner_pubkey,
            version=header.version,
        )
        assert roundtrip.to_dict() == header.to_dict()
        assert canonical_json(header.to_dict()) == canonical_json(roundtrip.to_dict())


def test_block_header_rejects_missing_fields():
    """Missing fields should raise KeyError/TypeError without crashing."""
    base_payload = _random_header_dict()
    required = ["index", "previous_hash", "merkle_root", "timestamp", "difficulty", "nonce"]
    for key in required:
        missing = dict(base_payload)
        missing.pop(key)
        with pytest.raises(TypeError):
            BlockHeader(**missing)


def test_canonical_json_deterministic_even_with_unsorted_dicts():
    """canonical_json must produce identical output regardless of key order."""
    payload = _random_header_dict()
    dict_a = payload.copy()
    dict_b = {k: dict_a[k] for k in reversed(list(dict_a.keys()))}
    assert canonical_json(dict_a) == canonical_json(dict_b)
