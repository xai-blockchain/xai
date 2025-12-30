"""
Unit tests for GeoIPResolver.

Coverage targets:
- GeoIPMetadata dataclass and properties
- IP lookup with caching
- Private/local address detection
- HTTP API fallback resolution
- Graceful error handling (never raises)
- Cache expiration
"""

import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from xai.network.geoip_resolver import GeoIPMetadata, GeoIPResolver


class TestGeoIPMetadata:
    """Tests for the GeoIPMetadata dataclass."""

    def test_normalized_country_uppercase(self):
        """Country code is normalized to uppercase."""
        meta = GeoIPMetadata(
            ip="1.2.3.4",
            country="us",
            country_name="United States",
            asn="AS12345",
            as_name="Test ISP",
            source="test",
        )
        assert meta.normalized_country == "US"

    def test_normalized_country_unknown_when_empty(self):
        """Empty country returns UNKNOWN."""
        meta = GeoIPMetadata(
            ip="1.2.3.4",
            country="",
            country_name="",
            asn="AS12345",
            as_name="Test ISP",
            source="test",
        )
        assert meta.normalized_country == "UNKNOWN"

    def test_normalized_country_unknown_when_none(self):
        """None country returns UNKNOWN."""
        meta = GeoIPMetadata(
            ip="1.2.3.4",
            country=None,
            country_name="",
            asn="AS12345",
            as_name="Test ISP",
            source="test",
        )
        assert meta.normalized_country == "UNKNOWN"

    def test_normalized_asn_with_prefix(self):
        """ASN with AS prefix is kept as-is (uppercase)."""
        meta = GeoIPMetadata(
            ip="1.2.3.4",
            country="US",
            country_name="United States",
            asn="as12345",
            as_name="Test ISP",
            source="test",
        )
        assert meta.normalized_asn == "AS12345"

    def test_normalized_asn_adds_prefix(self):
        """ASN without prefix gets AS prepended."""
        meta = GeoIPMetadata(
            ip="1.2.3.4",
            country="US",
            country_name="United States",
            asn="12345",
            as_name="Test ISP",
            source="test",
        )
        assert meta.normalized_asn == "AS12345"

    def test_normalized_asn_empty_returns_unknown(self):
        """Empty ASN returns AS-UNKNOWN."""
        meta = GeoIPMetadata(
            ip="1.2.3.4",
            country="US",
            country_name="United States",
            asn="",
            as_name="Test ISP",
            source="test",
        )
        assert meta.normalized_asn == "AS-UNKNOWN"

    def test_normalized_asn_none_returns_unknown(self):
        """None ASN returns AS-UNKNOWN."""
        meta = GeoIPMetadata(
            ip="1.2.3.4",
            country="US",
            country_name="United States",
            asn=None,
            as_name="Test ISP",
            source="test",
        )
        assert meta.normalized_asn == "AS-UNKNOWN"

    def test_metadata_is_frozen(self):
        """GeoIPMetadata is immutable (frozen dataclass)."""
        meta = GeoIPMetadata(
            ip="1.2.3.4",
            country="US",
            country_name="United States",
            asn="AS12345",
            as_name="Test ISP",
            source="test",
        )
        with pytest.raises(AttributeError):
            meta.country = "CA"


class TestGeoIPResolverInit:
    """Tests for GeoIPResolver initialization."""

    def test_default_initialization(self):
        """Resolver initializes with default values."""
        resolver = GeoIPResolver()
        assert "ipinfo.io" in resolver.http_endpoint
        assert resolver.timeout == 2.5
        assert resolver.cache_ttl == 3600
        assert resolver._cache == {}

    def test_custom_initialization(self):
        """Resolver accepts custom configuration."""
        resolver = GeoIPResolver(
            http_endpoint="https://custom.api/{ip}",
            timeout=5.0,
            cache_ttl=7200,
        )
        assert resolver.http_endpoint == "https://custom.api/{ip}"
        assert resolver.timeout == 5.0
        assert resolver.cache_ttl == 7200


