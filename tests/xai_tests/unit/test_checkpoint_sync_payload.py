"""
Tests for payload validation via CheckpointSyncManager.
"""

import hashlib

from xai.core.checkpoint_sync import CheckpointSyncManager
from xai.core.checkpoint_payload import CheckpointPayload


def test_validate_payload_integrity():
    data = {"snapshot": "ok"}
    digest = hashlib.sha256(str(data).encode("utf-8")).hexdigest()
    payload = CheckpointPayload(height=1, block_hash="h", state_hash=digest, data=data)
    assert CheckpointSyncManager.validate_payload(payload) is True

    bad = CheckpointPayload(height=1, block_hash="h", state_hash="deadbeef", data=data)
    assert CheckpointSyncManager.validate_payload(bad) is False
