from __future__ import annotations

"""
WebSocket API Handler

Handles all WebSocket-related functionality including:
- WebSocket connection management
- Channel subscriptions
- Real-time message broadcasting
- Background stats updates
"""

import hashlib
import json
import logging
import threading
import time
from collections import defaultdict, deque
from typing import Any

from flask import Flask, request
from flask_sock import Sock

from xai.core.api_auth import APIAuthManager
from xai.core.security_validation import log_security_event

logger = logging.getLogger(__name__)
ATTACHMENT_SAFE = True

class WebSocketLimiter:
    """WebSocket connection and rate limiting.

    Implements Task 66: WebSocket Limits with connection limits, rate limiting,
    timeouts, and message size limits.
    """

    def __init__(self):
        """Initialize WebSocket limiter with default limits."""
        self.connections_per_ip: dict[str, int] = defaultdict(int)
        self.total_connections: int = 0
        self.last_message_time: dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.connection_times: dict[str, float] = {}

        # Limits (configurable)
        self.MAX_CONNECTIONS_PER_IP = 10
        self.MAX_GLOBAL_CONNECTIONS = 10000
        self.CONNECTION_TIMEOUT = 300  # 5 minutes
        self.MESSAGE_SIZE_LIMIT = 1_048_576  # 1 MB
        self.MESSAGE_RATE_LIMIT = 100  # per minute

    def can_connect(self, ip_address: str) -> tuple[bool, str | None]:
        """Check if new connection is allowed.

        Args:
            ip_address: IP address of the connecting client

        Returns:
            Tuple of (can_connect, error_message)
        """
        # Check global limit
        if self.total_connections >= self.MAX_GLOBAL_CONNECTIONS:
            return False, "Global connection limit reached"

        # Check per-IP limit
        if self.connections_per_ip[ip_address] >= self.MAX_CONNECTIONS_PER_IP:
            return False, f"Connection limit for IP {ip_address} reached"

        return True, None

    def register_connection(self, client_id: str, ip_address: str) -> None:
        """Register new WebSocket connection.

        Args:
            client_id: Unique client identifier
            ip_address: IP address of the client
        """
        self.connections_per_ip[ip_address] += 1
        self.total_connections += 1
        self.connection_times[client_id] = time.time()

    def unregister_connection(self, client_id: str, ip_address: str) -> None:
        """Unregister WebSocket connection.

        Args:
            client_id: Unique client identifier
            ip_address: IP address of the client
        """
        self.connections_per_ip[ip_address] = max(0, self.connections_per_ip[ip_address] - 1)
        self.total_connections = max(0, self.total_connections - 1)

        if client_id in self.connection_times:
            del self.connection_times[client_id]
        if client_id in self.last_message_time:
            del self.last_message_time[client_id]

    def check_message_rate(self, client_id: str) -> tuple[bool, str | None]:
        """Check if client is within message rate limit.

        Args:
            client_id: Unique client identifier

        Returns:
            Tuple of (within_limit, error_message)
        """
        now = time.time()
        messages = self.last_message_time[client_id]

        # Count messages in last minute
        one_minute_ago = now - 60
        recent_messages = sum(1 for msg_time in messages if msg_time > one_minute_ago)

        if recent_messages >= self.MESSAGE_RATE_LIMIT:
            return False, "Message rate limit exceeded"

        messages.append(now)
        return True, None

    def validate_message_size(self, message: str) -> tuple[bool, str | None]:
        """Validate message size.

        Args:
            message: Message to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        size = len(message.encode('utf-8'))
        if size > self.MESSAGE_SIZE_LIMIT:
            return False, f"Message size {size} exceeds limit {self.MESSAGE_SIZE_LIMIT}"
        return True, None

    def check_idle_timeout(self, client_id: str) -> bool:
        """Check if connection has been idle too long.

        Args:
            client_id: Unique client identifier

        Returns:
            True if connection is idle and should be closed
        """
        if client_id not in self.connection_times:
            return False

        idle_time = time.time() - self.connection_times[client_id]
        return idle_time > self.CONNECTION_TIMEOUT

    def update_activity(self, client_id: str) -> None:
        """Update last activity time for a client.

        Args:
            client_id: Unique client identifier
        """
        if client_id in self.connection_times:
            self.connection_times[client_id] = time.time()

    def cleanup_stale_connections(self) -> list[str]:
        """Find and return list of stale connection IDs.

        Returns:
            List of client IDs with stale connections
        """
        stale = []
        now = time.time()

        for client_id, connect_time in list(self.connection_times.items()):
            if now - connect_time > self.CONNECTION_TIMEOUT:
                stale.append(client_id)

        return stale

    def get_stats(self) -> dict[str, Any]:
        """Get current limiter statistics.

        Returns:
            Dictionary of statistics
        """
        return {
            "total_connections": self.total_connections,
            "connections_by_ip": dict(self.connections_per_ip),
            "limits": {
                "max_connections_per_ip": self.MAX_CONNECTIONS_PER_IP,
                "max_global_connections": self.MAX_GLOBAL_CONNECTIONS,
                "connection_timeout": self.CONNECTION_TIMEOUT,
                "message_size_limit": self.MESSAGE_SIZE_LIMIT,
                "message_rate_limit": self.MESSAGE_RATE_LIMIT
            }
        }

class WebSocketAPIHandler:
    """Handles all WebSocket-related API endpoints and functionality."""

    def __init__(self, node: Any, app: Flask, api_auth: APIAuthManager | None = None):
        """
        Initialize WebSocket API Handler.

        Args:
            node: BlockchainNode instance
            app: Flask application instance
        """
        self.node = node
        self.app = app
        self.api_auth = api_auth or getattr(getattr(node, "api_routes", None), "api_auth", None)

        # WebSocket support
        self.sock = Sock(self.app)
        self.ws_clients: list[dict[str, Any]] = []  # Connected WebSocket clients
        self.ws_subscriptions: dict[str, list[str]] = {}  # client_id -> [channels]

        # WebSocket limiter (Task 66)
        self.limiter = WebSocketLimiter()

        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()

        # Register routes
        self._register_routes()

    def _register_routes(self) -> None:
        """Register WebSocket route."""

        @self.sock.route("/ws")
        def websocket_handler(ws: Any) -> None:
            """WebSocket connection handler."""
            self._handle_websocket_connection(ws)

    def _handle_websocket_connection(self, ws: Any) -> None:
        """
        Handle WebSocket connection lifecycle with rate limiting.

        Args:
            ws: WebSocket connection object
        """
        client_id = hashlib.sha256(f"{time.time()}".encode()).hexdigest()[:16]
        ip_address = request.remote_addr or "unknown"

        # Enforce API authentication before allocating connection slots
        auth_allowed, auth_error = self._authenticate_ws_request()
        if not auth_allowed:
            logger.warning(
                "WebSocket authentication failed for %s: %s",
                ip_address,
                auth_error or "unauthorized",
                extra={"event": "ws.auth_failure", "client_id": client_id}
            )
            self._close_with_error(ws, auth_error or "Unauthorized", code="WS_AUTH_FAILED")
            return

        # Check connection limits (Task 66)
        can_connect, error = self.limiter.can_connect(ip_address)
        if not can_connect:
            logger.warning(f"Connection rejected from {ip_address}: {error}")
            try:
                ws.send(json.dumps({"error": error}))
                ws.close()
            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                logger.debug(f"Failed to send rejection to {ip_address}: {type(e).__name__}")
            return

        # Register connection
        self.limiter.register_connection(client_id, ip_address)
        self.ws_clients.append({"id": client_id, "ws": ws, "ip": ip_address})
        self.ws_subscriptions[client_id] = []

        logger.info(f"WebSocket client {client_id} connected from {ip_address}")

        try:
            while True:
                message = ws.receive()

                if not message:
                    continue

                # Check message size (Task 66)
                valid_size, size_error = self.limiter.validate_message_size(message)
                if not valid_size:
                    ws.send(json.dumps({"error": size_error}))
                    continue

                # Check rate limit (Task 66)
                within_limit, rate_error = self.limiter.check_message_rate(client_id)
                if not within_limit:
                    ws.send(json.dumps({"error": rate_error}))
                    continue

                # Update activity timestamp
                self.limiter.update_activity(client_id)

                # Process message
                data = json.loads(message)
                self._handle_ws_message(client_id, ws, data)

        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            logger.error(f"WebSocket error for {client_id}: {e}")

        finally:
            # Cleanup
            self.limiter.unregister_connection(client_id, ip_address)
            self.ws_clients = [c for c in self.ws_clients if c["id"] != client_id]
            if client_id in self.ws_subscriptions:
                del self.ws_subscriptions[client_id]
            logger.info(f"WebSocket client {client_id} disconnected")

    def _authenticate_ws_request(self) -> tuple[bool, str | None]:
        """Authenticate incoming WebSocket upgrade request if API auth is enabled."""

        if not self.api_auth or not self.api_auth.is_enabled():
            return True, None

        try:
            allowed, reason = self.api_auth.authorize(request)
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
            logger.error(
                "WebSocket authentication raised error: %s",
                exc,
                extra={"event": "ws.auth_exception"}
            )
            log_security_event(
                "websocket.auth.exception",
                {
                    "remote_addr": request.remote_addr or "unknown",
                    "user_agent": request.headers.get("User-Agent", "unknown"),
                    "error": type(exc).__name__,
                },
                severity="ERROR"
            )
            return False, "Authentication error"

        if not allowed:
            log_security_event(
                "websocket.auth.denied",
                {
                    "remote_addr": request.remote_addr or "unknown",
                    "user_agent": request.headers.get("User-Agent", "unknown"),
                    "reason": reason or "unauthorized",
                },
                severity="WARNING"
            )
        return allowed, reason

    @staticmethod
    def _close_with_error(ws: Any, message: str, code: str = "WS_ERROR") -> None:
        """Send structured error payload and close socket safely."""

        try:
            ws.send(json.dumps({"error": message, "code": code}))
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
            logger.debug(
                "Failed to send WebSocket error response: %s",
                type(exc).__name__,
                extra={"event": "ws.error_send_failed"}
            )
        finally:
            try:
                ws.close()
            except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as exc:
                logger.debug(
                    "Failed to close WebSocket after error: %s",
                    type(exc).__name__,
                    extra={"event": "ws.close_failed"}
                )

    def _handle_ws_message(self, client_id: str, ws: Any, data: dict[str, Any]) -> None:
        """
        Handle WebSocket message from client.

        Args:
            client_id: Client identifier
            ws: WebSocket connection object
            data: Message data
        """
        action = data.get("action")
        channel = data.get("channel")

        if action == "subscribe" and channel:
            if client_id not in self.ws_subscriptions:
                self.ws_subscriptions[client_id] = []

            if channel not in self.ws_subscriptions[client_id]:
                self.ws_subscriptions[client_id].append(channel)
                ws.send(json.dumps({"success": True, "message": f"Subscribed to {channel}"}))

        elif action == "unsubscribe" and channel:
            if client_id in self.ws_subscriptions:
                if channel in self.ws_subscriptions[client_id]:
                    self.ws_subscriptions[client_id].remove(channel)
                    ws.send(
                        json.dumps({"success": True, "message": f"Unsubscribed from {channel}"})
                    )

    def broadcast_ws(self, message: dict[str, Any]) -> None:
        """
        Broadcast message to subscribed WebSocket clients.

        Args:
            message: Message to broadcast (must include 'channel' key)
        """
        channel = message.get("channel")

        for client in self.ws_clients:
            client_id = client["id"]
            if channel in self.ws_subscriptions.get(client_id, []):
                try:
                    client["ws"].send(json.dumps(message))
                except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                    logger.error(f"Failed to send to client {client_id}: {e}")

    def _cleanup_loop(self) -> None:
        """Periodic cleanup of stale connections (Task 66)."""
        while True:
            time.sleep(60)  # Check every minute

            stale_clients = self.limiter.cleanup_stale_connections()
            for client_id in stale_clients:
                # Find and close stale client
                for client in self.ws_clients[:]:
                    if client["id"] == client_id:
                        try:
                            client["ws"].close()
                        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
                            logger.debug(f"Failed to close stale client {client_id}: {type(e).__name__}")

                        ip = client.get("ip", "unknown")
                        self.limiter.unregister_connection(client_id, ip)
                        self.ws_clients.remove(client)

                        if client_id in self.ws_subscriptions:
                            del self.ws_subscriptions[client_id]

                        logger.info(f"Closed stale connection: {client_id}")

    def broadcast_sync_progress(self, progress_data: dict[str, Any]) -> None:
        """
        Broadcast sync progress update to WebSocket clients subscribed to 'sync' channel.

        Args:
            progress_data: Sync progress data to broadcast
        """
        message = {
            "channel": "sync",
            "type": "sync_progress",
            "data": progress_data
        }
        self.broadcast_ws(message)

    def start_background_tasks(self) -> None:
        """Start background monitoring tasks."""

        def stats_updater() -> None:
            """Periodically broadcast stats to WebSocket clients."""
            while True:
                time.sleep(10)  # Every 10 seconds

                # Broadcast blockchain stats
                stats = self.node.blockchain.get_stats()
                self.broadcast_ws({"channel": "stats", "event": "update", "data": stats})

        def sync_progress_updater() -> None:
            """Periodically broadcast sync progress to WebSocket clients."""
            while True:
                time.sleep(2)  # Every 2 seconds for more responsive sync updates

                # Broadcast light client header sync progress
                light_client_service = getattr(self.node, "light_client_service", None)
                if light_client_service:
                    try:
                        sync_progress = light_client_service.get_sync_progress()
                        progress_dict = sync_progress.to_dict()

                        # Only broadcast if actively syncing or recently completed
                        if progress_dict["sync_state"] in ["syncing", "stalled"]:
                            self.broadcast_ws({
                                "channel": "sync",
                                "type": "header_sync_progress",
                                "data": {
                                    "current_height": progress_dict["current_height"],
                                    "target_height": progress_dict["target_height"],
                                    "sync_percentage": progress_dict["sync_percentage"],
                                    "estimated_time_remaining": progress_dict["estimated_time_remaining"],
                                    "headers_per_second": progress_dict["headers_per_second"],
                                    "sync_state": progress_dict["sync_state"],
                                    "started_at": progress_dict["started_at"],
                                }
                            })
                    except (RuntimeError, ValueError, AttributeError) as e:
                        logger.debug(f"Failed to broadcast header sync progress: {type(e).__name__}")

                # Broadcast checkpoint sync progress
                sync_coordinator = getattr(self.node, "partial_sync_coordinator", None)
                sync_mgr = getattr(sync_coordinator, "sync_manager", None) if sync_coordinator else None
                if sync_mgr and hasattr(sync_mgr, "get_checkpoint_sync_progress"):
                    try:
                        checkpoint_progress = sync_mgr.get_checkpoint_sync_progress()
                        if checkpoint_progress.get("stage") not in ["idle", "completed"]:
                            self.broadcast_ws({
                                "channel": "sync",
                                "type": "checkpoint_progress",
                                "data": checkpoint_progress
                            })
                    except (RuntimeError, ValueError, AttributeError) as e:
                        logger.debug(f"Failed to broadcast checkpoint progress: {type(e).__name__}")

        stats_thread = threading.Thread(target=stats_updater, daemon=True)
        stats_thread.start()

        sync_thread = threading.Thread(target=sync_progress_updater, daemon=True)
        sync_thread.start()

        logger.info("WebSocket background tasks started")
