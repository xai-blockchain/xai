"""
Tests for SPVHeaderIngestor linkage validation.
"""

from xai.core.p2p.spv_header_ingestor import SPVHeaderIngestor


def test_ingest_valid_chain():
    ingestor = SPVHeaderIngestor()
    headers = [
        {"height": 0, "block_hash": "h0", "prev_hash": "", "bits": 1},
        {"height": 1, "block_hash": "h1", "prev_hash": "h0", "bits": 2},
        {"height": 2, "block_hash": "h2", "prev_hash": "h1", "bits": 2},
    ]
    added, rejected = ingestor.ingest(headers)
    assert added == 3
    assert rejected == []
    assert ingestor.store.get_best_tip().block_hash == "h2"


def test_ingest_rejects_orphan_and_bad_bits():
    ingestor = SPVHeaderIngestor()
    headers = [
        {"height": 0, "block_hash": "h0", "prev_hash": "", "bits": 1},
        {"height": 1, "block_hash": "bad", "prev_hash": "missing", "bits": 2},
        {"height": 2, "block_hash": "badbits", "prev_hash": "h0", "bits": 0},
    ]
    added, rejected = ingestor.ingest(headers)
    assert added == 1
    assert set(rejected) == {"bad", "badbits"}
