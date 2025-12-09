import asyncio
from types import SimpleNamespace

from xai.core.checkpoint_sync import CheckpointSyncManager
from xai.core.checkpoint_payload import CheckpointPayload


class DummyP2P:
    def __init__(self, payload):
        self.sent = []
        self.peer_features = {"peer": {"checkpoint_payload": payload}}

    async def broadcast(self, message):
        self.sent.append(message)


def test_request_checkpoint_from_peers():
    payload_data = {"height": 3, "block_hash": "abc", "state_hash": "dead", "data": {"utxo_snapshot": {}}}
    p2p = DummyP2P(payload_data)
    mgr = CheckpointSyncManager(blockchain=None, p2p_manager=p2p)

    cp = mgr.request_checkpoint_from_peers()
    assert cp.height == 3
    assert cp.block_hash == "abc"
    assert p2p.sent  # broadcast was invoked

