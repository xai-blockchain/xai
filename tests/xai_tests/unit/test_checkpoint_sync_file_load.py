"""
Tests for loading checkpoint payloads from file.
"""

import json

from xai.core.checkpoint_sync import CheckpointSyncManager


def test_load_payload_from_file(tmp_path):
    payload = {
        "height": 5,
        "block_hash": "hash5",
        "state_hash": "deadbeef",
        "data": {"utxo": "root"},
    }
    path = tmp_path / "cp.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = CheckpointSyncManager.load_payload_from_file(str(path))
    assert loaded is not None
    assert loaded.height == 5
    assert loaded.block_hash == "hash5"
    assert loaded.state_hash == "deadbeef"
    assert loaded.data == {"utxo": "root"}


def test_load_payload_from_file_handles_missing(tmp_path):
    missing = tmp_path / "missing.json"
    assert CheckpointSyncManager.load_payload_from_file(str(missing)) is None
