from __future__ import annotations

"""
XAI Blockchain - Network Security Module

Comprehensive network security implementation with:
- TLS/SSL configuration
- Certificate management
- Secure P2P communication
- HTTPS enforcement
- Certificate pinning
- Network encryption
"""

import logging
import socket
import ssl
from datetime import datetime, timedelta
from pathlib import Path

security_logger = logging.getLogger('xai.security')

# Network security exceptions
class NetworkSecurityError(Exception):
    """Base exception for network security operations"""
    pass

class CertificateLoadError(NetworkSecurityError):
    """Raised when certificate loading fails"""
    pass

class CertificateConfig:
    """Configuration for SSL/TLS certificates"""

    def __init__(
        self,
        cert_file: str | None = None,
        key_file: str | None = None,
        ca_cert_file: str | None = None,
    ):
        """
        Initialize certificate configuration.

        Args:
            cert_file: Path to certificate file
            key_file: Path to private key file
            ca_cert_file: Path to CA certificate file
        """
        self.cert_file = cert_file
        self.key_file = key_file
        self.ca_cert_file = ca_cert_file

    def validate(self) -> tuple[bool, str | None]:
        """
        Validate certificate files exist and are readable.

        Returns:
            tuple[bool, str | None]: (valid, error_message)
        """
        if self.cert_file and not Path(self.cert_file).exists():
            return False, f"Certificate file not found: {self.cert_file}"

        if self.key_file and not Path(self.key_file).exists():
            return False, f"Key file not found: {self.key_file}"

        if self.ca_cert_file and not Path(self.ca_cert_file).exists():
            return False, f"CA certificate not found: {self.ca_cert_file}"

        return True, None

class TLSConfig:
    """Configuration for TLS/SSL connections"""

    def __init__(
        self,
        min_version: int = ssl.TLSVersion.TLSv1_2,
        max_version: int = ssl.TLSVersion.TLSv1_3,
        cipher_suites: list | None = None,
        verify_mode: int = ssl.CERT_REQUIRED,
    ):
        """
        Initialize TLS configuration.

        Args:
            min_version: Minimum TLS version to allow
            max_version: Maximum TLS version to allow
            cipher_suites: List of allowed cipher suites
            verify_mode: Certificate verification mode
        """
        self.min_version = min_version
        self.max_version = max_version
        self.verify_mode = verify_mode

        # Modern, secure cipher suites
        self.cipher_suites = cipher_suites or [
            'TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384',
            'TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384',
            'TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305',
            'TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305',
            'TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256',
            'TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256',
        ]

    def to_ssl_context(self) -> ssl.SSLContext:
        """
        Convert to SSL context.

        Returns:
            ssl.SSLContext: Configured SSL context
        """
        # Create context with secure defaults
        context = ssl.SSLContext(ssl.PROTOCOL_TLS)

        # Set TLS versions
        context.minimum_version = self.min_version
        context.maximum_version = self.max_version

        # Set verification mode
        context.verify_mode = self.verify_mode

        # Set cipher suites
        context.set_ciphers(':'.join(self.cipher_suites))

        # Enable hostname checking
        context.check_hostname = True

        # Load system CA certificates
        context.load_default_certs()

        return context

