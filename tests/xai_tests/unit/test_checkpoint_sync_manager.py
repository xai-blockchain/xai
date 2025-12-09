"""
Tests for CheckpointSyncManager partial-sync helper.
"""

from types import SimpleNamespace

from xai.core.checkpoint_sync import CheckpointSyncManager


class DummyCheckpoint:
    def __init__(self, height=5, block_hash="abc", timestamp=1.0):
        self.height = height
        self.block_hash = block_hash
        self.timestamp = timestamp


class DummyCheckpointManager:
    def __init__(self, checkpoint=None, latest_height=None):
        self._checkpoint = checkpoint
        self.latest_checkpoint_height = latest_height

    def load_latest_checkpoint(self):
        return self._checkpoint

    def load_checkpoint(self, height):
        if self._checkpoint and self._checkpoint.height == height:
            return self._checkpoint
        return DummyCheckpoint(height=height, block_hash="h", timestamp=2.0)


def test_prefers_p2p_metadata():
    cp = DummyCheckpoint(height=10, block_hash="h1", timestamp=11.0)
    cm = DummyCheckpointManager(cp)
    bc = SimpleNamespace(checkpoint_manager=cm)
    p2p = SimpleNamespace(_get_checkpoint_metadata=lambda: {"height": 20, "block_hash": "peer", "timestamp": 22.0})

    mgr = CheckpointSyncManager(bc, p2p)
    meta = mgr.get_best_checkpoint_metadata()
    assert meta["source"] == "p2p"
    assert meta["height"] == 20


def test_fallback_to_local_when_no_p2p():
    cp = DummyCheckpoint(height=7, block_hash="h7", timestamp=77.0)
    cm = DummyCheckpointManager(cp)
    bc = SimpleNamespace(checkpoint_manager=cm)
    mgr = CheckpointSyncManager(bc, p2p_manager=None)
    meta = mgr.get_best_checkpoint_metadata()
    assert meta["source"] == "local"
    assert meta["height"] == 7


def test_apply_local_checkpoint_specific_height():
    cm = DummyCheckpointManager(checkpoint=None, latest_height=5)
    bc = SimpleNamespace(checkpoint_manager=cm)
    mgr = CheckpointSyncManager(bc, p2p_manager=None)
    cp = mgr.apply_local_checkpoint(height=5)
    assert cp.height == 5
    assert cp.block_hash == "h"
