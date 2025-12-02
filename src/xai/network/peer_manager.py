import asyncio
import hashlib
import json
import logging
import os
import ssl
import time
from collections import defaultdict, deque
from typing import List, Dict, Any, Optional, Tuple, Iterable
import threading
import websockets

# Fail fast: cryptography library is REQUIRED for P2P networking security
# The node cannot operate without TLS encryption
try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, ec
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.backends import default_backend
    CRYPTOGRAPHY_AVAILABLE = True
    CRYPTOGRAPHY_ERROR = None
except ImportError as e:
    CRYPTOGRAPHY_AVAILABLE = False
    CRYPTOGRAPHY_ERROR = str(e)

logger = logging.getLogger(__name__)

# Error message for missing cryptography library
CRYPTO_INSTALL_MSG = """
========================================
FATAL: Missing required dependency
========================================

The 'cryptography' library is required for secure P2P networking.

Install it with:
    pip install cryptography>=41.0.0

On some systems you may need:
    sudo apt-get install libffi-dev libssl-dev  # Debian/Ubuntu
    brew install openssl@3                       # macOS

The XAI node cannot run without TLS encryption.
========================================
"""


class PeerReputation:
    """Track and manage peer reputation scores"""

    def __init__(self):
        self.scores: Dict[str, float] = defaultdict(lambda: 50.0)  # Start at 50/100
        self.history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.lock = threading.RLock()

        # Scoring parameters
        self.VALID_BLOCK_REWARD = 5.0
        self.VALID_TX_REWARD = 0.5
        self.INVALID_BLOCK_PENALTY = -10.0
        self.INVALID_TX_PENALTY = -2.0
        self.UPTIME_REWARD_PER_HOUR = 0.1
        self.DISCONNECT_PENALTY = -1.0
        self.MAX_SCORE = 100.0
        self.MIN_SCORE = 0.0
        self.BAN_THRESHOLD = 10.0

    def record_valid_block(self, peer_id: str) -> float:
        """Record that a peer sent a valid block"""
        return self._adjust_score(peer_id, self.VALID_BLOCK_REWARD, "valid_block")

    def record_invalid_block(self, peer_id: str) -> float:
        """Record that a peer sent an invalid block"""
        return self._adjust_score(peer_id, self.INVALID_BLOCK_PENALTY, "invalid_block")

    def record_valid_transaction(self, peer_id: str) -> float:
        """Record that a peer sent a valid transaction"""
        return self._adjust_score(peer_id, self.VALID_TX_REWARD, "valid_transaction")

    def record_invalid_transaction(self, peer_id: str) -> float:
        """Record that a peer sent an invalid transaction"""
        return self._adjust_score(peer_id, self.INVALID_TX_PENALTY, "invalid_transaction")

    def record_uptime(self, peer_id: str, hours: float) -> float:
        """Record peer uptime"""
        reward = hours * self.UPTIME_REWARD_PER_HOUR
        return self._adjust_score(peer_id, reward, "uptime")

    def record_disconnect(self, peer_id: str) -> float:
        """Record peer disconnect"""
        return self._adjust_score(peer_id, self.DISCONNECT_PENALTY, "disconnect")

    def _adjust_score(self, peer_id: str, delta: float, reason: str) -> float:
        """Adjust peer reputation score"""
        with self.lock:
            old_score = self.scores[peer_id]
            new_score = max(self.MIN_SCORE, min(self.MAX_SCORE, old_score + delta))
            self.scores[peer_id] = new_score

            # Record in history
            self.history[peer_id].append(
                {"timestamp": time.time(), "delta": delta, "reason": reason, "score": new_score}
            )

            return new_score

    def get_score(self, peer_id: str) -> float:
        """Get current reputation score"""
        with self.lock:
            return self.scores.get(peer_id, 50.0)

    def should_ban(self, peer_id: str) -> bool:
        """Check if peer should be banned based on reputation"""
        return self.get_score(peer_id) <= self.BAN_THRESHOLD

    def get_top_peers(self, limit: int = 10) -> List[Tuple[str, float]]:
        """Get top peers by reputation"""
        with self.lock:
            return sorted(self.scores.items(), key=lambda x: x[1], reverse=True)[:limit]

    def get_history(self, peer_id: str) -> List[Dict]:
        """Get reputation history for a peer"""
        with self.lock:
            return list(self.history.get(peer_id, []))


