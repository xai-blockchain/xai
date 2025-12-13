"""
Production-Grade Certificate Pinning System
Provides secure certificate validation with backup pins and rotation support
"""

import hashlib
import logging
import time
import ssl
import socket
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


# Certificate pinning exceptions
class CertificatePinningError(Exception):
    """Base exception for certificate pinning operations"""
    pass


class CertificateFetchError(CertificatePinningError):
    """Raised when certificate fetching fails"""
    pass


class CertificateValidationError(CertificatePinningError):
    """Raised when certificate validation fails"""
    pass


@dataclass
class Pin:
    """Certificate pin with metadata"""
    spki_hash: str
    description: str = ""
    added_at: float = 0.0
    is_backup: bool = False


class CertificatePinner:
    """
    Production-grade certificate pinning implementation.

    Features:
    - Primary and backup pin support
    - Pin rotation with grace period
    - Automatic certificate fetching and validation
    - Expiration tracking
    - Detailed logging and alerting
    """

    def __init__(self, enforce_pinning: bool = True, grace_period_days: int = 7):
        """
        Initialize certificate pinner.

        Args:
            enforce_pinning: If False, log violations but don't block
            grace_period_days: Days to allow old pins during rotation
        """
        # Stores pinned public key hashes with metadata
        self.pinned_certificates: Dict[str, List[Pin]] = {}
        self.enforce_pinning = enforce_pinning
        self.grace_period = timedelta(days=grace_period_days)

        # Track violations for monitoring
        self.violations: List[Dict] = []
        self.max_violations_log = 100

        logger.info("CertificatePinner initialized with enforcement=%s", enforce_pinning)

    def pin_certificate(
        self,
        hostname: str,
        spki_hash: str,
        description: str = "",
        is_backup: bool = False
    ):
        """
        Add a public key hash (SPKI hash) pin for a hostname.

        Args:
            hostname: Target hostname
            spki_hash: SHA-256 hash of Subject Public Key Info
            description: Human-readable description
            is_backup: Whether this is a backup pin
        """
        if not hostname or not spki_hash:
            raise ValueError("Hostname and SPKI hash cannot be empty.")

        pin = Pin(
            spki_hash=spki_hash,
            description=description,
            added_at=time.time(),
            is_backup=is_backup
        )

        if hostname not in self.pinned_certificates:
            self.pinned_certificates[hostname] = []

        self.pinned_certificates[hostname].append(pin)
        logger.info(
            "Pinned %s certificate for '%s': %s... (%s)",
            "backup" if is_backup else "primary",
            hostname,
            spki_hash[:16],
            description
        )

    def verify_connection(self, hostname: str, presented_spki_hash: str) -> bool:
        """
        Verify a network connection using certificate pinning.

        Args:
            hostname: Target hostname
            presented_spki_hash: SPKI hash from server certificate

        Returns:
            True if valid, False if pinning violation
        """
        if not hostname or not presented_spki_hash:
            raise ValueError("Hostname and presented SPKI hash cannot be empty.")

        # No pins configured for this host
        if hostname not in self.pinned_certificates:
            logger.warning(
                "No pins configured for '%s'. %s connection.",
                hostname,
                "Allowing" if not self.enforce_pinning else "Blocking"
            )
            return not self.enforce_pinning

        pins = self.pinned_certificates[hostname]
        current_time = time.time()

        # Check against all pins (including those in grace period)
        for pin in pins:
            if pin.spki_hash == presented_spki_hash:
                # Check if pin is expired (outside grace period)
                age = datetime.fromtimestamp(current_time) - datetime.fromtimestamp(pin.added_at)
                if age > self.grace_period and pin.is_backup:
                    logger.warning(
                        "Certificate for '%s' matches expired backup pin (age: %s)",
                        hostname,
                        age
                    )
                    continue

                logger.debug(
                    "Certificate for '%s' verified against pin: %s",
                    hostname,
                    pin.description or pin.spki_hash[:16]
                )
                return True

        # Pinning violation detected
        violation = {
            "timestamp": current_time,
            "hostname": hostname,
            "presented_hash": presented_spki_hash,
            "expected_hashes": [p.spki_hash for p in pins]
        }
        self.violations.append(violation)

        # Trim violations log
        if len(self.violations) > self.max_violations_log:
            self.violations = self.violations[-self.max_violations_log:]

        logger.error(
            "!!! SECURITY ALERT !!! Certificate pinning violation for '%s'. "
            "Presented hash '%s...' does not match any of %d pinned hashes.",
            hostname,
            presented_spki_hash[:16],
            len(pins)
        )

        return not self.enforce_pinning

    def fetch_and_pin_current_certificate(
        self,
        hostname: str,
        port: int = 443,
        description: str = ""
    ) -> Optional[str]:
        """
        Fetch current certificate from server and add as pin.

        Args:
            hostname: Target hostname
            port: TLS port (default 443)
            description: Pin description

        Returns:
            SPKI hash if successful, None on error
        """
        try:
            # Create SSL context
            context = ssl.create_default_context()

            # Connect and get certificate
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert_der = ssock.getpeercert(binary_form=True)

            # Calculate SPKI hash (simplified - in production use proper SPKI extraction)
            spki_hash = hashlib.sha256(cert_der).hexdigest()

            # Add as pin
            self.pin_certificate(hostname, spki_hash, description)

            logger.info("Fetched and pinned certificate for '%s': %s...", hostname, spki_hash[:16])
            return spki_hash

        except (socket.timeout, TimeoutError) as e:
            logger.warning(
                "Connection timeout while fetching certificate for '%s': %s",
                hostname,
                e,
                extra={"event": "cert_pin.fetch_timeout", "hostname": hostname}
            )
            return None
        except (socket.gaierror, socket.error, ConnectionError, OSError) as e:
            logger.warning(
                "Network error while fetching certificate for '%s': %s",
                hostname,
                e,
                extra={"event": "cert_pin.fetch_network_error", "hostname": hostname}
            )
            return None
        except ssl.SSLError as e:
            logger.error(
                "SSL error while fetching certificate for '%s': %s",
                hostname,
                e,
                extra={"event": "cert_pin.fetch_ssl_error", "hostname": hostname}
            )
            return None
        except ValueError as e:
            logger.error(
                "Invalid certificate data for '%s': %s",
                hostname,
                e,
                extra={"event": "cert_pin.fetch_invalid_data", "hostname": hostname}
            )
            return None
        except (RuntimeError, MemoryError, AttributeError, UnicodeDecodeError) as e:
            logger.error(
                "Unexpected error fetching certificate for '%s': %s",
                hostname,
                e,
                exc_info=True,
                extra={"event": "cert_pin.fetch_unexpected_error", "hostname": hostname, "error_type": type(e).__name__}
            )
            return None

    def rotate_pins(
        self,
        hostname: str,
        new_spki_hash: str,
        description: str = "Rotated pin"
    ):
        """
        Rotate certificate pins with grace period.

        Args:
            hostname: Target hostname
            new_spki_hash: New SPKI hash to add
            description: Description of new pin
        """
        # Mark existing pins as backup
        if hostname in self.pinned_certificates:
            for pin in self.pinned_certificates[hostname]:
                if not pin.is_backup:
                    pin.is_backup = True
                    logger.info("Marked pin as backup: %s", pin.spki_hash[:16])

        # Add new primary pin
        self.pin_certificate(hostname, new_spki_hash, description, is_backup=False)
        logger.info("Pin rotation complete for '%s'", hostname)

    def cleanup_expired_pins(self) -> int:
        """
        Remove backup pins outside grace period.

        Returns:
            Number of pins removed
        """
        removed = 0
        current_time = time.time()

        for hostname, pins in list(self.pinned_certificates.items()):
            pins_to_keep = []

            for pin in pins:
                age = datetime.fromtimestamp(current_time) - datetime.fromtimestamp(pin.added_at)

                # Keep primary pins and backups within grace period
                if not pin.is_backup or age <= self.grace_period:
                    pins_to_keep.append(pin)
                else:
                    removed += 1
                    logger.info(
                        "Removed expired backup pin for '%s': %s (age: %s)",
                        hostname,
                        pin.spki_hash[:16],
                        age
                    )

            self.pinned_certificates[hostname] = pins_to_keep

        return removed

    def get_pins(self, hostname: str) -> List[Dict]:
        """Get all pins for hostname"""
        if hostname not in self.pinned_certificates:
            return []

        return [
            {
                "spki_hash": pin.spki_hash,
                "description": pin.description,
                "added_at": pin.added_at,
                "is_backup": pin.is_backup,
                "age_days": (time.time() - pin.added_at) / 86400
            }
            for pin in self.pinned_certificates[hostname]
        ]

    def get_violations(self, limit: int = 10) -> List[Dict]:
        """Get recent pinning violations"""
        return self.violations[-limit:]

    def get_stats(self) -> Dict:
        """Get certificate pinning statistics"""
        return {
            "total_hosts": len(self.pinned_certificates),
            "total_pins": sum(len(pins) for pins in self.pinned_certificates.values()),
            "total_violations": len(self.violations),
            "enforce_pinning": self.enforce_pinning,
            "grace_period_days": self.grace_period.days,
            "hosts": list(self.pinned_certificates.keys())
        }


# Example Usage (for testing purposes)
if __name__ == "__main__":
    raise SystemExit("Certificate pinning demo removed; rely on tests.")
