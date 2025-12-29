import time

from xai.core.p2p.node_p2p import P2PNetworkManager


class DummyBlockchain:
    """Minimal blockchain stub for P2PNetworkManager construction."""

    def __init__(self):
        self.chain = []
        self.storage = type("S", (), {"data_dir": "data"})


def test_connection_reset_storm_bans_peer(monkeypatch):
    manager = P2PNetworkManager(DummyBlockchain())
    manager._reset_window_seconds = 30
    manager._reset_threshold = 3

    peer_id = "10.0.0.1"
    base = time.time()
    for idx in range(3):
        manager._record_connection_reset_event(peer_id, now=base + idx, reason="RST_STREAM")

    assert peer_id in manager.peer_manager.banned_peers


def test_reset_events_evicted_outside_window(monkeypatch):
    manager = P2PNetworkManager(DummyBlockchain())
    manager._reset_window_seconds = 5
    manager._reset_threshold = 3

    peer_id = "10.0.0.2"
    base = time.time()
    # Two old resets outside window
    manager._record_connection_reset_event(peer_id, now=base - 10)
    manager._record_connection_reset_event(peer_id, now=base - 9)
    # One recent reset - should not ban yet
    manager._record_connection_reset_event(peer_id, now=base)
    assert peer_id not in manager.peer_manager.banned_peers

    # Two more within window trigger ban
    manager._record_connection_reset_event(peer_id, now=base + 1)
    manager._record_connection_reset_event(peer_id, now=base + 2)
    assert peer_id in manager.peer_manager.banned_peers