class TestGeoIPResolverLookup:
    """Tests for the main lookup method."""

    def test_lookup_empty_ip_returns_unknown(self):
        """Empty IP address returns unknown metadata."""
        resolver = GeoIPResolver()
        meta = resolver.lookup("")
        assert meta.source == "missing_ip"
        assert meta.country == "UNKNOWN"

    def test_lookup_whitespace_ip_returns_unknown(self):
        """Whitespace-only IP returns unknown metadata."""
        resolver = GeoIPResolver()
        meta = resolver.lookup("   ")
        assert meta.source == "missing_ip"

    def test_lookup_none_ip_returns_unknown(self):
        """None IP returns unknown metadata."""
        resolver = GeoIPResolver()
        meta = resolver.lookup(None)
        assert meta.source == "missing_ip"

    def test_lookup_caches_result(self):
        """Lookups are cached."""
        resolver = GeoIPResolver(http_endpoint=None)  # Disable HTTP
        meta1 = resolver.lookup("127.0.0.1")
        meta2 = resolver.lookup("127.0.0.1")
        assert meta1 is meta2  # Same cached instance

    def test_lookup_cache_expires(self, monkeypatch):
        """Cache entries expire after TTL."""
        resolver = GeoIPResolver(http_endpoint=None, cache_ttl=60)

        # First lookup at t=0
        monkeypatch.setattr(time, "time", lambda: 0)
        meta1 = resolver.lookup("127.0.0.1")

        # Second lookup at t=30 (cache still valid)
        monkeypatch.setattr(time, "time", lambda: 30)
        meta2 = resolver.lookup("127.0.0.1")
        assert meta1 is meta2

        # Third lookup at t=61 (cache expired)
        monkeypatch.setattr(time, "time", lambda: 61)
        meta3 = resolver.lookup("127.0.0.1")
        assert meta3 is not meta1  # New instance created


class TestPrivateAddressDetection:
    """Tests for private/special address handling."""

    def test_loopback_ipv4_detected(self):
        """127.0.0.1 is detected as private."""
        resolver = GeoIPResolver(http_endpoint=None)
        meta = resolver.lookup("127.0.0.1")
        assert meta.country == "PRIVATE"
        assert meta.asn == "AS-LOCAL"
        assert meta.source == "private"

    def test_private_class_a_detected(self):
        """10.x.x.x addresses are detected as private."""
        resolver = GeoIPResolver(http_endpoint=None)
        meta = resolver.lookup("10.0.0.1")
        assert meta.country == "PRIVATE"
        assert meta.source == "private"

    def test_private_class_b_detected(self):
        """172.16.x.x addresses are detected as private."""
        resolver = GeoIPResolver(http_endpoint=None)
        meta = resolver.lookup("172.16.0.1")
        assert meta.country == "PRIVATE"
        assert meta.source == "private"

    def test_private_class_c_detected(self):
        """192.168.x.x addresses are detected as private."""
        resolver = GeoIPResolver(http_endpoint=None)
        meta = resolver.lookup("192.168.1.1")
        assert meta.country == "PRIVATE"
        assert meta.source == "private"

    def test_link_local_detected(self):
        """Link-local addresses are detected."""
        resolver = GeoIPResolver(http_endpoint=None)
        meta = resolver.lookup("169.254.1.1")
        assert meta.country == "PRIVATE"
        assert meta.source == "private"

    def test_ipv6_loopback_detected(self):
        """IPv6 loopback is detected as private."""
        resolver = GeoIPResolver(http_endpoint=None)
        meta = resolver.lookup("::1")
        assert meta.country == "PRIVATE"
        assert meta.source == "private"

    def test_invalid_ip_returns_unknown(self):
        """Invalid IP format returns unknown with invalid source."""
        resolver = GeoIPResolver(http_endpoint=None)
        meta = resolver.lookup("not.an.ip.address")
        assert meta.source == "invalid"
        assert meta.country == "UNKNOWN"

    def test_invalid_ip_too_many_octets(self):
        """IP with too many octets returns unknown."""
        resolver = GeoIPResolver(http_endpoint=None)
        meta = resolver.lookup("1.2.3.4.5")
        assert meta.source == "invalid"


