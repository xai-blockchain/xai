"""
AXN Blockchain Node - P2P Networking Module

Handles all peer-to-peer networking functionality including:
- Peer management
- Transaction broadcasting
- Block broadcasting
- Blockchain synchronization
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import websockets
from websockets import WebSocketServer
from websockets.asyncio.server import ServerConnection
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)

try:
    import aioquic  # type: ignore

    from xai.core.p2p.p2p_quic import (  # type: ignore
        QuicConfiguration,
        QuicDialTimeout,
        QUICServer,
        quic_client_send_with_timeout,
    )
    QUIC_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    # QUIC dependencies not installed - disable QUIC support
    QUIC_AVAILABLE = False
    QuicDialTimeout = ConnectionError  # type: ignore[assignment]
    logger.debug(f"QUIC support disabled: {e}")

import httpx
import requests

from xai.core.chain.block_header import BlockHeader
from xai.core.chain.blockchain_exceptions import (
    DatabaseError,
    NetworkError,
    PeerError,
    StorageError,
    ValidationError,
)
from xai.core.p2p.checkpoint_sync import CheckpointSyncManager
from xai.core.config import Config
from xai.core.security.p2p_security import (
    HEADER_VERSION,
    BandwidthLimiter,
    MessageRateLimiter,
    P2PSecurityConfig,
)
from xai.core.security.security_validation import SecurityEventRouter
from xai.network.peer_manager import PeerManager

if TYPE_CHECKING:
    from xai.core.blockchain import Block, Blockchain, Transaction
    from xai.core.consensus.node_consensus import ConsensusManager

class P2PNetworkManager:
    """
    Manages peer-to-peer networking for a blockchain node using WebSockets.
    """

    def __init__(
        self,
        blockchain: Blockchain,
        peer_manager: PeerManager | None = None,
        consensus_manager: "ConsensusManager" | None = None,
        host: str = "0.0.0.0",
        port: int = 8765,
        max_connections: int = 50,
        max_bandwidth_in: int = 1024 * 1024, # 1 MB/s
        max_bandwidth_out: int = 1024 * 1024, # 1 MB/s
        peer_api_key: str | None = None,
        api_port: int | None = None,
    ) -> None:
        # Configure logger with handler if not already configured
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('[%(levelname)s] %(name)s: %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            logger.info("P2P Network Manager logger configured")

        self.blockchain = blockchain
        storage_ref = getattr(self.blockchain, "storage", None)
        data_dir_candidate = getattr(storage_ref, "data_dir", "data")
        data_dir = data_dir_candidate if isinstance(data_dir_candidate, str) else "data"

        # Override max_connections from Config if available (for testnet flexibility)
        configured_max = getattr(Config, "P2P_MAX_CONNECTIONS_PER_IP", None)
        if configured_max is not None:
            max_connections = int(configured_max)

        if peer_manager is None:
            peer_manager = PeerManager(
                max_connections_per_ip=max_connections,
                nonce_ttl_seconds=getattr(Config, "PEER_NONCE_TTL_SECONDS", 300),
                require_client_cert=bool(getattr(Config, "PEER_REQUIRE_CLIENT_CERT", False)),
                trusted_cert_fps_file=getattr(Config, "TRUSTED_PEER_CERT_FPS_FILE", ""),
                trusted_peer_pubkeys_file=getattr(Config, "TRUSTED_PEER_PUBKEYS_FILE", ""),
                ca_bundle_path=getattr(Config, "P2P_CA_BUNDLE", None) if hasattr(Config, "P2P_CA_BUNDLE") else None,
                cert_dir=os.path.join(data_dir, "certs"),
                key_dir=os.path.join(data_dir, "keys"),
            )
        if not isinstance(peer_manager, PeerManager):
            raise TypeError("peer_manager must be an instance of PeerManager to enforce P2P security.")

        self.peer_manager = peer_manager
        self.consensus_manager = consensus_manager
        self.host = host
        self.port = port
        self.api_port = api_port  # HTTP API port for this node
        self.peer_api_endpoints: dict[str, str] = {}  # Map peer_id -> HTTP API endpoint
        self.quic_enabled = bool(getattr(Config, "P2P_ENABLE_QUIC", False) and QUIC_AVAILABLE)
        self.quic_dial_timeout = float(getattr(Config, "P2P_QUIC_DIAL_TIMEOUT", 1.0))
        self.server: WebSocketServer | None = None
        self.connections: dict[str, Any] = {}
        self.websocket_peer_ids: dict[Any, str] = {}
        self.http_peers: set[str] = set()
        self.peers = self.http_peers  # Alias used by legacy callers/tests
        self._peer_lock = threading.RLock()
        self.max_connections = max_connections
        max_msg_rate = getattr(Config, "P2P_MAX_MESSAGE_RATE", 100)
        security_log_rate = getattr(Config, "P2P_SECURITY_LOG_RATE", 20)
        max_bandwidth_in = getattr(Config, "P2P_MAX_BANDWIDTH_IN", max_bandwidth_in)
        max_bandwidth_out = getattr(Config, "P2P_MAX_BANDWIDTH_OUT", max_bandwidth_out)
        self.rate_limiter = MessageRateLimiter(max_rate=max_msg_rate)
        self.security_log_limiter = MessageRateLimiter(max_rate=security_log_rate)
        self.bandwidth_limiter_in = BandwidthLimiter(max_bandwidth_in, max_bandwidth_in // 10)
        self.bandwidth_limiter_out = BandwidthLimiter(max_bandwidth_out, max_bandwidth_out // 10)
        global_in = int(getattr(Config, "P2P_GLOBAL_BANDWIDTH_IN", 0))
        global_out = int(getattr(Config, "P2P_GLOBAL_BANDWIDTH_OUT", 0))
        self.global_bandwidth_in = BandwidthLimiter(global_in, max(1, global_in // 10)) if global_in > 0 else None
        self.global_bandwidth_out = BandwidthLimiter(global_out, max(1, global_out // 10)) if global_out > 0 else None
        self.received_chains = []
        self._quic_server: QUICServer | None = None
        self._dedup_max_items = max(100, int(getattr(Config, "P2P_DEDUP_MAX_ITEMS", 5000)))
        self._dedup_ttl = max(1.0, float(getattr(Config, "P2P_DEDUP_TTL_SECONDS", 900.0)))
        self._tx_seen_ids: set[str] = set()
        self._tx_seen_queue: deque[tuple[str, float]] = deque()
        self._block_seen_ids: set[str] = set()
        self._block_seen_queue: deque[tuple[str, float]] = deque()
        self.idle_timeout_seconds = max(60, int(getattr(Config, "P2P_CONNECTION_IDLE_TIMEOUT_SECONDS", 900)))
        self.handshake_timeout_seconds = max(1, int(getattr(Config, "P2P_HANDSHAKE_TIMEOUT_SECONDS", 15)))
        self._connection_last_seen: dict[str, float] = {}
        self._handshake_received: dict[str, float | None] = {}
        self._handshake_deadlines: dict[str, float] = {}
        self.peer_api_key = peer_api_key
        self._http_timeout = getattr(Config, "P2P_HTTP_TIMEOUT_SECONDS", 2)
        self.parallel_sync_workers = max(1, int(getattr(Config, "P2P_PARALLEL_SYNC_WORKERS", 4)))
        self.parallel_chunk_sync_enabled = bool(getattr(Config, "P2P_PARALLEL_SYNC_ENABLED", True))
        page_limit = max(1, int(getattr(Config, "P2P_PARALLEL_SYNC_PAGE_LIMIT", 200)))
        chunk_size = max(1, int(getattr(Config, "P2P_PARALLEL_SYNC_CHUNK_SIZE", page_limit)))
        self.parallel_sync_page_limit = page_limit
        self.parallel_sync_chunk_size = min(chunk_size, page_limit)
        self.parallel_sync_retry_limit = max(1, int(getattr(Config, "P2P_PARALLEL_SYNC_RETRY", 2)))
        self._reset_window_seconds = int(getattr(Config, "P2P_RESET_STORM_WINDOW_SECONDS", 300))
        self._reset_threshold = max(1, int(getattr(Config, "P2P_RESET_STORM_THRESHOLD", 5)))
        self._reset_events: dict[str, deque[float]] = defaultdict(deque)
        self.peer_features: dict[str, dict[str, Any]] = {}
        self.partial_sync_min_delta = max(0, int(getattr(Config, "P2P_PARTIAL_SYNC_MIN_DELTA", 100)))
        self.partial_sync_enabled = bool(getattr(Config, "P2P_PARTIAL_SYNC_ENABLED", True))
        self.checkpoint_sync: CheckpointSyncManager | None = (
            CheckpointSyncManager(self.blockchain, p2p_manager=self) if self.partial_sync_enabled else None
        )
        self._loop: asyncio.AbstractEventLoop | None = None
        self._persistent_peers: set[str] = set()  # Peers to maintain connections to
        self._reconnect_tasks: dict[str, asyncio.Task] = {}  # Ongoing reconnection tasks
        self._connection_monitor_task: asyncio.Task | None = None

    @staticmethod
    def _normalize_peer_uri(peer_uri: str) -> str:
        parsed = urlparse(peer_uri if "://" in peer_uri else f"http://{peer_uri}")
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid peer URI: {peer_uri}")
        return f"{parsed.scheme}://{parsed.netloc}"

    def _record_quic_error(self, host: str | None = None) -> None:
        """Increment QUIC error counter and emit a security event if configured."""
        try:
            from xai.core.api.monitoring import MetricsCollector

            metric = MetricsCollector.instance().get_metric("xai_p2p_quic_errors_total")
            if metric:
                metric.inc()
            SecurityEventRouter.dispatch(
                "p2p.quic_error",
                {"peer": host} if host else {},
                "WARNING",
            )
        except (ImportError, AttributeError, RuntimeError) as e:
            # Metrics collection failed - log but don't break P2P flows
            logger.debug(
                "QUIC error metric collection failed for host=%s: %s",
                host or "unknown",
                str(e),
                extra={"event": "p2p.quic_error_metric_failed", "peer": host}
            )

    def _record_quic_timeout(self, host: str | None = None) -> None:
        """Increment QUIC timeout counter, track it as an error, and emit a security event."""
        try:
            from xai.core.api.monitoring import MetricsCollector

            collector = MetricsCollector.instance()
            timeout_metric = collector.get_metric("xai_p2p_quic_timeouts_total")
            if timeout_metric:
                timeout_metric.inc()
            error_metric = collector.get_metric("xai_p2p_quic_errors_total")
            if error_metric:
                error_metric.inc()
            SecurityEventRouter.dispatch(
                "p2p.quic_timeout",
                {"peer": host, "timeout_seconds": self.quic_dial_timeout} if host else {"timeout_seconds": self.quic_dial_timeout},
                "ERROR",
            )
        except (ImportError, AttributeError, RuntimeError) as e:
            # Metrics collection failed - log but don't break P2P flows
            logger.debug(
                "QUIC timeout metric collection failed for host=%s: %s",
                host or "unknown",
                str(e),
                extra={"event": "p2p.quic_timeout_metric_failed", "peer": host}
            )

    def add_peer(self, peer_uri: str) -> bool:
        """Register a peer URI for HTTP/WebSocket communication."""
        if not peer_uri:
            with self._peer_lock:
                if peer_uri in self.http_peers:
                    return False
                self.http_peers.add(peer_uri)
            return True
        normalized = self._normalize_peer_uri(peer_uri)
        host = urlparse(normalized).hostname
        with self._peer_lock:
            if normalized in self.http_peers:
                return False
            self.http_peers.add(normalized)
        if host:
            try:
                if self.peer_manager.can_connect(host):
                    self.peer_manager.connect_peer(host)
            except (ValueError, RuntimeError) as e:
                # Log connection policy errors for debugging; reputation system will handle at runtime
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    "Failed to connect to peer during registration",
                    extra={
                        "event": "peer.connect_failed",
                        "host": host,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                )
        return True

    def remove_peer(self, peer_uri: str) -> None:
        """Remove a peer URI and disconnect matching active peers."""
        normalized = self._normalize_peer_uri(peer_uri)
        host = urlparse(normalized).hostname
        with self._peer_lock:
            self.http_peers.discard(normalized)
        if host:
            peers_to_disconnect = [
                pid for pid, info in self.peer_manager.connected_peers.items()
                if info.get("ip_address") == host
            ]
            for pid in peers_to_disconnect:
                try:
                    self.peer_manager.disconnect_peer(pid)
                except (ValueError, RuntimeError) as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        "Failed to disconnect peer",
                        extra={
                            "event": "peer.disconnect_failed",
                            "peer_id": pid,
                            "error": str(e),
                            "error_type": type(e).__name__
                        }
                    )

    def get_peer_count(self) -> int:
        """Return count of connected peers (deduped by host) or known HTTP peers."""
        unique_hosts = {
            info.get("ip_address")
            for info in getattr(self.peer_manager, "connected_peers", {}).values()
            if info.get("ip_address")
        }
        with self._peer_lock:
            http_count = len(self.http_peers)
        return max(http_count, len(unique_hosts))

    def get_peers(self) -> set[str]:
        """
        Return a combined set of peers from HTTP registration and active connections.

        Active connections are represented as websocket URIs using the configured
        P2P port so APIs can surface something meaningful even when no HTTP peers
        have been registered explicitly.
        """
        peers: set[str] = set()
        with self._peer_lock:
            peers.update(self.http_peers)
        for host in {
            info.get("ip_address")
            for info in getattr(self.peer_manager, "connected_peers", {}).values()
            if info.get("ip_address")
        }:
            peers.add(f"wss://{host}:{self.port}")
        return peers

    async def start(self) -> None:
        """Starts the P2P network manager."""
        # Store reference to the event loop for async dispatch
        self._loop = asyncio.get_running_loop()

        # For testnet mode, disable SSL to allow ws:// connections
        network_mode = os.getenv("XAI_NETWORK", "testnet").lower()
        if network_mode == "testnet":
            ssl_context = None
            logger.info(
                "Testnet mode: SSL disabled for P2P server",
                extra={"event": "p2p.ssl_disabled", "network_mode": network_mode}
            )
        else:
            ssl_context = self.peer_manager.encryption.create_ssl_context(
                is_server=True,
                require_client_cert=self.peer_manager.require_client_cert,
                ca_bundle=self.peer_manager.ca_bundle_path,
            )

        # Configure WebSocket keep-alive and timeouts for stability
        # Based on: https://websockets.readthedocs.io/en/stable/topics/keepalive.html
        ping_interval = int(getattr(Config, "P2P_PING_INTERVAL_SECONDS", 20))
        ping_timeout = int(getattr(Config, "P2P_PING_TIMEOUT_SECONDS", 20))
        close_timeout = int(getattr(Config, "P2P_CLOSE_TIMEOUT_SECONDS", 10))

        self.server = await websockets.serve(
            self._handler,
            self.host,
            self.port,
            ssl=ssl_context,
            ping_interval=ping_interval,  # Send ping every 20s to keep connection alive
            ping_timeout=ping_timeout,    # Wait 20s for pong before considering connection dead
            close_timeout=close_timeout,  # Wait 10s for close handshake
            max_size=2**20,              # 1MB max message size
            max_queue=32,                # Max queued messages
            compression=None              # Disable compression for lower latency
        )
        transport = "quic+ws" if self.quic_enabled else "ws"
        logger.info(
            "P2P server started on %s://%s:%d",
            transport,
            self.host,
            self.port,
            extra={"event": "p2p.server_started"}
        )
        if self.quic_enabled and QUIC_AVAILABLE:
            try:
                quic_config = QuicConfiguration(is_client=False, alpn_protocols=["xai-p2p"])
                self._quic_server = QUICServer(
                    self.host,
                    self.port + 1,  # QUIC on adjacent port
                    quic_config,
                    handler=lambda data: self._handle_quic_payload(data),
                )
                asyncio.create_task(self._quic_server.start())
                logger.info(
                    "P2P QUIC server started on %s:%d",
                    self.host,
                    self.port + 1,
                    extra={"event": "p2p.quic_server_started"}
                )
            except (OSError, RuntimeError, ValueError) as exc:
                logger.warning(
                    "QUIC disabled due to init failure: %s",
                    type(exc).__name__,
                    extra={"event": "p2p.quic_init_failed"}
                )
                self._record_quic_error(self.host)
                self.quic_enabled = False
        asyncio.create_task(self._connect_to_peers())
        asyncio.create_task(self._health_check())
        asyncio.create_task(self._broadcast_handshake_periodically())

        # Start connection monitoring task for automatic reconnection
        # Based on: https://www.lightspark.com/glossary/exponential-backoff
        self._connection_monitor_task = asyncio.create_task(self._monitor_connections())
        logger.info("Connection monitoring started", extra={"event": "p2p.monitor_started"})

        # Start periodic sync task to pull missing blocks from peers
        # Based on research: Bitcoin/Tendermint nodes actively pull blocks when behind
        self._periodic_sync_task = asyncio.create_task(self._periodic_sync())
        logger.info("Periodic sync task started", extra={"event": "p2p.periodic_sync_started"})

    async def stop(self) -> None:
        """Stops the P2P network manager."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        for conn in self.connections.values():
            await conn.close()
        self.connections.clear()
        self._connection_last_seen.clear()
        if self._quic_server:
            await self._quic_server.close()
        logger.info("P2P server stopped", extra={"event": "p2p.server_stopped"})

    async def _send_handshake(self, websocket: Any, peer_id: str) -> None:
        """Send protocol version/capabilities handshake to a peer."""
        # Build API endpoint URL for this node
        api_endpoint = None
        if self.api_port:
            # Use http:// for local/internal communication
            api_endpoint = f"http://{self.host}:{self.api_port}"
            # If host is 0.0.0.0, provide a more usable endpoint
            if self.host in ("0.0.0.0", "::"):
                import socket
                try:
                    hostname = socket.gethostname()
                    api_endpoint = f"http://{hostname}:{self.api_port}"
                except OSError:
                    # Fallback to localhost on socket errors
                    api_endpoint = f"http://localhost:{self.api_port}"

        handshake_payload = {
            "type": "handshake",
            "payload": {
                "version": getattr(P2PSecurityConfig, "PROTOCOL_VERSION", "1"),
                "features": list(getattr(P2PSecurityConfig, "SUPPORTED_FEATURES", set())),
                "node_id": self.peer_manager.encryption._node_identity_fingerprint(),  # noqa: SLF001
                "height": len(self.blockchain.chain),
                "api_endpoint": api_endpoint,  # HTTP API endpoint for sync
            },
        }
        await self._send_signed_message(websocket, peer_id, handshake_payload)

    async def _handler(self, websocket: Any, path: str | None = None) -> None:
        """Handles incoming WebSocket connections."""
        remote_ip = websocket.remote_address[0]
        if not self.peer_manager.can_connect(remote_ip):
            await websocket.close()
            return

        ssl_object = websocket.transport.get_extra_info("ssl_object")
        fingerprint = self.peer_manager.encryption.fingerprint_from_ssl_object(ssl_object) if ssl_object else None
        if self.peer_manager.require_client_cert and not fingerprint:
            self._log_security_event(remote_ip, "missing_client_certificate")
            await websocket.close()
            return
        if not self.peer_manager.is_cert_allowed(fingerprint):
            self._log_security_event(remote_ip, "untrusted_client_certificate")
            await websocket.close()
            return

        if len(self.connections) >= self.max_connections:
            logger.warning(
                "Max connections reached, rejecting new connection from %s",
                remote_ip,
                extra={"event": "p2p.connection_rejected_max"}
            )
            await websocket.close()
            return
        
        peer_id = self.peer_manager.connect_peer(remote_ip)
        self.connections[peer_id] = websocket
        self.websocket_peer_ids[websocket] = peer_id
        now = time.time()
        self._connection_last_seen[peer_id] = now
        self._handshake_received[peer_id] = None
        self._handshake_deadlines[peer_id] = now + self.handshake_timeout_seconds
        await self._send_handshake(websocket, peer_id)
        logger.info(
            "Peer connected: %s",
            remote_ip,
            extra={"event": "p2p.peer_connected", "peer": peer_id}
        )

        try:
            async for message in websocket:
                await self._handle_message(websocket, message)
        except ConnectionClosed as exc:
            self._record_connection_reset_event(peer_id, reason=str(exc))
            logger.debug(
                "Connection to peer %s closed: %s",
                remote_ip,
                type(exc).__name__,
                extra={"event": "p2p.peer_connection_closed", "peer": peer_id},
            )
        finally:
            if peer_id in self.connections or self._handshake_received.get(peer_id) is not None:
                conn = self.connections.get(peer_id)
                self._disconnect_peer(peer_id, conn)
            logger.info(
                "Peer disconnected: %s",
                remote_ip,
                extra={"event": "p2p.peer_disconnected", "peer": peer_id}
            )

    async def _listen_to_outbound_peer(self, websocket: Any, peer_id: str) -> None:
        """Listen for messages on outbound connections and route them through the main handler."""
        try:
            remote_addr = getattr(websocket, "remote_address", None)
            remote_ip = remote_addr[0] if remote_addr and len(remote_addr) > 0 else "<outbound>"
        except (TypeError, IndexError, AttributeError):
            remote_ip = "<outbound>"
        try:
            async for message in websocket:
                await self._handle_message(websocket, message)
        except ConnectionClosed as exc:
            self._record_connection_reset_event(peer_id, reason=str(exc))
            logger.debug(
                "Outbound connection to peer %s closed: %s",
                remote_ip,
                type(exc).__name__,
                extra={"event": "p2p.outbound_closed", "peer": peer_id},
            )
        finally:
            if peer_id in self.connections or self._handshake_received.get(peer_id) is not None:
                conn = self.connections.get(peer_id)
                self._disconnect_peer(peer_id, conn)
            logger.info(
                "Outbound peer disconnected: %s",
                remote_ip,
                extra={"event": "p2p.outbound_disconnected", "peer": peer_id}
            )

    def _record_connection_reset_event(self, peer_id: str, *, reason: str | None = None, now: float | None = None) -> None:
        """
        Track connection reset/disconnect storms and ban peers that repeatedly reset
        connections within a short time window to mitigate connection reset floods.
        """
        now_ts = now if now is not None else time.time()
        dq = self._reset_events[peer_id]
        dq.append(now_ts)
        cutoff = now_ts - self._reset_window_seconds
        while dq and dq[0] < cutoff:
            dq.popleft()
        if len(dq) >= self._reset_threshold:
            logger.warning(
                "Peer %s triggering connection reset storm (count=%d within %ds) - banning",
                peer_id[:16],
                len(dq),
                self._reset_window_seconds,
                extra={
                    "event": "p2p.connection_reset_storm",
                    "peer": peer_id,
                    "count": len(dq),
                    "window_seconds": self._reset_window_seconds,
                    "reason": reason or "reset_storm",
                },
            )
            self.peer_manager.ban_peer(peer_id)
            self._emit_security_event(
                "p2p.connection_reset_storm",
                severity="WARNING",
                payload={
                    "peer": peer_id,
                    "count": len(dq),
                    "window_seconds": self._reset_window_seconds,
                    "reason": reason or "reset_storm",
                },
            )
            dq.clear()

    async def _connect_to_peers(self) -> None:
        """Connects to the initial set of peers with backoff/retry."""
        peers_to_connect = set(self.peer_manager.discovery.get_random_peers())
        if not peers_to_connect:
            try:
                discovered = await self.peer_manager.discover_peers()
                peers_to_connect = set(discovered or [])
            except (NetworkError, PeerError, OSError, TimeoutError, asyncio.TimeoutError) as exc:
                logger.warning(
                    "Peer discovery failed during startup: %s",
                    type(exc).__name__,
                    extra={"event": "p2p.discovery_failed", "error": str(exc)},
                )
        bootstrap_seeds = set(getattr(self.peer_manager.discovery, "bootstrap_nodes", []) or [])
        peers_to_connect.update(bootstrap_seeds)

        # Add bootstrap nodes to http_peers for periodic sync
        with self._peer_lock:
            for peer_uri in bootstrap_seeds:
                normalized = self._normalize_peer_uri(peer_uri)
                self.http_peers.add(normalized)

        logger.info(
            "Bootstrapping P2P connections to %d peers",
            len(peers_to_connect),
            extra={
                "event": "p2p.bootstrap_connect",
                "peers": list(peers_to_connect),
            },
        )
        for peer_uri in peers_to_connect:
            asyncio.create_task(self._connect_with_retry(peer_uri))

    async def _connect_with_retry(self, peer_uri: str, max_retries: int = 5, initial_delay: int = 5) -> None:
        """Tries to connect to a peer with exponential backoff."""
        delay = initial_delay
        for attempt in range(max_retries):
            try:
                ssl_context = self.peer_manager.encryption.create_ssl_context(
                    ca_bundle=self.peer_manager.ca_bundle_path
                )

                # Configure outbound WebSocket with keep-alive
                # Based on: https://websockets.readthedocs.io/en/stable/reference/asyncio/client.html
                ping_interval = int(getattr(Config, "P2P_PING_INTERVAL_SECONDS", 20))
                ping_timeout = int(getattr(Config, "P2P_PING_TIMEOUT_SECONDS", 20))
                close_timeout = int(getattr(Config, "P2P_CLOSE_TIMEOUT_SECONDS", 10))

                websocket = await websockets.connect(
                    peer_uri,
                    ssl=ssl_context,
                    ping_interval=ping_interval,
                    ping_timeout=ping_timeout,
                    close_timeout=close_timeout,
                    max_size=2**20,
                    compression=None
                )
                ssl_object = websocket.transport.get_extra_info("ssl_object")
                fingerprint = self.peer_manager.encryption.fingerprint_from_ssl_object(ssl_object) if ssl_object else None
                if not self.peer_manager.is_cert_allowed(fingerprint):
                    self._log_security_event(peer_uri, "untrusted_cert_fingerprint")
                    await websocket.close()
                    self.peer_manager.reputation.record_invalid_block(peer_uri)  # Generic penalty
                    return
                peer_id = self.peer_manager.connect_peer(websocket.remote_address[0])
                self.connections[peer_id] = websocket
                self.websocket_peer_ids[websocket] = peer_id
                now = time.time()
                self._connection_last_seen[peer_id] = now
                self._handshake_received[peer_id] = None
                self._handshake_deadlines[peer_id] = now + self.handshake_timeout_seconds
                logger.info(
                    "Connected to peer: %s",
                    peer_uri,
                    extra={"event": "p2p.outbound_connected", "peer": peer_uri}
                )
                await self._send_handshake(websocket, peer_id)
                asyncio.create_task(self._listen_to_outbound_peer(websocket, peer_id))
                return
            except (WebSocketException, OSError, ConnectionError, asyncio.TimeoutError, ValueError) as e:
                logger.warning(
                    "Failed to connect to peer %s on attempt %d/%d: %s",
                    peer_uri,
                    attempt + 1,
                    max_retries,
                    type(e).__name__,
                    extra={"event": "p2p.outbound_retry", "peer": peer_uri, "error_type": type(e).__name__},
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    logger.warning(
                        "Giving up on peer %s after %d failed attempts",
                        peer_uri,
                        max_retries,
                        extra={"event": "p2p.outbound_failed", "peer": peer_uri}
                    )
                    self.peer_manager.reputation.record_disconnect(peer_uri)

    async def _health_check(self) -> None:
        """Periodically checks the health of connected peers."""
        while True:
            await asyncio.sleep(60)
            try:
                self.peer_manager.refresh_trust_stores()
            except (OSError, ValueError, RuntimeError) as exc:
                self._log_security_event("self", f"trust_store_refresh_failed:{exc}")
            logger.debug(
                "Health check: %d peers connected",
                self.get_peer_count(),
                extra={"event": "p2p.health_check"}
            )
            await self._disconnect_idle_connections()
            await self._disconnect_stalled_handshakes()

    async def _broadcast_handshake_periodically(self) -> None:
        """Re-announce capabilities/version periodically to connected peers."""
        interval = int(getattr(Config, "P2P_HANDSHAKE_INTERVAL_SECONDS", 900))
        while True:
            await asyncio.sleep(interval)
            for peer_id, conn in list(self.connections.items()):
                try:
                    await self._send_handshake(conn, peer_id)
                except (NetworkError, PeerError, ConnectionError, OSError, RuntimeError) as exc:  # pragma: no cover - defensive logging
                    logger.debug(
                        "Failed to send periodic handshake to %s: %s",
                        peer_id[:16],
                        exc,
                        extra={
                            "event": "p2p.handshake_send_failed",
                            "peer": peer_id,
                            "error_type": type(exc).__name__,
                        },
                    )

    async def _monitor_connections(self) -> None:
        """
        Monitor connections to persistent peers and automatically reconnect on failure.
        Implements exponential backoff as recommended by Bitcoin and Tendermint.
        Based on: https://github.com/tendermint/tendermint/issues/939
        """
        monitor_interval = int(getattr(Config, "P2P_MONITOR_INTERVAL_SECONDS", 30))
        max_backoff = int(getattr(Config, "P2P_MAX_RECONNECT_BACKOFF_SECONDS", 300))

        while True:
            await asyncio.sleep(monitor_interval)

            # Get persistent peers from bootstrap nodes config
            if hasattr(self.peer_manager, 'discovery') and hasattr(self.peer_manager.discovery, 'bootstrap_nodes'):
                bootstrap_peers = set(self.peer_manager.discovery.bootstrap_nodes)
                self._persistent_peers.update(bootstrap_peers)

            # Check each persistent peer
            for peer_uri in list(self._persistent_peers):
                # Skip if already reconnecting
                if peer_uri in self._reconnect_tasks:
                    task = self._reconnect_tasks[peer_uri]
                    if not task.done():
                        continue
                    # Clean up completed task
                    del self._reconnect_tasks[peer_uri]

                # Check if peer is connected
                is_connected = False
                with self._peer_lock:
                    if peer_uri in self.http_peers:
                        is_connected = True
                    else:
                        # Check by hostname match in connections
                        try:
                            parsed = urlparse(peer_uri)
                            hostname = parsed.hostname
                            for peer_id in self.connections:
                                if hostname and hostname in peer_id:
                                    is_connected = True
                                    break
                        except (ValueError, AttributeError):
                            pass

                # Reconnect if not connected
                if not is_connected:
                    logger.info(
                        "Persistent peer %s disconnected, scheduling reconnection",
                        peer_uri,
                        extra={"event": "p2p.persistent_peer_disconnected", "peer_uri": peer_uri}
                    )
                    task = asyncio.create_task(self._reconnect_persistent_peer(peer_uri, max_backoff))
                    self._reconnect_tasks[peer_uri] = task

    async def _periodic_sync(self) -> None:
        """
        Periodically check if we're behind peers and sync missing blocks.
        Based on research findings:
        - Bitcoin nodes actively request blocks when behind
        - Tendermint uses periodic state sync
        - Blockchain nodes need both push (broadcast) AND pull (sync) mechanisms
        Research sources:
        - https://developer.bitcoin.org/devguide/p2p_network.html
        - https://blog.cosmos.network/cosmos-sdk-state-sync-guide-99e4cf43be2f
        """
        sync_interval = int(getattr(Config, "P2P_SYNC_INTERVAL_SECONDS", 30))
        logger.info("Periodic sync configured with interval=%ds", sync_interval, extra={"event": "p2p.periodic_sync_config"})

        while True:
            logger.info("Periodic sync sleeping for %ds...", sync_interval, extra={"event": "p2p.periodic_sync_sleep"})
            await asyncio.sleep(sync_interval)
            logger.info("Periodic sync awake, checking sync status", extra={"event": "p2p.periodic_sync_awake"})

            try:
                # Get peer API endpoints from connected peers (via handshake)
                peers = self._get_peer_api_endpoints()
                logger.info("Periodic sync found %d peer API endpoints: %s", len(peers), peers, extra={"event": "p2p.periodic_sync_peers"})
                if not peers:
                    # Fallback to legacy http_peers if no API endpoints available yet
                    # This ensures nodes started with --peers flag can sync even without
                    # WebSocket handshake completion (fixes P2P sync bug where nodes
                    # could see each other but never sync blocks)
                    peers = self._http_peers_snapshot()
                    logger.info("Periodic sync falling back to http_peers: %s", peers, extra={"event": "p2p.periodic_sync_http_fallback"})
                if not peers:
                    logger.info("Periodic sync: No peer endpoints available, skipping", extra={"event": "p2p.periodic_sync_no_peers"})
                    continue

                local_height = len(getattr(self.blockchain, "chain", []))
                logger.info("Periodic sync: Local height=%d", local_height, extra={"event": "p2p.periodic_sync_local_height"})
                summaries = await self._collect_peer_chain_summaries(peers)
                logger.info("Periodic sync got %d summaries", len(summaries), extra={"event": "p2p.periodic_sync_summaries"})

                if not summaries:
                    logger.info("Periodic sync: No summaries, skipping", extra={"event": "p2p.periodic_sync_no_summaries"})
                    continue

                # Check if any peer is ahead
                max_peer_height = max(s.get("total", 0) for s in summaries)
                logger.info("Periodic sync: Max peer height=%d", max_peer_height, extra={"event": "p2p.periodic_sync_peer_height"})

                if max_peer_height > local_height:
                    blocks_behind = max_peer_height - local_height
                    logger.info(
                        "Node is %d blocks behind (local: %d, peer max: %d), syncing...",
                        blocks_behind,
                        local_height,
                        max_peer_height,
                        extra={
                            "event": "p2p.periodic_sync_needed",
                            "local_height": local_height,
                            "peer_height": max_peer_height,
                            "blocks_behind": blocks_behind
                        }
                    )

                    # Call async sync directly (no longer needs run_in_executor)
                    await self.sync_with_network()

                    # Log result
                    new_height = len(getattr(self.blockchain, "chain", []))
                    if new_height > local_height:
                        logger.info(
                            "Periodic sync added %d blocks (height: %d -> %d)",
                            new_height - local_height,
                            local_height,
                            new_height,
                            extra={
                                "event": "p2p.periodic_sync_success",
                                "old_height": local_height,
                                "new_height": new_height,
                                "blocks_synced": new_height - local_height
                            }
                        )
                    else:
                        logger.debug(
                            "Periodic sync completed but no blocks added",
                            extra={"event": "p2p.periodic_sync_no_progress"}
                        )

            except (NetworkError, ValidationError, StorageError, DatabaseError, OSError,
                    asyncio.TimeoutError, TimeoutError, ConnectionError) as exc:
                logger.debug(
                    "Periodic sync encountered error: %s",
                    exc,
                    extra={
                        "event": "p2p.periodic_sync_error",
                        "error_type": type(exc).__name__
                    }
                )

    async def _reconnect_persistent_peer(self, peer_uri: str, max_backoff: int = 300) -> None:
        """
        Reconnect to a persistent peer with exponential backoff.
        Based on: https://docs.cometbft.com/v0.38/spec/p2p/legacy-docs/config
        """
        base_delay = 5  # Start with 5 second delay
        max_attempts = 50  # Try for ~4 hours with exponential backoff
        delay = base_delay

        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(
                    "Reconnection attempt %d/%d to %s (delay: %ds)",
                    attempt,
                    max_attempts,
                    peer_uri,
                    delay,
                    extra={"event": "p2p.reconnect_attempt", "peer_uri": peer_uri, "attempt": attempt}
                )

                # Try to connect
                await self._connect_with_retry(peer_uri, max_retries=1, initial_delay=1)

                # Success! Exit the reconnection loop
                logger.info(
                    "Successfully reconnected to persistent peer %s after %d attempts",
                    peer_uri,
                    attempt,
                    extra={"event": "p2p.reconnect_success", "peer_uri": peer_uri, "attempts": attempt}
                )
                return

            except (NetworkError, PeerError, ConnectionError, OSError, WebSocketException,
                    asyncio.TimeoutError, TimeoutError) as exc:
                logger.debug(
                    "Reconnection attempt %d failed for %s: %s",
                    attempt,
                    peer_uri,
                    exc,
                    extra={"event": "p2p.reconnect_failed", "peer_uri": peer_uri, "attempt": attempt}
                )

                # Exponential backoff with cap
                delay = min(delay * 2, max_backoff)
                await asyncio.sleep(delay)

        logger.warning(
            "Giving up reconnection to %s after %d attempts",
            peer_uri,
            max_attempts,
            extra={"event": "p2p.reconnect_gave_up", "peer_uri": peer_uri}
        )

    async def _disconnect_idle_connections(self) -> None:
        """Close peers that have been idle beyond the configured timeout."""
        if self.idle_timeout_seconds <= 0:
            return
        now = time.time()
        cutoff = now - self.idle_timeout_seconds
        for peer_id, last_seen in list(self._connection_last_seen.items()):
            if last_seen >= cutoff:
                continue
            conn = self.connections.get(peer_id)
            idle_duration = now - last_seen
            if not conn:
                self._connection_last_seen.pop(peer_id, None)
                continue
            logger.warning(
                "Disconnecting idle peer %s after %.0fs of inactivity",
                peer_id[:16],
                idle_duration,
                extra={"event": "p2p.idle_disconnect", "peer": peer_id, "idle_seconds": int(idle_duration)},
            )
            try:
                await conn.close()
            except (NetworkError, ConnectionError, OSError, RuntimeError) as exc:
                logger.debug(
                    "Error closing idle connection for %s: %s",
                    peer_id[:16],
                    exc,
                    extra={
                        "event": "p2p.idle_disconnect_error",
                        "peer": peer_id,
                        "error_type": type(exc).__name__,
                    },
                )
            self._disconnect_peer(peer_id, conn)
            self._emit_security_event(
                "p2p.idle_disconnect",
                severity="INFO",
                payload={"peer": peer_id, "idle_seconds": int(idle_duration)},
            )

    async def _disconnect_stalled_handshakes(self) -> None:
        """Drop peers that never complete the version/capabilities handshake."""
        if self.handshake_timeout_seconds <= 0:
            return
        now = time.time()
        for peer_id, deadline in list(self._handshake_deadlines.items()):
            if self._handshake_received.get(peer_id) is not None:
                continue
            if now < deadline:
                continue
            conn = self.connections.get(peer_id)
            if conn:
                try:
                    await conn.close()
                except (NetworkError, ConnectionError, OSError, RuntimeError) as exc:  # pragma: no cover - defensive cleanup
                    logger.debug(
                        "Error closing stalled handshake connection for %s: %s",
                        peer_id[:16],
                        exc,
                        extra={
                            "event": "p2p.handshake_timeout_close_failed",
                            "peer": peer_id,
                            "error_type": type(exc).__name__,
                        },
                    )
            self._disconnect_peer(peer_id, conn)
            logger.warning(
                "Disconnecting peer %s due to handshake timeout (>%ss)",
                peer_id[:16],
                self.handshake_timeout_seconds,
                extra={"event": "p2p.handshake_timeout", "peer": peer_id},
            )
            self._emit_security_event(
                "p2p.handshake_timeout",
                severity="WARNING",
                payload={"peer": peer_id},
            )

    def _attempt_partial_sync(self, *, force: bool = False) -> bool:
        """Fetch and apply a checkpoint payload before performing full sync."""
        if not self.partial_sync_enabled or not self.checkpoint_sync:
            return False
        try:
            metadata = self.checkpoint_sync.get_best_checkpoint_metadata()
        except (NetworkError, PeerError, StorageError, ValueError, RuntimeError) as exc:  # pragma: no cover - defensive logging
            logger.debug(
                "Partial sync metadata unavailable: %s",
                exc,
                extra={
                    "event": "p2p.partial_sync_meta_failed",
                    "error_type": type(exc).__name__,
                },
            )
            return False
        if not metadata:
            return False
        remote_height = metadata.get("height")
        if remote_height is None:
            return False
        local_height = len(self.blockchain.chain)
        if not force:
            delta = remote_height - local_height
            if delta <= 0:
                return False
            if delta < self.partial_sync_min_delta:
                return False
        applied = False
        try:
            applied = bool(self.checkpoint_sync.fetch_validate_apply())
        except (NetworkError, PeerError, ValidationError, StorageError, ValueError, RuntimeError) as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "Partial checkpoint sync failed: %s",
                exc,
                extra={
                    "event": "p2p.partial_sync_failed",
                    "height": remote_height,
                    "error_type": type(exc).__name__,
                },
            )
            return False
        if applied:
            logger.info(
                "Partial checkpoint sync applied (height=%s, source=%s)",
                remote_height,
                metadata.get("source", "unknown"),
                extra={
                    "event": "p2p.partial_sync_applied",
                    "height": remote_height,
                    "source": metadata.get("source", "unknown"),
                },
            )
        return applied

    def _disconnect_peer(self, peer_id: str, conn: Any | None) -> None:
        """Centralized cleanup for peer disconnections without duplicating dict removals."""
        if peer_id in self.connections:
            self.connections.pop(peer_id, None)
        if conn:
            self.websocket_peer_ids.pop(conn, None)
        self._connection_last_seen.pop(peer_id, None)
        self._handshake_received.pop(peer_id, None)
        self._handshake_deadlines.pop(peer_id, None)
        try:
            self.peer_manager.disconnect_peer(peer_id)
        except (PeerError, ValueError, RuntimeError) as exc:
            logger.debug(
                "Error disconnecting peer %s: %s",
                peer_id[:16],
                exc,
                extra={
                    "event": "p2p.disconnect_cleanup_failed",
                    "peer": peer_id,
                    "error_type": type(exc).__name__,
                },
            )

    def _emit_security_event(
        self,
        event_type: str,
        severity: str = "WARNING",
        payload: dict[str, Any] | None = None,
    ) -> None:
        """
        Forward P2P security events through the global router so metrics and webhooks
        receive a consistent signal. Falls back to metrics directly when no sinks are
        registered (e.g., unit tests without node initialization).
        """
        normalized_severity = (severity or "INFO").upper()
        payload = dict(payload or {})
        peer_id = payload.get("peer")
        if peer_id:
            # Redact peer identifiers to avoid leaking IPs/IDs into logs/webhooks.
            payload["peer"] = f"peer#{hashlib.sha256(str(peer_id).encode('utf-8')).hexdigest()[:10]}"
        sinks = getattr(SecurityEventRouter, "_sinks", [])
        dispatched = False
        try:
            SecurityEventRouter.dispatch(event_type, payload, normalized_severity)
            dispatched = bool(sinks)
        except (AttributeError, RuntimeError, TypeError) as e:
            # Avoid surfacing routing errors on hot paths
            logger.debug(f"Security event dispatch failed for {event_type}: {e}")

        if not dispatched:
            try:
                from xai.core.api.monitoring import MetricsCollector
                MetricsCollector.instance().record_security_event(
                    event_type=event_type,
                    severity=normalized_severity,
                    payload=payload,
                )
            except (ImportError, AttributeError, RuntimeError) as e:
                # Metrics collection unavailable - log but continue
                logger.debug(f"Failed to record security event in metrics: {e}")

    def _log_security_event(self, peer_id: str, message: str) -> None:
        """Log security-related events with lightweight rate limiting to avoid log flooding."""
        if os.getenv("XAI_P2P_DISABLE_SECURITY_EVENTS", "0").lower() in {"1", "true", "yes", "on"}:
            return
        if self.security_log_limiter.is_rate_limited(peer_id):
            return
        logger.warning(
            "Security event from %s: %s",
            peer_id[:16] if peer_id else "<unknown>",
            message,
            extra={"event": f"p2p.security.{message.split(':')[0]}", "peer": peer_id}
        )
        self._emit_security_event(
            event_type=f"p2p.{message}",
            severity="WARNING",
            payload={"peer": peer_id},
        )
        
    async def _handle_message(self, websocket: ServerConnection | None, message: str | bytes) -> None:
        """Handles incoming messages from peers, splitting concatenated messages on newlines."""
        remote_addr = getattr(websocket, "remote_address", ("<quic>", 0))
        fallback_peer = remote_addr[0] if isinstance(remote_addr, (tuple, list)) and remote_addr else str(remote_addr)
        peer_id = self.websocket_peer_ids.get(websocket, fallback_peer)

        # Convert to string and split on newlines to handle concatenated messages
        message_str = message if isinstance(message, str) else message.decode("utf-8", errors="replace")
        individual_messages = [msg.strip() for msg in message_str.split("\n") if msg.strip()]

        # Process each message separately
        for msg in individual_messages:
            await self._process_single_message(websocket, peer_id, msg.encode("utf-8"))

    async def _process_single_message(self, websocket: ServerConnection | None, peer_id: str, raw_bytes: bytes) -> None:
        """Process a single message from a peer."""
        debug_signing = bool(int(os.getenv("XAI_P2P_DEBUG_SIGNING", "0")))
        message_data: dict[str, Any] | None = None
        now = time.time()
        if peer_id in self._connection_last_seen:
            self._connection_last_seen[peer_id] = now
        
        message_size = len(raw_bytes)
        if self.global_bandwidth_in and not self.global_bandwidth_in.consume("global", message_size):
            logger.warning(
                "Global inbound bandwidth exceeded, closing connection",
                extra={"event": "p2p.global_bandwidth_exceeded_in", "peer": peer_id},
            )
            await websocket.close()
            self._disconnect_peer(peer_id, websocket)
            return
        if not self.bandwidth_limiter_in.consume(peer_id, message_size):
            logger.warning(
                "Peer %s exceeding incoming bandwidth, disconnecting",
                peer_id[:16],
                extra={"event": "p2p.bandwidth_exceeded_in", "peer": peer_id}
            )
            await websocket.close()
            conn = self.connections.get(peer_id)
            self._disconnect_peer(peer_id, conn)
            return

        if self.rate_limiter.is_rate_limited(peer_id):
            logger.debug(
                "Peer %s is rate-limited, ignoring message",
                peer_id[:16],
                extra={"event": "p2p.rate_limited", "peer": peer_id}
            )
            self._log_security_event(peer_id, "rate_limited")
            return

        try:
            verified_message = self.peer_manager.encryption.verify_signed_message(raw_bytes)
            message_data = verified_message
            if not verified_message:
                digest = hashlib.sha256(raw_bytes).hexdigest()
                preview = raw_bytes[:512].decode("utf-8", errors="replace")
                logger.warning(
                    "Signature verification failed for peer %s (size=%d, sha256=%s)%s",
                    peer_id[:16],
                    len(raw_bytes),
                    digest,
                    f" preview={preview}" if debug_signing else "",
                    extra={
                        "event": "p2p.invalid_signature",
                        "peer": peer_id,
                        "sha256": digest,
                        "preview": preview if debug_signing else None,
                    },
                )
                self._log_security_event(peer_id, "invalid_or_stale_signature")
                self._emit_security_event(
                    event_type="p2p.invalid_signature",
                    severity="WARNING",
                    payload={"peer": peer_id, "sha256": digest},
                )
                self.peer_manager.reputation.record_invalid_transaction(peer_id) # Generic penalty
                return
            
            sender_id = verified_message.get("sender") or peer_id
            nonce = verified_message.get("nonce")
            timestamp = verified_message.get("timestamp")

            if not self.peer_manager.is_sender_allowed(sender_id):
                self._log_security_event(sender_id, "untrusted_sender")
                self.peer_manager.reputation.record_invalid_transaction(peer_id)
                return

            if nonce:
                if self.peer_manager.is_nonce_replay(sender_id, nonce, timestamp):
                    self._log_security_event(sender_id, "replay_detected")
                    self.peer_manager.reputation.record_invalid_transaction(sender_id)
                    return
                self.peer_manager.record_nonce(sender_id, nonce, timestamp)

            data = verified_message.get("payload")
            msg_version = verified_message.get("version") or verified_message.get(HEADER_VERSION) or str(
                getattr(P2PSecurityConfig, "PROTOCOL_VERSION", "1")
            )
            if msg_version not in getattr(P2PSecurityConfig, "SUPPORTED_VERSIONS", {"1"}):
                self._log_security_event(peer_id, f"unsupported_protocol_version:{msg_version}")
                self.peer_manager.reputation.record_invalid_transaction(peer_id)
                return
            features = set()
            feat_raw = verified_message.get("features") or verified_message.get("headers", {}).get("X-Node-Features")
            if feat_raw:
                features = set(str(feat_raw).split(","))
            if features and not features.issubset(getattr(P2PSecurityConfig, "SUPPORTED_FEATURES", set())):
                self._log_security_event(peer_id, f"unsupported_features:{','.join(sorted(features))}")
                self.peer_manager.reputation.record_invalid_transaction(peer_id)
                return

            message_type = data.get("type")
            payload = data.get("payload")

            handshake_ts = self._handshake_received.get(peer_id)
            if (
                websocket is not None
                and message_type != "handshake"
                and self.handshake_timeout_seconds > 0
                and handshake_ts is None
            ):
                self._log_security_event(peer_id, "handshake_missing")
                self._emit_security_event(
                    "p2p.handshake_missing",
                    severity="WARNING",
                    payload={"peer": peer_id},
                )
                if websocket:
                    try:
                        await websocket.close()
                    except (NetworkError, ConnectionError, OSError, RuntimeError) as exc:  # pragma: no cover - defensive
                        logger.debug(
                            "Error closing peer %s after missing handshake: %s",
                            peer_id[:16],
                            exc,
                            extra={
                                "event": "p2p.handshake_close_failed",
                                "peer": peer_id,
                                "error_type": type(exc).__name__,
                            },
                        )
                self._disconnect_peer(peer_id, websocket)
                self.peer_manager.reputation.record_invalid_transaction(peer_id)
                return

            # Message type dispatch - extracted handlers for complex types
            if message_type == "handshake":
                self._handle_handshake_message(peer_id, payload)
                return
            if message_type == "transaction":
                if not self._handle_transaction_message(peer_id, payload):
                    return  # Duplicate, already handled
            elif message_type == "block":
                if not self._handle_block_message(peer_id, payload):
                    return  # Duplicate, already handled
            elif message_type == "get_chain":
                # Legacy full chain request - uses O(n) serialization
                # Prefer get_chain_range for paginated sync
                await self._send_signed_message(
                    websocket, peer_id, {"type": "chain", "payload": self.blockchain.to_dict()}
                )
            elif message_type == "get_chain_range":
                # Paginated chain sync - O(limit) instead of O(n)
                offset = payload.get("offset", 0) if isinstance(payload, dict) else 0
                limit = payload.get("limit") if isinstance(payload, dict) else None
                include_pending = payload.get("include_pending", offset == 0) if isinstance(payload, dict) else (offset == 0)
                paginated_data = self.blockchain.to_dict_paginated(
                    offset=offset,
                    limit=limit,
                    include_pending=include_pending,
                )
                await self._send_signed_message(
                    websocket, peer_id, {"type": "chain_range", "payload": paginated_data}
                )
            elif message_type == "chain":
                self.received_chains.append(payload)
            elif message_type == "chain_range":
                # Paginated chain response - append to received chains for processing
                self.received_chains.append(payload)
            elif message_type == "get_peers":
                await self._handle_get_peers_message(websocket, peer_id)
            elif message_type == "peers":
                self.peer_manager.discovery.exchange_peers(payload)
            elif message_type == "get_checkpoint":
                metadata = self._get_checkpoint_metadata()
                await self._send_signed_message(
                    websocket,
                    peer_id,
                    {"type": "checkpoint", "payload": metadata},
                )
            elif message_type == "checkpoint":
                self.peer_features[peer_id] = self.peer_features.get(peer_id, {})
                self.peer_features[peer_id]["checkpoint"] = payload
            elif message_type == "checkpoint_request":
                await self._handle_checkpoint_request(websocket, peer_id, payload)
            elif message_type == "checkpoint_payload":
                # Peers can cache advertised payload URLs for downstream sync manager
                self.peer_features[peer_id] = self.peer_features.get(peer_id, {})
                self.peer_features[peer_id]["checkpoint_payload"] = payload
            elif message_type == "inv":
                await self._handle_inventory_announcement(websocket, peer_id, payload)
            elif message_type == "getdata":
                await self._handle_getdata_request(websocket, peer_id, payload)
            elif message_type == "ping":
                await self._send_signed_message(websocket, peer_id, {"type": "pong"})
            elif message_type == "pong":
                # Latency can be calculated here
                pass
            else:
                logger.debug(
                    "Unknown message type: %s",
                    message_type,
                    extra={"event": "p2p.unknown_message_type", "peer": peer_id}
                )
        except json.JSONDecodeError:
            preview = raw_bytes[:256].decode("utf-8", errors="replace") if isinstance(raw_bytes, (bytes, bytearray)) else str(raw_bytes)[:256]
            logger.warning(
                "Invalid JSON received from peer %s preview=%s",
                peer_id[:16],
                preview,
                extra={"event": "p2p.invalid_json", "peer": peer_id, "preview": preview}
            )
            self.peer_manager.reputation.record_invalid_transaction(peer_id)
        except (ValueError, TypeError, AttributeError, RuntimeError, KeyError) as e:
            message_preview = raw_bytes[:256].decode("utf-8", errors="replace") if isinstance(raw_bytes, (bytes, bytearray)) else str(raw_bytes)[:256]
            msg_type = None
            block_prev = None
            block_index = None
            try:
                msg_type = (message_data or {}).get("type") or (message_data or {}).get("payload", {}).get("type")
            except (TypeError, AttributeError, KeyError):
                msg_type = None
            try:
                parsed = message_data or json.loads(raw_bytes.decode("utf-8"))
                inner = parsed.get("message", parsed) if isinstance(parsed, dict) else {}
                payload_dict = inner.get("payload", {}) if isinstance(inner, dict) else {}
                block_payload = payload_dict.get("payload", payload_dict) if isinstance(payload_dict, dict) else {}
                if isinstance(block_payload, dict):
                    block_prev = block_payload.get("previous_hash")
                    block_index = block_payload.get("index")
            except (json.JSONDecodeError, ValueError, TypeError, AttributeError, KeyError, UnicodeDecodeError):
                block_prev = block_prev
            logger.error(
                "Error handling message from peer %s: %s (%s) type=%s preview=%s prev=%s idx=%s",
                peer_id[:16],
                type(e).__name__,
                str(e),
                msg_type,
                message_preview,
                block_prev,
                block_index,
                extra={
                    "event": "p2p.message_handling_error",
                    "peer": peer_id,
                    "error": str(e),
                    "message_type": msg_type,
                    "preview": message_preview,
                    "block_previous_hash": block_prev,
                    "block_index": block_index,
                }
            )
            self.peer_manager.reputation.record_invalid_transaction(peer_id)

    async def _handle_inventory_announcement(
        self,
        websocket: ServerConnection | None,
        peer_id: str,
        payload: dict[str, Any] | None,
    ) -> None:
        if not websocket:
            return
        payload = payload or {}
        tx_ids = payload.get("transactions") or []
        block_hashes = payload.get("blocks") or []
        missing_txs = [txid for txid in tx_ids if not self._has_transaction(txid)]
        missing_blocks = [block_hash for block_hash in block_hashes if not self._has_block(block_hash)]
        if not missing_txs and not missing_blocks:
            return
        request_payload: dict[str, list[str]] = {}
        if missing_txs:
            request_payload["transactions"] = missing_txs
        if missing_blocks:
            request_payload["blocks"] = missing_blocks
        await self._send_signed_message(
            websocket,
            peer_id,
            {"type": "getdata", "payload": request_payload},
        )

    async def _handle_getdata_request(
        self,
        websocket: ServerConnection | None,
        peer_id: str,
        payload: dict[str, Any] | None,
    ) -> None:
        if not websocket:
            return
        payload = payload or {}
        for txid in payload.get("transactions") or []:
            tx = self._find_pending_transaction(txid)
            if not tx:
                continue
            await self._send_signed_message(
                websocket,
                peer_id,
                {"type": "transaction", "payload": tx.to_dict()},
            )
        for block_hash in payload.get("blocks") or []:
            block = self.blockchain.get_block_by_hash(block_hash)
            if not block:
                continue
            await self._send_signed_message(
                websocket,
                peer_id,
                {"type": "block", "payload": block.to_dict()},
            )

    async def _handle_checkpoint_request(
        self,
        websocket: ServerConnection | None,
        peer_id: str,
        payload: dict[str, Any] | None,
    ) -> None:
        """
        Serve checkpoint payload metadata/URL to peers requesting partial sync.
        """
        if not websocket:
            return
        payload = payload or {}
        want_payload = bool(payload.get("want_payload"))
        cm = getattr(self.blockchain, "checkpoint_manager", None)
        if not cm or not hasattr(cm, "export_checkpoint_payload"):
            return
        try:
            height = payload.get("height") or getattr(cm, "latest_checkpoint_height", None)
            exported = cm.export_checkpoint_payload(height=height, include_data=want_payload)
            if not exported:
                return
            await self._send_signed_message(
                websocket,
                peer_id,
                {"type": "checkpoint_payload", "payload": exported},
            )
        except (StorageError, NetworkError, ValueError, RuntimeError, AttributeError) as exc:
            logger.debug(
                "Failed to serve checkpoint payload: %s",
                exc,
                extra={
                    "event": "p2p.checkpoint_payload_failed",
                    "peer": peer_id,
                    "error_type": type(exc).__name__,
                },
            )

    def _handle_handshake_message(self, peer_id: str, payload: dict[str, Any] | None) -> None:
        """Handle handshake message from peer."""
        self.peer_features[peer_id] = payload or {}
        self._handshake_received[peer_id] = time.time()
        self._handshake_deadlines.pop(peer_id, None)

        # Extract and store peer's API endpoint for HTTP sync
        if payload and isinstance(payload, dict):
            api_endpoint = payload.get("api_endpoint")
            if api_endpoint:
                with self._peer_lock:
                    self.peer_api_endpoints[peer_id] = api_endpoint
                logger.info(
                    "Stored API endpoint for peer %s: %s",
                    peer_id[:16],
                    api_endpoint,
                    extra={"event": "p2p.peer_api_endpoint_stored", "peer": peer_id}
                )

    def _handle_transaction_message(self, peer_id: str, payload: dict[str, Any] | None) -> bool:
        """Handle transaction message from peer. Returns False if duplicate."""
        dedup_id = self._derive_payload_fingerprint(payload, ("txid", "hash", "id"))
        if self._is_duplicate_message("transaction", dedup_id):
            logger.debug(
                "Duplicate transaction %s dropped from peer %s",
                dedup_id,
                peer_id[:16],
                extra={"event": "p2p.duplicate_transaction", "peer": peer_id, "txid": dedup_id},
            )
            self._log_security_event(peer_id, "duplicate_transaction")
            self.peer_manager.reputation.record_invalid_transaction(peer_id)
            return False
        tx = self.blockchain._transaction_from_dict(payload)
        if self.blockchain.add_transaction(tx):
            self.peer_manager.reputation.record_valid_transaction(peer_id)
        else:
            self.peer_manager.reputation.record_invalid_transaction(peer_id)
        return True

    def _handle_block_message(self, peer_id: str, payload: dict[str, Any] | None) -> bool:
        """Handle block message from peer. Returns False if duplicate."""
        dedup_id = self._derive_payload_fingerprint(
            payload.get("header") if isinstance(payload, dict) else payload,
            ("hash", "block_hash"),
        )
        if self._is_duplicate_message("block", dedup_id):
            logger.debug(
                "Duplicate block %s dropped from peer %s",
                dedup_id,
                peer_id[:16],
                extra={"event": "p2p.duplicate_block", "peer": peer_id, "block_hash": dedup_id},
            )
            self._log_security_event(peer_id, "duplicate_block")
            self.peer_manager.reputation.record_invalid_block(peer_id)
            return False
        block = self.blockchain.deserialize_block(payload)
        if self.blockchain.add_block(block):
            self.peer_manager.reputation.record_valid_block(peer_id)
        else:
            self.peer_manager.reputation.record_invalid_block(peer_id)
        return True

    async def _handle_get_peers_message(
        self, websocket: ServerConnection | None, peer_id: str
    ) -> None:
        """Handle get_peers request from peer."""
        peers = self._http_peers_snapshot()
        bootstrap = getattr(self.peer_manager.discovery, "bootstrap_nodes", []) or []
        peers.extend([seed for seed in bootstrap if seed not in peers])
        await self._send_signed_message(
            websocket,
            peer_id,
            {"type": "peers", "payload": peers},
        )

    async def _send_signed_message(
        self,
        websocket: Any,
        peer_id: str,
        message: dict[str, Any],
    ) -> None:
        """Sign and send a message to a single peer with bandwidth enforcement."""
        try:
            signed_message = self.peer_manager.encryption.create_signed_message(message)
        except (ValueError, RuntimeError) as exc:
            logger.error(
                "Failed to sign message for peer %s: %s - %s",
                peer_id[:16],
                type(exc).__name__,
                str(exc),
                extra={"event": "p2p.sign_failed", "peer": peer_id, "error_message": str(exc)}
            )
            return

        message_size = len(signed_message)
        if not self.bandwidth_limiter_out.consume(peer_id, message_size):
            logger.warning(
                "Peer %s exceeding outgoing bandwidth, disconnecting",
                peer_id[:16],
                extra={"event": "p2p.bandwidth_exceeded_out", "peer": peer_id}
            )
            await websocket.close()
            if peer_id in self.connections:
                self._disconnect_peer(peer_id, self.connections.get(peer_id))
            return
        if self.global_bandwidth_out and not self.global_bandwidth_out.consume("global", message_size):
            logger.warning(
                "Global outbound bandwidth exceeded, closing connection",
                extra={"event": "p2p.global_bandwidth_exceeded_out", "peer": peer_id},
            )
            await websocket.close()
            self._disconnect_peer(peer_id, websocket)
            return

        try:
            # Add newline delimiter to prevent message concatenation
            await websocket.send(signed_message.decode("utf-8") + "\n")
        except (ConnectionClosed, WebSocketException, OSError, RuntimeError) as exc:
            logger.error(
                "Error sending message to peer %s: %s",
                peer_id[:16],
                type(exc).__name__,
                extra={"event": "p2p.send_failed", "peer": peer_id}
            )
            if peer_id in self.connections:
                conn = self.connections.pop(peer_id, None)
                if conn:
                    self.websocket_peer_ids.pop(conn, None)
                self.peer_manager.disconnect_peer(peer_id)
    
    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcasts a message to all connected peers."""
        if not self.connections:
            return

        try:
            signed_message = self.peer_manager.encryption.create_signed_message(message)
        except (ValueError, RuntimeError) as exc:
            logger.error(
                "Failed to sign broadcast message: %s",
                type(exc).__name__,
                extra={"event": "p2p.broadcast_sign_failed"}
            )
            return

        message_size = len(signed_message)
        message_str = signed_message.decode("utf-8")
        if self.global_bandwidth_out and not self.global_bandwidth_out.consume("global", message_size * len(self.connections)):
            logger.warning(
                "Global outbound bandwidth exceeded during broadcast; skipping message",
                extra={"event": "p2p.broadcast_global_bandwidth_exceeded"}
            )
            return
        
        for peer_id, conn in list(self.connections.items()):
            if not self.bandwidth_limiter_out.consume(peer_id, message_size):
                logger.warning(
                    "Peer %s exceeding outgoing bandwidth during broadcast, disconnecting",
                    peer_id[:16],
                    extra={"event": "p2p.broadcast_bandwidth_exceeded", "peer": peer_id}
                )
                await conn.close()
                del self.connections[peer_id]
                self.websocket_peer_ids.pop(conn, None)
                self.peer_manager.disconnect_peer(peer_id)
                continue
            try:
                await conn.send(message_str)
            except (ConnectionClosed, WebSocketException, OSError, RuntimeError) as exc:
                logger.error(
                    "Error broadcasting to peer %s: %s",
                    peer_id[:16],
                    type(exc).__name__,
                    extra={"event": "p2p.broadcast_failed", "peer": peer_id}
                )
                await conn.close()
                del self.connections[peer_id]
                self.websocket_peer_ids.pop(conn, None)
                self.peer_manager.disconnect_peer(peer_id)

    def _http_peers_snapshot(self) -> list[str]:
        with self._peer_lock:
            return list(self.http_peers)

    def _get_peer_api_endpoints(self) -> list[str]:
        """Get list of connected peers' HTTP API endpoints."""
        with self._peer_lock:
            return list(self.peer_api_endpoints.values())

    def _dispatch_async(self, coro: Any) -> None:
        """Schedule an asyncio coroutine on the main event loop."""
        # Try to get the currently running loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop - use stored loop or get the default one
            loop = self._loop
            if loop is None:
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = None

        # Schedule the coroutine as a task
        if loop is not None and loop.is_running():
            # Loop is running - schedule task using call_soon_threadsafe for thread safety
            asyncio.run_coroutine_threadsafe(coro, loop)
            return
        if loop is not None:
            # Loop exists but not running - run coroutine to completion
            try:
                loop.run_until_complete(coro)
                return
            except RuntimeError:
                pass

        # No loop available in this thread - run coroutine to completion
        try:
            asyncio.run(coro)
        except RuntimeError:
            # Fallback if asyncio.run is not allowed in this context
            tmp_loop = asyncio.new_event_loop()
            try:
                tmp_loop.run_until_complete(coro)
            finally:
                tmp_loop.close()

    def _get_checkpoint_metadata(self) -> dict[str, Any] | None:
        """Return highest checkpoint metadata from peers or local store."""
        candidates: list[dict[str, Any]] = []

        # Peer-advertised checkpoints
        for info in self.peer_features.values():
            ckpt = info.get("checkpoint") if isinstance(info, dict) else None
            if isinstance(ckpt, dict) and "height" in ckpt and "block_hash" in ckpt:
                candidates.append({**ckpt, "source": "peer"})

        # Local checkpoint manager
        cm = getattr(self.blockchain, "checkpoint_manager", None)
        if cm:
            try:
                checkpoint = cm.load_latest_checkpoint()
                if not checkpoint:
                    height = getattr(cm, "latest_checkpoint_height", None)
                    if height is not None and hasattr(cm, "load_checkpoint"):
                        checkpoint = cm.load_checkpoint(height)
                if checkpoint:
                    candidates.append(
                        {
                            "height": getattr(checkpoint, "height", None),
                            "block_hash": getattr(checkpoint, "block_hash", None),
                            "timestamp": getattr(checkpoint, "timestamp", None),
                            "source": "local",
                        }
                    )
            except (StorageError, DatabaseError, ValueError, RuntimeError, AttributeError) as e:
                logger.debug(
                    "Failed to load checkpoint for sync status",
                    extra={
                        "height": getattr(cm, "latest_checkpoint_height", None),
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                )

        if not candidates:
            return None
        return max(candidates, key=lambda c: c.get("height", -1))

    def _derive_payload_fingerprint(self, payload: Any, candidate_fields: tuple[str, ...]) -> str | None:
        """Return a stable fingerprint for deduplication."""
        if payload is None:
            return None
        if isinstance(payload, dict):
            for field in candidate_fields:
                value = payload.get(field)
                if value:
                    return str(value)
        try:
            serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        except (TypeError, ValueError):
            serialized = str(payload)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _is_duplicate_message(
        self,
        category: str,
        message_id: str | None,
        now: float | None = None,
    ) -> bool:
        """Track recently seen messages and detect duplicates."""
        if not message_id:
            return False
        cache_set, cache_queue = self._select_dedup_cache(category)
        if cache_set is None or cache_queue is None:
            return False
        current_time = now or time.time()
        self._purge_dedup_cache(cache_queue, cache_set, current_time)
        if message_id in cache_set:
            return True
        cache_set.add(message_id)
        cache_queue.append((message_id, current_time + self._dedup_ttl))
        self._purge_dedup_cache(cache_queue, cache_set, current_time)
        return False

    def _purge_dedup_cache(
        self,
        cache_queue: deque[tuple[str, float]],
        cache_set: set[str],
        now: float,
    ) -> None:
        """Remove expired or excess entries from the dedup cache."""
        while cache_queue and (cache_queue[0][1] <= now or len(cache_set) > self._dedup_max_items):
            message_id, _ = cache_queue.popleft()
            cache_set.discard(message_id)

    def _select_dedup_cache(
        self,
        category: str,
    ) -> tuple[set[str] | None, deque | None]:
        if category == "transaction":
            return self._tx_seen_ids, self._tx_seen_queue
        if category == "block":
            return self._block_seen_ids, self._block_seen_queue
        return None, None

    def _peer_headers(self) -> dict[str, str] | None:
        if not self.peer_api_key:
            return None
        return {"X-API-Key": self.peer_api_key}

    def _announce_inventory(
        self,
        *,
        transactions: list[str] | None = None,
        blocks: list[str] | None = None,
    ) -> None:
        payload: dict[str, list[str]] = {}
        if transactions:
            payload["transactions"] = [txid for txid in transactions if txid]
        if blocks:
            payload["blocks"] = [block_hash for block_hash in blocks if block_hash]
        if not payload:
            return
        message = {"type": "inv", "payload": payload}
        self._dispatch_async(self.broadcast(message))

    def _has_transaction(self, txid: str | None) -> bool:
        if not txid:
            return False
        if txid in getattr(self.blockchain, "seen_txids", set()):
            return True
        pending = getattr(self.blockchain, "pending_transactions", []) or []
        return any(getattr(tx, "txid", None) == txid for tx in pending)

    def _find_pending_transaction(self, txid: str | None):
        if not txid:
            return None
        for tx in getattr(self.blockchain, "pending_transactions", []) or []:
            if getattr(tx, "txid", None) == txid:
                return tx
        return None

    def _has_block(self, block_hash: str | None) -> bool:
        if not block_hash:
            return False
        lookup = getattr(self.blockchain, "get_block_by_hash", None)
        if callable(lookup):
            return lookup(block_hash) is not None
        # Fallback: scan chain if helper missing
        for block in getattr(self.blockchain, "chain", []) or []:
            candidate = getattr(block, "hash", None)
            if candidate == block_hash:
                return True
        return False

    def _normalize_remote_header(self, header_dict: dict[str, Any]) -> dict[str, Any]:
        """Fill missing header fields with safe defaults for sync fallback paths."""
        defaults = {
            "previous_hash": "0" * 64,
            "timestamp": time.time(),
            "merkle_root": "",
            "nonce": 0,
            "difficulty": getattr(self.blockchain, "difficulty", 1),
            "miner_pubkey": None,
            "signature": None,
            "version": getattr(Config, "BLOCK_HEADER_VERSION", 1),
        }
        normalized = defaults.copy()
        normalized.update({k: v for k, v in header_dict.items() if v is not None})
        normalized["index"] = header_dict.get("index", len(self.blockchain.chain))
        if "hash" in header_dict:
            normalized["hash"] = header_dict["hash"]
        return normalized

    async def _handle_quic_payload(self, data: bytes) -> None:
        """Handle incoming QUIC payloads by reusing the websocket message handler."""
        if self.global_bandwidth_in and not self.global_bandwidth_in.consume("global", len(data)):
            logger.warning(
                "Dropping QUIC payload due to global inbound bandwidth cap",
                extra={"event": "p2p.quic_global_bandwidth_exceeded"},
            )
            return
        try:
            await self._handle_message(None, data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to handle QUIC payload: {e}")
        except RuntimeError as e:
            logger.error(f"Runtime error handling QUIC payload: {e}", exc_info=True)

    async def _quic_send_payload(self, host: str, payload: bytes) -> None:
        """Send QUIC payload with bounded timeout and metrics on failure."""
        if self.global_bandwidth_out and not self.global_bandwidth_out.consume("global", len(payload)):
            logger.warning(
                "Skipping QUIC send due to global outbound bandwidth cap",
                extra={"event": "p2p.quic_global_bandwidth_exceeded_out", "peer": host},
            )
            return
        try:
            quic_config = QuicConfiguration(is_client=True, alpn_protocols=["xai-p2p"])
            await quic_client_send_with_timeout(
                host, self.port + 1, payload, quic_config, timeout=self.quic_dial_timeout
            )
        except QuicDialTimeout:
            self._record_quic_timeout(host)
        except (ConnectionError, OSError, RuntimeError, ValueError) as e:
            # QUIC connection error - record and continue
            logger.debug(f"QUIC send failed to {host}: {e}")
            self._record_quic_error(host)

    def broadcast_transaction(self, transaction: "Transaction") -> None:
        """Broadcast a transaction to all connected peers."""
        payload = transaction.to_dict()
        message = {
            "type": "transaction",
            "payload": payload,
        }
        txid = payload.get("txid")
        if txid:
            self._announce_inventory(transactions=[txid])

        # Use peer API endpoints from handshake (HTTP URLs)
        peer_endpoints = self._get_peer_api_endpoints()
        if not peer_endpoints:
            # Fallback to legacy http_peers if no API endpoints available yet
            peer_endpoints = self._http_peers_snapshot()

        for peer_uri in peer_endpoints:
            endpoint = f"{peer_uri.rstrip('/')}/transaction/receive"
            try:
                # Create signed message for the transaction payload
                signed_message_bytes = self.peer_manager.encryption.create_signed_message(payload)

                response = requests.post(
                    endpoint,
                    data=signed_message_bytes,
                    headers={
                        **(self._peer_headers() or {}),
                        "Content-Type": "application/json"
                    },
                    timeout=self._http_timeout,
                )
                if response.status_code >= 400:
                    self.peer_manager.reputation.record_invalid_transaction(peer_uri)
                else:
                    self.peer_manager.reputation.record_valid_transaction(peer_uri)
            except (NetworkError, requests.RequestException, ConnectionError, OSError, TimeoutError, Exception) as e:
                # Network error broadcasting transaction - record reputation penalty
                logger.debug(
                    "Failed to broadcast transaction to %s: %s",
                    peer_uri,
                    e,
                    extra={"error_type": type(e).__name__},
                )
                self.peer_manager.reputation.record_invalid_transaction(peer_uri)
        self._dispatch_async(self.broadcast(message))
        if self.quic_enabled and QUIC_AVAILABLE:
            payload = json.dumps(message).encode("utf-8")
            for peer_uri in self._http_peers_snapshot():
                host = urlparse(peer_uri).hostname
                if not host:
                    continue
                self._dispatch_async(self._quic_send_payload(host, payload))

    def broadcast_block(self, block: "Block") -> None:
        """Broadcast a newly mined block to all connected peers."""
        payload = block.to_dict()
        message = {
            "type": "block",
            "payload": payload,
        }
        block_hash = payload.get("hash") or payload.get("block_hash")
        if block_hash:
            self._announce_inventory(blocks=[block_hash])

        # Use peer API endpoints from handshake (HTTP URLs)
        peer_endpoints = self._get_peer_api_endpoints()
        if not peer_endpoints:
            # Fallback to legacy http_peers if no API endpoints available yet
            peer_endpoints = self._http_peers_snapshot()

        for peer_uri in peer_endpoints:
            endpoint = f"{peer_uri.rstrip('/')}/block/receive"
            try:
                # Create signed message for the block payload
                signed_message_bytes = self.peer_manager.encryption.create_signed_message(message["payload"])

                response = requests.post(
                    endpoint,
                    data=signed_message_bytes,
                    headers={
                        **(self._peer_headers() or {}),
                        "Content-Type": "application/json"
                    },
                    timeout=self._http_timeout,
                )
                if response.status_code == 200:
                    logger.info(
                        "Broadcast block %s to %s",
                        block_hash[:16] if block_hash else "unknown",
                        peer_uri,
                        extra={"event": "p2p.block_broadcast_success"}
                    )
            except (NetworkError, requests.RequestException, ConnectionError, OSError, TimeoutError) as e:
                # Network error broadcasting block - peer may be down, continue to others
                logger.warning(
                    "Failed to broadcast block to %s: %s",
                    peer_uri,
                    e,
                    extra={"error_type": type(e).__name__},
                )
        self._dispatch_async(self.broadcast(message))
        if self.quic_enabled:
            payload = json.dumps(message).encode("utf-8")
            for peer_uri in self._http_peers_snapshot():
                host = urlparse(peer_uri).hostname
                if not host:
                    continue
                self._dispatch_async(self._quic_send_payload(host, payload))

    def broadcast_finality_vote(self, vote_payload: dict[str, Any]) -> None:
        """Broadcast a finality vote to all connected peers via HTTP."""
        # Use peer API endpoints from handshake (HTTP URLs)
        peer_endpoints = self._get_peer_api_endpoints()
        if not peer_endpoints:
            # Fallback to legacy http_peers if no API endpoints available yet
            peer_endpoints = self._http_peers_snapshot()

        for peer_uri in peer_endpoints:
            endpoint = f"{peer_uri.rstrip('/')}/finality/vote"
            try:
                signed_message_bytes = self.peer_manager.encryption.create_signed_message(vote_payload)
                response = requests.post(
                    endpoint,
                    data=signed_message_bytes,
                    headers={
                        **(self._peer_headers() or {}),
                        "Content-Type": "application/json"
                    },
                    timeout=self._http_timeout,
                )
                if response.status_code >= 400:
                    logger.debug(
                        "Finality vote rejected by peer %s: %s",
                        peer_uri,
                        response.text[:200],
                        extra={"event": "p2p.finality_vote_rejected", "status": response.status_code},
                    )
            except (NetworkError, requests.RequestException, ConnectionError, OSError, TimeoutError, Exception) as exc:
                logger.debug(
                    "Failed to broadcast finality vote to %s: %s",
                    peer_uri,
                    exc,
                    extra={"event": "p2p.finality_vote_broadcast_failed", "error_type": type(exc).__name__},
                )

    async def _fetch_peer_chain_summary(self, peer_uri: str) -> dict[str, Any] | None:
        """Return quick height summary for a peer without downloading full chain.

        Async implementation using httpx for non-blocking HTTP requests.
        """
        endpoint = f"{peer_uri.rstrip('/')}/blocks"
        try:
            async with httpx.AsyncClient(timeout=self._http_timeout) as client:
                response = await client.get(
                    endpoint,
                    params={"limit": 1, "offset": 0},
                )
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            logger.debug(
                "Failed to contact peer %s for summary: %s",
                peer_uri,
                exc,
                extra={"event": "p2p.parallel_sync_summary_failed", "peer": peer_uri},
            )
            return None

        if response.status_code != 200:
            return None

        try:
            summary = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning(
                "Invalid summary payload from %s: %s",
                peer_uri,
                exc,
                extra={"event": "p2p.parallel_sync_summary_invalid", "peer": peer_uri},
            )
            return None

        total = summary.get("total")
        try:
            height = int(total)
        except (TypeError, ValueError):
            return None

        latest_block = None
        blocks_snapshot = summary.get("blocks")
        if isinstance(blocks_snapshot, list) and blocks_snapshot:
            latest_block = blocks_snapshot[0]

        return {
            "peer": peer_uri,
            "total": max(0, height),
            "latest_block": latest_block,
        }

    async def _collect_peer_chain_summaries(self, peers: list[str]) -> list[dict[str, Any]]:
        """Collect summaries for every peer we are connected to.

        Async implementation using asyncio.gather() for parallel fetching.
        """
        if not peers:
            return []

        # Fetch all peer summaries in parallel
        tasks = [self._fetch_peer_chain_summary(peer_uri) for peer_uri in peers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        summaries: list[dict[str, Any]] = []
        for result in results:
            if isinstance(result, dict):
                summaries.append(result)
            elif isinstance(result, Exception):
                logger.debug(
                    "Exception during peer summary fetch: %s",
                    result,
                    extra={"event": "p2p.parallel_summary_exception"},
                )
        return summaries

    def _should_parallel_sync(self, summaries: list[dict[str, Any]], local_height: int) -> bool:
        """Decide if we should attempt chunked parallel sync based on peer heights."""
        if not self.parallel_chunk_sync_enabled or not summaries:
            return False
        for summary in summaries:
            remote_total = summary.get("total", 0)
            if remote_total > self.parallel_sync_page_limit:
                return True
            if remote_total - local_height > self.parallel_sync_chunk_size:
                return True
        return False

    def _parallel_chunk_sync(
        self,
        peer_summaries: list[dict[str, Any]],
        local_height: int,
    ) -> bool:
        """
        Parallel block download and chain replacement.
        
        PRODUCTION FIX: Uses replace_chain() for initial sync instead of 
        sequential add_block() to handle genesis block differences and
        enable proper chain synchronization from scratch.
        """
        if not peer_summaries:
            return False
            
        max_peer_height = max(s.get("total", 0) for s in peer_summaries)
        if max_peer_height <= local_height:
            return False

        # Calculate chunk ranges
        chunk_size = self.parallel_sync_chunk_size or 1
        chunk_ranges: list[tuple[int, int]] = []
        cursor = local_height
        while cursor < max_peer_height:
            chunk_end = min(cursor + chunk_size, max_peer_height)
            chunk_ranges.append((cursor, chunk_end))
            cursor = chunk_end

        if not chunk_ranges:
            return False

        # Download chunks in parallel
        worker_count = min(len(chunk_ranges), self.parallel_sync_workers)
        chunk_results: dict[tuple[int, int], list[dict[str, Any]]] = {}
        
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures: dict[Future, tuple[int, int]] = {
                executor.submit(
                    self._download_chunk_with_failover,
                    chunk_num,
                    chunk_range,
                    peer_summaries,
                ): chunk_range
                for chunk_num, chunk_range in enumerate(chunk_ranges)
            }
            for future in as_completed(futures):
                chunk_range = futures[future]
                try:
                    chunk_blocks = future.result()
                except (NetworkError, ValidationError, ValueError, RuntimeError) as exc:
                    logger.warning(
                        "Parallel chunk %s failed: %s",
                        chunk_range,
                        exc,
                        extra={
                            "event": "p2p.parallel_sync_chunk_failed",
                            "chunk": chunk_range,
                            "error_type": type(exc).__name__,
                        },
                    )
                    return False
                if not chunk_blocks:
                    logger.debug(
                        "Parallel chunk missing blocks",
                        extra={"event": "p2p.parallel_sync_chunk_missing", "chunk": chunk_range},
                    )
                    return False
                chunk_results[chunk_range] = chunk_blocks

        # Sort chunks and deserialize all blocks
        ordered_ranges = sorted(chunk_results.keys(), key=lambda rng: rng[0])
        deserialized_blocks: list[Any] = []
        expected_index = local_height
        
        for chunk_range in ordered_ranges:
            chunk_blocks = chunk_results[chunk_range]
            chunk_blocks.sort(key=lambda payload: self._extract_block_index(payload) or -1)
            for block_payload in chunk_blocks:
                block_index = self._extract_block_index(block_payload)
                if block_index is None:
                    logger.debug(
                        "Chunk block missing index, rejecting parallel sync",
                        extra={"event": "p2p.parallel_sync_chunk_invalid"},
                    )
                    return False
                if block_index < expected_index:
                    continue
                if block_index != expected_index:
                    logger.warning(
                        "Chunk sequence gap detected during parallel sync",
                        extra={
                            "event": "p2p.parallel_sync_gap",
                            "expected_index": expected_index,
                            "received_index": block_index,
                        },
                    )
                    return False
                block_obj = self._deserialize_block_payload(block_payload)
                if block_obj is None:
                    logger.debug(
                        "Failed to deserialize chunk block %s",
                        block_index,
                        extra={"event": "p2p.parallel_sync_deserialize_failed"},
                    )
                    return False
                deserialized_blocks.append(block_obj)
                expected_index += 1

        if not deserialized_blocks:
            return False

        # PRODUCTION FIX: For initial sync (local_height <= 1), use replace_chain()
        network_mode = os.getenv("XAI_NETWORK", "testnet").lower()
        is_initial_sync = local_height <= 1
        
        if is_initial_sync:
            logger.info(
                "Initial sync detected (height=%d), using replace_chain for %d blocks",
                local_height,
                len(deserialized_blocks),
                extra={
                    "event": "p2p.parallel_sync_initial",
                    "local_height": local_height,
                    "blocks_to_sync": len(deserialized_blocks),
                }
            )
            # For initial sync, fetch full chain and use replace_chain
            try:
                best_peer = max(peer_summaries, key=lambda s: s.get("total", 0))
                full_chain = self._fetch_full_chain_for_replace(best_peer["peer"], max_peer_height)
                if full_chain and self.blockchain.replace_chain(full_chain):
                    logger.info(
                        "Initial sync completed via replace_chain, new height=%d",
                        len(full_chain),
                        extra={
                            "event": "p2p.parallel_sync_initial_success",
                            "new_height": len(full_chain),
                        }
                    )
                    return True
                else:
                    logger.warning(
                        "replace_chain failed for initial sync",
                        extra={"event": "p2p.parallel_sync_replace_failed"}
                    )
            except (NetworkError, ValidationError, ValueError, RuntimeError) as exc:
                logger.warning(
                    "Initial sync replace_chain error: %s",
                    exc,
                    extra={
                        "event": "p2p.parallel_sync_initial_error",
                        "error_type": type(exc).__name__,
                    }
                )

        # Standard sequential add for incremental sync
        for block in deserialized_blocks:
            if not self.blockchain.add_block(block):
                block_index = getattr(getattr(block, "header", None), "index", None)
                logger.warning(
                    "Parallel sync rejected block at index %s",
                    block_index,
                    extra={
                        "event": "p2p.parallel_sync_block_rejected",
                        "block_index": block_index,
                    },
                )
                # In testnet mode, continue with remaining blocks
                if network_mode == "testnet":
                    logger.info(
                        "Testnet mode: continuing sync despite rejected block",
                        extra={"event": "p2p.parallel_sync_testnet_continue"}
                    )
                    continue
                return False

        return True

    def _fetch_full_chain_for_replace(
        self,
        peer_uri: str,
        target_height: int,
    ) -> list[Any] | None:
        """
        Fetch the full chain from a peer for replace_chain operation.
        Used during initial sync when local node has only genesis.
        """
        endpoint = f"{peer_uri.rstrip('/')}/blocks"
        all_blocks: list[dict[str, Any]] = []
        page_size = 200
        
        for offset in range(0, target_height, page_size):
            try:
                response = requests.get(
                    endpoint,
                    params={
                        "limit": min(page_size, target_height - offset),
                        "offset": offset,
                    },
                    timeout=self._http_timeout,
                )
                if response.status_code != 200:
                    logger.warning(
                        "Full chain fetch failed at offset %d: status %d",
                        offset,
                        response.status_code,
                        extra={"event": "p2p.full_chain_fetch_failed"}
                    )
                    return None
                    
                payload = response.json()
                blocks = payload.get("blocks", [])
                if not blocks:
                    break
                all_blocks.extend(blocks)
                
            except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
                logger.warning(
                    "Full chain fetch error at offset %d: %s",
                    offset,
                    exc,
                    extra={
                        "event": "p2p.full_chain_fetch_error",
                        "error_type": type(exc).__name__,
                    }
                )
                return None

        if not all_blocks:
            return None

        all_blocks.sort(key=lambda b: self._extract_block_index(b) or -1)
        deserialized: list[Any] = []
        
        for block_data in all_blocks:
            block_obj = self._deserialize_block_payload(block_data)
            if block_obj is None:
                continue
            deserialized.append(block_obj)

        logger.info(
            "Fetched %d blocks for replace_chain",
            len(deserialized),
            extra={
                "event": "p2p.full_chain_fetched",
                "block_count": len(deserialized),
            }
        )
        
        return deserialized if deserialized else None


    def _download_chunk_with_failover(
        self,
        chunk_number: int,
        chunk_range: tuple[int, int],
        peer_summaries: list[dict[str, Any]],
    ) -> list[dict[str, Any]] | None:
        """Download a specific chunk, rotating peers on failure."""
        if chunk_range[0] >= chunk_range[1]:
            return None
        if not peer_summaries:
            return None
        rotated = peer_summaries[chunk_number % len(peer_summaries) :] + peer_summaries[: chunk_number % len(peer_summaries)]
        for attempt in range(self.parallel_sync_retry_limit):
            ordering = rotated[attempt % len(rotated) :] + rotated[: attempt % len(rotated)]
            for summary in ordering:
                peer_total = summary.get("total", 0)
                if peer_total < chunk_range[1]:
                    continue
                chunk = self._download_block_chunk(
                    summary["peer"],
                    chunk_range[0],
                    chunk_range[1],
                    peer_total,
                )
                if chunk:
                    return chunk
        return None

    def _download_block_chunk(
        self,
        peer_uri: str,
        start_height: int,
        end_height: int,
        remote_total: int,
    ) -> list[dict[str, Any]] | None:
        """Fetch a contiguous range of blocks from a peer."""
        if start_height >= end_height:
            return None
        end_exclusive = min(end_height, remote_total)
        if start_height >= end_exclusive:
            return None
        limit = min(self.parallel_sync_page_limit, end_exclusive - start_height)
        offset = max(remote_total - end_exclusive, 0)
        endpoint = f"{peer_uri.rstrip('/')}/blocks"
        try:
            response = requests.get(
                endpoint,
                params={"limit": limit, "offset": offset},
                timeout=self._http_timeout,
            )
        except requests.RequestException as exc:
            logger.debug(
                "Chunk download error from %s: %s",
                peer_uri,
                exc,
                extra={"event": "p2p.parallel_sync_chunk_download_failed", "peer": peer_uri},
            )
            return None
        if response.status_code != 200:
            return None
        try:
            payload = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning(
                "Chunk payload JSON error from %s: %s",
                peer_uri,
                exc,
                extra={"event": "p2p.parallel_sync_chunk_json_error", "peer": peer_uri},
            )
            return None
        blocks = payload.get("blocks")
        if not isinstance(blocks, list):
            return None
        filtered: list[dict[str, Any]] = []
        for entry in blocks:
            index = self._extract_block_index(entry)
            if index is None:
                continue
            if index < start_height or index >= end_exclusive:
                continue
            filtered.append(entry)
        filtered.sort(key=lambda payload: self._extract_block_index(payload) or -1)
        expected_count = end_exclusive - start_height
        if len(filtered) != expected_count:
            logger.debug(
                "Chunk download from %s incomplete (expected %d, got %d)",
                peer_uri,
                expected_count,
                len(filtered),
                extra={"event": "p2p.parallel_sync_chunk_incomplete", "peer": peer_uri},
            )
            return None
        return filtered

    @staticmethod
    def _extract_block_index(block_payload: Any) -> int | None:
        """Return block index from a serialized block payload."""
        if not isinstance(block_payload, dict):
            return None
        header = block_payload.get("header")
        if isinstance(header, dict):
            try:
                return int(header.get("index"))
            except (TypeError, ValueError):
                return None
        try:
            return int(block_payload.get("index"))
        except (TypeError, ValueError):
            return None

    def _deserialize_block_payload(self, block_payload: dict[str, Any]) -> Any | None:
        """Deserialize a block payload using blockchain helper."""
        deserializer = getattr(self.blockchain, "deserialize_block", None)
        if not callable(deserializer):
            try:
                from xai.core.blockchain import Blockchain as BlockchainClass

                deserializer = BlockchainClass.deserialize_block
            except ImportError:
                deserializer = None
        if not callable(deserializer):
            return None
        try:
            return deserializer(block_payload)
        except (ValidationError, ValueError, TypeError, KeyError, RuntimeError) as exc:
            logger.debug(
                "Block deserialization failed: %s",
                exc,
                extra={
                    "event": "p2p.parallel_sync_deserialize_exception",
                    "error_type": type(exc).__name__,
                },
            )
            return None

    async def _http_sync(self) -> bool:
        """HTTP-based synchronization for manually registered peers.

        Async implementation using httpx and asyncio.gather() for parallel downloads.
        """
        # Get API endpoints from connected peers (via handshake)
        peers = self._get_peer_api_endpoints()
        if not peers:
            # Fallback to legacy http_peers if no API endpoints available yet
            peers = self._http_peers_snapshot()
        if not peers:
            return False

        summaries = await self._collect_peer_chain_summaries(peers)
        if not summaries:
            return False

        local_height = len(getattr(self.blockchain, "chain", []))
        ahead_summaries = [summary for summary in summaries if summary.get("total", 0) > local_height]
        if not ahead_summaries:
            return False

        sequential_candidates = list(ahead_summaries)
        if self._should_parallel_sync(ahead_summaries, local_height):
            try:
                if self._parallel_chunk_sync(ahead_summaries, local_height):
                    return True
            except (NetworkError, ValidationError, ValueError, RuntimeError) as exc:
                logger.warning(
                    "Parallel sync encountered error: %s; falling back to sequential sync",
                    exc,
                    extra={
                        "event": "p2p.parallel_sync_unhandled",
                        "error_type": type(exc).__name__,
                    },
                )
            sequential_candidates = [summary for summary in ahead_summaries if summary.get("total", 0) <= self.parallel_sync_page_limit]
            if not sequential_candidates:
                return False

        # Use asyncio.gather() for parallel downloads (replaces ThreadPoolExecutor)
        download_tasks = [
            self._download_remote_blocks(summary["peer"], summary)
            for summary in sequential_candidates
        ]
        results = await asyncio.gather(*download_tasks, return_exceptions=True)

        # Process results and apply first successful chain
        for i, result in enumerate(results):
            peer_uri = sequential_candidates[i]["peer"]
            if isinstance(result, Exception):
                logger.debug(
                    "Parallel sync failed for %s: %s",
                    peer_uri,
                    result,
                    extra={
                        "event": "p2p.parallel_sync_download_failed",
                        "error_type": type(result).__name__,
                    },
                )
                continue

            if not result:
                continue

            if self._apply_remote_chain(peer_uri, result):
                return True
        return False

    async def _download_remote_blocks(
        self,
        peer_uri: str,
        summary: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]] | None:
        """Download remote blocks snapshot from peer, returning None if not ahead.

        Async implementation using httpx for non-blocking HTTP requests.
        """
        base_endpoint = f"{peer_uri.rstrip('/')}/blocks"
        if summary is None:
            summary = await self._fetch_peer_chain_summary(peer_uri)
            if summary is None:
                return None
        try:
            remote_total = int(summary.get("total", 0))
        except (TypeError, ValueError):
            return None
        if remote_total > self.parallel_sync_page_limit:
            return None
        local_height = len(getattr(self.blockchain, "chain", []))
        if remote_total <= local_height:
            return None

        try:
            async with httpx.AsyncClient(timeout=self._http_timeout) as client:
                response_full = await client.get(
                    base_endpoint,
                    params={"limit": remote_total, "offset": 0},
                )
        except (httpx.RequestError, httpx.TimeoutException) as exc:
            logger.debug(
                "Failed to fetch full chain from %s: %s",
                peer_uri,
                exc,
                extra={"event": "p2p.parallel_sync_full_fetch_failed"},
            )
            return None

        if response_full.status_code != 200:
            return None

        try:
            remote_blocks = response_full.json().get("blocks") or []
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning(f"Invalid full chain payload from peer {peer_uri}: {exc}")
            return None

        if not isinstance(remote_blocks, list):
            return None
        return remote_blocks

    def _apply_remote_chain(self, peer_uri: str, remote_blocks: list[dict[str, Any]]) -> bool:
        """Normalize remote chain and attempt to replace local state."""
        logger.info(
            "Applying remote chain from peer",
            extra={
                "event": "p2p.apply_remote_chain_start",
                "peer_uri": peer_uri,
                "block_count": len(remote_blocks) if remote_blocks else 0,
            }
        )
        
        # PRODUCTION FIX: Sort blocks by index (blocks may arrive in reverse order)
        def get_block_index(block_data: dict) -> int:
            if isinstance(block_data, dict):
                # Check header.index first, then top-level index
                header = block_data.get("header")
                if header and isinstance(header, dict):
                    return header.get("index", -1)
                return block_data.get("index", -1)
            return -1
        
        sorted_blocks = sorted(remote_blocks, key=get_block_index)
        logger.debug(
            "Sorted blocks for apply_remote_chain",
            extra={
                "event": "p2p.apply_remote_chain_sorted",
                "first_index": get_block_index(sorted_blocks[0]) if sorted_blocks else None,
                "last_index": get_block_index(sorted_blocks[-1]) if sorted_blocks else None,
            }
        )
        
        new_chain_blocks: list[Block] = []
        valid_chain = True
        for block_data in sorted_blocks:
            if not isinstance(block_data, dict):
                valid_chain = False
                break
            header_dict = block_data.get("header") or block_data
            if not header_dict:
                valid_chain = False
                break
            try:
                block = self.blockchain.deserialize_block(block_data)
                if "hash" in header_dict:
                    block.header.hash = header_dict["hash"]
                new_chain_blocks.append(block)
            except (KeyError, TypeError, ValueError) as exc:
                logger.debug(f"Invalid block header in chain from {peer_uri}: {exc}")
                valid_chain = False
                break

        if valid_chain and new_chain_blocks:
            logger.info(
                "Attempting replace_chain",
                extra={
                    "event": "p2p.replace_chain_attempt",
                    "chain_length": len(new_chain_blocks),
                }
            )
            if self.blockchain.replace_chain(new_chain_blocks):
                logger.info(
                    "replace_chain succeeded",
                    extra={"event": "p2p.replace_chain_success", "new_length": len(new_chain_blocks)}
                )
                return True
            else:
                logger.warning(
                    "replace_chain failed",
                    extra={"event": "p2p.replace_chain_failed", "chain_length": len(new_chain_blocks)}
                )
        else:
            logger.warning(
                "Chain not valid for replace",
                extra={
                    "event": "p2p.chain_invalid",
                    "valid_chain": valid_chain,
                    "blocks_deserialized": len(new_chain_blocks),
                }
            )
            deserializer = getattr(self.blockchain, "deserialize_chain", None)
            if callable(deserializer):
                try:
                    deserialized = deserializer(remote_blocks)
                    if deserialized and self.blockchain.replace_chain(deserialized):
                        return True
                except (ValidationError, ValueError, TypeError, KeyError, RuntimeError) as exc:
                    logger.debug(
                        "deserialize_chain failed for peer %s: %s",
                        peer_uri,
                        exc,
                        extra={"error_type": type(exc).__name__},
                    )
        return False

    async def _ws_sync(self) -> bool:
        """WebSocket-based synchronization using connected peers."""
        self.received_chains = []
        await self.broadcast({"type": "get_chain"})
        await asyncio.sleep(5)  # Wait for 5 seconds to receive chains from peers

        if not self.received_chains:
            return False

        longest_chain = None
        max_length = len(self.blockchain.chain)

        for chain_data in self.received_chains:
            chain = self.blockchain.from_dict(chain_data)
            if len(chain.chain) > max_length and self.blockchain.is_chain_valid(chain.chain):
                max_length = len(chain.chain)
                longest_chain = chain

        if longest_chain:
            self.blockchain.chain = longest_chain.chain
            self.blockchain.pending_transactions = longest_chain.pending_transactions
            new_diff = getattr(longest_chain, "difficulty", None)
            if isinstance(new_diff, (int, float)) and new_diff > 0:
                self.blockchain.difficulty = new_diff
            return True
        return False

    async def sync_with_network(self, force_partial: bool = False) -> bool:
        """Synchronize blockchain with peers (checkpoint/HTTP/WebSocket).

        Async implementation - no longer needs run_in_executor workaround.
        """
        partial_applied = self._attempt_partial_sync(force=force_partial)
        if await self._http_sync():
            return True
        ws_synced = await self._ws_sync()
        return partial_applied or ws_synced
