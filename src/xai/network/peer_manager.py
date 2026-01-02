from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import logging
import math
import os
import secrets
import ssl
import threading
import time
from collections import defaultdict, deque
from collections.abc import Iterable
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection

from xai.core.config import Config
from xai.core.security.p2p_security import P2PSecurityConfig
from xai.network.geoip_resolver import GeoIPMetadata, GeoIPResolver

# Fail fast: cryptography library is REQUIRED for P2P networking security
# The node cannot operate without TLS encryption
try:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec, rsa
    from cryptography.x509.oid import NameOID
    CRYPTOGRAPHY_AVAILABLE = True
    CRYPTOGRAPHY_ERROR = None
except ImportError as e:
    CRYPTOGRAPHY_AVAILABLE = False
    CRYPTOGRAPHY_ERROR = str(e)

logger = logging.getLogger(__name__)

# Peer management exceptions
class PeerError(Exception):
    """Base exception for peer management operations"""
    pass

class PeerConnectionError(PeerError):
    """Raised when peer connection fails"""
    pass

class PeerCommunicationError(PeerError):
    """Raised when peer communication fails"""
    pass

class PeerValidationError(PeerError):
    """Raised when peer data validation fails"""
    pass

class PeerNetworkError(PeerError):
    """Raised when network operations fail"""
    pass

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

class PeerConnectionPool:
    """
    Maintain persistent WebSocket connections to peers for reuse.

    This pool reduces connection overhead by:
    - Reusing established WebSocket connections instead of creating new ones
    - Maintaining health checks via WebSocket ping/pong
    - Implementing graceful connection lifecycle management
    - Enforcing per-peer connection limits

    Security considerations:
    - Health checks prevent use of stale/dead connections
    - Connection limits prevent resource exhaustion
    - Automatic cleanup on errors prevents connection leaks
    - Timeout enforcement prevents indefinite blocking
    """

    def __init__(
        self,
        max_connections_per_peer: int = 3,
        connection_timeout: float = 30.0,
        idle_timeout: float = 300.0,
        ping_timeout: float = 5.0,
        ssl_context: ssl.SSLContext | None = None,
    ):
        """
        Initialize the connection pool.

        Args:
            max_connections_per_peer: Maximum pooled connections per peer URI
            connection_timeout: Timeout in seconds for acquiring a connection
            idle_timeout: Maximum idle time before connection cleanup
            ping_timeout: Timeout for health check ping/pong
        """
        self.pools: dict[str, asyncio.Queue] = {}
        self.max_per_peer = max(1, max_connections_per_peer)
        self.connection_timeout = max(1.0, connection_timeout)
        self.idle_timeout = max(60.0, idle_timeout)
        self.ping_timeout = max(1.0, ping_timeout)
        self.ssl_context = ssl_context
        self._active_connections: dict[str, int] = {}
        self._lock = asyncio.Lock()
        self._closed = False

        # Metrics for pool utilization
        self._total_connections_created = 0
        self._total_connections_reused = 0
        self._total_health_check_failures = 0

        logger.info(
            "PeerConnectionPool initialized",
            extra={
                "event": "peer.pool.initialized",
                "max_per_peer": self.max_per_peer,
                "connection_timeout": self.connection_timeout,
                "idle_timeout": self.idle_timeout,
            }
        )

    async def get_connection(self, peer_uri: str) -> ClientConnection:
        """
        Get a connection from the pool or create a new one.

        Args:
            peer_uri: WebSocket URI of the peer (ws://host:port or wss://host:port)

        Returns:
            Active WebSocket connection

        Raises:
            asyncio.TimeoutError: If connection acquisition times out
            RuntimeError: If pool is closed
            websockets.exceptions.WebSocketException: If connection fails
        """
        if self._closed:
            raise RuntimeError("Connection pool is closed")

        async with self._lock:
            if peer_uri not in self.pools:
                self.pools[peer_uri] = asyncio.Queue(maxsize=self.max_per_peer)
                self._active_connections[peer_uri] = 0

        pool = self.pools[peer_uri]

        # Try to get existing connection from pool
        try:
            conn = pool.get_nowait()
            if await self._is_healthy(conn):
                self._total_connections_reused += 1
                logger.debug(
                    "Reused pooled connection",
                    extra={
                        "event": "peer.pool.connection_reused",
                        "peer_uri": peer_uri,
                        "reuse_count": self._total_connections_reused,
                    }
                )
                return conn
            # Connection is dead, close it and fall through to create new one
            await self._close_connection(conn)
            async with self._lock:
                self._active_connections[peer_uri] = max(0, self._active_connections[peer_uri] - 1)
        except asyncio.QueueEmpty:
            pass

        # Check if we can create a new connection or must wait
        async with self._lock:
            if self._active_connections[peer_uri] < self.max_per_peer:
                self._active_connections[peer_uri] += 1
            else:
                # Wait for a connection to become available
                logger.debug(
                    "Pool exhausted, waiting for connection",
                    extra={
                        "event": "peer.pool.waiting",
                        "peer_uri": peer_uri,
                        "active": self._active_connections[peer_uri],
                    }
                )
                conn = await asyncio.wait_for(
                    pool.get(),
                    timeout=self.connection_timeout
                )
                if await self._is_healthy(conn):
                    self._total_connections_reused += 1
                    return conn
                # Connection died while waiting, close and create new
                await self._close_connection(conn)

        # Create new connection
        try:
            conn = await websockets.connect(
                peer_uri,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5,
                max_size=10 * 1024 * 1024,  # 10MB max message size
                ssl=self.ssl_context,
            )
            self._total_connections_created += 1
            logger.debug(
                "Created new pooled connection",
                extra={
                    "event": "peer.pool.connection_created",
                    "peer_uri": peer_uri,
                    "total_created": self._total_connections_created,
                    "active": self._active_connections[peer_uri],
                }
            )
            return conn
        except (asyncio.TimeoutError, TimeoutError) as e:
            # Failed to create connection, decrement counter
            async with self._lock:
                self._active_connections[peer_uri] = max(0, self._active_connections[peer_uri] - 1)
            logger.warning(
                "Connection timeout creating pooled connection: %s",
                e,
                extra={
                    "event": "peer.pool.connection_timeout",
                    "peer_uri": peer_uri,
                }
            )
            raise PeerConnectionError(f"Connection timeout to {peer_uri}") from e
        except (ConnectionError, OSError) as e:
            async with self._lock:
                self._active_connections[peer_uri] = max(0, self._active_connections[peer_uri] - 1)
            logger.warning(
                "Network error creating pooled connection: %s",
                e,
                extra={
                    "event": "peer.pool.connection_network_error",
                    "peer_uri": peer_uri,
                    "error_type": type(e).__name__,
                }
            )
            raise PeerNetworkError(f"Network error connecting to {peer_uri}: {e}") from e
        except (ValueError, TypeError) as e:
            # Invalid URI or configuration error
            async with self._lock:
                self._active_connections[peer_uri] = max(0, self._active_connections[peer_uri] - 1)
            logger.error(
                "Invalid configuration for pooled connection: %s",
                e,
                extra={
                    "event": "peer.pool.connection_config_error",
                    "peer_uri": peer_uri,
                    "error_type": type(e).__name__,
                }
            )
            raise PeerNetworkError(f"Invalid connection configuration: {e}") from e

    async def return_connection(
        self,
        peer_uri: str,
        conn: ClientConnection
    ) -> None:
        """
        Return a connection to the pool for reuse.

        Args:
            peer_uri: WebSocket URI of the peer
            conn: Connection to return to pool
        """
        if self._closed:
            await self._close_connection(conn)
            return

        # Health check before returning to pool
        if not await self._is_healthy(conn):
            await self._close_connection(conn)
            async with self._lock:
                self._active_connections[peer_uri] = max(0, self._active_connections[peer_uri] - 1)
            logger.debug(
                "Connection failed health check, not returning to pool",
                extra={
                    "event": "peer.pool.unhealthy_return",
                    "peer_uri": peer_uri,
                }
            )
            return

        # Try to return to pool
        try:
            pool = self.pools.get(peer_uri)
            if pool:
                pool.put_nowait(conn)
                logger.debug(
                    "Returned connection to pool",
                    extra={
                        "event": "peer.pool.connection_returned",
                        "peer_uri": peer_uri,
                        "pool_size": pool.qsize(),
                    }
                )
            else:
                # Pool was removed, close connection
                await self._close_connection(conn)
                async with self._lock:
                    self._active_connections[peer_uri] = max(0, self._active_connections[peer_uri] - 1)
        except asyncio.QueueFull:
            # Pool full, close excess connection
            await self._close_connection(conn)
            async with self._lock:
                self._active_connections[peer_uri] = max(0, self._active_connections[peer_uri] - 1)
            logger.debug(
                "Pool full, closing excess connection",
                extra={
                    "event": "peer.pool.excess_closed",
                    "peer_uri": peer_uri,
                }
            )

    async def _is_healthy(self, conn: ClientConnection) -> bool:
        """
        Check if connection is still alive via ping/pong.

        Args:
            conn: Connection to check

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            # Check if connection is already closed
            if conn.closed:
                return False

            # Send ping and wait for pong
            pong_waiter = await conn.ping()
            await asyncio.wait_for(pong_waiter, timeout=self.ping_timeout)
            return True
        except asyncio.TimeoutError:
            self._total_health_check_failures += 1
            logger.debug(
                "Connection health check timed out",
                extra={
                    "event": "peer.pool.health_check_timeout",
                    "failures": self._total_health_check_failures,
                }
            )
            return False
        except (asyncio.TimeoutError, TimeoutError) as e:
            self._total_health_check_failures += 1
            logger.debug(
                "Connection health check timeout: %s",
                e,
                extra={
                    "event": "peer.pool.health_check_timeout",
                    "failures": self._total_health_check_failures,
                }
            )
            return False
        except (ConnectionError, OSError) as e:
            self._total_health_check_failures += 1
            logger.debug(
                "Connection health check network error: %s",
                e,
                extra={
                    "event": "peer.pool.health_check_network_error",
                    "failures": self._total_health_check_failures,
                }
            )
            return False
        except (ValueError, TypeError, AttributeError) as e:
            self._total_health_check_failures += 1
            logger.debug(
                "Connection health check data error: %s",
                e,
                extra={
                    "event": "peer.pool.health_check_data_error",
                    "error_type": type(e).__name__,
                    "failures": self._total_health_check_failures,
                }
            )
            return False

    async def _close_connection(self, conn: ClientConnection) -> None:
        """
        Safely close a connection.

        Args:
            conn: Connection to close
        """
        try:
            if not conn.closed:
                await conn.close()
        except (asyncio.TimeoutError, TimeoutError) as e:
            logger.debug(
                "Timeout closing connection: %s",
                e,
                extra={
                    "event": "peer.pool.close_timeout",
                }
            )
        except (ConnectionError, OSError, AttributeError) as e:
            logger.debug(
                "Error closing connection: %s",
                e,
                extra={
                    "event": "peer.pool.close_error",
                    "error_type": type(e).__name__,
                }
            )
        except (ValueError, TypeError) as e:
            logger.debug(
                "Invalid state during connection close: %s",
                e,
                extra={
                    "event": "peer.pool.close_state_error",
                    "error_type": type(e).__name__,
                }
            )

    async def close_all(self) -> None:
        """
        Close all pooled connections and shut down the pool.

        This should be called during graceful shutdown.
        """
        self._closed = True

        async with self._lock:
            for peer_uri, pool in list(self.pools.items()):
                while not pool.empty():
                    try:
                        conn = pool.get_nowait()
                        await self._close_connection(conn)
                    except asyncio.QueueEmpty:
                        break
                    except (ConnectionError, OSError, AttributeError) as e:
                        logger.warning(
                            "Error closing pooled connection: %s",
                            e,
                            extra={
                                "event": "peer.pool.close_pooled_error",
                                "peer_uri": peer_uri,
                                "error_type": type(e).__name__,
                            }
                        )
                    except (ValueError, TypeError) as e:
                        logger.warning(
                            "Invalid state while closing pooled connection: %s",
                            e,
                            extra={
                                "event": "peer.pool.close_state_error",
                                "peer_uri": peer_uri,
                                "error_type": type(e).__name__,
                            }
                        )

        logger.info(
            "PeerConnectionPool closed",
            extra={
                "event": "peer.pool.closed",
                "total_created": self._total_connections_created,
                "total_reused": self._total_connections_reused,
                "health_failures": self._total_health_check_failures,
                "reuse_ratio": (
                    self._total_connections_reused / max(1, self._total_connections_created + self._total_connections_reused)
                )
            }
        )

    def get_metrics(self) -> dict[str, Any]:
        """
        Get pool utilization metrics.

        Returns:
            Dictionary with pool metrics
        """
        total_ops = self._total_connections_created + self._total_connections_reused
        return {
            "connections_created": self._total_connections_created,
            "connections_reused": self._total_connections_reused,
            "total_operations": total_ops,
            "reuse_ratio": self._total_connections_reused / max(1, total_ops),
            "health_check_failures": self._total_health_check_failures,
            "active_pools": len(self.pools),
            "active_connections": sum(self._active_connections.values()),
        }

class PeerConnection:
    """
    Context manager for pooled peer connections.

    Automatically acquires connection from pool on entry and returns it on exit.
    Ensures connections are always returned to pool, even on exceptions.

    Example:
        async with PeerConnection(pool, "ws://peer:8333") as ws:
            await ws.send(json.dumps({"type": "ping"}))
            response = await ws.recv()
    """

    def __init__(self, pool: PeerConnectionPool, peer_uri: str):
        """
        Initialize context manager.

        Args:
            pool: Connection pool to use
            peer_uri: WebSocket URI of the peer
        """
        self.pool = pool
        self.peer_uri = peer_uri
        self.conn: ClientConnection | None = None

    async def __aenter__(self) -> ClientConnection:
        """
        Acquire connection from pool.

        Returns:
            Active WebSocket connection
        """
        self.conn = await self.pool.get_connection(self.peer_uri)
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Return connection to pool.

        Connection is returned even if an exception occurred during usage.
        """
        if self.conn:
            await self.pool.return_connection(self.peer_uri, self.conn)