class TestHTTPFallback:
    """Tests for HTTP API fallback resolution."""

    def test_http_lookup_success(self, monkeypatch):
        """Successful HTTP lookup returns correct metadata."""
        resolver = GeoIPResolver(http_endpoint="https://api.example.com/{ip}")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "country": "US",
            "country_name": "United States",
            "asn": "AS12345",
            "org": "Test ISP",
        }
        mock_response.raise_for_status = MagicMock()

        monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mock_response)

        meta = resolver.lookup("8.8.8.8")
        assert meta.country == "US"
        assert meta.as_name == "Test ISP"
        assert meta.source == "http"

    def test_http_lookup_alternative_fields(self, monkeypatch):
        """HTTP lookup handles alternative field names."""
        resolver = GeoIPResolver(http_endpoint="https://api.example.com/{ip}")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "countryCode": "DE",
            "countryName": "Germany",
            "asn_id": "7890",
            "orgName": "Deutsche Telekom",
        }
        mock_response.raise_for_status = MagicMock()

        monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mock_response)

        meta = resolver.lookup("8.8.4.4")
        assert meta.country == "DE"
        assert meta.asn == "AS7890"
        assert meta.as_name == "Deutsche Telekom"

    def test_http_lookup_asn_already_prefixed(self, monkeypatch):
        """HTTP lookup doesn't double-prefix ASN."""
        resolver = GeoIPResolver(http_endpoint="https://api.example.com/{ip}")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "country": "JP",
            "asn": "AS44444",
            "org": "Japanese ISP",
        }
        mock_response.raise_for_status = MagicMock()

        monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mock_response)

        meta = resolver.lookup("1.1.1.1")
        assert meta.asn == "AS44444"

    def test_http_lookup_timeout(self, monkeypatch):
        """HTTP timeout returns None (falls through to unknown)."""
        resolver = GeoIPResolver(http_endpoint="https://api.example.com/{ip}")

        def raise_timeout(*args, **kwargs):
            raise requests.Timeout("Request timed out")

        monkeypatch.setattr(requests, "get", raise_timeout)

        meta = resolver.lookup("8.8.8.8")
        assert meta.source == "unresolved"
        assert meta.country == "UNKNOWN"

    def test_http_lookup_connection_error(self, monkeypatch):
        """HTTP connection error returns unknown."""
        resolver = GeoIPResolver(http_endpoint="https://api.example.com/{ip}")

        def raise_error(*args, **kwargs):
            raise requests.ConnectionError("Connection failed")

        monkeypatch.setattr(requests, "get", raise_error)

        meta = resolver.lookup("8.8.8.8")
        assert meta.source == "unresolved"

    def test_http_lookup_invalid_json(self, monkeypatch):
        """Invalid JSON response returns unknown."""
        resolver = GeoIPResolver(http_endpoint="https://api.example.com/{ip}")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")

        monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mock_response)

        meta = resolver.lookup("8.8.8.8")
        assert meta.source == "unresolved"

    def test_http_lookup_http_error(self, monkeypatch):
        """HTTP error status returns unknown."""
        resolver = GeoIPResolver(http_endpoint="https://api.example.com/{ip}")

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")

        monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mock_response)

        meta = resolver.lookup("8.8.8.8")
        assert meta.source == "unresolved"

    def test_http_endpoint_disabled(self):
        """Disabled HTTP endpoint skips HTTP lookup."""
        resolver = GeoIPResolver(http_endpoint=None)
        meta = resolver.lookup("8.8.8.8")
        # Should fall through to unknown since HTTP is disabled
        assert meta.source == "unresolved"

    def test_http_endpoint_empty_string(self):
        """Empty HTTP endpoint skips HTTP lookup."""
        resolver = GeoIPResolver(http_endpoint="")
        meta = resolver.lookup("8.8.8.8")
        assert meta.source == "unresolved"

    def test_http_lookup_missing_country(self, monkeypatch):
        """HTTP lookup handles missing country gracefully."""
        resolver = GeoIPResolver(http_endpoint="https://api.example.com/{ip}")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "org": "Test ISP",
        }
        mock_response.raise_for_status = MagicMock()

        monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mock_response)

        meta = resolver.lookup("8.8.8.8")
        assert meta.country == "UNKNOWN"

    def test_http_lookup_missing_asn(self, monkeypatch):
        """HTTP lookup handles missing ASN gracefully."""
        resolver = GeoIPResolver(http_endpoint="https://api.example.com/{ip}")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "country": "FR",
        }
        mock_response.raise_for_status = MagicMock()

        monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mock_response)

        meta = resolver.lookup("8.8.8.8")
        assert meta.asn == "AS-UNKNOWN"


