"""
Tests for CheckpointPayload integrity helper.
"""

from xai.core.consensus.checkpoint_payload import CheckpointPayload


def test_checkpoint_payload_integrity_passes():
    data = {"utxo_root": "abc", "metadata": {"foo": "bar"}}
    import hashlib

    digest = hashlib.sha256(str(data).encode("utf-8")).hexdigest()
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
