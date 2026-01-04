"""
Tests for payload validation via CheckpointSyncManager.
"""

import hashlib
import json

from xai.core.p2p.checkpoint_sync import CheckpointSyncManager
from xai.core.consensus.checkpoint_payload import CheckpointPayload


def test_validate_payload_integrity():
    data = {"snapshot": "ok"}
    serialized = json.dumps(data, sort_keys=True).encode("utf-8")
    digest = hashlib.sha256(serialized).hexdigest()
    payload = CheckpointPayload(height=1, block_hash="h", state_hash=digest, data=data)
    assert CheckpointSyncManager.validate_payload(payload) is True

    bad = CheckpointPayload(height=1, block_hash="h", state_hash="deadbeef", data=data)
    assert CheckpointSyncManager.validate_payload(bad) is False


def test_apply_payload_invokes_applier():
    data = {"snapshot": "ok"}
    serialized = json.dumps(data, sort_keys=True).encode("utf-8")
    digest = hashlib.sha256(serialized).hexdigest()
    payload = CheckpointPayload(height=1, block_hash="h", state_hash=digest, data=data)

    applied = {}

    class Applier:
        def apply_checkpoint(self, p):
            applied["payload"] = p

    mgr = CheckpointSyncManager(blockchain=None)
    assert mgr.apply_payload(payload, Applier()) is True
    assert applied["payload"] is payload

    # invalid payload should not be applied
    bad = CheckpointPayload(height=1, block_hash="h", state_hash="bad", data=data)
    assert mgr.apply_payload(bad, Applier()) is False
