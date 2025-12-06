import time

from xai.network.peer_manager import PeerManager


class DummyConfigBlockchain:
    def __init__(self):
        self.chain = []
        self.storage = type("S", (), {"data_dir": "data"})


def test_exponential_ban_backoff(monkeypatch):
    manager = PeerManager(max_connections_per_ip=5)
    manager.base_ban_seconds = 2
    manager.max_ban_seconds = 16

    peer_ip = "10.10.0.1"
    manager.ban_peer(peer_ip)
    first_expiry = manager.banned_until[peer_ip]
    first_duration = first_expiry - time.time()
    assert 1.5 <= first_duration <= 3.0

    manager.ban_peer(peer_ip)
    second_expiry = manager.banned_until[peer_ip]
    second_duration = second_expiry - time.time()
    assert second_duration >= first_duration * 1.9  # roughly doubled


def test_ban_expiry_allows_reconnect(monkeypatch):
    manager = PeerManager(max_connections_per_ip=5)
    peer_ip = "10.10.0.2"
    manager.ban_peer(peer_ip)
    manager.banned_until[peer_ip] = time.time() - 1  # force expiry
    allowed = manager.can_connect(peer_ip)
    assert allowed is True
    assert peer_ip not in manager.banned_peers


def test_subnet_diversity_enforced():
    manager = PeerManager(max_connections_per_ip=5)
    manager.max_connections_per_subnet16 = 1
    ip1 = "192.168.10.1"
    ip2 = "192.168.10.99"  # same /16
    peer1 = manager.connect_peer(ip1)
    assert peer1
    # Second connect in same /16 should fail
    try:
        manager.connect_peer(ip2)
        allowed = True
    except ValueError:
        allowed = False
    assert allowed is False
    # Different subnet should succeed
    peer3 = manager.connect_peer("192.169.20.5")
    assert peer3