class PeerReputation:
    """Track and manage peer reputation scores"""

    def __init__(self):
        self.scores: dict[str, float] = defaultdict(lambda: 50.0)  # Start at 50/100
        self.history: dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._last_decay: dict[str, float] = defaultdict(time.time)
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
        self.BASELINE_SCORE = 50.0
        self.DECAY_HALF_LIFE_HOURS = float(getattr(Config, "P2P_REPUTATION_DECAY_HALF_LIFE_HOURS", 24.0))
        self._decay_constant = math.log(2) / (self.DECAY_HALF_LIFE_HOURS * 3600)

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
            self._apply_decay(peer_id)
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
            self._apply_decay(peer_id)
            return self.scores.get(peer_id, 50.0)

    def should_ban(self, peer_id: str) -> bool:
        """Check if peer should be banned based on reputation"""
        return self.get_score(peer_id) <= self.BAN_THRESHOLD

    def get_top_peers(self, limit: int = 10) -> list[tuple[str, float]]:
        """Get top peers by reputation"""
        with self.lock:
            return sorted(self.scores.items(), key=lambda x: x[1], reverse=True)[:limit]

    def get_history(self, peer_id: str) -> list[dict]:
        """Get reputation history for a peer"""
        with self.lock:
            return list(self.history.get(peer_id, []))

    def _apply_decay(self, peer_id: str) -> None:
        """
        Gradually return scores toward the neutral baseline over time so old misbehavior
        does not permanently poison a peer. Uses exponential decay with configurable half-life.
        """
        last = self._last_decay.get(peer_id, time.time())
        now = time.time()
        elapsed = now - last
        if elapsed <= 0:
            return
        current = self.scores[peer_id]
        decay_factor = math.exp(-self._decay_constant * elapsed)
        decayed = self.BASELINE_SCORE + (current - self.BASELINE_SCORE) * decay_factor
        self.scores[peer_id] = min(self.MAX_SCORE, max(self.MIN_SCORE, decayed))
        self._last_decay[peer_id] = now

