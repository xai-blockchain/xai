"""
AXN Blockchain Node - Core Orchestration
Coordinates blockchain operations, mining, P2P networking, and API services.

This refactored version delegates most functionality to specialized modules:
- node_utils.py: Utility functions and constants
- node_api.py: All Flask route handlers
- node_consensus.py: Consensus and validation logic
- node_mining.py: Mining operations
- node_p2p.py: Peer-to-peer networking
"""

from __future__ import annotations
from typing import Optional, Set, Any, Dict, List, Callable
import json
import os
import sys
import time
import threading
import argparse
import weakref
import base64
import re
import logging
from queue import Queue, Full
import requests
from cryptography.fernet import Fernet, InvalidToken
from flask import Flask, request, make_response, jsonify
from flask_cors import CORS

logger = logging.getLogger(__name__)

# Import blockchain core
from xai.core.blockchain import Blockchain, Transaction
from xai.core.monitoring import MetricsCollector
from xai.core.security_validation import SecurityValidator, SecurityEventRouter
from xai.core.wallet import WalletManager
from xai.core.account_abstraction import AccountAbstractionManager
from xai.core.config import Config

# Import refactored modules
from xai.core.node_utils import (
    get_allowed_origins,
    get_base_dir,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_MINER_ADDRESS,
    ALGO_FEATURES_ENABLED,
)
from xai.core.node_api import NodeAPIRoutes
from xai.core.node_consensus import ConsensusManager
from xai.core.node_p2p import P2PNetworkManager
from xai.network.peer_manager import PeerManager
from xai.core.security_middleware import setup_security_middleware, SecurityConfig
from xai.core.request_validator_middleware import setup_request_validation
from xai.core.node_identity import load_or_create_identity


class CORSPolicyManager:
    """Production-grade CORS policy management.

    Implements Task 67: CORS Policy with environment-based whitelist,
    strict validation, and proper headers.
    """

    def __init__(self, app: Flask):
        """Initialize CORS policy manager.

        Args:
            app: Flask application instance
        """
        self.app = app
        self.allowed_origins = self._load_allowed_origins()
        self.setup_cors()

    def _load_allowed_origins(self) -> List[str]:
        """Load allowed origins from environment.

        Returns:
            List of allowed origin URLs
        """
        # Default: same-origin only in production
        default_origins: List[str] = []

        # Load from environment variable
        env_origins = os.getenv("XAI_ALLOWED_ORIGINS", "")
        if env_origins:
            origins = [origin.strip() for origin in env_origins.split(",") if origin.strip()]
            return origins

        # Network-specific defaults
        network = os.getenv("XAI_NETWORK_TYPE", "mainnet")
        if network == "testnet":
            # More permissive for testnet
            return ["http://localhost:*", "http://127.0.0.1:*"]
        elif network == "development":
            return ["*"]  # Allow all in development

        # Production: only specific domains
        return default_origins

    def setup_cors(self) -> None:
        """Setup CORS with strict policies."""
        if not self.allowed_origins or len(self.allowed_origins) == 0:
            # No CORS - same origin only
            logger.info("CORS: Same-origin only (production mode)")
            return

        # Configure CORS
        CORS(
            self.app,
            origins=self.allowed_origins,
            methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Admin-Token"],
            expose_headers=["Content-Range", "X-Content-Range"],
            supports_credentials=True,
            max_age=3600  # Cache preflight for 1 hour
        )

        logger.info(f"CORS configured with origins: {self.allowed_origins}")

        # Register request/response hooks
        self._register_hooks()

    def _register_hooks(self) -> None:
        """Register Flask hooks for CORS validation."""

        @self.app.before_request
        def check_cors() -> Optional[Any]:
            """Validate origin on all requests."""
            origin = request.headers.get("Origin")

            if origin and not self.validate_origin(origin):
                logger.warning(f"CORS: Blocked request from unauthorized origin: {origin}")
                return make_response(jsonify({
                    "error": "Origin not allowed",
                    "code": "cors_violation"
                }), 403)
            return None

        @self.app.after_request
        def add_cors_headers(response: Any) -> Any:
            """Add proper CORS headers to response."""
            origin = request.headers.get("Origin")

            if origin and self.validate_origin(origin):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key"

            return response

    def validate_origin(self, origin: str) -> bool:
        """Validate origin against whitelist.

        Args:
            origin: Origin URL to validate

        Returns:
            True if origin is allowed
        """
        if not origin:
            return False

        # Wildcard check
        if "*" in self.allowed_origins:
            return True

        # Exact match
        if origin in self.allowed_origins:
            return True

        # Pattern matching (e.g., http://localhost:*)
        for allowed in self.allowed_origins:
            if "*" in allowed:
                pattern = allowed.replace("*", ".*")
                if re.match(pattern, origin):
                    return True

        return False