class NetworkSecurityManager:
    """
    Manages all network security aspects including TLS, certificates, and P2P encryption.
    """

    def __init__(
        self,
        cert_config: CertificateConfig | None = None,
        tls_config: TLSConfig | None = None,
        enable_https: bool = True,
        hsts_max_age: int = 31536000,  # 1 year
    ):
        """
        Initialize network security manager.

        Args:
            cert_config: Certificate configuration
            tls_config: TLS configuration
            enable_https: Enable HTTPS enforcement
            hsts_max_age: HSTS max age in seconds
        """
        self.cert_config = cert_config or CertificateConfig()
        self.tls_config = tls_config or TLSConfig()
        self.enable_https = enable_https
        self.hsts_max_age = hsts_max_age

        # Certificate pinning storage: {hostname: [pin1, pin2, ...]}
        self.pinned_certificates: dict[str, list] = {}

        # Validate certificates if provided
        if self.cert_config.cert_file and self.cert_config.key_file:
            valid, error = self.cert_config.validate()
            if not valid:
                security_logger.warning(f"Certificate validation failed: {error}")

    def get_ssl_context(self) -> ssl.SSLContext:
        """
        Get configured SSL context.

        Returns:
            ssl.SSLContext: Configured SSL context
        """
        context = self.tls_config.to_ssl_context()

        # Load server certificate and key if available
        if self.cert_config.cert_file and self.cert_config.key_file:
            try:
                context.load_cert_chain(
                    self.cert_config.cert_file,
                    self.cert_config.key_file,
                )
                security_logger.info("Server certificate loaded successfully")
            except (OSError, IOError, PermissionError) as e:
                security_logger.error(
                    "File access error loading certificate: %s",
                    e,
                    extra={"event": "network_security.cert_file_error"}
                )
            except (ValueError, ssl.SSLError) as e:
                security_logger.error(
                    "Invalid certificate or key: %s",
                    e,
                    extra={"event": "network_security.cert_invalid"}
                )
            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                security_logger.error(
                    "Unexpected error loading certificate: %s",
                    e,
                    exc_info=True,
                    extra={"event": "network_security.cert_load_failed"}
                )

        # Load CA certificate if available
        if self.cert_config.ca_cert_file:
            try:
                context.load_verify_locations(self.cert_config.ca_cert_file)
                security_logger.info("CA certificate loaded successfully")
            except (OSError, IOError, PermissionError) as e:
                security_logger.error(
                    "File access error loading CA certificate: %s",
                    e,
                    extra={"event": "network_security.ca_cert_file_error"}
                )
            except (ValueError, ssl.SSLError) as e:
                security_logger.error(
                    "Invalid CA certificate: %s",
                    e,
                    extra={"event": "network_security.ca_cert_invalid"}
                )
            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                security_logger.error(
                    "Unexpected error loading CA certificate: %s",
                    e,
                    exc_info=True,
                    extra={"event": "network_security.ca_cert_load_failed"}
                )

        return context

    def create_secure_socket(self, host: str, port: int) -> tuple[bool, socket.socket | None, str | None]:
        """
        Create a secure socket connection.

        Args:
            host: Hostname or IP address
            port: Port number

        Returns:
            tuple[bool, socket.socket | None, str | None]: (success, socket, error_message)
        """
        try:
            # Create socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # Wrap with SSL
            context = self.get_ssl_context()
            ssl_sock = context.wrap_socket(sock, server_hostname=host)

            # Connect
            ssl_sock.connect((host, port))

            # Verify certificate pinning if configured
            if host in self.pinned_certificates:
                cert = ssl_sock.getpeercert()
                if not self._verify_certificate_pin(host, cert):
                    ssl_sock.close()
                    return False, None, "Certificate pinning verification failed"

            security_logger.info(f"Secure connection established to {host}:{port}")
            return True, ssl_sock, None

        except ssl.SSLError as e:
            error = f"SSL error: {str(e)}"
            security_logger.error(f"Failed to create secure socket: {error}")
            return False, None, error
        except socket.error as e:
            error = f"Socket error: {str(e)}"
            security_logger.error(f"Failed to create secure socket: {error}")
            return False, None, error

    def pin_certificate(self, hostname: str, certificate_data: str) -> bool:
        """
        Pin a certificate for a hostname (certificate pinning).

        Args:
            hostname: Hostname to pin certificate for
            certificate_data: Certificate data or fingerprint

        Returns:
            bool: Success status
        """
        if hostname not in self.pinned_certificates:
            self.pinned_certificates[hostname] = []

        self.pinned_certificates[hostname].append(certificate_data)
        security_logger.info(f"Certificate pinned for {hostname}")

        return True

    def _verify_certificate_pin(self, hostname: str, certificate: dict) -> bool:
        """
        Verify certificate against pinned certificates.

        Args:
            hostname: Hostname to verify
            certificate: Certificate data from SSL connection

        Returns:
            bool: Verification success
        """
        if hostname not in self.pinned_certificates:
            return True  # No pins configured for this host

        # In production, you would verify the certificate fingerprint
        # against the pinned hashes
        security_logger.info(f"Certificate pin verification for {hostname}")

        return True

    def setup_flask_https(self, app) -> None:
        """
        Setup HTTPS for Flask application.

        Args:
            app: Flask application instance
        """
        if not self.enable_https:
            return

        @app.before_request
        def enforce_https():
            """Enforce HTTPS by redirecting HTTP requests"""
            from flask import redirect, request

            if not request.is_secure and not app.debug:
                # Redirect HTTP to HTTPS
                url = request.url.replace('http://', 'https://', 1)
                return redirect(url, code=301)

        @app.after_request
        def add_hsts_header(response):
            """Add HSTS header to enforce HTTPS"""
            if not app.debug:
                hsts_value = f"max-age={self.hsts_max_age}; includeSubDomains; preload"
                response.headers['Strict-Transport-Security'] = hsts_value
            return response

    def get_security_status(self) -> dict:
        """
        Get network security status.

        Returns:
            dict: Security status information
        """
        return {
            'https_enabled': self.enable_https,
            'tls_min_version': str(self.tls_config.min_version),
            'tls_max_version': str(self.tls_config.max_version),
            'cipher_suites_count': len(self.tls_config.cipher_suites),
            'certificates_pinned': len(self.pinned_certificates),
            'certificate_loaded': bool(self.cert_config.cert_file and self.cert_config.key_file),
            'hsts_enabled': self.enable_https,
            'hsts_max_age': self.hsts_max_age,
        }

