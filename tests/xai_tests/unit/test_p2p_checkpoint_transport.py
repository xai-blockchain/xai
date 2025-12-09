import asyncio
from types import SimpleNamespace

import pytest

from xai.core.node_p2p import P2PNetworkManager
from xai.network.peer_manager import PeerManager


class DummyCheckpointManager:
    def __init__(self, payload):
        self._payload = payload
        self.latest_checkpoint_height = payload.get("height")

    def export_checkpoint_payload(self, height=None, include_data=False):
        return self._payload


class DummyBlockchain:
    def __init__(self, payload):
        self.checkpoint_manager = DummyCheckpointManager(payload)


class DummyPeerManager:
    def __init__(self):
        self.encryption = SimpleNamespace(
            create_signed_message=lambda msg: str(msg).encode("utf-8"),
            verify_signed_message=lambda raw: {"payload": eval(raw.decode("utf-8")), "sender": "peer", "version": "1"},
        )
        self.reputation = SimpleNamespace(
            record_invalid_transaction=lambda peer_id: None,
            record_valid_transaction=lambda peer_id: None,
            record_invalid_block=lambda peer_id: None,
            record_valid_block=lambda peer_id: None,
            connect_peer=lambda host: None,
            disconnect_peer=lambda peer_id: None,
        )
        self.discovery = SimpleNamespace(exchange_peers=lambda peers: None)
        self.connected_peers = {}
        self.max_connections_per_ip = 50
        self.allowlist = set()

    def can_connect(self, host: str) -> bool:
        return True


@pytest.mark.asyncio
async def test_handle_checkpoint_request_sends_payload(monkeypatch):
    payload = {"height": 5, "block_hash": "abc", "state_hash": "deadbeef", "url": "file:///tmp/cp.json"}
    bc = DummyBlockchain(payload)
    pm = PeerManager(
        max_connections_per_ip=10,
        nonce_ttl_seconds=300,
        require_client_cert=False,
        trusted_cert_fps_file="",
        trusted_peer_pubkeys_file="",
        cert_dir="/tmp",
        key_dir="/tmp",
    )
    # Patch encryption to bypass signing complexity
    pm.encryption.create_signed_message = lambda msg: str(msg).encode("utf-8")  # type: ignore
    pm.encryption.verify_signed_message = lambda raw: {"payload": eval(raw.decode("utf-8")), "sender": "peer", "version": "1"}  # type: ignore
    p2p = P2PNetworkManager(blockchain=bc, peer_manager=pm, consensus_manager=None, host="0.0.0.0", port=0)

    sent = {}

    async def fake_send(msg):
        sent["msg"] = msg

    websocket = SimpleNamespace(send=fake_send)
    await p2p._handle_checkpoint_request(websocket, "peer1", {"want_payload": True})

    assert "checkpoint_payload" in sent.get("msg", "")
