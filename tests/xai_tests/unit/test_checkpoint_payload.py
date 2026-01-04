"""
Tests for CheckpointPayload integrity helper.
"""

import json

from xai.core.consensus.checkpoint_payload import CheckpointPayload


def test_checkpoint_payload_integrity_passes():
    data = {"utxo_root": "abc", "metadata": {"foo": "bar"}}
    import hashlib

    serialized = json.dumps(data, sort_keys=True).encode("utf-8")
    digest = hashlib.sha256(serialized).hexdigest()
    payload = CheckpointPayload(
        height=10,
        block_hash="h",
        state_hash=digest,
        data=data,
    )
    assert payload.verify_integrity() is True

def test_checkpoint_payload_integrity_detects_mismatch():
    data = {"utxo_root": "abc"}
    payload = CheckpointPayload(
        height=10,
        block_hash="h",
        state_hash="deadbeef",
        data=data,
    )
    assert payload.verify_integrity() is False