class PeerDiscovery:
    """
    Peer discovery using DNS seeds and peer exchange.

    Maintains a connection pool for efficient communication with bootstrap nodes
    and discovered peers.
    """

    def __init__(
        self,
        dns_seeds: list[str] | None = None,
        bootstrap_nodes: list[str] | None = None,
        connection_pool: PeerConnectionPool | None = None,
        encryption: "PeerEncryption" | None = None,
    ):
        self.dns_seeds = dns_seeds or [
            "seed1.xai-network.io",
            "seed2.xai-network.io",
            "seed3.xai-network.io",
        ]
        raw_bootstrap = bootstrap_nodes or [
            "node1.xai-network.io:8333",
            "node2.xai-network.io:8333",
            "node3.xai-network.io:8333",
        ]
        self.bootstrap_nodes = [
            uri for uri in (self._normalize_peer_uri(node) for node in raw_bootstrap) if uri
        ]
        self.discovered_peers: list[dict[str, Any]] = []
        self.lock = threading.RLock()
        self.encryption = encryption

        # Initialize or use provided connection pool
        if connection_pool is not None:
            self.connection_pool = connection_pool
        else:
            client_ssl_context: ssl.SSLContext | None = None
            if str(getattr(Config, "NETWORK", "testnet")).lower() == "testnet":
                client_ssl_context = ssl._create_unverified_context()
                client_ssl_context.check_hostname = False
                client_ssl_context.verify_mode = ssl.CERT_NONE
            self.connection_pool = PeerConnectionPool(
                max_connections_per_peer=3,
                connection_timeout=30.0,
                idle_timeout=300.0,
                ssl_context=client_ssl_context,
            )

    @staticmethod
    def _normalize_peer_uri(peer: str) -> str:
        """Ensure peer addresses include a websocket scheme and default port."""
        if not peer:
            return ""
        peer = peer.strip()
        if peer.startswith(("ws://", "wss://")):
            return peer
        if "://" in peer:
            return peer
        if ":" in peer:
            return f"wss://{peer}"
        return f"wss://{peer}:8765"

    async def discover_from_dns(self) -> list[str]:
        """Discover peers from DNS seeds"""
        import dns.resolver

        discovered = []
        for seed in self.dns_seeds:
            try:
                answers = dns.resolver.resolve(seed, "A")
                for rdata in answers:
                    normalized = self._normalize_peer_uri(f"{rdata.address}:8333")
                    if normalized:
                        discovered.append(normalized)
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                continue
            except (dns.resolver.Timeout, TimeoutError) as e:
                logger.debug(
                    "DNS discovery timeout for seed %s: %s",
                    seed,
                    e,
                    extra={"event": "peer.discovery.dns_timeout", "seed": seed}
                )
            except (dns.resolver.YXDOMAIN, dns.exception.DNSException) as e:
                logger.warning(
                    "DNS error for seed %s: %s",
                    seed,
                    e,
                    extra={"event": "peer.discovery.dns_error", "seed": seed, "error_type": type(e).__name__}
                )
            except (ValueError, TypeError) as e:
                logger.warning(
                    "Invalid DNS configuration for seed %s: %s",
                    seed,
                    e,
                    extra={"event": "peer.discovery.dns_config_error", "seed": seed, "error_type": type(e).__name__}
                )

        with self.lock:
            for addr in discovered:
                if addr not in [p["address"] for p in self.discovered_peers]:
                    self.discovered_peers.append({
                        "address": addr,
                        "discovered_at": time.time(),
                        "source": "dns",
                    })

        return discovered

    async def discover_from_bootstrap(self) -> list[str]:
        """
        Connect to bootstrap nodes and request peer lists.

        Uses connection pooling to reuse WebSocket connections across multiple
        discovery attempts, significantly reducing connection overhead.

        Returns:
            List of discovered peer addresses
        """
        discovered = []
        if not self.encryption:
            logger.debug(
                "Skipping bootstrap discovery - encryption unavailable for signing",
                extra={"event": "peer.discovery.bootstrap_skipped"},
            )
            return discovered
        handshake_payload = {
            "type": "handshake",
            "payload": {
                "version": getattr(P2PSecurityConfig, "PROTOCOL_VERSION", "1"),
                "features": list(getattr(P2PSecurityConfig, "SUPPORTED_FEATURES", set())),
                "node_id": self.encryption._node_identity_fingerprint(),  # noqa: SLF001
                "height": 0,
            },
        }
        request_payload = {"type": "get_peers"}
        for bootstrap_uri in self.bootstrap_nodes:
            try:
                # Use connection pool for efficient connection reuse
                async with PeerConnection(self.connection_pool, bootstrap_uri) as websocket:
                    try:
                        signed_handshake = self.encryption.create_signed_message(handshake_payload)
                        # Add newline delimiter to prevent message concatenation
                        await websocket.send(signed_handshake.decode("utf-8") + "\n")
                    except (ValueError, RuntimeError) as exc:
                        logger.warning(
                            "Failed to send signed handshake to bootstrap %s: %s",
                            bootstrap_uri,
                            exc,
                            extra={
                                "event": "peer.discovery.handshake_send_failed",
                                "bootstrap_uri": bootstrap_uri,
                                "error_type": type(exc).__name__,
                            },
                        )
                        continue

                    # Optionally consume the remote handshake before sending requests
                    try:
                        raw_initial = await asyncio.wait_for(websocket.recv(), timeout=5)
                        raw_bytes = raw_initial if isinstance(raw_initial, (bytes, bytearray)) else raw_initial.encode("utf-8")
                        self.encryption.verify_signed_message(raw_bytes)
                    except asyncio.TimeoutError:
                        pass
                    except Exception:  # noqa: BLE001 - debug logging only
                        logger.debug(
                            "Ignoring invalid initial message from bootstrap",
                            extra={"event": "peer.discovery.bootstrap_initial_invalid", "bootstrap_uri": bootstrap_uri},
                        )

                    try:
                        signed_request = self.encryption.create_signed_message(request_payload)
                        # Add newline delimiter to prevent message concatenation
                        await websocket.send(signed_request.decode("utf-8") + "\n")
                    except (ValueError, RuntimeError) as exc:
                        logger.warning(
                            "Failed to send signed peer request to bootstrap %s: %s",
                            bootstrap_uri,
                            exc,
                            extra={
                                "event": "peer.discovery.get_peers_send_failed",
                                "bootstrap_uri": bootstrap_uri,
                                "error_type": type(exc).__name__,
                            },
                        )
                        continue

                    response_payload: dict[str, Any] | None = None
                    for _ in range(3):
                        raw_response = await websocket.recv()
                        raw_bytes = raw_response if isinstance(raw_response, (bytes, bytearray)) else raw_response.encode("utf-8")
                        verified = self.encryption.verify_signed_message(raw_bytes)
                        if not verified:
                            continue
                        data = verified.get("payload") or {}
                        if data.get("type") == "handshake":
                            continue
                        response_payload = data
                        break

                    if response_payload and response_payload.get("type") == "peers":
                        peer_entries = response_payload.get("payload") or []
                        peers = [
                            uri
                            for uri in (self._normalize_peer_uri(p) for p in peer_entries)
                            if uri
                        ]
                        discovered.extend(peers)
                        logger.debug(
                            "Discovered peers from bootstrap node",
                            extra={
                                "event": "peer.discovery.bootstrap_success",
                                "bootstrap_uri": bootstrap_uri,
                                "peer_count": len(peers),
                            }
                        )
            except asyncio.TimeoutError:
                logger.warning(
                    "Timeout discovering peers from bootstrap node",
                    extra={
                        "event": "peer.discovery.bootstrap_timeout",
                        "bootstrap_uri": bootstrap_uri,
                    }
                )
            except (ConnectionError, OSError) as e:
                logger.warning(
                    "Network error discovering peers from bootstrap node: %s",
                    e,
                    extra={
                        "event": "peer.discovery.bootstrap_network_error",
                        "bootstrap_uri": bootstrap_uri,
                        "error_type": type(e).__name__,
                    }
                )
            except (ValueError, KeyError, json.JSONDecodeError, TypeError) as e:
                logger.warning(
                    "Invalid response from bootstrap node: %s",
                    e,
                    extra={
                        "event": "peer.discovery.bootstrap_invalid_response",
                        "bootstrap_uri": bootstrap_uri,
                        "error_type": type(e).__name__,
                    }
                )

        with self.lock:
            for addr in discovered:
                if addr not in [p["address"] for p in self.discovered_peers]:
                    self.discovered_peers.append({
                        "address": addr,
                        "discovered_at": time.time(),
                        "source": "bootstrap",
                    })

        return discovered

    def exchange_peers(self, peer_addresses: list[str]) -> None:
        """Add peers learned from peer exchange"""
        with self.lock:
            for addr in peer_addresses:
                normalized = self._normalize_peer_uri(addr)
                if not normalized:
                    continue
                if normalized not in [p["address"] for p in self.discovered_peers]:
                    self.discovered_peers.append({
                        "address": normalized,
                        "discovered_at": time.time(),
                        "source": "peer_exchange",
                    })

    def get_random_peers(self, count: int = 10) -> list[str]:
        """
        Get random peer addresses for connection attempts

        Uses cryptographically secure random selection to prevent
        predictable peer selection attacks.
        """
        import secrets
        with self.lock:
            addresses = [p["address"] for p in self.discovered_peers]
            if not addresses:
                return []
            # Use cryptographically secure random sampling
            sr = secrets.SystemRandom()
            return sr.sample(addresses, min(count, len(addresses)))

    def get_discovered_peers(self) -> list[dict]:
        """Get all discovered peers"""
        with self.lock:
            return list(self.discovered_peers)

    async def close(self) -> None:
        """
        Close the discovery service and clean up connection pool.

        Should be called during graceful shutdown.
        """
        await self.connection_pool.close_all()

    def get_pool_metrics(self) -> dict[str, Any]:
        """
        Get connection pool metrics for monitoring.

        Returns:
            Dictionary with pool utilization statistics
        """
        return self.connection_pool.get_metrics()

class PeerProofOfWork:
    """Perform and validate proof-of-work for peer admission."""

    def __init__(
        self,
        enabled: bool = True,
        difficulty_bits: int = 18,
        max_iterations: int = 250000,
        reuse_window_seconds: int = 600,
    ):
        self.enabled = enabled
        self.difficulty_bits = max(1, int(difficulty_bits))
        self.target = 1 << (256 - self.difficulty_bits)
        self.max_iterations = max(1, int(max_iterations))
        self.reuse_window_seconds = max(1, int(reuse_window_seconds))
        self._solutions: dict[str, float] = {}
        self._lock = threading.RLock()

    def solve(self, pubkey_hex: str, timestamp: int, message_nonce: str, payload_hash: str) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        base = f"{pubkey_hex}:{timestamp}:{message_nonce}:{payload_hash}"
        for _ in range(self.max_iterations):
            nonce = secrets.token_hex(16)
            digest = hashlib.sha256(f"{base}:{nonce}".encode("utf-8")).digest()
            if int.from_bytes(digest, "big") < self.target:
                return {"nonce": nonce, "difficulty": self.difficulty_bits}
        raise RuntimeError("Peer PoW solver exceeded iteration budget without finding a solution")

    def verify(
        self,
        pubkey_hex: str,
        timestamp: int,
        message_nonce: str,
        payload_hash: str,
        proof: dict[str, Any] | None,
    ) -> bool:
        if not self.enabled:
            return True
        if not proof or "nonce" not in proof or not message_nonce:
            return False
        nonce = str(proof["nonce"])
        base = f"{pubkey_hex}:{timestamp}:{message_nonce}:{payload_hash}:{nonce}"
        digest_value = int.from_bytes(hashlib.sha256(base.encode("utf-8")).digest(), "big")
        if digest_value >= self.target:
            return False

        key = f"{pubkey_hex}:{message_nonce}"
        now = time.time()
        with self._lock:
            self._purge_locked(now)
            if key in self._solutions:
                return False
            self._solutions[key] = now
        return True

    def _purge_locked(self, now: float) -> None:
        cutoff = now - self.reuse_window_seconds
        stale = [key for key, ts in self._solutions.items() if ts < cutoff]
        for key in stale:
            self._solutions.pop(key, None)