class _SecurityWebhookForwarder:
    """Asynchronous webhook sender with retry/backoff."""

    def __init__(
        self,
        url: str,
        headers: Dict[str, str],
        timeout: int = 5,
        max_retries: int = 3,
        backoff: float = 1.5,
        max_queue: int = 500,
        start_worker: bool = True,
        queue_path: Optional[str] = None,
        encryption_key: Optional[str] = None,
    ) -> None:
        self.url = url
        self.headers = dict(headers)
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff
        self.max_backoff = 30.0
        self.dropped_events = 0
        self.queue_path = queue_path
        self._fernet = self._build_fernet(encryption_key)
        self.queue: Queue = Queue(maxsize=max_queue)
        self._load_persisted_events()
        self._worker_thread = None
        if start_worker:
            self._worker_thread = threading.Thread(target=self._worker, daemon=True)
            self._worker_thread.start()

    def enqueue(self, payload: Dict[str, Any]) -> None:
        try:
            self.queue.put_nowait(payload)
            self._persist_queue()
        except Full:
            self.dropped_events += 1
            print(f"[SECURITY] Dropping webhook event {payload.get('event_type')} (queue full)")

    def _worker(self) -> None:
        while True:
            payload = self.queue.get()
            try:
                self._deliver(payload)
            finally:
                self.queue.task_done()
                self._persist_queue()

    def _deliver(self, payload: Dict[str, Any]) -> None:
        attempt = 0
        while attempt < self.max_retries:
            try:
                requests.post(
                    self.url,
                    json=payload,
                    timeout=self.timeout,
                    headers=self.headers,
                )
                return
            except Exception as exc:
                attempt += 1
                if attempt >= self.max_retries:
                    print(
                        f"[SECURITY] Failed to deliver webhook event {payload.get('event_type')}: {exc}"
                    )
                    return
                delay = min(self.backoff * attempt, self.max_backoff)
                time.sleep(delay)

    def _persist_queue(self) -> None:
        if not self.queue_path:
            return
        try:
            directory = os.path.dirname(self.queue_path) or os.getcwd()
            os.makedirs(directory, exist_ok=True)
            snapshot = list(self.queue.queue)
            data = json.dumps(snapshot).encode("utf-8")
            if self._fernet:
                data = self._fernet.encrypt(data)
            with open(self.queue_path, "wb") as handle:
                handle.write(data)
        except Exception as exc:
            print(f"[SECURITY] Failed to persist webhook queue: {exc}")

    def _load_persisted_events(self) -> None:
        if not self.queue_path or not os.path.exists(self.queue_path):
            return
        try:
            with open(self.queue_path, "rb") as handle:
                data = handle.read()
            if self._fernet:
                try:
                    data = self._fernet.decrypt(data)
                except InvalidToken as exc:
                    print(f"[SECURITY] Failed to decrypt webhook queue: {exc}")
                    return
            payloads = json.loads(data.decode("utf-8"))
            for item in payloads:
                try:
                    self.queue.put_nowait(item)
                except Full:
                    self.dropped_events += 1
                    break
        except Exception as exc:
            print(f"[SECURITY] Failed to load webhook queue: {exc}")

    @staticmethod
    def _build_fernet(raw_key: Optional[str]) -> Optional[Fernet]:
        if not raw_key:
            return None
        key = raw_key.strip().encode("utf-8")
        try:
            return Fernet(key)
        except Exception:
            try:
                hex_bytes = bytes.fromhex(raw_key.strip())
                return Fernet(base64.urlsafe_b64encode(hex_bytes))
            except Exception as exc:
                print(f"[SECURITY] Invalid webhook queue key: {exc}")
                return None


