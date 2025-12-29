import types
from decimal import Decimal

from xai.core.p2p.checkpoint_sync import CheckpointSyncManager, CheckpointMetadata
from xai.core.consensus.checkpoint_payload import CheckpointPayload


class DummyCheckpoint:
    def __init__(self, height, block_hash, timestamp=None):
        self.height = height
        self.block_hash = block_hash
        self.timestamp = timestamp


class DummyCheckpointManager:
    def __init__(self, checkpoint=None):
        self._checkpoint = checkpoint
        self.latest_checkpoint_height = checkpoint.height if checkpoint else None

    def load_latest_checkpoint(self):
        return self._checkpoint

    def load_checkpoint(self, height):
        if self._checkpoint and self._checkpoint.height == height:
            return self._checkpoint
        return None


class DummyBlockchain:
    def __init__(self, checkpoint=None):
        self.checkpoint_manager = DummyCheckpointManager(checkpoint)
        self.utxo_manager = types.SimpleNamespace(restored=None)

        def restore(snapshot):
            self.utxo_manager.restored = snapshot

        self.utxo_manager.restore = restore

    def apply_checkpoint(self, payload):
        self.applied = payload


def test_checkpoint_metadata_prefers_peer_over_local():
    local = DummyCheckpoint(height=10, block_hash="local", timestamp=1.0)
    blockchain = DummyBlockchain(checkpoint=local)
    p2p = types.SimpleNamespace(_get_checkpoint_metadata=lambda: {"height": 20, "block_hash": "peer", "source": "peer"})
    mgr = CheckpointSyncManager(blockchain, p2p_manager=p2p)

    best = mgr.get_best_checkpoint_metadata()
    assert best["height"] == 20
    assert best["block_hash"] == "peer"
    assert best["source"] in {"peer", "p2p"}


def test_apply_payload_invokes_utxo_restore_and_checkpoint_height():
    snapshot = {"utxo_snapshot": {"k": "v"}}
    payload = CheckpointPayload(
        height=5,
        block_hash="abc",
        state_hash="",
        data=snapshot,
    )
    # Compute real state hash
    import json, hashlib
    payload.state_hash = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode("utf-8")).hexdigest()
    blockchain = DummyBlockchain()
    mgr = CheckpointSyncManager(blockchain)

    assert mgr.apply_payload(payload, blockchain) is True
    assert blockchain.utxo_manager.restored == {"k": "v"}
    assert blockchain.checkpoint_manager.latest_checkpoint_height == 5
