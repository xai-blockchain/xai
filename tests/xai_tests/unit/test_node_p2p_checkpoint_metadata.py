"""
Unit tests for checkpoint metadata exposure in P2PNetworkManager.
"""

import types

from xai.core.node_p2p import P2PNetworkManager


class DummyCheckpoint:
    def __init__(self, height=5, block_hash="abc", timestamp=123.0):
        self.height = height
        self.block_hash = block_hash
        self.timestamp = timestamp


class DummyCheckpointManager:
    def __init__(self, latest=None, latest_height=None, raise_on_load=False):
        self._latest = latest
        self.latest_checkpoint_height = latest_height
        self.raise_on_load = raise_on_load

    def load_latest_checkpoint(self):
        return self._latest

    def load_checkpoint(self, height):
        if self.raise_on_load:
            raise RuntimeError("failed")
        if self._latest and self._latest.height == height:
            return self._latest
        return DummyCheckpoint(height=height, block_hash="hash", timestamp=321.0)


class DummyBlockchain:
    def __init__(self, checkpoint_manager=None):
        self.checkpoint_manager = checkpoint_manager
        self.chain = []


def test_checkpoint_metadata_from_latest():
    cp = DummyCheckpoint(height=10, block_hash="h1", timestamp=111.0)
    bc = DummyBlockchain(DummyCheckpointManager(latest=cp))
    mgr = P2PNetworkManager(bc)
    meta = mgr._get_checkpoint_metadata()
    assert meta == {"height": 10, "block_hash": "h1", "timestamp": 111.0}


def test_checkpoint_metadata_fallback_to_latest_height():
    cm = DummyCheckpointManager(latest=None, latest_height=7)
    bc = DummyBlockchain(cm)
    mgr = P2PNetworkManager(bc)
    meta = mgr._get_checkpoint_metadata()
    assert meta == {"height": 7, "block_hash": "hash", "timestamp": 321.0}


def test_checkpoint_metadata_handles_errors():
    cm = DummyCheckpointManager(latest=None, latest_height=7, raise_on_load=True)
    bc = DummyBlockchain(cm)
    mgr = P2PNetworkManager(bc)
    assert mgr._get_checkpoint_metadata() is None


def test_no_checkpoint_manager_returns_none():
    bc = DummyBlockchain(checkpoint_manager=None)
    mgr = P2PNetworkManager(bc)
    assert mgr._get_checkpoint_metadata() is None