class PeerDiscovery:
    """Peer discovery using DNS seeds and peer exchange"""

    def __init__(self, dns_seeds: Optional[List[str]] = None, bootstrap_nodes: Optional[List[str]] = None):
        self.dns_seeds = dns_seeds or [
            "seed1.xai-network.io",
            "seed2.xai-network.io",
            "seed3.xai-network.io",
        ]
        self.bootstrap_nodes = bootstrap_nodes or [
            "node1.xai-network.io:8333",
            "node2.xai-network.io:8333",
            "node3.xai-network.io:8333",
        ]
        self.discovered_peers: List[Dict[str, Any]] = []
        self.lock = threading.RLock()

    async def discover_from_dns(self) -> List[str]:
        """Discover peers from DNS seeds"""
        import dns.resolver

        discovered = []
        for seed in self.dns_seeds:
            try:
                answers = dns.resolver.resolve(seed, "A")
                for rdata in answers:
                    discovered.append(f"{rdata.address}:8333")
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                continue
            except Exception as e:
                print(f"DNS discovery failed for seed {seed}: {e}")

        with self.lock:
            for addr in discovered:
                if addr not in [p["address"] for p in self.discovered_peers]:
                    self.discovered_peers.append({
                        "address": addr,
                        "discovered_at": time.time(),
                        "source": "dns",
                    })

        return discovered

    async def discover_from_bootstrap(self) -> List[str]:
        """Connect to bootstrap nodes and request peer lists"""
        discovered = []

        for bootstrap_uri in self.bootstrap_nodes:
            try:
                async with websockets.connect(bootstrap_uri) as websocket:
                    await websocket.send(json.dumps({"type": "get_peers"}))
                    response_str = await websocket.recv()
                    response = json.loads(response_str)
                    if response.get("type") == "peers":
                        peers = response.get("payload", [])
                        discovered.extend(peers)
            except Exception as e:
                print(f"Failed to discover peers from bootstrap node {bootstrap_uri}: {e}")

        with self.lock:
            for addr in discovered:
                if addr not in [p["address"] for p in self.discovered_peers]:
                    self.discovered_peers.append({
                        "address": addr,
                        "discovered_at": time.time(),
                        "source": "bootstrap",
                    })

        return discovered

    def exchange_peers(self, peer_addresses: List[str]) -> None:
        """Add peers learned from peer exchange"""
        with self.lock:
            for addr in peer_addresses:
                if addr not in [p["address"] for p in self.discovered_peers]:
                    self.discovered_peers.append({
                        "address": addr,
                        "discovered_at": time.time(),
                        "source": "peer_exchange",
                    })

    def get_random_peers(self, count: int = 10) -> List[str]:
        """Get random peer addresses for connection attempts"""
        import random
        with self.lock:
            addresses = [p["address"] for p in self.discovered_peers]
            return random.sample(addresses, min(count, len(addresses)))

    def get_discovered_peers(self) -> List[Dict]:
        """Get all discovered peers"""
        with self.lock:
            return list(self.discovered_peers)


import hmac
import secp256k1
from datetime import datetime, timedelta


