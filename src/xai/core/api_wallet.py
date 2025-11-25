"""
Wallet and Trading API Handler

Handles all wallet and trading-related API endpoints including:
- Wallet creation (standard and embedded)
- WalletConnect integration
- Trade orders and matching
- Trade gossip protocol
- Wallet seeds snapshot
"""

import os
import json
import time
import logging
from typing import Dict, Any, Tuple, Optional
from flask import Flask, jsonify, request, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from xai.core.config import Config
from xai.core.security_validation import ValidationError

logger = logging.getLogger(__name__)

trade_orders_counter = Counter("xai_trade_orders_total", "Total trade orders submitted")
trade_matches_counter = Counter("xai_trade_matches_total", "Total trade matches created")
trade_secrets_counter = Counter("xai_trade_secrets_revealed_total", "Secrets revealed for matches")
walletconnect_sessions_counter = Counter(
    "xai_walletconnect_sessions_total", "WalletConnect sessions registered"
)


class WalletAPIHandler:
    """Handles all wallet and trading-related API endpoints."""

    def __init__(
        self, node: Any, app: Flask, broadcast_callback: callable, trade_peers: Dict[str, float]
    ):
        """
        Initialize Wallet API Handler.

        Args:
            node: BlockchainNode instance
            app: Flask application instance
            broadcast_callback: Function to broadcast WebSocket messages
            trade_peers: Dictionary of trade peers (hostname -> last_seen)
        """
        self.node = node
        self.app = app
        self.broadcast_ws = broadcast_callback
        self.trade_peers = trade_peers

        # Register routes
        self._register_routes()

    def _register_routes(self) -> None:
        """Register all wallet and trading routes."""

        # Wallet creation routes
        @self.app.route("/wallet/create", methods=["POST"])
        def create_wallet() -> Tuple[Dict[str, Any], int]:
            """Create new wallet."""
            return self.create_wallet_handler()

        @self.app.route("/wallet/embedded/create", methods=["POST"])
        def create_embedded_wallet() -> Tuple[Dict[str, Any], int]:
            """Create an embedded wallet alias."""
            return self.create_embedded_wallet_handler()

        @self.app.route("/wallet/embedded/login", methods=["POST"])
        def login_embedded_wallet() -> Tuple[Dict[str, Any], int]:
            """Login to embedded wallet."""
            return self.login_embedded_wallet_handler()

        # WalletConnect routes
        @self.app.route("/wallet-trades/wc/handshake", methods=["POST"])
        def walletconnect_handshake() -> Tuple[Dict[str, Any], int]:
            """WalletConnect handshake."""
            return self.walletconnect_handshake_handler()

        @self.app.route("/wallet-trades/wc/confirm", methods=["POST"])
        def walletconnect_confirm() -> Tuple[Dict[str, Any], int]:
            """Confirm WalletConnect handshake."""
            return self.walletconnect_confirm_handler()

        # Trade session routes
        @self.app.route("/wallet-trades/register", methods=["POST"])
        def register_trade_session() -> Tuple[Dict[str, Any], int]:
            """Create WalletConnect-style session."""
            return self.register_trade_session_handler()

        # Trade order routes
        @self.app.route("/wallet-trades/orders", methods=["GET"])
        def list_trade_orders() -> Tuple[Dict[str, Any], int]:
            """List trade orders."""
            return self.list_trade_orders_handler()

        @self.app.route("/wallet-trades/orders", methods=["POST"])
        def create_trade_order() -> Tuple[Dict[str, Any], int]:
            """Create trade order."""
            return self.create_trade_order_handler()

        @self.app.route("/wallet-trades/orders/<order_id>", methods=["GET"])
        def get_trade_order(order_id: str) -> Tuple[Dict[str, Any], int]:
            """Get specific trade order."""
            return self.get_trade_order_handler(order_id)

        # Trade match routes
        @self.app.route("/wallet-trades/matches", methods=["GET"])
        def list_trade_matches() -> Tuple[Dict[str, Any], int]:
            """List trade matches."""
            return self.list_trade_matches_handler()

        @self.app.route("/wallet-trades/matches/<match_id>", methods=["GET"])
        def get_trade_match(match_id: str) -> Tuple[Dict[str, Any], int]:
            """Get specific trade match."""
            return self.get_trade_match_handler(match_id)

        @self.app.route("/wallet-trades/matches/<match_id>/secret", methods=["POST"])
        def submit_trade_secret(match_id: str) -> Tuple[Dict[str, Any], int]:
            """Submit trade secret for match."""
            return self.submit_trade_secret_handler(match_id)

        # Gossip and snapshot routes
        @self.app.route("/wallet-trades/gossip", methods=["POST"])
        def inbound_gossip() -> Tuple[Dict[str, Any], int]:
            """Handle inbound gossip."""
            return self.inbound_gossip_handler()

        @self.app.route("/wallet-trades/snapshot", methods=["GET"])
        def snapshot_orderbook() -> Tuple[Dict[str, Any], int]:
            """Get orderbook snapshot."""
            return self.snapshot_orderbook_handler()

        @self.app.route("/wallet-trades/peers/register", methods=["POST"])
        def register_trade_peer() -> Tuple[Dict[str, Any], int]:
            """Register trade peer."""
            return self.register_trade_peer_handler()

        @self.app.route("/wallet-trades/backfill", methods=["GET"])
        def trade_backfill() -> Tuple[Dict[str, Any], int]:
            """Get trade event backfill."""
            return self.trade_backfill_handler()

        @self.app.route("/wallet-trades/history", methods=["GET"])
        def get_trade_history() -> Tuple[Dict[str, Any], int]:
            """Get trade history."""
            return self.get_trade_history_handler()

        @self.app.route("/wallet-seeds/snapshot", methods=["GET"])
        def wallet_seeds_snapshot() -> Tuple[Dict[str, Any], int]:
            """Get wallet seeds snapshot."""
            return self.wallet_seeds_snapshot_handler()

        # Metrics route
        @self.app.route("/metrics", methods=["GET"])
        def metrics() -> Response:
            """Get Prometheus metrics."""
            return self.metrics_handler()

    def create_wallet_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle wallet creation.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        from xai.core.wallet import Wallet

        wallet = Wallet()

        return (
            jsonify(
                {
                    "success": True,
                    "address": wallet.address,
                    "public_key": wallet.public_key,
                    "private_key": wallet.private_key,
                    "warning": "Save private key securely. Cannot be recovered.",
                }
            ),
            200,
        )

    def create_embedded_wallet_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle embedded wallet creation.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        if not hasattr(self.node, "account_abstraction"):
            return jsonify({"success": False, "error": "EMBEDDED_NOT_ENABLED"}), 503

        payload = request.get_json(silent=True) or {}
        alias = payload.get("alias")
        contact = payload.get("contact")
        secret = payload.get("secret")

        if not all([alias, contact, secret]):
            return (
                jsonify({"success": False, "error": "alias, contact, and secret required"}),
                400,
            )

        try:
            record = self.node.account_abstraction.create_embedded_wallet(alias, contact, secret)
        except ValueError as exc:
            return (
                jsonify({"success": False, "error": "ALIAS_EXISTS", "message": str(exc)}),
                400,
            )

        token = self.node.account_abstraction.get_session_token(alias)
        return (
            jsonify(
                {
                    "success": True,
                    "alias": alias,
                    "contact": contact,
                    "address": record.address,
                    "session_token": token,
                }
            ),
            200,
        )

    def login_embedded_wallet_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle embedded wallet login.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        if not hasattr(self.node, "account_abstraction"):
            return jsonify({"success": False, "error": "EMBEDDED_NOT_ENABLED"}), 503

        payload = request.get_json(silent=True) or {}
        alias = payload.get("alias")
        secret = payload.get("secret")

        if not all([alias, secret]):
            return jsonify({"success": False, "error": "alias and secret required"}), 400

        token = self.node.account_abstraction.authenticate(alias, secret)
        if not token:
            return jsonify({"success": False, "error": "AUTH_FAILED"}), 403

        record = self.node.account_abstraction.get_record(alias)
        return (
            jsonify(
                {
                    "success": True,
                    "alias": alias,
                    "address": record.address if record else None,
                    "session_token": token,
                }
            ),
            200,
        )

    def walletconnect_handshake_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle WalletConnect handshake.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        data = request.json or {}
        wallet_address = data.get("wallet_address")

        if not wallet_address:
            return jsonify({"success": False, "error": "wallet_address required"}), 400

        handshake = self.node.blockchain.trade_manager.begin_walletconnect_handshake(wallet_address)
        walletconnect_sessions_counter.inc()
        return jsonify(handshake), 200

    def walletconnect_confirm_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle WalletConnect confirmation.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        data = request.json or {}
        handshake_id = data.get("handshake_id")
        wallet_address = data.get("wallet_address")
        client_public = data.get("client_public")

        if not all([handshake_id, wallet_address, client_public]):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "handshake_id, wallet_address, and client_public required",
                    }
                ),
                400,
            )

        session = self.node.blockchain.trade_manager.complete_walletconnect_handshake(
            handshake_id, wallet_address, client_public
        )
        if not session:
            return jsonify({"success": False, "error": "handshake failed"}), 400

        return jsonify({"success": True, "session_token": session["session_token"]}), 200

    def register_trade_session_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle trade session registration.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        data = request.json or {}
        wallet_address = data.get("wallet_address")

        if not wallet_address:
            return jsonify({"success": False, "error": "wallet_address required"}), 400

        session = self.node.blockchain.register_trade_session(wallet_address)
        self.node.blockchain.record_trade_event(
            "session_registered",
            {"wallet_address": wallet_address, "session_token": session["session_token"]},
        )
        return jsonify({"success": True, **session}), 200

    def list_trade_orders_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle trade orders listing.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        orders = self.node.blockchain.get_trade_orders()
        return jsonify({"success": True, "orders": orders}), 200

    def create_trade_order_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle trade order creation.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        order_data = request.json or {}
        try:
            result = self.node.blockchain.submit_trade_order(order_data)
        except ValueError as exc:
            return jsonify({"success": False, "error": str(exc)}), 400

        trade_orders_counter.inc()

        event = {
            "channel": "wallet-trades",
            "event": "order_created" if result.get("status") == "pending" else "match_ready",
            "data": result,
        }
        self.broadcast_ws(event)

        if result.get("status") != "pending":
            trade_matches_counter.inc()

        order_obj = self.node.blockchain.trade_manager.get_order(result["order_id"])
        gossip_payload = {
            "type": "order",
            "order": order_obj.to_dict() if order_obj else order_data,
        }
        self._gossip_trade_event(gossip_payload)

        return jsonify(result), 200

    def get_trade_order_handler(self, order_id: str) -> Tuple[Dict[str, Any], int]:
        """
        Handle specific trade order retrieval.

        Args:
            order_id: Order ID to retrieve

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        order = self.node.blockchain.trade_manager.get_order(order_id)
        if not order:
            return jsonify({"success": False, "error": "Order not found"}), 404
        return jsonify({"success": True, "order": order.to_dict()}), 200

    def list_trade_matches_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle trade matches listing.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        matches = self.node.blockchain.get_trade_matches()
        return jsonify({"success": True, "matches": matches}), 200

    def get_trade_match_handler(self, match_id: str) -> Tuple[Dict[str, Any], int]:
        """
        Handle specific trade match retrieval.

        Args:
            match_id: Match ID to retrieve

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        match = self.node.blockchain.trade_manager.get_match(match_id)
        if not match:
            return jsonify({"success": False, "error": "Match not found"}), 404
        return jsonify({"success": True, "match": match.to_dict()}), 200

    def submit_trade_secret_handler(self, match_id: str) -> Tuple[Dict[str, Any], int]:
        """
        Handle trade secret submission.

        Args:
            match_id: Match ID to submit secret for

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        payload = request.json or {}
        secret = payload.get("secret")

        if not secret:
            return jsonify({"success": False, "message": "secret required"}), 400

        response = self.node.blockchain.reveal_trade_secret(match_id, secret)
        if response["success"]:
            self.broadcast_ws(
                {
                    "channel": "wallet-trades",
                    "event": "match_settlement",
                    "data": {"match_id": match_id},
                }
            )
            trade_secrets_counter.inc()

        return jsonify(response), 200

    def inbound_gossip_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle inbound gossip messages.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        event = request.json or {}
        token = request.headers.get("X-Wallet-Trade-Secret")
        host = request.remote_addr

        if token != Config.WALLET_TRADE_PEER_SECRET:
            logger.warning(f"Rejected gossip from {host} due to missing/invalid secret")
            return jsonify({"success": False, "error": "Invalid peer secret"}), 403

        self._register_trade_peer(request.host_url[:-1])
        result = self.node.blockchain.trade_manager.ingest_gossip(event)
        return jsonify(result), 200

    def snapshot_orderbook_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle orderbook snapshot request.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        snapshot = self.node.blockchain.trade_manager.snapshot()
        return jsonify({"success": True, "snapshot": snapshot}), 200

    def register_trade_peer_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle trade peer registration.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        data = request.json or {}
        host = data.get("host")
        secret = data.get("secret")

        if not host:
            return jsonify({"success": False, "error": "host required"}), 400

        if secret != Config.WALLET_TRADE_PEER_SECRET:
            return jsonify({"success": False, "error": "invalid secret"}), 403

        self._register_trade_peer(host)
        return jsonify({"success": True, "host": host}), 200

    def trade_backfill_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle trade event backfill request.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        limit = int(request.args.get("limit", 25))
        signed_events = self.node.blockchain.trade_manager.signed_event_batch(limit)
        return (
            jsonify(
                {
                    "success": True,
                    "events": signed_events,
                    "public_key": (
                        signed_events[0]["public_key"]
                        if signed_events
                        else self.node.blockchain.trade_manager.audit_signer.public_key()
                    ),
                }
            ),
            200,
        )

    def get_trade_history_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle trade history request.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        history = self.node.blockchain.trade_history
        return jsonify({"success": True, "history": history}), 200

    def wallet_seeds_snapshot_handler(self) -> Tuple[Dict[str, Any], int]:
        """
        Handle wallet seeds snapshot request.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        manifest_path = os.path.join(os.getcwd(), "premine_manifest.json")
        summary_path = os.path.join(os.getcwd(), "premine_wallets_SUMMARY.json")

        if not os.path.exists(manifest_path) or not os.path.exists(summary_path):
            return jsonify({"success": False, "error": "Manifest or summary not found"}), 404

        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        with open(summary_path, "r") as f:
            summary = json.load(f)

        return jsonify({"success": True, "manifest": manifest, "summary": summary}), 200

    def metrics_handler(self) -> Response:
        """
        Handle Prometheus metrics request.

        Returns:
            Prometheus metrics response
        """
        data = generate_latest()
        return Response(data, mimetype=CONTENT_TYPE_LATEST)

    def _register_trade_peer(self, host: str) -> None:
        """
        Register a trade peer.

        Args:
            host: Peer hostname
        """
        normalized = host.rstrip("/")
        if not normalized:
            return
        self.trade_peers[normalized] = time.time()
        logger.info(f"Registered wallet-trade peer {normalized}")

    def _gossip_trade_event(self, event: Dict[str, Any]) -> None:
        """
        Gossip trade event to peers.

        Args:
            event: Event to gossip
        """
        import requests

        for host, _ in list(self.trade_peers.items()):
            try:
                url = f"{host}/wallet-trades/gossip"
                requests.post(
                    url,
                    json=event,
                    headers={"X-Wallet-Trade-Secret": Config.WALLET_TRADE_PEER_SECRET},
                    timeout=3,
                )
                self.trade_peers[host] = time.time()
                logger.info(f"Gossiped trade event to {host}")
            except Exception as exc:
                logger.warning(f"Trade gossip to {host} failed: {exc}")
