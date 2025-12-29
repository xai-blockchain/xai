import json

from xai.core.p2p.checkpoint_sync import CheckpointSyncManager


class DummyUtxoManager:
    def __init__(self):
        self.restored = None

    def restore(self, snapshot):
        self.restored = snapshot


class DummyCheckpointManager:
    def __init__(self):
        self.latest_checkpoint_height = None

    def load_latest_checkpoint(self):
        return None


class DummyBlockchain:
    def __init__(self):
        self.utxo_manager = DummyUtxoManager()
        self.checkpoint_manager = DummyCheckpointManager()

    def apply_checkpoint(self, payload):
        # simulate apply hook
        self.applied = payload


class DummyP2P:
    def __init__(self, meta):
        self._meta = meta

    def _get_checkpoint_metadata(self):
        return self._meta


def test_partial_sync_applies_checkpoint_from_peer(tmp_path):
    snapshot = {"utxo_snapshot": {"k": "v"}}
    state_hash = __import__("hashlib").sha256(json.dumps(snapshot, sort_keys=True).encode("utf-8")).hexdigest()
    payload = {
        "height": 5,
        "block_hash": "abc123",
        "state_hash": state_hash,
        "data": snapshot,
    }

    payload_path = tmp_path / "checkpoint.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    bc = DummyBlockchain()
    p2p = DummyP2P({"height": 5, "block_hash": "abc123", "timestamp": 1.0, "url": str(payload_path)})
    mgr = CheckpointSyncManager(blockchain=bc, p2p_manager=p2p)

    assert mgr.fetch_validate_apply() is True
    assert bc.utxo_manager.restored == {"k": "v"}
    assert bc.checkpoint_manager.latest_checkpoint_height == 5
