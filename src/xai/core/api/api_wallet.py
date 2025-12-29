from __future__ import annotations

"""
Wallet and Trading API Handler

Handles all wallet and trading-related API endpoints including:
- Wallet creation (standard and embedded)
- WalletConnect integration
- Trade orders and matching
- Trade gossip protocol
- Wallet seeds snapshot
"""

import json
import logging
import os
import time
from typing import Any

import requests
from flask import Flask, Response, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

from xai.core.config import Config
from xai.core.security.security_validation import ValidationError
from xai.core.wallet import Wallet

logger = logging.getLogger(__name__)
ATTACHMENT_SAFE = True

trade_orders_counter = Counter("xai_trade_orders_total", "Total trade orders submitted")
trade_matches_counter = Counter("xai_trade_matches_total", "Total trade matches created")
trade_secrets_counter = Counter("xai_trade_secrets_revealed_total", "Secrets revealed for matches")
walletconnect_sessions_counter = Counter(
    "xai_walletconnect_sessions_total", "WalletConnect sessions registered"
)

class WalletAPIHandler:
    """Handles all wallet and trading-related API endpoints."""

    def __init__(
        self, node: Any, app: Flask, broadcast_callback: callable, trade_peers: dict[str, float]
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
        def create_wallet() -> tuple[dict[str, Any], int]:
            """Create new wallet."""
            return self.create_wallet_handler()

        @self.app.route("/wallet/embedded/create", methods=["POST"])
        def create_embedded_wallet() -> tuple[dict[str, Any], int]:
            """Create an embedded wallet alias."""
            return self.create_embedded_wallet_handler()

        @self.app.route("/wallet/embedded/login", methods=["POST"])
        def login_embedded_wallet() -> tuple[dict[str, Any], int]:
            """Login to embedded wallet."""
            return self.login_embedded_wallet_handler()

        # Transaction signing route
        @self.app.route("/wallet/sign", methods=["POST"])
        def sign_transaction() -> tuple[dict[str, Any], int]:
            """Sign transaction with ECDSA."""
            return self.sign_transaction_handler()

        # Public key derivation route
        @self.app.route("/wallet/derive-public-key", methods=["POST"])
        def derive_public_key() -> tuple[dict[str, Any], int]:
            """Derive public key from private key."""
            return self.derive_public_key_handler()

        # WalletConnect routes
        @self.app.route("/wallet-trades/wc/handshake", methods=["POST"])
        def walletconnect_handshake() -> tuple[dict[str, Any], int]:
            """WalletConnect handshake."""
            return self.walletconnect_handshake_handler()

        @self.app.route("/wallet-trades/wc/confirm", methods=["POST"])
        def walletconnect_confirm() -> tuple[dict[str, Any], int]:
            """Confirm WalletConnect handshake."""
            return self.walletconnect_confirm_handler()

        # Trade session routes
        @self.app.route("/wallet-trades/register", methods=["POST"])
        def register_trade_session() -> tuple[dict[str, Any], int]:
            """Create WalletConnect-style session."""
            return self.register_trade_session_handler()

        # Trade order routes
        @self.app.route("/wallet-trades/orders", methods=["GET"])
        def list_trade_orders() -> tuple[dict[str, Any], int]:
            """List trade orders."""
            return self.list_trade_orders_handler()

        @self.app.route("/wallet-trades/orders", methods=["POST"])
        def create_trade_order() -> tuple[dict[str, Any], int]:
            """Create trade order."""
            return self.create_trade_order_handler()

        @self.app.route("/wallet-trades/orders/<order_id>", methods=["GET"])
        def get_trade_order(order_id: str) -> tuple[dict[str, Any], int]:
            """Get specific trade order."""
            return self.get_trade_order_handler(order_id)

        # Trade match routes
        @self.app.route("/wallet-trades/matches", methods=["GET"])
        def list_trade_matches() -> tuple[dict[str, Any], int]:
            """List trade matches."""
            return self.list_trade_matches_handler()

        @self.app.route("/wallet-trades/matches/<match_id>", methods=["GET"])
        def get_trade_match(match_id: str) -> tuple[dict[str, Any], int]:
            """Get specific trade match."""
            return self.get_trade_match_handler(match_id)

        @self.app.route("/wallet-trades/matches/<match_id>/secret", methods=["POST"])
        def submit_trade_secret(match_id: str) -> tuple[dict[str, Any], int]:
            """Submit trade secret for match."""
            return self.submit_trade_secret_handler(match_id)

        # Gossip and snapshot routes
        @self.app.route("/wallet-trades/gossip", methods=["POST"])
        def inbound_gossip() -> tuple[dict[str, Any], int]:
            """Handle inbound gossip."""
            return self.inbound_gossip_handler()

        @self.app.route("/wallet-trades/snapshot", methods=["GET"])
        def snapshot_orderbook() -> tuple[dict[str, Any], int]:
            """Get orderbook snapshot."""
            return self.snapshot_orderbook_handler()

        @self.app.route("/wallet-trades/peers/register", methods=["POST"])
        def register_trade_peer() -> tuple[dict[str, Any], int]:
            """Register trade peer."""
            return self.register_trade_peer_handler()

        @self.app.route("/wallet-trades/backfill", methods=["GET"])
        def trade_backfill() -> tuple[dict[str, Any], int]:
            """Get trade event backfill."""
            return self.trade_backfill_handler()

        @self.app.route("/wallet-trades/history", methods=["GET"])
        def get_trade_history() -> tuple[dict[str, Any], int]:
            """Get trade history."""
            return self.get_trade_history_handler()

        @self.app.route("/wallet-seeds/snapshot", methods=["GET"])
        def wallet_seeds_snapshot() -> tuple[dict[str, Any], int]:
            """Get wallet seeds snapshot."""
            return self.wallet_seeds_snapshot_handler()

        # Metrics route
        @self.app.route("/metrics", methods=["GET"])
        def metrics() -> Response:
            """Get Prometheus metrics."""
            return self.metrics_handler()

    def create_wallet_handler(self) -> tuple[dict[str, Any], int]:
        """
        Handle wallet creation - returns encrypted keystore.

        SECURITY: This endpoint NEVER returns raw private keys in HTTP responses.
        Instead, it returns an encrypted keystore that the client must decrypt
        locally with their password.

        Expects JSON payload:
        {
            "encryption_password": "strong password (minimum 12 characters)"
        }

        Returns:
            Tuple of (response dict, HTTP status code)

        Response format:
        {
            "success": true,
            "address": "XAI...",
            "public_key": "hex-encoded public key",
            "encrypted_keystore": {
                "ciphertext": "base64-encoded AES-GCM ciphertext",
                "nonce": "base64-encoded nonce",
                "salt": "base64-encoded PBKDF2 salt"
            },
            "instructions": "Decrypt this keystore locally. Never share your password or decrypted keys."
        }

        Security Notes:
            - Uses AES-256-GCM encryption with PBKDF2 key derivation (100k iterations)
            - Password must be minimum 12 characters
            - Client must decrypt locally - server never stores or transmits raw private keys
            - Over HTTPS, encrypted keystore provides defense-in-depth
        """
        payload = request.get_json(silent=True) or {}
        password = payload.get("encryption_password")

        # Enforce strong password requirement
        if not password:
            logger.warning(
                "Wallet creation rejected: no encryption password provided",
                extra={"event": "wallet.create_no_password"}
            )
            return (
                jsonify({
                    "success": False,
                    "error": "encryption_password required",
                    "details": "Strong encryption password required (minimum 12 characters)",
                    "documentation": "https://xai.network/docs/wallet-security"
                }),
                400,
            )

        if len(password) < 12:
            logger.warning(
                "Wallet creation rejected: password too weak",
                extra={"event": "wallet.create_weak_password", "password_length": len(password)}
            )
            return (
                jsonify({
                    "success": False,
                    "error": "weak_password",
                    "details": "Password must be at least 12 characters for security",
                    "documentation": "https://xai.network/docs/wallet-security"
                }),
                400,
            )

        # Generate new wallet
        wallet = Wallet()

        # Prepare wallet data for encryption
        wallet_data = {
            "private_key": wallet.private_key,
            "public_key": wallet.public_key,
            "address": wallet.address,
            "created_at": time.time(),
            "version": "1.0"
        }

        # Encrypt the keystore with user's password
        try:
            encrypted_keystore = wallet._encrypt_payload(json.dumps(wallet_data), password)
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            logger.error(
                f"Wallet encryption failed: {e}",
                extra={"event": "wallet.encryption_failed"},
                exc_info=True
            )
            return (
                jsonify({
                    "success": False,
                    "error": "encryption_failed",
                    "details": "Failed to encrypt wallet keystore"
                }),
                500,
            )

        public_key = wallet.public_key.decode("utf-8") if isinstance(wallet.public_key, (bytes, bytearray)) else wallet.public_key

        logger.info(
            "Wallet created with encrypted keystore",
            extra={
                "event": "wallet.created_encrypted",
                "address": wallet.address[:16] + "...",
                "keystore_size": len(json.dumps(encrypted_keystore))
            }
        )

        return (
            jsonify({
                "success": True,
                "address": wallet.address,
                "public_key": public_key,
                "encrypted_keystore": encrypted_keystore,
                "instructions": "Decrypt this keystore locally with your password. Store it securely. Password cannot be recovered.",
                "warning": "NEVER share your password or decrypted private key. XAI support will NEVER ask for them.",
                "client_decryption_guide": "https://xai.network/docs/wallet-decryption"
            }),
            201,
        )

    def sign_transaction_handler(self) -> tuple[dict[str, Any], int]:
        """
        Handle transaction signing with ECDSA secp256k1.

        Expects JSON payload:
        {
            "message_hash": "hex-encoded SHA-256 hash of message",
            "private_key": "hex-encoded private key (64 chars)",
            "ack_hash_prefix": "first N chars of message_hash acknowledged by signer"
        }

        Returns:
            Tuple of (response dict, HTTP status code)

        Security Note:
            This endpoint receives private keys and should only be used
            over HTTPS. A hash-prefix acknowledgement is required to
            prevent blind signing. Prefer client-side signing for production.
        """
        from xai.core.security.crypto_utils import sign_message_hex

        try:
            payload = request.get_json(silent=True) or {}
            message_hash = payload.get("message_hash")
            private_key = payload.get("private_key")
            ack_prefix = (payload.get("ack_hash_prefix") or "").strip()

            # Validate inputs
            if not message_hash:
                return jsonify({"success": False, "error": "message_hash required"}), 400

            if not private_key:
                return jsonify({"success": False, "error": "private_key required"}), 400

            min_ack_len = max(8, int(getattr(Config, "SIGNING_ACK_PREFIX_MIN_LEN", 8)))
            if len(ack_prefix) < min_ack_len:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"ack_hash_prefix must be at least {min_ack_len} characters to confirm signer intent",
                        }
                    ),
                    400,
                )

            if len(private_key) != 64:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Invalid private key: must be 64 hex characters",
                        }
                    ),
                    400,
                )

            if len(message_hash) != 64:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Invalid message_hash: must be 64 hex characters (SHA-256)",
                        }
                    ),
                    400,
                )

            # Convert hex hash to bytes
            try:
                message_bytes = bytes.fromhex(message_hash)
            except ValueError:
                return (
                    jsonify(
                        {"success": False, "error": "message_hash must be valid hexadecimal"}
                    ),
                    400,
                )

            # Require explicit acknowledgement of the signing hash (case-insensitive prefix match)
            if not message_hash.lower().startswith(ack_prefix.lower()):
                return (
                    jsonify(
                        {"success": False, "error": "ack_hash_prefix does not match message_hash"}
                    ),
                    400,
                )

            # Sign the message hash with ECDSA
            signature = sign_message_hex(private_key, message_bytes)

            logger.info(
                "Transaction signed successfully",
                extra={
                    "event": "transaction.signed",
                    "signature_length": len(signature),
                },
            )

            return (
                jsonify(
                    {
                        "success": True,
                        "signature": signature,
                        "algorithm": "ECDSA-secp256k1",
                        "hash_algorithm": "SHA-256",
                    }
                ),
                200,
            )

        except ValueError as e:
            logger.error(f"Signing failed with ValueError: {e}")
            return jsonify({"success": False, "error": str(e)}), 400
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            logger.error(f"Unexpected error during signing: {e}", exc_info=True)
            return (
                jsonify({"success": False, "error": "Internal signing error"}),
                500,
            )

    def derive_public_key_handler(self) -> tuple[dict[str, Any], int]:
        """
        Handle public key derivation from private key.

        Expects JSON payload:
        {
            "private_key": "hex-encoded private key (64 chars)"
        }

        Returns:
            Tuple of (response dict, HTTP status code)

        Security Note:
            This endpoint receives private keys and should only be used
            over HTTPS in trusted environments.
        """
        from xai.core.security.crypto_utils import derive_public_key_hex

        try:
            payload = request.get_json(silent=True) or {}
            private_key = payload.get("private_key")

            # Validate input
            if not private_key:
                return jsonify({"success": False, "error": "private_key required"}), 400

            if len(private_key) != 64:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Invalid private key: must be 64 hex characters",
                        }
                    ),
                    400,
                )

            # Derive public key
            public_key = derive_public_key_hex(private_key)

            return (
                jsonify(
                    {
                        "success": True,
                        "public_key": public_key,
                        "curve": "secp256k1",
                    }
                ),
                200,
            )

        except ValueError as e:
            logger.error(f"Public key derivation failed with ValueError: {e}")
            return jsonify({"success": False, "error": str(e)}), 400
        except (OSError, IOError, ValueError, TypeError, RuntimeError, KeyError, AttributeError) as e:
            logger.error(f"Unexpected error during public key derivation: {e}", exc_info=True)
            return (
                jsonify({"success": False, "error": "Internal derivation error"}),
                500,
            )

    def create_embedded_wallet_handler(self) -> tuple[dict[str, Any], int]:
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
            logger.warning(
                "ValueError in create_embedded_wallet_handler",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "create_embedded_wallet_handler"
                }
            )
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

    def login_embedded_wallet_handler(self) -> tuple[dict[str, Any], int]:
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

    def walletconnect_handshake_handler(self) -> tuple[dict[str, Any], int]:
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

    def walletconnect_confirm_handler(self) -> tuple[dict[str, Any], int]:
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

    def register_trade_session_handler(self) -> tuple[dict[str, Any], int]:
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

    def list_trade_orders_handler(self) -> tuple[dict[str, Any], int]:
        """
        Handle trade orders listing.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        orders = self.node.blockchain.get_trade_orders()
        return jsonify({"success": True, "orders": orders}), 200

    def create_trade_order_handler(self) -> tuple[dict[str, Any], int]:
        """
        Handle trade order creation.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        order_data = request.json or {}
        try:
            result = self.node.blockchain.submit_trade_order(order_data)
        except ValueError as exc:
            logger.warning(
                "ValueError in create_trade_order_handler",
                extra={
                    "error_type": "ValueError",
                    "error": str(exc),
                    "function": "create_trade_order_handler"
                }
            )
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

    def get_trade_order_handler(self, order_id: str) -> tuple[dict[str, Any], int]:
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

    def list_trade_matches_handler(self) -> tuple[dict[str, Any], int]:
        """
        Handle trade matches listing.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        matches = self.node.blockchain.get_trade_matches()
        return jsonify({"success": True, "matches": matches}), 200

    def get_trade_match_handler(self, match_id: str) -> tuple[dict[str, Any], int]:
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

    def submit_trade_secret_handler(self, match_id: str) -> tuple[dict[str, Any], int]:
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

    def inbound_gossip_handler(self) -> tuple[dict[str, Any], int]:
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

    def snapshot_orderbook_handler(self) -> tuple[dict[str, Any], int]:
        """
        Handle orderbook snapshot request.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        snapshot = self.node.blockchain.trade_manager.snapshot()
        return jsonify({"success": True, "snapshot": snapshot}), 200

    def register_trade_peer_handler(self) -> tuple[dict[str, Any], int]:
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

    def trade_backfill_handler(self) -> tuple[dict[str, Any], int]:
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

    def get_trade_history_handler(self) -> tuple[dict[str, Any], int]:
        """
        Handle trade history request.

        Returns:
            Tuple of (response dict, HTTP status code)
        """
        history = self.node.blockchain.trade_history
        return jsonify({"success": True, "history": history}), 200

    def wallet_seeds_snapshot_handler(self) -> tuple[dict[str, Any], int]:
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

    def _gossip_trade_event(self, event: dict[str, Any]) -> None:
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
            except requests.exceptions.Timeout as exc:
                logger.warning(f"Trade gossip to {host} timed out: {exc}")
            except requests.exceptions.ConnectionError as exc:
                logger.warning(f"Trade gossip connection to {host} failed: {exc}")
            except requests.exceptions.RequestException as exc:
                logger.warning(f"Trade gossip request to {host} failed: {exc}")
            except Exception as exc:
                # Unexpected error - log with context for debugging
                logger.warning(f"Unexpected error in trade gossip to {host}: {type(exc).__name__}: {exc}")
