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
from typing import Dict, List, Any
from flask import Flask
from flask_sock import Sock

logger = logging.getLogger(__name__)


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
        Handle WebSocket connection lifecycle.

        Args:
            ws: WebSocket connection object
        """
        client_id = hashlib.sha256(f"{time.time()}".encode()).hexdigest()[:16]
        self.ws_clients.append({"id": client_id, "ws": ws})
        self.ws_subscriptions[client_id] = []

        logger.info(f"WebSocket client {client_id} connected")

        try:
            while True:
                message = ws.receive()
                if message:
                    data = json.loads(message)
                    self._handle_ws_message(client_id, ws, data)

        except Exception as e:
            logger.error(f"WebSocket error for {client_id}: {e}")

        finally:
            # Cleanup
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