class TestIPWhoisFallback:
    """Tests for ipwhois library fallback (when available)."""

    def test_ipwhois_lookup_success(self, monkeypatch):
        """Successful ipwhois lookup returns correct metadata."""
        # Create a mock IPWhois class
        mock_ipwhois_instance = MagicMock()
        mock_ipwhois_instance.lookup_rdap.return_value = {
            "asn": "15169",
            "asn_country_code": "US",
            "asn_description": "Google LLC",
        }
        mock_ipwhois_class = MagicMock(return_value=mock_ipwhois_instance)

        # Import the module and patch it
        import xai.network.geoip_resolver as geoip_module

        # Save original values
        orig_available = geoip_module.IPWHOIS_AVAILABLE

        try:
            # Patch module-level attributes
            geoip_module.IPWHOIS_AVAILABLE = True
            geoip_module.IPWhois = mock_ipwhois_class

            resolver = GeoIPResolver(http_endpoint=None)
            meta = resolver.lookup("8.8.8.8")

            assert meta.country == "US"
            assert meta.asn == "15169"
            assert meta.as_name == "Google LLC"
            assert meta.source == "ipwhois"
        finally:
            # Restore original state
            geoip_module.IPWHOIS_AVAILABLE = orig_available
            if hasattr(geoip_module, "IPWhois") and geoip_module.IPWhois is mock_ipwhois_class:
                delattr(geoip_module, "IPWhois")

    def test_ipwhois_lookup_network_error(self, monkeypatch):
        """ipwhois network error falls through to next strategy."""
        # Create a mock IPWhois that raises ConnectionError
        mock_ipwhois_instance = MagicMock()
        mock_ipwhois_instance.lookup_rdap.side_effect = ConnectionError("Network unreachable")
        mock_ipwhois_class = MagicMock(return_value=mock_ipwhois_instance)

        import xai.network.geoip_resolver as geoip_module

        orig_available = geoip_module.IPWHOIS_AVAILABLE

        try:
            geoip_module.IPWHOIS_AVAILABLE = True
            geoip_module.IPWhois = mock_ipwhois_class

            resolver = GeoIPResolver(http_endpoint=None)
            meta = resolver.lookup("8.8.8.8")

            # Should fall through to unknown
            assert meta.source == "unresolved"
        finally:
            geoip_module.IPWHOIS_AVAILABLE = orig_available
            if hasattr(geoip_module, "IPWhois") and geoip_module.IPWhois is mock_ipwhois_class:
                delattr(geoip_module, "IPWhois")

    def test_ipwhois_lookup_value_error(self, monkeypatch):
        """ipwhois ValueError falls through to next strategy."""
        mock_ipwhois_instance = MagicMock()
        mock_ipwhois_instance.lookup_rdap.side_effect = ValueError("Invalid IP")
        mock_ipwhois_class = MagicMock(return_value=mock_ipwhois_instance)

        import xai.network.geoip_resolver as geoip_module

        orig_available = geoip_module.IPWHOIS_AVAILABLE

        try:
            geoip_module.IPWHOIS_AVAILABLE = True
            geoip_module.IPWhois = mock_ipwhois_class

            resolver = GeoIPResolver(http_endpoint=None)
            meta = resolver.lookup("8.8.8.8")

            assert meta.source == "unresolved"
        finally:
            geoip_module.IPWHOIS_AVAILABLE = orig_available
            if hasattr(geoip_module, "IPWhois") and geoip_module.IPWhois is mock_ipwhois_class:
                delattr(geoip_module, "IPWhois")

    def test_ipwhois_uses_network_country_fallback(self, monkeypatch):
        """ipwhois falls back to network country if asn_country_code missing."""
        mock_ipwhois_instance = MagicMock()
        mock_ipwhois_instance.lookup_rdap.return_value = {
            "asn": "12345",
            "network": {"country": "GB"},
            "asn_description": "Test ISP",
        }
        mock_ipwhois_class = MagicMock(return_value=mock_ipwhois_instance)

        import xai.network.geoip_resolver as geoip_module

        orig_available = geoip_module.IPWHOIS_AVAILABLE

        try:
            geoip_module.IPWHOIS_AVAILABLE = True
            geoip_module.IPWhois = mock_ipwhois_class

            resolver = GeoIPResolver(http_endpoint=None)
            meta = resolver.lookup("8.8.8.8")

            assert meta.country == "GB"
        finally:
            geoip_module.IPWHOIS_AVAILABLE = orig_available
            if hasattr(geoip_module, "IPWhois") and geoip_module.IPWhois is mock_ipwhois_class:
                delattr(geoip_module, "IPWhois")


