import asyncio
from types import SimpleNamespace

from xai.core.checkpoint_sync import CheckpointSyncManager
from xai.core.checkpoint_payload import CheckpointPayload


class DummyP2P:
    def __init__(self, payload):
        self.sent = []
        # simulate two peers advertising the same payload to satisfy quorum
        self.peer_features = {
            "peerA": {"checkpoint_payload": payload},
            "peerB": {"checkpoint_payload": payload},
        }

    async def broadcast(self, message):
        self.sent.append(message)


def test_request_checkpoint_from_peers():
    snapshot = {"utxo_snapshot": {}}
    import hashlib, json

    state_hash = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode("utf-8")).hexdigest()
    payload_data = {"height": 3, "block_hash": "abc", "state_hash": state_hash, "data": snapshot}
    p2p = DummyP2P(payload_data)
    mgr = CheckpointSyncManager(blockchain=SimpleNamespace(config=SimpleNamespace(CHECKPOINT_QUORUM=2)), p2p_manager=p2p)

    cp = mgr.request_checkpoint_from_peers()
    assert cp.height == 3
    assert cp.block_hash == "abc"
    assert p2p.sent  # broadcast was invoked