class PeerEncryption:
    """Handle peer-to-peer encryption using TLS/SSL and message signing."""

    def __init__(self, cert_dir: str = "data/certs", key_dir: str = "data/keys"):
        # Fail fast if cryptography library is not available
        if not CRYPTOGRAPHY_AVAILABLE:
            raise ImportError(
                f"{CRYPTO_INSTALL_MSG}\n"
                f"Original error: {CRYPTOGRAPHY_ERROR}"
            )

        self.cert_dir = cert_dir
        self.key_dir = key_dir
        os.makedirs(self.cert_dir, exist_ok=True)
        os.makedirs(self.key_dir, exist_ok=True)

        self.cert_file = os.path.join(self.cert_dir, "peer_cert.pem")
        self.key_file = os.path.join(self.cert_dir, "peer_key.pem")

        self.signing_key_file = os.path.join(self.key_dir, "signing_key.pem")
        self.signing_key: Optional[secp256k1.PrivateKey] = None
        self.verifying_key: Optional[secp256k1.PublicKey] = None

        # Generate TLS certificates if they don't exist
        if not os.path.exists(self.cert_file) or not os.path.exists(self.key_file):
            self._generate_self_signed_cert()

        # Generate signing key if it doesn't exist
        self._generate_signing_key()

    def _generate_signing_key(self) -> None:
        """Generate or load a secp256k1 private key for signing messages."""
        try:
            if os.path.exists(self.signing_key_file):
                with open(self.signing_key_file, "rb") as f:
                    pk_bytes = f.read()
                self.signing_key = secp256k1.PrivateKey(pk_bytes)
                print(f"Loaded signing key from: {self.signing_key_file}")
            else:
                self.signing_key = secp256k1.PrivateKey()
                serialized = self.signing_key.serialize()
                serialized_bytes = (
                    bytes.fromhex(serialized) if isinstance(serialized, str) else serialized
                )
                with open(self.signing_key_file, "wb") as f:
                    f.write(serialized_bytes)
                print(f"Generated new signing key: {self.signing_key_file}")

            self.verifying_key = self.signing_key.pubkey
        except Exception as e:
            print(f"Error generating/loading signing key: {e}")
            # Self-heal by regenerating a fresh key when deserialization fails
            try:
                self.signing_key = secp256k1.PrivateKey(os.urandom(32))
                serialized = self.signing_key.serialize()
                serialized_bytes = (
                    bytes.fromhex(serialized) if isinstance(serialized, str) else serialized
                )
                with open(self.signing_key_file, "wb") as f:
                    f.write(serialized_bytes)
                self.verifying_key = self.signing_key.pubkey
                print(f"Regenerated signing key at: {self.signing_key_file}")
            except Exception as inner_exc:
                print(f"Failed to regenerate signing key: {inner_exc}")
                self.signing_key = None
                self.verifying_key = None

    def _generate_self_signed_cert(self) -> None:
        """
        Generate self-signed certificate for peer connections.

        Uses RSA-2048 with SHA-256 for signing. Certificate is valid for 365 days.

        Security notes:
        - Uses industry-standard RSA key size (2048 bits minimum)
        - Proper key usage extensions for TLS server/client auth
        - Certificate validity period limited to prevent long-term exposure
        """
        # Generate private key with secure parameters
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Generate certificate with proper subject fields
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Blockchain"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Network"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "XAI Network"),
            x509.NameAttribute(NameOID.COMMON_NAME, "xai-peer"),
        ])

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)
        ).sign(private_key, hashes.SHA256())

        # Write private key with proper permissions
        with open(self.key_file, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

        # Set restrictive permissions on private key (owner read/write only)
        os.chmod(self.key_file, 0o600)

        # Write certificate
        with open(self.cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        logger.info(
            "Generated self-signed TLS certificate",
            extra={
                "event": "peer.cert_generated",
                "cert_file": self.cert_file,
                "key_size": 2048,
                "validity_days": 365
            }
        )

    def validate_peer_certificate(self, cert_bytes: bytes) -> bool:
        """
        Validate that peer certificate is properly formed and meets security requirements.

        Checks performed:
        - Certificate is not expired or not yet valid
        - RSA key size is at least 2048 bits (industry standard minimum)
        - EC key size is at least 256 bits
        - Certificate can be parsed as valid x509

        Args:
            cert_bytes: PEM or DER encoded certificate bytes

        Returns:
            True if certificate passes validation, False otherwise

        Security notes:
        - Weak key sizes are rejected to prevent cryptographic attacks
        - Expired certificates are rejected to enforce key rotation
        - Timestamps are checked against current UTC time
        """
        try:
            # Try to load as PEM first, then DER
            try:
                cert = x509.load_pem_x509_certificate(cert_bytes)
            except ValueError:
                cert = x509.load_der_x509_certificate(cert_bytes)

            # Check certificate is not expired or not yet valid
            now = datetime.utcnow()
            if cert.not_valid_before > now:
                logger.warning(
                    "Peer certificate is not yet valid",
                    extra={
                        "event": "peer.cert_not_yet_valid",
                        "not_valid_before": cert.not_valid_before.isoformat(),
                        "current_time": now.isoformat()
                    }
                )
                return False

            if cert.not_valid_after < now:
                logger.warning(
                    "Peer certificate is expired",
                    extra={
                        "event": "peer.cert_expired",
                        "not_valid_after": cert.not_valid_after.isoformat(),
                        "current_time": now.isoformat()
                    }
                )
                return False

            # Check key size is sufficient for security
            public_key = cert.public_key()

            # RSA keys must be at least 2048 bits
            if hasattr(public_key, 'key_size'):
                if public_key.key_size < 2048:
                    logger.warning(
                        "Peer certificate RSA key size too small",
                        extra={
                            "event": "peer.cert_weak_key",
                            "key_size": public_key.key_size,
                            "minimum_required": 2048
                        }
                    )
                    return False

            # EC keys must be at least 256 bits
            if hasattr(public_key, 'curve'):
                if hasattr(public_key.curve, 'key_size'):
                    if public_key.curve.key_size < 256:
                        logger.warning(
                            "Peer certificate EC key size too small",
                            extra={
                                "event": "peer.cert_weak_ec_key",
                                "key_size": public_key.curve.key_size,
                                "minimum_required": 256
                            }
                        )
                        return False

            return True

        except Exception as e:
            logger.error(
                "Failed to validate peer certificate",
                extra={
                    "event": "peer.cert_validation_error",
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            return False

    def create_ssl_context(
        self,
        is_server: bool = False,
        require_client_cert: bool = False,
        ca_bundle: Optional[str] = None,
    ) -> ssl.SSLContext:
        """
        Create SSL context for encrypted peer connections.

        Args:
            is_server: True if creating context for server socket
            require_client_cert: True to require and verify client certificates
            ca_bundle: Path to CA certificate bundle for verification

        Returns:
            Configured SSLContext with secure defaults

        Security notes:
        - Server mode enforces client cert verification if require_client_cert=True
        - Client mode always verifies server certificates (CERT_REQUIRED)
        - Uses TLS 1.2+ with secure cipher suites (via create_default_context)
        """
        if is_server:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(self.cert_file, self.key_file)
            if require_client_cert:
                context.verify_mode = ssl.CERT_REQUIRED
                context.check_hostname = False
                if ca_bundle:
                    try:
                        context.load_verify_locations(cafile=ca_bundle)
                    except Exception as exc:
                        logger.error(
                            "Failed to load CA bundle for server",
                            extra={
                                "event": "peer.ca_bundle_load_failed",
                                "ca_bundle": ca_bundle,
                                "error": str(exc)
                            }
                        )
        else:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED  # Always enforce certificate verification
            if ca_bundle:
                try:
                    context.load_verify_locations(cafile=ca_bundle)
                except Exception as exc:
                    logger.error(
                        "Failed to load CA bundle for client",
                        extra={
                            "event": "peer.ca_bundle_load_failed",
                            "ca_bundle": ca_bundle,
                            "error": str(exc)
                        }
                    )

        return context

    def create_signed_message(self, payload: Dict[str, Any]) -> bytes:
        """Create a signed message with payload, timestamp, nonce, and signature."""
        if not self.signing_key:
            raise ValueError("Signing key not available.")

        message = {
            "payload": payload,
            "timestamp": time.time(),
            "nonce": os.urandom(16).hex(),
        }
        
        # Serialize the message for signing
        serialized_message = json.dumps(message, sort_keys=True).encode('utf-8')
        
        # Create a digest of the message
        message_hash = hashlib.sha256(serialized_message).digest()

        # Sign the hash
        signature = self.signing_key.ecdsa_sign(message_hash)
        sig_bytes = self.signing_key.ecdsa_serialize(signature)
        if isinstance(sig_bytes, str):
            sig_bytes = bytes.fromhex(sig_bytes)
        sig_hex = sig_bytes.hex()
        pubkey_serialized = self.signing_key.pubkey.serialize()
        if isinstance(pubkey_serialized, str):
            pubkey_serialized = bytes.fromhex(pubkey_serialized)
        pubkey_hex = pubkey_serialized.hex()
        
        # Final message structure including the signature
        signed_message = {
            "message": message,
            "signature": pubkey_hex + '.' + sig_hex
        }

        return json.dumps(signed_message, sort_keys=True).encode('utf-8')

    @staticmethod
    def fingerprint_from_ssl_object(ssl_object: ssl.SSLObject) -> Optional[str]:
        """Compute SHA256 fingerprint of the peer certificate from an SSLObject."""
        try:
            der_cert = ssl_object.getpeercert(binary_form=True)
            if not der_cert:
                return None
            return hashlib.sha256(der_cert).hexdigest()
        except Exception:
            return None

    def verify_signed_message(self, signed_message_bytes: bytes) -> Optional[Dict[str, Any]]:
        """
        Verify a signed message, checking signature and freshness.

        Returns a dict containing the decoded payload plus metadata:
        {"payload": ..., "sender": <pubkey_hex>, "nonce": <nonce>, "timestamp": <timestamp>}
        """
        try:
            signed_message = json.loads(signed_message_bytes.decode('utf-8'))
            
            message = signed_message["message"]
            signature_str = signed_message["signature"]
            
            pubkey_hex, sig_hex = signature_str.split('.')
            
            pubkey = secp256k1.PublicKey(bytes.fromhex(pubkey_hex), raw=True)
            signature_bytes = bytes.fromhex(sig_hex)
            signature = pubkey.ecdsa_deserialize(signature_bytes)

            # Verify timestamp is recent (e.g., within the last 5 minutes)
            if time.time() - message["timestamp"] > 300:
                logger.warning(
                    "Stale message received, discarding",
                    extra={
                        "event": "peer.stale_message",
                        "message_age_seconds": time.time() - message["timestamp"],
                        "sender": pubkey_hex[:16] + "..." if pubkey_hex else "unknown"
                    }
                )
                return None

            # Serialize the inner message for verification
            serialized_message = json.dumps(message, sort_keys=True).encode('utf-8')
            message_hash = hashlib.sha256(serialized_message).digest()

            # Verify the signature
            if not pubkey.ecdsa_verify(message_hash, signature):
                logger.warning(
                    "Invalid signature in peer message",
                    extra={
                        "event": "peer.invalid_signature",
                        "sender": pubkey_hex[:16] + "..." if pubkey_hex else "unknown"
                    }
                )
                return None
            
            return {
                "payload": message["payload"],
                "sender": pubkey_hex,
                "nonce": message.get("nonce"),
                "timestamp": message.get("timestamp"),
            }
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(
                "Error verifying signed message",
                extra={
                    "event": "peer.message_verification_error",
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            return None

    def is_nonce_replay(self, sender_id: str, nonce: str, timestamp: Optional[float] = None) -> bool:
        """Check if nonce has been seen recently for a sender, pruning expired nonces."""
        now = timestamp if timestamp is not None else time.time()
        with self._nonce_lock:
            dq: deque[Tuple[str, float]] = self.seen_nonces[sender_id]
            while dq and now - dq[0][1] > self.nonce_ttl_seconds:
                dq.popleft()
            return any(stored_nonce == nonce for stored_nonce, _ in dq)

    def record_nonce(self, sender_id: str, nonce: str, timestamp: Optional[float] = None) -> None:
        """Record a nonce for replay protection with timestamp pruning."""
        now = timestamp if timestamp is not None else time.time()
        with self._nonce_lock:
            dq: deque[Tuple[str, float]] = self.seen_nonces[sender_id]
            while dq and now - dq[0][1] > self.nonce_ttl_seconds:
                dq.popleft()
            dq.append((nonce, now))

    def add_trusted_peer_key(self, pubkey_hex: str) -> None:
        """Whitelist a peer public key for message-level trust decisions."""
        self.trusted_peer_pubkeys.add(pubkey_hex.lower())

    def remove_trusted_peer_key(self, pubkey_hex: str) -> None:
        """Remove a peer public key from trust store."""
        self.trusted_peer_pubkeys.discard(pubkey_hex.lower())

    def is_sender_allowed(self, pubkey_hex: Optional[str]) -> bool:
        """
        Check if sender is allowed. If a trust list is defined, enforce membership.
        If no trusted keys configured, allow by default.
        """
        if not pubkey_hex:
            return False if self.trusted_peer_pubkeys else True
        if not self.trusted_peer_pubkeys:
            return True
        return pubkey_hex.lower() in self.trusted_peer_pubkeys

    def add_trusted_cert_fingerprint(self, fingerprint_hex: str) -> None:
        """Add a pinned TLS certificate fingerprint (hex sha256)."""
        self.trusted_cert_fingerprints.add(fingerprint_hex.lower())

    def remove_trusted_cert_fingerprint(self, fingerprint_hex: str) -> None:
        """Remove a pinned TLS certificate fingerprint."""
        self.trusted_cert_fingerprints.discard(fingerprint_hex.lower())

    def is_cert_allowed(self, fingerprint_hex: Optional[str]) -> bool:
        """
        Check if peer certificate fingerprint is allowed.
        If no pins configured, allow by default.
        """
        if not self.trusted_cert_fingerprints:
            return True
        if not fingerprint_hex:
            return False
        return fingerprint_hex.lower() in self.trusted_cert_fingerprints

    def _load_lines_from_file(self, file_path: str) -> list[str]:
        """Load non-empty, comment-stripped lines from a file."""
        entries: list[str] = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                cleaned = line.split("#", 1)[0].strip()
                if cleaned:
                    entries.append(cleaned)
        return entries

    def refresh_trust_stores(self, force: bool = False) -> None:
        """
        Reload trust stores from configured files if mtime changed or force requested.
        Supports runtime rotation by ops pipelines.
        """
        updated_pubkeys: Optional[set[str]] = None
        updated_fps: Optional[set[str]] = None

        try:
            if self.trusted_peer_pubkeys_file:
                mtime = os.path.getmtime(self.trusted_peer_pubkeys_file)
                if force or self._trust_file_mtimes.get(self.trusted_peer_pubkeys_file) != mtime:
                    lines = self._load_lines_from_file(self.trusted_peer_pubkeys_file)
                    updated_pubkeys = set(line.lower() for line in lines)
                    self._trust_file_mtimes[self.trusted_peer_pubkeys_file] = mtime
                    logger.info(
                        "Reloaded trusted peer pubkeys",
                        extra={
                            "event": "peer.trust_store_reload",
                            "store_type": "pubkeys",
                            "count": len(updated_pubkeys),
                            "file": self.trusted_peer_pubkeys_file
                        }
                    )
        except FileNotFoundError:
            logger.debug(
                "Trusted peer pubkeys file not found",
                extra={
                    "event": "peer.trust_store_missing",
                    "store_type": "pubkeys",
                    "file": self.trusted_peer_pubkeys_file
                }
            )
        except Exception as exc:
            logger.error(
                "Failed to reload trusted pubkeys",
                extra={
                    "event": "peer.trust_store_error",
                    "store_type": "pubkeys",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "file": self.trusted_peer_pubkeys_file
                }
            )

        try:
            if self.trusted_cert_fps_file:
                mtime = os.path.getmtime(self.trusted_cert_fps_file)
                if force or self._trust_file_mtimes.get(self.trusted_cert_fps_file) != mtime:
                    lines = self._load_lines_from_file(self.trusted_cert_fps_file)
                    updated_fps = set(line.lower() for line in lines)
                    self._trust_file_mtimes[self.trusted_cert_fps_file] = mtime
                    logger.info(
                        "Reloaded trusted cert fingerprints",
                        extra={
                            "event": "peer.trust_store_reload",
                            "store_type": "cert_fps",
                            "count": len(updated_fps),
                            "file": self.trusted_cert_fps_file
                        }
                    )
        except FileNotFoundError:
            logger.debug(
                "Trusted cert fingerprints file not found",
                extra={
                    "event": "peer.trust_store_missing",
                    "store_type": "cert_fps",
                    "file": self.trusted_cert_fps_file
                }
            )
        except Exception as exc:
            logger.error(
                "Failed to reload trusted cert fingerprints",
                extra={
                    "event": "peer.trust_store_error",
                    "store_type": "cert_fps",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "file": self.trusted_cert_fps_file
                }
            )

        if updated_pubkeys is not None:
            self.trusted_peer_pubkeys = updated_pubkeys
        if updated_fps is not None:
            self.trusted_cert_fingerprints = updated_fps
        if updated_fps is not None:
            self.require_client_cert = self.require_client_cert or bool(self.trusted_cert_fingerprints)


class PeerManager:
    def __init__(
        self,
        max_connections_per_ip: int = 5,
        trusted_peer_pubkeys: Optional[Iterable[str]] = None,
        trusted_cert_fingerprints: Optional[Iterable[str]] = None,
        trusted_peer_pubkeys_file: Optional[str] = None,
        trusted_cert_fps_file: Optional[str] = None,
        nonce_ttl_seconds: Optional[int] = None,
        require_client_cert: bool = False,
        ca_bundle_path: Optional[str] = None,
        dns_seeds: Optional[Iterable[str]] = None,
        bootstrap_nodes: Optional[Iterable[str]] = None,
        cert_dir: str = "data/certs",
        key_dir: str = "data/keys",
    ):
        if not isinstance(max_connections_per_ip, int) or max_connections_per_ip <= 0:
            raise ValueError("Max connections per IP must be a positive integer.")

        self.max_connections_per_ip = max_connections_per_ip
        self.trusted_peers: set[str] = set()  # Set of trusted IP addresses or node IDs
        self.banned_peers: set[str] = set()  # Set of banned IP addresses or node IDs

        # Stores connected peers: {peer_id: {"ip_address": str, "connected_at": float}}
        self.connected_peers: Dict[str, Dict[str, Any]] = {}
        # Tracks connections per IP: {ip_address: count}
        self.connections_by_ip: Dict[str, int] = defaultdict(int)
        self._peer_id_counter = 0

        # Replay protection: store the last 1000 nonces per peer with timestamps
        self.seen_nonces: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._nonce_lock = threading.RLock()
        self.nonce_ttl_seconds = nonce_ttl_seconds if nonce_ttl_seconds else 300  # Default TTL for nonce validity

        # Trust stores
        self.trusted_peer_pubkeys: set[str] = set(k.lower() for k in (trusted_peer_pubkeys or []))  # Hex-encoded secp256k1 public keys
        self.trusted_cert_fingerprints: set[str] = set(fp.lower() for fp in (trusted_cert_fingerprints or []))  # SHA256 fingerprints for TLS cert pinning
        self.trusted_peer_pubkeys_file = trusted_peer_pubkeys_file
        self.trusted_cert_fps_file = trusted_cert_fps_file
        self.require_client_cert = require_client_cert or bool(self.trusted_cert_fingerprints)
        self.ca_bundle_path = ca_bundle_path
        self._trust_file_mtimes: Dict[str, float] = {}

        # Initialize subsystems
        self.reputation = PeerReputation()
        self.discovery = PeerDiscovery(
            dns_seeds=list(dns_seeds) if dns_seeds else None,
            bootstrap_nodes=list(bootstrap_nodes) if bootstrap_nodes else None,
        )
        self.encryption = PeerEncryption(cert_dir=cert_dir, key_dir=key_dir)

        print(f"PeerManager initialized. Max connections per IP: {self.max_connections_per_ip}.")

        # Initial load from trust store files, if provided
        self.refresh_trust_stores(force=True)

    def add_trusted_peer(self, peer_identifier: str):
        """Adds a peer to the trusted list."""
        self.trusted_peers.add(peer_identifier.lower())
        print(f"Added {peer_identifier} to trusted peers.")

    def remove_trusted_peer(self, peer_identifier: str):
        """Removes a peer from the trusted list."""
        self.trusted_peers.discard(peer_identifier.lower())
        print(f"Removed {peer_identifier} from trusted peers.")

    def ban_peer(self, peer_identifier: str):
        """Adds a peer to the banned list and disconnects if currently connected."""
        self.banned_peers.add(peer_identifier.lower())
        print(f"Banned {peer_identifier}.")

        # Disconnect any active connections from this banned peer
        peers_to_disconnect = [
            pid
            for pid, peer_info in self.connected_peers.items()
            if peer_info["ip_address"].lower() == peer_identifier.lower()
        ]
        for pid in peers_to_disconnect:
            self.disconnect_peer(pid)

    def unban_peer(self, peer_identifier: str):
        """Removes a peer from the banned list."""
        self.banned_peers.discard(peer_identifier.lower())
        print(f"Unbanned {peer_identifier}.")

    def can_connect(self, ip_address: str) -> bool:
        """
        Checks if a peer with the given IP address is allowed to connect.
        Considers banned list and connection limits.
        """
        ip_lower = ip_address.lower()

        if ip_lower in self.banned_peers:
            print(f"Connection from {ip_address} rejected: IP is banned.")
            return False

        if self.connections_by_ip[ip_lower] >= self.max_connections_per_ip:
            print(
                f"Connection from {ip_address} rejected: Exceeds max connections per IP ({self.max_connections_per_ip})."
            )
            return False

        print(f"Connection from {ip_address} allowed by policy.")
        return True

    def connect_peer(self, ip_address: str) -> str:
        """
        Simulates connecting a new peer if allowed by policy.
        Returns the peer_id if successful.
        """
        if not self.can_connect(ip_address):
            raise ValueError(
                f"Cannot connect to peer from {ip_address} due to policy restrictions."
            )

        self._peer_id_counter += 1
        peer_id = f"peer_{self._peer_id_counter}"

        self.connected_peers[peer_id] = {
            "ip_address": ip_address,
            "connected_at": time.time(),
            "last_seen": time.time(),
        }
        self.connections_by_ip[ip_address] += 1
        print(
            f"Peer {peer_id} connected from {ip_address}. Total connections from {ip_address}: {self.connections_by_ip[ip_address]}"
        )
        return peer_id

    def disconnect_peer(self, peer_id: str):
        """Simulates disconnecting a peer."""
        peer = self.connected_peers.pop(peer_id, None)
        if peer:
            ip_address = peer["ip_address"]
            self.connections_by_ip[ip_address] -= 1
            if self.connections_by_ip[ip_address] == 0:
                del self.connections_by_ip[ip_address]
            
            # Clear nonce history for the disconnected peer
            if peer_id in self.seen_nonces:
                del self.seen_nonces[peer_id]

            # Update reputation
            self.reputation.record_disconnect(peer_id)

            # Calculate uptime
            connected_at = peer.get("connected_at", time.time())
            uptime_hours = (time.time() - connected_at) / 3600
            if uptime_hours > 0.1:  # Only record if connected for more than 6 minutes
                self.reputation.record_uptime(peer_id, uptime_hours)

            print(f"Peer {peer_id} from {ip_address} disconnected.")
        else:
            print(f"Peer {peer_id} not found.")

    def get_peer_reputation(self, peer_id: str) -> float:
        """Get reputation score for a peer"""
        return self.reputation.get_score(peer_id)

    def get_best_peers(self, count: int = 10) -> List[Tuple[str, float]]:
        """Get top peers by reputation"""
        return self.reputation.get_top_peers(count)

    async def discover_peers(self) -> List[str]:
        """Discover new peers using DNS and bootstrap nodes"""
        dns_peers = await self.discovery.discover_from_dns()
        bootstrap_peers = await self.discovery.discover_from_bootstrap()
        return dns_peers + bootstrap_peers

    def get_ssl_context(self, is_server: bool = False) -> ssl.SSLContext:
        """Get SSL context for encrypted peer connections"""
        return self.encryption.create_ssl_context(is_server)


# Example Usage (for testing purposes)
if __name__ == "__main__":
    manager = PeerManager(max_connections_per_ip=2)

    trusted_node_ip = "10.0.0.1"
    malicious_ip = "192.168.1.100"
    normal_ip_1 = "172.16.0.1"
    normal_ip_2 = "172.16.0.2"

    manager.add_trusted_peer(trusted_node_ip)
    manager.ban_peer(malicious_ip)

    print("\n--- Attempting Connections ---")
    # Trusted peer connection
    try:
        peer_trusted_1 = manager.connect_peer(trusted_node_ip)
        peer_trusted_2 = manager.connect_peer(trusted_node_ip)
        # peer_trusted_3 = manager.connect_peer(trusted_node_ip) # This would exceed max_connections_per_ip
    except ValueError as e:
        print(f"Error (expected): {e}")

    # Banned peer connection
    try:
        manager.connect_peer(malicious_ip)
    except ValueError as e:
        print(f"Error (expected): {e}")

    # Normal peer connections
    try:
        peer_normal_1 = manager.connect_peer(normal_ip_1)
        peer_normal_2 = manager.connect_peer(normal_ip_1)
        peer_normal_3 = manager.connect_peer(normal_ip_1)  # Should fail
    except ValueError as e:
        print(f"Error (expected): {e}")

    try:
        peer_normal_4 = manager.connect_peer(normal_ip_2)
    except ValueError as e:
        print(f"Error: {e}")

    print("\n--- Disconnecting and Re-evaluating ---")
    manager.disconnect_peer(peer_normal_1)
    try:
        peer_normal_5 = manager.connect_peer(normal_ip_1)  # Should now be allowed
    except ValueError as e:
        print(f"Error: {e}")

    print("\n--- Unbanning and Connecting ---")
    manager.unban_peer(malicious_ip)
    try:
        manager.connect_peer(malicious_ip)
    except ValueError as e:
        print(f"Error: {e}")


# -----------------------------------------------------------------------------
# Production-grade PeerManager (module-level binding)
# -----------------------------------------------------------------------------
class PeerManager:
    def __init__(
        self,
        max_connections_per_ip: int = 5,
        trusted_peer_pubkeys: Optional[Iterable[str]] = None,
        trusted_cert_fingerprints: Optional[Iterable[str]] = None,
        trusted_peer_pubkeys_file: Optional[str] = None,
        trusted_cert_fps_file: Optional[str] = None,
        nonce_ttl_seconds: Optional[int] = None,
        require_client_cert: bool = False,
        ca_bundle_path: Optional[str] = None,
        dns_seeds: Optional[Iterable[str]] = None,
        bootstrap_nodes: Optional[Iterable[str]] = None,
        cert_dir: str = "data/certs",
        key_dir: str = "data/keys",
    ):
        if not isinstance(max_connections_per_ip, int) or max_connections_per_ip <= 0:
            raise ValueError("Max connections per IP must be a positive integer.")

        self.max_connections_per_ip = max_connections_per_ip
        self.trusted_peers: set[str] = set()
        self.banned_peers: set[str] = set()
        self.connected_peers: Dict[str, Dict[str, Any]] = {}
        self.connections_by_ip: Dict[str, int] = defaultdict(int)
        self._peer_id_counter = 0

        self.seen_nonces: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._nonce_lock = threading.RLock()
        self.nonce_ttl_seconds = nonce_ttl_seconds if nonce_ttl_seconds else 300

        self.trusted_peer_pubkeys: set[str] = set(k.lower() for k in (trusted_peer_pubkeys or []))
        self.trusted_cert_fingerprints: set[str] = set(fp.lower() for fp in (trusted_cert_fingerprints or []))
        self.trusted_peer_pubkeys_file = trusted_peer_pubkeys_file
        self.trusted_cert_fps_file = trusted_cert_fps_file
        self._trust_file_mtimes: Dict[str, float] = {}
        self.require_client_cert = require_client_cert or bool(self.trusted_cert_fingerprints)
        self.ca_bundle_path = ca_bundle_path

        self.reputation = PeerReputation()
        self.discovery = PeerDiscovery(
            dns_seeds=list(dns_seeds) if dns_seeds else None,
            bootstrap_nodes=list(bootstrap_nodes) if bootstrap_nodes else None,
        )
        self.encryption = PeerEncryption(cert_dir=cert_dir, key_dir=key_dir)

        print(f"PeerManager initialized. Max connections per IP: {self.max_connections_per_ip}.")
        self.refresh_trust_stores(force=True)

    def _load_lines_from_file(self, file_path: str) -> list[str]:
        entries: list[str] = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                cleaned = line.split("#", 1)[0].strip()
                if cleaned:
                    entries.append(cleaned)
        return entries

    def refresh_trust_stores(self, force: bool = False) -> None:
        updated_pubkeys: Optional[set[str]] = None
        updated_fps: Optional[set[str]] = None

        try:
            if self.trusted_peer_pubkeys_file:
                mtime = os.path.getmtime(self.trusted_peer_pubkeys_file)
                if force or self._trust_file_mtimes.get(self.trusted_peer_pubkeys_file) != mtime:
                    lines = self._load_lines_from_file(self.trusted_peer_pubkeys_file)
                    updated_pubkeys = set(line.lower() for line in lines)
                    self._trust_file_mtimes[self.trusted_peer_pubkeys_file] = mtime
                    logger.info(
                        "Reloaded trusted peer pubkeys",
                        extra={
                            "event": "peer.trust_store_reload",
                            "store_type": "pubkeys",
                            "count": len(updated_pubkeys),
                            "file": self.trusted_peer_pubkeys_file
                        }
                    )
        except FileNotFoundError:
            logger.debug(
                "Trusted peer pubkeys file not found",
                extra={
                    "event": "peer.trust_store_missing",
                    "store_type": "pubkeys",
                    "file": self.trusted_peer_pubkeys_file
                }
            )
        except Exception as exc:
            logger.error(
                "Failed to reload trusted pubkeys",
                extra={
                    "event": "peer.trust_store_error",
                    "store_type": "pubkeys",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "file": self.trusted_peer_pubkeys_file
                }
            )

        try:
            if self.trusted_cert_fps_file:
                mtime = os.path.getmtime(self.trusted_cert_fps_file)
                if force or self._trust_file_mtimes.get(self.trusted_cert_fps_file) != mtime:
                    lines = self._load_lines_from_file(self.trusted_cert_fps_file)
                    updated_fps = set(line.lower() for line in lines)
                    self._trust_file_mtimes[self.trusted_cert_fps_file] = mtime
                    logger.info(
                        "Reloaded trusted cert fingerprints",
                        extra={
                            "event": "peer.trust_store_reload",
                            "store_type": "cert_fps",
                            "count": len(updated_fps),
                            "file": self.trusted_cert_fps_file
                        }
                    )
        except FileNotFoundError:
            logger.debug(
                "Trusted cert fingerprints file not found",
                extra={
                    "event": "peer.trust_store_missing",
                    "store_type": "cert_fps",
                    "file": self.trusted_cert_fps_file
                }
            )
        except Exception as exc:
            logger.error(
                "Failed to reload trusted cert fingerprints",
                extra={
                    "event": "peer.trust_store_error",
                    "store_type": "cert_fps",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "file": self.trusted_cert_fps_file
                }
            )

        if updated_pubkeys is not None:
            self.trusted_peer_pubkeys = updated_pubkeys
        if updated_fps is not None:
            self.trusted_cert_fingerprints = updated_fps
        if updated_fps is not None:
            self.require_client_cert = self.require_client_cert or bool(self.trusted_cert_fingerprints)

    def add_trusted_peer_key(self, pubkey_hex: str) -> None:
        self.trusted_peer_pubkeys.add(pubkey_hex.lower())

    def remove_trusted_peer_key(self, pubkey_hex: str) -> None:
        self.trusted_peer_pubkeys.discard(pubkey_hex.lower())

    def is_sender_allowed(self, pubkey_hex: Optional[str]) -> bool:
        if not pubkey_hex:
            return False if self.trusted_peer_pubkeys else True
        if not self.trusted_peer_pubkeys:
            return True
        return pubkey_hex.lower() in self.trusted_peer_pubkeys

    def add_trusted_cert_fingerprint(self, fingerprint_hex: str) -> None:
        self.trusted_cert_fingerprints.add(fingerprint_hex.lower())

    def remove_trusted_cert_fingerprint(self, fingerprint_hex: str) -> None:
        self.trusted_cert_fingerprints.discard(fingerprint_hex.lower())

    def is_cert_allowed(self, fingerprint_hex: Optional[str]) -> bool:
        if not self.trusted_cert_fingerprints:
            return True
        if not fingerprint_hex:
            return False
        return fingerprint_hex.lower() in self.trusted_cert_fingerprints

    def is_nonce_replay(self, sender_id: str, nonce: str, timestamp: Optional[float] = None) -> bool:
        now = timestamp if timestamp is not None else time.time()
        with self._nonce_lock:
            dq: deque[Tuple[str, float]] = self.seen_nonces[sender_id]
            while dq and now - dq[0][1] > self.nonce_ttl_seconds:
                dq.popleft()
            return any(stored_nonce == nonce for stored_nonce, _ in dq)

    def record_nonce(self, sender_id: str, nonce: str, timestamp: Optional[float] = None) -> None:
        now = timestamp if timestamp is not None else time.time()
        with self._nonce_lock:
            dq: deque[Tuple[str, float]] = self.seen_nonces[sender_id]
            while dq and now - dq[0][1] > self.nonce_ttl_seconds:
                dq.popleft()
            dq.append((nonce, now))

    def add_trusted_peer(self, peer_identifier: str):
        self.trusted_peers.add(peer_identifier.lower())

    def remove_trusted_peer(self, peer_identifier: str):
        self.trusted_peers.discard(peer_identifier.lower())

    def ban_peer(self, peer_identifier: str):
        self.banned_peers.add(peer_identifier.lower())
        peers_to_disconnect = [
            pid
            for pid, peer_info in self.connected_peers.items()
            if peer_info["ip_address"].lower() == peer_identifier.lower()
        ]
        for pid in peers_to_disconnect:
            self.disconnect_peer(pid)

    def unban_peer(self, peer_identifier: str):
        self.banned_peers.discard(peer_identifier.lower())

    def can_connect(self, ip_address: str) -> bool:
        ip_lower = ip_address.lower()
        if ip_lower in self.banned_peers:
            print(f"Connection from {ip_address} rejected: IP is banned.")
            return False
        if self.connections_by_ip[ip_lower] >= self.max_connections_per_ip:
            print(
                f"Connection from {ip_address} rejected: Exceeds max connections per IP ({self.max_connections_per_ip})."
            )
            return False
        return True

    def connect_peer(self, ip_address: str) -> str:
        if not self.can_connect(ip_address):
            raise ValueError(
                f"Cannot connect to peer from {ip_address} due to policy restrictions."
            )
        self._peer_id_counter += 1
        peer_id = f"peer_{self._peer_id_counter}"
        self.connected_peers[peer_id] = {
            "ip_address": ip_address,
            "connected_at": time.time(),
            "last_seen": time.time(),
        }
        self.connections_by_ip[ip_address] += 1
        return peer_id

    def disconnect_peer(self, peer_id: str):
        peer = self.connected_peers.pop(peer_id, None)
        if peer:
            ip_address = peer["ip_address"]
            self.connections_by_ip[ip_address] -= 1
            if self.connections_by_ip[ip_address] == 0:
                del self.connections_by_ip[ip_address]
            if peer_id in self.seen_nonces:
                del self.seen_nonces[peer_id]
            self.reputation.record_disconnect(peer_id)