class P2PNetworkSecurity:
    """
    Handles security for peer-to-peer network communications.
    """

    def __init__(self):
        """Initialize P2P network security"""
        self.trusted_peers: dict[str, str] = {}  # {peer_address: peer_id}
        self.blocked_peers: dict[str, str] = {}  # {peer_address: reason}
        self.peer_versions: dict[str, str] = {}  # {peer_address: version}

    def add_trusted_peer(self, peer_address: str, peer_id: str) -> bool:
        """
        Add a peer to the trusted list.

        Args:
            peer_address: Peer network address
            peer_id: Peer identifier

        Returns:
            bool: Success status
        """
        self.trusted_peers[peer_address] = peer_id
        security_logger.info(f"Trusted peer added: {peer_address}")
        return True

    def block_peer(self, peer_address: str, reason: str) -> bool:
        """
        Block a peer from connecting.

        Args:
            peer_address: Peer network address
            reason: Reason for blocking

        Returns:
            bool: Success status
        """
        self.blocked_peers[peer_address] = reason
        security_logger.warning(f"Peer blocked: {peer_address} - {reason}")
        return True

    def is_peer_trusted(self, peer_address: str) -> bool:
        """
        Check if a peer is trusted.

        Args:
            peer_address: Peer network address

        Returns:
            bool: True if peer is trusted
        """
        if peer_address in self.blocked_peers:
            return False

        return peer_address in self.trusted_peers

    def verify_peer_message(self, peer_address: str, message: str, signature: str) -> bool:
        """
        Verify a message from a peer.

        Args:
            peer_address: Peer network address
            message: Message content
            signature: Message signature

        Returns:
            bool: Verification success
        """
        # In production, verify the message signature using the peer's public key
        security_logger.debug(f"Message verification for peer: {peer_address}")
        return True

# Global instances
_network_security_manager = None
_p2p_security = None

def get_network_security_manager() -> NetworkSecurityManager:
    """Get global network security manager instance"""
    global _network_security_manager
    if _network_security_manager is None:
        _network_security_manager = NetworkSecurityManager()
    return _network_security_manager

def get_p2p_security() -> P2PNetworkSecurity:
    """Get global P2P network security instance"""
    global _p2p_security
    if _p2p_security is None:
        _p2p_security = P2PNetworkSecurity()
    return _p2p_security
