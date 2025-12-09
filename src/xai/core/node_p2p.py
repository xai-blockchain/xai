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
import os
import threading
import time
from urllib.parse import urlparse
from collections import defaultdict, deque
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException
from websockets.server import WebSocketServerProtocol
import json
import hashlib
import logging
from typing import TYPE_CHECKING, Set, Optional, Dict, Any, Union, Tuple

logger = logging.getLogger(__name__)

try:
    import aioquic  # type: ignore
    from xai.core.p2p_quic import (  # type: ignore
        QUICServer,
        QuicDialTimeout,
        QuicConfiguration,
        quic_client_send_with_timeout,
    )
    QUIC_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    # QUIC dependencies not installed - disable QUIC support
    QUIC_AVAILABLE = False
    QuicDialTimeout = ConnectionError  # type: ignore[assignment]
    logger.debug(f"QUIC support disabled: {e}")

import requests
from xai.network.peer_manager import PeerManager
from xai.core.block_header import BlockHeader
from xai.core.p2p_security import MessageRateLimiter, BandwidthLimiter, HEADER_VERSION, P2PSecurityConfig
from xai.core.security_validation import SecurityEventRouter
from xai.core.config import Config

if TYPE_CHECKING:
    from xai.core.blockchain import Blockchain, Transaction, Block
    from xai.core.node_consensus import ConsensusManager


