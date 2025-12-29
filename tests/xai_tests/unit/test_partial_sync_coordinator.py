from types import SimpleNamespace

from xai.core.p2p.partial_sync import PartialSyncCoordinator
from xai.core.p2p.checkpoint_sync import CheckpointPayload


class DummyCheckpoint:
    def __init__(self, height=5, block_hash="abc", timestamp=1.0):
        self.height = height
        self.block_hash = block_hash
        self.timestamp = timestamp
        self.data = {"utxo_snapshot": {"k": "v"}}
        import json, hashlib

        self.state_hash = hashlib.sha256(json.dumps(self.data, sort_keys=True).encode("utf-8")).hexdigest()


class DummyCheckpointManager:
    def __init__(self, checkpoint=None):
        self._checkpoint = checkpoint
        self.latest_checkpoint_height = checkpoint.height if checkpoint else None

    def load_latest_checkpoint(self):
        if not self._checkpoint:
            return None
        payload = CheckpointPayload(
            height=self._checkpoint.height,
            block_hash=self._checkpoint.block_hash,
            state_hash=self._checkpoint.state_hash,
            data=self._checkpoint.data,
        )
        return payload


class DummyBlockchain:
    def __init__(self, height=0, checkpoint=None):
        self.height = height
        self.checkpoint_manager = DummyCheckpointManager(checkpoint)
        self.utxo_manager = SimpleNamespace(restored=None)

        def restore(snapshot):
            self.utxo_manager.restored = snapshot

        self.utxo_manager.restore = restore

    def apply_checkpoint(self, payload):
        self.applied = payload


def test_bootstrap_applies_checkpoint_when_empty():
    checkpoint = DummyCheckpoint()
    bc = DummyBlockchain(height=0, checkpoint=checkpoint)
    coord = PartialSyncCoordinator(bc, p2p_manager=None)

    applied = coord.bootstrap_if_empty()
    assert applied is True
    assert bc.utxo_manager.restored == {"k": "v"}
    assert bc.checkpoint_manager.latest_checkpoint_height == checkpoint.height


def test_bootstrap_skips_when_chain_not_empty():
    bc = DummyBlockchain(height=10, checkpoint=None)
    coord = PartialSyncCoordinator(bc, p2p_manager=None)
    assert coord.bootstrap_if_empty() is False

