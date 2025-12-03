import time
import pytest

from xai.network.peer_manager import PeerManager
from xai.network.geoip_resolver import GeoIPMetadata
from xai.core.config import Config


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


def test_asn_limit_enforced(monkeypatch):
    monkeypatch.setattr(Config, "P2P_MAX_PEERS_PER_ASN", 1, raising=False)
    monkeypatch.setattr(Config, "P2P_MAX_PEERS_PER_COUNTRY", 5, raising=False)
    monkeypatch.setattr(Config, "P2P_MAX_UNKNOWN_GEO", 5, raising=False)
    manager = PeerManager(max_connections_per_ip=5)

    def fake_lookup(ip: str) -> GeoIPMetadata:
        return GeoIPMetadata(
            ip=ip,
            country="US",
            country_name="United States",
            asn="AS123",
            as_name="Test ASN",
            source="test",
        )

    manager.geoip_resolver.lookup = fake_lookup

    manager.connect_peer("203.0.113.1")
    assert manager.can_connect("203.0.113.2") is False
    with pytest.raises(ValueError):
        manager.connect_peer("203.0.113.2")


def test_unknown_geo_limit(monkeypatch):
    monkeypatch.setattr(Config, "P2P_MAX_UNKNOWN_GEO", 1, raising=False)
    monkeypatch.setattr(Config, "P2P_MAX_PEERS_PER_ASN", 10, raising=False)
    monkeypatch.setattr(Config, "P2P_MAX_PEERS_PER_COUNTRY", 10, raising=False)
    manager = PeerManager(max_connections_per_ip=5)

    def unknown_lookup(ip: str) -> GeoIPMetadata:
        return GeoIPMetadata(
            ip=ip,
            country="UNKNOWN",
            country_name="Unknown",
            asn="AS-UNKNOWN",
            as_name="Unknown",
            source="test",
        )

    manager.geoip_resolver.lookup = unknown_lookup
    manager.connect_peer("198.51.100.1")
    assert manager.can_connect("198.51.100.2") is False


def test_diversity_counters_release_on_disconnect(monkeypatch):
    monkeypatch.setattr(Config, "P2P_MAX_PEERS_PER_COUNTRY", 1, raising=False)
    monkeypatch.setattr(Config, "P2P_MAX_PEERS_PER_ASN", 10, raising=False)
    monkeypatch.setattr(Config, "P2P_MAX_UNKNOWN_GEO", 5, raising=False)
    manager = PeerManager(max_connections_per_ip=5)

    def us_lookup(ip: str) -> GeoIPMetadata:
        return GeoIPMetadata(
            ip=ip,
            country="US",
            country_name="United States",
            asn=f"AS{ip.split('.')[-1]}",
            as_name="Test",
            source="test",
        )

    manager.geoip_resolver.lookup = us_lookup
    peer_id = manager.connect_peer("192.0.2.10")
    manager.disconnect_peer(peer_id)
    assert manager.can_connect("192.0.2.11") is True


def test_min_unique_asn_requirement_enforced(monkeypatch):
    monkeypatch.setattr(Config, "P2P_MIN_UNIQUE_ASNS", 3, raising=False)
    monkeypatch.setattr(Config, "P2P_MAX_PEERS_PER_ASN", 10, raising=False)
    monkeypatch.setattr(Config, "P2P_MAX_PEERS_PER_COUNTRY", 10, raising=False)
    monkeypatch.setattr(Config, "P2P_MAX_UNKNOWN_GEO", 5, raising=False)
    manager = PeerManager(max_connections_per_ip=10)

    asn_map = {
        "203.0.113.1": "AS100",
        "203.0.113.2": "AS200",
        "203.0.113.3": "AS100",
        "203.0.113.4": "AS300",
        "203.0.113.5": "AS100",
    }

    def lookup(ip: str) -> GeoIPMetadata:
        return GeoIPMetadata(
            ip=ip,
            country="US",
            country_name="United States",
            asn=asn_map[ip],
            as_name="Test ASN",
            source="test",
        )

    manager.geoip_resolver.lookup = lookup

    manager.connect_peer("203.0.113.1")  # AS100
    manager.connect_peer("203.0.113.2")  # AS200

    # Still below the min unique ASN requirement (3), so another AS100 is rejected
    assert manager.can_connect("203.0.113.3") is False
    with pytest.raises(ValueError):
        manager.connect_peer("203.0.113.3")

    # Introduce a new ASN to meet the requirement
    manager.connect_peer("203.0.113.4")  # AS300

    # Once unique ASN threshold satisfied, additional AS100 peers are allowed
    assert manager.can_connect("203.0.113.5") is True
    manager.connect_peer("203.0.113.5")


