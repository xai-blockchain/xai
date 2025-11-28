import time

from xai.network.peer_manager import PeerManager


def test_nonce_ttl_expires_replays():
    pm = PeerManager(nonce_ttl_seconds=1)
    sender = "peerA"
    nonce = "n-1"
    now = time.time()

    pm.record_nonce(sender, nonce, timestamp=now - 5)
    assert pm.is_nonce_replay(sender, nonce, timestamp=now) is False

    pm.record_nonce(sender, nonce, timestamp=now)
    assert pm.is_nonce_replay(sender, nonce, timestamp=now) is True


def test_trusted_cert_pinning_allows_configured():
    pm = PeerManager(trusted_cert_fingerprints=["abc123"])
    assert pm.is_cert_allowed("abc123") is True
    assert pm.is_cert_allowed("ABC123") is True  # case-insensitive
    assert pm.is_cert_allowed("deadbeef") is False
