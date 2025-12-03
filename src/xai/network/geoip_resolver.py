"""
GeoIP/ASN resolution helper for P2P diversity enforcement.

Provides cached lookups for country and ASN metadata with multiple strategies:
1. Private/local address detection (no network calls)
2. ipwhois lookups when the optional dependency is installed
3. HTTP API fallback (default ipinfo.io-compatible payload)

The resolver never raises to callers; failures return "UNKNOWN" metadata so
callers can enforce strict policies (e.g., limiting unknown peers).
"""

from __future__ import annotations

import ipaddress
import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

try:
    from ipwhois import IPWhois  # type: ignore

    IPWHOIS_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    IPWHOIS_AVAILABLE = False


@dataclass(frozen=True)
class GeoIPMetadata:
    """Represents normalized metadata for a peer's IP address."""

    ip: str
    country: str
    country_name: str
    asn: str
    as_name: str
    source: str

    @property
    def normalized_country(self) -> str:
        return (self.country or "UNKNOWN").upper()

    @property
    def normalized_asn(self) -> str:
        # Always prefix with AS to keep formatting consistent
        value = (self.asn or "").upper()
        if value and value.startswith("AS"):
            return value
        if value:
            return f"AS{value}"
        return "AS-UNKNOWN"


class GeoIPResolver:
    """Resolve ASN/country metadata with caching and graceful fallbacks."""

    def __init__(
        self,
        http_endpoint: str = "https://ipinfo.io/{ip}/json",
        timeout: float = 2.5,
        cache_ttl: int = 3600,
    ) -> None:
        self.http_endpoint = http_endpoint
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Tuple[GeoIPMetadata, float]] = {}

    def lookup(self, ip_address: str) -> GeoIPMetadata:
        """Return cached metadata or resolve via available strategies."""
        normalized_ip = (ip_address or "").strip()
        if not normalized_ip:
            return self._unknown_metadata("missing_ip")

        cached = self._cache.get(normalized_ip)
        if cached and time.time() - cached[1] < self.cache_ttl:
            return cached[0]

        metadata = (
            self._private_metadata(normalized_ip)
            or self._lookup_ipwhois(normalized_ip)
            or self._lookup_http(normalized_ip)
            or self._unknown_metadata("unresolved", normalized_ip)
        )

        self._cache[normalized_ip] = (metadata, time.time())
        return metadata

    def _private_metadata(self, ip_address: str) -> Optional[GeoIPMetadata]:
        try:
            ip_obj = ipaddress.ip_address(ip_address)
        except ValueError:
            logger.warning(
                "Invalid IP address provided for GeoIP lookup",
                extra={"event": "p2p.geoip.invalid_ip", "ip": ip_address},
            )
            return self._unknown_metadata("invalid", ip_address)

        if any(
            [
                ip_obj.is_private,
                ip_obj.is_loopback,
                ip_obj.is_reserved,
                ip_obj.is_link_local,
            ]
        ):
            return GeoIPMetadata(
                ip=ip_address,
                country="PRIVATE",
                country_name="Private",
                asn="AS-LOCAL",
                as_name="Local Network",
                source="private",
            )
        return None

    def _lookup_ipwhois(self, ip_address: str) -> Optional[GeoIPMetadata]:
        if not IPWHOIS_AVAILABLE:  # pragma: no cover - optional path
            return None
        try:
            lookup = IPWhois(ip_address)
            result = lookup.lookup_rdap(depth=1)
            asn = result.get("asn") or "AS-UNKNOWN"
            country = (
                result.get("asn_country_code")
                or result.get("network", {}).get("country")
                or "UNKNOWN"
            )
            return GeoIPMetadata(
                ip=ip_address,
                country=country.upper(),
                country_name=result.get("asn_country_code") or country.upper(),
                asn=asn,
                as_name=result.get("asn_description") or "Unknown ASN",
                source="ipwhois",
            )
        except Exception as exc:  # pragma: no cover - depends on env/network
            logger.debug(
                "ipwhois lookup failed",
                extra={
                    "event": "p2p.geoip.ipwhois_failed",
                    "ip": ip_address,
                    "error": type(exc).__name__,
                },
            )
            return None

    def _lookup_http(self, ip_address: str) -> Optional[GeoIPMetadata]:
        if not self.http_endpoint:
            return None
        url = self.http_endpoint.format(ip=ip_address)
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.warning(
                "GeoIP HTTP lookup failed",
                extra={
                    "event": "p2p.geoip.http_failed",
                    "ip": ip_address,
                    "error": type(exc).__name__,
                },
            )
            return None

        country = (data.get("country") or data.get("countryCode") or "UNKNOWN").upper()
        asn = data.get("asn") or data.get("asn_id") or data.get("org", "")
        organization = data.get("org") or data.get("asn_org") or data.get("orgName") or "Unknown ASN"
        country_name = data.get("country_name") or data.get("countryName") or country
        return GeoIPMetadata(
            ip=ip_address,
            country=country,
            country_name=country_name,
            asn=asn if str(asn).upper().startswith("AS") else f"AS{asn}" if asn else "AS-UNKNOWN",
            as_name=organization,
            source="http",
        )

    def _unknown_metadata(self, source: str, ip_address: str = "unknown") -> GeoIPMetadata:
        return GeoIPMetadata(
            ip=ip_address,
            country="UNKNOWN",
            country_name="Unknown",
            asn="AS-UNKNOWN",
            as_name="Unknown",
            source=source,
        )