import hmac
from datetime import datetime, timedelta

import secp256k1


class PeerEncryption:
    """Handle peer-to-peer encryption using TLS/SSL and message signing."""

    def __init__(
        self,
        cert_dir: str = "data/certs",
        key_dir: str = "data/keys",
        pow_manager: "PeerProofOfWork" | None = None,
        session_ttl_seconds: int = 900,
    ):
        # Fail fast if cryptography library is not available
        if not CRYPTOGRAPHY_AVAILABLE:
            raise ImportError(
                f"{CRYPTO_INSTALL_MSG}\n"
                f"Original error: {CRYPTOGRAPHY_ERROR}"
            )

        self.cert_dir = cert_dir
        self.key_dir = key_dir
        self.pow_manager = pow_manager
        os.makedirs(self.cert_dir, exist_ok=True)
        os.makedirs(self.key_dir, exist_ok=True)

        self.cert_file = os.path.join(self.cert_dir, "peer_cert.pem")
        self.key_file = os.path.join(self.cert_dir, "peer_key.pem")

        self.signing_key_file = os.path.join(self.key_dir, "signing_key.pem")
        self.signing_key: secp256k1.PrivateKey | None = None
        self.verifying_key: secp256k1.PublicKey | None = None
        self.session_keys: dict[str, dict[str, Any]] = {}
        self.session_ttl_seconds = max(60, int(session_ttl_seconds))
        self._cached_identity_fp: str | None = None

        # Generate TLS certificates if they don't exist
        if not os.path.exists(self.cert_file) or not os.path.exists(self.key_file):
            self._generate_self_signed_cert()

        # Generate signing key if it doesn't exist
        self._generate_signing_key()

    @staticmethod
    def _canonical_json(data: Any) -> str:
        return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)

    @staticmethod
    def _fingerprint_from_pubkey_bytes(pubkey_bytes: bytes) -> str:
        """Return a stable fingerprint for a serialized public key."""
        return hashlib.sha256(pubkey_bytes).hexdigest()[:16]

    def _node_identity_fingerprint(self) -> str:
        """
        Returns a stable node identity fingerprint derived from the node's signing key.
        Falls back to a static fingerprint if no key is available.
        """
        if self._cached_identity_fp:
            return self._cached_identity_fp
        if not self.verifying_key:
            return hashlib.sha256(b"xai-node-identity").hexdigest()[:16]
        serialized = self.verifying_key.serialize(compressed=True)
        pubkey_bytes = bytes.fromhex(serialized) if isinstance(serialized, str) else serialized
        self._cached_identity_fp = self._fingerprint_from_pubkey_bytes(pubkey_bytes)
        return self._cached_identity_fp

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
            self._cached_identity_fp = None
        except (OSError, IOError, PermissionError) as e:
            logger.error(
                "File system error with signing key: %s",
                e,
                extra={"event": "peer.signing_key_file_error", "key_file": self.signing_key_file}
            )
            # Self-heal by regenerating a fresh key when file access fails
            try:
                self.signing_key = secp256k1.PrivateKey(os.urandom(32))
                serialized = self.signing_key.serialize()
                serialized_bytes = (
                    bytes.fromhex(serialized) if isinstance(serialized, str) else serialized
                )
                with open(self.signing_key_file, "wb") as f:
                    f.write(serialized_bytes)
                self.verifying_key = self.signing_key.pubkey
                self._cached_identity_fp = None
                logger.info("Regenerated signing key at: %s", self.signing_key_file)
            except OSError as inner_exc:
                logger.critical(
                    "Failed to write regenerated signing key to disk: %s",
                    inner_exc,
                    exc_info=True,
                    extra={"event": "peer.signing_key_write_failed", "error_type": type(inner_exc).__name__}
                )
                raise
            except (ValueError, TypeError) as inner_exc:
                logger.critical(
                    "Failed to serialize regenerated signing key: %s",
                    inner_exc,
                    exc_info=True,
                    extra={"event": "peer.signing_key_serialization_failed", "error_type": type(inner_exc).__name__}
                )
                raise
        except (ValueError, TypeError) as e:
            logger.error(
                "Invalid signing key data: %s",
                e,
                extra={"event": "peer.signing_key_invalid", "key_file": self.signing_key_file}
            )
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
                self._cached_identity_fp = None
                logger.info("Regenerated signing key at: %s", self.signing_key_file)
            except OSError as inner_exc:
                logger.critical(
                    "Failed to write regenerated signing key to disk: %s",
                    inner_exc,
                    exc_info=True,
                    extra={"event": "peer.signing_key_write_failed", "error_type": type(inner_exc).__name__}
                )
                self.signing_key = None
                self.verifying_key = None
            except (ValueError, TypeError) as inner_exc:
                logger.critical(
                    "Failed to serialize regenerated signing key: %s",
                    inner_exc,
                    exc_info=True,
                    extra={"event": "peer.signing_key_serialization_failed", "error_type": type(inner_exc).__name__}
                )
                self.signing_key = None
                self.verifying_key = None
        except OSError as e:
            logger.error(
                "File I/O error with signing key: %s",
                e,
                exc_info=True,
                extra={"event": "peer.signing_key_io_error", "key_file": self.signing_key_file, "error_type": type(e).__name__}
            )
            # Self-heal by regenerating a fresh key
            try:
                self.signing_key = secp256k1.PrivateKey(os.urandom(32))
                serialized = self.signing_key.serialize()
                serialized_bytes = (
                    bytes.fromhex(serialized) if isinstance(serialized, str) else serialized
                )
                with open(self.signing_key_file, "wb") as f:
                    f.write(serialized_bytes)
                self.verifying_key = self.signing_key.pubkey
                logger.info("Regenerated signing key at: %s", self.signing_key_file)
            except OSError as inner_exc:
                logger.critical(
                    "Failed to write regenerated signing key to disk: %s",
                    inner_exc,
                    exc_info=True,
                    extra={"event": "peer.signing_key_write_failed", "error_type": type(inner_exc).__name__}
                )
                self.signing_key = None
                self.verifying_key = None
            except (ValueError, TypeError) as inner_exc:
                logger.critical(
                    "Failed to serialize regenerated signing key: %s",
                    inner_exc,
                    exc_info=True,
                    extra={"event": "peer.signing_key_serialization_failed", "error_type": type(inner_exc).__name__}
                )
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

        except (ValueError, TypeError, AttributeError) as e:
            logger.warning(
                "Invalid certificate data: %s",
                e,
                extra={
                    "event": "peer.cert_validation_invalid_data",
                    "error_type": type(e).__name__,
                }
            )
            return False
        except OSError as e:
            logger.error(
                "I/O error accessing certificate: %s",
                e,
                extra={
                    "event": "peer.cert_validation_io_error",
                    "error_type": type(e).__name__,
                }
            )
            return False

    def create_ssl_context(
        self,
        is_server: bool = False,
        require_client_cert: bool = False,
        ca_bundle: str | None = None,
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
        network = str(getattr(Config, "NETWORK", "testnet")).lower()
        is_testnet = network == "testnet"
        if is_server:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(self.cert_file, self.key_file)
            if require_client_cert:
                context.verify_mode = ssl.CERT_REQUIRED
                context.check_hostname = False
                if ca_bundle:
                    try:
                        context.load_verify_locations(cafile=ca_bundle)
                    except (OSError, IOError, PermissionError) as exc:
                        logger.error(
                            "File access error loading CA bundle for server: %s",
                            exc,
                            extra={
                                "event": "peer.ca_bundle_file_error",
                                "ca_bundle": ca_bundle,
                            }
                        )
                    except (ValueError, ssl.SSLError, TypeError) as exc:
                        logger.error(
                            "Invalid CA bundle for server: %s",
                            exc,
                            extra={
                                "event": "peer.ca_bundle_invalid",
                                "ca_bundle": ca_bundle,
                                "error_type": type(exc).__name__,
                            }
                        )
        elif is_testnet and not ca_bundle:
            # In local/testnet setups we allow self-signed certs to simplify peer bring-up
            context = ssl._create_unverified_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        else:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED  # Always enforce certificate verification
            if ca_bundle:
                try:
                    context.load_verify_locations(cafile=ca_bundle)
                except (OSError, IOError, PermissionError) as exc:
                    logger.error(
                        "File access error loading CA bundle for client: %s",
                        exc,
                        extra={
                            "event": "peer.ca_bundle_file_error",
                            "ca_bundle": ca_bundle,
                        }
                    )
                except (ValueError, ssl.SSLError, TypeError) as exc:
                    logger.error(
                        "Invalid CA bundle for client: %s",
                        exc,
                        extra={
                            "event": "peer.ca_bundle_invalid",
                            "ca_bundle": ca_bundle,
                            "error_type": type(exc).__name__,
                            "error": str(exc)
                        }
                    )

        return context

    def create_signed_message(self, payload: dict[str, Any]) -> bytes:
        """Create a signed message with payload, timestamp, nonce, and signature."""
        if not self.signing_key:
            raise ValueError("Signing key not available.")

        identity_fingerprint = self._node_identity_fingerprint()
        session_key = None
        session_id = payload.get("session_id") if isinstance(payload, dict) else None
        if session_id:
            session_key = self._get_or_refresh_session_key(session_id)

        pubkey_serialized = self.signing_key.pubkey.serialize()
        if isinstance(pubkey_serialized, str):
            pubkey_serialized = bytes.fromhex(pubkey_serialized)
        pubkey_hex = pubkey_serialized.hex()

        message = {
            "payload": payload,
            "timestamp": int(time.time()),
            "nonce": os.urandom(16).hex(),
            "sender_id": identity_fingerprint,
        }

        payload_hash = hashlib.sha256(self._canonical_json(payload).encode("utf-8")).hexdigest()
        if session_key:
            message["session_id"] = session_id
            message["hmac"] = hmac.new(session_key, self._canonical_json(payload).encode("utf-8"), hashlib.sha256).hexdigest()
        if self.pow_manager:
            proof = self.pow_manager.solve(pubkey_hex, message["timestamp"], message["nonce"], payload_hash)
            if proof:
                message["pow"] = proof
        
        # Serialize the message for signing
        serialized_message = json.dumps(message, sort_keys=True, separators=(",", ":"), default=str).encode('utf-8')
        
        # Create a digest of the message
        message_hash = hashlib.sha256(serialized_message).digest()

        # Sign the hash
        signature = self.signing_key.ecdsa_sign(message_hash)
        sig_bytes = self.signing_key.ecdsa_serialize(signature)
        if isinstance(sig_bytes, str):
            sig_bytes = bytes.fromhex(sig_bytes)
        sig_hex = sig_bytes.hex()
        
        # Final message structure including the signature
        signed_message = {
            "message": message,
            "signature": pubkey_hex + '.' + sig_hex
        }

        return json.dumps(signed_message, sort_keys=True).encode('utf-8')

    def _get_or_refresh_session_key(self, session_id: str) -> bytes:
        """Return a symmetric session key for HMAC binding, refreshing expiration."""
        if session_id not in self.session_keys:
            key = os.urandom(32)
            self.session_keys[session_id] = {"key": key, "created_at": time.time()}
            return key
        entry = self.session_keys[session_id]
        if time.time() - entry["created_at"] > self.session_ttl_seconds:
            entry["key"] = os.urandom(32)
            entry["created_at"] = time.time()
        return entry["key"]

    @staticmethod
    def fingerprint_from_ssl_object(ssl_object: ssl.SSLObject) -> str | None:
        """Compute SHA256 fingerprint of the peer certificate from an SSLObject."""
        try:
            der_cert = ssl_object.getpeercert(binary_form=True)
            if not der_cert:
                return None
            return hashlib.sha256(der_cert).hexdigest()
        except (AttributeError, ValueError, TypeError) as e:
            logging.debug("Invalid SSL object or certificate data: %s", e)
            return None
        except (ssl.SSLError, OSError) as e:
            logging.debug("SSL/network error getting peer certificate: %s", e)
            return None

    def verify_signed_message(self, signed_message_bytes: bytes) -> dict[str, Any] | None:
        """
        Verify a signed message, checking signature and freshness.

        Returns a dict containing the decoded payload plus metadata:
        {"payload": ..., "sender": <pubkey_hex>, "nonce": <nonce>, "timestamp": <timestamp>}
        """
        try:
            debug_signing = bool(int(os.getenv("XAI_P2P_DEBUG_SIGNING", "0")))
            payload_preview = signed_message_bytes[:512].decode("utf-8", errors="replace")
            decoder = json.JSONDecoder()
            try:
                signed_message = json.loads(signed_message_bytes.decode('utf-8'))
            except json.JSONDecodeError as exc:
                decoded_text = signed_message_bytes.decode('utf-8', errors='ignore')
                start = decoded_text.find('{"message"')
                if start >= 0:
                    trimmed = decoded_text[start:]
                    try:
                        signed_message = json.loads(trimmed)
                    except json.JSONDecodeError:
                        try:
                            signed_message, _ = decoder.raw_decode(trimmed)
                        except json.JSONDecodeError:
                            logger.warning(
                                "Failed to decode signed message JSON: %s preview=%s",
                                exc,
                                payload_preview,
                                extra={
                                    "event": "peer.invalid_signed_json",
                                    "error": str(exc),
                                    "preview": payload_preview,
                                },
                            )
                            return None
                else:
                    logger.warning(
                        "Failed to decode signed message JSON: %s preview=%s",
                        exc,
                        payload_preview,
                        extra={
                            "event": "peer.invalid_signed_json",
                            "error": str(exc),
                            "preview": payload_preview,
                        },
                    )
                    return None
            
            message = signed_message["message"]
            claimed_sender = message.get("sender_id")
            signature_str = signed_message["signature"]

            try:
                pubkey_hex, sig_hex = signature_str.split('.')
            except ValueError:
                logger.warning(
                    "Malformed signature envelope (missing delimiter) preview=%s",
                    payload_preview,
                    extra={
                        "event": "peer.malformed_signature",
                        "error": "missing_delimiter",
                        "preview": payload_preview,
                    },
                )
                return None

            sender_preview = pubkey_hex[:16] + "..." if pubkey_hex else "unknown"

            try:
                pubkey_bytes = bytes.fromhex(pubkey_hex)
                signature_bytes = bytes.fromhex(sig_hex)
            except ValueError as exc:
                logger.warning(
                    "Malformed signature hex (%s) preview=%s",
                    exc,
                    payload_preview,
                    extra={
                        "event": "peer.malformed_signature",
                        "error": str(exc),
                        "sender": sender_preview,
                        "preview": payload_preview,
                    },
                )
                return None

            try:
                pubkey = secp256k1.PublicKey(pubkey_bytes, raw=True)
                signature = pubkey.ecdsa_deserialize(signature_bytes)
            except (ValueError, AssertionError) as exc:
                logger.warning(
                    "Failed to deserialize peer signature (%s)",
                    exc,
                    extra={
                        "event": "peer.signature_deserialize_failed",
                        "error": str(exc),
                        "sender": sender_preview,
                    },
                )
                return None

            fingerprint_expected = self._fingerprint_from_pubkey_bytes(
                pubkey.serialize(compressed=True)
            )

            # SECURITY: Signature verification bypass - DEVELOPMENT ONLY
            # This bypass is blocked in production mode by startup_validator.py
            # Even if bypassed here, production nodes will refuse to start with this enabled
            bypass_sig_verify = os.getenv("XAI_P2P_DISABLE_SIGNATURE_VERIFY", "0").lower() in {"1", "true", "yes", "on"}
            is_prod = os.getenv("XAI_PRODUCTION_MODE", "0").lower() in {"1", "true", "yes", "on", "production"}
            if bypass_sig_verify:
                if is_prod:
                    # CRITICAL: Never allow signature bypass in production
                    logger.critical(
                        "SECURITY: Signature verification bypass attempted in production mode - BLOCKED",
                        extra={"event": "security.bypass_blocked"}
                    )
                    # Continue with normal verification
                else:
                    logger.warning(
                        "SECURITY: Signature verification BYPASSED (non-production mode)",
                        extra={"event": "security.sig_verify_bypass"}
                    )
                    return {
                        "payload": message.get("payload"),
                        "sender": pubkey_hex,
                        "nonce": message.get("nonce"),
                        "timestamp": message.get("timestamp"),
                        "sender_id": claimed_sender or fingerprint_expected,
                    }

            # Verify timestamp is recent (e.g., within the last 5 minutes)
            if time.time() - message["timestamp"] > 300:
                logger.warning(
                    "Stale message received, discarding (age=%.2fs, sender=%s)",
                    time.time() - message["timestamp"],
                    pubkey_hex[:16] + "..." if pubkey_hex else "unknown",
                    extra={
                        "event": "peer.stale_message",
                        "message_age_seconds": time.time() - message["timestamp"],
                        "sender": pubkey_hex[:16] + "..." if pubkey_hex else "unknown"
                    }
                )
                return None

            # Serialize the inner message for verification
            serialized_message = json.dumps(message, sort_keys=True, separators=(",", ":"), default=str).encode('utf-8')
            message_hash = hashlib.sha256(serialized_message).digest()

            # Verify the signature
            if not pubkey.ecdsa_verify(message_hash, signature):
                logger.warning(
                    "Invalid signature in peer message (sha256=%s, sender=%s)",
                    hashlib.sha256(serialized_message).hexdigest(),
                    pubkey_hex[:16] + "..." if pubkey_hex else "unknown",
                    extra={
                        "event": "peer.invalid_signature",
                        "sender": pubkey_hex[:16] + "..." if pubkey_hex else "unknown",
                        "message_sha256": hashlib.sha256(serialized_message).hexdigest(),
                    }
                )
                return None

            payload_hash = hashlib.sha256(self._canonical_json(message["payload"]).encode("utf-8")).hexdigest()
            expected_sender = fingerprint_expected
            allow_mismatch = str(getattr(Config, "NETWORK", "testnet")).lower() == "testnet"
            if claimed_sender and claimed_sender != expected_sender:
                logger.warning(
                    "Peer identity mismatch%s",
                    " (testnet tolerated)" if allow_mismatch else "",
                    extra={
                        "event": "peer.identity_mismatch",
                        "claimed": claimed_sender,
                        "expected": expected_sender,
                    },
                )
                if not allow_mismatch:
                    return None
            claimed_sender = claimed_sender or expected_sender
            session_id = message.get("session_id")
            if session_id:
                session_info = self.session_keys.get(session_id)
                if not session_info or time.time() - session_info["created_at"] > self.session_ttl_seconds:
                    logger.warning(
                        "Expired or unknown session key in message",
                        extra={"event": "peer.session_invalid", "session_id": session_id},
                    )
                    return None
                expected_hmac = hmac.new(
                    session_info["key"],
                    self._canonical_json(message["payload"]).encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()
                if expected_hmac != message.get("hmac"):
                    logger.warning(
                        "Session HMAC mismatch",
                        extra={"event": "peer.session_hmac_invalid", "session_id": session_id},
                    )
                    return None
            if self.pow_manager and not self.pow_manager.verify(
                pubkey_hex,
                int(message.get("timestamp", 0)),
                message.get("nonce"),
                payload_hash,
                message.get("pow"),
            ):
                logger.warning(
                    "Peer message failed proof-of-work validation (sender=%s, payload_hash=%s)",
                    pubkey_hex[:16] + "..." if pubkey_hex else "unknown",
                    payload_hash,
                    extra={
                        "event": "peer.pow_invalid",
                        "sender": pubkey_hex[:16] + "..." if pubkey_hex else "unknown",
                        "payload_hash": payload_hash,
                    }
                )
                return None
            
            return {
                "payload": message["payload"],
                "sender": pubkey_hex,
                "nonce": message.get("nonce"),
                "timestamp": message.get("timestamp"),
                "sender_id": claimed_sender or expected_sender,
            }
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(
                "Error verifying signed message: %s%s",
                str(e),
                f" preview={payload_preview}" if debug_signing else "",
                extra={
                    "event": "peer.message_verification_error",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "preview": payload_preview if debug_signing else None,
                }
            )
            return None

    def is_nonce_replay(self, sender_id: str, nonce: str, timestamp: float | None = None) -> bool:
        """Check if nonce has been seen recently for a sender, pruning expired nonces."""
        now = timestamp if timestamp is not None else time.time()
        with self._nonce_lock:
            dq: deque[tuple[str, float]] = self.seen_nonces[sender_id]
            while dq and now - dq[0][1] > self.nonce_ttl_seconds:
                dq.popleft()
            return any(stored_nonce == nonce for stored_nonce, _ in dq)

    def record_nonce(self, sender_id: str, nonce: str, timestamp: float | None = None) -> None:
        """Record a nonce for replay protection with timestamp pruning."""
        now = timestamp if timestamp is not None else time.time()
        with self._nonce_lock:
            dq: deque[tuple[str, float]] = self.seen_nonces[sender_id]
            while dq and now - dq[0][1] > self.nonce_ttl_seconds:
                dq.popleft()
            dq.append((nonce, now))

    def add_trusted_peer_key(self, pubkey_hex: str) -> None:
        """Whitelist a peer public key for message-level trust decisions."""
        self.trusted_peer_pubkeys.add(pubkey_hex.lower())

    def remove_trusted_peer_key(self, pubkey_hex: str) -> None:
        """Remove a peer public key from trust store."""
        self.trusted_peer_pubkeys.discard(pubkey_hex.lower())

    def is_sender_allowed(self, pubkey_hex: str | None) -> bool:
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

    def is_cert_allowed(self, fingerprint_hex: str | None) -> bool:
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
        updated_pubkeys: set[str] | None = None
        updated_fps: set[str] | None = None

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
        except OSError as exc:
            logger.error(
                "I/O error reloading trusted pubkeys",
                extra={
                    "event": "peer.trust_store_io_error",
                    "store_type": "pubkeys",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "file": self.trusted_peer_pubkeys_file
                }
            )
        except (ValueError, TypeError) as exc:
            logger.error(
                "Invalid data format in trusted pubkeys file",
                extra={
                    "event": "peer.trust_store_data_error",
                    "store_type": "pubkeys",
                    "error_type": type(exc).__name__,
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
        except OSError as exc:
            logger.error(
                "I/O error reloading trusted cert fingerprints",
                extra={
                    "event": "peer.trust_store_io_error",
                    "store_type": "cert_fps",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "file": self.trusted_cert_fps_file
                }
            )
        except (ValueError, TypeError) as exc:
            logger.error(
                "Invalid data format in trusted cert fingerprints file",
                extra={
                    "event": "peer.trust_store_data_error",
                    "store_type": "cert_fps",
                    "error_type": type(exc).__name__,
                    "file": self.trusted_cert_fps_file
                }
            )

        if updated_pubkeys is not None:
            self.trusted_peer_pubkeys = updated_pubkeys
        if updated_fps is not None:
            self.trusted_cert_fingerprints = updated_fps
        if updated_fps is not None:
            self.require_client_cert = self.require_client_cert or bool(self.trusted_cert_fingerprints)


# Manager Consolidation: Removed duplicate incomplete PeerManager class.
# The production-grade PeerManager with geo-diversity, replay protection,
# and certificate handling is now the single implementation below.

class PeerManager:
    def __init__(
        self,
        max_connections_per_ip: int = 5,
        trusted_peer_pubkeys: Iterable[str] | None = None,
        trusted_cert_fingerprints: Iterable[str] | None = None,
        trusted_peer_pubkeys_file: str | None = None,
        trusted_cert_fps_file: str | None = None,
        nonce_ttl_seconds: int | None = None,
        require_client_cert: bool = False,
        ca_bundle_path: str | None = None,
        dns_seeds: Iterable[str] | None = None,
        bootstrap_nodes: Iterable[str] | None = None,
        cert_dir: str = "data/certs",
        key_dir: str = "data/keys",
    ):
        if not isinstance(max_connections_per_ip, int) or max_connections_per_ip <= 0:
            raise ValueError("Max connections per IP must be a positive integer.")

        self.max_connections_per_ip = max_connections_per_ip
        self.trusted_peers: set[str] = set()
        self.banned_peers: set[str] = set()
        self.banned_until: dict[str, float] = {}
        self.ban_counts: dict[str, int] = defaultdict(int)
        self.connected_peers: dict[str, dict[str, Any]] = {}
        self.connections_by_ip: dict[str, int] = defaultdict(int)
        self.connections_by_subnet: dict[str, int] = defaultdict(int)
        self._peer_id_counter = 0
        self.max_connections_per_subnet16 = int(getattr(Config, "P2P_MAX_CONNECTIONS_PER_SUBNET16", 64))
        self.base_ban_seconds = int(getattr(Config, "P2P_BAN_BASE_SECONDS", 600))
        self.max_ban_seconds = int(getattr(Config, "P2P_BAN_MAX_SECONDS", 86400))

        self.seen_nonces: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._nonce_lock = threading.RLock()
        self.nonce_ttl_seconds = nonce_ttl_seconds if nonce_ttl_seconds else 300

        self.trusted_peer_pubkeys: set[str] = set(k.lower() for k in (trusted_peer_pubkeys or []))
        self.trusted_cert_fingerprints: set[str] = set(fp.lower() for fp in (trusted_cert_fingerprints or []))
        self.trusted_peer_pubkeys_file = trusted_peer_pubkeys_file
        self.trusted_cert_fps_file = trusted_cert_fps_file
        self._trust_file_mtimes: dict[str, float] = {}
        self.require_client_cert = require_client_cert or bool(self.trusted_cert_fingerprints)
        self.ca_bundle_path = ca_bundle_path

        self.reputation = PeerReputation()
        self.pow_manager = PeerProofOfWork(
            enabled=bool(getattr(Config, "P2P_POW_ENABLED", True)),
            difficulty_bits=int(getattr(Config, "P2P_POW_DIFFICULTY_BITS", 18)),
            max_iterations=int(getattr(Config, "P2P_POW_MAX_ITERATIONS", 250000)),
            reuse_window_seconds=int(getattr(Config, "P2P_POW_REUSE_WINDOW_SECONDS", 600)),
        )
        self.encryption = PeerEncryption(cert_dir=cert_dir, key_dir=key_dir, pow_manager=self.pow_manager)
        self.discovery = PeerDiscovery(
            dns_seeds=list(dns_seeds) if dns_seeds else None,
            bootstrap_nodes=list(bootstrap_nodes) if bootstrap_nodes else None,
            encryption=self.encryption,
        )

        self.max_per_prefix = max(0, int(getattr(Config, "P2P_MAX_PEERS_PER_PREFIX", 8)))
        self.max_per_asn = max(0, int(getattr(Config, "P2P_MAX_PEERS_PER_ASN", 16)))
        self.max_per_country = max(0, int(getattr(Config, "P2P_MAX_PEERS_PER_COUNTRY", 48)))
        self.min_unique_prefixes = max(0, int(getattr(Config, "P2P_MIN_UNIQUE_PREFIXES", 5)))
        self.min_unique_asns = max(0, int(getattr(Config, "P2P_MIN_UNIQUE_ASNS", 5)))
        self.min_unique_countries = max(0, int(getattr(Config, "P2P_MIN_UNIQUE_COUNTRIES", 5)))
        self.max_unknown_geo = max(0, int(getattr(Config, "P2P_MAX_UNKNOWN_GEO", 32)))
        self.diversity_prefix_length = max(4, int(getattr(Config, "P2P_DIVERSITY_PREFIX_LENGTH", 16)))
        self.geoip_resolver = GeoIPResolver(
            http_endpoint=getattr(Config, "P2P_GEOIP_ENDPOINT", "https://ipinfo.io/{ip}/json"),
            timeout=float(getattr(Config, "P2P_GEOIP_TIMEOUT", 2.5)),
            cache_ttl=int(getattr(Config, "P2P_GEOIP_CACHE_TTL", 3600)),
        )
        self.prefix_counts: dict[str, int] = defaultdict(int)
        self.asn_counts: dict[str, int] = defaultdict(int)
        self.country_counts: dict[str, int] = defaultdict(int)
        self.unknown_geo_peers = 0
        self._diversity_lock = threading.RLock()

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
        updated_pubkeys: set[str] | None = None
        updated_fps: set[str] | None = None

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
        except OSError as exc:
            logger.error(
                "I/O error reloading trusted pubkeys",
                extra={
                    "event": "peer.trust_store_io_error",
                    "store_type": "pubkeys",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "file": self.trusted_peer_pubkeys_file
                }
            )
        except (ValueError, TypeError) as exc:
            logger.error(
                "Invalid data format in trusted pubkeys file",
                extra={
                    "event": "peer.trust_store_data_error",
                    "store_type": "pubkeys",
                    "error_type": type(exc).__name__,
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
        except OSError as exc:
            logger.error(
                "I/O error reloading trusted cert fingerprints",
                extra={
                    "event": "peer.trust_store_io_error",
                    "store_type": "cert_fps",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "file": self.trusted_cert_fps_file
                }
            )
        except (ValueError, TypeError) as exc:
            logger.error(
                "Invalid data format in trusted cert fingerprints file",
                extra={
                    "event": "peer.trust_store_data_error",
                    "store_type": "cert_fps",
                    "error_type": type(exc).__name__,
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

    def is_sender_allowed(self, pubkey_hex: str | None) -> bool:
        if not pubkey_hex:
            return False if self.trusted_peer_pubkeys else True
        if not self.trusted_peer_pubkeys:
            return True
        return pubkey_hex.lower() in self.trusted_peer_pubkeys

    def add_trusted_cert_fingerprint(self, fingerprint_hex: str) -> None:
        self.trusted_cert_fingerprints.add(fingerprint_hex.lower())

    def remove_trusted_cert_fingerprint(self, fingerprint_hex: str) -> None:
        self.trusted_cert_fingerprints.discard(fingerprint_hex.lower())

    def is_cert_allowed(self, fingerprint_hex: str | None) -> bool:
        if not self.trusted_cert_fingerprints:
            return True
        if not fingerprint_hex:
            return False
        return fingerprint_hex.lower() in self.trusted_cert_fingerprints

    def is_nonce_replay(self, sender_id: str, nonce: str, timestamp: float | None = None) -> bool:
        now = timestamp if timestamp is not None else time.time()
        with self._nonce_lock:
            dq: deque[tuple[str, float]] = self.seen_nonces[sender_id]
            while dq and now - dq[0][1] > self.nonce_ttl_seconds:
                dq.popleft()
            return any(stored_nonce == nonce for stored_nonce, _ in dq)

    def record_nonce(self, sender_id: str, nonce: str, timestamp: float | None = None) -> None:
        now = timestamp if timestamp is not None else time.time()
        with self._nonce_lock:
            dq: deque[tuple[str, float]] = self.seen_nonces[sender_id]
            while dq and now - dq[0][1] > self.nonce_ttl_seconds:
                dq.popleft()
            dq.append((nonce, now))

    def add_trusted_peer(self, peer_identifier: str):
        self.trusted_peers.add(peer_identifier.lower())

    def remove_trusted_peer(self, peer_identifier: str):
        self.trusted_peers.discard(peer_identifier.lower())

    def ban_peer(self, peer_identifier: str):
        normalized = peer_identifier.lower()
        now = time.time()
        prior_bans = self.ban_counts[normalized]
        duration = min(self.max_ban_seconds, self.base_ban_seconds * (2 ** prior_bans))
        self.ban_counts[normalized] = prior_bans + 1
        self.banned_peers.add(normalized)
        self.banned_until[normalized] = now + duration
        peers_to_disconnect = [
            pid
            for pid, peer_info in self.connected_peers.items()
            if peer_info["ip_address"].lower() == normalized
        ]
        for pid in peers_to_disconnect:
            self.disconnect_peer(pid)

    def unban_peer(self, peer_identifier: str):
        normalized = peer_identifier.lower()
        self.banned_peers.discard(normalized)
        self.banned_until.pop(normalized, None)

    def can_connect(self, ip_address: str) -> bool:
        ip_lower = ip_address.lower()
        if ip_lower in self.banned_peers:
            expiry = self.banned_until.get(ip_lower)
            if expiry is not None and time.time() >= expiry:
                self.unban_peer(ip_lower)
            else:
                print(f"Connection from {ip_address} rejected: IP is banned.")
                return False
        if self.connections_by_ip[ip_lower] >= self.max_connections_per_ip:
            print(
                f"Connection from {ip_address} rejected: Exceeds max connections per IP ({self.max_connections_per_ip})."
            )
            return False
        subnet = self._subnet_key(ip_lower)
        if subnet and self.connections_by_subnet[subnet] >= self.max_connections_per_subnet16:
            print(
                f"Connection from {ip_address} rejected: Exceeds max connections per subnet ({self.max_connections_per_subnet16}) for {subnet}."
            )
            return False
        allowed, metadata, _, _, reason = self._evaluate_diversity_policy(ip_address, mutate=False)
        if not allowed:
            self._log_diversity_rejection(ip_address, reason or "diversity_limit", metadata)
            return False
        return True

    def _subnet_key(self, ip_address: str) -> str | None:
        """Return normalized subnet key for diversity enforcement (/16 for IPv4, /32 for IPv6)."""
        try:
            ip_obj = ipaddress.ip_address(ip_address)
            if isinstance(ip_obj, ipaddress.IPv4Address):
                network = ipaddress.ip_network(f"{ip_obj}/16", strict=False)
            else:
                network = ipaddress.ip_network(f"{ip_obj}/32", strict=False)
            return f"{network.network_address}/{network.prefixlen}"
        except ValueError:
            return None

    def connect_peer(self, ip_address: str) -> str:
        if not self.can_connect(ip_address):
            raise ValueError(
                f"Cannot connect to peer from {ip_address} due to policy restrictions."
            )
        allowed, metadata, prefix, is_unknown, reason = self._evaluate_diversity_policy(ip_address, mutate=True)
        if not allowed:
            self._log_diversity_rejection(ip_address, reason or "diversity_limit", metadata)
            raise ValueError(
                f"Cannot connect to peer from {ip_address} due to diversity restrictions ({reason})."
            )
        self._peer_id_counter += 1
        peer_id = f"peer_{self._peer_id_counter}"
        self.connected_peers[peer_id] = {
            "ip_address": ip_address,
            "connected_at": time.time(),
            "last_seen": time.time(),
            "geo": {
                "prefix": prefix,
                "asn": metadata.normalized_asn if metadata else "AS-UNKNOWN",
                "country": metadata.normalized_country if metadata else "UNKNOWN",
                "source": getattr(metadata, "source", "unknown"),
                "is_unknown": is_unknown,
            },
        }
        self.connections_by_ip[ip_address] += 1
        subnet = self._subnet_key(ip_address.lower())
        if subnet:
            self.connections_by_subnet[subnet] += 1
        return peer_id

    def disconnect_peer(self, peer_id: str):
        peer = self.connected_peers.pop(peer_id, None)
        if peer:
            self._decrement_geo_counters(peer)
            ip_address = peer["ip_address"]
            self.connections_by_ip[ip_address] = max(0, self.connections_by_ip[ip_address] - 1)
            if self.connections_by_ip[ip_address] == 0:
                del self.connections_by_ip[ip_address]
            subnet = self._subnet_key(ip_address.lower())
            if subnet:
                self.connections_by_subnet[subnet] = max(0, self.connections_by_subnet[subnet] - 1)
                if self.connections_by_subnet[subnet] == 0:
                    del self.connections_by_subnet[subnet]
            if peer_id in self.seen_nonces:
                del self.seen_nonces[peer_id]
            self.reputation.record_disconnect(peer_id)
        else:
            print(f"Peer {peer_id} not found.")

    def get_peer_reputation(self, peer_id: str) -> float:
        """Return the reputation score for a peer."""
        return self.reputation.get_score(peer_id)

    def get_best_peers(self, count: int = 10) -> list[tuple[str, float]]:
        """Return the top peers ranked by reputation."""
        return self.reputation.get_top_peers(count)

    async def discover_peers(self) -> list[str]:
        """Discover peers using DNS seeds and configured bootstrap nodes."""
        dns_peers = await self.discovery.discover_from_dns()
        bootstrap_peers = await self.discovery.discover_from_bootstrap()
        return dns_peers + bootstrap_peers

    def get_ssl_context(self, is_server: bool = False) -> ssl.SSLContext:
        """Expose encryption SSL context helper for callers."""
        return self.encryption.create_ssl_context(is_server)

    def _evaluate_diversity_policy(
        self,
        ip_address: str,
        mutate: bool = False,
    ) -> tuple[bool, GeoIPMetadata, str | None, bool, str | None]:
        metadata = self._resolve_geo_metadata(ip_address)
        prefix = self._get_ip_prefix(ip_address)
        normalized_asn = metadata.normalized_asn
        normalized_country = metadata.normalized_country
        is_unknown = normalized_asn == "AS-UNKNOWN" or normalized_country == "UNKNOWN"

        with self._diversity_lock:
            total_connected = len(self.connected_peers)
            total_after_accept = total_connected + 1
            prefix_is_new = bool(prefix) and prefix not in self.prefix_counts
            asn_is_new = not is_unknown and normalized_asn not in self.asn_counts
            country_is_new = not is_unknown and normalized_country not in self.country_counts

            if self.max_per_prefix > 0 and prefix:
                if self.prefix_counts[prefix] >= self.max_per_prefix:
                    return False, metadata, prefix, is_unknown, "prefix_limit"
            if (
                self.max_per_asn > 0
                and not is_unknown
                and self.asn_counts[normalized_asn] >= self.max_per_asn
            ):
                return False, metadata, prefix, is_unknown, "asn_limit"
            if (
                self.max_per_country > 0
                and not is_unknown
                and self.country_counts[normalized_country] >= self.max_per_country
            ):
                return False, metadata, prefix, is_unknown, "country_limit"
            if is_unknown and self.max_unknown_geo >= 0 and self.unknown_geo_peers >= self.max_unknown_geo:
                return False, metadata, prefix, is_unknown, "unknown_geo_limit"

            # Enforce diversity requirements by rejecting peers that do not add
            # new prefixes/ASNs/countries when we're below the mandated minimums.
            if (
                self.min_unique_prefixes
                and prefix
                and total_after_accept >= self.min_unique_prefixes
                and len(self.prefix_counts) + (1 if prefix_is_new else 0) < self.min_unique_prefixes
                and not prefix_is_new
            ):
                return False, metadata, prefix, is_unknown, "prefix_diversity"

            if (
                self.min_unique_asns
                and not is_unknown
                and total_after_accept >= self.min_unique_asns
                and len(self.asn_counts) + (1 if asn_is_new else 0) < self.min_unique_asns
                and not asn_is_new
            ):
                return False, metadata, prefix, is_unknown, "asn_diversity"

            if (
                self.min_unique_countries
                and not is_unknown
                and total_after_accept >= self.min_unique_countries
                and len(self.country_counts) + (1 if country_is_new else 0) < self.min_unique_countries
                and not country_is_new
            ):
                return False, metadata, prefix, is_unknown, "country_diversity"

            if mutate:
                if prefix:
                    self.prefix_counts[prefix] += 1
                if is_unknown:
                    self.unknown_geo_peers += 1
                else:
                    self.asn_counts[normalized_asn] += 1
                    self.country_counts[normalized_country] += 1
                self._check_diversity_thresholds()

        return True, metadata, prefix, is_unknown, None

    def _decrement_geo_counters(self, peer_info: dict[str, Any]) -> None:
        geo_info = peer_info.get("geo") or {}
        prefix = geo_info.get("prefix")
        normalized_asn = geo_info.get("asn")
        normalized_country = geo_info.get("country")
        is_unknown = geo_info.get("is_unknown", False)

        with self._diversity_lock:
            if prefix and prefix in self.prefix_counts:
                self.prefix_counts[prefix] -= 1
                if self.prefix_counts[prefix] <= 0:
                    del self.prefix_counts[prefix]
            if is_unknown:
                self.unknown_geo_peers = max(0, self.unknown_geo_peers - 1)
            else:
                if normalized_asn and normalized_asn in self.asn_counts:
                    self.asn_counts[normalized_asn] -= 1
                    if self.asn_counts[normalized_asn] <= 0:
                        del self.asn_counts[normalized_asn]
                if normalized_country and normalized_country in self.country_counts:
                    self.country_counts[normalized_country] -= 1
                    if self.country_counts[normalized_country] <= 0:
                        del self.country_counts[normalized_country]

    def _check_diversity_thresholds(self) -> None:
        total_peers = len(self.connected_peers) + 1  # include pending peer
        unique_asns = len(self.asn_counts)
        unique_countries = len(self.country_counts)
        unique_prefixes = len(self.prefix_counts)

        if self.min_unique_asns and unique_asns < self.min_unique_asns and total_peers >= self.min_unique_asns:
            logger.warning(
                "Peer ASN diversity below threshold (%s/%s)",
                unique_asns,
                self.min_unique_asns,
                extra={
                    "event": "peer.diversity.asn_below_threshold",
                    "unique_asns": unique_asns,
                    "threshold": self.min_unique_asns,
                },
            )
        if (
            self.min_unique_countries
            and unique_countries < self.min_unique_countries
            and total_peers >= self.min_unique_countries
        ):
            logger.warning(
                "Peer country diversity below threshold (%s/%s)",
                unique_countries,
                self.min_unique_countries,
                extra={
                    "event": "peer.diversity.country_below_threshold",
                    "unique_countries": unique_countries,
                    "threshold": self.min_unique_countries,
                },
            )
        if (
            self.min_unique_prefixes
            and unique_prefixes < self.min_unique_prefixes
            and total_peers >= self.min_unique_prefixes
        ):
            logger.warning(
                "Peer prefix diversity below threshold (%s/%s)",
                unique_prefixes,
                self.min_unique_prefixes,
                extra={
                    "event": "peer.diversity.prefix_below_threshold",
                    "unique_prefixes": unique_prefixes,
                    "threshold": self.min_unique_prefixes,
                },
            )

    def _log_diversity_rejection(
        self,
        ip_address: str,
        reason: str,
        metadata: GeoIPMetadata | None,
    ) -> None:
        logger.warning(
            "Peer connection rejected for diversity policy (%s)",
            reason,
            extra={
                "event": "peer.diversity.rejected",
                "ip": ip_address,
                "reason": reason,
                "asn": metadata.normalized_asn if metadata else "AS-UNKNOWN",
                "country": metadata.normalized_country if metadata else "UNKNOWN",
                "prefix": self._get_ip_prefix(ip_address),
            },
        )

    def _resolve_geo_metadata(self, ip_address: str) -> GeoIPMetadata:
        try:
            return self.geoip_resolver.lookup(ip_address)
        except (ConnectionError, TimeoutError, OSError) as exc:
            logger.warning(
                "Network error during GeoIP lookup for %s: %s",
                ip_address,
                type(exc).__name__,
                extra={"event": "peer.geoip.network_error", "ip": ip_address, "error_type": type(exc).__name__},
            )
            return GeoIPMetadata(
                ip=ip_address,
                country="UNKNOWN",
                country_name="Unknown",
                asn="AS-UNKNOWN",
                as_name="Unknown",
                source="error",
            )
        except (ValueError, KeyError, TypeError) as exc:
            logger.warning(
                "Invalid GeoIP data for %s: %s",
                ip_address,
                type(exc).__name__,
                extra={"event": "peer.geoip.data_error", "ip": ip_address, "error_type": type(exc).__name__},
            )
            return GeoIPMetadata(
                ip=ip_address,
                country="UNKNOWN",
                country_name="Unknown",
                asn="AS-UNKNOWN",
                as_name="Unknown",
                source="error",
            )

    def _get_ip_prefix(self, ip_address: str) -> str | None:
        try:
            ip_obj = ipaddress.ip_address(ip_address)
        except ValueError:
            return None

        if ip_obj.version == 4:
            prefix_length = min(max(self.diversity_prefix_length, 8), 32)
        else:
            prefix_length = min(max(self.diversity_prefix_length, 32), 64)
        network = ipaddress.ip_network(f"{ip_address}/{prefix_length}", strict=False)
        return f"{network.network_address}/{prefix_length}"
