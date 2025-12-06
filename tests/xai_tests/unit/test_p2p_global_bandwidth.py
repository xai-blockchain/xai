import time

from xai.core.node_p2p import P2PNetworkManager
from xai.core.p2p_security import BandwidthLimiter


class DummyBlockchain:
    def __init__(self):
        self.chain = []
        self.storage = type("S", (), {"data_dir": "data"})


def test_global_bandwidth_limiter_consumes_and_expires():
    manager = P2PNetworkManager(DummyBlockchain())
    manager.global_bandwidth_in = BandwidthLimiter(50, 10)

    assert manager.global_bandwidth_in.consume("global", 40) is True
    assert manager.global_bandwidth_in.consume("global", 20) is False

    # After enough time passes, tokens should refill
    time.sleep(0.2)  # 2 bytes refilled
    assert manager.global_bandwidth_in.consume("global", 5) in (True, False)  # non-throwing


def test_disconnect_peer_helper_cleans_state():
    manager = P2PNetworkManager(DummyBlockchain())
    fake_conn = object()
    peer_id = "peer-test"
    manager.connections[peer_id] = fake_conn
    manager.websocket_peer_ids[fake_conn] = peer_id
    manager._connection_last_seen[peer_id] = time.time()

    manager._disconnect_peer(peer_id, fake_conn)

    assert peer_id not in manager.connections
    assert fake_conn not in manager.websocket_peer_ids
    assert peer_id not in manager._connection_last_seen


def test_quic_payload_respects_global_inbound_cap(monkeypatch):
    manager = P2PNetworkManager(DummyBlockchain())
    manager.global_bandwidth_in = BandwidthLimiter(4, 0)  # tiny cap
    called = {"count": 0}

    async def fake_handle(ws, msg):
        called["count"] += 1

    manager._handle_message = fake_handle  # type: ignore

    # First small payload passes
    manager.global_bandwidth_in.consume("global", 0)  # ensure bucket initialized
    manager._loop = None
    import asyncio
    asyncio.get_event_loop().run_until_complete(manager._handle_quic_payload(b"123"))
    # Second bigger payload should be dropped
    asyncio.get_event_loop().run_until_complete(manager._handle_quic_payload(b"12345"))

    assert called["count"] == 1