class P2PNetworkManager:
    """
    Manages peer-to-peer networking for a blockchain node using WebSockets.
    """

    def __init__(
        self,
        blockchain: Blockchain,
        peer_manager: Optional[PeerManager] = None,
        consensus_manager: Optional["ConsensusManager"] = None,
        host: str = "0.0.0.0",
        port: int = 8765,
        max_connections: int = 50,
        max_bandwidth_in: int = 1024 * 1024, # 1 MB/s
        max_bandwidth_out: int = 1024 * 1024, # 1 MB/s
        peer_api_key: Optional[str] = None,
    ) -> None:
        self.blockchain = blockchain
        storage_ref = getattr(self.blockchain, "storage", None)
        data_dir_candidate = getattr(storage_ref, "data_dir", "data")
        data_dir = data_dir_candidate if isinstance(data_dir_candidate, str) else "data"
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
        self.quic_enabled = bool(getattr(Config, "P2P_ENABLE_QUIC", False) and QUIC_AVAILABLE)
        self.quic_dial_timeout = float(getattr(Config, "P2P_QUIC_DIAL_TIMEOUT", 1.0))
        self.server: Optional[websockets.WebSocketServer] = None
        self.connections: Dict[str, Any] = {}
        self.websocket_peer_ids: Dict[Any, str] = {}
        self.http_peers: Set[str] = set()
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
        self._quic_server: Optional[QUICServer] = None
        self._dedup_max_items = max(100, int(getattr(Config, "P2P_DEDUP_MAX_ITEMS", 5000)))
        self._dedup_ttl = max(1.0, float(getattr(Config, "P2P_DEDUP_TTL_SECONDS", 900.0)))
        self._tx_seen_ids: Set[str] = set()
        self._tx_seen_queue: deque[Tuple[str, float]] = deque()
        self._block_seen_ids: Set[str] = set()
        self._block_seen_queue: deque[Tuple[str, float]] = deque()
        self.idle_timeout_seconds = max(60, int(getattr(Config, "P2P_CONNECTION_IDLE_TIMEOUT_SECONDS", 900)))
        self._connection_last_seen: Dict[str, float] = {}
        self.peer_api_key = peer_api_key
        self._http_timeout = getattr(Config, "P2P_HTTP_TIMEOUT_SECONDS", 2)
        self._reset_window_seconds = int(getattr(Config, "P2P_RESET_STORM_WINDOW_SECONDS", 300))
        self._reset_threshold = max(1, int(getattr(Config, "P2P_RESET_STORM_THRESHOLD", 5)))
        self._reset_events: Dict[str, deque[float]] = defaultdict(deque)
        self.peer_features: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _normalize_peer_uri(peer_uri: str) -> str:
        parsed = urlparse(peer_uri if "://" in peer_uri else f"http://{peer_uri}")
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid peer URI: {peer_uri}")
        return f"{parsed.scheme}://{parsed.netloc}"

    def _record_quic_error(self, host: Optional[str] = None) -> None:
        """Increment QUIC error counter and emit a security event if configured."""
        try:
            from xai.core.monitoring import MetricsCollector

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

    def _record_quic_timeout(self, host: Optional[str] = None) -> None:
        """Increment QUIC timeout counter, track it as an error, and emit a security event."""
        try:
            from xai.core.monitoring import MetricsCollector

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
        """Return count of known peers (HTTP/WebSocket)."""
        with self._peer_lock:
            return len(self.http_peers)

    def get_peers(self) -> Set[str]:
        with self._peer_lock:
            return set(self.http_peers)

    async def start(self) -> None:
        """Starts the P2P network manager."""
        ssl_context = self.peer_manager.encryption.create_ssl_context(
            is_server=True,
            require_client_cert=self.peer_manager.require_client_cert,
            ca_bundle=self.peer_manager.ca_bundle_path,
        )
        self.server = await websockets.serve(
            self._handler, self.host, self.port, ssl=ssl_context
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
        asyncio.create_task(self._broadcast_handshake_periodically())

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
        handshake_payload = {
            "type": "handshake",
            "payload": {
                "version": getattr(P2PSecurityConfig, "PROTOCOL_VERSION", "1"),
                "features": list(getattr(P2PSecurityConfig, "SUPPORTED_FEATURES", set())),
                "node_id": self.peer_manager.encryption._node_identity_fingerprint(),  # noqa: SLF001
                "height": len(self.blockchain.chain),
            },
        }
        await self._send_signed_message(websocket, peer_id, handshake_payload)

    async def _handler(self, websocket: Any, path: str) -> None:
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
        self._connection_last_seen[peer_id] = time.time()
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
            if peer_id in self.connections:
                conn = self.connections.pop(peer_id, None)
                if conn:
                    self.websocket_peer_ids.pop(conn, None)
                self._connection_last_seen.pop(peer_id, None)
                self.peer_manager.disconnect_peer(peer_id)
            logger.info(
                "Peer disconnected: %s",
                remote_ip,
                extra={"event": "p2p.peer_disconnected", "peer": peer_id}
            )

    def _record_connection_reset_event(self, peer_id: str, *, reason: Optional[str] = None, now: Optional[float] = None) -> None:
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
        peers_to_connect = self.peer_manager.discovery.get_random_peers()
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
                websocket = await websockets.connect(peer_uri, ssl=ssl_context)
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
                self._connection_last_seen[peer_id] = time.time()
                logger.info(
                    "Connected to peer: %s",
                    peer_uri,
                    extra={"event": "p2p.outbound_connected", "peer": peer_uri}
                )
                await self._send_handshake(websocket, peer_id)
                return
            except (WebSocketException, OSError, ConnectionError, asyncio.TimeoutError, ValueError) as e:
                logger.debug(
                    "Failed to connect to peer %s on attempt %d/%d: %s",
                    peer_uri,
                    attempt + 1,
                    max_retries,
                    type(e).__name__
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

    async def _broadcast_handshake_periodically(self) -> None:
        """Re-announce capabilities/version periodically to connected peers."""
        interval = int(getattr(Config, "P2P_HANDSHAKE_INTERVAL_SECONDS", 900))
        while True:
            await asyncio.sleep(interval)
            for peer_id, conn in list(self.connections.items()):
                try:
                    await self._send_handshake(conn, peer_id)
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.debug(
                        "Failed to send periodic handshake to %s: %s",
                        peer_id[:16],
                        exc,
                        extra={"event": "p2p.handshake_send_failed", "peer": peer_id},
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
            except Exception as exc:
                logger.debug(
                    "Error closing idle connection for %s: %s",
                    peer_id[:16],
                    exc,
                    extra={"event": "p2p.idle_disconnect_error", "peer": peer_id},
                )
            self.connections.pop(peer_id, None)
            self.websocket_peer_ids.pop(conn, None)
            self._connection_last_seen.pop(peer_id, None)
            self.peer_manager.disconnect_peer(peer_id)
            self._emit_security_event(
                "p2p.idle_disconnect",
                severity="INFO",
                payload={"peer": peer_id, "idle_seconds": int(idle_duration)},
            )

    def _disconnect_peer(self, peer_id: str, conn: Optional[Any]) -> None:
        """Centralized cleanup for peer disconnections without duplicating dict removals."""
        if peer_id in self.connections:
            self.connections.pop(peer_id, None)
        if conn:
            self.websocket_peer_ids.pop(conn, None)
        self._connection_last_seen.pop(peer_id, None)
        try:
            self.peer_manager.disconnect_peer(peer_id)
        except Exception as exc:
            logger.debug(
                "Error disconnecting peer %s: %s",
                peer_id[:16],
                exc,
                extra={"event": "p2p.disconnect_cleanup_failed", "peer": peer_id},
            )

    def _emit_security_event(
        self,
        event_type: str,
        severity: str = "WARNING",
        payload: Optional[Dict[str, Any]] = None,
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
                from xai.core.monitoring import MetricsCollector
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
        
    async def _handle_message(self, websocket: Optional[WebSocketServerProtocol], message: Union[str, bytes]) -> None:
        """Handles incoming messages from peers."""
        remote_addr = getattr(websocket, "remote_address", ("<quic>", 0))
        fallback_peer = remote_addr[0] if isinstance(remote_addr, (tuple, list)) and remote_addr else str(remote_addr)
        peer_id = self.websocket_peer_ids.get(websocket, fallback_peer)
        raw_bytes = message if isinstance(message, (bytes, bytearray)) else message.encode("utf-8")
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
            if peer_id in self.connections:
                conn = self.connections.pop(peer_id, None)
                if conn:
                    self.websocket_peer_ids.pop(conn, None)
                self._connection_last_seen.pop(peer_id, None)
                self.peer_manager.disconnect_peer(peer_id)
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
            # Verify message signature
            verified_message = self.peer_manager.encryption.verify_signed_message(raw_bytes)
            if not verified_message:
                self._log_security_event(peer_id, "invalid_or_stale_signature")
                self._emit_security_event(
                    event_type="p2p.invalid_signature",
                    severity="WARNING",
                    payload={"peer": peer_id},
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

            if message_type == "handshake":
                self.peer_features[peer_id] = payload or {}
                return
            if message_type == "transaction":
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
                    return
                tx = self.blockchain._transaction_from_dict(payload)
                if self.blockchain.add_transaction(tx):
                    self.peer_manager.reputation.record_valid_transaction(peer_id)
                else:
                    self.peer_manager.reputation.record_invalid_transaction(peer_id)
            elif message_type == "block":
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
                    return
                block = self.blockchain.deserialize_block(payload)
                if self.blockchain.add_block(block):
                    self.peer_manager.reputation.record_valid_block(peer_id)
                else:
                    self.peer_manager.reputation.record_invalid_block(peer_id)
            elif message_type == "get_chain":
                await self._send_signed_message(
                    websocket,
                    peer_id,
                    {"type": "chain", "payload": self.blockchain.to_dict()},
                )
            elif message_type == "chain":
                self.received_chains.append(payload)
            elif message_type == "get_peers":
                peers = list(self.peer_manager.connected_peers.keys())
                await self._send_signed_message(
                    websocket,
                    peer_id,
                    {"type": "peers", "payload": peers},
                )
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
            logger.warning(
                "Invalid JSON received from peer %s",
                peer_id[:16],
                extra={"event": "p2p.invalid_json", "peer": peer_id}
            )
            self.peer_manager.reputation.record_invalid_transaction(peer_id)
        except (ValueError, TypeError, AttributeError, RuntimeError, KeyError) as e:
            logger.error(
                "Error handling message from peer %s: %s",
                peer_id[:16],
                type(e).__name__,
                extra={"event": "p2p.message_handling_error", "peer": peer_id}
            )
            self.peer_manager.reputation.record_invalid_transaction(peer_id)

    async def _handle_inventory_announcement(
        self,
        websocket: Optional[WebSocketServerProtocol],
        peer_id: str,
        payload: Optional[Dict[str, Any]],
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
        request_payload: Dict[str, List[str]] = {}
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
        websocket: Optional[WebSocketServerProtocol],
        peer_id: str,
        payload: Optional[Dict[str, Any]],
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

    async def _send_signed_message(
        self,
        websocket: Any,
        peer_id: str,
        message: Dict[str, Any],
    ) -> None:
        """Sign and send a message to a single peer with bandwidth enforcement."""
        try:
            signed_message = self.peer_manager.encryption.create_signed_message(message)
        except (ValueError, RuntimeError) as exc:
            logger.error(
                "Failed to sign message for peer %s: %s",
                peer_id[:16],
                type(exc).__name__,
                extra={"event": "p2p.sign_failed", "peer": peer_id}
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
            await websocket.send(signed_message.decode("utf-8"))
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
    
    async def broadcast(self, message: Dict[str, Any]) -> None:
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

    def _dispatch_async(self, coro: Any) -> None:
        """Run or schedule an asyncio coroutine even when no loop is running."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            asyncio.run(coro)

    def _get_checkpoint_metadata(self) -> Optional[Dict[str, Any]]:
        """Return highest checkpoint metadata from peers or local store."""
        candidates: list[Dict[str, Any]] = []

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
            except Exception as e:
                logger.debug(
                    "Failed to load checkpoint for sync status",
                    height=getattr(cm, "latest_checkpoint_height", None),
                    error=str(e)
                )

        if not candidates:
            return None
        return max(candidates, key=lambda c: c.get("height", -1))

    def _derive_payload_fingerprint(self, payload: Any, candidate_fields: Tuple[str, ...]) -> Optional[str]:
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
        message_id: Optional[str],
        now: Optional[float] = None,
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
        cache_queue: deque[Tuple[str, float]],
        cache_set: Set[str],
        now: float,
    ) -> None:
        """Remove expired or excess entries from the dedup cache."""
        while cache_queue and (cache_queue[0][1] <= now or len(cache_set) > self._dedup_max_items):
            message_id, _ = cache_queue.popleft()
            cache_set.discard(message_id)

    def _select_dedup_cache(
        self,
        category: str,
    ) -> Tuple[Optional[Set[str]], Optional[deque]]:
        if category == "transaction":
            return self._tx_seen_ids, self._tx_seen_queue
        if category == "block":
            return self._block_seen_ids, self._block_seen_queue
        return None, None

    def _peer_headers(self) -> Optional[Dict[str, str]]:
        if not self.peer_api_key:
            return None
        return {"X-API-Key": self.peer_api_key}

    def _announce_inventory(
        self,
        *,
        transactions: Optional[List[str]] = None,
        blocks: Optional[List[str]] = None,
    ) -> None:
        payload: Dict[str, List[str]] = {}
        if transactions:
            payload["transactions"] = [txid for txid in transactions if txid]
        if blocks:
            payload["blocks"] = [block_hash for block_hash in blocks if block_hash]
        if not payload:
            return
        message = {"type": "inv", "payload": payload}
        self._dispatch_async(self.broadcast(message))

    def _has_transaction(self, txid: Optional[str]) -> bool:
        if not txid:
            return False
        if txid in getattr(self.blockchain, "seen_txids", set()):
            return True
        pending = getattr(self.blockchain, "pending_transactions", []) or []
        return any(getattr(tx, "txid", None) == txid for tx in pending)

    def _find_pending_transaction(self, txid: Optional[str]):
        if not txid:
            return None
        for tx in getattr(self.blockchain, "pending_transactions", []) or []:
            if getattr(tx, "txid", None) == txid:
                return tx
        return None

    def _has_block(self, block_hash: Optional[str]) -> bool:
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

    def _normalize_remote_header(self, header_dict: Dict[str, Any]) -> Dict[str, Any]:
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
        for peer_uri in self._http_peers_snapshot():
            endpoint = f"{peer_uri.rstrip('/')}/transaction/receive"
            try:
                response = requests.post(
                    endpoint,
                    json=payload,
                    headers=self._peer_headers(),
                    timeout=self._http_timeout,
                )
                if response.status_code >= 400:
                    self.peer_manager.reputation.record_invalid_transaction(peer_uri)
                else:
                    self.peer_manager.reputation.record_valid_transaction(peer_uri)
            except Exception as e:
                # Network error broadcasting transaction - record reputation penalty
                logger.debug(f"Failed to broadcast transaction to {peer_uri}: {e}")
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
        for peer_uri in self._http_peers_snapshot():
            endpoint = f"{peer_uri.rstrip('/')}/block/receive"
            try:
                requests.post(
                    endpoint,
                    json=message["payload"],
                    headers=self._peer_headers(),
                    timeout=self._http_timeout,
                )
            except Exception as e:
                # Network error broadcasting block - peer may be down, continue to others
                logger.debug(f"Failed to broadcast block to {peer_uri}: {e}")
        self._dispatch_async(self.broadcast(message))
        if self.quic_enabled:
            payload = json.dumps(message).encode("utf-8")
            for peer_uri in self._http_peers_snapshot():
                host = urlparse(peer_uri).hostname
                if not host:
                    continue
                self._dispatch_async(self._quic_send_payload(host, payload))

    def _http_sync(self) -> bool:
        """HTTP-based synchronization for manually registered peers."""
        for peer_uri in self._http_peers_snapshot():
            try:
                base_endpoint = f"{peer_uri.rstrip('/')}/blocks"
                response = requests.get(base_endpoint, timeout=self._http_timeout)
                if response.status_code != 200:
                    continue
                data = response.json()
                remote_blocks = data.get("blocks") or []
                remote_total = data.get("total", len(remote_blocks))
                if remote_total > len(self.blockchain.chain):
                    # Fetch full chain snapshot if remote height is greater
                    response_full = requests.get(
                        base_endpoint,
                        params={"limit": remote_total, "offset": 0},
                        timeout=self._http_timeout,
                    )
                    if response_full.status_code != 200:
                        continue
                    remote_blocks = response_full.json().get("blocks") or []
                    if not isinstance(remote_blocks, list):
                        continue
                    new_chain_headers: list[BlockHeader] = []
                    valid_chain = True
                    for block_data in remote_blocks:
                        header_dict = None
                        txs = []
                        if isinstance(block_data, dict):
                            header_dict = block_data.get("header") or block_data
                            txs = block_data.get("transactions", [])
                        if not header_dict:
                            valid_chain = False
                            break
                        if txs is None:
                            txs = []
                        if not isinstance(txs, list):
                            valid_chain = False
                            break
                        try:
                            normalized_header = self._normalize_remote_header(header_dict)
                            header = BlockHeader(
                                index=normalized_header["index"],
                                previous_hash=normalized_header["previous_hash"],
                                timestamp=normalized_header["timestamp"],
                                merkle_root=normalized_header["merkle_root"],
                                nonce=normalized_header["nonce"],
                                difficulty=normalized_header["difficulty"],
                                miner_pubkey=normalized_header.get("miner_pubkey"),
                                signature=normalized_header.get("signature"),
                                version=normalized_header.get("version"),
                            )
                            if "hash" in normalized_header:
                                header.hash = normalized_header["hash"]
                            new_chain_headers.append(header)
                        except (KeyError, TypeError, ValueError) as e:
                            logger.debug(f"Invalid block header in chain from {peer_uri}: {e}")
                            valid_chain = False
                            break
                    if valid_chain and self.blockchain.replace_chain(new_chain_headers):
                        return True
                    if not valid_chain:
                        deserializer = getattr(self.blockchain, "deserialize_chain", None)
                        if callable(deserializer):
                            try:
                                deserialized = deserializer(remote_blocks)
                                if deserialized and self.blockchain.replace_chain(deserialized):
                                    return True
                            except Exception as exc:
                                logger.debug(f"deserialize_chain failed for peer {peer_uri}: {exc}")
            except Exception as e:
                logger.debug(f"Failed to sync with peer {peer_uri}: {e}")
                continue
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
                # Invalid response format from peer - try next peer
                logger.warning(f"Invalid chain data from peer {peer_uri}: {e}")
                continue
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
            return True
        return False

    def sync_with_network(self) -> bool:
        """Synchronize blockchain with peers (HTTP first, then WebSocket)."""
        if self._http_sync():
            return True
        try:
            return asyncio.run(self._ws_sync())
        except RuntimeError:
            # Already inside an event loop; schedule and return False to avoid blocking
            self._dispatch_async(self._ws_sync())
            return False
