"""
Unit tests for BlockHeader and canonical_json.

Coverage targets:
- Deterministic JSON hashing
- Version inclusion toggle
- Hash recalculation when fields mutate
"""

from xai.core.block_header import BlockHeader, canonical_json


def test_canonical_json_determinism():
    data1 = {"b": 2, "a": 1}
    data2 = {"a": 1, "b": 2}
    assert canonical_json(data1) == canonical_json(data2)
    assert canonical_json(data1) == '{"a":1,"b":2}'


def test_block_header_hash_and_version_flag():
    header = BlockHeader(index=1, previous_hash="0" * 64, merkle_root="a" * 64, timestamp=1.0, difficulty=1, nonce=0)
    orig_hash = header.hash
    # Changing nonce and recalculating updates hash
    header.nonce = 1
    header.hash = header.calculate_hash()
    assert header.hash != orig_hash

    # Version included when provided
    header_v = BlockHeader(index=1, previous_hash="0" * 64, merkle_root="b" * 64, timestamp=1.0, difficulty=1, nonce=0, version=2)
    assert "version" in header_v.to_dict()