def test_min_unique_country_requirement_enforced(monkeypatch):
    monkeypatch.setattr(Config, "P2P_MIN_UNIQUE_COUNTRIES", 2, raising=False)
    monkeypatch.setattr(Config, "P2P_MAX_PEERS_PER_COUNTRY", 10, raising=False)
    monkeypatch.setattr(Config, "P2P_MAX_PEERS_PER_ASN", 10, raising=False)
    monkeypatch.setattr(Config, "P2P_MAX_UNKNOWN_GEO", 5, raising=False)
    manager = PeerManager(max_connections_per_ip=10)

    country_map = {
        "198.51.100.1": ("US", "AS900"),
        "198.51.100.2": ("US", "AS901"),
        "198.51.100.3": ("CA", "AS902"),
    }

    def lookup(ip: str) -> GeoIPMetadata:
        country, asn = country_map[ip]
        return GeoIPMetadata(
            ip=ip,
            country=country,
            country_name="Test Country",
            asn=asn,
            as_name="ASN",
            source="test",
        )

    manager.geoip_resolver.lookup = lookup

    manager.connect_peer("198.51.100.1")  # US

    # Another US peer is blocked until a different country connects
    assert manager.can_connect("198.51.100.2") is False
    with pytest.raises(ValueError):
        manager.connect_peer("198.51.100.2")

    manager.connect_peer("198.51.100.3")  # CA satisfies diversity threshold
    assert manager.can_connect("198.51.100.2") is True
    manager.connect_peer("198.51.100.2")


def _enable_pow(monkeypatch, bits: int = 12) -> None:
    monkeypatch.setattr(Config, "P2P_POW_ENABLED", True, raising=False)
    monkeypatch.setattr(Config, "P2P_POW_DIFFICULTY_BITS", bits, raising=False)
    monkeypatch.setattr(Config, "P2P_POW_MAX_ITERATIONS", 200000, raising=False)
    monkeypatch.setattr(Config, "P2P_POW_REUSE_WINDOW_SECONDS", 5, raising=False)


def test_pow_proofs_required(monkeypatch, tmp_path):
    _enable_pow(monkeypatch, bits=10)
    pm = PeerManager(
        max_connections_per_ip=2,
        cert_dir=str(tmp_path / "certs"),
        key_dir=str(tmp_path / "keys"),
    )

    signed = pm.encryption.create_signed_message({"type": "ping"})
    decoded = pm.encryption.verify_signed_message(signed)
    assert decoded is not None
    assert decoded["payload"]["type"] == "ping"


def test_pow_missing_message_rejected(monkeypatch, tmp_path):
    _enable_pow(monkeypatch, bits=8)
    pm = PeerManager(
        max_connections_per_ip=2,
        cert_dir=str(tmp_path / "certs"),
        key_dir=str(tmp_path / "keys"),
    )

    pm.encryption.pow_manager.enabled = False
    signed = pm.encryption.create_signed_message({"type": "ping"})
    pm.encryption.pow_manager.enabled = True

    assert pm.encryption.verify_signed_message(signed) is None