from xai.core.blockchain_interface import BlockchainDataProvider

class BlockchainNode:
    """
    Main blockchain node implementation.

    Orchestrates all node operations including:
    - Blockchain management
    - Mining operations
    - P2P networking
    - API services
    - Consensus mechanisms
    """

    def __init__(
        self,
        blockchain: Optional[Blockchain] = None,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        miner_address: Optional[str] = None,
        **kwargs,
    ) -> None:
        """
        Initialize blockchain node.

        Args:
            blockchain: The blockchain instance to manage (creates new if None)
            host: Host address to bind to
            port: Port number to listen on
            miner_address: Address to receive mining rewards
        """
        # Core configuration
        self.blockchain = blockchain if blockchain is not None else Blockchain()
        self.host = host
        self.port = port
        self.miner_address = miner_address or DEFAULT_MINER_ADDRESS

        # Node state
        self.start_time: float = 0.0
        self.is_mining: bool = False
        self.peers: Set[str] = set()
        self.mining_thread: Optional[threading.Thread] = None
        self.mined_blocks_counter = 0
        self.last_mining_time = time.time()

        # Flask app setup
        self.app = Flask(__name__)
        self.app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(32).hex())

        # Load or create node identity (used for P2P message signing)
        try:
            data_dir = getattr(self.blockchain.storage, "data_dir", os.path.join(os.getcwd(), "data"))
            self.identity = load_or_create_identity(data_dir)
        except Exception as exc:
            print(f"[WARN] Failed to initialize node identity: {exc}")
            self.identity = {"private_key": "", "public_key": ""}

        # Setup CORS with production-grade policy manager (Task 67)
        self.cors_manager = CORSPolicyManager(self.app)

        # Enforce global request validation limits before any route handlers execute.
        self.request_validator = setup_request_validation(
            self.app,
            max_json_size=getattr(Config, "API_MAX_JSON_BYTES", 1_000_000),
            max_form_size=getattr(Config, "API_MAX_JSON_BYTES", 1_000_000) * 10,
        )

        # Initialize managers
        self.metrics_collector = MetricsCollector(
            blockchain=self.blockchain,
            update_interval=2,
        )
        self._register_security_sinks()
        self.consensus_manager = ConsensusManager(blockchain=self.blockchain)
        self.validator = SecurityValidator()

        # Peer-to-peer networking
        self.peer_manager = PeerManager(
            trusted_peer_pubkeys=getattr(Config, "TRUSTED_PEER_PUBKEYS", []),
            trusted_cert_fingerprints=getattr(Config, "TRUSTED_PEER_CERT_FINGERPRINTS", []),
            trusted_peer_pubkeys_file=getattr(Config, "TRUSTED_PEER_PUBKEYS_FILE", None) or None,
            trusted_cert_fps_file=getattr(Config, "TRUSTED_PEER_CERT_FPS_FILE", None) or None,
            nonce_ttl_seconds=getattr(Config, "PEER_NONCE_TTL_SECONDS", 300),
            require_client_cert=getattr(Config, "PEER_REQUIRE_CLIENT_CERT", False),
            ca_bundle_path=getattr(Config, "PEER_CA_BUNDLE", None) or None,
            dns_seeds=getattr(Config, "P2P_DNS_SEEDS", None),
            bootstrap_nodes=getattr(Config, "P2P_BOOTSTRAP_NODES", None),
        )
        self.p2p_manager = P2PNetworkManager(
            blockchain=self.blockchain,
            peer_manager=self.peer_manager,
            consensus_manager=self.consensus_manager,
            host=self.host,
            port=kwargs.get("p2p_port", 8765),
        )
        # Provide identity to P2P manager
        setattr(self.p2p_manager, "node_identity", self.identity)

        # Setup security middleware
        security_config = SecurityConfig()
        # Align security middleware CORS with CORSPolicyManager
        security_config.CORS_ORIGINS = self.cors_manager.allowed_origins
        self.security_middleware = setup_security_middleware(
            self.app,
            config=security_config,
            enable_cors=True
        )
        print("[INIT] Security middleware initialized")

        # Initialize optional features (these may not exist in all setups)
        self._initialize_optional_features()
        self._initialize_embedded_wallets()

        # Setup API routes
        self.api_routes = NodeAPIRoutes(self)
        self.api_routes.setup_routes()

        @self.app.before_request
        def before_request():
            request.start_time = time.time()

        @self.app.after_request
        def after_request(response):
            latency = time.time() - request.start_time
            self.metrics_collector.get_metric("xai_api_endpoint_latency_seconds").observe(
                latency, labels={"endpoint": request.path}
            )
            return response

        print("[INIT] Blockchain node initialized")

    def _register_security_sinks(self) -> None:
        SecurityEventRouter.register_sink(self._create_security_event_sink())

        webhook_url = getattr(Config, "SECURITY_WEBHOOK_URL", "")
        if webhook_url:
            SecurityEventRouter.register_sink(
                self._create_security_webhook_sink(
                    webhook_url,
                    getattr(Config, "SECURITY_WEBHOOK_TOKEN", ""),
                    int(getattr(Config, "SECURITY_WEBHOOK_TIMEOUT", 5) or 5),
                )
            )

    def _create_security_event_sink(self):
        """Create a weakref-backed sink so global security events feed metrics."""
        node_ref = weakref.ref(self)

        def _sink(event_type: str, details: Dict[str, Any], severity: str) -> None:
            node = node_ref()
            if not node:
                return
            collector = getattr(node, "metrics_collector", None)
            if collector:
                collector.record_security_event(event_type, severity, details)

        return _sink

    @staticmethod
    def _create_security_webhook_sink(
        url: str,
        token: str = "",
        timeout: int = 5,
        max_retries: int = 3,
        backoff: float = 1.5,
    ) -> Optional[Callable[[str, Dict[str, Any], str], None]]:
        sanitized_url = (url or "").strip()
        if not sanitized_url:
            return None

        base_headers = {"Content-Type": "application/json"}
        auth_token = (token or "").strip()
        if auth_token:
            scheme = "Bearer " if not auth_token.lower().startswith("bearer ") else ""
            base_headers["Authorization"] = f"{scheme}{auth_token}".strip()

        queue_path = getattr(Config, "SECURITY_WEBHOOK_QUEUE_PATH", "") or None
        encryption_key = getattr(Config, "SECURITY_WEBHOOK_QUEUE_KEY", "") or None
        forwarder = _SecurityWebhookForwarder(
            sanitized_url,
            base_headers,
            timeout=timeout,
            max_retries=max(1, max_retries),
            backoff=max(backoff, 0.1),
            queue_path=queue_path,
             encryption_key=encryption_key,
        )

        def _sink(event_type: str, details: Dict[str, Any], severity: str) -> None:
            normalized = (severity or "INFO").upper()
            if normalized not in {"WARNING", "WARN", "ERROR", "CRITICAL"}:
                return

            payload = {
                "event_type": event_type,
                "severity": normalized,
                "timestamp": time.time(),
                "details": details,
            }

            forwarder.enqueue(payload)

        return _sink

    def _initialize_optional_features(self) -> None:
        """
        Initialize optional features that may not be available.

        These features are initialized if ALGO_FEATURES_ENABLED or if
        the necessary managers exist in the blockchain.
        """
        # Ensure optional attributes exist even if the imports fail so other
        # parts of the node can safely introspect their availability.
        self.fee_optimizer = None
        self.fraud_detector = None
        self.recovery_manager = None
        self.exchange_wallet_manager = None
        self.crypto_deposit_manager = None
        self.payment_processor = None

        # Algorithmic features
        if ALGO_FEATURES_ENABLED:
            try:
                from xai.core.algo_fee_optimizer import FeeOptimizer
                from xai.core.fraud_detection import FraudDetector

                self.fee_optimizer = FeeOptimizer()
                self.fraud_detector = FraudDetector()
                print("[INIT] Algorithmic features enabled")
            except ImportError as exc:
                print(f"[WARN] Algorithmic features unavailable: {exc}")

        # Social recovery
        try:
            from xai.core.social_recovery import SocialRecoveryManager

            self.recovery_manager = SocialRecoveryManager()
        except (ImportError, AttributeError) as exc:
            print(f"[WARN] Social recovery disabled: {exc}")

        # Mining bonuses
        try:
            from xai.core.mining_bonus_system import MiningBonusSystem

            self.bonus_manager = MiningBonusSystem()
        except (ImportError, AttributeError):
            self.bonus_manager = None

        # Exchange features
        try:
            from xai.core.exchange_wallet_manager import ExchangeWalletManager

            self.exchange_wallet_manager = ExchangeWalletManager()
            self.blockchain.trade_manager.attach_exchange_manager(
                self.exchange_wallet_manager
            )
        except (ImportError, AttributeError) as exc:
            self.exchange_wallet_manager = None
            print(f"[WARN] Exchange wallet manager disabled: {exc}")

        if self.exchange_wallet_manager:
            try:
                from xai.core.crypto_deposit_manager import CryptoDepositManager

                self.crypto_deposit_manager = CryptoDepositManager(
                    exchange_wallet_manager=self.exchange_wallet_manager
                )
            except (ImportError, AttributeError):
                self.crypto_deposit_manager = None

            try:
                from xai.core.payment_processor import PaymentProcessor

                self.payment_processor = PaymentProcessor()
            except (ImportError, AttributeError):
                self.payment_processor = None

    def _initialize_embedded_wallets(self) -> None:
        """Initialize wallet and account abstraction managers for embedded wallets."""

        self.wallet_manager = None
        self.account_abstraction = None

        try:
            wallet_dir = getattr(Config, "WALLET_DIR", None)
            if wallet_dir:
                self.wallet_manager = WalletManager(data_dir=wallet_dir)
            else:
                self.wallet_manager = WalletManager()

            storage_dir = getattr(Config, "EMBEDDED_WALLET_DIR", None)
            self.account_abstraction = AccountAbstractionManager(
                wallet_manager=self.wallet_manager,
                storage_path=storage_dir,
            )
            print("[INIT] Embedded wallet manager initialized")
        except Exception as exc:
            self.wallet_manager = None
            self.account_abstraction = None
            print(f"[WARN] Embedded wallets disabled: {exc}")

    # ==================== FAUCET OPERATIONS ====================

    def queue_faucet_transaction(self, recipient: str, amount: float) -> Transaction:
        """
        Create a faucet transaction and enqueue it for inclusion in the next block.

        Args:
            recipient: Address that should receive the testnet funds.
            amount: Amount of XAI to credit.

        Returns:
            The created Transaction instance.
        """
        faucet_tx = Transaction(
            sender="COINBASE",
            recipient=recipient,
            amount=amount,
            tx_type="faucet",
            outputs=[{"address": recipient, "amount": amount}],
        )
        faucet_tx.metadata = {
            "type": "faucet",
            "requested_at": time.time(),
        }
        faucet_tx.txid = faucet_tx.calculate_hash()
        self.blockchain.pending_transactions.append(faucet_tx)
        return faucet_tx

    # ==================== MINING OPERATIONS ====================

    def start_mining(self) -> None:
        """Start automatic mining in background thread."""
        if self.is_mining:
            print("[WARN] Mining already active")
            return

        self.is_mining = True
        self.mining_thread = threading.Thread(target=self._mine_continuously, daemon=True)
        self.mining_thread.start()
        print("[MINING] Auto-mining started")

    def stop_mining(self) -> None:
        """Stop automatic mining."""
        if not self.is_mining:
            print("[WARN] Mining not active")
            return

        self.is_mining = False
        if self.mining_thread:
            self.mining_thread.join(timeout=5)
        print("[MINING] Auto-mining stopped")

    def _mine_continuously(self) -> None:
        """
        Continuously mine blocks.

        This method runs in a background thread and mines blocks
        whenever there are pending transactions.
        """
        while self.is_mining:
            if self.blockchain.pending_transactions:
                try:
                    print(
                        f"Mining block with {len(self.blockchain.pending_transactions)} transactions..."
                    )
                    block = self.blockchain.mine_pending_transactions(self.miner_address, self.identity)
                    print(f"[OK] Block {block.index} mined! Hash: {block.hash}")

                    self.mined_blocks_counter += 1
                    time_since_last_block = time.time() - self.last_mining_time
                    if time_since_last_block > 0:
                        mining_rate = self.mined_blocks_counter / time_since_last_block
                        self.metrics_collector.get_metric("xai_mining_rate_blocks_per_second").set(mining_rate)
                    
                    if self.mined_blocks_counter > 100:
                        self.mined_blocks_counter = 0
                        self.last_mining_time = time.time()

                    # Broadcast to peers
                    self.broadcast_block(block)
                except Exception as e:
                    print(f"[ERROR] Mining error: {e}")

            time.sleep(1)  # Small delay between mining attempts

    # ==================== P2P NETWORKING ====================

    def add_peer(self, peer_url: str) -> None:
        """
        Add peer node to the network.

        Args:
            peer_url: URL of the peer node (e.g., "http://peer.example.com:8545")
        """
        self.p2p_manager.add_peer(peer_url)

    def broadcast_transaction(self, transaction: Transaction) -> None:
        """
        Broadcast transaction to all peers.

        Args:
            transaction: Transaction to broadcast
        """
        self.p2p_manager.broadcast_transaction(transaction)

    def broadcast_block(self, block: Any) -> None:
        """
        Broadcast new block to all peers.

        Args:
            block: Block to broadcast
        """
        self.p2p_manager.broadcast_block(block)

    def sync_with_network(self) -> bool:
        """
        Sync blockchain with network.

        Queries all peers for their chains and adopts the longest valid chain.

        Returns:
            True if sync was successful and chain was updated
        """
        return self.p2p_manager.sync_with_network()

    # ==================== EXCHANGE ORDER MATCHING ====================

    def _match_orders(
        self, new_order: Dict[str, Any], all_orders: Dict[str, List[Dict[str, Any]]]
    ) -> bool:
        """
        Internal method to match buy/sell orders and execute balance transfers.

        This method is called by the exchange API to match orders immediately
        upon placement.

        Args:
            new_order: The newly placed order
            all_orders: Dictionary containing all buy and sell orders

        Returns:
            True if any trades were matched
        """
        try:
            matched_trades = []

            # Determine which orders to match against
            if new_order["order_type"] == "buy":
                matching_orders = [
                    o
                    for o in all_orders["sell"]
                    if o["status"] == "open" and o["price"] <= new_order["price"]
                ]
                matching_orders.sort(key=lambda x: x["price"])  # Lowest price first
            else:
                matching_orders = [
                    o
                    for o in all_orders["buy"]
                    if o["status"] == "open" and o["price"] >= new_order["price"]
                ]
                matching_orders.sort(key=lambda x: x["price"], reverse=True)  # Highest price first

            # Match orders
            for match_order in matching_orders:
                if new_order["remaining"] <= 0:
                    break

                # Calculate trade details
                trade_amount = min(new_order["remaining"], match_order["remaining"])
                trade_price = match_order["price"]
                trade_total = trade_price * trade_amount

                # Determine buyer and seller
                buyer_addr = (
                    new_order["address"]
                    if new_order["order_type"] == "buy"
                    else match_order["address"]
                )
                seller_addr = (
                    match_order["address"]
                    if new_order["order_type"] == "buy"
                    else new_order["address"]
                )

                base_currency = new_order.get("base_currency", "AXN")
                quote_currency = new_order.get("quote_currency", "USD")

                # Execute trade if exchange wallet manager available
                if self.exchange_wallet_manager:
                    trade_result = self.exchange_wallet_manager.execute_trade(
                        buyer_address=buyer_addr,
                        seller_address=seller_addr,
                        base_currency=base_currency,
                        quote_currency=quote_currency,
                        base_amount=trade_amount,
                        quote_amount=trade_total,
                    )

                    if not trade_result["success"]:
                        print(f"[ERROR] Trade execution failed: {trade_result.get('error')}")
                        continue

                    # Unlock balances
                    if new_order["order_type"] == "buy":
                        self.exchange_wallet_manager.unlock_from_order(
                            buyer_addr, quote_currency, trade_total
                        )
                        self.exchange_wallet_manager.unlock_from_order(
                            seller_addr, base_currency, trade_amount
                        )
                    else:
                        self.exchange_wallet_manager.unlock_from_order(
                            seller_addr, base_currency, trade_amount
                        )
                        self.exchange_wallet_manager.unlock_from_order(
                            buyer_addr, quote_currency, trade_total
                        )

                # Create trade record
                trade = {
                    "id": f"trade_{int(time.time() * 1000)}",
                    "pair": f"{base_currency}/{quote_currency}",
                    "buyer": buyer_addr,
                    "seller": seller_addr,
                    "price": trade_price,
                    "amount": trade_amount,
                    "total": trade_total,
                    "timestamp": time.time(),
                }
                matched_trades.append(trade)

                # Update order remainings
                new_order["remaining"] -= trade_amount
                match_order["remaining"] -= trade_amount

                # Update order statuses
                if new_order["remaining"] <= 0:
                    new_order["status"] = "filled"
                if match_order["remaining"] <= 0:
                    match_order["status"] = "filled"

            # Save trades
            if matched_trades:
                trades_dir = os.path.join(get_base_dir(), "exchange_data")
                trades_file = os.path.join(trades_dir, "trades.json")

                if os.path.exists(trades_file):
                    with open(trades_file, "r") as f:
                        all_trades = json.load(f)
                else:
                    all_trades = []

                all_trades.extend(matched_trades)

                with open(trades_file, "w") as f:
                    json.dump(all_trades, f, indent=2)

                # Update orders file
                orders_file = os.path.join(trades_dir, "orders.json")
                with open(orders_file, "w") as f:
                    json.dump(all_orders, f, indent=2)

            return len(matched_trades) > 0

        except Exception as e:
            print(f"[ERROR] Error matching orders: {e}")
            return False

    # ==================== NODE CONTROL ====================

    def run(self, debug: bool = False) -> None:
        """
        Start the blockchain node.

        Args:
            debug: Enable Flask debug mode
        """
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start_services(debug=debug))

    async def start_services(self, debug: bool = False) -> None:
        """
        Start all node services.
        """
        self.start_time = time.time()

        print("=" * 60)
        print("XAI BLOCKCHAIN NODE")
        print("=" * 60)
        print(f"Miner Address: {self.miner_address}")
        print(f"Listening on: http://{self.host}:{self.port}")
        print(f"P2P Listening on: ws://{self.p2p_manager.host}:{self.p2p_manager.port}")
        print(f"Blockchain height: {len(self.blockchain.chain)}")
        print(f"Network difficulty: {self.blockchain.difficulty}")
        print("=" * 60)

        # Start P2P manager
        await self.p2p_manager.start()

        # Start auto-mining by default
        self.start_mining()

        # Run Flask app in a separate thread
        flask_thread = threading.Thread(
            target=self.app.run,
            kwargs={"host": self.host, "port": self.port, "debug": debug, "threaded": True},
            daemon=True,
        )
        flask_thread.start()

        try:
            while True:
                await asyncio.sleep(3600)  # Keep the event loop running
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop_services()

    async def stop_services(self) -> None:
        """
        Stop all node services.
        """
        self.stop_mining()
        await self.p2p_manager.stop()


async def main_async() -> None:
    """Command-line entry point for running a blockchain node."""

    parser = argparse.ArgumentParser(description="XAI Blockchain Node")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("XAI_API_PORT", DEFAULT_PORT)),
        help="Port to listen on",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind to")
    parser.add_argument("--p2p-port", type=int, default=8765, help="P2P port to listen on")
    parser.add_argument("--miner", help="Miner wallet address")
    parser.add_argument("--data-dir", default=os.getenv("XAI_DATA_DIR", "data"), help="Directory to persist blockchain state")
    parser.add_argument("--peers", nargs="+", help="Peer node URLs")

    args = parser.parse_args()

    blockchain = Blockchain(data_dir=args.data_dir)
    node = BlockchainNode(
        blockchain=blockchain,
        host=args.host,
        port=args.port,
        p2p_port=args.p2p_port,
        miner_address=args.miner,
    )

    if args.peers:
        for peer in args.peers:
            node.add_peer(peer)

    await node.start_services()

def main() -> None:
    """Command-line entry point for running a blockchain node."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("Shutting down node...")

# Backwards compatibility alias
Node = BlockchainNode

# ==================== MAIN ENTRY POINT ====================

if __name__ == "__main__":
    main()