class TestResolutionOrder:
    """Tests for resolution strategy ordering."""

    def test_private_takes_precedence(self, monkeypatch):
        """Private addresses skip external lookups."""
        # Even with HTTP enabled, private should be detected first
        resolver = GeoIPResolver(http_endpoint="https://api.example.com/{ip}")

        # Mock HTTP to verify it's not called
        http_called = []
        def mock_get(*args, **kwargs):
            http_called.append(True)
            raise requests.Timeout()

        monkeypatch.setattr(requests, "get", mock_get)

        meta = resolver.lookup("192.168.1.1")
        assert meta.source == "private"
        assert len(http_called) == 0  # HTTP was never called


class TestUnknownMetadata:
    """Tests for unknown metadata generation."""

    def test_unknown_metadata_structure(self):
        """Unknown metadata has correct structure."""
        resolver = GeoIPResolver(http_endpoint=None)
        meta = resolver._unknown_metadata("test_source", "1.2.3.4")

        assert meta.ip == "1.2.3.4"
        assert meta.country == "UNKNOWN"
        assert meta.country_name == "Unknown"
        assert meta.asn == "AS-UNKNOWN"
        assert meta.as_name == "Unknown"
        assert meta.source == "test_source"

    def test_unknown_metadata_default_ip(self):
        """Unknown metadata uses 'unknown' as default IP."""
        resolver = GeoIPResolver(http_endpoint=None)
        meta = resolver._unknown_metadata("test")
        assert meta.ip == "unknown"


class TestEdgeCases:
    """Edge case and boundary tests."""

    def test_ipv6_public_address(self, monkeypatch):
        """IPv6 public addresses go through lookup chain."""
        resolver = GeoIPResolver(http_endpoint="https://api.example.com/{ip}")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "country": "SE",
            "org": "Swedish ISP",
        }
        mock_response.raise_for_status = MagicMock()

        monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mock_response)

        meta = resolver.lookup("2001:4860:4860::8888")
        assert meta.country == "SE"

    def test_ip_normalization_strips_whitespace(self, monkeypatch):
        """IP addresses are stripped of whitespace."""
        resolver = GeoIPResolver(http_endpoint=None)

        # Lookup with whitespace
        meta = resolver.lookup("  127.0.0.1  ")
        assert meta.source == "private"
        assert meta.ip == "127.0.0.1"

    def test_concurrent_lookups_same_ip(self, monkeypatch):
        """Multiple lookups for same IP use cache."""
        resolver = GeoIPResolver(http_endpoint=None, cache_ttl=3600)

        monkeypatch.setattr(time, "time", lambda: 100)

        # Multiple lookups should return same cached instance
        results = [resolver.lookup("127.0.0.1") for _ in range(5)]
        assert all(r is results[0] for r in results)

    def test_cache_stores_correct_timestamp(self, monkeypatch):
        """Cache stores lookup timestamp for TTL checking."""
        resolver = GeoIPResolver(http_endpoint=None, cache_ttl=60)

        monkeypatch.setattr(time, "time", lambda: 1000)
        resolver.lookup("127.0.0.1")

        # Verify cache entry has correct timestamp
        cached_meta, cached_time = resolver._cache.get("127.0.0.1")
        assert cached_time == 1000
