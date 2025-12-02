"""
WebSocket API Handler

Handles all WebSocket-related functionality including:
- WebSocket connection management
- Channel subscriptions
- Real-time message broadcasting
- Background stats updates
"""

import time
import json
import hashlib
import threading
import logging
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict, deque
from flask import Flask, request
from flask_sock import Sock

logger = logging.getLogger(__name__)


class WebSocketLimiter:
    """WebSocket connection and rate limiting.

    Implements Task 66: WebSocket Limits with connection limits, rate limiting,
    timeouts, and message size limits.
    """

    def __init__(self):
        """Initialize WebSocket limiter with default limits."""
        self.connections_per_ip: Dict[str, int] = defaultdict(int)
        self.total_connections: int = 0
        self.last_message_time: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.connection_times: Dict[str, float] = {}

        # Limits (configurable)
        self.MAX_CONNECTIONS_PER_IP = 10
        self.MAX_GLOBAL_CONNECTIONS = 10000
        self.CONNECTION_TIMEOUT = 300  # 5 minutes
        self.MESSAGE_SIZE_LIMIT = 1_048_576  # 1 MB
        self.MESSAGE_RATE_LIMIT = 100  # per minute

    def can_connect(self, ip_address: str) -> Tuple[bool, Optional[str]]:
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

    def check_message_rate(self, client_id: str) -> Tuple[bool, Optional[str]]:
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

    def validate_message_size(self, message: str) -> Tuple[bool, Optional[str]]:
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

    def cleanup_stale_connections(self) -> List[str]:
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

    def get_stats(self) -> Dict[str, Any]:
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

    def __init__(self, node: Any, app: Flask):
        """
        Initialize WebSocket API Handler.

        Args:
            node: BlockchainNode instance
            app: Flask application instance
        """
        self.node = node
        self.app = app

        # WebSocket support
        self.sock = Sock(self.app)
        self.ws_clients: List[Dict[str, Any]] = []  # Connected WebSocket clients
        self.ws_subscriptions: Dict[str, List[str]] = {}  # client_id -> [channels]

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

        # Check connection limits (Task 66)
        can_connect, error = self.limiter.can_connect(ip_address)
        if not can_connect:
            logger.warning(f"Connection rejected from {ip_address}: {error}")
            try:
                ws.send(json.dumps({"error": error}))
                ws.close()
            except Exception as e:
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

        except Exception as e:
            logger.error(f"WebSocket error for {client_id}: {e}")

        finally:
            # Cleanup
            self.limiter.unregister_connection(client_id, ip_address)
            self.ws_clients = [c for c in self.ws_clients if c["id"] != client_id]
            if client_id in self.ws_subscriptions:
                del self.ws_subscriptions[client_id]
            logger.info(f"WebSocket client {client_id} disconnected")

    def _handle_ws_message(self, client_id: str, ws: Any, data: Dict[str, Any]) -> None:
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

    def broadcast_ws(self, message: Dict[str, Any]) -> None:
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
                except Exception as e:
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
                        except Exception as e:
                            logger.debug(f"Failed to close stale client {client_id}: {type(e).__name__}")

                        ip = client.get("ip", "unknown")
                        self.limiter.unregister_connection(client_id, ip)
                        self.ws_clients.remove(client)

                        if client_id in self.ws_subscriptions:
                            del self.ws_subscriptions[client_id]

                        logger.info(f"Closed stale connection: {client_id}")

    def start_background_tasks(self) -> None:
        """Start background monitoring tasks."""

        def stats_updater() -> None:
            """Periodically broadcast stats to WebSocket clients."""
            while True:
                time.sleep(10)  # Every 10 seconds

                # Broadcast blockchain stats
                stats = self.node.blockchain.get_stats()
                self.broadcast_ws({"channel": "stats", "event": "update", "data": stats})

        stats_thread = threading.Thread(target=stats_updater, daemon=True)
        stats_thread.start()
        logger.info("WebSocket background tasks started")
