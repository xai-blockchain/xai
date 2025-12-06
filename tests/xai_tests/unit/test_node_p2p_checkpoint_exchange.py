import json
import asyncio
from unittest.mock import AsyncMock

import pytest

from xai.core.node_p2p import P2PNetworkManager


class DummyCheckpoint:
    def __init__(self, height=5, block_hash="abc123", timestamp=1.0):
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
        return self._checkpoint if self._checkpoint and self._checkpoint.height == height else None


class DummyBlockchain:
    def __init__(self, checkpoint=None):
        self.chain = []
        self.storage = type("S", (), {"data_dir": "data"})
        self.checkpoint_manager = DummyCheckpointManager(checkpoint)


@pytest.mark.asyncio
async def test_get_checkpoint_returns_metadata():
    checkpoint = DummyCheckpoint()
    blockchain = DummyBlockchain(checkpoint)
    manager = P2PNetworkManager(blockchain)
    manager.peer_manager.pow_manager.enabled = False

    websocket = AsyncMock()
    websocket.remote_address = ("1.1.1.1", 1000)
    peer_id = "peer1"
    manager.connections[peer_id] = websocket
    manager.websocket_peer_ids[websocket] = peer_id
    manager._connection_last_seen[peer_id] = 0

    payload = {"type": "get_checkpoint", "payload": None}
    signed = manager.peer_manager.encryption.create_signed_message({"type": "get_checkpoint", "payload": None})

    await manager._handle_message(websocket, signed)
    websocket.send.assert_awaited()
    sent = json.loads(websocket.send.await_args.args[0])
    msg = sent["message"]["payload"]
    assert msg["type"] == "checkpoint"
    assert msg["payload"]["block_hash"] == "abc123"
